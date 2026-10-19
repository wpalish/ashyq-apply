"""Expert KB batches -> the product's verified knowledge base (``app/knowledge/kb_cs_bachelor.json``).

Owner decision (2026-10-19): live search frozen; the bachelor's in Computer
Science is answered from a verified knowledge base of the top-100 catalogue
universities (``evaluation/research/data/kb_top100_list.json``). Expert workers
write drafts in the dev5 formats::

    <drafts_root>/batch<N>/programme/<case>.<n>-<role>.json   (programme pages)
    <drafts_root>/batch<N>/core/<case>.json                   (the six core answers)

and CI checks every quote with the production fetcher
(``benchmark-capture.yml`` mode ``verify_evidence``, extra_args = a batch dir).
This converter turns every batch into ONE product file, reusing the dev5/dev4
rules unchanged (``core_drafts.items_for``, the programme roles of
``core_drafts_dev5``):

* a value is ``known`` only when a CI evidence report found its quote on an
  official page (``official`` and ``quote_found``); everything else is listed
  under ``unknown`` with the reason, or ``not_applicable`` with its evidence;
* each fact carries value, unit, period, academic_year, population, source
  URL, verbatim quote, accessed_on and verified_on (the date of the CI check);
* the entry shape is the development import's (``kb-imported-dev/1``,
  ``docs/process/KB_IMPORT_2026-10-19.md``), so one loader reads both.

A draft's university is its ``seed_id`` field, else a case equal to a seed_id,
an ``existing_case`` or the first label of an official domain. Rows marked
``excluded_heldout`` are never built. Run from ``backend``::

    python -m evaluation.research.expert.kb_build \\
        evaluation/research/expert/data/kb_drafts.2026-10-19 \\
        --evidence REPORT.json [REPORT.json ...] [--out app/knowledge/kb_cs_bachelor.json]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from app.knowledge import KB_FILE, QUESTIONS, stale_reasons

from ..identities import IdentityMap
from ..metrics import canonical_url
from .core_drafts import (
    _CYCLE_2026,
    DATA,
    Proposal,
    Report,
    _number,
    academic_year_matches,
    items_for,
    load_drafts,
    requested_year,
)
from .core_drafts import DRAFT_DATE as CORE_DRAFT_DATE

FORMAT = "kb-cs-bachelor/1"
LIST = DATA / "kb_top100_list.json"
PROGRAMME_ROLES = frozenset({"local", "twin", "site", "department"})
#: Cases whose files this tool must never read or build (heldout nine).
HELDOUT_CASES = frozenset("nu metu sabanci charles masaryk tum tartu polimi vilnius".split())
#: ``<case>.<n>-<role>.json``; a KB case is a seed_id with a hyphen (``qs2027-005``).
_PROGRAMME_FILE = re.compile(r"([a-z0-9-]+)\.(\d+)-([a-z]+)\.json")
_DATE = re.compile(r"(20\d\d-\d\d-\d\d)")

Row = dict[str, Any]


# ------------------------------------------------------------------ inputs


def load_list(path: Path = LIST) -> list[Row]:
    rows = json.loads(path.read_text(encoding="utf-8"))["rows"]
    return [r for r in rows if isinstance(r, dict) and r.get("seed_id")]


class Resolver:
    """Draft case -> list row (seed_id field, seed_id, existing case, domain label)."""

    def __init__(self, rows: list[Row]) -> None:
        self.by_seed = {str(r["seed_id"]): r for r in rows}
        self.by_case = {str(r["existing_case"]): r for r in rows if r.get("existing_case")}
        self.by_label: dict[str, Row] = {}
        for r in rows:
            for host in (r.get("official_domain"), _host(r.get("official_site"))):
                label = str(host or "").lower().removeprefix("www.").split(".")[0]
                if label:
                    self.by_label.setdefault(label, r)

    def __call__(self, case: str, draft: dict[str, Any] | None = None) -> Row | None:
        seed = str((draft or {}).get("seed_id") or "")
        return (
            self.by_seed.get(seed)
            or self.by_seed.get(case)
            or self.by_case.get(case)
            or self.by_label.get(case.lower())
        )


def _host(url: Any) -> str:
    match = re.match(r"https?://([^/:]+)", str(url or ""))
    return match.group(1).lower().removeprefix("www.") if match else ""


def load_reports(paths: list[Path]) -> list[Row]:
    """Every row of every CI report, each stamped with the date the check ran."""
    out: list[Row] = []
    for path in paths:
        if "container" in path.name:
            # The CI run is authoritative; a container pre-check is not evidence.
            print(
                f"skip {path.name}: a container check, not the CI evidence check", file=sys.stderr
            )
            continue
        stamp = _DATE.search(path.name)
        rows = json.loads(path.read_text(encoding="utf-8"))
        for row in rows if isinstance(rows, list) else []:
            if isinstance(row, dict):
                out.append({**row, "_report_date": stamp.group(1) if stamp else None})
    return out


def _passed(row: Row) -> bool:
    return row.get("official") is True and row.get("quote_found") is True


def _reason(row: Row | None) -> str:
    if row is None:
        return "no evidence-check row"
    if row.get("official") is not True:
        return "source host is not an official domain"
    note = f": {row['note']}" if row.get("note") else ""
    return f"quote not found on the page (fetch outcome {row.get('outcome') or '-'}{note})"


def _checked_on(row: Row, default: str) -> str:
    return str(row.get("checked_on") or row.get("_report_date") or default)


def _pick(rows: list[Row], url: str | None) -> Row | None:
    """The row for this URL (a passing one first); any passing row when no URL is known."""
    wanted = canonical_url(url) if url else None
    same = [r for r in rows if wanted is None or canonical_url(str(r.get("url") or "")) == wanted]
    return next((r for r in same if _passed(r)), same[0] if same else None)


class Evidence:
    """The CI reports, indexed by case and item."""

    def __init__(self, rows: list[Row]) -> None:
        self.rows: dict[tuple[str, str], list[Row]] = {}
        for row in rows:
            self.rows.setdefault((str(row.get("case")), str(row.get("item"))), []).append(row)

    def find(self, case: str, item: str, url: str | None) -> Row | None:
        return _pick(self.rows.get((case, item), []), url)

    def report_for(self, draft: dict[str, Any]) -> Report:
        """The ``core_drafts.Report`` of one draft: per item, the row for its URL."""
        case = str(draft["case"])
        out: Report = {}
        for item, answer in (draft.get("answers") or {}).items():
            url = answer.get("url") if isinstance(answer, dict) else None
            row = self.find(case, str(item), url)
            if row is not None:
                out[(case, str(item))] = row
        return out


def batch_dirs(root: Path) -> list[Path]:
    """``batch*`` directories under the root, or the root itself when it is one batch."""
    batches = sorted(p for p in root.glob("batch*") if p.is_dir())
    return batches or [root]


def load_programme_pages(directory: Path) -> dict[str, list[tuple[str, dict[str, Any]]]]:
    """Case -> [(role, draft)] in file order (``<case>.<n>-<role>.json``)."""
    out: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    if not directory.is_dir():
        return out
    files = []
    for path in directory.glob("*.json"):
        match = _PROGRAMME_FILE.fullmatch(path.name)
        if match:
            files.append((match[1], int(match[2]), match[3], path))
    for case, _n, role, path in sorted(files):
        draft = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(draft, dict):
            out.setdefault(str(draft.get("case") or case), []).append((role, draft))
    return out


# ------------------------------------------------------------------ facts


def _question(item: str, key: str) -> str:
    if item == "scholarship":
        return "scholarship_exists" if key.endswith(".exists") else "scholarship_international"
    return item


def _answer_name(question: str) -> str:
    return question


def _unit(key: str, value: Any, answer: dict[str, Any]) -> str | None:
    value_raw = answer.get("value")
    raw: dict[str, Any] = value_raw if isinstance(value_raw, dict) else {}
    if key.startswith("ielts."):
        return "IELTS band"
    if key == "english_evidence.toefl_ibt.minimum":
        return "TOEFL iBT total (0-120)"
    if key == "english_evidence.duolingo.minimum":
        return "Duolingo English Test total"
    if key == "gpa":
        return str(raw.get("unit") or raw.get("scale") or "") or None
    if key == "deadline":
        return "date"
    if key == "tuition" and isinstance(value, dict):
        return f"{value.get('currency')} per {raw.get('period') or 'year'}"
    return None


def fact_from(
    proposal: Proposal,
    question: str,
    answer: dict[str, Any],
    *,
    verified_on: str,
    today: date,
    intake: str,
    award: dict[str, Any] | None,
) -> Row:
    ev = proposal.evidence or {}
    value_raw = answer.get("value")
    raw: dict[str, Any] = value_raw if isinstance(value_raw, dict) else {}
    key = proposal.key
    fact: Row = {
        "key": key,
        "value": proposal.value,
        "unit": _unit(key, proposal.value, answer),
        "period": (
            str(raw.get("period") or "year")
            if key == "tuition"
            else intake
            if key == "deadline"
            else None
        ),
        "academic_year": raw.get("academic_year") or answer.get("academic_year"),
        "population": answer.get("population") or raw.get("population"),
        "source_url": ev.get("url"),
        "quote": ev.get("excerpt"),
        "quote_truncated": bool(ev.get("excerpt_truncated")),
        "source_type": "official",
        "accessed_on": ev.get("accessed_on"),
        "verified_on": verified_on,
        "notes": proposal.notes,
    }
    if award and question.startswith("scholarship"):
        fact["award"] = award
    reasons = stale_reasons(fact, today, intake)
    fact["stale"] = bool(reasons)
    if reasons:
        fact["stale_reasons"] = reasons
    return fact


def core_facts(
    draft: dict[str, Any],
    row: Row,
    evidence: Evidence,
    *,
    intake: str,
    today: date,
    default_verified: str,
) -> tuple[dict[str, list[Row]], list[Row], list[Row]]:
    """(facts per question, unknown, not_applicable) of one core draft."""
    request = {
        "university": row["name"],
        "programme": None,
        "degree": "bachelor",
        "field": "computer science",
        "intake": intake,
        "population": None,
        "qualification": None,
        "academic_year": None,
    }
    report = evidence.report_for(draft)
    domain = str(row.get("official_domain") or "")
    items, _binding, note = items_for(
        draft, request, domain, IdentityMap(version="kb", bindings=[]), report
    )
    answers = draft.get("answers") or {}
    researched = str(draft.get("researched_on") or default_verified)
    facts: dict[str, list[Row]] = {q: [] for q in QUESTIONS}
    unknown: list[Row] = []
    not_applicable: list[Row] = []
    exists = answers.get("scholarship_exists") or {}
    name = (
        (exists.get("value") or {}).get("name") if isinstance(exists.get("value"), dict) else None
    )
    award = {"subject": name, "source_url": exists.get("url")} if name else None
    for item in items:
        for p in item.proposals:
            question = _question(item.question, p.key)
            answer = answers.get(_answer_name(question)) or {}
            p.notes = p.notes.replace(CORE_DRAFT_DATE, researched)
            used = report.get((str(draft["case"]), _answer_name(question)))
            verified_on = _checked_on(used, default_verified) if used else default_verified
            if p.status == "known":
                facts[question].append(
                    fact_from(
                        p,
                        question,
                        answer,
                        verified_on=verified_on,
                        today=today,
                        intake=intake,
                        award=award,
                    )
                )
            elif p.status == "not_applicable":
                ev = p.evidence or {}
                not_applicable.append(
                    {
                        "question": question,
                        "key": p.key,
                        "reason": p.notes,
                        "source_url": ev.get("url"),
                        "quote": ev.get("excerpt"),
                        "verified_on": verified_on,
                    }
                )
            else:
                unknown.append({"question": question, "key": p.key, "reason": p.notes})
    for question in ("tuition", "deadline"):
        if facts[question]:
            continue
        stale_fact = year_ruled_fact(
            question,
            answers.get(question) or {},
            report.get((str(draft["case"]), question)),
            request,
            researched=researched,
            today=today,
            default_verified=default_verified,
        )
        if stale_fact is not None:
            facts[question].append(stale_fact)
            unknown = [u for u in unknown if u["key"] != question]
    if note:
        unknown.append({"question": "scholarship_exists", "key": "scholarships", "reason": note})
    return facts, unknown, not_applicable


def year_ruled_fact(
    question: str,
    answer: dict[str, Any],
    row: Row | None,
    request: dict[str, Any],
    *,
    researched: str,
    today: date,
    default_verified: str,
) -> Row | None:
    """A verified tuition or deadline the year rules kept from ``known``, as a STALE fact.

    ``core_drafts`` writes a fee for another academic year (or none stated) and
    a past-cycle deadline ``unknown``. For the KB that would drop a verified,
    published value silently; it is kept instead, with its year and period as
    published, and shown as stale with the reason. A per-semester or
    whole-programme fee whose year matches is kept current, its period as
    published. A deadline whose quote prints no year stays unknown: its year
    would be ours, not the page's.
    """
    if row is None or not _passed(row) or answer.get("status") != "known":
        return None
    url, quote = str(answer.get("url") or ""), str(answer.get("quote") or "").strip()
    if not url or not quote:
        return None
    intake = str(request.get("intake") or "")
    raw = answer.get("value")
    reasons: list[str] = []
    if question == "tuition":
        if not isinstance(raw, dict):
            return None
        amount, currency = _number(raw.get("amount")), str(raw.get("currency") or "").upper()
        if amount is None or not re.fullmatch(r"[A-Z]{3}", currency):
            return None
        value: Any = {"amount": amount, "currency": currency}
        year = raw.get("academic_year")
        start = requested_year(request)
        # A calendar-year system (Australia, NZ, Korea) publishes "2027" for the
        # academic year a 2027 intake joins; that is the intake's own year.
        calendar_year = re.fullmatch(r"\s*(20\d\d)\s*", str(year or ""))
        same_calendar_year = bool(calendar_year and start and int(calendar_year[1]) == start)
        if start is None or not (academic_year_matches(year, start) or same_calendar_year):
            reasons.append(
                f"published for academic year {year}, not the {intake} intake's"
                if year
                else "the academic year is not stated"
            )
        period = str(raw.get("period") or "year")
        unit = f"{currency} per {period}"
    else:
        value = str(raw or "").strip()
        try:
            day = date.fromisoformat(value)
        except ValueError:
            return None
        if str(day.year) not in quote:
            return None
        if _CYCLE_2026.search(str(answer.get("notes") or "")):
            reasons.append("published for the 2026 cycle")
        year, period, unit = answer.get("academic_year"), intake, "date"
    fact: Row = {
        "key": question,
        "value": value,
        "unit": unit,
        "period": period,
        "academic_year": year,
        "population": answer.get("population") or (raw or {}).get("population")
        if isinstance(raw, dict)
        else answer.get("population"),
        "source_url": url,
        "quote": re.sub(r"\s+", " ", quote),
        "quote_truncated": False,
        "source_type": "official",
        "accessed_on": researched,
        "verified_on": _checked_on(row, default_verified),
        "notes": str(answer.get("notes") or ""),
    }
    computed = stale_reasons(fact, today, intake)
    if any(r.startswith("academic year") for r in computed):
        reasons = [r for r in reasons if not r.startswith("published for academic year")]
    reasons = list(dict.fromkeys([*computed, *reasons]))
    fact["stale"] = bool(reasons)
    if reasons:
        fact["stale_reasons"] = reasons
    return fact


def programme_block(
    case: str,
    pages: list[tuple[str, dict[str, Any]]],
    evidence: Evidence,
    *,
    default_verified: str,
) -> Row:
    """Programme status, URLs and verified quotes, by the dev5 page roles."""
    urls: list[str] = []
    quotes: list[Row] = []
    language: list[Row] = []
    related: list[str] = []
    remarks: list[str] = []
    for role, draft in pages:
        related += [str(u) for u in draft.get("related_programme_urls") or []]
        programme = draft.get("programme") or {}
        url, quote = str(programme.get("url") or ""), str(programme.get("title") or "")
        if not url or not quote:
            continue
        if role == "related":
            related.append(url)
            continue
        row = evidence.find(case, "programme", url)
        ok = row is not None and _passed(row)
        if not ok:
            remarks.append(f"{url} not verified: {_reason(row)}.")
            continue
        assert row is not None
        record = {
            "url": url,
            "quote": quote,
            "quote_truncated": False,
            "accessed_on": draft.get("accessed_on") or draft.get("researched_on"),
            "verified_on": _checked_on(row, default_verified),
            "source_type": "official",
        }
        if role == "language":
            language.append(record)
        elif role in PROGRAMME_ROLES:
            quotes.append(record)
            if url not in urls:
                urls.append(url)
    block: Row = {
        "status": "known" if quotes else "unknown",
        "urls": urls,
        "evidence": quotes,
        "related_programme_urls": list(dict.fromkeys(u for u in related if u not in urls)),
    }
    if language:
        block["teaching_language_evidence"] = language
    if not quotes:
        block["reason"] = " ".join(remarks) or "no programme page draft"
    elif remarks:
        block["notes"] = " ".join(remarks)
    return block


# ------------------------------------------------------------------- build


def build(
    root: Path,
    reports: list[Path],
    *,
    list_path: Path = LIST,
    built_at: str | None = None,
    intake: str = "fall 2027",
    version: str | None = None,
) -> Row:
    built_at = built_at or datetime.now(UTC).date().isoformat()
    today = date.fromisoformat(built_at)
    rows = load_list(list_path)
    resolve = Resolver(rows)
    evidence = Evidence(load_reports(reports))
    list_doc = json.loads(list_path.read_text(encoding="utf-8"))

    pages: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    cores: dict[str, tuple[dict[str, Any], str]] = {}
    for batch in batch_dirs(root):
        for case, found in load_programme_pages(batch / "programme").items():
            pages.setdefault(case, []).extend(found)
        core_dir = batch / "core"
        if core_dir.is_dir():
            for draft in load_drafts(core_dir):
                cores[str(draft["case"])] = (draft, batch.name)

    entries: dict[str, Row] = {}
    unresolved: list[Row] = []
    for case in sorted(set(pages) | set(cores)):
        draft, batch_name = cores.get(case, ({}, ""))
        first = draft or (pages.get(case) or [("", {})])[0][1]
        row = resolve(case, first)
        if case in HELDOUT_CASES or row is None or row.get("status") == "excluded_heldout":
            unresolved.append(
                {
                    "case": case,
                    "reason": "heldout case, never built"
                    if case in HELDOUT_CASES or (row or {}).get("status") == "excluded_heldout"
                    else "no kb_top100_list row for this case",
                }
            )
            continue
        default_verified = built_at
        facts: dict[str, list[Row]] = {q: [] for q in QUESTIONS}
        unknown: list[Row] = []
        not_applicable: list[Row] = []
        if draft:
            facts, unknown, not_applicable = core_facts(
                draft,
                row,
                evidence,
                intake=intake,
                today=today,
                default_verified=default_verified,
            )
        else:
            unknown = [{"question": q, "key": q, "reason": "no core draft"} for q in QUESTIONS]
        programme = programme_block(
            case, pages.get(case, []), evidence, default_verified=default_verified
        )
        dates = [f["verified_on"] for fs in facts.values() for f in fs] + [
            e["verified_on"] for e in programme["evidence"]
        ]
        domains = [
            str(row.get("official_domain") or ""),
            _host(row.get("official_site")),
            *[str(d).lower().removeprefix("www.") for d in row.get("extra_domains") or []],
        ]
        entries[str(row["seed_id"])] = {
            "seed_id": row["seed_id"],
            "source_case": case,
            "source_batch": batch_name,
            "review_status": "expert_checked",
            "verified_on": max(dates) if dates else None,
            "verified_on_basis": "ci_evidence_check",
            "university": row["name"],
            "country": row.get("country"),
            "official_domain": row.get("official_domain"),
            "official_domains": list(dict.fromkeys(d for d in domains if d)),
            "programme": programme,
            "facts": facts,
            "unknown": unknown,
            "not_applicable": not_applicable,
            "known_fact_count": sum(len(fs) for fs in facts.values()),
        }
    stale = [
        {"seed_id": s, "question": q, "key": f["key"], "reasons": f["stale_reasons"]}
        for s, e in entries.items()
        for q, fs in e["facts"].items()
        for f in fs
        if f.get("stale")
    ]
    return {
        "format": FORMAT,
        "version": version or f"{built_at}.kb-cs-bachelor",
        "built_at": built_at,
        "programme": "bachelor computer science",
        "applicant": "international",
        "intake": intake,
        "list_version": list_doc.get("version"),
        "questions": list(QUESTIONS),
        "stale_policy": {
            "as_of": built_at,
            "accessed_older_than_days": 365,
            "academic_year_past": "end year <= as_of year",
            "deadline_passed": "deadline value before as_of",
        },
        "evidence_reports": [p.name for p in reports],
        "entries": dict(sorted(entries.items())),
        "stale_facts": stale,
        "unresolved_drafts": unresolved,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("drafts_root", type=Path)
    parser.add_argument("--evidence", type=Path, nargs="+", default=[])
    parser.add_argument("--out", type=Path, default=KB_FILE)
    parser.add_argument("--list", type=Path, default=LIST)
    parser.add_argument("--built-at", help="YYYY-MM-DD (default: today, UTC)")
    parser.add_argument("--intake", default="fall 2027")
    parser.add_argument("--version")
    args = parser.parse_args(argv)
    if not args.evidence:
        print("no --evidence report: every value stays unknown", file=sys.stderr)
    data = build(
        args.drafts_root,
        args.evidence,
        list_path=args.list,
        built_at=args.built_at,
        intake=args.intake,
        version=args.version,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    known = sum(e["known_fact_count"] for e in data["entries"].values())
    print(
        f"entries={len(data['entries'])} known_facts={known} stale={len(data['stale_facts'])} "
        f"unresolved={len(data['unresolved_drafts'])} -> {args.out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
