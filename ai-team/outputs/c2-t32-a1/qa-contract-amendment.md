# T32 A1 — QA contract amendment report (campaign c2, attempt A2)

- ROLE_PHASE: QA / TEST_CONTRACT_AMENDMENT
- STATUS: AMENDED
- Worktree: /Users/wpalish/ashyq-worktrees/c2-t32-qa-a2 (branch ai/c2/t32/qa-a2)
- CHECKED_SHA (start): ade82fb1873c8b2de5ba7d9a69aaa6545a5b9697 (final dev candidate, tree clean)
- AMEND_COMMIT_SHA: 7bfa715a994e973a5a8216b1713324ee74cf1fe3 (parent ade82fb; trailer "Agent: ashyq-qa"; no push)

## SCOPE DISCREPANCY (disclosed, substance unchanged)

The task packet's scope item 1 said the R8 reflection-key fix is in
`backend/tests/test_source_scan.py`. In the actual tree the R8 assertions live in
`backend/tests/test_freshness_regressions.py` (`_assert_t32_columns`, ex-lines 633 and
643), exactly as developer.md BLOCKER-1 stated. The amendment was applied where the code
actually is; the substance is identical to the packet (2 assertion key accesses, asserted
facts ON DELETE SET NULL and recheck_generation default 0 unchanged, either reflection
representation accepted per dialect). Gate (a) could not reach 44/0 otherwise.

## PRE-AMENDMENT REPRODUCTION (real RED, at ade82fb)

`./.venv/bin/python -m pytest tests/test_freshness_regressions.py tests/test_source_scan.py --tb=line`
→ exit 1 (via pipe; summary line): **4 failed, 40 passed** — exactly the 4 approved
test-side defects:
- TestT32MigrationRoundTrip::test_upgrade_then_downgrade_on_sqlite (R8 FK ondelete / server_default reflection)
- TestT32MigrationRoundTrip::test_upgrade_then_downgrade_on_postgresql (same, PG)
- TestReextractSupersedesAndAppendsAtomically::test_a_fenced_or_crashed_attempt_writes_neither_side (_take_over backoff)
- TestSourceScanBootstrapRaces::test_a_lease_takeover_does_not_duplicate_reextract_enqueues (_take_over backoff)

Independent probe (throwaway, deleted): SQLite reflection of the migrated schema shows the
FK dict carries `options: {'ondelete': 'SET NULL'}` with NO top-level `ondelete` key, and
`recheck_generation` has NO `server_default` key while `default == "'0'"` — matching
developer.md BLOCKER-1 exactly.

## DIFF_SUMMARY (2 files, +92/−73; majority ruff rewrap)

backend/tests/test_freshness_regressions.py:
1. `_assert_t32_columns` FK assertion (ex-line 633): read
   `reflected_ondelete = fk.get("ondelete") or (fk.get("options") or {}).get("ondelete")`,
   assert `== "SET NULL"` with the SAME message. Fact unchanged.
2. `_assert_t32_columns` default assertion (ex-line 643): `default = gen.get("server_default")`;
   `if default is None: default = gen.get("default")`; the assertion line
   (`default is not None and "0" in str(getattr(default, "arg", default))`) and its message
   are byte-identical. Fact unchanged (default 0).
3. ruff I001 ×2 (module import block, `_run_research_to_decision` locals) + format rewraps (no logic).

backend/tests/test_source_scan.py:
4. `_take_over` (ex-line 383): after `assert JobStore(session).reap_expired() == [job_id]`
   and BEFORE worker-b's claim, added a direct UPDATE restoring the requeued row:
   `session.execute(sa.update(Job).where(Job.id == job_id).values(available_at=datetime.now(UTC)))`
   + `session.commit()`. Frozen T10/T28 store semantics (requeue at now+30s) untouched.
5. ruff I001 ×1 (`app.adapters.fetching` import order) + format rewraps (no logic).

No assertion semantics, expected values, tests, or production files changed.
`git diff 65e1522 ade82fb -- tests/` empty confirms tests/ were frozen since the QA RED
commit; all ruff findings pre-date this amendment and sit in these two QA files.

## GATES (real runs, backend/ cwd, venv ./.venv, no extra pytest args)

a. `./.venv/bin/python -m pytest tests/test_freshness_regressions.py tests/test_source_scan.py`
   → **44 passed, 0 failed**, EXIT=0 (frozen developer expectation met exactly)
b. `./.venv/bin/python -m pytest tests/test_worker.py tests/test_jobs.py`
   → **66 passed**, EXIT=0
c. `./.venv/bin/python -m mypy app tests`
   → Success: no issues found in 163 source files, EXIT=0
d. `./.venv/bin/python -m ruff check app tests` → All checks passed, EXIT=0;
   `./.venv/bin/python -m ruff format --check app tests` → 163 files already formatted, EXIT=0

## ARTIFACT_REFS

- qa-amend-gate-a-44.log (gate a full output)
- qa-amend-gate-b-66.log (gate b full output)
- qa-amend-gate-mypy.log (gate c full output)
- gate d output recorded in the invocation transcript (no separate file)

## BLOCKERS

None. All approved amendments applied within scope; every gate green.

## NEXT_ACTION

Dispatcher: freeze 7bfa715a994e973a5a8216b1713324ee74cf1fe3 as the amended QA test
contract; route the candidate (dev ade82fb + this QA amendment) to VERIFY/REVIEW on the
agreed affected suites. No push performed.
