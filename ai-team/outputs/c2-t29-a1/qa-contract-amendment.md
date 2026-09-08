# T29 A1 — QA Contract Amendment Report (campaign c2, attempt A1, phase TEST_CONTRACT_AMENDMENT)

- ROLE_PHASE: ashyq-qa / TEST_CONTRACT_AMENDMENT
- STATUS: AMENDED
- DATE: 2026-09-07

## CHECKED_SHA

- START: 6ae2799b77a7a0fb6a863249d3a79bee013ef83b (branch ai/c2/t29/qa-a2, worktree
  /Users/wpalish/ashyq-worktrees/c2-t29-qa-a2, clean tree at start)
- Chain verified in worktree: 2ed4f51 (baseline) -> 7585b57 (QA RED) -> 6ae2799 (dev candidate)
- AMEND_COMMIT_SHA: ff6a90e3330c6040bfce02c63c6f8c163398d914 (parent 6ae2799, trailer `Agent: ashyq-qa`, no push)

## SCOPE COMPLIANCE

Only file touched: `backend/tests/test_live_discovery.py`. Working tree clean after commit
(`git status --short` empty). No production code, no assertions, no test bodies, no expected
values changed.

## DIFF_SUMMARY (exact)

```diff
--- a/backend/tests/test_live_discovery.py
+++ b/backend/tests/test_live_discovery.py
@@ -1260,7 +1260,7 @@ def _js_catalog_renderer(tmp_path, page: WalkerFakePage):
     return fetcher, renderer


-def _catalogue_html(*anchors: str) -> str:
+def _catalogue_html(*anchors: tuple[str, str]) -> str:
     items = "".join(f'<li><a href="{url}">{label}</a></li>' for url, label in anchors)
```

1 file changed, 1 insertion(+), 1 deletion(-). Type annotation only.

## Justification

- Reproduced on pristine candidate BEFORE edit: mypy reported exactly 3 errors, all at
  `backend/tests/test_live_discovery.py:1264` (the unpacking line inside the helper):
  - `Unpacking a string is disallowed [misc]`
  - `Cannot determine type of "url" [has-type]`
  - `Cannot determine type of "label" [has-type]`
- All 7 call sites verified to pass `(url, label)` string pairs:
  lines 1305, 1360, 1405, 1442, 1520, 1623 (explicit tuple literals) and line 1719
  (`_catalogue_html(*anchors)` where `anchors` is a list of `(url, label)` tuples built at
  lines ~1712-1721). The preferred signature `*anchors: tuple[str, str]` matches every call site.
- No OTHER mypy error existed in the file, so no additional annotation fixes were needed.

## COMMANDS AND EXIT CODES (all run from /Users/wpalish/ashyq-worktrees/c2-t29-qa-a2/backend)

| # | Command | Result | Exit |
|---|---------|--------|------|
| 1 | `./.venv/bin/python -m mypy app tests` (BEFORE edit) | `Found 3 errors in 1 file (checked 161 source files)` — all 3 at tests/test_live_discovery.py:1264 | 1 |
| 2 | `./.venv/bin/python -m pytest tests/test_live_discovery.py` (BEFORE edit) | `124 passed in 4.33s` | 0 |
| 3 | `./.venv/bin/python -m mypy app tests` (AFTER edit) | `Success: no issues found in 161 source files` | 0 |
| 4 | `./.venv/bin/python -m pytest tests/test_live_discovery.py` (AFTER edit) | `124 passed in 0.93s` | 0 |
| 5 | `./.venv/bin/python -m pytest tests/test_browser_network.py tests/test_ssrf.py tests/test_source_pages.py` | `106 passed in 7.12s` | 0 |
| 6 | `./.venv/bin/python -m ruff check tests/test_live_discovery.py` | `All checks passed!` | 0 |
| 7 | `./.venv/bin/python -m ruff format --check tests/test_live_discovery.py` | `1 file already formatted` | 0 |

No extra pytest flags were passed (no `-q`, no retries, no timeout changes).

## GATES

- mypy: FAIL (3 errors) -> PASS (0 errors)
- pytest tests/test_live_discovery.py: 124 passed BEFORE -> 124 passed AFTER (identical count, all green; no behavioral change)
- Slice (browser_network + ssrf + source_pages): 106 passed
- ruff check + format --check on amended file: clean

## ASSERTIONS

No assertion, expected-value, or test-logic change was made anywhere. The single edit is the
helper's parameter annotation. Test count and pass status unchanged before/after.

## ENVIRONMENT

- Worktree: /Users/wpalish/ashyq-worktrees/c2-t29-qa-a2 (branch ai/c2/t29/qa-a2)
- venv: backend/.venv (worktree-local), macOS darwin arm64
- No PostgreSQL/E2E runs, no network-dependent tests, no resource conflicts observed.

## REPRODUCED_BUGS

None in production code (this phase amends QA test infrastructure only). The 3 pre-existing
mypy errors in the QA-authored test file were reproduced on the pristine candidate before the edit.

## UNTESTED_RISKS

- Full pytest suite and frontend gates were NOT re-run here (out of this amendment's scope);
  the verification phase should run them on the amended candidate.
- ruff was run on the amended file only (per scope), not `app tests` wholesale; mypy covered
  `app tests` fully and is clean.
- The commit is local only; no push (per rules).

## BLOCKERS

None.

## NEXT_ACTION

Developer (or dispatcher) re-runs the mypy gate on candidate ff6a90e3330c6040bfce02c63c6f8c163398d914
(= 6ae2799 + this one-line amendment); a fresh VERIFY_CANDIDATE pass is required since the
candidate SHA changed after the previous review.
