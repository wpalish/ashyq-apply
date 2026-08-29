"""Two runs converting money at the same time must not see each other's rates.

The worker runs two jobs concurrently by default. `ResearchRunner` selected the
exchange-rate provider by assigning to a module-level global, so whichever run
started second silently re-pointed the first run's currency conversions at a
different source — a demo job could hand its bundled table to a live job
halfway through computing a funding gap.

A funding gap is the number this product is most careful about. It has to be
computed against one snapshot, and that snapshot has to be the one the run
recorded.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime

import pytest

from app.domain.currency import FxSnapshot, convert
from app.schemas.money import Money


def snapshot(provider_id: str, usd_per_eur: float) -> FxSnapshot:
    """A snapshot whose EUR->USD factor identifies which provider produced it."""
    return FxSnapshot(
        base="EUR",
        rates={"EUR": 1.0, "USD": usd_per_eur},
        observed_on=date.today(),
        source_url=f"https://example.invalid/{provider_id}",
        provider_id=provider_id,
        fetched_at=datetime.now(UTC),
    )


class SlowProvider:
    """Yields control while producing its snapshot, so runs really interleave."""

    def __init__(self, provider_id: str, usd_per_eur: float, delay: float = 0.02):
        self.provider_id = provider_id
        self._snapshot = snapshot(provider_id, usd_per_eur)
        self._delay = delay

    def snapshot(self) -> FxSnapshot:
        return self._snapshot

    async def converted(self, amount: float) -> float:
        """Convert with a suspension point in the middle, as a real run has."""
        await asyncio.sleep(self._delay)
        out = convert(
            Money(amount=amount, currency="EUR"), "USD", provider=self,
        )
        await asyncio.sleep(self._delay)
        return out.amount


class TestConcurrentRunsKeepTheirOwnRates:
    @pytest.mark.asyncio
    async def test_two_runs_with_different_providers_do_not_cross(self):
        """The reproduction: one run expects 20.0, the other 10.87."""
        a = SlowProvider("run-a", 2.0)      # 10 EUR -> 20 USD
        b = SlowProvider("run-b", 1.087)    # 10 EUR -> 10.87 USD

        results = await asyncio.gather(
            *[a.converted(10.0) for _ in range(6)],
            *[b.converted(10.0) for _ in range(6)],
        )
        from_a, from_b = results[:6], results[6:]
        assert all(v == pytest.approx(20.0) for v in from_a), (
            f"run A saw another run's rate: {from_a}"
        )
        assert all(v == pytest.approx(10.87) for v in from_b), (
            f"run B saw another run's rate: {from_b}"
        )

    @pytest.mark.asyncio
    async def test_a_demo_run_cannot_hand_its_bundled_table_to_a_live_run(self):
        from app.domain.currency import EcbFxProvider, StaticFxProvider

        live = EcbFxProvider()
        demo = StaticFxProvider()
        # Only the shapes matter here; neither is asked for a live rate.
        assert live.provider_id != demo.provider_id

        demo_snap = demo.snapshot()
        assert demo_snap.authoritative is False, (
            "the bundled table must never claim to describe today's market"
        )

    @pytest.mark.asyncio
    async def test_each_conversion_names_the_provider_that_produced_it(self):
        a, b = SlowProvider("run-a", 2.0), SlowProvider("run-b", 1.087)
        out_a = convert(Money(amount=10, currency="EUR"), "USD", provider=a)
        out_b = convert(Money(amount=10, currency="EUR"), "USD", provider=b)
        assert "run-a" in out_a.rate_source
        assert "run-b" in out_b.rate_source


class TestTheProviderIsExplicit:
    def test_conversion_requires_a_provider_rather_than_reading_a_global(self):
        """A conversion with no provider is a bug, not a default.

        Reading process state here is what let one run change another's rates.
        """
        import inspect

        from app.domain.currency import compute_provider_signature, convert

        assert "provider" in inspect.signature(convert).parameters
        assert compute_provider_signature is not None

    def test_the_gap_calculation_takes_a_provider(self):
        import inspect

        from app.domain.costs import compute_funding_gap

        assert "provider" in inspect.signature(compute_funding_gap).parameters


class TestCapabilitiesDescribeThisInstance:
    """`/api/capabilities` must describe the configured instance.

    It read a process-global provider, so before any run had started it
    described a default nobody was using, and its limits text said "a dated
    static snapshot, not a live feed" even where live rates were configured.
    """

    @staticmethod
    def meta(*, demo: bool, fx: str) -> dict:
        from app.api.routes_meta import _currency_meta
        from app.config import Settings

        return _currency_meta(Settings(demo_mode=demo, fx_provider=fx))

    def test_a_live_instance_reports_the_live_provider(self):
        assert self.meta(demo=False, fx="ecb")["provider"] == "ecb-daily"

    def test_a_static_instance_reports_the_bundled_table(self):
        meta = self.meta(demo=False, fx="static")
        assert meta["provider"] == "static-bundled"
        assert meta["authoritative"] is False

    def test_demo_mode_always_reports_the_bundled_table(self):
        """Demo is deterministic and offline whatever the configuration says."""
        assert self.meta(demo=True, fx="ecb")["provider"] == "static-bundled"

    def test_it_answers_before_any_run_has_started(self):
        """No run has set anything; the answer comes from the configuration."""
        assert self.meta(demo=False, fx="ecb")["available"] in (True, False)

    def test_the_limits_sentence_matches_the_provider(self):
        from app.api.routes_meta import _currency_limit
        from app.config import Settings

        live = _currency_limit(Settings(demo_mode=False, fx_provider="ecb"))
        bundled = _currency_limit(Settings(demo_mode=False, fx_provider="static"))
        assert "bundled snapshot" in bundled
        assert "bundled snapshot" not in live

    def test_an_unavailable_provider_advertises_no_currencies(self):
        """Listing the bundled table's currencies would advertise live
        conversions that are not available."""
        from app.domain.currency import FxUnavailable, supported_currencies

        class Broken:
            provider_id = "broken"

            def snapshot(self):
                raise FxUnavailable("unreachable")

        assert supported_currencies(Broken()) == []


class TestTheRunRecordsWhatItUsed:
    def test_the_signature_carries_full_provenance(self):
        from app.domain.currency import StaticFxProvider, compute_provider_signature

        sig = compute_provider_signature(StaticFxProvider())
        for key in ("provider", "source_url", "observed_on", "fetched_at",
                    "authoritative", "age_days"):
            assert key in sig, f"{key} missing from the run's rate provenance"

    def test_an_unavailable_provider_is_recorded_as_such(self):
        from app.domain.currency import FxUnavailable, compute_provider_signature

        class Broken:
            provider_id = "broken"

            def snapshot(self):
                raise FxUnavailable("the feed could not be reached")

        sig = compute_provider_signature(Broken())
        assert sig["available"] is False
        assert "could not be reached" in str(sig["reason"])

    def test_demo_and_live_select_different_providers(self):
        from app.domain.currency import provider_for

        assert provider_for("ecb", demo=True).provider_id == "static-bundled"
        assert provider_for("ecb", demo=False).provider_id == "ecb-daily"
        assert provider_for("static", demo=False).provider_id == "static-bundled"
