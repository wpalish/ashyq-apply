"""dev4 core-question drafts -> ``dev4.draft2.json`` and its signing table (wayfinder ticket 09).

The rules are ``core_drafts.items_for``'s, unchanged: an expert ``known`` or
``not_applicable`` answer becomes a label only when the
``scripts/verify_evidence.py`` report has that case and item with ``official``
and ``quote_found``; anything else is written ``unknown`` with the expert value
in the note. Programme rows of ``dev4.draft1.json`` are copied unchanged; the
core labels are appended after ``programme.exists``.

Run from ``backend``::

    python -m evaluation.research.expert.core_drafts_dev4 \\
        evaluation/research/expert/data/core_drafts_dev4.2026-10-18 [--evidence REPORT.json]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from ..identities import IdentityMap
from ..metrics import canonical_url
from ..schema import Dataset
from .core_drafts import (
    DATA,
    QUESTION_RU,
    _short,
    items_for,
    load_drafts,
    load_report,
    row_value,
)

DRAFT_DATE = "2026-10-18"
VERSION = f"{DRAFT_DATE}.dev4-draft2"
BASE = DATA / "dev4.draft1.json"
BASE_BINDINGS = DATA / "identity_bindings.dev4-draft1.json"
OUT = DATA / "dev4.draft2.json"
OUT_BINDINGS = DATA / "identity_bindings.dev4-draft2.json"


def build(
    base: dict[str, Any], identities: IdentityMap, drafts: list[dict[str, Any]], report: Any
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    """(dataset, bindings, worksheet rows)."""
    by_case = {str(d["case"]): d for d in drafts}
    cases, bindings, rows = [], [], []
    known = {(b.kind, canonical_url(b.source_url), b.subject) for b in identities.bindings}
    for case in base["cases"]:
        case = json.loads(json.dumps(case))
        case["dataset_version"] = VERSION
        draft = by_case.get(case["id"])
        if draft is not None:
            items, binding, note = items_for(
                draft, case["request"], case["domain"], identities, report
            )
            programme_labels = [lb for lb in case["labels"] if lb["key"] == "programme.exists"]
            core = [
                {
                    "key": p.key,
                    "status": p.status,
                    "value": p.value,
                    "evidence": [p.evidence] if p.evidence and p.status != "unknown" else [],
                    "critical": True,
                    "notes": p.notes or f"Expert draft {DRAFT_DATE}.",
                }
                for item in items
                for p in item.proposals
            ]
            case["labels"] = programme_labels + core
            notes = [
                f"dev4 draft2 ({DRAFT_DATE}, wayfinder finish-algorithm ticket 09): core-question "
                f"labels from one expert draft, listed in docs/process/SIGN_DEV4_CORE_{DRAFT_DATE}.md; "
                "unsigned.",
                case["review"]["notes"],
            ]
            if note:
                notes.append(note)
            case["review"]["notes"] = " ".join(notes)
            if binding:
                identity = ("award", canonical_url(binding["source_url"]), binding["subject"])
                if identity not in known:
                    known.add(identity)
                    bindings.append(binding)
            answers = draft.get("answers") or {}
            for item in items:
                answer = answers.get(
                    item.question if item.question != "scholarship" else "scholarship_exists"
                ) or {}
                rows.append(
                    {
                        "case": case["id"],
                        "question": QUESTION_RU[item.question],
                        "value": row_value(item.proposals),
                        "offered": item.offered,
                        "verified": item.verified,
                        "url": item.url,
                        "quote": item.quote,
                        "lang": answer.get("page_language") or "",
                        "why": "" if item.offered else _short(answer.get("notes"), 140),
                    }
                )
            if not any(i.question == "scholarship" for i in items):
                ex = answers.get("scholarship_exists") or {}
                rows.append(
                    {
                        "case": case["id"],
                        "question": QUESTION_RU["scholarship"],
                        "value": "н/п (нет стипендий)" if ex.get("status") == "not_applicable"
                        else "неизвестно",
                        "offered": ex.get("status") == "not_applicable",
                        "verified": False,
                        "url": ex.get("url"),
                        "quote": ex.get("quote") or "",
                        "lang": ex.get("page_language") or "",
                        "why": _short(ex.get("notes"), 140),
                    }
                )
        cases.append(case)
    data = {**{k: v for k, v in base.items() if k != "cases"}, "version": VERSION, "cases": cases}
    Dataset.model_validate(data)
    out_bindings = {
        "version": VERSION,
        "bindings": [b.model_dump(mode="json") for b in identities.bindings] + bindings,
    }
    IdentityMap.model_validate(out_bindings)
    return data, out_bindings, rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("drafts", type=Path)
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--rows", type=Path, help="write the worksheet rows as JSON here")
    args = parser.parse_args(argv)
    base = json.loads(BASE.read_text(encoding="utf-8"))
    identities = IdentityMap.model_validate_json(BASE_BINDINGS.read_text(encoding="utf-8"))
    data, bindings, rows = build(
        base, identities, load_drafts(args.drafts), load_report(args.evidence)
    )
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    OUT_BINDINGS.write_text(
        json.dumps(bindings, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    if args.rows:
        args.rows.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    statuses: dict[str, int] = {}
    for case in data["cases"]:
        for label in case["labels"]:
            statuses[label["status"]] = statuses.get(label["status"], 0) + 1
    print(f"cases={len(data['cases'])} labels={statuses} bindings={len(bindings['bindings'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
