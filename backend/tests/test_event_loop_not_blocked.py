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

import ast
import asyncio
import time
from pathlib import Path

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
    """A source-level backstop that works out for itself what is expensive.

    The first version of this test named the call sites by hand, and promptly
    proved why that is not enough: it did not name ``classify_page``, which
    soups the same page a line below two calls the fix had already moved, in
    six different coroutines. So this one derives the set instead.

    A function is *expensive* when its own body builds a ``BeautifulSoup`` or a
    ``PdfReader``, or when it calls a function that is — closed transitively —
    plus the two network-policy entry points, which resolve a name and so block
    on a socket. Any of those called directly from an ``async def`` in the
    adapters is a stall; passing one to ``off_loop`` is not a call, so the
    fixed form is invisible to this check by construction.
    """

    #: Blocking for a reason no parse tree shows: these resolve a hostname.
    RESOLVERS = frozenset({"check_url", "is_allowed", "resolve_target"})
    #: The primitives whose cost is unbounded in a third party's input.
    PRIMITIVES = ("BeautifulSoup(", "PdfReader(")

    @staticmethod
    def _adapter_sources() -> dict:
        root = Path(__file__).resolve().parent.parent / "app" / "adapters"
        return {
            path: path.read_text(encoding="utf-8")
            for path in sorted(root.rglob("*.py"))
            if "__pycache__" not in str(path)
        }

    def _expensive_names(self, sources: dict) -> set:
        """Every function that ends up parsing, however many hops away."""
        # Sync functions only. An `async def` yields to the loop by
        # definition, so awaiting one is never the stall — whatever it does
        # inside is that function's own problem, and it is checked separately
        # when this walk reaches it.
        bodies: dict[str, str] = {}
        calls: dict[str, set] = {}
        for path, text in sources.items():
            tree = ast.parse(text, filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.FunctionDef):
                    continue
                segment = ast.get_source_segment(text, node) or ""
                bodies[node.name] = segment
                named = set()
                for inner in ast.walk(node):
                    if isinstance(inner, ast.Call):
                        target = inner.func
                        if isinstance(target, ast.Name):
                            named.add(target.id)
                        elif isinstance(target, ast.Attribute):
                            named.add(target.attr)
                calls[node.name] = named

        expensive = {
            name
            for name, segment in bodies.items()
            if any(primitive in segment for primitive in self.PRIMITIVES)
        } | set(self.RESOLVERS)

        # Closure: calling something expensive makes you expensive.
        changed = True
        while changed:
            changed = False
            for name, named in calls.items():
                if name not in expensive and named & expensive:
                    expensive.add(name)
                    changed = True
        return expensive

    def test_no_async_adapter_parses_or_resolves_on_the_loop(self) -> None:
        sources = self._adapter_sources()
        expensive = self._expensive_names(sources)
        # The set is derived, so this is a canary on the derivation itself: the
        # page classifier soups its input, and a version of this test that could
        # not see that is the version that let the stall through.
        assert {"classify_page", "readable_text", "_award_links"} <= expensive

        offenders: list[str] = []
        for path, text in sources.items():
            tree = ast.parse(text, filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.AsyncFunctionDef):
                    continue
                for inner in ast.walk(node):
                    # A nested sync helper is somebody else's problem; it is
                    # only a stall once something awaits it on this loop.
                    if isinstance(inner, ast.FunctionDef) and inner is not node:
                        continue
                    if not isinstance(inner, ast.Call):
                        continue
                    target = inner.func
                    name = (
                        target.id
                        if isinstance(target, ast.Name)
                        else target.attr
                        if isinstance(target, ast.Attribute)
                        else ""
                    )
                    if name in expensive:
                        offenders.append(
                            f"{path.name}:{inner.lineno}: {node.name}() calls {name}() directly"
                        )

        assert not offenders, (
            "these block the event loop — hand them to app.adapters.offload.off_loop:\n"
            + "\n".join(sorted(offenders))
        )
