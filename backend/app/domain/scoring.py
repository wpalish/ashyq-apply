"""Preference scoring.

The output is a weighted sum with every component exposed, plus an explicit
penalty for absent data. It is deliberately *not* calibrated against admission
outcomes, and the schema carries a disclaimer saying so, because a number like
"73%" would be read as a probability we have no basis to state.
"""

from __future__ import annotations

from app.domain.currency import UnsupportedCurrency, convert
from app.domain.enums import AdmissionsFit, EligibilityStatus, FundingFit
from app.schemas.money import ConvertedMoney, Money
from app.schemas.profile import ApplicantProfileIn, ScoringWeights
from app.schemas.result import ExplainableScore, ProgramResult, ScoreComponent

#: Each absent component costs this share of the final score, so a sparse
#: profile ranks below an equally-matched complete one instead of tying.
MISSING_DATA_PENALTY_PER_FIELD = 0.03
MAX_MISSING_PENALTY = 0.25

_CITY_SIZE_BUCKETS = {"small": 1, "medium": 2, "large": 3, "metropolis": 4}


def _fit_scale(distance: int) -> float:
    return {0: 1.0, 1: 0.7, 2: 0.4}.get(distance, 0.2)


def score_result(result: ProgramResult, profile: ApplicantProfileIn) -> ExplainableScore:
    w: ScoringWeights = profile.weights
    comps: list[ScoreComponent] = []
    missing: list[str] = []

    def add(
        name: str,
        raw: float | None,
        weight: float,
        explanation: str,
        missing_label: str | None = None,
    ) -> None:
        present = raw is not None
        if not present:
            missing.append(missing_label or name)
        value = raw if raw is not None else 0.0
        comps.append(
            ScoreComponent(
                name=name,
                raw=round(value, 4),
                weight=weight,
                weighted=round(value * weight, 4),
                explanation=explanation,
                data_present=present,
            )
        )

    # --- academic fit --------------------------------------------------
    # Class rank is context for a human reader, never a number: no university
    # in this product publishes a rank threshold, so scoring it would be
    # inventing a judgement.
    rank = profile.academics.class_rank
    rank_note = (
        f" Class rank {rank}"
        + (f" of {profile.academics.class_size}" if profile.academics.class_size else "")
        + " is recorded for the admissions office to weigh; it is not scored here."
        if rank is not None
        else ""
    )
    if result.eligibility == EligibilityStatus.MET:
        add(
            "Academic fit",
            1.0,
            w.academic_fit,
            "All published requirements checked are met." + rank_note,
        )
    elif result.eligibility == EligibilityStatus.PENDING:
        add(
            "Academic fit",
            0.6,
            w.academic_fit,
            "Requirements are met apart from items still pending (tests, documents, or profile gaps).",
        )
    elif result.eligibility == EligibilityStatus.GAP:
        add("Academic fit", 0.15, w.academic_fit, "At least one published requirement is not met.")
    else:
        add(
            "Academic fit",
            None,
            w.academic_fit,
            "Requirements could not be verified officially.",
            "published requirements",
        )

    # --- funding fit ---------------------------------------------------
    # The form asks how decisive funding is and nothing read the answer. It
    # scales the weight of the two funding components rather than their raw
    # values: a fully funded place is still fully funded, it simply matters
    # more to someone who cannot go without it.
    criticality = {"nice_to_have": 0.5, "important": 0.75, "decisive": 1.0}.get(
        profile.funding.funding_criticality, 1.0
    )
    funding_weight = w.funding_fit * criticality
    funding_raw = {
        FundingFit.CONFIRMED_OPPORTUNITY: 1.0,
        FundingFit.COMPETITIVE_OPPORTUNITY: 0.75,
        FundingFit.LIMITED_OPPORTUNITY: 0.35,
        FundingFit.NOT_ELIGIBLE: 0.0,
    }.get(result.funding_fit)
    if result.funding_fit == FundingFit.UNKNOWN:
        add(
            "Funding fit",
            None,
            funding_weight,
            "No official funding information was confirmed.",
            "scholarship data",
        )
    else:
        add(
            "Funding fit",
            funding_raw,
            funding_weight,
            f"Funding fit is {result.funding_fit.value}; best classification "
            f"{result.best_funding_classification.value}.",
        )

    # --- affordability against the family's own ceiling ------------------
    gap = result.funding_gap
    weight = funding_weight * 0.5
    if gap is None or not gap.computable or gap.gap is None:
        add(
            "Affordability",
            None,
            weight,
            "Remaining annual cost could not be computed.",
            "cost of attendance",
        )
    else:
        ceiling, note, refusal = _comparable_ceiling(profile, gap.gap.currency)
        if refusal:
            add(
                "Affordability",
                None,
                weight,
                refusal,
                "exchange rate for the stated budget currency",
            )
        elif ceiling is None:
            add(
                "Affordability",
                0.5,
                weight,
                f"Remaining annual cost is {gap.gap}. No family budget ceiling was set to compare against.",
            )
        else:
            if ceiling > 0:
                ratio = gap.gap.amount / ceiling
                raw = 1.0 if ratio <= 1 else max(0.0, 1.5 - ratio / 2)
            else:
                # "I can contribute nothing" against a cost that remains: the
                # worst case, not a middling one.
                raw = 1.0 if gap.gap.amount == 0 else 0.0
            contribution = profile.funding.max_family_contribution
            add(
                "Affordability",
                raw,
                weight,
                f"Remaining annual cost {gap.gap.amount:,.0f} {gap.gap.currency} against a stated "
                f"ceiling of {ceiling:,.0f} {gap.gap.currency}{note}."
                + (
                    f" The family states it can contribute up to {contribution:,.0f} "
                    f"{(profile.funding.budget_currency or 'USD').upper()} a year."
                    if contribution is not None
                    else ""
                ),
            )

    # --- country preference ---------------------------------------------
    prefs = profile.preferences
    country = result.country.lower()
    if country in {c.lower() for c in prefs.excluded_countries}:
        add(
            "Country preference",
            0.0,
            w.country_preference,
            f"{result.country} is on the excluded list.",
        )
    elif not prefs.preferred_countries:
        add("Country preference", 0.5, w.country_preference, "No country preference was stated.")
    elif country in {c.lower() for c in prefs.preferred_countries}:
        add(
            "Country preference",
            1.0,
            w.country_preference,
            f"{result.country} is a preferred country.",
        )
    else:
        add(
            "Country preference",
            0.3,
            w.country_preference,
            f"{result.country} is outside the preferred list.",
        )

    # --- programme quality via ranking ------------------------------------
    rank = _best_rank(result)
    if rank is None:
        add(
            "Programme standing",
            None,
            w.program_quality,
            "No ranking position was found.",
            "ranking position",
        )
    else:
        target = {"top_50": 50, "top_100": 100, "top_300": 300, "top_500": 500}.get(
            prefs.target_ranking_band
        )
        raw = max(0.0, 1.0 - (rank / 1000.0))
        note = f"Best ranking position found: {rank}."
        if target:
            raw = 1.0 if rank <= target else max(0.1, 1.0 - (rank - target) / (target * 3))
            note += f" Target band: {prefs.target_ranking_band.replace('_', ' ')}."
        add("Programme standing", raw, w.program_quality, note)

    # --- extracurricular alignment -----------------------------------------
    if not profile.activities and not profile.achievements:
        add(
            "Extracurricular profile",
            None,
            w.extracurricular_alignment,
            "No activities or achievements recorded.",
            "activities",
        )
    else:
        # hours_per_week without weeks_per_year (or the reverse) cannot become
        # annual hours: a school club runs about 34 weeks, a summer lab about
        # 8, a paid job about 48. Any fixed week count would be an invented
        # number multiplied straight into the score, so the half-stated
        # activity keeps the neutral "hours unknown" footing that
        # `_activity_strength` already gives it - and the gap is named rather
        # than left to look like a complete answer.
        partial = [
            a
            for a in profile.activities
            if a.annual_hours is None
            and (a.hours_per_week is not None or a.weeks_per_year is not None)
        ]
        note = (
            ""
            if not partial
            else f" Sustained hours are unknown for {len(partial)} of them: hours per week and"
            " weeks per year only mean something together, and the missing half is not assumed."
        )
        add(
            "Extracurricular profile",
            _activity_strength(profile),
            w.extracurricular_alignment,
            f"{len(profile.activities)} activities and {len(profile.achievements)} achievements, "
            "weighted by level, leadership and sustained hours." + note,
        )
        if partial:
            missing.append("weeks per year for activities with stated hours")

    # --- soft location fits --------------------------------------------------
    add(
        "City fit",
        _label_to_raw(result.city_fit),
        w.city_fit,
        f"City fit assessed as {result.city_fit}.",
    )
    add(
        "Climate fit",
        _label_to_raw(result.climate_fit),
        w.climate_fit,
        f"Climate fit assessed as {result.climate_fit}.",
    )
    add(
        "Workload fit",
        _label_to_raw(result.workload_fit),
        w.workload_fit,
        f"Workload fit assessed as {result.workload_fit}.",
    )
    add(
        "University size",
        _label_to_raw(result.size_fit),
        w.university_size_fit,
        f"Preferred size {prefs.university_size}; this university is assessed as "
        f"{result.size_fit}.",
        "university size",
    )
    add(
        "Campus type",
        _label_to_raw(result.campus_fit),
        w.campus_fit,
        f"Preferred campus {prefs.campus_type}; this university is assessed as "
        f"{result.campus_fit}.",
        "campus type",
    )

    # --- careers -------------------------------------------------------------
    if result.career_notes:
        add(
            "Career and internships",
            0.8 if prefs.values_internships else 0.5,
            w.career_outcomes,
            result.career_notes[:200],
        )
    else:
        add(
            "Career and internships",
            None,
            w.career_outcomes,
            "No official careers information was found.",
            "career information",
        )

    if result.post_study_work:
        add(
            "Post-study work",
            1.0 if prefs.needs_post_study_work else 0.6,
            w.post_study_work,
            result.post_study_work[:200],
        )
    elif prefs.needs_post_study_work:
        add(
            "Post-study work",
            None,
            w.post_study_work,
            "Post-study work rules were not confirmed but matter to this applicant.",
            "post-study work rules",
        )
    else:
        add("Post-study work", 0.5, w.post_study_work, "Post-study work was not a stated priority.")

    total = sum(c.weighted for c in comps)
    max_possible = sum(c.weight for c in comps)
    penalty = min(MAX_MISSING_PENALTY, len(missing) * MISSING_DATA_PENALTY_PER_FIELD)
    total = max(0.0, total * (1 - penalty))

    return ExplainableScore(
        total=round(total, 4),
        max_possible=round(max_possible, 4),
        components=comps,
        missing_data_penalty=round(penalty, 4),
        missing_fields=missing,
    )


def _label_to_raw(label: str) -> float | None:
    return {"strong": 1.0, "good": 0.75, "acceptable": 0.5, "weak": 0.25, "poor": 0.1}.get(label)


def _comparable_ceiling(
    profile: ApplicantProfileIn, target_currency: str
) -> tuple[float | None, str, str]:
    """The family's ceiling, expressed in the currency the gap is in.

    Returns (ceiling, explanatory note, refusal). The ceiling is stated in
    `funding.budget_currency` while the gap is in the target currency, so
    comparing the bare numbers made a 2,880,000 KZT ceiling look infinite
    beside a 6,000 USD gap and every option scored as affordable.

    An unsupported currency is a refusal, never a number: converting at a rate
    we do not hold would be exactly the guess this product refuses to make.
    """
    funding = profile.funding
    # `or` treated a deliberate "I can contribute nothing" as no ceiling at all
    # and silently fell through to the annual budget, a different question.
    ceiling = (
        funding.max_acceptable_gap
        if funding.max_acceptable_gap is not None
        else funding.max_annual_budget
    )
    if ceiling is None:
        return None, "", ""

    source_currency = (funding.budget_currency or "USD").upper()
    target = target_currency.upper()
    if source_currency == target:
        return float(ceiling), "", ""

    try:
        converted = convert(Money(amount=float(ceiling), currency=source_currency), target)
    except UnsupportedCurrency as exc:
        return (
            None,
            "",
            f"The budget is stated in {source_currency} and the remaining cost in {target}. "
            f"No bundled rate connects them, so affordability is left unknown rather than "
            f"guessed. {exc}",
        )
    if not isinstance(converted, ConvertedMoney):  # pragma: no cover - currencies differ here
        return float(converted.amount), "", ""
    note = (
        f" (converted from {ceiling:,.0f} {source_currency} at "
        f"{converted.rate:,.4f} {target}/{source_currency}, rate of {converted.rate_date})"
    )
    return converted.amount, note, ""


def _best_rank(result: ProgramResult) -> int | None:
    best: int | None = None
    for r in result.rankings:
        digits = "".join(ch for ch in r.position.split("-")[0] if ch.isdigit())
        if digits:
            v = int(digits)
            best = v if best is None else min(best, v)
    return best


def _activity_strength(profile: ApplicantProfileIn) -> float:
    level_w = {"school": 0.2, "city": 0.4, "regional": 0.6, "national": 0.85, "international": 1.0}
    role_w = {
        "participant": 0.3,
        "contributor": 0.5,
        "coordinator": 0.7,
        "leader": 0.9,
        "founder": 1.0,
    }
    score = 0.0
    for act in profile.activities:
        base = role_w.get(act.responsibility_level, 0.3)
        hours = act.annual_hours or 0
        sustain = min(1.0, hours / 200.0) if hours else 0.4
        outcome = 1.0 if act.measurable_outcome else 0.7
        score += base * (0.5 + 0.5 * sustain) * outcome
    for ach in profile.achievements:
        score += level_w.get(ach.level, 0.2)
    return min(1.0, score / 6.0)


def admissions_fit_for(
    result: ProgramResult, profile: ApplicantProfileIn
) -> tuple[AdmissionsFit, str]:
    """A coarse, four-way judgement — never a percentage."""
    if result.eligibility == EligibilityStatus.NEEDS_OFFICIAL_CLARIFICATION:
        return (
            AdmissionsFit.INSUFFICIENT_DATA,
            "Published requirements could not be verified, so no comparison is possible.",
        )
    if result.eligibility == EligibilityStatus.GAP:
        return (
            AdmissionsFit.AMBITIOUS,
            "At least one published requirement is currently unmet; selection would depend on "
            "factors beyond the published criteria.",
        )

    met = [c for c in result.requirement_checks if c.status == EligibilityStatus.MET]
    margins = [
        (c.applicant_value - c.published_value) / c.published_value
        for c in met
        if isinstance(c.applicant_value, int | float)
        and isinstance(c.published_value, int | float)
        and c.published_value
    ]
    if not margins:
        return (
            AdmissionsFit.PLAUSIBLE_FIT,
            "Formal requirements are met, but there are no numeric published thresholds to "
            "compare the profile against.",
        )

    avg = sum(margins) / len(margins)
    strength = _activity_strength(profile)
    if avg >= 0.12 and strength >= 0.5:
        return (
            AdmissionsFit.STRONGER_FIT,
            f"Applicant scores sit on average {avg:.0%} above published minimums, with a "
            "substantive activity record. The decision still depends on competitive selection.",
        )
    if avg >= 0.03:
        return (
            AdmissionsFit.PLAUSIBLE_FIT,
            f"Applicant scores sit on average {avg:.0%} above published minimums. "
            "The decision depends on competitive selection.",
        )
    return (
        AdmissionsFit.AMBITIOUS,
        "Applicant scores sit at or barely above published minimums, so the profile is at the "
        "bottom of the published range.",
    )
