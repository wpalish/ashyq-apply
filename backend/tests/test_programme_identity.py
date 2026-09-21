"""V2-17 — six dimensions, never one score.

The failure being fixed is measured: the pipeline reads official pages
correctly (primary-source rate 13/13) and applies them to the wrong
population, year or programme (wrong-scope claim rate 5/5). Almost every test
here is about refusing to guess the dimension a page does not state.
"""

from __future__ import annotations

import pytest

from app.adapters.search.identity import verify_candidate
from app.adapters.search.intent import DiscoveryIntent
from app.domain.enums import DegreeLevel
from app.domain.programme_identity import (
    IDENTITY_DIMENSIONS,
    SCOPE_DIMENSIONS,
    IdentityState,
    ProgrammeIdentity,
    ScopeState,
    Verdict,
)

Y, N, U = Verdict.YES, Verdict.NO, Verdict.UNKNOWN


def an_intent(**kw) -> DiscoveryIntent:
    return DiscoveryIntent(
        **{
            "institution": "Nazarbayev University",
            "domain": "nu.edu.kz",
            "degree": DegreeLevel.BACHELOR,
            "field": "computer science",
            **kw,
        }
    )


def identity(**kw) -> ProgrammeIdentity:
    return ProgrammeIdentity(**{"exists": Y, "university": Y, "degree_level": Y, "field": Y, **kw})


class TestTheRuleNeverCollapsesIntoOneScore:
    def test_all_four_identity_dimensions_confirmed_is_an_exact_match(self):
        assert identity().identity_state is IdentityState.EXACT
        assert identity().is_exact_match

    def test_one_refuted_dimension_rules_the_candidate_out(self):
        """A wrong degree level is not outweighed by three right dimensions."""
        assert identity(degree_level=N).identity_state is IdentityState.NOT_A_MATCH
        assert identity(field=N).refuted == ("field",)

    def test_an_unconfirmed_dimension_is_not_a_match_and_not_a_failure(self):
        """Invariant I4: an unverified dimension is not a refuted one."""
        result = identity(field=U)

        assert result.identity_state is IdentityState.NEEDS_REVIEW
        assert not result.is_exact_match
        assert result.refuted == ()
        assert result.unresolved[0] == "field"

    def test_a_refutation_beats_an_unknown(self):
        assert identity(field=U, degree_level=N).identity_state is IdentityState.NOT_A_MATCH

    def test_every_dimension_carries_its_reason(self):
        result = ProgrammeIdentity(exists=Y, reasons=(("exists", "the page says so"),))

        assert result.reason("exists") == "the page says so"
        assert "exists=yes (the page says so)" in result.explain()

    def test_asking_for_a_dimension_that_does_not_exist_is_an_error(self):
        with pytest.raises(KeyError, match="vibes"):
            identity().verdict("vibes")

    def test_the_six_dimensions_are_the_guides_six(self):
        assert IDENTITY_DIMENSIONS == ("exists", "university", "degree_level", "field")
        assert SCOPE_DIMENSIONS == ("active", "intake")


class TestScopeIsSeparateFromIdentity:
    def test_the_right_programme_with_an_unknown_intake_is_still_the_right_programme(self):
        """Most pages never state an intake. That must not make them non-matches."""
        result = identity(active=U, intake=U)

        assert result.is_exact_match
        assert result.scope_state is ScopeState.UNKNOWN

    def test_a_discontinued_programme_is_out_of_scope_without_ceasing_to_be_itself(self):
        result = identity(active=N)

        assert result.is_exact_match
        assert result.scope_state is ScopeState.OUT_OF_SCOPE

    def test_in_scope_needs_both_scope_dimensions_confirmed(self):
        assert identity(active=Y, intake=Y).scope_state is ScopeState.IN_SCOPE
        assert identity(active=Y, intake=U).scope_state is ScopeState.UNKNOWN


class TestAppliesToReturnsAVerdictNotABool:
    def test_an_unknown_scope_stays_unknown_rather_than_rounding_either_way(self):
        """This is the wrong-scope failure, in one assertion.

        A bool has nowhere to put "we do not know". Rounding it up states a
        2027 requirement nobody published; rounding it down throws away a real
        fact. The claim is recorded with the scope it has.
        """
        assert identity(active=U, intake=U).applies_to_requested_intake() is U

    def test_confirmed_identity_and_confirmed_scope_is_a_yes(self):
        assert identity(active=Y, intake=Y).applies_to_requested_intake() is Y

    def test_a_wrong_programme_never_applies(self):
        assert identity(field=N, active=Y, intake=Y).applies_to_requested_intake() is N

    def test_an_explicitly_unsupported_intake_never_applies(self):
        assert identity(intake=N).applies_to_requested_intake() is N

    def test_an_unreviewed_identity_does_not_apply_by_default(self):
        assert identity(field=U, active=Y, intake=Y).applies_to_requested_intake() is U


class TestReadingTheDimensionsOffARealCandidate:
    def test_a_full_programme_page_confirms_everything_it_states(self):
        result = verify_candidate(
            url="https://nu.edu.kz/programmes/bsc-computer-science",
            title="BSc Computer Science",
            text="Entry requirements. Applications are open. Entry in 2027.",
            intent=an_intent(intake_year=2027),
        )

        assert result.applies_to_requested_intake() is Y
        assert result.unresolved == ()

    def test_another_institution_is_refuted(self):
        result = verify_candidate(
            url="https://elsewhere.test/programmes/cs", intent=an_intent(), title="Computer Science"
        )

        assert result.university is N

    def test_a_neighbouring_field_is_refuted_not_left_unknown(self):
        """A page that clearly says Data Science has established what it is."""
        result = verify_candidate(
            url="https://nu.edu.kz/programmes/bsc-data-science",
            title="BSc Data Science",
            text="Programme structure.",
            intent=an_intent(),
        )

        assert result.field is N
        assert "neighbouring field" in result.reason("field")

    def test_a_strong_alias_confirms_the_field(self):
        result = verify_candidate(
            url="https://nu.edu.kz/programmes/computing-science",
            title="Computing Science",
            text="Programme.",
            intent=an_intent(),
        )

        assert result.field is Y

    def test_a_page_that_names_no_field_leaves_it_unknown(self):
        result = verify_candidate(
            url="https://nu.edu.kz/programmes/index",
            title="Our programmes",
            text="Programme list.",
            intent=an_intent(),
        )

        assert result.field is U

    def test_the_wrong_degree_level_is_refuted(self):
        result = verify_candidate(
            url="https://nu.edu.kz/programmes/msc-computer-science",
            title="MSc Computer Science",
            text="Programme.",
            intent=an_intent(),
        )

        assert result.degree_level is N

    def test_a_page_naming_no_level_leaves_it_unknown(self):
        result = verify_candidate(
            url="https://nu.edu.kz/programmes/computer-science",
            title="Computer Science",
            text="Programme.",
            intent=an_intent(),
        )

        assert result.degree_level is U


class TestTheAdapterRefusesToGuess:
    def test_an_old_page_is_not_a_discontinued_programme(self):
        """Only an explicit statement moves the active dimension."""
        result = verify_candidate(
            url="https://nu.edu.kz/programmes/cs",
            title="Computer Science",
            text="Programme overview. Last updated 2019.",
            intent=an_intent(),
        )

        assert result.active is U

    @pytest.mark.parametrize(
        "phrase",
        [
            "This programme has been discontinued.",
            "We are no longer accepting applications.",
            "This was the final intake.",
        ],
    )
    def test_an_explicit_closure_is_refuted(self, phrase):
        result = verify_candidate(
            url="https://nu.edu.kz/programmes/cs",
            title="Computer Science",
            text=phrase,
            intent=an_intent(),
        )

        assert result.active is N

    def test_a_year_appearing_on_a_page_is_not_an_intake(self):
        """The single most direct cause of a wrong-scope claim."""
        result = verify_candidate(
            url="https://nu.edu.kz/programmes/cs",
            title="Computer Science",
            text="Our 2027 strategy mentions this programme. Fees were set in 2027 prices.",
            intent=an_intent(intake_year=2027),
        )

        assert result.intake is U
        assert "not as an intake" in result.reason("intake")

    def test_an_explicit_entry_statement_confirms_the_intake(self):
        result = verify_candidate(
            url="https://nu.edu.kz/programmes/cs",
            title="Computer Science",
            text="Entry in September 2027.",
            intent=an_intent(intake_year=2027),
        )

        assert result.intake is Y

    def test_an_explicit_absence_of_an_intake_refutes_it(self):
        result = verify_candidate(
            url="https://nu.edu.kz/programmes/cs",
            title="Computer Science",
            text="There is no intake in 2027 for this programme.",
            intent=an_intent(intake_year=2027),
        )

        assert result.intake is N

    def test_no_requested_intake_means_the_dimension_stays_unknown(self):
        result = verify_candidate(
            url="https://nu.edu.kz/programmes/cs", title="Computer Science", intent=an_intent()
        )

        assert result.intake is U
        assert result.reason("intake") == "no intake was requested"

    def test_a_page_that_is_not_a_programme_page_leaves_existence_unknown(self):
        result = verify_candidate(
            url="https://nu.edu.kz/about",
            title="About us",
            text="We were founded in 2010.",
            intent=an_intent(),
        )

        assert result.exists is U

    def test_an_empty_page_confirms_nothing(self):
        result = verify_candidate(url="https://nu.edu.kz/x", intent=an_intent(intake_year=2027))

        assert set(result.unresolved) >= {"exists", "degree_level", "field", "active", "intake"}
        assert result.applies_to_requested_intake() is U
