# Security and privacy model

ASHYQ Apply handles applicant profiles, academic results and application plans.
Treat every profile, export, backup and database snapshot as confidential student
data. The service is a research assistant: it never submits an application,
attests, pays, uploads to a portal or impersonates a recommender.

## Trust boundaries

- The browser is untrusted input. Authentication uses a random opaque session
  token in an `HttpOnly`, `SameSite=Strict` cookie; only its SHA-256 hash is
  stored. Production refuses to start without authentication, PostgreSQL,
  HTTPS-only CORS origins and Secure cookies.
- Every database read and mutation starts from the authenticated organization.
  Applicant cases, runs, results, claims, exports and audit events are filtered
  by that tenant; another tenant's identifier returns 404 rather than revealing
  that it exists.
- Every university URL is attacker-controlled. Only HTTP(S) on approved web
  ports is accepted. Loopback, private, link-local, metadata, multicast,
  reserved and mixed public/private DNS answers are blocked. Each redirect is
  revalidated, the HTTP connection is pinned to the validated address, TLS SNI
  and `Host` retain the original hostname, response types are allow-listed and
  bodies are streamed under hard size limits.
- Browser rendering is a fallback only. Every navigation and subresource is
  intercepted and checked by the same network policy; downloads, service
  workers, media, fonts and websockets are disabled. Production infrastructure
  should additionally deny private and metadata egress at the network layer.
- The worker treats jobs as hostile state: leases, bounded attempts,
  idempotency keys and unique constraints prevent duplicate or immortal work.

## Web controls

- Passwords are normalized only by length and stored with salted `scrypt`.
- Login, registration and expensive research starts have fixed-window abuse
  limits. The limiter is a per-process safety shield, not a distributed quota.
- Unsafe authenticated requests reject cross-site Fetch Metadata and untrusted
  `Origin` values. Security headers include CSP, frame denial, MIME sniffing
  denial, a restrictive permissions policy and HSTS in production.
- Outbound URLs are checked for email addresses, credential-shaped parameters
  and long identifier-like query values. Applicant profile fields are never
  added to university search URLs.
- Application logs and audit events contain identifiers and actions, not names,
  scores, citizenship, passwords or source-page bodies.

## Payments

- `POST /webhooks/apipay` is the only unauthenticated write endpoint in the
  service. It caps the body at 64 KiB before parsing, verifies
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

## Data lifecycle

- Deleting an applicant case cascades through its runs, results, evidence,
  conflicts and document checklists.
- Exports and HTTP cache files are local operational data and must not be
  committed. `backend/data/`, `private-backups/` and environment files are
  ignored by Git.
- PostgreSQL backups contain the same sensitive data as production. Encrypt
  them, restrict access, keep at least 7 daily and 4 weekly restore points, and
  verify restores only in a new scratch database. See
  `docs/BACKUP_RESTORE.md`.
- The repository contains synthetic demo applicants only. Demo sources use the
  `fixture://` scheme and exports are labelled synthetic.

## Known residual risks

- Email verification, password reset, MFA, organization invitations and
  counselor roles are not implemented. Public self-registration should remain
  disabled unless an operator is prepared to manage abuse and account support.
- The abuse limiter is local to one API process. A multi-replica public service
  needs a shared limiter at the edge or in PostgreSQL/Redis.
- Application-level DNS pinning protects the HTTP tier. Chromium still performs
  its own connection after route validation, so a production host must also
  enforce egress firewall rules that deny RFC1918, link-local and cloud metadata
  ranges.
- Live extraction is conservative but not authoritative. A sourced result is a
  statement about a page, never a guarantee of admission or funding.
- The container stack is defined and CI builds it, but it has not been run on
  this Mac because Docker is unavailable. No public deployment has been
  security-reviewed.

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
