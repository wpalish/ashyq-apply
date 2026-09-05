"""Ranking v2: weights, axes, aggregation, buckets.

The v1 score let a place nobody could pay for finish first, because thirteen
components were added up and a zero on affordability was bought back by good
scores elsewhere. v2 replaces that with a weighted geometric mean, and the
weights come from an ordering the applicant actually states.
"""

from __future__ import annotations

from itertools import pairwise

import pytest

from app.domain.priorities import (
    AXES,
    PRIORITY_GROUPS,
    axis_weights,
    complete_order,
    roc_weights,
    weights_from_override,
)
from app.schemas.profile import DEFAULT_PRIORITIES, ScoringWeights

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
