"""Fetched programme titles prove identity without widening requirement text."""

from __future__ import annotations

from datetime import UTC, datetime
from html import escape
from unittest.mock import AsyncMock, Mock

import pytest

from app.adapters.base import AdapterResult, Candidate, CandidateProgram
from app.adapters.extraction import ClaimBuilder, html_title, html_to_text, readable_text
from app.adapters.fetching import Fetcher, FetchResult
from app.adapters.page_classifier import PageType, classify_page
from app.adapters.requirements.web_requirements import WebRequirementsAdapter
from app.adapters.scope_reader import read_scope
from app.domain.claim_verifier import RejectReason, is_verbatim_excerpt
from app.domain.enums import ClaimStatus, ClaimType, DegreeLevel, FetchOutcome, SourceSpecificity
from app.schemas.claim import MAX_EXCERPT_CHARS, Claim

_TITLE = "Bachelor of Science in Mathematical and Computer Sciences"
_SECOND_TITLE = "Bachelor of Computing in Computer Science with Second Major in Business (International Trading)"
_URL = "https://www.ntu.edu.sg/education/undergraduate-programme/mathematical-and-computer-sciences"
_BODY = (
    "This double major combines mathematics and computing to solve complex real-world challenges. "
    "The degree programme develops strong foundations in both disciplines through practical "
    "projects, algorithms and scientific methods. Entry requirements: IELTS overall band of 7.0."
)
_READ_AT = datetime(2026, 9, 29, 8, 29, tzinfo=UTC)


def _html(
    *,
    title: str | None = _TITLE,
    heading: str | None = _TITLE,
    body: str = _BODY,
    chrome: str = "",
) -> str:
    """NTU's degree heading is outside the selected programme article."""
    head = f"<title>{escape(title)} | NTU Singapore</title>" if title is not None else ""
    hero = f'<h1 class="detail-header__title">{escape(heading)}</h1>' if heading is not None else ""
    return (
        f"<html><head>{head}</head><body>{hero}"
        f"<nav>{escape(chrome)}</nav>"
        f'<article class="programme-detail__details"><p>{escape(body)}</p></article>'
        "</body></html>"
    )


async def _verify(html: str, *, requested: str = _TITLE) -> AdapterResult:
    fetched = FetchResult(
        url=_URL,
        final_url=_URL,
        outcome=FetchOutcome.CACHED,
        status_code=200,
        content_type="text/html",
        content=html.encode(),
        text=html,
        fetched_at=_READ_AT,
    )
    fetcher = Mock(spec=Fetcher)
    fetcher.get = AsyncMock(return_value=fetched)
    candidate = Candidate(
        name="Nanyang Technological University",
        country="Singapore",
        city="Singapore",
        domain="ntu.edu.sg",
    )
    program = CandidateProgram(requested, "computer science", DegreeLevel.BACHELOR, _URL)
    result = await WebRequirementsAdapter(fetcher, "2026/27").verify(
        candidate, program, "fall 2027"
    )
    fetcher.get.assert_awaited_once_with(_URL)
    return result


def _identities(result: AdapterResult) -> list[Claim]:
    return [c for c in result.claims if c.claim_type is ClaimType.PROGRAM_EXISTS]


@pytest.mark.asyncio
@pytest.mark.parametrize("title", [_TITLE, _SECOND_TITLE])
async def test_fetched_title_proves_identity_when_article_does_not_repeat_it(title: str) -> None:
    html = _html(title=title, heading=title)
    text = readable_text(html)
    page = classify_page(url=_URL, html=html, text=text)
    assert page.page_type is PageType.PROGRAM_DETAIL
    assert page.subject == title
    assert title not in text

    result = await _verify(html, requested=title)
    claims = _identities(result)
    assert len(claims) == 1
    claim = claims[0]
    assert claim.normalized_value["program"] == title
    assert claim.normalized_value["degree"] == "bachelor"
    assert claim.normalized_value["language"] is None
    assert claim.status is ClaimStatus.VERIFIED_CURRENT
    assert claim.source_url == _URL
    assert claim.accessed_at == _READ_AT
    assert len(claim.original_text_excerpt) <= MAX_EXCERPT_CHARS
    assert title in claim.original_text_excerpt
    assert is_verbatim_excerpt(claim.original_text_excerpt, html_to_text(html))
    assert not is_verbatim_excerpt(claim.original_text_excerpt, text)


@pytest.mark.asyncio
async def test_actual_heading_fallback_is_allowed_when_html_title_is_absent() -> None:
    html = _html(title=None)
    assert html_title(html) == _TITLE
    assert _TITLE not in readable_text(html)
    claims = _identities(await _verify(html))
    assert len(claims) == 1
    assert is_verbatim_excerpt(claims[0].original_text_excerpt, html_to_text(html))


@pytest.mark.asyncio
async def test_identity_title_does_not_become_requirement_extraction_context() -> None:
    html = _html(
        title=f"{_TITLE} | IELTS overall band of 9.0",
        chrome="SAT minimum score 1550. Application fee SGD 200. IELTS overall band of 8.5.",
    )
    text = readable_text(html)
    result = await _verify(html)
    assert len(_identities(result)) == 1
    ielts = [c for c in result.claims if c.claim_type is ClaimType.IELTS_MIN_OVERALL]
    assert [c.normalized_value for c in ielts] == [7.0]
    assert all(is_verbatim_excerpt(c.original_text_excerpt, text) for c in ielts)
    assert not any(c.claim_type is ClaimType.APPLICATION_FEE for c in result.claims)
    for claim in result.claims:
        if claim.claim_type is not ClaimType.PROGRAM_EXISTS:
            assert is_verbatim_excerpt(claim.original_text_excerpt, text)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "language_statement",
    ["This bachelor programme is taught in English.", "Language: Polish"],
)
async def test_title_fallback_does_not_add_language_without_contiguous_proof(
    language_statement: str,
) -> None:
    html = _html(body=f"{_BODY}\n{language_statement}")
    page = classify_page(url=_URL, html=html, text=readable_text(html))
    assert page.language_of_instruction in {"english", "polish"}
    assert _TITLE not in readable_text(html)

    claims = _identities(await _verify(html))
    assert len(claims) == 1
    assert claims[0].normalized_value["language"] is None
    assert language_statement not in claims[0].original_text_excerpt
    assert is_verbatim_excerpt(claims[0].original_text_excerpt, html_to_text(html))


@pytest.mark.asyncio
async def test_an_unrelated_fetched_degree_title_cannot_confirm_the_requested_programme() -> None:
    other = "Bachelor of Science in Chemistry"
    html = _html(title=other, heading=other)
    result = await _verify(html)
    assert _identities(result) == []
    assert any("not confirming" in error for error in result.errors)


@pytest.mark.asyncio
async def test_requested_name_and_url_cannot_supply_a_missing_source_title() -> None:
    result = await _verify(_html(title=None, heading=None))
    assert _identities(result) == []
    assert result.errors


def test_legacy_reader_refuses_unproven_identity_and_surfaces_verifier_diagnostic() -> None:
    """Classification metadata alone is not verbatim evidence in the reader."""
    html = _html()
    text = readable_text(html)
    page = classify_page(url=_URL, html=html, text=text)
    assert page.page_type is PageType.PROGRAM_DETAIL
    builder = ClaimBuilder(
        source_url=_URL,
        page_title=html_title(html),
        specificity=SourceSpecificity.PROGRAM,
        program=_TITLE,
        official_domain=True,
        accessed_at=_READ_AT,
        scope=read_scope(text, title=html_title(html)),
        page_text=text,
        page_type=page.page_type.value,
        allowed_domains=["ntu.edu.sg"],
    )
    fetcher = Mock(spec=Fetcher)
    result = AdapterResult()
    WebRequirementsAdapter(fetcher, "2026/27")._claim_program_exists(
        page,
        CandidateProgram(_TITLE, "computer science", DegreeLevel.BACHELOR, _URL),
        builder,
        result,
        text,
    )
    fetcher.get.assert_not_called()
    assert builder.claims == []
    assert builder.rejected
    assert builder.rejected[0][2] is RejectReason.EXCERPT_NOT_VERBATIM
    assert any(_URL in error and "excerpt_not_verbatim" in error for error in result.errors)
