"""Plan rule LX-1: degree words, funding-gate scope, localized aliases, PG-1 words.

Shapes from the dev3 discovery analysis of 2026-10-18 (§1, §3 fix C). The page
fixtures keep only the title and headings the four pages published (IIT Delhi's
B.Tech page, Auckland's computer science undergraduate page, PUC's
licenciatura page, UiO's informatikk bachelor); every body sentence is
written for the test. Offline: nothing is fetched.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from app.adapters import page_classifier
from app.adapters.discovery import live_discovery
from app.adapters.discovery.live_discovery import (
    degree_level_named,
    is_excluded_path,
    matches_field_text,
    profile_rejects,
    with_strong_aliases,
)
from app.adapters.page_classifier import PageType, classify_page, classify_url, degree_level_of
from app.adapters.search.ontology import canonical_field, localized_aliases, retrieval_candidates
from app.adapters.search.prefilter import is_archive_page

BACKEND = Path(__file__).resolve().parents[1]

IITD_URL = "https://homecse.iitd.ac.in/b-tech-program/"
IITD_HTML = (
    "<html><head><title>BTech in CSE – Computer Science and Engineering</title></head>"
    "<body><main><h1>BTech in CSE – Computer Science and Engineering</h1><h2>B.Tech</h2>"
    "<p>The four-year undergraduate programme admits students through the joint "
    "entrance examination. Students take core courses in algorithms, systems and "
    "theory, followed by electives and a project in the final year.</p>"
    "<h2>Strong Undergraduate Program</h2><p>Small classes and close faculty contact.</p>"
    "</main></body></html>"
)

AUCKLAND_URL = (
    "https://www.auckland.ac.nz/en/science/study-with-us/computer-science/undergraduate.html"
)
AUCKLAND_HTML = (
    "<html><head><title>Undergraduate study in Computer Science – University of Auckland"
    "</title></head><body><main><h1>Undergraduate study in Computer Science</h1>"
    "<h2>What can you study in Computer Science?</h2><p>Computer Science is a major of the "
    "Bachelor of Science. You learn programming, algorithms, software and the theory "
    "behind them, and you can combine it with a second major.</p>"
    "<h2>Structuring your programme</h2><p>Plan your courses across three years.</p>"
    "<h2>Scholarships and awards</h2><p>See <a href='/en/study/scholarships.html'>"
    "Scholarships</a> for what you could apply for.</p>"
    "<h2>Help and advice</h2><p>Contact the student hub.</p></main></body></html>"
)

PUC_URL = "https://admision.uc.cl/carreras/licenciatura-en-ingenieria-en-ciencia-de-la-computacion/"
PUC_HTML = (
    "<html><head><title>Licenciatura en Ingeniería en Ciencia de la Computación - Admisión y "
    "Vinculación Escolar</title></head><body><main>"
    "<h1>Licenciatura en Ingeniería en Ciencia de la Computación</h1>"
    "<h2>Requisitos y Ponderaciones</h2><p>La carrera dura cinco años y forma ingenieros "
    "en ciencia de la computación. Los postulantes rinden la prueba de acceso y se "
    "ponderan sus puntajes según la tabla publicada.</p></main></body></html>"
)

UIO_URL = "https://www.uio.no/studier/program/informatikk-programmering/"
UIO_HTML = (
    '<html lang="no"><head><title>Informatikk: programmering og systemarkitektur (bachelor) – '
    "Universitetet i Oslo</title></head><body><main>"
    "<h1>Informatikk: programmering og systemarkitektur</h1><p>Bachelorprogrammet varer "
    "i tre år og gir 180 studiepoeng. Du lærer programmering, algoritmer og hvordan "
    "datamaskiner og nettverk er bygget opp.</p><h2>Programmet tilbys av</h2>"
    "<p>Institutt for informatikk.</p></main></body></html>"
)


@pytest.fixture(params=[False, True], ids=["off", "on"])
def lexicon(request, monkeypatch) -> bool:
    monkeypatch.setattr(page_classifier, "LEXICON_V2", request.param)
    return request.param


def test_flag_is_off_by_default() -> None:
    assert page_classifier.LEXICON_V2 is False


# --- 1. degree words -----------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "level"),
    [
        ("BTech in CSE – Computer Science and Engineering", "bachelor"),
        ("B.Tech", "bachelor"),
        ("B. Tech in Computer Science", "bachelor"),
        ("M.Tech in Computer Science", "master"),
        ("Licenciatura en Ingeniería en Ciencia de la Computación", "bachelor"),
        ("Grado en Ingeniería Informática", "bachelor"),
        ("Bachillerato en Ciencias de la Computación", "bachelor"),
        ("Bachelorprogram i informatikk", "bachelor"),
        ("Bachelorstudium Informatik", "bachelor"),
        ("Bachelorstudiengang Informatik", "bachelor"),
        ("Bacheloropleiding Informatica", "bachelor"),
    ],
)
def test_local_and_indian_degree_words(lexicon: bool, text: str, level: str) -> None:
    assert degree_level_of(text) == (level if lexicon else None)


@pytest.mark.parametrize(
    "text",
    [
        "Bachelor of Technology in Computer Science",
        "Bachelor's programme in Computer Science",
        "Bachelor’s Programme in Computer Science",
    ],
)
def test_english_bachelor_titles_unchanged(lexicon: bool, text: str) -> None:
    assert degree_level_of(text) == "bachelor"


@pytest.mark.parametrize(
    "text",
    [
        # The Spanish school-leaving qualification is not a university bachelor.
        "Título de Bachillerato o equivalente",
        # "grado" alone is any degree.
        "Requisitos de grado",
        "Before you be admitted",
    ],
)
def test_words_that_are_not_a_bachelor(lexicon: bool, text: str) -> None:
    assert degree_level_of(text) is None


def test_iit_delhi_btech_page_is_a_bachelor_programme_page(lexicon: bool) -> None:
    page = classify_page(url=IITD_URL, html=IITD_HTML)
    if not lexicon:
        assert page.page_type is PageType.UNKNOWN
        return
    assert page.page_type is PageType.PROGRAM_DETAIL
    assert page.degree_level == "bachelor"
    assert page.subject == "BTech in CSE – Computer Science and Engineering"


def test_iit_delhi_subject_passes_on_the_requested_field_itself(monkeypatch) -> None:
    """LX-1 does not touch the CSE policy, and the policy does not decide this page.

    ``matches_field_text`` accepts a label containing the applicant's own field
    words before the filler rule runs, and never consults
    ``related_not_equivalent``; "BTech in CSE – Computer Science and
    Engineering" therefore passes for "computer science" once it has a level.
    """
    monkeypatch.setattr(page_classifier, "LEXICON_V2", True)
    page = classify_page(url=IITD_URL, html=IITD_HTML)
    assert profile_rejects(page, "bachelor", ["computer science"]) is None
    assert profile_rejects(page, "bachelor", ["computing"]) is not None


def test_puc_licenciatura_page_reads_as_bachelor(lexicon: bool) -> None:
    page = classify_page(url=PUC_URL, html=PUC_HTML)
    if not lexicon:
        assert page.page_type is PageType.UNKNOWN
        return
    assert page.page_type is PageType.PROGRAM_DETAIL
    assert page.degree_level == "bachelor"
    # "Ingeniería" names another subject; the filler rule still refuses the title.
    assert profile_rejects(page, "bachelor", ["computer science"]) is not None


@pytest.mark.parametrize("localized", [False, True])
def test_btech_slug(lexicon: bool, localized: bool, monkeypatch) -> None:
    monkeypatch.setattr(live_discovery, "LOCALIZED_IDENTITY", localized)
    assert degree_level_named(IITD_URL) == ("bachelor" if lexicon else None)
    assert degree_level_named("https://x.ac.in/mtech/cse") == ("master" if lexicon else None)
    # An existing slug still wins and nothing else is touched.
    assert degree_level_named("https://x.ac.in/bsc/btech") == "bachelor"
    assert degree_level_named("https://x.ac.in/biotech-research/") is None


# --- 2. funding gate scope ---------------------------------------------------------


def test_auckland_scholarship_h2_does_not_make_a_scholarship_index(
    lexicon: bool, monkeypatch
) -> None:
    # FI-1 (on by default) narrows the funding gate on its own; pinned off so
    # "off" still means LEXICON_V2's own effect (FI-1's is in its own file).
    monkeypatch.setattr(page_classifier, "FUNDING_IDENTITY_SCOPE", False)
    page = classify_page(url=AUCKLAND_URL, html=AUCKLAND_HTML)
    if not lexicon:
        assert page.page_type is PageType.SCHOLARSHIP_INDEX
        return
    assert page.page_type is PageType.PROGRAM_DETAIL
    assert page.degree_level == "bachelor"
    assert profile_rejects(page, "bachelor", ["computer science"]) is None


def test_a_scholarship_named_in_the_h1_is_still_a_funding_page(lexicon: bool) -> None:
    html = (
        "<html><head><title>Global Excellence Scholarship | Uni</title></head><body><main>"
        "<h1>Global Excellence Scholarship</h1><h2>Eligibility</h2><p>Open to international "
        "students starting a bachelor's degree. The award is worth NZ$10,000 towards tuition "
        "fees. Apply by 1 May; selection is based on academic merit.</p></main></body></html>"
    )
    page = classify_page(url="https://www.uni.ac.nz/en/global-excellence.html", html=html)
    assert page.page_type is PageType.SCHOLARSHIP_AWARD


def test_a_scholarship_named_only_in_the_title_is_still_a_funding_page(lexicon: bool) -> None:
    """CL-1's scope: identity and title each on its own."""
    html = (
        "<html><head><title>Orange Tulip Scholarship | Uni</title></head><body><main>"
        "<h1>Orange Tulip</h1><p>The award is worth EUR 5,000 towards tuition fees for "
        "students from eligible countries. Apply by 1 April; selection is based on merit."
        "</p></main></body></html>"
    )
    page = classify_page(url="https://www.uni.nl/en/orange-tulip", html=html)
    # The funding family was entered on the title alone (its h1 names no award).
    assert page.page_type is PageType.UNKNOWN
    assert page.signals[0].startswith("funding page with")


# --- 3. localized computer science aliases ---------------------------------------


@pytest.mark.parametrize(
    "label",
    [
        "Informatikk",
        "Bachelor i informatikk",
        "Datalogi",
        "Ciencia de la Computación",
    ],
)
def test_localized_aliases_name_computer_science(lexicon: bool, label: str) -> None:
    assert matches_field_text(label, ["computer science"]) is lexicon


def test_existing_aliases_unchanged(lexicon: bool) -> None:
    assert matches_field_text("Ciencias de la Computación", ["computer science"])
    assert matches_field_text("Informatica", ["computer science"])
    # Accents are folded, so Catalan "Informàtica" already matched Dutch/Italian "informatica".
    assert matches_field_text("Informàtica", ["computer science"])
    assert not matches_field_text("Bioinformatikk", ["computer science"])
    assert not matches_field_text("Data Science", ["computer science"])


def test_aliases_need_localized_identity(monkeypatch) -> None:
    monkeypatch.setattr(page_classifier, "LEXICON_V2", True)
    monkeypatch.setattr(live_discovery, "LOCALIZED_IDENTITY", False)
    assert not matches_field_text("Informatikk", ["computer science"])


def test_aliases_are_identity_only_never_query_terms(lexicon: bool) -> None:
    new = {
        "informatikk",
        "datalogi",
        "informàtica",
        "ciencia de la computación",
    }
    terms = {candidate.term for candidate in retrieval_candidates("computer science")}
    assert not new & terms
    assert all(canonical_field(alias) is None for alias in new - {"informàtica"})
    assert not new & set(localized_aliases("computer science"))
    names = {name.lower() for name in with_strong_aliases(["computer science"])}
    assert (new <= names) is lexicon
    assert bool(new & names) is lexicon


def test_flagged_alias_selection() -> None:
    every = set(localized_aliases("computer science", include_flagged=True))
    li1_only = set(
        localized_aliases(
            "computer science", include_flagged=True, flags=frozenset({"LOCALIZED_IDENTITY"})
        )
    )
    assert "informatikk" in every and "informatikk" not in li1_only
    assert "datavetenskap" in li1_only and "informatik" in li1_only


def test_uio_subtitle_is_still_refused(monkeypatch) -> None:
    """The alias alone does not accept a subject with a subtitle (not part of LX-1)."""
    monkeypatch.setattr(page_classifier, "LEXICON_V2", True)
    page = classify_page(url=UIO_URL, html=UIO_HTML)
    assert page.page_type is PageType.PROGRAM_DETAIL
    assert page.degree_level == "bachelor"
    assert profile_rejects(page, "bachelor", ["computer science"]) is not None


# --- 4. PG-1 publication words and the lirias host -------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "https://ing.uc.cl/publicaciones/a-mobile-robotics-course-for-undergraduate-students/",
        "https://www.uni.es/publicacion/123",
        "https://www.uni.nl/publicaties/informatica",
        "https://www.uio.no/publikasjoner/2024",
        "https://lirias.kuleuven.be/retrieve/123",
    ],
)
def test_local_publication_urls_are_irrelevant(lexicon: bool, url: str) -> None:
    assert (classify_url(url) is PageType.IRRELEVANT) is lexicon


@pytest.mark.parametrize(
    "url",
    [
        "https://ing.uc.cl/publicaciones/a-mobile-robotics-course/",
        "https://www.uni.nl/publicaties/",
        "https://www.uio.no/publikasjoner/x",
    ],
)
def test_local_publication_paths_are_excluded_under_pg1(lexicon: bool, url: str) -> None:
    assert is_excluded_path(url) is lexicon


def test_publication_paths_need_pg1(monkeypatch) -> None:
    monkeypatch.setattr(page_classifier, "LEXICON_V2", True)
    monkeypatch.setattr(page_classifier, "PROGRAMME_PAGE_GUARD", False)
    assert not is_excluded_path("https://ing.uc.cl/publicaciones/x")


def test_lirias_is_an_archive_host(lexicon: bool) -> None:
    assert is_archive_page("https://lirias.kuleuven.be/retrieve/123") is lexicon
    assert not is_archive_page("https://onderwijsaanbod.kuleuven.be/opleidingen/n/x.htm")
    assert is_archive_page("https://pure.example.ac.uk/x")


def test_a_programme_path_is_untouched(lexicon: bool) -> None:
    assert classify_url(PUC_URL) is PageType.UNKNOWN
    assert not is_excluded_path(PUC_URL)


# --- harness flag ----------------------------------------------------------------


def test_harness_exposes_and_forwards_the_flag() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "evaluation.research.live", "--help"],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "--lexicon-v2" in result.stdout
    source = (BACKEND / "evaluation/research/live.py").read_text(encoding="utf-8")
    assert "lx1_module.LEXICON_V2 = True" in source
    assert '*(["--lexicon-v2"] if args.lexicon_v2 else [])' in source


def test_catalan_computer_engineering_is_not_computer_science(monkeypatch) -> None:
    """Like the Italian "Ingegneria Informatica", refused on purpose."""
    monkeypatch.setattr(page_classifier, "LEXICON_V2", True)
    monkeypatch.setattr(live_discovery, "LOCALIZED_IDENTITY", True)
    assert not matches_field_text("Enginyeria Informàtica", ["computer science"])
