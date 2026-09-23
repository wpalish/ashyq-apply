"""Why a claim with the right value still did not count as supported.

``metrics.score`` counts a claim correct only when its value matches, its scope
matches, and it is *supported*. Without a human adjudication, supported means
``exact_evidence`` on the same page. Until 2026-09-23 that was one direction
only — our quote inside the reviewer's — and reviewers quote the least that
proves a fact ("6.5", "4 May 2026") while the pipeline quotes a sentence, so a
right value from the right page was never supported. The owner then accepted
the reverse as well, for a quote of at most ``SUPPORTING_QUOTE_MAX`` characters
(``metrics.quote_supports``).

This walks the claims whose value already matches and says, for each, which
relation holds, so the effect of the rule stays visible run by run.

Evaluation tooling: it reads the certified corpus, so nothing under ``app/``
may import it, and it is never part of a run.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .metrics import SUPPORTING_QUOTE_MAX, _domain, canonical_url
from .schema import Capture, Dataset

#: Our quote lies inside the reviewer's: the original rule.
OURS_IN_THEIRS = "ours_in_theirs"
#: The reviewer's quote lies inside ours: we quoted the certifying words and more.
#: Counted as supported since the owner's decision of 2026-09-23.
THEIRS_IN_OURS = "theirs_in_ours"
#: The reviewer's words are inside ours, but ours is too long to be a quotation.
THEIRS_IN_LONG_QUOTE = "theirs_in_long"
#: Same page, and neither quote contains the other.
NEITHER = "neither"
#: Another page of the same university's site than any the reviewer cited.
#: Counted as supported since the owner's decision of 2026-09-23.
SAME_SITE = "same_site"
#: A page on another site entirely.
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
        theirs = label.evidence[0].excerpt if label.evidence else ""
        if _domain(evidence.url) in {_domain(e.url) for e in label.evidence}:
            return SAME_SITE, theirs
        return OTHER_PAGE, theirs
    ours = " ".join(evidence.excerpt.split())
    for theirs in same_page:
        if ours and ours in " ".join(theirs.excerpt.split()):
            return OURS_IN_THEIRS, theirs.excerpt
    for theirs in same_page:
        flat = " ".join(theirs.excerpt.split())
        if flat and flat in ours:
            shape = THEIRS_IN_OURS if len(ours) <= SUPPORTING_QUOTE_MAX else THEIRS_IN_LONG_QUOTE
            return shape, theirs.excerpt
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
    for shape in (
        OURS_IN_THEIRS,
        THEIRS_IN_OURS,
        THEIRS_IN_LONG_QUOTE,
        NEITHER,
        SAME_SITE,
        OTHER_PAGE,
        NO_EVIDENCE,
    ):
        lines.append(f"  {shape:15} {counts.get(shape, 0)}")
    lines.append("")
    lines.append(
        f"{OURS_IN_THEIRS}, {THEIRS_IN_OURS} and {SAME_SITE} count as supported "
        "(owner decisions 2026-09-23); "
        f"{THEIRS_IN_LONG_QUOTE} holds the reviewer's words inside more than "
        f"{SUPPORTING_QUOTE_MAX} characters, which does not."
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
