"""Plan v3 rule R2 (ST-1, stage 4(b)): subject title shapes.

Wayfinder programme-discovery tickets 19 (Q1 subtitle, Q2 place and form
words, Q4 symmetry) and 03 (Q3 related programme, Q4 business degrees), the
glossary's *subject head*, *filler word* and *related field*, and 16-Q6 (a page
refused only on the subject head is recorded as ``related_programmes``). The
development gold pages are R1's saved copies in ``fixtures/localized_identity/``;
every other title is written for the test. No heldout page, label or capture
was opened. Offline: nothing is fetched.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

import app.adapters.search as search_pkg
from app.adapters import page_classifier
from app.adapters.base import AdapterResult
from app.adapters.discovery import live_discovery
from app.adapters.discovery.catalog_walker import CatalogWalk, CatalogWalker, WalkerLink
from app.adapters.discovery.live_discovery import (
    DiscoveryTrace,
    LiveDiscoveryAdapter,
    is_related_refusal,
    matches_field_text,
    profile_rejects,
    subject_head,
    subject_head_verdict,
)
from app.adapters.fetching import Fetcher
from app.adapters.page_classifier import classify_page
from app.adapters.requirements.web_requirements import WebRequirementsAdapter
from app.domain.enums import ClaimType
from app.schemas.claim import Claim
from evaluation.research import live
from evaluation.research.metrics import adjudicate_programme_pages
from evaluation.research.schema import Dataset, Observation
from tests.test_live_discovery import StubSite, program_html, sitemap_xml
from tests.test_question_routing import (
    UCT_ADMISSIONS,
    UCT_BSC,
    UCT_LANGUAGE,
    UCT_LANGUAGE_PAGE,
    _Fetcher,
    _Provider,
    _uct_admissions_page,
    _uct_programme_page,
)
from tests.test_question_routing import _uct as _routing_uct

BACKEND = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).parent / "fixtures" / "localized_identity"
CS = ["computer science"]


@pytest.fixture(params=[False, True], ids=["r1-off", "r1-on"])
def r1(request, monkeypatch) -> bool:
    """R2 composes with R1 either way; LX-1 stays off (R1 absorbs it)."""
    monkeypatch.setattr(page_classifier, "LOCALIZED_PAGE_IDENTITY", request.param)
    monkeypatch.setattr(page_classifier, "LEXICON_V2", False)
    monkeypatch.setattr(live_discovery, "LOCALIZED_IDENTITY", True)
    return request.param


@pytest.fixture
def r2(monkeypatch) -> None:
    monkeypatch.setattr(live_discovery, "SUBJECT_TITLE_SHAPES", True)


@pytest.fixture
def r2_off(monkeypatch) -> None:
    """R2 is on by default; the ``test_off_*`` tests pin the old rule."""
    monkeypatch.setattr(live_discovery, "SUBJECT_TITLE_SHAPES", False)


def test_flag_is_on_by_default() -> None:
    assert live_discovery.SUBJECT_TITLE_SHAPES is True


# --- 1. the development gold pages ---------------------------------------------------


def _gold(name: str) -> tuple[str, str]:
    html = (FIXTURES / f"{name}.html").read_text(encoding="utf-8")
    return html.split("<!-- source: ", 1)[1].split(" ", 1)[0], html


def _verdict(name: str, country: str) -> str | None:
    url, html = _gold(name)
    page = classify_page(url=url, html=html)
    return profile_rejects(page, "bachelor", CS, url=url, country=country)


def _refused(subject: str) -> str:
    return f"page subject {subject!r} does not match requested fields {CS!r}"


def test_uio_subject_head_before_the_colon(r1, r2) -> None:
    """ "Informatikk" is the head; the alias itself is R1's (LX-1's) Norwegian entry."""
    subject = "Informatikk: programmering og systemarkitektur"
    assert subject_head(subject) == "Informatikk"
    assert _verdict("uio", "Norway") == (None if r1 else _refused(subject))


def test_kuleuven_head_before_the_dash_with_its_place_and_form_word(r1, r2) -> None:
    """ "(Leuven)" is a domestic place, "Studieprogramma" a form word: filler (19-Q2)."""
    assert subject_head("Bachelor in de informatica (Leuven) - Studieprogramma") == (
        "Bachelor in de informatica"
    )
    assert _verdict("kuleuven", "Belgium") is None


def test_iitd_computer_science_and_engineering_is_the_programme(r1, r2) -> None:
    """19-Q4 as amended: "Computer Science and Engineering" is computer science.

    The subject is accepted whichever way R1 stands. Whether the page is a
    bachelor's programme page at all is R1's question: without R1's B.Tech
    degree words the classifier reads it as no programme page, and R2 does
    not change that.
    """
    subject = "BTech in CSE – Computer Science and Engineering"
    assert subject_head(subject) == "Computer Science and Engineering"
    assert subject_head_verdict(subject, CS) == "field"
    assert matches_field_text(subject, CS)
    verdict = _verdict("iitd", "India")
    assert verdict == (None if r1 else "reads as unknown, not a programme page")
    assert not is_related_refusal(verdict)


DELFT = (
    "https://www.tudelft.nl/en/onderwijs/opleidingen/bachelors/computer-science-and-engineering/"
    "bachelor-of-computer-science-and-engineering"
)
DELFT_TITLE = "Bachelor of Computer Science and Engineering"


def test_delft_gold_page_is_the_programme(r1, r2) -> None:
    """Delft's cohort gold page: the amendment's motivating case (19-Q4)."""
    page = classify_page(url=DELFT, html=program_html(DELFT_TITLE))
    assert page.subject == DELFT_TITLE
    assert profile_rejects(page, "bachelor", CS, url=DELFT, country="Netherlands") is None


def test_the_ontology_cse_entry_does_not_refuse_it(r1, r2) -> None:
    """ "computer science and engineering" stays a related_not_equivalent entry
    (retrieval reads it), but names no related head under R2."""
    concept = live_discovery.load_ontology().fields["computer_science"]
    assert "computer science and engineering" in concept["related_not_equivalent"]
    assert ("computer", "science", "and", "engineering") not in live_discovery._related_heads(
        "computer science"
    )
    assert subject_head_verdict("Computer Science and Engineering", CS) == "field"


@pytest.mark.parametrize(
    ("name", "country"),
    [("psaclay_fr", "France"), ("uba", "Argentina"), ("ucph_da", "Denmark"), ("puc", "Chile")],
)
def test_r1s_accepted_pages_stay_accepted(r1, r2, monkeypatch, name, country) -> None:
    on = _verdict(name, country)
    monkeypatch.setattr(live_discovery, "SUBJECT_TITLE_SHAPES", False)
    assert on == _verdict(name, country)


@pytest.mark.parametrize(
    ("name", "country"),
    [
        ("psaclay_fr", "France"),
        ("uba", "Argentina"),
        ("ucph_da", "Denmark"),
        ("puc", "Chile"),
        ("iitd", "India"),
        ("uio", "Norway"),
        ("kuleuven", "Belgium"),
        ("ub", "Spain"),
    ],
)
def test_off_the_gold_verdicts_are_r1s(r1, r2_off, name, country) -> None:
    """Flag off: R1's own verdicts, pinned in test_localized_page_identity."""
    from tests.test_localized_page_identity import GOLD

    off, on = next((row[3], row[4]) for row in GOLD if row[0] == name)
    assert _verdict(name, country) == (on if r1 else off)


# --- 2. title shapes -----------------------------------------------------------------

#: (title, verdict under R2). "field" is the programme, "related" a related
#: programme (refused, recorded), None neither.
SHAPES = [
    # 19-Q1: the head before ":" / " - " / " – " is the subject; the tail is ignored.
    ("Computer Science: Artificial Intelligence", "field"),
    ("Computer Science – Bachelor of Science", "field"),
    ("Mathematics: Computer Science", None),
    # A head of degree or form words only gives way to the next part.
    ("Bachelor: Computer Science", "field"),
    ("BTech in CSE – Computer Science and Engineering", "field"),
    # 19-Q2: a place in brackets and a form word are filler; a bracketed
    # single form word too, a longer bracket is not.
    ("Bachelor in de informatica (Leuven) - Studieprogramma", "field"),
    ("Informatica (Leuven)", "field"),
    ("Computing (International)", "field"),
    ("Computing (International Programme of Study) (MEng)", None),
    ("Informatik (Lehramt)", None),
    ("Bachelor Informatik – Studiencenter Informatik", "field"),
    ("KIT - Studiengänge - Informatik Bachelor of Science", "field"),
    # Award names name the degree's faculty, not the subject (19-Q3).
    ("Bachelor of Engineering in Computer Science", "field"),
    ("Bachelor of Engineering (Honours) in Computer Science", "field"),
    ("Informatics Bachelor of Science", "field"),
    ("Bachelor of Science in Computer Science", "field"),
    ("Bachelor of Computing in Computer Science", "field"),
    # 19-Q4 / 03-Q4: the field joined to a related field, in the listed shapes.
    ("Bachelor of Business Science specialising in Computer Science", "related"),
    ("Business Science specialising in Computer Science", "related"),
    ("Mathematics and Computer Science", "related"),
    ("Mathematics and Computer Science BEng", "related"),
    ("Bachelor of Science in Mathematical and Computer Sciences", "related"),
    # 19-Q4 as amended: "<field> and Engineering" is the field itself.
    ("Computer Science and Engineering", "field"),
    ("Bachelor of Computer Science and Engineering", "field"),
    ("Computer Science & Engineering", "field"),
    ("Computer Science and Engineering - Laurea - Cesena", "field"),
    # ... but only that join: another related field beside it stays related.
    ("Mathematics and Computer Science and Engineering", "related"),
    ("Computer Science and Engineering and Economics", "related"),
    ("Bachelor of Science (BSc) in Computer Science and Economics", "related"),
    ("Computer Science & Business", "related"),
    # The ontology's related_not_equivalent heads are related fields too.
    ("Computer Science and Artificial Intelligence", "related"),
    ("Computing and Data Science", "related"),
    ("Bachelor of Commerce specialising in Information Systems & Computer Science", "related"),
    ("Informatics and Economics", "related"),
    # Any other neighbour is left as it was: listed shapes only (02-Q7).
    ("Computer Science (Software Engineering)", "field"),
    ("Bachelor of Computer Science (Computer System and Network)", "field"),
    ("Bachelor of Computing in Computer Science with Second Major in Business", "field"),
    ("Computer Science, Linguistics and a Language", "field"),
    ("Data & Computer Science", "field"),
    ("Computer Science", "field"),
    # Not the field at all.
    ("Computer Engineering", None),
    ("Business Informatics", "related"),
    ("Bachelor — Admissions 2026", None),
]


@pytest.mark.parametrize(("title", "expected"), SHAPES, ids=[s[0] for s in SHAPES])
def test_title_shape(r1, r2, title: str, expected) -> None:
    assert subject_head_verdict(title, CS) == expected
    assert matches_field_text(title, CS) is (expected == "field")


#: What ``matches_field_text`` said before R2 for every title above — the
#: flag off must keep it.
OFF = {
    "Computer Science: Artificial Intelligence": True,
    "Computer Science – Bachelor of Science": True,
    "Mathematics: Computer Science": True,
    "Bachelor: Computer Science": True,
    "BTech in CSE – Computer Science and Engineering": True,
    "Bachelor in de informatica (Leuven) - Studieprogramma": False,
    "Informatica (Leuven)": False,
    "Computing (International)": False,
    "Computing (International Programme of Study) (MEng)": False,
    "Informatik (Lehramt)": False,
    "Bachelor Informatik – Studiencenter Informatik": False,
    "KIT - Studiengänge - Informatik Bachelor of Science": False,
    "Bachelor of Engineering in Computer Science": True,
    "Bachelor of Engineering (Honours) in Computer Science": True,
    "Informatics Bachelor of Science": False,
    "Bachelor of Science in Computer Science": True,
    "Bachelor of Computing in Computer Science": True,
    "Bachelor of Business Science specialising in Computer Science": True,
    "Business Science specialising in Computer Science": True,
    "Mathematics and Computer Science": True,
    "Mathematics and Computer Science BEng": True,
    "Bachelor of Science in Mathematical and Computer Sciences": True,
    "Computer Science and Engineering": True,
    "Bachelor of Computer Science and Engineering": True,
    "Computer Science & Engineering": True,
    "Computer Science and Engineering - Laurea - Cesena": True,
    "Mathematics and Computer Science and Engineering": True,
    "Computer Science and Engineering and Economics": True,
    "Bachelor of Science (BSc) in Computer Science and Economics": True,
    "Computer Science & Business": True,
    "Computer Science and Artificial Intelligence": True,
    "Computing and Data Science": False,
    "Bachelor of Commerce specialising in Information Systems & Computer Science": True,
    "Informatics and Economics": False,
    "Computer Science (Software Engineering)": True,
    "Bachelor of Computer Science (Computer System and Network)": True,
    "Bachelor of Computing in Computer Science with Second Major in Business": True,
    "Computer Science, Linguistics and a Language": True,
    "Data & Computer Science": True,
    "Computer Science": True,
    "Computer Engineering": False,
    "Business Informatics": False,
    "Bachelor — Admissions 2026": False,
}


@pytest.mark.parametrize(("title", "_expected"), SHAPES, ids=[s[0] for s in SHAPES])
def test_off_the_old_rule_answers(r1, r2_off, title: str, _expected) -> None:
    assert matches_field_text(title, CS) is OFF[title]


def test_every_shape_has_its_old_answer() -> None:
    assert {title for title, _ in SHAPES} == set(OFF)


@pytest.mark.parametrize(
    ("title", "lang"),
    [("计算机科学与技术专业", "zh"), ("计算机科学学科", "zh"), ("Бакалавриат: Информатика", "ru")],
)
def test_form_words_left_to_r2_in_unspaced_and_cyrillic_titles(
    r2, monkeypatch, title, lang
) -> None:
    """R1 refused "专业" and "学科" as leftovers; under R2 they are form words."""
    monkeypatch.setattr(page_classifier, "LOCALIZED_PAGE_IDENTITY", True)
    assert matches_field_text(title, CS)
    monkeypatch.setattr(page_classifier, "LOCALIZED_PAGE_IDENTITY", False)
    assert not matches_field_text(title, CS), lang


def test_a_department_word_in_an_unspaced_title_is_still_refused(r2, monkeypatch) -> None:
    monkeypatch.setattr(page_classifier, "LOCALIZED_PAGE_IDENTITY", True)
    assert not matches_field_text("情報科学科", CS)


def test_another_field_keeps_its_own_words(r1, r2) -> None:
    """The related list never refuses a field its own word ("Software Engineering")."""
    assert subject_head_verdict("Software Engineering", ["software engineering"]) == "field"
    assert subject_head_verdict("BSc Mathematics", ["mathematics"]) == "field"


# --- 3. the confirm predicate --------------------------------------------------------

UCT = "https://sit.uct.ac.za/bachelor-business-science-specialising-computer-science"
#: The same page under a path the sitemap reader keeps as a programme page.
UCT_LEAD = "https://www.uct.ac.za/study/courses/undergraduate/business-science-computer-science"
UCT_TITLE = "Bachelor of Business Science specialising in Computer Science"
MATHS_CS = (
    "https://www.uni.ac.uk/study/courses/undergraduate/2027/mathematics-computer-science-beng"
)
CS_PAGE = "https://www.uni.ac.uk/study/courses/undergraduate/2027/computing-beng"


def _page(url: str, title: str):
    return classify_page(url=url, html=program_html(title))


def test_profile_rejects_uct_as_related(r1, r2) -> None:
    page = _page(UCT, UCT_TITLE)
    assert page.subject == UCT_TITLE
    verdict = profile_rejects(page, "bachelor", CS, url=UCT, country="South Africa")
    assert verdict == f"page subject {UCT_TITLE!r} names a related programme, not {CS!r}"
    assert is_related_refusal(verdict)


def test_off_uct_is_confirmed_as_before(r1, r2_off) -> None:
    page = _page(UCT, UCT_TITLE)
    assert profile_rejects(page, "bachelor", CS, url=UCT, country="South Africa") is None


def test_a_related_programme_on_a_foreign_campus_is_a_campus_refusal(r1, r2) -> None:
    url = "https://www.uni.edu.au/study/undergraduate/mathematics-computer-science-bengaluru"
    page = _page(url, "Mathematics and Computer Science (Bengaluru)")
    verdict = profile_rejects(page, "bachelor", CS, url=url, country="Australia")
    assert verdict == "page names a campus abroad (bengaluru), not the institution's own"
    assert not is_related_refusal(verdict)


def test_a_foreign_campus_in_brackets_is_still_refused(r1, r2) -> None:
    """A bracketed place is filler for the subject; CG-1 still refuses one abroad (19-Q2)."""
    url = "https://www.unsw.edu.au/study/undergraduate/computer-science-bengaluru"
    page = _page(url, "Bachelor of Science in Computer Science (Bengaluru)")
    verdict = profile_rejects(page, "bachelor", CS, url=url, country="Australia")
    assert verdict == "page names a campus abroad (bengaluru), not the institution's own"


def test_a_master_page_is_refused_on_its_level_not_recorded(r1, r2) -> None:
    url = "https://www.uni.ac.uk/study/postgraduate/msc-mathematics-and-computer-science"
    page = _page(url, "MSc Mathematics and Computer Science")
    verdict = profile_rejects(page, "bachelor", CS, url=url, country="United Kingdom")
    assert verdict is not None and not is_related_refusal(verdict)


# --- 4. discovery records related programmes on the trace (16-Q6) ---------------------


def _registry(tmp_path: Path, homepage: str, country: str) -> Path:
    import json

    path = tmp_path / "registry.json"
    path.write_text(
        json.dumps([{"name": "U", "country": country, "city": "X", "homepage": homepage}])
    )
    return path


async def _discover(
    tmp_path: Path, pages: dict[str, bytes | str], profile, homepage: str, country: str
):
    site = StubSite(pages)
    async with Fetcher(tmp_path / "c", offline=True) as fetcher:
        site.install(fetcher)
        adapter = LiveDiscoveryAdapter(fetcher, _registry(tmp_path, homepage, country))
        candidate = (await adapter.discover(profile))[0]
    return candidate, adapter.traces[0]


def _uct_site() -> dict[str, bytes | str]:
    root = "https://www.uct.ac.za/"
    return {
        f"{root}robots.txt": f"Sitemap: {root}s.xml\n",
        f"{root}s.xml": sitemap_xml(UCT_LEAD),
        UCT_LEAD: program_html(UCT_TITLE),
    }


@pytest.mark.asyncio
async def test_uct_is_recorded_as_related_not_confirmed(tmp_path, r1, r2, profile) -> None:
    candidate, trace = await _discover(
        tmp_path, _uct_site(), profile, "https://www.uct.ac.za/", "South Africa"
    )
    assert [p.url for p in candidate.programs] == []
    assert trace.related_programmes == [{"url": UCT_LEAD, "title": UCT_TITLE}]
    as_dict = trace.as_dict()
    assert as_dict["related_programmes"] == [{"url": UCT_LEAD, "title": UCT_TITLE}]
    assert live.related_programmes(as_dict) == [UCT_LEAD]


@pytest.mark.asyncio
async def test_off_uct_is_confirmed_and_nothing_is_recorded(tmp_path, r1, r2_off, profile) -> None:
    candidate, trace = await _discover(
        tmp_path, _uct_site(), profile, "https://www.uct.ac.za/", "South Africa"
    )
    assert [p.url for p in candidate.programs] == [UCT_LEAD]
    assert trace.related_programmes == []
    assert "related_programmes" not in trace.as_dict()


@pytest.mark.asyncio
async def test_the_field_page_beside_a_related_one_is_confirmed(tmp_path, r1, r2, profile) -> None:
    """Imperial's shape: maths-and-CS is related, the computing page is the programme."""
    root = "https://www.uni.ac.uk/"
    pages: dict[str, bytes | str] = {
        f"{root}robots.txt": f"Sitemap: {root}s.xml\n",
        f"{root}s.xml": sitemap_xml(MATHS_CS, CS_PAGE),
        MATHS_CS: program_html("Mathematics and Computer Science BEng"),
        CS_PAGE: program_html("Computer Science BEng"),
    }
    candidate, trace = await _discover(tmp_path, pages, profile, root, "United Kingdom")
    assert [p.url for p in candidate.programs] == [CS_PAGE]
    assert trace.related_programmes == [
        {"url": MATHS_CS, "title": "Mathematics and Computer Science BEng"}
    ]


@pytest.mark.asyncio
async def test_delft_is_confirmed_and_nothing_is_recorded(tmp_path, r1, r2, profile) -> None:
    root = "https://www.tudelft.nl/"
    pages: dict[str, bytes | str] = {
        f"{root}robots.txt": f"Sitemap: {root}s.xml\n",
        f"{root}s.xml": sitemap_xml(DELFT),
        DELFT: program_html(DELFT_TITLE),
    }
    candidate, trace = await _discover(tmp_path, pages, profile, root, "Netherlands")
    assert [p.url for p in candidate.programs] == [DELFT]
    assert trace.related_programmes == []


@pytest.mark.asyncio
async def test_the_walker_records_a_related_programme(tmp_path, r1, r2) -> None:
    site = StubSite({UCT: program_html(UCT_TITLE)})
    async with Fetcher(tmp_path / "cache", offline=True) as fetcher:
        site.install(fetcher)
        walker = CatalogWalker(
            fetcher=fetcher,
            domain="uct.ac.za",
            degree="bachelor",
            fields=CS,
            country="South Africa",
        )
        walk = CatalogWalk(catalogue_url="https://sit.uct.ac.za/programmes")
        await walker._read_lead(
            WalkerLink(url=UCT, label="Business Science: Computer Science", score=1, source="html"),
            walk,
        )
    assert walk.confirmed == []
    assert walk.related == [(UCT, UCT_TITLE)]
    assert walk.outcomes == [(UCT, "reads_as_program_detail")]


def test_the_trace_records_each_related_page_once() -> None:
    trace = DiscoveryTrace(institution="U", domain="uni.ac.uk")
    verdict = f"page subject 'X' {live_discovery.RELATED_PROGRAMME_VERDICT}, not {CS!r}"
    trace.note_read(MATHS_CS, MATHS_CS, "<html></html>", verdict, "X")
    trace.note_read(MATHS_CS, MATHS_CS, "<html></html>", verdict, "X")
    trace.note_read(CS_PAGE, CS_PAGE, "<html></html>", None, "Computing")
    assert trace.related_programmes == [{"url": MATHS_CS, "title": "X"}]


def _case(gold: str) -> Dataset:
    evidence = {
        "url": gold,
        "excerpt": "BEng Computing",
        "scope": {"university": "U"},
        "accessed_on": "2026-10-18",
        "source_type": "official",
    }
    case = {
        "id": "uni",
        "dataset_version": "test",
        "university": "U",
        "domain": "uni.ac.uk",
        "country": "United Kingdom",
        "site_types": ["static"],
        "request": {"university": "U"},
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
    return Dataset.model_validate({"version": "test", "split": "development", "cases": [case]})


def test_the_scorer_reads_a_recorded_related_page_as_related_not_wrong() -> None:
    """Imperial before R2: the maths-and-CS page returned is a wrong page; after, related."""
    case = _case("https://www.uni.ac.uk/study/courses/undergraduate/computing-beng/").cases[0]
    before = Observation(case_id="uni", programme_urls=[MATHS_CS])
    assert adjudicate_programme_pages(case, before).outcome == "wrong"
    trace = DiscoveryTrace(institution="U", domain="uni.ac.uk")
    trace.note_related(MATHS_CS, "Mathematics and Computer Science BEng")
    after = Observation(
        case_id="uni",
        programme_urls=[],
        related_programme_urls=live.related_programmes(trace.as_dict()),
    )
    verdict = adjudicate_programme_pages(case, after)
    assert (verdict.outcome, verdict.wrong) == ("related", frozenset())


# --- R2b: a related verdict reads the field's page beside it; no unscoped topic claim ---

IMPERIAL_ROOT = "https://www.uni.ac.uk/"
IMPERIAL_DIR = f"{IMPERIAL_ROOT}study/courses/undergraduate/2027/"
#: Pages the sitemap ranks above the computing page: each names the field in
#: its slug and none is a programme page (Imperial's fee-group and
#: entry-requirements pages took six of the eight confirm reads).
IMPERIAL_DECOYS = [
    f"{IMPERIAL_DIR}entry-requirements---2027/mathematics-and-computer-science-{i}"
    for i in range(1, 9)
]
DECOY = "<html><head><title>Standard requirement</title></head><body><p>A*A*A.</p></body></html>"


def _imperial_site() -> dict[str, bytes | str]:
    return {
        f"{IMPERIAL_ROOT}robots.txt": f"Sitemap: {IMPERIAL_ROOT}s.xml\n",
        f"{IMPERIAL_ROOT}s.xml": sitemap_xml(MATHS_CS, *IMPERIAL_DECOYS, CS_PAGE),
        MATHS_CS: program_html("Mathematics and Computer Science BEng"),
        CS_PAGE: program_html("Computing BEng"),
        **{url: DECOY for url in IMPERIAL_DECOYS},
    }


@pytest.mark.asyncio
async def test_imperial_the_field_page_beside_a_related_one_is_read_next(
    tmp_path, r1, r2, profile
) -> None:
    """dev3 imperial: the related maths-and-CS page gives its next read to computing-beng."""
    candidate, trace = await _discover(
        tmp_path, _imperial_site(), profile, IMPERIAL_ROOT, "United Kingdom"
    )
    assert [p.url for p in candidate.programs] == [CS_PAGE]
    read = [row[0] for row in trace.pages_read]
    assert read[:2] == [MATHS_CS, CS_PAGE]
    # One read moved, none added: the cap is the same eight.
    assert len(read) == live_discovery.MAX_PROGRAM_CANDIDATES_CHECKED
    assert trace.related_programmes == [
        {"url": MATHS_CS, "title": "Mathematics and Computer Science BEng"}
    ]
    assert any(e.startswith(f"R2b: reading {CS_PAGE} next") for e in trace.errors)


@pytest.mark.asyncio
async def test_off_imperial_confirms_maths_and_cs_and_never_reads_computing(
    tmp_path, r1, r2_off, profile
) -> None:
    candidate, trace = await _discover(
        tmp_path, _imperial_site(), profile, IMPERIAL_ROOT, "United Kingdom"
    )
    assert [p.url for p in candidate.programs] == [MATHS_CS]
    assert CS_PAGE not in [row[0] for row in trace.pages_read]
    assert not any(e.startswith("R2b") for e in trace.errors)


@pytest.mark.asyncio
async def test_imperial_the_deadline_comes_from_the_computing_page(
    tmp_path, r1, r2, profile, monkeypatch
) -> None:
    """The deadline the off arm read on the related page is read on the field's own."""
    monkeypatch.setattr(search_pkg, "get_search_provider", lambda: _Provider({}))
    site = _imperial_site()
    deadline = (
        "<p>Submit your application via UCAS. UCAS institution code: I50. Application "
        "deadlines – Wednesday 13 January 2027 at 18.00 (UK time).</p></main>"
    )
    site[CS_PAGE] = str(site[CS_PAGE]).replace("</main>", deadline)
    site[MATHS_CS] = str(site[MATHS_CS]).replace("</main>", deadline)
    stub = StubSite(site)
    async with Fetcher(tmp_path / "c", offline=True) as fetcher:
        stub.install(fetcher)
        registry = _registry(tmp_path, IMPERIAL_ROOT, "United Kingdom")
        candidate = (await LiveDiscoveryAdapter(fetcher, registry).discover(profile))[0]
        [program] = candidate.programs
        result = await WebRequirementsAdapter(fetcher, "2027/28").verify(
            candidate, program, "fall 2027"
        )
    deadlines = [c for c in result.claims if c.claim_type is ClaimType.ADMISSION_DEADLINE]
    assert [(str(c.normalized_value), c.source_url) for c in deadlines] == [("2027-01-13", CS_PAGE)]


def test_the_sibling_is_found_beside_the_url_read_or_the_url_it_ended_at(r2) -> None:
    """Imperial redirects ``/2027/<course>`` to ``/<course>/``; the queue holds the first."""
    redirected = f"{IMPERIAL_ROOT}study/courses/undergraduate/mathematics-computer-science-beng/"
    other_dir = f"{IMPERIAL_ROOT}study/courses/computing"
    queued = [MATHS_CS, other_dir, *IMPERIAL_DECOYS, CS_PAGE]
    reads = queued[:8]
    moved = live_discovery._queue_field_sibling(
        (MATHS_CS, redirected), queued, reads, 1, CS, "bachelor"
    )
    assert moved[:2] == [MATHS_CS, CS_PAGE]
    assert moved[2:] == reads[1:7] and len(moved) == 8
    # Seen only beside the redirected URL, the 2027 directory is not its own.
    assert (
        live_discovery._queue_field_sibling(
            (redirected, redirected), queued, reads, 1, CS, "bachelor"
        )
        == reads
    )


def test_a_sibling_naming_no_field_or_another_level_is_not_moved(r2) -> None:
    courses = f"{IMPERIAL_ROOT}courses/2027/"
    related = f"{courses}mathematics-and-computer-science"
    master = f"{courses}msc-computing"
    physics = f"{courses}physics-bsc"
    queued = [related, *IMPERIAL_DECOYS, master, physics]
    reads = queued[:8]
    assert live_discovery.names_other_degree_level(master, "bachelor")
    assert (
        live_discovery._queue_field_sibling((related, related), queued, reads, 1, CS, "bachelor")
        == reads
    )
    # The same page under a bachelor's slug is moved.
    beng = f"{courses}computing-beng"
    assert live_discovery._queue_field_sibling(
        (related, related), [*queued, beng], reads, 1, CS, "bachelor"
    )[:2] == [related, beng]
    assert live_discovery._slug_subject(f"{IMPERIAL_DIR}computing-beng/") == "computing beng"
    assert live_discovery._slug_subject("https://www.kit.edu/x/bachelor-informatik.php") == (
        "bachelor informatik"
    )


# UCT (dev2, on rep 2): a slow host, so the sitemap stage selected no admissions
# page; the confirmed page links no English page (UCT's department and
# business-science pages link only "How to apply"), and the English topic
# query found the degree-silent language page, claimed for every degree.


async def _uct_verify(
    monkeypatch, pages: dict[str, str], admissions: str | None = None
) -> AdapterResult:
    monkeypatch.setattr(
        search_pkg, "get_search_provider", lambda: _Provider({"English language": UCT_LANGUAGE})
    )
    candidate, program = _routing_uct()
    candidate.admissions_url = admissions
    adapter = WebRequirementsAdapter(_Fetcher(pages), "2027/28")  # type: ignore[arg-type]
    return await adapter.verify(candidate, program, "fall 2027")


def _uct_topic_pages(language: str = UCT_LANGUAGE_PAGE) -> dict[str, str]:
    return {
        UCT_BSC: _uct_programme_page("Bachelor of Science in Computer Science", link=False),
        UCT_LANGUAGE: language,
    }


def _ielts(result: AdapterResult) -> list[Claim]:
    return [c for c in result.claims if c.claim_type is ClaimType.IELTS_MIN_OVERALL]


@pytest.mark.asyncio
async def test_uct_a_degree_silent_topic_page_is_not_claimed(r2, monkeypatch) -> None:
    result = await _uct_verify(monkeypatch, _uct_topic_pages())
    assert _ielts(result) == []
    assert not [c for c in result.claims if c.source_url == UCT_LANGUAGE]
    assert any(e.startswith(f"{UCT_LANGUAGE}: R2b:") for e in result.errors)


@pytest.mark.asyncio
async def test_off_uct_the_topic_page_is_claimed_for_every_degree(r2_off, monkeypatch) -> None:
    [claim] = _ielts(await _uct_verify(monkeypatch, _uct_topic_pages()))
    assert claim.source_url == UCT_LANGUAGE
    assert claim.scope is not None and claim.scope.degree is None


@pytest.mark.asyncio
async def test_uct_the_admissions_route_still_carries_the_degree(r2, monkeypatch) -> None:
    """UCT on rep 1 (and both off reps): QR-1c through the admissions page is unchanged."""
    pages = {**_uct_topic_pages(), UCT_ADMISSIONS: _uct_admissions_page()}
    [claim] = _ielts(await _uct_verify(monkeypatch, pages, admissions=UCT_ADMISSIONS))
    assert (claim.normalized_value, claim.source_url) == (6.5, UCT_LANGUAGE)
    assert claim.scope is not None and claim.scope.degree == "bachelor"
    assert "linked through the admissions page" in claim.notes


@pytest.mark.asyncio
async def test_uct_a_topic_page_stating_the_degree_is_claimed(r2, monkeypatch) -> None:
    language = UCT_LANGUAGE_PAGE.replace(
        "All applicants must", "All applicants to an undergraduate programme must"
    )
    [claim] = _ielts(await _uct_verify(monkeypatch, _uct_topic_pages(language)))
    assert claim.scope is not None and claim.scope.degree == "bachelor"


# --- harness flag ----------------------------------------------------------------------


def test_harness_exposes_and_forwards_the_flag() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "evaluation.research.live", "--help"],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "--subject-title-shapes" in result.stdout
    source = (BACKEND / "evaluation/research/live.py").read_text(encoding="utf-8")
    assert "r2_module.SUBJECT_TITLE_SHAPES = True" in source
    assert '["--subject-title-shapes"]' in source
