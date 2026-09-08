# qa-verify-candidate-a2.md — T27 A2 (repair cycle c2), ashyq-qa, VERIFY_CANDIDATE

## STATUS

VERIFIED_PASS — frozen candidate `da836a20167a0186e8681e58a3ec29356bfc040b` independently re-verified in a fresh verification worktree. Reviewer blocking F1 is fixed by the minimal, table-only change; all gates green; scope clean; adversarial checks found no new issue.

## CHECKED_SHA

- Worktree `/Users/wpalish/ashyq-worktrees/c2-t27-verify-a2`, branch `ai/c2/t27/verify-a2`.
- `git rev-parse HEAD` → `da836a20167a0186e8681e58a3ec29356bfc040b` (== frozen CANDIDATE_SHA).
- `git status --porcelain` → empty before and after all runs (re-checked at the end).
- Ancestry verified with `git merge-base --is-ancestor`: `51f211d` (A1 candidate) → `c823d72` (QA A2 RED) → `da836a2` (candidate). Linear chain, one dev commit on top of the QA RED commit: `git log` shows `da836a2 (parent c823d72) "fix: T27 A2 widen multi-part public suffix table..."` ← `c823d72 (parent 51f211d) "test: T27 A2 RED — ..."` ← `51f211d (parent d8553e1)`.
- No modifications made by QA in this worktree (read-only except pytest caches; none tracked).

## SCOPE_CHECK

- `git diff c823d72..HEAD --stat` → **only** `backend/app/domain/claim_verifier.py | 70 +++++...+++ | 62 insertions(+), 8 deletions(-)`. No other production file.
- `git diff c823d72..HEAD -- backend/tests/` → empty (0 lines): QA test file byte-identical to the QA A2 commit. Independently confirmed by `diff` against the QA worktree file and SHA-256: `5989edc91ec7...` for both `/Users/wpalish/ashyq-worktrees/c2-t27-verify-a2/backend/tests/test_claim_verifier.py` and `/Users/wpalish/ashyq-worktrees/c2-t27-qa-a2/backend/tests/test_claim_verifier.py`.
- `git diff 51f211d..HEAD --stat` → exactly 2 files: `backend/app/domain/claim_verifier.py` (+70/−8 across 1 hunk) and `backend/tests/test_claim_verifier.py` (+117, the QA A2 test additions). No fixture, no extraction.py, no web_requirements.py, no OFFICIAL_PUBLIC_TLDS changes vs A1.

## DIFF_REVIEW — table-only confirmation

- The entire production delta vs A1 is **one hunk** (`git diff 51f211d..HEAD -- backend/app/domain/claim_verifier.py | grep -c '^@@'` → 1): `_MULTIPART_PUBLIC_SUFFIXES` 13 → 59 entries plus an 8-line comment above the table. Verified mechanically: every changed `+/-` line outside the table is one of the 8 comment lines; zero non-comment, non-table lines changed.
- Table properties (checked programmatically by parsing the source and importing the module): 59 entries; all-lowercase; source order == `sorted()` (alphabetical); no duplicate entries; runtime type is `frozenset`; declared `Final[frozenset[str]]` (same DATA form as before).
- Merge correctness: `old_verifier(13) ∪ live_discovery.MULTIPART_SUFFIXES(57) == new_table(59)` → `True`; `old − new` = empty (no old entry dropped); `discovery − verifier` = **empty** (subset holds — reviewer F1 direction closed); `verifier − discovery` = exactly `{gov.au, govt.nz}` (reverse divergence kept and now documented in the code comment, as ruled).
- No logic changes: `registrable_domain` (keep = 3 if last two labels in table else 2), `url_matches_domains`, negation, value-range and excerpt logic are byte-unchanged vs A1.
- `domain/` still imports nothing from `app.adapters.*` (duplication documented in-comment; the subset test is the divergence guard).

## GATES (all run in `/Users/wpalish/ashyq-worktrees/c2-t27-verify-a2/backend`, venv `./.venv`)

| Gate | Command | Real output | Exit |
|---|---|---|---|
| a | `./.venv/bin/python -m pytest tests/test_claim_verifier.py` | `93 passed in 1.77s` | 0 |
| a′ | `./.venv/bin/python -m pytest tests/test_claim_verifier.py::TestMultiPartPublicSuffixAgreement -v` | `7 passed in 0.48s` (all 6 former REDs + positive pin) | 0 |
| b | `./.venv/bin/python -m pytest tests/test_claim_verifier.py --cov=app.domain.claim_verifier --cov-fail-under=100` | `app/domain/claim_verifier.py 93 stmts 0 miss 100%` … `Required test coverage of 100% reached. Total coverage: 100.00%`, `93 passed in 1.18s` | 0 |
| c | `./.venv/bin/python -m pytest tests/test_live_regressions.py tests/test_adapters.py tests/test_live_extraction.py tests/test_security.py` | `180 passed, 1 warning in 10.55s` (warning is a pre-existing starlette TestClient import deprecation note) | 0 |
| d | `./.venv/bin/python -m mypy app tests` | `Success: no issues found in 157 source files` (pre-existing `annotation-unchecked` notes only) | 0 |
| e | `./.venv/bin/python -m ruff check app tests` then `./.venv/bin/python -m ruff format --check app tests` | `All checks passed!` / `157 files already formatted` | 0 / 0 |

No retries, no timeout increases, no `-q` or other extra flags beyond the packet-specified coverage gate.

## SEMANTIC_SPOT_CHECKS (executed directly against the candidate module)

- `registrable_domain("uw.edu.pl") == "uw.edu.pl"` → True
- `registrable_domain("iab.edu.kz") == "iab.edu.kz"` → True
- `registrable_domain("www.ox.ac.uk") == "ox.ac.uk"` and endswith `ac.uk` → True (positive pin intact)
- `url_matches_domains("https://pw.edu.pl/", ["uw.edu.pl"])` → **False** (sibling spoof closed)
- `url_matches_domains("https://www.narxoz.kz/", ["narxoz.kz"])` → **True** (legitimate subdomain still matches)
- Extra: `url_matches_domains("https://iab.edu.kz/", ["kbtu.edu.kz"])` → False; `registrable_domain("narxoz.kz.attacker.example")` → `attacker.example`; `url_matches_domains("https://evil.example/?u=narxoz.kz", ["narxoz.kz"])` → False (audit regression intact).
- E2E sibling scenario is covered by `test_a_sibling_university_page_is_never_verified_current` (pw.edu.pl page, candidate uw.edu.pl → no VERIFIED_CURRENT) — passing inside gate a/a′.

## ADVERSARIAL_NOTES

1. No entry that would break a legitimate single-institution domain: all 59 entries are genuine 2-label compound suffixes (no bare ccTLDs). A table entry can only make matching stricter (host must reach 3 labels), never spoofable; the spoofable direction (missing entry) is closed by the subset guard test.
2. Duplicates/conflicts: none (source has 59 unique strings; casefold check clean; both tables all-lowercase).
3. Old-vs-new outcome diff over every domain-like string in `app/corpus/data.py` (16 swept): exactly 3 outcomes changed — `u-tokyo.ac.jp: ac.jp → u-tokyo.ac.jp`, `univie.ac.at: ac.at → univie.ac.at`, `uw.edu.pl: edu.pl → uw.edu.pl`. All three are the fix direction (public suffix returned before, real registrable domain now); zero corpus outcomes degraded. Independent corroboration of regression slice c: `test_live_regressions.py` green inside gate c.
4. Brute force over all 46 newly added suffixes × 8 synthetic institution labels × 2 host depths (736 outcome flips): in every flip the new answer is the 3-label registrable domain; zero flips still collapse to the 2-label suffix.
5. Reverse divergence `{gov.au, govt.nz}` remains unguarded by tests (subset test only guards discovery ⊆ verifier). Documented by dev; acceptable per packet scope, but it is a standing asymmetry — flagged for planner if a shared source or superset guard is ever chosen.
6. Reviewer non-blocking F2–F7 and security F1 (redirect provenance / final_url), fee-window class, clause-scoped negation remain open and untouched — correctly out of A2 scope.

## BLOCKERS

None.

## NEXT_ACTION

Candidate `da836a2` is accepted by QA verification. Hand to reviewer for the re-review of the frozen SHA (per repair flow; QA verdict alone is not merge approval), then integration gate. No push performed (user gate).

## ENVIRONMENT

- macOS darwin 25.6.0 arm64; Python 3.12.13 in `/Users/wpalish/ashyq-worktrees/c2-t27-verify-a2/backend/.venv` (pytest-9.1.1, cov-6.0.0, mypy, ruff as provisioned).
- Offline; no network calls, no PostgreSQL/E2E, no conflicting resource slots used. pytest.ini `addopts -q --strict-markers` respected (no extra flags passed).
- Artifacts: extraction of A1 module and QA test for comparison at `/tmp/t27a2_old_verifier.py`, `/tmp/t27a2_qa_test.py` (untracked, outside repo).

## UNTESTED_RISKS

- Full-suite coverage gate (`--cov=app --cov-fail-under=92`) and frontend gates intentionally not run here (packet: do NOT run full --cov); QA gate coverage limited to the agreed affected suites.
- govt.nz/gov.au superset asymmetry (see ADVERSARIAL_NOTES 5).
- Security-review REQUIRED_EXTRA_TESTS (redirect→attacker-host, Unicode verbatim table, negation 8-sentence table, IDN/IPv6 table, $150-window probes) belong to separate tickets (T28/T29/T31 scoping), not to this A2 delta.
