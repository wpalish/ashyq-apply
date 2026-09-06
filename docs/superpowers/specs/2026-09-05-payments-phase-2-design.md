# Payments, phase 2 — school subscriptions with a case quota

Status: approved for planning · Date: 2026-09-05 · Branch: `claude/payments-phase-2`
Builds on: [phase 1](2026-09-04-payments-phase-1-design.md)

## 1. Why

Schools and admissions consultancies do not buy one case at a time. They sign a
contract, pay an invoice by bank transfer, and expect a block of cases for a
term. Phase 1 sells one case to one person; this sells a term to an
organization.

Nothing here touches ApiPay. Money arrives by bank transfer against an invoice
raised outside the product, so the product's job is only to record what was
sold and to spend it correctly.

## 2. What phase 1 assumed, and what this overturns

Phase 1 reserved a shape for this: an `entitlements` row with
`kind='org_subscription'` and a null `profile_id`, meaning *the whole
organization is unlocked*. `has_full_access` already honours it, and a partial
index `uq_entitlements_org` guards it.

**A quota makes that wrong.** A subscription no longer grants access; it grants
the *right to spend*. So phase 2 removes the `ORG_SUBSCRIPTION` branch from
`has_full_access`, drops `uq_entitlements_org`, and retires the enum value.
`entitlements` goes back to meaning exactly one thing: this case is open.

That is a guess made before the model was chosen. Removing it is cheaper than
leaving it in place to be misread later.

## 3. Product rules

A subscription is **a quota of cases for a term**, sold to one organization.

* Opening a case under a subscription spends **one** unit, once. Re-running or
  re-reading that case spends nothing more.
* When the quota runs out, or the term ends, the organization falls back to
  phase 1: the same `402`, the same 4990 ₸ per case. Nobody is ever stuck
  mid-work.
* **Subscriptions queue rather than expire into nothing.** A school that renews
  before its current term ends holds two: the new one starts the moment the old
  one is exhausted by usage *or* reaches its end date, whichever comes first.
  Unused cases are therefore never destroyed by an early renewal.

Because a queued subscription's start is not known when it is sold, a
subscription carries a **duration**, not a start date. `starts_at` is written
when it activates; `ends_at` is `starts_at + duration`.

A subscription's life: `pending` → `active` → `exhausted` or `expired`.
`cancelled` is reachable from `pending` or `active` and is the only manual exit.

## 4. Data model

**`subscriptions`** — new table.

| Column | Notes |
|---|---|
| `id`, `created_at`, `updated_at` | as elsewhere |
| `organization_id` | FK, indexed |
| `case_quota` | integer, or null for an unlimited contract |
| `duration_days` | the term length, applied when it activates |
| `starts_at`, `ends_at` | null until activation |
| `status` | `pending` / `active` / `exhausted` / `expired` / `cancelled` |
| `invoice_note` | the contract or invoice number, so a row can be explained a year later |

**`entitlements`** gains `subscription_id` (nullable, indexed). A `case_full`
row with `source='subscription'` and a `subscription_id` **is** one spent unit.

There is deliberately no `used_count` column. A counter can drift from the rows
it claims to count, and the day it does is the day a customer disputes it.
Remaining is `case_quota - COUNT(entitlements WHERE subscription_id = …)`.

Migration on top of `d4b2c8f17a90`: create `subscriptions`, add
`entitlements.subscription_id`, drop `uq_entitlements_org`.

## 5. Logic

New module `backend/app/payments/subscriptions.py`:

* `current_subscription(session, organization_id) -> Subscription | None` —
  **pure read.** The active one, if it is neither expired nor exhausted.
* `quota_remaining(session, subscription) -> int | None` — null means unlimited.
* `queued_subscriptions(session, organization_id) -> list[Subscription]` — what
  is waiting, for display.
* `consume_for_case(session, *, organization_id, profile_id) -> ConsumeResult` —
  **the only place a unit is spent.**

`consume_for_case` runs one transaction, in this order:

1. Lock the organization's non-terminal subscriptions (`SELECT … FOR UPDATE`),
   so two counsellors clicking at once cannot both take the last unit.
2. Retire the active one if its term has ended (`expired`) or its quota is gone
   (`exhausted`).
3. Activate the oldest `pending` one if there is now no active subscription:
   stamp `starts_at = now`, `ends_at = now + duration_days`.
4. If a usable subscription remains, grant a `case_full` entitlement carrying
   its `subscription_id` and return it. Otherwise return "no quota".

Two callers, one function:

* `start_run` — a school with quota gets a full run without being asked.
* `POST /api/billing/unlock-from-subscription` — the paywall's button, for a
  case whose free run already happened.

Steps 2 and 3 are writes, which is why they live in the writer and not in
`current_subscription`. A read must never spend money.

## 6. Granting a subscription

`backend/scripts/grant_subscription.py`, following the argparse style already
used by `seed_demo.py` and `scripts/canary_discovery.py`:

```bash
python scripts/grant_subscription.py --org <slug> --cases 50 --days 365 \
    --invoice "Договор 14/26"
python scripts/grant_subscription.py --list
python scripts/grant_subscription.py --list --org <slug>
python scripts/grant_subscription.py --cancel <subscription-id>
```

A grant is **always** created `pending`, even when the organization has nothing
active — activation belongs to `consume_for_case` and nowhere else, so there is
one activation path rather than two that must agree. The practical effect is
that a school's first subscription activates the moment its first case is
opened, which is also when its term should start counting.

No new network entry point, no new privileged role. Every action writes an
`AuditEvent`.

Unlimited contracts: `--cases` omitted means `case_quota = NULL`.

## 7. HTTP surface

* `POST /api/billing/unlock-from-subscription` — `{profile_id}`. Verifies
  ownership through `owned_profile`, calls `consume_for_case`, returns the
  entitlement view. `409` when no quota remains, so the frontend can fall back
  to the price.
* `GET /api/billing/entitlements` gains `subscription_cases_left: int | null`
  and `subscription_queued: int`.
* The `402` body gains `subscription_cases_left`, so the paywall knows whether
  to offer a button or a price without a second call.

## 8. Frontend

`PaywallNotice` gets one branch. With cases left it offers **«Открыть из
подписки (осталось N)»** and calls the new endpoint; with none it shows today's
4990 ₸ screen unchanged. The header shows the remaining count for an
organization that has a subscription, and names a queued one if present.

## 9. How this is proven

* **Unit** — remaining against a quota; an expired term; an exhausted quota; an
  unlimited contract; a cancelled subscription; the queue advancing on
  exhaustion and on expiry.
* **API** — starting a run spends exactly one unit; a second run on the same
  case spends none; at zero the gated routes answer `402` carrying the price;
  another organization cannot spend our quota; `unlock-from-subscription`
  answers `409` at zero.
* **Concurrency, on real PostgreSQL** — two simultaneous consumptions of the
  last unit produce one grant and one refusal, never two grants.
* **CLI** — grant, list, cancel, and that a grant lands `pending`.

Gates unchanged: `pytest`, `ruff`, `mypy`, frontend tests, `tsc`, ESLint, build.

## 10. Needs the user

* The subscription price list and term — the product only records what was
  sold; it never quotes a school.
* A decision on whether an exhausted-but-unexpired subscription should still
  show in the header as history. Assumed yes, as "0 из 50 осталось".
