# Payments, phase 1 — one-time case unlock via Kaspi (ApiPay)

Status: approved for planning · Date: 2026-09-04 · Branch: `worktree-payments-phase-1`

## 1. Why

ASHYQ Apply has no monetisation. The agreed model has two surfaces:

* **B2C** — the first run of a case is free but deliberately incomplete. The full
  report is unlocked by a single payment for that case.
* **B2B** — schools and admissions consultancies buy an organization-wide
  subscription.

This spec covers **B2C only**. It is designed so that B2B reuses the same
entitlement table and the same provider adapter without rework.

## 2. Scope

**In scope**

* Order lifecycle for a one-time "case unlock" purchase.
* Kaspi payment through ApiPay, both by phone invoice and by QR.
* Webhook ingestion plus a polling reconciler, because a webhook can be lost.
* Entitlement checks on every route that exposes paid material.
* Free-tier truncation of a run's coverage and of what results reveal.
* Frontend paywall, payment modal, and unlock flow.

**Out of scope (phase 2, separate spec)**

* Organization subscriptions (`POST /subscriptions` on ApiPay).
* Refunds initiated from our UI. The provider supports them; we will operate
  refunds from the ApiPay dashboard until there is a reason not to.
* Invoices, VAT documents, fiscal receipts.
* Promo codes, discounts, referrals.

## 3. Product rules

A **case** is an `ApplicantProfileRow`. A purchase unlocks one case, permanently,
for the organization that owns it.

| Capability | Free | Case unlocked |
|---|---|---|
| Runs of the case | allowed, `candidate_limit = 5` | allowed, full `candidate_limit` |
| Shortlist rows | top 5: programme, institution, degree, score | all rows, all fields |
| `GET /runs/{id}/results/{result_id}` (evidence, claims, funding) | 402 | 200 |
| `GET /runs/{id}/claims`, `/conflicts`, `/questions` | 402 | 200 |
| `GET /runs/{id}/export.{fmt}` | 402 | 200 |
| `POST /runs/{id}/collect-documents` | 402 | 202 |

Two consequences we accept deliberately:

* **Paying does not retroactively widen a free run.** A free run really did fetch
  less. On payment we enqueue a fresh full run for the case, and the UI says so.
* **The free tier is cheap to serve.** Truncation is applied at run start, not
  only at read time, so an unpaid user cannot cost us a full crawl.

Price lives in configuration (`case_unlock_price_kzt`, default `4990`). The
amount is decided server-side from configuration; the client never sends a price.

## 4. Provider — ApiPay (Kaspi Pay)

Base URL `https://api.apipay.kz/api/v1`, authenticated with an `X-API-Key`
header. Endpoints this phase uses:

| Purpose | Call |
|---|---|
| Invoice by phone | `POST /invoices` — `amount` (whole tenge), `phone` (`8XXXXXXXXXX`), `description`, `external_order_id`; async, returns status `processing` |
| Invoice by QR | `POST /invoices/qr` — synchronous, returns status `pending` and a `qr_expires_at` a few minutes out |
| Status read | `GET /invoices/{id}` — `processing` / `pending` / `paid` / `cancelled` / `expired` / `partially_refunded` |
| Cancel | `POST /invoices/{id}/cancel` — pending or processing only; QR cancellation is not supported |
| Sandbox | `POST /invoices/{invoice}/simulate-status` |

Webhooks we consume: `invoice.status_changed` and `invoice.qr_scanned`, signed as
`X-Webhook-Signature: sha256=<hmac_sha256(raw_body, webhook_secret)>`.

Error shapes we must handle by name, not by guessing: `duplicate_idempotency_key`
(409), `tariff_inactive` (403), `kaspi_session_expired`, `kaspi_session_not_configured`,
`amount_must_be_whole_tenge`, `request_rate_limited` (429, honour `Retry-After`),
and 422 validation payloads of the form `{"message": ..., "errors": {field: [...]}}`.

**Verification obligation.** The table above was read from ApiPay's published
OpenAPI document. Before the adapter is considered done, the implementation must
re-read `openapi.yaml` from the published spec and reconcile field names, enum
values and the webhook body against it. Any divergence is a bug in our adapter,
and the contract test fixtures must be regenerated from the spec rather than from
our assumptions.

## 5. Data model

New file `backend/app/models/billing.py`, following the shape of `models/auth.py`.

**`orders`**

| Column | Notes |
|---|---|
| `id` | as elsewhere |
| `organization_id` | FK, indexed — the tenant that pays |
| `profile_id` | FK — the case being unlocked |
| `kind` | `case_unlock` |
| `amount_kzt` | integer tenge, server-decided |
| `status` | `created` / `pending` / `paid` / `cancelled` / `expired` / `failed` |
| `provider` | `apipay` / `fake` |
| `provider_invoice_id` | nullable until the provider answers |
| `external_order_id` | unique — our idempotency key to the provider |
| `method` | `phone` / `qr` |
| `phone_masked` | `8707***4455`, never the full number |
| `qr_payload`, `qr_expires_at` | QR only |
| `paid_at`, `failure_code` | |

At most one non-terminal order per `(profile_id, kind)`, so a double click cannot
open two invoices for the same case.

**`payment_events`** — append-only. `order_id`, `source` (`webhook` / `poll`),
`event_type`, `provider_status`, `signature_valid`, `received_at`, and a redacted
payload. This is the record we reach for when a customer says they paid.

**`entitlements`** — `organization_id`, `profile_id`, `kind` (`case_full`),
`source` (`purchase` / `manual` / later `subscription`), `order_id`, `granted_at`.
Unique on `(organization_id, profile_id, kind)`. **This table is the only thing
the rest of the application asks about.** Phase 2 inserts rows with
`kind='org_subscription'` and `profile_id` null; no route changes.

Migration: one Alembic revision on top of `c3a1f4e9b2d7`.

`research_runs` gains `access_tier` (`free` / `full`), recorded at start, so a run
carries the truth about how much it was allowed to fetch.

## 6. Backend structure

```
backend/app/payments/
  provider.py       Protocol: create_phone_invoice, create_qr_invoice,
                    get_invoice, cancel_invoice, verify_webhook
  apipay.py         ApiPayProvider — httpx, X-API-Key, retry, error mapping
  fake.py           FakeProvider — deterministic, drives every test
  errors.py         PaymentError hierarchy, mapped from provider error codes
  entitlements.py   pure: has_full_access(), free_view() projection
  service.py        create_order, apply_status (idempotent), grant, cancel
backend/app/api/routes_billing.py
backend/app/api/routes_webhooks.py
backend/app/jobs/payment_reconcile.py
```

Each file has one job. `entitlements.py` is pure apart from a single lookup, so
the truncation rules are unit-testable on their own.

## 7. HTTP surface

Authenticated, tenant-scoped, mounted like the existing routers:

* `GET  /billing/pricing` — amount, currency, and what unlocking includes.
* `GET  /billing/entitlements?profile_id=` — what this case already has.
* `POST /billing/orders` — `{profile_id, method, phone?}`. Verifies ownership via
  the existing `owned_profile`, refuses if an entitlement already exists, returns
  the order view.
* `GET  /billing/orders/{id}` — the frontend polls this.
* `POST /billing/orders/{id}/cancel`.

Unauthenticated but signed:

* `POST /webhooks/apipay` — raw body required for HMAC, body size capped, rate
  limited by the existing `FixedWindowLimiter`, unknown event types acknowledged
  with 200 and recorded, never acted on.

Paid routes answer `402` with `{"error": "payment_required", "profile_id": ..., "price_kzt": ...}`
so the frontend can raise the paywall without guessing.

## 8. Lifecycle and idempotency

```
POST /billing/orders
  -> order(created), external_order_id minted
  -> provider.create_*_invoice
  -> order(pending|processing), reconcile job enqueued
       |                                    |
   webhook invoice.status_changed      poll GET /invoices/{id}
       |                                    |
       +---------> apply_status() <---------+
                        |
                 paid -> entitlement granted -> full run enqueued
```

`apply_status(order, provider_status, source)` is the single writer. It is:

* **Idempotent** — the same terminal status twice grants once.
* **Order-insensitive** — a `paid` that arrives before `processing` wins;
  a non-terminal status never overwrites a terminal one.
* **Journalled** — every call appends a `payment_events` row, including calls
  that changed nothing and calls whose signature failed.

Reconciliation exists because webhook delivery is not guaranteed. It runs on the
existing durable queue with backoff and stops at a terminal status or at TTL
(QR: shortly after `qr_expires_at`; phone: 24h), marking the order `expired`.

## 9. Security

* The amount is read from configuration on the server. A client-supplied amount is
  ignored, and a test asserts that.
* Signature comparison uses `hmac.compare_digest`. An invalid signature is recorded
  and answered `401` without revealing why.
* The payer's phone is stored masked. `assert_no_pii`-style discipline applies: the
  phone never enters a log line, a URL, or an error message.
* `apipay_api_key` and `apipay_webhook_secret` are `SecretStr` and are excluded
  from any settings dump.
* Cross-tenant: unlocking is authorised through `owned_profile`, so an order for
  another organization's case 404s, consistent with the existing convention.
* Replay: a webhook replayed with a valid signature is idempotent by construction.

## 10. Configuration

Added to `Settings`:

| Setting | Default |
|---|---|
| `payments_enabled` | `False` |
| `payments_provider` | `fake` |
| `apipay_base_url` | `https://api.apipay.kz/api/v1` |
| `apipay_api_key` | `""` (SecretStr) |
| `apipay_webhook_secret` | `""` (SecretStr) |
| `apipay_timeout_seconds` | `20.0` |
| `case_unlock_price_kzt` | `4990` |
| `free_candidate_limit` | `5` |
| `free_shortlist_rows` | `5` |

With `payments_enabled=False` the product behaves exactly as it does today:
every case is fully accessible and no paywall is shown. That keeps the existing
test suite honest and makes the feature safe to merge before keys exist.

## 11. Frontend

* `api/client.ts` recognises `402` and surfaces `payment_required` to the store
  rather than throwing a generic error.
* `PaymentModal` — method choice (phone default, QR fallback), phone entry with
  `8XXXXXXXXXX` validation, then a status view polling `GET /billing/orders/{id}`
  every 2s with a cap; QR shows a countdown to `qr_expires_at` and offers a retry
  when it lapses.
* Locked affordances on `ShortlistScreen`, `ResultDetail`, `ExportScreen` and
  `DocumentsScreen` state plainly what unlocking adds.
* On success: refetch entitlements, then offer to start the full run.

## 12. How this is proven

No provider keys exist yet, so the evidence is local and contract-based.

* **Unit** — HMAC accept/reject/tamper; provider status to order status mapping;
  `apply_status` idempotence and out-of-order behaviour; the free-tier projection.
* **Contract** — `FakeProvider` reproduces ApiPay's documented success and error
  responses, including `duplicate_idempotency_key`, `tariff_inactive`, 422
  validation and 429 with `Retry-After`. Fixtures are derived from the published
  OpenAPI document, not from prose.
* **API** — 402 on each paid route; webhook grants access; replayed webhook grants
  once; out-of-order events; reconciler recovers a lost webhook; an order for
  another tenant's case 404s; `payments_enabled=False` restores today's behaviour.
* **Frontend** — paywall states, polling, QR expiry, and the post-payment prompt.

Gates that must stay green: `pytest` (553 passing at baseline), `ruff`, `mypy`,
frontend unit tests, `tsc`, ESLint.

## 13. Needs the user

* An ApiPay account with Kaspi Pay connected, then `APIPAY_API_KEY`,
  `APIPAY_WEBHOOK_SECRET`, and the webhook URL registered in their dashboard.
* Confirmation of the price before launch; `4990` is a placeholder default.
* A public HTTPS URL for the webhook endpoint, which depends on the deployment
  that `RELEASE_CHECKLIST.md` already lists as needing the user.
