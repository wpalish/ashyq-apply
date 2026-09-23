"""How much better could *ranking alone* make discovery?

Before comparing rerankers — a cross-encoder, Jev, an LLM, each with its own
cost per candidate — it is worth asking whether reordering can help at all. A
reranker can only reorder the set retrieval produced. If the correct page is
not in that set, no ranking function reaches it, and a comparison between
rerankers measures nothing.

This module answers that by intersecting two things the project already has
and trusts: the ``ranked_urls`` of the frozen capture, which is what the
pipeline really surfaced on a bounded canary run, and the certified corpus's
``programme_urls``, which a named human signed.

Both sides are canonicalised with the same function discovery uses, so a
trailing slash or a tracking parameter cannot make a hit look like a miss.

It is evaluation tooling: it never runs in production and never touches the
network.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from app.adapters.discovery.live_discovery import canonical_url


@dataclass(frozen=True)
class CaseCeiling:
    """What reranking could do for one case."""

    case_id: str
    candidates: int
    #: 1-based position of the best correct page, or ``None`` if absent.
    correct_position: int | None

    @property
    def reachable(self) -> bool:
        """Whether any reranker could put a correct page first."""
        return self.correct_position is not None

    @property
    def already_first(self) -> bool:
        return self.correct_position == 1


@dataclass(frozen=True)
class CeilingReport:
    dataset_version: str
    cases: tuple[CaseCeiling, ...]

    @property
    def scored(self) -> int:
        """Cases with a ground-truth URL to be right about."""
        return len(self.cases)

    @property
    def ceiling(self) -> int:
        """Cases a perfect reranker could get right."""
        return sum(1 for c in self.cases if c.reachable)

    @property
    def already_correct(self) -> int:
        """Cases the current ranking already puts first."""
        return sum(1 for c in self.cases if c.already_first)

    @property
    def headroom(self) -> int:
        """Cases a better ranking could win. The whole case for a reranker."""
        return self.ceiling - self.already_correct

    @property
    def retrieved_nothing(self) -> int:
        return sum(1 for c in self.cases if c.candidates == 0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_version": self.dataset_version,
            "scored_cases": self.scored,
            "reranking_ceiling": self.ceiling,
            "already_first": self.already_correct,
            "headroom_for_any_reranker": self.headroom,
            "cases_with_no_candidates": self.retrieved_nothing,
            "cases": [asdict(c) for c in self.cases],
        }


def compute_ceiling(dataset: dict[str, Any], capture: dict[str, Any]) -> CeilingReport:
    """Intersect what was retrieved with what is correct."""
    truth = {
        case["id"]: {canonical_url(url) for url in case["programme_urls"]}
        for case in dataset["cases"]
    }

    cases: list[CaseCeiling] = []
    for observation in capture["observations"]:
        case_id = observation["case_id"]
        correct = truth.get(case_id) or set()
        if not correct:
            # No signed answer for this case: it cannot be scored either way,
            # and counting it as a miss would blame retrieval for a gap in
            # the corpus.
            continue

        ranked = [canonical_url(url) for url in observation.get("ranked_urls") or []]
        positions = [i + 1 for i, url in enumerate(ranked) if url in correct]
        cases.append(
            CaseCeiling(
                case_id=case_id,
                candidates=len(ranked),
                correct_position=min(positions) if positions else None,
            )
        )

    return CeilingReport(dataset_version=dataset["version"], cases=tuple(cases))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--capture", required=True, type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)

    report = compute_ceiling(
        json.loads(args.dataset.read_text(encoding="utf-8")),
        json.loads(args.capture.read_text(encoding="utf-8")),
    )
    rendered = json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()
