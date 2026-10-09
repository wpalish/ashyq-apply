# Offline deployment/security configuration review

Source-only result: **two material configuration gaps remain in the Compose/Nginx path**. The address-trust contract is contradicted by the published API port and by the treatment of forwarded headers. The known Nginx header-inheritance gap remains unverified at runtime. Neither finding establishes a deployed vulnerability, an authentication bypass, an exploit, or a comparison of competitor security.

This packet reviewed 24 finite source paths/ranges at HEAD `57a603de35a1ea8817814e8bc29e7ab4f8829726` / `task/product-privacy-diagnostics`. Source hashes are in `source-manifest.json`. Root alone may decide and apply a next task. No primary or Git mutation, server, container, test, network/vendor/provider/model request, secret/environment read, user database read, label/heldout read, or reset-token proposal inspection/execution occurred. Counters for these executions are all **0**. The reset native scope remains stopped and is not a recommendation in this report.

## 1. Highest-priority next bounded task: make Compose client-address trust true

**Source-confirmed configuration conflict; runtime/deployment status NOT RUN.**

- `docker-compose.yml:62-65` says Nginx is the only caller and enables `UNIMATCH_TRUST_PROXY_HEADERS=true`. The same stack publishes the API at `docker-compose.yml:75-76` using `${API_PORT:-8099}:8099`, with no host-address restriction in that mapping. `backend/Dockerfile:56` binds Uvicorn to `0.0.0.0` and declares all forwarded peers trusted. Source therefore does not enforce its own “only Nginx” premise. Actual reachability depends on the deployment/host network and was not checked.
- In the intended Nginx API path, `frontend/nginx.conf:34` uses `$proxy_add_x_forwarded_for`, while `backend/app/main.py:159-163` selects the first comma-separated header entry whenever proxy trust is true. That combination does not visibly establish an operator-controlled, caller-independent first entry. It needs an actual single-trusted-proxy contract. There is no `set_real_ip_from` / `real_ip_header` configuration in the reviewed Nginx file.
- The affected source boundary is the per-address budget for login/register, research enqueue, PDF parsing and social mutations (`backend/app/main.py:208-229`). It is **not** a tenant-authorization bypass. Normal login also has a separate per-email budget (`backend/app/api/routes_auth.py:142-151`); do not claim every rate limit disappears. Per-process limiting remains an explicitly documented residual even after the trusted-address issue is repaired.
- Existing `backend/tests/test_security.py:208-253` passes synthetic forwarded addresses directly into TestClient to verify separate budgets and the per-email control. Those source tests do not verify an actual Nginx boundary, a directly published Docker port, or the Fly edge. Their already-completed predecessor execution is not repeated or adopted as this review's runtime proof.

**Minimal proposed task, not a patch:** decide the supported Compose ingress topology, then restrict the API to that topology and ensure the last trusted ingress constructs the canonical caller address. For the current one-Nginx layout, removing the external API publication is the cleanest candidate; a deliberate local-only diagnostic mapping is an alternative with a narrower claim. Nginx should construct a controlled canonical forwarded value rather than preserve an untrusted first entry. Do not blindly change the Fly header interpretation: it uses a different ingress path and is not proven by this Compose review.

A finite task would primarily touch `docker-compose.yml`, `frontend/nginx.conf` and `scripts/verify_compose.sh`. The current smoke script uses direct `$API` at lines13,32,45,55,60,65, so removing the public API port also requires the script to verify through `$WEB/api/...` or an explicitly private in-container check. Preserve the stated web → API → worker acceptance, synthetic data, internal API healthcheck, ordinary users' separate limits, legitimate CLI behavior and the separate per-email control. Root writes exact source/test scope before any application change.

Required evidence for closure: exact supported server/container version and config; an isolated synthetic actual ingress observation; ordinary distinct callers retain their intended budgets; injected inbound forwarded text cannot become a new operator-trusted identity; direct ingress is inaccessible or explicitly untrusted according to the chosen topology; internal health and same-origin browser/CLI flows still work. A source assertion alone is not these runtime results. If the required container/server runtime is unavailable, report **NOT RUN / deferred**, never PASS.

## 2. Known separate gap: Nginx headers at location scope

`frontend/nginx.conf:10-14` sets five security headers at server scope. `/assets/` and exact `/index.html` define their own `add_header Cache-Control` at lines19 and25. The Dockerfile declares `nginxinc/nginx-unprivileged:1.27-alpine` at `frontend/Dockerfile:18` and copies that exact config at line23. This is the inherited-header concern already retained in `SECURITY.md:257-258` and `docs/legal/RELEASE_READINESS.md:23`; it is **not a newly discovered or fixed issue**.

Source shape indicates a location-inheritance risk for the HTML document and assets; the exact built image/runtime responses were not checked, and no header-loss observation is claimed. Do not resolve it with a newer-version-only inheritance directive against the declared 1.27 image without a versioned compatibility check. A shared included header block or explicit same policy in locations is a candidate, preserving hashed-asset immutable caching and index revalidation. Do not weaken CSP, drop cache contracts, or call local API middleware proof an Nginx proof.

Finite acceptance matrix for a later task: `/`, `/index.html`, one real hashed JS/CSS asset, missing asset, one SPA deep link, normal API response, unauthorized API response, early CSRF/rate refusal, and `/metrics` refusal. Record actual status/header sets for each from the exact supported config. The private API `no-store` control and static cache directives must remain distinguishable. Include the actual image identifier/version, not merely this Dockerfile tag. The known absence of Docker on the owner machine remains **container verification NOT RUN**.

The Fly build (`Dockerfile.fly` + `fly.toml`) directly serves built frontend assets through FastAPI's static mount; it does not reference the separate frontend Nginx image. A Compose/Nginx correction cannot by itself be described as a Fly production header fix.

## 3. Implemented source controls and their limits

| Source control | Verified from inspected source | Scope/remaining qualification |
|---|---|---|
| Production guard | `backend/app/config.py:221-244`: rejects auth-off, insecure cookie, non-PostgreSQL and absent/wildcard/non-HTTPS CORS origins | Source/runtime validation logic; real deployed effective settings were not inspected |
| Browser mutation checks | `backend/app/main.py:189-206`: unsafe methods with auth reject `Sec-Fetch-Site: cross-site` and unlisted Origin | Missing browser metadata is deliberately permitted for CLI; no new CSRF vulnerability is inferred solely from that intent |
| Opaque session cookie | `backend/app/security.py:151-177`: random token; stored token hash, HttpOnly, configured Secure, SameSite=Lax, Path=/, no Domain parameter | Secure is enforced by the production guard; no claim MFA, verified email or representative authorization exists |
| Principal binding | `backend/app/security.py:195-238`: stored session expiry, user active and workspace membership required | Existing server authorization remains authority; no account data/runtime was read |
| Response policy | `backend/app/main.py:167-186`: CSP/security policy on returned middleware responses and API `no-store`; HSTS conditional on production+Secure | Already accepted local increment; an unhandled exception outside the completed middleware or an external proxy is a separate boundary |
| Fly declared ingress | `fly.toml:12-15,26-28,41,44-50`: production/auth/Secure, explicit HTTPS origin, trust enabled, forwarded-all Uvicorn, forced HTTPS and app-only service | Edge rewriting/reachability are comments/declarations, not independently verified effective deployment; app region `ams` is not a DB/backup country |
| Runtime account restrictions | `backend/app/config.py:136-148`: immutable moderator account IDs default empty; email configuration gives no privilege | Operator must identify/provision actual IDs; do not infer provision from source defaults |
| Container constraints | `backend/Dockerfile:31-48`, `Dockerfile.fly` non-root account; Compose API/web read-only, API/worker/web no-new-privileges; PostgreSQL expose-only | File definitions only; no containers were built/run or host access/firewall state established |
| Frontend transport | `frontend/src/api/client.ts:143-145`: relative same-origin requests with credentials included | Does not prove a trusted reverse-proxy address or session-cookie race cancellation |
| Rate limiting | `backend/app/main.py:109-145,208-229`: per-process groups; `routes_auth.py:142-151`: normal-login per-email limit | Not shared across API replicas; source does not claim distributed quotas |

No other material configuration defect is asserted from missing hardening middleware or hypothetical configuration values. Public documentation endpoints and the absence of TrustedHost middleware were not turned into findings without an actual source-confirmed sensitive use of the supplied Host value.

## 4. Operator-dependent release gates are still real work

`docs/legal/operator-facts.json:3-28` remains `UNCONFIRMED_NOT_FOR_FINAL_PUBLICATION`: legal name/identifier/country/address/privacy contact/support contact are null; primary/replica/backup/log countries and encryption/retention evidence are null; actual processors, legal jurisdiction/basis, minors/representative procedure, consent runtime, seller/refunds and incident contact/tabletop are also null. The one confirmed source fact `source_config_app_region=ams` does not fill any of those actual-storage fields.

`docs/legal/README.md:18-20`, `docs/legal/RELEASE_READINESS.md:17-24` and `frontend/src/screens/LegalScreen.tsx:41-42` disclose these draft boundaries. `frontend/src/App.tsx:200-201` permits the legal screen and AuthGate imports the public notice; that is useful access, not a consent record. Normal registration at `backend/app/api/routes_auth.py:85-125` records account/workspace and creates a session, with no policy-version/notice-hash/purpose/representative receipt. `docs/legal/CONSENT_SPEC_RU.md:28-36` is a proposed server specification, not completed runtime consent. Do not insert fabricated operator facts or pretend a checkbox alone supplies the missing server contract.

The existing `SECURITY.md:276-281` points to private repository-owner contact; `docs/legal/INCIDENT_RESPONSE.md:7` correctly requires a genuinely serviced incident/privacy route. A GitHub-profile reference does not prove a staffed privacy-rights contact, response time, backup retention, or an operator identity. Owner confirmation is required for those facts and the legal package cannot truthfully become final without them. This review requests no repeated question; root already has a pending operator-facts request.

## 5. Handoff conclusion

The highest useful source-only next step is the Compose ingress/address-trust contract, followed by the exact-version Nginx header matrix. Root's current PII diagnostics proposal remains independent and takes precedence in the active baton. Operator/legal/consent/deployed-journey gates remain unresolved. Research quality is not tested by this packet. Security Draft #78/local source5b48 acceptance is neither undone nor broadened. No candidate source change, app default, historical STOP, production, branch protection, secret, user database, cloud CI, model/provider or university request was changed.

Report status: **SOURCE_CONFIRMED_QUEUE_INPUT / NO_PATCH / ALL_RUNTIME_NOT_RUN**.
