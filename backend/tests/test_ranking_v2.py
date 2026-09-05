"""Ranking v2: weights, axes, aggregation, buckets.

The v1 score let a place nobody could pay for finish first, because thirteen
components were added up and a zero on affordability was bought back by good
scores elsewhere. v2 replaces that with a weighted geometric mean, and the
weights come from an ordering the applicant actually states.
"""

from __future__ import annotations

import inspect
from itertools import pairwise
from pathlib import Path

import pytest

from app.domain import ranking_v2
from app.domain.enums import AdmissionsFit, Bucket, EligibilityStatus, FundingFit
from app.domain.priorities import (
    AXES,
    PRIORITY_GROUPS,
    axis_weights,
    complete_order,
    roc_weights,
    weights_from_override,
)
from app.domain.ranking_v2 import Quotas, ShortlistCandidate, build_shortlist, rank_result
from app.schemas.money import Money
from app.schemas.profile import DEFAULT_PRIORITIES, ScoringWeights
from app.schemas.result import (
    AxisScore,
    FundingGap,
    ProgramResult,
    RankingEntry,
    RankingV2,
    RequirementCheck,
)


def result(**kwargs) -> ProgramResult:
    return ProgramResult(
        **{
            "id": "r",
            "run_id": "run",
            "university": "Test University",
            "university_id": "u",
            "country": "Netherlands",
            "city": "Delft",
            "program": "BSc CS",
            "degree": "bachelor",
            "intake": "fall 2027",
            **kwargs,
        }
    )


TOLERANCE = 1e-9


class TestRankOrderCentroidWeights:
    """T10: the six group weights sum to one and fall with position."""

    def test_the_six_group_weights_sum_to_one(self):
        assert sum(roc_weights(DEFAULT_PRIORITIES).values()) == pytest.approx(1.0, abs=TOLERANCE)

    def test_a_group_ranked_higher_always_weighs_more(self):
        weights = list(roc_weights(DEFAULT_PRIORITIES).values())
        assert all(a > b for a, b in pairwise(weights))

    def test_the_published_centroid_weights_are_reproduced(self):
        expected = [0.408, 0.242, 0.158, 0.103, 0.061, 0.028]
        got = list(roc_weights(DEFAULT_PRIORITIES).values())
        assert got == pytest.approx(expected, abs=5e-4)

    def test_moving_a_group_up_moves_its_weight_up(self):
        default = roc_weights(DEFAULT_PRIORITIES)
        promoted = roc_weights(["campus_life", *DEFAULT_PRIORITIES])
        assert promoted["campus_life"] > default["campus_life"]

    def test_an_empty_ordering_is_the_default_ordering(self):
        assert roc_weights([]) == roc_weights(DEFAULT_PRIORITIES)

    def test_a_partial_ordering_keeps_the_default_order_for_the_rest(self):
        assert complete_order(["career"]) == [
            "career",
            *(g for g in DEFAULT_PRIORITIES if g != "career"),
        ]

    def test_an_unknown_group_name_is_ignored_rather_than_weighted(self):
        assert complete_order(["chess_club"]) == list(DEFAULT_PRIORITIES)


class TestAxisWeights:
    """T10: the group weight is split across that group's axes."""

    def test_the_axis_weights_sum_to_one(self):
        assert sum(axis_weights(DEFAULT_PRIORITIES).values()) == pytest.approx(1.0, abs=TOLERANCE)

    def test_every_axis_of_every_group_gets_a_weight(self):
        assert set(axis_weights(DEFAULT_PRIORITIES)) == set(AXES)

    def test_a_group_splits_its_weight_in_the_published_shares(self):
        weights = axis_weights(DEFAULT_PRIORITIES)
        academic = weights["academic_fit"] + weights["programme_standing"]
        assert weights["academic_fit"] / academic == pytest.approx(
            PRIORITY_GROUPS["academic"]["academic_fit"], abs=TOLERANCE
        )

    def test_funding_criticality_changes_the_weight_of_funding(self):
        decisive = axis_weights(DEFAULT_PRIORITIES, "decisive")
        optional = axis_weights(DEFAULT_PRIORITIES, "nice_to_have")
        assert optional["funding_fit"] < decisive["funding_fit"]
        assert optional["affordability"] < decisive["affordability"]

    def test_making_funding_optional_lifts_every_other_axis(self):
        decisive = axis_weights(DEFAULT_PRIORITIES, "decisive")
        optional = axis_weights(DEFAULT_PRIORITIES, "nice_to_have")
        assert optional["academic_fit"] > decisive["academic_fit"]

    def test_an_unknown_criticality_is_treated_as_decisive(self):
        assert axis_weights(DEFAULT_PRIORITIES, "whenever") == axis_weights(
            DEFAULT_PRIORITIES, "decisive"
        )


class TestAdvancedModeWeights:
    """The v1 sliders stay usable for anyone who already moved them."""

    def test_the_override_weights_sum_to_one(self):
        assert sum(weights_from_override(ScoringWeights()).values()) == pytest.approx(
            1.0, abs=TOLERANCE
        )

    def test_every_axis_still_gets_a_weight(self):
        assert set(weights_from_override(ScoringWeights())) == set(AXES)

    def test_raising_a_slider_raises_its_axis(self):
        default = weights_from_override(ScoringWeights())
        louder = weights_from_override(ScoringWeights(climate_fit=3.0))
        assert louder["climate"] > default["climate"]

    def test_the_funding_slider_also_weighs_affordability(self):
        default = weights_from_override(ScoringWeights())
        louder = weights_from_override(ScoringWeights(funding_fit=3.0))
        assert louder["affordability"] > default["affordability"]

    def test_the_extracurricular_slider_no_longer_weighs_anything(self):
        """It scored the applicant, so it was the same on every university."""
        assert weights_from_override(ScoringWeights(extracurricular_alignment=3.0)) == (
            weights_from_override(ScoringWeights(extracurricular_alignment=0.0))
        )

    def test_silencing_every_slider_falls_back_to_the_default_priorities(self):
        silent = ScoringWeights(**dict.fromkeys(ScoringWeights.model_fields, 0.0))
        assert weights_from_override(silent) == axis_weights(DEFAULT_PRIORITIES)


class TestResultSchema:
    """The row carries the ranking, its inputs, and where they came from."""

    def test_a_stored_result_written_before_v2_still_loads(self):
        stored = {
            "id": "r",
            "run_id": "run",
            "university": "Test University",
            "university_id": "u",
            "country": "Netherlands",
            "city": "Delft",
            "program": "BSc CS",
            "degree": "bachelor",
            "intake": "fall 2027",
        }
        row = ProgramResult.model_validate(stored)
        assert row.ranking is None
        assert row.catalog_attributes == {}
        assert row.catalog_attributes_source == ""

    def test_the_attributes_are_kept_raw_so_a_rerank_needs_no_crawl(self):
        row = result(
            catalog_attributes={"climate": "temperate", "city_size": "medium"},
            catalog_attributes_source="fixture-catalog",
        )
        assert row.catalog_attributes["climate"] == "temperate"

    def test_a_ranking_says_it_is_not_a_probability(self):
        ranking = RankingV2(coverage=1.0, sort_key=0.5, gamma=0.5, bucket=Bucket.PLAUSIBLE)
        assert "Not a probability" in ranking.disclaimer

    def test_an_axis_records_its_weight_and_its_reason(self):
        axis = AxisScore(axis="climate", value=1.0, state="known", weight=0.08, reason="Matches.")
        assert axis.weight and axis.reason


def affordable_row(**kwargs) -> ProgramResult:
    """A row where every axis is known and good, unless a test says otherwise."""
    return result(
        **{
            "eligibility": EligibilityStatus.MET,
            "admissions_fit": AdmissionsFit.STRONGER_FIT,
            "funding_fit": FundingFit.CONFIRMED_OPPORTUNITY,
            "rankings": [RankingEntry(source="QS", year=2026, position="40")],
            "funding_gap": FundingGap(computable=True, gap=Money(amount=1000.0, currency="USD")),
            "catalog_attributes": {
                "city_size": "medium",
                "climate": "temperate",
                "size": "large",
                "campus": "urban",
                "workload": "demanding",
            },
            "career_notes": "The careers service runs an internship programme.",
            **kwargs,
        }
    )


def unaffordable_row(**kwargs) -> ProgramResult:
    """The same row with 3.6x the family's stated ceiling still to pay."""
    return affordable_row(
        funding_gap=FundingGap(computable=True, gap=Money(amount=21600.0, currency="USD")),
        **kwargs,
    )


def axis_of(ranking: RankingV2, name: str) -> AxisScore:
    return next(a for a in ranking.axes if a.axis == name)


class TestNoAxisCanBeBoughtBack:
    """T1: the defect that started v2."""

    def test_an_unaffordable_place_ranks_below_an_affordable_one(self, profile):
        affordable = rank_result(affordable_row(), profile)
        unaffordable = rank_result(unaffordable_row(), profile)
        assert unaffordable.sort_key < affordable.sort_key
        assert affordable.fit is not None and affordable.fit >= 0.6

    def test_the_unaffordable_place_lands_outside_the_ranked_buckets(self, profile):
        assert rank_result(unaffordable_row(), profile).bucket == Bucket.OUT_OF_BUDGET

    def test_one_hopeless_axis_cannot_be_averaged_away(self, profile):
        """A sum let strong axes pay for a zero; a product does not."""
        strong = rank_result(affordable_row(), profile)
        vetoed = rank_result(affordable_row(funding_fit=FundingFit.NOT_ELIGIBLE), profile)
        assert vetoed.fit is not None and strong.fit is not None
        assert vetoed.fit < strong.fit / 2


class TestPreferencesActuallyMove:
    """T2: in v1 the whole climate preference moved the score by 1.7 %."""

    def test_ranking_climate_first_reorders_two_otherwise_identical_places(self, profile):
        profile.preferences.priorities = ["city_climate", *DEFAULT_PRIORITIES]
        cold = affordable_row(catalog_attributes={"climate": "cold"})
        warm = affordable_row(catalog_attributes={"climate": "warm"})

        profile.preferences.climate = "warm"
        assert rank_result(warm, profile).fit > rank_result(cold, profile).fit

        profile.preferences.climate = "cold"
        assert rank_result(cold, profile).fit > rank_result(warm, profile).fit


class TestUnknownsDoNotPunish:
    def without_climate(self) -> ProgramResult:
        attributes = dict(affordable_row().catalog_attributes)
        del attributes["climate"]
        return affordable_row(catalog_attributes=attributes)

    def test_an_unknown_axis_is_never_scored_as_a_failed_one(self, profile):
        """T3: a badly parsed website is not a worse university.

        Fit is a mean over the axes we know, so dropping one moves that mean —
        what must never happen is an unknown counting *against* the row. Here
        the same university is compared with its climate mismatched and with
        its climate unread; not knowing has to be the better of the two.
        """
        profile.preferences.climate = "cold"
        mismatched = rank_result(affordable_row(), profile)
        unknown = rank_result(self.without_climate(), profile)
        assert unknown.fit > mismatched.fit
        assert axis_of(unknown, "climate").value is None

    def test_an_unknown_axis_lowers_coverage_by_exactly_its_weight_share(self, profile):
        profile.preferences.climate = "temperate"
        known = rank_result(affordable_row(), profile)
        unknown = rank_result(self.without_climate(), profile)

        rated = sum(a.weight for a in unknown.axes if a.state != "not_applicable")
        share = axis_of(unknown, "climate").weight / rated
        assert unknown.coverage == pytest.approx(known.coverage - share, abs=TOLERANCE)
        assert "climate" in unknown.unknown_axes

    def test_an_axis_the_applicant_did_not_ask_about_changes_nothing(self, profile):
        """T4: 'any climate' is not a missing answer, it is no question.

        Two universities with opposite climates must rank identically once the
        applicant says climate does not matter — and the axis must not count
        towards coverage either, or 'no preference' would read as 'unverified'.
        """
        profile.preferences.climate = "any"
        warm = rank_result(affordable_row(catalog_attributes={"climate": "warm"}), profile)
        cold = rank_result(affordable_row(catalog_attributes={"climate": "cold"}), profile)

        assert warm.fit == pytest.approx(cold.fit, abs=TOLERANCE)
        assert warm.coverage == pytest.approx(cold.coverage, abs=TOLERANCE)
        assert axis_of(warm, "climate").state == "not_applicable"
        assert "climate" not in warm.unknown_axes

    def test_an_unasked_axis_does_not_count_against_coverage(self, profile):
        profile.preferences.climate = "any"
        unasked = rank_result(self.without_climate(), profile)
        assert "climate" not in unasked.unknown_axes
        assert unasked.coverage == pytest.approx(1.0, abs=TOLERANCE)


class TestKnockOuts:
    def test_an_excluded_country_is_listed_but_never_ranked(self, profile):
        """T5."""
        profile.preferences.preferred_countries = []
        profile.preferences.excluded_countries = ["Netherlands"]
        ranking = rank_result(affordable_row(), profile)
        assert ranking.bucket == Bucket.EXCLUDED
        assert ranking.sort_key == 0.0
        assert ranking.knocked_out_by

    def test_a_confirmed_hard_filter_knocks_the_row_out(self, profile):
        ranking = rank_result(
            affordable_row(
                requirement_checks=[
                    RequirementCheck(
                        requirement="IELTS writing",
                        status=EligibilityStatus.GAP,
                        is_hard_filter=True,
                        explanation="Published minimum 6.5; applicant 6.0.",
                    )
                ]
            ),
            profile,
        )
        assert ranking.bucket == Bucket.EXCLUDED
        assert "IELTS writing" in ranking.knocked_out_by[0]

    def test_an_unread_requirement_excludes_nobody(self, profile):
        ranking = rank_result(
            affordable_row(
                eligibility=EligibilityStatus.NEEDS_OFFICIAL_CLARIFICATION,
                admissions_fit=AdmissionsFit.INSUFFICIENT_DATA,
            ),
            profile,
        )
        assert ranking.bucket == Bucket.NEEDS_CLARIFICATION


class TestDeterminism:
    """T6."""

    def candidates(self, buckets: list[Bucket], country: str = "Netherlands"):
        return [
            ShortlistCandidate(id=f"r{i:02d}", country=country, bucket=b, sort_key=1.0 - i / 100)
            for i, b in enumerate(buckets)
        ]

    def test_the_same_rows_in_any_input_order_give_the_same_list(self):
        rows = self.candidates([Bucket.PLAUSIBLE] * 20, country="Netherlands")
        expected = [r.id for r in build_shortlist(rows, Quotas(max_per_country=99))[0]]
        for start in range(20):
            rotated = rows[start:] + rows[:start]
            chosen, _ = build_shortlist(rotated, Quotas(max_per_country=99))
            assert [r.id for r in chosen] == expected

    def test_rows_that_tie_are_ordered_by_id(self):
        rows = [
            ShortlistCandidate(id="b", country="Belgium", bucket=Bucket.PLAUSIBLE, sort_key=0.5),
            ShortlistCandidate(id="a", country="Austria", bucket=Bucket.PLAUSIBLE, sort_key=0.5),
        ]
        assert [r.id for r in build_shortlist(rows)[0]] == ["a", "b"]

    def test_ranking_the_same_row_twice_gives_the_same_numbers(self, profile):
        first = rank_result(affordable_row(), profile)
        assert rank_result(affordable_row(), profile).model_dump() == first.model_dump()


class TestBalancedShortlist:
    """T7: twenty ambitious options is a list nobody can act on."""

    def candidates(self, buckets: list[Bucket], country: str = "Netherlands"):
        return [
            ShortlistCandidate(id=f"r{i:02d}", country=country, bucket=b, sort_key=1.0 - i / 100)
            for i, b in enumerate(buckets)
        ]

    def test_no_more_than_three_ambitious_rows_are_chosen(self):
        chosen, _ = build_shortlist(
            self.candidates([Bucket.AMBITIOUS] * 20), Quotas(max_per_country=99)
        )
        assert len(chosen) == 3

    def test_no_more_than_three_rows_come_from_one_country(self):
        chosen, _ = build_shortlist(self.candidates([Bucket.PLAUSIBLE] * 20))
        assert len(chosen) == 3

    def test_the_minimums_are_filled_before_the_ranking_speaks(self):
        rows = [
            *self.candidates([Bucket.AMBITIOUS] * 6),
            ShortlistCandidate(
                id="zz", country="Belgium", bucket=Bucket.WELL_PLACED, sort_key=0.01
            ),
        ]
        chosen, _ = build_shortlist(rows, Quotas(max_per_country=99))
        assert "zz" in [r.id for r in chosen]

    def test_a_minimum_that_cannot_be_met_is_stated_not_hidden(self):
        _, notes = build_shortlist(
            self.candidates([Bucket.AMBITIOUS] * 5), Quotas(max_per_country=99)
        )
        assert any("well placed" in n for n in notes)
        assert any("plausible" in n for n in notes)

    def test_the_list_stops_at_the_requested_size(self):
        chosen, _ = build_shortlist(
            self.candidates([Bucket.PLAUSIBLE] * 40), Quotas(size=10, max_per_country=99)
        )
        assert len(chosen) == 10

    def test_an_excluded_row_never_enters_the_shortlist(self):
        chosen, _ = build_shortlist(self.candidates([Bucket.EXCLUDED] * 5))
        assert chosen == []


class TestEveryAxisExplainsItself:
    """T9: the v1 explainability tests, ported to v2."""

    def test_every_axis_names_its_weight_and_its_reason(self, profile):
        for axis in rank_result(affordable_row(), profile).axes:
            assert axis.reason, f"{axis.axis} has no reason"
            assert axis.weight > 0, f"{axis.axis} has no weight"

    def test_every_axis_of_the_ranking_is_present_on_every_row(self, profile):
        assert {a.axis for a in rank_result(affordable_row(), profile).axes} == set(AXES)

    def test_a_university_size_mismatch_moves_the_ranking(self, profile):
        profile.preferences.university_size = "small"
        large = rank_result(affordable_row(), profile)
        small = rank_result(
            affordable_row(catalog_attributes={"size": "small", "climate": "temperate"}), profile
        )
        assert small.fit > large.fit

    def test_funding_criticality_changes_the_weight_of_funding(self, profile):
        profile.funding.funding_criticality = "decisive"
        decisive = rank_result(affordable_row(), profile)
        profile.funding.funding_criticality = "nice_to_have"
        optional = rank_result(affordable_row(), profile)
        assert axis_of(optional, "funding_fit").weight < axis_of(decisive, "funding_fit").weight

    def test_a_tenge_ceiling_is_converted_before_it_is_compared(self, profile):
        """A 2,880,000 KZT ceiling must not read as infinite beside a USD gap."""
        profile.funding.budget_currency = "KZT"
        profile.funding.max_acceptable_gap = 2_880_000
        profile.funding.max_annual_budget = 2_880_000
        row = affordable_row(
            funding_gap=FundingGap(computable=True, gap=Money(amount=20000.0, currency="USD"))
        )
        affordability = axis_of(rank_result(row, profile), "affordability")
        assert affordability.state == "known"
        assert affordability.value is not None and affordability.value < 0.5

    def test_a_campus_mismatch_is_not_dressed_up_as_acceptable(self, profile):
        profile.preferences.campus_type = "campus"
        campus = axis_of(rank_result(affordable_row(), profile), "campus")
        assert campus.state == "known"
        assert campus.value is not None and campus.value < 0.5

    def test_an_axis_carries_the_claims_that_confirmed_it(self, profile):
        row = affordable_row(
            requirement_checks=[
                RequirementCheck(
                    requirement="IELTS overall",
                    published_value=6.5,
                    applicant_value=7.0,
                    status=EligibilityStatus.MET,
                    claim_ids=["claim-1"],
                )
            ]
        )
        assert axis_of(rank_result(row, profile), "academic_fit").evidence_claim_ids == ["claim-1"]

    def test_the_ranking_records_where_its_weights_came_from(self, profile):
        assert rank_result(affordable_row(), profile).weights_source == "priorities_roc"
        profile.weights_override = True
        assert rank_result(affordable_row(), profile).weights_source == "weights_override"

    def test_a_row_with_nothing_known_has_no_fit_rather_than_a_zero(self, profile):
        profile.preferences.preferred_countries = []
        bare = result(university="Unknown University")
        ranking = rank_result(bare, profile)
        assert ranking.fit is None
        assert ranking.coverage == 0.0
        assert ranking.sort_key == 0.0


class TestTheRankingNeverReadsAnAdapter:
    """T11 / I1: no number an LLM produced can reach fit, coverage or order."""

    def test_the_module_imports_nothing_from_an_adapter(self):
        source = Path(ranking_v2.__file__).read_text(encoding="utf-8")
        assert "adapters" not in source

    def test_no_adapter_module_is_reachable_from_the_module_namespace(self):
        imported = {
            module.__name__
            for module in vars(ranking_v2).values()
            if inspect.ismodule(module) and hasattr(module, "__name__")
        }
        assert not [name for name in imported if name.startswith("app.adapters")]
