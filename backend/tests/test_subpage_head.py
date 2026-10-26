"""SP-1: a page whose head names only part of a programme is a sub-page.

G-07 gold knockout 2026-10-19 §3, candidate ticket 2
(``CONFIRM_REJECTS_SUBPAGE_HEAD``, harness ``--reject-subpage-head``). With the
gold page hidden, identity recovery confirmed a year of a licence ("L2
Informatique") and an application page ("Application for the B.Sc. Computer
Science Course of Study"): their bodies name the level and the subject, their
heads name one study year or a process before any programme title of their
own. On: such a head is refused with a pinned verdict (an identity refusal),
and a lead whose path sits above the sub-page in the same candidate set is
read next. A head that names the programme first and the part after it stays
the programme's page. Off: nothing changes.

Offline: synthetic heads in English, French, German, Italian, Czech, Spanish
and Japanese, plus five development pages hand-fetched through the production
``Fetcher`` (``trust_env_proxy=True``, robots honoured, 2026-10-19) and
trimmed of scripts and styles: ``tests/fixtures/subpage_head/``. The word
tables were committed (53009706) before any of those pages was read.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from app.adapters.discovery import live_discovery
from app.adapters.discovery.live_discovery import (
    MAX_PROGRAM_CANDIDATES_CHECKED,
    SUBPAGE_HEAD_VERDICT,
    DiscoveryTrace,
    LiveDiscoveryAdapter,
    _queue_subpage_parent,
    head_subpage_rejects,
    is_identity_refusal,
    is_subpage_refusal,
    local_twin_wanted,
    profile_rejects,
    subpage_parent_lead,
)
from app.adapters.fetching import Fetcher
from app.adapters.page_classifier import classify_page
from app.adapters.search.retrieval import RankedCandidate
from evaluation.research import live, stage_summary
from tests.test_live_discovery import StubSite

BACKEND = Path(__file__).resolve().parents[1]
FIXTURES = BACKEND / "tests" / "fixtures" / "subpage_head"
CH1_FIXTURES = BACKEND / "tests" / "fixtures" / "confirm_head_identity"
LANGUAGES = BACKEND / "app" / "adapters" / "search" / "languages.json"
CS = ["computer science"]

PSACLAY = "https://www.universite-paris-saclay.fr/formation/licence/informatique"
PSACLAY_L2 = PSACLAY + "/l2-informatique"
PSACLAY_OTHER = "https://www.universite-paris-saclay.fr/en/study/bachelor/computer-science"
RWTH = (
    "https://www.informatik.rwth-aachen.de/cms/informatik/studium/vor-dem-studium/"
    "bewerbungsinfos/~npqh/bachelor-informatik/"
)
RWTH_EN = RWTH + "?lidx=1"
CTU = "https://fit.cvut.cz/en/applicants/admissions-procedure/bachelor-study-program"
GRONINGEN = "https://www.rug.nl/bachelors/computing-science/?lang=en"
DELFT = (
    "https://www.tudelft.nl/en/onderwijs/opleidingen/bachelors/computer-science-and-engineering/"
    "bachelor-of-computer-science-and-engineering"
)
SYNTHETIC = "https://www.uni.example/study/bachelor/computer-science/part"


def fixture(name: str) -> str:
    return (FIXTURES / f"{name}.html").read_text(encoding="utf-8")


def ch1_fixture(name: str) -> str:
    return (CH1_FIXTURES / f"{name}.html").read_text(encoding="utf-8")


def page_html(title: str, h1: str, lang: str = "en") -> str:
    """A programme-shaped page whose body names the level and the subject."""
    return (
        f"<html lang='{lang}'><head><title>{title}</title></head><body>"
        "<header><nav><a href='/'>Home</a></nav></header><main>"
        f"<h1>{h1}</h1><p>Bachelor of Science in Computer Science. Three years, taught "
        "in English. Entry requirements include IELTS 6.5; tuition fees apply.</p>"
        "</main></body></html>"
    )


def head(title: str, h1: str, lang: str = "en") -> str | None:
    return head_subpage_rejects(classify_page(url=SYNTHETIC, html=page_html(title, h1, lang)), CS)


@pytest.fixture(params=[False, True], ids=["off", "on"])
def sp1(request, monkeypatch) -> bool:
    monkeypatch.setattr(live_discovery, "CONFIRM_REJECTS_SUBPAGE_HEAD", request.param)
    return request.param


@pytest.fixture
def on(monkeypatch) -> None:
    monkeypatch.setattr(live_discovery, "CONFIRM_REJECTS_SUBPAGE_HEAD", True)


async def _recover(tmp_path, profile, pages: dict[str, str], leads: list[str]):
    """Identity recovery on ``leads`` (in order), each served from ``pages``."""
    profile.context.intended_fields = list(CS)
    site = StubSite(dict(pages))
    domain = leads[0].split("/")[2].removeprefix("www.")
    trace = DiscoveryTrace(institution="U", domain=domain, country="")
    found: list[str] = []
    async with Fetcher(Path(tmp_path) / "cache", offline=True) as fetcher:
        site.install(fetcher)
        candidates = [RankedCandidate(url, "Computer Science", 1.0, "fake") for url in leads]
        await LiveDiscoveryAdapter(fetcher)._recover_search_pages(candidates, found, trace, profile)
    return found, dict(trace.rejected), site.requested, trace


# --- the flag, the tables ---------------------------------------------------


def test_sp1_is_on_by_default() -> None:
    assert live_discovery.CONFIRM_REJECTS_SUBPAGE_HEAD is True


def test_the_word_tables_cover_every_language_of_languages_json() -> None:
    countries = json.loads(LANGUAGES.read_text(encoding="utf-8"))["countries"]
    languages = {"en", *(code for codes in countries.values() for code in codes)}
    for table in (live_discovery._SUBPAGE_YEAR_WORDS, live_discovery._SUBPAGE_PROCESS_WORDS):
        assert set(table) == languages
        assert all(table[code] for code in languages)


def test_no_subject_or_degree_word_from_the_motivating_pages_is_in_the_tables() -> None:
    # Overfitting guard: the tables name years and processes, never a subject,
    # a degree or a word of the psaclay/rwth/ctu heads beyond the generic nouns.
    words = " ".join(
        word
        for table in (live_discovery._SUBPAGE_YEAR_WORDS, live_discovery._SUBPAGE_PROCESS_WORDS)
        for entries in table.values()
        for word in entries
    )
    for foreign in ("informati", "computer", "science", "bachelor", "b.sc", "course of study"):
        assert foreign not in words


# --- the predicate on synthetic heads ------------------------------------------


@pytest.mark.parametrize(
    ("lang", "title", "h1", "word"),
    [
        ("en", "Year 2 Computer Science | University", "Year 2 Computer Science", "year 2"),
        (
            "en",
            "Computer Science | University",
            "Application for the BSc Computer Science",
            "application for",
        ),
        ("en", "Admissions | BSc Computer Science | University", "", "admissions"),
        ("en", "How to apply | University", "How to apply", "how to apply"),
        ("fr", "L1 Informatique | Université", "L1 Informatique", "l1"),
        ("fr", "Licence Informatique", "Candidature en licence informatique", "candidature"),
        (
            "de",
            "Bachelor Informatik | Universität",
            "Bewerbung für den Bachelor Informatik",
            "bewerbung",
        ),
        ("de", "2. Studienjahr Informatik", "2. Studienjahr Informatik", "2. studienjahr"),
        ("it", "Laurea in Informatica", "Immatricolazione al corso di laurea", "immatricolazione"),
        ("it", "Primo anno — Informatica", "Primo anno", "primo anno"),
        ("cs", "Informatika", "Přijímací řízení na bakalářské studium", "prijimaci"),
        ("es", "Grado en Informática", "Admisión al Grado en Ingeniería Informática", "admision"),
        ("ja", "入試情報 | 情報科学科", "入試情報", "入試"),
    ],
)
def test_a_head_naming_a_year_or_a_process_first_is_a_subpage(lang, title, h1, word) -> None:
    assert head(title, h1, lang) == SUBPAGE_HEAD_VERDICT.format(word)


@pytest.mark.parametrize(
    ("lang", "title", "h1"),
    [
        # The overfitting guard: a full programme title first, the process after.
        (
            "en",
            "Bachelor of Science in Computer Science — Admission requirements",
            "Bachelor of Science in Computer Science — Admission requirements",
        ),
        ("en", "BSc Computer Science", "Bachelor of Science in Computer Science: fees and funding"),
        ("en", "Computer Science BSc Admission Requirements", "Computer Science BSc"),
        ("fr", "Licence Informatique — Admission", "Licence Informatique — Candidature"),
        ("de", "Informatik (B.Sc.) – Bewerbung", "Informatik (B.Sc.)"),
        ("it", "Laurea in Informatica - Ammissione", "Laurea in Informatica"),
        # Words that also name a field or a course are not processes.
        ("en", "Computer Science and Applications", "Computer Science and Applications (BSc)"),
        ("en", "Software Application Development", "Application Development BSc"),
        (
            "en",
            "Computer Science with a Year in Industry",
            "Computer Science with a Year in Industry",
        ),
        # A year number is one digit, never a calendar year.
        ("en", "Year 2026 Computer Science", "Year 2026 Computer Science"),
        # Two or more years span the programme.
        ("fr", "L1, L2, L3 Informatique | Université", "L1-L3 Informatique"),
        ("cs", "Informatika – bakalářský studijní program", "Informatika"),
    ],
)
def test_a_programme_title_first_or_no_part_word_is_not_a_subpage(lang, title, h1) -> None:
    assert head(title, h1, lang) is None


@pytest.mark.asyncio
async def test_a_programme_page_with_an_admission_subtitle_is_confirmed_on(
    tmp_path, profile, on
) -> None:
    title = "Bachelor of Science in Computer Science — Admission requirements"
    url = "https://www.uni.example/study/bachelor/computer-science"
    html = page_html(title + " | University", title)
    assert profile_rejects(classify_page(url=url, html=html), "bachelor", CS, url=url) is None
    found, _rejected, _requested, _trace = await _recover(tmp_path, profile, {url: html}, [url])
    assert found == [url]


# --- the hand-fetched development pages -------------------------------------


@pytest.mark.asyncio
async def test_psaclay_l2_page_is_refused_on_and_confirmed_off(tmp_path, profile, sp1) -> None:
    found, rejected, _requested, _trace = await _recover(
        tmp_path, profile, {PSACLAY_L2: fixture("psaclay_l2")}, [PSACLAY_L2]
    )
    if sp1:
        assert found == []
        assert rejected[PSACLAY_L2] == (
            "page head names part of a programme (l2), not the programme page"
        )
    else:
        assert found == [PSACLAY_L2]


@pytest.mark.asyncio
async def test_rwth_application_page_is_refused_on_and_confirmed_off(
    tmp_path, profile, sp1
) -> None:
    found, rejected, _requested, _trace = await _recover(
        tmp_path, profile, {RWTH_EN: fixture("rwth_application_en")}, [RWTH_EN]
    )
    if sp1:
        assert found == []
        assert rejected[RWTH_EN] == SUBPAGE_HEAD_VERDICT.format("application for")
    else:
        assert found == [RWTH_EN]


def test_rwth_german_application_head_names_a_process() -> None:
    page = classify_page(url=RWTH, html=fixture("rwth_application_de"))
    assert page.heading == "Bewerbung für den Bachelor Informatik"
    assert head_subpage_rejects(page, CS) == SUBPAGE_HEAD_VERDICT.format("bewerbung")


def test_ctu_admissions_page_is_outside_the_rule() -> None:
    # Recorded limit: ctu's head names a programme ("Bachelor's degree
    # programme Informatics"); the process is only in its URL and breadcrumb,
    # which SP-1 does not read. The case stays a knockout guess under SP-1.
    page = classify_page(url=CTU, html=fixture("ctu_admissions"))
    assert page.heading == "Bachelor’s degree programme Informatics"
    assert head_subpage_rejects(page, CS) is None


@pytest.mark.asyncio
@pytest.mark.parametrize("ch1", [False, True], ids=["ch1-off", "ch1-on"])
@pytest.mark.parametrize(
    ("url", "html"),
    [
        (GRONINGEN, lambda: ch1_fixture("groningen_gold")),
        (DELFT, lambda: ch1_fixture("delft_gold")),
        (PSACLAY, lambda: fixture("psaclay_gold")),
    ],
    ids=["groningen", "delft", "psaclay"],
)
async def test_gold_pages_are_still_confirmed_on(
    tmp_path, profile, monkeypatch, on, ch1, url, html
) -> None:
    monkeypatch.setattr(live_discovery, "CONFIRM_REQUIRES_HEAD_IDENTITY", ch1)
    page = classify_page(url=url, html=html())
    assert head_subpage_rejects(page, CS) is None
    assert profile_rejects(page, "bachelor", CS, url=url) is None
    found, _rejected, _requested, _trace = await _recover(tmp_path, profile, {url: html()}, [url])
    assert found == [url]


# --- the parent lead ----------------------------------------------------------


@pytest.mark.asyncio
async def test_recovery_reads_the_parent_lead_next_after_a_subpage(tmp_path, profile, sp1) -> None:
    pages = {
        PSACLAY_L2: fixture("psaclay_l2"),
        PSACLAY_OTHER: page_html("Computer Science | University", "Computer Science"),
        PSACLAY: fixture("psaclay_gold"),
    }
    found, rejected, requested, trace = await _recover(
        tmp_path, profile, pages, [PSACLAY_L2, PSACLAY_OTHER, PSACLAY]
    )
    # Without a discovery budget recovery reads every lead (SB-1 stops at the
    # first confirmation in production); what SP-1 changes is the order.
    if sp1:
        # The gold sits above the refused L2 page: it is read next, ahead of
        # the lead ranked before it. The same three leads, no other read.
        assert requested == [PSACLAY_L2, PSACLAY, PSACLAY_OTHER]
        assert found == [PSACLAY, PSACLAY_OTHER]
        assert is_subpage_refusal(rejected[PSACLAY_L2])
        assert f"SP-1: reading {PSACLAY} next, above the sub-page {PSACLAY_L2}" in trace.errors
    else:
        assert requested == [PSACLAY_L2, PSACLAY_OTHER, PSACLAY]
        assert found == [PSACLAY_L2, PSACLAY_OTHER, PSACLAY]


def test_the_confirm_stage_moves_the_parent_into_the_next_read() -> None:
    trace = DiscoveryTrace(institution="U", domain="uni.example", country="")
    sub = "https://www.uni.example/study/informatics/year-2"
    parent = "https://www.uni.example/study/informatics"
    others = [f"https://www.uni.example/study/other-{n}" for n in range(10)]
    queued = [sub, *others, parent]
    reads = queued[:MAX_PROGRAM_CANDIDATES_CHECKED]
    moved = _queue_subpage_parent((sub, sub), queued, reads, 1, trace)
    assert moved[:2] == [sub, parent]
    assert len(moved) == len(reads)  # one read moves, none is added
    assert moved[2:] == reads[1 : MAX_PROGRAM_CANDIDATES_CHECKED - 1]
    assert trace.errors == [f"SP-1: reading {parent} next, above the sub-page {sub}"]
    # No parent in the candidate set: the reads are untouched.
    assert _queue_subpage_parent((sub, sub), others, others[:8], 1, trace) == others[:8]


def test_the_parent_is_the_nearest_lead_above_the_subpage_on_its_host() -> None:
    sub = "https://www.uni.example/a/b/c/year-1"
    assert subpage_parent_lead([sub], ["https://uni.example/a", "https://uni.example/a/b/c"]) == (
        "https://uni.example/a/b/c"
    )
    assert subpage_parent_lead([sub], ["https://other.example/a/b"]) is None
    assert subpage_parent_lead([sub], ["https://www.uni.example/a/x"]) is None
    assert subpage_parent_lead([sub], [sub]) is None
    assert subpage_parent_lead(["https://u.example/en/x/y"], ["https://u.example/en"]) is None
    assert subpage_parent_lead(["https://u.example/en/x/y"], ["https://u.example/"]) is None
    # The URL a redirect ended at counts as well; a query is not a path.
    assert subpage_parent_lead(
        ["https://u.example/old", RWTH_EN], ["https://www.informatik.rwth-aachen.de/cms"]
    ) == ("https://www.informatik.rwth-aachen.de/cms")


# --- LOCO: one country's own words left out ------------------------------------


def _without(monkeypatch, language: str) -> None:
    for name in ("_SUBPAGE_YEAR_WORDS", "_SUBPAGE_PROCESS_WORDS"):
        table = getattr(live_discovery, name)
        monkeypatch.setattr(
            live_discovery, name, {code: w for code, w in table.items() if code != language}
        )


def test_loco_rwth_without_german_still_refuses_its_english_page(monkeypatch) -> None:
    _without(monkeypatch, "de")
    page = classify_page(url=RWTH_EN, html=fixture("rwth_application_en"))
    assert head_subpage_rejects(page, CS) == SUBPAGE_HEAD_VERDICT.format("application for")
    german = classify_page(url=RWTH, html=fixture("rwth_application_de"))
    assert head_subpage_rejects(german, CS) is None


def test_loco_psaclay_rests_on_its_own_language(monkeypatch) -> None:
    # Recorded: "L2" is the French system's own year word; without French no
    # other language's table refuses psaclay's page.
    _without(monkeypatch, "fr")
    page = classify_page(url=PSACLAY_L2, html=fixture("psaclay_l2"))
    assert head_subpage_rejects(page, CS) is None


@pytest.mark.parametrize("language", ["en", "fr", "de", "it", "cs", "es", "ja"])
def test_loco_each_language_stands_alone(monkeypatch, language) -> None:
    # Leaving one language out moves only that language's heads.
    heads = {
        "en": ("Year 2 Computer Science", "en"),
        "fr": ("L1 Informatique", "fr"),
        "de": ("Bewerbung für den Bachelor Informatik", "de"),
        "it": ("Immatricolazione al corso di laurea", "it"),
        "cs": ("Pro uchazeče o studium", "cs"),
        "es": ("Admisión al Grado en Ingeniería Informática", "es"),
        "ja": ("入試情報", "ja"),
    }
    _without(monkeypatch, language)
    for code, (h1, lang) in heads.items():
        verdict = head(h1, h1, lang)
        assert (verdict is None) is (code == language), (code, verdict)


def test_loco_czech_admission_procedure_is_also_slovak(monkeypatch) -> None:
    # Recorded: cs "přijímací" and sk "prijímací" fold to one stem, so a Czech
    # admission-procedure head is refused with Czech left out (Slovak's word).
    _without(monkeypatch, "cs")
    verdict = head("Přijímací řízení", "Přijímací řízení na bakalářské studium", "cs")
    assert verdict == SUBPAGE_HEAD_VERDICT.format("prijimaci")


# --- the verdict, the harness ---------------------------------------------------


def test_the_sp1_verdict_is_an_identity_refusal() -> None:
    verdict = SUBPAGE_HEAD_VERDICT.format("l2")
    assert verdict.startswith("page head ")
    assert is_identity_refusal(verdict)
    assert local_twin_wanted(verdict)
    assert is_subpage_refusal(verdict)
    assert not is_subpage_refusal("page head names a unit (department), not a programme")
    assert stage_summary.refusal_category(verdict) == "head_names_part"


@pytest.mark.asyncio
async def test_off_every_verdict_is_todays(tmp_path, profile, monkeypatch) -> None:
    """Off, the sub-page predicate is never asked: every verdict is today's."""

    def never(*args, **kwargs):  # pragma: no cover - reached only on a regression
        raise AssertionError("SP-1 asked while off")

    monkeypatch.setattr(live_discovery, "CONFIRM_REJECTS_SUBPAGE_HEAD", False)
    monkeypatch.setattr(live_discovery, "head_subpage_rejects", never)
    monkeypatch.setattr(live_discovery, "subpage_parent_lead", never)
    pages = {
        PSACLAY_L2: fixture("psaclay_l2"),
        PSACLAY: fixture("psaclay_gold"),
        RWTH_EN: fixture("rwth_application_en"),
        RWTH: fixture("rwth_application_de"),
        CTU: fixture("ctu_admissions"),
    }
    verdicts = {
        url: profile_rejects(classify_page(url=url, html=html), "bachelor", CS, url=url)
        for url, html in pages.items()
    }
    assert verdicts == {
        PSACLAY_L2: None,
        PSACLAY: None,
        RWTH_EN: None,
        RWTH: (
            "page subject 'Bewerbung für den Bachelor Informatik' does not match "
            "requested fields ['computer science']"
        ),
        CTU: None,
    }
    found, _rejected, requested, _trace = await _recover(
        tmp_path, profile, pages, [PSACLAY_L2, PSACLAY]
    )
    assert requested == [PSACLAY_L2, PSACLAY]
    assert found == [PSACLAY_L2, PSACLAY]


def test_harness_exposes_forwards_and_negates_the_flag() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "evaluation.research.live", "--help"],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "--reject-subpage-head" in result.stdout
    assert "--no-reject-subpage-head" in result.stdout
    source = (BACKEND / "evaluation" / "research" / "live.py").read_text(encoding="utf-8")
    assert "sp1_module.CONFIRM_REJECTS_SUBPAGE_HEAD = True" in source
    assert '["--reject-subpage-head"] if args.reject_subpage_head' in source
    assert live.NEGATABLE_RULES["reject-subpage-head"] == (
        ("app.adapters.discovery.live_discovery", "CONFIRM_REJECTS_SUBPAGE_HEAD"),
    )
    assert "reject-subpage-head" not in live.DEFAULT_OFF_NEGATABLE
