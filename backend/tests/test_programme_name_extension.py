"""Plan v3 change #3: verify-side programme identity (loss stages v3 2026-10-18 §2).

KIT's gold page ``…/english/vorstudium/bachelor-informatics.php`` was found at
HEAD but ``programme.exists`` was never claimed: ``_program_name_from_url``
stripped only ``.html``, so the programme was named "Bachelor Informatics.Php",
"php" became a requested subject word (overlap 2/4 < 0.6), and
``_named_after_its_url`` missed the placeholder for the same reason. The fix
(on, no flag) strips any page extension in both. ``ALIAS_AWARE_PROGRAM_MATCH``
(off) lets the match accept a subject that names the field or one of its
aliases by discovery's own field predicate. Offline: pages written for the test.
"""

from __future__ import annotations

import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock

import pytest

from app.adapters import matching
from app.adapters.base import AdapterResult, CandidateProgram
from app.adapters.discovery.live_discovery import _program_name_from_url, strip_url_extension
from app.adapters.extraction import ClaimBuilder, readable_text
from app.adapters.fetching import Fetcher
from app.adapters.matching import program_matches
from app.adapters.page_classifier import PageType, classify_page
from app.adapters.requirements.web_requirements import (
    WebRequirementsAdapter,
    _named_after_its_url,
)
from app.adapters.scope_reader import read_scope
from app.domain.enums import ClaimType, DegreeLevel, SourceSpecificity
from app.schemas.claim import Claim

BACKEND = Path(__file__).resolve().parents[1]
CS = "computer science"
KIT_EN = "https://www.sle.kit.edu/english/vorstudium/bachelor-informatics.php"
KIT_DE = "https://www.sle.kit.edu/vorstudium/bachelor-informatik.php"
KIT_EN_TITLE = "KIT - Study programs - Informatics Bachelor of Science"
KIT_DE_TITLE = "KIT - Studiengänge - Informatik Bachelor"


@pytest.fixture(params=[False, True], ids=["alias-off", "alias-on"])
def alias(request, monkeypatch) -> bool:
    monkeypatch.setattr(matching, "ALIAS_AWARE_PROGRAM_MATCH", request.param)
    return request.param


def test_alias_aware_match_is_off_by_default() -> None:
    assert matching.ALIAS_AWARE_PROGRAM_MATCH is True


# --- the extension fix (on by default) ------------------------------------------------


@pytest.mark.parametrize(
    ("url", "name"),
    [
        (KIT_EN, "Bachelor Informatics"),
        ("https://u.example/study/computer-science.php", "Computer Science"),
        ("https://u.example/study/computer-science.aspx", "Computer Science"),
        ("https://u.example/study/computer_science.asp", "Computer Science"),
        ("https://u.example/study/computer-science.jsp", "Computer Science"),
        ("https://u.example/study/computer-science.htm", "Computer Science"),
        ("https://u.example/study/computer-science.HTM", "Computer Science"),
        ("https://u.example/study/computer-science.cfm", "Computer Science"),
        # Unchanged: .html was stripped before, digits and bare slugs as before.
        ("https://u.example/study/computer-science.html", "Computer Science"),
        ("https://u.example/study/computing-beng/", "Computing Beng"),
        ("https://u.example/study/12345.html", "12345"),
        ("https://u.example/study/12506.php", "12506"),
        ("https://u.example/study/2027/", "computer science (bachelor)"),
        ("https://u.example/study/node.js-course", "Node.Js Course"),
    ],
)
def test_program_name_from_url_strips_any_page_extension(url: str, name: str) -> None:
    assert _program_name_from_url(url, [CS], "bachelor") == name


def test_strip_url_extension_only_at_the_end() -> None:
    assert strip_url_extension("bachelor-informatics.php") == "bachelor-informatics"
    assert strip_url_extension("php-programming") == "php-programming"
    assert strip_url_extension("informatics.phpx") == "informatics.phpx"


@pytest.mark.parametrize(
    "url",
    [KIT_EN, KIT_DE, "https://u.example/a/computer-science.aspx", "https://u.example/a/cs.htm"],
)
def test_named_after_its_url_sees_the_placeholder_behind_any_extension(url: str) -> None:
    name = _program_name_from_url(url, [CS], "bachelor")
    assert _named_after_its_url(CandidateProgram(name, CS, DegreeLevel.BACHELOR, url))


def test_a_registry_name_is_not_a_placeholder() -> None:
    program = CandidateProgram("Informatics", CS, DegreeLevel.BACHELOR, KIT_EN)
    assert not _named_after_its_url(program)


def test_kit_matches_once_the_extension_is_gone(alias) -> None:
    name = _program_name_from_url(KIT_EN, [CS], "bachelor")
    matched, why = program_matches(name, CS, KIT_EN_TITLE, "bachelor", "bachelor")
    assert matched, why
    # The name the analysis found in the raw claim: refused, 2 of 4 words.
    old, _ = program_matches("Bachelor Informatics.Php", CS, KIT_EN_TITLE, "bachelor", "bachelor")
    assert not old


# --- programme.exists through the requirements reader ---------------------------------


def _html(title: str) -> str:
    return (
        f'<html lang="en"><head><title>{title}</title></head><body><main><h1>{title}</h1>'
        "<p>The bachelor programme takes six semesters and 180 ECTS credits. Admission "
        "requirements and application deadline: 15 July. Language of instruction: German."
        "</p></main></body></html>"
    )


def _claim(url: str, title: str, name: str | None = None) -> tuple[list[Claim], list[str]]:
    html = _html(title)
    text = readable_text(html)
    page = classify_page(url=url, html=html, text=text)
    assert page.page_type is PageType.PROGRAM_DETAIL
    name = name if name is not None else _program_name_from_url(url, [CS], "bachelor")
    builder = ClaimBuilder(
        source_url=url,
        page_title=title,
        specificity=SourceSpecificity.PROGRAM,
        program=name,
        academic_year="2026/27",
        official_domain=True,
        accessed_at=datetime.now(UTC),
        scope=read_scope(text, title=title),
        page_text=text,
        page_type=page.page_type.value,
        allowed_domains=["kit.edu", "u.example"],
    )
    out = AdapterResult()
    WebRequirementsAdapter(Mock(spec=Fetcher), "2026/27")._claim_program_exists(
        page, CandidateProgram(name, CS, DegreeLevel.BACHELOR, url), builder, out, text
    )
    exists = [c for c in builder.claims if c.claim_type is ClaimType.PROGRAM_EXISTS]
    return exists, out.errors


def test_kit_programme_exists_is_claimed(alias) -> None:
    exists, errors = _claim(KIT_EN, KIT_EN_TITLE)
    assert len(exists) == 1, errors
    assert exists[0].normalized_value["program"] == KIT_EN_TITLE


def test_kit_german_page_needs_the_alias(alias) -> None:
    # "Informatik" shares one word with "Bachelor Informatik" + "computer science".
    exists, errors = _claim(KIT_DE, KIT_DE_TITLE)
    assert len(exists) == (1 if alias else 0), errors


def test_an_opaque_url_page_naming_an_alias_needs_the_alias(alias) -> None:
    url = "https://u.example/english/12506.php"
    exists, errors = _claim(url, "Informatics Bachelor of Science")
    assert len(exists) == (1 if alias else 0), errors


def test_business_informatics_is_refused_either_way(alias) -> None:
    url = "https://u.example/english/bachelor-business-informatics.php"
    exists, errors = _claim(url, "Business Informatics Bachelor of Science")
    assert exists == []
    assert any("does not name the requested field" in e for e in errors), errors


def test_a_registry_name_of_another_programme_is_not_matched_through_aliases(alias) -> None:
    exists, errors = _claim(
        "https://u.example/english/12506.php", "Informatics Bachelor of Science", "Data Science"
    )
    assert exists == [], errors


def test_another_level_is_still_a_hard_no(monkeypatch) -> None:
    monkeypatch.setattr(matching, "ALIAS_AWARE_PROGRAM_MATCH", True)
    matched, why = program_matches(
        "12506", CS, "Informatics", "bachelor", "master", subject_names_field=True
    )
    assert not matched and "master" in why


def test_harness_exposes_and_forwards_the_flag() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "evaluation.research.live", "--help"],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "--alias-aware-program-match" in result.stdout
    source = (BACKEND / "evaluation/research/live.py").read_text(encoding="utf-8")
    assert "am1_module.ALIAS_AWARE_PROGRAM_MATCH = True" in source
    assert '["--alias-aware-program-match"]' in source
