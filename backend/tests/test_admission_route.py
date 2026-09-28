"""ADMISSION_ROUTE: admitted without a declared major, choosing one later."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.adapters.extraction import ClaimBuilder, extract_admission_route, extract_requirements
from app.domain.enums import ClaimType

#: The sentences as KAIST's School of Computing publishes them (cs.kaist.ac.kr,
#: content?menu=40, read 2026-09-27), after a navigation menu with no full stop.
KAIST = "\n".join(
    [
        "KAIST School of Computing",
        "홈",
        "소개",
        "ㆍ학부소개",
        "ㆍ학부발전기금",
        "학부 입학",
        "장학금",
        "Directions",
        "KAIST 학부생은 전공선택 없이 무학과로 입학을 하고 있습니다. "
        "무학과 입학 후 2학기 때 전산을 포함한 전공을 선택하고 있습니다.",
        "이에 대한 자세한 설명은 KAIST 입학처 홈페이지에서 제공하고 있습니다.",
    ]
)


def _builder() -> ClaimBuilder:
    return ClaimBuilder(
        source_url="https://cs.example.edu/admission",
        page_title="Admission",
        official_domain=True,
        extraction_method="html_rule",
        accessed_at=datetime(2026, 9, 27, tzinfo=UTC),
    )


def test_kaist_route_is_read_and_quoted_by_its_own_sentences() -> None:
    claim = extract_admission_route(KAIST, _builder())

    assert claim is not None
    assert claim.normalized_value == "undeclared_then_major_selection"
    assert claim.original_text_excerpt == (
        "KAIST 학부생은 전공선택 없이 무학과로 입학을 하고 있습니다. "
        "무학과 입학 후 2학기 때 전산을 포함한 전공을 선택하고 있습니다."
    )


@pytest.mark.parametrize(
    "text",
    [
        "All first-year students are admitted as undeclared and choose a major later.",
        "Students are admitted without a declared major.",
        "You will declare your major at the end of the first year.",
    ],
)
def test_english_statements_of_the_route(text: str) -> None:
    claim = extract_admission_route(text, _builder())
    assert claim is not None and claim.normalized_value == "undeclared_then_major_selection"


@pytest.mark.parametrize(
    "text",
    [
        "Students may change their major after the first year.",
        "Applicants apply directly to the Computer Science major.",
        "대학원 입학 안내: 전공별로 선발합니다.",
        "The major was founded in the first year of the university's history.",
    ],
)
def test_direct_entry_or_a_change_of_major_is_not_the_route(text: str) -> None:
    assert extract_admission_route(text, _builder()) is None


def test_requirements_extraction_includes_the_route() -> None:
    claims = extract_requirements(KAIST, _builder())
    assert [c.claim_type for c in claims] == [ClaimType.ADMISSION_ROUTE]
