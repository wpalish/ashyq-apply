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

* a value is ``known`` only when an evidence report found its quote on an
  official page (``official`` and ``quote_found``): the CI report, or a
  recheck report of the rows CI could not read (``scripts/verify_evidence.py
  --recheck``, ``evidence_check.recheck-<date>.json``, rows with ``origin``
  ``sandbox-proxy``). For one (case, item, URL) a passing row wins, CI's first.
  Everything else is listed under ``unknown`` with the reason, or
  ``not_applicable`` with its evidence;
* each fact carries value, unit, period, academic_year, population, source
  URL, verbatim quote, accessed_on, verified_on (the date of the check) and
  verified_by (``ci`` or ``recheck``);
* **robots override** (owner, 2026-10-19, expires at product launch;
  AGENTS.md §6): ``scripts/verify_evidence.py --robots-override-kb`` reports
  (``evidence_check.robots-override-<date>.json``, rows with
  ``"robots_override": true``) are evidence too, ranked after CI and recheck.
  A row whose read actually needed the override (``robots_override_used``)
  verifies as ``verified_by: "robots_override"`` and marks its record
  ``robots_override: true``; one robots.txt allowed after all counts as a
  recheck. Every such record is listed at the top level under
  ``robots_override_facts``; ``--exclude-robots-override`` builds without
  those rows (the launch-day step);
* **top-up dirs** (``topup*``, read after ``batch*``) may hold only some
  answers of a university: its drafts are merged answer by answer, per
  question and per English test, a later answer winning only when it is
  ``known`` or ``not_applicable``; each draft is verified against its own
  dir's reports (``merge_core_results``);
* **two pending owner decisions, both off by default**:
  ``--yearless-deadlines-with-caveat`` keeps a verified deadline whose quote
  prints day and month but no year, the year inferred from the intake's
  application cycle (``application_cycle_year``), with ``year_inferred`` and a
  ``caveat``; ``--standing-fee-policy-current`` shows a listed standing fee
  policy (``STANDING_FEE_POLICIES``) that states no academic year as current,
  with a ``caveat``. Only a build with a flag on writes ``owner_flags`` and
  ``caveat_facts``;
* **application documents**: a draft's ``documents`` answer lists one item
  per document the official page names (``app.knowledge.documents``); each
  item is checked as its own evidence row (``documents.<kind>``) and becomes
  one fact when verified (``document_facts``). A documents-only draft is
  merged in and never becomes the base;
* the entry shape is the development import's (``kb-imported-dev/1``,
  ``docs/process/KB_IMPORT_2026-10-19.md``), so one loader reads both.

A draft's university is its ``seed_id`` field, else a case equal to a seed_id,
an ``existing_case`` or the first label of an official domain. Rows marked
``excluded_heldout`` are never built. Run from ``backend``::

    python -m evaluation.research.expert.kb_build \\
        evaluation/research/expert/data/kb_drafts.2026-10-19 \\
        --evidence REPORT.json [REPORT.json ...] [--out app/knowledge/kb_cs_bachelor.json]

**Refresh** (free-search ticket 07): ``--refresh KB.json --evidence REPORT.json
--out OUT.json`` takes a ``scripts/verify_evidence.py --from-kb`` report and
re-stamps an already built KB without its drafts. A record whose row still
verifies gets the row's ``checked_on`` as ``verified_on`` (``verified_by``:
``ci``, or ``recheck`` for a sandbox-proxy row); one whose row does not keeps
its value and its old date, gets ``review`` (``needed``, the class from
``kb_refresh_diff.classify``, the outcome) and is listed under
``review_queue``. Staleness is recomputed for ``--built-at``. No value is
dropped or changed; a record the report did not check is left as it was.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from app.knowledge import (
    DOCUMENTS,
    KB_FILE,
    QUESTIONS,
    STANDING_FEE_POLICY_CAVEAT,
    YEAR_INFERRED_CAVEAT,
    stale_reasons,
)
from app.knowledge.documents import DOCUMENT_KINDS, REQUIREMENTS

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
from .kb_refresh_diff import VERIFIED, classify, current_stale_reasons

FORMAT = "kb-cs-bachelor/1"
#: ``origin`` of a recheck report's rows (``scripts/verify_evidence.py --recheck``).
RECHECK_ORIGIN = "sandbox-proxy"
#: ``verified_by`` of a record verified only by the owner's KB robots override.
ROBOTS_OVERRIDE = "robots_override"
#: Which check's passing row wins for one (case, item, URL): CI, recheck, override.
_CHECK_RANK = {"ci": 0, "recheck": 1, ROBOTS_OVERRIDE: 2}
LIST = DATA / "kb_top100_list.json"
PROGRAMME_ROLES = frozenset({"local", "twin", "site", "department"})
#: Cases whose files this tool must never read or build (heldout nine).
HELDOUT_CASES = frozenset("nu metu sabanci charles masaryk tum tartu polimi vilnius".split())
#: ``<case>.<n>-<role>.json``; a KB case is a seed_id with a hyphen (``qs2027-005``).
_PROGRAMME_FILE = re.compile(r"([a-z0-9-]+)\.(\d+)-([a-z]+)\.json")
_DATE = re.compile(r"(20\d\d-\d\d-\d\d)")

Row = dict[str, Any]

#: Owner decision pending (NEXT_CYCLES_2026-10-19 §3.2 deadlines): keep a
#: verified deadline whose quote prints the day and month but no year, with the
#: year inferred from the intake's application cycle and a caveat. CLI flag
#: ``--yearless-deadlines-with-caveat``. Off: such a deadline stays unknown.
KB_YEARLESS_DEADLINES_WITH_CAVEAT = False
#: Owner decision pending (NEXT_CYCLES_2026-10-19 §5 Q7): show a verified fee
#: of a standing fee policy page that prints no academic year as current, with
#: a caveat. CLI flag ``--standing-fee-policy-current``. Off: it stays stale.
KB_STANDING_FEE_POLICY_CURRENT = False


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


def _check_of(row: Row, name: str) -> str:
    """``ci``, ``recheck`` or ``robots_override``: which check one report row is."""
    if row.get("robots_override") is True or "robots-override" in name:
        # robots.txt allowed the read after all: an ordinary recheck.
        return ROBOTS_OVERRIDE if row.get("robots_override_used", True) else "recheck"
    return "recheck" if row.get("origin") == RECHECK_ORIGIN or "recheck" in name else "ci"


def load_reports(paths: list[Path], *, exclude_robots_override: bool = False) -> list[Row]:
    """Every row of every evidence report, stamped with its date and which check it is.

    ``exclude_robots_override`` drops the rows only the owner's KB robots
    override could read (the launch-day build).
    """
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
                check = _check_of(row, path.name)
                if exclude_robots_override and check == ROBOTS_OVERRIDE:
                    continue
                out.append(
                    {
                        **row,
                        "_report_date": stamp.group(1) if stamp else None,
                        "_verified_by": check,
                        "_dir": _drafts_dir(path),
                    }
                )
    return out


def _drafts_dir(path: Path) -> str | None:
    """The ``batch*``/``topup*`` dir a report sits in (``batch3/evidence_check...``)."""
    return next((p.name for p in path.parents if p.name.startswith(("batch", "topup"))), None)


def verified_by(row: Row | None) -> str:
    """Which check a row comes from: ``ci``, ``recheck`` or ``robots_override``."""
    return str((row or {}).get("_verified_by") or "ci")


def _marked(record: Row) -> Row:
    """A record verified only by the robots override says so in its own fields."""
    if record.get("verified_by") == ROBOTS_OVERRIDE:
        record["robots_override"] = True
    return record


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
    """The row for this URL; any row when no URL is known.

    A passing row wins: CI's, then a recheck's, then a robots override's. With
    none passing, the latest check's row is returned, so the reason given is
    the most recent.
    """
    wanted = canonical_url(url) if url else None
    same = [r for r in rows if wanted is None or canonical_url(str(r.get("url") or "")) == wanted]
    same.sort(key=lambda r: _CHECK_RANK.get(verified_by(r), 1))
    return next((r for r in same if _passed(r)), same[-1] if same else None)


class Evidence:
    """The CI reports, indexed by case and item."""

    def __init__(self, rows: list[Row]) -> None:
        self.rows: dict[tuple[str, str], list[Row]] = {}
        for row in rows:
            self.rows.setdefault((str(row.get("case")), str(row.get("item"))), []).append(row)

    def find(
        self, case: str, item: str, url: str | None, *, scope: str | None = None
    ) -> Row | None:
        """The row for (case, item, URL); with ``scope``, only from that dir's reports.

        A report kept outside every ``batch*``/``topup*`` dir belongs to no
        scope and is read for every draft.
        """
        rows = self.rows.get((case, item), [])
        if scope is not None:
            rows = [r for r in rows if r.get("_dir") in (scope, None)]
        return _pick(rows, url)

    def report_for(self, draft: dict[str, Any], *, scope: str | None = None) -> Report:
        """The ``core_drafts.Report`` of one draft: per item, the row for its URL.

        ``scope`` (a ``batch*``/``topup*`` dir name) limits the rows to the
        reports in that dir. A university with drafts in several dirs is built
        this way, draft by draft: the reports carry no quote, so a batch row
        for the same URL must not verify a top-up's different quote, and a
        top-up the CI has not checked yet stays unknown.
        """
        case = str(draft["case"])
        out: Report = {}
        for item, answer in (draft.get("answers") or {}).items():
            url = answer.get("url") if isinstance(answer, dict) else None
            row = self.find(case, str(item), url, scope=scope)
            if row is not None:
                out[(case, str(item))] = row
        return out


def batch_dirs(root: Path) -> list[Path]:
    """``batch*`` and ``topup*`` directories under the root, or the root itself when it is one.

    A top-up dir fills gaps of universities imported from the development sets;
    the loader merges those entries with ``kb_imported_dev.json`` fact by fact.
    """
    batches = sorted(
        p for pattern in ("batch*", "topup*") for p in root.glob(pattern) if p.is_dir()
    )
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
        exists = key == "scholarships" or key.endswith(".exists")  # "scholarships": none offered
        return "scholarship_exists" if exists else "scholarship_international"
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
    checked_by: str = "ci",
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
        "verified_by": checked_by,
        "notes": proposal.notes,
    }
    if award and question.startswith("scholarship"):
        fact["award"] = award
    _marked(fact)
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
    scope: str | None = None,
    yearless_deadlines: bool = KB_YEARLESS_DEADLINES_WITH_CAVEAT,
    standing_fee_policy: bool = KB_STANDING_FEE_POLICY_CURRENT,
) -> tuple[dict[str, list[Row]], list[Row], list[Row]]:
    """(facts per question, unknown, not_applicable) of one core draft.

    ``scope`` limits the evidence to that dir's reports (``Evidence.report_for``).
    ``yearless_deadlines`` and ``standing_fee_policy`` are the two pending owner
    decisions (``yearless_deadline_fact``, ``standing_fee_policy_fact``), off
    by default.
    """
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
    report = evidence.report_for(draft, scope=scope)
    domain = str(row.get("official_domain") or "")
    items, _binding, note = items_for(
        draft,
        request,
        domain,
        IdentityMap(version="kb", bindings=[]),
        report,
        none_statement=True,
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
                        checked_by=verified_by(used),
                    )
                )
            elif p.status == "not_applicable":
                ev = p.evidence or {}
                not_applicable.append(
                    _marked(
                        {
                            "question": question,
                            "key": p.key,
                            "reason": p.notes,
                            "source_url": ev.get("url"),
                            "quote": ev.get("excerpt"),
                            "verified_on": verified_on,
                            "verified_by": verified_by(used),
                        }
                    )
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
        if stale_fact is not None and standing_fee_policy and question == "tuition":
            stale_fact = (
                standing_fee_policy_fact(
                    stale_fact,
                    answers.get(question) or {},
                    str(row.get("seed_id") or ""),
                    today=today,
                    intake=intake,
                )
                or stale_fact
            )
        if stale_fact is None and yearless_deadlines and question == "deadline":
            stale_fact, refused = yearless_deadline_fact(
                answers.get(question) or {},
                report.get((str(draft["case"]), question)),
                intake=intake,
                researched=researched,
                today=today,
                default_verified=default_verified,
            )
            if stale_fact is None and refused not in ("not verified", "the quote prints the year"):
                unknown = [
                    {**u, "reason": f"{u['reason']} Year not inferred: {refused}."}
                    if u["key"] == question
                    else u
                    for u in unknown
                ]
        if stale_fact is not None:
            facts[question].append(stale_fact)
            unknown = [u for u in unknown if u["key"] != question]
    if note:
        unknown.append({"question": "scholarship_exists", "key": "scholarships", "reason": note})
    found, missing = document_facts(
        draft,
        evidence,
        intake=intake,
        today=today,
        researched=researched,
        default_verified=default_verified,
        scope=scope,
    )
    facts[DOCUMENTS] = found
    unknown += missing
    return facts, unknown, not_applicable


def _documents_only(draft: dict[str, Any]) -> bool:
    """A draft whose answers hold the documents question and no core question."""
    answers = draft.get("answers") or {}
    return DOCUMENTS in answers and not any(q in answers for q in QUESTIONS if q != DOCUMENTS)


def document_item(kind: str) -> str:
    """The evidence-check item of one document (``documents.transcript``)."""
    return f"{DOCUMENTS}.{kind}"


def document_facts(
    draft: dict[str, Any],
    evidence: Evidence,
    *,
    intake: str,
    today: date,
    researched: str,
    default_verified: str,
    scope: str | None = None,
) -> tuple[list[Row], list[Row]]:
    """(facts, unknown) of a draft's ``documents`` answer, one fact per verified item.

    The answer is ``{"status", "population", "academic_year", "items": [...]}``;
    each item names a kind of ``app.knowledge.documents.DOCUMENT_KINDS``, its
    requirement (``required``, ``optional`` or ``conditional`` with the page's
    ``condition``), a URL and a verbatim quote. An item is known only when the
    evidence row of ``documents.<kind>`` at its URL is official with the quote
    found. Anything else (an unknown kind, an invalid requirement, a missing
    quote, an unverified row, a repeated kind) is listed as unknown with the
    reason; no document is inferred. A draft without the answer adds nothing.
    """
    answer = (draft.get("answers") or {}).get(DOCUMENTS)
    if not isinstance(answer, dict):
        return [], []
    case = str(draft["case"])
    raw_items = answer.get("items")
    items = raw_items if isinstance(raw_items, list) else []
    if answer.get("status") != "known" or not items:
        reason = str(answer.get("notes") or answer.get("reason") or "no document list drafted")
        return [], [{"question": DOCUMENTS, "key": DOCUMENTS, "reason": reason}]
    facts: list[Row] = []
    unknown: list[Row] = []
    seen: set[str] = set()
    for raw in items:
        item: Row = raw if isinstance(raw, dict) else {}
        kind = str(item.get("kind") or "")
        key = document_item(kind or "unnamed")
        url = str(item.get("url") or "")
        quote = re.sub(r"\s+", " ", str(item.get("quote") or "")).strip()
        requirement = str(item.get("requirement") or "")
        condition = str(item.get("condition") or "").strip() or None
        problem = None
        row: Row | None = None
        if kind not in DOCUMENT_KINDS:
            problem = f"document kind {kind!r} is not in the document vocabulary"
        elif kind in seen:
            problem = f"document kind {kind!r} is listed twice; only the first is kept"
        elif requirement not in REQUIREMENTS:
            problem = f"requirement {requirement!r} is not one of {', '.join(REQUIREMENTS)}"
        elif requirement == "conditional" and not condition:
            problem = "a conditional document without its condition"
        elif not url or not quote:
            problem = "no url or quote in the draft"
        else:
            row = evidence.find(case, key, url, scope=scope)
            if row is None or not _passed(row):
                problem = _reason(row)
        if problem is not None or row is None:
            unknown.append({"question": DOCUMENTS, "key": key, "reason": problem})
            continue
        seen.add(kind)
        fact: Row = {
            "key": key,
            "value": {"kind": kind, "requirement": requirement, "condition": condition},
            "unit": None,
            "period": None,
            "academic_year": item.get("academic_year") or answer.get("academic_year"),
            "population": item.get("population") or answer.get("population"),
            "source_url": url,
            "quote": quote,
            "quote_truncated": False,
            "source_type": "official",
            "accessed_on": str(item.get("date") or researched),
            "verified_on": _checked_on(row, default_verified),
            "verified_by": verified_by(row),
            "notes": str(item.get("notes") or ""),
        }
        _marked(fact)
        reasons = stale_reasons(fact, today, intake)
        fact["stale"] = bool(reasons)
        if reasons:
            fact["stale_reasons"] = reasons
        facts.append(fact)
    return facts, unknown


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
        "verified_by": verified_by(row),
        "notes": str(answer.get("notes") or ""),
    }
    _marked(fact)
    computed = stale_reasons(fact, today, intake)
    if any(r.startswith("academic year") for r in computed):
        reasons = [r for r in reasons if not r.startswith("published for academic year")]
    reasons = list(dict.fromkeys([*computed, *reasons]))
    fact["stale"] = bool(reasons)
    if reasons:
        fact["stale_reasons"] = reasons
    return fact


# ------------------------------------------------- owner flags (both off by default)

#: The standing fee policies of NEXT_CYCLES_2026-10-19 §3.2 / Q7: pages that
#: state a fee rule with no academic year (or only the year the rule began).
#: An explicit list, not a pattern: whether a yearless fee page is a standing
#: policy or last year's figure with the year left off is a reader's call.
STANDING_FEE_POLICIES = {
    "qs2027-008": "ETH Zurich",
    "qs2027-022": "EPFL",
    "qs2027-099": "Freie Universitaet Berlin",
    "qs2027-086": "Universität Heidelberg",
    "qs2027-100": "University of Zurich",
    "qs2027-082": "KTH Royal Institute of Technology",
    "qs2027-071": "Lund University",
    "qs2027-044": "Institut Polytechnique de Paris",
    "qs2027-095": "The University of Osaka",
    "qs2027-090": "Nanjing University",
    "qs2027-049": "University of California, Los Angeles (UCLA)",
    "qs2027-064": "Kyoto University",
    "qs2027-097": "Institute of Science Tokyo",
}

#: Month names in the languages the drafts quote (en, de, nl, sv, fr).
_MONTH_NAMES = (
    "january jan januar jänner januari janvier",
    "february feb februar februari février fevrier",
    "march mar märz maerz maart mars",
    "april apr avril",
    "may mai mei maj",
    "june jun juni juin",
    "july jul juli juillet",
    "august aug augustus augusti août aout",
    "september sep sept septembre",
    "october oct oktober octobre",
    "november nov novembre",
    "december dec dezember décembre decembre",
)
_MONTHS = {name: n for n, names in enumerate(_MONTH_NAMES, start=1) for name in names.split()}
_MONTH = "|".join(sorted(_MONTHS, key=len, reverse=True))
#: "15 January", "15. Januar", "1st of May", "1 mei", "15 april".
_DAY_MONTH = re.compile(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\.?\s+(?:of\s+)?({_MONTH})\b\.?", re.I)
#: "January 15", "Jan. 1", "December 1st".
_MONTH_DAY = re.compile(rf"\b({_MONTH})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?\b", re.I)
#: "15.07." (German numeric day.month.), never "15.07.2027".
_NUMERIC_DAY_MONTH = re.compile(r"(?<![\d.])(\d{1,2})\.(\d{1,2})\.(?!\d)")
#: "5月15日".
_CJK_DAY_MONTH = re.compile(r"(\d{1,2})\s*月\s*(\d{1,2})\s*日")
#: Words that put a date on another intake or round than the main fall one.
_OTHER_ROUND = re.compile(
    r"\b(early\s+(?:decision|action)|round\s+(?:2|3|ii|iii|two|three)|second\s+round|"
    r"late\s+round|mid-?year|spring|summer|sommersemester|semester\s+(?:2|ii|two)|"
    r"second\s+semester|transfer)\b",
    re.I,
)
_OTHER_ROUND_ACRONYM = re.compile(r"\b(?:ED\s?(?:I{1,2}|[12])?|EA|REA|SCEA)\b")


def quoted_day_months(quote: str) -> set[tuple[int, int]]:
    """Every (day, month) the quote prints, in the languages the drafts use."""
    found: set[tuple[int, int]] = set()
    for match in _DAY_MONTH.finditer(quote):
        found.add((int(match[1]), _MONTHS[match[2].lower()]))
    for match in _MONTH_DAY.finditer(quote):
        found.add((int(match[2]), _MONTHS[match[1].lower()]))
    for match in _NUMERIC_DAY_MONTH.finditer(quote):
        found.add((int(match[1]), int(match[2])))
    for match in _CJK_DAY_MONTH.finditer(quote):
        found.add((int(match[2]), int(match[1])))
    return {(d, m) for d, m in found if 1 <= d <= 31 and 1 <= m <= 12}


def application_cycle_year(month: int, intake: str) -> int | None:
    """The calendar year a yearless day of ``month`` falls in for this intake's cycle.

    Only a fall (autumn) intake has a rule. A fall-Y intake starts between
    August and October of Y, and its applications close before it starts. A
    day in August-December can precede that start only in Y-1 (in Y it would
    fall at or after the start); a day in January-July falls in Y (in Y-1 it
    would close a year or more before the start: the previous cycle). So a
    fall 2027 intake reads "1 December" as 2026-12-01 and "15 January" as
    2027-01-15. The August boundary errs towards the past: a rare late
    deadline in August of Y is read as Y-1 and then shows as passed (stale),
    never as a current date that is in fact gone.
    """
    match = re.fullmatch(r"\s*(?:fall|autumn)\s+(20\d\d)\s*", str(intake or ""), re.I)
    if not match:
        return None
    year = int(match[1])
    return year - 1 if month >= 8 else year


def yearless_deadline_fact(
    answer: dict[str, Any],
    row: Row | None,
    *,
    intake: str,
    researched: str,
    today: date,
    default_verified: str,
) -> tuple[Row | None, str]:
    """A verified deadline whose quote prints day and month but no year, year inferred.

    (``KB_YEARLESS_DEADLINES_WITH_CAVEAT``.) Returns ``(fact, "")`` or
    ``(None, why not)``. The fact carries ``year_inferred`` and ``caveat``;
    its value is the inferred date, so it turns stale once that date passes.
    Refused: a quote that prints the expert's year (not yearless: the ordinary
    rules decide), does not print the day and month, names another intake or
    round, or names a year of another cycle; an expert year other than the
    inferred one; an intake with no cycle rule (``application_cycle_year``).
    """
    if row is None or not _passed(row) or answer.get("status") != "known":
        return None, "not verified"
    url, quote = str(answer.get("url") or ""), " ".join(str(answer.get("quote") or "").split())
    if not url or not quote:
        return None, "no URL or quote"
    try:
        day = date.fromisoformat(str(answer.get("value") or "").strip())
    except ValueError:
        return None, "not a YYYY-MM-DD date"
    if str(day.year) in quote:
        return None, "the quote prints the year"
    if (day.day, day.month) not in quoted_day_months(quote):
        return None, "the quote does not print this day and month"
    cycle = application_cycle_year(day.month, intake)
    if cycle is None:
        return None, f"no application-cycle rule for the {intake} intake"
    if day.year != cycle:
        return None, f"the expert dated it {day.year}, not the {intake} cycle's {cycle}"
    if _CYCLE_2026.search(str(answer.get("notes") or "")):
        return None, "the expert marks it as another cycle"
    other = _OTHER_ROUND.search(quote) or _OTHER_ROUND_ACRONYM.search(quote)
    if other:
        return None, f"the quote names another intake or round ({other[0]!r})"
    start = requested_year({"intake": intake}) or cycle
    printed = {int(y) for y in re.findall(r"(?<!\d)(20\d\d)(?!\d)", quote)}
    if printed - {start - 1, start}:
        return None, f"the quote names another cycle's year ({min(printed - {start - 1, start})})"
    fact: Row = {
        "key": "deadline",
        "value": date(cycle, day.month, day.day).isoformat(),
        "unit": "date",
        "period": intake,
        "academic_year": answer.get("academic_year"),
        "population": answer.get("population"),
        "source_url": url,
        "quote": quote,
        "quote_truncated": False,
        "source_type": "official",
        "accessed_on": researched,
        "verified_on": _checked_on(row, default_verified),
        "verified_by": verified_by(row),
        "notes": str(answer.get("notes") or ""),
        "year_inferred": cycle,
        "caveat": YEAR_INFERRED_CAVEAT,
    }
    _marked(fact)
    reasons = stale_reasons(fact, today, intake)
    fact["stale"] = bool(reasons)
    if reasons:
        fact["stale_reasons"] = reasons
    return fact, ""


_YEAR_NOT_STATED = re.compile(r"\bnot stated\b|\bno academic year\b", re.I)


def standing_fee_policy_fact(
    fact: Row, answer: dict[str, Any], seed_id: str, *, today: date, intake: str
) -> Row | None:
    """A stale "academic year not stated" fee of a listed standing policy, made current.

    (``KB_STANDING_FEE_POLICY_CURRENT``.) Only for a ``STANDING_FEE_POLICIES``
    university whose fee states no academic year. The published year text, if
    any, moves to ``academic_year_stated``; ``academic_year`` is cleared, so no
    year rule reads it, and the fact gets the caveat. It stays stale for the
    reasons that do not depend on the year (a verification older than 365 days).
    The period is kept: a per-semester or whole-programme fee is current but
    still never enters the yearly cost table.
    """
    if seed_id not in STANDING_FEE_POLICIES or fact.get("key") != "tuition":
        return None
    raw = answer.get("value")
    stated = (raw or {}).get("academic_year") if isinstance(raw, dict) else None
    if stated and not _YEAR_NOT_STATED.search(str(stated)):
        return None
    out: Row = {**fact, "academic_year": None, "caveat": STANDING_FEE_POLICY_CAVEAT}
    out["standing_policy"] = True
    if stated:
        out["academic_year_stated"] = stated
    out.pop("stale_reasons", None)
    reasons = stale_reasons(out, today, intake)
    out["stale"] = bool(reasons)
    if reasons:
        out["stale_reasons"] = reasons
    return out


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
            "verified_by": verified_by(row),
            "source_type": "official",
        }
        _marked(record)
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


# ------------------------------------------------------------------- merge

#: (facts per question, unknown, not_applicable): what ``core_facts`` returns.
CoreResult = tuple[dict[str, list[Row]], list[Row], list[Row]]


def _merge_unit(question: str, key: str) -> tuple[str, ...]:
    """What one later draft can replace: a whole question, or one English test.

    The English answer nests several tests (IELTS overall and sub-scores, TOEFL,
    Duolingo) under one quote, so each test's fact merges on its own key: a
    top-up that verifies only Duolingo keeps the batch's IELTS fact.
    """
    return (question, key) if question == "english" else (question,)


def _by_unit(result: CoreResult) -> dict[tuple[str, ...], dict[str, list[Row]]]:
    facts, unknown, not_applicable = result
    out: dict[tuple[str, ...], dict[str, list[Row]]] = {}

    def slot(question: str, key: str) -> dict[str, list[Row]]:
        return out.setdefault(
            _merge_unit(question, key), {"facts": [], "not_applicable": [], "unknown": []}
        )

    for question, found in facts.items():
        for fact in found:
            slot(question, str(fact.get("key")))["facts"].append(fact)
    for record in not_applicable:
        slot(str(record["question"]), str(record["key"]))["not_applicable"].append(record)
    for record in unknown:
        slot(str(record["question"]), str(record["key"]))["unknown"].append(record)
    return out


def merge_core_results(parts: list[tuple[dict[str, Any], str, CoreResult]]) -> CoreResult:
    """One university's core drafts from several dirs (``batch*`` then ``topup*``), merged.

    ``parts`` is ``(draft, batch name, core_facts result)`` in build order; the
    first is the base. A later draft replaces a question (an English test, see
    ``_merge_unit``) only when it is ``known`` or ``not_applicable`` there; its
    ``unknown`` never overwrites a known or not-applicable record. With nothing
    known on either side, the unknown reason of the latest draft that answered
    the question wins (the newer research says why). A record taken from a
    draft other than the base carries ``source_batch``; the base's records
    inherit the entry's own ``source_batch``. Evidence still decides known-ness
    per draft: each draft's facts were built from the rows for its own URLs.
    """
    if len(parts) == 1:
        return parts[0][2]
    base = parts[0][1]
    merged: dict[tuple[str, ...], dict[str, list[Row]]] = {}
    for draft, batch, result in parts:
        answered = {q for q, a in (draft.get("answers") or {}).items() if isinstance(a, dict)}
        for unit, records in _by_unit(result).items():
            if batch != base:
                for record in (r for rs in records.values() for r in rs):
                    record["source_batch"] = batch
            offers = bool(records["facts"] or records["not_applicable"])
            held = merged.get(unit)
            held_offers = bool(held and (held["facts"] or held["not_applicable"]))
            if held is None and batch == base:
                merged[unit] = records  # the base draft: every record as built
            elif offers or (unit[0] in answered and not held_offers):
                merged[unit] = records
    facts: dict[str, list[Row]] = {q: [] for q in QUESTIONS}
    unknown: list[Row] = []
    not_applicable: list[Row] = []
    for unit, records in merged.items():
        facts.setdefault(unit[0], []).extend(records["facts"])
        not_applicable += records["not_applicable"]
        unknown += records["unknown"]
    return facts, unknown, not_applicable


# ------------------------------------------------------------------- build


def robots_override_records(entries: dict[str, Row]) -> list[Row]:
    """Every record marked ``robots_override``: what the launch-day build removes."""
    out: list[Row] = []
    for seed_id, entry in entries.items():
        programme = entry.get("programme") or {}
        for kind in ("evidence", "teaching_language_evidence"):
            out += [
                {
                    "seed_id": seed_id,
                    "source": "programme",
                    "question": "programme",
                    "key": kind,
                    "url": r.get("url"),
                }
                for r in programme.get(kind) or []
                if r.get("robots_override")
            ]
        out += [
            {
                "seed_id": seed_id,
                "source": "fact",
                "question": q,
                "key": f.get("key"),
                "url": f.get("source_url"),
            }
            for q, fs in (entry.get("facts") or {}).items()
            for f in fs or []
            if f.get("robots_override")
        ]
        out += [
            {
                "seed_id": seed_id,
                "source": "not_applicable",
                "question": r.get("question"),
                "key": r.get("key"),
                "url": r.get("source_url"),
            }
            for r in entry.get("not_applicable") or []
            if r.get("robots_override")
        ]
    return out


def build(
    root: Path,
    reports: list[Path],
    *,
    list_path: Path = LIST,
    built_at: str | None = None,
    intake: str = "fall 2027",
    version: str | None = None,
    exclude_robots_override: bool = False,
    yearless_deadlines_with_caveat: bool = KB_YEARLESS_DEADLINES_WITH_CAVEAT,
    standing_fee_policy_current: bool = KB_STANDING_FEE_POLICY_CURRENT,
) -> Row:
    built_at = built_at or datetime.now(UTC).date().isoformat()
    today = date.fromisoformat(built_at)
    rows = load_list(list_path)
    resolve = Resolver(rows)
    evidence = Evidence(load_reports(reports, exclude_robots_override=exclude_robots_override))
    list_doc = json.loads(list_path.read_text(encoding="utf-8"))

    pages: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    # Every dir's core draft of a case, in build order: a ``topup*`` draft may
    # hold only some answers, so it is merged answer by answer, never swapped in.
    cores: dict[str, list[tuple[dict[str, Any], str]]] = {}
    for batch in batch_dirs(root):
        for case, found in load_programme_pages(batch / "programme").items():
            held = pages.setdefault(case, [])
            # Programme pages: the union over dirs, a page restated by a top-up once.
            held += [page for page in found if page not in held]
        core_dir = batch / "core"
        if core_dir.is_dir():
            for draft in load_drafts(core_dir):
                cores.setdefault(str(draft["case"]), []).append((draft, batch.name))

    entries: dict[str, Row] = {}
    unresolved: list[Row] = []
    for case in sorted(set(pages) | set(cores)):
        # A documents-only draft (``topup_documents1``) sorts before
        # ``topup_imported`` by name but is never the base: the base is the
        # first draft that answers a core question (a stable sort).
        drafts = sorted(cores.get(case) or [({}, "")], key=lambda d: _documents_only(d[0]))
        draft, batch_name = drafts[0]
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
            facts, unknown, not_applicable = merge_core_results(
                [
                    (
                        one,
                        name,
                        core_facts(
                            one,
                            row,
                            evidence,
                            intake=intake,
                            today=today,
                            default_verified=default_verified,
                            scope=name if len(drafts) > 1 else None,
                            yearless_deadlines=yearless_deadlines_with_caveat,
                            standing_fee_policy=standing_fee_policy_current,
                        ),
                    )
                    for one, name in drafts
                ]
            )
        else:
            unknown = [{"question": q, "key": q, "reason": "no core draft"} for q in QUESTIONS]
        programme = programme_block(
            case, pages.get(case, []), evidence, default_verified=default_verified
        )
        dates = [f["verified_on"] for fs in facts.values() for f in fs] + [
            e["verified_on"] for e in programme["evidence"]
        ]
        checks = {f["verified_by"] for fs in facts.values() for f in fs} | {
            e["verified_by"] for e in programme["evidence"]
        }
        basis = "ci_evidence_check"
        if "recheck" in checks:
            basis += "+sandbox_recheck"
        if ROBOTS_OVERRIDE in checks:
            basis += "+robots_override"
        domains = [
            str(row.get("official_domain") or ""),
            _host(row.get("official_site")),
            *[str(d).lower().removeprefix("www.") for d in row.get("extra_domains") or []],
        ]
        entry: Row = {
            "seed_id": row["seed_id"],
            "source_case": case,
            "source_batch": batch_name,
            "review_status": "expert_checked",
            "verified_on": max(dates) if dates else None,
            "verified_on_basis": basis,
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
        if len(drafts) > 1:
            # Merged from several dirs: the base is ``source_batch``; a record
            # taken from a later dir carries its own ``source_batch``.
            entry["source_batches"] = [name for _one, name in drafts]
        entries[str(row["seed_id"])] = entry
    stale = [
        {"seed_id": s, "question": q, "key": f["key"], "reasons": f["stale_reasons"]}
        for s, e in entries.items()
        for q, fs in e["facts"].items()
        for f in fs
        if f.get("stale")
    ]
    document: Row = {
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
        "robots_override_excluded": exclude_robots_override,
        "robots_override_facts": robots_override_records(entries),
        "entries": dict(sorted(entries.items())),
        "stale_facts": stale,
        "unresolved_drafts": unresolved,
    }
    if yearless_deadlines_with_caveat or standing_fee_policy_current:
        # Only a build with an owner flag on carries these keys: a default
        # build is byte-identical to one made before the flags existed.
        document["owner_flags"] = {
            "yearless_deadlines_with_caveat": yearless_deadlines_with_caveat,
            "standing_fee_policy_current": standing_fee_policy_current,
        }
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


# ----------------------------------------------------------------- refresh


def _refresh_key(*parts: str) -> tuple[str, ...]:
    """(seed_id, source, item, key, URL, quote) of a KB record or a ``--from-kb`` row."""
    seed_id, source, item, key, url, quote = parts
    return (seed_id, source, item, key, canonical_url(url), quote)


def _restamp(record: Row, row: Row | None, where: Row, review: list[Row]) -> None:
    """One KB record against its refresh row: re-date it, or mark it for review."""
    if row is None:
        return  # not checked this time (``--only``): left exactly as it was
    found = classify(row)
    if found == VERIFIED:
        record["verified_on"] = str(row.get("checked_on") or record.get("verified_on"))
        record["verified_by"] = "recheck" if row.get("origin") == RECHECK_ORIGIN else "ci"
        # Re-verified by an ordinary check: no longer an override record.
        record.pop("robots_override", None)
        record.pop("review", None)
        return
    record["review"] = {
        "needed": True,
        "class": found,
        "outcome": row.get("outcome"),
        "status_code": row.get("status_code"),
        "checked_on": row.get("checked_on"),
    }
    review.append({**where, "class": found})


def refresh(document: Row, rows: list[Row], *, today: date, report: str = "") -> Row:
    """A copy of a built KB re-stamped from a ``--from-kb`` report (module docstring)."""
    out: Row = json.loads(json.dumps(document))
    index = {
        _refresh_key(
            str(r.get("seed_id")),
            str(r.get("source")),
            str(r.get("item")),
            str(r.get("key")),
            str(r.get("url") or ""),
            str(r.get("quote") or ""),
        ): r
        for r in rows
        if isinstance(r, dict)
    }
    intake = out.get("intake") or "fall 2027"
    review: list[Row] = []

    def visit(seed: str, record: Row, source: str, item: str, key: str, url: str) -> None:
        quote = str(record.get("quote") or "")
        row = index.get(_refresh_key(seed, source, item, key, url, quote))
        where = {"seed_id": seed, "question": item, "key": key, "source": source, "url": url}
        _restamp(record, row, where, review)

    for seed_id, entry in (out.get("entries") or {}).items():
        seed = str(seed_id)
        programme = entry.get("programme") or {}
        for record in programme.get("evidence") or []:
            url = str(record.get("url") or "")
            visit(seed, record, "programme", "programme", url, url)
        for question, facts in (entry.get("facts") or {}).items():
            for fact in facts or []:
                url = str(fact.get("source_url") or "")
                # A document fact's check item is its key, as in --from-kb.
                item = str(fact.get("key")) if question == DOCUMENTS else str(question)
                visit(seed, fact, "fact", item, str(fact.get("key")), url)
                reasons = current_stale_reasons(fact, today, intake)
                fact["stale"] = bool(reasons)
                if reasons:
                    fact["stale_reasons"] = reasons
                else:
                    fact.pop("stale_reasons", None)
        for record in entry.get("not_applicable") or []:
            url = str(record.get("source_url") or "")
            question, key = str(record.get("question") or ""), str(record.get("key"))
            visit(seed, record, "not_applicable", question, key, url)
        records = [
            *(programme.get("evidence") or []),
            *[f for fs in (entry.get("facts") or {}).values() for f in fs or []],
        ]
        dates = [str(r["verified_on"]) for r in records if r.get("verified_on")]
        if dates and entry.get("verified_on"):
            entry["verified_on"] = max(dates)
    out["stale_facts"] = [
        {"seed_id": s, "question": q, "key": f["key"], "reasons": f["stale_reasons"]}
        for s, e in (out.get("entries") or {}).items()
        for q, fs in (e.get("facts") or {}).items()
        for f in fs or []
        if f.get("stale")
    ]
    if isinstance(out.get("stale_policy"), dict):
        out["stale_policy"]["as_of"] = today.isoformat()
    if report:
        out["evidence_reports"] = [*(out.get("evidence_reports") or []), report]
    if "robots_override_facts" in out:
        out["robots_override_facts"] = robots_override_records(out.get("entries") or {})
    out["refreshed_at"] = today.isoformat()
    out["review_queue"] = review
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("drafts_root", type=Path, nargs="?")
    parser.add_argument(
        "--refresh",
        type=Path,
        metavar="KB",
        help="re-stamp this built KB from a --from-kb report (--evidence) instead of building",
    )
    parser.add_argument("--evidence", type=Path, nargs="+", default=[])
    parser.add_argument("--out", type=Path, default=KB_FILE)
    parser.add_argument("--list", type=Path, default=LIST)
    parser.add_argument("--built-at", help="YYYY-MM-DD (default: today, UTC)")
    parser.add_argument("--intake", default="fall 2027")
    parser.add_argument("--version")
    parser.add_argument(
        "--exclude-robots-override",
        action="store_true",
        help="build without the rows only the owner's KB robots override read (launch day)",
    )
    parser.add_argument(
        "--yearless-deadlines-with-caveat",
        action="store_true",
        default=KB_YEARLESS_DEADLINES_WITH_CAVEAT,
        help="keep a verified day-and-month deadline with no printed year, year inferred from "
        "the intake's application cycle, with a caveat (owner decision; off by default)",
    )
    parser.add_argument(
        "--standing-fee-policy-current",
        action="store_true",
        default=KB_STANDING_FEE_POLICY_CURRENT,
        help="show a listed standing fee policy that prints no academic year as current, with "
        "a caveat (owner decision Q7; off by default)",
    )
    args = parser.parse_args(argv)
    if args.refresh:
        if args.drafts_root or len(args.evidence) != 1:
            parser.error("--refresh takes no drafts root and exactly one --evidence report")
        if args.out.resolve() in (KB_FILE.resolve(), args.refresh.resolve()):
            parser.error("--refresh needs an explicit --out (the built KB is never overwritten)")
        today = date.fromisoformat(args.built_at or datetime.now(UTC).date().isoformat())
        rows = json.loads(args.evidence[0].read_text(encoding="utf-8"))
        document = json.loads(args.refresh.read_text(encoding="utf-8"))
        data = refresh(document, rows, today=today, report=args.evidence[0].name)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(
            f"refreshed {args.refresh.name}: review={len(data['review_queue'])} "
            f"stale={len(data['stale_facts'])} -> {args.out}"
        )
        return 0
    if args.drafts_root is None:
        parser.error("give a drafts root, or --refresh KB")
    if not args.evidence:
        print("no --evidence report: every value stays unknown", file=sys.stderr)
    data = build(
        args.drafts_root,
        args.evidence,
        list_path=args.list,
        built_at=args.built_at,
        intake=args.intake,
        version=args.version,
        exclude_robots_override=args.exclude_robots_override,
        yearless_deadlines_with_caveat=args.yearless_deadlines_with_caveat,
        standing_fee_policy_current=args.standing_fee_policy_current,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    known = sum(e["known_fact_count"] for e in data["entries"].values())
    print(
        f"entries={len(data['entries'])} known_facts={known} stale={len(data['stale_facts'])} "
        f"unresolved={len(data['unresolved_drafts'])} "
        f"robots_override={len(data['robots_override_facts'])}"
        + (f" caveat_facts={len(data['caveat_facts'])}" if "caveat_facts" in data else "")
        + f" -> {args.out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
