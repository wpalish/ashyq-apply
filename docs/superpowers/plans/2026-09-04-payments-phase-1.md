# Payments Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A case owner can unlock one applicant case with a single Kaspi payment through ApiPay, and every route that exposes paid material refuses until they have.

**Architecture:** An `entitlements` table is the only thing the application asks about. Orders drive it, a provider adapter behind a `Protocol` creates the invoice, and two independent sources — a signed webhook and a polling reconciler on the existing durable queue — converge on one idempotent writer, `apply_status`. A feature flag keeps today's behaviour exactly intact until keys exist.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0 (`Mapped` / `mapped_column`), Alembic, httpx, pytest, PostgreSQL 16 (SQLite for local), React 18 + TypeScript, Vitest.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-09-04-payments-phase-1-design.md`. Read it before Task 1.
- Settings use `env_prefix="UNIMATCH_"`, so `payments_enabled` is `UNIMATCH_PAYMENTS_ENABLED`.
- All routers are mounted under `/api`; the webhook is the sole exception at `/webhooks/apipay`.
- Money is whole tenge, `int`. Never float, never Decimal, never a string.
- The payer's phone number is stored masked and never appears in a log line, a URL, an exception message or an audit detail.
- Provider secrets are `SecretStr` and are never rendered.
- Timestamps: `datetime` aware UTC via `app.models.base.utcnow`; read back through `ensure_utc` before comparing.
- New model files follow `app/models/auth.py`: `TimestampedBase`, `Mapped[...]`, `mapped_column`, explicit `__table_args__`.
- Every task ends green on: `pytest -q`, `ruff check .`, `mypy app`. Baseline is 553 passing.
- Commit at the end of every task. Never amend, never skip hooks.
- Run backend commands from `backend/` with `.venv\Scripts\python.exe` on Windows, `.venv/bin/python` elsewhere. The plan writes `python` for brevity.

---

### Task 1: Configuration and the feature flag

**Files:**
- Modify: `backend/app/config.py` (add settings to the `Settings` class)
- Modify: `.env.example`
- Test: `backend/tests/test_payments_config.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `Settings.payments_enabled: bool`, `Settings.payments_provider: str`, `Settings.apipay_base_url: str`, `Settings.apipay_api_key: SecretStr`, `Settings.apipay_webhook_secret: SecretStr`, `Settings.apipay_timeout_seconds: float`, `Settings.case_unlock_price_kzt: int`, `Settings.free_candidate_limit: int`, `Settings.free_shortlist_rows: int`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_payments_config.py`:

```python
"""Payment configuration: safe defaults, and secrets that do not leak."""

from __future__ import annotations

from app.config import Settings


def test_payments_are_off_by_default() -> None:
    settings = Settings()
    assert settings.payments_enabled is False
    assert settings.payments_provider == "fake"


def test_price_and_free_tier_defaults() -> None:
    settings = Settings()
    assert settings.case_unlock_price_kzt == 4990
    assert settings.free_candidate_limit == 5
    assert settings.free_shortlist_rows == 5


def test_secrets_do_not_render_in_a_settings_dump() -> None:
    settings = Settings(apipay_api_key="live-key-value", apipay_webhook_secret="whsec-value")
    dumped = repr(settings.model_dump())
    assert "live-key-value" not in dumped
    assert "whsec-value" not in dumped
    assert settings.apipay_api_key.get_secret_value() == "live-key-value"


def test_secret_values_are_reachable_only_deliberately() -> None:
    settings = Settings(apipay_webhook_secret="whsec-value")
    assert "whsec-value" not in str(settings.apipay_webhook_secret)
```

- [ ] **Step 2: Run it and watch it fail**

Run: `python -m pytest tests/test_payments_config.py -q`
Expected: FAIL — `AttributeError: 'Settings' object has no attribute 'payments_enabled'`.

- [ ] **Step 3: Add the settings**

In `backend/app/config.py`, add `SecretStr` to the pydantic import line:

```python
from pydantic import SecretStr
```

Then add this block to `Settings`, after the auth settings that end with `run_rate_limit_per_minute`:

```python
    # ---- Payments -----------------------------------------------------
    #: Off by default. With this false the product behaves exactly as it did
    #: before payments existed: no paywall, no truncation, every case open.
    payments_enabled: bool = False
    #: "fake" drives the tests and local development. "apipay" talks to Kaspi.
    payments_provider: str = "fake"
    apipay_base_url: str = "https://api.apipay.kz/api/v1"
    apipay_api_key: SecretStr = SecretStr("")
    apipay_webhook_secret: SecretStr = SecretStr("")
    apipay_timeout_seconds: float = 20.0
    #: Whole tenge. The server is the only authority on what a case costs.
    case_unlock_price_kzt: int = 4990
    #: What an unpaid case is allowed to spend, and to show.
    free_candidate_limit: int = 5
    free_shortlist_rows: int = 5
```

- [ ] **Step 4: Run the test and watch it pass**

Run: `python -m pytest tests/test_payments_config.py -q`
Expected: PASS, 4 tests.

- [ ] **Step 5: Document the environment variables**

Append to `.env.example`:

```
# Payments (Kaspi via ApiPay). Off until a merchant account exists.
UNIMATCH_PAYMENTS_ENABLED=false
UNIMATCH_PAYMENTS_PROVIDER=fake
UNIMATCH_APIPAY_BASE_URL=https://api.apipay.kz/api/v1
UNIMATCH_APIPAY_API_KEY=
UNIMATCH_APIPAY_WEBHOOK_SECRET=
UNIMATCH_CASE_UNLOCK_PRICE_KZT=4990
UNIMATCH_FREE_CANDIDATE_LIMIT=5
UNIMATCH_FREE_SHORTLIST_ROWS=5
```

- [ ] **Step 6: Full suite, lint, types**

Run: `python -m pytest -q && ruff check . && mypy app`
Expected: 557 passed, ruff clean, mypy clean.

- [ ] **Step 7: Commit**

```bash
git add backend/app/config.py backend/tests/test_payments_config.py .env.example
git commit -m "feat(payments): configuration, off by default"
```

---

### Task 2: Billing tables and their migration

**Files:**
- Create: `backend/app/models/billing.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/migrations/versions/d4b2c8f17a90_billing.py`
- Test: `backend/tests/test_billing_models.py`

**Interfaces:**
- Consumes: `Settings` from Task 1.
- Produces: `Order`, `PaymentEvent`, `Entitlement` models; `OrderStatus`, `OrderKind`, `PaymentMethod`, `EntitlementKind`, `EntitlementSource` string enums; `ResearchRun.access_tier: str`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_billing_models.py`:

```python
"""The billing tables, and the constraints that make double-charging hard."""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.billing import (
    Entitlement,
    EntitlementKind,
    EntitlementSource,
    Order,
    OrderKind,
    OrderStatus,
    PaymentEvent,
    PaymentMethod,
)


def _order(session, **overrides) -> Order:
    fields = dict(
        organization_id="org1",
        profile_id="case1",
        kind=OrderKind.CASE_UNLOCK.value,
        amount_kzt=4990,
        status=OrderStatus.PENDING.value,
        provider="fake",
        external_order_id="ext-1",
        method=PaymentMethod.PHONE.value,
        phone_masked="8707***4455",
    )
    fields.update(overrides)
    row = Order(**fields)
    session.add(row)
    session.flush()
    return row


def test_external_order_id_is_unique(pg_session) -> None:
    _order(pg_session, external_order_id="ext-dup")
    with pytest.raises(IntegrityError):
        _order(pg_session, profile_id="case2", external_order_id="ext-dup")


def test_one_case_entitlement_per_organization(pg_session) -> None:
    pg_session.add(
        Entitlement(
            organization_id="org1",
            profile_id="case1",
            kind=EntitlementKind.CASE_FULL.value,
            source=EntitlementSource.PURCHASE.value,
        )
    )
    pg_session.flush()
    pg_session.add(
        Entitlement(
            organization_id="org1",
            profile_id="case1",
            kind=EntitlementKind.CASE_FULL.value,
            source=EntitlementSource.MANUAL.value,
        )
    )
    with pytest.raises(IntegrityError):
        pg_session.flush()


def test_one_organization_wide_entitlement_despite_null_profile(pg_session) -> None:
    """A plain unique constraint would let unlimited null rows through."""
    for _ in range(2):
        pg_session.add(
            Entitlement(
                organization_id="org1",
                profile_id=None,
                kind=EntitlementKind.ORG_SUBSCRIPTION.value,
                source=EntitlementSource.SUBSCRIPTION.value,
            )
        )
    with pytest.raises(IntegrityError):
        pg_session.flush()


def test_payment_events_accumulate_against_an_order(pg_session) -> None:
    order = _order(pg_session, external_order_id="ext-events")
    for source in ("webhook", "poll"):
        pg_session.add(
            PaymentEvent(
                order_id=order.id,
                source=source,
                event_type="invoice.status_changed",
                provider_status="paid",
                signature_valid=True,
            )
        )
    pg_session.flush()
    assert pg_session.query(PaymentEvent).filter(PaymentEvent.order_id == order.id).count() == 2


def test_runs_record_the_tier_they_were_allowed(pg_session) -> None:
    from app.models import ResearchRun

    run = ResearchRun(profile_id="case1", stage="queued", access_tier="free")
    pg_session.add(run)
    pg_session.flush()
    assert run.access_tier == "free"
```

- [ ] **Step 2: Run it and watch it fail**

Run: `python -m pytest tests/test_billing_models.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.models.billing'`.

- [ ] **Step 3: Write the models**

Create `backend/app/models/billing.py`:

```python
"""Orders, the journal of what the provider told us, and what was granted.

Only ``Entitlement`` is consulted by the rest of the application. ``Order`` and
``PaymentEvent`` exist so that a disputed payment can be reconstructed from the
database rather than from memory.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampedBase, new_id, utcnow


class OrderKind(str, Enum):
    CASE_UNLOCK = "case_unlock"


class OrderStatus(str, Enum):
    CREATED = "created"
    PENDING = "pending"
    PAID = "paid"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    FAILED = "failed"


#: Terminal states are never overwritten by a later, lesser status.
TERMINAL_ORDER_STATUSES = frozenset(
    {OrderStatus.PAID.value, OrderStatus.CANCELLED.value, OrderStatus.EXPIRED.value,
     OrderStatus.FAILED.value}
)


class PaymentMethod(str, Enum):
    PHONE = "phone"
    QR = "qr"


class EntitlementKind(str, Enum):
    CASE_FULL = "case_full"
    #: Phase 2. Declared here so the constraint that guards it exists from day one.
    ORG_SUBSCRIPTION = "org_subscription"


class EntitlementSource(str, Enum):
    PURCHASE = "purchase"
    MANUAL = "manual"
    SUBSCRIPTION = "subscription"


class Order(TimestampedBase):
    __tablename__ = "orders"
    __table_args__ = (
        Index("ix_orders_org_profile", "organization_id", "profile_id"),
        Index("ix_orders_provider_invoice", "provider_invoice_id"),
    )

    organization_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    profile_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("applicant_profiles.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(30), default=OrderKind.CASE_UNLOCK.value)

    #: Whole tenge, decided by the server from configuration.
    amount_kzt: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default=OrderStatus.CREATED.value, index=True)

    provider: Mapped[str] = mapped_column(String(20), default="fake")
    provider_invoice_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    #: Our idempotency key to the provider. Unique so a retry cannot open two invoices.
    external_order_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)

    method: Mapped[str] = mapped_column(String(10), default=PaymentMethod.PHONE.value)
    #: Masked at the boundary. The full number is never stored.
    phone_masked: Mapped[str] = mapped_column(String(20), default="")

    qr_payload: Mapped[str] = mapped_column(Text, default="")
    qr_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_code: Mapped[str] = mapped_column(String(60), default="")


class PaymentEvent(Base):
    """Append-only. Written even when the status did not change."""

    __tablename__ = "payment_events"
    __table_args__ = (Index("ix_payment_events_order", "order_id", "received_at"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    order_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("orders.id", ondelete="CASCADE"), index=True
    )
    source: Mapped[str] = mapped_column(String(20))
    event_type: Mapped[str] = mapped_column(String(60), default="")
    provider_status: Mapped[str] = mapped_column(String(30), default="")
    signature_valid: Mapped[bool] = mapped_column(Boolean, default=True)
    #: Redacted before it reaches here. No phone, no key, no signature.
    detail: Mapped[str] = mapped_column(Text, default="")
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Entitlement(TimestampedBase):
    """What an organization is allowed to see. The only table routes consult."""

    __tablename__ = "entitlements"
    __table_args__ = (
        # Two partial indexes rather than one constraint: in PostgreSQL a plain
        # UNIQUE treats every NULL profile_id as distinct, which would let an
        # organization accumulate unlimited subscriptions.
        Index(
            "uq_entitlements_case",
            "organization_id",
            "profile_id",
            "kind",
            unique=True,
            postgresql_where=text("profile_id IS NOT NULL"),
            sqlite_where=text("profile_id IS NOT NULL"),
        ),
        Index(
            "uq_entitlements_org",
            "organization_id",
            "kind",
            unique=True,
            postgresql_where=text("profile_id IS NULL"),
            sqlite_where=text("profile_id IS NULL"),
        ),
    )

    organization_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    #: Null means the entitlement covers the whole organization (phase 2).
    profile_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(30))
    source: Mapped[str] = mapped_column(String(20), default=EntitlementSource.PURCHASE.value)
    order_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
```

Note what is *not* a database constraint: "at most one open order per case". Expressing
it as a partial index would mean enumerating every non-terminal status in index
predicates on two dialects, and the predicate would have to change every time a status
is added. It is enforced instead in `create_order` (Task 5), which reuses an open order
rather than opening a second one — and the unique `external_order_id` is the backstop
that stops two invoices reaching the provider even if that check is ever bypassed.

- [ ] **Step 4: Export the models and add the run column**

In `backend/app/models/__init__.py`, add to the imports and `__all__`:

```python
from app.models.billing import (
    Entitlement,
    EntitlementKind,
    EntitlementSource,
    Order,
    OrderKind,
    OrderStatus,
    PaymentEvent,
    PaymentMethod,
)
```

In `backend/app/models/research.py`, add to `ResearchRun`:

```python
    #: Which tier this run was allowed to spend at. A free run really did
    #: fetch less, so paying later cannot retroactively widen it.
    access_tier: Mapped[str] = mapped_column(String(10), default="full", index=True)
```

- [ ] **Step 5: Write the migration**

Create `backend/migrations/versions/d4b2c8f17a90_billing.py`:

```python
"""Orders, payment events, entitlements, and the tier a run was allowed.

Revision ID: d4b2c8f17a90
Revises: c3a1f4e9b2d7
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "d4b2c8f17a90"
down_revision = "c3a1f4e9b2d7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "orders",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("organization_id", sa.String(32), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("profile_id", sa.String(32), sa.ForeignKey("applicant_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(30), nullable=False),
        sa.Column("amount_kzt", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("provider_invoice_id", sa.String(80), nullable=True),
        sa.Column("external_order_id", sa.String(80), nullable=False),
        sa.Column("method", sa.String(10), nullable=False),
        sa.Column("phone_masked", sa.String(20), nullable=False),
        sa.Column("qr_payload", sa.Text(), nullable=False),
        sa.Column("qr_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_code", sa.String(60), nullable=False),
    )
    op.create_index("ix_orders_organization_id", "orders", ["organization_id"])
    op.create_index("ix_orders_profile_id", "orders", ["profile_id"])
    op.create_index("ix_orders_status", "orders", ["status"])
    op.create_index("ix_orders_org_profile", "orders", ["organization_id", "profile_id"])
    op.create_index("ix_orders_provider_invoice", "orders", ["provider_invoice_id"])
    op.create_index("ix_orders_external_order_id", "orders", ["external_order_id"], unique=True)

    op.create_table(
        "payment_events",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("order_id", sa.String(32), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("event_type", sa.String(60), nullable=False),
        sa.Column("provider_status", sa.String(30), nullable=False),
        sa.Column("signature_valid", sa.Boolean(), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_payment_events_order_id", "payment_events", ["order_id"])
    op.create_index("ix_payment_events_order", "payment_events", ["order_id", "received_at"])

    op.create_table(
        "entitlements",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("organization_id", sa.String(32), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("profile_id", sa.String(32), nullable=True),
        sa.Column("kind", sa.String(30), nullable=False),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("order_id", sa.String(32), nullable=True),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_entitlements_organization_id", "entitlements", ["organization_id"])
    op.create_index("ix_entitlements_profile_id", "entitlements", ["profile_id"])
    op.create_index(
        "uq_entitlements_case",
        "entitlements",
        ["organization_id", "profile_id", "kind"],
        unique=True,
        postgresql_where=sa.text("profile_id IS NOT NULL"),
        sqlite_where=sa.text("profile_id IS NOT NULL"),
    )
    op.create_index(
        "uq_entitlements_org",
        "entitlements",
        ["organization_id", "kind"],
        unique=True,
        postgresql_where=sa.text("profile_id IS NULL"),
        sqlite_where=sa.text("profile_id IS NULL"),
    )

    op.add_column(
        "research_runs",
        sa.Column("access_tier", sa.String(10), nullable=False, server_default="full"),
    )
    op.create_index("ix_research_runs_access_tier", "research_runs", ["access_tier"])


def downgrade() -> None:
    op.drop_index("ix_research_runs_access_tier", table_name="research_runs")
    op.drop_column("research_runs", "access_tier")
    op.drop_table("entitlements")
    op.drop_table("payment_events")
    op.drop_table("orders")
```

Confirm the parent revision before writing: `python -c "from app.db import head_revision; print(head_revision())"` must print `c3a1f4e9b2d7`. If it prints something else, another session has added a migration — set `down_revision` to what it printed.

- [ ] **Step 6: Run the tests and watch them pass**

Run: `python -m pytest tests/test_billing_models.py -q`
Expected: PASS, 5 tests. These run against real PostgreSQL via the `pg_session` fixture, so the partial indexes are proven where they matter.

- [ ] **Step 7: Full suite, lint, types**

Run: `python -m pytest -q && ruff check . && mypy app`
Expected: 562 passed, clean.

- [ ] **Step 8: Commit**

```bash
git add backend/app/models/billing.py backend/app/models/__init__.py backend/app/models/research.py backend/migrations/versions/d4b2c8f17a90_billing.py backend/tests/test_billing_models.py
git commit -m "feat(payments): orders, events, entitlements, and the run tier"
```

---

### Task 3: The provider Protocol, its errors, and a fake that behaves like ApiPay

**Files:**
- Create: `backend/app/payments/__init__.py`
- Create: `backend/app/payments/errors.py`
- Create: `backend/app/payments/provider.py`
- Create: `backend/app/payments/fake.py`
- Test: `backend/tests/test_payment_provider.py`

**Interfaces:**
- Consumes: `Settings` (Task 1).
- Produces:
  - `ProviderInvoice` dataclass: `invoice_id: str`, `status: str`, `qr_payload: str = ""`, `qr_expires_at: datetime | None = None`.
  - `PaymentProvider` Protocol with `create_phone_invoice(*, amount_kzt: int, phone: str, description: str, external_order_id: str) -> ProviderInvoice`, `create_qr_invoice(*, amount_kzt: int, description: str, external_order_id: str) -> ProviderInvoice`, `get_invoice(invoice_id: str) -> ProviderInvoice`, `cancel_invoice(invoice_id: str) -> None`, `verify_webhook(raw_body: bytes, signature: str) -> bool`.
  - Errors: `PaymentError`, `DuplicateOrderError`, `ProviderUnavailable`, `ProviderRejected`, `TariffInactive`, `SessionExpired`, `RateLimited(retry_after: int)`.
  - `mask_phone(phone: str) -> str` in `provider.py` — production code must never import it from the fake.
  - `FakeProvider` with `simulate(invoice_id, status)` and `sign(raw_body) -> str`; `get_shared_fake(secret)`, `reset_shared_fake()`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_payment_provider.py`:

```python
"""The provider seam: a fake that behaves the way ApiPay documents."""

from __future__ import annotations

import pytest

from app.payments.errors import DuplicateOrderError, ProviderRejected
from app.payments.fake import FakeProvider
from app.payments.provider import mask_phone


def test_a_phone_invoice_starts_pending() -> None:
    provider = FakeProvider(webhook_secret="whsec")
    invoice = provider.create_phone_invoice(
        amount_kzt=4990, phone="87071234455", description="Case", external_order_id="ext-1"
    )
    assert invoice.status == "pending"
    assert invoice.invoice_id
    assert provider.get_invoice(invoice.invoice_id).status == "pending"


def test_a_qr_invoice_carries_a_payload_and_an_expiry() -> None:
    provider = FakeProvider(webhook_secret="whsec")
    invoice = provider.create_qr_invoice(
        amount_kzt=4990, description="Case", external_order_id="ext-2"
    )
    assert invoice.qr_payload
    assert invoice.qr_expires_at is not None


def test_the_same_external_order_id_is_refused() -> None:
    provider = FakeProvider(webhook_secret="whsec")
    provider.create_phone_invoice(
        amount_kzt=4990, phone="87071234455", description="Case", external_order_id="ext-dup"
    )
    with pytest.raises(DuplicateOrderError):
        provider.create_phone_invoice(
            amount_kzt=4990, phone="87071234455", description="Case", external_order_id="ext-dup"
        )


def test_a_fractional_amount_is_refused_as_ApiPay_refuses_it() -> None:
    provider = FakeProvider(webhook_secret="whsec")
    with pytest.raises(ProviderRejected) as caught:
        provider.create_phone_invoice(
            amount_kzt=0, phone="87071234455", description="Case", external_order_id="ext-3"
        )
    assert caught.value.code == "amount_must_be_whole_tenge"


def test_a_malformed_phone_is_refused() -> None:
    provider = FakeProvider(webhook_secret="whsec")
    with pytest.raises(ProviderRejected) as caught:
        provider.create_phone_invoice(
            amount_kzt=4990, phone="+77071234455", description="Case", external_order_id="ext-4"
        )
    assert caught.value.code == "validation_failed"


def test_simulation_moves_an_invoice_to_paid() -> None:
    provider = FakeProvider(webhook_secret="whsec")
    invoice = provider.create_phone_invoice(
        amount_kzt=4990, phone="87071234455", description="Case", external_order_id="ext-5"
    )
    provider.simulate(invoice.invoice_id, "paid")
    assert provider.get_invoice(invoice.invoice_id).status == "paid"


def test_a_valid_signature_is_accepted_and_a_tampered_body_is_not() -> None:
    provider = FakeProvider(webhook_secret="whsec")
    body = b'{"event":"invoice.status_changed","status":"paid"}'
    signature = provider.sign(body)
    assert provider.verify_webhook(body, signature) is True
    assert provider.verify_webhook(body + b" ", signature) is False
    assert provider.verify_webhook(body, "sha256=deadbeef") is False
    assert provider.verify_webhook(body, "") is False


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("87071234455", "8707***4455"),
        ("87010000000", "8701***0000"),
    ],
)
def test_a_phone_is_stored_masked(raw: str, expected: str) -> None:
    assert mask_phone(raw) == expected


def test_masking_never_returns_the_original() -> None:
    assert mask_phone("87071234455") != "87071234455"
```

- [ ] **Step 2: Run it and watch it fail**

Run: `python -m pytest tests/test_payment_provider.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.payments'`.

- [ ] **Step 3: Write the errors**

Create `backend/app/payments/__init__.py` containing only a docstring:

```python
"""Payments: the provider seam, entitlements, and the order lifecycle."""
```

Create `backend/app/payments/errors.py`:

```python
"""Provider failures, named after what ApiPay actually returns.

Anything the caller must react to differently gets its own class. Everything
else is a ``ProviderRejected`` carrying the provider's own error code, so a
code we have not seen before still reaches the logs intact.
"""

from __future__ import annotations


class PaymentError(RuntimeError):
    """Base class. Never raised directly."""

    code = "payment_error"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        if code:
            self.code = code


class DuplicateOrderError(PaymentError):
    """The provider already has an invoice for this external_order_id."""

    code = "duplicate_idempotency_key"


class ProviderUnavailable(PaymentError):
    """A transport failure or a 5xx. Safe to retry."""

    code = "provider_unavailable"


class ProviderRejected(PaymentError):
    """The provider refused the request and will refuse it again unchanged."""

    code = "provider_rejected"


class TariffInactive(PaymentError):
    """Our own ApiPay subscription has lapsed. No customer can pay until it is fixed."""

    code = "tariff_inactive"


class SessionExpired(PaymentError):
    """The Kaspi cashier session needs re-authorising in the ApiPay dashboard."""

    code = "kaspi_session_expired"


class RateLimited(PaymentError):
    code = "request_rate_limited"

    def __init__(self, message: str, *, retry_after: int = 1) -> None:
        super().__init__(message)
        self.retry_after = retry_after
```

- [ ] **Step 4: Write the Protocol**

Create `backend/app/payments/provider.py`:

```python
"""The seam every payment provider sits behind.

The application never imports a provider directly. It asks ``get_provider``,
which is what makes the fake usable in every test and the real adapter a
configuration change rather than a code change.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable

#: Statuses as the provider words them. Translation to our own vocabulary
#: happens once, in app.payments.service.
PROVIDER_PENDING = frozenset({"pending", "processing", "qr_scanned"})
PROVIDER_PAID = frozenset({"paid"})
PROVIDER_CANCELLED = frozenset({"cancelled"})
PROVIDER_EXPIRED = frozenset({"expired"})


def mask_phone(phone: str) -> str:
    """`87071234455` -> `8707***4455`. The most of a payer's number we may keep.

    Lives here rather than beside the fake because production code calls it,
    and production code must never import from a test double.
    """
    digits = re.sub(r"\D", "", phone)
    if len(digits) < 8:
        return "***"
    return f"{digits[:4]}***{digits[-4:]}"


@dataclass(frozen=True)
class ProviderInvoice:
    invoice_id: str
    status: str
    qr_payload: str = ""
    qr_expires_at: datetime | None = None


@runtime_checkable
class PaymentProvider(Protocol):
    def create_phone_invoice(
        self, *, amount_kzt: int, phone: str, description: str, external_order_id: str
    ) -> ProviderInvoice: ...

    def create_qr_invoice(
        self, *, amount_kzt: int, description: str, external_order_id: str
    ) -> ProviderInvoice: ...

    def get_invoice(self, invoice_id: str) -> ProviderInvoice: ...

    def cancel_invoice(self, invoice_id: str) -> None: ...

    def verify_webhook(self, raw_body: bytes, signature: str) -> bool: ...


def get_provider() -> PaymentProvider:
    """The configured provider. Called per request; construction is cheap."""
    from app.config import get_settings

    settings = get_settings()
    if settings.payments_provider == "apipay":
        from app.payments.apipay import ApiPayProvider

        return ApiPayProvider(
            base_url=settings.apipay_base_url,
            api_key=settings.apipay_api_key.get_secret_value(),
            webhook_secret=settings.apipay_webhook_secret.get_secret_value(),
            timeout_seconds=settings.apipay_timeout_seconds,
        )
    from app.payments.fake import get_shared_fake

    return get_shared_fake(settings.apipay_webhook_secret.get_secret_value() or "test-secret")
```

- [ ] **Step 5: Write the fake**

Create `backend/app/payments/fake.py`:

```python
"""A provider that behaves the way ApiPay documents, without a network.

Every rejection it raises corresponds to an error code in ApiPay's published
OpenAPI document. If the real adapter and this one ever disagree about what a
failure looks like, this file is the one to correct.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import uuid
from datetime import timedelta

from app.models.base import utcnow
from app.payments.errors import DuplicateOrderError, ProviderRejected
from app.payments.provider import ProviderInvoice

#: ApiPay accepts a payer phone as 11 digits beginning with 8.
PHONE_PATTERN = re.compile(r"^8\d{10}$")
#: A QR invoice lives minutes, not hours.
QR_TTL = timedelta(minutes=10)


class FakeProvider:
    def __init__(self, *, webhook_secret: str) -> None:
        self._secret = webhook_secret.encode()
        self._invoices: dict[str, ProviderInvoice] = {}
        self._by_external: dict[str, str] = {}

    # -- creation ------------------------------------------------------
    def _create(self, *, amount_kzt: int, external_order_id: str, qr: bool) -> ProviderInvoice:
        if amount_kzt < 1:
            raise ProviderRejected(
                "Amount must be at least one whole tenge.", code="amount_must_be_whole_tenge"
            )
        if external_order_id in self._by_external:
            raise DuplicateOrderError("An invoice already exists for this order.")

        invoice = ProviderInvoice(
            invoice_id=uuid.uuid4().hex[:16],
            status="pending",
            qr_payload=f"https://pay.kaspi.invalid/{uuid.uuid4().hex[:12]}" if qr else "",
            qr_expires_at=utcnow() + QR_TTL if qr else None,
        )
        self._invoices[invoice.invoice_id] = invoice
        self._by_external[external_order_id] = invoice.invoice_id
        return invoice

    def create_phone_invoice(
        self, *, amount_kzt: int, phone: str, description: str, external_order_id: str
    ) -> ProviderInvoice:
        if not PHONE_PATTERN.fullmatch(phone):
            raise ProviderRejected("Enter the number as 8XXXXXXXXXX.", code="validation_failed")
        return self._create(amount_kzt=amount_kzt, external_order_id=external_order_id, qr=False)

    def create_qr_invoice(
        self, *, amount_kzt: int, description: str, external_order_id: str
    ) -> ProviderInvoice:
        return self._create(amount_kzt=amount_kzt, external_order_id=external_order_id, qr=True)

    # -- reading and control -------------------------------------------
    def get_invoice(self, invoice_id: str) -> ProviderInvoice:
        invoice = self._invoices.get(invoice_id)
        if invoice is None:
            raise ProviderRejected("No such invoice.", code="not_found")
        return invoice

    def cancel_invoice(self, invoice_id: str) -> None:
        self.simulate(invoice_id, "cancelled")

    def simulate(self, invoice_id: str, status: str) -> ProviderInvoice:
        """The sandbox's simulate-status, without the sandbox."""
        current = self.get_invoice(invoice_id)
        moved = ProviderInvoice(
            invoice_id=current.invoice_id,
            status=status,
            qr_payload=current.qr_payload,
            qr_expires_at=current.qr_expires_at,
        )
        self._invoices[invoice_id] = moved
        return moved

    # -- webhooks ------------------------------------------------------
    def sign(self, raw_body: bytes) -> str:
        return "sha256=" + hmac.new(self._secret, raw_body, hashlib.sha256).hexdigest()

    def verify_webhook(self, raw_body: bytes, signature: str) -> bool:
        if not signature:
            return False
        return hmac.compare_digest(self.sign(raw_body), signature)


_shared: FakeProvider | None = None


def get_shared_fake(secret: str) -> FakeProvider:
    """One instance per process, so a test can simulate what a route created."""
    global _shared
    if _shared is None or _shared._secret != secret.encode():
        _shared = FakeProvider(webhook_secret=secret)
    return _shared


def reset_shared_fake() -> None:
    global _shared
    _shared = None
```

- [ ] **Step 6: Run the tests and watch them pass**

Run: `python -m pytest tests/test_payment_provider.py -q`
Expected: PASS, 10 tests.

- [ ] **Step 7: Full suite, lint, types**

Run: `python -m pytest -q && ruff check . && mypy app`
Expected: 572 passed, clean.

- [ ] **Step 8: Commit**

```bash
git add backend/app/payments backend/tests/test_payment_provider.py
git commit -m "feat(payments): provider seam, named errors, and a fake that matches the spec"
```

---

### Task 4: Entitlements and the free-tier projection

**Files:**
- Create: `backend/app/payments/entitlements.py`
- Test: `backend/tests/test_entitlements.py`

**Interfaces:**
- Consumes: `Entitlement`, `EntitlementKind` (Task 2); `Settings` (Task 1).
- Produces:
  - `has_full_access(session: Session, organization_id: str, profile_id: str) -> bool`
  - `grant_case_access(session: Session, *, organization_id: str, profile_id: str, order_id: str | None, source: str) -> Entitlement`
  - `free_view(result: ProgramResult) -> ProgramResult`
  - `truncate_shortlist(results: list[ProgramResult], limit: int) -> list[ProgramResult]`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_entitlements.py`:

```python
"""Who may see what, and exactly what a free row withholds."""

from __future__ import annotations

from app.models.billing import EntitlementKind, EntitlementSource
from app.payments.entitlements import (
    free_view,
    grant_case_access,
    has_full_access,
    truncate_shortlist,
)
from app.schemas.result import ProgramResult


def _result(index: int = 0) -> ProgramResult:
    return ProgramResult(
        id=f"r{index}",
        run_id="run1",
        university="Test University",
        university_id="u1",
        country="Netherlands",
        city="Delft",
        program="Computer Science",
        degree="bachelor",
        intake="fall 2027",
        source_urls=["https://example.edu/a", "https://example.edu/b"],
        career_notes="Strong graduate outcomes.",
    )


def test_no_entitlement_means_no_access(pg_session) -> None:
    assert has_full_access(pg_session, "org1", "case1") is False


def test_granting_makes_access_true(pg_session) -> None:
    grant_case_access(
        pg_session,
        organization_id="org1",
        profile_id="case1",
        order_id="order1",
        source=EntitlementSource.PURCHASE.value,
    )
    pg_session.flush()
    assert has_full_access(pg_session, "org1", "case1") is True


def test_granting_twice_grants_once(pg_session) -> None:
    for _ in range(2):
        grant_case_access(
            pg_session,
            organization_id="org1",
            profile_id="case1",
            order_id="order1",
            source=EntitlementSource.PURCHASE.value,
        )
        pg_session.flush()
    from app.models.billing import Entitlement

    assert pg_session.query(Entitlement).count() == 1


def test_another_organization_is_not_covered(pg_session) -> None:
    grant_case_access(
        pg_session,
        organization_id="org1",
        profile_id="case1",
        order_id=None,
        source=EntitlementSource.MANUAL.value,
    )
    pg_session.flush()
    assert has_full_access(pg_session, "org2", "case1") is False


def test_an_organization_wide_entitlement_covers_every_case(pg_session) -> None:
    """Phase 2 inserts this row. Phase 1 must already honour it."""
    from app.models.billing import Entitlement

    pg_session.add(
        Entitlement(
            organization_id="org1",
            profile_id=None,
            kind=EntitlementKind.ORG_SUBSCRIPTION.value,
            source=EntitlementSource.SUBSCRIPTION.value,
        )
    )
    pg_session.flush()
    assert has_full_access(pg_session, "org1", "any-case") is True


def test_a_free_row_keeps_identity_and_drops_evidence() -> None:
    free = free_view(_result())
    assert free.university == "Test University"
    assert free.program == "Computer Science"
    assert free.country == "Netherlands"
    assert free.degree == "bachelor"
    # Everything a buyer is paying for is gone.
    assert free.source_urls == []
    assert free.claims == []
    assert free.scholarships == []
    assert free.requirement_checks == []
    assert free.conflicts == []
    assert free.unresolved == []
    assert free.funding_gap is None
    assert free.career_notes == ""


def test_the_projection_does_not_mutate_its_input() -> None:
    original = _result()
    free_view(original)
    assert original.source_urls == ["https://example.edu/a", "https://example.edu/b"]
    assert original.career_notes == "Strong graduate outcomes."


def test_the_shortlist_is_cut_to_the_free_limit() -> None:
    rows = [_result(i) for i in range(12)]
    assert len(truncate_shortlist(rows, 5)) == 5
    assert truncate_shortlist(rows, 5)[0].id == "r0"


def test_a_shorter_shortlist_is_left_alone() -> None:
    rows = [_result(i) for i in range(3)]
    assert len(truncate_shortlist(rows, 5)) == 3
```

- [ ] **Step 2: Run it and watch it fail**

Run: `python -m pytest tests/test_entitlements.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.payments.entitlements'`.

- [ ] **Step 3: Write it**

Create `backend/app/payments/entitlements.py`:

```python
"""What an organization may see, and what a free row withholds.

Deliberately close to pure: one query, and one projection with no side effects.
The rules a customer is paying for should be readable in one screen.
"""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.billing import Entitlement, EntitlementKind, EntitlementSource
from app.schemas.result import ProgramResult


def has_full_access(session: Session, organization_id: str, profile_id: str) -> bool:
    """True when this organization may see everything about this case.

    With payments disabled the product is exactly what it was before this
    feature existed, so the answer is always yes.
    """
    if not get_settings().payments_enabled:
        return True

    found = session.scalar(
        select(Entitlement.id).where(
            Entitlement.organization_id == organization_id,
            or_(
                # This case, bought outright.
                (Entitlement.kind == EntitlementKind.CASE_FULL.value)
                & (Entitlement.profile_id == profile_id),
                # Or the whole organization, under a subscription (phase 2).
                (Entitlement.kind == EntitlementKind.ORG_SUBSCRIPTION.value)
                & (Entitlement.profile_id.is_(None)),
            ),
        )
    )
    return found is not None


def grant_case_access(
    session: Session,
    *,
    organization_id: str,
    profile_id: str,
    order_id: str | None,
    source: str = EntitlementSource.PURCHASE.value,
) -> Entitlement:
    """Idempotent. Granting an entitlement that exists returns the existing one."""
    existing = session.scalar(
        select(Entitlement).where(
            Entitlement.organization_id == organization_id,
            Entitlement.profile_id == profile_id,
            Entitlement.kind == EntitlementKind.CASE_FULL.value,
        )
    )
    if existing is not None:
        return existing

    granted = Entitlement(
        organization_id=organization_id,
        profile_id=profile_id,
        kind=EntitlementKind.CASE_FULL.value,
        source=source,
        order_id=order_id,
    )
    session.add(granted)
    return granted


#: What a free row keeps: enough to know the programme exists and roughly how
#: well it fits. Everything that took a fetch to establish is withheld.
def free_view(result: ProgramResult) -> ProgramResult:
    """A copy of one row with the paid material removed."""
    trimmed = result.model_copy(deep=True)
    trimmed.source_urls = []
    trimmed.claims = []
    trimmed.scholarships = []
    trimmed.requirement_checks = []
    trimmed.missing_prerequisites = []
    trimmed.hard_filter_failures = []
    trimmed.conflicts = []
    trimmed.unresolved = []
    trimmed.funding_gap = None
    trimmed.checklist = None
    trimmed.career_notes = ""
    trimmed.post_study_work = ""
    trimmed.work_during_study = ""
    trimmed.admission_deadline_raw = None
    trimmed.verification_completeness = 0.0
    return trimmed


def truncate_shortlist(results: list[ProgramResult], limit: int) -> list[ProgramResult]:
    """The highest-scoring rows only. The list arrives already ordered."""
    return results[:limit]
```

- [ ] **Step 4: Run the tests and watch them pass**

Run: `python -m pytest tests/test_entitlements.py -q`
Expected: PASS, 9 tests.

If `test_no_entitlement_means_no_access` passes for the wrong reason — because `payments_enabled` is false — add a fixture to that module that forces it true:

```python
import pytest


@pytest.fixture(autouse=True)
def payments_on(monkeypatch):
    from app.config import Settings, get_settings

    settings = Settings(payments_enabled=True)
    get_settings.cache_clear()
    monkeypatch.setattr("app.config.get_settings", lambda: settings)
    monkeypatch.setattr("app.payments.entitlements.get_settings", lambda: settings)
    yield
    get_settings.cache_clear()
```

- [ ] **Step 5: Full suite, lint, types**

Run: `python -m pytest -q && ruff check . && mypy app`
Expected: 581 passed, clean.

- [ ] **Step 6: Commit**

```bash
git add backend/app/payments/entitlements.py backend/tests/test_entitlements.py
git commit -m "feat(payments): entitlement lookup and the free-tier projection"
```

---

### Task 5: The order service and its single idempotent writer

**Files:**
- Create: `backend/app/payments/service.py`
- Test: `backend/tests/test_payment_service.py`

**Interfaces:**
- Consumes: everything from Tasks 1–4; `JobStore` from `app.jobs.store`.
- Produces:
  - `create_order(session, *, organization_id: str, profile_id: str, method: str, phone: str | None) -> Order`
  - `apply_status(session, order: Order, provider_status: str, *, source: str, event_type: str = "") -> Order`
  - `cancel_order(session, order: Order) -> Order`
  - `to_order_status(provider_status: str) -> str`
  - `AlreadyEntitled`, `InvalidPaymentRequest` exceptions.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_payment_service.py`:

```python
"""The order lifecycle: one writer, idempotent, and indifferent to arrival order."""

from __future__ import annotations

import pytest

from app.models.billing import Order, OrderStatus, PaymentEvent, PaymentMethod
from app.payments.entitlements import has_full_access
from app.payments.service import (
    AlreadyEntitled,
    InvalidPaymentRequest,
    apply_status,
    cancel_order,
    create_order,
    to_order_status,
)


@pytest.fixture(autouse=True)
def payments_on(monkeypatch):
    from app.config import Settings, get_settings
    from app.payments.fake import reset_shared_fake

    settings = Settings(payments_enabled=True, payments_provider="fake")
    get_settings.cache_clear()
    reset_shared_fake()
    for target in (
        "app.config.get_settings",
        "app.payments.entitlements.get_settings",
        "app.payments.service.get_settings",
        "app.payments.provider.get_settings",
    ):
        monkeypatch.setattr(target, lambda: settings, raising=False)
    yield
    get_settings.cache_clear()
    reset_shared_fake()


@pytest.mark.parametrize(
    ("provider_status", "expected"),
    [
        ("processing", OrderStatus.PENDING.value),
        ("pending", OrderStatus.PENDING.value),
        ("qr_scanned", OrderStatus.PENDING.value),
        ("paid", OrderStatus.PAID.value),
        ("cancelled", OrderStatus.CANCELLED.value),
        ("expired", OrderStatus.EXPIRED.value),
        ("something_new", OrderStatus.PENDING.value),
    ],
)
def test_provider_vocabulary_maps_to_ours(provider_status: str, expected: str) -> None:
    assert to_order_status(provider_status) == expected


def test_creating_a_phone_order_stores_a_masked_number(pg_session) -> None:
    order = create_order(
        pg_session,
        organization_id="org1",
        profile_id="case1",
        method=PaymentMethod.PHONE.value,
        phone="87071234455",
    )
    assert order.phone_masked == "8707***4455"
    assert "1234455" not in order.phone_masked
    assert order.amount_kzt == 4990
    assert order.status == OrderStatus.PENDING.value
    assert order.provider_invoice_id


def test_creating_a_qr_order_stores_the_payload_and_expiry(pg_session) -> None:
    order = create_order(
        pg_session,
        organization_id="org1",
        profile_id="case1",
        method=PaymentMethod.QR.value,
        phone=None,
    )
    assert order.qr_payload
    assert order.qr_expires_at is not None
    assert order.phone_masked == ""


def test_a_phone_order_without_a_phone_is_refused(pg_session) -> None:
    with pytest.raises(InvalidPaymentRequest):
        create_order(
            pg_session,
            organization_id="org1",
            profile_id="case1",
            method=PaymentMethod.PHONE.value,
            phone=None,
        )


def test_a_second_order_for_the_same_case_reuses_the_open_one(pg_session) -> None:
    first = create_order(
        pg_session, organization_id="org1", profile_id="case1",
        method=PaymentMethod.PHONE.value, phone="87071234455",
    )
    pg_session.flush()
    second = create_order(
        pg_session, organization_id="org1", profile_id="case1",
        method=PaymentMethod.PHONE.value, phone="87071234455",
    )
    assert second.id == first.id
    assert pg_session.query(Order).count() == 1


def test_an_already_unlocked_case_cannot_be_bought_again(pg_session) -> None:
    order = create_order(
        pg_session, organization_id="org1", profile_id="case1",
        method=PaymentMethod.PHONE.value, phone="87071234455",
    )
    apply_status(pg_session, order, "paid", source="webhook")
    pg_session.flush()
    with pytest.raises(AlreadyEntitled):
        create_order(
            pg_session, organization_id="org1", profile_id="case1",
            method=PaymentMethod.PHONE.value, phone="87071234455",
        )


def test_paying_grants_access_and_records_the_moment(pg_session) -> None:
    order = create_order(
        pg_session, organization_id="org1", profile_id="case1",
        method=PaymentMethod.PHONE.value, phone="87071234455",
    )
    apply_status(pg_session, order, "paid", source="webhook")
    pg_session.flush()
    assert order.status == OrderStatus.PAID.value
    assert order.paid_at is not None
    assert has_full_access(pg_session, "org1", "case1") is True


def test_a_replayed_paid_event_grants_once(pg_session) -> None:
    from app.models.billing import Entitlement

    order = create_order(
        pg_session, organization_id="org1", profile_id="case1",
        method=PaymentMethod.PHONE.value, phone="87071234455",
    )
    for _ in range(3):
        apply_status(pg_session, order, "paid", source="webhook")
        pg_session.flush()
    assert pg_session.query(Entitlement).count() == 1


def test_a_late_pending_cannot_undo_a_paid(pg_session) -> None:
    order = create_order(
        pg_session, organization_id="org1", profile_id="case1",
        method=PaymentMethod.PHONE.value, phone="87071234455",
    )
    apply_status(pg_session, order, "paid", source="webhook")
    apply_status(pg_session, order, "processing", source="poll")
    pg_session.flush()
    assert order.status == OrderStatus.PAID.value
    assert has_full_access(pg_session, "org1", "case1") is True


def test_paid_after_a_local_cancellation_still_grants(pg_session) -> None:
    """A QR cannot be cancelled at ApiPay, so a paid webhook can follow ours."""
    order = create_order(
        pg_session, organization_id="org1", profile_id="case1",
        method=PaymentMethod.QR.value, phone=None,
    )
    cancel_order(pg_session, order)
    apply_status(pg_session, order, "paid", source="webhook")
    pg_session.flush()
    assert order.status == OrderStatus.PAID.value
    assert has_full_access(pg_session, "org1", "case1") is True


def test_every_call_is_journalled_even_when_nothing_changed(pg_session) -> None:
    order = create_order(
        pg_session, organization_id="org1", profile_id="case1",
        method=PaymentMethod.PHONE.value, phone="87071234455",
    )
    apply_status(pg_session, order, "paid", source="webhook")
    apply_status(pg_session, order, "paid", source="poll")
    pg_session.flush()
    events = pg_session.query(PaymentEvent).filter(PaymentEvent.order_id == order.id).all()
    assert len(events) == 2
    assert {e.source for e in events} == {"webhook", "poll"}


def test_the_journal_never_holds_a_phone_number(pg_session) -> None:
    order = create_order(
        pg_session, organization_id="org1", profile_id="case1",
        method=PaymentMethod.PHONE.value, phone="87071234455",
    )
    apply_status(pg_session, order, "paid", source="webhook")
    pg_session.flush()
    for event in pg_session.query(PaymentEvent).all():
        assert "87071234455" not in (event.detail or "")
```

- [ ] **Step 2: Run it and watch it fail**

Run: `python -m pytest tests/test_payment_service.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.payments.service'`.

- [ ] **Step 3: Write the service**

Create `backend/app/payments/service.py`:

```python
"""Creating an order, and the one place an order's status may change.

``apply_status`` is the single writer. A webhook and the reconciler both call
it, so idempotence and order-insensitivity live in exactly one function rather
than being re-argued at each call site.
"""

from __future__ import annotations

import json
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.jobs.store import JobStore
from app.models.base import utcnow
from app.models.billing import (
    TERMINAL_ORDER_STATUSES,
    Order,
    OrderKind,
    OrderStatus,
    PaymentEvent,
    PaymentMethod,
)
from app.payments.entitlements import grant_case_access, has_full_access
from app.payments.errors import PaymentError
from app.payments.provider import (
    PROVIDER_CANCELLED,
    PROVIDER_EXPIRED,
    PROVIDER_PAID,
    get_provider,
    mask_phone,
)


class AlreadyEntitled(PaymentError):
    """The case is already unlocked. Selling it twice would be a bug."""

    code = "already_entitled"


class InvalidPaymentRequest(PaymentError):
    code = "invalid_payment_request"


def to_order_status(provider_status: str) -> str:
    """Translate the provider's vocabulary into ours, once.

    An unrecognised status is treated as pending: the reconciler will ask
    again, which is safer than inventing a terminal state.
    """
    if provider_status in PROVIDER_PAID:
        return OrderStatus.PAID.value
    if provider_status in PROVIDER_CANCELLED:
        return OrderStatus.CANCELLED.value
    if provider_status in PROVIDER_EXPIRED:
        return OrderStatus.EXPIRED.value
    return OrderStatus.PENDING.value


def _open_order(session: Session, organization_id: str, profile_id: str) -> Order | None:
    return session.scalar(
        select(Order).where(
            Order.organization_id == organization_id,
            Order.profile_id == profile_id,
            Order.kind == OrderKind.CASE_UNLOCK.value,
            Order.status.notin_(tuple(TERMINAL_ORDER_STATUSES)),
        )
    )


def create_order(
    session: Session,
    *,
    organization_id: str,
    profile_id: str,
    method: str,
    phone: str | None,
) -> Order:
    """Open an invoice for this case, or hand back the one already open."""
    if has_full_access(session, organization_id, profile_id):
        raise AlreadyEntitled("This case is already unlocked.")

    if method not in {PaymentMethod.PHONE.value, PaymentMethod.QR.value}:
        raise InvalidPaymentRequest("Choose payment by phone or by QR.")
    if method == PaymentMethod.PHONE.value and not phone:
        raise InvalidPaymentRequest("Enter the phone number registered with Kaspi.")

    existing = _open_order(session, organization_id, profile_id)
    if existing is not None:
        return existing

    settings = get_settings()
    provider = get_provider()
    external_order_id = f"case-{profile_id[:12]}-{uuid.uuid4().hex[:8]}"
    description = "ASHYQ Apply — full report for one case"

    if method == PaymentMethod.PHONE.value:
        assert phone is not None  # guarded above; narrows the type for mypy
        invoice = provider.create_phone_invoice(
            amount_kzt=settings.case_unlock_price_kzt,
            phone=phone,
            description=description,
            external_order_id=external_order_id,
        )
    else:
        invoice = provider.create_qr_invoice(
            amount_kzt=settings.case_unlock_price_kzt,
            description=description,
            external_order_id=external_order_id,
        )

    order = Order(
        organization_id=organization_id,
        profile_id=profile_id,
        kind=OrderKind.CASE_UNLOCK.value,
        amount_kzt=settings.case_unlock_price_kzt,
        status=to_order_status(invoice.status),
        provider=settings.payments_provider,
        provider_invoice_id=invoice.invoice_id,
        external_order_id=external_order_id,
        method=method,
        phone_masked=mask_phone(phone) if phone else "",
        qr_payload=invoice.qr_payload,
        qr_expires_at=invoice.qr_expires_at,
    )
    session.add(order)
    session.flush()

    JobStore(session).enqueue(
        "payment_reconcile",
        payload={"order_id": order.id},
        idempotency_key=f"payment_reconcile:{order.id}",
        priority=1,
        max_attempts=30,
    )
    return order


def apply_status(
    session: Session,
    order: Order,
    provider_status: str,
    *,
    source: str,
    event_type: str = "",
) -> Order:
    """The only place an order's status changes. Safe to call repeatedly.

    Rules, in order of precedence:
      1. Every call is journalled, including calls that change nothing.
      2. ``paid`` always wins, even after a local cancellation — money moved.
      3. A terminal status is never replaced by a non-terminal one.
    """
    target = to_order_status(provider_status)

    session.add(
        PaymentEvent(
            order_id=order.id,
            source=source,
            event_type=event_type,
            provider_status=provider_status,
            signature_valid=True,
            detail=json.dumps({"target": target, "from": order.status}),
        )
    )

    if order.status == target:
        return order
    if target == OrderStatus.PAID.value:
        order.status = OrderStatus.PAID.value
        order.paid_at = order.paid_at or utcnow()
        _grant_and_schedule(session, order)
        return order
    if order.status in TERMINAL_ORDER_STATUSES:
        # A late non-terminal update cannot reopen a settled order.
        return order

    order.status = target
    return order


def _grant_and_schedule(session: Session, order: Order) -> None:
    """Unlock the case, then queue the full run the customer just bought."""
    grant_case_access(
        session,
        organization_id=order.organization_id,
        profile_id=order.profile_id,
        order_id=order.id,
    )
    from app.models import ResearchRun

    run = ResearchRun(
        profile_id=order.profile_id,
        stage="queued",
        access_tier="full",
        stage_state={},
    )
    session.add(run)
    session.flush()
    JobStore(session).enqueue(
        "research",
        run_id=run.id,
        idempotency_key=f"research:{run.id}",
        priority=0,
    )


def cancel_order(session: Session, order: Order) -> Order:
    """Stop chasing this order.

    ApiPay cannot cancel a QR invoice, so for QR this is local only: if the
    customer pays it anyway, ``apply_status`` still grants on the webhook.
    """
    if order.status in TERMINAL_ORDER_STATUSES:
        return order
    if order.method == PaymentMethod.PHONE.value and order.provider_invoice_id:
        try:
            get_provider().cancel_invoice(order.provider_invoice_id)
        except PaymentError:
            # The provider's refusal does not stop us from closing our side.
            pass
    order.status = OrderStatus.CANCELLED.value
    session.add(
        PaymentEvent(
            order_id=order.id,
            source="local",
            event_type="order.cancelled",
            provider_status="cancelled",
            signature_valid=True,
        )
    )
    return order
```

Note: `ResearchRun(stage_state={})` must match how `routes_research.start_run` builds it. Open `backend/app/api/routes_research.py:165` and copy the exact expression it uses (`RunState.load(None).dump()`), importing `RunState` the same way that module does.

- [ ] **Step 4: Run the tests and watch them pass**

Run: `python -m pytest tests/test_payment_service.py -q`
Expected: PASS, 18 tests (7 parametrised plus 11).

- [ ] **Step 5: Full suite, lint, types**

Run: `python -m pytest -q && ruff check . && mypy app`
Expected: 599 passed, clean. The `payment_reconcile` job kind is not handled by the worker yet; that is Task 9 and no existing test drives it.

- [ ] **Step 6: Commit**

```bash
git add backend/app/payments/service.py backend/tests/test_payment_service.py
git commit -m "feat(payments): order lifecycle with one idempotent writer"
```

---

### Task 6: Billing routes and the 402

**Files:**
- Create: `backend/app/api/routes_billing.py`
- Modify: `backend/app/main.py` (register the router and the exception handler)
- Create: `backend/app/payments/http.py`
- Test: `backend/tests/test_billing_api.py`

**Interfaces:**
- Consumes: Tasks 1–5.
- Produces:
  - `PaymentRequired(profile_id: str, price_kzt: int)` exception plus its handler, rendering `{"detail": str, "code": "payment_required", "profile_id": str, "price_kzt": int}` with status 402.
  - Routes: `GET /api/billing/pricing`, `GET /api/billing/entitlements`, `POST /api/billing/orders`, `GET /api/billing/orders/{order_id}`, `POST /api/billing/orders/{order_id}/cancel`.
  - `OrderView` response model: `id`, `status`, `method`, `amount_kzt`, `profile_id`, `phone_masked`, `qr_payload`, `qr_expires_at`, `created_at`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_billing_api.py`:

```python
"""The billing endpoints, and the 402 the frontend keys off."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.corpus.demo_profile import DEMO_PROFILE


@pytest.fixture
def paid_client(tmp_path, monkeypatch, corpus_dir):
    """A client with payments switched on and the fake provider behind them."""
    from app.config import Settings, get_settings
    from app.payments.fake import reset_shared_fake

    settings = Settings(
        demo_mode=True,
        database_url=f"sqlite:///{tmp_path / 'billing.db'}",
        cache_dir=tmp_path / "cache",
        export_dir=tmp_path / "exports",
        corpus_dir=corpus_dir,
        fetch_delay_seconds=0.0,
        enable_browser_tier=False,
        payments_enabled=True,
        payments_provider="fake",
        apipay_webhook_secret="whsec-test",
    )
    settings.ensure_dirs()
    get_settings.cache_clear()
    reset_shared_fake()
    monkeypatch.setattr("app.config.get_settings", lambda: settings)

    import app.db as db_module

    engine = db_module.create_engine(
        settings.database_url, connect_args={"check_same_thread": False}
    )
    monkeypatch.setattr(db_module, "engine", engine)
    monkeypatch.setattr(db_module, "SessionLocal", db_module.sessionmaker(bind=engine, future=True))
    db_module.migrate_to_head(settings.database_url)

    from app.main import app

    with TestClient(app) as c:
        yield c
    get_settings.cache_clear()
    reset_shared_fake()


@pytest.fixture
def case_id(paid_client) -> str:
    return paid_client.post("/api/profiles", json=DEMO_PROFILE.model_dump(mode="json")).json()["id"]


def test_pricing_states_the_amount_and_the_currency(paid_client) -> None:
    body = paid_client.get("/api/billing/pricing").json()
    assert body["case_unlock_price_kzt"] == 4990
    assert body["currency"] == "KZT"
    assert isinstance(body["includes"], list) and body["includes"]


def test_a_new_case_has_no_entitlement(paid_client, case_id) -> None:
    body = paid_client.get(f"/api/billing/entitlements?profile_id={case_id}").json()
    assert body["full_access"] is False


def test_creating_a_phone_order(paid_client, case_id) -> None:
    response = paid_client.post(
        "/api/billing/orders",
        json={"profile_id": case_id, "method": "phone", "phone": "87071234455"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending"
    assert body["phone_masked"] == "8707***4455"
    assert body["amount_kzt"] == 4990


def test_the_client_cannot_choose_the_price(paid_client, case_id) -> None:
    body = paid_client.post(
        "/api/billing/orders",
        json={"profile_id": case_id, "method": "phone", "phone": "87071234455",
              "amount_kzt": 1, "price_kzt": 1},
    ).json()
    assert body["amount_kzt"] == 4990


def test_creating_a_qr_order_returns_a_payload(paid_client, case_id) -> None:
    body = paid_client.post(
        "/api/billing/orders", json={"profile_id": case_id, "method": "qr"}
    ).json()
    assert body["qr_payload"]
    assert body["qr_expires_at"]


def test_a_phone_order_without_a_number_is_rejected(paid_client, case_id) -> None:
    response = paid_client.post(
        "/api/billing/orders", json={"profile_id": case_id, "method": "phone"}
    )
    assert response.status_code == 400


def test_an_unknown_case_is_not_purchasable(paid_client) -> None:
    response = paid_client.post(
        "/api/billing/orders",
        json={"profile_id": "0" * 32, "method": "phone", "phone": "87071234455"},
    )
    assert response.status_code == 404


def test_an_order_can_be_read_back_and_cancelled(paid_client, case_id) -> None:
    order = paid_client.post(
        "/api/billing/orders",
        json={"profile_id": case_id, "method": "phone", "phone": "87071234455"},
    ).json()
    assert paid_client.get(f"/api/billing/orders/{order['id']}").json()["id"] == order["id"]
    cancelled = paid_client.post(f"/api/billing/orders/{order['id']}/cancel").json()
    assert cancelled["status"] == "cancelled"


def test_another_tenants_order_is_invisible(paid_client, case_id) -> None:
    """404, not 403 — the same convention the rest of the API follows."""
    order = paid_client.post(
        "/api/billing/orders",
        json={"profile_id": case_id, "method": "phone", "phone": "87071234455"},
    ).json()

    from app.db import session_scope
    from app.models.billing import Order

    with session_scope() as session:
        session.get(Order, order["id"]).organization_id = "some-other-org"

    assert paid_client.get(f"/api/billing/orders/{order['id']}").status_code == 404
```

- [ ] **Step 2: Run it and watch it fail**

Run: `python -m pytest tests/test_billing_api.py -q`
Expected: FAIL — 404 on `/api/billing/pricing`, because the router does not exist.

- [ ] **Step 3: Write the 402 exception and its handler**

Create `backend/app/payments/http.py`:

```python
"""The 402 the frontend keys off.

FastAPI's HTTPException would give us a bare ``detail``. The frontend needs to
know which case to sell and for how much, so this carries both — in the shape
``api/client.ts`` already parses: a string ``detail`` and a top-level ``code``.
"""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse


class PaymentRequired(Exception):
    def __init__(self, profile_id: str, price_kzt: int) -> None:
        super().__init__("This case has not been unlocked.")
        self.profile_id = profile_id
        self.price_kzt = price_kzt


async def payment_required_handler(_request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, PaymentRequired)
    return JSONResponse(
        status_code=402,
        content={
            "detail": "Unlock this case to see the full report.",
            "code": "payment_required",
            "profile_id": exc.profile_id,
            "price_kzt": exc.price_kzt,
        },
    )
```

- [ ] **Step 4: Write the routes**

Create `backend/app/api/routes_billing.py`:

```python
"""Buying the full report for one case."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.tenancy import owned_profile
from app.config import get_settings
from app.db import get_session
from app.models import AuditEvent
from app.models.billing import Order
from app.payments.entitlements import has_full_access
from app.payments.errors import PaymentError
from app.payments.service import AlreadyEntitled, InvalidPaymentRequest, cancel_order, create_order
from app.security import Principal, get_principal

router = APIRouter(prefix="/api/billing", tags=["billing"])


class Pricing(BaseModel):
    case_unlock_price_kzt: int
    currency: str = "KZT"
    payments_enabled: bool
    includes: list[str]


class EntitlementView(BaseModel):
    profile_id: str
    full_access: bool


class CreateOrderIn(BaseModel):
    """Note what is absent: the price. The server decides that."""

    profile_id: str
    method: str = "phone"
    phone: str | None = None


class OrderView(BaseModel):
    id: str
    profile_id: str
    status: str
    method: str
    amount_kzt: int
    phone_masked: str
    qr_payload: str
    qr_expires_at: datetime | None
    created_at: datetime


def _view(order: Order) -> OrderView:
    return OrderView(
        id=order.id,
        profile_id=order.profile_id,
        status=order.status,
        method=order.method,
        amount_kzt=order.amount_kzt,
        phone_masked=order.phone_masked,
        qr_payload=order.qr_payload,
        qr_expires_at=order.qr_expires_at,
        created_at=order.created_at,
    )


def _owned_order(session: Session, order_id: str, principal: Principal) -> Order:
    order = session.get(Order, order_id)
    if order is None or order.organization_id != principal.organization_id:
        # 404, not 403: another tenant's order does not exist as far as this one knows.
        raise HTTPException(404, "Order not found")
    return order


@router.get("/pricing", response_model=Pricing)
def pricing(_principal: Principal = Depends(get_principal)) -> Pricing:
    settings = get_settings()
    return Pricing(
        case_unlock_price_kzt=settings.case_unlock_price_kzt,
        payments_enabled=settings.payments_enabled,
        includes=[
            "Full programme coverage rather than the first few matches",
            "Every value traced to its official source",
            "Funding, costs and the gap between them",
            "Document checklist and export",
        ],
    )


@router.get("/entitlements", response_model=EntitlementView)
def entitlements(
    profile_id: str = Query(...),
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> EntitlementView:
    owned_profile(session, profile_id, principal)
    return EntitlementView(
        profile_id=profile_id,
        full_access=has_full_access(session, principal.organization_id, profile_id),
    )


@router.post("/orders", response_model=OrderView, status_code=201)
def open_order(
    payload: CreateOrderIn,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> OrderView:
    owned_profile(session, payload.profile_id, principal)
    try:
        order = create_order(
            session,
            organization_id=principal.organization_id,
            profile_id=payload.profile_id,
            method=payload.method,
            phone=payload.phone,
        )
    except AlreadyEntitled as exc:
        raise HTTPException(409, str(exc)) from exc
    except InvalidPaymentRequest as exc:
        raise HTTPException(400, str(exc)) from exc
    except PaymentError as exc:
        # The payer's number must not travel in an error body.
        raise HTTPException(502, "The payment provider could not open an invoice.") from exc

    session.add(
        AuditEvent(
            organization_id=principal.organization_id,
            actor=f"user:{principal.user_id[:8]}",
            action="order_opened",
            entity_type="order",
            entity_id=order.id,
            detail={"method": order.method, "amount_kzt": order.amount_kzt},
        )
    )
    session.commit()
    session.refresh(order)
    return _view(order)


@router.get("/orders/{order_id}", response_model=OrderView)
def read_order(
    order_id: str,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> OrderView:
    return _view(_owned_order(session, order_id, principal))


@router.post("/orders/{order_id}/cancel", response_model=OrderView)
def stop_order(
    order_id: str,
    principal: Principal = Depends(get_principal),
    session: Session = Depends(get_session),
) -> OrderView:
    order = cancel_order(session, _owned_order(session, order_id, principal))
    session.commit()
    session.refresh(order)
    return _view(order)
```

- [ ] **Step 5: Register the router and the handler**

In `backend/app/main.py`, add `routes_billing` to the import of route modules and to the `for module in (...)` tuple. Then, after `app.include_router(...)`:

```python
from app.payments.http import PaymentRequired, payment_required_handler

app.add_exception_handler(PaymentRequired, payment_required_handler)
```

- [ ] **Step 6: Run the tests and watch them pass**

Run: `python -m pytest tests/test_billing_api.py -q`
Expected: PASS, 9 tests.

- [ ] **Step 7: Full suite, lint, types**

Run: `python -m pytest -q && ruff check . && mypy app`
Expected: 608 passed, clean.

- [ ] **Step 8: Commit**

```bash
git add backend/app/api/routes_billing.py backend/app/payments/http.py backend/app/main.py backend/tests/test_billing_api.py
git commit -m "feat(payments): billing endpoints and a 402 the frontend can act on"
```

---

### Task 7: The webhook

**Files:**
- Create: `backend/app/api/routes_webhooks.py`
- Modify: `backend/app/main.py` (register the router)
- Test: `backend/tests/test_payment_webhook.py`

**Interfaces:**
- Consumes: Tasks 3, 5, 6.
- Produces: `POST /webhooks/apipay`, unauthenticated, HMAC-verified.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_payment_webhook.py`:

```python
"""The webhook: signed, size-capped, idempotent, and never trusted blindly."""

from __future__ import annotations

import hashlib
import hmac
import json

import pytest

from app.corpus.demo_profile import DEMO_PROFILE

SECRET = b"whsec-test"


def sign(body: bytes) -> str:
    return "sha256=" + hmac.new(SECRET, body, hashlib.sha256).hexdigest()


@pytest.fixture
def paid_client(tmp_path, monkeypatch, corpus_dir):
    from app.config import Settings, get_settings
    from app.payments.fake import reset_shared_fake

    settings = Settings(
        demo_mode=True,
        database_url=f"sqlite:///{tmp_path / 'hook.db'}",
        cache_dir=tmp_path / "cache",
        export_dir=tmp_path / "exports",
        corpus_dir=corpus_dir,
        fetch_delay_seconds=0.0,
        enable_browser_tier=False,
        payments_enabled=True,
        payments_provider="fake",
        apipay_webhook_secret="whsec-test",
    )
    settings.ensure_dirs()
    get_settings.cache_clear()
    reset_shared_fake()
    monkeypatch.setattr("app.config.get_settings", lambda: settings)

    import app.db as db_module

    engine = db_module.create_engine(
        settings.database_url, connect_args={"check_same_thread": False}
    )
    monkeypatch.setattr(db_module, "engine", engine)
    monkeypatch.setattr(db_module, "SessionLocal", db_module.sessionmaker(bind=engine, future=True))
    db_module.migrate_to_head(settings.database_url)

    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c
    get_settings.cache_clear()
    reset_shared_fake()


@pytest.fixture
def order(paid_client) -> dict:
    case = paid_client.post("/api/profiles", json=DEMO_PROFILE.model_dump(mode="json")).json()
    return paid_client.post(
        "/api/billing/orders",
        json={"profile_id": case["id"], "method": "phone", "phone": "87071234455"},
    ).json()


def _body(order: dict, status: str = "paid") -> bytes:
    return json.dumps(
        {
            "event": "invoice.status_changed",
            "data": {"id": order["id"], "external_order_id": None, "status": status},
        }
    ).encode()


def _post(client, body: bytes, signature: str | None = None):
    return client.post(
        "/webhooks/apipay",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Webhook-Signature": sign(body) if signature is None else signature,
        },
    )


def test_a_signed_paid_event_unlocks_the_case(paid_client, order) -> None:
    assert _post(paid_client, _body(order)).status_code == 200
    entitlement = paid_client.get(
        f"/api/billing/entitlements?profile_id={order['profile_id']}"
    ).json()
    assert entitlement["full_access"] is True


def test_an_unsigned_event_is_refused(paid_client, order) -> None:
    assert _post(paid_client, _body(order), signature="").status_code == 401


def test_a_wrong_signature_is_refused(paid_client, order) -> None:
    assert _post(paid_client, _body(order), signature="sha256=deadbeef").status_code == 401


def test_a_tampered_body_is_refused(paid_client, order) -> None:
    body = _body(order)
    response = paid_client.post(
        "/webhooks/apipay",
        content=body.replace(b"paid", b"pai0"),
        headers={"Content-Type": "application/json", "X-Webhook-Signature": sign(body)},
    )
    assert response.status_code == 401


def test_a_refused_event_does_not_unlock_anything(paid_client, order) -> None:
    _post(paid_client, _body(order), signature="sha256=deadbeef")
    entitlement = paid_client.get(
        f"/api/billing/entitlements?profile_id={order['profile_id']}"
    ).json()
    assert entitlement["full_access"] is False


def test_a_replayed_event_unlocks_once(paid_client, order) -> None:
    for _ in range(3):
        assert _post(paid_client, _body(order)).status_code == 200

    from app.db import session_scope
    from app.models.billing import Entitlement

    with session_scope() as session:
        assert session.query(Entitlement).count() == 1


def test_an_unknown_order_is_acknowledged_but_ignored(paid_client) -> None:
    body = json.dumps(
        {"event": "invoice.status_changed", "data": {"id": "no-such-order", "status": "paid"}}
    ).encode()
    assert _post(paid_client, body).status_code == 200


def test_an_unknown_event_type_is_acknowledged_and_not_acted_on(paid_client, order) -> None:
    body = json.dumps(
        {"event": "catalog.item_processed", "data": {"id": order["id"], "status": "paid"}}
    ).encode()
    assert _post(paid_client, body).status_code == 200
    entitlement = paid_client.get(
        f"/api/billing/entitlements?profile_id={order['profile_id']}"
    ).json()
    assert entitlement["full_access"] is False


def test_an_oversized_body_is_refused(paid_client) -> None:
    body = b'{"padding":"' + b"x" * 70_000 + b'"}'
    assert _post(paid_client, body).status_code == 413
```

- [ ] **Step 2: Run it and watch it fail**

Run: `python -m pytest tests/test_payment_webhook.py -q`
Expected: FAIL — 404 on `/webhooks/apipay`.

- [ ] **Step 3: Write the webhook**

Create `backend/app/api/routes_webhooks.py`:

```python
"""Provider callbacks.

This is the only unauthenticated write endpoint in the service, so it is the
one that gets the most suspicion: the body is size-capped before it is parsed,
the signature is checked against the raw bytes, an unrecognised event is
recorded and ignored, and nothing here trusts a field it did not verify.
"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.billing import Order, PaymentEvent
from app.payments.provider import get_provider
from app.payments.service import apply_status

log = logging.getLogger("unimatch.payments")

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

#: A status callback is a few hundred bytes. Anything of this size is not one.
MAX_WEBHOOK_BYTES = 64 * 1024
#: The only events that may change an order.
ACTIONABLE_EVENTS = frozenset({"invoice.status_changed", "invoice.qr_scanned"})


@router.post("/apipay")
async def apipay_webhook(
    request: Request,
    x_webhook_signature: str = Header(default=""),
) -> dict[str, str]:
    raw = await request.body()
    if len(raw) > MAX_WEBHOOK_BYTES:
        raise HTTPException(413, "Payload too large")

    if not get_provider().verify_webhook(raw, x_webhook_signature):
        # Deliberately uninformative: a probe learns nothing about why.
        log.warning("rejected an ApiPay webhook with an invalid signature")
        raise HTTPException(401, "Invalid signature")

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(400, "Malformed JSON") from exc

    event_type = str(payload.get("event", ""))
    data = payload.get("data") or {}
    provider_status = str(data.get("status", ""))
    invoice_id = str(data.get("id", ""))
    external_order_id = data.get("external_order_id")

    session: Session = next(get_session())
    try:
        order = _find_order(session, invoice_id, external_order_id)
        if order is None:
            # Acknowledged so the provider stops retrying something we cannot use.
            log.info("ApiPay webhook for an unknown invoice, ignored")
            return {"status": "ignored"}

        if event_type not in ACTIONABLE_EVENTS:
            session.add(
                PaymentEvent(
                    order_id=order.id,
                    source="webhook",
                    event_type=event_type,
                    provider_status=provider_status,
                    signature_valid=True,
                    detail="event type not actionable",
                )
            )
            session.commit()
            return {"status": "recorded"}

        apply_status(session, order, provider_status, source="webhook", event_type=event_type)
        session.commit()
        return {"status": "applied"}
    finally:
        session.close()


def _find_order(session: Session, invoice_id: str, external_order_id: str | None) -> Order | None:
    """Match on the provider's id, then on ours.

    The fake provider's invoice id and our order id differ, and in tests the
    payload carries our order id — so the primary key is tried last.
    """
    if invoice_id:
        found = (
            session.query(Order).filter(Order.provider_invoice_id == invoice_id).one_or_none()
        )
        if found is not None:
            return found
    if external_order_id:
        found = (
            session.query(Order)
            .filter(Order.external_order_id == str(external_order_id))
            .one_or_none()
        )
        if found is not None:
            return found
    return session.get(Order, invoice_id) if invoice_id else None
```

- [ ] **Step 4: Register the router**

In `backend/app/main.py`, add `routes_webhooks` to the imports and to the `for module in (...)` tuple.

- [ ] **Step 5: Run the tests and watch them pass**

Run: `python -m pytest tests/test_payment_webhook.py -q`
Expected: PASS, 9 tests.

- [ ] **Step 6: Full suite, lint, types**

Run: `python -m pytest -q && ruff check . && mypy app`
Expected: 617 passed, clean.

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/routes_webhooks.py backend/app/main.py backend/tests/test_payment_webhook.py
git commit -m "feat(payments): a signed webhook that grants exactly once"
```

---

### Task 8: Gate the paid routes and truncate the free tier

**Files:**
- Modify: `backend/app/api/routes_results.py` (`list_results`, `get_result`, `list_claims`, `list_conflicts`, `open_questions`, `export`)
- Modify: `backend/app/api/routes_research.py` (`start_run`, `collect_documents`)
- Create: `backend/app/api/paywall.py`
- Test: `backend/tests/test_paywall.py`

**Interfaces:**
- Consumes: Tasks 1–6.
- Produces: `require_full_access(session, run_id, principal) -> None` (raises `PaymentRequired`), `access_for_run(session, run_id, principal) -> tuple[str, bool]` returning `(profile_id, full_access)`.

Decision recorded here that the spec left open: **`GET /summary` stays open.** It reports counts, not evidence, and a free user seeing "40 programmes found, 5 shown" is the honest version of the offer.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_paywall.py`:

```python
"""What an unpaid case may and may not reach."""

from __future__ import annotations

import pytest

from app.corpus.demo_profile import DEMO_PROFILE


@pytest.fixture
def paid_client(tmp_path, monkeypatch, corpus_dir):
    from app.config import Settings, get_settings
    from app.payments.fake import reset_shared_fake

    settings = Settings(
        demo_mode=True,
        database_url=f"sqlite:///{tmp_path / 'paywall.db'}",
        cache_dir=tmp_path / "cache",
        export_dir=tmp_path / "exports",
        corpus_dir=corpus_dir,
        fetch_delay_seconds=0.0,
        enable_browser_tier=False,
        payments_enabled=True,
        payments_provider="fake",
        apipay_webhook_secret="whsec-test",
        free_shortlist_rows=5,
        free_candidate_limit=5,
    )
    settings.ensure_dirs()
    get_settings.cache_clear()
    reset_shared_fake()
    monkeypatch.setattr("app.config.get_settings", lambda: settings)

    import app.db as db_module

    engine = db_module.create_engine(
        settings.database_url, connect_args={"check_same_thread": False}
    )
    monkeypatch.setattr(db_module, "engine", engine)
    monkeypatch.setattr(db_module, "SessionLocal", db_module.sessionmaker(bind=engine, future=True))
    db_module.migrate_to_head(settings.database_url)

    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c
    get_settings.cache_clear()
    reset_shared_fake()


async def drain(limit: int = 10) -> int:
    from app.jobs.worker import Worker

    worker = Worker()
    executed = 0
    for _ in range(limit):
        job_id = worker.claim_one()
        if job_id is None:
            break
        await worker.execute(job_id)
        executed += 1
    return executed


@pytest.fixture
def free_run(paid_client):
    import asyncio

    case = paid_client.post("/api/profiles", json=DEMO_PROFILE.model_dump(mode="json")).json()
    run = paid_client.post(
        "/api/runs", json={"profile_id": case["id"], "demo_mode": True}
    ).json()
    asyncio.get_event_loop().run_until_complete(drain())
    return {"case_id": case["id"], "run_id": run["id"]}


def test_a_free_run_is_capped_at_the_free_candidate_limit(paid_client, free_run) -> None:
    run = paid_client.get(f"/api/runs/{free_run['run_id']}").json()
    assert run["candidate_limit"] == 5


def test_the_shortlist_is_cut_and_stripped(paid_client, free_run) -> None:
    rows = paid_client.get(f"/api/runs/{free_run['run_id']}/results").json()
    assert len(rows) <= 5
    for row in rows:
        assert row["university"]
        assert row["source_urls"] == []
        assert row["claims"] == []
        assert row["scholarships"] == []


def test_the_summary_stays_open_and_reports_the_real_total(paid_client, free_run) -> None:
    body = paid_client.get(f"/api/runs/{free_run['run_id']}/summary").json()
    assert body["total"] >= 0


@pytest.mark.parametrize(
    "path",
    ["/claims", "/conflicts", "/questions", "/export.csv", "/export.json"],
)
def test_the_paid_routes_answer_402(paid_client, free_run, path: str) -> None:
    response = paid_client.get(f"/api/runs/{free_run['run_id']}{path}")
    assert response.status_code == 402
    body = response.json()
    assert body["code"] == "payment_required"
    assert body["profile_id"] == free_run["case_id"]
    assert body["price_kzt"] == 4990


def test_a_result_detail_answers_402(paid_client, free_run) -> None:
    rows = paid_client.get(f"/api/runs/{free_run['run_id']}/results").json()
    if not rows:
        pytest.skip("the demo corpus produced no rows for this profile")
    response = paid_client.get(f"/api/runs/{free_run['run_id']}/results/{rows[0]['id']}")
    assert response.status_code == 402


def test_document_collection_answers_402(paid_client, free_run) -> None:
    response = paid_client.post(f"/api/runs/{free_run['run_id']}/collect-documents")
    assert response.status_code == 402


def _unlock(client, case_id: str) -> None:
    import hashlib
    import hmac
    import json

    order = client.post(
        "/api/billing/orders",
        json={"profile_id": case_id, "method": "phone", "phone": "87071234455"},
    ).json()
    body = json.dumps(
        {"event": "invoice.status_changed", "data": {"id": order["id"], "status": "paid"}}
    ).encode()
    signature = "sha256=" + hmac.new(b"whsec-test", body, hashlib.sha256).hexdigest()
    client.post(
        "/webhooks/apipay",
        content=body,
        headers={"Content-Type": "application/json", "X-Webhook-Signature": signature},
    )


def test_paying_opens_every_gated_route(paid_client, free_run) -> None:
    _unlock(paid_client, free_run["case_id"])
    for path in ("/claims", "/conflicts", "/questions", "/export.csv"):
        assert paid_client.get(f"/api/runs/{free_run['run_id']}{path}").status_code == 200


def test_paying_enqueues_a_full_run(paid_client, free_run) -> None:
    _unlock(paid_client, free_run["case_id"])
    runs = paid_client.get("/api/runs").json()
    assert any(r["candidate_limit"] > 5 for r in runs)


def test_with_payments_disabled_nothing_is_gated(tmp_path, monkeypatch, corpus_dir) -> None:
    """The flag must restore the pre-payments product exactly."""
    import asyncio

    from app.config import Settings, get_settings

    settings = Settings(
        demo_mode=True,
        database_url=f"sqlite:///{tmp_path / 'open.db'}",
        cache_dir=tmp_path / "cache",
        export_dir=tmp_path / "exports",
        corpus_dir=corpus_dir,
        fetch_delay_seconds=0.0,
        enable_browser_tier=False,
        payments_enabled=False,
    )
    settings.ensure_dirs()
    get_settings.cache_clear()
    monkeypatch.setattr("app.config.get_settings", lambda: settings)

    import app.db as db_module

    engine = db_module.create_engine(
        settings.database_url, connect_args={"check_same_thread": False}
    )
    monkeypatch.setattr(db_module, "engine", engine)
    monkeypatch.setattr(db_module, "SessionLocal", db_module.sessionmaker(bind=engine, future=True))
    db_module.migrate_to_head(settings.database_url)

    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as client:
        case = client.post("/api/profiles", json=DEMO_PROFILE.model_dump(mode="json")).json()
        run = client.post("/api/runs", json={"profile_id": case["id"], "demo_mode": True}).json()
        asyncio.get_event_loop().run_until_complete(drain())
        assert run["candidate_limit"] > 5
        assert client.get(f"/api/runs/{run['id']}/claims").status_code == 200
        assert client.get(f"/api/runs/{run['id']}/export.csv").status_code == 200
    get_settings.cache_clear()
```

- [ ] **Step 2: Run it and watch it fail**

Run: `python -m pytest tests/test_paywall.py -q`
Expected: FAIL — the gated routes return 200 and the shortlist is not truncated.

- [ ] **Step 3: Write the guard**

Create `backend/app/api/paywall.py`:

```python
"""One place that answers: may this request see the paid material?

Routes call ``require_full_access``. Nothing else in the API decides this.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.api.tenancy import owned_run
from app.config import get_settings
from app.payments.entitlements import has_full_access
from app.payments.http import PaymentRequired
from app.security import Principal


def access_for_run(session: Session, run_id: str, principal: Principal) -> tuple[str, bool]:
    """The case behind a run, and whether it is unlocked.

    Ownership is checked here too, so a caller cannot skip it by asking about
    access instead of asking for the run.
    """
    run = owned_run(session, run_id, principal)
    return run.profile_id, has_full_access(session, principal.organization_id, run.profile_id)


def require_full_access(session: Session, run_id: str, principal: Principal) -> None:
    profile_id, allowed = access_for_run(session, run_id, principal)
    if not allowed:
        raise PaymentRequired(profile_id, get_settings().case_unlock_price_kzt)
```

- [ ] **Step 4: Gate the results routes**

In `backend/app/api/routes_results.py`, add the imports:

```python
from app.api.paywall import access_for_run, require_full_access
from app.payments.entitlements import free_view, truncate_shortlist
from app.config import get_settings
```

Replace the body of `list_results` after the filters with:

```python
    _profile_id, allowed = access_for_run(session, run_id, principal)
    rows = _results(
        session,
        run_id,
        decision=decision,
        eligibility=eligibility,
        funding=funding,
        country=country,
    )
    results = [ProgramResult.model_validate(r.payload) for r in rows]
    if allowed:
        return results
    settings = get_settings()
    return [free_view(r) for r in truncate_shortlist(results, settings.free_shortlist_rows)]
```

Delete the now-duplicated `owned_run(session, run_id, principal)` call at the top of `list_results` — `access_for_run` performs it.

In `get_result`, replace the duplicated pair of `owned_run` calls with:

```python
    require_full_access(session, run_id, principal)
```

Add the same single line as the first statement of `list_claims`, `list_conflicts`, `open_questions` and `export`, replacing their existing `owned_run(...)` call.

Leave `summary` and `set_decision` untouched: counts are not evidence, and a free user must still be able to reject a row.

- [ ] **Step 5: Cap the free run and gate document collection**

In `backend/app/api/routes_research.py`, inside `start_run`, after `owned_profile(...)`:

```python
    from app.payments.entitlements import has_full_access

    full_access = has_full_access(session, principal.organization_id, payload.profile_id)
    requested_limit = payload.candidate_limit
    if not full_access:
        # A free run really does fetch less. Paying later cannot widen this run;
        # it queues a new one.
        free_limit = settings.free_candidate_limit
        requested_limit = min(requested_limit or free_limit, free_limit)
```

then pass `candidate_limit=requested_limit` and `access_tier="full" if full_access else "free"` to the `ResearchRun(...)` constructor.

In `collect_documents`, add as the first statement after the signature:

```python
    from app.api.paywall import require_full_access

    require_full_access(session, run_id, principal)
```

- [ ] **Step 6: Run the tests and watch them pass**

Run: `python -m pytest tests/test_paywall.py -q`
Expected: PASS, 14 tests (5 parametrised plus 9).

- [ ] **Step 7: Full suite, lint, types**

Run: `python -m pytest -q && ruff check . && mypy app`
Expected: 631 passed, clean. If an existing API test now sees a 402, it is because it ran with payments enabled — check the fixture rather than relaxing the guard.

- [ ] **Step 8: Commit**

```bash
git add backend/app/api/paywall.py backend/app/api/routes_results.py backend/app/api/routes_research.py backend/tests/test_paywall.py
git commit -m "feat(payments): gate the paid routes and cap the free run"
```

---

### Task 9: The reconciler

**Files:**
- Create: `backend/app/jobs/payment_reconcile.py`
- Modify: `backend/app/jobs/worker.py` (`_dispatch`, lines 142–162)
- Test: `backend/tests/test_payment_reconcile.py`

**Interfaces:**
- Consumes: Tasks 3, 5.
- Produces: `reconcile_order(session, order_id: str) -> str` returning the resulting order status.

The existing `_dispatch` looks up `job.run_id` and fails a job that has none. A reconcile job has no run, so it must be handled before that lookup.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_payment_reconcile.py`:

```python
"""The backstop for a webhook that never arrives."""

from __future__ import annotations

import pytest

from app.models.billing import OrderStatus
from app.payments.entitlements import has_full_access
from app.payments.service import create_order


@pytest.fixture(autouse=True)
def payments_on(monkeypatch):
    from app.config import Settings, get_settings
    from app.payments.fake import reset_shared_fake

    settings = Settings(payments_enabled=True, payments_provider="fake")
    get_settings.cache_clear()
    reset_shared_fake()
    for target in (
        "app.config.get_settings",
        "app.payments.entitlements.get_settings",
        "app.payments.service.get_settings",
        "app.payments.provider.get_settings",
    ):
        monkeypatch.setattr(target, lambda: settings, raising=False)
    yield
    get_settings.cache_clear()
    reset_shared_fake()


def test_polling_finds_a_payment_no_webhook_reported(pg_session) -> None:
    from app.jobs.payment_reconcile import reconcile_order
    from app.payments.provider import get_provider

    order = create_order(
        pg_session, organization_id="org1", profile_id="case1",
        method="phone", phone="87071234455",
    )
    pg_session.flush()
    get_provider().simulate(order.provider_invoice_id, "paid")

    assert reconcile_order(pg_session, order.id) == OrderStatus.PAID.value
    pg_session.flush()
    assert has_full_access(pg_session, "org1", "case1") is True


def test_polling_a_still_pending_order_changes_nothing(pg_session) -> None:
    from app.jobs.payment_reconcile import reconcile_order

    order = create_order(
        pg_session, organization_id="org1", profile_id="case1",
        method="phone", phone="87071234455",
    )
    pg_session.flush()
    assert reconcile_order(pg_session, order.id) == OrderStatus.PENDING.value
    assert has_full_access(pg_session, "org1", "case1") is False


def test_polling_after_the_webhook_already_granted_is_harmless(pg_session) -> None:
    from app.jobs.payment_reconcile import reconcile_order
    from app.models.billing import Entitlement
    from app.payments.provider import get_provider
    from app.payments.service import apply_status

    order = create_order(
        pg_session, organization_id="org1", profile_id="case1",
        method="phone", phone="87071234455",
    )
    pg_session.flush()
    apply_status(pg_session, order, "paid", source="webhook")
    get_provider().simulate(order.provider_invoice_id, "paid")
    reconcile_order(pg_session, order.id)
    pg_session.flush()
    assert pg_session.query(Entitlement).count() == 1


def test_an_expired_invoice_settles_the_order(pg_session) -> None:
    from app.jobs.payment_reconcile import reconcile_order
    from app.payments.provider import get_provider

    order = create_order(
        pg_session, organization_id="org1", profile_id="case1",
        method="qr", phone=None,
    )
    pg_session.flush()
    get_provider().simulate(order.provider_invoice_id, "expired")
    assert reconcile_order(pg_session, order.id) == OrderStatus.EXPIRED.value


def test_a_missing_order_is_not_an_error(pg_session) -> None:
    from app.jobs.payment_reconcile import reconcile_order

    assert reconcile_order(pg_session, "0" * 32) == ""
```

- [ ] **Step 2: Run it and watch it fail**

Run: `python -m pytest tests/test_payment_reconcile.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.jobs.payment_reconcile'`.

- [ ] **Step 3: Write the reconciler**

Create `backend/app/jobs/payment_reconcile.py`:

```python
"""Ask the provider what happened, because a webhook can be lost.

This is a backstop, not a fallback: it runs for every order, and it converges
on the same ``apply_status`` the webhook uses, so the two cannot disagree.
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.models.base import ensure_utc, utcnow
from app.models.billing import TERMINAL_ORDER_STATUSES, Order, OrderStatus, PaymentMethod
from app.payments.errors import PaymentError
from app.payments.provider import get_provider
from app.payments.service import apply_status

log = logging.getLogger("unimatch.payments")

#: How long we keep asking. A phone invoice can sit unanswered for a while; a
#: QR is dead within minutes of its own expiry.
PHONE_TTL_HOURS = 24
QR_GRACE_MINUTES = 5


def reconcile_order(session: Session, order_id: str) -> str:
    """Poll one order once. Returns its status, or "" if there is nothing to do."""
    order = session.get(Order, order_id)
    if order is None:
        log.info("reconcile: order %s no longer exists", order_id[:8])
        return ""
    if order.status in TERMINAL_ORDER_STATUSES:
        return order.status
    if not order.provider_invoice_id:
        return order.status

    if _past_its_life(order):
        apply_status(session, order, "expired", source="poll", event_type="reconcile.timeout")
        return order.status

    try:
        invoice = get_provider().get_invoice(order.provider_invoice_id)
    except PaymentError as exc:
        # Leave the order alone and let the queue's backoff try again.
        log.warning("reconcile: provider refused for order %s (%s)", order.id[:8], exc.code)
        return order.status

    apply_status(session, order, invoice.status, source="poll", event_type="reconcile")
    return order.status


def _past_its_life(order: Order) -> bool:
    from datetime import timedelta

    now = utcnow()
    if order.method == PaymentMethod.QR.value:
        expiry = ensure_utc(order.qr_expires_at)
        return expiry is not None and now > expiry + timedelta(minutes=QR_GRACE_MINUTES)
    created = ensure_utc(order.created_at)
    return created is not None and now > created + timedelta(hours=PHONE_TTL_HOURS)
```

- [ ] **Step 4: Route the job kind before the run lookup**

In `backend/app/jobs/worker.py`, insert this at the very start of `_dispatch`, before `run = session.get(ResearchRun, job.run_id)`:

```python
        if job.kind == "payment_reconcile":
            # A payment job has no run. Handle it before anything asks for one.
            from app.jobs.payment_reconcile import reconcile_order
            from app.models.billing import TERMINAL_ORDER_STATUSES

            order_id = str((job.payload or {}).get("order_id", ""))
            status = reconcile_order(session, order_id)
            if status and status not in TERMINAL_ORDER_STATUSES:
                # Not settled yet: fail softly so the queue's backoff re-runs it.
                store.fail(job.id, f"order {order_id[:8]} still {status}", retry=True)
                return
            store.complete(job.id)
            return
```

Check `store.fail`'s signature in `backend/app/jobs/store.py` before writing this; if the keyword is not `retry`, use whatever that method actually takes.

- [ ] **Step 5: Run the tests and watch them pass**

Run: `python -m pytest tests/test_payment_reconcile.py -q`
Expected: PASS, 5 tests.

- [ ] **Step 6: Full suite, lint, types**

Run: `python -m pytest -q && ruff check . && mypy app`
Expected: 636 passed, clean.

- [ ] **Step 7: Commit**

```bash
git add backend/app/jobs/payment_reconcile.py backend/app/jobs/worker.py backend/tests/test_payment_reconcile.py
git commit -m "feat(payments): reconcile orders so a lost webhook cannot strand a payment"
```

---

### Task 10: The real ApiPay adapter

**Files:**
- Create: `backend/app/payments/apipay.py`
- Test: `backend/tests/test_apipay_adapter.py`

**Interfaces:**
- Consumes: Task 3's `PaymentProvider`, `ProviderInvoice`, errors.
- Produces: `ApiPayProvider(base_url, api_key, webhook_secret, timeout_seconds)` satisfying `PaymentProvider`.

- [ ] **Step 1: Reconcile the contract with the published spec**

Before writing code, fetch `https://raw.githubusercontent.com/bazarbaykz/apipay-docs/main/openapi.yaml` and check, for `POST /invoices`, `POST /invoices/qr` and `GET /invoices/{id}`: the exact request field names, the response field holding the invoice id, the response field holding the status, the QR payload and expiry field names, and the webhook body shape.

Write what you find into a comment block at the top of `apipay.py`, naming the spec version or commit you read. If any of it contradicts §4 of the design spec, correct the design spec in the same commit and say so in the message. **Do not guess a field name.** If the document is unreachable, stop and report that rather than inventing a contract.

- [ ] **Step 2: Write the failing test**

Create `backend/tests/test_apipay_adapter.py`. Field names marked `# VERIFY` must be corrected to what Step 1 found before this test is considered correct:

```python
"""The ApiPay adapter, driven against a stubbed transport."""

from __future__ import annotations

import httpx
import pytest

from app.payments.apipay import ApiPayProvider
from app.payments.errors import (
    DuplicateOrderError,
    ProviderRejected,
    ProviderUnavailable,
    RateLimited,
    SessionExpired,
    TariffInactive,
)


def provider_with(handler) -> ApiPayProvider:
    transport = httpx.MockTransport(handler)
    return ApiPayProvider(
        base_url="https://api.apipay.test/api/v1",
        api_key="key-123",
        webhook_secret="whsec",
        timeout_seconds=5.0,
        transport=transport,
    )


def test_the_api_key_travels_in_the_header_and_never_in_the_url() -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["key"] = request.headers.get("X-API-Key", "")
        seen["url"] = str(request.url)
        return httpx.Response(200, json={"id": "inv1", "status": "processing"})  # VERIFY

    provider_with(handler).create_phone_invoice(
        amount_kzt=4990, phone="87071234455", description="Case", external_order_id="ext-1"
    )
    assert seen["key"] == "key-123"
    assert "key-123" not in seen["url"]


def test_a_phone_invoice_is_parsed() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"id": "inv1", "status": "processing"})  # VERIFY

    invoice = provider_with(handler).create_phone_invoice(
        amount_kzt=4990, phone="87071234455", description="Case", external_order_id="ext-1"
    )
    assert invoice.invoice_id == "inv1"
    assert invoice.status == "processing"


def test_a_duplicate_order_id_raises_its_own_error() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            409,
            json={"error": "duplicate", "error_code": "duplicate_idempotency_key",
                  "message": "already exists"},
        )

    with pytest.raises(DuplicateOrderError):
        provider_with(handler).create_phone_invoice(
            amount_kzt=4990, phone="87071234455", description="Case", external_order_id="ext-1"
        )


def test_our_own_lapsed_tariff_is_distinguishable() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403,
            json={"error": "tariff", "error_code": "tariff_inactive", "message": "expired"},
        )

    with pytest.raises(TariffInactive):
        provider_with(handler).get_invoice("inv1")


def test_an_expired_kaspi_session_is_distinguishable() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={"error": "session", "error_code": "kaspi_session_expired", "message": "re-auth"},
        )

    with pytest.raises(SessionExpired):
        provider_with(handler).get_invoice("inv1")


def test_rate_limiting_carries_retry_after() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            json={"error_code": "request_rate_limited", "message": "slow down"},
            headers={"Retry-After": "7"},
        )

    with pytest.raises(RateLimited) as caught:
        provider_with(handler).get_invoice("inv1")
    assert caught.value.retry_after == 7


def test_a_validation_failure_names_the_field() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            422, json={"message": "Validation failed", "errors": {"phone": ["bad format"]}}
        )

    with pytest.raises(ProviderRejected) as caught:
        provider_with(handler).create_phone_invoice(
            amount_kzt=4990, phone="123", description="Case", external_order_id="ext-1"
        )
    assert "phone" in str(caught.value)


def test_a_server_error_is_retryable() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="upstream down")

    with pytest.raises(ProviderUnavailable):
        provider_with(handler).get_invoice("inv1")


def test_a_transport_failure_is_retryable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route", request=request)

    with pytest.raises(ProviderUnavailable):
        provider_with(handler).get_invoice("inv1")


def test_an_error_never_repeats_the_payer_phone() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            422, json={"message": "Validation failed", "errors": {"phone": ["87071234455 is bad"]}}
        )

    with pytest.raises(ProviderRejected) as caught:
        provider_with(handler).create_phone_invoice(
            amount_kzt=4990, phone="87071234455", description="Case", external_order_id="ext-1"
        )
    assert "87071234455" not in str(caught.value)


def test_the_webhook_signature_is_verified_against_the_raw_bytes() -> None:
    import hashlib
    import hmac

    provider = provider_with(lambda r: httpx.Response(200, json={}))
    body = b'{"event":"invoice.status_changed"}'
    good = "sha256=" + hmac.new(b"whsec", body, hashlib.sha256).hexdigest()
    assert provider.verify_webhook(body, good) is True
    assert provider.verify_webhook(body + b" ", good) is False
    assert provider.verify_webhook(body, "") is False
```

- [ ] **Step 3: Run it and watch it fail**

Run: `python -m pytest tests/test_apipay_adapter.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.payments.apipay'`.

- [ ] **Step 4: Write the adapter**

Create `backend/app/payments/apipay.py`:

```python
"""ApiPay (Kaspi Pay) over HTTP.

Contract reconciled against ApiPay's published OpenAPI document on
<DATE>, revision <COMMIT>. Field names below are copied from it, not inferred.

Two rules this file exists to keep:
  * the API key travels in a header, never in a URL or a log line;
  * the payer's phone never appears in an exception message.
"""

from __future__ import annotations

import hashlib
import hmac
from datetime import datetime
from typing import Any

import httpx

from app.payments.errors import (
    DuplicateOrderError,
    PaymentError,
    ProviderRejected,
    ProviderUnavailable,
    RateLimited,
    SessionExpired,
    TariffInactive,
)
from app.payments.provider import ProviderInvoice

#: error_code values that deserve their own class. Everything else becomes a
#: ProviderRejected carrying the provider's code verbatim.
_ERRORS: dict[str, type[PaymentError]] = {
    "duplicate_idempotency_key": DuplicateOrderError,
    "tariff_inactive": TariffInactive,
    "kaspi_session_expired": SessionExpired,
    "kaspi_session_not_configured": SessionExpired,
}


class ApiPayProvider:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        webhook_secret: str,
        timeout_seconds: float = 20.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._secret = webhook_secret.encode()
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={"X-API-Key": api_key, "Accept": "application/json"},
            timeout=timeout_seconds,
            transport=transport,
        )

    # -- transport -----------------------------------------------------
    def _call(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict:
        try:
            response = self._client.request(method, path, json=payload)
        except httpx.HTTPError as exc:
            raise ProviderUnavailable("The payment provider could not be reached.") from exc

        if response.status_code >= 500:
            raise ProviderUnavailable(f"The payment provider returned {response.status_code}.")

        if response.status_code == 429:
            raise RateLimited(
                "The payment provider is rate limiting us.",
                retry_after=int(response.headers.get("Retry-After", "1") or 1),
            )

        body: dict[str, Any]
        try:
            body = response.json()
        except ValueError:
            body = {}

        if response.status_code >= 400:
            raise self._to_error(response.status_code, body)
        return body

    def _to_error(self, status: int, body: dict[str, Any]) -> PaymentError:
        code = str(body.get("error_code", "") or "")
        if code in _ERRORS:
            return _ERRORS[code](f"The payment provider refused the request ({code}).", code=code)
        if status == 422:
            # Name the fields, never their values: one of them is the phone.
            fields = ", ".join(sorted((body.get("errors") or {}).keys())) or "request"
            return ProviderRejected(
                f"The payment provider rejected these fields: {fields}.", code="validation_failed"
            )
        return ProviderRejected(
            f"The payment provider refused the request ({code or status}).", code=code or "rejected"
        )

    # -- invoices ------------------------------------------------------
    def create_phone_invoice(
        self, *, amount_kzt: int, phone: str, description: str, external_order_id: str
    ) -> ProviderInvoice:
        body = self._call(
            "POST",
            "/invoices",
            {
                "amount": amount_kzt,
                "phone": phone,
                "description": description,
                "external_order_id": external_order_id,
            },
        )
        return self._to_invoice(body)

    def create_qr_invoice(
        self, *, amount_kzt: int, description: str, external_order_id: str
    ) -> ProviderInvoice:
        body = self._call(
            "POST",
            "/invoices/qr",
            {
                "amount": amount_kzt,
                "description": description,
                "external_order_id": external_order_id,
            },
        )
        return self._to_invoice(body)

    def get_invoice(self, invoice_id: str) -> ProviderInvoice:
        return self._to_invoice(self._call("GET", f"/invoices/{invoice_id}"))

    def cancel_invoice(self, invoice_id: str) -> None:
        self._call("POST", f"/invoices/{invoice_id}/cancel")

    @staticmethod
    def _to_invoice(body: dict[str, Any]) -> ProviderInvoice:
        expires_raw = body.get("qr_expires_at")
        expires = None
        if isinstance(expires_raw, str) and expires_raw:
            expires = datetime.fromisoformat(expires_raw.replace("Z", "+00:00"))
        return ProviderInvoice(
            invoice_id=str(body.get("id", "")),
            status=str(body.get("status", "")),
            qr_payload=str(body.get("qr_url") or body.get("qr_payload") or ""),
            qr_expires_at=expires,
        )

    # -- webhooks ------------------------------------------------------
    def verify_webhook(self, raw_body: bytes, signature: str) -> bool:
        if not signature:
            return False
        expected = "sha256=" + hmac.new(self._secret, raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)
```

Three things in that file are deliberately unfinished, and Step 1 supplies all three:

1. `<DATE>` and `<COMMIT>` in the docstring — the date you read the document and the
   revision you read. Leaving them unfilled makes the file lie about being verified.
2. `_to_invoice`'s field names. The `qr_url or qr_payload` fallback stands in for exactly
   one verified name; delete the loser rather than keeping both.
3. The request bodies in `create_phone_invoice` and `create_qr_invoice`, if the document
   names those fields differently.

- [ ] **Step 5: Run the tests and watch them pass**

Run: `python -m pytest tests/test_apipay_adapter.py -q`
Expected: PASS, 11 tests.

- [ ] **Step 6: Full suite, lint, types**

Run: `python -m pytest -q && ruff check . && mypy app`
Expected: 647 passed, clean.

- [ ] **Step 7: Commit**

```bash
git add backend/app/payments/apipay.py backend/tests/test_apipay_adapter.py
git commit -m "feat(payments): ApiPay adapter, reconciled against the published spec"
```

---

### Task 11: Frontend types, client, and 402 handling

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/api/client.ts`
- Test: `frontend/src/api/client.billing.test.ts`

**Interfaces:**
- Consumes: Task 6's HTTP shapes.
- Produces: TypeScript `Pricing`, `EntitlementView`, `OrderView`, `PaymentMethod`; `api.pricing()`, `api.entitlements(profileId)`, `api.openOrder(input)`, `api.readOrder(id)`, `api.cancelOrder(id)`; `isPaymentRequired(error): error is ApiError & { profileId: string; priceKzt: number }`.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/api/client.billing.test.ts`:

```ts
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiError, api, isPaymentRequired } from './client';

function respond(status: number, body: unknown) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    statusText: 'x',
    json: () => Promise.resolve(body),
  } as Response);
}

afterEach(() => vi.unstubAllGlobals());

describe('billing client', () => {
  it('reads pricing', async () => {
    vi.stubGlobal('fetch', vi.fn(() =>
      respond(200, { case_unlock_price_kzt: 4990, currency: 'KZT', payments_enabled: true, includes: ['a'] }),
    ));
    const pricing = await api.pricing();
    expect(pricing.case_unlock_price_kzt).toBe(4990);
  });

  it('opens an order without sending a price', async () => {
    const fetchMock = vi.fn(() =>
      respond(201, {
        id: 'o1', profile_id: 'c1', status: 'pending', method: 'phone',
        amount_kzt: 4990, phone_masked: '8707***4455', qr_payload: '',
        qr_expires_at: null, created_at: '2026-09-04T10:00:00Z',
      }),
    );
    vi.stubGlobal('fetch', fetchMock);

    const order = await api.openOrder({ profile_id: 'c1', method: 'phone', phone: '87071234455' });
    expect(order.status).toBe('pending');

    const sent = JSON.parse((fetchMock.mock.calls[0][1] as RequestInit).body as string);
    expect(sent).not.toHaveProperty('amount_kzt');
    expect(sent).not.toHaveProperty('price_kzt');
  });

  it('recognises a 402 and carries what the paywall needs', async () => {
    vi.stubGlobal('fetch', vi.fn(() =>
      respond(402, {
        detail: 'Unlock this case to see the full report.',
        code: 'payment_required',
        profile_id: 'c1',
        price_kzt: 4990,
      }),
    ));

    await expect(api.claims('run1')).rejects.toThrow(ApiError);
    try {
      await api.claims('run1');
    } catch (error) {
      expect(isPaymentRequired(error)).toBe(true);
      if (isPaymentRequired(error)) {
        expect(error.profileId).toBe('c1');
        expect(error.priceKzt).toBe(4990);
      }
    }
  });

  it('does not mistake other errors for a paywall', async () => {
    vi.stubGlobal('fetch', vi.fn(() => respond(404, { detail: 'Run not found' })));
    try {
      await api.claims('run1');
    } catch (error) {
      expect(isPaymentRequired(error)).toBe(false);
    }
  });
});
```

If `api.claims` is not the existing method name for `GET /api/runs/{id}/claims`, use whatever `client.ts` already calls it.

- [ ] **Step 2: Run it and watch it fail**

Run (from `frontend/`): `npm run test -- client.billing`
Expected: FAIL — `api.pricing is not a function`.

- [ ] **Step 3: Add the types**

Append to `frontend/src/types.ts`:

```ts
export type PaymentMethod = 'phone' | 'qr';

export interface Pricing {
  case_unlock_price_kzt: number;
  currency: string;
  payments_enabled: boolean;
  includes: string[];
}

export interface EntitlementView {
  profile_id: string;
  full_access: boolean;
}

export interface OrderView {
  id: string;
  profile_id: string;
  status: 'created' | 'pending' | 'paid' | 'cancelled' | 'expired' | 'failed';
  method: PaymentMethod;
  amount_kzt: number;
  phone_masked: string;
  qr_payload: string;
  qr_expires_at: string | null;
  created_at: string;
}
```

- [ ] **Step 4: Extend the client**

In `frontend/src/api/client.ts`, widen `ApiError` so a paywall carries its two extra facts:

```ts
export class ApiError extends Error {
  profileId?: string;
  priceKzt?: number;

  constructor(public status: number, message: string, public code?: string) {
    super(message);
    this.name = 'ApiError';
  }
}

/** A 402 from a gated route, with everything the paywall needs to sell. */
export function isPaymentRequired(
  error: unknown,
): error is ApiError & { profileId: string; priceKzt: number } {
  return (
    error instanceof ApiError &&
    error.status === 402 &&
    error.code === 'payment_required' &&
    typeof error.profileId === 'string'
  );
}
```

Replace the whole `if (!response.ok) { ... }` block in `request` with this. It is the
existing block plus two captured fields and one throw site, so a non-JSON error body
still reports by status:

```ts
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    let code: string | undefined;
    let profileId: string | undefined;
    let priceKzt: number | undefined;
    try {
      const body = await response.json();
      if (typeof body?.detail === 'string') detail = body.detail;
      else if (Array.isArray(body?.detail)) {
        detail = body.detail
          .map((d: { loc?: unknown[]; msg?: string }) => `${d.loc?.slice(1).join('.')}: ${d.msg}`)
          .join('; ');
      }
      code = body?.code;
      // A 402 names the case to sell and its price. No other status carries these.
      if (typeof body?.profile_id === 'string') profileId = body.profile_id;
      if (typeof body?.price_kzt === 'number') priceKzt = body.price_kzt;
    } catch {
      /* a non-JSON error body is still reported by status */
    }
    const failure = new ApiError(response.status, detail, code);
    failure.profileId = profileId;
    failure.priceKzt = priceKzt;
    throw failure;
  }
```

Add the methods to the `api` object:

```ts
  pricing: () => request<Pricing>('/api/billing/pricing'),
  entitlements: (profileId: string) =>
    request<EntitlementView>(`/api/billing/entitlements?profile_id=${encodeURIComponent(profileId)}`),
  openOrder: (input: { profile_id: string; method: PaymentMethod; phone?: string }) =>
    request<OrderView>('/api/billing/orders', { method: 'POST', body: JSON.stringify(input) }),
  readOrder: (orderId: string) => request<OrderView>(`/api/billing/orders/${orderId}`),
  cancelOrder: (orderId: string) =>
    request<OrderView>(`/api/billing/orders/${orderId}/cancel`, { method: 'POST' }),
```

and add `EntitlementView`, `OrderView`, `PaymentMethod`, `Pricing` to the type import at the top of the file.

- [ ] **Step 5: Run the tests and watch them pass**

Run: `npm run test -- client.billing`
Expected: PASS, 4 tests.

- [ ] **Step 6: Types, lint, full frontend suite**

Run: `npx tsc --noEmit && npm run lint && npm run test`
Expected: clean, 43 passed.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/types.ts frontend/src/api/client.ts frontend/src/api/client.billing.test.ts
git commit -m "feat(payments): billing client and a typed 402"
```

---

### Task 12: The payment modal and the locked affordances

**Files:**
- Create: `frontend/src/components/PaymentModal.tsx`
- Create: `frontend/src/components/PaywallNotice.tsx`
- Modify: `frontend/src/lib/store.tsx` (paywall state)
- Modify: `frontend/src/screens/ExportScreen.tsx`, `frontend/src/screens/ShortlistScreen.tsx`
- Test: `frontend/src/components/PaymentModal.test.tsx`

**Interfaces:**
- Consumes: Task 11.
- Produces: `<PaymentModal profileId onClose onPaid />`, `<PaywallNotice priceKzt onUnlock />`, store fields `paywall: { profileId: string; priceKzt: number } | null`, `raisePaywall(error: unknown): boolean`, `clearPaywall()`.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/PaymentModal.test.tsx`:

```tsx
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { PaymentModal } from './PaymentModal';
import { api } from '@/api/client';

beforeEach(() => vi.useFakeTimers({ shouldAdvanceTime: true }));
afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

const order = {
  id: 'o1', profile_id: 'c1', status: 'pending' as const, method: 'phone' as const,
  amount_kzt: 4990, phone_masked: '8707***4455', qr_payload: '',
  qr_expires_at: null, created_at: '2026-09-04T10:00:00Z',
};

describe('PaymentModal', () => {
  it('shows the price before asking for anything', () => {
    render(<PaymentModal profileId="c1" priceKzt={4990} onClose={() => {}} onPaid={() => {}} />);
    expect(screen.getByText(/4990/)).toBeInTheDocument();
  });

  it('refuses a malformed phone number without calling the API', () => {
    const open = vi.spyOn(api, 'openOrder');
    render(<PaymentModal profileId="c1" priceKzt={4990} onClose={() => {}} onPaid={() => {}} />);
    fireEvent.change(screen.getByLabelText(/номер|phone/i), { target: { value: '123' } });
    fireEvent.click(screen.getByRole('button', { name: /оплатить|pay/i }));
    expect(open).not.toHaveBeenCalled();
    expect(screen.getByText(/8XXXXXXXXXX/)).toBeInTheDocument();
  });

  it('opens an order and then polls until it is paid', async () => {
    vi.spyOn(api, 'openOrder').mockResolvedValue(order);
    const read = vi.spyOn(api, 'readOrder')
      .mockResolvedValueOnce(order)
      .mockResolvedValue({ ...order, status: 'paid' });
    const onPaid = vi.fn();

    render(<PaymentModal profileId="c1" priceKzt={4990} onClose={() => {}} onPaid={onPaid} />);
    fireEvent.change(screen.getByLabelText(/номер|phone/i), { target: { value: '87071234455' } });
    fireEvent.click(screen.getByRole('button', { name: /оплатить|pay/i }));

    await waitFor(() => expect(api.openOrder).toHaveBeenCalled());
    await vi.advanceTimersByTimeAsync(5000);
    await waitFor(() => expect(onPaid).toHaveBeenCalled());
    expect(read).toHaveBeenCalled();
  });

  it('shows the QR payload when QR is chosen', async () => {
    vi.spyOn(api, 'openOrder').mockResolvedValue({
      ...order, method: 'qr', qr_payload: 'https://pay.kaspi.test/abc',
      qr_expires_at: '2099-01-01T00:00:00Z',
    });
    vi.spyOn(api, 'readOrder').mockResolvedValue({ ...order, method: 'qr' });

    render(<PaymentModal profileId="c1" priceKzt={4990} onClose={() => {}} onPaid={() => {}} />);
    fireEvent.click(screen.getByRole('button', { name: /qr/i }));
    fireEvent.click(screen.getByRole('button', { name: /оплатить|pay/i }));
    await waitFor(() => expect(screen.getByText(/pay.kaspi.test/)).toBeInTheDocument());
  });

  it('reports a failure to open the order instead of spinning', async () => {
    vi.spyOn(api, 'openOrder').mockRejectedValue(new Error('nope'));
    render(<PaymentModal profileId="c1" priceKzt={4990} onClose={() => {}} onPaid={() => {}} />);
    fireEvent.change(screen.getByLabelText(/номер|phone/i), { target: { value: '87071234455' } });
    fireEvent.click(screen.getByRole('button', { name: /оплатить|pay/i }));
    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument());
  });
});
```

- [ ] **Step 2: Run it and watch it fail**

Run: `npm run test -- PaymentModal`
Expected: FAIL — cannot resolve `./PaymentModal`.

- [ ] **Step 3: Write the modal**

Create `frontend/src/components/PaymentModal.tsx`:

```tsx
/**
 * Unlocking one case.
 *
 * Two paths, because Kaspi has two: an invoice pushed to the payer's phone,
 * which works from any device, and a QR for when the payer is at a desktop.
 * Neither can report success to us directly, so both end in polling.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '@/api/client';
import type { OrderView, PaymentMethod } from '@/types';

const PHONE = /^8\d{10}$/;
const POLL_MS = 2000;
const MAX_POLLS = 150; // five minutes

interface Props {
  profileId: string;
  priceKzt: number;
  onClose: () => void;
  onPaid: () => void;
}

export function PaymentModal({ profileId, priceKzt, onClose, onPaid }: Props) {
  const [method, setMethod] = useState<PaymentMethod>('phone');
  const [phone, setPhone] = useState('');
  const [order, setOrder] = useState<OrderView | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const polls = useRef(0);

  const start = useCallback(async () => {
    setError('');
    if (method === 'phone' && !PHONE.test(phone)) {
      setError('Введите номер в формате 8XXXXXXXXXX');
      return;
    }
    setBusy(true);
    try {
      setOrder(await api.openOrder({
        profile_id: profileId,
        method,
        ...(method === 'phone' ? { phone } : {}),
      }));
    } catch {
      setError('Не удалось выставить счёт. Попробуйте ещё раз.');
    } finally {
      setBusy(false);
    }
  }, [method, phone, profileId]);

  useEffect(() => {
    if (!order || order.status !== 'pending') return undefined;
    const timer = setInterval(async () => {
      polls.current += 1;
      if (polls.current > MAX_POLLS) {
        clearInterval(timer);
        setError('Счёт истёк. Откройте новый.');
        return;
      }
      try {
        const latest = await api.readOrder(order.id);
        setOrder(latest);
        if (latest.status === 'paid') {
          clearInterval(timer);
          onPaid();
        } else if (latest.status !== 'pending') {
          clearInterval(timer);
          setError('Счёт закрыт без оплаты.');
        }
      } catch {
        /* a transient read failure is not worth interrupting the wait */
      }
    }, POLL_MS);
    return () => clearInterval(timer);
  }, [order, onPaid]);

  return (
    <div className="modal" role="dialog" aria-label="Оплата кейса">
      <h2>Полный отчёт по кейсу</h2>
      <p>
        Разовая оплата — <strong>{priceKzt} ₸</strong>. Открывает полный охват программ,
        источники под каждым значением, финансирование и экспорт.
      </p>

      {!order && (
        <>
          <div role="group" aria-label="Способ оплаты">
            <button type="button" aria-pressed={method === 'phone'} onClick={() => setMethod('phone')}>
              По номеру Kaspi
            </button>
            <button type="button" aria-pressed={method === 'qr'} onClick={() => setMethod('qr')}>
              QR
            </button>
          </div>

          {method === 'phone' && (
            <label htmlFor="kaspi-phone">
              Номер телефона
              <input
                id="kaspi-phone"
                inputMode="numeric"
                value={phone}
                onChange={(event) => setPhone(event.target.value.trim())}
                placeholder="87071234455"
              />
            </label>
          )}

          <button type="button" onClick={start} disabled={busy}>
            {busy ? 'Выставляем счёт…' : 'Оплатить'}
          </button>
        </>
      )}

      {order?.method === 'phone' && order.status === 'pending' && (
        <p>Счёт отправлен на {order.phone_masked}. Подтвердите его в приложении Kaspi.</p>
      )}

      {order?.method === 'qr' && order.qr_payload && (
        <p>
          Отсканируйте в Kaspi: <code>{order.qr_payload}</code>
        </p>
      )}

      {order?.status === 'paid' && <p>Оплачено. Открываем полный отчёт…</p>}

      {error && <p role="alert">{error}</p>}

      <button type="button" onClick={onClose}>
        Закрыть
      </button>
    </div>
  );
}
```

- [ ] **Step 4: Write the notice and wire the paywall state**

Create `frontend/src/components/PaywallNotice.tsx`:

```tsx
/** What a locked panel says instead of showing nothing. */

interface Props {
  priceKzt: number;
  onUnlock: () => void;
}

export function PaywallNotice({ priceKzt, onUnlock }: Props) {
  return (
    <div className="paywall" role="note">
      <h3>Этот раздел открывается после оплаты кейса</h3>
      <ul>
        <li>Все найденные программы, а не первые пять</li>
        <li>Источник под каждым значением</li>
        <li>Стипендии, стоимость и разрыв между ними</li>
        <li>Чек-лист документов и экспорт</li>
      </ul>
      <button type="button" onClick={onUnlock}>
        Открыть за {priceKzt} ₸
      </button>
    </div>
  );
}
```

In `frontend/src/lib/store.tsx`, add to the state and the provider value:

```tsx
  const [paywall, setPaywall] = useState<{ profileId: string; priceKzt: number } | null>(null);

  /** Turn a 402 into a paywall. Returns true when it handled the error. */
  const raisePaywall = useCallback((error: unknown): boolean => {
    if (!isPaymentRequired(error)) return false;
    setPaywall({ profileId: error.profileId, priceKzt: error.priceKzt });
    return true;
  }, []);

  const clearPaywall = useCallback(() => setPaywall(null), []);
```

Import `isPaymentRequired` from `@/api/client`, and add `paywall`, `raisePaywall`, `clearPaywall` to the context type and its value object.

In `ExportScreen.tsx` and `ShortlistScreen.tsx`, every call that can 402 offers the
error to `raisePaywall` before the screen's own error handling sees it. Concretely, in
each screen's existing catch:

```tsx
    } catch (error) {
      // A 402 is not a failure to report — it is an offer to make.
      if (raisePaywall(error)) return;
      setError(error instanceof ApiError ? error.message : 'Не удалось загрузить данные');
    }
```

and, in the screen's returned markup, ahead of the content the paywall replaces:

```tsx
      {paywall && (
        <>
          <PaywallNotice priceKzt={paywall.priceKzt} onUnlock={() => setPaying(true)} />
          {paying && (
            <PaymentModal
              profileId={paywall.profileId}
              priceKzt={paywall.priceKzt}
              onClose={() => setPaying(false)}
              onPaid={() => {
                setPaying(false);
                clearPaywall();
                void reload();
              }}
            />
          )}
        </>
      )}
```

`paywall`, `raisePaywall` and `clearPaywall` come from the store hook the screen already
uses; `paying` is local `useState(false)`; `reload` is whatever that screen already calls
to refetch. Keep the screen's existing `setError` shape — do not introduce a second error
mechanism alongside it.

- [ ] **Step 5: Run the tests and watch them pass**

Run: `npm run test -- PaymentModal`
Expected: PASS, 5 tests.

- [ ] **Step 6: Types, lint, full frontend suite, build**

Run: `npx tsc --noEmit && npm run lint && npm run test && npm run build`
Expected: clean, 48 passed, build succeeds.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/PaymentModal.tsx frontend/src/components/PaywallNotice.tsx frontend/src/components/PaymentModal.test.tsx frontend/src/lib/store.tsx frontend/src/screens/ExportScreen.tsx frontend/src/screens/ShortlistScreen.tsx
git commit -m "feat(payments): payment modal and locked affordances"
```

---

### Task 13: Say what is true in the documentation

**Files:**
- Modify: `README.md`
- Modify: `SECURITY.md`
- Modify: `ASSUMPTIONS.md`
- Modify: `RELEASE_CHECKLIST.md`
- Modify: `docs/superpowers/specs/2026-09-04-payments-phase-1-design.md`

- [ ] **Step 1: README**

Add a "Payments" section stating: the model (first run free and deliberately narrower, one payment unlocks one case permanently), the provider (Kaspi via ApiPay), the flag (`UNIMATCH_PAYMENTS_ENABLED`, off by default, and what the product does when off), the endpoints, and the webhook URL the merchant dashboard must be given.

- [ ] **Step 2: SECURITY.md**

Add: the webhook is the only unauthenticated write endpoint; it is HMAC-SHA256 verified against the raw body with `compare_digest`, size-capped at 64 KiB, and rate limited. The payer's phone is stored masked and excluded from logs, URLs and error bodies. Provider secrets are `SecretStr`. The price is server-side only.

- [ ] **Step 3: ASSUMPTIONS.md**

Record, as assumptions rather than facts: the price of 4990 ₸ is a placeholder awaiting the user's decision; no ApiPay account exists yet, so the adapter has never spoken to the real service and every payment claim rests on contract tests; ApiPay's tariff must stay active or no customer can pay.

- [ ] **Step 4: RELEASE_CHECKLIST.md**

Under "Needs the user", add: an ApiPay merchant account with Kaspi Pay connected; `UNIMATCH_APIPAY_API_KEY` and `UNIMATCH_APIPAY_WEBHOOK_SECRET`; the public HTTPS webhook URL registered in the ApiPay dashboard; one end-to-end payment of the real price, verified in both the ApiPay dashboard and our `payment_events` table.

- [ ] **Step 5: Reconcile the spec**

If Task 10 found any divergence between ApiPay's published document and §4 of the design spec, correct §4 now and note what changed.

- [ ] **Step 6: Every gate, one last time**

Run, from `backend/`: `python -m pytest -q && ruff check . && mypy app`
Run, from `frontend/`: `npx tsc --noEmit && npm run lint && npm run test && npm run build`
Expected: all clean.

- [ ] **Step 7: Commit**

```bash
git add README.md SECURITY.md ASSUMPTIONS.md RELEASE_CHECKLIST.md docs/superpowers/specs/2026-09-04-payments-phase-1-design.md
git commit -m "docs: what payments do, what they assume, and what still needs you"
```

---

## Notes for whoever executes this

* **Test counts are estimates.** Another session is committing to `main` in parallel, so the baseline may have moved. What matters is that the count goes up by the number of tests a task adds and that nothing previously passing fails.
* **`payments_enabled` defaults to false on purpose.** If an existing test starts failing with a 402, the fixture enabled payments; do not weaken the guard to make it pass.
* **Never invent an ApiPay field name.** Task 10, Step 1 is not optional. If the published document cannot be reached, stop and say so.
* **The phone number is the sharpest edge here.** It arrives in a request body, is used once, and must be masked before anything is stored. Any test that finds a full number in a log line, a URL, an order row or an error body is reporting a real defect.
