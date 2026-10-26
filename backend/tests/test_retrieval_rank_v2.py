"""Plan v3 change RK-2: retrieval rank v2 (``RETRIEVAL_RANK_V2``).

Three development cases lost the programme page after search had returned
it (loss stages v3, 2026-10-18, §1 and §5 #1): RWTH's central page was rank 1
in two first-pass families and never read, CTU's was rank 5 of the
local-language family only, Bologna's ``laurea/informatica`` rank 1 of the
local-language family and unread once a sibling was confirmed; IIT Delhi's
was rank 8 of one family. The result lists below are those of the r5 / r2b
captures (URLs and family ranks as recorded); the providers' titles were not
recorded, so the titles are the pages' own published titles where the loss
analysis quotes them and plausible ones elsewhere.

On: (a) a URL more families returned ranks higher; (b) R1's local degree
words and R4's local listing roots count as URL signals, and a local master's
slug is another level; (c) the first pass reads each family's top result ahead
of the ranked order. The confirm predicate and the single stop are unchanged.
Off: nothing changes.
"""

from __future__ import annotations

import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.adapters.discovery import live_discovery
from app.adapters.discovery.live_discovery import (
    DiscoveryTrace,
    LiveDiscoveryAdapter,
    PageCategory,
    StageBudget,
    canonical_url,
    local_master_slug,
    names_other_degree_level,
)
from app.adapters.search import intent as intent_module
from app.adapters.search import retrieval
from app.adapters.search.base import SearchResponse, SearchResult
from app.adapters.search.intent import DiscoveryIntent, queries_for
from app.adapters.search.prefilter import prefilter
from app.adapters.search.retrieval import (
    SIGNAL_WEIGHTS,
    RankedCandidate,
    discover_candidates,
    lead_with_family_tops,
    rank_candidates,
)
from app.domain.enums import DegreeLevel
from app.schemas.profile import ApplicantProfileIn
from tests.test_discovery_query_reserve import Fetcher
from tests.test_live_discovery import program_html

BACKEND = Path(__file__).resolve().parents[1]
FIELD = "Computer Science"
MISSING_REGISTRY = Path("/nonexistent-institution-registry.json")
NOW = datetime.now(UTC)

Rows = dict[str, list[tuple[str, str]]]

# --- the development cases' first-pass result lists -------------------------

RWTH_GOLD_EN = (
    "https://www.rwth-aachen.de/cms/root/studium/vor-dem-studium/studiengaenge/"
    "liste-aktuelle-studiengaenge/studiengangbeschreibung/~bnzs/informatik-b-sc-/?lidx=1"
)
RWTH_GOLD_DE = (
    "https://www.rwth-aachen.de/cms/root/studium/vor-dem-studium/studiengaenge/"
    "liste-aktuelle-studiengaenge/studiengangbeschreibung/~bnzs/informatik-b-sc-/"
)
RWTH_SC = "https://sc.informatik.rwth-aachen.de/en/studium/bachelor/informatik/"
RWTH_SC_DE = "https://sc.informatik.rwth-aachen.de/de/studium/bachelor/informatik/"
RWTH_EE = (
    "https://www.elektrotechnik.rwth-aachen.de/cms/elektrotechnik-und-informationstechnik/"
    "studium/bachelor-studiengaenge/~xku/bachelor-studiengaenge/?lidx=1"
)
RWTH: Rows = {
    "field_and_degree": [
        (RWTH_GOLD_EN, "Computer Science B.Sc. | RWTH Aachen University | EN"),
        (
            "https://swc.rwth-aachen.de/teaching/courses/2025-summer-semester/fsse-2025/",
            "FSSE 2025 - Software Construction",
        ),
        (RWTH_SC, "Bachelor Informatik – Computer Science – Studiencenter Informatik"),
        ("http://ceurspt.wikidata.dbis.rwth-aachen.de/Vol-3959/ET-paper3.pdf", "Paper"),
        (
            "https://sc.informatik.rwth-aachen.de/en/studium/bachelor/informatik/aufbau-und-ablauf/",
            "Aufbau und Ablauf – Bachelor Informatik – Studiencenter Informatik",
        ),
    ],
    "natural_language": [
        (RWTH_EE, "Bachelor-Studiengänge | Elektrotechnik und Informationstechnik"),
        (
            "https://www.informatik.rwth-aachen.de/cms/informatik/studium/vor-dem-studium/"
            "~buisol/studiengangs-faq/?lidx=1",
            "Study FAQ | Computer Science",
        ),
    ],
    "local_language": [
        (RWTH_GOLD_DE, "Informatik B.Sc. | RWTH Aachen University | DE"),
        (RWTH_SC_DE, "Bachelor Informatik – Studiencenter Informatik"),
    ],
}

CTU_GOLD = "https://fit.cvut.cz/cs/studijni-programy/bakalarske-studium/informatika"
CTU_EECS = "https://fel.cvut.cz/en/study-programs/eecs-electrical-engineering-and-computer-science"
CTU: Rows = {
    "field_and_degree": [
        (CTU_EECS, "EECS - Electrical Engineering and Computer Science | FEE CTU"),
        (
            CTU_EECS + "/interest-in-studying/bachelor-degree",
            "Bachelor degree | EECS",
        ),
        ("https://bilakniha.cvut.cz/en/predmet7629006.html", "Computer Science Fundamentals"),
        ("https://bilakniha.cvut.cz/en/stplan30021468.html", "Study plan - Computer Science"),
    ],
    "natural_language": [
        (
            "https://fit.cvut.cz/en/applicants/admissions-procedure/bachelor-study-program",
            "Bachelor study program admissions | FIT CTU",
        ),
    ],
    "local_language": [
        (
            "https://fit.cvut.cz/cs/studium/programy-a-obory/bakalarske",
            "Programy a obory | FIT ČVUT",
        ),
        (
            "https://fel.cvut.cz/cz/education/bk/obory/obor4075.B.B.P.10302204",
            "Otevřená informatika",
        ),
        ("https://oi.fel.cvut.cz/cs/bakalarsky-program", "Program | Otevřená informatika"),
        ("https://intranet.fel.cvut.cz/cz/education/bachelor/topicsOI2016.html", "Témata OI"),
        (CTU_GOLD, "Bakalářský studijní program Informatika - FIT ČVUT"),
    ],
}

UNIBO_CSE = "https://corsi.unibo.it/1cycle/ComputerScienceEngineering"
UNIBO_GOLD = "https://corsi.unibo.it/laurea/informatica"
UNIBO_MASTER = "https://corsi.unibo.it/magistrale/informatica"
UNIBO: Rows = {
    "field_and_degree": [
        (UNIBO_CSE, "Computer Science and Engineering - Bachelor - Bologna"),
        (
            "https://corsi.unibo.it/1cycle/ComputerSciencesTechnology",
            "Computer Sciences and Technology - Bachelor - Cesena",
        ),
        ("http://cs.unibo.it/~pellitta/GiulioPellittaCVeng.pdf", "CV - Computer Science"),
    ],
    "natural_language": [
        (
            "https://www.unibo.it/en/study/first-and-single-cycle-degree/programme/2024/8009",
            "Computer Science - Bachelor - Bologna",
        ),
        ("https://corsi.unibo.it/1cycle/ComputerScience", "Computer Science - Bachelor - Bologna"),
    ],
    "local_language": [
        (UNIBO_GOLD, "Informatica - Laurea - Bologna"),
        ("https://corsi.unibo.it/laurea/IngegneriaInformatica", "Ingegneria informatica"),
        ("https://corsi.unibo.it/laurea/informatica/insegnamenti", "Insegnamenti - Informatica"),
        (UNIBO_MASTER, "Informatica - Laurea Magistrale - Bologna"),
    ],
}

IITD_GOLD = "https://homecse.iitd.ac.in/b-tech-program/"
IITD_PDF = "https://maths.iitd.ac.in/api/uploadsMaths/btect_dual_degree_Program_structure.pdf"
IITD_ROOT = "https://www.iitd.ac.in/"
IITD_COURSES = "https://homecse.iitd.ac.in/all-courses/"
IITD: Rows = {
    "field_and_degree": [
        (IITD_PDF, "B.Tech dual degree programme structure"),
        ("https://www.cse.iitd.ac.in/~varma/index.html", "Computer Science | Varma"),
    ],
    "natural_language": [
        (IITD_ROOT, "IIT Delhi"),
        ("https://homecse.iitd.ac.in/", "Computer Science and Engineering | IIT Delhi"),
        ("https://home.iitd.ac.in/ug-admissions.php", "UG admissions"),
        (IITD_GOLD, "B.Tech Program | Computer Science and Engineering"),
    ],
    "programmes": [
        (IITD_COURSES, "All courses | Computer Science and Engineering"),
        ("https://homecse.iitd.ac.in/m-tech-program/", "M.Tech Program"),
    ],
}

CASES = {
    "rwth": (RWTH, "RWTH Aachen University", "rwth-aachen.de", "Germany"),
    "ctu": (CTU, "Czech Technical University in Prague", "cvut.cz", "Czech Republic"),
    "unibo": (UNIBO, "University of Bologna", "unibo.it", "Italy"),
    "iitd": (IITD, "Indian Institute of Technology Delhi", "iitd.ac.in", "India"),
}


@pytest.fixture(autouse=True)
def today(monkeypatch):
    """Pin the defaults this change is measured on (R5, R2, QB-1)."""
    monkeypatch.setattr(intent_module, "LOCAL_LANGUAGE_QUERIES", True)
    monkeypatch.setattr(intent_module, "DISCOVERY_QUERY_RESERVE", True)
    monkeypatch.setattr(intent_module, "SHARED_QUERY_BUDGET", True)
    monkeypatch.setattr(live_discovery, "SUBJECT_TITLE_SHAPES", True)
    monkeypatch.setattr(retrieval, "RETRIEVAL_RANK_V2", False)


@pytest.fixture
def rk2(monkeypatch):
    monkeypatch.setattr(retrieval, "RETRIEVAL_RANK_V2", True)


def an_intent(case: str) -> DiscoveryIntent:
    _rows, name, domain, country = CASES[case]
    return DiscoveryIntent(
        institution=name,
        domain=domain,
        degree=DegreeLevel.BACHELOR,
        field=FIELD,
        institution_country=country,
    )


def ranked(case: str) -> tuple[RankedCandidate, ...]:
    """``rank_candidates`` on one case's first pass, found_by as discovery builds it."""
    rows, _name, domain, _country = CASES[case]
    results = []
    families: dict[str, list[str]] = {}
    for family, listed in rows.items():
        for rank, (url, title) in enumerate(listed, start=1):
            results.append(
                SearchResult(url=url, title=title, provider="serper", rank=rank, retrieved_at=NOW)
            )
            seen = families.setdefault(canonical_url(url), [])
            if family not in seen:
                seen.append(family)
    outcome = prefilter(results, domain=domain, degree=DegreeLevel.BACHELOR)
    return rank_candidates(
        outcome, an_intent(case), found_by={url: tuple(f) for url, f in families.items()}
    )


def by_family(case: str) -> tuple[tuple[str, tuple[str, ...]], ...]:
    rows = CASES[case][0]
    return tuple((family, tuple(url for url, _ in listed)) for family, listed in rows.items())


def urls(candidates) -> list[str]:
    return [candidate.url for candidate in candidates]


def position(candidates, url: str) -> int:
    return urls(candidates).index(canonical_url(url))


# --- flag off ---------------------------------------------------------------


@pytest.mark.parametrize("case", sorted(CASES))
def test_flag_off_adds_no_signal(case):
    v2 = {"local_degree_word", "local_catalogue_path", "family_top_result"}
    for candidate in ranked(case):
        assert not v2 & set(candidate.signals)
        assert not any(s.startswith("family_consensus") for s in candidate.signals)


def test_flag_off_names_no_local_master_level():
    url = "https://fit.cvut.cz/cs/studium/navazujici-studium/informatika"
    assert local_master_slug(url) == "master"
    assert not names_other_degree_level(url, "bachelor")


async def test_flag_off_discovery_never_asks_for_family_tops(monkeypatch):
    seen: list[dict] = []
    real = retrieval.discover_candidates

    async def spy(*args, **kwargs):
        seen.append(kwargs)
        return await real(*args, **kwargs)

    monkeypatch.setattr(retrieval, "discover_candidates", spy)
    pages, trace, _fetcher = await discover("rwth", RWTH_PAGES)
    assert seen and all("family_tops_first" not in kwargs for kwargs in seen)
    assert not any(line.startswith("RK-2") for line in trace.errors)


# --- (a) family consensus ---------------------------------------------------


def test_a_url_more_families_returned_ranks_higher(rk2):
    results = [
        SearchResult(url=u, title="Computer Science", provider="p", rank=1, retrieved_at=NOW)
        for u in ("https://uni.edu/a", "https://uni.edu/b")
    ]
    outcome = prefilter(results, domain="uni.edu", degree=DegreeLevel.BACHELOR)
    english = DiscoveryIntent(
        institution="Uni", domain="uni.edu", degree=DegreeLevel.BACHELOR, field=FIELD
    )
    found_by = {
        "https://uni.edu/a": ("field_and_degree",),
        "https://uni.edu/b": ("field_and_degree", "natural_language", "programmes"),
    }
    first, second = rank_candidates(outcome, english, found_by=found_by)
    assert first.url == "https://uni.edu/b"
    assert "family_consensus_2" in first.signals
    assert first.score - second.score == pytest.approx(SIGNAL_WEIGHTS["family_consensus_2"])


def test_consensus_is_capped(rk2):
    results = [
        SearchResult(url="https://uni.edu/a", title="x", provider="p", rank=1, retrieved_at=NOW)
    ]
    outcome = prefilter(results, domain="uni.edu", degree=DegreeLevel.BACHELOR)
    english = DiscoveryIntent(
        institution="Uni", domain="uni.edu", degree=DegreeLevel.BACHELOR, field=FIELD
    )
    six = ("a", "b", "c", "d", "e", "f")
    (only,) = rank_candidates(outcome, english, found_by={"https://uni.edu/a": six})
    assert "family_consensus_3" in only.signals
    assert all(s in SIGNAL_WEIGHTS for s in only.signals)


# --- (b) local URL signals --------------------------------------------------


def test_ctu_gold_gains_the_local_listing_root(rk2):
    on = ranked("ctu")
    gold = on[position(on, CTU_GOLD)]
    assert "local_catalogue_path" in gold.signals
    # It climbs above the department pages it sat behind with the rule off.
    assert position(on, CTU_GOLD) < position(on, "https://oi.fel.cvut.cz/cs/bakalarsky-program")


def test_ctu_gold_moves_up_against_the_off_ranking(monkeypatch):
    off = ranked("ctu")
    monkeypatch.setattr(retrieval, "RETRIEVAL_RANK_V2", True)
    on = ranked("ctu")
    assert position(on, CTU_GOLD) < position(off, CTU_GOLD)
    assert on[position(on, CTU_GOLD)].score > off[position(off, CTU_GOLD)].score


def test_unibo_laurea_reads_as_the_bachelor(monkeypatch):
    off = ranked("unibo")
    monkeypatch.setattr(retrieval, "RETRIEVAL_RANK_V2", True)
    on = ranked("unibo")
    gold = on[position(on, UNIBO_GOLD)]
    assert "local_degree_word" in gold.signals
    assert position(on, UNIBO_GOLD) < position(off, UNIBO_GOLD)
    # The master's page never reaches the ranking, on or off.
    assert canonical_url(UNIBO_MASTER) not in urls(on)


def test_rwth_central_page_outranks_the_department_page(monkeypatch):
    off = ranked("rwth")
    assert position(off, RWTH_SC) < position(off, RWTH_GOLD_EN)
    monkeypatch.setattr(retrieval, "RETRIEVAL_RANK_V2", True)
    on = ranked("rwth")
    assert position(on, RWTH_GOLD_EN) < position(on, RWTH_SC)
    assert {"local_degree_word", "local_catalogue_path"} <= set(
        on[position(on, RWTH_GOLD_EN)].signals
    )


def test_an_english_country_gets_no_local_signal(rk2):
    results = [
        SearchResult(
            url="https://www.ox.ac.uk/studijni-programy/bakalarske-studium/informatika",
            title="Bakalářský studijní program",
            provider="p",
            rank=2,
            retrieved_at=NOW,
        )
    ]
    outcome = prefilter(results, domain="ox.ac.uk", degree=DegreeLevel.BACHELOR)
    english = DiscoveryIntent(
        institution="Oxford",
        domain="ox.ac.uk",
        degree=DegreeLevel.BACHELOR,
        field=FIELD,
        institution_country="United Kingdom",
    )
    (only,) = rank_candidates(outcome, english)
    assert not {"local_degree_word", "local_catalogue_path"} & set(only.signals)


@pytest.mark.parametrize(
    "url",
    [
        "https://fit.cvut.cz/cs/studium/navazujici-studium/informatika",
        "https://www.uc.cl/maestria-en-ciencias-de-la-computacion",
        "https://www.tu.de/studium/masterstudium/informatik",
        "https://www.aalto.fi/fi/maisteriohjelmat/tietotekniikka",
        "https://www.usp.br/pos-graduacao/computacao",
    ],
)
def test_a_local_master_slug_is_another_level(rk2, url):
    assert names_other_degree_level(url, "bachelor")
    assert not names_other_degree_level(url, "master")


@pytest.mark.parametrize(
    "url",
    [
        CTU_GOLD,
        UNIBO_GOLD,
        RWTH_GOLD_DE,
        "https://www.unibo.it/it/eventi/masterclass-informatica",
        "https://www.ku.dk/studier/kandidat/datalogi",
    ],
)
def test_bachelor_and_unlevelled_slugs_stay_unlevelled(rk2, url):
    assert not names_other_degree_level(url, "bachelor")


# --- (c) family tops first --------------------------------------------------


def test_rwth_the_family_tops_lead():
    order, moved = lead_with_family_tops(ranked("rwth"), by_family("rwth"))
    assert urls(order)[:2] == [canonical_url(RWTH_GOLD_EN), canonical_url(RWTH_GOLD_DE)]
    assert "family_top_result" in order[0].signals
    assert moved[:2] == tuple(urls(order)[:2])


def test_at_most_two_tops_go_ahead_of_the_ranked_head():
    head = RankedCandidate("https://uni.edu/head", "", 9.0, "p")
    rest = [RankedCandidate(f"https://uni.edu/{n}", "", 5.0 - n, "p") for n in range(5)]
    families = tuple((f"f{n}", (f"https://uni.edu/{n + 1}",)) for n in range(3))
    order, moved = lead_with_family_tops([head, *rest], families)
    assert moved == ("https://uni.edu/1", "https://uni.edu/2")
    assert urls(order)[:3] == ["https://uni.edu/1", "https://uni.edu/2", "https://uni.edu/head"]


def test_a_head_that_is_a_top_keeps_its_place():
    head = RankedCandidate("https://uni.edu/head", "", 9.0, "p")
    rest = [RankedCandidate(f"https://uni.edu/{n}", "", 5.0 - n, "p") for n in range(5)]
    families = (("a", ("https://uni.edu/head",)), ("b", ("https://uni.edu/4",)))
    order, moved = lead_with_family_tops([head, *rest], families)
    assert urls(order)[:2] == ["https://uni.edu/head", "https://uni.edu/4"]
    assert moved == ("https://uni.edu/head", "https://uni.edu/4")


def test_tops_already_first_move_nothing():
    first = RankedCandidate("https://uni.edu/a", "", 9.0, "p")
    second = RankedCandidate("https://uni.edu/b", "", 8.0, "p")
    order, moved = lead_with_family_tops([first, second], (("a", ("https://uni.edu/a",)),))
    assert moved == ()
    assert order == (first, second)


def test_iitd_a_pdf_or_a_front_page_is_never_read_ahead(rk2):
    order, moved = lead_with_family_tops(ranked("iitd"), by_family("iitd"))
    assert canonical_url(IITD_PDF) not in moved
    assert canonical_url(IITD_ROOT) not in moved
    assert set(moved) <= {canonical_url(IITD_COURSES)}


async def test_discover_candidates_reports_what_it_moved(rk2):
    provider = FamilyProvider("rwth")
    report = await discover_candidates(
        provider, an_intent("rwth"), hop_entry_points=0, family_tops_first=True
    )
    assert report.family_tops_first
    assert urls(report.candidates)[: len(report.family_tops_first)] == list(
        report.family_tops_first
    )
    plain = await discover_candidates(FamilyProvider("rwth"), an_intent("rwth"), hop_entry_points=0)
    assert plain.family_tops_first == ()


# --- discovery end to end: identity recovery under the stage budget ----------


class FamilyProvider:
    """Answers each discovery query with its family's recorded result list."""

    name = "serper"

    def __init__(self, case: str) -> None:
        self.rows = CASES[case][0]
        self.by_text = {query.text: query.family for query in queries_for(an_intent(case))}
        self.families: list[str] = []

    async def search(self, *, query, domains=(), max_results=10):
        family = self.by_text.get(query, "")
        self.families.append(family)
        listed = self.rows.get(family, [])
        return SearchResponse(
            query=query,
            provider=self.name,
            retrieved_at=NOW,
            results=tuple(
                SearchResult(url=url, title=title, provider=self.name, rank=i + 1, retrieved_at=NOW)
                for i, (url, title) in enumerate(listed[:max_results])
            ),
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


UNKNOWN = (
    "<html><head><title>{0}</title></head><body><h1>{0}</h1>"
    "<p>News and events from the department.</p></body></html>"
)
RWTH_PAGES = {
    canonical_url(RWTH_GOLD_EN): program_html("Computer Science B.Sc."),
    canonical_url(RWTH_GOLD_DE): program_html("Informatik B.Sc."),
    # The department's page of the same B.Sc. (accepted since R2), which the
    # gold does not list: confirming it first scored rwth wrong at HEAD.
    canonical_url(RWTH_SC): program_html("Bachelor Informatik"),
    canonical_url(RWTH_EE): UNKNOWN.format("Bachelor-Studiengänge"),
}
UNIBO_PAGES = {
    canonical_url(UNIBO_CSE): program_html("Computer Science and Engineering - Bachelor"),
    canonical_url(UNIBO_GOLD): program_html("Informatica - Laurea"),
    canonical_url("https://corsi.unibo.it/1cycle/ComputerScience"): program_html(
        "Computer Science"
    ),
}


async def discover(case: str, pages: dict[str, str]):
    rows, name, domain, country = CASES[case]
    fetcher = Fetcher(pages)
    built = LiveDiscoveryAdapter(fetcher, registry_path=MISSING_REGISTRY)  # type: ignore[arg-type]
    built._search_provider = FamilyProvider(case)  # type: ignore[assignment]
    built._search_provider_resolved = True
    # SB-1 on, a lead already offered (no hop roots): recovery stops at the
    # first page it confirms, exactly as on the live runs.
    built._budget = StageBudget(deadline_seconds=10_000, read_cap=28)
    built._confirmed = set()
    built._has_candidates = True
    built._search_wanted = True
    trace = DiscoveryTrace(institution=name, domain=f"www.{domain}", country=country)
    selected: dict[str, list[str]] = {category: [] for category in PageCategory.ALL}
    await built._add_search_results(
        {"name": name, "country": country}, f"www.{domain}", selected, trace, profile()
    )
    return selected[PageCategory.PROGRAM_PAGE], trace, fetcher


async def test_rwth_off_confirms_the_department_page():
    pages, _trace, fetcher = await discover("rwth", RWTH_PAGES)
    assert pages == [canonical_url(RWTH_SC)]
    assert canonical_url(RWTH_GOLD_EN) not in fetcher.read


async def test_rwth_on_confirms_the_central_page_first(rk2):
    _off_pages, _t, off_fetcher = await discover_off("rwth", RWTH_PAGES)
    pages, trace, fetcher = await discover("rwth", RWTH_PAGES)
    assert pages == [canonical_url(RWTH_GOLD_EN)]
    assert fetcher.read[0] == canonical_url(RWTH_GOLD_EN)
    assert len(fetcher.read) <= len(off_fetcher.read)
    assert trace.discovery_query_passes == [3], "confirmed in pass 1: the reserve is kept"
    assert any(line.startswith("RK-2: family top results moved ahead") for line in trace.errors)


async def discover_off(case: str, pages: dict[str, str]):
    previous = retrieval.RETRIEVAL_RANK_V2
    retrieval.RETRIEVAL_RANK_V2 = False
    try:
        return await discover(case, pages)
    finally:
        retrieval.RETRIEVAL_RANK_V2 = previous


async def test_unibo_one_page_is_confirmed_on_and_off(rk2):
    """The precision guard: two acceptable pages, one confirmation.

    Bologna's CSE page is the field-and-degree family's top result and the
    ranked head, so it is read first on both arms and stops recovery; the
    local family's ``laurea/informatica`` would pass the same predicate and is
    not read beside it. RK-2(c) changes the order of reads, never the count of
    confirmed pages.
    """
    off_pages, _t, _f = await discover_off("unibo", UNIBO_PAGES)
    pages, _trace, fetcher = await discover("unibo", UNIBO_PAGES)
    assert len(pages) == 1 == len(off_pages)
    assert pages == off_pages == [canonical_url(UNIBO_CSE)]
    assert canonical_url(UNIBO_GOLD) not in fetcher.read


async def test_unibo_laurea_is_reached_in_fewer_reads_when_the_head_is_refused(rk2):
    """When the ranked head is refused, the local family's top is read sooner."""
    pages = {
        **UNIBO_PAGES,
        # A page with no degree in its heading reads as general admissions.
        canonical_url(UNIBO_CSE): program_html("Computer Science and Engineering"),
    }
    off_found, _t, off_fetcher = await discover_off("unibo", pages)
    found, _trace, fetcher = await discover("unibo", pages)
    assert found == off_found == [canonical_url(UNIBO_GOLD)]
    assert len(fetcher.read) < len(off_fetcher.read)


async def test_ctu_on_reads_the_gold_within_the_recovery_cap(rk2):
    pages = {canonical_url(CTU_GOLD): program_html("Bakalářský studijní program Informatika")}
    found, _trace, fetcher = await discover("ctu", pages)
    assert found == [canonical_url(CTU_GOLD)]
    assert len(fetcher.read) <= live_discovery.MAX_PROGRAM_CANDIDATES_CHECKED


async def test_iitd_on_reads_no_more_than_off(rk2):
    pages = {canonical_url(IITD_GOLD): program_html("B.Tech Program in Computer Science")}
    off_found, _t, off_fetcher = await discover_off("iitd", pages)
    found, _trace, fetcher = await discover("iitd", pages)
    assert canonical_url(IITD_PDF) not in fetcher.read[:1]
    assert len(fetcher.read) <= max(len(off_fetcher.read), 1)
    assert found == off_found


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
    assert "--retrieval-rank-v2" in result.stdout
    source = (BACKEND / "evaluation/research/live.py").read_text(encoding="utf-8")
    assert "rk2_module.RETRIEVAL_RANK_V2 = True" in source
    assert '["--retrieval-rank-v2"]' in source
