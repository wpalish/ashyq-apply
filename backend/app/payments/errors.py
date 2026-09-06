"""Provider failures, named after what ApiPay actually returns.

Anything the caller must react to differently gets its own class. Everything
else becomes a ``ProviderRejected`` carrying the provider's own error code, so
a code we have never seen still reaches the logs intact rather than being
flattened into "something went wrong".
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
    """The provider refused, and will refuse again unless the request changes."""

    code = "provider_rejected"


class TariffInactive(PaymentError):
    """Our own ApiPay subscription has lapsed. No customer can pay until it is fixed."""

    code = "tariff_inactive"


class SessionExpired(PaymentError):
    """The Kaspi cashier session needs re-authorising in the ApiPay dashboard."""

    code = "kaspi_session_expired"


class RateLimited(PaymentError):
    """The provider is throttling us. ``retry_after`` is its own advice, in seconds."""

    code = "request_rate_limited"

    def __init__(self, message: str, *, retry_after: int = 1) -> None:
        super().__init__(message)
        self.retry_after = retry_after
