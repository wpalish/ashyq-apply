"""KB-2 (NEXT_CYCLES_2026-10-23 #4): v22 -> v23, re-quoted or unverified, from one sandbox check.

``kb_build --refresh`` re-stamps every KB record from a ``verify_evidence.py
--from-kb`` report but, by design, never changes a value: a record whose quote
is gone keeps its old date and gets ``review``. ``kb_build`` itself merges a
later top-up only when it is known (an ``unknown`` never overwrites a known
record). Neither can carry KB-2's two outcomes, so this script composes them
from the two functions, without touching either:

1. ``kb_build.refresh(v22, from_kb_rows)``: every record that still verifies is
   re-stamped with the check's date; every other one is marked ``review``.
2. ``kb_build.build(<this dir>, [batch report])``: the KB-2 drafts, verified by
   their own evidence report, through the ordinary build (year rules, ranges,
   kinds from the reviewed table ``kb_drafts.2026-10-19/unknown_kinds.json``).
3. For each draft, for each question it lists in ``questions_researched``, the
   refreshed entry's records of that question (facts, ``not_applicable``,
   ``unknown``) are replaced by the batch's — when the batch verified them, or
   when the draft itself says ``unknown`` (the page no longer states it). A
   known draft the check could not verify changes nothing (an access failure is
   not evidence that the page changed). Replaced records leave ``review_queue``.

Run from ``backend``, with v22 as the input (``git show
21fcbf69:backend/app/knowledge/kb_cs_bachelor.json > /tmp/kb_v22.json``)::

    PYTHONPATH=. python evaluation/research/expert/data/kb_drafts.2026-10-23/build_v23.py \\
        --kb /tmp/kb_v22.json \\
        --from-kb evaluation/research/expert/data/kb_refresh/evidence_check.kb-refresh-sandbox-2026-10-20.json \\
        --built-at 2026-10-25 --version 2026-10-25.kb-cs-bachelor.23 \\
        --out app/knowledge/kb_cs_bachelor.json
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

from evaluation.research.expert import kb_build
from evaluation.research.expert.kb_refresh_diff import current_stale_reasons

HERE = Path(__file__).resolve().parent
LABEL = "kb_drafts.2026-10-23/batch1"
KINDS = HERE.parent / "kb_drafts.2026-10-19" / kb_build.UNKNOWN_KINDS_FILE

Row = dict[str, Any]


def _drafts(batch: Path) -> list[Row]:
    return [
        json.loads(p.read_text(encoding="utf-8")) for p in sorted((batch / "core").glob("qs*.json"))
    ]


def splice(refreshed: Row, built: Row, drafts: list[Row], *, today: date) -> list[str]:
    """Replace the researched questions of each drafted entry in place; return a log."""
    log: list[str] = []
    entries = refreshed["entries"]
    intake = refreshed.get("intake") or "fall 2027"
    for draft in drafts:
        seed = str(draft["seed_id"])
        entry, new = entries[seed], built["entries"][seed]
        for question in draft.get("questions_researched") or []:
            answer = (draft.get("answers") or {}).get(question) or {}
            facts = list(new["facts"].get(question) or [])
            na = [r for r in new["not_applicable"] if r.get("question") == question]
            unknown = [u for u in new["unknown"] if u.get("question") == question]
            status = str(answer.get("status") or "unknown")
            if status != "unknown" and not (facts or na):
                log.append(
                    f"{seed} {question}: draft {status} not verified by the batch check; v22 kept"
                )
                continue
            for record in (*facts, *na, *unknown):
                record["source_batch"] = LABEL
            for fact in facts:
                reasons = current_stale_reasons(fact, today, intake)
                fact["stale"] = bool(reasons)
                if reasons:
                    fact["stale_reasons"] = reasons
                else:
                    fact.pop("stale_reasons", None)
            old = (
                len(entry["facts"].get(question) or []),
                sum(1 for r in entry["not_applicable"] if r.get("question") == question),
                sum(1 for u in entry["unknown"] if u.get("question") == question),
            )
            entry["facts"][question] = facts
            entry["not_applicable"] = [
                r for r in entry["not_applicable"] if r.get("question") != question
            ] + na
            entry["unknown"] = [
                u for u in entry["unknown"] if u.get("question") != question
            ] + unknown
            refreshed["review_queue"] = [
                r
                for r in refreshed.get("review_queue") or []
                if not (
                    r.get("seed_id") == seed and str(r.get("question")).split(".")[0] == question
                )
            ]
            log.append(
                f"{seed} {question}: facts/na/unknown {old[0]}/{old[1]}/{old[2]} -> "
                f"{len(facts)}/{len(na)}/{len(unknown)}"
            )
        batches = entry.get("source_batches") or [entry.get("source_batch")]
        entry["source_batches"] = [*batches, LABEL] if LABEL not in batches else batches
        records = [
            *(entry["programme"].get("evidence") or []),
            *[f for fs in entry["facts"].values() for f in fs],
        ]
        dates = [str(r["verified_on"]) for r in records if r.get("verified_on")]
        entry["verified_on"] = max(dates) if dates else None
        entry["known_fact_count"] = sum(len(fs) for fs in entry["facts"].values())
    return log


def finish(document: Row, *, built_at: str, version: str, batch_report: str) -> Row:
    """Top-level fields recomputed over the spliced entries."""
    for entry in document["entries"].values():
        records = [
            *(entry["programme"].get("evidence") or []),
            *[f for fs in entry["facts"].values() for f in fs],
        ]
        checks = {str(r.get("verified_by")) for r in records}
        basis = "ci_evidence_check"
        if "recheck" in checks:
            basis += "+sandbox_recheck"
        if kb_build.ROBOTS_OVERRIDE in checks:
            basis += "+robots_override"
        entry["verified_on_basis"] = basis
    document["version"] = version
    document["built_at"] = built_at
    document["evidence_reports"] = [*document["evidence_reports"], batch_report]
    document["stale_facts"] = [
        {"seed_id": s, "question": q, "key": f["key"], "reasons": f["stale_reasons"]}
        for s, e in document["entries"].items()
        for q, fs in e["facts"].items()
        for f in fs
        if f.get("stale")
    ]
    document["robots_override_facts"] = kb_build.robots_override_records(document["entries"])
    if "caveat_facts" in document:
        document["caveat_facts"] = [
            {
                "seed_id": s,
                "question": q,
                "key": f["key"],
                "value": f["value"],
                "caveat": f["caveat"],
                "stale": bool(f.get("stale")),
            }
            for s, e in document["entries"].items()
            for q, fs in e["facts"].items()
            for f in fs
            if f.get("caveat")
        ]
    return document


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--kb", type=Path, required=True)
    parser.add_argument("--from-kb", type=Path, required=True)
    parser.add_argument("--built-at", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    today = date.fromisoformat(args.built_at)
    batch = HERE / "batch1"
    reports = sorted(batch.glob("evidence_check.*.json"))
    rows = json.loads(args.from_kb.read_text(encoding="utf-8"))
    v22 = json.loads(args.kb.read_text(encoding="utf-8"))
    refreshed = kb_build.refresh(v22, rows, today=today, report=args.from_kb.name)
    built = kb_build.build(HERE, reports, built_at=args.built_at, unknown_kinds=KINDS)
    log = splice(refreshed, built, _drafts(batch), today=today)
    document = finish(
        refreshed,
        built_at=args.built_at,
        version=args.version,
        batch_report=f"{LABEL}/" + ",".join(p.name for p in reports),
    )
    args.out.write_text(json.dumps(document, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("\n".join(log))
    known = sum(e["known_fact_count"] for e in document["entries"].values())
    print(
        f"entries={len(document['entries'])} known_facts={known} "
        f"stale={len(document['stale_facts'])} review={len(document['review_queue'])} -> {args.out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
