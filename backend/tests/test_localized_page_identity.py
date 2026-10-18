"""Plan v3 rule R1 (LI-2, stage 4(a)): local-language programme page identity.

The eight development gold pages (``PROGRAMME_DISCOVERY_ANALYSIS_2026-10-18.md``
§2.2 and the classifier audit, ticket 10) are hand-fetched copies trimmed into
``fixtures/localized_identity/`` — each file names its source URL. Every other
page here is written for the test, one per language of ``languages.json``, the
heldout countries' languages included (16-Q5); no heldout page, label or
capture was opened. Offline: nothing is fetched.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.adapters import page_classifier
from app.adapters.discovery import live_discovery
from app.adapters.discovery.live_discovery import (
    LiveDiscoveryAdapter,
    degree_level_named,
    local_alternate,
    matches_field_text,
    profile_rejects,
    with_strong_aliases,
)
from app.adapters.extraction import (
    ClaimBuilder,
    extract_requirements,
    for_matching,
    html_title,
    readable_text,
)
from app.adapters.fetching import Fetcher
from app.adapters.page_classifier import PageType, classify_page, degree_level_of
from app.adapters.search.ontology import (
    canonical_field,
    country_languages,
    localized_aliases,
    localized_related_terms,
    retrieval_candidates,
)
from tests.test_deadline_opening_dates import IMPERIAL_DEADLINES
from tests.test_deadline_test_windows import IMPERIAL as IMPERIAL_TMUA
from tests.test_live_discovery import StubSite, sitemap_xml

BACKEND = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).parent / "fixtures" / "localized_identity"
CS = ["computer science"]


@pytest.fixture(params=[False, True], ids=["off", "on"])
def r1(request, monkeypatch) -> bool:
    monkeypatch.setattr(page_classifier, "LOCALIZED_PAGE_IDENTITY", request.param)
    monkeypatch.setattr(page_classifier, "LEXICON_V2", False)
    monkeypatch.setattr(live_discovery, "LOCALIZED_IDENTITY", True)
    return request.param


@pytest.fixture
def r1_on(monkeypatch) -> None:
    monkeypatch.setattr(page_classifier, "LOCALIZED_PAGE_IDENTITY", True)
    monkeypatch.setattr(page_classifier, "LEXICON_V2", False)
    monkeypatch.setattr(live_discovery, "LOCALIZED_IDENTITY", True)


def test_flag_is_on_by_default() -> None:
    assert page_classifier.LOCALIZED_PAGE_IDENTITY is True


# --- 1. the development gold pages -------------------------------------------------

NOT_A_PROGRAMME = "reads as unknown, not a programme page"


def _subject_refused(subject: str) -> str:
    return f"page subject {subject!r} does not match requested fields {CS!r}"


#: (fixture, url, country, verdict off, verdict on, what R1 leaves to R2).
GOLD = [
    (
        "psaclay_fr",
        "https://www.universite-paris-saclay.fr/formation/licence/informatique",
        "France",
        NOT_A_PROGRAMME,
        None,
        "",
    ),
    (
        "uba",
        "https://ingresantes.exactas.uba.ar/licenciatura-en-ciencias-de-la-computacion/",
        "Argentina",
        NOT_A_PROGRAMME,
        None,
        "",
    ),
    (
        "ucph_da",
        "https://www.ku.dk/studier/bachelor/datalogi",
        "Denmark",
        _subject_refused("Bachelor i datalogi"),
        None,
        "",
    ),
    (
        "puc",
        "https://admision.uc.cl/carreras/licenciatura-en-ingenieria-en-ciencia-de-la-computacion/",
        "Chile",
        NOT_A_PROGRAMME,
        None,
        "",
    ),
    (
        "iitd",
        "https://homecse.iitd.ac.in/b-tech-program/",
        "India",
        NOT_A_PROGRAMME,
        None,
        # Accepted on the requested words themselves; 19-Q4 (R2) makes
        # "Computer Science and Engineering" a related programme.
        "R2: related (computer science and engineering)",
    ),
    (
        "uio",
        "https://www.uio.no/studier/program/informatikk-programmering/",
        "Norway",
        _subject_refused("Informatikk: programmering og systemarkitektur"),
        _subject_refused("Informatikk: programmering og systemarkitektur"),
        "R2: subject head before ':'",
    ),
    (
        "kuleuven",
        "https://onderwijsaanbod.kuleuven.be/opleidingen/n/SC_51016742.htm",
        "Belgium",
        _subject_refused("Bachelor in de informatica (Leuven) - Studieprogramma"),
        _subject_refused("Bachelor in de informatica (Leuven) - Studieprogramma"),
        "R2: head before ' - ', domestic place and form word as filler",
    ),
    (
        "ub",
        "http://www.ub.edu/grad/infes/fitxaInfe.jsp?n0=L&n1=0&n2=1&tipus=&curs=2026&ens=TG1148",
        "Spain",
        NOT_A_PROGRAMME,
        NOT_A_PROGRAMME,
        "neither: the page's own text names no programme (a timetable)",
    ),
]


def _gold(name: str) -> str:
    return (FIXTURES / f"{name}.html").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("name", "url", "country", "off", "on", "_rest"), GOLD, ids=[g[0] for g in GOLD]
)
def test_gold_page_verdict(r1, monkeypatch, name, url, country, off, on, _rest) -> None:
    # R1's own verdicts, read under the pre-R2 subject rule; R2 (on by default)
    # accepts uio and kuleuven on their subject heads (test_gold_page_verdict_under_r2).
    monkeypatch.setattr(live_discovery, "SUBJECT_TITLE_SHAPES", False)
    page = classify_page(url=url, html=_gold(name))
    verdict = profile_rejects(page, "bachelor", CS, url=url, country=country)
    assert verdict == (on if r1 else off)
    if r1 and on is None:
        assert page.degree_level == "bachelor"
        assert page.page_type in (PageType.PROGRAM_DETAIL, PageType.INTAKE_SPECIFIC_PROGRAM)


#: R2 (SUBJECT_TITLE_SHAPES, on by default) reads the subject head: "Informatikk"
#: before uio's colon and "informatica" before kuleuven's dash name the field.
R2_ACCEPTS = {"uio", "kuleuven"}


@pytest.mark.parametrize(
    ("name", "url", "country", "_off", "on", "_rest"), GOLD, ids=[g[0] for g in GOLD]
)
def test_gold_page_verdict_under_r2(r1_on, name, url, country, _off, on, _rest) -> None:
    assert live_discovery.SUBJECT_TITLE_SHAPES is True
    page = classify_page(url=url, html=_gold(name))
    verdict = profile_rejects(page, "bachelor", CS, url=url, country=country)
    if name in R2_ACCEPTS:
        assert on is not None
        assert verdict is None
        assert page.degree_level == "bachelor"
    else:
        assert verdict == on


def test_every_fixture_names_its_source() -> None:
    for name, url, *_ in GOLD:
        assert _gold(name).startswith(f"<!-- source: {url} ")


def test_the_french_licence_reads_bachelor_from_the_path_under_its_own_language(r1_on) -> None:
    """The page's body lists the follow-on masters; the title and path place it."""
    url = "https://www.universite-paris-saclay.fr/formation/licence/informatique"
    page = classify_page(url=url, html=_gold("psaclay_fr"))
    assert (page.subject, page.degree_level) == ("Informatique", "bachelor")
    # The same page without its <html lang="fr"> is not read as a licence.
    html = _gold("psaclay_fr").replace('<html lang="fr">', "<html>")
    assert classify_page(url=url, html=html).degree_level is None


# --- 2. degree words in every language: bachelor and master -----------------------

#: (html lang, title, level). Every title is a dictionary rendering of
#: "<degree> in computer science"; nothing comes from a heldout page.
TITLES = [
    ("fr", "Licence Informatique", "bachelor"),
    ("fr", "Master Informatique", "master"),
    ("it", "Laurea triennale in Informatica", "bachelor"),
    ("it", "Corso di laurea in Informatica", "bachelor"),
    ("it", "Laurea magistrale in Informatica", "master"),
    ("it", "Corso di laurea magistrale in Informatica", "master"),
    ("tr", "Bilgisayar Bilimleri Lisans Programı", "bachelor"),
    ("tr", "Bilgisayar Bilimleri Yüksek Lisans Programı", "master"),
    ("tr", "BİLGİSAYAR BİLİMLERİ YÜKSEK LİSANS PROGRAMI", "master"),
    ("cs", "Bakalářský studijní program Informatika", "bachelor"),
    ("cs", "Navazující magisterský studijní program Informatika", "master"),
    ("cs", "Magisterský program Informatika", "master"),
    ("sk", "Bakalársky študijný program Informatika", "bachelor"),
    ("de", "Informatik Bachelorstudiengang", "bachelor"),
    ("de", "Informatik Masterstudiengang", "master"),
    ("de", "Masterstudium Informatik", "master"),
    ("et", "Informaatika bakalaureuseõpe", "bachelor"),
    ("et", "Informaatika magistriõpe", "master"),
    ("lt", "Informatika (bakalauras)", "bachelor"),
    ("lt", "Informatikos magistrantūra", "master"),
    ("es", "Licenciatura en Ciencias de la Computación", "bachelor"),
    ("es", "Grado en Ciencia de la Computación", "bachelor"),
    ("es", "Máster en Ciencia de la Computación", "master"),
    ("es", "Magíster en Ciencias de la Computación", "master"),
    ("es", "Maestría en Ciencias de la Computación", "master"),
    ("pt", "Bacharelado em Ciência da Computação", "bachelor"),
    ("pt", "Graduação em Ciência da Computação", "bachelor"),
    ("pt", "Mestrado em Ciência da Computação", "master"),
    ("pt", "Pós-graduação em Ciência da Computação", "master"),
    ("ca", "Grau en Informàtica", "bachelor"),
    ("ca", "Màster en Informàtica", "master"),
    ("no", "Bachelor i informatikk", "bachelor"),
    ("no", "Masterprogram i informatikk", "master"),
    ("nb", "Kandidat i informatikk", "master"),
    ("da", "Bachelor i datalogi", "bachelor"),
    ("da", "Bacheloruddannelse i datalogi", "bachelor"),
    ("da", "Kandidat i datalogi", "master"),
    ("da", "Kandidatuddannelse i datalogi", "master"),
    ("sv", "Kandidatprogram i datavetenskap", "bachelor"),
    ("sv", "Masterprogram i datavetenskap", "master"),
    ("sv", "Magisterprogram i datavetenskap", "master"),
    ("fi", "Tietojenkäsittelytiede, kandidaatti", "bachelor"),
    ("fi", "Tietojenkäsittelytiede, maisteri", "master"),
    ("nl", "Bacheloropleiding Informatica", "bachelor"),
    ("nl", "Masteropleiding Informatica", "master"),
    ("pl", "Informatyka (licencjat)", "bachelor"),
    ("pl", "Informatyka – studia drugiego stopnia", "master"),
    ("pl", "Informatyka – studia magisterskie", "master"),
    ("ru", "Бакалавриат: Информатика", "bachelor"),
    ("ru", "Магистратура: Информатика", "master"),
    ("kk", "Информатика бакалавриат", "bachelor"),
    ("kk", "Информатика магистратура", "master"),
    ("ja", "情報科学（学士）", "bachelor"),
    ("ja", "情報科学 修士課程", "master"),
    ("ja", "大学院 情報科学専攻", "master"),
    ("zh", "计算机科学与技术（本科）", "bachelor"),
    ("zh", "计算机科学与技术 硕士研究生", "master"),
    ("zh", "計算機科學 碩士班", "master"),
    ("ko", "컴퓨터과학 학사과정", "bachelor"),
    ("ko", "컴퓨터과학 석사과정", "master"),
    ("ko", "대학원 컴퓨터과학과", "master"),
    ("th", "วิทยาการคอมพิวเตอร์ ปริญญาตรี", "bachelor"),
    ("th", "วิทยาการคอมพิวเตอร์ ปริญญาโท", "master"),
]


def _page(lang: str, title: str, body: str = "") -> str:
    return (
        f'<html lang="{lang}"><head><title>{title}</title></head><body><main>'
        f"<h1>{title}</h1><p>{body or 'Studijní plán, 180 ECTS, přijímací řízení.'}</p>"
        "<p>Programme facts: duration, credits, admission and the study plan.</p>"
        "</main></body></html>"
    )


@pytest.mark.parametrize(("lang", "title", "level"), TITLES, ids=[t[1] for t in TITLES])
def test_degree_word_in_each_language(r1_on, lang: str, title: str, level: str) -> None:
    url = "https://www.uni.example/study/programme/one"
    page = classify_page(url=url, html=_page(lang, title))
    assert page.degree_level == level
    assert page.page_type in (PageType.PROGRAM_DETAIL, PageType.INTAKE_SPECIFIC_PROGRAM)
    verdict = profile_rejects(page, "bachelor", CS, url=url)
    if level == "master":
        assert verdict == "page names degree level master, not bachelor"
    else:
        assert verdict is None, f"{title!r}: {verdict}"


@pytest.mark.parametrize(("lang", "title", "level"), TITLES, ids=[t[1] for t in TITLES])
def test_off_no_local_page_is_confirmed_for_a_bachelor(monkeypatch, lang, title, level) -> None:
    """Flag off: the local words name nothing new; a master's page is refused as before."""
    monkeypatch.setattr(page_classifier, "LOCALIZED_PAGE_IDENTITY", False)
    url = "https://www.uni.example/study/programme/one"
    page = classify_page(url=url, html=_page(lang, title))
    if level == "master":
        assert profile_rejects(page, "bachelor", CS, url=url) is not None


@pytest.mark.parametrize(
    ("lang", "text", "level"),
    [
        # A master's compound is never read as its bachelor stem, wherever it is.
        ("it", "Dopo la laurea triennale si prosegue con la laurea magistrale", "bachelor"),
        ("it", "La laurea magistrale segue la laurea triennale", "master"),
        ("tr", "Yüksek lisans programına lisans mezunları başvurabilir", "master"),
        ("pt", "Programas de pós-graduação e cursos de graduação", "master"),
        # Words that are another thing in another language need the page's language.
        ("en", "A driving licence is not required", None),
        ("fr", "La licence informatique dure trois ans", "bachelor"),
        ("nl", "Informatie voor kandidaat-studenten", None),
        ("fi", "Kandidaatin tutkinto", "bachelor"),
        ("sv", "Kandidatexamen i datavetenskap", "bachelor"),
        ("de", "Kandidat", None),
        ("en", "The magistrate's court and a magisterial lecture", None),
        ("es", "Una clase magistral abierta", None),
        ("tr", "Ön lisans programları", None),
        ("tr", "Önlisans ve lisansüstü programlar", None),
        ("ko", "학부모 안내", None),
        ("ko", "전산학부 소개", None),
        ("zh", "信息学部介绍", None),
        ("ja", "理学部", "bachelor"),
    ],
)
def test_earliest_word_and_language_gates(r1_on, lang: str, text: str, level) -> None:
    assert page_classifier._degree_level(text, lang) == level


@pytest.mark.parametrize(
    "text",
    [
        "Licenciatura en Ciencias de la Computación",
        "Laurea in Informatica",
        "Lisans programı",
        "Бакалавриат",
        "本科",
        "Masterstudium",
        "Licence informatique",
    ],
)
def test_off_the_local_words_are_not_degree_words(monkeypatch, text: str) -> None:
    monkeypatch.setattr(page_classifier, "LOCALIZED_PAGE_IDENTITY", False)
    monkeypatch.setattr(page_classifier, "LEXICON_V2", False)
    assert degree_level_of(text) is None
    assert page_classifier._degree_level(text, "fr") is None


ENGLISH_TITLES = [
    ("Bachelor of Science in Computer Science", "bachelor"),
    ("BSc Computing Science", "bachelor"),
    ("MSc Computer Science", "master"),
    ("Master's programme in Computer Science", "master"),
    ("PhD in Computer Science", "phd"),
    ("Mathematics and Computer Science MEng", None),
    ("Undergraduate study in Computer Science", "bachelor"),
]


@pytest.mark.parametrize(("title", "level"), ENGLISH_TITLES)
def test_english_titles_unchanged(monkeypatch, title: str, level) -> None:
    html = _page("en", title, "Entry requirements, tuition fees and how to apply.")
    url = "https://www.uni.example/study/courses/one"
    seen = []
    for flag in (False, True):
        monkeypatch.setattr(page_classifier, "LOCALIZED_PAGE_IDENTITY", flag)
        assert degree_level_of(title) == level
        page = classify_page(url=url, html=html)
        seen.append((page.page_type, page.subject, page.degree_level, page.signals))
    assert seen[0] == seen[1]


# --- 3. LX-1's degree and subject parts are R1's (16-Q4) ---------------------------


def test_lx1_degree_words_and_slugs_under_r1(r1_on) -> None:
    assert degree_level_of("BTech in CSE – Computer Science and Engineering") == "bachelor"
    assert degree_level_of("M.Tech Computer Science") == "master"
    assert degree_level_of("Bachillerato en Ciencias de la Computación") == "bachelor"
    assert degree_level_named("https://homecse.iitd.ac.in/b-tech-program/") == "bachelor"
    assert degree_level_named("https://homecse.iitd.ac.in/m-tech-program/") == "master"


@pytest.mark.parametrize(
    "label",
    [
        "Informatikk",
        "Bachelor i informatikk",
        "Datalogi",
        "Ciencia de la Computación",
        "Licenciatura en Ingeniería en Ciencia de la Computación",
        "Ingeniería en Ciencias de la Computación",
        "Bacharelado em Ciências da Computação",
        "Ciência de Computadores",
        "Bilgisayar Bilimleri Lisans Programı",
        "Informaatika bakalaureuseõpe",
        "Informatika (bakalauras)",
        "Информатика бакалавриат",
        "Компьютерные науки",
        "Tietojenkäsittelytiede",
        "情報科学",
        "情報科学（学士）",
        "计算机科学与技术",
        "计算机科学与技术（本科）",
        "計算機科學",
        "컴퓨터과학 학사과정",
        "전산학",
        "วิทยาการคอมพิวเตอร์ ปริญญาตรี",
    ],
)
def test_localized_aliases_name_computer_science(r1_on, label: str) -> None:
    assert matches_field_text(label, CS), label


@pytest.mark.parametrize(
    "label",
    [
        "Informatikk",
        "Datalogi",
        "Ingeniería en Ciencias de la Computación",
        "Bilgisayar Bilimleri",
        "Informaatika",
        "情報科学（学士）",
        "컴퓨터과학 학사과정",
        "วิทยาการคอมพิวเตอร์ ปริญญาตรี",
    ],
)
def test_off_the_new_aliases_name_nothing(monkeypatch, label: str) -> None:
    monkeypatch.setattr(page_classifier, "LOCALIZED_PAGE_IDENTITY", False)
    monkeypatch.setattr(page_classifier, "LEXICON_V2", False)
    assert not matches_field_text(label, CS)


@pytest.mark.parametrize(
    "label",
    [
        # Neighbours, refused by name (the owner's ruling on computer engineering).
        "Ingeniería Informática",
        "Grado en Ingeniería Informática",
        "Enginyeria Informàtica",
        "Ingegneria Informatica",
        "Laurea in Ingegneria Informatica",
        "Engenharia Informática",
        "Engenharia de Computação",
        "Technische Informatik",
        "Informatique industrielle",
        "Bilgisayar Mühendisliği",
        "BİLGİSAYAR MÜHENDİSLİĞİ",
        "Informatikos inžinerija",
        "计算机工程",
        "컴퓨터공학",
        # Other fields that carry an alias's word, refused as before.
        "Wirtschaftsinformatik",
        "Bioinformatikk",
        "Прикладная математика и информатика",
        "情報科学科",
        "Informatica Umanistica",
        # A master's title is not let through on its subject either.
        "Magistrale Informatica",
    ],
)
def test_neighbours_and_other_fields_are_refused(r1_on, label: str) -> None:
    assert not matches_field_text(label, CS)


def test_a_form_word_left_to_r2_is_refused_without_it(r1_on, monkeypatch) -> None:
    """R1 alone refuses "专业" as a leftover; R2 (on by default) reads it as a form
    word, so the title is the field (test_subject_title_shapes)."""
    assert matches_field_text("计算机科学与技术专业", CS)
    monkeypatch.setattr(live_discovery, "SUBJECT_TITLE_SHAPES", False)
    assert not matches_field_text("计算机科学与技术专业", CS)


def test_related_forms_are_refused_by_name_even_when_an_alias_is_present(r1_on) -> None:
    title = "Licenciatura en Ciencias de la Computación e Ingeniería Informática"
    assert not matches_field_text(title, CS)


def test_new_aliases_are_identity_only_never_settled_or_query_terms(r1) -> None:
    flagged = localized_aliases(
        "computer science", include_flagged=True, flags=frozenset({"LOCALIZED_PAGE_IDENTITY"})
    )
    r1_only = set(flagged) - set(localized_aliases("computer science"))
    assert {"bilgisayar bilimleri", "informaatika", "情報科学", "วิทยาการคอมพิวเตอร์"} <= r1_only
    assert not r1_only & set(localized_aliases("computer science"))
    terms = {candidate.term for candidate in retrieval_candidates("computer science")}
    assert not r1_only & terms
    assert all(canonical_field(alias) is None for alias in r1_only)
    names = {name.lower() for name in with_strong_aliases(CS)}
    assert ({a.lower() for a in r1_only} <= names) is r1
    lx1 = {"informatikk", "datalogi", "ciencia de la computación"}
    assert (lx1 <= names) is r1


def test_related_terms_are_read_only_under_their_flag() -> None:
    assert "ingeniería informática" in localized_related_terms(
        "computer science", flags=frozenset({"LOCALIZED_PAGE_IDENTITY"})
    )
    assert localized_related_terms("computer science", flags=frozenset()) == ()
    assert localized_related_terms("underwater basket weaving", flags=frozenset({"X"})) == ()


# --- 4. the institution's languages and the twin in either direction ---------------


def test_country_languages_from_the_institution_table() -> None:
    assert country_languages("Norway") == ("no", "nb", "nn")
    assert country_languages("türkiye") == ("tr",)
    assert country_languages("Kazakhstan") == ("kk", "ru")
    assert country_languages("United Kingdom") == ()
    assert country_languages("") == ()
    raw = json.loads((BACKEND / "app/adapters/search/languages.json").read_text("utf-8"))
    heldout_languages = {"cs", "de", "tr", "et", "it", "lt", "kk"}
    assert heldout_languages <= {code for codes in raw["countries"].values() for code in codes}


ENGLISH_STUB = "https://www.uni.no/english/studies/programmes/informatics-bachelor"
NORWEGIAN = "https://www.uni.no/studier/program/informatikk-bachelor"


def english_stub(local: str = NORWEGIAN, hreflang: str = "nb") -> str:
    return (
        '<html lang="en"><head><title>Programme information</title>'
        f'<link rel="alternate" hreflang="{hreflang}" href="{local}">'
        "</head><body><main><h1>Programme information</h1><p>This programme is taught in "
        "Norwegian. Read the Norwegian page for admission, structure and credits; the "
        "English page is a summary for visitors.</p></main></body></html>"
    )


def norwegian_page() -> str:
    return (
        '<html lang="nb"><head><title>Bachelor i informatikk – Universitetet</title>'
        f'<link rel="alternate" hreflang="en" href="{ENGLISH_STUB}"></head><body><main>'
        "<h1>Bachelor i informatikk</h1><p>Bachelorprogrammet gir 180 studiepoeng over tre "
        "år. Opptakskrav: generell studiekompetanse og matematikk R1.</p></main></body></html>"
    )


def test_local_alternate_of_an_english_page(r1) -> None:
    found = local_alternate(ENGLISH_STUB, english_stub(), "uni.no", "Norway")
    assert found == (NORWEGIAN if r1 else None)


@pytest.mark.parametrize(
    ("html", "country"),
    [
        (english_stub(), "United Kingdom"),  # no local language
        (english_stub(hreflang="de"), "Norway"),  # not the country's language
        (english_stub(local="https://translate.example.com/uni/informatikk"), "Norway"),
        (norwegian_page(), "Norway"),  # the page is not English
        (english_stub().replace(' lang="en"', ""), "Norway"),  # language not stated
    ],
)
def test_local_alternate_is_not_followed(r1_on, html: str, country: str) -> None:
    assert local_alternate(ENGLISH_STUB, html, "uni.no", country) is None


def _registry(tmp_path, homepage: str, country: str):
    path = tmp_path / "registry.json"
    path.write_text(
        json.dumps([{"name": "U", "country": country, "city": "X", "homepage": homepage}])
    )
    return path


async def _discover(tmp_path, site: StubSite, profile, country: str = "Norway"):
    async with Fetcher(tmp_path / "c", offline=True) as fetcher:
        site.install(fetcher)
        adapter = LiveDiscoveryAdapter(fetcher, _registry(tmp_path, "https://www.uni.no/", country))
        candidate = (await adapter.discover(profile))[0]
    return candidate, adapter.traces[0]


def _norwegian_site() -> StubSite:
    return StubSite(
        {
            "https://www.uni.no/robots.txt": "Sitemap: https://www.uni.no/s.xml\n",
            "https://www.uni.no/s.xml": sitemap_xml(ENGLISH_STUB),
            ENGLISH_STUB: english_stub(),
            NORWEGIAN: norwegian_page(),
        }
    )


@pytest.mark.asyncio
async def test_a_refused_english_page_has_its_local_twin_read_and_confirmed(
    tmp_path, r1, profile
) -> None:
    site = _norwegian_site()
    candidate, trace = await _discover(tmp_path, site, profile)
    assert ENGLISH_STUB in site.requested
    urls = [p.url for p in candidate.programs]
    if r1:
        assert site.requested.index(NORWEGIAN) == site.requested.index(ENGLISH_STUB) + 1
        assert site.requested.count(NORWEGIAN) == 1
        assert NORWEGIAN in urls
        assert f"hreflang: reading the local alternate of {ENGLISH_STUB}" in trace.errors
    else:
        assert NORWEGIAN not in site.requested
        assert urls == []


@pytest.mark.asyncio
async def test_no_local_twin_for_an_institution_in_an_english_speaking_country(
    tmp_path, r1_on, profile
) -> None:
    site = _norwegian_site()
    await _discover(tmp_path, site, profile, country="United Kingdom")
    assert NORWEGIAN not in site.requested


# --- 5. LX-1's wrong Imperial deadline: the cause and the guard (16-Q4) -------------
#
# LX-1's paired run (39086520685 / 39086522101 / 39086523553) claimed Imperial
# deadlines 2026-04-28 and 2026-09-28 on its on arm only (runs/2026-10-17
# LOOP_REPORT "Cycle 3g"). Both arms read the same pages; only the on arm
# confirmed /2027/mathematics-computer-science-{meng,beng}: LX-1 part (ii), the
# funding gate on the page identity, stopped those course pages (h2 "Fees and
# funding") reading as funding pages. With a programme confirmed, the evidence
# stage read 2026-09-28 from the course page's TMUA "Booking closes" line and
# 2026-04-28 from the deadlines page's "28 April 2026 – UCAS' search tool
# opens". R1 carries none of part (ii) (that is FI-1, its own flag), changes
# no English classification, and both readings are fixed in extraction.

IMPERIAL_COURSE = (
    "<html lang='en'><head><title>Mathematics and Computer Science BEng | Study | Imperial "
    "College London</title></head><body><main><h1>Mathematics and Computer Science</h1>"
    "<p>Undergraduate BEng Mathematics and Computer Science. Develop powerful logical "
    "thinking and technical problem-solving skills.</p><h2>Entry requirements</h2>"
    "<p>Our minimum entry standard is A*A*A overall.</p><h2>Fees and funding</h2>"
    "<p>Home and overseas tuition fees for 2027 entry.</p></main></body></html>"
)
IMPERIAL_COURSE_URL = (
    "https://www.imperial.ac.uk/study/courses/undergraduate/2027/mathematics-computer-science-beng"
)


def _summary(url: str, html: str) -> tuple[object, ...]:
    page = classify_page(url=url, html=html)
    return (page.page_type, page.subject, page.degree_level, page.signals)


def test_r1_does_not_carry_lx1s_funding_gate(monkeypatch) -> None:
    monkeypatch.setattr(page_classifier, "FUNDING_IDENTITY_SCOPE", False)
    monkeypatch.setattr(page_classifier, "LEXICON_V2", False)
    monkeypatch.setattr(page_classifier, "LOCALIZED_PAGE_IDENTITY", False)
    heading_wide = _summary(IMPERIAL_COURSE_URL, IMPERIAL_COURSE)
    assert heading_wide[0] is not PageType.PROGRAM_DETAIL  # read as a funding page

    monkeypatch.setattr(page_classifier, "LOCALIZED_PAGE_IDENTITY", True)
    assert _summary(IMPERIAL_COURSE_URL, IMPERIAL_COURSE) == heading_wide

    # LX-1 itself flips the same page into a programme page: that is the path
    # its wrong deadlines came through, and R1 does not take it.
    monkeypatch.setattr(page_classifier, "LOCALIZED_PAGE_IDENTITY", False)
    monkeypatch.setattr(page_classifier, "LEXICON_V2", True)
    assert _summary(IMPERIAL_COURSE_URL, IMPERIAL_COURSE)[0] is PageType.PROGRAM_DETAIL


IMPERIAL_DEADLINES_URL = "https://www.imperial.ac.uk/study/apply/undergraduate/process/deadlines/"


def _deadlines(text: str) -> list[str]:
    builder = ClaimBuilder(
        source_url="fixture://imperial", accessed_at=datetime(2026, 10, 18, tzinfo=UTC)
    )
    extract_requirements(text, builder)
    return [
        str(c.normalized_value)
        for c in builder.claims
        if c.claim_type.value == "admission_deadline"
    ]


def test_r1_does_not_reintroduce_the_imperial_deadlines(r1) -> None:
    html = _gold("imperial_deadlines")
    assert html.startswith(f"<!-- source: {IMPERIAL_DEADLINES_URL} ")
    text = readable_text(html)
    assert "28 April 2026" in text
    assert _deadlines(text) == []
    assert "2026-04-28" not in _deadlines(for_matching(IMPERIAL_DEADLINES))
    assert _deadlines(IMPERIAL_TMUA) == ["2027-01-13"]
    assert html_title(html)


def test_english_imperial_pages_classify_the_same_with_r1(monkeypatch) -> None:
    pages = [
        (IMPERIAL_COURSE_URL, IMPERIAL_COURSE),
        (IMPERIAL_COURSE_URL.replace("-beng", "-meng"), IMPERIAL_COURSE.replace("BEng", "MEng")),
        (IMPERIAL_DEADLINES_URL, _gold("imperial_deadlines")),
    ]
    monkeypatch.setattr(page_classifier, "LOCALIZED_PAGE_IDENTITY", False)
    off = [_summary(url, html) for url, html in pages]
    off_verdicts = [
        profile_rejects(classify_page(url=u, html=h), "bachelor", CS, url=u, country="UK")
        for u, h in pages
    ]
    monkeypatch.setattr(page_classifier, "LOCALIZED_PAGE_IDENTITY", True)
    assert [_summary(url, html) for url, html in pages] == off
    assert [
        profile_rejects(classify_page(url=u, html=h), "bachelor", CS, url=u, country="UK")
        for u, h in pages
    ] == off_verdicts
    # The integrated master's is still refused for a bachelor request (IM-1).
    assert off_verdicts[1] is not None


# --- harness flag --------------------------------------------------------------------


def test_harness_exposes_and_forwards_the_flag() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "evaluation.research.live", "--help"],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "--localized-page-identity" in result.stdout
    source = (BACKEND / "evaluation/research/live.py").read_text(encoding="utf-8")
    assert "r1_module.LOCALIZED_PAGE_IDENTITY = True" in source
    assert '["--localized-page-identity"]' in source
