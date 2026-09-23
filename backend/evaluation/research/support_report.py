"""Why a claim with the right value still did not count as supported.

``metrics.score`` counts a claim correct only when its value matches, its scope
matches, and it is *supported*. Without a human adjudication, supported means
``exact_evidence``: the claim's quote is contained **in** the reviewer's quote,
on the same page. Reviewers quote the least that proves a fact ("6.5",
"4 May 2026"); the pipeline quotes a window around its match. So a claim can
carry the right value from the right page and still never be supported.

This walks the claims whose value already matches and says, for each, which
direction of containment holds. Nothing here changes the scorer: the direction
is a definition for the owner to settle, and this is the evidence for it.

Evaluation tooling: it reads the certified corpus, so nothing under ``app/``
may import it, and it is never part of a run.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .metrics import canonical_url
from .schema import Capture, Dataset

#: Our quote lies inside the reviewer's: what the scorer counts today.
OURS_IN_THEIRS = "ours_in_theirs"
#: The reviewer's quote lies inside ours: we quoted the certifying words and more.
THEIRS_IN_OURS = "theirs_in_ours"
#: Same page, and neither quote contains the other.
NEITHER = "neither"
#: Our quote is from another page than any the reviewer cited.
OTHER_PAGE = "other_page"
NO_EVIDENCE = "no_evidence"


@dataclass(frozen=True, slots=True)
class Support:
    case_id: str
    key: str
    shape: str
    ours: str
    theirs: str

    def line(self) -> str:
        return f"{self.case_id:11} {self.key:28} {self.shape:15} ours={self.ours[:70]!r}"


def _shape(prediction, label) -> tuple[str, str]:
    evidence = prediction.evidence
    if evidence is None:
        return NO_EVIDENCE, ""
    same_page = [e for e in label.evidence if canonical_url(e.url) == canonical_url(evidence.url)]
    if not same_page:
        return OTHER_PAGE, label.evidence[0].excerpt if label.evidence else ""
    for theirs in same_page:
        if evidence.excerpt in theirs.excerpt:
            return OURS_IN_THEIRS, theirs.excerpt
    for theirs in same_page:
        if theirs.excerpt in evidence.excerpt:
            return THEIRS_IN_OURS, theirs.excerpt
    return NEITHER, same_page[0].excerpt


def support_shapes(dataset: Dataset, capture: Capture) -> list[Support]:
    """Every value-correct prediction on a known label, and how its quote relates."""
    observed = {o.case_id: o for o in capture.observations}
    found: list[Support] = []
    for case in dataset.cases:
        observation = observed.get(case.id)
        if observation is None:
            continue
        labels = {label.key: label for label in case.labels if label.status == "known"}
        seen: set[str] = set()
        for prediction in observation.predictions:
            if prediction.value is None or prediction.value == "UNKNOWN":
                continue
            fingerprint = prediction.model_dump_json()
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            label = labels.get(prediction.key)
            if label is None:
                continue
            if json.dumps(prediction.value, sort_keys=True) != json.dumps(
                label.value, sort_keys=True
            ):
                continue
            shape, theirs = _shape(prediction, label)
            ours = prediction.evidence.excerpt if prediction.evidence else ""
            found.append(Support(case.id, prediction.key, shape, ours, theirs))
    return found


def summarise(rows: list[Support]) -> str:
    if not rows:
        return "no value-correct claims to adjudicate"
    counts = Counter(r.shape for r in rows)
    lines = [r.line() for r in rows]
    lines.append("")
    lines.append(f"{len(rows)} claims carry the certified value")
    for shape in (OURS_IN_THEIRS, THEIRS_IN_OURS, NEITHER, OTHER_PAGE, NO_EVIDENCE):
        lines.append(f"  {shape:15} {counts.get(shape, 0)}")
    lines.append("")
    lines.append(
        f"only {OURS_IN_THEIRS} counts as supported today; {THEIRS_IN_OURS} quoted the "
        "reviewer's words and more, which the scorer does not accept."
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--capture", type=Path, required=True)
    args = parser.parse_args()
    dataset = Dataset.model_validate_json(args.dataset.read_text(encoding="utf-8"))
    capture = Capture.model_validate_json(args.capture.read_text(encoding="utf-8"))
    print(summarise(support_shapes(dataset, capture)))


if __name__ == "__main__":
    main()
