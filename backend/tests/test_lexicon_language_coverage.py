"""LV-1: the lexicon battery (NEXT_CYCLES_2026-10-20 §LV-1; generalisation ticket 16, item 2).

Every language-keyed table of discovery and the page classifier is asked, for
every language ``languages.json`` names, whether it has a row; then one
synthetic programme page per language goes through the confirm stage
(``classify_page`` + ``profile_rejects``): the bachelor's is accepted for a
bachelor applicant, the master's is refused for its level, and an integrated
master's — where the language's degree law has one — never reads as a
bachelor's (IM-1: an integrated master's is a master's).

Every word below comes from a dictionary or a degree law, cited per row in
``DICTIONARY``; none comes from a page, so the battery says nothing about any
site and reaches languages no development case speaks (sk, and ca whose only
case is unreadable). No page is fetched; no heldout file, capture, log or label
was opened.

The rows the battery found missing for a language a development set speaks are
behind ``page_classifier.LEXICON_LANGUAGE_COVERAGE`` (off); the battery runs
with it on, and the flag-off tests pin what it changes.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import pytest

from app.adapters import page_classifier
from app.adapters.discovery import live_discovery
from app.adapters.discovery.live_discovery import degree_level_named, profile_rejects
from app.adapters.page_classifier import PageType, classify_page
from app.adapters.search.ontology import localized_aliases, localized_aliases_in

LANGUAGES_JSON = (
    Path(__file__).resolve().parents[1] / "app" / "adapters" / "search" / "languages.json"
)
CS = ["computer science"]


def _languages() -> dict[str, tuple[str, str]]:
    """Each language of ``languages.json`` → (a country publishing in it, its region).

    The first country that lists it first (Swedish is Sweden's, not Finland's),
    else the first that lists it at all (Catalan, Spain).
    """
    data = json.loads(LANGUAGES_JSON.read_text(encoding="utf-8"))
    out: dict[str, tuple[str, str]] = {}
    for primary_only in (True, False):
        for country, languages in data["countries"].items():
            for language in languages[:1] if primary_only else languages:
                out.setdefault(language, (country, data["regions"][country]))
    return out


LANGUAGES = _languages()


@dataclass(frozen=True)
class Row:
    """One language's dictionary words for a computer-science programme page."""

    alias: str
    #: The page title; ``{}`` is the alias.
    bachelor: str
    bachelor_slug: str
    master: str
    master_slug: str
    #: The integrated master's, where the language's degree law names one.
    integrated: str | None
    integrated_slug: str | None
    source: str


#: ja/zh/ko/th sites write their URL slugs in English, so their slug is the
#: English one ``_DEGREE_SLUGS`` reads; every other slug is the dictionary
#: word, accents folded, as a site writes it.
DICTIONARY: dict[str, Row] = {
    "ca": Row(
        "Informàtica",
        "Grau en {}",
        "grau-en-informatica",
        "Màster en {}",
        "master-en-informatica",
        None,
        None,
        "DIEC2 (IEC) s.v. grau, màster; Reial Decret 822/2021 art. 14 (Graduat en …)",
    ),
    "cs": Row(
        "Informatika",
        "{} — Bakalářský studijní program",
        "bakalarsky-studijni-program-informatika",
        "{} — Navazující magisterský studijní program",
        "navazujici-magistersky-program-informatika",
        None,
        None,
        "Act No. 111/1998 Coll. §45-§46 (bakalářský, navazující magisterský)",
    ),
    "da": Row(
        "Datalogi",
        "{} — Bacheloruddannelse",
        "bacheloruddannelse-datalogi",
        "{} — Kandidatuddannelse",
        "kandidatuddannelse-datalogi",
        None,
        None,
        "Den Danske Ordbog s.v. bacheloruddannelse, kandidatuddannelse",
    ),
    "de": Row(
        "Informatik",
        "{} — Bachelor of Science",
        "bachelor-informatik",
        "{} — Master of Science",
        "master-informatik",
        None,
        None,
        "KMK, Ländergemeinsame Strukturvorgaben (Bachelor, Master)",
    ),
    "es": Row(
        "Ciencias de la Computación",
        "Licenciatura en {}",
        "licenciatura-ciencias-de-la-computacion",
        "Maestría en {}",
        "maestria-ciencias-de-la-computacion",
        None,
        None,
        "RAE, DLE s.v. licenciatura, maestría",
    ),
    "et": Row(
        "Informaatika",
        "{} — Bakalaureuseõpe",
        "bakalaureuseope-informaatika",
        "{} — Magistriõpe",
        "magistriope-informaatika",
        "{} — Bakalaureuse- ja magistriõppe integreeritud õpe",
        "integreeritud-ope-informaatika",
        "Kõrgharidusseadus, RT I 2019 (bakalaureuseõpe, magistriõpe, integreeritud õpe)",
    ),
    "fi": Row(
        "Tietojenkäsittelytiede",
        "{} — Kandidaatin tutkinto",
        "kandidaatin-tutkinto-tietojenkasittelytiede",
        "{} — Maisterin tutkinto",
        "maisterin-tutkinto-tietojenkasittelytiede",
        None,
        None,
        "Government Decree on University Degrees 794/2004 (kandidaatin, maisterin tutkinto)",
    ),
    "fr": Row(
        "Informatique",
        "Licence {}",
        "licence-informatique",
        "Master {}",
        "master-informatique",
        None,
        None,
        "Code de l'éducation art. D612-32-2 (licence, master)",
    ),
    "it": Row(
        "Informatica",
        "{} — Laurea triennale",
        "laurea-informatica",
        "{} — Laurea magistrale",
        "laurea-magistrale-informatica",
        "{} — Laurea magistrale a ciclo unico",
        "laurea-magistrale-ciclo-unico-informatica",
        "DM 270/2004 art. 3 (laurea, laurea magistrale, a ciclo unico)",
    ),
    "ja": Row(
        "情報科学",
        "{} 学士課程",
        "bachelor-information-science",
        "{} 修士課程",
        "master-information-science",
        None,
        None,
        "Kōjien s.v. 学士, 修士",
    ),
    "kk": Row(
        "Информатика",
        "{} — Бакалавриат",
        "bakalavriat-informatika",
        "{} — Магистратура",
        "magistratura-informatika",
        None,
        None,
        "Law of the Republic of Kazakhstan On Education, art. 36 (бакалавриат, магистратура)",
    ),
    "ko": Row(
        "컴퓨터과학",
        "{} 학사과정",
        "bachelor-computer-science",
        "{} 석사과정",
        "master-computer-science",
        None,
        None,
        "Standard Korean Language Dictionary (NIKL) s.v. 학사, 석사",
    ),
    "lt": Row(
        "Informatika",
        "{} — Bakalauro studijos",
        "bakalauras-informatika",
        "{} — Magistro studijos",
        "magistras-informatika",
        "{} — Vientisosios studijos",
        "vientisosios-studijos-informatika",
        "Law on Higher Education and Research art. 47 (bakalauras, magistras, vientisosios)",
    ),
    "nb": Row(
        "Informatikk",
        "Bachelor i {}",
        "bachelor-informatikk",
        "Master i {}",
        "master-informatikk",
        "Integrert master i {}",
        "integrert-master-informatikk",
        "Bokmålsordboka s.v. informatikk, bachelor, master; Forskrift om grader (integrert)",
    ),
    "nl": Row(
        "Informatica",
        "{} — Bacheloropleiding",
        "bacheloropleiding-informatica",
        "{} — Masteropleiding",
        "masteropleiding-informatica",
        None,
        None,
        "Van Dale s.v. bacheloropleiding, masteropleiding",
    ),
    "nn": Row(
        "Informatikk",
        "Bachelor i {}",
        "bachelor-informatikk",
        "Master i {}",
        "master-informatikk",
        "Integrert master i {}",
        "integrert-master-informatikk",
        "Nynorskordboka s.v. informatikk, bachelor, master; Forskrift om grader (integrert)",
    ),
    "no": Row(
        "Informatikk",
        "Bachelor i {}",
        "bachelor-informatikk",
        "Master i {}",
        "master-informatikk",
        "Integrert master i {}",
        "integrert-master-informatikk",
        "Bokmålsordboka s.v. informatikk, bachelor, master; Forskrift om grader (integrert)",
    ),
    "pl": Row(
        "Informatyka",
        "{} — Studia pierwszego stopnia",
        "studia-pierwszego-stopnia-informatyka",
        "{} — Studia drugiego stopnia",
        "studia-drugiego-stopnia-informatyka",
        "{} — Jednolite studia magisterskie",
        "jednolite-studia-magisterskie-informatyka",
        "Act of 20 July 2018 art. 64 (pierwszego, drugiego stopnia, jednolite magisterskie)",
    ),
    "pt": Row(
        "Ciência da Computação",
        "Bacharelado em {}",
        "bacharelado-ciencia-da-computacao",
        "Mestrado em {}",
        "mestrado-ciencia-da-computacao",
        "Mestrado Integrado em {}",
        "mestrado-integrado-ciencia-da-computacao",
        "Houaiss s.v. bacharelado, mestrado; Decreto-Lei 74/2006 art. 19 (mestrado integrado)",
    ),
    "ru": Row(
        "Информатика",
        "{} — Бакалавриат",
        "bakalavriat-informatika",
        "{} — Магистратура",
        "magistratura-informatika",
        "{} — Специалитет",
        "specialitet-informatika",
        "Federal Law 273-FZ art. 10 (бакалавриат, специалитет, магистратура)",
    ),
    "sk": Row(
        "Informatika",
        "{} — Bakalársky študijný program",
        "bakalarsky-studijny-program-informatika",
        "{} — Inžiniersky študijný program",
        "inziniersky-studijny-program-informatika",
        None,
        None,
        "Act No. 131/2002 Coll. §52-§53 (bakalársky; magisterský, inžiniersky)",
    ),
    "sv": Row(
        "Datavetenskap",
        "Kandidatprogram i {}",
        "kandidatprogram-datavetenskap",
        "Masterprogram i {}",
        "masterprogram-datavetenskap",
        "Civilingenjörsprogram i {}",
        "civilingenjorsprogram-datavetenskap",
        "Högskoleförordningen (1993:100) bilaga 2 (kandidat-, master-, civilingenjörsexamen)",
    ),
    "th": Row(
        "วิทยาการคอมพิวเตอร์",
        "{} ปริญญาตรี",
        "bachelor-computer-science",
        "{} ปริญญาโท",
        "master-computer-science",
        None,
        None,
        "Royal Institute Dictionary s.v. ปริญญาตรี, ปริญญาโท",
    ),
    "tr": Row(
        "Bilgisayar Bilimleri",
        "{} Lisans Programı",
        "lisans-bilgisayar-bilimleri",
        "{} Yüksek Lisans Programı",
        "yuksek-lisans-bilgisayar-bilimleri",
        None,
        None,
        "TDK Güncel Türkçe Sözlük s.v. lisans, yüksek lisans",
    ),
    "zh": Row(
        "计算机科学",
        "{} 本科",
        "undergraduate-computer-science",
        "{} 硕士",
        "master-computer-science",
        None,
        None,
        "Xiandai Hanyu Cidian s.v. 本科, 硕士",
    ),
}


@pytest.fixture
def lv1(monkeypatch: pytest.MonkeyPatch) -> None:
    """The defaults in force, with LV-1's rows on."""
    monkeypatch.setattr(page_classifier, "LEXICON_LANGUAGE_COVERAGE", True)
    monkeypatch.setattr(page_classifier, "LOCALIZED_PAGE_IDENTITY", True)
    monkeypatch.setattr(live_discovery, "LOCALIZED_IDENTITY", True)


def test_the_dictionary_covers_exactly_the_languages_of_languages_json() -> None:
    assert set(DICTIONARY) == set(LANGUAGES)


LANGUAGE_KEYED_TABLES: dict[str, Mapping[str, object]] = {
    "live_discovery._UNIT_WORDS": live_discovery._UNIT_WORDS,
    "live_discovery._SUBPAGE_YEAR_WORDS": live_discovery._SUBPAGE_YEAR_WORDS,
    "live_discovery._SUBPAGE_PROCESS_WORDS": live_discovery._SUBPAGE_PROCESS_WORDS,
    "page_classifier._DEGREE_FIELD_LABELS": page_classifier._DEGREE_FIELD_LABELS,
    "page_classifier._LOCAL_BACHELOR_QUERY_WORDS": page_classifier._LOCAL_BACHELOR_QUERY_WORDS,
}


@pytest.mark.parametrize("table", sorted(LANGUAGE_KEYED_TABLES))
def test_every_language_keyed_table_has_a_row_for_every_language(table: str) -> None:
    rows = LANGUAGE_KEYED_TABLES[table]
    assert sorted(lang for lang in LANGUAGES if not rows.get(lang)) == []
    # No row for a language the institutions' countries do not publish in.
    assert set(rows) - {"en"} <= set(LANGUAGES)


@pytest.mark.usefixtures("lv1")
@pytest.mark.parametrize("lang", sorted(LANGUAGES))
def test_each_language_has_a_query_word_and_an_alias(lang: str) -> None:
    flags = page_classifier.localized_alias_flags()
    aliases = localized_aliases_in("computer science", lang, flags=flags)
    assert DICTIONARY[lang].alias.lower() in aliases
    # R5's word is handed out only when R1's table reads it as a bachelor's.
    assert page_classifier.local_bachelor_word(lang) is not None


@pytest.mark.usefixtures("lv1")
@pytest.mark.parametrize("lang", sorted(LANGUAGES))
def test_each_language_reads_its_level_words_in_text_and_slug(lang: str) -> None:
    row = DICTIONARY[lang]
    for title, slug, level in (
        (row.bachelor, row.bachelor_slug, "bachelor"),
        (row.master, row.master_slug, "master"),
    ):
        text = title.format(row.alias)
        assert page_classifier._degree_level(text, lang) == level, text
        assert level in page_classifier.degree_levels_named(text), text
        url = _url(lang, slug)
        assert degree_level_named(url) == level, url


def _url(lang: str, slug: str) -> str:
    _country, region = LANGUAGES[lang]
    return f"https://www.uni.{region}/study/{slug}"


def _page(lang: str, title: str) -> str:
    return (
        f'<html lang="{lang}"><head><title>{title}</title></head><body><main>'
        f"<h1>{title}</h1><p>180 ECTS.</p>"
        "<p>Programme facts: duration, credits, admission and the study plan.</p>"
        "</main></body></html>"
    )


def _confirm(lang: str, title: str, slug: str) -> tuple[str | None, str | None]:
    """The page's level and the confirm stage's verdict for a bachelor applicant."""
    country, _region = LANGUAGES[lang]
    url = _url(lang, slug)
    page = classify_page(url=url, html=_page(lang, title))
    return page.degree_level, profile_rejects(page, "bachelor", CS, url=url, country=country)


@pytest.mark.usefixtures("lv1")
@pytest.mark.parametrize("lang", sorted(LANGUAGES))
def test_confirm_accepts_the_bachelors_page(lang: str) -> None:
    row = DICTIONARY[lang]
    country, _region = LANGUAGES[lang]
    url = _url(lang, row.bachelor_slug)
    page = classify_page(url=url, html=_page(lang, row.bachelor.format(row.alias)))
    assert page.page_type is PageType.PROGRAM_DETAIL
    assert page.degree_level == "bachelor"
    assert profile_rejects(page, "bachelor", CS, url=url, country=country) is None


@pytest.mark.usefixtures("lv1")
@pytest.mark.parametrize("lang", sorted(LANGUAGES))
def test_confirm_refuses_the_masters_page_for_its_level(lang: str) -> None:
    row = DICTIONARY[lang]
    level, verdict = _confirm(lang, row.master.format(row.alias), row.master_slug)
    assert level == "master"
    assert verdict == "page names degree level master, not bachelor"


INTEGRATED = sorted(lang for lang, row in DICTIONARY.items() if row.integrated)


@pytest.mark.usefixtures("lv1")
@pytest.mark.parametrize("lang", INTEGRATED)
def test_an_integrated_masters_never_reads_as_a_bachelors(lang: str) -> None:
    """IM-1: a master's, or no level at all (ticket 16: unset is fine); never a bachelor's."""
    row = DICTIONARY[lang]
    assert row.integrated is not None and row.integrated_slug is not None
    level, verdict = _confirm(lang, row.integrated.format(row.alias), row.integrated_slug)
    assert level in ("master", None)
    assert verdict is not None
    assert degree_level_named(_url(lang, row.integrated_slug)) in ("master", None)


#: Integrated master's names no table reads as a level today: the page is
#: refused as no programme page at all, which is fine (ticket 16 item 2).
UNSET_INTEGRATED = {"lt", "ru", "sv"}


@pytest.mark.usefixtures("lv1")
@pytest.mark.parametrize("lang", INTEGRATED)
def test_integrated_masters_read_as_master_where_a_table_names_them(lang: str) -> None:
    row = DICTIONARY[lang]
    assert row.integrated is not None and row.integrated_slug is not None
    level, _verdict = _confirm(lang, row.integrated.format(row.alias), row.integrated_slug)
    assert level == (None if lang in UNSET_INTEGRATED else "master")


# --- the flag off: what LV-1's rows change ----------------------------------


@pytest.fixture
def lv1_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(page_classifier, "LEXICON_LANGUAGE_COVERAGE", False)
    monkeypatch.setattr(page_classifier, "LOCALIZED_PAGE_IDENTITY", True)
    monkeypatch.setattr(live_discovery, "LOCALIZED_IDENTITY", True)


def test_lv1_is_off_by_default() -> None:
    assert page_classifier.LEXICON_LANGUAGE_COVERAGE is False


@pytest.mark.usefixtures("lv1_off")
def test_off_the_estonian_integrated_study_is_confirmed_as_a_bachelors() -> None:
    """The battery's one wrong level read (H-D, level dimension): pinned while the flag is off."""
    row = DICTIONARY["et"]
    assert row.integrated is not None
    level, verdict = _confirm("et", row.integrated.format(row.alias), "informaatika")
    assert (level, verdict) == ("bachelor", None)


@pytest.mark.usefixtures("lv1_off")
def test_off_a_japanese_head_writing_gakushi_katei_names_no_subject() -> None:
    row = DICTIONARY["ja"]
    level, verdict = _confirm("ja", row.bachelor.format(row.alias), row.bachelor_slug)
    assert level == "bachelor"
    assert verdict is not None and "does not match requested fields" in verdict


@pytest.mark.usefixtures("lv1_off")
def test_off_no_bokmal_or_nynorsk_alias_and_page_aliases_unchanged() -> None:
    flags = page_classifier.localized_alias_flags()
    assert "LEXICON_LANGUAGE_COVERAGE" not in flags
    assert localized_aliases_in("computer science", "nb", flags=flags) == ()
    assert localized_aliases_in("computer science", "nn", flags=flags) == ()
    # On or off, the page-side alias set is the same: "informatikk" is Norwegian's already.
    off = localized_aliases("computer science", include_flagged=True, flags=flags)
    on = localized_aliases(
        "computer science",
        include_flagged=True,
        flags=flags | {"LEXICON_LANGUAGE_COVERAGE"},
    )
    assert off == on


SLUGS_BEHIND_THE_FLAG = [
    ("fi", "kandidaatin-tutkinto-tietojenkasittelytiede", "bachelor"),
    ("fi", "maisterin-tutkinto-tietojenkasittelytiede", "master"),
    ("pl", "studia-pierwszego-stopnia-informatyka", "bachelor"),
    ("pl", "studia-drugiego-stopnia-informatyka", "master"),
    ("pt", "bacharelado-ciencia-da-computacao", "bachelor"),
    ("es", "maestria-ciencias-de-la-computacion", "master"),
    ("da", "kandidatuddannelse-datalogi", "master"),
    ("nl", "bacheloropleiding-informatica", "bachelor"),
    ("nl", "masteropleiding-informatica", "master"),
    ("sv", "masterprogram-datavetenskap", "master"),
    ("et", "integreeritud-ope-informaatika", "master"),
]


@pytest.mark.parametrize(("lang", "slug", "level"), SLUGS_BEHIND_THE_FLAG)
def test_off_the_flagged_slugs_read_no_level(
    monkeypatch: pytest.MonkeyPatch, lang: str, slug: str, level: str
) -> None:
    monkeypatch.setattr(page_classifier, "LEXICON_LANGUAGE_COVERAGE", False)
    assert degree_level_named(_url(lang, slug)) is None
    monkeypatch.setattr(page_classifier, "LEXICON_LANGUAGE_COVERAGE", True)
    assert degree_level_named(_url(lang, slug)) == level


@pytest.mark.parametrize(
    "url",
    [
        # Words the flagged slugs must not take: Dutch "kandidaat-studenten"
        # (prospective students), a bare "grau" (German "grey").
        "https://www.uni.nl/kandidaat-studenten",
        "https://www.uni.de/grau",
        # Polish "inżynierskie" is a first cycle, never Slovak "inžiniersky".
        "https://www.uni.pl/studia-inzynierskie-informatyka",
    ],
)
def test_flagged_slugs_keep_their_neighbours_apart(monkeypatch, url: str) -> None:
    monkeypatch.setattr(page_classifier, "LEXICON_LANGUAGE_COVERAGE", True)
    assert degree_level_named(url) in (None, "bachelor")
    assert degree_level_named(url) != "master"


def test_unflagged_rows_for_languages_no_development_set_speaks() -> None:
    """ca and sk: in the tables with the flag off (no dev case reads them)."""
    assert page_classifier.LEXICON_LANGUAGE_COVERAGE is False
    assert page_classifier.local_bachelor_word("ca") == "grau en"
    assert degree_level_named(_url("ca", "grau-en-informatica")) == "bachelor"
    assert degree_level_named(_url("sk", "inziniersky-studijny-program-informatika")) == "master"
    assert page_classifier._degree_level("Inžiniersky študijný program", "sk") == "master"
    # Slovak's word under another page language reads nothing.
    assert page_classifier._degree_level("Inžiniersky študijný program", "cs") is None


@pytest.mark.parametrize(
    "url",
    [
        "https://www.uni.example/study/computer-science-bsc",
        "https://www.uni.example/study/computer-science-msc",
        "https://www.uni.example/undergraduate/computing-meng",
        "https://www.uni.example/news/2026/open-day",
    ],
)
def test_english_slugs_read_the_same_on_and_off(monkeypatch, url: str) -> None:
    monkeypatch.setattr(page_classifier, "LEXICON_LANGUAGE_COVERAGE", False)
    off = degree_level_named(url)
    monkeypatch.setattr(page_classifier, "LEXICON_LANGUAGE_COVERAGE", True)
    assert degree_level_named(url) == off
