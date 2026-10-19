"""Harness defect 2026-10-19: a dev5 case built through the harness reaches discovery search.

The first dev5 paired baseline read ``discovery_queries = 0`` over thirteen cases
while dev4, on the same homepage-entry path, sends about four per case. These
tests run the real child path (``live.capture_one`` -> canary -> runner ->
discovery) offline, with the search provider mocked and every page synthetic,
and prove a dev5 case and a dev4 case take the same path to the provider: the
same query families, restricted to the case's own official domain, recorded in
the discovery trace the stage summary reads. Nothing here reads a dev5 capture,
log or label.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

import app.adapters.search as search
from app.adapters import fetching
from app.adapters.fetching import FetchOutcome, FetchResult
from app.adapters.search.base import SearchResponse
from evaluation.research import live

_HTML = (
    "<html><head><title>University</title></head><body>"
    '<a href="/study/bachelor/computer-science">Computer Science BSc</a>'
    f"<p>{'text ' * 200}</p></body></html>"
)


class _Provider:
    name = "fake"

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[str, ...]]] = []

    async def search(self, *, query: str, domains=(), max_results: int = 10) -> SearchResponse:
        self.calls.append((query, tuple(domains)))
        return SearchResponse(query=query, provider=self.name, retrieved_at=datetime.now(UTC))


async def _capture(case_id: str, tmp_path: Path, monkeypatch) -> tuple[_Provider, dict]:
    provider = _Provider()

    async def get(self, url: str, **kwargs) -> FetchResult:
        return FetchResult(
            url=url,
            outcome=FetchOutcome.OK,
            status_code=200,
            final_url=url,
            text=_HTML,
            content=_HTML.encode(),
            content_type="text/html",
        )

    monkeypatch.setattr(search, "get_search_provider", lambda: provider)
    monkeypatch.setattr(fetching.Fetcher, "get", get)
    output = tmp_path / f"{case_id}.json"
    await live.capture_one(case_id, output, 60, 120)
    raw = json.loads(output.with_suffix(".raw.json").read_text(encoding="utf-8"))
    trace = raw["canary"]["institutions"][0]["discovery_trace"]
    return provider, trace


@pytest.mark.asyncio
@pytest.mark.parametrize("case_id", ["lmu", "kbtu"])
async def test_a_dev5_case_reaches_discovery_search_like_a_dev4_case(
    case_id, tmp_path, monkeypatch
) -> None:
    # lmu: on-seed, www host; kbtu: off-seed row added by the harness, bare host.
    assert case_id in live.DEV5_DOMAINS and case_id in live.NO_REGISTRY_CASES
    dev5, dev5_trace = await _capture(case_id, tmp_path, monkeypatch)
    dev4, dev4_trace = await _capture("rwth", tmp_path, monkeypatch)

    for calls, trace, domain in (
        (dev5.calls, dev5_trace, live.DEV5_DOMAINS[case_id]),
        (dev4.calls, dev4_trace, live.DEV4_DOMAINS["rwth"]),
    ):
        assert calls, "discovery sent no search query"
        assert {domains for _query, domains in calls} == {(domain,)}
        # What stage_summary counts as discovery_queries.
        assert len(trace["search_results"]) == len(calls)
        assert "search" in trace["stage_order"]

    # The two sets take the same path: the same families, in the same order.
    def families(trace: dict) -> list[str]:
        return [row["family"] for row in trace["search_results"]]

    assert families(dev5_trace) == families(dev4_trace)
    assert dev5_trace["stage_order"] == dev4_trace["stage_order"]
