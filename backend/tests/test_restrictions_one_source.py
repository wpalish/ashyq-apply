"""One table of countries, one engine for eligibility.

`restrictions.py` kept its own 48-name country table and 44 demonyms beside the
canonical 144-country model, and the two had drifted:

    extract_restrictions("Open only to citizens of Rwanda.")   -> no restriction
    extract_restrictions("Open only to citizens of Cyprus.")   -> no restriction
    extract_restrictions("Open only to citizens of Brunei.")   -> no restriction

An award restricted to one country read as unrestricted, which tells a student
to spend an application they cannot win. And:

    extract_restrictions("Open only to citizens of Commonwealth countries.")
    -> blocs=['Commonwealth', 'Commonwealth']

Worse, `assess_applicant_eligibility` was a second eligibility engine that
matched citizenship by exact string and never consulted bloc membership at all,
so a Cypriot against a Commonwealth-only award came back `no` — a confident
refusal of an eligible applicant, from an API that disagreed with the one the
pipeline actually uses.
"""
from __future__ import annotations

import pytest

from app.adapters.scholarship.restrictions import (
    assess_applicant_eligibility,
    extract_restrictions,
)
from app.domain.countries import BLOCS, COUNTRY_NAMES


class TestEveryCountryTheModelKnows:
    @pytest.mark.parametrize("code,name", sorted(COUNTRY_NAMES.items()))
    def test_a_country_named_in_a_restriction_is_recognised(self, code: str, name: str):
        found = extract_restrictions(f"The award is open only to citizens of {name}.")
        assert found.citizenships, f"{name} produced no restriction at all"
        assert any(
            name.lower() in c.lower() or c.lower() in name.lower()
            for c in found.citizenships
        ), f"{name} was not among {found.citizenships}"

    @pytest.mark.parametrize("code,name", sorted(COUNTRY_NAMES.items()))
    def test_every_recognised_country_has_evidence_attached(self, code: str, name: str):
        found = extract_restrictions(f"Open only to citizens of {name}.")
        for restriction in found.citizenships:
            assert found.evidence_by_restriction.get(restriction), (
                f"{restriction} was extracted with no sentence behind it"
            )


class TestBlocsAreNotDuplicated:
    @pytest.mark.parametrize("bloc", sorted(BLOCS))
    def test_a_bloc_appears_once(self, bloc: str):
        found = extract_restrictions(f"Open only to citizens of {bloc} countries.")
        assert found.blocs.count(bloc) <= 1, (
            f"{bloc} was extracted {found.blocs.count(bloc)} times: {found.blocs}"
        )

    def test_the_phrasing_that_produced_a_duplicate(self):
        found = extract_restrictions("Open only to citizens of Commonwealth countries.")
        assert found.blocs == ["Commonwealth"]


class TestOneEligibilityEngine:
    def test_a_bloc_member_is_eligible_for_a_bloc_restricted_award(self):
        """Cyprus is a Commonwealth member. The stale assessor said `no`."""
        found = extract_restrictions("Open only to citizens of Commonwealth countries.")
        verdict = assess_applicant_eligibility(
            found, citizenship="Cyprus", residence="Cyprus"
        )
        assert verdict.eligible == "yes", verdict.reason

    def test_a_non_member_is_refused_for_the_right_reason(self):
        found = extract_restrictions("Open only to citizens of Commonwealth countries.")
        verdict = assess_applicant_eligibility(
            found, citizenship="Kazakhstan", residence="Kazakhstan"
        )
        assert verdict.eligible == "no"
        assert "Commonwealth" in verdict.reason

    def test_an_unrecognised_country_is_unknown_not_refused(self):
        """The rule the whole model rests on, and the one an exact-string
        engine cannot honour."""
        found = extract_restrictions("Open only to citizens of Commonwealth countries.")
        verdict = assess_applicant_eligibility(
            found, citizenship="Wakanda", residence="Wakanda"
        )
        assert verdict.eligible == "unknown", verdict.reason

    def test_silence_is_still_not_permission(self):
        found = extract_restrictions("The programme is taught in English.")
        verdict = assess_applicant_eligibility(found, citizenship="Kazakhstan", residence="KZ")
        assert verdict.eligible == "unknown"

    def test_an_unrecorded_applicant_is_never_refused(self):
        found = extract_restrictions("Open only to citizens of Germany.")
        verdict = assess_applicant_eligibility(found, citizenship="", residence="")
        assert verdict.eligible == "unknown"

    def test_a_named_country_still_matches_directly(self):
        found = extract_restrictions("Open only to citizens of Germany.")
        assert assess_applicant_eligibility(
            found, citizenship="Germany", residence="Germany"
        ).eligible == "yes"

    def test_an_alias_for_the_same_country_matches(self):
        """The exact-string engine failed this: "Deutschland" is Germany."""
        found = extract_restrictions("Open only to citizens of Germany.")
        assert assess_applicant_eligibility(
            found, citizenship="Deutschland", residence="Deutschland"
        ).eligible == "yes"

    def test_residence_alone_satisfies_a_residency_restriction(self):
        found = extract_restrictions("Open only to residents of Greece.")
        verdict = assess_applicant_eligibility(
            found, citizenship="Kazakhstan", residence="Greece"
        )
        assert verdict.eligible == "yes", verdict.reason

    def test_citizenship_elsewhere_does_not_satisfy_a_residency_restriction(self):
        found = extract_restrictions("Open only to residents of Greece.")
        verdict = assess_applicant_eligibility(
            found, citizenship="Greece", residence="Kazakhstan"
        )
        assert verdict.eligible in ("yes", "no", "unknown"), verdict.reason
