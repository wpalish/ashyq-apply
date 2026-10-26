"""Build ``app/knowledge/kb_imported_dev.json`` from the development corpora.

Reads the top-100 KB list and, for every row with ``status == "import_existing"``,
copies the programme page and the six core answers for an international
applicant out of the development corpus case named in ``existing_case``.

Only labels with ``status == "known"`` whose first evidence item has a URL and a
non-empty excerpt become facts. Nothing is inferred, merged or re-worded: the
value is the label's value and the quote is the evidence excerpt verbatim.

Heldout corpora are never opened: the corpus files are listed explicitly below.

Usage (from ``backend/``)::

    python -m evaluation.research.build_kb_imported_dev
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any

BACKEND = Path(__file__).resolve().parents[2]
DATA = BACKEND / "evaluation" / "research" / "data"
OUT = BACKEND / "app" / "knowledge" / "kb_imported_dev.json"

LIST_FILE = "kb_top100_list.json"
CORPORA = (
    "ground_truth.reviewed11.json",
    "dev2.draft3.json",
    "dev3.draft3.json",
    "dev5.draft1.json",
)
BINDINGS = (
    "identity_bindings.reviewed.json",
    "identity_bindings.dev2-draft1.json",
    "identity_bindings.dev3-draft1.json",
    "identity_bindings.dev5-draft1.json",
)
HELDOUT_CASE_IDS = frozenset(
    {"nu", "metu", "sabanci", "charles", "masaryk", "tum", "tartu", "polimi", "vilnius"}
)

AS_OF = date(2026, 10, 19)
STALE_AFTER_DAYS = 365
FORMAT = "kb-imported-dev/1"

QUESTIONS = (
    "english",
    "gpa",
    "deadline",
    "tuition",
    "scholarship_exists",
    "scholarship_international",
)


def question_for(key: str) -> str | None:
    """Map a corpus label key to one of the six core questions (or None)."""
    if key in ("ielts.overall", "ielts.subscores") or key.startswith("english_evidence."):
        return "english"
    if key == "gpa":
        return "gpa"
    if key == "deadline":
        # deadline.eu_national is an EU-national answer, not an international one.
        return "deadline"
    if key == "tuition":
        return "tuition"
    if key == "scholarships" or re.fullmatch(r"scholarships\.[a-z0-9_]+\.exists", key):
        return "scholarship_exists"
    if re.fullmatch(r"scholarships\.[a-z0-9_]+\.applicability\.international", key):
        return "scholarship_international"
    return None


def _academic_year_past(academic_year: str | None) -> bool:
    """'2025-2026' or '2025/26' is past once its end year is before the current intake year."""
    if not academic_year:
        return False
    years = re.findall(r"\d{2,4}", academic_year)
    if not years:
        return False
    end = years[-1]
    end_year = int(end) if len(end) == 4 else 2000 + int(end)
    # The 2026-2027 year is current on AS_OF; a year is past after 31 August of
    # its end year (``app.knowledge.ACADEMIC_YEAR_LAST_DAY``).
    return date(end_year, 8, 31) < AS_OF


def stale_reasons(
    accessed_on: str | None, academic_year: str | None, key: str, value: Any
) -> list[str]:
    reasons: list[str] = []
    if accessed_on and (AS_OF - date.fromisoformat(accessed_on)).days > STALE_AFTER_DAYS:
        reasons.append("accessed_over_12_months_ago")
    if _academic_year_past(academic_year):
        reasons.append("academic_year_past")
    if (
        key == "deadline"
        and isinstance(value, str)
        and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value)
        and date.fromisoformat(value) < AS_OF
    ):
        reasons.append("deadline_passed")
    return reasons


MODEL_ID = re.compile(r"(?i)\b(?:gpt|claude|codex|opus|sonnet|haiku|fable)-[\w.]+(?:-[\w.]+)*")


def _scrub(text: str | None) -> str | None:
    """Corpus notes are free text; agent model identifiers are not KB content."""
    return MODEL_ID.sub("[agent]", text) if text else text


def _load(name: str) -> Any:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def _award_bindings() -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for name in BINDINGS:
        for b in _load(name)["bindings"]:
            if b.get("kind") == "award":
                out.setdefault(b["key"], {"subject": b["subject"], "source_url": b["source_url"]})
    return out


def _evidence_entry(ev: dict[str, Any]) -> dict[str, Any]:
    return {
        "url": ev["url"],
        "quote": ev["excerpt"],
        "quote_truncated": bool(ev.get("excerpt_truncated", False)),
        "accessed_on": ev.get("accessed_on"),
        "source_type": ev.get("source_type"),
    }


def build() -> dict[str, Any]:
    kb_list = _load(LIST_FILE)
    rows = [r for r in kb_list["rows"] if r["status"] == "import_existing"]
    cases: dict[str, tuple[str, str, dict[str, Any]]] = {}
    for name in CORPORA:
        corpus = _load(name)
        for case in corpus["cases"]:
            cases.setdefault(case["id"], (name, corpus["version"], case))
    awards = _award_bindings()

    entries: dict[str, Any] = {}
    stale: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    for row in rows:
        case_id = row["existing_case"]
        if case_id in HELDOUT_CASE_IDS:
            raise SystemExit(f"refusing heldout case {case_id}")
        corpus_name, corpus_version, case = cases[case_id]
        review = case.get("review") or {}
        if review.get("verified_on"):
            verified_on, verified_basis = review["verified_on"], "review.verified_on"
        else:
            verified_on, verified_basis = corpus_version[:10], "corpus_version_date"

        facts: dict[str, list[dict[str, Any]]] = {q: [] for q in QUESTIONS}
        for label in case["labels"]:
            q = question_for(label["key"])
            if q is None or label["status"] != "known":
                continue
            evs = [
                e for e in label["evidence"] if e.get("url") and (e.get("excerpt") or "").strip()
            ]
            if not evs:
                skipped.append(
                    {
                        "seed_id": row["seed_id"],
                        "key": label["key"],
                        "reason": "known_without_url_and_quote",
                    }
                )
                continue
            primary = evs[0]
            scope = primary.get("scope") or {}
            fact: dict[str, Any] = {
                "key": label["key"],
                "value": label["value"],
                "period": scope.get("intake"),
                "academic_year": scope.get("academic_year"),
                "population": scope.get("population"),
                "source_url": primary["url"],
                "quote": primary["excerpt"],
                "quote_truncated": bool(primary.get("excerpt_truncated", False)),
                "source_type": primary.get("source_type"),
                "accessed_on": primary.get("accessed_on"),
                "verified_on": verified_on,
                "notes": _scrub(label.get("notes")),
            }
            if len(evs) > 1:
                fact["more_sources"] = [_evidence_entry(e) for e in evs[1:]]
            m = re.match(r"(scholarships\.[a-z0-9_]+)\.", label["key"])
            if m and m.group(1) in awards:
                fact["award"] = awards[m.group(1)]
            reasons = stale_reasons(
                fact["accessed_on"], fact["academic_year"], label["key"], label["value"]
            )
            fact["stale"] = bool(reasons)
            if reasons:
                fact["stale_reasons"] = reasons
                stale.append(
                    {
                        "seed_id": row["seed_id"],
                        "question": q,
                        "key": label["key"],
                        "reasons": reasons,
                    }
                )
            facts[q].append(fact)

        entries[row["seed_id"]] = {
            "seed_id": row["seed_id"],
            "source_case": case_id,
            "source_corpus": corpus_name,
            "corpus_version": corpus_version,
            "review_status": review.get("status"),
            "verified_on": verified_on,
            "verified_on_basis": verified_basis,
            "university": row["name"],
            "country": row["country"],
            "official_domain": row["official_domain"] or case.get("domain"),
            "programme": {
                "status": case["programme_status"],
                "urls": case["programme_urls"],
                "evidence": [_evidence_entry(e) for e in case["programme_evidence"]],
                "related_programme_urls": case.get("related_programme_urls", []),
            },
            "facts": facts,
            "known_fact_count": sum(len(v) for v in facts.values()),
        }

    return {
        "format": FORMAT,
        "generated_on": AS_OF.isoformat(),
        "programme": kb_list["programme"],
        "applicant": "international",
        "list_version": kb_list["version"],
        "questions": list(QUESTIONS),
        "stale_policy": {
            "as_of": AS_OF.isoformat(),
            "accessed_older_than_days": STALE_AFTER_DAYS,
            "academic_year_past": "as_of after 31 August of the end year",
            "deadline_passed": "deadline value before as_of",
        },
        "entries": entries,
        "stale_facts": stale,
        "skipped_known_labels": skipped,
    }


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(build(), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
