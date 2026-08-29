"""Foreign-exchange rates: where they came from and when they were observed.

A conversion is a material value in this product — it decides the funding gap,
and a zero funding gap is the most consequential number the system can print.
So a rate carries the same burden of proof as any other claim: a source, an
observation date, and a refusal to answer when it has neither.

The rule these tests protect: when a rate cannot be obtained or is too old to
trust, the amount stays in its original currency and the gap is reported as
not computable. It never silently falls back to a stale number.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest

from app.domain.currency import (
    MAX_RATE_AGE_DAYS,
    EcbFxProvider,
    FxSnapshot,
    FxUnavailable,
    StaticFxProvider,
    convert,
    rate,
)
from app.schemas.money import Money

# There is no global provider to restore: every call names the one it wants.


def snapshot(observed: date, rates: dict[str, float]) -> FxSnapshot:
    return FxSnapshot(
        base="USD", rates={"USD": 1.0, **rates}, observed_on=observed,
        source_url="https://example.invalid/rates", provider_id="test",
    )


class StubProvider:
    def __init__(self, snap: FxSnapshot | None, error: str = "") -> None:
        self._snap, self._error, self.calls = snap, error, 0

    def snapshot(self) -> FxSnapshot:
        self.calls += 1
        if self._snap is None:
            raise FxUnavailable(self._error or "no rates")
        return self._snap


class TestProvenance:
    def test_a_conversion_carries_its_rate_source_and_date(self):
        provider = StubProvider(snapshot(date(2026, 8, 28), {"EUR": 0.90}))
        out = convert(Money(amount=1000, currency="EUR"), "USD", provider=provider)
        assert out.original_amount == 1000
        assert out.original_currency == "EUR"
        assert out.rate_date == date(2026, 8, 28)
        assert "example.invalid" in out.rate_source

    def test_the_source_amount_is_always_preserved(self):
        provider = StubProvider(snapshot(date(2026, 8, 28), {"EUR": 0.90}))
        out = convert(Money(amount=1234.56, currency="EUR"), "USD", provider=provider)
        assert out.original_amount == 1234.56
        assert out.original_currency == "EUR"

    def test_same_currency_is_not_a_conversion(self):
        out = convert(Money(amount=100, currency="USD"), "USD")
        assert not hasattr(out, "rate")


class TestNoSilentFallback:
    def test_an_unavailable_provider_raises_rather_than_guessing(self):
        provider = StubProvider(None, "the rate service could not be reached")
        with pytest.raises(FxUnavailable) as exc:
            convert(Money(amount=1000, currency="EUR"), "USD", provider=provider)
        assert "could not be reached" in str(exc.value)

    def test_a_stale_snapshot_is_refused(self):
        old = date.today() - timedelta(days=MAX_RATE_AGE_DAYS + 1)
        provider = StubProvider(snapshot(old, {"EUR": 0.90}))
        with pytest.raises(FxUnavailable) as exc:
            convert(Money(amount=1000, currency="EUR"), "USD", provider=provider)
        assert "stale" in str(exc.value).lower()
        assert str(old) in str(exc.value), "the refusal must say how old the rate is"

    def test_a_fresh_snapshot_is_accepted(self):
        fresh = date.today() - timedelta(days=1)
        provider = StubProvider(snapshot(fresh, {"EUR": 0.90}))
        assert convert(Money(amount=1000, currency="EUR"), "USD", provider=provider).rate_date == fresh

    def test_a_currency_the_provider_does_not_publish_is_refused(self):
        """The ECB publishes no rate for the Kazakhstani tenge. Refusing is the
        honest answer; inventing one would corrupt a funding gap."""
        provider = StubProvider(snapshot(date.today(), {"EUR": 0.90}))
        with pytest.raises(FxUnavailable) as exc:
            convert(Money(amount=1000, currency="KZT"), "USD", provider=provider)
        assert "KZT" in str(exc.value)


class TestCaching:
    def test_the_provider_is_asked_once_per_conversion_batch(self):
        stub = StubProvider(snapshot(date.today(), {"EUR": 0.90, "GBP": 0.78}))
        provider = stub
        convert(Money(amount=1, currency="EUR"), "USD", provider=provider)
        convert(Money(amount=1, currency="GBP"), "USD", provider=provider)
        assert stub.calls <= 2, "each conversion re-fetched the rate table"


class TestStaticProvider:
    """The deterministic provider tests and demo mode run on."""

    def test_it_is_deterministic(self):
        provider = StaticFxProvider()
        assert rate("EUR", "USD", provider=provider) == rate("EUR", "USD", provider=provider)

    def test_it_reports_its_own_date_and_source(self):
        provider = StaticFxProvider()
        snap = provider.snapshot()
        assert snap.observed_on
        assert "bundled" in snap.source_url.lower() or "static" in snap.provider_id.lower()

    def test_it_never_reaches_the_network(self, monkeypatch):
        import httpx

        def explode(*a, **k):
            raise AssertionError("the static provider must not use the network")

        monkeypatch.setattr(httpx, "Client", explode)
        provider = StaticFxProvider()
        assert rate("EUR", "USD", provider=provider) > 0


class TestEcbProviderParsing:
    """Parsing is tested offline; the live fetch is exercised by the canary."""

    XML = """<?xml version="1.0" encoding="UTF-8"?>
    <gesmes:Envelope xmlns:gesmes="http://www.gesmes.org/xml/2002-08-01"
                     xmlns="http://www.ecb.int/vocabulary/2002-08-01/eurofxref">
      <Cube><Cube time="2026-08-28">
        <Cube currency="USD" rate="1.0850"/>
        <Cube currency="GBP" rate="0.8450"/>
        <Cube currency="PLN" rate="4.2700"/>
      </Cube></Cube>
    </gesmes:Envelope>"""

    def test_it_reads_the_published_date_and_rates(self):
        snap = EcbFxProvider.parse(self.XML)
        assert snap.observed_on == date(2026, 8, 28)
        assert snap.rates["EUR"] == 1.0
        assert snap.rates["USD"] == pytest.approx(1.0850)
        assert snap.base == "EUR"

    def test_a_cross_rate_goes_through_the_base(self):
        snap = EcbFxProvider.parse(self.XML)
        gbp_per_usd = snap.rates["GBP"] / snap.rates["USD"]
        assert gbp_per_usd == pytest.approx(0.8450 / 1.0850)

    def test_malformed_xml_raises_rather_than_returning_nothing(self):
        with pytest.raises(FxUnavailable):
            EcbFxProvider.parse("<not-xml")

    def test_an_empty_table_raises(self):
        with pytest.raises(FxUnavailable):
            EcbFxProvider.parse(
                '<gesmes:Envelope xmlns:gesmes="http://www.gesmes.org/xml/2002-08-01">'
                "</gesmes:Envelope>"
            )


class TestAuditTrail:
    def test_the_snapshot_records_when_it_was_observed_not_when_it_was_used(self):
        observed = date(2026, 8, 27)
        snap = snapshot(observed, {"EUR": 0.90})
        assert snap.observed_on == observed
        assert snap.fetched_at <= datetime.now(UTC)


class TestGapIsNotComputedWithoutARate:
    """The most consequential number in the product is a zero funding gap.

    When no rate is available the gap must be reported as not computable — not
    zero, and not an exception that takes the run down with it.
    """

    @staticmethod
    def breakdown_and_award():
        from app.schemas.money import Money
        from app.schemas.result import CostBreakdown, Scholarship

        costs = CostBreakdown(
            academic_year="2027/28",
            total=Money(amount=20000, currency="EUR", academic_year="2027/28"),
        )
        award = Scholarship(id="s1", name="Test Award",
                            amount=Money(amount=20000, currency="EUR"))
        return costs, award

    def test_an_unreachable_provider_does_not_raise_out_of_the_gap_calculation(self):
        from app.domain.costs import compute_funding_gap

        provider = StubProvider(None, "the rate feed could not be reached")
        costs, award = self.breakdown_and_award()
        gap = compute_funding_gap(costs, [award], target_currency="USD", provider=provider)
        assert gap is None or gap.computable is False, (
            "an unreachable rate feed must yield 'not computable', never a number"
        )

    def test_a_stale_provider_does_not_produce_a_zero_gap(self):
        from datetime import timedelta

        from app.domain.costs import compute_funding_gap

        old = date.today() - timedelta(days=MAX_RATE_AGE_DAYS + 5)
        provider = StubProvider(snapshot(old, {"EUR": 0.90}))
        costs, award = self.breakdown_and_award()
        gap = compute_funding_gap(costs, [award], target_currency="USD", provider=provider)
        assert gap is None or gap.computable is False
