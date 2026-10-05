"""A held qualification does not identify the study level an award funds."""

from __future__ import annotations

import pytest

from app.adapters.applicability import assess_degree_applicability

# Verbatim retained paragraphs from the Warsaw notice. First-cycle inclusion
# is conditional on Olympiad/sports achievements, not unconditional eligibility.
_WARSAW_INCLUSION = (
    "The Rector’s Scholarship is available to students admitted to the first year of first-cycle "
    "or long-cycle studies in the year in which they took their final secondary school examination "
    ", provided that they also meet one of the following criteria: 👉 are laureates of an "
    "international olympiad; 👉 are laureates or finalists of a central-level olympiad "
    "(in accordance with the legislation governing the education system); 👉 are medallists "
    "in a sports competition for the title of Polish Champion or a higher title in a given sport "
    "(in accordance with the legislation governing sport);"
)
_WARSAW_MASTER_HOLDERS = (
    "Students in later years of studies who: hold a master’s degree or an equivalent qualification "
    "(regardless of when or where it was obtained);"
)


def test_warsaw_conditional_first_cycle_notice_is_not_a_master_only_award() -> None:
    notice = f"{_WARSAW_INCLUSION}\n{_WARSAW_MASTER_HOLDERS}"
    assessment = assess_degree_applicability(notice, "bachelor")

    assert assessment.verdict == "unknown"
    assert assessment.evidence == ""
    assert assessment.mentioned_degrees == ("master",)


@pytest.mark.parametrize(
    "qualification_statement",
    [
        "The award requires students to hold a master’s degree or equivalent qualification.",
        "Applicants holding a Master’s degree may seek advice from the scholarships office.",
        "Applicants have already obtained an MSc qualification.",
        "The applicant’s previous qualification is a Master of Science degree.",
        "Applicants hold their first master’s degree.",
        "Applicants have completed their first Master’s qualification.",
    ],
)
def test_prior_master_qualifications_do_not_exclude_the_requested_bachelor_level(
    qualification_statement: str,
) -> None:
    assessment = assess_degree_applicability(qualification_statement, "bachelor")

    assert assessment.verdict == "unknown"
    assert assessment.evidence == ""
    assert assessment.mentioned_degrees == ("master",)


def test_prior_bachelor_qualification_does_not_confirm_bachelor_funding() -> None:
    assessment = assess_degree_applicability(
        "Applicants have already obtained their Bachelor’s degree.", "bachelor"
    )

    assert assessment.verdict == "unknown"
    assert assessment.evidence == ""


def test_first_cycle_exception_does_not_create_blanket_bachelor_inclusion() -> None:
    assessment = assess_degree_applicability(_WARSAW_INCLUSION, "bachelor")

    assert assessment.verdict == "unknown"
    assert assessment.mentioned_degrees == ()


@pytest.mark.parametrize(
    ("requested", "expected"),
    [("bachelor", "no"), ("master", "yes")],
)
def test_explicit_master_programme_award_still_settles_its_funded_level(
    requested: str, expected: str
) -> None:
    statement = "The scholarship is available to students enrolled in a Master’s programme."
    assessment = assess_degree_applicability(statement, requested)

    assert assessment.verdict == expected
    assert assessment.evidence
    assert assessment.evidence in statement


def test_explicit_bachelor_exclusion_still_has_negative_source_evidence() -> None:
    statement = "This scholarship excludes bachelor students."
    assessment = assess_degree_applicability(statement, "bachelor")

    assert assessment.verdict == "no"
    assert assessment.evidence
    assert assessment.evidence in statement


def test_explicit_undergraduate_inclusion_remains_positive() -> None:
    statement = "The scholarship is open to undergraduate students."
    assessment = assess_degree_applicability(statement, "bachelor")

    assert assessment.verdict == "yes"
    assert assessment.evidence
    assert assessment.evidence in statement


def test_a_held_master_does_not_hide_a_real_master_programme_in_another_statement() -> None:
    prior = "Applicants hold a Master’s degree."
    funded = "The scholarship is available to students enrolled in a Master’s programme."
    assessment = assess_degree_applicability(f"{prior} {funded}", "bachelor")

    assert assessment.verdict == "no"
    assert assessment.evidence
    assert assessment.evidence in funded


def test_mixed_prior_and_funded_master_mentions_preserve_the_other_level_fallback() -> None:
    # Independent sections separate a prior credential from a real study level;
    # the existing reader's bounded prior-qualification context cannot span them.
    sections = (
        "Applicants hold a Master’s degree. "
        "Academic records and institutional references are reviewed by the awards office. "
        "Please check the published application instructions before submitting materials. "
        "Supported study levels: Master’s programmes."
    )
    assessment = assess_degree_applicability(sections, "bachelor")

    assert assessment.verdict == "no"
    assert assessment.mentioned_degrees == ("master",)


def test_a_held_master_does_not_cancel_an_explicit_undergraduate_funded_level() -> None:
    prior = "Applicants hold a Master’s degree."
    funded = "The scholarship is open to undergraduate students."
    assessment = assess_degree_applicability(f"{prior} {funded}", "bachelor")

    assert assessment.verdict == "yes"
    assert assessment.evidence
    assert assessment.evidence in funded
