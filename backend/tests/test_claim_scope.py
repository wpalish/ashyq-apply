"""V2-21 — who a published rule actually applies to.

The benchmark measured five claims out of five as the right fact about the
wrong population, year or programme. Every test here is about refusing the
one move that produces that: treating silence as agreement.
"""

from __future__ import annotations

import pytest

from app.domain.claim_scope import SCOPE_DIMENSIONS, ClaimScope, RequestedScope
from app.domain.programme_identity import Verdict

Y, N, U = Verdict.YES, Verdict.NO, Verdict.UNKNOWN


def a_request(**kw) -> RequestedScope:
    return RequestedScope(
        **{
            "university": "Nazarbayev University",
            "programme": "Computer Science",
            "degree": "bachelor",
            "intake": "fall 2027",
            "population": "international",
            **kw,
        }
    )


def a_scope(**kw) -> ClaimScope:
    return ClaimScope(
        **{
            "university": "Nazarbayev University",
            "programme": "Computer Science",
            "degree": "bachelor",
            "intake": "fall 2027",
            "population": "international",
            **kw,
        }
    )


class TestSilenceIsNotAgreement:
    def test_a_page_that_does_not_say_who_it_is_for_does_not_answer_the_question(self):
        """The wrong-scope failure, in one assertion.

        This is the common case and today it passes silently as a match. The
        claim is real; what is unestablished is who it is about.
        """
        scope = ClaimScope(
            university="Nazarbayev University", programme="Computer Science", degree="bachelor"
        )

        assert scope.covers(a_request()) is U
        assert set(scope.gaps(a_request())) == {"intake", "population"}

    def test_an_empty_scope_covers_nothing_rather_than_everything(self):
        assert ClaimScope().covers(a_request()) is U
        assert ClaimScope().stated() == ()

    def test_a_request_that_asks_nothing_is_answered_by_nothing(self):
        """Otherwise an unscoped question matches every claim ever made."""
        assert a_scope().covers(RequestedScope()) is U

    def test_a_dimension_the_request_does_not_name_is_not_a_gap(self):
        """A page stating more than was asked is not thereby unusable."""
        scope = a_scope(nationality="Kazakhstan", residency="outside the EU")

        assert scope.covers(a_request()) is Y


class TestContradictionRefuses:
    def test_a_different_intake_refutes_the_claim(self):
        assert a_scope(intake="fall 2026").covers(a_request()) is N

    def test_a_different_population_refutes_the_claim(self):
        """A rule for non-EU applicants is not the rule for this applicant."""
        assert a_scope(population="non-EU/EEA").covers(a_request()) is N

    def test_a_contradiction_outranks_a_gap(self):
        scope = ClaimScope(university="Nazarbayev University", intake="fall 2026")

        assert scope.covers(a_request()) is N
        assert scope.contradictions(a_request()) == ("intake",)

    def test_every_contradicting_dimension_is_named(self):
        scope = a_scope(intake="fall 2026", population="non-EU/EEA")

        assert set(scope.contradictions(a_request())) == {"intake", "population"}

    def test_case_and_spacing_do_not_make_a_contradiction(self):
        assert a_scope(degree=" Bachelor ").covers(a_request()) is Y

    def test_values_that_merely_look_alike_are_not_the_same_scope(self):
        """Two scopes are two scopes until something authoritative says otherwise."""
        assert a_scope(programme="Computer Science and Engineering").covers(a_request()) is N


class TestWhatItReportsToAReviewer:
    def test_gaps_are_named_so_they_can_be_closed(self):
        """A confidence number names nothing; a missing dimension names itself."""
        scope = ClaimScope(university="Nazarbayev University")

        assert set(scope.gaps(a_request())) == {"programme", "degree", "intake", "population"}

    def test_it_explains_each_verdict_in_one_line(self):
        assert "does not apply" in a_scope(intake="fall 2026").explain(a_request())
        assert "does not state" in ClaimScope(university="Nazarbayev University").explain(
            a_request()
        )
        assert "applies" in a_scope().explain(a_request())

    def test_unstated_dimensions_are_listed(self):
        scope = ClaimScope(university="Nazarbayev University")

        assert "faculty" in scope.unstated()
        assert "university" not in scope.unstated()


class TestPreferringTheMoreSpecificClaim:
    def test_a_superset_of_dimensions_is_narrower(self):
        broad = ClaimScope(university="Nazarbayev University")
        narrow = ClaimScope(university="Nazarbayev University", programme="Computer Science")

        assert narrow.narrower_than(broad)
        assert not broad.narrower_than(narrow)

    def test_two_different_single_dimensions_do_not_rank(self):
        """A programme scope and a nationality scope are not comparable."""
        by_programme = ClaimScope(programme="Computer Science")
        by_nationality = ClaimScope(nationality="Kazakhstan")

        assert not by_programme.narrower_than(by_nationality)
        assert not by_nationality.narrower_than(by_programme)

    def test_an_identical_scope_is_not_narrower_than_itself(self):
        assert not a_scope().narrower_than(a_scope())


class TestBuildingOneFromLooseData:
    def test_unknown_keys_are_ignored_and_known_ones_are_kept(self):
        scope = ClaimScope.from_mapping(
            {"programme": "Computer Science", "qualification": "NIS", "degree": "bachelor"}
        )

        assert scope.programme == "Computer Science"
        assert scope.degree == "bachelor"

    def test_empty_values_stay_unknown_rather_than_becoming_empty_strings(self):
        scope = ClaimScope.from_mapping({"programme": "", "intake": None})

        assert scope.programme is None
        assert scope.unstated() == SCOPE_DIMENSIONS


class TestTheDimensionsAreTheGuides:
    def test_all_nine_are_present_and_named(self):
        assert SCOPE_DIMENSIONS == (
            "university",
            "faculty",
            "programme",
            "degree",
            "intake",
            "academic_year",
            "population",
            "nationality",
            "residency",
        )

    @pytest.mark.parametrize("dimension", SCOPE_DIMENSIONS)
    def test_every_dimension_can_refute_on_its_own(self, dimension):
        """None is decorative: each one alone can make a claim inapplicable."""
        request = RequestedScope(**{dimension: "asked for"})
        scope = ClaimScope(**{dimension: "something else"})

        assert scope.covers(request) is N


class TestAScopeSurvivesBeingStored:
    """A field that does not survive persistence is a field that does not exist."""

    def _a_claim(self, **kw):
        from datetime import UTC, datetime

        from app.domain.enums import ClaimType
        from app.schemas.claim import Claim

        return Claim(
            claim_type=next(iter(ClaimType)),
            normalized_value=6.5,
            source_url="https://nu.edu.kz/programmes/cs",
            accessed_at=datetime.now(UTC),
            **kw,
        )

    def test_it_round_trips_through_the_payload_json(self):
        """`ClaimRow.payload` stores the claim whole, so no column is needed."""
        from app.schemas.claim import Claim

        original = self._a_claim(scope=a_scope())

        restored = Claim.model_validate(original.model_dump(mode="json"))

        assert restored.scope == original.scope

    def test_no_recorded_scope_and_an_empty_one_are_different_facts(self):
        """The first is a gap in our pipeline; the second is a fact about the page."""
        assert self._a_claim().scope is None
        assert self._a_claim(scope=ClaimScope()).scope == ClaimScope()

    def test_a_stored_claim_without_the_field_still_loads(self):
        """Every claim written before this field existed must keep working."""
        from app.schemas.claim import Claim

        stored = self._a_claim(scope=a_scope()).model_dump(mode="json")
        del stored["scope"]

        assert Claim.model_validate(stored).scope is None

    def test_the_flat_fields_are_untouched(self):
        """Nothing reads the new field yet, so nothing may depend on it."""
        claim = self._a_claim(intake="fall 2027", academic_year="2026/27", scope=a_scope())

        assert claim.intake == "fall 2027"
        assert claim.academic_year == "2026/27"

    def test_an_unrecorded_scope_leaves_no_key_in_the_json(self):
        """Absent means "nobody looked"; a key saying so invites a wrong reading.

        It also keeps every claim written before this field existed
        byte-identical, which a golden-hash regression test relies on.
        """
        assert "scope" not in self._a_claim().model_dump(mode="json")
        assert "scope" in self._a_claim(scope=a_scope()).model_dump(mode="json")

    def test_a_deliberately_empty_scope_is_still_written_down(self):
        """A page that stated no scope is a fact, and facts get recorded."""
        dumped = self._a_claim(scope=ClaimScope()).model_dump(mode="json")

        assert "scope" in dumped
        assert all(v is None for v in dumped["scope"].values())
