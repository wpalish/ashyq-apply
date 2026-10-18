"""Plan rule FI-1: the funding gate reads the page's identity and title only.

The funding-gate part of LX-1 (``LEXICON_V2``) on its own flag,
``page_classifier.FUNDING_IDENTITY_SCOPE``. Shapes from the wrong-claims analysis
of 2026-10-18 (R-D1): UNSW's own computer science programme page carries an h2
"Scholarships" and one link to the scholarships site, read as a scholarship
index, so identity recovery refused it and confirmed the Bengaluru campus page.
The fixtures keep the title and headings the pages published; every body
sentence is written for the test. Offline: nothing is fetched.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from app.adapters import page_classifier
from app.adapters.discovery.live_discovery import profile_rejects
from app.adapters.page_classifier import PageType, classify_page

BACKEND = Path(__file__).resolve().parents[1]

UNSW_URL = "https://www.unsw.edu.au/study/undergraduate/bachelor-of-computer-science"
UNSW_HTML = (
    "<html><head><title>Bachelor of Science (Computer Science) | UNSW Sydney</title></head>"
    "<body><main><h1>Bachelor of Science (Computer Science)</h1>"
    "<h2>Overview</h2><p>The three-year degree covers programming, algorithms, systems "
    "and the theory behind them, with a choice of majors in the second year.</p>"
    "<h2>Entry requirements</h2><p>Applicants complete secondary school with the "
    "assumed knowledge in mathematics.</p>"
    "<h2>English language requirements</h2><p>See the university's English language "
    "requirements for the tests accepted.</p>"
    "<h2>Program structure</h2><p>144 units of credit over three years.</p>"
    "<h2>Fees &amp; Scholarships</h2><h3>Scholarships</h3><p>Scholarships are offered "
    "across the university. <a href='https://www.scholarships.unsw.edu.au/'>"
    "Explore Scholarships</a></p></main></body></html>"
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
    "<h2>Scholarships and awards</h2><p>See <a href='/en/study/scholarships.html'>"
    "Scholarships</a> for what you could apply for.</p></main></body></html>"
)


@pytest.fixture(autouse=True)
def _defaults(monkeypatch) -> None:
    monkeypatch.setattr(page_classifier, "FUNDING_IDENTITY_SCOPE", False)
    monkeypatch.setattr(page_classifier, "LEXICON_V2", False)


def test_flag_is_on_by_default() -> None:
    source = (BACKEND / "app/adapters/page_classifier.py").read_text(encoding="utf-8")
    assert "\nFUNDING_IDENTITY_SCOPE = True\n" in source


@pytest.mark.parametrize(("url", "html"), [(UNSW_URL, UNSW_HTML), (AUCKLAND_URL, AUCKLAND_HTML)])
def test_off_a_scholarship_heading_makes_a_scholarship_index(url: str, html: str) -> None:
    assert classify_page(url=url, html=html).page_type is PageType.SCHOLARSHIP_INDEX


@pytest.mark.parametrize("flag", ["FUNDING_IDENTITY_SCOPE", "LEXICON_V2"])
@pytest.mark.parametrize(("url", "html"), [(UNSW_URL, UNSW_HTML), (AUCKLAND_URL, AUCKLAND_HTML)])
def test_either_flag_reads_the_programme_page(monkeypatch, flag: str, url: str, html: str) -> None:
    monkeypatch.setattr(page_classifier, flag, True)
    page = classify_page(url=url, html=html)
    assert page.page_type is PageType.PROGRAM_DETAIL
    assert page.degree_level == "bachelor"
    assert profile_rejects(page, "bachelor", ["computer science"]) is None


def test_the_flag_alone_leaves_the_lexicon_off(monkeypatch) -> None:
    monkeypatch.setattr(page_classifier, "FUNDING_IDENTITY_SCOPE", True)
    # LX-1 part (i): B.Tech is a degree word only under LEXICON_V2.
    assert page_classifier.degree_level_of("BTech in Computer Science") is None


def test_a_scholarship_in_the_h1_is_still_a_funding_page(monkeypatch) -> None:
    monkeypatch.setattr(page_classifier, "FUNDING_IDENTITY_SCOPE", True)
    html = (
        "<html><head><title>Global Excellence Scholarship | Uni</title></head><body><main>"
        "<h1>Global Excellence Scholarship</h1><h2>Eligibility</h2><p>Open to international "
        "students starting a bachelor's degree. The award is worth NZ$10,000 towards tuition "
        "fees. Apply by 1 May; selection is based on academic merit.</p></main></body></html>"
    )
    page = classify_page(url="https://www.uni.ac.nz/en/global-excellence.html", html=html)
    assert page.page_type is PageType.SCHOLARSHIP_AWARD


def test_a_scholarship_index_title_is_still_an_index(monkeypatch) -> None:
    monkeypatch.setattr(page_classifier, "FUNDING_IDENTITY_SCOPE", True)
    html = (
        "<html><head><title>Scholarships | Uni</title></head><body><main>"
        "<h1>Scholarships</h1><p>Find the award for you.</p>"
        "<a href='/scholarships/a'>Merit Scholarship</a>"
        "<a href='/scholarships/b'>Access Scholarship</a></main></body></html>"
    )
    page = classify_page(url="https://www.uni.edu/study/scholarships", html=html)
    assert page.page_type is PageType.SCHOLARSHIP_INDEX


def test_harness_exposes_and_forwards_the_flag() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "evaluation.research.live", "--help"],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "--funding-identity-scope" in result.stdout
    source = (BACKEND / "evaluation/research/live.py").read_text(encoding="utf-8")
    assert "fi1_module.FUNDING_IDENTITY_SCOPE = True" in source
    assert '*(["--funding-identity-scope"] if args.funding_identity_scope else [])' in source
