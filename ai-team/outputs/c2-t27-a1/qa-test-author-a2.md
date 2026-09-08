# qa-test-author-a2.md — T27 A2 (repair cycle c2), ashyq-qa, TEST_AUTHOR

## STATUS

TESTS_READY — 6 new RED regression tests pin reviewer blocking F1 on frozen candidate 51f211d; all existing tests and test_live_regressions.py stay green.

## CHECKED_SHA

- Baseline verified before any write: `51f211d9d1159f0e255f307dc707872ddd3a1f30`, branch `ai/c2/t27/qa-a2`, tree clean (`git status --porcelain` empty).
- QA commit produced: `c823d728179c59d5c1dbb235db517c181b8a6b8f` (HEAD of ai/c2/t27/qa-a2, parent 51f211d). No push.

## FILES_MODIFIED

- `/Users/wpalish/ashyq-worktrees/c2-t27-qa-a2/backend/tests/test_claim_verifier.py` — ONLY file in the commit; append-only (117 insertions, single hunk `@@ -453,3 +453,120 @@`), zero changes to existing tests. New class `TestMultiPartPublicSuffixAgreement` (7 tests).
- No production code touched. No fixture files, conftest, test_live_discovery.py or test_live_regressions.py touched.

## DEFECT REPRODUCED (reviewer blocking F1 confirmed by direct execution and by RED)

- `registrable_domain("uw.edu.pl")` → `"edu.pl"` and `registrable_domain("pw.edu.pl")` → `"edu.pl"` (public suffix returned instead of registrable domain; `_MULTIPART_PUBLIC_SUFFIXES` keep=2 fallback).
- `url_matches_domains("https://pw.edu.pl/admissions", ["uw.edu.pl"])` → **True** (sibling-institution spoof).
- `url_matches_domains("https://iab.edu.kz/", ["kbtu.edu.kz"])` → **True** (*.edu.kz home market vacuous).
- Structural: 46 of the 57 entries of `live_discovery.MULTIPART_SUFFIXES` are missing from `claim_verifier._MULTIPART_PUBLIC_SUFFIXES` (13), incl. edu.kz, edu.pl, edu.cn, edu.tr, ac.kr, ac.jp, ac.il, com.br.
- End-to-end via `WebRequirementsAdapter` (offline Fetcher harness, candidate.domain="uw.edu.pl", page served from `https://pw.edu.pl/admissions/requirements`): publishes `VERIFIED_CURRENT` `IELTS_MIN_OVERALL=6.5` and `IELTS_ACCEPTED_TYPES=['academic']` — exactly the reviewer's cross-institution scenario. Corpus anchor confirmed: `app/corpus/data.py:833` ships `"domain": "uw.edu.pl"`.

## RED_RESULTS (6 new tests, pytest exit 1)

Run: `cd backend && ./.venv/bin/python -m pytest tests/test_claim_verifier.py` → `6 failed, 87 passed in 0.64s`, exit code **1**.

| Test | Real failure snippet |
|---|---|
| test_a_sibling_university_under_edu_pl_is_not_the_allowed_domain | `E assert True is False` / `where True = url_matches_domains('https://pw.edu.pl/admissions', ['uw.edu.pl'])` |
| test_a_sibling_university_under_edu_kz_is_not_the_allowed_domain | `E assert True is False` / `where True = url_matches_domains('https://iab.edu.kz/', ['kbtu.edu.kz'])` |
| test_the_registrable_domain_of_an_edu_pl_host_is_not_the_public_suffix | `E AssertionError: assert 'edu.pl' == 'uw.edu.pl'` |
| test_the_registrable_domain_of_an_edu_kz_host_is_not_the_public_suffix | `E AssertionError: assert 'edu.kz' == 'iab.edu.kz'` |
| test_the_verifier_suffix_table_covers_the_discovery_table | `E assert not ['ac.at', 'ac.be', 'ac.cy', ... ]` — 46 missing suffixes listed, incl. `edu.kz`, `edu.pl`, `edu.cn`, `edu.tr`, `ac.kr`, `ac.jp`, `ac.il`, `com.br` |
| test_a_sibling_university_page_is_never_verified_current | `E AssertionError: a page served from pw.edu.pl must not publish VERIFIED_CURRENT claims for candidate uw.edu.pl: [(<ClaimType.IELTS_MIN_OVERALL: 'ielts_min_overall'>, 6.5), (<ClaimType.IELTS_ACCEPTED_TYPES: 'ielts_accepted_types'>, ['academic'])]` |

Not import/environment errors: every failure is a real assertion on the defect. RED is genuine, not engineered by weakening anything.

## GREEN_RESULTS (existing behavior intact)

- `tests/test_claim_verifier.py`: **87 passed** includes all pre-existing tests (unchanged, byte-identical per diff) + 1 new positive pin `test_a_listed_suffix_still_resolves_to_the_registrable_domain` (ox.ac.uk → `ox.ac.uk`; `url_matches_domains("https://www.ox.ac.uk/x", ["ox.ac.uk"]) is True`) — GREEN on the candidate, must stay green after the fix.
- `tests/test_live_regressions.py`: `71 passed in 1.33s`, exit code **0** (untouched file).
- narxoz.kz pins (TestUrlMatchesDomains/TestRegistrableDomain) green within the 87.

## COMMANDS

```
cd /Users/wpalish/ashyq-worktrees/c2-t27-qa-a2 && git rev-parse HEAD && git status --porcelain
./.venv/bin/python -m pytest tests/test_claim_verifier.py tests/test_live_regressions.py   # baseline pre-edit: 157 passed
./.venv/bin/python -m pytest tests/test_claim_verifier.py    # after edit: 6 failed, 87 passed, exit 1
./.venv/bin/python -m pytest tests/test_live_regressions.py  # 71 passed, exit 0
./.venv/bin/python -m ruff check tests/test_claim_verifier.py          # All checks passed (after local-import sort fix in NEW code only)
./.venv/bin/python -m ruff format --check tests/test_claim_verifier.py # 1 file already formatted
git add backend/tests/test_claim_verifier.py && git commit -m "test: T27 A2 RED — ..."   # → c823d72
```

## ASSERTIONS (test contract for the dev fix)

1. `url_matches_domains("https://pw.edu.pl/admissions", ["uw.edu.pl"]) is False`
2. `url_matches_domains("https://iab.edu.kz/", ["kbtu.edu.kz"]) is False`
3. `registrable_domain("uw.edu.pl") == "uw.edu.pl"`
4. `registrable_domain("iab.edu.kz") == "iab.edu.kz"`
5. Positive pin: `registrable_domain("www.ox.ac.uk") == "ox.ac.uk"` AND `url_matches_domains("https://www.ox.ac.uk/x", ["ox.ac.uk"]) is True`
6. Structural subset guard: `set(live_discovery.MULTIPART_SUFFIXES) - set(claim_verifier._MULTIPART_PUBLIC_SUFFIXES) == empty` (both sides imported in the test; domain/ itself stays adapter-free)
7. E2E: `WebRequirementsAdapter.verify` with candidate.domain="uw.edu.pl" against a page at `https://pw.edu.pl/admissions/requirements` → claims may exist but none with `status is VERIFIED_CURRENT` (post-fix expectation: `official_domain` False → UNVERIFIED; also fails the `OFFICIAL_PUBLIC_TLDS` branch, so fail-closed)
8. Existing narxoz.kz pins and all pre-existing tests unchanged and green.

## ENVIRONMENT

- macOS darwin 25.6.0 arm64; venv `/Users/wpalish/ashyq-worktrees/c2-t27-qa-a2/backend/.venv`; offline (no network; adapter test uses in-memory FetchResult via monkeypatched `fetcher.get`, offline Fetcher).
- pytest.ini: asyncio_mode=auto; addopts `-q --strict-markers` (no extra flags passed). ruff line-length 100.
- Note: dev fix must widen `_MULTIPART_PUBLIC_SUFFIXES` to cover all 46 missing suffixes (or share one domain-level source); the subset guard will then also force future discovery-table growth to propagate.

## ARTIFACT_REFS

- QA branch/commit: `ai/c2/t27/qa-a2` @ `c823d728179c59d5c1dbb235db517c181b8a6b8f` (not pushed — user gate).
- Test file: `/Users/wpalish/ashyq-worktrees/c2-t27-qa-a2/backend/tests/test_claim_verifier.py` (lines 456-572).
- Reviewer report read: `/Users/wpalish/ashyq-apply/ai-team/outputs/c2-t27-a1/reviews.md`.
- Run logs (untracked, outside repo): `/tmp/t27a2_verifier_final.txt` (RED run), `/tmp/t27a2_live_final.txt` (green run).

## REPRODUCED_BUGS

- T27 A1 reviewer F1 (HIGH): multi-part public suffix table divergence → sibling-institution spoof, VERIFIED_CURRENT cross-institution, *.edu.kz vacuous. Confirmed on frozen candidate 51f211d.

## UNTESTED_RISKS / NOTES

- Reverse divergence exists but is NOT asserted (per packet scope): verifier has `govt.nz` which discovery lacks — a superset guard was not requested; flagged for planner if a single shared source is chosen.
- Reviewer F1 fix responsibility sits with the dev patch; my e2e assertion is status-level (no VERIFIED_CURRENT), so it also passes if the dev instead fails-closed by other means, as long as positive pin (5) and subset guard (6) hold.
- Redirect-provenance F1 (security review, final_url ignored) is a separate ticket; NOT covered here (out of A2 scope).

## BLOCKERS

None.

## NEXT_ACTION

Developer: branch from QA commit `c823d72` (per TEAM_RULES repair flow), widen `_MULTIPART_PUBLIC_SUFFIXES` to agree with `live_discovery.MULTIPART_SUFFIXES` (allowed path), make the 6 RED tests green without touching test files, produce new candidate SHA for verification + re-review.
