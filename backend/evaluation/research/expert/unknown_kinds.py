"""Why a KB value is unknown: the reviewed ``unknown_kinds.json`` table (WHY-1).

Every ``unknown`` record a KB build writes carries a ``kind`` from
``app.knowledge.UNKNOWN_KINDS`` so the product can say *why* a cell is empty:

* ``not_published`` - the university publishes no such value (no GPA minimum,
  holistic review, no English minimum for the route, no award found);
* ``access`` - the official page refuses our servers (HTTP 403, a bot
  challenge, TLS, robots.txt, an encrypted or client-rendered page);
* ``unverified_quote`` - the expert's quote was not found on the page by the
  evidence check;
* ``undated`` - a deadline printed without a year;
* ``other_year`` - only another cycle's or year's value is published;
* ``not_researched`` - the expert did not establish it (a generic draft note);
* ``unspecified`` - no row in the table.

The kind is never inferred at build time: the build reads the reviewed table
(``kb_build.load_unknown_kinds``) and a record without a row is
``unspecified``. This module only *seeds* the table from the reason texts with
a deterministic keyword table (``classify``); a person reads the seeded rows
once and corrects them before it is committed. Run from ``backend``::

    python -m evaluation.research.expert.unknown_kinds \\
        app/knowledge/kb_cs_bachelor.json evaluation/research/expert/data/kb_drafts.2026-10-19 \\
        --out evaluation/research/expert/data/kb_drafts.2026-10-19/unknown_kinds.json

A row already in ``--out`` is kept as reviewed (a re-seed adds rows, never
rewrites one).
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from app.knowledge import UNKNOWN_KINDS

from .core_drafts import load_drafts

Row = dict[str, Any]

#: The generic reason the build writes for a scholarship the expert did not
#: establish; the draft's own note says why, so the seed reads that instead.
NO_SCHOLARSHIP = "Expert did not establish a scholarship"

#: (kind, pattern) in priority order: the first match wins. Case-insensitive.
KEYWORDS: tuple[tuple[str, str], ...] = (
    ("unverified_quote", r"not in the quoted excerpt|quote not found|unverified:"),
    ("undated", r"carries no year|written without a year"),
    (
        "access",
        r"\baccess\b|access failure|http 40[0-9]|cloudflare|bot challenge|incapsula|waf\b"
        r"|tls|could not be read|not readable|blocked|empty body|encrypted|robots\.txt unreachable"
        r"|not read:|answers? (?:every request with|http)",
    ),
    (
        "other_year",
        r"only the .* fee is published, not|cycle_stated|not the fall 20\d\d intake"
        r"|previous cycle|no 20\d\d date|spring \(march 20\d\d\) entry",
    ),
    (
        "not_published",
        r"no (?:minimum|grade|gpa|score|threshold|single grade|published|first-year|exact)"
        r"|holistic|prose only|prose/indicative|not a gpa|no gpa|no tuition amount"
        r"|no .*scholarship .* found|not determinable|only a generic statement|not printed on"
        r"|is set by those national procedures|department prose only",
    ),
    ("not_researched", r"expert did not establish it|not researched|not filled|expert draft"),
)


def classify(reason: str) -> str:
    """The seeded kind of one reason text (``not_researched`` when nothing matches)."""
    for kind, pattern in KEYWORDS:
        if re.search(pattern, reason, re.IGNORECASE):
            return kind
    return "not_researched"


def _expert_part(reason: str) -> str:
    """The expert's own note: what follows the build's "Expert did not establish it."."""
    head = "Expert did not establish it."
    return reason.split(head, 1)[1] if reason.startswith(head) else reason


def scholarship_notes(drafts_root: Path) -> dict[str, str]:
    """seed_id -> the latest draft note on an unknown ``scholarship_exists`` answer."""
    out: dict[str, str] = {}
    for batch in sorted(p for p in drafts_root.glob("*") if p.is_dir()):
        core = batch / "core"
        if not core.is_dir():
            continue
        for draft in load_drafts(core):
            answer = (draft.get("answers") or {}).get("scholarship_exists") or {}
            note = answer.get("notes") or answer.get("note")
            if answer.get("status") == "unknown" and note:
                out[str(draft.get("seed_id") or draft["case"])] = str(note)
    return out


def seed(kb: Row, drafts_root: Path | None = None) -> list[Row]:
    """One row per (seed_id, question, key) unknown record of a built KB, kind seeded."""
    notes = scholarship_notes(drafts_root) if drafts_root else {}
    rows: list[Row] = []
    for seed_id, entry in sorted((kb.get("entries") or {}).items()):
        for record in entry.get("unknown") or []:
            reason = str(record.get("reason") or "")
            if reason.startswith(NO_SCHOLARSHIP):
                text = notes.get(seed_id, "")
                kind = classify(text) if text else "not_researched"
            else:
                text = _expert_part(reason)
                kind = classify(text)
            rows.append(
                {
                    "seed_id": seed_id,
                    "question": record.get("question"),
                    "key": record.get("key"),
                    "kind": kind,
                    "basis": re.sub(r"\s+", " ", text).strip()[:160],
                }
            )
    return rows


def merge(reviewed: list[Row], seeded: list[Row]) -> list[Row]:
    """The reviewed rows unchanged, plus seeded rows for records not yet in it."""
    have = {(r["seed_id"], r["question"], r.get("key")) for r in reviewed}
    return [*reviewed, *(r for r in seeded if (r["seed_id"], r["question"], r["key"]) not in have)]


def validate(rows: list[Row]) -> list[str]:
    """Problems that make a table unusable (an unknown kind, a missing field)."""
    problems = []
    for i, row in enumerate(rows):
        if not row.get("seed_id") or not row.get("question"):
            problems.append(f"row {i}: needs seed_id and question")
        if row.get("kind") not in UNKNOWN_KINDS:
            problems.append(f"row {i}: kind {row.get('kind')!r} is not in UNKNOWN_KINDS")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("kb", type=Path)
    parser.add_argument("drafts_root", type=Path, nargs="?")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    kb = json.loads(args.kb.read_text(encoding="utf-8"))
    old = json.loads(args.out.read_text(encoding="utf-8")) if args.out.exists() else {}
    rows = merge(list(old.get("rows") or []), seed(kb, args.drafts_root))
    problems = validate(rows)
    if problems:
        raise SystemExit("\n".join(problems))
    document = {**old, "kinds": list(UNKNOWN_KINDS), "rows": rows}
    args.out.write_text(json.dumps(document, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(rows)} rows -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
