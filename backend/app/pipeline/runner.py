"""Pipeline execution.

Each stage reads what the previous stage persisted and writes its own output
back before returning, so an interrupted run resumes from the boundary rather
than from the beginning.
"""

from __future__ import annotations

import logging
import os
import socket
from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from app.adapters.base import Candidate, CandidateProgram
from app.adapters.browser import BrowserFetcher
from app.adapters.cost.web_costs import WebCostAdapter
from app.adapters.discovery.fixture_discovery import FixtureDiscoveryAdapter
from app.adapters.discovery.live_discovery import LiveDiscoveryAdapter
from app.adapters.documents.web_documents import WebDocumentsAdapter
from app.adapters.fetching import Fetcher
from app.adapters.government.web_government import WebGovernmentAdapter
from app.adapters.requirements.web_requirements import WebRequirementsAdapter
from app.adapters.scholarship.web_scholarships import WebScholarshipAdapter
from app.config import Settings
from app.domain import dedupe
from app.domain.conflicts import enforce_source_hierarchy, find_conflicts
from app.domain.costs import compute_funding_gap, total_cost
from app.domain.eligibility import evaluate_program
from app.domain.enums import (
    ClaimType,
    CostCategory,
    EligibilityStatus,
    PipelineStage,
    UserDecision,
)
from app.domain.freshness import age_days, apply_freshness, is_stale
from app.domain.funding import classify, funding_fit_for
from app.domain.scoring import admissions_fit_for, score_result
from app.domain.validation import validate_profile
from app.models import AuditEvent, ClaimRow, ConflictRow, ProgramResultRow, ResearchRun, new_id
from app.pipeline.state import IN_PROGRESS_STAGES, RunState
from app.schemas.claim import ClaimOut, UnresolvedQuestion
from app.schemas.profile import ApplicantProfileIn
from app.schemas.result import ProgramResult, Tristate

log = logging.getLogger("unimatch.pipeline")


class RunCancelled(RuntimeError):
    pass


class ResearchRunner:
    """Executes the pipeline for one run."""

    def __init__(
        self, session: Session, run: ResearchRun, profile: ApplicantProfileIn,
        settings: Settings, *, job_id: str | None = None,
    ) -> None:
        self.session = session
        self.run = run
        self.profile = profile
        self.settings = settings
        self.state = RunState.load(run.stage_state)
        self.demo = run.demo_mode
        # A per-run override wins over the server default, and verification is
        # never asked to cover more candidates than discovery produced.
        self.worker_id = f"{socket.gethostname()}:{os.getpid()}"
        #: When run by a worker, cancellation is observed through the job as
        #: well as the run, so either route stops the work.
        self.job_id = job_id
        #: Stages skipped because a previous attempt finished them.
        self.resumed_stages: list[str] = []
        self.candidate_limit = run.candidate_limit or settings.candidate_limit
        self.verify_limit = min(
            run.verify_limit or settings.verify_limit, self.candidate_limit
        )
        self.intake = f"{profile.context.intake_term} {profile.context.intake_year}"
        self._candidates: list[Candidate] = []

    # --- infrastructure -------------------------------------------------

    def _make_fetcher(self) -> Fetcher:
        return Fetcher(
            self.settings.cache_dir,
            delay_seconds=self.settings.fetch_delay_seconds,
            respect_robots=self.settings.respect_robots,
            offline=self.demo,
            cache_ttl_seconds=self.settings.cache_ttl_seconds,
            timeout=self.settings.fetch_timeout_seconds,
            contact=self.settings.fetch_contact,
            corpus_dir=self.settings.corpus_dir if self.demo else None,
        )

    def _audit(self, action: str, entity_type: str, entity_id: str, **detail) -> None:
        self.session.add(
            AuditEvent(actor="system", action=action, entity_type=entity_type,
                       entity_id=entity_id, detail=detail)
        )

    def _save(self) -> None:
        """Persist progress and refresh the lease.

        The heartbeat rides on the same commit as the progress it describes, so
        a worker that dies cannot leave a fresh heartbeat behind stale state.
        """
        self.run.stage_state = self.state.dump()
        self.run.heartbeat_at = datetime.now(UTC)
        # The lease follows the stage, not the order of assignments in the
        # caller: a run that is waiting on the user or finished holds no lease,
        # so it can never be mistaken for one whose worker died.
        try:
            in_progress = PipelineStage(self.run.stage) in IN_PROGRESS_STAGES
        except ValueError:
            in_progress = False
        self.run.worker_id = self.worker_id if in_progress else None
        self.session.add(self.run)
        self.session.commit()

    def _check_cancelled(self) -> None:
        """Observed between units of work so cancellation lands cleanly."""
        self.session.refresh(self.run)
        if self.run.cancelled:
            raise RunCancelled("Run was cancelled by the user.")
        if self.job_id is not None:
            from app.jobs.store import JobStore

            if JobStore(self.session).is_cancel_requested(self.job_id):
                raise RunCancelled("Job was cancelled by the user.")

    # --- entry point ------------------------------------------------------

    async def run_to_decision(self) -> None:
        """Stages 1-5, ending at AWAITING_USER_DECISION."""
        self.run.started_at = self.run.started_at or datetime.now(UTC)
        self.run.settings_snapshot = {
            "demo_mode": self.demo,
            "candidate_limit": self.candidate_limit,
            "verify_limit": self.verify_limit,
            "candidate_limit_source": "run" if self.run.candidate_limit else "server default",
            "academic_year": self.settings.academic_year,
            "target_currency": self.settings.target_currency,
            "respect_robots": self.settings.respect_robots,
        }
        fetcher = self._make_fetcher()
        browser = BrowserFetcher(fetcher, enabled=self.settings.enable_browser_tier and not self.demo)
        if browser.enabled:
            fetcher.attach_renderer(browser)
        try:
            async with fetcher:
                # Stages already marked done are not repeated. A retry after a
                # crash resumes from the boundary rather than redoing work and
                # colliding with the rows the first attempt already wrote.
                await self._maybe(PipelineStage.PROFILE_VALIDATION, self._stage_validate)
                # Discovery is cheap and its output is held in memory, so it is
                # re-run whenever candidates are needed downstream.
                await self._stage_discover(fetcher)
                await self._maybe(PipelineStage.PROGRAM_VERIFICATION, self._stage_verify, fetcher)
                await self._maybe(PipelineStage.FUNDING_DISCOVERY, self._stage_funding, fetcher)
                await self._maybe(PipelineStage.ASSESSMENT, self._stage_assess, fetcher)
            self.run.fetch_tiers = dict(fetcher.tier_counts)
            self._transition(PipelineStage.AWAITING_USER_DECISION)
            self._save()
        except RunCancelled:
            self.run.stage = PipelineStage.CANCELLED.value
            self.run.finished_at = datetime.now(UTC)
            self._audit("run_cancelled", "run", self.run.id)
            self._save()
            # Re-raise: swallowing this let the worker mark the job succeeded.
            raise
        except Exception as exc:  # keep the run inspectable rather than losing it
            log.exception("run %s failed", self.run.id)
            self.run.stage = PipelineStage.FAILED.value
            self.run.finished_at = datetime.now(UTC)
            self.run.errors = [*(self.run.errors or []), f"{type(exc).__name__}: {exc}"]
            self._audit("run_failed", "run", self.run.id, error=str(exc)[:400])
            self._save()
            raise
        finally:
            await browser.close()

    async def _maybe(self, stage: PipelineStage, step, *args) -> None:
        """Run a stage unless a previous attempt already completed it."""
        if self.state[stage].status == "done":
            log.info("run %s: skipping %s, already completed", self.run.id[:8], stage.value)
            self.resumed_stages.append(stage.value)
            return
        await step(*args)

    def _transition(self, stage: PipelineStage) -> None:
        self.run.stage = stage.value
        self.session.add(self.run)

    # --- stage 1: profile -------------------------------------------------

    async def _stage_validate(self) -> None:
        st = self.state[PipelineStage.PROFILE_VALIDATION]
        st.start(detail="Checking the profile for gaps that would weaken the result")
        self._transition(PipelineStage.PROFILE_VALIDATION)
        self._save()

        report = validate_profile(self.profile)
        if not report.can_proceed:
            st.fail(report.summary)
            self._save()
            raise ValueError(report.summary)
        st.finish(report.summary)
        self._audit("profile_validated", "run", self.run.id, gaps=len(report.gaps))
        self._save()

    # --- stage 2: discovery -----------------------------------------------

    async def _stage_discover(self, fetcher: Fetcher) -> None:
        self._check_cancelled()
        st = self.state[PipelineStage.CANDIDATE_DISCOVERY]
        st.start(detail="Searching catalogues and rankings for candidate universities")
        self._transition(PipelineStage.CANDIDATE_DISCOVERY)
        self._save()

        adapter = (
            FixtureDiscoveryAdapter(fetcher) if self.demo else LiveDiscoveryAdapter(fetcher)
        )
        self._candidates = await adapter.discover(self.profile, self.candidate_limit)
        # An adapter that over-delivers must not silently widen the run.
        if len(self._candidates) > self.candidate_limit:
            self._candidates = self._candidates[: self.candidate_limit]
        self.run.candidates_found = len(self._candidates)
        st.items_total = len(self._candidates)
        st.items_done = len(self._candidates)
        st.finish(
            f"{len(self._candidates)} candidates from {adapter.name}; "
            f"{sum(1 for c in self._candidates if c.verifiable)} have an official page to verify."
        )
        self._audit("candidates_discovered", "run", self.run.id,
                    count=len(self._candidates), adapter=adapter.name)
        self._save()

    # --- stage 3: programme verification -----------------------------------

    async def _stage_verify(self, fetcher: Fetcher) -> None:
        self._check_cancelled()
        st = self.state[PipelineStage.PROGRAM_VERIFICATION]
        targets = list(self._candidates)[: self.verify_limit]
        st.start(len(targets), "Reading official programme pages")
        self._transition(PipelineStage.PROGRAM_VERIFICATION)
        self._save()

        req = WebRequirementsAdapter(fetcher, self.settings.academic_year)
        cost = WebCostAdapter(fetcher, self.settings.academic_year)
        gov = WebGovernmentAdapter(fetcher)
        gov_cache: dict[str, str] = {}

        errors: list[str] = []
        retry: list[str] = []
        seen_keys: set[str] = set()

        for i, cand in enumerate(targets):
            self._check_cancelled()
            programs = cand.programs or [
                CandidateProgram(
                    name=f"{self.profile.context.intended_fields[0] if self.profile.context.intended_fields else 'Programme'} "
                         f"({self.profile.context.level.value})",
                    field=self.profile.context.intended_fields[0] if self.profile.context.intended_fields else "",
                    degree=self.profile.context.level,
                    url=None,
                )
            ]
            for prog in programs[:2]:
                key = dedupe.program_key(cand.name, prog.name, prog.degree, self.intake, cand.country)
                if key in seen_keys:
                    continue
                seen_keys.add(key)

                result = ProgramResult(
                    id=new_id(),
                    run_id=self.run.id,
                    university=cand.name,
                    university_id=dedupe.university_key(cand.name, cand.country),
                    country=cand.country,
                    city=cand.city,
                    program=prog.name,
                    program_url=prog.url,
                    degree=prog.degree,
                    intake=self.intake,
                    rankings=cand.rankings,
                    climate_fit=_fit_label(cand.attributes.get("climate"), self.profile.preferences.climate),
                    city_fit=_fit_label(cand.attributes.get("city_size"), self.profile.preferences.city_size),
                    workload_fit=_fit_label(cand.attributes.get("workload"), self.profile.preferences.acceptable_workload),
                    career_notes="",
                )

                ar = await req.verify(cand, prog, self.intake)
                errors.extend(ar.errors)
                retry.extend(ar.retry_urls)
                self.run.pages_checked += ar.pages_checked
                self.run.pages_failed += ar.pages_failed

                cb, cr = await cost.fetch(cand)
                errors.extend(cr.errors)
                retry.extend(cr.retry_urls)
                self.run.pages_checked += cr.pages_checked
                self.run.pages_failed += cr.pages_failed
                result.costs = cb

                if cand.country not in gov_cache:
                    gr = await gov.post_study_work(cand.country)
                    self.run.pages_checked += gr.pages_checked
                    self.run.pages_failed += gr.pages_failed
                    gov_cache[cand.country] = (
                        str(gr.claims[0].normalized_value) if gr.claims else ""
                    )
                    ar.claims.extend(gr.claims)
                result.post_study_work = gov_cache[cand.country]

                all_claims = ar.claims + cr.claims
                all_claims, demotion_qs = enforce_source_hierarchy(all_claims)
                all_claims = [
                    c.model_copy(
                        update={"status": apply_freshness(c.status, c.claim_type, c.accessed_at)}
                    )
                    for c in all_claims
                ]
                conflicts, all_claims = find_conflicts(
                    all_claims, context=f"{prog.name} at {cand.name}"
                )
                result.conflicts = conflicts
                result.unresolved.extend(demotion_qs)

                if not cand.verifiable:
                    result.unresolved.append(
                        UnresolvedQuestion(
                            topic="official source",
                            question=f"Which official page publishes entry requirements for {prog.name}?",
                            why_it_matters=(
                                "This university was found through a catalogue only. Nothing about "
                                "it has been verified against an official source."
                            ),
                            university=cand.name,
                            program=prog.name,
                            blocking=True,
                        )
                    )

                result.claims = [_to_out(c, f"{result.id}-c{j}") for j, c in enumerate(all_claims)]
                result.source_urls = sorted({c.source_url for c in all_claims})
                result.last_verified = max((c.accessed_at for c in all_claims), default=None)
                self._persist_result(result, all_claims, conflicts)
                st.items_done = i + 1
                self.run.programs_verified = len(seen_keys)
                self.run.claims_recorded += len(all_claims)

            if i % 4 == 0:
                self._save()

        self.run.errors = list(self.run.errors or []) + errors[:200]
        self.run.retry_urls = sorted(set(list(self.run.retry_urls or []) + retry))[:200]
        st.finish(
            f"{self.run.programs_verified} programmes checked across "
            f"{self.run.pages_checked} pages ({self.run.pages_failed} unreadable)."
        )
        self._save()

    # --- stage 4: funding --------------------------------------------------

    async def _stage_funding(self, fetcher: Fetcher) -> None:
        self._check_cancelled()
        st = self.state[PipelineStage.FUNDING_DISCOVERY]
        rows = self._rows()
        st.start(len(rows), "Reading official scholarship pages")
        self._transition(PipelineStage.FUNDING_DISCOVERY)
        self._save()

        adapter = WebScholarshipAdapter(fetcher, self.settings.academic_year)
        by_name = {c.name: c for c in self._candidates}
        errors: list[str] = []

        for i, row in enumerate(rows):
            self._check_cancelled()
            result = ProgramResult.model_validate(row.payload)
            cand = by_name.get(result.university)
            if cand is None:
                st.items_done = i + 1
                continue

            prog = CandidateProgram(name=result.program, field="", degree=result.degree, url=result.program_url)
            scholarships, ar = await adapter.find(cand, prog, self.profile)
            errors.extend(ar.errors)
            self.run.pages_checked += ar.pages_checked
            self.run.pages_failed += ar.pages_failed

            claims, demotion_qs = enforce_source_hierarchy(ar.claims)
            claims = [
                c.model_copy(update={"status": apply_freshness(c.status, c.claim_type, c.accessed_at)})
                for c in claims
            ]
            conflicts, claims = find_conflicts(claims, context=f"funding for {result.program}")

            # Bind the row explicitly: a bare closure over the loop variable is
            # correct only because dedupe_by runs now, and that is too subtle.
            scholarships = dedupe.dedupe_by(
                scholarships,
                lambda s, uni=result.university, country=result.country: dedupe.scholarship_key(
                    uni, s.name, country
                ),
            )

            total = total_cost(result.costs, self.settings.target_currency)
            tuition_money = result.costs.items.get(CostCategory.TUITION)
            for s in scholarships:
                s.eligibility_checks = _scholarship_eligibility(s, self.profile)
                # The checks are the evidence; this field is the verdict they
                # imply. Classification reads the verdict, so an award the
                # applicant cannot hold can never be classified as funding.
                s.applicant_eligible = _applicant_eligible(s)
                page_text = " ".join(
                    c.original_text_excerpt for c in claims if s.name[:30] in c.original_text_excerpt
                ) or s.name
                verdict = classify(
                    s,
                    total_cost_amount=total.amount if total else None,
                    tuition_amount=tuition_money.amount if tuition_money else None,
                    page_text=page_text,
                )
                s.classification = verdict.classification
                s.classification_reason = verdict.reason
                if verdict.marketing_language_detected and verdict.classification.value != "FULL_RIDE_CONFIRMED":
                    s.classification_reason += (
                        " The page uses promotional wording such as 'full ride'; the classification "
                        "here follows the published coverage table instead."
                    )
                if any(c.status.value == "NOT_ELIGIBLE" for c in s.eligibility_checks if hasattr(c.status, "value")):
                    pass

            result.scholarships = scholarships
            result.conflicts.extend(conflicts)
            result.unresolved.extend(demotion_qs)
            result.claims.extend(_to_out(c, f"{result.id}-f{j}") for j, c in enumerate(claims))
            result.source_urls = sorted(set(result.source_urls) | {c.source_url for c in claims})
            if not scholarships and ar.errors:
                result.unresolved.append(
                    UnresolvedQuestion(
                        topic="funding",
                        question=f"What scholarships are open to international students on {result.program}?",
                        why_it_matters="No official funding page could be read, so funding is unknown, not absent.",
                        university=result.university,
                        program=result.program,
                    )
                )

            self._update_result(row, result, extra_claims=claims, conflicts=conflicts)
            self.run.claims_recorded += len(claims)
            st.items_done = i + 1
            if i % 4 == 0:
                self._save()

        self.run.errors = list(self.run.errors or []) + errors[:200]
        st.finish(f"Funding checked for {len(rows)} programmes.")
        self._save()

    # --- stage 5: assessment -------------------------------------------------

    async def _stage_assess(self, fetcher: Fetcher) -> None:
        self._check_cancelled()
        st = self.state[PipelineStage.ASSESSMENT]
        rows = self._rows()
        st.start(len(rows), "Comparing the profile against verified requirements")
        self._transition(PipelineStage.ASSESSMENT)
        self._save()

        today = date.today()
        for i, row in enumerate(rows):
            result = ProgramResult.model_validate(row.payload)
            claims = [_from_out(c) for c in result.claims]

            outcome = evaluate_program(self.profile, claims, today=today)
            result.eligibility = outcome.status
            result.requirement_checks = outcome.checks
            result.hard_filter_failures = outcome.hard_filter_failures
            result.missing_prerequisites = outcome.missing_prerequisites

            dl = next((c for c in claims if c.claim_type == ClaimType.ADMISSION_DEADLINE), None)
            if dl is not None:
                parsed = _as_date(dl.normalized_value)
                result.admission_deadline = parsed
                result.admission_deadline_raw = str(dl.normalized_value)
                result.admission_deadline_timezone = (
                    dl.notes.replace("timezone: ", "") if dl.notes.startswith("timezone:") else None
                )
                result.deadline_passed = bool(parsed and parsed < today)

            for s in result.scholarships:
                if s.deadline and s.deadline < today:
                    s.eligibility_checks.append(
                        _check(
                            "Scholarship deadline",
                            s.deadline.isoformat(),
                            today.isoformat(),
                            EligibilityStatus.GAP,
                            f"The published scholarship deadline {s.deadline.isoformat()} has passed.",
                            hard=True,
                        )
                    )

            fit, best, reason = funding_fit_for(result.scholarships)
            result.funding_fit = fit
            result.best_funding_classification = best
            result.funding_gap = compute_funding_gap(
                result.costs, result.scholarships, self.settings.target_currency
            )
            if reason:
                result.funding_gap.warnings.append(reason)

            result.admissions_fit, fit_reason = admissions_fit_for(result, self.profile)
            result.preference_score = score_result(result, self.profile)
            result.preference_score.components.append(
                _explanation_component(fit_reason)
            )
            result.verification_completeness = _completeness(claims)
            result.career_notes = result.career_notes or ""

            self._update_result(row, result)
            st.items_done = i + 1
            if i % 5 == 0:
                self._save()

        st.finish(f"{len(rows)} programmes assessed on eligibility, admissions fit and funding fit.")
        self._audit("assessment_complete", "run", self.run.id, results=len(rows))
        self._save()

    # --- stage 6: documents (post-approval) ---------------------------------

    async def collect_documents(self) -> int:
        """Deep document collection for approved (and maybe) rows only."""
        st = self.state[PipelineStage.DOCUMENT_COLLECTION]
        rows = [
            r for r in self._rows()
            if r.user_decision in (UserDecision.APPROVED.value, UserDecision.MAYBE.value)
        ]
        st.start(len(rows), "Collecting documents and deadlines for approved programmes")
        self._transition(PipelineStage.DOCUMENT_COLLECTION)
        self._save()

        fetcher = self._make_fetcher()
        built = 0
        async with fetcher:
            adapter = WebDocumentsAdapter(fetcher, self.settings.academic_year)
            by_name = {c.name: c for c in self._candidates}
            if not by_name:
                disc = FixtureDiscoveryAdapter(fetcher) if self.demo else LiveDiscoveryAdapter(fetcher)
                self._candidates = await disc.discover(self.profile, self.candidate_limit)
                by_name = {c.name: c for c in self._candidates}

            for i, row in enumerate(rows):
                self._check_cancelled()
                result = ProgramResult.model_validate(row.payload)
                cand = by_name.get(result.university)
                if cand is None:
                    st.items_done = i + 1
                    continue
                prog = CandidateProgram(
                    name=result.program, field="", degree=result.degree, url=result.program_url
                )
                checklist, ar = await adapter.collect(cand, prog, result.scholarships)
                checklist.result_id = result.id
                self.run.pages_checked += ar.pages_checked
                self.run.pages_failed += ar.pages_failed
                result.checklist = checklist
                row.checklist = checklist.model_dump(mode="json")
                self._update_result(row, result)
                self._audit("checklist_built", "result", row.id, documents=len(ar.claims))
                built += 1
                st.items_done = i + 1
                self._save()

        st.finish(f"Checklists built for {built} approved programmes.")
        self._transition(PipelineStage.COMPLETED)
        self.run.finished_at = datetime.now(UTC)
        self._save()
        return built

    # --- persistence helpers ---------------------------------------------

    def _rows(self) -> list[ProgramResultRow]:
        return (
            self.session.query(ProgramResultRow)
            .filter(ProgramResultRow.run_id == self.run.id)
            .order_by(ProgramResultRow.id)
            .all()
        )

    def _persist_result(self, result: ProgramResult, claims, conflicts) -> None:
        """Write a result, or refresh the one a previous attempt wrote.

        A retry after a crash re-derives results the first attempt already
        stored. Inserting blindly violates the (run_id, dedupe_key) unique
        index and fails the retry, so an existing row is updated in place and
        its evidence replaced rather than appended to.
        """
        dedupe_key = dedupe.program_key(
            result.university, result.program, result.degree, result.intake, result.country
        )
        existing = (
            self.session.query(ProgramResultRow)
            .filter(
                ProgramResultRow.run_id == self.run.id,
                ProgramResultRow.dedupe_key == dedupe_key,
            )
            .one_or_none()
        )
        if existing is not None:
            result.id = existing.id
            self._replace_evidence(existing.id)
            self._update_result(existing, result, extra_claims=claims, conflicts=conflicts)
            return

        # The row's primary key is authoritative; the result document adopts it
        # so every claim, conflict and checklist points at the same identifier.
        row = ProgramResultRow(
            id=new_id(),
            run_id=self.run.id,
            dedupe_key=dedupe_key,
            university=result.university,
            university_key=result.university_id,
            country=result.country,
            program=result.program,
            eligibility=result.eligibility.value,
            admissions_fit=result.admissions_fit.value,
            funding_fit=result.funding_fit.value,
            funding_classification=result.best_funding_classification.value,
            score_total=0.0,
            payload=result.model_dump(mode="json"),
        )
        result.id = row.id
        row.payload = result.model_dump(mode="json")
        self.session.add(row)
        self.session.flush()
        self._store_claims(row.id, claims)
        self._store_conflicts(row.id, conflicts)

    def _update_result(self, row: ProgramResultRow, result: ProgramResult,
                       extra_claims=None, conflicts=None) -> None:
        result.id = row.id
        row.payload = result.model_dump(mode="json")
        row.eligibility = result.eligibility.value
        row.admissions_fit = result.admissions_fit.value
        row.funding_fit = result.funding_fit.value
        row.funding_classification = result.best_funding_classification.value
        row.score_total = result.preference_score.total if result.preference_score else 0.0
        self.session.add(row)
        if extra_claims:
            self._store_claims(row.id, extra_claims)
        if conflicts:
            self._store_conflicts(row.id, conflicts)

    def _replace_evidence(self, result_id: str) -> None:
        """Drop the evidence a previous attempt stored for this result.

        Re-running a stage re-reads the same pages, so keeping both copies
        would inflate the claim count and show the user duplicate evidence.
        """
        self.session.query(ClaimRow).filter(ClaimRow.result_id == result_id).delete(
            synchronize_session=False
        )
        self.session.query(ConflictRow).filter(ConflictRow.result_id == result_id).delete(
            synchronize_session=False
        )

    def _store_claims(self, result_id: str, claims) -> None:
        for c in claims:
            self.session.add(
                ClaimRow(
                    run_id=self.run.id,
                    result_id=result_id,
                    claim_type=c.claim_type.value,
                    status=c.status.value,
                    source_url=c.source_url,
                    source_specificity=c.source_specificity.value,
                    accessed_at=c.accessed_at,
                    payload=c.model_dump(mode="json"),
                )
            )

    def _store_conflicts(self, result_id: str, conflicts) -> None:
        for c in conflicts:
            self.session.add(
                ConflictRow(
                    run_id=self.run.id, result_id=result_id,
                    claim_type=c.claim_type.value, unresolved=c.unresolved,
                    payload=c.model_dump(mode="json"),
                )
            )


# --- small helpers ------------------------------------------------------


def _to_out(claim, claim_id: str) -> ClaimOut:
    return ClaimOut(
        **claim.model_dump(),
        id=claim_id,
        is_stale=is_stale(claim.claim_type, claim.accessed_at),
        age_days=age_days(claim.accessed_at),
    )


def _from_out(out: ClaimOut):
    from app.schemas.claim import Claim

    data = out.model_dump()
    for key in ("id", "is_stale", "age_days"):
        data.pop(key, None)
    return Claim(**data)


def _check(requirement, published, applicant, status, explanation, hard=False):
    from app.schemas.result import RequirementCheck

    return RequirementCheck(
        requirement=requirement, published_value=published, applicant_value=applicant,
        status=status, is_hard_filter=hard, explanation=explanation,
    )


def _scholarship_eligibility(s, profile: ApplicantProfileIn):
    """Check the applicant against an award's own published restrictions."""
    checks = []
    citizenship = profile.context.citizenship
    if s.citizenship_restrictions:
        allowed = " ".join(s.citizenship_restrictions).lower()
        ok = citizenship.lower() in allowed
        checks.append(
            _check(
                "Scholarship citizenship eligibility",
                s.citizenship_restrictions,
                citizenship,
                EligibilityStatus.MET if ok else EligibilityStatus.NOT_APPLICABLE,
                (
                    f"The award is restricted to {', '.join(s.citizenship_restrictions)}. "
                    f"An applicant holding {citizenship} citizenship is not eligible."
                    if not ok
                    else f"{citizenship} citizenship falls within the published restriction."
                ),
            )
        )
    elif s.international_eligible == "no":
        checks.append(
            _check(
                "Scholarship international eligibility", False, citizenship,
                EligibilityStatus.NOT_APPLICABLE,
                "The award is officially closed to international students.",
            )
        )
    elif s.international_eligible == "yes":
        checks.append(
            _check(
                "Scholarship international eligibility", True, citizenship,
                EligibilityStatus.MET,
                "The award is officially open to international students of any nationality.",
            )
        )

    for test, minimum in (s.min_test_scores or {}).items():
        got = {"ielts": profile.academics.ielts.overall,
               "toefl": profile.academics.toefl.total,
               "sat": profile.academics.sat.total}.get(test)
        if got is None:
            checks.append(
                _check(f"Scholarship {test.upper()} minimum", minimum, None,
                       EligibilityStatus.PENDING,
                       f"The award requires {test.upper()} {minimum}; no score is in the profile.")
            )
        else:
            checks.append(
                _check(f"Scholarship {test.upper()} minimum", minimum, got,
                       EligibilityStatus.MET if got >= minimum else EligibilityStatus.GAP,
                       f"Published minimum {minimum}; applicant {got}.")
            )
    return checks


def _applicant_eligible(scholarship) -> Tristate:
    """Roll a scholarship's eligibility checks into one three-valued verdict."""
    statuses = {c.status for c in scholarship.eligibility_checks}
    if scholarship.degree_applicability == "no" or scholarship.international_eligible == "no":
        return "no"
    if EligibilityStatus.NOT_APPLICABLE in statuses or EligibilityStatus.GAP in statuses:
        return "no"
    if not statuses or EligibilityStatus.PENDING in statuses:
        return "unknown"
    if scholarship.degree_applicability == "unknown":
        return "unknown"
    if statuses <= {EligibilityStatus.MET}:
        return "yes"
    return "unknown"


def _explanation_component(text: str):
    from app.schemas.result import ScoreComponent

    return ScoreComponent(
        name="Admissions fit rationale", raw=0.0, weight=0.0, weighted=0.0,
        explanation=text, data_present=True,
    )


#: The questions a user actually needs answered before applying. Completeness is
#: measured against these, not against whatever happened to be extracted -
#: otherwise a page yielding one verified fact and nothing else reads as 100%.
CORE_QUESTIONS: tuple[tuple[ClaimType, ...], ...] = (
    (ClaimType.IELTS_MIN_OVERALL, ClaimType.TOEFL_MIN_TOTAL, ClaimType.DUOLINGO_MIN),
    (ClaimType.MIN_GPA,),
    (ClaimType.ADMISSION_DEADLINE,),
    (ClaimType.TUITION, ClaimType.TOTAL_COST_OF_ATTENDANCE),
    (ClaimType.SCHOLARSHIP_EXISTS,),
    (ClaimType.SCHOLARSHIP_INTERNATIONAL_ELIGIBLE, ClaimType.SCHOLARSHIP_CITIZENSHIP_RESTRICTION),
)


def _completeness(claims) -> float:
    """Share of the core questions answered by a current, official claim."""
    from app.domain.enums import ClaimStatus

    verified = {
        c.claim_type
        for c in claims
        if c.status in (ClaimStatus.VERIFIED_CURRENT, ClaimStatus.POSSIBLY_STALE)
    }
    answered = sum(1 for group in CORE_QUESTIONS if verified & set(group))
    return round(answered / len(CORE_QUESTIONS), 3)


def _fit_label(actual: str | None, preferred: str) -> str:
    if not actual or actual == "unknown":
        return "unknown"
    if preferred in ("any", ""):
        return "acceptable"
    if actual == preferred:
        return "strong"
    ladders = {
        "city": ["small", "medium", "large", "metropolis"],
        "climate": ["cold", "temperate", "mediterranean", "warm"],
        "workload": ["moderate", "demanding", "very_demanding"],
    }
    for ladder in ladders.values():
        if actual in ladder and preferred in ladder:
            gap = abs(ladder.index(actual) - ladder.index(preferred))
            return {0: "strong", 1: "good", 2: "acceptable"}.get(gap, "weak")
    return "acceptable"


def _as_date(v):
    if isinstance(v, str):
        try:
            return date.fromisoformat(v)
        except ValueError:
            return None
    return v if isinstance(v, date) else None
