# Security and privacy model

**DRAFT — source controls applied; release verification pending.** This 9 October
2026 reconciliation describes applied source `c7b41fcf`, following the security
round and its authorized-case recovery. It is not a final operator policy or a
public launch approval. Focused implementation reviews are separate from the
current recovery full/browser checks, which are still pending at this snapshot.
See [release readiness](docs/legal/RELEASE_READINESS.md) for open conditions.

ASHYQ Apply handles applicant profiles, academic results and application plans.
Treat every profile, export, backup and database snapshot as confidential student
data. The service is a research assistant: it never submits an application,
attests, pays, uploads to a portal or impersonates a recommender.

## Trust boundaries

- The browser is untrusted input. Authentication uses a random opaque session
  token in an `HttpOnly`, `SameSite=Lax` cookie; only its SHA-256 hash is
  stored. Lax rather than Strict because Strict drops the cookie on any
  cross-site navigation, which signed people out as they arrived from a
  password-reset link; CSRF is carried by the Fetch Metadata and `Origin`
  checks below. Production refuses to start without authentication,
  PostgreSQL, HTTPS-only CORS origins, Secure cookies, an HTTPS public base
  URL, a configured mail sender and scrypt at 2**17 or stronger.
- Tenant-private case, research, export and audit routes start from the
  authenticated organization. Public account-entry and intended cross-workspace
  community flows have separate access rules.
  Applicant cases, runs, results, claims, exports and audit events are filtered
  by that tenant; another tenant's identifier returns 404 rather than revealing
  that it exists. This is a workspace boundary: members of the same workspace
  can access its cases. It is not a per-applicant permission system.
- Every university URL is attacker-controlled. Only HTTP(S) on approved web
  ports is accepted. Loopback, private, link-local, metadata, multicast,
  reserved and mixed public/private DNS answers are blocked. Each redirect is
  revalidated, the HTTP connection is pinned to the validated address, TLS SNI
  and `Host` retain the original hostname, response types are allow-listed and
  bodies are streamed under hard size limits.
- Browser rendering is a fallback only. Every navigation and subresource is
  intercepted and checked by the same network policy; downloads, service
  workers, media, fonts and websockets are disabled. The final navigation's
  HTTP status decides the outcome: a rendered error page (404/403/429/5xx) is
  reported as a failed fetch, so it can never be escalated, cached or cited
  as page content, and a navigation that returns no response fails closed
  too. A browser that dies mid-render surfaces as a diagnostic result rather
  than a crash. Production infrastructure should additionally deny private
  and metadata egress at the network layer.
- The worker treats jobs as hostile state: leases, bounded attempts,
  idempotency keys and unique constraints prevent duplicate or immortal work.

## Web controls

- Passwords are normalized only by length and stored with salted `scrypt`, at
  cost 2**17 for new hashes. Older 2**14 hashes still verify - the parameters
  travel in the encoded string - so raising the cost locks nobody out.
- Changing a password revokes every other session; completing a password reset
  revokes all of them, including the one that asked. Reset tokens are stored
  as digests, are single-use, expire in an hour, and are rate-limited per
  address and per account. The reset response is identical whether or not the
  email has an account. The reset-request API returns only the neutral detail
  response in every environment; the link goes to the configured mail sender.
  The development console sender logs the recipient and message, including the
  link, so those logs must be restricted and treated as sensitive.
- Sessions are capped per user (20 by default, oldest revoked first) and
  expired rows are cleaned up on the next sign-in.
- Deleting an account requires the password, and erases the workspaces where
  that user is the only member together with their applicant cases, runs and
  claims. An audit record is written before deletion; whether it survives an
  organization cascade depends on that record's lifecycle. There is no
  guaranteed surviving deletion receipt in the current implementation.
- `email_verified` is recorded but not enforced: there is no verification flow
  yet, and `UNIMATCH_AUTH_REQUIRE_VERIFIED_EMAIL` stays false until there is
  one. Saying so is the honest position; pretending otherwise would be
  theatre.
- Login, registration and expensive research starts have fixed-window abuse
  limits. The limiter is a per-process safety shield, not a distributed quota.
- Unsafe authenticated requests reject cross-site Fetch Metadata and untrusted
  `Origin` values. Security headers include CSP, frame denial, MIME sniffing
  denial, a restrictive permissions policy and HSTS in production.
- Global community moderation is provisioned by immutable account IDs in
  `moderator_user_ids` (empty by default). A claimed email, workspace ownership
  or the legacy email setting does not grant moderation privileges. Identifying
  and provisioning the intended account remains an operator responsibility.
- Returned responses on `/api` and `/api/*`, including ordinary route errors and
  early CSRF/rate refusals, receive `Cache-Control: no-store`. This leaves static
  caching unchanged. It does not erase previous caches, exports or browser
  storage; responses generated outside this middleware after an unhandled
  exception and deployed proxy behavior need separate verification.
- Authenticated browser drafts, case/run pointers and document ticks use a
  server-principal/user-and-organization namespace. Owner binding precedes
  private-tree hydration; acknowledged logout and owner changes remove the
  recognized applicant storage keys. Auth transitions lock other cooperative
  tabs, trigger private-tree unmount/revalidation, and use owner/generation checks
  around asynchronous API and store actions. Unscoped legacy drafts are not
  automatically imported into an authenticated owner; explicit auth-disabled
  demo behavior is retained. This is cooperative browser isolation, not server
  authorization, encrypted storage, an XSS defense or an atomic guarantee for
  requests already in flight with a shared cookie. Server tenant checks remain
  authoritative.
- Outbound URLs are checked for email addresses, credential-shaped parameters
  and long identifier-like query values. Normal programme queries can derive
  degree, field and intake from preferences; they exclude the full applicant
  profile, identity, contacts, grades and budget. This is minimization, not
  anonymity. The optional bounded TypeSafe decision adapter exists in source;
  an active product call path was not established in this audit.
- Audit records contain identifiers, actions and operation details, including
  some error text and payment metadata. Rejected URL/query error handling can
  retain rejected values. Redaction, retention and restricted operator access
  are required; logs must not be assumed to be free of personal information.

## Payments

- `POST /webhooks/apipay` is a payment callback authenticated by its signature.
  Public registration, login and reset requests separately write account,
  session or reset state under their account-entry controls. The callback caps
  the body at 64 KiB before parsing, verifies
  `X-Webhook-Signature` as HMAC-SHA256 over the raw bytes with
  `hmac.compare_digest`, and answers an invalid signature with a bare `401`
  that says nothing about why.
- An unrecognised event type is recorded and ignored; an unknown invoice is
  acknowledged so the provider stops retrying, and acts on nothing.
- A replayed webhook grants exactly once. `apply_status` is the single writer,
  and it is idempotent and indifferent to arrival order.
- **The price is server-side only.** The create-order request has no amount
  field; the amount comes from configuration. A test asserts that sending one
  changes nothing.
- The payer's phone is stored masked (`8707***4455`) and never enters a log
  line, a URL, an audit detail or an error body. A provider validation failure
  names the fields it rejected, never their values.
- `apipay_api_key` and `apipay_webhook_secret` are `SecretStr` and do not
  render in a settings dump. The API key travels in a header, never a URL.
- **A callback that cannot be verified is refused, not accepted.** Both
  providers return `False` from `verify_webhook` when no secret is configured,
  rather than comparing against an HMAC keyed on the empty string, and the
  fake provider is no longer handed a fallback secret written in the source.
  `Settings.validate_runtime` refuses to start when payments are enabled
  without a secret, when production is still pointed at the `fake` provider,
  or when a production secret is shorter than 16 characters. The webhook
  signature is the only thing between a stranger and a free unlock, so every
  way of having no signature is a startup failure.
- Unlocking is authorised through the same `owned_profile` check as everything
  else, so an order against another organization's case answers `404`.
- Subscription quota is spent by exactly one function, `consume_for_case`,
  which takes a row lock (`SELECT … FOR UPDATE`, PostgreSQL) before deciding.
  A test asserts the lock by holding it in one transaction and requiring a
  second with a 500ms `lock_timeout` to fail; with the lock removed that test
  fails, which is the only reason to trust it.
- Remaining quota is counted from the entitlement rows that spent it, never
  from a stored counter, so it cannot drift from what was actually granted.
- Granting a subscription is a CLI action requiring database access. It is
  deliberately not a network endpoint: it happens about once a year per school
  and an admin route would be a privileged surface bought for nothing.

## Accounts and mail

- Passwords are scrypt at `2**17` (about a second of CPU and 128 MB each). A
  hash written under weaker parameters still verifies and is rewritten at the
  next successful sign-in, so raising the cost actually reaches existing
  accounts instead of only new ones.
- Changing a password revokes every other session **and** any unspent password
  reset token. A reset link already in a mailbox is exactly the way back in
  that a password change is performed to close.
- Reset tokens are stored as digests, single-use, and expire in an hour; the
  response to a reset request is identical whether or not the account exists,
  and never carries the token.
- SMTP delivery uses STARTTLS with `ssl.create_default_context()`, so the
  server's certificate chain and hostname are verified. `smtplib`'s default
  context is `CERT_NONE` with hostname checking off, which would have
  encrypted the SMTP password and every reset link to whoever answered the
  port.

## Exports

- Every cell written to CSV and XLSX passes through `export.tabular.neutralize`,
  which prefixes a value beginning `=`, `+`, `-`, `@`, tab or carriage return
  with an apostrophe. Two values in a row come from outside the service — the
  applicant's own notes and text the crawler lifted off a third-party page —
  and a spreadsheet executes a cell that starts with any of those. A bare
  negative number is left alone so it stays a number.

## Data lifecycle

- Deleting an applicant case cascades through its runs, results, evidence,
  conflicts and document checklists. Exporting that case is not an account-wide
  export. Account deletion preserves workspaces with other members; some audit,
  job, entitlement and other users' report records can remain. Primary deletion
  does not prove removal from backups or copies held by recipients.
- A saved case can be exported or deleted before it has a research run. The
  deletion UI shows success and resets relevant local case state only after the
  API deletion is acknowledged; a refusal remains an error. Document-mark
  cleanup is limited to returned result IDs, not a proven sweep of every
  historical mark. Case export includes the case-scoped API record (profile,
  runs, results, claims, conflicts and matching audit entries), not every account,
  job, payment, community or backup record. The API's inherited complete-record
  and all-deletion wording still needs a separate correction.
- After an authenticated reload/login with no local case pointer, the store reads
  the authorized server case list and opens its first, most recently updated case
  through the existing profile/latest-run/result readers. An explicit local new
  case or saved pointer retains priority; newer case intent and owner changes
  invalidate late responses. `newCase` also releases a superseded loading state.
  This recovery uses read-only server data; it neither restores an unowned local
  draft nor creates a case, research run or automatic retry. Current full/browser
  verification of this correction is pending, not a security or data-rights proof.
- Exports and HTTP cache files are local operational data and must not be
  committed. `backend/data/`, `private-backups/` and environment files are
  ignored by Git.
- PostgreSQL backups contain the same sensitive data as production. Encrypt
  them, restrict access, keep at least 7 daily and 4 weekly restore points, and
  verify restores only in a new scratch database. See
  `docs/BACKUP_RESTORE.md`.
- The repository contains synthetic demo applicants only. Demo sources use the
  `fixture://` scheme and exports are labelled synthetic.
- Actual operator details, database/backup/log countries, recipients, lawful
  retention periods and the minors/representative procedure require confirmation.
  Registration currently records neither a policy version nor representative
  authorization. The legal package in `docs/legal/` is a draft until these gaps
  and the corresponding runtime controls are closed.

## Known residual risks

- Email verification, MFA, organization invitations and counselor roles are
  not implemented. Password recovery exists; its read-then-consume token path
  needs a concurrent-use check and atomic repair if confirmed. No concurrency
  result is claimed here. Public self-registration should remain
  disabled unless an operator is prepared to manage abuse and account support.
- The abuse limiter is local to one API process. A multi-replica public service
  needs a shared limiter at the edge or in PostgreSQL/Redis.
- The crawler's egress controls are application-level. What the application
  now enforces: every redirect hop is re-validated and its streamed response
  is closed before the next hop, the address blocklist covers the 6to4 relay
  and AS112 anycast ranges alongside loopback, private, link-local and
  metadata addresses, and a browser-rendered error status is a failed fetch
  that cannot reach the disk cache or a verified claim. What remains
  best-effort: Chromium resolves names and connects by itself after the
  policy's route check, so a DNS rebinding window survives that no in-process
  check can close; the redirects a browser follows internally are not bounded
  by the crawler's redirect cap; and the blocked-hostname list is deliberately
  short, a belt-and-braces check rather than an exhaustive inventory of names
  that resolve to the host. Guarantees therefore stop at the application
  boundary: a production host must also enforce egress firewall rules that
  deny RFC1918, link-local and cloud metadata ranges, which is what actually
  bounds a resolver race. These rules gate outbound crawling only; the
  service's own PostgreSQL and API traffic is unaffected.
- Live extraction is conservative but not authoritative. A sourced result is a
  statement about a page, never a guarantee of admission or funding.
- The container stack is defined and CI builds it, but it has not been run on
  this Mac because Docker is unavailable. No public deployment has been
  security-reviewed.
- Nginx location-level `add_header` declarations can override inherited security
  headers. The deployed Nginx version and route responses need a separate check.
- An application fix, a passing test or a written policy is not a penetration
  test, legal sign-off, a security comparison with competitors or launch proof.

## Verification

Run the security and tenancy suites directly:

```bash
cd backend
.venv/bin/pytest tests/test_security.py tests/test_ssrf.py
.venv/bin/ruff check app tests scripts
.venv/bin/mypy app tests scripts/backup_drill.py
```

Frontend E2E runs include axe WCAG A/AA scans across every reachable workflow
screen on desktop and mobile.

## Reporting

Do not open a public issue containing applicant data, credentials or a working
exploit. Contact the repository owner privately through their GitHub profile
and include the affected version, impact and a minimal reproduction with all
personal data removed.
