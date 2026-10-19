"""CQ-1: a programme page whose head names a field combination is a related programme.

Gold knockout 2026-10-19 §3, candidate ticket 1 (``CONFIRM_REJECTS_COMBINATION_HEAD``,
harness ``--reject-combination-head``). Under the knockout, identity recovery and
the confirm stage accepted pages whose head names the requested level and
subject plus a qualifier that makes them another programme: ntu's "Bachelor of
Computing in Computer Science with Second Major in Business" and tcd's
"Computer Science (JH)". On: such a head is refused with a pinned verdict that
is both an identity refusal (it frees the slot) and R2's related verdict (the
page is recorded as a related programme). Off: nothing changes.

Offline: synthetic pages in English, German, Spanish, French and Chinese, plus
four development pages hand-fetched through the production ``Fetcher``
(``trust_env_proxy=True``, robots honoured, 2026-10-19) and trimmed of scripts,
styles and comments: ``tests/fixtures/combination_head/``. Groningen's and
Delft's gold pages are CH-1's fixtures. uio's and um's gold pages (same
fetch, 2026-10-19) pin the dev3 bundle-replay regression: a joiner in the
subject's track, after a colon or in a bracket, joins no second field.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from app.adapters.discovery import combination_head, live_discovery
from app.adapters.discovery.combination_head import (
    HEAD_COMBINATION_VERDICT,
    combination_named,
    head_combination_rejects,
)
from app.adapters.discovery.live_discovery import (
    DiscoveryTrace,
    LiveDiscoveryAdapter,
    PageCategory,
    _queue_field_sibling,
    is_identity_refusal,
    is_related_refusal,
    local_twin_wanted,
    profile_rejects,
)
from app.adapters.fetching import Fetcher
from app.adapters.page_classifier import PageClassification, PageType, classify_page
from app.adapters.search.retrieval import RankedCandidate
from evaluation.research import live, stage_summary
from tests.test_live_discovery import StubSite

BACKEND = Path(__file__).resolve().parents[1]
FIXTURES = BACKEND / "tests" / "fixtures" / "combination_head"
CH1_FIXTURES = BACKEND / "tests" / "fixtures" / "confirm_head_identity"
LANGUAGES = BACKEND / "app" / "adapters" / "search" / "languages.json"
CS = ["computer science"]

NTU = (
    "https://www.ntu.edu.sg/education/undergraduate-programme/"
    "bachelor-of-computing-in-computer-science-with-second-major-in-business"
)
NTU_GOLD = (
    "https://www.ntu.edu.sg/education/undergraduate-programme/"
    "bachelor-of-computing-in-computer-science"
)
TCD = "https://www.tcd.ie/courses/undergraduate/courses/computer-science-jh/"
TCD_GOLD = "https://www.tcd.ie/courses/undergraduate/courses/computer-science/"
GRONINGEN = "https://www.rug.nl/bachelors/computing-science/?lang=en"
DELFT = (
    "https://www.tudelft.nl/en/onderwijs/opleidingen/bachelors/computer-science-and-engineering/"
    "bachelor-of-computer-science-and-engineering"
)
PROGRAMME = "https://www.uni.example/study/bachelor/computer-science"

TABLES = (
    "_COMBINATION_MARKERS",
    "_MAJOR_WORDS",
    "_MINOR_WORDS",
    "_COMBINATION_JOINERS",
    "_COMBINATION_COMPLEMENTS",
    "_COMBINATION_TRACK_WORDS",
)


def fixture(name: str) -> str:
    return (FIXTURES / f"{name}.html").read_text(encoding="utf-8")


def ch1_fixture(name: str) -> str:
    return (CH1_FIXTURES / f"{name}.html").read_text(encoding="utf-8")


def page_html(title: str, h1: str, body: str = "", lang: str = "en") -> str:
    return (
        f"<html lang='{lang}'><head><title>{title}</title></head><body>"
        "<header><nav><a href='/'>Home</a></nav></header><main>"
        f"<h1>{h1}</h1><p>Three years, full time. Entry requirements and fees.</p>{body}"
        "</main></body></html>"
    )


def head(title: str, h1: str = "") -> PageClassification:
    """A programme page as the classifier would report it, for the head predicate alone."""
    return PageClassification(
        page_type=PageType.PROGRAM_DETAIL,
        confidence=1.0,
        title=title,
        heading=h1,
        subject=h1 or title,
        degree_level="bachelor",
    )


@pytest.fixture(params=[False, True], ids=["off", "on"])
def cq1(request, monkeypatch) -> bool:
    monkeypatch.setattr(live_discovery, "CONFIRM_REJECTS_COMBINATION_HEAD", request.param)
    return request.param


@pytest.fixture
def on(monkeypatch) -> None:
    monkeypatch.setattr(live_discovery, "CONFIRM_REJECTS_COMBINATION_HEAD", True)


async def _recover(tmp_path, profile, url: str, html: str, country: str = ""):
    """Identity recovery on one search lead served with ``html``."""
    profile.context.intended_fields = list(CS)
    site = StubSite({url: html})
    domain = url.split("/")[2].split(".", 1)[1]
    trace = DiscoveryTrace(institution="U", domain=domain, country=country)
    found: list[str] = []
    async with Fetcher(Path(tmp_path) / "cache", offline=True) as fetcher:
        site.install(fetcher)
        lead = RankedCandidate(url, "Computer Science", 1.0, "fake")
        await LiveDiscoveryAdapter(fetcher)._recover_search_pages([lead], found, trace, profile)
    return found, trace


async def _confirm(tmp_path, profile, pages: dict[str, str]):
    """The confirm stage on programme-page leads served with ``pages``, in order."""
    profile.context.intended_fields = list(CS)
    selected: dict[str, list[str]] = {category: [] for category in PageCategory.ALL}
    selected[PageCategory.PROGRAM_PAGE] = list(pages)
    ranked: dict[str, list[tuple[int, str]]] = {category: [] for category in PageCategory.ALL}
    domain = next(iter(pages)).split("/")[2].split(".", 1)[1]
    trace = DiscoveryTrace(institution="U", domain=domain, country="")
    async with Fetcher(Path(tmp_path) / "cache", offline=True) as fetcher:
        StubSite(dict(pages)).install(fetcher)
        await LiveDiscoveryAdapter(fetcher)._confirm_programs(selected, ranked, trace, profile)
    return selected[PageCategory.PROGRAM_PAGE], trace


# --- the flag, the tables ---------------------------------------------------


def test_cq1_is_off_by_default() -> None:
    assert live_discovery.CONFIRM_REJECTS_COMBINATION_HEAD is False


def test_the_tables_cover_every_language_of_languages_json() -> None:
    countries = json.loads(LANGUAGES.read_text(encoding="utf-8"))["countries"]
    languages = {"en", *(code for codes in countries.values() for code in codes)}
    for name in TABLES:
        assert set(getattr(combination_head, name)) == languages, name
    for name in ("_COMBINATION_MARKERS", "_MAJOR_WORDS", "_MINOR_WORDS"):
        assert all(getattr(combination_head, name)[code] for code in languages), name


def test_no_word_from_the_motivating_pages_beyond_the_generic_markers() -> None:
    # Overfitting guard: ntu's and tcd's own words never enter the tables.
    words = {
        word
        for name in TABLES
        for phrases in getattr(combination_head, name).values()
        for phrase in phrases
        for word in phrase.split()
    }
    for word in ("business", "trading", "computing", "courses", "trinity", "singapore"):
        assert word not in words


# --- the predicate on synthetic heads ----------------------------------------


@pytest.mark.parametrize(
    ("text", "named"),
    [
        ("Bachelor of Computing in Computer Science with Second Major in Business", "second major"),
        ("Computer Science (JH)", "jh"),
        ("Computer Science Joint Honours", "joint honours"),
        ("Computer Science and Economics Double Degree", "double degree"),
        ("Dual Degree in Computer Science and Business", "dual degree"),
        ("Combined Honours Computer Science", "combined"),
        ("Computer Science Major with Business Minor", "major / minor"),
        ("Computer Science with Business", "with business"),
        ("Computer Science and Philosophy", "and philosophy"),
        ("Philosophy and Computer Science", "and philosophy"),
    ],
)
def test_combination_heads_are_named(text, named) -> None:
    assert combination_named(text, CS) == named


@pytest.mark.parametrize(
    "text",
    [
        "Computer Science with Honours",
        "BSc (Hons) Computer Science",
        "Computer Science (Hons)",
        "Computer Science with a Year in Industry",
        "Computer Science with Industrial Placement",
        "Computer Science with a Foundation Year",
        "Computer Science with Study Abroad",
        "Bachelor of Science with Honours in Computer Science",
        "Computer Science (with entrance exam procedure)",
        "Computer Science with a specialisation in Artificial Intelligence",
        "Computer Science and Engineering",
        "Computer Science and Technology",
        "Computer Science Major",
        "Computing Science",
        "Computer Science",
    ],
)
def test_single_subject_heads_are_not_combinations(text) -> None:
    assert combination_named(text, CS) is None
    assert head_combination_rejects(head(f"{text} | University", text), CS) is None


def test_an_alias_of_the_requested_subject_is_no_second_field() -> None:
    assert combination_named("Computer Science and Informatics", CS) is None
    assert combination_named("Mathematics and Computer Science", [*CS, "mathematics"]) is None


@pytest.mark.parametrize(
    ("text", "country"),
    [
        # uio's and um's gold heads (dev3 bundle replay, 2026-10-19): the joiner
        # sits in the subject's track, after a subtitle mark or in a bracket.
        ("Informatikk: programmering og systemarkitektur", "Norway"),
        ("Informatikk: robotikk og intelligente systemer", "Norway"),
        ("BACHELOR OF COMPUTER SCIENCE (COMPUTER SYSTEM AND NETWORK)", "Malaysia"),
        ("Computer Science: Software and Systems", ""),
        ("Computer Science - Theory and Practice of Computation", ""),
        ("Informatik (Algorithmen und Datenstrukturen)", "Germany"),
    ],
)
def test_a_joiner_in_the_subjects_track_names_no_combination(text, country) -> None:
    assert combination_named(text, CS, country=country) is None


@pytest.mark.parametrize(
    ("text", "country", "named"),
    [
        # The subject's own clause still joins a second field.
        ("Computer Science (Hons) and Philosophy", "", "and philosophy"),
        ("BSc: Computer Science and Philosophy", "", "and philosophy"),
        ("Computer Science and Philosophy: Joint Programme", "", "and philosophy"),
        ("Informatikk og filosofi", "Norway", "og filosofi"),
        ("Informatikk og filosofi: bachelor", "Norway", "og filosofi"),
        # The subject only in a bracket: the whole head is read, as before.
        ("Bachelor (Computer Science and Philosophy)", "", "and philosophy"),
        # Markers are read in the whole head, brackets and subtitles included.
        ("Computer Science (JH)", "", "jh"),
        ("Computer Science: Second Major in Business", "", "second major"),
    ],
)
def test_the_subjects_own_clause_still_names_a_combination(text, country, named) -> None:
    assert combination_named(text, CS, country=country) == named


def test_joiners_are_read_in_english_and_the_institutions_languages_only() -> None:
    assert combination_named("Informatik und Philosophie", CS, country="Germany") == (
        "und philosophie"
    )
    assert combination_named("Informatik und Philosophie", CS) is None
    assert combination_named("Informatik und Philosophie", CS, country="France") is None


def test_the_head_is_ch1s_h1_and_the_titles_first_part() -> None:
    # The site's name after the separator is not the head.
    assert head_combination_rejects(head("Computer Science | Joint Honours Office"), CS) is None
    assert head_combination_rejects(head("Computer Science (JH) - Courses | U"), CS) == (
        HEAD_COMBINATION_VERDICT.format("jh")
    )
    assert head_combination_rejects(head("Courses | U", "Computer Science (JH)"), CS) == (
        HEAD_COMBINATION_VERDICT.format("jh")
    )


# --- synthetic pages in other languages, through the classifier ---------------

OTHER_LANGUAGES = [
    (
        "de",
        "Germany",
        "https://www.uni.example/studium/bachelor/informatik-zwei-fach",
        "Informatik (Zwei-Fach-Bachelor) | Universität Beispiel",
        "Informatik",
        "zwei-fach-bachelor",
    ),
    (
        "es",
        "Spain",
        "https://www.uni.example/estudios/grado/doble-grado-informatica-matematicas",
        "Doble Grado en Informática y Matemáticas | Universidad Ejemplo",
        "Informática",
        "doble grado",
    ),
    (
        "fr",
        "France",
        "https://www.uni.example/formation/licence/double-licence-informatique",
        "Double licence Informatique et Mathématiques | Université Exemple",
        "Informatique",
        "double licence",
    ),
    (
        "zh",
        "China",
        "https://www.uni.example/bachelor/cs-double-degree",
        "计算机科学与技术（双学位）｜示例大学",
        "计算机科学与技术",
        "双学位",
    ),
]


@pytest.mark.parametrize(("lang", "country", "url", "title", "h1", "named"), OTHER_LANGUAGES)
def test_combination_heads_in_other_languages_are_refused_as_related(
    on, lang, country, url, title, h1, named
) -> None:
    page = classify_page(url=url, html=page_html(title, h1, lang=lang))
    assert page.page_type in (PageType.PROGRAM_DETAIL, PageType.INTAKE_SPECIFIC_PROGRAM)
    verdict = profile_rejects(page, "bachelor", CS, url=url, country=country)
    assert verdict == HEAD_COMBINATION_VERDICT.format(named)
    assert is_related_refusal(verdict)


@pytest.mark.parametrize(
    ("lang", "country", "url", "title", "h1"),
    [
        (
            "de",
            "Germany",
            "https://www.uni.example/studium/bachelor/informatik",
            "Informatik mit Praxissemester (Bachelor of Science) | Universität Beispiel",
            "Informatik",
        ),
        (
            "es",
            "Spain",
            "https://www.uni.example/estudios/grado/informatica",
            "Grado en Informática con mención en Computación | Universidad Ejemplo",
            "Informática",
        ),
        (
            "fr",
            "France",
            "https://www.uni.example/formation/licence/informatique",
            "Licence Informatique avec stage | Université Exemple",
            "Informatique",
        ),
    ],
)
def test_single_subject_heads_in_other_languages_pass(on, lang, country, url, title, h1) -> None:
    page = classify_page(url=url, html=page_html(title, h1, lang=lang))
    assert head_combination_rejects(page, CS, country=country) is None
    assert profile_rejects(page, "bachelor", CS, url=url, country=country) is None


@pytest.mark.parametrize(("lang", "country", "url", "title", "h1", "named"), OTHER_LANGUAGES)
def test_loco_without_english_the_other_languages_are_still_refused(
    monkeypatch, on, lang, country, url, title, h1, named
) -> None:
    # Leave-one-language-out: no English word in any table.
    for name in TABLES:
        table = getattr(combination_head, name)
        monkeypatch.setattr(
            combination_head, name, {code: w for code, w in table.items() if code != "en"}
        )
    page = classify_page(url=url, html=page_html(title, h1, lang=lang))
    assert profile_rejects(page, "bachelor", CS, url=url, country=country) == (
        HEAD_COMBINATION_VERDICT.format(named)
    )
    # And English's own markers are gone with it.
    assert combination_named("Computer Science (JH)", CS) is None


# --- the hand-fetched development pages -------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("url", "name", "named"),
    [(NTU, "ntu_second_major_business", "second major"), (TCD, "tcd_jh", "jh")],
)
async def test_the_confirm_stage_refuses_ntu_and_tcd_on_and_records_them_as_related(
    tmp_path, profile, cq1, url, name, named
) -> None:
    # ntu's second-major pages were confirmed in the confirm stage (registry
    # seed and sitemap leads, before search).
    found, trace = await _confirm(tmp_path, profile, {url: fixture(name)})
    if cq1:
        assert found == []
        assert dict(trace.rejected)[url] == HEAD_COMBINATION_VERDICT.format(named)
        # Classified as related, not dropped silently.
        page = classify_page(url=url, html=fixture(name))
        assert trace.related_programmes == [{"url": url, "title": page.subject}]
    else:
        assert found == [url]
        assert trace.related_programmes == []


@pytest.mark.asyncio
async def test_identity_recovery_refuses_tcds_jh_page_on_and_records_it_as_related(
    tmp_path, profile, cq1
) -> None:
    # tcd's JH page was confirmed by identity recovery under the knockout.
    found, trace = await _recover(tmp_path, profile, TCD, fixture("tcd_jh"))
    if cq1:
        assert found == []
        assert dict(trace.rejected)[TCD] == HEAD_COMBINATION_VERDICT.format("jh")
        assert trace.related_programmes == [{"url": TCD, "title": "Computer Science (JH)"}]
    else:
        assert found == [TCD]


@pytest.mark.asyncio
async def test_identity_recovery_reads_ntus_combination_as_related_on(
    tmp_path, profile, cq1
) -> None:
    # Recovery's own variant words already refused "second major" off; on,
    # the page is refused earlier, as a related programme.
    found, trace = await _recover(tmp_path, profile, NTU, fixture("ntu_second_major_business"))
    assert found == []
    verdict = dict(trace.rejected)[NTU]
    if cq1:
        assert verdict == HEAD_COMBINATION_VERDICT.format("second major")
        assert [row["url"] for row in trace.related_programmes] == [NTU]
    else:
        assert verdict.startswith("page names an alternate programme variant not requested")
        assert trace.related_programmes == []


@pytest.mark.asyncio
async def test_the_confirm_stage_keeps_tcds_own_page_beside_its_jh_page(
    tmp_path, profile, on
) -> None:
    found, trace = await _confirm(
        tmp_path, profile, {TCD: fixture("tcd_jh"), TCD_GOLD: fixture("tcd_gold")}
    )
    assert found == [TCD_GOLD]
    assert [row["url"] for row in trace.related_programmes] == [TCD]


@pytest.mark.asyncio
@pytest.mark.parametrize(("ch1", "cq1_on"), [(False, True), (True, True)], ids=["cq1", "ch1+cq1"])
@pytest.mark.parametrize(
    ("url", "html"),
    [
        (NTU_GOLD, lambda: fixture("ntu_gold")),
        (TCD_GOLD, lambda: fixture("tcd_gold")),
        (GRONINGEN, lambda: ch1_fixture("groningen_gold")),
        (DELFT, lambda: ch1_fixture("delft_gold")),
    ],
    ids=["ntu_gold", "tcd_gold", "groningen_gold", "delft_gold"],
)
async def test_single_subject_gold_pages_are_still_confirmed(
    tmp_path, profile, monkeypatch, ch1, cq1_on, url, html
) -> None:
    monkeypatch.setattr(live_discovery, "CONFIRM_REQUIRES_HEAD_IDENTITY", ch1)
    monkeypatch.setattr(live_discovery, "CONFIRM_REJECTS_COMBINATION_HEAD", cq1_on)
    page = classify_page(url=url, html=html())
    assert profile_rejects(page, "bachelor", CS, url=url) is None
    found, trace = await _recover(tmp_path, profile, url, html())
    assert found == [url]
    assert trace.related_programmes == []


UIO_GOLD = "https://www.uio.no/studier/program/informatikk-programmering"
UM_GOLD = "https://study.um.edu.my/bachelor-of-computer-science-computer-system-and-network"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("url", "name", "country"),
    [(UIO_GOLD, "uio_gold", "Norway"), (UM_GOLD, "um_gold", "Malaysia")],
    ids=["uio_gold", "um_gold"],
)
async def test_gold_pages_whose_track_holds_a_joiner_are_confirmed_under_the_bundle(
    tmp_path, profile, monkeypatch, url, name, country
) -> None:
    # dev3 bundle replay (2026-10-19): CQ-1 read "og systemarkitektur" in uio's
    # "Informatikk: programmering og systemarkitektur" and "and network" in
    # um's "… (COMPUTER SYSTEM AND NETWORK)" as second fields and refused both
    # gold pages as related. Pages fetched through the production Fetcher.
    monkeypatch.setattr(live_discovery, "CONFIRM_REQUIRES_HEAD_IDENTITY", True)
    monkeypatch.setattr(live_discovery, "CONFIRM_REJECTS_COMBINATION_HEAD", True)
    monkeypatch.setattr(live_discovery, "CONFIRM_REJECTS_SUBPAGE_HEAD", True)
    html = fixture(name)
    page = classify_page(url=url, html=html)
    assert head_combination_rejects(page, CS, country=country) is None
    assert profile_rejects(page, "bachelor", CS, url=url, country=country) is None
    found, trace = await _recover(tmp_path, profile, url, html, country=country)
    assert found == [url]
    assert trace.related_programmes == []


def test_a_refused_jh_page_gives_the_next_read_to_the_fields_own_page(on) -> None:
    # R2b reads the related verdict: tcd's single-subject page beside the JH page.
    other = "https://www.tcd.ie/courses/undergraduate/courses/history/"
    reads = _queue_field_sibling(
        (TCD, TCD), [TCD, other, TCD_GOLD], [TCD, other, TCD_GOLD], 1, CS, "bachelor"
    )
    assert reads[1] == TCD_GOLD


# --- the verdict --------------------------------------------------------------


def test_the_verdict_is_an_identity_refusal_and_a_related_verdict() -> None:
    verdict = HEAD_COMBINATION_VERDICT.format("jh")
    assert verdict.startswith("page head ")
    assert is_identity_refusal(verdict)
    assert local_twin_wanted(verdict)
    assert is_related_refusal(verdict)
    assert stage_summary.refusal_category(verdict) == "head_combination"


def test_a_combination_on_a_campus_abroad_keeps_the_campus_verdict(on, monkeypatch) -> None:
    monkeypatch.setattr(
        live_discovery, "_campus_abroad", lambda page, url, country: "page names a campus abroad"
    )
    page = head("Computer Science (JH) | U", "Computer Science (JH)")
    assert profile_rejects(page, "bachelor", CS, url=PROGRAMME) == "page names a campus abroad"


@pytest.mark.asyncio
async def test_off_every_verdict_is_todays(tmp_path, profile, monkeypatch) -> None:
    """Off, the combination predicate is never asked: every verdict is today's."""

    def never(*args, **kwargs):  # pragma: no cover - reached only on a regression
        raise AssertionError("CQ-1 asked while off")

    monkeypatch.setattr(live_discovery, "CONFIRM_REJECTS_COMBINATION_HEAD", False)
    monkeypatch.setattr(combination_head, "head_combination_rejects", never)
    pages = {
        NTU: fixture("ntu_second_major_business"),
        NTU_GOLD: fixture("ntu_gold"),
        TCD: fixture("tcd_jh"),
        TCD_GOLD: fixture("tcd_gold"),
        GRONINGEN: ch1_fixture("groningen_gold"),
        DELFT: ch1_fixture("delft_gold"),
    }
    for url, html in pages.items():
        assert profile_rejects(classify_page(url=url, html=html), "bachelor", CS, url=url) is None
        found, _trace = await _confirm(tmp_path / url.split("/")[-2], profile, {url: html})
        assert found == [url]
        found, _trace = await _recover(tmp_path / f"r-{url.split('/')[-2]}", profile, url, html)
        # Recovery's own variant words refuse ntu's second major today.
        assert found == ([] if url == NTU else [url])


# --- the harness -----------------------------------------------------------


def test_harness_exposes_forwards_and_negates_the_flag() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "evaluation.research.live", "--help"],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "--reject-combination-head" in result.stdout
    assert "--no-reject-combination-head" in result.stdout
    source = (BACKEND / "evaluation" / "research" / "live.py").read_text(encoding="utf-8")
    assert "cq1_module.CONFIRM_REJECTS_COMBINATION_HEAD = True" in source
    assert '["--reject-combination-head"] if args.reject_combination_head' in source
    assert live.NEGATABLE_RULES["reject-combination-head"] == (
        ("app.adapters.discovery.live_discovery", "CONFIRM_REJECTS_COMBINATION_HEAD"),
    )
    assert "reject-combination-head" in live.DEFAULT_OFF_NEGATABLE
