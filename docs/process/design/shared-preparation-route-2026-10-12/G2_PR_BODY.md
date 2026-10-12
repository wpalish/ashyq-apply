## Task
Owner engineering brief 2026-10-12, stage G2 (shared preparation route). Worked on by `gpt-6-astra`; root is the only application/Git writer. This Draft depends on #86 (`task/multi-programme-evidence`); predecessor main merge is not implied.

## What changed
- Explicit owned programmes produce a personal IELTS/SAT route with one shared capacity and exact versioned lessons/own reviews. Source alternatives, missing facts, scope and locked status remain conservative; the route gives no admission verdict.
- Save uses client UUID, expected revision, a fresh owned write fence, immutable reference-only receipt/history and an additive migration. Export/erase include the new owned records.
- Per-owner/per-case tab recovery preserves inputs and the original uncertain command across navigation/reload. A lost response is reconciled through current/exact revision reads; there is no automatic second write or preview. Meaningful new inputs remain a separate dirty draft.
- Private navigation and acknowledged logout are guarded. Another clean signed-in browser sees saved server state without receiving the first browser's private draft.

## Acceptance criteria
- [x] One accepted workload across explicit 2–20 own programmes, ordered exact lesson/review references and explicit personal deadlines.
- [x] Owned UUID replay/CAS/rollback/concurrency; source status does not rewrite accepted history or become an official score/eligibility claim.
- [x] Native actual API desktop/mobile save, lost-ACK recovery, reload/current/history/export, newer draft retained; original controls remain.
- [x] Authenticated clean-browser persistence, private Legal navigation/cancel, dismissed logout and actual acknowledged logout; exact journal isolation/cleanup.
- [x] SQLite/private PostgreSQL/local frontend/native gates qualified on exact source; all old test IDs retained, original failures retained.
- [ ] Owner/relay review and dependent chain integration on main.
- [ ] Published logged-in path, legal/operator/subscription facts, measured fresh search quality and full curriculum acceptance (outside G2).

## Contract changes
HANDOFF §8 records additive shared route schema/domain/API/model/migration, personal inputs and exact LearningTaskRef reuse, case-owned current/history, browser recovery and navigation boundaries. Migration `c3e71d902023` descends from `b5c81d9e2022`; one head. Existing learning versions/UUID bodies/default plans/quota/Fetcher/STOPs remain.

## Verification — completed local output
```text
ruff check app tests evaluation: All checks passed!
ruff format --check app tests evaluation: 430 files already formatted
mypy app tests: Success: no issues found in 398 source files
frontend typecheck/lint/unit/build: all exit 0 (static-persistence13)
frontend: 596 passed, 0 failure/error/skip; all old546 IDs +50
full SQLite: 5417 passed, 0 failure/error/skip; 95.168351% coverage
full private PostgreSQL: 5417 passed, 0 failure/error/skip; 95.162947% coverage
focused G2: 289 passed (142 allocator,98 API,49 concurrency)
native Demo: 105 passed,1 historical skip,0 failures/errors; old102 IDs +4
native Auth4: 12 passed,0 failures/errors/skips; old10 IDs +2
seed: Groningen #1, UBC OUT_OF_BUDGET
alembic heads: c3e71d902023 (head)
```
Coverage floor92 and native timeout120s/zero retries/serial execution unchanged. Backend full result is carried only because all624 consumed files (four before/after maps/current) remain exact. Demo is carried across only the later `auth-journey.spec.ts` test-only delta explicitly excluded by its config. Static13 and Auth4 are fresh on current tested frontend/native HEAD `9f1819e4b3db84bf53579cad89e1aa7db15c0cb8`; final proof commit `0d4729034301cb1322377750834fc8d60ee8854a` changes metadata/evidence only. App delta33 paths pinned in G2_FINAL_APP_SOURCE_PINS.json.

Nine lint warnings and bundle657.06kB (gzip185.09kB) retained. Docker/hosted CI/production/live search NOT_RUN. CI quota is not consumed by these `[skip ci]` pushes.

Full report: `docs/process/design/shared-preparation-route-2026-10-12/G2_SHARED_ROUTE_LOCAL_RELEASE_REPORT.md`. Exact source/carry/cleanup/independent reviews, complete raw/JUnit and bounded screenshots at320/768/1024/1440, actual forwarded native ACK attachments and immutable earlier failure traces are in the indexed archive. All908 entries are tracked and SHA/size verified, including20 formerly ignored synthetic proof originals added by exact path. A prior review's stage/archive path confusion is explicitly corrected; original report retained.

## Invariants and guarding controls
- Ownership/private context: foreign cases/reviews, org/case epochs, exact owner journal, clean-browser Auth controls.
- No provider/quota/scoring mutation: native providers-none, OS egress guards, semantic unchanged academic/practice/research assertions.
- Immutable command/history: physical SQLite/PG contention, same/different UUID/CAS, atomic rollback and exact original receipt controls.
- Unknown remains unknown: source/locked/alternatives/edition checks and reference-only projections.
- Exact content/legacy compatibility: old5128 backend/546frontend/102Demo/10Auth IDs retained; no removed legacy assertions.

## Reviewer checklist
- [ ] Review exact source/carry and complete immutable raw evidence; independently rerun only changed consumed bytes when required.
- [ ] No D1–D12/formula change, domain adapters or direct crawler/LLM call.
- [ ] No probability/chance/% near ranking; practice is not official readiness.
- [ ] v1/default scoring and tests,92% floor and privacy/STOP guards retained.
- [ ] One Alembic head; migration/cascade/export and physical concurrency controls.
- [ ] HANDOFF current status/head/Draft and next-stage boundary agree.

## Limits
Local G2 delivery only. Nine practice lessons are not full IELTS/SAT courses. Browser journal is per tab and does not promise cross-device/closed-tab draft transfer or atomic cross-tab storage CAS. G3 documents/applications/Today, G4 syllabus/diagnostics and G5 private portfolio are separately frozen designs. No main merge, deploy, published journey or live quality acceptance is claimed.
