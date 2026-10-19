"""Wayfinder free-search 06 — Wikidata P856 domain proposals, offline.

Every request goes to an ``httpx.MockTransport``; the clock and the sleep are
fakes, so the politeness rules (one request a second, ``Retry-After``) are
pinned without waiting and without the network.
"""

from __future__ import annotations

import copy
from typing import Any, ClassVar
from urllib.parse import parse_qs

import httpx
import pytest

from evaluation.research.wikidata_domains import (
    HELDOUT_SEED_IDS,
    USER_AGENT,
    Candidate,
    PoliteClient,
    WikidataResponseTooLarge,
    WikidataUnavailable,
    _literal,
    build_report,
    judge,
    name_variants,
    search_texts,
)

E = "http://www.wikidata.org/entity/"


class FakeTime:
    def __init__(self) -> None:
        self.now = 1000.0
        self.slept: list[float] = []

    def clock(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


def sparql_json(rows: list[dict[str, str]]) -> dict[str, object]:
    return {"results": {"bindings": [{k: {"value": v} for k, v in r.items()} for r in rows]}}


def query_of(request: httpx.Request) -> str:
    return parse_qs(request.content.decode())["query"][0]


def polite(handler, fake: FakeTime) -> PoliteClient:
    http = httpx.Client(transport=httpx.MockTransport(handler))
    return PoliteClient(http, sleep=fake.sleep, clock=fake.clock)


class TestNameVariants:
    def test_a_trailing_place_and_the_parenthesis_are_reshapes_of_the_same_name(self):
        variants = name_variants(
            "Nanyang Technological University, Singapore (NTU Singapore)", ["Singapore"]
        )
        assert variants["Nanyang Technological University, Singapore (NTU Singapore)"] == 0
        assert variants["Nanyang Technological University"] == 1
        assert variants["NTU Singapore"] == 1
        assert "Singapore" not in variants

    def test_a_piece_of_a_split_name_may_name_another_body(self):
        variants = name_variants("Birkbeck, University of London", ["London"])
        assert variants["University of London"] == 2

    def test_an_inverted_name_is_turned_round(self):
        assert name_variants("Essex, University of")["University of Essex"] == 1

    def test_an_acronym_and_its_name_are_both_the_institution(self):
        variants = name_variants("KIT, Karlsruhe Institute of Technology")
        assert variants["Karlsruhe Institute of Technology"] == 1
        assert variants["KIT"] == 1

    def test_the_catalogue_transliteration_is_undone(self):
        variants = name_variants("Albert-Ludwigs-Universitaet Freiburg")
        assert variants["Albert-Ludwigs-Universität Freiburg"] == 0

    def test_a_shortened_search_comes_after_every_full_one_and_is_marked(self):
        texts = search_texts({"Goethe-University Frankfurt am Main": 0})
        assert texts[0] == ("Goethe-University Frankfurt am Main", False)
        assert texts[-1] == ("Goethe University Frankfurt", True)


def cand(qid: str, label: str, site: str = "", **kw: object) -> Candidate:
    c = Candidate(item=qid, label=label, country="", sites=[site] if site else [])
    for key, value in kw.items():
        setattr(c, key, value)
    return c


class TestJudge:
    variants: ClassVar[dict[str, int]] = {
        "University of Melbourne": 0,
        "The University of Melbourne": 0,
    }

    def test_one_labelled_item_in_the_country_with_one_site_is_high(self):
        c = cand(
            "Q1",
            "University of Melbourne",
            "https://www.unimelb.edu.au/",
            label_match=True,
            matched_names={"University of Melbourne"},
        )
        match = judge(self.variants, "Australia", [c], {"Q1": {"Australia"}}, "label")
        assert (match.item, match.domains, match.confidence) == ("Q1", ("unimelb.edu.au",), "high")
        assert "country Australia" in match.reason

    def test_an_item_in_another_country_is_no_match(self):
        c = cand("Q2", "University of Melbourne", "https://x.example", label_match=True)
        match = judge(self.variants, "Australia", [c], {"Q2": {"Canada"}}, "label")
        assert match.item is None and match.confidence == "none"
        assert "Canada" in match.reason

    def test_a_dissolved_item_is_ignored(self):
        c = cand("Q3", "University of Melbourne", "https://x.example", dissolved=True)
        match = judge(self.variants, "Australia", [c], {"Q3": {"Australia"}}, "label")
        assert match.confidence == "none"

    def test_an_equally_strong_rival_makes_it_low(self):
        a = cand("Q4", "University of Melbourne", "https://a.edu.au", label_match=True)
        b = cand("Q5", "University of Melbourne", "https://b.edu.au", label_match=True)
        a.matched_names = b.matched_names = {"University of Melbourne"}
        match = judge(
            self.variants, "Australia", [a, b], {"Q4": {"Australia"}, "Q5": {"Australia"}}, "label"
        )
        assert match.confidence == "low" and "rival" in match.reason

    def test_an_alias_match_is_medium_and_hong_kong_is_carried_by_china(self):
        c = cand("Q6", "University of Hong Kong", "https://www.hku.hk", matched_names={"HKU"})
        match = judge(
            {"HKU": 0}, "Hong Kong SAR, China", [c], {"Q6": {"People's Republic of China"}}, "label"
        )
        assert match.confidence == "medium" and "alias match" in match.reason

    def test_an_item_without_p856_proposes_nothing(self):
        c = cand("Q7", "University of Melbourne", label_match=True)
        match = judge(self.variants, "Australia", [c], {"Q7": {"Australia"}}, "label")
        assert match.domains == () and match.confidence == "none"


class TestPoliteClient:
    def test_it_names_the_project_and_waits_a_second_between_requests(self):
        fake = FakeTime()
        agents: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            agents.append(request.headers["User-Agent"])
            return httpx.Response(200, json=sparql_json([]))

        client = polite(handler, fake)
        client.sparql("SELECT 1")
        client.sparql("SELECT 2")
        assert agents == [USER_AGENT, USER_AGENT]
        assert "ashyq-apply" in USER_AGENT
        assert fake.slept == [1.0]

    def test_429_waits_the_servers_retry_after(self):
        fake = FakeTime()
        answers = iter(
            [
                httpx.Response(429, headers={"Retry-After": "7"}),
                httpx.Response(200, json=sparql_json([{"x": "1"}])),
            ]
        )
        client = polite(lambda _r: next(answers), fake)
        assert client.sparql("SELECT 1") == [{"x": "1"}]
        assert 7.0 in fake.slept and client.throttled == 1

    def test_it_gives_up_rather_than_hammering(self):
        fake = FakeTime()
        client = polite(lambda _r: httpx.Response(503), fake)
        with pytest.raises(WikidataUnavailable):
            client.sparql("SELECT 1")
        assert client.requests == 4

    def test_an_oversized_body_is_refused_not_parsed(self):
        fake = FakeTime()
        big = sparql_json([{"x": "y" * 4096}])
        client = polite(lambda _r: httpx.Response(200, json=big), fake)
        client.max_response_bytes = 1024
        with pytest.raises(WikidataResponseTooLarge):
            client.sparql("SELECT 1")

    def test_an_oversized_stream_without_a_length_is_cut_off(self):
        fake = FakeTime()
        chunks = [b'{"results": {"bindings": [', b" " * 600, b" " * 600, b"]}}"]
        client = polite(lambda _r: httpx.Response(200, content=iter(chunks)), fake)
        client.max_response_bytes = 1024
        with pytest.raises(WikidataResponseTooLarge, match="cap"):
            client.sparql("SELECT 1")
        # Under the cap, the same streamed body parses.
        client.max_response_bytes = 4096
        client = polite(lambda _r: httpx.Response(200, content=iter(chunks)), fake)
        assert client.sparql("SELECT 1") == []


class TestLiteral:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("Plain", '"Plain"'),
            ('Say "hi"', '"Say \\"hi\\""'),
            ("L'Aquila", '"L\\\'Aquila"'),
            ("back\\slash", '"back\\\\slash"'),
            ("two\nlines\r", '"two\\nlines\\r"'),
            ('\\"', '"\\\\\\""'),
        ],
    )
    def test_a_literal_cannot_leave_its_quotes_or_break_a_line(self, text, expected):
        literal = _literal(text)
        assert literal == expected
        assert "\n" not in literal and "\r" not in literal
        # Every quote inside the literal is escaped by an odd run of backslashes.
        inner = literal[1:-1]
        for index, char in enumerate(inner):
            if char in "\"'":
                run = len(inner[:index]) - len(inner[:index].rstrip("\\"))
                assert run % 2 == 1


SEED: list[dict[str, Any]] = [
    {"seed_id": "qs2027-009", "name": "UCL", "country": "United Kingdom", "official_domain": None},
    {"seed_id": "qs2027-025", "name": "Heldout Row", "country": "Germany", "official_domain": None},
    {"seed_id": "qs2027-900", "name": "Nowhere College", "country": "France"},
    {"seed_id": "qs2027-001", "name": "MIT", "country": "United Kingdom", "official_domain": "x.y"},
]
KB: list[dict[str, Any]] = [
    {
        "seed_id": "qs2027-002",
        "name": "Imperial College London",
        "country": "United Kingdom",
        "official_domain": "imperial.ac.uk",
    },
    {
        "seed_id": "qs2027-003",
        "name": "Stanford University",
        "country": "United States of America",
        "official_domain": "stanford.edu",
    },
    {"seed_id": "qs2027-025", "name": "Heldout Row", "status": "excluded_heldout"},
]

LABELS = {
    "UCL": ("Q193196", "University College London", "https://www.ucl.ac.uk", "United Kingdom"),
    "Imperial College London": (
        "Q189022",
        "Imperial College London",
        "https://www.imperial.ac.uk/",
        "United Kingdom",
    ),
    "Stanford University": (
        "Q41506",
        "Stanford University",
        "https://www.stanford-mirror.org/",
        "United States",
    ),
}


def wikidata(queries: list[str]):
    def handler(request: httpx.Request) -> httpx.Response:
        query = query_of(request)
        queries.append(query)
        rows = []
        if "VALUES ?name" in query:
            for name, (qid, label, site, country) in LABELS.items():
                if f'"{name}"@en' in query:
                    rows.append(
                        {
                            "name": name,
                            "item": E + qid,
                            "itemLabel": label,
                            "site": site,
                            "countryLabel": country,
                            "isLabel": "true" if name == label else "false",
                            "dissolved": "false",
                        }
                    )
        return httpx.Response(200, json=sparql_json(rows))

    return handler


class TestTheReport:
    def run(self) -> tuple[dict[str, object], list[str]]:
        queries: list[str] = []
        client = polite(wikidata(queries), FakeTime())
        return build_report(client, SEED, KB), queries

    def test_held_out_rows_are_listed_and_never_looked_up(self):
        report, queries = self.run()
        assert report["excluded_heldout"] == [{"seed_id": "qs2027-025", "case": "tum"}]
        assert not any("Heldout Row" in q for q in queries)
        assert set(HELDOUT_SEED_IDS) >= {"qs2027-025", "qs2027-087"}

    def test_rows_without_a_domain_get_proposals_with_a_review_block(self):
        report, _ = self.run()
        proposals = {p["seed_id"]: p for p in report["proposals"]}  # type: ignore[union-attr]
        ucl = proposals["qs2027-009"]
        assert ucl["wikidata_item"] == "Q193196"
        assert ucl["proposed_official_domain"] == "ucl.ac.uk"
        assert ucl["match_confidence"] == "medium"
        assert ucl["review"] == {"decision": None, "reviewer": None, "note": None}
        assert proposals["qs2027-900"]["proposed_official_domain"] is None
        assert "qs2027-001" not in proposals

    def test_an_unmatched_row_is_tried_with_entity_search(self):
        _, queries = self.run()
        assert any("EntitySearch" in q and "Nowhere College" in q for q in queries)

    def test_kb_domains_disagreeing_with_p856_are_listed(self):
        report, _ = self.run()
        verdicts = {c["seed_id"]: c["verdict"] for c in report["kb_check"]}  # type: ignore[union-attr]
        assert verdicts == {"qs2027-002": "agree", "qs2027-003": "disagree"}
        counts = report["counts"]
        assert counts["kb_by_verdict"] == {"agree": 1, "disagree": 1}  # type: ignore[index]

    def test_the_catalogue_rows_are_never_written(self):
        seed, kb = copy.deepcopy(SEED), copy.deepcopy(KB)
        build_report(polite(wikidata([]), FakeTime()), seed, kb)
        assert seed == SEED and kb == KB
