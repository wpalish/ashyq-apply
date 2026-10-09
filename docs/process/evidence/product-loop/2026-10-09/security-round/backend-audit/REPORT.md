# Backend security / privacy audit

Read-only source review. Source paths below are relative to `/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply`; exact 45 file hashes are in source-pins.json. No app imports, account/DB operations, external calls, secrets values or Git operations in the audit. STOP remains `65b5ff0e…`. This is not a legal opinion, deployment penetration test, or launch acceptance.

## Confirmed findings

1. **P1 — moderation privilege from an unverified email.** `api/routes_auth.py:85–116` accepts a new email and issues a session; `api/routes_social.py:1028–1037` authorizes moderator by that email alone. `models/auth.py:31–34` records verification but no native check enforces it. If public registration is enabled and a configured moderator address is free, a registrant can read the global queue (including reported private-message excerpts) and remove other users' content (`routes_social.py:1097–1128`). Existing registration and session ownership do not prove mailbox ownership. Fix: default-empty operator-provisioned immutable account-ID allowlist. Native isolated reproduction/proposal will be a separate packet; deployment flags were not read.

2. **P2 — a privacy refusal can copy the rejected value into logs.** `adapters/fetching.py:973–980` logs the first 120 characters of a rejected email/token-bearing URL, and `:628–635` does the same on a redirect. `adapters/search/intent.py:72–90` repeats rejected field values in QueryPrivacyError, while `pipeline/runner.py:471–477` stores/logs the exception. Length truncation is not redaction. Fix: host/kind or opaque identifier only; value-free privacy errors. Test: synthetic marker never appears in caplog/run/audit diagnostics and no HTTP is sent.

3. **P2 — private API storage policy is absent.** `main.py:167–182,192–232` applies security headers but no `Cache-Control`; private profile/export/account/social responses therefore have no common no-store rule. Avatar API explicitly requests private 24h caching (`routes_social.py:1207–1214`). This confirms a response-policy gap, not a production caching exploit. Narrow fix: no-store at the existing middleware boundary for `/api` and `/api/*`, including 401/403/429, while static paths keep their existing cache headers. Native client regressions are proposed separately.

4. **P2, separate queued repair — reset token consume is not atomic.** `routes_account.py:233–252` reads used_at, then ordinary ORM updates password/used_at; `:272–273` commits and issues a session. Two concurrent transactions can both pass the initial unused check. Sequential reuse tests do not cover this (`tests/test_account_flows.py:500–511`). Preconditions: recovery enabled, same valid bearer token and concurrent requests. No PostgreSQL race was executed. Public fly.toml declares password reset disabled; this is not verification of the running deployment. Minimal fix: one atomic consume/lock-and-recheck in the password transaction; meaningful test uses two owned PG sessions and permits exactly one redemption.

5. **P2 — export/deletion copy promises more than native deletion.** `routes_profile.py:368–398` says complete record / removes all, yet entity-linked audit is retained and a deletion audit is added; `models/research.py:209–229` has only organization FK. `models/jobs.py:54–80` retains run IDs/errors without a run FK; `models/billing.py:135–144` retains entitlement profile IDs without FK. Social report excerpts deliberately survive deletion of the subject (`models/social.py:366–400`). This is a retention/disclosure mismatch, not proof of unauthorized access. Fix precise exceptions and bounded redaction/retention rules; retain necessary security/billing history deliberately rather than claim zero data.

## Existing protections verified in source

- Scrypt + random salt, constant-time verification; opaque server-side session token digests; HttpOnly/Secure-configurable/Lax cookie; session expiry and membership recheck (`security.py:93–109,151–230`).
- Owned profile/run queries include organization; cross-tenant IDs return 404; organization switch checks membership. Exports and full evidence are owned/paywall checked (`api/tenancy.py:12–39`, `routes_account.py:323–339`, `routes_results.py:434–471`). A workspace is shared by its members, not per-user isolation.
- Production refuses auth off, insecure cookie, SQLite and wildcard/non-HTTPS CORS; exact-origin unsafe-method checks and per-process abuse limits exist (`config.py:215–247`, `main.py:79–85,185–232`). Proxy trust must match actual trusted proxy topology; that topology was not audited. Main comment says SameSite=Strict, but actual cookie is Lax: documentation drift, not demonstrated CSRF bypass.
- Security headers/CSP/conditional HSTS; protected metrics; payment HMAC, request-size cap and value-redacted payment errors; crawler SSRF checks pin validated public addresses, block credential/private targets and validate redirects. These are source safeguards, not actual deployment proof.

## Privacy policy inputs

See DATA_FLOW.md and field-map.names-only.json for categories, recipients and exact source ownership/retention. Do not promise that all inputs are anonymous: display names, contact email, nationality, grades, finances, free-text activities/notes, social biography/messages and transcript excerpts can identify a person. Current app has no native profile-aware LLM invocation: the TypeSafe seam exists but has no app call site; research_privacy is stored preference only. Search sends a bounded public research target, not the profile payload. No current provider setting or vendor retention/region/DPA was inspected.

Launch privacy/consent readiness still needs operator-confirmed deployment flags, moderator IDs, actual vendors/regions, backup/log retention, deletion exceptions, security contact/controller details and age/guardian policy. None is established by a local test suite. No application is submitted by the audited research/export endpoints. Account deletion exists; shared workspaces survive removal of one member.

## Qualifications

Static audit only; runtime tests are sketches except future separate bounded proposal. Missing-path/glob read errors were tooling mistakes, not application failures. No primary changes or historical source/evidence rewrites. Full product/source gate PASS is not security or privacy policy acceptance.
