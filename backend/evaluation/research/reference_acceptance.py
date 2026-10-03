"""Offline release check against reviewed facts, never a source of live answers.

Usage: python -m evaluation.research.reference_acceptance --capture CAPTURE --out REPORT
An incomplete or incorrect result exits 2, even when the crawl itself succeeded.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .metrics import score
from .schema import Capture, Dataset

REVIEWED_DATASET = Path(__file__).parent / "data" / "ground_truth.reviewed.json"


def assess(dataset: Dataset, capture: Capture) -> dict[str, Any]:
    """Use the unchanged strict scorer; unknown facts do not become targets."""
    report = score(dataset, capture)
    observed = {observation.case_id: observation for observation in capture.observations}
    missing = sorted({case.id for case in dataset.cases} - observed.keys())
    errors = {key: row.error for key, row in observed.items() if row.error}
    metrics = report["metrics"]
    recall = metrics["claim_recall"]
    problems = []
    if missing:
        problems.append("missing_cases")
    if errors:
        problems.append("capture_errors")
    if not recall["denominator"]:
        problems.append("no_reviewed_known_facts")
    elif recall["numerator"] < recall["denominator"]:
        problems.append("known_facts_not_recovered")
    for metric, code in (
        ("wrong_scope_claim_rate", "wrong_scope_claims"),
        ("unsupported_claim_rate", "unsupported_claims"),
    ):
        if metrics[metric]["numerator"]:
            problems.append(code)
    precision = metrics["claim_precision"]
    if precision["numerator"] < precision["denominator"]:
        problems.append("incorrect_scored_claims")
    return {
        "reference_facts_complete": not problems,
        "reasons": problems,
        "missing_cases": missing,
        "capture_errors": errors,
        "scope": (
            "Reviewed known facts in this fixed corpus only. Unknown labels remain unknown. "
            "Unadjudicated extra claims, current source freshness, held-out universities and "
            "public runtime acceptance require separate evidence."
        ),
        "report": report,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    dataset = Dataset.model_validate_json(REVIEWED_DATASET.read_text(encoding="utf-8"))
    capture = Capture.model_validate_json(args.capture.read_text(encoding="utf-8"))
    result = assess(dataset, capture)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    recall = result["report"]["metrics"]["claim_recall"]
    print(f"Reviewed facts: {recall['numerator']}/{recall['denominator']}")
    print("PASS" if result["reference_facts_complete"] else "FAIL: " + ", ".join(result["reasons"]))
    raise SystemExit(0 if result["reference_facts_complete"] else 2)


if __name__ == "__main__":
    main()
