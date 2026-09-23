"""Which certified facts the pipeline could ever be scored on.

``claim_recall`` counts every known label, but a label is only recoverable if
some claim the pipeline emits can be mapped onto its key. A key that no claim
type produces, or an award or document whose identity is not bound, scores
zero forever, whatever extraction does. Read against 62, a recall of 0 says
nothing about which half of the problem is in the way; read against this
ceiling, it does.

Two ceilings, because two mappings exist. The live capture maps with
``normalize_claim`` alone: the identity bindings are drafts awaiting review
(HANDOFF), so no award or document fact can score live. The offline mapper
applies them. Both are printed; neither is changed here, because adding a
binding or a claim type is an identity decision for a person.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .mapping import AWARD_KEYS, CLAIM_KEYS, COVERAGE_KEYS
from .schema import Dataset

REACHABLE = "reachable"
NO_CLAIM_TYPE = "no claim type"
UNBOUND = "identity not bound"
UNSUPPORTED_FIELD = "bound, field not mapped"

#: The coverage categories ``normalize_subject_claims`` accepts.
_COVERAGE = (
    "tuition",
    "mandatory_fees",
    "housing",
    "meals",
    "health_insurance",
    "books",
    "travel",
    "visa",
    "personal",
)
_AWARD_FIELDS = frozenset(
    {"exists", *AWARD_KEYS.values(), *(f"coverage.{COVERAGE_KEYS.get(c, c)}" for c in _COVERAGE)}
)
_DOCUMENT_FIELDS = frozenset({"required", "maximum_words"})


@dataclass(frozen=True, slots=True)
class Reach:
    case_id: str
    key: str
    verdict: str


def reach(key: str, bindings: dict[str, str]) -> str:
    """Why ``key`` can or cannot be produced, given ``{prefix: kind}`` bindings."""
    if key in set(CLAIM_KEYS.values()):
        return REACHABLE
    for prefix, kind in bindings.items():
        if key.startswith(prefix + "."):
            field = key[len(prefix) + 1 :]
            fields = _AWARD_FIELDS if kind == "award" else _DOCUMENT_FIELDS
            return REACHABLE if field in fields else UNSUPPORTED_FIELD
    if key.startswith(("scholarships.", "documents.")):
        return UNBOUND
    return NO_CLAIM_TYPE


def report(dataset: Dataset, bindings: dict[str, str]) -> list[Reach]:
    """One verdict per known label, in the same population ``claim_recall`` counts."""
    return [
        Reach(case.id, label.key, reach(label.key, bindings))
        for case in dataset.cases
        for label in case.labels
        if label.status == "known"
    ]


def summarise(rows: list[Reach]) -> str:
    counts = Counter(r.verdict for r in rows)
    lines = [
        f"claim_recall can be scored on at most {counts[REACHABLE]} of {len(rows)} known facts",
    ]
    for verdict in (NO_CLAIM_TYPE, UNBOUND, UNSUPPORTED_FIELD):
        lines.append(f"  {verdict:26} {counts.get(verdict, 0)}")
        lines.extend(f"      {r.case_id}: {r.key}" for r in rows if r.verdict == verdict)
    return "\n".join(lines)


def load_bindings(path: Path) -> dict[str, str]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {b["key"]: b["kind"] for b in raw.get("bindings", [])}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--bindings", type=Path, required=True)
    args = parser.parse_args()
    dataset = Dataset.model_validate_json(args.dataset.read_text(encoding="utf-8"))
    print("LIVE (the capture maps without identity bindings)")
    print(summarise(report(dataset, {})))
    print()
    print(f"OFFLINE, with the draft bindings in {args.bindings.name}")
    print(summarise(report(dataset, load_bindings(args.bindings))))


if __name__ == "__main__":
    main()
