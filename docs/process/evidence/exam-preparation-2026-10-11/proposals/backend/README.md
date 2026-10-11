# Backend preparation foundation — external proposed patch

Root is the sole writer of `integration-2026-10-11/source` and Git. This packet supplies **15 proposed repository files**, including five explicitly separate integration copies (`main.py`, `models/__init__.py`, `models/applicant.py`, `api/routes_profile.py`, `api/routes_billing.py`). No source/primary/Git/provider/worker/API process was changed or launched by this agent. The audit is [backend.md](../../audits/backend.md); exact UI/API keys are in [CONTRACT.md](CONTRACT.md).

## Implemented scope in these bytes

- Public six-family, link-only exam metadata, with only three real original starter lessons (9 original multiple-choice items); planned TOEFL/DET/HSK/CSCA courses have zero invented lessons. No licensed/official items, logos, scraping, essays, audio, AI, band/SAT conversion or admission prediction.
- Read-only ACTIVE/EXHAUSTED **started-term** preparation access, independently of research-case quota and CASE_FULL. Exclusive end boundary, explicit development-only mode, no new checkout/provider/order kind.
- Owned-case lesson/submit/progress/plan API, exact content-version and full known-answer validation, UUID canonical replay/conflict with database case-scoped uniqueness. Feedback released only for a submitted complete attempt. Historical receipts/progress are own data after expiry; no server draft persistence promise.
- Original RequirementCheck and ClaimOut values, scopes, excerpts, IDs and URLs retained. Missing references/unrecorded scope remain unknown; age/supersession/profile-newer snapshots stale; unresolved conflicts remain conflicted. Co-published alternatives and waivers are not resolved. `test-blind` is not labelled optional. Specific IELTS unimplemented skills have no unrelated Reading goal; named SAT skills link only their own starter.
- New StudyAttempt table via migration `f1a2b3c4d511` from `d8e412c6a901`; ORM profile relationship `all, delete-orphan` with passive_deletes=False; profile export `study_attempts` + `counts.study_attempts`. No answer/feedback material in AuditEvent. Academic profile fields are never updated by practice.

## Actual verification

`evidence/static-results.json` records **Ruff check PASS**, **Ruff format --check PASS** (15 files), **focused mypy PASS** (6 new modules). These are static checks in an owned external tree using already-installed tools; no dependency installation. An initial Ruff style finding and one local type shadow were corrected before these final receipts.

Native pytest and migrations are **NOT_RUN** by this agent. `test-design.json` is a static AST calculation, not pytest collection: **92 API/database cases** (46 cases × migrated SQLite/PostgreSQL) + **30 pure synthetic domain/content cases = expected 122**; 110 assert statements. Tests register actual main routes without running lifespan/startup job reconciliation; fixtures use native migration-backed engines, function-scoped environment/cache isolation and IPv4/IPv6 connect/sendto/DNS refusal while preserving AF_UNIX. No existing app/test assertions or fixture configuration were weakened.

The independent curriculum review is [curriculum-review.md](../../audits/curriculum-review.md); it is static only and separate from engineering gates.

## Root acceptance prerequisites

1. Check every `before_sha256` / new-path absence in `source-pins.json` against the chosen integration tree. Apply only reviewed diffs; another head or schema head requires deliberate reconciliation.
2. Use the existing external full-gate isolation: synthetic Settings/env/database/cache/export, strict no-provider network, owned private Unix PG, shared runner lock and retained cleanup/source pins. New native fixture **does not itself fence libpq or descendant processes**; outer reviewed gate guard is required. Root must reject PostgreSQL skips for the required PG result.
3. Run the two unchanged proposed native modules on SQLite and real migrated private PostgreSQL; retain actual counts, migration/replay/source/cleanup receipts. Then existing backend full/native required coverage **92** + frontend/native integration controls on the exact applied bytes. No lowering, skipping or substitution for the full gate.
4. Check app integration/Billing optional-field compatibility, auth, profile/account ORM deletion and own export, and profile/result switch/reload/frontend UUID fences. All such runtime acceptance remains pending until root receipts exist.
5. Product acceptance is a starter foundation, not a complete commercial course. Expanded paid access/pricing for new customers, broader authored content, legal/licence decisions and versioned modern TOEFL/Chinese official-score profile fields are separate future work. Existing subscription-start policy is retained; a pending invoice alone cannot start learning here.

`proposed-backend.patch` is a unified readable proposal, not an applied patch. `source-pins.json` binds source dependencies and all 15 before/after files. `artifact-manifest.json` pins the deliverable packet and excludes the disposable static-tree/cache. Source HEAD is parent-reported `11091904`; agent did not run Git. Search quality remains outside this packet; closed STOP/UNSCORED research stays untouched.
