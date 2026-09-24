"""Why a claim's scope did not match — dimension by dimension.

``wrong_scope_claim_rate`` has always reported a number and never a reason. It
sat at 5/5 through all of Phase 2 and came back 3/3 from the first honest live
capture, and neither figure says *what* is wrong: a page that stated the wrong
population and a page that stated nothing at all score identically, while the
fix for one is nothing like the fix for the other.

This walks the same adjudicable predictions ``metrics.score`` walks and names
each mismatch as one of three shapes:

``silent``
    The label expects a value; the evidence records none. Nobody lied — the
    page did not say, and a page that does not say cannot be made to.

``differs``
    Both sides state the dimension and they disagree. Either the wrong page was
    read, or the label is wrong; both are worth a human's attention.

``unrecorded``
    No scope was recorded at all. That is a gap in our own pipeline rather than
    a fact about any page, and it is the only shape that is purely our bug.

Evaluation tooling: it reads the certified corpus, so nothing under ``app/``
may import it, and it is never part of a run.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

from .schema import Capture, Dataset, Scope

#: The dimensions a label can carry, in the order a reviewer reads them.
DIMENSIONS = (
    "university",
    "programme",
    "degree",
    "field",
    "intake",
    "population",
    "qualification",
    "academic_year",
)


@dataclass(frozen=True, slots=True)
class Mismatch:
    case_id: str
    key: str
    dimension: str
    expected: str
    recorded: str | None
    shape: str

    def line(self) -> str:
        got = "—" if self.recorded is None else repr(self.recorded)
        return (
            f"{self.case_id:12} {self.key:28} {self.dimension:14} "
            f"{self.shape:10} expected {self.expected!r}, recorded {got}"
        )


def _mismatches(expected: Scope, actual: Scope | None, case_id: str, key: str) -> list[Mismatch]:
    out: list[Mismatch] = []
    for dimension in DIMENSIONS:
        wanted = getattr(expected, dimension, None)
        if not wanted:
            continue
        if actual is None:
            out.append(Mismatch(case_id, key, dimension, wanted, None, "unrecorded"))
            continue
        got = getattr(actual, dimension, None)
        if got is None:
            out.append(Mismatch(case_id, key, dimension, wanted, None, "silent"))
        elif got != wanted and not (
            # The scorer compares every non-programme dimension case-blind
            # since 2026-09-23; a report that still flags "Fall 2027" against
            # "fall 2027" points at a difference that no longer costs a fact.
            dimension != "programme" and str(got).casefold() == str(wanted).casefold()
        ):
            out.append(Mismatch(case_id, key, dimension, wanted, got, "differs"))
    return out


def scope_mismatches(dataset: Dataset, capture: Capture) -> list[Mismatch]:
    """Every dimension that kept a known claim from scoring as in-scope.

    Deliberately mirrors ``metrics.score``'s selection — known labels, deduped
    predictions — so this explains the same claims the rate counts, and cannot
    quietly describe a different population than the number does.
    """
    observed = {o.case_id: o for o in capture.observations}
    found: list[Mismatch] = []
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
            evidence = prediction.evidence
            if evidence is not None and any(
                not _mismatches(e.scope, evidence.scope, case.id, prediction.key)
                for e in label.evidence
            ):
                continue  # one of the label's evidence scopes matched: in scope
            for expected in label.evidence:
                found.extend(
                    _mismatches(
                        expected.scope,
                        evidence.scope if evidence else None,
                        case.id,
                        prediction.key,
                    )
                )
    return found


def same_programme_under_another_name(mismatches: list[Mismatch]) -> list[Mismatch]:
    """Programme mismatches where both titles name one programme.

    Reported **beside** the rate, never folded into it. Whether the scorer
    should compare programme identity instead of programme strings is a change
    to what the benchmark means, and that is the owner's call — so this
    produces the evidence for that decision and changes no number.
    """
    from app.adapters.search.ontology import titles_name_same_programme
    from app.domain.programme_identity import Verdict

    return [
        m
        for m in mismatches
        if m.dimension == "programme"
        and m.recorded is not None
        and titles_name_same_programme(m.recorded, m.expected) is Verdict.YES
    ]


def summarise(mismatches: list[Mismatch]) -> str:
    if not mismatches:
        return "no scope mismatches: every adjudicable claim matched a label's scope"
    by_shape = Counter(m.shape for m in mismatches)
    by_dimension = Counter(f"{m.dimension} ({m.shape})" for m in mismatches)
    lines = [m.line() for m in mismatches]
    lines.append("")
    lines.append("by shape:     " + ", ".join(f"{k}={v}" for k, v in sorted(by_shape.items())))
    lines.append("by dimension: " + ", ".join(f"{k}={v}" for k, v in sorted(by_dimension.items())))
    renamed = same_programme_under_another_name(mismatches)
    if renamed:
        lines.append("")
        lines.append(
            f"of those, {len(renamed)} name the same programme as the label under a "
            "different title, by the ontology's own strong aliases:"
        )
        lines.extend(f"  {m.case_id}: {m.recorded!r} vs {m.expected!r}" for m in renamed)
        lines.append(
            "  (the scorer counts these as matches since 2026-09-22, when the owner settled "
            "that programme identity is compared rather than strings; they are listed here "
            "because a rename is still worth seeing)"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--json", type=Path, help="also write the mismatches as JSON")
    args = parser.parse_args()
    dataset = Dataset.model_validate_json(args.dataset.read_text(encoding="utf-8"))
    capture = Capture.model_validate_json(args.capture.read_text(encoding="utf-8"))
    mismatches = scope_mismatches(dataset, capture)
    print(summarise(mismatches))
    if args.json:
        args.json.write_text(
            json.dumps([asdict(m) for m in mismatches], indent=2), encoding="utf-8"
        )


if __name__ == "__main__":
    main()
