# Narrow backend security proposal — external, not applied

**Ready for exact independent review.** Three native app files and two existing test files only. Primary bytes and STOP unchanged. This packet repairs moderation authorization and private API response storage policy; rejected-PII logging, reset-token atomicity and retention wording remain queued audit findings.

- `backend/app/config.py`: default-empty operator-provisioned `moderator_user_ids`; comma-separated exact immutable account IDs. Legacy `moderator_emails` is still accepted by Settings but grants no privilege. No email verification is fabricated; no migration/auth default changed.
- `backend/app/api/routes_social.py`: require_moderator accepts only the authenticated Principal.user_id in that list. Account deletion/re-registration cannot inherit privilege via the same email. Account-ID provisioning is an operator trust decision. Avatar comment now reflects API no-store override.
- `backend/app/main.py`: _secure takes its current Request and sets Cache-Control:no-store on `/api` and `/api/*`, including both CSRF refusals, rate-limit refusal and normal route/HTTPException responses. Every existing call supplies Request. Static asset and `/apiary` routes retain their policy/ETag/Last-Modified. Stale SameSite comment corrected to Lax; cookie behavior unchanged. Generic uncaught server/upstream 500 responses outside this middleware's returned response boundary are not claimed covered.
- `backend/tests/test_social_moderation.py`: existing moderator helper explicitly provisions trusted fixture account ID. All 19 original test functions and assertions remain byte-identical. New native cases: unverified named-email denial, denied cross-workspace removal leaves Post/Report untouched, positive operator-provisioned account plus other tenant-owner denial, deleted/recreated same-email ID denial.
- `backend/tests/test_security.py`: all 21 original test functions byte-identical. Seven new functions / 11 cases exercise successful case/account/social responses, case and paid result exports, auth/404, both CSRF checks, limiter, actual avatar upload/read and static caching preservation. Native entitlement rows authorize the export; no paywall mock or invented flag.

## Exact evidence

Final formatted source **58 PASS / 0 FAIL / 0 skip** = 43 existing cases + 15 new. Final own native run 36.423s; normal imports resolve to owned runtime app. Corrected original-source OFF subset **1 PASS / 12 expected functional FAIL**: two real moderation failures (queue200, unauthorized remove200/actioned) + ten storage-policy failures; static preservation passes. OFF subset is not a full original suite.

Initial native ON **56 PASS / 2 FAIL**, OFF **1 PASS / 12 FAIL** included two author fixture mistakes (nonexistent paywall_enabled / unavailable Pillow). Original source, logs, JUnit and metadata preserved under history-attempt1; those two are not application defects. They were fixed via real native Entitlement and existing stdlib synthetic PNG helper. A failed formatted-text edit left two F821 Ruff errors; exact failed log retained, fixed before attempt2. Corrected attempt2 **58 PASS** then final same suite rerun after authorized comment correction; no original expectations changed, no install.

Backend-package-context Ruff check, format check and mypy on all five files exit0. Mypy emits unchanged annotation-unchecked notes. Pytest retains two environment/dependency warnings (plugin-disabled asyncio_mode; TestClient/httpx deprecation); no warnings suppressed by this proposal.

Socket/DNS guard blocked one import-time urllib3 IPv6 loopback bind(::1,0). Exact stack in network receipt; zero connect/DNS/external dispatch and zero listening ports. Do not call this “zero guard attempts”. Native own SQLite/session/migrations are isolated; no primary .env, DB, account, STOP reset, provider/model call or Git operation. Runtime/dependency/db/cache/pyc files are deliberately excluded from archive allowlist.

## Integration / acceptance bounds

Apply only the five proposed files in proposed-source.json after peer review. Review old moderator deployment config: provision the trusted account ID explicitly; email-only deployments fail closed. Full primary gates and deployment/header/browser cache behavior are not executed by this packet. no-store is defense in depth, not proof that every browser/back-forward/state copy was erased or that a production cache exploit occurred. Privacy policy must still disclose actual data/retention/vendors from the separate backend-audit map.
