"""WF-17: the trace keeps the provider's result lists, the reads and the twins.

Measurement only (wayfinder programme-discovery ticket 17). Discovery's rules
do not change; the trace records per query family what the provider returned
(public URLs, no query text), every page read with its verdict, and the
``hreflang`` twins each read page declares. The harness copies the twins of
the returned programme pages into the observation, the scorer counts a twin
of the gold page as a hit, and the scorecard says how far the gold page got.
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from app.adapters.discovery.live_discovery import (
    DiscoveryTrace,
    LiveDiscoveryAdapter,
    PageCategory,
    declared_alternates,
)
from app.adapters.search.fake import FakeSearchProvider
from app.adapters.search.intent import DiscoveryIntent, queries_for
from app.adapters.search.retrieval import discover_candidates
from app.config import get_settings
from app.domain.enums import DegreeLevel
from evaluation.research import live, scorecard
from evaluation.research.metrics import score
from evaluation.research.schema import Capture, Dataset, Observation
from scripts import canary_discovery as canary
from tests.test_discovery_query_reserve import (
    EVENT_PAGE,
    PAGES,
    PROGRAMME,
    Fetcher,
    Provider,
    planned_queries,
    reserve,  # noqa: F401 - fixture
    search,
)

NOW = datetime(2026, 10, 18, tzinfo=UTC)
LOCAL = "https://studier.uni.dk/bachelor/datalogi"
TWIN = "https://studier.uni.dk/en/bachelor/computer-science"


def _alternates_html(*links: tuple[str, str], lang: str = "da") -> str:
    tags = "".join(f'<link rel="alternate" hreflang="{h}" href="{u}">' for h, u in links)
    return f'<html lang="{lang}"><head>{tags}<title>Datalogi</title></head><body></body></html>'


# --- 1. provider result lists ----------------------------------------------


async def test_retrieval_reports_each_familys_results_in_rank_order_without_query_text() -> None:
    intent = DiscoveryIntent(
        institution="Example University",
        domain="uni.edu",
        degree=DegreeLevel.BACHELOR,
        field="computer science",
    )
    queries = queries_for(intent)
    rows = [
        "https://uni.edu/b#top",
        "https://user:secret@uni.edu/a?p7_code=CS",
        "https://uni.edu/c",
    ]
    provider = FakeSearchProvider({q.text: rows for q in queries}, now=NOW)

    report = await discover_candidates(provider, intent)

    assert [family for family, _ in report.results_by_family] == [q.family for q in queries]
    for _family, urls in report.results_by_family:
        # Rank order kept; fragment and credentials dropped; the query stays.
        assert urls == ("https://uni.edu/b", "https://uni.edu/a?p7_code=CS", "https://uni.edu/c")
    recorded = json.dumps(report.results_by_family)
    for query in queries:
        assert query.text not in recorded
    assert "site:" not in recorded
    assert "secret" not in recorded


async def test_discovery_traces_what_each_query_family_returned(reserve) -> None:  # noqa: F811
    provider = Provider(lambda n: [EVENT_PAGE] if n <= 3 else [EVENT_PAGE, PROGRAMME])
    selected, trace = await search(provider, Fetcher(PAGES))

    assert selected[PageCategory.PROGRAM_PAGE] == [PROGRAMME]
    rows = trace.as_dict()["search_results"]
    assert len(rows) == 6  # both QB-1 passes, one row per query sent
    assert [row["urls"] for row in rows] == [[EVENT_PAGE]] * 3 + [[EVENT_PAGE, PROGRAMME]] * 3
    assert all(set(row) == {"family", "urls"} for row in rows)
    # Redaction: the recorded lists carry the provider's URLs and nothing of
    # the queries (which name the field and level) or of the applicant.
    recorded = json.dumps(rows)
    for query in planned_queries():
        assert query not in recorded
    assert "site:" not in recorded
    assert "KZ" not in recorded
    # Every page read for identity, with its verdict ("" = accepted).
    verdicts = dict(trace.as_dict()["pages_read"])
    assert verdicts[PROGRAMME] == ""
    assert verdicts[EVENT_PAGE]


def test_an_empty_trace_serialises_as_before() -> None:
    shown = DiscoveryTrace(institution="x", domain="x.edu").as_dict()
    assert not {"search_results", "pages_read", "programme_url_aliases"} & set(shown)


def test_the_result_trace_is_bounded() -> None:
    trace = DiscoveryTrace(institution="x", domain="x.edu")
    trace.record_search_results([("f", [f"https://x.edu/{i}" for i in range(30)])] * 40)
    assert len(trace.search_results) == 24
    assert all(len(row["urls"]) == 10 for row in trace.search_results)  # type: ignore[arg-type]


# --- 3. declared twins --------------------------------------------------------


def test_declared_alternates_are_every_language_twin_on_the_same_site() -> None:
    html = _alternates_html(
        ("en-GB", "/en/bachelor/computer-science"),
        ("da", LOCAL),
        ("x-default", "https://studier.uni.dk/choose"),
        ("de", "https://other.de/informatik"),
    )
    assert declared_alternates(LOCAL, html, "uni.dk") == [TWIN]
    # Direction does not matter: an English page's local twin is recorded too.
    english = _alternates_html(("da-DK", LOCAL), lang="en")
    assert declared_alternates(TWIN, english, "uni.dk") == [LOCAL]


async def test_the_walker_records_the_twins_of_a_page_it_confirms() -> None:
    from app.adapters.discovery.catalog_walker import CatalogWalk, CatalogWalker, WalkerLink
    from tests.test_live_discovery import program_html

    english = "https://www.uni.dk/en/bachelor/computer-science"
    local = "https://www.uni.dk/bachelor/datalogi"
    page = program_html().replace(
        "<head>", f'<head><link rel="alternate" hreflang="da" href="{local}">', 1
    )
    walker = CatalogWalker(
        fetcher=Fetcher({english: page}),  # type: ignore[arg-type]
        domain="www.uni.dk",
        degree="bachelor",
        fields=["Computer Science"],
    )
    walk = CatalogWalk(catalogue_url="https://www.uni.dk/en/bachelor")
    await walker._read_lead(WalkerLink(english, "BSc Computer Science", 10, "html"), walk)

    assert walk.confirmed == [english]
    assert walk.alternates == {english: [local]}


def test_a_read_records_its_twins_in_both_directions() -> None:
    trace = DiscoveryTrace(institution="x", domain="uni.dk")
    trace.note_read(LOCAL, LOCAL, _alternates_html(("en", TWIN)), None)
    assert trace.programme_url_aliases == {LOCAL: [TWIN], TWIN: [LOCAL]}
    assert trace.pages_read == [(LOCAL, "")]


# --- 2. the harness: aliases at the checkpoint and at the end -------------------


def test_programme_aliases_match_on_the_canonical_url() -> None:
    trace = {"programme_url_aliases": {LOCAL + "/": [TWIN]}}
    assert live.programme_aliases([LOCAL], trace) == {LOCAL: [TWIN]}
    assert live.programme_aliases(["https://studier.uni.dk/other"], trace) == {}


@pytest.fixture
def _offline(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setenv("UNIMATCH_SEARCH_PROVIDER", "none")
    monkeypatch.setenv("UNIMATCH_DECISION_PROVIDER", "none")
    monkeypatch.setenv("UNIMATCH_ENABLE_BROWSER_TIER", "false")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


async def test_a_kill_after_confirm_keeps_the_twins_and_the_result_lists(
    _offline: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "ucph.json"

    async def confirm(adapter: Any, selected: Any, ranked: Any, trace: Any, profile: Any) -> None:
        trace.record_search_results([("programme_page", [LOCAL])])
        trace.note_read(LOCAL, LOCAL, _alternates_html(("en", TWIN)), None)
        selected[PageCategory.PROGRAM_PAGE] = [LOCAL]

    monkeypatch.setattr(LiveDiscoveryAdapter, "_confirm_programs", confirm)

    async def run(*args: Any, **kwargs: Any) -> dict[str, Any]:
        trace = DiscoveryTrace(institution="University of Copenhagen", domain="uni.dk")
        selected: dict[str, list[str]] = {c: [] for c in PageCategory.ALL}
        ranked: dict[str, list[tuple[int, str]]] = {PageCategory.PROGRAM_PAGE: []}
        await LiveDiscoveryAdapter._confirm_programs(None, selected, ranked, trace, None)  # type: ignore[arg-type]
        await asyncio.sleep(5)
        return {}

    monkeypatch.setattr(canary, "run_canary", run)
    await live.capture_one("ubc", output, 5, 0.3)

    observation = Observation.model_validate_json(output.read_text())
    assert observation.error == "BENCHMARK_WALL_CLOCK_BUDGET_EXHAUSTED"
    assert observation.programme_url_aliases == {LOCAL: [TWIN]}
    partial = json.loads(output.with_suffix(".trace.json").read_text())["discovery_trace"]
    assert partial["search_results"] == [{"family": "programme_page", "urls": [LOCAL]}]
    assert partial["programme_url_aliases"] == {LOCAL: [TWIN], TWIN: [LOCAL]}


# --- the scorer: a twin of the gold page is a hit ------------------------------

SCOPE = {"university": "Example University"}


def _dataset(gold: str = LOCAL) -> Dataset:
    evidence = {
        "url": gold,
        "excerpt": "Datalogi",
        "scope": SCOPE,
        "accessed_on": "2026-10-18",
        "source_type": "official",
    }
    return Dataset.model_validate(
        {
            "version": "test",
            "split": "development",
            "cases": [
                {
                    "id": "uni",
                    "dataset_version": "test",
                    "university": "Example University",
                    "domain": "uni.dk",
                    "country": "Denmark",
                    "site_types": ["static"],
                    "request": SCOPE,
                    "programme_urls": [gold],
                    "programme_status": "known",
                    "programme_evidence": [evidence],
                    "labels": [],
                    "review": {
                        "status": "human_verified",
                        "prepared_by": "test",
                        "reviewer": "test",
                        "verified_on": "2026-10-18",
                        "notes": "test",
                    },
                }
            ],
        }
    )


def _capture(aliases: dict[str, list[str]] | None = None, urls: list[str] | None = None) -> dict:
    return {
        "pipeline_sha": "abc",
        "captured_at": "20261018T000000Z",
        "mode": "live",
        "config": {},
        "observations": [
            {
                "case_id": "uni",
                "programme_urls": urls if urls is not None else [TWIN],
                **({"programme_url_aliases": aliases} if aliases is not None else {}),
            }
        ],
    }


def test_a_returned_twin_of_the_gold_page_is_a_hit() -> None:
    plain = score(_dataset(), Capture.model_validate(_capture()))["metrics"]
    assert plain["programme_page_recall"]["numerator"] == 0
    assert plain["programme_page_precision"]["numerator"] == 0

    twinned = score(_dataset(), Capture.model_validate(_capture({TWIN: [LOCAL]})))["metrics"]
    assert twinned["programme_page_recall"]["numerator"] == 1
    assert twinned["programme_page_precision"]["numerator"] == 1
    assert twinned["programme_page_precision"]["denominator"] == 1


def test_a_twin_of_another_returned_page_does_not_lend_its_hit() -> None:
    other = "https://studier.uni.dk/bachelor/fysik"
    capture = _capture({TWIN: [LOCAL]}, urls=[TWIN, other])
    metrics = score(_dataset(), Capture.model_validate(capture))["metrics"]
    assert metrics["programme_page_precision"]["numerator"] == 1
    assert metrics["programme_page_precision"]["denominator"] == 2


# --- 4. the scorecard: gold seen at stage -----------------------------------------


def _seen(trace: dict[str, Any] | None, urls: list[str] | None = None) -> dict[str, Any]:
    case = _dataset().cases[0]
    observation = Observation(case_id="uni", programme_urls=urls or [])  # type: ignore[arg-type]
    return scorecard.gold_seen(case, observation, trace)


def test_gold_seen_splits_never_seen_by_how_far_the_gold_got() -> None:
    returned = {"search_results": [{"family": "programme_page", "urls": [LOCAL]}]}
    assert _seen(None)["stage"] == "never"
    assert _seen({"search_results": [{"family": "f", "urls": [TWIN]}]})["stage"] == "never"
    assert _seen(returned) == {
        "stage": "returned",
        "seen_as": ["returned:programme_page"],
        "reasons": [],
    }
    linked = {"walker": {"candidates": [{"url": LOCAL}], "outcomes": []}}
    assert _seen(linked)["stage"] == "listed"
    assert _seen({"kept_by_link_text": [[LOCAL, "Datalogi"]]})["stage"] == "listed"
    assert _seen({"pages_read": [[LOCAL, ""]]})["stage"] == "read"
    refused = _seen({**returned, "pages_read": [[LOCAL, "page names another subject"]]})
    assert refused["stage"] == "rejected"
    assert refused["reasons"] == ["page names another subject"]
    assert refused["seen_as"] == ["read", "returned:programme_page"]
    dropped = _seen({"rejected_sample": [[LOCAL, "sitemap: no programme word"]]})
    assert dropped["stage"] == "rejected"
    assert _seen(None, [LOCAL])["stage"] == "confirmed"


def test_a_twin_of_the_gold_counts_as_the_gold_in_the_trace() -> None:
    trace = {
        "programme_url_aliases": {LOCAL: [TWIN], TWIN: [LOCAL]},
        "pages_read": [[TWIN, "page does not state the requested degree level"]],
    }
    assert _seen(trace)["stage"] == "rejected"


def test_the_scorecard_reads_the_raw_trace_or_the_checkpoint_copy(tmp_path: Path) -> None:
    for arm, stamp in (("off", "20261018T000001Z"), ("on", "20261018T000001Z")):
        target = tmp_path / f"uni-{arm}" / stamp
        target.mkdir(parents=True)
        (target / "capture.json").write_text(json.dumps(_capture(urls=[])))
    raw = {"canary": {"institutions": [{"discovery_trace": {"pages_read": [[LOCAL, ""]]}}]}}
    (tmp_path / "uni-off/20261018T000001Z/uni.raw.json").write_text(json.dumps(raw))
    partial = {"partial": True, "discovery_trace": {"kept_by_link_text": [[LOCAL, "x"]]}}
    (tmp_path / "uni-on/20261018T000001Z/uni.trace.json").write_text(json.dumps(partial))

    card = scorecard.build(_dataset(), scorecard.load_run(tmp_path))
    assert card["arms"]["off"]["repetitions"][0]["gold_seen"]["uni"]["stage"] == "read"
    assert card["arms"]["on"]["repetitions"][0]["gold_seen"]["uni"]["stage"] == "listed"
    text = scorecard.render(card)
    assert " gold seen |" in text
    assert "| listed (link_text) |" in text


def test_a_run_without_traces_keeps_its_table_shape(tmp_path: Path) -> None:
    path = tmp_path / "capture.json"
    path.write_text(json.dumps(_capture()))
    card = scorecard.build(_dataset(), scorecard.load_run(path))
    assert "gold seen" not in scorecard.render(card)
