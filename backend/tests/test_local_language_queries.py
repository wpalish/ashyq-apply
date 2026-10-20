"""Plan v3 rule R5: one query family in the institution's own language.

Every discovery query was English and Serper was never told a language, so
programme pages published only in the institution's language were never
returned. M5's probe found ``site:{domain} "{alias}" {bachelor word}`` with
Serper ``hl``/``gl`` returning the gold page on 5 of 6 local-language cases.
With ``LOCAL_LANGUAGE_QUERIES`` on, that family takes the third first-pass
slot, ``programmes`` moves to the reserve, ``admissions`` is dropped and six
stay six. The language comes from the institution's country, the alias from
the ontology and the degree word from R1's table — never from the applicant.
"""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.adapters import page_classifier
from app.adapters.discovery.live_discovery import (
    DiscoveryTrace,
    LiveDiscoveryAdapter,
    PageCategory,
)
from app.adapters.search import intent as intent_module
from app.adapters.search.base import SearchResponse, SearchResult
from app.adapters.search.intent import (
    DEFAULT_QUERY_BUDGET,
    DiscoveryIntent,
    local_language_terms,
    queries_for,
)
from app.adapters.search.ontology import country_languages, country_region
from app.adapters.search.prefilter import prefilter
from app.adapters.search.retrieval import discover_candidates, rank_candidates
from app.domain.enums import DegreeLevel
from app.schemas.profile import ApplicantProfileIn
from tests.test_discovery_query_reserve import Fetcher

BACKEND = Path(__file__).resolve().parents[1]
FIELD = "Computer Science"
MISSING_REGISTRY = Path("/nonexistent-institution-registry.json")

#: Today's six families, in order: what every plan was before R5.
TODAY = (
    "field_and_degree",
    "natural_language",
    "programmes",
    "courses",
    "undergraduate",
    "admissions",
)
WITH_LOCAL = (
    "field_and_degree",
    "natural_language",
    "local_language",
    "programmes",
    "courses",
    "undergraduate",
)


@pytest.fixture
def r5(monkeypatch):
    monkeypatch.setattr(intent_module, "LOCAL_LANGUAGE_QUERIES", True)


def intent(
    country: str,
    *,
    domain: str = "uio.no",
    name: str = "Universitetet i Oslo",
    field: str = FIELD,
    degree: DegreeLevel = DegreeLevel.BACHELOR,
) -> DiscoveryIntent:
    return DiscoveryIntent(
        institution=name, domain=domain, degree=degree, field=field, institution_country=country
    )


def families(found) -> tuple[str, ...]:
    return tuple(query.family for query in found)


# --- the plan ---------------------------------------------------------------


def test_on_by_default():
    assert intent_module.LOCAL_LANGUAGE_QUERIES is True


def test_off_a_local_language_institution_keeps_todays_plan(monkeypatch):
    monkeypatch.setattr(intent_module, "LOCAL_LANGUAGE_QUERIES", False)
    plan = queries_for(intent("Norway"))
    assert families(plan) == TODAY
    assert all(query.hl == query.gl == "" for query in plan)
    assert plan == queries_for(intent(""))


def test_on_the_local_family_takes_the_third_first_pass_slot(r5):
    plan = queries_for(intent("Norway"))
    assert families(plan) == WITH_LOCAL
    assert len(plan) == DEFAULT_QUERY_BUDGET
    first = families(plan)[: intent_module.DISCOVERY_FIRST_PASS_QUERIES]
    assert first == ("field_and_degree", "natural_language", "local_language")
    assert "admissions" not in families(plan)
    local = plan[2]
    # M5's shape d for uio, byte for byte.
    assert local.text == "site:uio.no informatikk bachelor"
    assert (local.hl, local.gl) == ("no", "no")
    # Every other family is today's, with no locale.
    off = {q.family: q for q in replace_flag_off(intent("Norway"))}
    for query in plan:
        if query.family != "local_language":
            assert query == off[query.family]


def replace_flag_off(value: DiscoveryIntent):
    previous = intent_module.LOCAL_LANGUAGE_QUERIES
    intent_module.LOCAL_LANGUAGE_QUERIES = False
    try:
        return queries_for(value)
    finally:
        intent_module.LOCAL_LANGUAGE_QUERIES = previous


@pytest.mark.parametrize(
    ("country", "domain", "text", "hl", "gl"),
    [
        (
            "Argentina",
            "uba.ar",
            'site:uba.ar "ciencias de la computación" licenciatura',
            "es",
            "ar",
        ),
        ("France", "universite-paris-saclay.fr", None, "fr", "fr"),
        ("Denmark", "ku.dk", "site:ku.dk datalogi bachelor", "da", "dk"),
        ("Belgium", "kuleuven.be", "site:kuleuven.be informatica bachelor", "nl", "be"),
        ("China", "tsinghua.edu.cn", "site:tsinghua.edu.cn 计算机科学与技术 本科", "zh-cn", "cn"),
        ("Taiwan", "ntu.edu.tw", None, "zh-tw", "tw"),
    ],
)
def test_m5_shapes(r5, country, domain, text, hl, gl):
    plan = queries_for(intent(country, domain=domain))
    local = next(q for q in plan if q.family == "local_language")
    if text is not None:
        assert local.text == text
    assert (local.hl, local.gl) == (hl, gl)
    assert len(plan) == DEFAULT_QUERY_BUDGET


def test_an_english_speaking_country_is_byte_identical(r5):
    for country in ("United Kingdom", "Australia", "Canada", "Ireland", ""):
        on = queries_for(intent(country, domain="rug.nl", name="A University"))
        assert on == replace_flag_off(intent(country, domain="rug.nl", name="A University"))
        assert families(on) == TODAY
    assert local_language_terms(intent("United Kingdom")) is None


def test_a_country_with_two_languages_uses_the_first_that_has_both_words(r5, monkeypatch):
    assert country_languages("Belgium")[:2] == ("nl", "fr")
    assert local_language_terms(intent("Belgium")).language == "nl"
    # No Dutch degree word: the family falls to French, still Belgium's gl.
    words = dict(page_classifier._LOCAL_BACHELOR_QUERY_WORDS)
    del words["nl"]
    monkeypatch.setattr(page_classifier, "_LOCAL_BACHELOR_QUERY_WORDS", words)
    local = next(q for q in queries_for(intent("Belgium", domain="uclouvain.be")) if q.hl)
    assert local.text == "site:uclouvain.be informatique licence"
    assert (local.hl, local.gl) == ("fr", "be")


def test_switzerland_and_kazakhstan_take_their_first_language(r5):
    assert local_language_terms(intent("Switzerland")).language == "de"
    assert local_language_terms(intent("Switzerland")).gl == "ch"
    kz = local_language_terms(intent("Kazakhstan"))
    assert (kz.language, kz.alias, kz.degree_word, kz.gl) == (
        "kk",
        "информатика",
        "бакалавр",
        "kz",
    )


def test_no_alias_no_degree_word_or_another_level_means_no_local_family(r5, monkeypatch):
    # A field the ontology has no localized alias for.
    assert families(queries_for(intent("Norway", field="Sociology"))) == TODAY
    # R1's table names a bachelor's only; a master's plan is today's.
    master = intent("Norway", degree=DegreeLevel.MASTER)
    assert queries_for(master) == replace_flag_off(master)
    # A language with an alias but no degree word. Catalan had none until LV-1
    # gave it R1's own "grau en" ("grau" alone is not R1's word).
    assert page_classifier.local_bachelor_word("ca") == "grau en"
    monkeypatch.setattr(page_classifier, "_LOCAL_BACHELOR_QUERY_WORDS", {"ca": "grau"})
    assert page_classifier.local_bachelor_word("ca") is None
    monkeypatch.setattr(page_classifier, "_LOCAL_BACHELOR_QUERY_WORDS", {})
    assert families(queries_for(intent("Norway"))) == TODAY


def test_the_alias_follows_the_flags_the_confirm_step_reads(r5, monkeypatch):
    # informatikk is an LX-1 entry R1 absorbed: with R1 and LX-1 off the
    # confirm would refuse it, so the query does not name it.
    monkeypatch.setattr(page_classifier, "LOCALIZED_PAGE_IDENTITY", False)
    monkeypatch.setattr(page_classifier, "LEXICON_V2", False)
    # LV-1 adds informatikk under nb/nn; pinned off to isolate R1 and LX-1.
    monkeypatch.setattr(page_classifier, "LEXICON_LANGUAGE_COVERAGE", False)
    assert local_language_terms(intent("Norway")) is None
    # A settled alias needs no flag.
    assert local_language_terms(intent("Germany", domain="tum.de")).alias == "informatik"


def test_degree_words_are_r1s_and_every_country_has_a_region(monkeypatch):
    monkeypatch.setattr(page_classifier, "LOCALIZED_PAGE_IDENTITY", True)
    raw = json.loads((BACKEND / "app/adapters/search/languages.json").read_text("utf-8"))
    for country, languages in raw["countries"].items():
        assert country_region(country) == raw["regions"][country]
        assert len(raw["regions"][country]) == 2
        for language in languages:
            word = page_classifier.local_bachelor_word(language)
            if word is None:
                assert language == "ca"
                continue
            # R1's own reading of the word, on a page in that language.
            assert page_classifier._degree_level(word, language) == "bachelor"
    assert country_region("United Kingdom") == ""


def test_no_applicant_attribute_reaches_the_local_family(r5):
    """The language is the institution's country, not the applicant's."""
    applicant = ApplicantProfileIn.model_validate(
        {
            "display_name": "Aigerim Example",
            "context": {
                "level": "bachelor",
                "intended_fields": [FIELD],
                "intake_year": 2027,
                "citizenship": "KZ",
                "country_of_residence": "KZ",
                "education_country": "KZ",
                "education_system": "KZ",
            },
        }
    )
    built = DiscoveryIntent.from_profile(
        applicant, institution="Universitetet i Oslo", domain="uio.no"
    )
    # from_profile never sets the institution's country: no family from a profile alone.
    assert families(queries_for(built)) == TODAY
    plan = queries_for(replace(built, institution_country="Norway"))
    text = " ".join(q.text for q in plan).lower()
    for word in ("aigerim", "kazakh", "kz ", "2027", "информатика", "бакалавр"):
        assert word not in text
    assert next(q for q in plan if q.family == "local_language").hl == "no"
    # A UK institution for the same Kazakh applicant: no local family at all.
    assert families(queries_for(replace(built, institution_country="United Kingdom"))) == TODAY


def test_an_institution_country_carrying_applicant_data_is_refused():
    with pytest.raises(ValueError, match="email"):
        intent("someone@example.com")


# --- sending it -------------------------------------------------------------


class Provider:
    """Records every call, with ``hl``/``gl`` when the localized search is used."""

    name = "fake"

    def __init__(self, answers=lambda query: []) -> None:
        self.answers = answers
        self.calls: list[dict] = []

    def _respond(self, query: str) -> SearchResponse:
        now = datetime.now(UTC)
        return SearchResponse(
            query=query,
            provider=self.name,
            retrieved_at=now,
            results=tuple(
                SearchResult(url=url, title=title, provider=self.name, rank=i + 1, retrieved_at=now)
                for i, (url, title) in enumerate(self.answers(query))
            ),
        )

    async def search(self, *, query, domains=(), max_results=10):
        self.calls.append({"query": query, "domains": list(domains)})
        return self._respond(query)

    async def search_localized(self, *, query, hl, gl, domains=(), max_results=10):
        self.calls.append({"query": query, "hl": hl, "gl": gl, "domains": list(domains)})
        return self._respond(query)


class PlainProvider:
    name = "plain"

    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def search(self, *, query, domains=(), max_results=10):
        self.calls.append({"query": query, "domains": list(domains)})
        return SearchResponse(query=query, provider=self.name, retrieved_at=datetime.now(UTC))


async def test_hl_and_gl_reach_a_provider_that_takes_them(r5):
    provider = Provider()
    report = await discover_candidates(provider, intent("Norway"), hop_entry_points=0)
    assert report.queries_run == WITH_LOCAL
    localized = [call for call in provider.calls if "hl" in call]
    assert localized == [
        {"query": "site:uio.no informatikk bachelor", "hl": "no", "gl": "no", "domains": []}
    ]
    # Every other family goes through plain search with its domain, as today.
    assert all(call["domains"] == ["uio.no"] for call in provider.calls if "hl" not in call)


async def test_a_provider_without_a_locale_gets_the_same_words(r5):
    provider = PlainProvider()
    report = await discover_candidates(provider, intent("Norway"), hop_entry_points=0)
    assert report.queries_run == WITH_LOCAL
    assert provider.calls[2] == {"query": "site:uio.no informatikk bachelor", "domains": ["uio.no"]}


async def test_found_by_names_the_local_family(r5):
    page = "https://www.uio.no/studier/program/informatikk-programmering/"

    def answers(query):
        return (
            [(page, "Informatikk: programmering og systemarkitektur")]
            if "informatikk" in query
            else []
        )

    report = await discover_candidates(Provider(answers), intent("Norway"), hop_entry_points=0)
    (found,) = report.candidates
    assert found.found_by == ("local_language",)
    assert ("local_language", (page,)) in report.results_by_family


def test_the_local_alias_ranks_as_the_field_when_on(r5, monkeypatch):
    now = datetime.now(UTC)
    results = [
        SearchResult(
            url="https://exactas.uba.ar/carreras/computacion/",
            title="Licenciatura en Ciencias de la Computación",
            provider="fake",
            rank=2,
            retrieved_at=now,
        )
    ]
    uba = intent("Argentina", domain="uba.ar", name="Universidad de Buenos Aires")
    outcome = prefilter(results, domain="uba.ar", degree=DegreeLevel.BACHELOR)
    (on,) = rank_candidates(outcome, uba)
    assert "strong_alias_in_title" in on.signals
    monkeypatch.setattr(intent_module, "LOCAL_LANGUAGE_QUERIES", False)
    (off,) = rank_candidates(outcome, uba)
    assert "strong_alias_in_title" not in off.signals
    assert on.score > off.score


# --- discovery's two passes and the shared budget ---------------------------

NAME = "Universitetet i Oslo"
DOMAIN = "www.uio.no"
EVENT = "https://www.uio.no/om/aktuelt/arrangementer/informatikk-dag.html"
EVENT_HTML = (
    "<html><head><title>Event</title></head><body><h1>Informatikk-dagen</h1>"
    "<p>Join us for talks and demos on campus.</p></body></html>"
)


def profile() -> ApplicantProfileIn:
    return ApplicantProfileIn.model_validate(
        {
            "context": {
                "level": "bachelor",
                "intended_fields": [FIELD],
                "intake_year": 2027,
                "citizenship": "KZ",
                "country_of_residence": "KZ",
                "education_country": "KZ",
                "education_system": "KZ",
            }
        }
    )


@pytest.fixture
def reserve(monkeypatch):
    monkeypatch.setattr(intent_module, "DISCOVERY_QUERY_RESERVE", True)
    monkeypatch.setattr(intent_module, "SHARED_QUERY_BUDGET", True)


async def run_search(provider, *, country="Norway", sent_before=0, trace_country=""):
    built = LiveDiscoveryAdapter(Fetcher({EVENT: EVENT_HTML}), registry_path=MISSING_REGISTRY)  # type: ignore[arg-type]
    built._search_provider = provider
    built._search_provider_resolved = True
    trace = DiscoveryTrace(institution=NAME, domain=DOMAIN, country=trace_country)
    trace.search_queries_sent = sent_before
    selected = {category: [] for category in PageCategory.ALL}
    await built._add_search_results(
        {"name": NAME, "country": country}, DOMAIN, selected, trace, profile()
    )
    return trace


def sent_families(provider) -> list[str]:
    by_text = {q.text: q.family for q in queries_for(intent("Norway"))}
    return [by_text[call["query"]] for call in provider.calls]


async def test_two_passes_send_six_with_local_first_and_programmes_in_reserve(r5, reserve):
    provider = Provider(lambda query: [(EVENT, "Informatikk-dagen")])
    trace = await run_search(provider)
    assert sent_families(provider) == list(WITH_LOCAL)
    assert trace.discovery_query_passes == [3, 3]
    assert trace.search_queries_sent == DEFAULT_QUERY_BUDGET
    assert [call.get("hl") for call in provider.calls] == [None, None, "no", None, None, None]
    assert [row["family"] for row in trace.search_results] == list(WITH_LOCAL)
    # The lead was read once; the families that returned it are on the trace.
    assert trace.lead_found_by[EVENT][:3] == [
        "field_and_degree",
        "natural_language",
        "local_language",
    ]
    assert "lead_found_by" in trace.as_dict()


async def test_the_identity_fallback_query_leaves_five_with_local_still_first(r5, reserve):
    provider = Provider(lambda query: [(EVENT, "Informatikk-dagen")])
    trace = await run_search(provider, sent_before=1)
    assert sent_families(provider) == list(WITH_LOCAL[:5])
    assert trace.discovery_query_passes == [3, 2]
    assert trace.search_queries_sent == DEFAULT_QUERY_BUDGET


async def test_the_trace_country_is_the_institutions(r5, reserve):
    provider = Provider()
    await run_search(provider, country="", trace_country="Norway")
    assert any(call.get("hl") == "no" for call in provider.calls)


async def test_off_discovery_sends_todays_six_and_records_no_lead_families(reserve, monkeypatch):
    monkeypatch.setattr(intent_module, "LOCAL_LANGUAGE_QUERIES", False)
    provider = Provider(lambda query: [(EVENT, "Informatikk-dagen")])
    trace = await run_search(provider)
    by_text = {q.text: q.family for q in queries_for(intent(""))}
    assert [by_text[call["query"]] for call in provider.calls] == list(TODAY)
    assert all("hl" not in call for call in provider.calls)
    assert trace.lead_found_by == {}
    assert "lead_found_by" not in trace.as_dict()


async def test_an_english_country_institution_sends_todays_six_with_the_rule_on(r5, reserve):
    provider = Provider(lambda query: [(EVENT, "Informatikk-dagen")])
    await run_search(provider, country="United Kingdom")
    by_text = {q.text: q.family for q in queries_for(intent(""))}
    assert [by_text[call["query"]] for call in provider.calls] == list(TODAY)
    assert all("hl" not in call for call in provider.calls)


# --- the benchmark flag -----------------------------------------------------


def test_the_benchmark_flag_reaches_the_child_and_turns_the_rule_on(tmp_path, monkeypatch):
    import subprocess
    import sys

    from evaluation.research import live
    from evaluation.research.schema import Observation

    monkeypatch.setattr(intent_module, "LOCAL_LANGUAGE_QUERIES", False)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            *("live", "--live", "--case", "groningen", "--out", str(tmp_path)),
            "--local-language-queries",
        ],
    )
    monkeypatch.setattr(subprocess, "check_output", lambda *args, **kwargs: "synthetic-sha")
    commands = []

    def child(command, **kwargs):
        commands.append(command)
        output = Path(command[command.index("--out") + 1])
        output.write_text(Observation(case_id="groningen").model_dump_json(), encoding="utf-8")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", child)
    live.main()
    assert "--local-language-queries" in commands[0]

    seen = []

    async def capture(case_id, output, max_pages, seconds, **kwargs):
        seen.append(intent_module.LOCAL_LANGUAGE_QUERIES)

    monkeypatch.setattr(live, "capture_one", capture)
    monkeypatch.setenv("UNIMATCH_SEARCH_PROVIDER", "none")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            *("live", "--live", "--child", "--case", "groningen"),
            *("--out", str(tmp_path / "o.json"), "--local-language-queries"),
        ],
    )
    live.main()
    assert seen == [True]
