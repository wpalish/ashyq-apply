# developer-a2.md — T27 A2 (repair cycle c2), ashyq-developer

## STATUS

IMPLEMENTED — reviewer blocking F1 fixed with a single-table widening; 6 QA RED regression tests green; all gates green; candidate frozen for verification + re-review.

## BASELINE_SHA

- `c823d728179c59d5c1dbb235db517c181b8a6b8f` (QA A2 RED commit, HEAD of ai/c2/t27/dev-a2 at start).
- Pre-flight verified: branch `ai/c2/t27/dev-a2`, `git status --porcelain` empty, HEAD matched the packet.

## CANDIDATE_SHA

- `da836a20167a0186e8681e58a3ec29356bfc040b` (commit "fix: T27 A2 widen multi-part public suffix table to agree with discovery layer", trailer `Agent: ashyq-developer`). Tree clean after commit. No push.

## CHANGED_FILES

- `/Users/wpalish/ashyq-worktrees/c2-t27-dev-a2/backend/app/domain/claim_verifier.py` — ONLY file (62 insertions, 8 deletions). `_MULTIPART_PUBLIC_SUFFIXES` widened from 13 to 59 entries = union of the old verifier table and `live_discovery.MULTIPART_SUFFIXES` (46 added), sorted alphabetically, same module-level `Final[frozenset[str]]` DATA form. Comment above the table documents: deliberate duplication (domain/ must not import app.adapters.*, AGENTS.md §6), the subset test in test_claim_verifier.py as the divergence guard, and the intentionally allowed reverse divergence (`govt.nz`, `gov.au` — verifier table is at least as wide as discovery's).
- No test files touched (QA tests byte-identical). extraction.py / web_requirements.py / all other production files untouched: `git diff --name-only c823d728..HEAD -- app/ | grep -v claim_verifier` → empty.

## ROOT_CAUSE_FIXED

Reviewer F1: for hosts under multi-part public suffixes missing from the verifier table, `registrable_domain` kept only 2 labels and returned the public suffix itself, collapsing sibling universities (uw.edu.pl vs pw.edu.pl, kbtu.edu.kz vs iab.edu.kz) into one "same registrable domain" → `url_matches_domains` True → `is_official_domain` True → VERIFIED_CURRENT from a different institution. Root cause is the stale duplicated table; fix widens it to cover all 57 discovery suffixes. No logic rewiring: `registrable_domain` keep=2/keep=3 selection unchanged.

## GATES (real runs in /Users/wpalish/ashyq-worktrees/c2-t27-dev-a2/backend)

| Gate | Command | Result |
|---|---|---|
| a | `./.venv/bin/python -m pytest tests/test_claim_verifier.py` | **93 passed in 0.46s**, exit 0 |
| b | `./.venv/bin/python -m pytest tests/test_live_regressions.py tests/test_adapters.py tests/test_live_extraction.py` | **158 passed in 2.68s**, exit 0 |
| c | `./.venv/bin/python -m pytest tests/test_claim_verifier.py --cov=app.domain.claim_verifier --cov-fail-under=100` | **93 passed, 100% coverage (93/93 stmts, 0 miss)**, exit 0 |
| d | `./.venv/bin/python -m mypy app tests` | **Success: no issues found in 157 source files**, exit 0 (only pre-existing `annotation-unchecked` notes) |
| e | `./.venv/bin/python -m ruff check app tests && ./.venv/bin/python -m ruff format --check app tests` | **All checks passed! / 157 files already formatted**, exit 0 |

## RED_TO_GREEN (baseline `c823d72`: 6 failed, 87 passed → candidate: 93 passed)

- test_a_sibling_university_under_edu_pl_is_not_the_allowed_domain — RED (`assert True is False`) → PASSED
- test_a_sibling_university_under_edu_kz_is_not_the_allowed_domain — RED (`assert True is False`) → PASSED
- test_the_registrable_domain_of_an_edu_pl_host_is_not_the_public_suffix — RED (`'edu.pl' != 'uw.edu.pl'`) → PASSED
- test_the_registrable_domain_of_an_edu_kz_host_is_not_the_public_suffix — RED (`'edu.kz' != 'iab.edu.kz'`) → PASSED
- test_the_verifier_suffix_table_covers_the_discovery_table — RED (46 missing suffixes) → PASSED
- test_a_sibling_university_page_is_never_verified_current — RED (pw.edu.pl published VERIFIED_CURRENT IELTS claims for uw.edu.pl) → PASSED
- test_a_listed_suffix_still_resolves_to_the_registrable_domain (was already GREEN) — stays PASSED

## DESIGN_NOTES

- Merge analysis (computed programmatically, not by eye): discovery = 57 entries, old verifier = 13, missing = 46, union = 59. No casing conflicts — both tables are all-lowercase (casefold check found zero collisions).
- Reverse divergence (verifier-only, discovery lacks): `gov.au`, `govt.nz`. Kept in the verifier table; this direction is intentionally allowed and now documented in the code comment (QA A2 had flagged govt.nz; gov.au is the second such entry).
- Semantics verified post-fix: `registrable_domain("uw.edu.pl")=="uw.edu.pl"`, `("iab.edu.kz")=="iab.edu.kz"`, `("www.ox.ac.uk")=="ox.ac.uk"`; narxoz.kz pins and attacker.example shape unchanged (`narxoz.kz.attacker.example` → `attacker.example`).
- OFFICIAL_PUBLIC_TLDS deliberately untouched (out of F1 scope; behaviour gated by tests unchanged).

## MIGRATIONS

None. No schema, enum, or payload changes; pure domain-data widening.

## RESIDUALS

- Reviewer non-blocking F2-F7 and security F1 (redirect provenance / final_url), F2 fee-window class, F3 clause-scoped negation, F4 `none` negation, F5 T31 producer contract remain open tickets — untouched, as scoped.
- Known reverse divergence (`gov.au`, `govt.nz`) is unguarded by design (subset test only guards discovery ⊆ verifier); if a superset guard is ever wanted, it needs a new QA cycle.
- If discovery's table grows again, the subset test forces this table to follow — that coupling is the guard, not a shared source (cross-import forbidden by AGENTS.md §6).

## BLOCKERS

None.

## NEXT_ACTION

QA verification + reviewer re-review on frozen candidate `da836a20167a0186e8681e58a3ec29356bfc040b` (branch ai/c2/t27/dev-a2, not pushed — user gate).
