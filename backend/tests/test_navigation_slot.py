"""ER-07: one programme-page slot kept for the navigation hop, off by default."""

from __future__ import annotations

from types import SimpleNamespace

from app.adapters.search.retrieval import RankedCandidate


def _ranked(url: str, provider: str = "fake") -> RankedCandidate:
    return RankedCandidate(url=url, title="", score=1.0, provider=provider, signals=())


SEARCH = [_ranked(f"https://ex.edu/search-{i}") for i in range(4)]
NAV = _ranked("https://cs.ex.edu/content?menu=40", provider="navigation")


async def _merge(monkeypatch, profile, tmp_path, *, slot: bool) -> tuple[list[str], list[str]]:
    import app.adapters.discovery.live_discovery as live
    import app.adapters.search as search_pkg
    import app.adapters.search.retrieval as retrieval
    from app.adapters.discovery.live_discovery import (
        DiscoveryTrace,
        LiveDiscoveryAdapter,
        PageCategory,
    )

    async def fake_discover(provider, intent, **kwargs):
        return SimpleNamespace(
            candidates=(*SEARCH, NAV),
            provider="fake",
            queries_run=(),
            failed_queries=(),
            failure_diagnostics=(),
            rejection_counts={},
            throttled=False,
        )

    monkeypatch.setattr(search_pkg, "get_search_provider", lambda: object())
    monkeypatch.setattr(retrieval, "discover_candidates", fake_discover)
    monkeypatch.setattr(live, "NAVIGATION_SLOT", slot)
    # This fixture isolates the earlier rank-only slot experiment and has no
    # fetched page bodies. Content recovery is tested with real FetchResults
    # in test_search_identity_recovery.py.
    monkeypatch.setattr(live, "RECOVER_SEARCH_CANDIDATES", False)

    class _Fetcher:
        async def get(self, url):
            return None

    adapter = LiveDiscoveryAdapter(_Fetcher(), registry_path=tmp_path / "missing.json")  # type: ignore[arg-type]
    selected: dict[str, list[str]] = {
        c: [] for c in vars(PageCategory).values() if isinstance(c, str)
    }
    trace = DiscoveryTrace(institution="Ex", domain="ex.edu")
    await adapter._add_search_results({"name": "Ex"}, "ex.edu", selected, trace, profile)
    return selected[PageCategory.PROGRAM_PAGE], trace.errors


async def test_off_search_fills_every_slot(monkeypatch, profile, tmp_path) -> None:
    pages, _ = await _merge(monkeypatch, profile, tmp_path, slot=False)
    assert pages == [c.url for c in SEARCH[:3]]


async def test_on_the_navigation_candidate_keeps_one_slot(monkeypatch, profile, tmp_path) -> None:
    pages, errors = await _merge(monkeypatch, profile, tmp_path, slot=True)
    assert pages == [SEARCH[0].url, SEARCH[1].url, NAV.url]
    assert any(e.startswith("navigation slot:") for e in errors)
