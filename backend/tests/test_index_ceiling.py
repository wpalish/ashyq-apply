"""Free-search ticket 04: the own-index ceiling tool, offline (fixture sitemaps and pages)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.adapters.discovery import live_discovery
from app.adapters.fetching import Fetcher, FetchResult
from app.domain.enums import FetchOutcome
from evaluation.research import index_ceiling as ic
from tests.test_live_discovery import StubSite, sitemap_index_xml, sitemap_xml

ORIGIN = "https://www.uni.example.nl"
GOLD = f"{ORIGIN}/opleidingen/bachelor-informatica.htm"
DEEP = f"{ORIGIN}/onderwijs/deep-programme"
NEWS_ONLY = f"{ORIGIN}/nieuws/item-programme"
LINKED = f"{ORIGIN}/study/bsc-computing"
TWIN_SOURCE = f"{ORIGIN}/nl/opleiding-x"
TWIN = f"{ORIGIN}/en/programme-x"
REFUSED = f"{ORIGIN}/admissions/locked"
NOWHERE = f"{ORIGIN}/hidden/page"


def _html(title: str, *, lang: str = "nl", head: str = "", body: str = "") -> str:
    return (
        f'<html lang="{lang}"><head><title>{title}</title>{head}</head>'
        f"<body><h1>{title}</h1>{body}</body></html>"
    )


def _site() -> StubSite:
    children = [f"{ORIGIN}/sitemap-{n}.xml" for n in range(1, 15)]
    pages: dict[str, bytes | str] = {
        f"{ORIGIN}/robots.txt": f"User-agent: *\nDisallow:\nSitemap: {ORIGIN}/sitemap.xml\n",
        f"{ORIGIN}/sitemap.xml": sitemap_index_xml(f"{ORIGIN}/sitemap-news.xml", *children),
        # Trimmed by SM-2 (a news sitemap): read only when unbounded.
        f"{ORIGIN}/sitemap-news.xml": sitemap_xml(NEWS_ONLY),
        # The first child holds the gold without its .htm extension, with a lastmod.
        f"{ORIGIN}/sitemap-1.xml": (
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            f"<url><loc>{GOLD.removesuffix('.htm')}</loc><lastmod>2026-10-01</lastmod></url>"
            f"<url><loc>{TWIN}</loc></url></urlset>"
        ),
        # The 14th child: past the product's 12-document cap.
        f"{ORIGIN}/sitemap-14.xml": sitemap_xml(DEEP),
        f"{ORIGIN}/": _html(
            "Universiteit",
            body=(
                '<a href="/study">Study</a><a href="/news/today">News</a>'
                f'<a href="{REFUSED}">Apply</a>'
            ),
        ),
        f"{ORIGIN}/study": _html("Study", lang="en", body=f'<a href="{LINKED}">BSc Computing</a>'),
        GOLD: _html("Bachelor in de informatica"),
        DEEP: _html("Deep"),
        NEWS_ONLY: _html("News item"),
        LINKED: _html("BSc Computing", lang="en"),
        TWIN_SOURCE: _html(
            "Opleiding X",
            head=(
                f'<link rel="alternate" hreflang="en" href="{TWIN}">'
                f'<link rel="alternate" hreflang="x-default" href="{ORIGIN}/">'
            ),
        ),
        NOWHERE: _html("Hidden"),
    }
    for child in children:
        pages.setdefault(child, sitemap_xml(f"{child.removesuffix('.xml')}/page"))
    site = StubSite(pages)
    original = site.install

    def install(fetcher: Fetcher) -> Fetcher:
        original(fetcher)
        stub = fetcher.get

        async def get(url: str, **kwargs: object) -> FetchResult:
            if url == REFUSED:
                site.requested.append(url)
                return FetchResult(
                    url=url, outcome=FetchOutcome.HTTP_ERROR, status_code=403, final_url=url
                )
            return await stub(url, **kwargs)  # type: ignore[arg-type]

        fetcher.get = get  # type: ignore[method-assign]
        return fetcher

    site.install = install  # type: ignore[method-assign]
    return site


SITE = ic.Site(key="uni", homepage=f"{ORIGIN}/", domain="uni.example.nl", country="Netherlands")


def _targets() -> list[ic.Target]:
    urls = [GOLD, DEEP, NEWS_ONLY, LINKED, TWIN_SOURCE, REFUSED, NOWHERE]
    return [ic.Target(url, "uni", "dev3", "uni", ("gold",)) for url in urls]


async def _measure(tmp_path: Path, **kwargs: object) -> tuple[dict, StubSite]:
    site = _site()
    async with Fetcher(tmp_path / "c", offline=True) as fetcher:
        site.install(fetcher)
        records = await ic.measure(fetcher, {"uni": SITE}, _targets(), **kwargs)  # type: ignore[arg-type]
    return records[0], site


def _row(record: dict, url: str) -> dict:
    return next(row for row in record["rows"] if row["url"] == url)


async def test_bounded_reader_misses_what_the_cap_and_the_trim_leave_out(tmp_path) -> None:
    record, _ = await _measure(tmp_path)
    gold, deep, news = _row(record, GOLD), _row(record, DEEP), _row(record, NEWS_ONLY)
    # .htm stripped (metrics._page_forms) and the first child read under the bounds.
    assert gold["in_sitemap_bounded"] and gold["in_sitemap_any"]
    assert gold["document_read_bounded"] and gold["lastmod"] is True
    # The 14th child: listed, but past MAX_SITEMAP_DOCUMENTS.
    assert deep["in_sitemap_any"] and not deep["in_sitemap_bounded"]
    assert deep["document_ordinal"] > live_discovery.MAX_SITEMAP_DOCUMENTS
    assert not deep["document_read_bounded"]
    # A news sitemap: SM-2 never reads it; unbounded does.
    assert news["in_sitemap_any"] and not news["in_sitemap_bounded"]
    assert news["document_trimmed"]
    assert record["bounded_documents_read"] == live_discovery.MAX_SITEMAP_DOCUMENTS
    assert record["unbounded_documents"] == 16


async def test_two_hops_follow_study_links_only(tmp_path) -> None:
    record, site = await _measure(tmp_path)
    assert _row(record, LINKED)["linked_hop"] == 2
    assert _row(record, REFUSED)["linked_hop"] == 1
    assert _row(record, NOWHERE)["linked_hop"] is None
    assert f"{ORIGIN}/news/today" not in site.requested


async def test_crawl_budget_counts_the_homepage(tmp_path) -> None:
    site = _site()
    async with Fetcher(tmp_path / "c", offline=True) as fetcher:
        site.install(fetcher)
        crawl = await ic.crawl_two_hops(fetcher, SITE, budget=1)
    assert crawl.pages_read == 1
    assert f"{ORIGIN}/study" not in site.requested


async def test_twin_and_refusal_are_recorded(tmp_path) -> None:
    record, _ = await _measure(tmp_path)
    twin = _row(record, TWIN_SOURCE)
    assert twin["twins"] == [TWIN]  # x-default is not a twin
    assert twin["twin_declared"] and not twin["in_sitemap_any"]
    refused = _row(record, REFUSED)
    assert refused["host_refused"] == "http 403"
    assert refused["read_outcome"] == "http_error 403"


async def test_title_names_the_localized_alias(tmp_path) -> None:
    record, _ = await _measure(tmp_path)
    gold = _row(record, GOLD)
    assert gold["html_lang"] == "nl"
    assert gold["title_alias"] == {"language": "nl", "alias": "informatica", "match": True}
    assert _row(record, DEEP)["title_alias"]["match"] is False


def test_alias_match_is_whole_word_and_folds_accents() -> None:
    assert ic.names_alias("Grau en Enginyeria Informàtica", "informàtica")
    assert ic.names_alias("Grado en INFORMATICA", "informàtica")
    assert not ic.names_alias("Bioinformatica", "informatica")
    assert ic.names_alias("计算机科学与技术专业", "计算机科学与技术")
    # An English page in a non-English country is tested in the country's languages.
    assert ic.alias_match("Informatik B.Sc.", "", "en", "Germany")["match"]


async def test_tables_count_cases_and_questions(tmp_path) -> None:
    record, _ = await _measure(tmp_path)
    sets = ic.per_set([record])
    # One case: any of its gold pages meeting a column counts the case once.
    assert sets["dev3"]["cases_with_gold"] == 1
    assert sets["dev3"]["ceiling"] == 1 and sets["dev3"]["host_refused"] == 1
    kb_record = {
        **record,
        "rows": [
            {**_row(record, GOLD), "group": "kb", "kinds": ["programme", "english"]},
            {**_row(record, NOWHERE), "group": "kb", "kinds": ["deadline"]},
        ],
    }
    questions = ic.per_question([kb_record])
    assert questions["all"]["urls"] == 2 and questions["all"]["in_sitemap_bounded"] == 1
    assert questions["deadline"]["ceiling"] == 0
    markdown = ic.markdown([record])
    assert NOWHERE in markdown and "| dev3 | 1 |" in markdown


def test_dev_loader_refuses_a_heldout_case(tmp_path) -> None:
    corpus = {"cases": [{"id": "tum", "domain": "tum.de", "country": "Germany"}]}
    path = tmp_path / "x.json"
    path.write_text(json.dumps(corpus), encoding="utf-8")
    with pytest.raises(ValueError, match="heldout"):
        ic.load_dev_targets(["dev4"], {"dev4": path})


def test_dev_loader_reads_gold_and_falls_back_to_related(tmp_path) -> None:
    corpus = {
        "cases": [
            {"id": "a", "domain": "a.example", "programme_urls": ["https://www.a.example/p"]},
            {
                "id": "b",
                "domain": "taltech.ee",
                "programme_urls": [],
                "related_programme_urls": ["https://taltech.ee/r"],
            },
        ]
    }
    path = tmp_path / "x.json"
    path.write_text(json.dumps(corpus), encoding="utf-8")
    sites, targets = ic.load_dev_targets(["dev4"], {"dev4": path})
    assert sites["a"].homepage == "https://www.a.example/"
    assert sites["b"].homepage == "https://taltech.ee/"
    assert [(t.case, t.kinds) for t in targets] == [("a", ("gold",)), ("b", ("related",))]


def test_kb_loader_groups_urls_by_question_and_keeps_dev5_blind(tmp_path) -> None:
    fact = {"source_url": "https://www.lmu.de/fees"}
    kb = {
        "entries": {
            "qs-1": {
                "official_domain": "lmu.de",
                "country": "Germany",
                "programme": {"urls": ["https://www.lmu.de/p"], "evidence": []},
                "facts": {"tuition": [fact], "scholarship_exists": [fact]},
                "not_applicable": [{"question": "gpa", "source_url": "https://www.lmu.de/g"}],
            },
            "qs-2": {"official_domain": "tum.de", "programme": {"urls": ["https://tum.de/x"]}},
        }
    }
    path = tmp_path / "kb.json"
    path.write_text(json.dumps(kb), encoding="utf-8")
    sites, targets = ic.load_kb_targets([path, path], seed_path=tmp_path / "missing.json")
    assert set(sites) == {"qs-1"} and sites["qs-1"].blind
    kinds = {t.url: t.kinds for t in targets}
    assert kinds == {
        "https://www.lmu.de/fees": ("tuition", "scholarship"),
        "https://www.lmu.de/g": ("gpa",),
        "https://www.lmu.de/p": ("programme",),
    }
    record = {"site": "qs-1", "blind": True, "homepage": "h", "rows": [{"url": "x"}]}
    assert ic.written([record]) == [{"site": "blind", "blind": True, "homepage": "", "rows": []}]


def test_refused_sites_reads_an_earlier_report() -> None:
    report: list[dict[str, Any]] = [
        {"site": "a", "homepage_refusal": "http 403", "rows": []},
        {"site": "b", "homepage_refusal": "", "rows": [{"host_refused": "robots"}]},
        {"site": "c", "homepage_refusal": "", "rows": [{"host_refused": ""}]},
        {"site": "blind", "homepage_refusal": "timeout", "rows": []},
    ]
    assert ic.refused_sites(report) == {"a", "b"}


def test_safe_links_drops_only_the_anchors_links_from_cannot_parse() -> None:
    html = (
        '<a href="https://eaulas.usp.br​/x">bad host</a>'
        '<a href="http://www.uni.example.nl: +49 241 80-95777">phone as port</a>'
        f'<a href="{LINKED}">BSc Computing</a>'
    )
    assert [link.url for link in ic.safe_links(html, f"{ORIGIN}/")] == [LINKED]
    assert ic.page_keys("http://x.example: +49 241") == (set(), set())


async def test_a_kb_seed_id_is_not_the_intent_institution(tmp_path) -> None:
    site = _site()
    seeded = ic.Site(key="qs2027-001", homepage=f"{ORIGIN}/", domain="uni.example.nl", country="")
    async with Fetcher(tmp_path / "c", offline=True) as fetcher:
        site.install(fetcher)
        crawl = await ic.crawl_two_hops(fetcher, seeded)
    assert crawl.hops[LINKED] == 2


async def test_a_read_that_raises_is_recorded_not_fatal(tmp_path) -> None:
    async with Fetcher(tmp_path / "c", offline=True) as fetcher:

        async def boom(url: str, **kwargs: object) -> FetchResult:
            raise ValueError("Invalid IDNA hostname")

        fetcher.get = boom  # type: ignore[method-assign]
        records = await ic.measure(fetcher, {"uni": SITE}, _targets()[:1])
    row = records[0]["rows"][0]
    assert row["read_outcome"] == "unparseable"
    assert not row["in_sitemap_any"] and row["linked_hop"] is None
