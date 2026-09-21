"""V2-22 — filling a claim's scope from what a page states.

The reader's job is small and its refusals are the point: every test here
either proves a page's own words were read, or proves that a page which did
not say something came back silent instead of convenient.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.adapters.extraction import ClaimBuilder
from app.adapters.scope_reader import read_scope
from app.domain.claim_scope import ClaimScope, RequestedScope
from app.domain.enums import ClaimStatus, ClaimType, SourceSpecificity
from app.domain.programme_identity import Verdict


def test_a_page_that_states_its_scope_has_it_read_back() -> None:
    scope = read_scope(
        "Entry requirements for the MSc programme. Applications for the "
        "September 2026 intake open in October. These requirements apply to "
        "international applicants for the academic year 2026/27.",
    )
    assert scope.degree == "master"
    assert scope.intake == "September 2026"
    assert scope.academic_year == "2026/27"
    assert scope.population == "international"


def test_the_title_counts_as_the_page_speaking() -> None:
    """A degree is stated in a title far more often than in prose."""
    scope = read_scope("Admission is competitive.", title="Bachelor's programme in Physics")
    assert scope.degree == "bachelor"


def test_a_page_that_says_nothing_about_who_it_is_for_stays_silent() -> None:
    scope = read_scope("Applicants must submit a transcript and a personal statement.")
    assert scope == ClaimScope()
    assert scope.stated() == ()


def test_naming_two_populations_is_not_naming_one() -> None:
    """A fees page covering both groups is scoped to neither."""
    scope = read_scope("EU/EEA applicants pay no tuition; international applicants pay 12 000 EUR.")
    assert scope.population is None


def test_non_eu_is_never_read_as_eu() -> None:
    assert read_scope("Fees for non-EU/EEA applicants.").population == "non-EU/EEA"


def test_a_negated_sentence_does_not_scope_the_page() -> None:
    """The trap that already cost this pipeline once: a match inside a denial."""
    scope = read_scope("This scholarship is not available to international applicants.")
    assert scope.population is None


def test_a_page_listing_every_intake_is_scoped_to_none_of_them() -> None:
    scope = read_scope("We admit in Fall 2026 and Spring 2027.")
    assert scope.intake is None


def test_autumn_and_fall_are_the_same_intake_not_two() -> None:
    scope = read_scope("Autumn 2026 entry. The Fall 2026 deadline is 15 January.")
    assert scope.intake == "Fall 2026"


def test_a_degree_word_in_passing_does_not_scope_the_page() -> None:
    """'Our master's graduates' says nothing about who this page is for."""
    assert read_scope("Our master's graduates work across Europe.").degree is None


def test_nationality_is_never_guessed() -> None:
    """Documented refusal: no phrase family distinguishes it from provenance."""
    assert read_scope("We welcome applicants from Kazakhstan.").nationality is None


def test_a_claim_records_the_scope_its_page_stated() -> None:
    builder = ClaimBuilder(
        source_url="https://example.edu/msc",
        official_domain=True,
        specificity=SourceSpecificity.PROGRAM,
        scope=read_scope("Requirements for international applicants, Fall 2026 intake."),
        accessed_at=datetime(2026, 9, 21, tzinfo=UTC),
    )
    claim = builder.add(
        ClaimType.IELTS_MIN_OVERALL, 6.5, "IELTS overall 6.5", status=ClaimStatus.VERIFIED_CURRENT
    )
    assert claim is not None
    assert claim.scope is not None
    assert claim.scope.population == "international"
    assert "scope" in claim.model_dump()


def test_a_builder_given_no_scope_records_none_and_serialises_as_before() -> None:
    builder = ClaimBuilder(source_url="https://example.edu/msc", official_domain=False)
    claim = builder.add(ClaimType.IELTS_MIN_OVERALL, 6.5, "IELTS overall 6.5")
    assert claim is not None
    assert claim.scope is None
    assert "scope" not in claim.model_dump()


def test_a_read_scope_answers_the_request_it_actually_matches() -> None:
    """End to end: page words in, a verdict about a request out."""
    scope = read_scope("Entry requirements for international applicants, Fall 2027 intake.")
    assert (
        scope.covers(RequestedScope(population="international", intake="Fall 2027")) is Verdict.YES
    )
    assert scope.covers(RequestedScope(population="domestic", intake="Fall 2027")) is Verdict.NO
    assert (
        scope.covers(RequestedScope(population="international", nationality="KZ"))
        is Verdict.UNKNOWN
    )


def test_a_deadline_date_is_not_an_intake() -> None:
    """The first draft read "15 January 2027" as the intake of 39 demo claims.

    A month and a year are a date; only an intake word beside them, with no
    day number in front, makes them a term.
    """
    assert read_scope("Applications close on 15 January 2027.").intake is None
    assert read_scope("Teaching starts in September 2026.").intake == "September 2026"


def test_the_reversed_form_is_the_same_intake() -> None:
    """Pages written year-first ("2027 Fall intake") say the same thing."""
    assert read_scope("Applications for 2027 Fall intake.").intake == "Fall 2027"


def test_negation_governs_every_dimension_not_just_population() -> None:
    assert (
        read_scope("These rules do not apply in the academic year 2026/2027.").academic_year is None
    )
    assert read_scope("Admission is not open for Fall 2026.").intake is None
    assert read_scope("The programme does not start in September 2026.").intake is None
    assert read_scope("Not applicable to the 2027 Spring intake.").intake is None


def test_a_year_beside_a_figure_is_not_the_page_s_year() -> None:
    """Toronto's demo award, in its own words.

    The page is a 2026/27 one that happens to quote a 2024/25 value. Reading a
    bare year range as the page's scope put the deadline, the coverage and the
    renewal rules of that award under 2024/25 — the deadline-as-intake mistake,
    one dimension over.
    """
    assert read_scope("The award is worth CAD 89,000 per year for 2024/25.").academic_year is None
    assert read_scope("Fees for the academic year 2026/27.").academic_year == "2026/27"
    assert read_scope("Entry in 2026/27 follows these rules.").academic_year == "2026/27"
