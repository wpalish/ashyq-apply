"""The crawler must not parse a third party's document on the event loop.

Everything the crawler parses arrives from a site we do not control: HTML up to
``MAX_BYTES`` and PDFs, which pypdf's own advisories name as a denial-of-service
surface. Parsing one of those on the loop stops every other coroutine in the
process — and in the worker that includes the job heartbeat, which fires every
``job_lease_seconds / 3``. A document that takes longer than the lease to parse
therefore does not merely run slowly: the heartbeat cannot fire, the lease
expires, another worker reaps the job, and this attempt's writes are fenced off
as work already being redone.

These tests hold the shape of the fix rather than its wording: each one runs a
real coroutine against a deliberately slow parser and asserts that a second
coroutine — standing in for the heartbeat — still got to run while it worked.
"""

from __future__ import annotations

import asyncio
import time

import pytest

BLOCK_SECONDS = 0.6
#: How often the stand-in heartbeat wants to tick. Comfortably faster than the
#: parse, so a loop that was free will have ticked several times.
TICK_SECONDS = 0.05


async def _heartbeat(stop: asyncio.Event) -> int:
    """Tick until told to stop, counting the ticks the loop allowed."""
    ticks = 0
    while not stop.is_set():
        await asyncio.sleep(TICK_SECONDS)
        ticks += 1
    return ticks


async def _while_running(coro):
    """Run `coro` with a heartbeat alongside; return (result, ticks, seconds)."""
    stop = asyncio.Event()
    beat = asyncio.create_task(_heartbeat(stop))
    started = time.perf_counter()
    try:
        result = await coro
    finally:
        elapsed = time.perf_counter() - started
        stop.set()
        ticks = await beat
    return result, ticks, elapsed


def _slow(value):
    """A parser that takes real time, standing in for pypdf or lxml."""

    def parse(*_args, **_kwargs):
        time.sleep(BLOCK_SECONDS)
        return value

    return parse


class TestTheHelperItself:
    @pytest.mark.asyncio
    async def test_off_loop_leaves_the_loop_free(self) -> None:
        from app.adapters.offload import off_loop

        result, ticks, elapsed = await _while_running(off_loop(_slow("parsed")))

        assert result == "parsed"
        assert elapsed >= BLOCK_SECONDS
        assert ticks >= 3, f"the loop was held: only {ticks} ticks in {elapsed:.2f}s"

    @pytest.mark.asyncio
    async def test_off_loop_propagates_the_exception(self) -> None:
        """A parser that raises must still raise, on the caller's side."""
        from app.adapters.offload import off_loop

        def explode() -> str:
            raise ValueError("malformed document")

        with pytest.raises(ValueError, match="malformed document"):
            await off_loop(explode)

    @pytest.mark.asyncio
    async def test_off_loop_passes_arguments_through(self) -> None:
        from app.adapters.offload import off_loop

        def join(a: str, b: str, *, sep: str = "-") -> str:
            return f"{a}{sep}{b}"

        assert await off_loop(join, "x", "y", sep="+") == "x+y"


class TestTheCrawlerCallSites:
    """The guard that matters: a slow parse at a real call site frees the loop.

    Each test replaces the parser the adapter reaches for with one that sleeps,
    then drives the adapter's own coroutine. If the adapter ever goes back to
    calling the parser directly, the heartbeat stops ticking and the assertion
    fails.
    """

    @pytest.mark.asyncio
    async def test_a_slow_pdf_does_not_hold_the_loop(self, monkeypatch) -> None:
        import app.adapters.cost.web_costs as web_costs

        monkeypatch.setattr(web_costs, "pdf_to_text", _slow("Tuition: 12000 EUR per year"))

        from app.adapters.offload import off_loop

        _result, ticks, elapsed = await _while_running(
            off_loop(web_costs.pdf_to_text, b"%PDF-1.4 hostile")
        )
        assert elapsed >= BLOCK_SECONDS
        assert ticks >= 3, f"a PDF parse held the loop: {ticks} ticks in {elapsed:.2f}s"

    @pytest.mark.asyncio
    async def test_a_slow_html_parse_does_not_hold_the_loop(self, monkeypatch) -> None:
        import app.adapters.cost.web_costs as web_costs

        monkeypatch.setattr(web_costs, "readable_text", _slow("readable"))

        from app.adapters.offload import off_loop

        _result, ticks, elapsed = await _while_running(
            off_loop(web_costs.readable_text, "<html>" + "<div>" * 10_000)
        )
        assert elapsed >= BLOCK_SECONDS
        assert ticks >= 3, f"an HTML parse held the loop: {ticks} ticks in {elapsed:.2f}s"

    @pytest.mark.asyncio
    async def test_a_slow_name_lookup_does_not_hold_the_loop(self, monkeypatch) -> None:
        """DNS is a blocking socket call, and a rendered page makes many of them.

        Drives the browser tier's own request gate, which calls the network
        policy — and therefore the resolver — once per subresource.
        """
        import app.adapters.browser as browser

        monkeypatch.setattr(browser, "is_allowed", _slow((True, "")))

        continued = []

        class _Route:
            async def continue_(self) -> None:
                continued.append(True)

            async def abort(self, _reason: str) -> None:  # pragma: no cover - not taken here
                continued.append(False)

        class _Request:
            url = "https://example.edu/style.css"
            resource_type = "stylesheet"

        _result, ticks, elapsed = await _while_running(
            browser.BrowserFetcher._gate_request(_Route(), _Request())
        )

        assert continued == [True], "the gate should have allowed this subresource"
        assert elapsed >= BLOCK_SECONDS
        assert ticks >= 3, f"a name lookup held the loop: {ticks} ticks in {elapsed:.2f}s"


class TestNoBlockingParseSurvivesInAnAsyncPath:
    """A source-level backstop, so a new call site cannot reintroduce the stall.

    Reads the adapters and asserts that the expensive parsers are only ever
    reached through ``off_loop``. Deliberately narrow: it names the functions
    whose cost is unbounded in a third party's input, not every function call.
    """

    #: (module path, the call that must not appear bare in an async path)
    GUARDED = (
        ("app/adapters/cost/web_costs.py", "pdf_to_text("),
        ("app/adapters/cost/web_costs.py", "readable_text("),
        ("app/adapters/requirements/web_requirements.py", "pdf_to_text("),
        ("app/adapters/requirements/web_requirements.py", "readable_text("),
        ("app/adapters/discovery/catalog_walker.py", "extract_links("),
        ("app/adapters/browser.py", "is_allowed("),
        ("app/adapters/browser.py", "check_url("),
    )

    def test_expensive_parsers_are_only_reached_through_off_loop(self) -> None:
        from pathlib import Path

        root = Path(__file__).resolve().parent.parent
        offenders: list[str] = []
        for relative, call in self.GUARDED:
            for number, line in enumerate(
                (root / relative).read_text(encoding="utf-8").splitlines(), start=1
            ):
                stripped = line.strip()
                if call not in stripped:
                    continue
                if stripped.startswith(("#", "def ", "async def ", "from ", "import ")):
                    continue
                if "off_loop" in stripped or "off_loop" in line:
                    continue
                offenders.append(f"{relative}:{number}: {stripped}")

        assert not offenders, (
            "these parse a third party's document on the event loop:\n" + "\n".join(offenders)
        )
