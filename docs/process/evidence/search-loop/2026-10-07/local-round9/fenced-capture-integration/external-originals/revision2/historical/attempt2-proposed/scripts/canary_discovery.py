"""Live canary: run the real pipeline against real university websites.

This exists because a system verified only against its own fixtures is
verified against its own assumptions. The offline suite in
``tests/test_live_discovery.py`` proves the discovery *logic*; this proves what
the logic actually reaches on sites nobody wrote for us.

It is deliberately not a test. It needs the network, it is slow, its results
change when a university edits a page, and a red result here is a finding to
investigate rather than a build to fail.

What it measures, per institution:

* which URLs discovery selected, by category, and where each came from
* whether a programme page and a scholarship page were found at all
* pages fetched, and pages that failed, with the reason
* per page: how its reading ended (fetched-ok / fetch-failed / unreadable /
  classifier-rejected / no-pattern-match), what kind of page it was, and the
  adapter's own reason — so a zero claims are explained, not just reported
* how many claims came back, and the run's own completeness score
* structural false positives, in the four categories where we allow none:
  a full-ride classification, a degree applicability verdict, a deadline and
  an admission requirement each have to rest on a page specific enough to
  carry them.

Access is honest about refusal. If robots.txt disallows a path, the outcome is
recorded as BLOCKED and the institution is reported as blocked. Nothing here
retries with a different agent, ignores a directive, or substitutes a cached
copy to make a row look green.

Usage::

    ./.venv/bin/python scripts/canary_discovery.py --out ../artifacts/canary
    ./.venv/bin/python scripts/canary_discovery.py --only rug.nl --verbose
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import tempfile
from collections import Counter
from contextlib import contextmanager
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.adapters.discovery.live_discovery import (
    REGISTRY_PATH,
    LiveDiscoveryAdapter,
    registrable_domain,
)
from app.adapters.fetching import Fetcher
from app.catalogue.importer import identity_key, import_catalogue, stable_id
from app.config import Settings
from app.domain.enums import (
    ClaimStatus,
    DegreeLevel,
    EligibilityStatus,
    FetchOutcome,
    FundingClassification,
    PipelineStage,
    SourceSpecificity,
)
from app.jobs import worker as worker_module
from app.jobs.store import JobStore, worker_identity
from app.models import Job
from app.models.applicant import ApplicantProfileRow
from app.models.auth import Organization
from app.models.base import Base
from app.models.research import (
    ClaimRow,
    ProgramResultRow,
    ResearchRun,
)
from app.models.source_page import SourcePage
from app.models.university import University
from app.pipeline import read_budget
from app.pipeline.runner import ResearchRunner
from app.pipeline.state import RunState
from app.schemas.profile import (
    AcademicRecord,
    ApplicantProfileIn,
    ApplicationContext,
    FundingNeeds,
    GradeValue,
    IeltsScore,
    Preferences,
    SatScore,
)
from app.schemas.result import ProgramResult

#: Specificity levels that can carry a programme-specific fact. A university's
#: general funding page cannot settle a deadline for one programme.
PROGRAMME_SPECIFIC = {SourceSpecificity.PROGRAM_INTAKE, SourceSpecificity.PROGRAM}

#: Claim types whose value is only meaningful against a specific programme.
DEADLINE_CLAIMS = {"application_deadline", "scholarship_deadline"}

# Historical category KPI: the three evidence categories measured by the
# original 26/30 canary. Programme pages are deliberately a separate KPI.
CANARY_CATEGORIES = ("admissions", "costs", "scholarships")
PROGRAM_RECALL_TARGET = 0.7
CATEGORY_RECALL_TARGET = 26 / 30

# Fixed harness diagnostics are safe provenance. Arbitrary exception strings
# can contain SQL parameters or secrets and are deliberately not copied.
_SAFE_CAPTURE_CONTROL_MESSAGES = frozenset(
    {"BENCHMARK_PAGE_BUDGET_EXHAUSTED", "BENCHMARK_WALL_CLOCK_BUDGET_EXHAUSTED"}
)


def canary_profile() -> ApplicantProfileIn:
    """One realistic applicant, used for every institution.

    A Kazakhstani school-leaver applying for a bachelor's and needing nearly
    full funding: the case the product exists for, and the one where a wrong
    "full ride" costs the most. The IELTS writing band is deliberately 6.0, so
    a per-band requirement that the overall score would hide still bites.
    """
    return ApplicantProfileIn(
        display_name="Canary Applicant (synthetic)",
        context=ApplicationContext(
            level=DegreeLevel.BACHELOR,
            intended_fields=["computer science"],
            intake_term="fall",
            intake_year=2027,
            citizenship="Kazakhstan",
            country_of_residence="Kazakhstan",
            education_country="Kazakhstan",
            education_system="KZ national secondary",
            graduation_date="2027-05-25",
        ),
        academics=AcademicRecord(
            gpa=GradeValue(raw_value=4.8, raw_scale_max=5.0, raw_scale_label="KZ 5-point"),
            ielts=IeltsScore(overall=7.0, listening=7.5, reading=7.5, writing=6.0, speaking=7.0),
            sat=SatScore(total=1400, math=760, reading_writing=640),
        ),
        preferences=Preferences(),
        funding=FundingNeeds(max_annual_budget=6000, max_acceptable_gap=6000),
    )


class FetchAudit:
    """Records every request the pipeline makes, grouped by institution.

    Installed onto the fetcher the runner builds rather than replacing it, so
    the canary measures the exact fetch path the product uses — same robots
    handling, same cache, same limits — and cannot drift from
    ``ResearchRunner._make_fetcher``.
    """

    def __init__(self) -> None:
        self.by_domain: dict[str, Counter] = {}
        self.failures: dict[str, list[tuple[str, str]]] = {}

    def install(self, fetcher: Fetcher) -> Fetcher:
        original = fetcher.get

        async def audited(url: str, **kwargs):
            result = await original(url, **kwargs)
            domain = registrable_domain(url)
            self.by_domain.setdefault(domain, Counter())[result.outcome.value] += 1
            if not result.ok:
                self.failures.setdefault(domain, []).append(
                    (url, f"{result.outcome.value}: {(result.error or '')[:120]}")
                )
            return result

        fetcher.get = audited  # type: ignore[method-assign]
        return fetcher


class CanaryRunner(ResearchRunner):
    """The real runner, with its fetch path observed."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.audit = FetchAudit()
        self.discovery_instances: list[LiveDiscoveryAdapter] = []

    def _make_fetcher(self) -> Fetcher:
        return self.audit.install(super()._make_fetcher())

    def _make_discovery_adapter(self, fetcher):
        adapter = super()._make_discovery_adapter(fetcher)
        if isinstance(adapter, LiveDiscoveryAdapter):
            self.discovery_instances.append(adapter)
        return adapter


# --- per-page extraction outcomes -----------------------------------------

#: The record the runner files on the run for every page it touched:
#: "page <category>: <url> (page_type <type>[, <n> chars]): <reason>".
#: Categories: fetch-failed / unreadable / classifier-rejected /
#: no-pattern-match / fetched-ok.
_PAGE_OUTCOME_RE = re.compile(
    r"^page (?P<category>[a-z-]+): (?P<url>\S+) "
    r"\(page_type (?P<page_type>[a-z_]+)(?:, (?P<characters>\d+) chars)?\): (?P<detail>.*)$"
)


def page_outcomes(run: ResearchRun) -> list[dict[str, str]]:
    """The run's per-page outcome records, parsed back out of its diagnostics.

    Both columns are read: a page that could not be read at all is filed as a
    failure, a page that was read and said nothing as an unknown, and the
    report has to count both to explain a zero.
    """
    found = []
    for line in list(run.errors or []) + list(run.unknowns or []):
        match = _PAGE_OUTCOME_RE.match(str(line))
        if match:
            found.append(match.groupdict())
    return found


# --- the four zero-tolerance checks --------------------------------------


def false_positives(result: ProgramResult, claims: list[dict]) -> list[dict]:
    """Structural false positives in the categories that allow none.

    Each check asks the same question: is the page this rests on specific
    enough to carry the statement? A claim without a source, without an
    excerpt, or from a page too general for the question is a defect whether or
    not the value happens to be right.
    """
    found: list[dict] = []

    def flag(kind: str, detail: str, url: str = "") -> None:
        found.append({"kind": kind, "detail": detail, "url": url})

    by_type: dict[str, list[dict]] = {}
    for claim in claims:
        by_type.setdefault(claim["claim_type"], []).append(claim)

    # 1. Full ride. The strongest statement the product can make about money.
    for scholarship in result.scholarships:
        if scholarship.classification is not FundingClassification.FULL_RIDE_CONFIRMED:
            continue
        supporting = [
            c
            for c in claims
            if c["claim_type"].startswith("scholarship")
            and scholarship.name.lower()[:24] in json.dumps(c["payload"]).lower()
        ]
        if not supporting:
            flag(
                "full_ride_without_evidence",
                f"{scholarship.name!r} classified FULL_RIDE_CONFIRMED with no claim behind it",
            )
        elif not any(c["payload"].get("original_text_excerpt") for c in supporting):
            flag(
                "full_ride_without_excerpt",
                f"{scholarship.name!r} has claims but none quote the page",
                supporting[0]["source_url"],
            )
        if scholarship.international_eligible != "yes":
            flag(
                "full_ride_without_confirmed_eligibility",
                f"{scholarship.name!r} is FULL_RIDE_CONFIRMED while international "
                f"eligibility is {scholarship.international_eligible!r}",
            )

    # 2. Degree applicability. "This award is for bachelors" is a claim about
    #    the award, and needs the award's own page to say so.
    for scholarship in result.scholarships:
        if scholarship.degree_applicability == "unknown":
            continue
        if not scholarship.degree_applicability_reason:
            flag(
                "degree_applicability_without_reason",
                f"{scholarship.name!r} states degree applicability "
                f"{scholarship.degree_applicability!r} with no stated reason",
            )

    # 3. Deadlines. A date is worthless attached to the wrong page.
    for claim_type in DEADLINE_CLAIMS:
        for claim in by_type.get(claim_type, []):
            if claim["source_specificity"] not in {s.value for s in PROGRAMME_SPECIFIC} | {
                SourceSpecificity.UNIVERSITY_ADMISSIONS.value,
                SourceSpecificity.SCHOLARSHIP_ADMINISTRATOR.value,
            }:
                flag(
                    "deadline_from_general_page",
                    f"{claim_type} taken from a {claim['source_specificity']} page",
                    claim["source_url"],
                )
            if not claim["payload"].get("original_text_excerpt"):
                flag("deadline_without_excerpt", claim_type, claim["source_url"])

    # 4. Admission requirements. A satisfied/failed verdict has to name the
    #    page it came from, and that page has to be about admission.
    for check in result.requirement_checks:
        # The statuses this used to skip - "unknown", "needs_clarification" -
        # are not values `EligibilityStatus` has ever had, so the skip never
        # fired either. The honest "could not confirm" answer is
        # NEEDS_OFFICIAL_CLARIFICATION, and it asserts nothing about the
        # applicant, so it is the one that needs no source behind it.
        if check.status == EligibilityStatus.NEEDS_OFFICIAL_CLARIFICATION:
            continue
        # `RequirementCheck.requirement` is the requirement's name, a plain
        # string, and its provenance is `claim_ids`. This check used to ask the
        # string for `.claim_type` and `.source_url`, which no string has, so it
        # could never pass: any decided requirement was reported as a false
        # positive. It went unnoticed because until Charles University joined
        # the registry every live requirement came back unknown or
        # needs_clarification, and the branch was never taken. A release gate
        # that cannot pass is worse than no gate: the first time it fired it
        # was wrong, and the instinct on a red gate is to change the product.
        if not check.claim_ids:
            flag(
                "requirement_verdict_without_source",
                f"{check.requirement} decided {check.status.value} with no claim behind it",
            )

    # 5. Any claim at all that lacks the provenance the product promises.
    for claim in claims:
        if not claim["source_url"]:
            flag("claim_without_url", claim["claim_type"])
        elif not claim["payload"].get("original_text_excerpt"):
            flag("claim_without_excerpt", claim["claim_type"], claim["source_url"])
        elif not claim.get("accessed_at"):
            flag("claim_without_timestamp", claim["claim_type"], claim["source_url"])

    return found


# --- the run --------------------------------------------------------------

#: The tenant the canary writes into. Its database is a fresh temporary file
#: per run, so this identifier never meets anybody else's data.
CANARY_ORGANIZATION_ID = "00000000000000000000000000000c0d"


def select_registry_entries(registry: list[dict], selectors: list[str] | None) -> list[dict]:
    """Select one explicit live batch without changing registry order."""
    if not selectors:
        return list(registry)
    normalized = [selector.strip().lower() for selector in selectors if selector.strip()]
    selected = [
        entry
        for entry in registry
        if any(
            selector in entry["homepage"].lower() or selector in entry["name"].lower()
            for selector in normalized
        )
    ]
    if not selected:
        raise SystemExit(f"no institution in the registry matches {selectors!r}")
    return selected


def select_catalogue_entries(session: Session, ids: list[str]) -> list[dict]:
    """Explicit imported identities only; never export seed facts or research routes."""
    if not ids or len(set(ids)) != len(ids):
        raise ValueError("Catalogue selection must be nonempty and have no duplicate ids")
    entries = []
    for university_id in ids:
        if not re.fullmatch(r"[0-9a-f]{32}", university_id):
            raise ValueError("Catalogue selection requires stable 32-character ids")
        university = session.get(University, university_id)
        if university is None or not university.domain:
            raise ValueError("Catalogue id is unknown or has no public domain hint")
        entries.append(
            {
                "id": university.id,
                "name": university.name,
                "country": university.country,
                "homepage": f"https://{university.domain}/",
                "identity_status": university.domain_status,
            }
        )
    return entries


def recall_metrics(rows: list[dict]) -> dict[str, dict[str, float | int]]:
    """Publish recall as honest numerators and denominators, never a slogan."""
    program_numerator = sum(bool(row.get("program_page_found")) for row in rows)
    category_numerator = sum(
        bool((row.get("discovered") or {}).get(category))
        for row in rows
        for category in CANARY_CATEGORIES
    )
    return {
        "program": {
            "numerator": program_numerator,
            "denominator": len(rows),
            "target": PROGRAM_RECALL_TARGET,
        },
        "category": {
            "numerator": category_numerator,
            "denominator": len(rows) * len(CANARY_CATEGORIES),
            "target": CATEGORY_RECALL_TARGET,
        },
    }


def validate_job_protocol(only, batch, catalogue_ids, native, fenced, *, check_seeds=False):
    if native and not fenced:
        raise ValueError("University read budget requires a genuine fenced research Job")
    if not fenced:
        return
    if check_seeds:
        raise ValueError("Fenced research protocol does not cover check-seeds")
    groups = int(bool(only)) + int(bool(batch)) + int(bool(catalogue_ids))
    if groups != 1 or (batch and len(batch) != 1) or (catalogue_ids and len(catalogue_ids) != 1):
        raise ValueError("Fenced research requires exactly one explicit identity selector")


async def run_canary(
    only,
    verbose,
    batch=None,
    *,
    catalogue_ids=None,
    university_read_budget=None,
    fenced_research_job=False,
    stop_file=None,
):
    native = (
        read_budget.UNIVERSITY_READ_BUDGET
        if university_read_budget is None
        else university_read_budget
    )
    validate_job_protocol(only, batch, catalogue_ids, native, fenced_research_job)
    if fenced_research_job and stop_file is not None and stop_file.exists():
        raise ValueError("PROVIDER_STOP_BEFORE_JOB")
    with patch.object(read_budget, "UNIVERSITY_READ_BUDGET", native):
        return await _run_canary(
            only,
            verbose,
            batch,
            catalogue_ids=catalogue_ids,
            university_read_budget=native,
            fenced_research_job=fenced_research_job,
            stop_file=stop_file,
        )


async def _execute_fenced_job(engine, run_id, settings):
    """Real production dispatch; factories bind only this isolated SQLite run."""
    if engine.dialect.name != "sqlite" or not engine.url.database:
        raise ValueError("Genuine canary requires its isolated SQLite case database")
    factory = sessionmaker(bind=engine)
    owner = worker_identity()
    protocol = {
        "kind": "genuine-research-job",
        "sqlite_case_database": engine.url.database,
        "started": False,
        "native_ledger": None,
        "native_enabled": read_budget.UNIVERSITY_READ_BUDGET,
        "worker_id": owner,
        "observation_available": False,
        "control_error": None,
        "control_message": None,
    }
    runners = []
    with factory() as session:
        created = JobStore(session).enqueue(
            "research", run_id=run_id, idempotency_key="canary:" + run_id
        )
        session.commit()
    with factory() as session:
        store = JobStore(session, worker_id=owner, lease_seconds=settings.job_lease_seconds)
        job = store.claim(worker_id=owner)
        if not created.created or job is None or job.id != created.job_id or job.attempts != 1:
            raise ValueError("Genuine canary could not claim its fresh research Job")
        protocol.update(started=True, run_id=run_id, job_id=job.id, claim_token=job.attempts)
        session.commit()

    @contextmanager
    def scoped_session():
        with factory() as session:
            try:
                yield session
                session.commit()
            except BaseException:
                session.rollback()
                raise

    class JobRunner(CanaryRunner):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            runners.append(self)

        async def run_to_decision(self):
            try:
                return await super().run_to_decision()
            except BaseException as exc:
                self._canary_original_control = exc
                reason = getattr(exc, "reason", None)
                message = exc.args[0] if len(exc.args) == 1 else None
                message = (
                    message
                    if type(exc) in (RuntimeError, TimeoutError)
                    and isinstance(message, str)
                    and message in _SAFE_CAPTURE_CONTROL_MESSAGES
                    else None
                )
                protocol.update(
                    control_type=type(exc).__name__,
                    control_reason=reason,
                    control_message=message,
                    control_error=type(exc).__name__
                    + (": " + (reason or message) if reason or message else ""),
                )
                raise

    worker = worker_module.Worker(settings, worker_id=owner)
    escaped = None
    tasks = []
    loop = asyncio.get_running_loop()
    create = loop.create_task

    def tracked(coro, *args, **kwargs):
        task = create(coro, *args, **kwargs)
        if getattr(getattr(coro, "cr_code", None), "co_name", None) == "_beat":
            tasks.append(task)
        return task

    with (
        patch.object(worker_module, "session_scope", scoped_session),
        patch.object(worker_module, "ResearchRunner", JobRunner),
    ):
        loop.create_task = tracked
        try:
            await worker.execute(created.job_id)
        except BaseException as exc:
            escaped = exc
        finally:
            loop.create_task = create
            # Worker already cancels its heartbeat in finally; observe and join
            # just those tasks without a new source-work clock or immediate retry.
            await asyncio.gather(*tasks, return_exceptions=True)
            protocol.update(
                heartbeat_tasks=len(tasks),
                heartbeat_done=[t.done() for t in tasks],
                heartbeat_cancelled=[t.cancelled() for t in tasks],
                worker_jobs_done=worker.jobs_done,
                worker_jobs_failed=worker.jobs_failed,
            )
    return (runners[0] if runners else None), protocol, escaped


async def _run_canary(
    only: str | None,
    verbose: bool,
    batch: list[str] | None = None,
    *,
    catalogue_ids: list[str] | None = None,
    university_read_budget: bool | None = None,
    fenced_research_job: bool = False,
    stop_file: Path | None = None,
) -> dict:
    if catalogue_ids is not None and (only or batch):
        raise ValueError("Catalogue ids cannot be combined with registry selectors")
    registry = json.loads(REGISTRY_PATH.read_text())
    selectors = batch or ([only] if only else None)
    registry = select_registry_entries(registry, selectors)

    profile = canary_profile()
    workdir = Path(tempfile.mkdtemp(prefix="canary-"))

    # A throwaway database. The canary never touches the project's own data.
    engine = create_engine(f"sqlite:///{workdir / 'canary.db'}")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    import_catalogue(session)
    if catalogue_ids is not None:
        try:
            registry = select_catalogue_entries(session, catalogue_ids)
        except ValueError:
            session.close()
            engine.dispose()
            raise

    if fenced_research_job and len(registry) != 1:
        session.close()
        engine.dispose()
        raise ValueError("Fenced selector must resolve to exactly one university")

    settings = Settings(
        cache_dir=workdir / "cache",
        export_dir=workdir / "exports",
        database_url=f"sqlite:///{workdir / 'canary.db'}",
        candidate_limit=len(registry),
        verify_limit=len(registry),
        respect_robots=True,
    )

    # The organization is passed explicitly. It used to be a "dev-org" default
    # on the column, which Phase 4 removed so that a caller forgetting the
    # tenant fails loudly instead of writing into someone else's workspace.
    # This script was not re-run after that change and had been failing on a
    # NOT NULL constraint ever since - in a throwaway database of its own, so
    # the loudness went nowhere until the next canary.
    organization = Organization(id=CANARY_ORGANIZATION_ID, name="Canary", slug="canary")
    session.add(organization)
    session.flush()
    row = ApplicantProfileRow(
        organization_id=organization.id,
        display_name="canary",
        payload=profile.model_dump(mode="json"),
    )
    session.add(row)
    session.flush()
    run = ResearchRun(
        profile_id=row.id,
        stage=PipelineStage.QUEUED.value,
        demo_mode=False,
        stage_state=RunState.load(None).dump(),
        candidate_limit=len(registry),
        verify_limit=len(registry),
        university_ids=[
            e.get("id") or stable_id(identity_key(e["name"], e["country"])) for e in registry
        ],
    )
    session.add(run)
    session.flush()

    started = datetime.now(UTC)
    if fenced_research_job:
        run_id = run.id
        session.commit()
        session.close()
        try:
            runner, protocol, escaped = await _execute_fenced_job(engine, run_id, settings)
        except BaseException:
            engine.dispose()
            raise
        error = protocol.get("control_error") or ""
        try:
            with sessionmaker(bind=engine)() as reporting:
                run = reporting.get(ResearchRun, run_id)
                job = reporting.get(Job, protocol["job_id"])
                if run is None or job is None or runner is None:
                    raise ValueError("Genuine Job/run/runner provenance unavailable")
                report = _gather_report(
                    reporting, run, registry, runner, started, datetime.now(UTC), error, verbose
                )
                protocol.update(
                    job_status=job.status,
                    lease_token=job.attempts,
                    recorded_worker_id=job.worker_id,
                    native_ledger=deepcopy(
                        (run.settings_snapshot or {}).get(read_budget.LEDGER_KEY)
                    ),
                    page_outcomes=page_outcomes(run),
                    run_unknowns=list(run.unknowns or []),
                    run_errors=list(run.errors or []),
                    claim_records=[
                        {
                            "id": c.id,
                            "claim_type": c.claim_type,
                            "source_url": c.source_url,
                            "accessed_at": c.accessed_at.isoformat() if c.accessed_at else None,
                            "payload": c.payload,
                        }
                        for c in reporting.query(ClaimRow).filter(ClaimRow.run_id == run_id)
                    ],
                    observation_available=True,
                )
        except Exception as observation_error:
            # Observation may itself be contended. Preserve the original control
            # reason without a writer/retry or a fabricated zero native ledger.
            protocol.update(
                observation_available=False,
                observation_error=type(observation_error).__name__,
                native_ledger=None,
            )
            report = {
                "accessed_at": started.isoformat(),
                "duration_seconds": round((datetime.now(UTC) - started).total_seconds(), 1),
                "run_error": error or "PROTOCOL_OBSERVATION_UNAVAILABLE",
                "batch": [e["name"] for e in registry],
                "institutions": [],
                "totals": {
                    "institutions": len(registry),
                    "reached": None,
                    "blocked": None,
                    "program_pages_found": None,
                    "scholarship_pages_found": None,
                    "claims": None,
                    "false_positives": None,
                    "catalogs_walked": None,
                    "walker_programs_confirmed": None,
                    "source_pages_recorded": None,
                    "fetch_tiers": {},
                    "recall": {
                        "program": {
                            "numerator": None,
                            "denominator": len(registry),
                            "target": PROGRAM_RECALL_TARGET,
                        },
                        "category": {
                            "numerator": None,
                            "denominator": len(registry) * len(CANARY_CATEGORIES),
                            "target": CATEGORY_RECALL_TARGET,
                        },
                    },
                },
            }
        finally:
            engine.dispose()
        report["job_protocol"] = protocol
        hook = getattr(runner, "_record_fenced_report", None)
        if hook is not None:
            try:
                hook(report)
            except Exception as mapping_error:
                protocol["mapping_error"] = type(mapping_error).__name__
                report["run_error"] = error or "PROTOCOL_MAPPING_UNAVAILABLE"
        if escaped is not None:
            raise escaped
        return report

    runner = CanaryRunner(session, run, profile, settings)
    error = ""
    try:
        await runner.run_to_decision()
    except Exception as exc:  # a canary that crashes must still report
        error = f"{type(exc).__name__}: {exc}"
        if verbose:
            import traceback

            traceback.print_exc()
    finished = datetime.now(UTC)
    report = _gather_report(session, run, registry, runner, started, finished, error, verbose)
    session.close()
    return report


def _gather_report(session, run, registry, runner, started, finished, error, verbose):
    results = {
        r.university: ProgramResult.model_validate(r.payload)
        for r in session.query(ProgramResultRow).filter(ProgramResultRow.run_id == run.id)
    }
    claims_by_result: dict[str, list[dict]] = {}
    for c in session.query(ClaimRow).filter(ClaimRow.run_id == run.id):
        claims_by_result.setdefault(c.result_id or "", []).append(
            {
                "claim_type": c.claim_type,
                "status": c.status,
                "source_url": c.source_url,
                "source_specificity": c.source_specificity,
                "accessed_at": c.accessed_at.isoformat() if c.accessed_at else None,
                "payload": c.payload,
            }
        )
    result_ids = {
        r.university: r.id
        for r in session.query(ProgramResultRow).filter(ProgramResultRow.run_id == run.id)
    }

    traces = {t.institution: t for adapter in runner.discovery_instances for t in adapter.traces}

    # Per-page outcomes, filed by the runner next to the prose errors. Grouped
    # by domain so each institution's row explains its own pages.
    records_by_domain: dict[str, list[dict[str, str]]] = {}
    for record in page_outcomes(run):
        records_by_domain.setdefault(registrable_domain(record["url"]), []).append(record)

    rows = []
    for entry in registry:
        name = entry["name"]
        domain = registrable_domain(entry["homepage"])
        outcomes = runner.audit.by_domain.get(domain, Counter())
        blocked = outcomes.get(FetchOutcome.ROBOTS_DISALLOWED.value, 0)
        checked = sum(outcomes.values())
        failed = (
            checked
            - outcomes.get(FetchOutcome.OK.value, 0)
            - outcomes.get(FetchOutcome.CACHED.value, 0)
        )

        candidate = next((c for c in runner._candidates if c.name == name), None)
        trace = traces.get(name)
        result = results.get(name)
        claims = claims_by_result.get(result_ids.get(name, ""), [])
        page_records = records_by_domain.get(domain, [])
        outcome_counts = Counter(record["category"] for record in page_records)
        type_counts = Counter(
            record["page_type"] for record in page_records if record["page_type"] != "unclassified"
        )

        row_out = {
            "catalogue_id": entry.get("id"),
            "institution": name,
            "country": entry["country"],
            "domain": domain,
            "access": (
                "BLOCKED"
                if blocked and checked == blocked
                else "PARTIALLY_BLOCKED"
                if blocked
                else "REACHED"
                if checked
                else "NOT_ATTEMPTED"
            ),
            "robots_disallowed_requests": blocked,
            "pages_checked": checked,
            "pages_failed": failed,
            "failures": runner.audit.failures.get(domain, [])[:8],
            "outcomes": dict(outcomes),
            "discovered": trace.selected if trace else {},
            "discovery_trace": trace.as_dict() if trace else None,
            "programs": [p.url for p in candidate.programs] if candidate else [],
            "program_page_found": bool(candidate and candidate.programs),
            "scholarship_page_found": bool(candidate and candidate.scholarships_url),
            "discovery_notes": candidate.notes if candidate else "no candidate produced",
            "claims": len(claims),
            "claims_verified": sum(
                1
                for c in claims
                if c["status"]
                in (ClaimStatus.VERIFIED_CURRENT.value, ClaimStatus.POSSIBLY_STALE.value)
            ),
            "completeness": result.verification_completeness if result else 0.0,
            "eligibility": result.eligibility.value if result else "no result",
            "funding_fit": result.funding_fit.value if result else "no result",
            "scholarships_found": len(result.scholarships) if result else 0,
            "false_positives": false_positives(result, claims) if result else [],
            # Why the pages produced what they did, per page: fetch-failed /
            # unreadable / classifier-rejected / no-pattern-match / fetched-ok,
            # each read page's classification, and the adapter's own reason.
            "page_outcomes": dict(outcome_counts),
            "page_types": dict(type_counts),
            "page_diagnostics": page_records[:40],
        }
        rows.append(row_out)
        if verbose:
            print(
                f"  {name}: {row_out['access']}, {row_out['claims']} claims, "
                f"{len(row_out['false_positives'])} false positives",
                flush=True,
            )

    source_pages_recorded = session.query(SourcePage).count()
    fetch_tiers = dict(run.fetch_tiers or {})
    totals_outcomes: Counter = Counter()
    totals_types: Counter = Counter()
    for reported in rows:
        totals_outcomes.update(reported["page_outcomes"])
        totals_types.update(reported["page_types"])
    recall = recall_metrics(rows)
    return {
        "accessed_at": started.isoformat(),
        "duration_seconds": round((finished - started).total_seconds(), 1),
        "run_error": error,
        "batch": [entry["name"] for entry in registry],
        "institutions": rows,
        "totals": {
            "institutions": len(rows),
            "reached": sum(1 for r in rows if r["access"] == "REACHED"),
            "blocked": sum(1 for r in rows if r["access"].endswith("BLOCKED")),
            "program_pages_found": sum(1 for r in rows if r["program_page_found"]),
            "scholarship_pages_found": sum(1 for r in rows if r["scholarship_page_found"]),
            "claims": sum(r["claims"] for r in rows),
            "false_positives": sum(len(r["false_positives"]) for r in rows),
            "page_outcomes": dict(totals_outcomes),
            "page_types": dict(totals_types),
            "recall": recall,
            "catalogs_walked": sum(
                ((row.get("discovery_trace") or {}).get("walker") or {}).get("catalogs_walked", 0)
                for row in rows
            ),
            "walker_programs_confirmed": sum(
                ((row.get("discovery_trace") or {}).get("walker") or {}).get(
                    "programs_confirmed", 0
                )
                for row in rows
            ),
            "source_pages_recorded": source_pages_recorded,
            "fetch_tiers": fetch_tiers,
        },
    }


def markdown_table(report: dict) -> str:
    head = (
        "| Institution | Country | Access | Programme page | Scholarship page | "
        "Pages ok/fail | Claims | Completeness | False positives |\n"
        "|---|---|---|---|---|---|---|---|---|\n"
    )
    lines = []
    for r in report["institutions"]:
        ok = r["pages_checked"] - r["pages_failed"]
        lines.append(
            f"| {r['institution']} | {r['country']} | {r['access']} | "
            f"{'yes' if r['program_page_found'] else 'no'} | "
            f"{'yes' if r['scholarship_page_found'] else 'no'} | "
            f"{ok}/{r['pages_failed']} | {r['claims']} | "
            f"{r['completeness']:.0%} | {len(r['false_positives'])} |"
        )
    return head + "\n".join(lines)


def markdown_report(report: dict) -> str:
    totals = report["totals"]
    program = totals["recall"]["program"]
    category = totals["recall"]["category"]
    summary = (
        f"Accessed: {report['accessed_at']}\n\n"
        f"- Program recall: **{program['numerator']}/{program['denominator']}** "
        f"(target {PROGRAM_RECALL_TARGET:.0%})\n"
        f"- Category recall: **{category['numerator']}/{category['denominator']}** "
        f"(target {CATEGORY_RECALL_TARGET:.1%})\n"
        f"- False positives: **{totals['false_positives']}**\n"
        f"- Catalogs walked / programmes confirmed: **{totals['catalogs_walked']} / "
        f"{totals['walker_programs_confirmed']}**\n"
        f"- Source pages recorded: **{totals['source_pages_recorded']}**\n"
        f"- Fetch tiers: `{json.dumps(totals['fetch_tiers'], sort_keys=True)}`\n\n"
    )
    return summary + markdown_table(report) + "\n"


async def check_seeds() -> int:
    """Fetch every manual seed and report the ones that no longer resolve.

    A seed whose URL has moved is worse than no seed: it consumes the fetch
    budget and contributes nothing. The first live run found six dead seeds
    across four institutions, so this is a standing check rather than a
    one-time cleanup.
    """
    entries = json.loads(REGISTRY_PATH.read_text())
    workdir = Path(tempfile.mkdtemp(prefix="seed-check-"))
    broken: list[tuple[str, str, str, str]] = []
    total = 0
    async with Fetcher(workdir, respect_robots=True, contact="canary") as fetcher:
        for entry in entries:
            for category, url in (entry.get("seeds") or {}).items():
                total += 1
                result = await fetcher.get(url)
                if not result.ok:
                    broken.append((entry["name"], category, url, result.outcome.value))
                print(
                    f"{'ok ' if result.ok else 'BAD'} {entry['name'][:24]:26} {category:16} {url}",
                    flush=True,
                )
    print(f"\n{len(broken)} of {total} seeds no longer resolve")
    for name, category, url, outcome in broken:
        print(f"  {name} / {category}: {outcome} — {url}")
    return 1 if broken else 0


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, help="directory for the JSON and Markdown output")
    parser.add_argument("--only", help="substring of one institution's homepage")
    parser.add_argument(
        "--batch",
        help="comma-separated homepage/name substrings for one explicitly approved live batch",
    )
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument(
        "--catalogue-id", action="append", help="opt-in imported identity id; repeat for a batch"
    )
    parser.add_argument(
        "--check-seeds",
        action="store_true",
        help="only verify that the registry's manual seeds still resolve",
    )
    parser.add_argument(
        "--university-read-budget",
        action=argparse.BooleanOptionalAction,
        default=read_budget.UNIVERSITY_READ_BUDGET,
    )
    parser.add_argument(
        "--fenced-research-job", action=argparse.BooleanOptionalAction, default=False
    )
    args = parser.parse_args()

    if args.only and args.batch:
        parser.error("--only and --batch are mutually exclusive")
    if args.catalogue_id and (args.only or args.batch or args.check_seeds):
        parser.error("--catalogue-id cannot be combined with registry/seed selectors")

    try:
        validate_job_protocol(
            args.only,
            [x.strip() for x in args.batch.split(",")] if args.batch else None,
            args.catalogue_id,
            args.university_read_budget,
            args.fenced_research_job,
            check_seeds=args.check_seeds,
        )
    except ValueError as exc:
        parser.error(str(exc))

    if args.check_seeds:
        return await check_seeds()

    print("Live canary — real network, real sites, robots.txt respected.", flush=True)
    batch = [item.strip() for item in args.batch.split(",")] if args.batch else None
    report = await run_canary(
        args.only,
        args.verbose,
        batch=batch,
        catalogue_ids=args.catalogue_id,
        university_read_budget=args.university_read_budget,
        fenced_research_job=args.fenced_research_job,
    )

    print()
    print(markdown_table(report))
    print()
    totals = report["totals"]
    print(
        f"reached {totals['reached']}/{totals['institutions']}, "
        f"blocked {totals['blocked']}, "
        f"programme pages {totals['program_pages_found']}, "
        f"scholarship pages {totals['scholarship_pages_found']}, "
        f"claims {totals['claims']}, "
        f"false positives {totals['false_positives']}"
    )
    program = totals["recall"]["program"]
    category = totals["recall"]["category"]
    print(
        f"program recall {program['numerator']}/{program['denominator']} "
        f"(target {PROGRAM_RECALL_TARGET:.0%}); category recall "
        f"{category['numerator']}/{category['denominator']} "
        f"(target {CATEGORY_RECALL_TARGET:.1%})"
    )
    print(
        f"catalogs walked {totals['catalogs_walked']}, walker programmes confirmed "
        f"{totals['walker_programs_confirmed']}, source pages recorded "
        f"{totals['source_pages_recorded']}, fetch tiers {totals['fetch_tiers']}"
    )
    outcomes = totals.get("page_outcomes") or {}
    if outcomes:
        print(
            "page outcomes: "
            + ", ".join(f"{category} {count}" for category, count in sorted(outcomes.items()))
        )
        types = totals.get("page_types") or {}
        if types:
            print(
                "page types: "
                + ", ".join(f"{page_type} {count}" for page_type, count in sorted(types.items()))
            )
    if report["run_error"]:
        print(f"RUN ERROR: {report['run_error']}")

    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        stamp = datetime.fromisoformat(report["accessed_at"]).strftime("%Y-%m-%dT%H%M%SZ")
        (args.out / f"canary-{stamp}.json").write_text(json.dumps(report, indent=2))
        (args.out / f"canary-{stamp}.md").write_text(markdown_report(report))
        print(f"\nwrote {args.out}/canary-{stamp}.json")

    if args.fenced_research_job and report["run_error"]:
        return 2  # Genuine protocol partial/control outcome; no success exit invented.
    return 1 if totals["false_positives"] else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
