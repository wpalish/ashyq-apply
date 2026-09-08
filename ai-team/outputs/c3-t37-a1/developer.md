# T37 A1 — Developer report (ashyq-developer)

- ROLE_PHASE: ashyq-developer / IMPLEMENTED (campaign c3, task T37, finding S7, attempt A1)
- STATUS: IMPLEMENTED
- CHECKED_SHA (start): 25af8ff2ac4e41a73d4eb493a29a14c11bf9b2a0 (QA RED commit; parent = baseline edf546de9f998c0909337d0abe6f8e1c9c4a0be5)
- CANDIDATE_SHA: 2e8e6f9f784d03960562ca25e9b6b6c85d05eca2 (branch ai/c3/t37/dev, tree clean, not pushed)
- Worktree: /Users/wpalish/ashyq-worktrees/c3-t37-dev (single writer; runner.py exclusively mine in c3)

## CHANGED_FILES

- backend/app/pipeline/runner.py — +30 / -1. Nothing else.

Diff contents (exactly the frozen contract scope):
1. Gate change in `_update_result`: `if extra_claims:` → `if extra_claims is not None:` (the only changed line of existing code).
2. Before the existing `self._store_claims(row.id, extra_claims)`: targeted delete of `ClaimRow` where `result_id == row.id AND claim_type.in_(FUNDING_CLAIM_TYPES) AND status != ClaimStatus.SUPERSEDED.value`, then targeted delete of `ConflictRow` where `result_id == row.id AND claim_type.in_(FUNDING_CLAIM_TYPES)` (ConflictRow has no status column — verified app/models/research.py:181-190). Both with `synchronize_session=False`, same as `_replace_evidence`. `if conflicts: self._store_conflicts(...)` untouched.
3. Module constant `FUNDING_CLAIM_TYPES: frozenset[ClaimType]` next to `CORE_QUESTIONS` (former :1306-1316 area, now :1335-1343), derived at import time: `frozenset(member for member in ClaimType if member.value.startswith("scholarship_"))` → all 14 SCHOLARSHIP_* members. Comment documents the derivation and the re-open rule: a future funding claim type WITHOUT the `scholarship_` prefix does NOT join the family automatically — extending the delete scope is a new contract session.
4. Rationale comment in the branch: funding re-entry owns the whole scholarship family; SUPERSEDED was/stale history preserved like `_replace_evidence`.

Untouched, verified: `_persist_result`, `_replace_evidence`, all other `_update_result` call sites (:889/:961/:1038 — no extra_claims, gate False, zero behavior change), stage order/reextract/freshness, schema, `run.claims_recorded += len(claims)` semantics, QA test file.

## GATES (real runs, cwd backend, venv /Users/wpalish/ashyq-worktrees/c3-t37-dev/backend/.venv)

- a. `./.venv/bin/python -m pytest tests/test_pipeline.py` → `32 passed in 20.45s` (TestFundingReEntry green; 31 pre-existing green)
- b. `./.venv/bin/python -m pytest tests/test_source_scan.py tests/test_freshness_regressions.py` → `47 passed, 1 warning in 11.51s`
- c. `./.venv/bin/python -m pytest tests/test_api.py` → `66 passed, 1 warning in 37.93s` (TestRetry :293-362 green)
- d. `./.venv/bin/python -m pytest tests/test_worker.py` → `36 passed in 9.80s`
- e. `./.venv/bin/python -m mypy app tests` → `Success: no issues found in 164 source files`
- f. `./.venv/bin/python -m ruff check app tests && ./.venv/bin/python -m ruff format --check app tests` → clean (`All checks passed!`, `164 files already formatted`)

## RED_TO_GREEN

Baseline (QA report): assertion (1) FAIL — `re-entering funding_discovery changed the stored claim totals; Groningen 40 -> 58`; (2)-(5) PASS. Post-fix, all five assertion groups PASS in the committed suite (gate a) and in a second fresh scenario run (probe copy: /Users/wpalish/ashyq-apply/ai-team/outputs/c3-t37-a1/dev_probe_postfix.py, exit 0, stage_state log confirms program_verification stayed done — stage-retry path, not recheck):

Per-result counts after fix (before → after re-entry): every row identical.

| result | total | sch | verify | conflicts |
|---|---|---|---|---|
| University of Groningen | 40 → 40 | 18 → 18 | 22 → 22 | 0 → 0 |
| Delft University of Technology | 30 → 30 | 11 → 11 | 19 → 19 | 1 → 1 |
| National University of Singapore | 33 → 33 | 14 → 14 | 19 → 19 | 0 → 0 |
| KU Leuven | 32 → 32 | 16 → 16 | 16 → 16 | 0 → 0 |
| all other 16 rows | unchanged | unchanged | unchanged | unchanged |

`results with doubled scholarship claims: 0; results with doubled conflicts: 0` (was: 14 of 20 results doubled SCHOLARSHIP_* on baseline).

## DESIGN_NOTES

- Constant derivation: enum-comprehension over `ClaimType` by value prefix `scholarship_` (exactly the 14 members at enums.py:119-132; no other member carries the prefix). Frozen contract allows explicit list or enum-derived frozenset ("эквивалентны"); the derivation guarantees a future `SCHOLARSHIP_*` member cannot be forgotten in the delete filter, while the documented re-open rule blocks silent expansion for non-prefixed funding types.
- `is not None` gate consequences: callers passing `extra_claims=None` (:889, :961, :1038) skip the branch entirely as before. The two list-passing callers: :813 (funding) now honestly replaces even when `claims == []` (adapter found nothing → previous pass's funding evidence is dropped, mirroring reextract zero-page semantics — intended per contract). :1072 (`_persist_result` retry path) is preceded by `_replace_evidence` (:1071) which already deleted all non-SUPERSEDED ClaimRows, so the targeted delete there is a no-op; empty-list behavior unchanged. No caller passes an empty list expecting append.
- `run.claims_recorded` (:814) untouched; counts new claims per pass as before.

## RESIDUALS

- QA-flagged (qa-test-author.md): the conflict-delete branch is not corpus-covered — assertion (5) is a guard, not RED; the bundled corpus emits zero funding-family ConflictRows (only conflict is Delft's verify-stage `ielts_min_overall`, untouched 1→1). Coverage impact: the `ConflictRow.claim_type.in_(FUNDING_CLAIM_TYPES)` delete executes but has no rows to act on in any test. The mechanism is identical to the ClaimRow delete (same query shape, verified by code flow); a corpus funding conflict would need a contract extension to pin.
- Existing production duplicate rows (from pre-fix runs) are not cleaned up — owner's call per contract non-goals.
- Candidate not pushed; no independent QA/review has run on it yet.

## BLOCKERS

None.

## NEXT_ACTION

VERIFY_CANDIDATE on frozen SHA 2e8e6f9f784d03960562ca25e9b6b6c85d05eca2 in a separate verification worktree: TestFundingReEntry green, gates b-f green, diff scope re-checked.
