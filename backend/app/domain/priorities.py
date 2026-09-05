"""Axis weights for ranking v2, derived from what the applicant said matters.

Twelve 0-3 sliders were offered and nobody moved them, so the stated ordering
of six groups is the real input (AI_TASK_BRIEF D8). Rank-order centroid turns
that ordering into weights without asking anyone to invent a number: position
alone decides, and the gap between first and second is wide enough that the
top priority actually shows in the result.

Pure arithmetic, no I/O — the ranking must not depend on anything an adapter
fetched (invariant I1).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import cast

from app.schemas.profile import DEFAULT_PRIORITIES, PriorityGroup, ScoringWeights

#: Which axes belong to a group, and how the group's weight splits between
#: them (SPEC_matching_v2 §5.1). Every inner mapping sums to 1.
PRIORITY_GROUPS: dict[PriorityGroup, dict[str, float]] = {
    "funding": {"funding_fit": 0.5, "affordability": 0.5},
    "academic": {"academic_fit": 0.6, "programme_standing": 0.4},
    "country": {"country": 1.0},
    "city_climate": {"city": 0.5, "climate": 0.5},
    "career": {"career": 0.5, "post_study_work": 0.5},
    "campus_life": {"university_size": 1 / 3, "campus": 1 / 3, "workload": 1 / 3},
}

#: Every axis a ranked result can carry, in group order.
AXES: tuple[str, ...] = tuple(a for axes in PRIORITY_GROUPS.values() for a in axes)

#: A funded place is a funded place; it simply matters more to a family that
#: cannot go without one. Same multipliers as v1 scoring, kept so the two
#: rankings disagree about the shape of the answer and not about the money.
FUNDING_CRITICALITY: dict[str, float] = {
    "nice_to_have": 0.5,
    "important": 0.75,
    "decisive": 1.0,
}

#: Old slider -> v2 axis. `extracurricular_alignment` has no target: it scored
#: the applicant, not the university, so it was identical on every row and is
#: now read through admissions fit instead (AI_TASK_BRIEF P5).
_OVERRIDE_AXIS_OF: dict[str, str] = {
    "academic_fit": "academic_fit",
    "funding_fit": "funding_fit",
    "program_quality": "programme_standing",
    "country_preference": "country",
    "city_fit": "city",
    "climate_fit": "climate",
    "workload_fit": "workload",
    "university_size_fit": "university_size",
    "campus_fit": "campus",
    "career_outcomes": "career",
    "post_study_work": "post_study_work",
}

#: v1 gave affordability half of the funding weight and had no slider of its
#: own. Someone who tuned the v1 sliders tuned that ratio, so keep it.
_OVERRIDE_AFFORDABILITY_SHARE = 0.5


def complete_order(order: Sequence[str] | None) -> list[PriorityGroup]:
    """The applicant's ordering, with anything unranked left in default order.

    A partially ranked list is normal — the UI lets someone move one card and
    stop — and every group still needs a weight, so the tail is the default.
    """
    ranked = [cast(PriorityGroup, g) for g in dict.fromkeys(order or []) if g in PRIORITY_GROUPS]
    return [*ranked, *(g for g in DEFAULT_PRIORITIES if g not in ranked)]


def roc_weights(order: Sequence[str] | None) -> dict[PriorityGroup, float]:
    """Rank-order centroid: ``w_k = (1/n) · Σ_{j=k..n} 1/j``. Sums to 1.

    For six groups: 0.408, 0.242, 0.158, 0.103, 0.061, 0.028.
    """
    groups = complete_order(order)
    n = len(groups)
    return {g: sum(1.0 / j for j in range(k, n + 1)) / n for k, g in enumerate(groups, start=1)}


def axis_weights(order: Sequence[str] | None, criticality: str = "decisive") -> dict[str, float]:
    """Per-axis weights from a priority ordering. Sums to 1."""
    group_weight = roc_weights(order)
    funding_multiplier = FUNDING_CRITICALITY.get(criticality, 1.0)
    raw = {
        axis: group_weight[group] * share * (funding_multiplier if group == "funding" else 1.0)
        for group, axes in PRIORITY_GROUPS.items()
        for axis, share in axes.items()
    }
    return _normalised(raw)


def weights_from_override(weights: ScoringWeights) -> dict[str, float]:
    """Per-axis weights from the advanced-mode sliders. Sums to 1.

    Funding criticality is not applied here: a slider the applicant moved by
    hand already states how much the money matters to them.
    """
    raw = {axis: float(getattr(weights, slider)) for slider, axis in _OVERRIDE_AXIS_OF.items()}
    raw["affordability"] = raw["funding_fit"] * _OVERRIDE_AFFORDABILITY_SHARE
    if sum(raw.values()) <= 0:
        # Every slider at zero says nothing about what to rank by. Ranking on
        # the default priorities beats dividing by zero or ordering at random.
        return axis_weights(None)
    return _normalised(raw)


def _normalised(weights: dict[str, float]) -> dict[str, float]:
    total = sum(weights.values())
    return {axis: w / total for axis, w in weights.items()}
