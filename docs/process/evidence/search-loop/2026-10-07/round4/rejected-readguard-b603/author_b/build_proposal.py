"""Write external source snapshots and a proposed production-path patch, never repo files."""
from pathlib import Path
import difflib
import hashlib
import json
import re

BASE = Path(__file__).resolve().parent
REPO = Path('/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply/backend')
OUT = BASE/'proposed'
SOURCES = ['app/adapters/base.py','app/pipeline/runner.py','app/catalogue/discovery.py','app/adapters/discovery/live_discovery.py','app/adapters/discovery/catalog_walker.py']
originals={p:(REPO/p).read_text() for p in SOURCES}
for path,source in originals.items():
    p=BASE/'original'/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(source)

def write(path,source):
    p=OUT/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(source)

s=originals['app/adapters/base.py'].replace('    search_queries_used: int = 0\n','    search_queries_used: int = 0\n    #: Stable imported identity for internal university-wide source-work scope.\n    catalogue_id: str | None = None\n',1)
write('app/adapters/base.py',s)

s=originals['app/pipeline/runner.py']
s=s.replace('import socket\n','import socket\nfrom contextlib import contextmanager\nfrom copy import deepcopy\n',1)
s=s.replace('from sqlalchemy import select\n','from sqlalchemy import select\nfrom sqlalchemy.exc import OperationalError\n',1)
s=s.replace('    ConflictRow,\n','    ConflictRow,\n    Job,\n',1)
s=s.replace('from app.adapters.base import Candidate, CandidateProgram, PageOutcome','from app.adapters.base import AdapterResult, Candidate, CandidateProgram, PageOutcome',1)
s=s.replace('from app.pipeline.state import IN_PROGRESS_STAGES, RunState','from app.pipeline import read_budget\nfrom app.pipeline.control import LeaseLost, RunCancelled, UniversityReadStopped\nfrom app.pipeline.state import IN_PROGRESS_STAGES, RunState',1)
start=s.index('class RunCancelled(RuntimeError):');end=s.index('class ResearchRunner:',start)
s=s[:start]+s[end:]
s=s.replace('        self._candidates: list[Candidate] = []\n','''        self._candidates: list[Candidate] = []
        self._read_guard_enabled = False
        self._read_guard_out_of_scope = False
        self._read_guard_writing = False
        self._read_episode_fresh = False
        self._read_job_kind: str | None = None
''',1)
s=s.replace('''        return Fetcher(
            self.settings.cache_dir,''','''        factory = read_budget.BudgetedFetcher if self._read_guard_enabled else Fetcher
        extra = {"before_get": self._reserve_university_read} if self._read_guard_enabled else {}
        return factory(
            self.settings.cache_dir,''',1)
s=s.replace('''            corpus_dir=self.settings.corpus_dir if self.demo else None,
        )''','''            corpus_dir=self.settings.corpus_dir if self.demo else None,
            **extra,
        )''',1)
s=s.replace('''            page_recorder=lambda **fields: SourcePage.record(self.session, **fields),
        )''','''            page_recorder=lambda **fields: SourcePage.record(self.session, **fields),
            research_scope=self._university_read_scope if self._read_guard_enabled else None,
        )''',1)
# The existing fence remains the only committer; ordinary checkpoints preserve latest JSON under lock.
s=s.replace('''        self.run.stage_state = self.state.dump()
''','''        if not self._read_guard_writing and (
            self._read_guard_enabled or read_budget.LEDGER_KEY in (self.run.settings_snapshot or {})
        ):
            self.run.settings_snapshot = read_budget.copy_snapshot_with_ledger(
                self.run.settings_snapshot or {}, self._read_snapshot(lock=True)
            )
        self.run.stage_state = self.state.dump()
''',1)
# Recheck/document jobs are explicitly outside this bounded decision-episode prototype.
s=s.replace('''        await self.run_to_decision()
        return len(stale_claims)''','''        prior = self._read_guard_out_of_scope
        self._read_guard_out_of_scope = True
        try:
            await self.run_to_decision()
        finally:
            self._read_guard_out_of_scope = prior
        return len(stale_claims)''',1)
s=s.replace('''        self.run.started_at = self.run.started_at or datetime.now(UTC)
        self.run.settings_snapshot = {''','''        self._read_episode_fresh = self.run.started_at is None
        self._read_guard_enabled = (
            read_budget.UNIVERSITY_READ_BUDGET and not self.demo and not self._read_guard_out_of_scope
        )
        previous_snapshot = deepcopy(self.run.settings_snapshot or {})
        self.run.started_at = self.run.started_at or datetime.now(UTC)
        self.run.settings_snapshot = {''',1)
s=s.replace('''            "university_ids": self.run.university_ids or [],
        }
        fetcher = self._make_fetcher()''','''            "university_ids": self.run.university_ids or [],
        }
        if read_budget.LEDGER_KEY in previous_snapshot:
            self.run.settings_snapshot[read_budget.LEDGER_KEY] = previous_snapshot[read_budget.LEDGER_KEY]
        if self._read_guard_enabled:
            self.run.settings_snapshot["university_read_budget_scope"] = "decision-job-episode"
        fetcher = self._make_fetcher()''',1)
s=s.replace('''        st = self.state[PipelineStage.DOCUMENT_COLLECTION]
''','''        self._read_guard_enabled = False  # Post-approval documents have no budget contract here.
        st = self.state[PipelineStage.DOCUMENT_COLLECTION]
''',1)
# Wrap each real source adapter call separately: completed caller-owned outputs survive later refusal.
s=s.replace('''                ar = await req.verify(cand, prog, self.intake)
''','''                budget_stopped = False
                ar = AdapterResult()
                try:
                    with self._university_read_scope(cand):
                        ar = await req.verify(cand, prog, self.intake)
                except UniversityReadStopped as stopped:
                    budget_stopped = True
                    self._read_budget_unknown(cand, stopped, result)
''',1)
s=s.replace('''                cb, cr = await cost.fetch(cand)
''','''                cb, cr = CostBreakdown(), AdapterResult()
                try:
                    with self._university_read_scope(cand):
                        cb, cr = await cost.fetch(cand)
                except UniversityReadStopped as stopped:
                    budget_stopped = True
                    self._read_budget_unknown(cand, stopped, result)
''',1)
s=s.replace('''                    gr = await gov.post_study_work(cand.country)
''','''                    gr = AdapterResult()
                    government_stopped = False
                    try:
                        with self._university_read_scope(cand):
                            gr = await gov.post_study_work(cand.country)
                    except UniversityReadStopped as stopped:
                        budget_stopped = True
                        government_stopped = True
                        self._read_budget_unknown(cand, stopped, result)
''',1)
s=s.replace('''                    gov_cache[cand.country] = (
                        str(gr.claims[0].normalized_value) if gr.claims else "",
                        list(gr.claims),
                    )
                government_value, government_claims = gov_cache[cand.country]''','''                    if not government_stopped:
                        gov_cache[cand.country] = (
                            str(gr.claims[0].normalized_value) if gr.claims else "",
                            list(gr.claims),
                        )
                government_value, government_claims = gov_cache.get(cand.country, ("", []))''',1)
s=s.replace('''                self._persist_result(result, all_claims, conflicts)
                self.run.programs_verified''','''                if budget_stopped:
                    recorded = self._persist_read_partial_result(result, all_claims, conflicts)
                else:
                    self._persist_result(result, all_claims, conflicts)
                    recorded = len(all_claims)
                self.run.programs_verified''',1)
s=s.replace('''                self.run.claims_recorded += len(all_claims)
''','''                self.run.claims_recorded += recorded
''',1)
s=s.replace('''            scholarships, ar = await adapter.find(
                cand,
                prog,
                self.profile,
                allow_search=any(c.claim_type is ClaimType.PROGRAM_EXISTS for c in result.claims),
            )''','''            try:
                with self._university_read_scope(cand):
                    scholarships, ar = await adapter.find(
                        cand,
                        prog,
                        self.profile,
                        allow_search=any(c.claim_type is ClaimType.PROGRAM_EXISTS for c in result.claims),
                    )
            except UniversityReadStopped as stopped:
                self._read_budget_unknown(cand, stopped, result)
                self._update_result(row, result)
                st.items_done = i + 1
                continue''',1)
helper='''    def _lock_read_checkpoint_job(self) -> None:
        if not self.job_id or type(self.lease_token) is not int or self.lease_token <= 0:
            return  # Reads still fail closed in _change_read_budget; no fake fence.
        statement = select(Job.kind).where(
            Job.id == self.job_id,
            Job.run_id == self.run.id,
            Job.status == "running",
            Job.worker_id == self.worker_id,
            Job.attempts == self.lease_token,
        ).with_for_update(nowait=True)
        with self.session.no_autoflush:
            kind = self.session.execute(statement).scalar_one_or_none()
        if kind is None:
            self.session.rollback()
            raise LeaseLost("Read checkpoint no longer holds its job attempt.")
        self._read_job_kind = kind

    def _read_snapshot(self, *, lock: bool) -> dict:
        # Always acquire Job then Run, both NOWAIT: the existing cancel/recovery
        # writers can use the opposite order. Never wait across that lock pair.
        statement = select(ResearchRun.settings_snapshot).where(ResearchRun.id == self.run.id)
        try:
            if lock:
                self._lock_read_checkpoint_job()
                statement = statement.with_for_update(nowait=True)
            with self.session.no_autoflush:
                value = self.session.execute(statement).scalar_one()
        except OperationalError as error:
            self.session.rollback()
            if getattr(error.orig, "sqlstate", None) == "55P03":
                raise UniversityReadStopped("checkpoint_busy") from error
            raise
        if not isinstance(value, dict):
            raise UniversityReadStopped("invalid_snapshot")
        return deepcopy(value)

    @contextmanager
    def _university_read_scope(self, candidate: Candidate):
        if not self._read_guard_enabled:
            yield
            return
        self._check_cancelled()
        key = read_budget.university_key(candidate)
        token = read_budget.ACTIVE_UNIVERSITY.set(key)
        try:
            self._change_read_budget(key, reserve=False)
            yield
        finally:
            read_budget.ACTIVE_UNIVERSITY.reset(token)

    def _reserve_university_read(self) -> None:
        self._check_cancelled()
        key = read_budget.ACTIVE_UNIVERSITY.get()
        if key is None:
            raise UniversityReadStopped("missing_university_scope")
        self._change_read_budget(key, reserve=True)

    def _change_read_budget(self, key: str, *, reserve: bool) -> None:
        # No genuine fenced job means no admission. Canary/direct runner must
        # acquire a real worker protocol before an owner can enable this flag.
        if not self.job_id or type(self.lease_token) is not int or self.lease_token <= 0:
            raise UniversityReadStopped("unfenced_episode")
        durable = self._read_snapshot(lock=True)
        if self._read_job_kind != "research":
            raise UniversityReadStopped("unsupported_job_episode")
        if read_budget.LEDGER_KEY in durable:
            ledger = read_budget.validate_ledger(durable[read_budget.LEDGER_KEY])
        elif self._read_episode_fresh:
            ledger = read_budget.new_ledger()
        else:
            raise UniversityReadStopped("legacy_episode_untracked")
        episode_id = "decision:" + self.job_id
        episode = ledger["episodes"].get(episode_id)
        if episode is None:
            if not self._read_episode_fresh and self.lease_token != 1:
                raise UniversityReadStopped("missing_retry_episode")
            episode = {"read_counts": {}}
            ledger["episodes"][episode_id] = episode
        ledger["active_episode"] = episode_id
        count = episode["read_counts"].get(key, 0)
        if count >= read_budget.READ_LIMIT:
            # A refused get has no FetchResult/status/pages-failed. Do not
            # rewrite the counter or refund previously admitted invocations.
            self._save()
            raise UniversityReadStopped("read_cap")
        episode["read_counts"][key] = count + (1 if reserve else 0)
        replacement = read_budget.copy_snapshot_with_ledger(self.run.settings_snapshot or {}, durable)
        replacement[read_budget.LEDGER_KEY] = ledger
        self.run.settings_snapshot = replacement
        self._read_guard_writing = True
        try:
            self._save()  # heartbeat fence and counter commit BEFORE original get
        finally:
            self._read_guard_writing = False

    def _read_budget_unknown(self, candidate: Candidate, stopped: UniversityReadStopped, result=None) -> None:
        message = (
            f"Remaining research for {candidate.name} is unknown: "
            f"university read allowance refused ({stopped.reason})."
        )
        if message not in (self.run.unknowns or []):
            self.run.unknowns = [*(self.run.unknowns or []), message]
        if result is not None and not any(q.topic == "research read allowance" for q in result.unresolved):
            result.unresolved.append(UnresolvedQuestion(
                topic="research read allowance",
                question=f"Which remaining official facts can be established for {result.program}?",
                why_it_matters=message,
                university=candidate.name,
                program=result.program,
                blocking=False,
            ))

    def _persist_read_partial_result(self, result: ProgramResult, claims, conflicts) -> int:
        key = dedupe.program_key(result.university, result.program, result.degree, result.intake, result.country)
        existing = self.session.query(ProgramResultRow).filter(
            ProgramResultRow.run_id == self.run.id, ProgramResultRow.dedupe_key == key
        ).one_or_none()
        if existing is None:
            self._persist_result(result, claims, conflicts)
            return len(claims)
        # A incomplete reread must never replace previous established evidence.
        # Completed new outputs are durably retained for reconciliation in the
        # audit record, not silently mixed into the previous complete result.
        previous = ProgramResult.model_validate(existing.payload)
        for question in result.unresolved:
            if not any(q.model_dump() == question.model_dump() for q in previous.unresolved):
                previous.unresolved.append(question)
        self._update_result(existing, previous)
        if claims:
            self._audit("partial_read_evidence_retained", "result", existing.id,
                        claims=[c.model_dump(mode="json") for c in claims])
        return 0

'''
s=s.replace('    # --- stage 1: profile',helper+'    # --- stage 1: profile',1)
write('app/pipeline/runner.py',s)

s=originals['app/catalogue/discovery.py'].replace('import asyncio\n','import asyncio\nfrom contextlib import nullcontext\n',1)
s=s.replace('from app.config', 'from app.config') # keep imports intact; insert near existing app imports
needle='from app.adapters.base import Candidate\n'
assert needle in s
s=s.replace(needle,needle+'from app.pipeline.control import UniversityReadStopped\n',1)
s=s.replace('''                name=uni.name,
                country=uni.country,''','''                name=uni.name,
                catalogue_id=uni.id,
                country=uni.country,''',1)
s=s.replace('''                    candidate, trace = await asyncio.wait_for(
                        self._enrich(uni, profile, candidate, trace), timeout=300
                    )''','''                    with self.research_scope(candidate) if self.research_scope else nullcontext():
                        candidate, trace = await asyncio.wait_for(
                            self._enrich(uni, profile, candidate, trace), timeout=300
                        )''',1)
s=s.replace('''                except TimeoutError:
''','''                except UniversityReadStopped as stopped:
                    trace.search_limitations.append(
                        f"Remaining research remains unknown: university read allowance unavailable ({stopped.reason})."
                    )
                except TimeoutError:
''',1)
s=s.replace('''        enriched.discovery_source = f"local-catalogue:{uni.id}; {enriched.discovery_source}"
''','''        enriched.catalogue_id = uni.id
        enriched.discovery_source = f"local-catalogue:{uni.id}; {enriched.discovery_source}"
''',1)
write('app/catalogue/discovery.py',s)

s=originals['app/adapters/discovery/live_discovery.py']
s=s.replace('from __future__ import annotations\n','from __future__ import annotations\n\nfrom contextlib import AbstractContextManager, nullcontext\n',1)
needle='from app.adapters.base import Candidate'
# import statement includes CandidateProgram etc; independent control import can be placed before it.
s=s.replace(needle,'from app.pipeline.control import LeaseLost, RunCancelled, UniversityReadStopped\n'+needle,1)
s=s.replace('''        page_recorder: PageRecorder | None = None,
    ) -> None:
        self.fetcher''','''        page_recorder: PageRecorder | None = None,
        research_scope: Callable[[Candidate], AbstractContextManager] | None = None,
    ) -> None:
        self.research_scope = research_scope
        self.fetcher''',1)
s=s.replace('''        for entry in entries:
            candidate, trace = await self._discover_one(entry, profile)
            self.traces.append(trace)
            out.append(candidate)''','''        for entry in entries:
            seed = Candidate(name=entry["name"], country=entry["country"], city=entry.get("city", ""))
            try:
                with self.research_scope(seed) if self.research_scope else nullcontext():
                    candidate, trace = await self._discover_one(entry, profile)
            except UniversityReadStopped as stopped:
                candidate = seed
                trace = DiscoveryTrace(institution=seed.name, domain="")
                trace.search_limitations.append(
                    f"Remaining research remains unknown: university read allowance unavailable ({stopped.reason})."
                )
            self.traces.append(trace)
            out.append(candidate)''',1)
s=s.replace('''        except Exception as exc:  #''','''        except (UniversityReadStopped, RunCancelled, LeaseLost):
            raise
        except Exception as exc:  #''')
write('app/adapters/discovery/live_discovery.py',s)

s=originals['app/adapters/discovery/catalog_walker.py']
needle='from app.adapters.base import '
if needle in s:
    s=s.replace(needle,'from app.pipeline.control import LeaseLost, RunCancelled, UniversityReadStopped\n'+needle,1)
else:
    s=s.replace('from __future__ import annotations\n','from __future__ import annotations\n\nfrom app.pipeline.control import LeaseLost, RunCancelled, UniversityReadStopped\n',1)
s = re.sub(
    r"(?m)^([ \t]*)except Exception as exc:",
    lambda m: m.group(1)+"except (UniversityReadStopped, RunCancelled, LeaseLost):\n"+m.group(1)+"    raise\n"+m.group(1)+"except Exception as exc:",
    s,
)
write('app/adapters/discovery/catalog_walker.py',s)

patch=''
for path in SOURCES+['app/pipeline/control.py','app/pipeline/read_budget.py']:
    before=originals.get(path,'')
    after=(OUT/path).read_text()
    patch+=''.join(difflib.unified_diff(before.splitlines(keepends=True),after.splitlines(keepends=True),fromfile='a/backend/'+path if before else '/dev/null',tofile='b/backend/'+path))
(BASE/'readguard.patch').write_text(patch)
(BASE/'source-baseline.json').write_text(json.dumps({p:hashlib.sha256((REPO/p).read_bytes()).hexdigest() for p in SOURCES},indent=2)+'\n')
print('External source generation complete; never applied to repository.')
