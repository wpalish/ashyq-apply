"""Wayfinder free-search 06 — Wikidata P856 domain proposals, offline.

Every request goes to an ``httpx.MockTransport``; the clock and the sleep are
fakes, so the politeness rules (one request a second, ``Retry-After``) are
pinned without waiting and without the network.
"""

from __future__ import annotations

import copy
import json
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
    build_native_report,
    build_report,
    judge,
    name_variants,
    off_seed_rows,
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


# --- NN-1a: native names (P1448 and the labels in the row's languages) --------------

NATIVE_SEED: list[dict[str, Any]] = [
    {
        "seed_id": "qs2027-801",
        "name": "Synthetic Technical University",
        "country": "Türkiye",
        "official_domain": "stu.edu.tr",
    },
    {
        "seed_id": "qs2027-802",
        "name": "Mismatch University",
        "country": "Türkiye",
        "official_domain": "mine.edu.tr",
    },
    {"seed_id": "qs2027-803", "name": "Paris Example University", "country": "France"},
    {"seed_id": "qs2027-804", "name": "Example University", "country": "United Kingdom"},
    {"seed_id": "qs2027-025", "name": "Heldout Row", "country": "Germany"},
]
OFF_SEED = [{"seed_id": None, "name": "Tallinn Example University", "country": "Estonia"}]

NATIVE_LABELS = {
    "Synthetic Technical University": ("Q1001", "https://www.stu.edu.tr/", "Turkey"),
    "Mismatch University": ("Q1002", "https://www.other.edu.tr/", "Turkey"),
    "Tallinn Example University": ("Q1003", "https://www.tex.ee/", "Estonia"),
}
NATIVE_VALUES = {
    "Q1001": [
        ("official", "Sentetik Teknik Üniversitesi", "tr"),
        ("official", "Synthetic Technical University", "en"),
        ("label", "Sentetik Teknik Üniversitesi", "tr"),
        ("label", "Synthetic Technical University", "tr"),
        ("label", "Synthetische Technische Universität", "de"),
    ],
    "Q1002": [("label", "Uyumsuz Üniversitesi", "tr")],
    "Q1003": [("label", "Tallinna Näidisülikool", "et")],
}


def native_wikidata(queries: list[str]):
    def handler(request: httpx.Request) -> httpx.Response:
        query = query_of(request)
        queries.append(query)
        rows: list[dict[str, str]] = []
        if "VALUES ?name" in query:
            for name, (qid, site, country) in NATIVE_LABELS.items():
                if f'"{name}"@en' in query:
                    rows.append(
                        {
                            "name": name,
                            "item": E + qid,
                            "itemLabel": name,
                            "site": site,
                            "countryLabel": country,
                            "isLabel": "true",
                            "dissolved": "false",
                        }
                    )
        elif "VALUES ?item" in query:
            for qid, values in NATIVE_VALUES.items():
                if f"wd:{qid}" in query:
                    rows += [
                        {"item": E + qid, "value": value, "lang": lang, "kind": kind}
                        for kind, value, lang in values
                    ]
        return httpx.Response(200, json=sparql_json(rows))

    return handler


class TestNativeNames:
    def run(self) -> tuple[dict[str, Any], list[str]]:
        queries: list[str] = []
        client = polite(native_wikidata(queries), FakeTime())
        return build_native_report(client, NATIVE_SEED, OFF_SEED), queries

    def proposals(self) -> dict[str, dict[str, Any]]:
        report, _ = self.run()
        return {p["name"]: p for p in report["proposals"]}

    def test_held_out_and_english_only_rows_are_never_looked_up(self):
        report, queries = self.run()
        assert report["excluded_heldout"] == [{"seed_id": "qs2027-025", "case": "tum"}]
        assert not any("Heldout Row" in q or '"Example University"' in q for q in queries)
        assert report["counts"]["english_only_skipped"] == 1
        assert report["counts"]["queried"] == 4
        assert report["counts"]["dev_off_seed"] == 1
        assert "Example University" not in {p["name"] for p in report["proposals"]}

    def test_the_native_query_asks_for_the_official_name_and_the_rows_languages(self):
        _, queries = self.run()
        (native,) = [q for q in queries if "VALUES ?item" in q]
        assert "wdt:P1448" in native and "wd:Q1001" in native and "wd:Q1003" in native
        assert '"tr"' in native and '"et"' in native
        assert '"en"' not in native.split("IN (")[1]
        # Only item ids, never a row's domain, travel in that query.
        assert "stu.edu.tr" not in native

    def test_a_matched_row_gets_its_native_names_and_a_review_block(self):
        stu = self.proposals()["Synthetic Technical University"]
        assert stu["wikidata_item"] == "Q1001"
        assert stu["match_confidence"] == "high"
        assert stu["domain_check"] == "agree"
        assert stu["languages"] == ["tr"]
        # The English name again, a duplicate spelling and a German label are left out.
        assert stu["proposed_native_names"] == ["Sentetik Teknik Üniversitesi"]
        assert {"value": "Synthetic Technical University", "lang": "en"} in stu["official_names"]
        assert all(label["lang"] == "tr" for label in stu["labels"])
        assert stu["review"] == {"decision": None, "reviewer": None, "note": None}
        assert stu["source"] == "catalogue"

    def test_an_item_whose_site_is_not_the_rows_domain_is_capped_at_low(self):
        row = self.proposals()["Mismatch University"]
        assert row["domain_check"] == "disagree"
        assert row["match_confidence"] == "low"
        assert "official_domain" in row["reason"]

    def test_an_unmatched_row_proposes_nothing(self):
        report, queries = self.run()
        row = {p["name"]: p for p in report["proposals"]}["Paris Example University"]
        assert row["match_confidence"] == "none" and row["proposed_native_names"] == []
        assert any("EntitySearch" in q and "Paris Example University" in q for q in queries)

    def test_a_dev_university_outside_the_seed_is_proposed_without_a_seed_id(self):
        row = self.proposals()["Tallinn Example University"]
        assert row["seed_id"] is None and row["source"] == "dev_off_seed"
        assert row["proposed_native_names"] == ["Tallinna Näidisülikool"]

    def test_the_seed_is_never_written(self):
        seed = copy.deepcopy(NATIVE_SEED)
        build_native_report(polite(native_wikidata([]), FakeTime()), seed, OFF_SEED)
        assert seed == NATIVE_SEED

    def test_the_cli_writes_the_native_proposals(self, tmp_path, monkeypatch):
        from evaluation.research import wikidata_domains

        real_client = httpx.Client

        def offline_client(**kwargs: Any) -> httpx.Client:
            assert kwargs.get("follow_redirects") is False
            return real_client(transport=httpx.MockTransport(native_wikidata([])))

        fake = FakeTime()
        seed = tmp_path / "seed.json"
        seed.write_text(json.dumps({"universities": NATIVE_SEED}), encoding="utf-8")
        monkeypatch.setattr(wikidata_domains, "SEED_PATH", seed)
        monkeypatch.setattr(wikidata_domains.httpx, "Client", offline_client)
        monkeypatch.setattr(
            wikidata_domains,
            "PoliteClient",
            lambda http: PoliteClient(http, sleep=fake.sleep, clock=fake.clock),
        )
        monkeypatch.setattr(wikidata_domains, "off_seed_rows", lambda: OFF_SEED)
        out = tmp_path / "native.json"
        assert wikidata_domains.main(["--native-names", "--out", str(out)]) == 0
        report = json.loads(out.read_text(encoding="utf-8"))
        assert report["schema"] == "catalogue_native_names.proposed/1"
        assert report["counts"]["dev_off_seed"] == 1
        assert report["counts"]["queried"] == 4
        assert wikidata_domains.NATIVE_OUT_PATH.name == "catalogue_native_names.proposed.json"

    def test_the_off_seed_rows_are_the_dev_tables_names_only(self):
        from evaluation.research.live import PROXY_OFF_SEED

        rows = off_seed_rows()
        assert {(r["name"], r["country"]) for r in rows} == {
            (name, country) for name, country, _ in PROXY_OFF_SEED.values()
        }
        assert all(
            r["seed_id"] is None and set(r) == {"seed_id", "name", "country", "city"} for r in rows
        )


class TestItemIds:
    """SR2-10 / SEC-3: an id cut from a response goes into the next query only as ``Q<digits>``."""

    def test_only_a_q_number_is_an_item(self):
        from evaluation.research.wikidata_domains import _qid

        assert _qid(E + "Q1001") == "Q1001"
        for uri in (
            E + "Q1;DROP",
            E + "Q1 } ?x ?y ?z {",
            E + "P856",
            E + "q12",
            E + "Q",
            E + "Q12\n",
            "",
        ):
            assert _qid(uri) == ""

    def test_a_hostile_uri_yields_no_item_and_no_query_value(self):
        from evaluation.research.wikidata_domains import collect, native_query

        found = collect(
            [
                {"item": E + "Q1;DROP", "itemLabel": "Injected", "site": "https://x.example/"},
                {"item": E + "Q7", "itemLabel": "Real", "site": "https://real.example/"},
            ]
        )
        assert set(found) == {"Q7"}
        query = native_query(["Q1;DROP", "", "Q7"], ["de"])
        assert "VALUES ?item { wd:Q7 }" in query
        assert "DROP" not in query and "wd: " not in query
