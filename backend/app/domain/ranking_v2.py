"""Ranking v2: a non-compensatory fit, a separate coverage, and a bucket.

v1 added thirteen weighted components together. A place with a 21,471 USD
annual shortfall for a family with a 6,000 USD ceiling scored zero on
affordability and still finished first, because funding, academic and country
paid the difference. Sums do that: any axis can be bought back.

v2 multiplies instead. The fit is a weighted geometric mean over the axes we
actually know, so an axis near zero drags the whole row down and no amount of
excellence elsewhere rescues it. What we do *not* know is kept out of the fit
entirely and reported as ``coverage``, because a university with a badly
parsed website is not a worse university (P1, P6, D1, D2).

Pure functions over stored data — no adapter imports (invariant I1), so a
changed preference re-ranks without crawling anything again (P4).
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from itertools import pairwise

from app.domain.enums import AdmissionsFit, Bucket, EligibilityStatus, FundingFit
from app.domain.priorities import axis_weights, weights_from_override
from app.domain.scoring import best_rank, comparable_ceiling, requirement_margin
from app.schemas.profile import ApplicantProfileIn
from app.schemas.result import AxisScore, ProgramResult, RankingV2

#: Floor for the logarithm. An axis at 0.02 is a near-veto that still has a
#: finite log, so one hopeless dimension sinks the row instead of the whole
#: arithmetic (ln 0 = -inf would make every such row equally, uselessly bad).
EPSILON = 0.02

#: `sort_key = fit · coverage^GAMMA`. At 0.5 a row we verified half of gives up
#: about 29 % of its fit — enough that a confirmed answer beats a guessy one,
#: not so much that a thin website is a death sentence.
DEFAULT_GAMMA = 0.5


class Missing(StrEnum):
    """Why an axis has no number. The two reasons are not interchangeable."""

    #: We could not verify it. Counts against coverage, never against fit (I4).
    UNKNOWN = "unknown"
    #: The applicant stated no preference. Ignored by both (I5).
    NOT_APPLICABLE = "not_applicable"


Utility = float | Missing


class KnockOut(Exception):
    """A confirmed hard filter. The row is listed with its reason, not ranked."""


@dataclass(frozen=True)
class Axis:
    name: str
    value: Utility
    weight: float
    reason: str
    evidence_claim_ids: tuple[str, ...] = ()


@dataclass
class Score:
    fit: float | None
    coverage: float
    axes: list[Axis]
    unknown: list[str] = field(default_factory=list)
    not_applicable: list[str] = field(default_factory=list)

    def sort_key(self, gamma: float = DEFAULT_GAMMA) -> float:
        if self.fit is None:
            return 0.0
        return self.fit * (self.coverage**gamma)


# --- Per-axis utilities (SPEC_matching_v2 §5.2) --------------------------


def u_academic(eligibility: EligibilityStatus, margin: float | None) -> tuple[Utility, str]:
    """How far above the published minimums the applicant sits.

    Never a probability: a met requirement is a fact, the decision that follows
    it is a committee's.
    """
    if eligibility == EligibilityStatus.MET:
        if margin is None:
            return (
                0.75,
                "All published requirements are met; there are no numeric minimums to "
                "measure a margin against.",
            )
        return (
            min(1.0, max(0.6, 0.6 + 2.0 * margin)),
            f"All published requirements are met, on average {margin:.0%} above the minimums.",
        )
    if eligibility == EligibilityStatus.PENDING:
        return 0.5, "Requirements are met apart from items still pending."
    if eligibility == EligibilityStatus.GAP:
        return 0.15, "At least one published requirement is not met."
    return Missing.UNKNOWN, "Published requirements could not be verified."


_FUNDING_UTILITY: dict[FundingFit, float] = {
    FundingFit.CONFIRMED_OPPORTUNITY: 1.0,
    FundingFit.COMPETITIVE_OPPORTUNITY: 0.7,
    FundingFit.LIMITED_OPPORTUNITY: 0.3,
    FundingFit.NOT_ELIGIBLE: EPSILON,
}


def u_funding(funding_fit: FundingFit) -> tuple[Utility, str]:
    value = _FUNDING_UTILITY.get(funding_fit)
    if value is None:
        return Missing.UNKNOWN, "No official funding information was confirmed."
    return value, f"Funding fit is {funding_fit.value.lower().replace('_', ' ')}."


#: Above the ceiling, utility falls 1.4 per unit of ratio, so 1.5x the ceiling
#: lands on 0.3 and anything beyond is the floor. Bought-back affordability was
#: the original defect; the slope is steep on purpose.
_OVER_CEILING_SLOPE = 1.4
_UNAFFORDABLE_RATIO = 1.5


def u_affordability(gap: float | None, ceiling: float | None) -> tuple[Utility, str]:
    if gap is None:
        return Missing.UNKNOWN, "The remaining annual cost could not be computed."
    if ceiling is None:
        return Missing.UNKNOWN, "No family budget ceiling was stated to compare against."
    if ceiling <= 0:
        if gap <= 0:
            return 1.0, "Nothing remains to be paid."
        return (
            EPSILON,
            f"The family states it can contribute nothing, and {gap:,.0f} a year remains.",
        )
    ratio = gap / ceiling
    if ratio <= 1.0:
        return (
            1.0,
            f"The remaining {gap:,.0f} a year is within the stated ceiling of {ceiling:,.0f}.",
        )
    if ratio <= _UNAFFORDABLE_RATIO:
        return (
            1.0 - _OVER_CEILING_SLOPE * (ratio - 1.0),
            f"The remaining {gap:,.0f} a year is {ratio - 1:.0%} above the stated "
            f"ceiling of {ceiling:,.0f}.",
        )
    return (
        EPSILON,
        f"The remaining {gap:,.0f} a year is {ratio:.1f} times the stated ceiling "
        f"of {ceiling:,.0f}.",
    )


#: Somewhere the applicant did not ask for is worth something — it is still a
#: place they can study — but plainly less than one they named.
_UNPREFERRED_COUNTRY = 0.35


def u_country(
    country: str, preferred: Sequence[str], excluded: Sequence[str]
) -> tuple[Utility, str]:
    lowered = country.lower()
    if lowered in {c.lower() for c in excluded}:
        raise KnockOut(f"{country} is on the applicant's excluded list.")
    if not preferred:
        return Missing.NOT_APPLICABLE, "No country preference was stated."
    if lowered in {c.lower() for c in preferred}:
        return 1.0, f"{country} is a preferred country."
    return _UNPREFERRED_COUNTRY, f"{country} is outside the preferred list."


#: Ranking positions are interpolated on a log scale: the distance from 1 to
#: 100 means far more than the distance from 1400 to 1500.
_RANK_ANCHORS: tuple[tuple[int, float], ...] = ((1, 1.0), (100, 0.8), (500, 0.5), (1500, 0.2))
_BEYOND_ANCHORS = 0.1
_TARGET_BANDS = {"top_50": 50, "top_100": 100, "top_300": 300, "top_500": 500}


def u_standing(rank: int | None, target_band: str) -> tuple[Utility, str]:
    if rank is None:
        return Missing.UNKNOWN, "No ranking position was found."
    target = _TARGET_BANDS.get(target_band)
    if target and rank <= target:
        return 1.0, f"Ranked {rank}, inside the requested {target_band.replace('_', ' ')}."
    x = math.log(rank)
    points = [(math.log(r), u) for r, u in _RANK_ANCHORS]
    if x >= points[-1][0]:
        return _BEYOND_ANCHORS, f"Ranked {rank}, outside the top {_RANK_ANCHORS[-1][0]}."
    for (x0, y0), (x1, y1) in pairwise(points):
        if x0 <= x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0), f"Consensus ranking position {rank}."
    return 1.0, f"Ranked {rank}."


#: Ordered preferences: being one step off is not the same as being opposite.
_LADDERS: dict[str, tuple[str, ...]] = {
    "city": ("small", "medium", "large", "metropolis"),
    "climate": ("cold", "temperate", "mediterranean", "warm", "tropical"),
    "workload": ("moderate", "demanding", "very_demanding"),
    "university_size": ("small", "medium", "large"),
}
_STEP_UTILITY: dict[int, float] = {0: 1.0, 1: 0.75, 2: 0.5}
#: A mismatch with no ordering to soften it — an urban university for someone
#: who asked for a campus one.
_UNORDERED_MISMATCH = 0.25


def u_ladder(axis: str, actual: str | None, preferred: str) -> tuple[Utility, str]:
    """Match one stated attribute preference. `campus` has no ladder, by design."""
    if preferred in ("any", ""):
        return Missing.NOT_APPLICABLE, f"No {axis.replace('_', ' ')} preference was stated."
    if not actual or actual == "unknown":
        return Missing.UNKNOWN, f"The {axis.replace('_', ' ')} of this university is not known."
    if actual == preferred:
        return 1.0, f"{actual} matches the stated preference."
    ladder = _LADDERS.get(axis)
    if ladder and actual in ladder and preferred in ladder:
        steps = abs(ladder.index(actual) - ladder.index(preferred))
        return (
            _STEP_UTILITY.get(steps, _UNORDERED_MISMATCH),
            f"{actual} against a preference for {preferred}: "
            f"{steps} step{'s' if steps > 1 else ''} apart.",
        )
    return _UNORDERED_MISMATCH, f"{actual} differs from the preferred {preferred}."


def u_career(
    *,
    has_coop: bool | None,
    has_internships: bool | None,
    has_page: bool,
    values_internships: bool,
    values_coop: bool,
) -> tuple[Utility, str]:
    """What the careers pages confirm, against what the applicant asked for.

    ``has_coop`` and ``has_internships`` stay None until a claim type exists to
    confirm them ([2.2]); a page that exists without specifics is worth half a
    match and says so, rather than being read as a yes.
    """
    if not (values_internships or values_coop):
        return Missing.NOT_APPLICABLE, "Careers were not a stated priority."
    if values_coop and has_coop:
        return 1.0, "A co-op or placement year is officially offered."
    if has_internships:
        return 0.8, "An internship programme is officially described."
    if has_page:
        return 0.5, "A careers page exists but states nothing specific enough to check."
    return Missing.UNKNOWN, "No official careers information was found."


#: Two years of post-study work is treated as a full answer; longer rights are
#: real but stop changing the decision.
_FULL_POST_STUDY_MONTHS = 24


def u_post_study_work(months: int | None, needed: bool) -> tuple[Utility, str]:
    if not needed:
        return Missing.NOT_APPLICABLE, "Post-study work was not a stated priority."
    if months is None:
        return Missing.UNKNOWN, "Post-study work rules were not confirmed in months."
    value = max(EPSILON, min(1.0, months / _FULL_POST_STUDY_MONTHS))
    return value, f"A post-study work right of {months} months is published."


# --- Aggregation (SPEC_matching_v2 §5.3) ---------------------------------


def aggregate(axes: Sequence[Axis]) -> Score:
    """Weighted geometric mean over known axes, plus how much weight that was.

    No rounding happens here. Rounding inside the arithmetic would make a
    coverage share disappear in the third decimal, and T3 compares those
    shares exactly.
    """
    known = [a for a in axes if not isinstance(a.value, Missing)]
    unknown = [a for a in axes if a.value == Missing.UNKNOWN]
    not_applicable = [a for a in axes if a.value == Missing.NOT_APPLICABLE]
    known_weight = sum(a.weight for a in known)
    rated_weight = known_weight + sum(a.weight for a in unknown)
    names = ([a.name for a in unknown], [a.name for a in not_applicable])
    if known_weight <= 0:
        return Score(None, 0.0, list(axes), *names)
    log_sum = sum(a.weight * math.log(max(float(a.value), EPSILON)) for a in known)
    fit = math.exp(log_sum / known_weight)
    coverage = known_weight / rated_weight if rated_weight else 0.0
    return Score(fit, coverage, list(axes), *names)


# --- Buckets and the balanced shortlist (SPEC_matching_v2 §5.5) ----------

#: How far past the family's ceiling a row may sit before it stops being an
#: option at all. Someone who called funding decisive means it.
_BUDGET_KNOCKOUT_RATIO: dict[str, float] = {
    "decisive": 1.5,
    "important": 2.5,
    "nice_to_have": math.inf,
}


def bucket_of(
    admissions_fit: AdmissionsFit,
    funding_fit: FundingFit,
    gap_ratio: float | None,
    criticality: str,
) -> tuple[Bucket, str]:
    if admissions_fit == AdmissionsFit.INSUFFICIENT_DATA:
        return (
            Bucket.NEEDS_CLARIFICATION,
            "Too little of the published requirements could be verified to place this row.",
        )
    limit = _BUDGET_KNOCKOUT_RATIO.get(criticality, math.inf)
    if gap_ratio is not None and gap_ratio > limit:
        return (
            Bucket.OUT_OF_BUDGET,
            f"The remaining cost is {gap_ratio:.1f} times the stated ceiling, past the "
            f"{limit:.1f} times this applicant said they could stretch to.",
        )
    affordable = gap_ratio is None or gap_ratio <= 1.0
    if (
        admissions_fit == AdmissionsFit.STRONGER_FIT
        and funding_fit == FundingFit.CONFIRMED_OPPORTUNITY
        and affordable
    ):
        return (
            Bucket.WELL_PLACED,
            "Requirements are met with room, funding is confirmed, and the remaining cost "
            "is within the stated ceiling.",
        )
    if (
        admissions_fit in (AdmissionsFit.STRONGER_FIT, AdmissionsFit.PLAUSIBLE_FIT)
        and funding_fit in (FundingFit.CONFIRMED_OPPORTUNITY, FundingFit.COMPETITIVE_OPPORTUNITY)
        and (gap_ratio is None or gap_ratio <= _UNAFFORDABLE_RATIO)
    ):
        return Bucket.PLAUSIBLE, "Requirements and funding both look reachable on published data."
    return (
        Bucket.AMBITIOUS,
        "Either the requirements, the funding or the remaining cost makes this a stretch.",
    )


@dataclass(frozen=True)
class Quotas:
    """Shape of a balanced list. Numbers are settings, not laws of nature."""

    size: int = 10
    min_well_placed: int = 2
    min_plausible: int = 4
    max_ambitious: int = 3
    max_per_country: int = 3


@dataclass(frozen=True)
class ShortlistCandidate:
    id: str
    country: str
    bucket: Bucket
    sort_key: float


def build_shortlist(
    rows: Sequence[ShortlistCandidate], quotas: Quotas | None = None
) -> tuple[list[ShortlistCandidate], list[str]]:
    """A deterministic balanced list: quotas first, then the best of the rest.

    A top-20 of twenty ambitious options is a list nobody can act on, so the
    minimums are filled before the ranking gets to speak. A minimum that cannot
    be met produces a note — never a quietly shorter list.
    """
    quotas = quotas or Quotas()
    notes: list[str] = []
    chosen: list[ShortlistCandidate] = []
    taken: set[str] = set()
    per_country: dict[str, int] = {}
    ambitious = 0

    def can_take(row: ShortlistCandidate) -> bool:
        if row.id in taken:
            return False
        if row.bucket == Bucket.AMBITIOUS and ambitious >= quotas.max_ambitious:
            return False
        return per_country.get(row.country, 0) < quotas.max_per_country

    def take(row: ShortlistCandidate) -> None:
        nonlocal ambitious
        chosen.append(row)
        taken.add(row.id)
        per_country[row.country] = per_country.get(row.country, 0) + 1
        if row.bucket == Bucket.AMBITIOUS:
            ambitious += 1

    # Tie-break on id so the same input is always the same output (I6).
    by_key = sorted(rows, key=lambda r: (-r.sort_key, r.id))

    for bucket, minimum in (
        (Bucket.WELL_PLACED, quotas.min_well_placed),
        (Bucket.PLAUSIBLE, quotas.min_plausible),
    ):
        found = 0
        for row in by_key:
            if found >= minimum or len(chosen) >= quotas.size:
                break
            if row.bucket == bucket and can_take(row):
                take(row)
                found += 1
        if found < minimum:
            notes.append(
                f"Found {found} {bucket.value.lower().replace('_', ' ')} option(s); "
                f"wanted at least {minimum}."
            )

    rankable = (Bucket.WELL_PLACED, Bucket.PLAUSIBLE, Bucket.AMBITIOUS)
    for row in by_key:
        if len(chosen) >= quotas.size:
            break
        if row.bucket in rankable and can_take(row):
            take(row)
    return chosen, notes


# --- Top level -----------------------------------------------------------

#: Axis name -> the catalogue attribute that answers it, and the preference
#: field it is compared against.
_ATTRIBUTE_AXES: tuple[tuple[str, str, str], ...] = (
    ("city", "city_size", "city_size"),
    ("climate", "climate", "climate"),
    ("university_size", "size", "university_size"),
    ("campus", "campus", "campus_type"),
    ("workload", "workload", "acceptable_workload"),
)


def gap_and_ceiling(
    result: ProgramResult, profile: ApplicantProfileIn
) -> tuple[float | None, float | None]:
    """The annual shortfall and the family's ceiling, in one currency."""
    gap = result.funding_gap
    if gap is None or not gap.computable or gap.gap is None:
        return None, None
    ceiling, _note, refusal = comparable_ceiling(profile, gap.gap.currency)
    if refusal:
        # No bundled rate connects the two currencies. Unknown, never guessed.
        return gap.gap.amount, None
    return gap.gap.amount, ceiling


def rank_result(
    result: ProgramResult, profile: ApplicantProfileIn, *, gamma: float = DEFAULT_GAMMA
) -> RankingV2:
    """Rank one row against one profile, from stored data only."""
    prefs, funding = profile.preferences, profile.funding
    if profile.weights_override:
        weights = weights_from_override(profile.weights)
        weights_source = "weights_override"
    else:
        weights = axis_weights(prefs.priorities, funding.funding_criticality)
        weights_source = "priorities_roc"

    gap, ceiling = gap_and_ceiling(result, profile)
    ratio = gap / ceiling if (gap is not None and ceiling) else None

    knocked_out = [
        f"{check.requirement}: {check.explanation or 'a published requirement is not met'}"
        for check in result.requirement_checks
        if check.is_hard_filter
    ]
    try:
        axes = _axes_for(result, profile, weights, gap, ceiling)
    except KnockOut as excluded:
        knocked_out.append(str(excluded))
        axes = []

    if knocked_out:
        return RankingV2(
            fit=None,
            coverage=0.0,
            sort_key=0.0,
            gamma=gamma,
            axes=[_as_axis_score(a) for a in axes],
            knocked_out_by=knocked_out,
            bucket=Bucket.EXCLUDED,
            bucket_reason=knocked_out[0],
            weights_source=weights_source,
        )

    score = aggregate(axes)
    bucket, bucket_reason = bucket_of(
        result.admissions_fit, result.funding_fit, ratio, funding.funding_criticality
    )
    return RankingV2(
        fit=score.fit,
        coverage=score.coverage,
        sort_key=score.sort_key(gamma),
        gamma=gamma,
        axes=[_as_axis_score(a) for a in axes],
        unknown_axes=score.unknown,
        not_applicable_axes=score.not_applicable,
        bucket=bucket,
        bucket_reason=bucket_reason,
        weights_source=weights_source,
    )


def _axes_for(
    result: ProgramResult,
    profile: ApplicantProfileIn,
    weights: Mapping[str, float],
    gap: float | None,
    ceiling: float | None,
) -> list[Axis]:
    prefs = profile.preferences
    attributes = result.catalog_attributes
    spec: list[tuple[str, tuple[Utility, str], tuple[str, ...]]] = [
        (
            "academic_fit",
            u_academic(result.eligibility, requirement_margin(result)),
            tuple(cid for check in result.requirement_checks for cid in check.claim_ids),
        ),
        (
            "funding_fit",
            u_funding(result.funding_fit),
            tuple(cid for award in result.scholarships for cid in award.claim_ids),
        ),
        ("affordability", u_affordability(gap, ceiling), ()),
        (
            "country",
            u_country(result.country, prefs.preferred_countries, prefs.excluded_countries),
            (),
        ),
        ("programme_standing", u_standing(best_rank(result), prefs.target_ranking_band), ()),
        *(
            (axis, u_ladder(axis, attributes.get(attribute), getattr(prefs, preference)), ())
            for axis, attribute, preference in _ATTRIBUTE_AXES
        ),
        (
            "career",
            u_career(
                # Neither co-op nor internships have a claim type yet ([2.2]),
                # so only the existence of an official page is confirmable.
                has_coop=None,
                has_internships=None,
                has_page=bool(result.career_notes),
                values_internships=prefs.values_internships,
                values_coop=prefs.values_coop,
            ),
            (),
        ),
        (
            "post_study_work",
            # Months are parsed from ClaimType.POST_STUDY_WORK_MONTHS in [2.2].
            # Until then the axis says unknown rather than inventing a number.
            u_post_study_work(None, prefs.needs_post_study_work),
            (),
        ),
    ]
    return [
        Axis(name, value, weights.get(name, 0.0), reason, claim_ids)
        for name, (value, reason), claim_ids in spec
    ]


def _as_axis_score(axis: Axis) -> AxisScore:
    known = not isinstance(axis.value, Missing)
    return AxisScore(
        axis=axis.name,
        value=float(axis.value) if known else None,
        state="known" if known else str(axis.value),
        weight=axis.weight,
        reason=axis.reason,
        evidence_claim_ids=list(dict.fromkeys(axis.evidence_claim_ids)),
    )
