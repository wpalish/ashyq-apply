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
    alias_head,
    local_phrase_from_links,
)
from app.adapters.search import intent as intent_module
from app.adapters.search.base import SearchResponse, SearchResult
from app.adapters.search.intent import (
    DEFAULT_QUERY_BUDGET,
    DiscoveryIntent,
    local_language_terms,
    local_query_phrase,
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
    assert local_language_terms(intent("Germany", domain="kit.edu")).alias == "informatik"


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


# --- LQ-2a: the local query from the site's own words -------------------------
#
# Every site below is written for the test (``example-uni.*``); no page, label
# or URL is a development or heldout case's. The labels are ordinary programme
# names in each language, each chosen to exercise one rule.


@pytest.fixture
def lq2(r5, monkeypatch):
    monkeypatch.setattr(intent_module, "LOCAL_QUERY_FROM_PAGE_EVIDENCE", True)


def page(lang: str, *links: tuple[str, str]) -> str:
    anchors = "".join(f'<li><a href="{href}">{text}</a></li>' for href, text in links)
    return (
        f'<html lang="{lang}"><head><title>Home</title></head>'
        f"<body><ul>{anchors}</ul></body></html>"
    )


def phrase_of(html: str, links, *, languages, from_catalogue=False):
    return local_phrase_from_links(
        html,
        links,
        languages=languages,
        fields=[FIELD],
        degree="bachelor",
        from_catalogue=from_catalogue,
    )


def local_query(value: DiscoveryIntent):
    return next(q for q in queries_for(value) if q.family == "local_language")


def test_lq2_is_off_by_default():
    assert intent_module.LOCAL_QUERY_FROM_PAGE_EVIDENCE is False


def test_lq2_off_the_query_is_todays_byte_for_byte(r5):
    plain = intent("Chile", domain="example-uni.cl", name="Universidad Ejemplo")
    carrying = replace(
        plain,
        local_phrase="Licenciatura en Ciencia de la Computación",
        native_name="Universidad Ejemplo de Chile",
    )
    assert queries_for(carrying) == queries_for(plain)
    assert local_query(carrying).text == (
        'site:example-uni.cl "ciencias de la computación" licenciatura'
    )
    terms = local_language_terms(carrying)
    assert terms == local_language_terms(plain)
    assert terms is not None and terms.phrase is None


SYNTHETIC_HOMEPAGES = [
    # (country, page lang, link url, link text) -> the link text is the phrase
    (
        "Chile",
        "es",
        "https://www.example-uni.cl/carreras/computacion",
        "Licenciatura en Ciencia de la Computación",
    ),
    (
        "Mexico",
        "es-MX",
        "https://www.example-uni.mx/carreras/tecnologias-computacionales",
        "Ingeniería en Tecnologías Computacionales",
    ),
    (
        "France",
        "fr",
        "https://www.example-uni.fr/programmes/licence-informatique",
        "Licence Informatique",
    ),
    (
        "Germany",
        "de",
        "https://www.example-uni.de/studium/studiengaenge/informatik",
        "Informatik (B.Sc.)",
    ),
    (
        "Norway",
        "nb",
        "https://www.example-uni.no/programmes/informatikk",
        "Informatikk: språk og kommunikasjon",
    ),
    (
        "China",
        "zh-CN",
        "https://www.example-uni.cn/undergraduate/programmes/cs",
        "计算机科学与技术专业",
    ),
    ("South Korea", "ko", "https://www.example-uni.kr/programmes/computing", "컴퓨터과학 학사과정"),
    (
        "Russia",
        "ru",
        "https://www.example-uni.ru/programs/computer-science",
        "Компьютерные науки и инженерия",
    ),
]


@pytest.mark.parametrize(("country", "lang", "url", "text"), SYNTHETIC_HOMEPAGES)
def test_lq2_a_homepage_link_in_the_sites_language_gives_the_phrase(lq2, country, lang, url, text):
    links = [("https://www.example-uni.org/news/", "News"), (url, text)]
    html = page(lang, *links)
    assert phrase_of(html, links, languages=intent(country).languages) == (text, url)


def test_lq2_the_head_is_the_longest_words_stem_or_an_unspaced_alias_whole():
    assert alias_head("ciencias de la computación") == "computaci"
    assert alias_head("informatique") == "informatiq"
    assert alias_head("datalogi") == "datalo"
    assert alias_head("전산학") == "전산학"
    assert alias_head("计算机科学与技术") == "计算机科学与技术"


def test_lq2_a_field_title_comes_before_a_head_only_title_on_one_page(lq2):
    links = [
        ("https://www.example-uni.cl/carreras/a", "Ingeniería en Tecnologías Computacionales"),
        ("https://www.example-uni.cl/carreras/b", "Ciencia de la Computación"),
    ]
    html = page("es", *links)
    # A catalogue page: both links are programme leads, as the walk reads them.
    assert phrase_of(html, links, languages=("es",), from_catalogue=True) == (
        "Ciencia de la Computación",
        "https://www.example-uni.cl/carreras/b",
    )
    # The head-only title alone is still a phrase (the second R5 shape it misses).
    assert phrase_of(html, links[:1], languages=("es",), from_catalogue=True) == links[0][::-1]


@pytest.mark.parametrize(
    "text",
    [
        # More than eight words: a card's run-on text, not a name.
        "Ciencia de la Computación para estudiantes que quieren aprender mucho más",
        # Digits: a programme code, a year or a score.
        "Ciencia de la Computación 2027",
        "6B06104 Ciencia de la Computación",
        # A personal title: a name follows it.
        "Prof. Ana Pérez, Ciencia de la Computación",
        "Dra Ana Computación",
        # Another level, in any language.
        "Magíster en Ciencia de la Computación",
        # A related programme, not the field.
        "Ingeniería Informática y Computación",
        # An address.
        "computacion@example-uni.cl",
        # A currency sign: _reject_applicant_data's refusal.
        "Computación € beca",
        # A unit (CH-1's unit nouns), not a programme.
        "Departamento de Ciencia de la Computación",
        # The information false friend of the informati- stem.
        "Información para estudiantes de informática",
    ],
)
def test_lq2_refused_link_texts_give_no_phrase(lq2, text):
    url = "https://www.example-uni.cl/carreras/x"
    control = "Ciencia de la Computación"
    # On a catalogue page, so only the label decides; the control link passes.
    assert phrase_of(page("es"), [(url, control)], languages=("es",), from_catalogue=True)
    html = page("es", (url, text))
    assert phrase_of(html, [(url, text)], languages=("es",), from_catalogue=True) is None


def test_lq2_the_information_false_friend_and_a_unit_in_german(lq2):
    links = [
        ("https://www.example-uni.de/studium/info", "Informationen für Erstsemester"),
        ("https://www.example-uni.de/studium/institut", "Institut für Informatik"),
    ]
    html = page("de", *links)
    assert phrase_of(html, links, languages=("de",), from_catalogue=True) is None
    # The stem still reaches the field's own word.
    kept = [("https://www.example-uni.de/studium/x", "Informatik")]
    assert phrase_of(page("de", *kept), kept, languages=("de",), from_catalogue=True) == (
        "Informatik",
        "https://www.example-uni.de/studium/x",
    )


def test_lq2_a_url_naming_the_level_breaks_a_tie_between_field_titles(lq2):
    links = [
        ("https://www.example-uni.de/studium/lehramt-informatik", "Informatik B.Ed."),
        ("https://www.example-uni.de/studium/bachelor-informatik", "Informatik B.Sc."),
    ]
    html = page("de", *links)
    assert phrase_of(html, links, languages=("de",), from_catalogue=True) == links[1][::-1]


def test_lq2_the_cap_and_the_privacy_check_are_the_query_sides(lq2):
    assert local_query_phrase(" «Licenciatura en Ciencia de la Computación» ") == (
        "Licenciatura en Ciencia de la Computación"
    )
    assert local_query_phrase("uno dos tres cuatro cinco seis siete ocho") is not None
    assert local_query_phrase("uno dos tres cuatro cinco seis siete ocho nueve") is None
    assert local_query_phrase("Informática 3.8") is None
    assert local_query_phrase("Informática $") is None
    assert local_query_phrase("http://example-uni.cl Informática") is None
    assert local_query_phrase("") is None


@pytest.mark.parametrize(
    "mark", ['"', "“", "”", "„", "‟", "«", "»", "＂", "〝", "〞", "〟", "″", "‶"]
)
def test_lq2_no_double_quote_of_any_script_leaves_the_phrase(lq2, mark):
    """SR2-04 (security review 2026-10-22): page text cannot close the quoted phrase.

    A link text is the site's, and a quote left in it would end the phrase
    early and put the rest, operators included, outside the quotes.
    """
    text = f"Informática{mark} OR site:example.org {mark}x"
    phrase = local_query_phrase(text)
    assert phrase is not None
    assert mark not in phrase
    query = local_query(
        replace(
            intent("Chile", domain="example-uni.cl", name="Universidad Ejemplo"),
            local_phrase=text,
        )
    )
    # Exactly the two quotes the query adds around the phrase, and nothing outside them.
    assert query.text == f'site:example-uni.cl "{phrase}" licenciatura'
    assert sum(query.text.count(m) for m in '"“”„‟«»＂〝〞〟″‶') == 2


def test_lq2_a_page_not_in_a_language_of_the_country_gives_nothing(lq2):
    url = "https://www.example-uni.cl/carreras/x"
    links = [(url, "Ciencia de la Computación")]
    assert phrase_of(page("en", *links), links, languages=("es",)) is None
    assert phrase_of(page("pt", *links), links, languages=("es",)) is None
    no_lang = "<html><body><a href='/carreras/x'>Ciencia de la Computación</a></body></html>"
    assert phrase_of(no_lang, links, languages=("es",)) is None


def test_lq2_a_link_that_is_no_programme_lead_gives_nothing_on_a_homepage(lq2):
    url = "https://www.example-uni.cl/noticias/premio"
    links = [(url, "Ciencia de la Computación")]
    html = page("es", *links)
    assert phrase_of(html, links, languages=("es",)) is None
    # On a catalogue page the same link is a programme lead, as the walk reads it.
    assert phrase_of(html, links, languages=("es",), from_catalogue=True) == (
        "Ciencia de la Computación",
        url,
    )


def test_lq2_the_phrase_replaces_the_alias_with_the_same_locale(lq2):
    base = intent("Chile", domain="example-uni.cl", name="Universidad Ejemplo")
    today = local_query(base)
    on = replace(base, local_phrase="Ingeniería en Tecnologías Computacionales")
    query = local_query(on)
    assert query.text == (
        'site:example-uni.cl "Ingeniería en Tecnologías Computacionales" licenciatura'
    )
    assert (query.hl, query.gl) == (today.hl, today.gl) == ("es", "cl")
    plan = queries_for(on)
    assert families(plan) == WITH_LOCAL
    assert len(plan) == DEFAULT_QUERY_BUDGET
    for mine, theirs in zip(plan, queries_for(base), strict=True):
        if mine.family != "local_language":
            assert mine == theirs


def test_lq2_a_phrase_holding_the_degree_word_is_not_given_it_twice(lq2):
    on = replace(
        intent("Chile", domain="example-uni.cl", name="Universidad Ejemplo"),
        local_phrase="Licenciatura en Ciencia de la Computación",
    )
    assert local_query(on).text == (
        'site:example-uni.cl "Licenciatura en Ciencia de la Computación"'
    )
    # A one-word phrase is still quoted: it is the site's exact name.
    one = replace(intent("Norway"), local_phrase="Informatikk")
    assert local_query(one).text == 'site:uio.no "Informatikk" bachelor'


def test_lq2_falls_back_to_the_native_name_then_to_todays_words(lq2):
    base = intent("Chile", domain="example-uni.cl", name="Universidad Ejemplo")
    native = replace(base, native_name="Universidad Ejemplo de Chile")
    terms = local_language_terms(native)
    assert terms is not None
    assert (terms.phrase, terms.phrase_source) == ("Universidad Ejemplo de Chile", "native_name")
    assert local_query(native).text == (
        'site:example-uni.cl "Universidad Ejemplo de Chile" '
        '"ciencias de la computación" licenciatura'
    )
    # The link phrase wins over the native name.
    both = replace(native, local_phrase="Ciencia de la Computación")
    both_terms = local_language_terms(both)
    assert both_terms is not None and both_terms.phrase_source == "link"
    # Neither: today's words, byte for byte.
    assert local_query(base).text == (
        'site:example-uni.cl "ciencias de la computación" licenciatura'
    )
    base_terms = local_language_terms(base)
    assert base_terms is not None and base_terms.phrase is None


def test_lq2_a_phrase_the_check_refuses_falls_back(lq2):
    base = intent("Chile", domain="example-uni.cl", name="Universidad Ejemplo")
    long = replace(base, local_phrase="uno dos tres cuatro cinco seis siete ocho nueve")
    assert local_query(long) == local_query(base)


def test_lq2_no_local_family_no_phrase(lq2):
    english = replace(
        intent("United Kingdom", domain="example-uni.ac.uk"), local_phrase="Computing"
    )
    assert families(queries_for(english)) == TODAY
    master = replace(intent("Chile", degree=DegreeLevel.MASTER), local_phrase="Computación")
    assert "local_language" not in families(queries_for(master))


def test_lq2_a_phrase_carrying_applicant_data_cannot_build_an_intent():
    with pytest.raises(ValueError, match="email"):
        replace(intent("Chile"), local_phrase="someone@example.com")
    with pytest.raises(ValueError, match="grade"):
        replace(intent("Chile"), native_name="Universidad 3.8")


# --- LQ-2a in discovery: the navigation read, then the search ------------------

LQ2_HOME = "https://www.example-uni.cl/"
LQ2_LINK = "https://www.example-uni.cl/carreras/ciencia-computacion"
LQ2_HOMEPAGE = page(
    "es",
    ("/noticias/", "Noticias"),
    ("/carreras/ciencia-computacion", "Licenciatura en Ciencia de la Computación"),
)


def lq2_adapter(provider, pages: dict[str, str]) -> LiveDiscoveryAdapter:
    built = LiveDiscoveryAdapter(Fetcher(pages), registry_path=MISSING_REGISTRY)  # type: ignore[arg-type]
    built._search_provider = provider
    built._search_provider_resolved = True
    return built


async def lq2_discovery_run(provider) -> DiscoveryTrace:
    built = lq2_adapter(provider, {LQ2_HOME: LQ2_HOMEPAGE})
    trace = DiscoveryTrace(institution="Universidad Ejemplo", domain="example-uni.cl")
    selected: dict[str, list[str]] = {category: [] for category in PageCategory.ALL}
    entry = {"name": "Universidad Ejemplo", "country": "Chile", "homepage": LQ2_HOME}
    await built._navigation_fallback(entry, "example-uni.cl", selected, trace, profile())
    selected[PageCategory.PROGRAM_PAGE] = []
    await built._add_search_results(entry, "example-uni.cl", selected, trace, profile())
    return trace


async def test_lq2_discovery_sends_the_homepage_phrase_and_traces_it(lq2, reserve):
    provider = Provider()
    trace = await lq2_discovery_run(provider)
    localized = [call for call in provider.calls if "hl" in call]
    assert localized == [
        {
            "query": 'site:example-uni.cl "Licenciatura en Ciencia de la Computación"',
            "hl": "es",
            "gl": "cl",
            "domains": [],
        }
    ]
    assert trace.search_queries_sent <= DEFAULT_QUERY_BUDGET
    assert trace.local_query_phrase == {
        "phrase": "Licenciatura en Ciencia de la Computación",
        "source": "link",
        "link": LQ2_LINK,
        "page": LQ2_HOME,
        "planned": "yes",
    }
    assert trace.as_dict()["local_query_phrase"]["link"] == LQ2_LINK


async def test_lq2_off_discovery_sends_todays_words_and_traces_nothing(r5, reserve):
    provider = Provider()
    trace = await lq2_discovery_run(provider)
    localized = [call["query"] for call in provider.calls if "hl" in call]
    assert localized == ['site:example-uni.cl "ciencias de la computación" licenciatura']
    assert trace.local_query_phrase == {}
    assert "local_query_phrase" not in trace.as_dict()


async def test_lq2_a_native_name_on_the_seed_row_is_the_fallback(lq2, reserve):
    provider = Provider()
    built = lq2_adapter(provider, {})
    trace = DiscoveryTrace(institution="Universidad Ejemplo", domain="example-uni.cl")
    selected: dict[str, list[str]] = {category: [] for category in PageCategory.ALL}
    entry = {
        "name": "Universidad Ejemplo",
        "country": "Chile",
        # The first carries a digit and is refused; the second is the one sent.
        "native_name": ["Universidad Ejemplo 2026", "Universidad Ejemplo de Chile"],
    }
    await built._add_search_results(entry, "example-uni.cl", selected, trace, profile())
    (localized,) = [call for call in provider.calls if "hl" in call]
    assert localized["query"] == (
        'site:example-uni.cl "Universidad Ejemplo de Chile" '
        '"ciencias de la computación" licenciatura'
    )
    assert trace.local_query_phrase == {
        "phrase": "Universidad Ejemplo de Chile",
        "source": "native_name",
        "planned": "yes",
    }


def test_lq2_the_harness_flag_and_its_off_form(tmp_path, monkeypatch):
    import subprocess
    import sys

    from evaluation.research import live

    assert live.NEGATABLE_RULES["local-query-from-evidence"] == (
        ("app.adapters.search.intent", "LOCAL_QUERY_FROM_PAGE_EVIDENCE"),
    )
    assert "local-query-from-evidence" in live.DEFAULT_OFF_NEGATABLE
    result = subprocess.run(
        [sys.executable, "-m", "evaluation.research.live", "--help"],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "--local-query-from-evidence" in result.stdout
    assert "--no-local-query-from-evidence" in result.stdout

    seen = []

    async def capture(case_id, output, max_pages, seconds, **kwargs):
        seen.append(intent_module.LOCAL_QUERY_FROM_PAGE_EVIDENCE)

    monkeypatch.setattr(intent_module, "LOCAL_QUERY_FROM_PAGE_EVIDENCE", False)
    monkeypatch.setattr(live, "capture_one", capture)
    monkeypatch.setenv("UNIMATCH_SEARCH_PROVIDER", "none")
    argv = ["live", "--live", "--child", "--case", "groningen", "--out", str(tmp_path / "o.json")]
    monkeypatch.setattr(sys, "argv", [*argv, "--local-query-from-evidence"])
    live.main()
    assert seen == [True]


def test_lq2_the_parent_forwards_the_flag(tmp_path, monkeypatch):
    import subprocess
    import sys

    from evaluation.research import live
    from evaluation.research.schema import Observation

    argv = ["live", "--live", "--case", "groningen", "--out", str(tmp_path)]
    monkeypatch.setattr(sys, "argv", [*argv, "--local-query-from-evidence"])
    monkeypatch.setattr(subprocess, "check_output", lambda *args, **kwargs: "synthetic-sha")
    commands = []

    def child(command, **kwargs):
        commands.append(command)
        output = Path(command[command.index("--out") + 1])
        output.write_text(Observation(case_id="groningen").model_dump_json(), encoding="utf-8")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", child)
    live.main()
    assert "--local-query-from-evidence" in commands[0]
