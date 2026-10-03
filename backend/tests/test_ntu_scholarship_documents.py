"""NTU scholarship submission statements must become the right documents."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.adapters.document_ir import build_document_ir
from app.adapters.documents.web_documents import read_documents
from app.adapters.extraction import ClaimBuilder, html_to_text
from app.adapters.scope_reader import read_scope
from app.domain.claim_verifier import is_verbatim_excerpt, normalize_text
from app.domain.enums import (
    ClaimStatus,
    ClaimType,
    DocumentOwner,
    DocumentPurpose,
    SourceSpecificity,
)
from app.schemas.claim import MAX_EXCERPT_CHARS
from app.schemas.result import DocumentItem

_URL = (
    "https://www.ntu.edu.sg/admissions/undergraduate/scholarships/"
    "scholarship-opportunities/detail/nanyang-scholarship"
)
_TITLE = "Nanyang Global Scholarship"
_ESSAY = "As part of completing the form, a Personal Essay of not more than 250 words is required."
_PHOTO = "upload a recent passport-size photo (digital image)."
_APPRAISAL = (
    "submit a referee's appraisal online. The appraisal is to be completed by your school teacher, "
    "who must not be your family or relative."
)
_APPRAISAL_FOLLOWUP = (
    "After you have submitted your scholarship application, you will be provided with a URL "
    "to be forwarded to your school teacher. When you are passing the link to your teacher, "
    "please inform him/her of your NTU application number and Date of Birth, as he/she will need "
    "the information to submit the appraisal online. Your school teacher is to complete the "
    "online appraisal form and submit it within 7 days of your scholarship application. "
    "If your teacher is not able to submit it online within 7 days and needs more time, please "
    "inform him/her to submit as soon as possible (preferably not more than 2 weeks from your "
    "date of scholarship application). Note that only one online appraisal can be submitted "
    "to support your application."
)
_ELIGIBILITY = (
    "<section><h2>Eligibility</h2><p>Possess outstanding academic achievements in the "
    "Singapore-Cambridge GCE 'A' level, Diploma awarded by a polytechnic in Singapore, "
    "NUS High School Diploma, IB Diploma or Year 12 equivalent qualifications.</p></section>"
)


def _read(body: str, *, navigation: str = "") -> tuple[list[DocumentItem], ClaimBuilder, str]:
    """The real reader receives the same text and structural IR as its adapter."""
    html = (
        f"<html><head><title>{_TITLE}</title></head><body>"
        + (f"<nav>{navigation}</nav>" if navigation else "")
        + f"<main><h1>{_TITLE}</h1>{body}</main></body></html>"
    )
    text = html_to_text(html)
    scope = read_scope(text, title=_TITLE)
    builder = ClaimBuilder(
        source_url=_URL,
        page_title=_TITLE,
        specificity=SourceSpecificity.PROGRAM_INTAKE,
        program="Computer Science",
        academic_year="2026/27",
        official_domain=True,
        accessed_at=datetime(2026, 9, 29, tzinfo=UTC),
        scope=scope,
        page_text=text,
        allowed_domains=["ntu.edu.sg"],
    )
    items = read_documents(
        text,
        _URL,
        DocumentPurpose.SCHOLARSHIP,
        scope,
        builder,
        document=build_document_ir(html, _URL),
    )
    assert not builder.rejected
    for claim in builder.claims:
        assert claim.source_url == _URL
        assert claim.official_domain
        assert claim.status is ClaimStatus.VERIFIED_CURRENT
        assert 0 < len(claim.original_text_excerpt) <= MAX_EXCERPT_CHARS
        assert is_verbatim_excerpt(claim.original_text_excerpt, text)
    for item in items:
        assert item.purpose is DocumentPurpose.SCHOLARSHIP
        assert item.source_url == _URL
        assert item.claim_ids == [_URL]
        assert item.scope is not None
    return items, builder, text


def _required_claim_for(builder: ClaimBuilder, item: DocumentItem):
    claims = [
        claim
        for claim in builder.claims
        if claim.claim_type is ClaimType.REQUIRED_DOCUMENT and claim.normalized_value == item.name
    ]
    assert len(claims) == 1
    return claims[0]


@pytest.mark.parametrize(
    ("body", "navigation"),
    [
        ("", '<a href="/financial-matters">Financial Matters</a>'),
        (_ELIGIBILITY, ""),
        ("<p>You may optionally submit a personal statement.</p>", ""),
        ("<p>An academic reference is not required.</p>", ""),
        ("<p>A Personal Essay of not more than 250 words is an optional exercise.</p>", ""),
        ("<p>Our alumni discuss referee appraisals and school teachers in their blogs.</p>", ""),
    ],
    ids=[
        "financial-navigation",
        "diploma-eligibility",
        "optional-personal-statement",
        "reference-not-required",
        "optional-personal-essay",
        "appraisal-context-only",
    ],
)
def test_mentions_and_optional_documents_do_not_become_submission_requirements(
    body: str, navigation: str
) -> None:
    items, builder, _ = _read(body, navigation=navigation)

    assert not any(item.required for item in items)
    assert not any(claim.claim_type is ClaimType.REQUIRED_DOCUMENT for claim in builder.claims)
    assert not any(
        claim.claim_type in {ClaimType.ESSAY_PROMPT, ClaimType.RECOMMENDATION_REQUIREMENT}
        for claim in builder.claims
    )


def test_a_digital_passport_size_photo_is_not_a_passport_identity_page() -> None:
    items, builder, _ = _read(
        "<section><h2>Application Procedures</h2>"
        "<p>Applicants are required to submit the following after completing your application form:</p>"
        f"<ul><li>{_PHOTO}</li></ul></section>"
    )

    assert len(items) == 1
    photo = items[0]
    assert "photo" in photo.name.casefold()
    assert "identity page" not in photo.name.casefold()
    assert photo.owner is DocumentOwner.APPLICANT
    assert photo.required
    assert _PHOTO in normalize_text(_required_claim_for(builder, photo).original_text_excerpt)


def test_a_repeated_photo_requirement_cannot_fall_through_to_a_passport_copy() -> None:
    items, builder, _ = _read(
        "<section><h2>Application Procedures</h2>"
        "<p>Applicants are required to submit the following after completing your application form: "
        + _PHOTO
        + "</p><p>After completing your application form, applicants are required to submit "
        "the following: " + _PHOTO + "</p></section>"
    )

    assert len(items) == 1
    photo = items[0]
    assert "photo" in photo.name.casefold()
    assert photo.owner is DocumentOwner.APPLICANT
    assert _PHOTO in normalize_text(_required_claim_for(builder, photo).original_text_excerpt)
    assert len(builder.claims) == 1


def test_an_explicit_required_documents_table_keeps_its_transcript_row() -> None:
    items, builder, _ = _read(
        "<section><h2>Required documents</h2><table>"
        "<tr><th>Document</th><th>Format</th></tr>"
        "<tr><td>Full academic transcript</td><td>PDF</td></tr></table></section>"
    )

    assert len(items) == 1
    transcript = items[0]
    assert transcript.name == "Full academic transcript"
    assert transcript.owner is DocumentOwner.SCHOOL
    assert transcript.required
    assert (
        "Full academic transcript" in _required_claim_for(builder, transcript).original_text_excerpt
    )


@pytest.mark.parametrize(
    "denial",
    ["This document is optional.", "This transcript is not required."],
    ids=["optional-completion-document", "completion-document-not-required"],
)
def test_completion_form_facts_do_not_make_an_optional_document_required(denial: str) -> None:
    items, builder, _ = _read(
        "<h3>Transcript</h3><p>Scan of your academic record or if not yet completed: "
        f"school-issued list of your courses. {denial}</p>"
    )

    forms = [
        claim for claim in builder.claims if claim.claim_type is ClaimType.DOCUMENT_BY_COMPLETION
    ]
    assert len(forms) == 2
    assert {claim.normalized_value["status"] for claim in forms} == {"completed", "not_completed"}
    assert all(denial in claim.original_text_excerpt for claim in forms)
    assert not any(item.required for item in items)
    assert not any(claim.claim_type is ClaimType.REQUIRED_DOCUMENT for claim in builder.claims)


def test_the_required_personal_essay_retains_its_250_word_limit() -> None:
    items, builder, _ = _read(
        f"<section><h2>Application Procedures</h2><p>{_ESSAY} "
        "The scholarship application form includes 1 compulsory topic for you to write on.</p></section>"
    )

    assert len(items) == 1
    essay = items[0]
    assert essay.owner is DocumentOwner.APPLICANT
    assert essay.required
    assert essay.word_limit == 250
    assert _ESSAY in normalize_text(_required_claim_for(builder, essay).original_text_excerpt)
    limits = [claim for claim in builder.claims if claim.claim_type is ClaimType.ESSAY_PROMPT]
    assert len(limits) == 1
    assert limits[0].normalized_value == {"document": essay.name, "word_limit": 250}
    assert _ESSAY in normalize_text(limits[0].original_text_excerpt)


def test_a_long_appraisal_paragraph_keeps_the_school_teacher_and_non_relative_proof() -> None:
    paragraph = f"{_APPRAISAL} {_APPRAISAL_FOLLOWUP}"
    assert len(paragraph) > MAX_EXCERPT_CHARS
    items, builder, text = _read(
        "<section><h2>Application Procedures</h2>"
        "<p>Applicants are required to submit the following:</p>"
        f"<ul><li>{paragraph}</li></ul></section>"
    )

    assert any(len(line) > MAX_EXCERPT_CHARS for line in text.splitlines())
    assert len(items) == 1
    appraisal = items[0]
    assert appraisal.required
    assert appraisal.owner is DocumentOwner.RECOMMENDER
    assert _APPRAISAL in normalize_text(
        _required_claim_for(builder, appraisal).original_text_excerpt
    )
    recommendations = [
        claim
        for claim in builder.claims
        if claim.claim_type is ClaimType.RECOMMENDATION_REQUIREMENT
    ]
    assert len(recommendations) == 1
    assert recommendations[0].normalized_value == {
        "document": appraisal.name,
        "role": "school_teacher",
        "family_or_relative_allowed": False,
    }
    assert _APPRAISAL in normalize_text(recommendations[0].original_text_excerpt)


def test_the_source_shaped_scholarship_has_only_its_three_actual_submission_items() -> None:
    items, builder, _ = _read(
        _ELIGIBILITY
        + "<section><h2>Application Procedures</h2>"
        + f"<p>{_ESSAY}</p>"
        + "<p>Applicants are required to submit the following:</p>"
        + f"<ul><li>{_PHOTO}</li><li>{_APPRAISAL} {_APPRAISAL_FOLLOWUP}</li></ul></section>",
        navigation='<a href="/financial-matters">Financial Matters</a>',
    )

    assert len(items) == 3
    assert sum(item.owner is DocumentOwner.APPLICANT for item in items) == 2
    assert sum(item.owner is DocumentOwner.RECOMMENDER for item in items) == 1
    assert sum(item.word_limit == 250 for item in items) == 1
    assert all(item.required for item in items)
    assert all("diploma" not in item.name.casefold() for item in items)
    assert all("financial" not in item.name.casefold() for item in items)
    assert all("identity page" not in item.name.casefold() for item in items)
    for item in items:
        _required_claim_for(builder, item)


def test_another_section_cannot_scope_the_document_population():
    items, builder, _ = _read(
        "<h2>Tuition grant</h2><p>International students have a service bond.</p>"
        f"<h2>Application Procedures</h2><p>{_ESSAY}</p>"
    )
    assert items and builder.claims
    assert all(item.scope.population is None for item in items)
    assert all(claim.scope.population is None for claim in builder.claims)
    assert builder.meta["scope"].population == "international"


def test_document_heading_retains_its_explicit_population():
    items, builder, _ = _read(f"<h2>International applicants</h2><p>{_ESSAY}</p>")
    assert all(item.scope.population == "international" for item in items)
    assert all(claim.scope.population == "international" for claim in builder.claims)


@pytest.mark.parametrize(
    "statement",
    [
        "submit a referee's appraisal online. The appraisal may be completed by your school teacher.",
        "submit a referee's appraisal online. If shortlisted, the appraisal must be completed by your school teacher.",
        "submit a referee's appraisal online. The appraisal is to be completed by your school teacher unless exempted.",
        "submit a referee's appraisal online. Your school teacher can provide advice.",
    ],
)
def test_referee_roles_are_not_guessed_or_stripped_of_conditions(statement):
    _, builder, _ = _read(f"<p>{statement}</p>")
    assert all(
        not isinstance(c.normalized_value, dict)
        for c in builder.claims
        if c.claim_type is ClaimType.RECOMMENDATION_REQUIREMENT
    )


def test_a_referee_role_does_not_imply_a_family_exclusion():
    _, builder, _ = _read(
        "<p>submit a referee's appraisal online. "
        "The appraisal must be completed by a university lecturer.</p>"
    )
    values = [
        c.normalized_value
        for c in builder.claims
        if c.claim_type is ClaimType.RECOMMENDATION_REQUIREMENT
    ]
    assert values == [{"document": "Referee appraisal", "role": "university_lecturer"}]


@pytest.mark.asyncio
@pytest.mark.parametrize("foreign", [False, True])
async def test_document_redirect_uses_final_source_or_rejects_foreign_site(tmp_path, foreign):
    from unittest.mock import AsyncMock

    from app.adapters.base import AdapterResult, Candidate, CandidateProgram
    from app.adapters.documents.web_documents import WebDocumentsAdapter
    from app.adapters.fetching import Fetcher, FetchResult
    from app.domain.enums import DegreeLevel, FetchOutcome

    final = (
        "https://foreign.example/scholarship"
        if foreign
        else "https://www.ntu.edu.sg/admissions/scholarships/current"
    )
    html = f"<h1>{_TITLE}</h1><p>{_ESSAY}</p>"
    async with Fetcher(tmp_path) as fetcher:
        fetcher.get = AsyncMock(  # type: ignore[method-assign]
            return_value=FetchResult(_URL, FetchOutcome.OK, text=html, final_url=final)
        )
        out = AdapterResult()
        items = await WebDocumentsAdapter(fetcher, "2026/27")._from_page(
            Candidate("NTU", "Singapore", "Singapore", "ntu.edu.sg"),
            CandidateProgram("Computer Science", "computer science", DegreeLevel.BACHELOR),
            _URL,
            DocumentPurpose.SCHOLARSHIP,
            out,
        )
    if foreign:
        assert items == []
        assert out.claims == []
        assert out.pages_failed == 1
        assert out.page_outcomes[0].detail == "cross-site redirect"
    else:
        assert items and out.claims
        assert all(item.source_url == final and item.claim_ids == [final] for item in items)
        assert all(claim.source_url == final for claim in out.claims)
        assert out.pages_failed == 0
