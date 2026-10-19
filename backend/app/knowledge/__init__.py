"""The verified knowledge base: bachelor's in Computer Science, top-100 catalogue.

Owner decision (2026-10-19): live search and discovery are frozen; the product
answers from facts an expert drafted and the CI evidence check
(``scripts/verify_evidence.py``) confirmed on an official page, word for word.

Two files, one entry shape (``docs/process/KNOWLEDGE_BASE.md``):

* ``kb_cs_bachelor.json`` - built from the expert batches by
  ``python -m evaluation.research.expert.kb_build``;
* ``kb_imported_dev.json`` - the development-corpus import
  (``docs/process/KB_IMPORT_2026-10-19.md``), merged when present.

Both are keyed by the catalogue ``seed_id``. A fact's identity is
``(seed_id, key)``; on a collision the more recently verified fact wins, and the
built file wins a tie. Nothing here touches the network.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

log = logging.getLogger("unimatch.knowledge")

KNOWLEDGE_DIR = Path(__file__).resolve().parent
KB_FILE = KNOWLEDGE_DIR / "kb_cs_bachelor.json"
IMPORTED_FILE = KNOWLEDGE_DIR / "kb_imported_dev.json"

#: The six core questions, in display order.
CORE_QUESTIONS = (
    "english",
    "gpa",
    "deadline",
    "tuition",
    "scholarship_exists",
    "scholarship_international",
)
#: The application documents an international applicant sends: one fact per
#: required, optional or conditional item (``app.knowledge.documents``).
DOCUMENTS = "documents"
#: Every question a KB entry answers: the six core ones, then the documents.
QUESTIONS = (*CORE_QUESTIONS, DOCUMENTS)
#: A fact verified longer ago than this is shown as stale, never as current.
MAX_AGE_DAYS = 365

#: How a review status reads to the applicant. An unsigned expert draft whose
#: quote the CI check found is not a human verification and never says so.
REVIEW_LABELS = {
    "human_verified": "human verified",
    "draft": "expert-checked, quote verified",
    "expert_checked": "expert-checked, quote verified",
}


def review_label(status: str | None) -> str:
    return REVIEW_LABELS.get(str(status or ""), "expert-checked, quote verified")


#: The two caveats a KB build can attach to a fact when an owner flag is on
#: (``evaluation.research.expert.kb_build``: ``--yearless-deadlines-with-caveat``,
#: ``--standing-fee-policy-current``). A fact with a caveat may be current, but
#: it is never shown as fully verified: the page did not print the year.
YEAR_INFERRED_CAVEAT = "year not printed on the page; assumed current application cycle"
STANDING_FEE_POLICY_CAVEAT = "fee policy page; no academic year printed"
#: How a caveat reads in a claim's notes ("Caveat: <caveat>.").
CAVEAT_MARK = "Caveat: "


def fact_caveat(fact: dict[str, Any]) -> str | None:
    """The fact's caveat, or None.

    A deadline whose year the build inferred (``year_inferred``) always has
    one, even if the file lost it, so an inferred year is never shown as read
    from the page.
    """
    caveat = fact.get("caveat")
    if isinstance(caveat, str) and caveat.strip():
        return " ".join(caveat.split()).rstrip(".")
    if fact.get("year_inferred") is not None:
        return YEAR_INFERRED_CAVEAT
    return None


def _as_date(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


#: The build's annotation for a page that prints no academic year ("not stated
#: (...)", "... (no academic year stated)"): whatever year the note mentions is
#: context, not the fact's academic year.
_YEAR_NOT_STATED = re.compile(r"\bnot stated\b|\bno academic year\b", re.IGNORECASE)
#: "2026/27", "2026-2027", "2026/2027"; never part of an ISO date ("2019-04-01").
_ACADEMIC_YEAR = re.compile(r"(?<![\d/-])(20\d\d)\s*[/-]\s*(\d{4}|\d{2})(?![\d/-])")
#: "since WS 2017/18", "from the 2025/26 winter semester": the year a policy began.
_POLICY_START = re.compile(
    r"\b(?:since|from|starting|effective|as of)\b(?:\s+[^\s\d]+){0,3}\s*$", re.IGNORECASE
)


def academic_year_not_stated(text: Any) -> bool:
    """Whether a stated academic year is the build's "not stated" annotation."""
    return bool(_YEAR_NOT_STATED.search(str(text or "")))


def academic_year_end(text: Any) -> int | None:
    """The end year of "2026/27", "2026-2027" or "2026/2027"; None when unstated.

    Only two consecutive years are an academic year: an ISO date ("2019-04-01")
    is not, nor is the year a policy began ("since winter semester 2017/18"),
    nor any year inside a "not stated (...)" annotation.
    """
    text = str(text or "")
    if academic_year_not_stated(text):
        return None
    for match in _ACADEMIC_YEAR.finditer(text):
        if _POLICY_START.search(text[: match.start()]):
            continue
        start, end = int(match[1]), match[2]
        last = int(end) if len(end) == 4 else (start // 100) * 100 + int(end)
        if last == start + 1:
            return last
    return None


def intake_academic_year_start(intake: str | None) -> int | None:
    """The first calendar year of the academic year an intake starts ("fall 2027" -> 2027).

    A winter, spring or summer intake joins the academic year that began the
    autumn before (the runner's ``_TERM_START_MONTH``: January, January, May),
    so a summer 2027 intake is in 2026/27, as ``applicant_academic_year`` has it.
    """
    match = re.search(r"\b(20\d\d)\b", str(intake or ""))
    if not match:
        return None
    year = int(match[1])
    return year - 1 if re.search(r"winter|spring|summer", str(intake), re.IGNORECASE) else year


#: A stored reason the build computed against *its* intake ("academic year
#: 2026/2027 is before the fall 2027 intake's 2027/28"). It holds only for
#: that intake; for any other, ``stale_reasons`` recomputes it.
_INTAKE_RELATIVE_REASON = re.compile(r"^academic year .* is before the (?P<intake>.+?) intake's ")


def carried_stale_reasons(fact: dict[str, Any], intake: str | None) -> list[str]:
    """The build's stored ``stale_reasons`` that still hold for ``intake``.

    Every stored reason is kept but one computed for another intake: the KB is
    built for one intake (fall 2027) and a spring 2027 applicant's 2026/27 fee
    is current, not "before the fall 2027 intake's 2027/28".
    """
    wanted = " ".join(str(intake or "").lower().split())
    kept: list[str] = []
    for reason in fact.get("stale_reasons") or []:
        found = _INTAKE_RELATIVE_REASON.match(str(reason))
        if found and wanted and " ".join(found["intake"].lower().split()) != wanted:
            continue
        kept.append(str(reason))
    return kept


def stale_reasons(fact: dict[str, Any], today: date, intake: str | None = None) -> list[str]:
    """Why a fact may not be shown as current (empty: it may).

    Stale: verified more than ``MAX_AGE_DAYS`` ago; an academic year already
    past, or (given the intake) one before the intake's academic year, so a
    2026/27 fee is stale for a fall 2027 applicant; a deadline that has passed.
    """
    reasons: list[str] = []
    verified = _as_date(fact.get("verified_on")) or _as_date(fact.get("accessed_on"))
    if verified is None:
        reasons.append("no verification date")
    elif (today - verified).days > MAX_AGE_DAYS:
        reasons.append(f"verified on {verified.isoformat()}, more than {MAX_AGE_DAYS} days ago")
    end = academic_year_end(fact.get("academic_year"))
    wanted = intake_academic_year_start(intake)
    if end is not None and end <= today.year:
        reasons.append(f"academic year {fact.get('academic_year')} is past")
    elif end is not None and wanted is not None and end - 1 < wanted:
        reasons.append(
            f"academic year {fact.get('academic_year')} is before the {intake} intake's "
            f"{wanted}/{str(wanted + 1)[2:]}"
        )
    key = str(fact.get("key") or "")
    if key == "deadline" or key.startswith("deadline."):
        day = _as_date(fact.get("value"))
        if day is not None and day < today:
            reasons.append(f"deadline {day.isoformat()} has passed")
    return reasons


@dataclass
class KnowledgeEntry:
    """One university's verified answers for the bachelor's in Computer Science."""

    seed_id: str
    university: str
    country: str
    official_domains: tuple[str, ...]
    review_status: str
    verified_on: str | None
    programme: dict[str, Any]
    facts: dict[str, list[dict[str, Any]]]
    unknown: list[dict[str, Any]] = field(default_factory=list)
    #: Verified "does not apply" answers, e.g. no scholarship for bachelor's
    #: applicants: ``{question, key, reason, source_url, quote, verified_on}``.
    not_applicable: list[dict[str, Any]] = field(default_factory=list)
    origin: str = ""

    @property
    def programme_known(self) -> bool:
        return self.programme.get("status") == "known" and bool(self.programme.get("evidence"))

    @property
    def has_verified_data(self) -> bool:
        """A verified programme page or at least one verified fact."""
        return self.programme_known or any(self.facts.get(q) for q in QUESTIONS)

    def all_facts(self) -> list[tuple[str, dict[str, Any]]]:
        return [(q, f) for q in QUESTIONS for f in self.facts.get(q, [])]


@dataclass
class KnowledgeBase:
    version: str
    built_at: str | None
    entries: dict[str, KnowledgeEntry]
    sources: list[str] = field(default_factory=list)

    def get(self, seed_id: str | None) -> KnowledgeEntry | None:
        return self.entries.get(seed_id or "")

    def by_domain(self, host: str | None) -> KnowledgeEntry | None:
        """The entry whose official domain is ``host`` or a parent of it."""
        host = (host or "").lower().removeprefix("www.")
        if not host:
            return None
        for entry in self.entries.values():
            if any(host == d or host.endswith("." + d) for d in entry.official_domains):
                return entry
        return None


def _entry(seed_id: str, raw: dict[str, Any], origin: str) -> KnowledgeEntry:
    domains = raw.get("official_domains") or [raw.get("official_domain")]
    facts_raw = raw.get("facts") or {}
    facts = {
        q: [dict(f) for f in facts_raw.get(q) or [] if isinstance(f, dict) and f.get("quote")]
        for q in QUESTIONS
    }
    return KnowledgeEntry(
        seed_id=seed_id,
        university=str(raw.get("university") or ""),
        country=str(raw.get("country") or ""),
        official_domains=tuple(
            str(d).lower().removeprefix("www.") for d in domains if isinstance(d, str) and d
        ),
        review_status=str(raw.get("review_status") or "draft"),
        verified_on=raw.get("verified_on"),
        programme=dict(raw.get("programme") or {}),
        facts=facts,
        unknown=list(raw.get("unknown") or []),
        not_applicable=[dict(n) for n in raw.get("not_applicable") or [] if isinstance(n, dict)],
        origin=origin,
    )


def _read(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as exc:
        log.error("knowledge base %s unreadable: %s", path, exc)
        return None
    return data if isinstance(data, dict) else None


def _entries(document: dict[str, Any], origin: str) -> dict[str, KnowledgeEntry]:
    raw = document.get("entries") or {}
    if isinstance(raw, list):
        raw = {str(e.get("seed_id")): e for e in raw if isinstance(e, dict) and e.get("seed_id")}
    return {str(k): _entry(str(k), v, origin) for k, v in raw.items() if isinstance(v, dict)}


def merge_entries(primary: KnowledgeEntry, other: KnowledgeEntry) -> KnowledgeEntry:
    """``primary`` (the built file) merged with ``other`` (the import), fact by fact."""
    facts: dict[str, list[dict[str, Any]]] = {}
    for question in QUESTIONS:
        by_key: dict[str, dict[str, Any]] = {}
        for fact in other.facts.get(question, []):
            by_key[str(fact.get("key"))] = fact
        for fact in primary.facts.get(question, []):
            key = str(fact.get("key"))
            old = by_key.get(key)
            if old is None or str(fact.get("verified_on") or "") >= str(
                old.get("verified_on") or ""
            ):
                by_key[key] = fact
        facts[question] = list(by_key.values())
    known_keys = {str(f.get("key")) for fs in facts.values() for f in fs}
    unknown = [
        u
        for u in [*primary.unknown, *other.unknown]
        if str(u.get("key") or u.get("question")) not in known_keys
    ]
    # A "does not apply" answer is a fact too: the more recently verified one
    # of a key wins, the built file on a tie, and a known fact of that key wins.
    by_na: dict[str, dict[str, Any]] = {}
    for row in [*other.not_applicable, *primary.not_applicable]:
        key = str(row.get("key") or row.get("question"))
        old = by_na.get(key)
        if old is None or str(row.get("verified_on") or "") >= str(old.get("verified_on") or ""):
            by_na[key] = row
    not_applicable = [n for k, n in by_na.items() if k not in known_keys]
    return KnowledgeEntry(
        seed_id=primary.seed_id,
        university=primary.university or other.university,
        country=primary.country or other.country,
        official_domains=tuple(dict.fromkeys((*primary.official_domains, *other.official_domains))),
        review_status=primary.review_status,
        verified_on=max((v for v in (primary.verified_on, other.verified_on) if v), default=None),
        programme=primary.programme if primary.programme_known else other.programme,
        facts=facts,
        unknown=unknown,
        not_applicable=not_applicable,
        origin=f"{primary.origin}+{other.origin}",
    )


def load_knowledge_base(path: Path | None = None, imported: Path | None = None) -> KnowledgeBase:
    """The built KB merged with the development import; an empty KB when neither exists."""
    path = path or KB_FILE
    imported = imported or IMPORTED_FILE
    built = _read(path)
    extra = _read(imported)
    entries = _entries(built, path.name) if built else {}
    sources = [path.name] if built else []
    if extra:
        sources.append(imported.name)
        for seed_id, entry in _entries(extra, imported.name).items():
            entries[seed_id] = (
                merge_entries(entries[seed_id], entry) if seed_id in entries else entry
            )
    return KnowledgeBase(
        version=str((built or {}).get("version") or (extra or {}).get("format") or "empty"),
        built_at=(built or {}).get("built_at") or (extra or {}).get("generated_on"),
        entries=entries,
        sources=sources,
    )
