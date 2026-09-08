# T32 A1 — QA contract amendment (second amendment, attempt A3)

- ROLE_PHASE: ashyq-qa / TEST_CONTRACT_AMENDMENT (campaign c2, T32, attempt A1)
- DATE (UTC): 2026-09-08
- WORKTREE: /Users/wpalish/ashyq-worktrees/c2-t32-qa-a3 (branch ai/c2/t32/qa-a3)
- CHECKED_SHA (start): 7bfa715a994e973a5a8216b1713324ee74cf1fe3 (clean tree, verified)
- AMEND_COMMIT_SHA: 51a52c4b39381f873bdfabac8c3aaff2fbc02de3
- STATUS: AMENDED

## Defect (carried from QA verify, re-proven here)

`TestDemoRunIsByteIdentical::test_the_demo_pipeline_payload_is_byte_identical_to_baseline`
in backend/tests/test_freshness_regressions.py is date-bound: the baseline golden
payload contains unmasked date-only strings (written by pre-campaign runner code,
commit 9cfb20b, untouched by T32), so the byte-identity assertion fails at every
UTC date rollover from the golden capture date (2026-09-07). Re-proven in this
session under the real clock (UTC 2026-09-08): real assertion failure on the sha256
comparison (f738705e... vs aae8c595...), not an import/environment error.

## Mechanism choice (ONE, documented in-file)

CHOSEN: clock freeze to the golden capture date. `frozen_clock` fixture pins
`GOLDEN_CAPTURE_UTC = 2026-09-07T12:00:00Z` via frozen subclasses of
`datetime`/`date`, monkeypatched onto the six app.pipeline/app.domain modules that
read the wall clock (runner, state, eligibility, freshness → `datetime`;
claim_verifier, currency → `date`). All `datetime.now`/`date.today` call sites in
app/pipeline + app/domain were inventoried first (16 sites).

REJECTED: masking date-only strings in `_mask_volatile`. Diagnostic
(diag_date_keys_a3.py, exit 0) found 112 date-only strings in a demo dump; only 16
(`applicant_value` = today) are clock-dependent; the other 96 are semantic corpus
values (admission_deadline, scholarships[*].deadline, normalized_value,
published_value) that byte-identity must keep guarding. Blanket masking would have
WEAKENED the golden — not "equally strong".

The asserted FACT is unchanged: same golden hash, same `_canonical_demo_dump`
machinery, same mask. The hash was NOT re-captured.

## Negative control (freeze is load-bearing)

Backup copy → sed-detach `frozen_clock` from `demo_session` → golden test FAILS
under real clock → byte-identical restore from backup → PASS. Proves the green
comes from the freeze, not from a weakened assertion. Post-restore file is
byte-identical to what ruff/mypy validated.

## Gates (all commands run from backend/ with ./.venv/bin/python, no extra -q)

| Gate | Command | Result |
|---|---|---|
| A (pre-amendment repro) | pytest tests/test_freshness_regressions.py::TestDemoRunIsByteIdentical::test_the_demo_pipeline_payload_is_byte_identical_to_baseline -x | 1 failed (real RED) |
| A (post-amendment) | pytest tests/test_freshness_regressions.py::TestDemoRunIsByteIdentical | 2 passed |
| B | pytest tests/test_freshness_regressions.py tests/test_source_scan.py | 44 passed |
| C (regression slice) | pytest tests/test_worker.py tests/test_pipeline.py | 64 passed |
| D | mypy app tests | Success: no issues found in 163 source files, exit 0 |
| E | ruff check tests/test_freshness_regressions.py | All checks passed, exit 0 |
| E | ruff format --check tests/test_freshness_regressions.py | 1 file already formatted, exit 0 |
| F (negative control) | fixture detached → pytest R6 golden | 1 failed (expected), file restored |

Logs: qa-a3-gate-a-r6.log, qa-a3-gate-b-44.log, qa-a3-gate-c-worker-pipeline.log,
qa-a3-gate-d-mypy.log (all in this directory).

## Commit

51a52c4b39381f873bdfabac8c3aaff2fbc02de3 on ai/c2/t32/qa-a3 — ONLY
backend/tests/test_freshness_regressions.py (81 insertions, 3 deletions), trailer
`Agent: ashyq-qa`. No push. Working tree clean after commit.

## Artifacts (this directory)

- diag_date_keys_a3.py + diag_date_keys_a3.out — date-key diagnostic (exit 0)
- qa-a3-gate-*.log — gate logs listed above

## Notes / residual

- The module docstring and R6 comment now document the amendment and the
  never-re-capture-against-real-clock rule.
- Residual blind spot (unchanged from original design, slightly widened scope
  documented): timestamps remain masked as before; the freeze fixes the date-only
  leak without touching mask coverage of statuses/values/conflicts/ranking/counts.
- QA cannot declare final merge approval.
