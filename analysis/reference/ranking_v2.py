"""Reference implementation of ranking v2 — pure functions, no I/O.

This is the executable form of the formulas in SPEC_matching_v2.md.  It is
deliberately standalone (only the project's Pydantic result/profile types are
imported) so that it can be diffed against the spec and run on stored results
without touching the pipeline.

    cd backend && UNIMATCH_DEMO_MODE=true ./.venv/bin/python ../analysis/reference/ranking_v2.py
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import StrEnum

EPSILON = 0.02  # floor for ln(); a 0.02 axis is a near-veto, not a NaN

# ---------------------------------------------------------------------------
# 1. Weights: rank-order-centroid from the applicant's priority ordering
# ---------------------------------------------------------------------------

PRIORITY_GROUPS: dict[str, dict[str, float]] = {
    # group            -> axis: share of the group's weight
    "funding":         {"funding_fit": 0.5, "affordability": 0.5},
    "academic":        {"academic_fit": 0.6, "programme_standing": 0.4},
    "country":         {"country": 1.0},
    "city_climate":    {"city": 0.5, "climate": 0.5},
    "career":          {"career": 0.5, "post_study_work": 0.5},
    "campus_life":     {"university_size": 1 / 3, "campus": 1 / 3, "workload": 1 / 3},
}


def roc_weights(order: list[str]) -> dict[str, float]:
    """Rank-order-centroid: w_k = (1/n) * sum_{j>=k} 1/j.  Sums to 1."""
    n = len(order)
    out: dict[str, float] = {}
    for k, group in enumerate(order, start=1):
        out[group] = sum(1.0 / j for j in range(k, n + 1)) / n
    return out


def axis_weights(order: list[str]) -> dict[str, float]:
    g = roc_weights(order)
    return {axis: g[grp] * share for grp, axes in PRIORITY_GROUPS.items() for axis, share in axes.items()}


# ---------------------------------------------------------------------------
# 2. Utilities per axis: value in [0,1], UNKNOWN, or NOT_APPLICABLE
# ---------------------------------------------------------------------------

class Missing(StrEnum):
    UNKNOWN = "unknown"              # counts against coverage
    NOT_APPLICABLE = "not_applicable"  # applicant stated no preference; ignored entirely


Utility = float | Missing


@dataclass
class Axis:
    name: str
    value: Utility
    weight: float
    reason: str


def u_academic(eligibility: str, margin: float | None) -> tuple[Utility, str]:
    eligibility = eligibility.lower()
    if eligibility == "met":
        if margin is None:
            return 0.75, "All published requirements met; no numeric minimums to measure a margin against."
        u = min(1.0, max(0.6, 0.6 + 2.0 * margin))
        return u, f"All published requirements met with an average margin of {margin:.0%} above the minimums."
    if eligibility == "pending":
        return 0.5, "Requirements met apart from items still pending."
    if eligibility == "gap":
        return 0.15, "At least one published requirement is not met."
    return Missing.UNKNOWN, "Published requirements could not be verified."


def u_funding(funding_fit: str) -> tuple[Utility, str]:
    funding_fit = funding_fit.lower()
    table = {
        "confirmed_opportunity": 1.0,
        "competitive_opportunity": 0.7,
        "limited_opportunity": 0.3,
        "not_eligible": EPSILON,
    }
    if funding_fit in table:
        return table[funding_fit], f"Funding fit is {funding_fit}."
    return Missing.UNKNOWN, "No official funding information was confirmed."


def u_affordability(gap: float | None, ceiling: float | None) -> tuple[Utility, str]:
    if gap is None:
        return Missing.UNKNOWN, "Remaining annual cost could not be computed."
    if ceiling is None:
        return Missing.UNKNOWN, "No budget ceiling was stated, so affordability cannot be assessed."
    if ceiling <= 0:
        return (1.0 if gap <= 0 else EPSILON), "The family can contribute nothing; any remaining cost is unaffordable."
    r = gap / ceiling
    if r <= 1.0:
        return 1.0, f"Remaining cost {gap:,.0f} is within the stated ceiling {ceiling:,.0f} (ratio {r:.2f})."
    if r <= 1.5:
        return 1.0 - 1.4 * (r - 1.0), f"Remaining cost exceeds the ceiling by {r - 1:.0%} (ratio {r:.2f})."
    return EPSILON, f"Remaining cost is {r:.1f}x the stated ceiling — effectively out of budget."


def u_country(country: str, preferred: list[str], excluded: list[str]) -> tuple[Utility, str]:
    c = country.lower()
    if c in {x.lower() for x in excluded}:
        raise KnockOut(f"{country} is on the excluded list.")
    if not preferred:
        return Missing.NOT_APPLICABLE, "No country preference stated."
    if c in {x.lower() for x in preferred}:
        return 1.0, f"{country} is a preferred country."
    return 0.35, f"{country} is outside the preferred list."


_RANK_ANCHORS = [(1, 1.0), (100, 0.8), (500, 0.5), (1500, 0.2)]


def u_standing(rank: int | None, target_band: str) -> tuple[Utility, str]:
    if rank is None:
        return Missing.UNKNOWN, "No ranking position was found."
    target = {"top_50": 50, "top_100": 100, "top_300": 300, "top_500": 500}.get(target_band)
    if target and rank <= target:
        return 1.0, f"Ranked {rank}, inside the requested {target_band.replace('_', ' ')}."
    x = math.log(rank)
    pts = [(math.log(r), u) for r, u in _RANK_ANCHORS]
    if x >= pts[-1][0]:
        return 0.1, f"Ranked {rank}, well outside the top 1500."
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= x <= x1:
            u = y0 + (y1 - y0) * (x - x0) / (x1 - x0)
            return round(u, 4), f"Consensus ranking position {rank}."
    return 1.0, f"Ranked {rank}."


_LADDERS = {
    "city": ["small", "medium", "large", "metropolis"],
    "climate": ["cold", "temperate", "mediterranean", "warm", "tropical"],
    "workload": ["moderate", "demanding", "very_demanding"],
    "university_size": ["small", "medium", "large"],
}
_LABEL_U = {0: 1.0, 1: 0.75, 2: 0.5}


def u_ladder(axis: str, actual: str | None, preferred: str) -> tuple[Utility, str]:
    if preferred in ("any", "", None):
        return Missing.NOT_APPLICABLE, f"No {axis} preference stated."
    if not actual or actual == "unknown":
        return Missing.UNKNOWN, f"The university's {axis} is not known."
    if actual == preferred:
        return 1.0, f"{axis}: {actual} matches the preference."
    ladder = _LADDERS.get(axis)
    if ladder and actual in ladder and preferred in ladder:
        gap = abs(ladder.index(actual) - ladder.index(preferred))
        return _LABEL_U.get(gap, 0.25), f"{axis}: {actual} vs preferred {preferred} ({gap} step{'s' if gap > 1 else ''} apart)."
    return 0.25, f"{axis}: {actual} differs from preferred {preferred}."


def u_career(has_coop: bool | None, has_internships: bool | None, has_page: bool,
             values_internships: bool, values_coop: bool) -> tuple[Utility, str]:
    if not (values_internships or values_coop):
        return Missing.NOT_APPLICABLE, "Careers were not a stated priority."
    if values_coop and has_coop:
        return 1.0, "A co-op / placement year is officially offered."
    if has_internships:
        return 0.8, "An internship programme is officially described."
    if has_page:
        return 0.5, "A careers page exists but states nothing specific."
    return Missing.UNKNOWN, "No official careers information was found."


def u_post_study_work(months: int | None, needed: bool) -> tuple[Utility, str]:
    if not needed:
        return Missing.NOT_APPLICABLE, "Post-study work was not a stated priority."
    if months is None:
        return Missing.UNKNOWN, "Post-study work rules were not confirmed."
    return max(EPSILON, min(1.0, months / 24.0)), f"Post-study work right of {months} months."


# ---------------------------------------------------------------------------
# 3. Aggregation: weighted geometric mean over known axes + coverage
# ---------------------------------------------------------------------------

class KnockOut(Exception):
    """A confirmed hard filter: the row is listed, not ranked."""


@dataclass
class Score:
    fit: float | None              # [0,1] or None when nothing is known
    coverage: float                # [0,1]
    axes: list[Axis]
    unknown: list[str] = field(default_factory=list)
    not_applicable: list[str] = field(default_factory=list)

    def sort_key(self, gamma: float = 0.5) -> float:
        if self.fit is None:
            return 0.0
        return self.fit * (self.coverage ** gamma)


def aggregate(axes: list[Axis]) -> Score:
    known = [a for a in axes if not isinstance(a.value, Missing)]
    unknown = [a for a in axes if a.value == Missing.UNKNOWN]
    na = [a for a in axes if a.value == Missing.NOT_APPLICABLE]
    w_known = sum(a.weight for a in known)
    w_total = w_known + sum(a.weight for a in unknown)
    if w_known == 0:
        return Score(None, 0.0, axes, [a.name for a in unknown], [a.name for a in na])
    log_sum = sum(a.weight * math.log(max(float(a.value), EPSILON)) for a in known)
    fit = math.exp(log_sum / w_known)
    coverage = w_known / w_total if w_total else 0.0
    # No rounding here: presentation rounds, arithmetic does not (T3 compares exact shares).
    return Score(fit, coverage, axes, [a.name for a in unknown], [a.name for a in na])


# ---------------------------------------------------------------------------
# 4. Portfolio: buckets and a balanced shortlist
# ---------------------------------------------------------------------------

class Bucket(StrEnum):
    WELL_PLACED = "well_placed"          # "safety" in common parlance — never called that in the UI
    PLAUSIBLE = "plausible"              # "match"
    AMBITIOUS = "ambitious"              # "reach"
    OUT_OF_BUDGET = "out_of_budget"
    NEEDS_CLARIFICATION = "needs_clarification"
    EXCLUDED = "excluded"                # knocked out by a confirmed hard filter


_BUDGET_KNOCKOUT_RATIO = {"decisive": 1.5, "important": 2.5, "nice_to_have": math.inf}


def bucket_of(admissions_fit: str, funding_fit: str, gap_ratio: float | None, criticality: str) -> Bucket:
    admissions_fit, funding_fit = admissions_fit.lower(), funding_fit.lower()
    if admissions_fit == "insufficient_data":
        return Bucket.NEEDS_CLARIFICATION
    if gap_ratio is not None and gap_ratio > _BUDGET_KNOCKOUT_RATIO.get(criticality, math.inf):
        return Bucket.OUT_OF_BUDGET
    affordable = gap_ratio is None or gap_ratio <= 1.0
    if admissions_fit == "stronger_fit" and funding_fit == "confirmed_opportunity" and affordable:
        return Bucket.WELL_PLACED
    if admissions_fit in ("stronger_fit", "plausible_fit") and funding_fit in (
        "confirmed_opportunity", "competitive_opportunity"
    ) and (gap_ratio is None or gap_ratio <= 1.5):
        return Bucket.PLAUSIBLE
    return Bucket.AMBITIOUS


@dataclass
class Quotas:
    size: int = 10
    min_well_placed: int = 2
    min_plausible: int = 4
    max_ambitious: int = 3
    max_per_country: int = 3


def build_shortlist(rows: list[dict], quotas: Quotas = Quotas()) -> tuple[list[dict], list[str]]:
    """rows: dicts with keys id, country, bucket, sort_key.  Deterministic."""
    notes: list[str] = []
    chosen: list[dict] = []
    per_country: dict[str, int] = {}
    counts: dict[Bucket, int] = {}

    def can_take(r: dict) -> bool:
        if r["bucket"] == Bucket.AMBITIOUS and counts.get(Bucket.AMBITIOUS, 0) >= quotas.max_ambitious:
            return False
        return per_country.get(r["country"], 0) < quotas.max_per_country

    def take(r: dict) -> None:
        chosen.append(r)
        per_country[r["country"]] = per_country.get(r["country"], 0) + 1
        counts[r["bucket"]] = counts.get(r["bucket"], 0) + 1

    by_key = sorted(rows, key=lambda r: (-r["sort_key"], r["id"]))
    for bucket, minimum in ((Bucket.WELL_PLACED, quotas.min_well_placed), (Bucket.PLAUSIBLE, quotas.min_plausible)):
        got = 0
        for r in by_key:
            if got >= minimum or len(chosen) >= quotas.size:
                break
            if r["bucket"] == bucket and r not in chosen and can_take(r):
                take(r)
                got += 1
        if got < minimum:
            notes.append(f"Only {got} {bucket.value.replace('_', ' ')} option(s) found (wanted at least {minimum}).")
    for r in by_key:
        if len(chosen) >= quotas.size:
            break
        if r["bucket"] in (Bucket.WELL_PLACED, Bucket.PLAUSIBLE, Bucket.AMBITIOUS) and r not in chosen and can_take(r):
            take(r)
    return chosen, notes


# ---------------------------------------------------------------------------
# 5. Demo: rescore the stored demo run and compare with v1
# ---------------------------------------------------------------------------

def _demo() -> None:  # pragma: no cover - manual check
    import json
    import os
    import sys

    sys.path.insert(0, os.getcwd())
    from app.corpus.demo_profile import DEMO_PROFILE
    from app.db import init_db, session_scope
    from app.models import ProgramResultRow
    from app.schemas.result import ProgramResult

    init_db()
    catalog = {r["name"]: r for r in json.load(open("app/corpus/pages/catalog.json"))}
    with session_scope() as s:
        rows = s.query(ProgramResultRow).order_by(ProgramResultRow.score_total.desc()).all()
        results = [(ProgramResult.model_validate(r.payload), r.score_total) for r in rows]

    profile = DEMO_PROFILE
    prefs, funding = profile.preferences, profile.funding
    ceiling = funding.max_acceptable_gap if funding.max_acceptable_gap is not None else funding.max_annual_budget

    def run(order: list[str], climate_pref: str, title: str) -> None:
        w = axis_weights(order)
        table = []
        for r, old in results:
            cat = catalog.get(r.university, {})
            rank = None
            for e in r.rankings:
                digits = "".join(ch for ch in e.position.split("-")[0] if ch.isdigit())
                if digits:
                    rank = int(digits) if rank is None else min(rank, int(digits))
            gap = r.funding_gap.gap.amount if (r.funding_gap and r.funding_gap.computable and r.funding_gap.gap) else None
            met = [c for c in r.requirement_checks if str(c.status).lower() == "met"
                   and isinstance(c.applicant_value, (int, float)) and isinstance(c.published_value, (int, float)) and c.published_value]
            margin = (sum((c.applicant_value - c.published_value) / c.published_value for c in met) / len(met)) if met else None
            try:
                spec = [
                    ("academic_fit", u_academic(r.eligibility.value, margin)),
                    ("funding_fit", u_funding(r.funding_fit.value)),
                    ("affordability", u_affordability(gap, ceiling)),
                    ("country", u_country(r.country, prefs.preferred_countries, prefs.excluded_countries)),
                    ("programme_standing", u_standing(rank, prefs.target_ranking_band)),
                    ("city", u_ladder("city", cat.get("city_size"), prefs.city_size)),
                    ("climate", u_ladder("climate", cat.get("climate"), climate_pref)),
                    ("university_size", u_ladder("university_size", cat.get("size"), prefs.university_size)),
                    ("campus", u_ladder("campus", cat.get("campus"), prefs.campus_type)),
                    ("workload", u_ladder("workload", cat.get("workload"), prefs.acceptable_workload)),
                    ("career", u_career(None, None, bool(r.career_notes), prefs.values_internships, prefs.values_coop)),
                    ("post_study_work", u_post_study_work(24 if r.post_study_work else None, prefs.needs_post_study_work)),
                ]
            except KnockOut as ko:
                table.append((r.university, r.country, old, None, 0.0, 0.0, Bucket.EXCLUDED, str(ko)))
                continue
            axes = [Axis(n, v, w[n], why) for n, (v, why) in spec]
            sc = aggregate(axes)
            ratio = (gap / ceiling) if (gap is not None and ceiling) else None
            b = bucket_of(r.admissions_fit.value, r.funding_fit.value, ratio, funding.funding_criticality)
            table.append((r.university, r.country, old, sc.fit, sc.coverage, sc.sort_key(), b, ""))

        table.sort(key=lambda t: -t[5])
        print(f"\n=== {title} ===")
        print(f"{'University':32} {'Ctry':12} {'v1':>5} {'fit':>5} {'cov':>5} {'key':>5}  bucket")
        for uni, ctry, old, fit, cov, key, b, note in table:
            fit_s = f"{fit:.2f}" if fit is not None else "  -  "
            print(f"{uni[:32]:32} {ctry[:12]:12} {old:5.2f} {fit_s:>5} {cov:5.2f} {key:5.2f}  {b.value}{('  ' + note) if note else ''}")
        rows_for_portfolio = [
            {"id": uni, "country": ctry, "bucket": b, "sort_key": key} for uni, ctry, _, _, _, key, b, _ in table
        ]
        chosen, notes = build_shortlist(rows_for_portfolio)
        print("\nBalanced shortlist:", [f"{c['id'][:18]} [{c['bucket'].value[:4]}]" for c in chosen])
        for n in notes:
            print("  note:", n)

    default_order = ["funding", "academic", "country", "city_climate", "career", "campus_life"]
    run(default_order, prefs.climate, "v2 — priorities: funding > academic > country > city/climate > career > campus")
    run(["city_climate", "funding", "academic", "country", "career", "campus_life"], "warm",
        "v2 — climate=WARM ranked FIRST (does the order react?)")
    run(["city_climate", "funding", "academic", "country", "career", "campus_life"], "cold",
        "v2 — climate=COLD ranked FIRST")


if __name__ == "__main__":
    _demo()
