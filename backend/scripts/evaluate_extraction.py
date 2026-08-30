#!/usr/bin/env python
"""Measure extraction against hand-verified truth, per field.

The canary counts the claims the extractor produced. It cannot say whether that
is many or few, because nothing records what the pages actually said. "51
claims" and "5.6% complete" are both compatible with an extractor that is
nearly right and with one that is nearly useless.

This reads `app/corpus/gold/gold_claims.json` — answers a person read off the
institutions' own pages — runs the real adapters against the same programmes,
and reports precision and recall per decision question.

    ./.venv/bin/python scripts/evaluate_extraction.py
    ./.venv/bin/python scripts/evaluate_extraction.py --only rug --json out.json

What the three verdicts do here
-------------------------------

``answered``    the page says it. Not producing it is a false negative.
``absent``      the page does not say it. Producing it anyway is a false
                positive — the dangerous direction, because an applicant acts
                on an invented deadline.
``not_checked`` excluded from both, and reported as coverage. A benchmark that
                hides its gaps produces a number that looks like a measurement.

It is deliberately not a test: it needs the network, it is slow, and a drop
here is a finding to investigate rather than a build to fail. The offline
suite covers the extraction *rules*; this covers what they reach on real pages.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.adapters.base import Candidate, CandidateProgram  # noqa: E402
from app.adapters.cost.web_costs import WebCostAdapter  # noqa: E402
from app.adapters.fetching import Fetcher  # noqa: E402
from app.adapters.requirements.web_requirements import (  # noqa: E402
    WebRequirementsAdapter,
)
from app.config import get_settings  # noqa: E402
from app.domain.enums import ClaimStatus, ClaimType, DegreeLevel  # noqa: E402
from app.eval.gold import ABSENT, ANSWERED, GoldProgramme, load_gold  # noqa: E402
from app.pipeline.assessment import DECISION_QUESTIONS  # noqa: E402

QUESTION_TYPES: dict[str, tuple[ClaimType, ...]] = dict(DECISION_QUESTIONS)


@dataclass
class Tally:
    """One decision question's score across every programme audited."""

    true_positive: int = 0
    false_negative: int = 0
    false_positive: int = 0
    true_negative: int = 0
    #: Right question, wrong value. Counted separately: a wrong number is not
    #: the same failure as a missing one, and averaging them hides which.
    wrong_value: int = 0
    misses: list[str] = field(default_factory=list)

    @property
    def precision(self) -> float | None:
        produced = self.true_positive + self.false_positive
        return self.true_positive / produced if produced else None

    @property
    def recall(self) -> float | None:
        should = self.true_positive + self.false_negative
        return self.true_positive / should if should else None

    @property
    def f1(self) -> float | None:
        p, r = self.precision, self.recall
        if p is None or r is None or p + r == 0:
            return None
        return 2 * p * r / (p + r)


#: Tokens too short to carry meaning on their own. Requiring them to match
#: would fail a gold value of "BSc in Computing Science" against a produced
#: "Computing Science" over the word "in".
_MIN_TOKEN = 3
_TOKEN = re.compile(r"[a-z0-9]+(?:\.[0-9]+)?")


def leaves(value: Any) -> str:
    """Flatten a produced value to the text it contains.

    Claims carry whatever shape the extractor found useful — a float for an
    IELTS band, a dict for a fee, a list for required subjects. Gold truth is
    written the way the page states it, and must stay that way: a benchmark
    written in the extractor's own data structures measures agreement with the
    implementation rather than with the institution.
    """
    if isinstance(value, dict):
        return " ".join(leaves(v) for v in value.values())
    if isinstance(value, list | tuple | set):
        return " ".join(leaves(v) for v in value)
    return str(value)


def tokens(text: str) -> set[str]:
    out: set[str] = set()
    for token in _TOKEN.findall(text.lower()):
        try:
            number = float(token)
        except ValueError:
            if len(token) >= _MIN_TOKEN:
                out.add(token)
        else:
            # 2694, 2694.0 and 2,694 are one number; 05 and 5 are one month.
            out.add(f"{number:g}")
    return out


def values_agree(gold: str, produced: Any) -> bool:
    """Whether a produced value says what the page said.

    The rule is containment, not equality: every meaningful token of the gold
    value has to appear in the produced one. That lets a fee recorded as
    "EUR 2694" match a claim carrying `{'amount': 2694.0, 'currency': 'EUR'}`,
    while "6.5" still fails against 7.0 — which is the comparison that has to
    stay sharp, because a wrong English requirement is a rejected application.
    """
    wanted = tokens(gold)
    return bool(wanted) and wanted <= tokens(leaves(produced))


async def claims_for(programme: GoldProgramme, intake: str) -> list[Any]:
    """Run the real adapters over one gold programme."""
    settings = get_settings()
    candidate = Candidate(
        name=programme.institution,
        country="",
        city="",
        domain=programme.domain,
        programs=[
            CandidateProgram(
                name=programme.programme,
                field=programme.discipline,
                degree=DegreeLevel.BACHELOR,
                url=programme.programme_url,
            )
        ],
    )
    # The same politeness the canary uses: robots respected, a contact in the
    # user agent, and the project's own cache so a re-run does not re-fetch.
    async with Fetcher(
        settings.cache_dir,
        delay_seconds=settings.fetch_delay_seconds or 1.0,
        respect_robots=True,
        contact="extraction-eval",
    ) as fetcher:
        requirements = WebRequirementsAdapter(fetcher, settings.academic_year)
        costs = WebCostAdapter(fetcher, settings.academic_year)
        produced = await requirements.verify(candidate, candidate.programs[0], intake)
        claims = list(produced.claims)
        try:
            _breakdown, cost_result = await costs.fetch(candidate)
        except Exception as exc:  # pragma: no cover - a live-network path
            print(f"  cost adapter failed: {type(exc).__name__}: {exc}")
        else:
            claims.extend(cost_result.claims)
    return claims


def score(programme: GoldProgramme, claims: list[Any], tallies: dict[str, Tally]) -> None:
    by_type: dict[ClaimType, list[Any]] = {}
    for claim in claims:
        by_type.setdefault(claim.claim_type, []).append(claim)

    for answer in programme.checked():
        tally = tallies.setdefault(answer.question, Tally())
        types = QUESTION_TYPES.get(answer.question, ())
        produced = [c for t in types for c in by_type.get(t, [])]

        if answer.verdict == ANSWERED:
            if not produced:
                tally.false_negative += 1
                tally.misses.append(f"{programme.id}: not produced")
                continue
            gold_values = [c.value for c in answer.claims]
            if any(
                values_agree(str(g), p.normalized_value)
                for g in gold_values
                for p in produced
            ):
                tally.true_positive += 1
            else:
                tally.wrong_value += 1
                tally.false_positive += 1
                tally.misses.append(
                    f"{programme.id}: expected {gold_values[0]!r}, produced "
                    f"{produced[0].normalized_value!r}"
                )
        elif answer.verdict == ABSENT:
            if produced:
                tally.false_positive += 1
                tally.misses.append(
                    f"{programme.id}: produced {produced[0].normalized_value!r} "
                    "for a question the page does not answer"
                )
            else:
                tally.true_negative += 1


#: `_completeness` in the pipeline counts a question as answered only when a
#: claim for it is VERIFIED_CURRENT or POSSIBLY_STALE. A claim that comes back
#: UNVERIFIED raises the claim count and moves completeness not at all — which
#: would make "51 claims, 5.6% complete" consistent, and is worth being able to
#: see rather than infer.
COUNTS_TOWARD_COMPLETENESS = (ClaimStatus.VERIFIED_CURRENT, ClaimStatus.POSSIBLY_STALE)


def status_breakdown(claims: list[Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for claim in claims:
        counts[claim.status.value] = counts.get(claim.status.value, 0) + 1
    return dict(sorted(counts.items()))


def report(tallies: dict[str, Tally], coverage: dict[str, int]) -> dict[str, Any]:
    rows = []
    for label, _types in DECISION_QUESTIONS:
        tally = tallies.get(label)
        if tally is None:
            rows.append({"question": label, "audited": 0})
            continue
        rows.append(
            {
                "question": label,
                "audited": (
                    tally.true_positive + tally.false_negative
                    + tally.false_positive + tally.true_negative
                ),
                "true_positive": tally.true_positive,
                "false_negative": tally.false_negative,
                "false_positive": tally.false_positive,
                "true_negative": tally.true_negative,
                "wrong_value": tally.wrong_value,
                "precision": tally.precision,
                "recall": tally.recall,
                "f1": tally.f1,
                "misses": tally.misses[:5],
            }
        )
    total = Tally()
    for tally in tallies.values():
        total.true_positive += tally.true_positive
        total.false_negative += tally.false_negative
        total.false_positive += tally.false_positive
        total.true_negative += tally.true_negative
        total.wrong_value += tally.wrong_value
    return {
        "coverage": coverage,
        "questions": rows,
        "overall": {
            "true_positive": total.true_positive,
            "false_negative": total.false_negative,
            "false_positive": total.false_positive,
            "true_negative": total.true_negative,
            "wrong_value": total.wrong_value,
            "precision": total.precision,
            "recall": total.recall,
            "f1": total.f1,
        },
    }


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", help="substring of a gold programme id")
    parser.add_argument("--intake", default="September 2027")
    parser.add_argument("--json", type=Path, help="write the full report here")
    args = parser.parse_args()

    gold = load_gold()
    coverage = gold.coverage()
    print(
        f"gold set frozen {gold.frozen_at} at {gold.frozen_at_commit[:8]}  "
        f"{coverage['programmes_resolved']}/{coverage['programmes']} programmes "
        f"resolved, {coverage['answered'] + coverage['absent']}/"
        f"{coverage['question_slots']} question slots audited"
    )
    if not coverage["answered"] and not coverage["absent"]:
        print(
            "\nNothing has been audited yet, so there is nothing to measure. "
            "This is reported rather than scored as 0: an unaudited benchmark "
            "is not a result."
        )
        return 0

    targets = [
        p for p in gold.resolved()
        if p.checked() and (not args.only or args.only in p.id)
    ]
    tallies: dict[str, Tally] = {}
    statuses: dict[str, int] = {}
    for programme in targets:
        print(f"\n{programme.id}  {programme.programme}")
        claims = await claims_for(programme, args.intake)
        counting = sum(1 for c in claims if c.status in COUNTS_TOWARD_COMPLETENESS)
        breakdown = status_breakdown(claims)
        for status, n in breakdown.items():
            statuses[status] = statuses.get(status, 0) + n
        print(
            f"  {len(claims)} claim(s) produced, {counting} of which count "
            f"toward completeness  {breakdown}"
        )
        score(programme, claims, tallies)

    result = report(tallies, coverage)
    result["claim_status_totals"] = dict(sorted(statuses.items()))
    print()
    print(f"{'question':<42} {'audit':>5} {'prec':>6} {'rec':>6} {'F1':>6}")
    for row in result["questions"]:
        if not row["audited"]:
            continue
        fmt = lambda v: f"{v:6.2f}" if isinstance(v, float) else "     -"  # noqa: E731
        print(
            f"{row['question'][:42]:<42} {row['audited']:>5} "
            f"{fmt(row['precision'])} {fmt(row['recall'])} {fmt(row['f1'])}"
        )
    print(f"\nclaim statuses across every programme: {result['claim_status_totals']}")
    overall = result["overall"]
    print(
        f"\noverall  tp={overall['true_positive']} fn={overall['false_negative']} "
        f"fp={overall['false_positive']} tn={overall['true_negative']} "
        f"(of which wrong value: {overall['wrong_value']})"
    )
    if args.json:
        args.json.write_text(json.dumps(result, indent=2) + "\n")
        print(f"wrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
