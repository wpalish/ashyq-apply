"""CH-1: a programme page is confirmed only when its head carries the identity.

Replay plan 2026-10-19 §5.1 (``CONFIRM_REQUIRES_HEAD_IDENTITY``, harness
``--confirm-head-identity``). The two stable development wrong pages on the
signed corpora were unit pages confirmed from body text: UCT's department page
("Department of Computer Science") and a Bologna lab's course list, both
accepted by identity recovery because a full degree title stood somewhere in
the body. On: the head — ``<title>`` or first ``h1`` — must name the subject,
the level must be named in the head, the URL's degree slug or a labelled
field, and a head that names a unit and no degree is refused with a pinned
verdict. Off: nothing changes.

Offline: synthetic pages in English, German, Italian, Czech and Japanese, plus
four development pages hand-fetched through the production ``Fetcher``
(robots honoured, 2026-10-19) and trimmed of scripts and styles:
``tests/fixtures/confirm_head_identity/``.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from app.adapters import page_classifier
from app.adapters.discovery import live_discovery
from app.adapters.discovery.live_discovery import (
    HEAD_UNIT_VERDICT,
    DiscoveryTrace,
    LiveDiscoveryAdapter,
    head_identity_rejects,
    head_unit_word,
    is_identity_refusal,
    local_twin_wanted,
    profile_rejects,
)
from app.adapters.fetching import Fetcher
from app.adapters.page_classifier import (
    PageType,
    classify_page,
    degree_levels_named,
    labelled_degree_level,
)
from app.adapters.search.retrieval import RankedCandidate
from evaluation.research import live, stage_summary
from tests.test_live_discovery import StubSite

BACKEND = Path(__file__).resolve().parents[1]
FIXTURES = BACKEND / "tests" / "fixtures" / "confirm_head_identity"
LANGUAGES = BACKEND / "app" / "adapters" / "search" / "languages.json"
CS = ["computer science"]

UCT = "https://sit.uct.ac.za/department-computer-science"
UNIBO_LAB = "https://site.unibo.it/digital-sustainability-lab/en/teachings/courses"
GRONINGEN = "https://www.rug.nl/bachelors/computing-science/?lang=en"
DELFT = (
    "https://www.tudelft.nl/en/onderwijs/opleidingen/bachelors/computer-science-and-engineering/"
    "bachelor-of-computer-science-and-engineering"
)
DEPARTMENT = "https://www.uni.example/department-of-computer-science"
PROGRAMME = "https://www.uni.example/study/bachelor/computer-science"
LAB = "https://www.uni.example/robotics-lab/teaching/courses"


def fixture(name: str) -> str:
    return (FIXTURES / f"{name}.html").read_text(encoding="utf-8")


def page_html(title: str, h1: str, body: str, lang: str = "en") -> str:
    return (
        f"<html lang='{lang}'><head><title>{title}</title></head><body>"
        "<header><nav><a href='/'>Home</a></nav></header><main>"
        f"<h1>{h1}</h1>{body}</main></body></html>"
    )


def department_page(h1: str = "Department of Computer Science") -> str:
    """A department hub whose body names the bachelor's it teaches."""
    return page_html(
        "Department of Computer Science | Faculty of Science",
        h1,
        "<p>The department teaches the Bachelor of Science in Computer Science and "
        "supervises research in algorithms, systems and machine learning.</p>"
        "<h2>Research groups</h2><p>Theory, systems, data.</p>",
    )


def programme_page() -> str:
    """A programme page whose head names the subject and whose URL names the level."""
    return page_html(
        "Computer Science | University",
        "Computer Science",
        "<p>Three years, taught in English. Entry requirements include IELTS 6.5.</p>",
    )


def lab_courses_page() -> str:
    """A lab's course list: the level is labelled, the head names no subject."""
    return page_html(
        "Courses — Robotics Lab",
        "Courses",
        "<dl><dt>Level</dt><dd>Bachelor</dd></dl>"
        "<p>We teach in the Bachelor in Computer Science and Engineering.</p>"
        "<ul><li>Robot kinematics</li><li>Embedded systems</li></ul>",
    )


@pytest.fixture(params=[False, True], ids=["off", "on"])
def ch1(request, monkeypatch) -> bool:
    monkeypatch.setattr(live_discovery, "CONFIRM_REQUIRES_HEAD_IDENTITY", request.param)
    return request.param


@pytest.fixture
def on(monkeypatch) -> None:
    monkeypatch.setattr(live_discovery, "CONFIRM_REQUIRES_HEAD_IDENTITY", True)


async def _recover(tmp_path, profile, url: str, html: str):
    """Identity recovery on one search lead served with ``html``."""
    profile.context.intended_fields = list(CS)
    site = StubSite({url: html})
    domain = url.split("/")[2].split(".", 1)[1]
    trace = DiscoveryTrace(institution="U", domain=domain, country="")
    found: list[str] = []
    async with Fetcher(Path(tmp_path) / "cache", offline=True) as fetcher:
        site.install(fetcher)
        lead = RankedCandidate(url, "Computer Science", 1.0, "fake")
        await LiveDiscoveryAdapter(fetcher)._recover_search_pages([lead], found, trace, profile)
    return found, dict(trace.rejected)


# --- the flag, the tables ---------------------------------------------------


def test_ch1_is_on_by_default() -> None:
    assert live_discovery.CONFIRM_REQUIRES_HEAD_IDENTITY is True


def test_the_word_tables_cover_every_language_of_languages_json() -> None:
    countries = json.loads(LANGUAGES.read_text(encoding="utf-8"))["countries"]
    languages = {"en", *(code for codes in countries.values() for code in codes)}
    assert set(live_discovery._UNIT_WORDS) == languages
    assert set(page_classifier._DEGREE_FIELD_LABELS) == languages
    assert all(live_discovery._UNIT_WORDS[code] for code in languages)


def test_no_word_from_the_motivating_pages_beyond_the_generic_unit_nouns() -> None:
    # Overfitting guard: uct's and unibo's own words never enter the table.
    english = set(live_discovery._UNIT_WORDS["en"])
    for word in ("computer", "science", "information", "technology", "sustainability"):
        assert word not in english
    assert "digital" not in english


# --- the predicate on synthetic pages ----------------------------------------


def test_a_department_page_with_bachelor_in_the_body_only_is_refused_as_a_unit(on) -> None:
    page = classify_page(url=DEPARTMENT, html=department_page())
    assert page.heading == "Department of Computer Science"
    assert head_identity_rejects(page, "bachelor", CS, url=DEPARTMENT) == (
        "page head names a unit (department), not a programme"
    )


@pytest.mark.asyncio
async def test_recovery_confirms_the_department_page_off_and_refuses_it_on(
    tmp_path, profile, ch1
) -> None:
    found, rejected = await _recover(tmp_path, profile, DEPARTMENT, department_page())
    if ch1:
        assert DEPARTMENT not in found
        assert rejected[DEPARTMENT] == HEAD_UNIT_VERDICT.format("department")
    else:
        assert found == [DEPARTMENT]


@pytest.mark.asyncio
async def test_the_same_page_headed_bsc_computer_science_is_confirmed(
    tmp_path, profile, ch1
) -> None:
    html = department_page(h1="BSc Computer Science")
    page = classify_page(url=DEPARTMENT, html=html)
    assert page.page_type in (PageType.PROGRAM_DETAIL, PageType.INTAKE_SPECIFIC_PROGRAM)
    assert profile_rejects(page, "bachelor", CS, url=DEPARTMENT) is None
    found, _rejected = await _recover(tmp_path, profile, DEPARTMENT, html)
    assert found == [DEPARTMENT]


@pytest.mark.asyncio
async def test_a_programme_page_headed_by_its_subject_with_a_bachelor_slug_is_confirmed(
    tmp_path, profile, ch1
) -> None:
    page = classify_page(url=PROGRAMME, html=programme_page())
    assert page.heading == "Computer Science"
    assert head_identity_rejects(page, "bachelor", CS, url=PROGRAMME) is None
    found, _rejected = await _recover(tmp_path, profile, PROGRAMME, programme_page())
    assert found == [PROGRAMME]


def test_the_level_must_be_in_the_head_the_slug_or_a_label(on) -> None:
    html = programme_page()
    no_slug = "https://www.uni.example/study/computer-science"
    page = classify_page(url=no_slug, html=html)
    if page.page_type in (PageType.PROGRAM_DETAIL, PageType.INTAKE_SPECIFIC_PROGRAM):
        assert profile_rejects(page, "bachelor", CS, url=no_slug) == (
            "page head names no bachelor level, nor do the URL or a label"
        )
    assert head_identity_rejects(page, "bachelor", CS, url=no_slug) == (
        "page head names no bachelor level, nor do the URL or a label"
    )
    labelled = page_html(
        "Computer Science | University",
        "Computer Science",
        "<dl><dt>Degree</dt><dd>BSc</dd></dl><p>Taught in English.</p>",
    )
    page = classify_page(url=no_slug, html=labelled)
    assert page.labelled_degree_level == "bachelor"
    assert head_identity_rejects(page, "bachelor", CS, url=no_slug) is None


@pytest.mark.asyncio
async def test_a_labs_courses_page_is_refused_for_no_subject_in_its_head(
    tmp_path, profile, ch1
) -> None:
    page = classify_page(url=LAB, html=lab_courses_page())
    assert page.labelled_degree_level == "bachelor"
    assert head_unit_word(page) is None  # the lab is the site's name, not the head
    found, rejected = await _recover(tmp_path, profile, LAB, lab_courses_page())
    if ch1:
        assert LAB not in found
        assert rejected[LAB] == "page head does not name the requested subject ['computer science']"
    else:
        assert found == [LAB]


@pytest.mark.parametrize(
    ("lang", "url", "title", "h1", "word"),
    [
        (
            "de",
            "https://www.uni.example/institut-fuer-informatik",
            "Institut für Informatik | Fakultät für Mathematik",
            "Institut für Informatik",
            "institut",
        ),
        (
            "it",
            "https://www.uni.example/dipartimento-informatica",
            "Dipartimento di Informatica",
            "Dipartimento di Informatica",
            "dipartimento",
        ),
        (
            "cs",
            "https://www.uni.example/katedra-informatiky",
            "Katedra informatiky – Fakulta aplikovaných věd",
            "Katedra informatiky",
            "katedra",
        ),
        (
            "ja",
            "https://www.uni.example/is",
            "情報科学研究科",
            "情報科学研究科",
            "研究科",
        ),
    ],
)
def test_unit_heads_in_other_languages_are_refused(on, lang, url, title, h1, word) -> None:
    html = page_html(title, h1, "<p>Bachelor of Science in Computer Science.</p>", lang)
    page = classify_page(url=url, html=html)
    assert head_identity_rejects(page, "bachelor", CS, url=url) == HEAD_UNIT_VERDICT.format(word)


@pytest.mark.parametrize(
    ("lang", "url", "title", "h1"),
    [
        (
            "de",
            "https://www.uni.example/studium/informatik",
            "Informatik (Bachelor of Science) | Fakultät für Informatik",
            "Informatik (Bachelor of Science)",
        ),
        (
            "it",
            "https://corsi.uni.example/laurea/informatica",
            "Informatica - Laurea - Dipartimento di Informatica",
            "Informatica",
        ),
        (
            "cs",
            "https://www.uni.example/studium/informatika",
            "Informatika – bakalářský studijní program",
            "Informatika",
        ),
    ],
)
def test_programme_heads_in_other_languages_pass(on, lang, url, title, h1) -> None:
    html = page_html(title, h1, "<p>Studium.</p>", lang)
    page = classify_page(url=url, html=html)
    assert head_unit_word(page) is None
    assert head_identity_rejects(page, "bachelor", CS, url=url) is None


def test_a_degree_in_the_head_keeps_a_unit_named_page_from_the_unit_verdict(on) -> None:
    html = page_html(
        "Department of Computer Science | Undergraduate", "BSc in Computer Science", ""
    )
    page = classify_page(url=DEPARTMENT, html=html)
    assert head_identity_rejects(page, "bachelor", CS, url=DEPARTMENT) is None


# --- the hand-fetched development pages -------------------------------------


@pytest.mark.asyncio
async def test_uct_department_page_is_refused_on(tmp_path, profile, ch1) -> None:
    found, rejected = await _recover(tmp_path, profile, UCT, fixture("uct_department"))
    if ch1:
        assert UCT not in found
        assert rejected[UCT] == "page head names a unit (department), not a programme"
    else:
        assert found == [UCT]


@pytest.mark.asyncio
async def test_unibo_lab_courses_page_is_refused_on(tmp_path, profile, ch1) -> None:
    found, rejected = await _recover(tmp_path, profile, UNIBO_LAB, fixture("unibo_lab_courses"))
    if ch1:
        assert UNIBO_LAB not in found
        assert rejected[UNIBO_LAB].startswith("page head ")
    else:
        assert found == [UNIBO_LAB]


@pytest.mark.asyncio
@pytest.mark.parametrize(("url", "name"), [(GRONINGEN, "groningen_gold"), (DELFT, "delft_gold")])
async def test_groningen_and_delft_gold_pages_are_still_confirmed(
    tmp_path, profile, ch1, url, name
) -> None:
    page = classify_page(url=url, html=fixture(name))
    assert profile_rejects(page, "bachelor", CS, url=url) is None
    found, _rejected = await _recover(tmp_path, profile, url, fixture(name))
    assert found == [url]


@pytest.mark.asyncio
async def test_loco_without_english_uct_is_still_refused_on_the_level(
    tmp_path, profile, monkeypatch, on
) -> None:
    # Leave-one-language-out: with no English unit noun, the head names no
    # level and the URL no degree slug, so rule 2 refuses the page.
    words = {code: w for code, w in live_discovery._UNIT_WORDS.items() if code != "en"}
    monkeypatch.setattr(live_discovery, "_UNIT_WORDS", words)
    page = classify_page(url=UCT, html=fixture("uct_department"))
    assert head_unit_word(page) is None
    found, rejected = await _recover(tmp_path, profile, UCT, fixture("uct_department"))
    assert UCT not in found
    assert rejected[UCT] == "page head names no bachelor level, nor do the URL or a label"


# --- the verdicts --------------------------------------------------------------


def test_every_ch1_verdict_is_an_identity_refusal() -> None:
    for verdict in (
        HEAD_UNIT_VERDICT.format("department"),
        "page head names no bachelor level, nor do the URL or a label",
        "page head does not name the requested subject ['computer science']",
    ):
        assert is_identity_refusal(verdict)
        assert local_twin_wanted(verdict)


def test_stage_summary_counts_the_ch1_verdicts() -> None:
    assert stage_summary.refusal_category(HEAD_UNIT_VERDICT.format("katedra")) == (
        "head_names_unit"
    )
    assert stage_summary.refusal_category(
        "page head names no bachelor level, nor do the URL or a label"
    ) == ("head_no_level")
    assert stage_summary.refusal_category(
        "page head does not name the requested subject ['x']"
    ) == ("head_no_subject")


@pytest.mark.asyncio
async def test_off_every_verdict_is_todays(tmp_path, profile, monkeypatch) -> None:
    """Off, the head predicate is never asked: every verdict is today's."""

    def never(*args, **kwargs):  # pragma: no cover - reached only on a regression
        raise AssertionError("CH-1 asked while off")

    monkeypatch.setattr(live_discovery, "CONFIRM_REQUIRES_HEAD_IDENTITY", False)
    monkeypatch.setattr(live_discovery, "head_identity_rejects", never)
    pages = {
        UCT: fixture("uct_department"),
        UNIBO_LAB: fixture("unibo_lab_courses"),
        GRONINGEN: fixture("groningen_gold"),
        DELFT: fixture("delft_gold"),
        DEPARTMENT: department_page(),
        PROGRAMME: programme_page(),
        LAB: lab_courses_page(),
    }
    verdicts = {
        url: profile_rejects(classify_page(url=url, html=html), "bachelor", CS, url=url)
        for url, html in pages.items()
    }
    assert verdicts == {
        UCT: "reads as unknown, not a programme page",
        UNIBO_LAB: "reads as program_catalog, not a programme page",
        GRONINGEN: None,
        DELFT: None,
        DEPARTMENT: "reads as unknown, not a programme page",
        PROGRAMME: None,
        LAB: "reads as program_catalog, not a programme page",
    }
    for url, html in pages.items():
        found, _rejected = await _recover(tmp_path / url.split("/")[2], profile, url, html)
        assert found == [url]


# --- the classifier's new fields --------------------------------------------


def test_heading_and_labelled_level_change_no_verdict() -> None:
    page = classify_page(url=GRONINGEN, html=fixture("groningen_gold"))
    assert page.heading == "Computing Science"
    assert page.page_type is PageType.INTAKE_SPECIFIC_PROGRAM
    assert page.subject == "Computing Science"
    assert classify_page(url=PROGRAMME, html="").heading == ""


@pytest.mark.parametrize(
    ("text", "level"),
    [
        ("Degree:\nBSc", "bachelor"),
        ("Degree: Bachelor of Science", "bachelor"),
        ("Abschluss: Bachelor of Science (B.Sc.)", "bachelor"),
        ("Titolo\nLaurea magistrale", "master"),
        ("Typ studia: bakalářský", "bachelor"),
        ("This bachelor's programme is taught in English.", None),
        ("Degree: BSc or MSc", None),
        ("Degree\n" + "a" * 100, None),
    ],
)
def test_labelled_degree_level(text, level) -> None:
    assert labelled_degree_level(text) == level


def test_degree_levels_named_reads_every_language() -> None:
    assert degree_levels_named("Bachelor's degree programmes") == {"bachelor"}
    assert degree_levels_named("Laurea in Informatica") == {"bachelor"}
    assert degree_levels_named("Department of Computer Science") == frozenset()


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
    assert "--confirm-head-identity" in result.stdout
    assert "--no-confirm-head-identity" in result.stdout
    source = (BACKEND / "evaluation" / "research" / "live.py").read_text(encoding="utf-8")
    assert "ch1_module.CONFIRM_REQUIRES_HEAD_IDENTITY = True" in source
    assert '["--confirm-head-identity"] if args.confirm_head_identity' in source
    assert live.NEGATABLE_RULES["confirm-head-identity"] == (
        ("app.adapters.discovery.live_discovery", "CONFIRM_REQUIRES_HEAD_IDENTITY"),
    )
    assert "confirm-head-identity" not in live.DEFAULT_OFF_NEGATABLE
