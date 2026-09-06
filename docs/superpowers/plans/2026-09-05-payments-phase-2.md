# Payments Phase 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A school pays an invoice, receives a quota of cases for a term, and spends exactly one unit per case opened — falling back to the phase 1 price when the quota runs out.

**Architecture:** A `subscriptions` table holds what was sold. One function, `consume_for_case`, is the only thing that spends a unit; it also retires an exhausted or expired subscription and activates the next queued one, under a row lock. Reads never spend. Remaining is counted from the entitlement rows themselves, never from a stored counter.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, pytest, PostgreSQL 16 (SQLite for local), React 18 + TypeScript, Vitest.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-05-payments-phase-2-design.md`. Read it before Task 1.
- Branch is `claude/payments-phase-2`, which already contains all of phase 1.
- Settings use `env_prefix="UNIMATCH_"`. Payments stay off by default (`payments_enabled=False`), and with them off nothing in this plan changes behaviour.
- `SELECT … FOR UPDATE` is PostgreSQL-only. Guard it with a dialect check, as `app/db.py` already does for its SQLite pragmas.
- Timestamps are aware UTC via `app.models.base.utcnow`; read back through `ensure_utc` before comparing.
- Every task ends green on `pytest -q`, `ruff check app tests`, `mypy app tests` — run from `backend/` with `.venv\Scripts\python.exe` on Windows. The plan writes `python` for brevity.
- Frontend gates: `npx tsc --noEmit`, `npm run lint`, `npm run test`, `npm run build`, run from `frontend/`.
- Commit at the end of every task.

---

### Task 1: The subscriptions table, and retiring phase 1's guess

**Files:**
- Create: `backend/app/models/subscription.py`
- Modify: `backend/app/models/billing.py` (add `subscription_id` to `Entitlement`, drop the `uq_entitlements_org` index and the `ORG_SUBSCRIPTION` enum member)
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/payments/entitlements.py` (remove the org-wide branch)
- Modify: `backend/tests/test_entitlements.py` (the org-wide test asserts behaviour that is being removed)
- Create: `backend/migrations/versions/e7c1a4d90b52_subscriptions.py`
- Test: `backend/tests/test_subscription_models.py`

**Interfaces:**
- Produces: `Subscription` model; `SubscriptionStatus` enum (`PENDING`, `ACTIVE`, `EXHAUSTED`, `EXPIRED`, `CANCELLED`); `TERMINAL_SUBSCRIPTION_STATUSES`; `Entitlement.subscription_id: str | None`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_subscription_models.py`:

```python
"""What a sold subscription looks like in the database."""

from __future__ import annotations

import pytest

from app.models.subscription import (
    TERMINAL_SUBSCRIPTION_STATUSES,
    Subscription,
    SubscriptionStatus,
)


@pytest.fixture
def org(pg_session):
    from app.models import Organization

    row = Organization(name="Test school", slug="test-school")
    pg_session.add(row)
    pg_session.flush()
    return row


def test_a_grant_starts_pending_and_undated(pg_session, org) -> None:
    """Activation belongs to consume_for_case, so a grant has no dates yet."""
    sub = Subscription(
        organization_id=org.id, case_quota=50, duration_days=365, invoice_note="Contract 14/26"
    )
    pg_session.add(sub)
    pg_session.flush()
    assert sub.status == SubscriptionStatus.PENDING.value
    assert sub.starts_at is None
    assert sub.ends_at is None


def test_an_unlimited_contract_has_no_quota(pg_session, org) -> None:
    sub = Subscription(organization_id=org.id, case_quota=None, duration_days=365)
    pg_session.add(sub)
    pg_session.flush()
    assert sub.case_quota is None


def test_exhausted_expired_and_cancelled_are_terminal() -> None:
    assert TERMINAL_SUBSCRIPTION_STATUSES == frozenset(
        {
            SubscriptionStatus.EXHAUSTED.value,
            SubscriptionStatus.EXPIRED.value,
            SubscriptionStatus.CANCELLED.value,
        }
    )


def test_an_entitlement_can_name_the_subscription_that_paid_for_it(pg_session, org) -> None:
    from app.models import ApplicantProfileRow
    from app.models.billing import Entitlement, EntitlementKind, EntitlementSource

    case = ApplicantProfileRow(organization_id=org.id, payload={})
    sub = Subscription(organization_id=org.id, case_quota=50, duration_days=365)
    pg_session.add_all([case, sub])
    pg_session.flush()

    pg_session.add(
        Entitlement(
            organization_id=org.id,
            profile_id=case.id,
            kind=EntitlementKind.CASE_FULL.value,
            source=EntitlementSource.SUBSCRIPTION.value,
            subscription_id=sub.id,
        )
    )
    pg_session.flush()
    spent = (
        pg_session.query(Entitlement).filter(Entitlement.subscription_id == sub.id).count()
    )
    assert spent == 1


def test_the_org_wide_entitlement_kind_is_gone() -> None:
    """A quota grants the right to spend, not blanket access."""
    from app.models.billing import EntitlementKind

    assert not hasattr(EntitlementKind, "ORG_SUBSCRIPTION")
```

- [ ] **Step 2: Run it and watch it fail**

Run: `python -m pytest tests/test_subscription_models.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.models.subscription'`.

- [ ] **Step 3: Write the model**

Create `backend/app/models/subscription.py`:

```python
"""What a school bought, and how much of it is left.

Deliberately no ``used_count``: remaining is counted from the entitlement rows
that claim to have spent it. A counter can drift from those rows, and the day
it drifts is the day a customer disputes the bill.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TimestampedBase


class SubscriptionStatus(str, Enum):
    #: Sold, not yet started. Every grant begins here.
    PENDING = "pending"
    ACTIVE = "active"
    #: The quota ran out.
    EXHAUSTED = "exhausted"
    #: The term ended, whatever was left unspent.
    EXPIRED = "expired"
    CANCELLED = "cancelled"


TERMINAL_SUBSCRIPTION_STATUSES = frozenset(
    {
        SubscriptionStatus.EXHAUSTED.value,
        SubscriptionStatus.EXPIRED.value,
        SubscriptionStatus.CANCELLED.value,
    }
)


class Subscription(TimestampedBase):
    __tablename__ = "subscriptions"
    __table_args__ = (Index("ix_subscriptions_org_status", "organization_id", "status"),)

    organization_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    #: Cases included. Null means an unlimited contract.
    case_quota: Mapped[int | None] = mapped_column(Integer, nullable=True)
    #: The term, applied when the subscription activates. A queued renewal has
    #: no start date until the one before it finishes.
    duration_days: Mapped[int] = mapped_column(Integer)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default=SubscriptionStatus.PENDING.value, index=True
    )
    #: The contract or invoice this row corresponds to, so it can be explained
    #: a year later.
    invoice_note: Mapped[str] = mapped_column(String(200), default="")
```

- [ ] **Step 4: Retire phase 1's org-wide guess**

In `backend/app/models/billing.py`, delete the `ORG_SUBSCRIPTION` member from `EntitlementKind`, delete the `uq_entitlements_org` `Index(...)` from `Entitlement.__table_args__`, and add the column:

```python
    #: Which subscription paid for this case, when one did. Counting these rows
    #: is how a subscription's remaining quota is known.
    subscription_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
```

In `backend/app/payments/entitlements.py`, replace the `or_(...)` in `has_full_access` with the single remaining rule and drop the now-unused imports (`or_`, `EntitlementKind` stays for `CASE_FULL`):

```python
    found = session.scalar(
        select(Entitlement.id).where(
            Entitlement.organization_id == organization_id,
            Entitlement.kind == EntitlementKind.CASE_FULL.value,
            Entitlement.profile_id == profile_id,
        )
    )
    return found is not None
```

In `backend/app/models/__init__.py`, remove `EntitlementKind`'s org member from nothing (it is a member, not an export), and add:

```python
from app.models.subscription import (
    TERMINAL_SUBSCRIPTION_STATUSES,
    Subscription,
    SubscriptionStatus,
)
```

adding `"Subscription"`, `"SubscriptionStatus"` and `"TERMINAL_SUBSCRIPTION_STATUSES"` to `__all__`.

In `backend/tests/test_entitlements.py`, delete
`test_an_organization_wide_entitlement_covers_every_case` — it asserts exactly
the behaviour being removed — and replace it with:

```python
def test_a_subscription_no_longer_grants_blanket_access(pg_session, tenant) -> None:
    """Phase 2 turned the subscription into a right to spend, not access."""
    from app.models.subscription import Subscription

    pg_session.add(
        Subscription(organization_id=tenant["organization_id"], case_quota=50, duration_days=365)
    )
    pg_session.flush()
    assert has_full_access(pg_session, tenant["organization_id"], tenant["profile_id"]) is False
```

Remove the now-unused `EntitlementKind` import from that test module if ruff flags it.

- [ ] **Step 5: Write the migration**

Create `backend/migrations/versions/e7c1a4d90b52_subscriptions.py`:

```python
"""School subscriptions, and the retirement of the org-wide entitlement.

Revision ID: e7c1a4d90b52
Revises: d4b2c8f17a90
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "e7c1a4d90b52"
down_revision = "d4b2c8f17a90"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "organization_id",
            sa.String(32),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("case_quota", sa.Integer(), nullable=True),
        sa.Column("duration_days", sa.Integer(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("invoice_note", sa.String(200), nullable=False),
    )
    op.create_index("ix_subscriptions_organization_id", "subscriptions", ["organization_id"])
    op.create_index("ix_subscriptions_status", "subscriptions", ["status"])
    op.create_index(
        "ix_subscriptions_org_status", "subscriptions", ["organization_id", "status"]
    )

    op.add_column("entitlements", sa.Column("subscription_id", sa.String(32), nullable=True))
    op.create_index("ix_entitlements_subscription_id", "entitlements", ["subscription_id"])

    # Phase 1 reserved an org-wide entitlement for a subscription that granted
    # blanket access. A quota grants the right to spend instead, so the shape
    # and its guard come out rather than sit there to be misread.
    op.drop_index("uq_entitlements_org", table_name="entitlements")


def downgrade() -> None:
    op.create_index(
        "uq_entitlements_org",
        "entitlements",
        ["organization_id", "kind"],
        unique=True,
        postgresql_where=sa.text("profile_id IS NULL"),
        sqlite_where=sa.text("profile_id IS NULL"),
    )
    op.drop_index("ix_entitlements_subscription_id", table_name="entitlements")
    op.drop_column("entitlements", "subscription_id")
    op.drop_table("subscriptions")
```

Before writing it, confirm the parent: `python -c "from app.db import head_revision; print(head_revision())"` must print `d4b2c8f17a90`.

- [ ] **Step 6: Run the tests and watch them pass**

Run: `python -m pytest tests/test_subscription_models.py tests/test_entitlements.py -q`
Expected: PASS, 5 + 10 tests.

- [ ] **Step 7: Full gates**

Run: `python -m pytest -q && ruff check app tests && mypy app tests`
Expected: all clean.

- [ ] **Step 8: Commit**

```bash
git add backend/app/models/subscription.py backend/app/models/billing.py backend/app/models/__init__.py backend/app/payments/entitlements.py backend/tests/test_entitlements.py backend/migrations/versions/e7c1a4d90b52_subscriptions.py backend/tests/test_subscription_models.py
git commit -m "feat(subscriptions): what a school bought, and the end of blanket access"
```

---

### Task 2: Reading a subscription without spending it

**Files:**
- Create: `backend/app/payments/subscriptions.py`
- Test: `backend/tests/test_subscription_reads.py`

**Interfaces:**
- Consumes: `Subscription`, `SubscriptionStatus` (Task 1).
- Produces:
  - `is_expired(subscription, now=None) -> bool`
  - `spent(session, subscription) -> int`
  - `quota_remaining(session, subscription) -> int | None` (None = unlimited)
  - `is_usable(session, subscription) -> bool` (active, unexpired, quota left)
  - `current_subscription(session, organization_id) -> Subscription | None`
  - `queued_subscriptions(session, organization_id) -> list[Subscription]`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_subscription_reads.py`:

```python
"""Reads never spend, and never change a row."""

from __future__ import annotations

from datetime import timedelta

import pytest

from app.models.base import utcnow
from app.models.subscription import Subscription, SubscriptionStatus
from app.payments.subscriptions import (
    current_subscription,
    is_expired,
    quota_remaining,
    queued_subscriptions,
    spent,
)


@pytest.fixture
def org(pg_session):
    from app.models import Organization

    row = Organization(name="Test school", slug="test-school")
    pg_session.add(row)
    pg_session.flush()
    return row


def _sub(session, org, **overrides) -> Subscription:
    fields = {
        "organization_id": org.id,
        "case_quota": 50,
        "duration_days": 365,
        "status": SubscriptionStatus.ACTIVE.value,
        "starts_at": utcnow() - timedelta(days=1),
        "ends_at": utcnow() + timedelta(days=364),
    }
    fields.update(overrides)
    row = Subscription(**fields)
    session.add(row)
    session.flush()
    return row


def _spend(session, org, sub, n: int) -> None:
    from app.models import ApplicantProfileRow
    from app.models.billing import Entitlement, EntitlementKind, EntitlementSource

    for _ in range(n):
        case = ApplicantProfileRow(organization_id=org.id, payload={})
        session.add(case)
        session.flush()
        session.add(
            Entitlement(
                organization_id=org.id,
                profile_id=case.id,
                kind=EntitlementKind.CASE_FULL.value,
                source=EntitlementSource.SUBSCRIPTION.value,
                subscription_id=sub.id,
            )
        )
    session.flush()


def test_a_fresh_subscription_has_its_whole_quota(pg_session, org) -> None:
    sub = _sub(pg_session, org)
    assert spent(pg_session, sub) == 0
    assert quota_remaining(pg_session, sub) == 50


def test_remaining_counts_the_rows_that_spent_it(pg_session, org) -> None:
    sub = _sub(pg_session, org)
    _spend(pg_session, org, sub, 3)
    assert spent(pg_session, sub) == 3
    assert quota_remaining(pg_session, sub) == 47


def test_an_unlimited_contract_never_runs_out(pg_session, org) -> None:
    sub = _sub(pg_session, org, case_quota=None)
    _spend(pg_session, org, sub, 100)
    assert quota_remaining(pg_session, sub) is None


def test_a_term_that_has_passed_is_expired(pg_session, org) -> None:
    sub = _sub(pg_session, org, ends_at=utcnow() - timedelta(days=1))
    assert is_expired(sub) is True


def test_a_pending_subscription_is_not_expired(pg_session, org) -> None:
    """It has no end date yet, because it has not started."""
    sub = _sub(
        pg_session, org, status=SubscriptionStatus.PENDING.value, starts_at=None, ends_at=None
    )
    assert is_expired(sub) is False


def test_the_current_subscription_is_the_active_usable_one(pg_session, org) -> None:
    sub = _sub(pg_session, org)
    assert current_subscription(pg_session, org.id) is not None
    assert current_subscription(pg_session, org.id).id == sub.id


def test_an_exhausted_subscription_is_not_current(pg_session, org) -> None:
    sub = _sub(pg_session, org, case_quota=2)
    _spend(pg_session, org, sub, 2)
    assert current_subscription(pg_session, org.id) is None


def test_an_expired_subscription_is_not_current(pg_session, org) -> None:
    _sub(pg_session, org, ends_at=utcnow() - timedelta(days=1))
    assert current_subscription(pg_session, org.id) is None


def test_a_cancelled_subscription_is_not_current(pg_session, org) -> None:
    _sub(pg_session, org, status=SubscriptionStatus.CANCELLED.value)
    assert current_subscription(pg_session, org.id) is None


def test_an_organization_without_one_has_none(pg_session, org) -> None:
    assert current_subscription(pg_session, org.id) is None


def test_queued_subscriptions_are_the_pending_ones_oldest_first(pg_session, org) -> None:
    _sub(pg_session, org)
    first = _sub(
        pg_session, org, status=SubscriptionStatus.PENDING.value, starts_at=None, ends_at=None
    )
    second = _sub(
        pg_session, org, status=SubscriptionStatus.PENDING.value, starts_at=None, ends_at=None
    )
    queued = queued_subscriptions(pg_session, org.id)
    assert [q.id for q in queued] == [first.id, second.id]


def test_reading_does_not_change_a_subscription(pg_session, org) -> None:
    """The read path must never retire or activate anything."""
    sub = _sub(pg_session, org, ends_at=utcnow() - timedelta(days=1))
    current_subscription(pg_session, org.id)
    pg_session.refresh(sub)
    assert sub.status == SubscriptionStatus.ACTIVE.value
```

- [ ] **Step 2: Run it and watch it fail**

Run: `python -m pytest tests/test_subscription_reads.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.payments.subscriptions'`.

- [ ] **Step 3: Write the reads**

Create `backend/app/payments/subscriptions.py`:

```python
"""Subscriptions: what is left, and which one is in force.

Everything here is a read. Retiring an exhausted subscription and starting the
next one are writes, and they live in ``consume_for_case`` — a GET must never
spend a customer's quota.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.base import ensure_utc, utcnow
from app.models.billing import Entitlement
from app.models.subscription import Subscription, SubscriptionStatus


def is_expired(subscription: Subscription, now: datetime | None = None) -> bool:
    """True when the term has passed. A subscription that never started has not."""
    ends_at = ensure_utc(subscription.ends_at)
    if ends_at is None:
        return False
    return (now or utcnow()) > ends_at


def spent(session: Session, subscription: Subscription) -> int:
    """How many cases this subscription has paid for, counted from the rows.

    Counted, never stored. A ``used_count`` column can drift from the rows it
    claims to describe, and the day it drifts is a dispute with a customer.
    """
    return (
        session.query(Entitlement)
        .filter(Entitlement.subscription_id == subscription.id)
        .count()
    )


def quota_remaining(session: Session, subscription: Subscription) -> int | None:
    """Cases left, or None for an unlimited contract."""
    if subscription.case_quota is None:
        return None
    return max(0, subscription.case_quota - spent(session, subscription))


def is_usable(session: Session, subscription: Subscription) -> bool:
    if subscription.status != SubscriptionStatus.ACTIVE.value:
        return False
    if is_expired(subscription):
        return False
    remaining = quota_remaining(session, subscription)
    return remaining is None or remaining > 0


def current_subscription(session: Session, organization_id: str) -> Subscription | None:
    """The active subscription, if it can still be spent. Never mutates."""
    active = session.scalar(
        select(Subscription).where(
            Subscription.organization_id == organization_id,
            Subscription.status == SubscriptionStatus.ACTIVE.value,
        )
    )
    if active is None or not is_usable(session, active):
        return None
    return active


def queued_subscriptions(session: Session, organization_id: str) -> list[Subscription]:
    """Bought but not started, oldest first — the order they will be used in."""
    return list(
        session.scalars(
            select(Subscription)
            .where(
                Subscription.organization_id == organization_id,
                Subscription.status == SubscriptionStatus.PENDING.value,
            )
            .order_by(Subscription.created_at, Subscription.id)
        )
    )
```

- [ ] **Step 4: Run the tests and watch them pass**

Run: `python -m pytest tests/test_subscription_reads.py -q`
Expected: PASS, 12 tests.

- [ ] **Step 5: Full gates**

Run: `python -m pytest -q && ruff check app tests && mypy app tests`
Expected: all clean.

- [ ] **Step 6: Commit**

```bash
git add backend/app/payments/subscriptions.py backend/tests/test_subscription_reads.py
git commit -m "feat(subscriptions): reads that never spend"
```

---

### Task 3: Spending a unit, and advancing the queue

**Files:**
- Modify: `backend/app/payments/subscriptions.py` (add the writer)
- Test: `backend/tests/test_subscription_consume.py`

**Interfaces:**
- Consumes: everything from Task 2; `grant_case_access` from `app.payments.entitlements`.
- Produces:
  - `@dataclass(frozen=True) ConsumeResult: granted: bool; reason: str; subscription_id: str | None; remaining: int | None`
  - `consume_for_case(session, *, organization_id: str, profile_id: str) -> ConsumeResult`
  - `reason` is one of `"granted"`, `"already_entitled"`, `"no_subscription"`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_subscription_consume.py`:

```python
"""Spending a unit: once per case, and never past zero."""

from __future__ import annotations

from datetime import timedelta

import pytest

from app.models.base import utcnow
from app.models.billing import Entitlement
from app.models.subscription import Subscription, SubscriptionStatus
from app.payments.entitlements import has_full_access
from app.payments.subscriptions import consume_for_case, quota_remaining


@pytest.fixture(autouse=True)
def payments_on(monkeypatch):
    from app.config import get_settings

    monkeypatch.setenv("UNIMATCH_PAYMENTS_ENABLED", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def org(pg_session):
    from app.models import Organization

    row = Organization(name="Test school", slug="test-school")
    pg_session.add(row)
    pg_session.flush()
    return row


def _case(session, org) -> str:
    from app.models import ApplicantProfileRow

    row = ApplicantProfileRow(organization_id=org.id, payload={})
    session.add(row)
    session.flush()
    return row.id


def _sub(session, org, **overrides) -> Subscription:
    fields = {
        "organization_id": org.id,
        "case_quota": 3,
        "duration_days": 365,
        "status": SubscriptionStatus.PENDING.value,
    }
    fields.update(overrides)
    row = Subscription(**fields)
    session.add(row)
    session.flush()
    return row


def test_without_a_subscription_nothing_is_spent(pg_session, org) -> None:
    result = consume_for_case(
        pg_session, organization_id=org.id, profile_id=_case(pg_session, org)
    )
    assert result.granted is False
    assert result.reason == "no_subscription"


def test_the_first_use_activates_a_pending_subscription(pg_session, org) -> None:
    sub = _sub(pg_session, org)
    result = consume_for_case(
        pg_session, organization_id=org.id, profile_id=_case(pg_session, org)
    )
    pg_session.flush()
    pg_session.refresh(sub)

    assert result.granted is True
    assert sub.status == SubscriptionStatus.ACTIVE.value
    assert sub.starts_at is not None
    assert sub.ends_at is not None
    assert (sub.ends_at - sub.starts_at).days == 365


def test_spending_opens_the_case(pg_session, org) -> None:
    _sub(pg_session, org)
    case_id = _case(pg_session, org)
    consume_for_case(pg_session, organization_id=org.id, profile_id=case_id)
    pg_session.flush()
    assert has_full_access(pg_session, org.id, case_id) is True


def test_the_same_case_is_never_charged_twice(pg_session, org) -> None:
    sub = _sub(pg_session, org)
    case_id = _case(pg_session, org)
    first = consume_for_case(pg_session, organization_id=org.id, profile_id=case_id)
    pg_session.flush()
    second = consume_for_case(pg_session, organization_id=org.id, profile_id=case_id)
    pg_session.flush()

    assert first.granted is True
    assert second.granted is True
    assert second.reason == "already_entitled"
    pg_session.refresh(sub)
    assert quota_remaining(pg_session, sub) == 2


def test_the_quota_runs_out_and_stops(pg_session, org) -> None:
    sub = _sub(pg_session, org, case_quota=2)
    for _ in range(2):
        assert consume_for_case(
            pg_session, organization_id=org.id, profile_id=_case(pg_session, org)
        ).granted
        pg_session.flush()

    last = consume_for_case(
        pg_session, organization_id=org.id, profile_id=_case(pg_session, org)
    )
    pg_session.flush()
    assert last.granted is False
    assert last.reason == "no_subscription"
    pg_session.refresh(sub)
    assert sub.status == SubscriptionStatus.EXHAUSTED.value


def test_an_early_renewal_takes_over_when_the_first_runs_out(pg_session, org) -> None:
    """The point of the queue: unspent cases are not destroyed by renewing."""
    first = _sub(pg_session, org, case_quota=1)
    renewal = _sub(pg_session, org, case_quota=5)

    consume_for_case(pg_session, organization_id=org.id, profile_id=_case(pg_session, org))
    pg_session.flush()
    consume_for_case(pg_session, organization_id=org.id, profile_id=_case(pg_session, org))
    pg_session.flush()

    pg_session.refresh(first)
    pg_session.refresh(renewal)
    assert first.status == SubscriptionStatus.EXHAUSTED.value
    assert renewal.status == SubscriptionStatus.ACTIVE.value
    assert quota_remaining(pg_session, renewal) == 4


def test_an_expired_term_hands_over_to_the_renewal(pg_session, org) -> None:
    expiring = _sub(
        pg_session,
        org,
        case_quota=10,
        status=SubscriptionStatus.ACTIVE.value,
        starts_at=utcnow() - timedelta(days=400),
        ends_at=utcnow() - timedelta(days=1),
    )
    renewal = _sub(pg_session, org, case_quota=5)

    result = consume_for_case(
        pg_session, organization_id=org.id, profile_id=_case(pg_session, org)
    )
    pg_session.flush()

    pg_session.refresh(expiring)
    pg_session.refresh(renewal)
    assert result.granted is True
    assert expiring.status == SubscriptionStatus.EXPIRED.value
    assert renewal.status == SubscriptionStatus.ACTIVE.value


def test_an_unlimited_contract_keeps_granting(pg_session, org) -> None:
    _sub(pg_session, org, case_quota=None)
    for _ in range(20):
        assert consume_for_case(
            pg_session, organization_id=org.id, profile_id=_case(pg_session, org)
        ).granted
        pg_session.flush()


def test_a_cancelled_subscription_is_never_spent(pg_session, org) -> None:
    _sub(pg_session, org, status=SubscriptionStatus.CANCELLED.value)
    result = consume_for_case(
        pg_session, organization_id=org.id, profile_id=_case(pg_session, org)
    )
    assert result.granted is False


def test_another_organization_cannot_spend_our_quota(pg_session, org) -> None:
    from app.models import ApplicantProfileRow, Organization

    _sub(pg_session, org, case_quota=5)
    other = Organization(name="Other", slug="other")
    pg_session.add(other)
    pg_session.flush()
    their_case = ApplicantProfileRow(organization_id=other.id, payload={})
    pg_session.add(their_case)
    pg_session.flush()

    result = consume_for_case(
        pg_session, organization_id=other.id, profile_id=their_case.id
    )
    assert result.granted is False
    assert pg_session.query(Entitlement).count() == 0
```

- [ ] **Step 2: Run it and watch it fail**

Run: `python -m pytest tests/test_subscription_consume.py -q`
Expected: FAIL — `ImportError: cannot import name 'consume_for_case'`.

- [ ] **Step 3: Write the writer**

Append to `backend/app/payments/subscriptions.py`:

```python
@dataclass(frozen=True)
class ConsumeResult:
    granted: bool
    #: "granted", "already_entitled" or "no_subscription".
    reason: str
    subscription_id: str | None = None
    remaining: int | None = None


def consume_for_case(
    session: Session, *, organization_id: str, profile_id: str
) -> ConsumeResult:
    """Spend one unit of the organization's quota on this case.

    The only place a unit is spent, and the only place a subscription changes
    state. It runs in this order:

      1. lock the organization's non-terminal subscriptions, so two counsellors
         clicking at once cannot both take the last unit;
      2. retire the active one if its term ended or its quota is gone;
      3. start the oldest queued one if nothing is active;
      4. grant the case, carrying the subscription that paid for it.
    """
    if has_full_access(session, organization_id, profile_id):
        # Already open. Re-running or re-reading a case costs nothing more.
        return ConsumeResult(granted=True, reason="already_entitled")

    subscription = _claim_usable_subscription(session, organization_id)
    if subscription is None:
        return ConsumeResult(granted=False, reason="no_subscription")

    grant_case_access(
        session,
        organization_id=organization_id,
        profile_id=profile_id,
        order_id=None,
        source=EntitlementSource.SUBSCRIPTION.value,
    )
    session.flush()

    remaining = quota_remaining(session, subscription)
    if remaining == 0:
        subscription.status = SubscriptionStatus.EXHAUSTED.value

    return ConsumeResult(
        granted=True,
        reason="granted",
        subscription_id=subscription.id,
        remaining=remaining,
    )


def _claim_usable_subscription(session: Session, organization_id: str) -> Subscription | None:
    """Retire what is finished, start what is next, return what can be spent."""
    query = select(Subscription).where(
        Subscription.organization_id == organization_id,
        Subscription.status.in_(
            (SubscriptionStatus.ACTIVE.value, SubscriptionStatus.PENDING.value)
        ),
    )
    # Row locking is PostgreSQL's; SQLite serialises writers anyway.
    if session.bind is not None and session.bind.dialect.name == "postgresql":
        query = query.with_for_update()
    rows = list(session.scalars(query))

    active = next(
        (r for r in rows if r.status == SubscriptionStatus.ACTIVE.value), None
    )
    if active is not None:
        if is_expired(active):
            active.status = SubscriptionStatus.EXPIRED.value
            active = None
        elif not is_usable(session, active):
            active.status = SubscriptionStatus.EXHAUSTED.value
            active = None

    if active is not None:
        return active

    pending = sorted(
        (r for r in rows if r.status == SubscriptionStatus.PENDING.value),
        key=lambda r: (r.created_at, r.id),
    )
    if not pending:
        return None

    started = pending[0]
    started.status = SubscriptionStatus.ACTIVE.value
    started.starts_at = utcnow()
    started.ends_at = started.starts_at + timedelta(days=started.duration_days)
    session.flush()
    return started if is_usable(session, started) else None
```

Task 2 already imported `datetime`, `Entitlement`, `Session` and `select`. Add
only what is new:

```python
from dataclasses import dataclass
from datetime import timedelta

from app.models.billing import EntitlementSource
from app.payments.entitlements import grant_case_access, has_full_access
```

- [ ] **Step 4: Run the tests and watch them pass**

Run: `python -m pytest tests/test_subscription_consume.py -q`
Expected: PASS, 10 tests.

- [ ] **Step 5: Prove the lock, on real PostgreSQL**

Append to `backend/tests/test_subscription_consume.py`:

```python
def test_two_counsellors_cannot_both_take_the_last_unit(pg_engine, org) -> None:
    """Without FOR UPDATE this grants twice and the school is over quota."""
    import threading

    from sqlalchemy.orm import sessionmaker

    from app.models import ApplicantProfileRow, Organization

    Session = sessionmaker(bind=pg_engine, future=True)

    with Session() as setup:
        school = Organization(name="Race school", slug="race-school")
        setup.add(school)
        setup.flush()
        sub = Subscription(
            organization_id=school.id,
            case_quota=1,
            duration_days=365,
            status=SubscriptionStatus.PENDING.value,
        )
        setup.add(sub)
        setup.flush()
        cases = []
        for _ in range(2):
            case = ApplicantProfileRow(organization_id=school.id, payload={})
            setup.add(case)
            setup.flush()
            cases.append(case.id)
        school_id = school.id
        setup.commit()

    results: list[bool] = []
    barrier = threading.Barrier(2)

    def take(case_id: str) -> None:
        with Session() as session:
            barrier.wait()
            outcome = consume_for_case(
                session, organization_id=school_id, profile_id=case_id
            )
            session.commit()
            results.append(outcome.granted)

    threads = [threading.Thread(target=take, args=(c,)) for c in cases]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert sorted(results) == [False, True]
    with Session() as check:
        assert check.query(Entitlement).filter(Entitlement.organization_id == school_id).count() == 1
```

Run: `python -m pytest tests/test_subscription_consume.py -q`
Expected: PASS, 11 tests. If the race test grants twice, the dialect guard is
not firing — check `session.bind.dialect.name`.

- [ ] **Step 6: Full gates**

Run: `python -m pytest -q && ruff check app tests && mypy app tests`
Expected: all clean.

- [ ] **Step 7: Commit**

```bash
git add backend/app/payments/subscriptions.py backend/tests/test_subscription_consume.py
git commit -m "feat(subscriptions): one writer that spends, retires and advances the queue"
```

---

### Task 4: Wiring the quota into the product

**Files:**
- Modify: `backend/app/payments/http.py` (`PaymentRequired` carries the remaining count)
- Modify: `backend/app/api/paywall.py` (`require_full_access` supplies it)
- Modify: `backend/app/api/routes_research.py` (`start_run` spends a unit)
- Modify: `backend/app/api/routes_billing.py` (new endpoint, richer entitlement view)
- Test: `backend/tests/test_subscription_api.py`

**Interfaces:**
- Consumes: `consume_for_case`, `current_subscription`, `quota_remaining`, `queued_subscriptions`.
- Produces: `POST /api/billing/unlock-from-subscription`; `EntitlementView` gains `subscription_cases_left: int | None` and `subscription_queued: int`; the 402 body gains `subscription_cases_left`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_subscription_api.py`:

```python
"""What a school sees: quota spent silently, then the phase 1 price."""

from __future__ import annotations

import pytest

from app.models.subscription import Subscription, SubscriptionStatus


def _grant(quota: int) -> str:
    """Give the paid client's organization a subscription. Returns its id."""
    from app.db import session_scope
    from app.security import DEV_ORGANIZATION_ID

    with session_scope() as session:
        sub = Subscription(
            organization_id=DEV_ORGANIZATION_ID,
            case_quota=quota,
            duration_days=365,
            status=SubscriptionStatus.PENDING.value,
        )
        session.add(sub)
        session.flush()
        return sub.id


def test_without_a_subscription_the_paywall_offers_only_a_price(paid_client, case_id) -> None:
    body = paid_client.get(f"/api/billing/entitlements?profile_id={case_id}").json()
    assert body["full_access"] is False
    assert body["subscription_cases_left"] is None
    assert body["subscription_queued"] == 0


def test_a_subscription_is_reported_before_it_is_spent(paid_client, case_id) -> None:
    _grant(5)
    body = paid_client.get(f"/api/billing/entitlements?profile_id={case_id}").json()
    # Not started yet, so it is queued rather than current.
    assert body["subscription_queued"] == 1


def test_starting_a_run_spends_one_unit_and_runs_full(paid_client, case_id) -> None:
    _grant(5)
    run = paid_client.post(
        "/api/runs", json={"profile_id": case_id, "demo_mode": True}
    ).json()
    assert run["candidate_limit"] > 5

    body = paid_client.get(f"/api/billing/entitlements?profile_id={case_id}").json()
    assert body["full_access"] is True
    assert body["subscription_cases_left"] == 4


def test_a_second_run_on_the_same_case_spends_nothing(paid_client, case_id) -> None:
    _grant(5)
    for _ in range(2):
        paid_client.post("/api/runs", json={"profile_id": case_id, "demo_mode": True})
    body = paid_client.get(f"/api/billing/entitlements?profile_id={case_id}").json()
    assert body["subscription_cases_left"] == 4


def test_unlocking_from_the_subscription_opens_a_case(paid_client, case_id) -> None:
    _grant(2)
    response = paid_client.post(
        "/api/billing/unlock-from-subscription", json={"profile_id": case_id}
    )
    assert response.status_code == 200
    assert response.json()["full_access"] is True
    assert response.json()["subscription_cases_left"] == 1


def test_unlocking_without_quota_is_a_conflict(paid_client, case_id) -> None:
    response = paid_client.post(
        "/api/billing/unlock-from-subscription", json={"profile_id": case_id}
    )
    assert response.status_code == 409


def test_a_402_tells_the_frontend_there_is_no_quota(paid_client, case_id) -> None:
    run = paid_client.post(
        "/api/runs", json={"profile_id": case_id, "demo_mode": True}
    ).json()
    body = paid_client.get(f"/api/runs/{run['id']}/claims").json()
    assert body["code"] == "payment_required"
    assert body["subscription_cases_left"] is None


def test_a_second_case_still_sees_the_remaining_quota(paid_client, case_id) -> None:
    """One unit spent on the first case leaves one to offer on the next."""
    from app.corpus.demo_profile import DEMO_PROFILE

    _grant(2)
    paid_client.post("/api/runs", json={"profile_id": case_id, "demo_mode": True})

    second = paid_client.post(
        "/api/profiles", json=DEMO_PROFILE.model_dump(mode="json")
    ).json()["id"]
    body = paid_client.get(f"/api/billing/entitlements?profile_id={second}").json()
    assert body["full_access"] is False
    assert body["subscription_cases_left"] == 1


def test_an_unknown_case_cannot_be_unlocked(paid_client) -> None:
    response = paid_client.post(
        "/api/billing/unlock-from-subscription", json={"profile_id": "0" * 32}
    )
    assert response.status_code == 404
```

- [ ] **Step 2: Run it and watch it fail**

Run: `python -m pytest tests/test_subscription_api.py -q`
Expected: FAIL — `KeyError: 'subscription_cases_left'` and 404 on the new endpoint.

- [ ] **Step 3: Let the 402 carry the quota**

Replace `backend/app/payments/http.py` with:

```python
"""The 402 the frontend keys off.

``HTTPException`` would give us a bare ``detail``. The frontend needs to know
which case to sell, for how much, and whether the organization can pay from a
subscription instead — so this carries all three, in the shape
``api/client.ts`` already parses.
"""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse


class PaymentRequired(Exception):
    """Raised by the paywall guard. Rendered as 402 by the handler below."""

    def __init__(
        self, profile_id: str, price_kzt: int, subscription_cases_left: int | None = None
    ) -> None:
        super().__init__("This case has not been unlocked.")
        self.profile_id = profile_id
        self.price_kzt = price_kzt
        self.subscription_cases_left = subscription_cases_left


async def payment_required_handler(_request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, PaymentRequired)
    return JSONResponse(
        status_code=402,
        content={
            "detail": "Unlock this case to see the full report.",
            "code": "payment_required",
            "profile_id": exc.profile_id,
            "price_kzt": exc.price_kzt,
            "subscription_cases_left": exc.subscription_cases_left,
        },
    )
```

In `backend/app/api/paywall.py`, add a helper and use it:

```python
def cases_left(session: Session, organization_id: str) -> int | None:
    """Cases the organization can still open from its subscription."""
    from app.payments.subscriptions import current_subscription, quota_remaining

    subscription = current_subscription(session, organization_id)
    if subscription is None:
        return None
    return quota_remaining(session, subscription)


def require_full_access(session: Session, run_id: str, principal: Principal) -> None:
    profile_id, allowed = access_for_run(session, run_id, principal)
    if not allowed:
        raise PaymentRequired(
            profile_id,
            get_settings().case_unlock_price_kzt,
            cases_left(session, principal.organization_id),
        )
```

- [ ] **Step 4: Spend a unit when a run starts**

In `backend/app/api/routes_research.py`, inside `start_run`, replace the
`full_access = has_full_access(...)` line with:

```python
    # A school with quota gets a full run without being asked; the unit is
    # spent here, once, when the case is actually opened.
    full_access = has_full_access(session, principal.organization_id, payload.profile_id)
    if not full_access:
        from app.payments.subscriptions import consume_for_case

        full_access = consume_for_case(
            session,
            organization_id=principal.organization_id,
            profile_id=payload.profile_id,
        ).granted
```

- [ ] **Step 5: Add the endpoint and widen the view**

In `backend/app/api/routes_billing.py`, extend `EntitlementView`:

```python
class EntitlementView(BaseModel):
    profile_id: str
    full_access: bool
    #: Cases left on the current subscription; null when there is none.
    subscription_cases_left: int | None = None
    #: How many bought-but-not-started subscriptions are waiting behind it.
    subscription_queued: int = 0
```

Add a builder and use it in both routes:

```python
def _entitlement_view(session: Session, principal: Principal, profile_id: str) -> EntitlementView:
    from app.payments.subscriptions import (
        current_subscription,
        quota_remaining,
        queued_subscriptions,
    )

    subscription = current_subscription(session, principal.organization_id)
    return EntitlementView(
        profile_id=profile_id,
        full_access=has_full_access(session, principal.organization_id, profile_id),
        subscription_cases_left=(
            None if subscription is None else quota_remaining(session, subscription)
        ),
        subscription_queued=len(queued_subscriptions(session, principal.organization_id)),
    )
```

Replace the body of `entitlements` with `return _entitlement_view(session, principal, profile_id)`
after its `owned_profile` check, and add:

```python
class UnlockFromSubscriptionIn(BaseModel):
    profile_id: str


@router.post("/unlock-from-subscription", response_model=EntitlementView)
def unlock_from_subscription(
    payload: UnlockFromSubscriptionIn,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> EntitlementView:
    """Open a case out of the organization's subscription quota."""
    from app.payments.subscriptions import consume_for_case

    owned_profile(session, payload.profile_id, principal)
    result = consume_for_case(
        session, organization_id=principal.organization_id, profile_id=payload.profile_id
    )
    if not result.granted:
        # 409, not 402: the case is purchasable, just not from the subscription.
        raise HTTPException(409, "No subscription cases remain.")

    session.add(
        AuditEvent(
            organization_id=principal.organization_id,
            actor=f"user:{principal.user_id[:8]}",
            action="case_unlocked_from_subscription",
            entity_type="profile",
            entity_id=payload.profile_id,
            detail={"subscription_id": result.subscription_id, "remaining": result.remaining},
        )
    )
    session.commit()
    return _entitlement_view(session, principal, payload.profile_id)
```

- [ ] **Step 6: Run the tests and watch them pass**

Run: `python -m pytest tests/test_subscription_api.py -q`
Expected: PASS, 9 tests.

- [ ] **Step 7: Full gates**

Run: `python -m pytest -q && ruff check app tests && mypy app tests`
Expected: all clean. `tests/test_paywall.py` must still pass unchanged — a
school with no subscription is exactly the phase 1 customer.

- [ ] **Step 8: Commit**

```bash
git add backend/app/payments/http.py backend/app/api/paywall.py backend/app/api/routes_research.py backend/app/api/routes_billing.py backend/tests/test_subscription_api.py
git commit -m "feat(subscriptions): spend quota on run start, and say what is left"
```

---

### Task 5: The grant CLI

**Files:**
- Create: `backend/scripts/grant_subscription.py`
- Test: `backend/tests/test_grant_subscription_cli.py`

**Interfaces:**
- Consumes: `Subscription`, `SubscriptionStatus`.
- Produces: `grant(session, *, org_slug, cases, days, invoice) -> Subscription`, `listing(session, org_slug=None) -> list[str]`, `cancel(session, subscription_id) -> bool`, and `main(argv=None) -> int`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_grant_subscription_cli.py`:

```python
"""Granting a subscription after a school pays its invoice."""

from __future__ import annotations

import pytest

from app.models.subscription import Subscription, SubscriptionStatus
from scripts.grant_subscription import cancel, grant, listing


@pytest.fixture
def org(pg_session):
    from app.models import Organization

    row = Organization(name="Test school", slug="test-school")
    pg_session.add(row)
    pg_session.flush()
    return row


def test_a_grant_lands_pending_and_records_the_invoice(pg_session, org) -> None:
    sub = grant(
        pg_session, org_slug="test-school", cases=50, days=365, invoice="Договор 14/26"
    )
    pg_session.flush()
    assert sub.status == SubscriptionStatus.PENDING.value
    assert sub.case_quota == 50
    assert sub.duration_days == 365
    assert sub.invoice_note == "Договор 14/26"
    assert sub.starts_at is None


def test_omitting_the_case_count_means_unlimited(pg_session, org) -> None:
    sub = grant(pg_session, org_slug="test-school", cases=None, days=365, invoice="")
    pg_session.flush()
    assert sub.case_quota is None


def test_an_unknown_organization_is_refused(pg_session) -> None:
    with pytest.raises(LookupError):
        grant(pg_session, org_slug="no-such-school", cases=10, days=30, invoice="")


def test_a_grant_writes_an_audit_event(pg_session, org) -> None:
    from app.models import AuditEvent

    grant(pg_session, org_slug="test-school", cases=10, days=30, invoice="")
    pg_session.flush()
    actions = [e.action for e in pg_session.query(AuditEvent).all()]
    assert "subscription_granted" in actions


def test_listing_reports_what_a_school_holds(pg_session, org) -> None:
    grant(pg_session, org_slug="test-school", cases=50, days=365, invoice="A")
    pg_session.flush()
    lines = listing(pg_session, org_slug="test-school")
    assert len(lines) == 1
    assert "test-school" in lines[0]
    assert "pending" in lines[0]


def test_cancelling_marks_it_cancelled(pg_session, org) -> None:
    sub = grant(pg_session, org_slug="test-school", cases=50, days=365, invoice="")
    pg_session.flush()
    assert cancel(pg_session, sub.id) is True
    pg_session.flush()
    pg_session.refresh(sub)
    assert sub.status == SubscriptionStatus.CANCELLED.value


def test_cancelling_something_that_does_not_exist_reports_it(pg_session) -> None:
    assert cancel(pg_session, "0" * 32) is False


def test_a_cancelled_subscription_is_never_spent(pg_session, org) -> None:
    from app.models import ApplicantProfileRow
    from app.payments.subscriptions import consume_for_case

    sub = grant(pg_session, org_slug="test-school", cases=5, days=365, invoice="")
    pg_session.flush()
    cancel(pg_session, sub.id)
    pg_session.flush()

    case = ApplicantProfileRow(organization_id=org.id, payload={})
    pg_session.add(case)
    pg_session.flush()
    assert (
        consume_for_case(pg_session, organization_id=org.id, profile_id=case.id).granted
        is False
    )
    assert pg_session.query(Subscription).one().status == SubscriptionStatus.CANCELLED.value
```

- [ ] **Step 2: Run it and watch it fail**

Run: `python -m pytest tests/test_grant_subscription_cli.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.grant_subscription'`.

- [ ] **Step 3: Write the script**

Create `backend/scripts/grant_subscription.py`:

```python
"""Record a school subscription after its invoice is paid.

Money arrives by bank transfer against a contract raised outside the product,
so this is the whole of "billing" for a school: write down what was sold.

A grant always lands ``pending``. Activation belongs to ``consume_for_case``
and nowhere else, so there is one activation path rather than two that have to
agree — the term starts counting when the school opens its first case.

Usage::

    python scripts/grant_subscription.py --org <slug> --cases 50 --days 365 \\
        --invoice "Договор 14/26"
    python scripts/grant_subscription.py --list
    python scripts/grant_subscription.py --list --org <slug>
    python scripts/grant_subscription.py --cancel <subscription-id>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.models import AuditEvent, Organization  # noqa: E402
from app.models.subscription import Subscription, SubscriptionStatus  # noqa: E402


def grant(
    session: Session, *, org_slug: str, cases: int | None, days: int, invoice: str
) -> Subscription:
    """Record a sold subscription. Refuses an organization it cannot find."""
    org = session.scalar(select(Organization).where(Organization.slug == org_slug))
    if org is None:
        raise LookupError(f"No organization with slug {org_slug!r}")

    subscription = Subscription(
        organization_id=org.id,
        case_quota=cases,
        duration_days=days,
        status=SubscriptionStatus.PENDING.value,
        invoice_note=invoice,
    )
    session.add(subscription)
    session.flush()
    session.add(
        AuditEvent(
            organization_id=org.id,
            actor="cli",
            action="subscription_granted",
            entity_type="subscription",
            entity_id=subscription.id,
            detail={"cases": cases, "days": days, "invoice": invoice},
        )
    )
    return subscription


def listing(session: Session, org_slug: str | None = None) -> list[str]:
    """One readable line per subscription, newest last."""
    from app.payments.subscriptions import quota_remaining

    query = select(Subscription, Organization).join(
        Organization, Organization.id == Subscription.organization_id
    )
    if org_slug:
        query = query.where(Organization.slug == org_slug)
    query = query.order_by(Subscription.created_at)

    lines = []
    for subscription, org in session.execute(query):
        remaining = quota_remaining(session, subscription)
        quota = "unlimited" if subscription.case_quota is None else str(subscription.case_quota)
        left = "-" if remaining is None else str(remaining)
        ends = subscription.ends_at.date().isoformat() if subscription.ends_at else "not started"
        lines.append(
            f"{subscription.id}  {org.slug:<20}  {subscription.status:<10}  "
            f"{left}/{quota} left  ends {ends}  {subscription.invoice_note}"
        )
    return lines


def cancel(session: Session, subscription_id: str) -> bool:
    """Cancel a subscription. False when there is no such row."""
    subscription = session.get(Subscription, subscription_id)
    if subscription is None:
        return False
    subscription.status = SubscriptionStatus.CANCELLED.value
    session.add(
        AuditEvent(
            organization_id=subscription.organization_id,
            actor="cli",
            action="subscription_cancelled",
            entity_type="subscription",
            entity_id=subscription.id,
            detail={},
        )
    )
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--org", help="organization slug")
    parser.add_argument("--cases", type=int, help="cases included; omit for unlimited")
    parser.add_argument("--days", type=int, default=365, help="term length in days")
    parser.add_argument("--invoice", default="", help="contract or invoice number")
    parser.add_argument("--list", action="store_true", help="show subscriptions")
    parser.add_argument("--cancel", help="cancel a subscription by id")
    args = parser.parse_args(argv)

    from app.db import session_scope

    with session_scope() as session:
        if args.cancel:
            if not cancel(session, args.cancel):
                print(f"No subscription {args.cancel}", file=sys.stderr)
                return 1
            print(f"Cancelled {args.cancel}")
            return 0

        if args.list:
            lines = listing(session, args.org)
            print("\n".join(lines) if lines else "No subscriptions.")
            return 0

        if not args.org:
            parser.error("--org is required when granting")
        subscription = grant(
            session,
            org_slug=args.org,
            cases=args.cases,
            days=args.days,
            invoice=args.invoice,
        )
        session.flush()
        quota = "unlimited" if args.cases is None else f"{args.cases} cases"
        print(f"Granted {subscription.id}: {quota} for {args.days} days, pending first use.")
        return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
```

- [ ] **Step 4: Make the script importable from tests**

`backend/pytest.ini` sets the rootdir; confirm `scripts` is importable by
running `python -c "import scripts.grant_subscription"` from `backend/`. If it
fails with `ModuleNotFoundError: No module named 'scripts'`, add an empty
`backend/scripts/__init__.py`.

- [ ] **Step 5: Run the tests and watch them pass**

Run: `python -m pytest tests/test_grant_subscription_cli.py -q`
Expected: PASS, 8 tests.

- [ ] **Step 6: Full gates**

Run: `python -m pytest -q && ruff check app tests && mypy app tests`
Expected: all clean. If ruff objects to the `sys.path` insert before imports,
keep the `# noqa: E402` markers shown above — the existing scripts do the same.

- [ ] **Step 7: Commit**

```bash
git add backend/scripts/grant_subscription.py backend/tests/test_grant_subscription_cli.py
git commit -m "feat(subscriptions): a CLI to record what a school bought"
```

---

### Task 6: The paywall offers the subscription first

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/lib/store.tsx`
- Modify: `frontend/src/components/PaywallNotice.tsx`
- Test: `frontend/src/components/PaywallNotice.test.tsx`

**Interfaces:**
- Consumes: Task 4's HTTP shapes.
- Produces: `EntitlementView` gains `subscription_cases_left: number | null` and `subscription_queued: number`; `ApiError.subscriptionCasesLeft?: number | null`; `api.unlockFromSubscription(profileId)`; store gains `unlockFromSubscription(): Promise<void>` and `paywall.casesLeft`.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/PaywallNotice.test.tsx`:

```tsx
import { afterEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { PaywallNotice } from './PaywallNotice';
import { StoreProvider } from '@/lib/store';
import { api } from '@/api/client';

afterEach(() => vi.restoreAllMocks());

function renderWith(paywall: { profileId: string; priceKzt: number; casesLeft: number | null }) {
  vi.spyOn(api, 'capabilities').mockResolvedValue({} as never);
  vi.spyOn(api, 'cases').mockResolvedValue([]);
  vi.spyOn(api, 'validateProfile').mockResolvedValue({} as never);
  return render(
    <StoreProvider>
      <PaywallNotice testPaywall={paywall} />
    </StoreProvider>,
  );
}

describe('PaywallNotice', () => {
  it('offers the price when there is no subscription', () => {
    renderWith({ profileId: 'c1', priceKzt: 4990, casesLeft: null });
    expect(screen.getByRole('button', { name: /4990/ })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /подписки/i })).toBeNull();
  });

  it('offers the subscription first when cases remain', () => {
    renderWith({ profileId: 'c1', priceKzt: 4990, casesLeft: 37 });
    expect(screen.getByRole('button', { name: /осталось 37/i })).toBeInTheDocument();
  });

  it('falls back to the price when the quota is exhausted', () => {
    renderWith({ profileId: 'c1', priceKzt: 4990, casesLeft: 0 });
    expect(screen.getByRole('button', { name: /4990/ })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /осталось/i })).toBeNull();
  });

  it('spends a subscription case when asked', async () => {
    const unlock = vi.spyOn(api, 'unlockFromSubscription').mockResolvedValue({
      profile_id: 'c1',
      full_access: true,
      subscription_cases_left: 36,
      subscription_queued: 0,
    });
    renderWith({ profileId: 'c1', priceKzt: 4990, casesLeft: 37 });
    fireEvent.click(screen.getByRole('button', { name: /осталось 37/i }));
    await waitFor(() => expect(unlock).toHaveBeenCalledWith('c1'));
  });
});
```

`PaywallNotice` takes an optional `testPaywall` prop purely so this test can
drive it without a 402 round trip; when absent it reads the store as before.

- [ ] **Step 2: Run it and watch it fail**

Run (from `frontend/`): `npm run test -- PaywallNotice`
Expected: FAIL — `api.unlockFromSubscription is not a function`.

- [ ] **Step 3: Extend the types and client**

In `frontend/src/types.ts`, replace the `EntitlementView` interface with:

```ts
export interface EntitlementView {
  profile_id: string;
  full_access: boolean;
  subscription_cases_left: number | null;
  subscription_queued: number;
}
```

In `frontend/src/api/client.ts`, add to `ApiError`:

```ts
  /** Cases left on the organization's subscription, when a 402 reported one. */
  subscriptionCasesLeft?: number | null;
```

Replace the whole `failureFrom` function with this — it is the existing one
plus one captured field:

```ts
/** Build the error for a failed response. Shared so downloads report like calls. */
async function failureFrom(response: Response): Promise<ApiError> {
  let detail = `${response.status} ${response.statusText}`;
  let code: string | undefined;
  let profileId: string | undefined;
  let priceKzt: number | undefined;
  let casesLeft: number | null | undefined;
  try {
    const body = await response.json();
    if (typeof body?.detail === 'string') detail = body.detail;
    else if (Array.isArray(body?.detail)) {
      detail = body.detail
        .map((d: { loc?: unknown[]; msg?: string }) => `${d.loc?.slice(1).join('.')}: ${d.msg}`)
        .join('; ');
    }
    code = body?.code;
    // A 402 names the case to sell, its price, and whether the organization
    // can pay from a subscription instead. No other status carries these.
    if (typeof body?.profile_id === 'string') profileId = body.profile_id;
    if (typeof body?.price_kzt === 'number') priceKzt = body.price_kzt;
    if (typeof body?.subscription_cases_left === 'number') {
      casesLeft = body.subscription_cases_left;
    }
  } catch {
    /* a non-JSON error body is still reported by status */
  }
  const failure = new ApiError(response.status, detail, code);
  failure.profileId = profileId;
  failure.priceKzt = priceKzt;
  failure.subscriptionCasesLeft = casesLeft;
  return failure;
}
```

Add to the `api` object:

```ts
  unlockFromSubscription: (profileId: string) =>
    request<EntitlementView>('/api/billing/unlock-from-subscription', {
      method: 'POST',
      body: JSON.stringify({ profile_id: profileId }),
    }),
```

- [ ] **Step 4: Carry the count through the store**

In `frontend/src/lib/store.tsx`, widen the paywall state and add the action:

```tsx
  const [paywall, setPaywall] = useState<
    { profileId: string; priceKzt: number; casesLeft: number | null } | null
  >(null);
```

In `fail`, keep the interception and carry the count:

```tsx
    if (isPaymentRequired(e)) {
      setPaywall({
        profileId: e.profileId,
        priceKzt: e.priceKzt,
        casesLeft: e.subscriptionCasesLeft ?? null,
      });
      return;
    }
```

Add the action, beside `exportShortlist`:

```tsx
  const unlockFromSubscription = useCallback(async () => {
    if (!paywall) return;
    setError(null);
    try {
      await api.unlockFromSubscription(paywall.profileId);
      setPaywall(null);
      await refreshResults();
    } catch (e) {
      fail(e);
    }
  }, [paywall, fail, refreshResults]);
```

Update the `Store` interface (`paywall` gains `casesLeft: number | null`; add
`unlockFromSubscription: () => Promise<void>`), and add both to the `useMemo`
value and its dependency array.

- [ ] **Step 5: Give the notice its branch**

Replace `frontend/src/components/PaywallNotice.tsx` with:

```tsx
/**
 * What a locked panel says instead of showing nothing.
 *
 * A school with quota left is offered its own subscription first — being asked
 * for 4990 ₸ when the school has already paid for the year would be wrong.
 */

import { useState } from 'react';
import { PaymentModal } from './PaymentModal';
import { useStore } from '@/lib/store';

interface Props {
  /** Test seam: drive the component without a 402 round trip. */
  testPaywall?: { profileId: string; priceKzt: number; casesLeft: number | null };
}

export function PaywallNotice({ testPaywall }: Props) {
  const { paywall: storePaywall, clearPaywall, refreshResults, unlockFromSubscription } =
    useStore();
  const [paying, setPaying] = useState(false);
  const paywall = testPaywall ?? storePaywall;

  if (!paywall) return null;

  const fromSubscription = paywall.casesLeft !== null && paywall.casesLeft > 0;

  return (
    <div style={{ padding: 'var(--space-4) var(--space-6) 0' }}>
      <div className="notice notice--info" role="note">
        <div style={{ flex: 1 }}>
          <strong>Этот раздел открывается после оплаты кейса.</strong> Полный охват программ,
          источник под каждым значением, финансирование и экспорт.
        </div>
        {fromSubscription ? (
          <button className="btn btn--sm btn--primary" onClick={() => void unlockFromSubscription()}>
            Открыть из подписки (осталось {paywall.casesLeft})
          </button>
        ) : (
          <button className="btn btn--sm btn--primary" onClick={() => setPaying(true)}>
            Открыть за {paywall.priceKzt} ₸
          </button>
        )}
        <button className="btn btn--sm btn--ghost" onClick={clearPaywall}>
          Не сейчас
        </button>
      </div>

      {paying && (
        <PaymentModal
          profileId={paywall.profileId}
          priceKzt={paywall.priceKzt}
          onClose={() => setPaying(false)}
          onPaid={() => {
            setPaying(false);
            clearPaywall();
            void refreshResults();
          }}
        />
      )}
    </div>
  );
}
```

- [ ] **Step 6: Run the tests and watch them pass**

Run: `npm run test -- PaywallNotice`
Expected: PASS, 4 tests.

- [ ] **Step 7: Full frontend gates**

Run: `npx tsc --noEmit && npm run lint && npm run test && npm run build`
Expected: all clean.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/types.ts frontend/src/api/client.ts frontend/src/lib/store.tsx frontend/src/components/PaywallNotice.tsx frontend/src/components/PaywallNotice.test.tsx
git commit -m "feat(subscriptions): offer the school its own quota before a price"
```

---

### Task 7: Say what is true

**Files:**
- Modify: `README.md`
- Modify: `ASSUMPTIONS.md`
- Modify: `RELEASE_CHECKLIST.md`
- Modify: `SECURITY.md`

- [ ] **Step 1: README**

Extend the Payments section: schools buy a quota of cases for a term against an
invoice paid by bank transfer; ApiPay is not involved. Opening a case spends one
unit, once; running out falls back to the per-case price. An early renewal
queues rather than destroying what is left. Record the CLI's four commands
verbatim from Task 5's docstring.

- [ ] **Step 2: ASSUMPTIONS.md**

Under the Payments heading added in phase 1, record: the subscription price
list is not in the product and never was — the product only writes down what
was sold; an expired term burns whatever quota it still held, which is what
"until the term ends" means; a school's term starts when it opens its first
case, not when the invoice was paid.

- [ ] **Step 3: RELEASE_CHECKLIST.md**

Under "Needs the user", add: the subscription price list and standard term; and
that granting a subscription is a manual CLI step run by an operator with
database access, so whoever sells must be able to reach a shell.

- [ ] **Step 4: SECURITY.md**

Under the Payments heading added in phase 1, add: quota is spent by exactly one
function, under a row lock on PostgreSQL, so two counsellors cannot both take
the last unit; remaining is counted from entitlement rows rather than a stored
counter, so it cannot drift from what was actually granted; granting is a CLI
action requiring database access, deliberately not a network endpoint.

- [ ] **Step 5: Every gate, one last time**

From `backend/`: `python -m pytest -q && ruff check app tests && mypy app tests`
From `frontend/`: `npx tsc --noEmit && npm run lint && npm run test && npm run build`
Expected: all clean.

- [ ] **Step 6: Commit**

```bash
git add README.md ASSUMPTIONS.md RELEASE_CHECKLIST.md SECURITY.md
git commit -m "docs: how a school subscription is sold, spent and queued"
```

---

## Notes for whoever executes this

* **Reads must never spend.** If you find yourself wanting to retire or activate
  a subscription inside `current_subscription`, stop: that is how a page refresh
  starts costing a customer money. Both writes belong in `consume_for_case`.
* **No `used_count` column.** Remaining is counted from the entitlement rows.
  Adding a counter "for speed" reintroduces exactly the drift this design
  removes; measure first, and if it is ever slow, the fix is an index.
* **Test counts are estimates.** Another session commits to `main` in parallel;
  what matters is that the count rises by what a task adds and nothing that
  passed starts failing.
* **`payments_enabled` still defaults to false.** With payments off,
  `has_full_access` returns true for everything and none of this is reachable.
