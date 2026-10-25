"""KB-3 (NEXT_CYCLES_2026-10-26): v22 -> v24, ``build_v23.py``'s steps plus the 2026-10-25 checks.

The same composition of the two ``kb_build`` functions as ``build_v23.py``
(nothing under ``app/`` or in ``kb_build.py`` changes), with the evidence of
v23 plus:

1. ``kb_build.refresh(v22, from_kb_rows)`` exactly as in v23 (the 2026-10-20
   sandbox ``--from-kb`` check).
2. Each ``--draft-check`` report (a CI ``verify_evidence`` run over a drafts
   dir, e.g. ``kb_drafts.2026-10-19/topup_documents4/evidence_check.ci-2026-10-25.json``)
   is turned into ``--from-kb`` rows by joining each row to its draft's quote
   (``verify_evidence.items``), and a second ``kb_build.refresh`` re-stamps
   exactly the KB records with that (seed, item, key, URL, quote): a found
   quote re-dates the record (``verified_by: ci``) and removes its ``review``;
   a failed read (an HTTP 403, say) keeps value and date and marks ``review``
   with the class ``kb_refresh_diff.classify`` gives it. Only document rows
   (``documents.<kind>``, whose KB key is the item) are joined; any other row
   is reported and skipped. A record the report did not check is left as it was.
3. Each ``--batch`` (a drafts root with one ``batch1``, its reports globbed)
   built by ``kb_build.build`` and spliced per researched question
   (``build_v23.splice``), in the order given: KB-2's ``kb_drafts.2026-10-23``
   (now with CI's report beside the sandbox's; a passing CI row wins) and KB-3's
   ``kb_drafts.2026-10-26`` (the TCD scholarship re-quote).
4. ``review_queue`` recomputed from the records that carry ``review`` (the
   second refresh alone would list only its own rows), in refresh order.

Run from ``backend``::

    git show 21fcbf69:backend/app/knowledge/kb_cs_bachelor.json > /tmp/kb_v22.json
    PYTHONPATH=. python evaluation/research/expert/data/kb_drafts.2026-10-23/build_v24.py \\
        --kb /tmp/kb_v22.json \\
        --from-kb evaluation/research/expert/data/kb_refresh/evidence_check.kb-refresh-sandbox-2026-10-20.json \\
        --draft-check evaluation/research/expert/data/kb_drafts.2026-10-19/topup_documents4/evidence_check.ci-2026-10-25.json \\
        --batch evaluation/research/expert/data/kb_drafts.2026-10-23 \\
                evaluation/research/expert/data/kb_drafts.2026-10-26 \\
        --built-at 2026-10-25 --version 2026-10-25.kb-cs-bachelor.24 \\
        --out app/knowledge/kb_cs_bachelor.json
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from datetime import date
from pathlib import Path
from typing import Any

from app.knowledge import DOCUMENTS
from evaluation.research.expert import kb_build
from scripts import verify_evidence

HERE = Path(__file__).resolve().parent
DATA = HERE.parent
KINDS = DATA / "kb_drafts.2026-10-19" / kb_build.UNKNOWN_KINDS_FILE

_spec = importlib.util.spec_from_file_location("build_v23", HERE / "build_v23.py")
assert _spec and _spec.loader
build_v23 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build_v23)

Row = dict[str, Any]


def _label(path: Path) -> str:
    """``kb_drafts.<date>/<dir>/<file>`` (or shorter): how the KB names a report."""
    parts = path.resolve().relative_to(DATA.resolve()).parts
    return "/".join(parts)


def from_kb_rows(report: Path) -> tuple[list[Row], list[str]]:
    """A drafts-dir check as ``--from-kb`` rows (each row with its draft's quote)."""
    quotes: dict[tuple[str, str, str], str] = {}
    for draft in verify_evidence.load(report.parent):
        for item, _status, url, quote in verify_evidence.items(draft):
            if url and quote:
                quotes[(str(draft["case"]), item, url)] = quote
    rows: list[Row] = []
    skipped: list[str] = []
    for row in json.loads(report.read_text(encoding="utf-8")):
        if not row.get("url"):
            continue
        case, item, url = str(row["case"]), str(row["item"]), str(row["url"])
        quote = quotes.get((case, item, url))
        if not item.startswith(f"{DOCUMENTS}.") or quote is None:
            skipped.append(f"{case} {item}: not a document row with a draft quote; skipped")
            continue
        rows.append(
            {
                **row,
                "seed_id": str(row.get("seed_id") or case),
                "source": "fact",
                "key": item,
                "quote": quote,
            }
        )
    return rows, skipped


def review_queue(document: Row) -> list[Row]:
    """Every record that carries ``review``, as ``kb_build.refresh`` lists them."""
    out: list[Row] = []

    def add(record: Row, where: Row) -> None:
        review = record.get("review")
        if isinstance(review, dict) and review.get("needed"):
            out.append({**where, "class": review.get("class")})

    for seed, entry in (document.get("entries") or {}).items():
        for record in (entry.get("programme") or {}).get("evidence") or []:
            url = str(record.get("url") or "")
            add(
                record,
                {"seed_id": seed, "question": "programme", "key": url, "source": "programme"}
                | {"url": url},
            )
        for question, facts in (entry.get("facts") or {}).items():
            for fact in facts or []:
                item = str(fact.get("key")) if question == DOCUMENTS else str(question)
                where = {"seed_id": seed, "question": item, "key": str(fact.get("key"))}
                add(fact, where | {"source": "fact", "url": str(fact.get("source_url") or "")})
        for record in entry.get("not_applicable") or []:
            where = {
                "seed_id": seed,
                "question": str(record.get("question") or ""),
                "key": str(record.get("key")),
            }
            add(
                record,
                where | {"source": "not_applicable", "url": str(record.get("source_url") or "")},
            )
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--kb", type=Path, required=True)
    parser.add_argument("--from-kb", type=Path, required=True)
    parser.add_argument("--draft-check", type=Path, nargs="*", default=[])
    parser.add_argument("--batch", type=Path, nargs="+", required=True)
    parser.add_argument("--built-at", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    today = date.fromisoformat(args.built_at)
    document = kb_build.refresh(
        json.loads(args.kb.read_text(encoding="utf-8")),
        json.loads(args.from_kb.read_text(encoding="utf-8")),
        today=today,
        report=args.from_kb.name,
    )
    log: list[str] = []
    for report in args.draft_check:
        rows, skipped = from_kb_rows(report)
        document = kb_build.refresh(document, rows, today=today, report=_label(report))
        log += skipped
        log.append(f"{_label(report)}: {len(rows)} rows joined to KB records")
    batch_reports: list[str] = []
    for root in args.batch:
        batch = root / "batch1"
        reports = sorted(batch.glob("evidence_check.*.json"))
        label = f"{root.name}/batch1"
        built = kb_build.build(root, reports, built_at=args.built_at, unknown_kinds=KINDS)
        log += build_v23.splice(document, built, build_v23._drafts(batch), today=today, label=label)
        batch_reports.append(f"{label}/" + ",".join(p.name for p in reports))
    document["review_queue"] = review_queue(document)
    document = build_v23.finish(
        document, built_at=args.built_at, version=args.version, batch_report=batch_reports[0]
    )
    document["evidence_reports"] += batch_reports[1:]
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
