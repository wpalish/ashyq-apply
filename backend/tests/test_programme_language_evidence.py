"""A labelled teaching language needs proof in the programme's single claim."""

from __future__ import annotations

from datetime import UTC, datetime
from html import escape
from unittest.mock import Mock

import pytest

from app.adapters.base import AdapterResult, CandidateProgram
from app.adapters.extraction import ClaimBuilder, readable_text
from app.adapters.fetching import Fetcher
from app.adapters.page_classifier import PageClassification, PageType, classify_page
from app.adapters.requirements.web_requirements import WebRequirementsAdapter
from app.adapters.scope_reader import read_scope
from app.domain.claim_verifier import is_verbatim_excerpt, normalize_text
from app.domain.conflicts import find_conflicts
from app.domain.enums import ClaimStatus, ClaimType, DegreeLevel, SourceSpecificity
from app.schemas.claim import MAX_EXCERPT_CHARS, Claim

_TITLE = "Bachelor of Science in Computer Science"
_URL = "https://example.edu/bachelors/computer-science"
_DESCRIPTION = "This three-year degree programme covers algorithms, programming and systems."


def _read_programme(
    *paragraphs: str, navigation: str = "", facts_aside: str = ""
) -> tuple[PageClassification, Claim, str]:
    """Use the classifier and existence reader that consume official HTML."""
    html = (
        f"<html><head><title>{_TITLE}</title></head><body>"
        + (f"<nav>{escape(navigation)}</nav>" if navigation else "")
        + f"<main><h1>{_TITLE}</h1>"
        + "".join(f"<p>{escape(paragraph)}</p>" for paragraph in paragraphs)
        + (f'<aside class="key-facts"><p>{escape(facts_aside)}</p></aside>' if facts_aside else "")
        + "</main></body></html>"
    )
    text = readable_text(html)
    page = classify_page(url=_URL, html=html, text=text)
    assert page.page_type is PageType.PROGRAM_DETAIL
    assert page.subject == _TITLE
    assert page.degree_level == "bachelor"
    builder = ClaimBuilder(
        source_url=_URL,
        page_title=_TITLE,
        specificity=SourceSpecificity.PROGRAM,
        program=_TITLE,
        academic_year="2026/27",
        official_domain=True,
        accessed_at=datetime.now(UTC),
        scope=read_scope(text, title=_TITLE),
        page_text=text,
        page_type=page.page_type.value,
        allowed_domains=["example.edu"],
    )
    fetcher = Mock(spec=Fetcher)
    out = AdapterResult()
    WebRequirementsAdapter(fetcher, "2026/27")._claim_program_exists(
        page,
        CandidateProgram(_TITLE, "computer science", DegreeLevel.BACHELOR, _URL),
        builder,
        out,
        text,
    )
    fetcher.get.assert_not_called()
    assert not out.errors
    assert not builder.rejected
    # A second PROGRAM_EXISTS value would manufacture a conflict instead of
    # repairing the evidence for the programme the first claim already names.
    assert len(builder.claims) == 1
    claim = builder.claims[0]
    assert claim.claim_type is ClaimType.PROGRAM_EXISTS
    assert claim.status is ClaimStatus.VERIFIED_CURRENT
    assert claim.normalized_value["program"] == _TITLE
    assert claim.normalized_value["degree"] == "bachelor"
    assert claim.source_url == _URL
    assert len(claim.original_text_excerpt) <= MAX_EXCERPT_CHARS
    assert is_verbatim_excerpt(claim.original_text_excerpt, text)
    assert find_conflicts(builder.claims)[0] == []
    return page, claim, text


@pytest.mark.parametrize("label", ["Language: Polish", "Language\nPolish"])
def test_labelled_language_has_complete_contiguous_title_and_label_proof(label: str) -> None:
    """Warsaw's field must survive beyond the old title-only quote window."""
    description = _DESCRIPTION + " " + "Practical projects develop programming skills. " * 4
    page, claim, _ = _read_programme(description, label)

    assert page.language_of_instruction == "polish"
    assert claim.normalized_value["language"] == "polish"
    quote = normalize_text(claim.original_text_excerpt)
    assert _TITLE in quote
    assert normalize_text(label) in quote
    # The intervening source text must remain in the same contiguous excerpt.
    assert description.strip() in quote


def test_a_label_at_the_excerpt_cap_is_retained_in_full() -> None:
    label = "Language: Polish"
    # The closest title starts at h1. Including its following separator, the
    # intervening paragraph and the whole label consumes exactly the cap.
    description = "Study details: " + "x" * (
        MAX_EXCERPT_CHARS - len(_TITLE) - len(label) - len("Study details: ") - 2
    )
    assert len(f"{_TITLE} {description} {label}") == MAX_EXCERPT_CHARS
    _, claim, _ = _read_programme(description, label)

    assert claim.normalized_value["language"] == "polish"
    assert normalize_text(claim.original_text_excerpt) == f"{_TITLE} {description} {label}"


def test_a_remote_label_cannot_outlive_its_bounded_proof() -> None:
    page, claim, _ = _read_programme(
        _DESCRIPTION, "Study details: " + "x" * 650, "Language: Polish"
    )

    # The page identifies Polish, but no single permitted excerpt can prove
    # both that field and the complete programme title. Existence still stands.
    assert page.language_of_instruction == "polish"
    assert claim.normalized_value["language"] is None
    assert _TITLE in claim.original_text_excerpt


def test_site_navigation_does_not_supply_the_programmes_language() -> None:
    page, claim, _ = _read_programme(_DESCRIPTION, navigation="Language: Polish")

    assert page.language_of_instruction is None
    assert claim.normalized_value["language"] is None


def test_a_matching_navigation_label_cannot_replace_the_main_content_proof() -> None:
    description = _DESCRIPTION + " " + "Practical projects develop programming skills. " * 4
    page, claim, _ = _read_programme(
        description,
        "Language: Polish",
        navigation="Menu controls\nLanguage: Polish",
    )

    assert page.language_of_instruction == "polish"
    assert claim.normalized_value["language"] == "polish"
    quote = normalize_text(claim.original_text_excerpt)
    assert f"{_TITLE} {description.strip()} Language: Polish" in quote
    assert "Menu controls" not in quote


def test_conflicting_programme_language_fields_abstain() -> None:
    page, claim, _ = _read_programme(_DESCRIPTION, "Language: Polish", "Language: English")

    assert page.language_of_instruction is None
    assert claim.normalized_value["language"] is None


@pytest.mark.parametrize("in_fact_aside", [False, True])
def test_existing_prose_language_route_keeps_its_original_single_claim(in_fact_aside: bool) -> None:
    prose = "This bachelor programme is taught in English."
    if in_fact_aside:
        _, claim, text = _read_programme(facts_aside=prose)
    else:
        _, claim, text = _read_programme(prose)

    assert claim.normalized_value["language"] == "english"
    assert claim.original_text_excerpt == normalize_text(text)
    assert prose in claim.original_text_excerpt
