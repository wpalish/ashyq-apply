# T37 A1 — QA verify-candidate report (ashyq-qa)

- ROLE_PHASE: ashyq-qa / VERIFY_CANDIDATE (campaign c3, task T37, finding S7, attempt A1)
- STATUS: VERIFIED_PASS
- CHECKED_SHA: 2e8e6f9f784d03960562ca25e9b6b6c85d05eca2 (branch `ai/c3/t37/verify`, tree clean before and after all runs)
- Worktree: /Users/wpalish/ashyq-worktrees/c3-t37-verify (independent verification worktree; venv as provisioned; no extra -q)

## SCOPE_CHECK

- `git rev-parse HEAD` = 2e8e6f9f784d03960562ca25e9b6b6c85d05eca2 == frozen candidate. `git status --porcelain` empty (re-checked after all gates).
- Ancestry verified with `git merge-base --is-ancestor`: edf546d → 25af8ff → 2e8e6f9. Parents: `git rev-parse 25af8ff^` = edf546de…, `git rev-parse HEAD^` = 25af8ff2….
- `git diff 25af8ff..HEAD --stat` = exactly `backend/app/pipeline/runner.py | 31 +++++…+, 1 file changed, 30 insertions(+), 1 deletion(-)`.
- `git diff 25af8ff..HEAD -- backend/tests/` = empty (0 lines) — QA RED tests byte-identical; nothing weakened or tuned.

## ANTI_WEAKENING_CHECK

Read the full diff; it contains exactly two hunks:

1. `_update_result` gate: `if extra_claims:` → `if extra_claims is not None:` (only changed existing line). New targeted deletes BEFORE `_store_claims`, matching the frozen contract:
   - `ClaimRow` where `result_id == row.id AND claim_type.in_(FUNDING_CLAIM_TYPES) AND status != ClaimStatus.SUPERSEDED.value`
   - `ConflictRow` where `result_id == row.id AND claim_type.in_(FUNDING_CLAIM_TYPES)` (no status filter — model verified: ConflictRow = run_id/result_id/claim_type/unresolved/payload, no status column, app/models/research.py:181-190)
   - both `synchronize_session=False`, same as `_replace_evidence`; trailing `if conflicts: self._store_conflicts(...)` untouched.
2. Module constant `FUNDING_CLAIM_TYPES: frozenset[ClaimType]` at runner.py:1335-1343 (directly after CORE_QUESTIONS), derived `frozenset(member for member in ClaimType if member.value.startswith("scholarship_"))`, comment documents the re-open contract rule (a future funding claim type WITHOUT the prefix does NOT auto-join; extending the delete scope is a new contract session).

Caller audit (grep: `_update_result` referenced only in runner.py; `extra_claims` nowhere else in app/):
- :813 `_stage_funding` — passes `extra_claims=claims`; empty list now honestly replaces previous funding evidence (intended per contract, mirrors reextract zero-page semantics). Sole behavioral change.
- :889, :961, :1038 — no extra_claims → None → gate False → zero behavior change (three None sites unchanged).
- :1072 `_persist_result` retry branch — preceded by `_replace_evidence(existing.id)` (:1071) which already deleted all non-SUPERSEDED ClaimRows and all ConflictRows, so the targeted deletes there are no-ops; `_store_claims(row, [])` is an empty loop. No caller passes `[]` expecting append. Developer's audit confirmed at source level.

Enum derivation verification (programmatic, venv): ClaimType has 51 members; 14 carry the `scholarship_` prefix (enums.py:119-132); `FUNDING_CLAIM_TYPES == {m for m in ClaimType if m.value.startswith('scholarship_')}` → True; size 14; symmetric difference empty. Family boundary exact: `WebScholarshipAdapter` (sole emitter feeding `_stage_funding`) emits exactly those 14 ClaimTypes — no non-scholarship funding type exists today to be missed.

Targeted-delete correctness: scoped by `result_id == row.id`; `result_id` is the ProgramResultRow PK (fresh `new_id()` per row, rows iterated via `_rows()` of this run only) — no cross-result or cross-run deletion possible. SUPERSEDED filter present in the ClaimRow delete; reextract/supersession paths untouched by the diff (T32 mechanics intact).

## GATES (real runs, cwd backend, venv ./.venv)

- a. `./.venv/bin/python -m pytest tests/test_pipeline.py` → `32 passed in 15.14s`, PYTEST_EXIT=0. RED→GREEN flip confirmed: baseline (QA report) `1 failed, 31 passed` → candidate `32 passed`. Targeted: `pytest tests/test_pipeline.py -k TestFundingReEntry -v` → `1 passed, 31 deselected in 1.41s`, EXIT=0 (all five assertion groups green, incl. verify-family guard, user_* preservation, SUPERSEDED survival).
- b. `./.venv/bin/python -m pytest tests/test_source_scan.py tests/test_freshness_regressions.py` → `47 passed, 1 warning in 11.51s`, PYTEST_EXIT=0 (T32 gate).
- c. `./.venv/bin/python -m pytest tests/test_api.py` → `66 passed, 1 warning in 33.91s`, PYTEST_EXIT=0 (TestRetry gate).
- d. `./.venv/bin/python -m pytest tests/test_worker.py` → `36 passed in 8.86s`, PYTEST_EXIT=0 (pgserver).
- e. `./.venv/bin/python -m mypy app tests` → `Success: no issues found in 164 source files`, MYPY_EXIT=0 (only pre-existing annotation-unchecked notes).
- f. `ruff check app tests` → `All checks passed!`, exit 0; `ruff format --check app tests` → `164 files already formatted`, exit 0.

## ADVERSARIAL_NOTES

- is-not-None gate: no other stage/adapter passes `extra_claims=[]` (or anything) — `_update_result` is private to runner.py with exactly five call sites; audit above. No hidden reliance on the old skip outside the intended funding site.
- ConflictRow re-store asymmetry (unchanged code): fresh conflicts re-store is gated on truthy `if conflicts:` AFTER the wholesale family delete — a re-entry pass with zero fresh conflicts drops old funding conflicts without replacement. Consistent with honest-replace semantics; noting it is intended.
- Coverage observation (report-only, did not fix): `pytest tests/test_pipeline.py --cov=app.pipeline.runner --cov-report=term` → `app/pipeline/runner.py 596 stmts, 98 miss, 84%`. term-missing in the changed region: all NEW lines (1117-1134: gate, both deletes, store) are EXECUTED. Missing nearby: :1136 `self._store_conflicts(row.id, conflicts)` (fresh funding-conflict re-store — corpus emits zero funding conflicts, unreached; this is the QA-flagged residual) and :1147-1151 `_replace_evidence` body (exercised by test_api TestRetry, not pipeline tests — pre-existing split). The ConflictRow delete executes but never matches a row in the corpus: the "delete actually removes a funding conflict" effect remains untested, mechanism argued by code-shape identity with the ClaimRow delete only. The 92 floor is the FULL-suite gate (`--cov=app --cov-fail-under=92`, integrator's) — module-level 84% here is not that metric; integrator must confirm the floor on the combined suite.

## BLOCKERS

None.

## NEXT_ACTION

Hand frozen candidate 2e8e6f9f784d03960562ca25e9b6b6c85d05eca2 to reviewer/security review and then the integrator (full `--cov=app --cov-fail-under=92` + frontend gates on the integration branch). QA does not grant merge approval. Residuals for the ledger: (1) funding-conflict delete is corpus-uncovered (guard-only); (2) pre-fix production duplicate rows are the owner's cleanup decision per contract non-goals.
