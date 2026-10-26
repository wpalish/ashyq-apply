"""v3-M5 query-shape probe: offline, with a fake provider (no network, no key)."""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from app.adapters.search.base import SearchResponse, SearchResult, SearchUnavailable
from app.adapters.search.intent import QueryPrivacyError
from app.adapters.search.ontology import load_ontology
from app.adapters.search.serper import SerperSearchProvider
from evaluation.research.schema import Case
from scripts import probe_query_shapes as probe

BACKEND = Path(__file__).resolve().parents[1]
DATASETS = tuple(BACKEND / p for p in probe.DEFAULT_DATASETS)
NOW = datetime(2026, 10, 18, tzinfo=UTC)


def cases(ids: Sequence[str] = probe.DEFAULT_CASES) -> list[Case]:
    return probe.load_cases(DATASETS, ids)


class FakeProvider:
    """Answers from a table of query text -> URLs; records every call."""

    name = "serper"

    def __init__(self, answers: dict[tuple[str, str], list[str]] | None = None) -> None:
        self.answers = answers or {}
        self.calls: list[tuple[str, str]] = []

    def _response(self, query: str, locale: str) -> SearchResponse:
        self.calls.append((query, locale))
        urls = self.answers.get((query, locale), [f"https://example.org/{i}" for i in range(12)])
        return SearchResponse(
            query=query,
            provider=self.name,
            retrieved_at=NOW,
            results=tuple(
                SearchResult(url=u, title=f"t{i}", provider=self.name, rank=i, retrieved_at=NOW)
                for i, u in enumerate(urls, start=1)
            ),
        )

    async def search(
        self, *, query: str, domains: Sequence[str] = (), max_results: int = 10
    ) -> SearchResponse:
        assert not domains
        return self._response(query, "")

    async def search_localized(
        self,
        *,
        query: str,
        hl: str,
        gl: str,
        domains: Sequence[str] = (),
        max_results: int = 10,
    ) -> SearchResponse:
        return self._response(query, f"{hl}/{gl}")


def test_default_plan_is_five_shapes_times_six_cases_and_each_alias_is_the_ontologys():
    plan = probe.build_plan(cases())
    assert len(plan) == 30
    by_case: dict[str, list[str]] = {}
    for q in plan:
        by_case.setdefault(q.case_id, []).append(q.shape)
    assert set(by_case) == set(probe.DEFAULT_CASES)
    assert all(shapes == list(probe.SHAPES) for shapes in by_case.values())
    texts = {(q.case_id, q.shape): q for q in plan}
    assert texts["uio", "a_today"].text == 'site:uio.no "computer science" "bachelor"'
    assert texts["uio", "c_local"].text == "site:uio.no informatikk bachelor"
    assert texts["puc", "c_local"].text == 'site:uc.cl "ciencia de la computación" licenciatura'
    assert (texts["uio", "d_local_hl_gl"].hl, texts["uio", "d_local_hl_gl"].gl) == ("no", "no")
    assert texts["uio", "d_local_hl_gl"].text == texts["uio", "c_local"].text
    assert "site:" not in texts["uio", "e_local_natural"].text
    assert texts["uba", "b_alias_or"].text.startswith('site:uba.ar ("computer science" OR')


def test_every_local_terms_entry_uses_an_ontology_alias():
    for case in cases([*probe.DEFAULT_CASES, "ucph", "chula"]):
        probe.check_local_terms(case, probe.LOCAL_TERMS[case.id])


def test_no_applicant_words_reach_a_query():
    """Every token is institution data, the request's public words or the ontology."""
    ontology = load_ontology().fields["computer_science"]
    allowed: set[str] = {"site", "or", "bachelor"}
    words = re.compile(r"[\w.-]+", re.UNICODE)
    for alias in ontology["strong_aliases"]:
        allowed |= set(words.findall(alias.casefold()))
    for case in cases():
        terms = probe.LOCAL_TERMS[case.id]
        for text in (
            case.domain,
            case.university,
            case.request.field or "",
            terms.alias,
            terms.degree_word,
            terms.local_name,
        ):
            allowed |= set(words.findall(text.casefold()))
    for q in probe.build_plan(cases()):
        tokens = set(words.findall(q.text.casefold().replace("site:", "site ")))
        assert tokens <= allowed, (q.case_id, q.shape, tokens - allowed)
        assert not re.search(r"\d{3,}|@|\d\.\d", q.text)


def test_a_case_carrying_applicant_data_is_refused_before_anything_is_sent():
    case = cases(["uio"])[0]
    leaky = case.model_copy(update={"university": "University of Oslo jane@example.com"})
    with pytest.raises(QueryPrivacyError):
        probe.plan_case(leaky, probe.LOCAL_TERMS["uio"])
    gpa = probe.LocalTerms("no", "no", "no", "informatikk", "bachelor 3.9", "Universitetet i Oslo")
    with pytest.raises(QueryPrivacyError):
        probe.plan_case(case, gpa)


def test_heldout_ids_and_heldout_files_are_refused_unread(tmp_path: Path):
    with pytest.raises(ValueError, match="Held-out"):
        probe.load_cases(DATASETS, ["uio", "tum"])
    # The file does not exist: refusing by name means it is never opened.
    with pytest.raises(ValueError, match="held-out file"):
        probe.load_cases([tmp_path / "heldout.draft1.json"], ["uio"])


def test_a_case_without_gold_cannot_be_probed():
    probe.LOCAL_TERMS.setdefault("tec", probe.LOCAL_TERMS["uba"])
    try:
        with pytest.raises(ValueError, match="No gold"):
            probe.load_cases(DATASETS, ["tec"])
    finally:
        del probe.LOCAL_TERMS["tec"]


async def test_the_plan_is_refused_whole_over_300_and_nothing_is_sent(monkeypatch):
    many = cases() * 11  # 6 * 11 * 5 = 330
    provider = FakeProvider()
    with pytest.raises(probe.ProbeBudgetExceeded):
        await probe.run_probe(many, provider)
    assert provider.calls == []
    with pytest.raises(probe.ProbeBudgetExceeded):
        probe.build_plan(cases(), limit=301)
    with pytest.raises(SystemExit):
        probe.main(["--out", "unused", "--max-queries", "301"])


async def test_exactly_300_is_allowed_and_the_sender_refuses_the_301st(monkeypatch):
    sixty = cases() * 10  # 300 queries
    provider = FakeProvider()
    data = await probe.run_probe(sixty, provider)
    assert data["requests_sent"] == 300 == len(provider.calls)

    # A wrong plan cannot spend past the ceiling: the sender counts on its own.
    sender = probe._Sender(provider, 2)
    plan = probe.build_plan(cases(["uio"]))
    await sender.send(plan[0])
    await sender.send(plan[1])
    with pytest.raises(probe.ProbeBudgetExceeded):
        await sender.send(plan[2])
    assert sender.sent == 2


def test_scoring_counts_canonical_variants_and_gold_twins_only_in_the_top_10():
    ucph = cases(["ucph"])[0]  # gold: datalogi and its English twin
    english_twin = "https://www.ku.dk/studies/bachelor/computer-science/"  # trailing slash
    rank, url, matched, _ = probe.score_results(ucph, ["https://www.ku.dk/x", english_twin])
    assert (rank, matched) == (2, "https://www.ku.dk/studies/bachelor/computer-science")
    assert url == english_twin
    uio = cases(["uio"])[0]
    variant = "https://www.uio.no/studier/program/informatikk-programmering/index.html"
    assert probe.score_results(uio, [variant])[0] == 1
    year = "https://www.uio.no/studier/program/informatikk-programmering/2027/"
    assert probe.score_results(uio, [year])[0] == 1
    eleventh = [f"https://www.uio.no/{i}" for i in range(10)] + [variant]
    assert probe.score_results(uio, eleventh)[0] is None
    other = "https://www.uio.no/studier/program/informatikk-design/"
    assert probe.score_results(uio, [other])[0] is None


async def test_run_records_ranked_top_10_scores_and_decides_by_four_of_six(tmp_path: Path):
    six = cases()
    plan = probe.build_plan(six)
    answers: dict[tuple[str, str], list[str]] = {}
    gold = {case.id: str(case.programme_urls[0]) for case in six}
    # c_local finds the gold on four cases at rank 3; e_local_natural on three.
    for q in plan:
        locale = f"{q.hl}/{q.gl}" if q.hl else ""
        urls = [f"https://noise.example/{q.case_id}/{i}" for i in range(15)]
        if q.shape == "c_local" and q.case_id in {"uba", "puc", "uio", "kuleuven"}:
            urls[2] = gold[q.case_id]
        if q.shape == "e_local_natural" and q.case_id in {"uba", "puc", "uio"}:
            urls[0] = gold[q.case_id]
        answers[q.text, locale] = urls
    provider = FakeProvider(answers)
    data = await probe.run_probe(six, provider)

    assert data["requests_sent"] == 30
    rows = {(r["case_id"], r["shape"]): r for r in data["results"]}
    row = rows["uio", "c_local"]
    assert [t["rank"] for t in row["top"]] == list(range(1, 11))
    assert row["gold_rank"] == 3
    assert rows["uio", "d_local_hl_gl"]["gold_rank"] is None  # different locale key
    assert ("site:uio.no informatikk bachelor", "no/no") in provider.calls
    assert data["shapes"]["c_local"]["hits"] == 4
    assert data["shapes"]["c_local"]["joins_first_pass"] is True
    assert data["shapes"]["e_local_natural"]["joins_first_pass"] is False
    assert data["decision"]["shapes_joining_first_pass"] == ["c_local"]
    assert data["decision"]["r5_exists"] is True
    assert data["decision"]["complete"] is True
    table = probe.markdown(data)
    assert "| uio | — | — | 3 | — | 1 |" in table
    assert "**4** ✓" in table


async def test_errors_are_recorded_without_provider_text_and_block_the_decision():
    class Failing(FakeProvider):
        async def search(self, *, query, domains=(), max_results=10):
            raise SearchUnavailable("secret-key-abc echoed body", http_status=403)

    data = await probe.run_probe(cases(), Failing())
    errors = [r for r in data["results"] if r["status"] == "error"]
    assert len(errors) == 24  # every shape but d
    assert all("secret" not in r["error"] for r in errors)
    assert errors[0]["error"] == "Search service unavailable (serper; HTTP 403)."
    assert data["decision"]["complete"] is False
    assert data["shapes"]["c_local"]["joins_first_pass"] is False


async def test_a_provider_without_hl_gl_skips_shape_d_without_sending():
    class Plain:
        name = "serper"
        calls = 0

        async def search(self, *, query, domains=(), max_results=10):
            Plain.calls += 1
            return SearchResponse(query=query, provider="serper", retrieved_at=NOW)

    data = await probe.run_probe(cases(), Plain())
    assert Plain.calls == 24 == data["requests_sent"]
    assert {r["status"] for r in data["results"] if r["shape"] == "d_local_hl_gl"} == {
        "unsupported"
    }


def test_dry_run_writes_json_and_markdown_and_sends_nothing(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(BACKEND)
    assert probe.main(["--out", str(tmp_path)]) == 0
    data = json.loads((tmp_path / "probe.json").read_text(encoding="utf-8"))
    assert data["live"] is False and data["requests_sent"] == 0
    assert data["queries_planned"] == 30
    assert "dry run" in (tmp_path / "probe.md").read_text(encoding="utf-8")


async def test_serper_sends_hl_and_gl_only_on_the_localized_call():
    bodies: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json={"organic": [{"link": "https://uio.no/a", "title": "a"}]})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    serper = SerperSearchProvider("test-key-not-a-real-one", client=client)
    await serper.search(query="site:uio.no informatikk bachelor")
    response = await serper.search_localized(
        query="site:uio.no informatikk bachelor", hl="zh-cn", gl="cn"
    )
    assert bodies[0] == {"q": "site:uio.no informatikk bachelor", "num": 10}
    assert bodies[1] == {
        "q": "site:uio.no informatikk bachelor",
        "num": 10,
        "hl": "zh-cn",
        "gl": "cn",
    }
    assert response.results[0].url == "https://uio.no/a"
    with pytest.raises(ValueError, match="locale code"):
        await serper.search_localized(query="q", hl="Norwegian please", gl="no")
