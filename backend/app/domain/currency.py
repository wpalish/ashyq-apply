"""Currency conversion that always shows its work.

A conversion is a material value here: it decides the funding gap, and a zero
funding gap is the most consequential number this product can print. A rate
therefore carries the same burden of proof as any other claim — a source, an
observation date, and a refusal to answer when it has neither.

Rates come from a provider:

* :class:`StaticFxProvider` — a dated snapshot bundled with the app.
  Deterministic, offline, and what the tests and demo mode run on.
* :class:`EcbFxProvider` — the European Central Bank's daily reference rates,
  published free and without a key by the institution that sets them.

There is no silent fallback between them. When the live provider cannot be
reached, or the newest rate it has is older than :data:`MAX_RATE_AGE_DAYS`, or
the currency is one it does not publish, conversion raises
:class:`FxUnavailable` and the caller keeps the amount in its source currency
and reports the gap as not computable. A stale rate presented as current is
worse than no rate at all.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Protocol
from xml.etree import ElementTree

from app.schemas.money import ConvertedMoney, Money

log = logging.getLogger("unimatch.currency")

#: How old a rate may be before it is refused. Weekends and holidays mean the
#: ECB publishes nothing for up to four days, so a few days' slack is normal;
#: beyond this the number stops describing today's money.
MAX_RATE_AGE_DAYS = 10

#: Bundled snapshot. Units of the currency per 1 USD.
STATIC_RATE_DATE = date(2026, 8, 1)
STATIC_RATE_SOURCE = "Static snapshot bundled with ASHYQ Apply (app/domain/currency.py)"
_PER_USD: dict[str, float] = {
    "USD": 1.0, "EUR": 0.92, "GBP": 0.78, "CAD": 1.36, "AUD": 1.50, "CHF": 0.88,
    "SEK": 10.60, "NOK": 10.70, "DKK": 6.85, "PLN": 3.95, "CZK": 23.10,
    "HUF": 355.0, "TRY": 34.0, "AED": 3.67, "SGD": 1.34, "HKD": 7.82,
    "JPY": 152.0, "KRW": 1340.0, "CNY": 7.16, "KZT": 480.0, "RUB": 92.0,
    "INR": 83.5, "MYR": 4.55, "NZD": 1.63, "ZAR": 18.4, "BRL": 5.35,
    "MXN": 18.0, "ILS": 3.70, "SAR": 3.75, "QAR": 3.64,
}

ECB_DAILY_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"


class FxUnavailable(RuntimeError):
    """No trustworthy rate is available, and none will be invented."""


class UnsupportedCurrency(FxUnavailable, ValueError):
    """The provider publishes no rate for this currency.

    A subclass of both, because the two callers want different things: code
    handling "we cannot convert right now" catches :class:`FxUnavailable`,
    while code that has always treated an unknown currency as bad input keeps
    catching ``ValueError``. The distinction is real — an unreachable feed is
    temporary, an unpublished currency is a property of the request.
    """


@dataclass(frozen=True)
class FxSnapshot:
    """One observation of the exchange market, with its provenance."""

    base: str
    #: Units of each currency per 1 unit of ``base``.
    rates: dict[str, float]
    #: The date the *rates* describe, not the date we read them.
    observed_on: date
    source_url: str
    provider_id: str
    fetched_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    #: Whether this snapshot claims to describe *today's* market. The staleness
    #: limit applies only to snapshots that make that claim. The bundled table
    #: does not: it is openly a dated snapshot, every conversion through it is
    #: labelled an estimate, and production is expected to configure a live
    #: provider instead. That keeps tests deterministic without ever letting an
    #: old rate be presented as a current one.
    authoritative: bool = True

    @property
    def age_days(self) -> int:
        return (date.today() - self.observed_on).days

    def factor(self, from_currency: str, to_currency: str) -> float:
        src, dst = from_currency.upper(), to_currency.upper()
        missing = [c for c in (src, dst) if c not in self.rates]
        if missing:
            raise UnsupportedCurrency(
                f"{self.provider_id} publishes no rate for {', '.join(missing)}. "
                "The amount stays in its original currency."
            )
        return self.rates[dst] / self.rates[src]


class FxProvider(Protocol):
    def snapshot(self) -> FxSnapshot: ...


class StaticFxProvider:
    """The bundled snapshot. Deterministic and offline by construction."""

    provider_id = "static-bundled"

    def snapshot(self) -> FxSnapshot:
        return FxSnapshot(
            base="USD", rates=dict(_PER_USD), observed_on=STATIC_RATE_DATE,
            source_url=STATIC_RATE_SOURCE, provider_id=self.provider_id,
            authoritative=False,
        )


class EcbFxProvider:
    """The European Central Bank's daily euro reference rates.

    Free, keyless, and published by the institution that sets them. One fixed
    URL is fetched, so there is no user-controlled destination here.

    The result is cached for the process: a research run converts many amounts
    and the ECB publishes once a day.
    """

    provider_id = "ecb-daily"

    def __init__(self, *, timeout: float = 10.0, attempts: int = 2) -> None:
        self.timeout = timeout
        self.attempts = max(1, attempts)
        self._cached: FxSnapshot | None = None

    @staticmethod
    def parse(xml: str) -> FxSnapshot:
        """Read the ECB envelope. Raises rather than returning an empty table."""
        try:
            root = ElementTree.fromstring(xml)
        except ElementTree.ParseError as exc:
            raise FxUnavailable(f"the ECB rate feed could not be parsed: {exc}") from exc

        observed: date | None = None
        rates: dict[str, float] = {"EUR": 1.0}
        for node in root.iter():
            attrib = node.attrib
            if "time" in attrib:
                try:
                    observed = date.fromisoformat(attrib["time"])
                except ValueError:
                    continue
            currency, value = attrib.get("currency"), attrib.get("rate")
            if currency and value:
                try:
                    rates[currency.upper()] = float(value)
                except ValueError:
                    continue
        if observed is None or len(rates) < 2:
            raise FxUnavailable(
                "the ECB rate feed carried no dated rate table; no rate was invented"
            )
        return FxSnapshot(
            base="EUR", rates=rates, observed_on=observed,
            source_url=ECB_DAILY_URL, provider_id=EcbFxProvider.provider_id,
        )

    def snapshot(self) -> FxSnapshot:
        if self._cached is not None and self._cached.age_days <= MAX_RATE_AGE_DAYS:
            return self._cached
        import httpx

        last = ""
        for attempt in range(self.attempts):
            try:
                with httpx.Client(timeout=self.timeout, follow_redirects=False) as client:
                    response = client.get(ECB_DAILY_URL)
                response.raise_for_status()
                self._cached = self.parse(response.text)
                return self._cached
            except FxUnavailable:
                raise
            except Exception as exc:  # network, TLS, HTTP status
                last = f"{type(exc).__name__}: {exc}"
                log.info("ECB rate fetch attempt %s failed: %s", attempt + 1, last)
        raise FxUnavailable(f"the ECB rate feed could not be reached ({last})")


#: The provider used when a caller does not name one. It is a *default*, never
#: a switch: nothing reassigns it at runtime. An earlier version let
#: `ResearchRunner` point a module-level global at whichever provider its own
#: run wanted, so with two jobs in flight — the worker runs two by default —
#: one run silently re-pointed the other's conversions at a different source.
#: A funding gap has to be computed against one snapshot, and that snapshot has
#: to be the one its own run recorded.
_DEFAULT_PROVIDER: FxProvider = StaticFxProvider()


def default_provider() -> FxProvider:
    """The fallback for callers outside a run, such as the vocabulary endpoint."""
    return _DEFAULT_PROVIDER


def provider_for(settings_value: str, *, demo: bool) -> FxProvider:
    """The provider one run should use, built fresh for that run.

    Demo mode is deterministic and offline, so it always uses the bundled
    table whatever the configuration says.
    """
    if demo or settings_value == "static":
        return StaticFxProvider()
    return EcbFxProvider()


def compute_provider_signature(provider: FxProvider) -> dict[str, object]:
    """What a run records about the rates it used, for its evidence trail."""
    try:
        snap = provider.snapshot()
    except FxUnavailable as exc:
        return {
            "provider": getattr(provider, "provider_id", "unknown"),
            "available": False,
            "reason": str(exc),
        }
    return {
        "provider": snap.provider_id,
        "available": True,
        "source_url": snap.source_url,
        "observed_on": snap.observed_on.isoformat(),
        "fetched_at": snap.fetched_at.isoformat(),
        "authoritative": snap.authoritative,
        "age_days": snap.age_days,
    }


def _usable_snapshot(provider: FxProvider | None = None) -> FxSnapshot:
    snap = (provider or _DEFAULT_PROVIDER).snapshot()
    if snap.authoritative and snap.age_days > MAX_RATE_AGE_DAYS:
        raise FxUnavailable(
            f"the newest rate available is stale: observed on {snap.observed_on} "
            f"({snap.age_days} days ago, limit {MAX_RATE_AGE_DAYS}). "
            "The amount stays in its original currency."
        )
    return snap


def supported_currencies(provider: FxProvider | None = None) -> list[str]:
    """Currencies this provider can actually convert, right now.

    On failure this returned the bundled table's currencies, which advertised
    live conversions that were not available. An unavailable provider supports
    nothing.
    """
    try:
        return sorted((provider or _DEFAULT_PROVIDER).snapshot().rates)
    except FxUnavailable:
        return []


def rate(
    from_currency: str, to_currency: str, *, provider: FxProvider | None = None
) -> float:
    return _usable_snapshot(provider).factor(from_currency, to_currency)


def convert(
    money: Money, to_currency: str, *, provider: FxProvider | None = None
) -> ConvertedMoney | Money:
    """Convert, preserving the original amount, the rate and the rate's date.

    Returns the input untouched when the currency already matches, so callers
    never see a spurious ``rate=1.0`` conversion record.
    """
    dst = to_currency.upper()
    if money.currency.upper() == dst:
        return money
    snap = _usable_snapshot(provider)
    r = snap.factor(money.currency, dst)
    return ConvertedMoney(
        amount=round(money.amount * r, 2),
        currency=dst,
        academic_year=money.academic_year,
        as_of=money.as_of,
        range_low=round(money.range_low * r, 2) if money.range_low is not None else None,
        range_high=round(money.range_high * r, 2) if money.range_high is not None else None,
        source_url=money.source_url,
        original_amount=money.amount,
        original_currency=money.currency.upper(),
        rate=r,
        rate_date=snap.observed_on,
        rate_source=(
            f"{snap.provider_id} — {snap.source_url}"
            + ("" if snap.authoritative else
               f" (bundled snapshot of {snap.observed_on}, not a live rate)")
        ),
        # A conversion is only as current as its rate. One made from the
        # bundled table is an estimate and says so, wherever it is displayed.
        is_estimate=money.is_estimate or not snap.authoritative,
    )
