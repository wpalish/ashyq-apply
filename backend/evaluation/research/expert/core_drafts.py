"""Expert core-question drafts -> unsigned draft corpora and a signing worksheet.

Finish plan v2, track A (docs/process/SEARCH_FINISH_PLAN_V2.md). Expert
subagents answer the six core questions (English minimum, GPA, deadline,
tuition, scholarship exists, scholarship open to internationals) plus the
programme page, each with an official URL and a verbatim quote. This module
turns those answers into *drafts only*: nothing it writes is signed, and every
case it changes is ``review.status == "draft"`` until the owner signs.

Run from ``backend``::

    python -m evaluation.research.expert.core_drafts DRAFTS_DIR \\
        [--evidence REPORT.json] [--out-cohort ...] [--out-heldout ...] \\
        [--out-bindings ...] [--worksheet ...]

Rules, in the order they are applied:

* **Verification.** A ``known`` or ``not_applicable`` expert item is VERIFIED
  only if the evidence report of ``scripts/verify_evidence.py`` has a row for
  that case and item with ``official`` and ``quote_found`` both true. Without a
  report nothing is verified. An unverified item never becomes ``known`` or
  ``not_applicable``: it is written ``unknown`` with the note
  ``expert value X unverified: <reason>``.
* **English.** ``ielts.overall`` (float), ``ielts.subscores`` (four bands; a
  "no band below" floor is written for every band, as UBC's signed label),
  ``english_evidence.toefl_ibt.minimum`` and ``english_evidence.duolingo.minimum``
  (ints; the reviewed9 ``english_evidence.<test>.minimum`` family, which the
  scorecard's core-question pattern also matches). A sub-value whose number is
  not in the expert's quote stays ``unknown``: one quote cannot evidence a
  figure it does not contain. When the requirement is another language
  (German, Italian, Polish, Czech, ...) or no test is required,
  ``ielts.overall``/``ielts.subscores`` are ``not_applicable`` with the reason.
* **GPA.** ``gpa`` is ``known`` only for a grade/average threshold on the
  school record, and its value is a string description (``mapping.py`` has no
  corpus key for ``MIN_GPA``; the pipeline's bare float would lose the scale).
  A test-score threshold (SAT, ACT, UNT, TOL/TOLC, a points scheme) makes
  ``gpa`` ``not_applicable`` with the threshold kept in the notes. An
  indicative past-years average or "lower boundary" is not a published
  minimum and stays ``unknown``.
* **Deadline.** ``YYYY-MM-DD``. A date before the research date, or one the
  expert marks as the 2026 cycle, is ``unknown`` ("only the 2026 cycle is
  published"). A date whose year is not printed in the quote is not dated
  (REVIEW_DRAFT8.md, "Conventions used").
* **Tuition.** ``{"amount": float, "currency": ISO}`` per year, the shape of
  every reviewed9 tuition label; population and academic year go into the
  evidence scope. **Fee-year rule applied:** the strict one. REVIEW_DRAFT8.md
  and reviewed9 keep NTU tuition ``unknown`` because "only Academic Year
  2026/2027 is published", so a fee whose stated academic year is not 2027/28
  (or is not stated) is ``unknown`` with the published year in the note. Money
  is per year (REVIEW_DRAFT8.md); a per-semester or per-credit figure is not
  multiplied out, it stays ``unknown``.
* **Scholarships.** ``scholarships.<slug>.exists`` = true and
  ``scholarships.<slug>.applicability.international``. The slug reuses an
  existing award binding of the same case when the names agree
  (``nanyang_global``, ``kaist``); otherwise it is built from the award name.
  Each new (source, subject) identity gets a draft binding. An expert
  ``not_applicable`` (no award for bachelor applicants) writes no scholarship
  keys, only a case note. The KB builder alone (``none_statement=True``)
  writes it as a ``scholarships`` ``not_applicable`` label with its quote.
* **Scope.** Evidence scope is the case request; tuition evidence also
  carries the population and academic year the expert read.
* **Cohort merge.** reviewed9 is the base. A reviewed9 ``known`` label is never
  overwritten: a different expert value is a CONFLICT row (old and new value,
  both URLs) and a case note. A reviewed9 ``unknown``/``not_applicable`` label
  is replaced by a verified expert label; an unverified expert value replaces
  only an ``unknown`` (as ``unknown`` with the note), never a signed N/A.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from pydantic import HttpUrl, TypeAdapter, ValidationError

from ..identities import IdentityMap
from ..live import DEV2_DOMAINS, DEV3_IDS, HELDOUT
from ..metrics import canonical_url
from ..schema import Dataset

DRAFT_DATE = "2026-10-17"
PREPARED_BY = "claude-opus-5 + expert subagents"
COHORT_VERSION = f"{DRAFT_DATE}.draft10"
HELDOUT_VERSION = f"{DRAFT_DATE}.heldout-draft1"
BINDINGS_VERSION = f"{DRAFT_DATE}.draft2"
BINDING_NOTE = f"expert draft {DRAFT_DATE}, unsigned"
#: The schema allows only development/validation; the heldout set is validation.
HELDOUT_SPLIT = "validation"
#: dev2 (finish plan v2, loop 2): universities with no curated registry entry,
#: a development split for tuning discovery, so the heldout nine stay clean.
DEV2_VERSION = f"{DRAFT_DATE}.dev2-draft1"
DEV2_SPLIT = "development"
#: dev3: fifteen more no-seed universities, its own development file.
DEV3_VERSION = f"{DRAFT_DATE}.dev3-draft1"
#: Every non-cohort case the converter can build: heldout and dev2.
OTHER_DOMAINS: dict[str, str] = {**HELDOUT, **DEV2_DOMAINS}


def other_version(case_id: str) -> str:
    if case_id in DEV3_IDS:
        return DEV3_VERSION
    return DEV2_VERSION if case_id in DEV2_DOMAINS else HELDOUT_VERSION


DATA = Path(__file__).resolve().parents[1] / "data"
REVIEWED = DATA / "ground_truth.reviewed9.json"
BINDINGS = DATA / "identity_bindings.reviewed.json"

ITEMS = (
    "english",
    "gpa",
    "deadline",
    "tuition",
    "scholarship_exists",
    "scholarship_international",
)
QUESTION_RU = {
    "programme": "программа",
    "english": "английский",
    "gpa": "GPA",
    "deadline": "срок подачи",
    "tuition": "плата",
    "scholarship": "стипендия",
}
COUNTRIES = {
    "nu": "Kazakhstan",
    "metu": "Turkey",
    "sabanci": "Turkey",
    "charles": "Czech Republic",
    "masaryk": "Czech Republic",
    "tum": "Germany",
    "tartu": "Estonia",
    "polimi": "Italy",
    "vilnius": "Lithuania",
    "ethz": "Switzerland",
    "psaclay": "France",
    "uppsala": "Sweden",
    "tcd": "Ireland",
    "tsinghua": "China",
    "tec": "Mexico",
    "uba": "Argentina",
    "kaznu": "Kazakhstan",
    "uct": "South Africa",
    "khalifa": "United Arab Emirates",
    "imperial": "United Kingdom",
    "unsw": "Australia",
    "utokyo": "Japan",
    "ntutw": "Taiwan",
    "um": "Malaysia",
    "kuleuven": "Belgium",
    "auckland": "New Zealand",
    "ucph": "Denmark",
    "msu": "Russian Federation",
    "iitd": "India",
    "puc": "Chile",
    "uio": "Norway",
    "usp": "Brazil",
    "ub": "Spain",
    "chula": "Thailand",
}
IELTS_BANDS = ("listening", "reading", "speaking", "writing")
#: Languages an expert may name instead of English.
OTHER_LANGUAGES = tuple(
    "german italian polish czech estonian lithuanian latvian finnish swedish dutch french "
    "spanish turkish korean chinese russian kazakh hungarian portuguese".split()
)
#: Test-score markers; abbreviations are case-sensitive ("sat", "act" are words).
_TEST_ABBR = re.compile(r"\b(SAT|ACT|UNT|ENT|NUET|TOLC?|CEnT|YÖS)\b")
_TEST_WORDS = re.compile(
    r"\b(Unified National Test(ing)?|entrance (test|exam)|aptitude|(?<!grade )points?|Punkte|punkt\w*|"
    r"balas|composite|competitive score|test (score|result)s?)\b",
    re.IGNORECASE,
)
_GRADE_WORDS = re.compile(
    r"\b(GPA|grade point|average|grades?|grading scale|diploma score|certificate results)\b",
    re.IGNORECASE,
)
_GRADE_LETTERS = re.compile(r"\b[A-F]{3}\b|[Ss]core of [A-F]\b")
_INDICATIVE = re.compile(
    r"in past years|indicative|lower boundary|not a fixed minimum|not guaranteed minim",
    re.IGNORECASE,
)
_CYCLE_2026 = re.compile(
    r"\b(this is the|only the|from the previous)\b[^.]{0,40}\b2026\b[^.]{0,25}\bcycle",
    re.IGNORECASE,
)
_HTTP_URL: TypeAdapter[HttpUrl] = TypeAdapter(HttpUrl)


# --------------------------------------------------------------------- loading


def load_drafts(directory: Path) -> list[dict[str, Any]]:
    """Every ``*.json`` in the directory that looks like an expert draft."""
    drafts: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"skip {path.name}: {exc}", file=sys.stderr)
            continue
        if isinstance(data, dict) and data.get("case") and isinstance(data.get("answers"), dict):
            drafts.append(data)
        else:
            print(f"skip {path.name}: not an expert draft", file=sys.stderr)
    return drafts


Report = dict[tuple[str, str], dict[str, Any]]


def load_report(path: Path | None) -> Report | None:
    if path is None:
        return None
    rows = json.loads(path.read_text(encoding="utf-8"))
    return {(str(r.get("case")), str(r.get("item"))): r for r in rows if isinstance(r, dict)}


def verification(report: Report | None, case: str, item: str) -> tuple[bool, str]:
    """(verified, reason when not)."""
    if report is None:
        return False, "no evidence-check report (unchecked)"
    row = report.get((case, item))
    if row is None:
        return False, "no evidence-check row"
    if row.get("official") is not True:
        return False, "source host is not an official domain"
    if row.get("quote_found") is not True:
        return False, f"quote not found on the page (fetch outcome {row.get('outcome') or '-'})"
    return True, ""


# --------------------------------------------------------------------- helpers


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.replace(",", "").strip())
        except ValueError:
            return None
    return None


def _valid_url(url: Any) -> str | None:
    if not isinstance(url, str) or not url.strip():
        return None
    try:
        _HTTP_URL.validate_python(url.strip())
    except ValidationError:
        return None
    return url.strip()


def _short(text: Any, limit: int) -> str:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _number_in(text: str, number: float) -> bool:
    """Whether ``number`` is written in ``text`` (6.5 or 6,5; 7 also as 7.0)."""
    whole = int(number)
    if number == whole:
        pattern = rf"(?<![\d.,]){whole}(?:[.,]0+)?(?![\d])"
    else:
        a, b = f"{number:g}".split(".")
        pattern = rf"(?<![\d.,]){a}[.,]{b}(?![\d])"
    return re.search(pattern, text) is not None


def _same(a: Any, b: Any) -> bool:
    """Value equality with ints and floats compared numerically."""
    if isinstance(a, dict) and isinstance(b, dict):
        return set(a) == set(b) and all(_same(a[k], b[k]) for k in a)
    numeric = (int, float)
    if (
        isinstance(a, numeric)
        and isinstance(b, numeric)
        and not isinstance(a, bool)
        and not isinstance(b, bool)
    ):
        return float(a) == float(b)
    return bool(a == b)


def show(value: Any) -> str:
    """A value as one short line for notes and the worksheet."""
    if value is None:
        return "—"
    if isinstance(value, dict) and set(value) == {"amount", "currency"}:
        amount = _number(value["amount"])
        figure = f"{amount:,.2f}".rstrip("0").rstrip(".") if amount is not None else "?"
        return f"{figure} {value['currency']}"
    if isinstance(value, dict) and value and set(value) <= set(IELTS_BANDS):
        bands = {f"{v:g}" if isinstance(v, int | float) else str(v) for v in value.values()}
        if len(bands) == 1 and len(value) == 4:
            return f"каждая часть ≥ {bands.pop()}"
        return ", ".join(f"{k} {v:g}" for k, v in sorted(value.items()))
    if isinstance(value, bool):
        return "да" if value else "нет"
    if isinstance(value, float):
        return f"{value:g}"
    return _short(value if isinstance(value, str) else json.dumps(value, ensure_ascii=False), 80)


_SLUG_STOP = frozenset(
    "the of for and on in based scholarship scholarships stipendium stypendium stipendija "
    "university universiteto school student students international undergraduate award "
    "awards".split()
)


def slugify(name: str) -> str:
    """An award id in the binding-key style (``nanyang_global``, ``kaist``)."""
    abbreviation = re.search(r"\(([A-Z]{2,8})\)", name)
    if abbreviation:
        return abbreviation.group(1).lower()
    head = re.split(r"\s[(—–-]\s?|\(|,|/", name, maxsplit=1)[0]
    ascii_text = unicodedata.normalize("NFKD", head).encode("ascii", "ignore").decode()
    words = [
        w
        for w in re.findall(r"[a-z0-9]+", ascii_text.lower())
        if w not in _SLUG_STOP and len(w) > 1
    ]
    slug = "_".join(words[:4]) or "award"
    return slug if slug[0].isalpha() else "award_" + slug


def requested_year(request: dict[str, Any]) -> int | None:
    match = re.search(r"\b(20\d\d)\b", str(request.get("intake") or ""))
    return int(match.group(1)) if match else None


def academic_year_matches(text: Any, start: int) -> bool:
    """Whether the stated academic year *is* ``start``/``start+1`` (2027/28, 2027-2028)."""
    nxt = start + 1
    pattern = rf"\s*{start}\s*[/-]\s*(?:{nxt}|{str(nxt)[2:]})\b"
    return re.match(pattern, str(text or "")) is not None


# ------------------------------------------------------------------ proposals


@dataclass
class Proposal:
    """One corpus label an expert item proposes, before the merge.

    ``display`` is the worksheet's short Russian rendering when the value
    alone does not say it (an N/A reason, why a value stayed unknown).
    """

    key: str
    status: str
    value: Any = None
    notes: str = ""
    evidence: dict[str, Any] | None = None
    display: str = ""
    #: What the expert offered, kept when verification downgraded it to unknown,
    #: so that a disagreement with a signed value is still reported.
    original: Proposal | None = None


@dataclass
class Item:
    """One expert answer turned into labels, with its verification."""

    case: str
    question: str
    proposals: list[Proposal]
    verified: bool
    offered: bool
    url: str | None
    quote: str


@dataclass
class Row:
    """One worksheet line."""

    group: str  # conflict | addition | heldout
    university: str
    question: str
    value: str
    quote: str
    url: str | None
    verified: bool
    old_url: str | None = None


@dataclass
class CaseResult:
    case: dict[str, Any]
    rows: list[Row] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    statuses: Counter[str] = field(default_factory=Counter)
    verified: int = 0
    conflicts: int = 0


#: Scope dimensions a label's evidence carries. The signed corpus records
#: what the page itself states, which for a core answer is the university and
#: the degree; the request's field and intake are what we asked, not what the
#: page answered, and the scorer compares every set dimension literally (a
#: label scoped to "fall 2027" made a correct NTU claim read as wrong scope).
LABEL_SCOPE_KEYS = ("university", "degree")


def label_scope(scope: dict[str, Any]) -> dict[str, Any]:
    """The request scope reduced to LABEL_SCOPE_KEYS; every other dimension None."""
    return {k: (v if k in LABEL_SCOPE_KEYS else None) for k, v in scope.items()}


def evidence(
    url: str, quote: str, scope: dict[str, Any], accessed_on: str, **extra: Any
) -> dict[str, Any]:
    """One Evidence entry in the schema's exact shape."""
    excerpt = re.sub(r"\s+", " ", quote).strip()
    truncated = len(excerpt) > 600
    return {
        "url": url,
        "excerpt": excerpt[:599] + "…" if truncated else excerpt,
        "scope": {**scope, **{k: v for k, v in extra.items() if v is not None}},
        "accessed_on": accessed_on,
        "source_type": "official",
        "excerpt_truncated": truncated,
    }


def _expert_note(answer: dict[str, Any]) -> str:
    note = _short(answer.get("notes"), 300)
    return f"Expert ({DRAFT_DATE}): {note}" if note else f"Expert draft {DRAFT_DATE}."


def other_language(value: Any) -> str | None:
    """The non-English language an English answer actually names, if any."""
    if not isinstance(value, dict):
        return None
    if any(_number(value.get(k)) is not None for k in ("ielts_overall", "toefl_ibt", "duolingo")):
        return None
    for key, item in value.items():
        lowered = key.lower()
        for lang in OTHER_LANGUAGES:
            if lowered.startswith(lang):
                details = "; ".join(
                    f"{k}={_short(v, 80)}" for k, v in value.items() if k.lower().startswith(lang)
                )
                return f"{lang.title()} ({details})"
        if lowered == "language" and isinstance(item, str) and item.lower() != "english":
            return f"{item.strip()} (no English requirement published)"
    match = re.search(r"taught in (\w+)", json.dumps(value, ensure_ascii=False))
    if match and match.group(1).lower() in OTHER_LANGUAGES:
        return f"{match.group(1)} (programme taught in {match.group(1)})"
    return None


def propose_english(answer: dict[str, Any], ev: dict[str, Any] | None) -> list[Proposal]:
    status = answer.get("status")
    value = answer.get("value")
    note = _expert_note(answer)
    if status not in {"known", "not_applicable"} or ev is None:
        return [Proposal("ielts.overall", "unknown", notes="Expert did not establish it. " + note)]
    language = other_language(value)
    no_test = isinstance(value, dict) and (
        value.get("language_test_required") is False
        or (value.get("english_test_required") is False and language is None)
    )
    if status == "not_applicable" or language or no_test:
        reason = (
            f"Not an English requirement: the language requirement is {language}."
            if language
            else "No English language test result is required for this route."
        )
        shown = f"н/п: язык {language.split(' (')[0]}" if language else "н/п: тест не нужен"
        return [
            Proposal("ielts.overall", "not_applicable", None, f"{reason} {note}", ev, shown),
            Proposal("ielts.subscores", "not_applicable", None, reason, ev, shown),
        ]
    if not isinstance(value, dict):
        return [Proposal("ielts.overall", "unknown", notes=f"Unreadable expert value. {note}")]
    quote = ev["excerpt"]
    out: list[Proposal] = []

    def quoted(key: str, numbers: list[float], render: Any, lead: str = "") -> None:
        if all(_number_in(quote, n) for n in numbers):
            out.append(Proposal(key, "known", render, (lead + " " + note).strip(), ev))
        else:
            out.append(
                Proposal(
                    key,
                    "unknown",
                    notes=f"expert value {show(render)} is not in the quoted excerpt. {note}",
                    display=f"{show(render)} — нет в цитате",
                )
            )

    refused = value.get("ielts_accepted") is False or str(
        value.get("ielts", "")
    ).lower().startswith("not")
    overall = _number(value.get("ielts_overall"))
    if overall is not None:
        quoted("ielts.overall", [overall], overall)
    elif refused:
        out.append(
            Proposal(
                "ielts.overall",
                "not_applicable",
                None,
                "IELTS is not accepted; English is shown by other tests. " + note,
                ev,
                "н/п: IELTS не принимают",
            )
        )
    else:
        out.append(Proposal("ielts.overall", "unknown", notes="No IELTS figure given. " + note))
    floor = _number(value.get("ielts_min_section"))
    bands = {b: _number(value.get(f"ielts_{b}")) for b in IELTS_BANDS}
    stated = {b: v for b in IELTS_BANDS if (v := bands[b] if bands[b] is not None else floor)}
    if stated:
        quoted("ielts.subscores", list(stated.values()), stated)
    toefl = _number(value.get("toefl_ibt"))
    if toefl is not None and 0 < toefl <= 120:
        quoted("english_evidence.toefl_ibt.minimum", [toefl], int(toefl), "TOEFL iBT, 0-120.")
    duolingo = _number(value.get("duolingo"))
    if duolingo is not None and 10 <= duolingo <= 160:
        quoted("english_evidence.duolingo.minimum", [duolingo], int(duolingo), "Duolingo total.")
    return out


def gpa_kind(answer: dict[str, Any]) -> str:
    """grade | test | indicative | unclear: what the expert's threshold is.

    The quote decides first (it is the evidence); the expert's own metadata
    only when the quote is silent, e.g. a quote in Polish or Lithuanian.
    """
    value = answer.get("value")
    quote = str(answer.get("quote") or "")
    meta = ""
    if isinstance(value, dict):
        meta = " ".join(
            str(value.get(k) or "")
            for k in ("type", "metric", "exam", "unit", "scale", "value_meaning", "description")
        )
    elif isinstance(value, str):
        meta = value
    if _INDICATIVE.search(quote) or _INDICATIVE.search(meta):
        return "indicative"
    for text in (quote, meta):
        if _TEST_ABBR.search(text) or _TEST_WORDS.search(text):
            return "test"
        if _GRADE_WORDS.search(text) or _GRADE_LETTERS.search(text):
            return "grade"
    return "unclear"


def gpa_value(value: Any) -> str | None:
    """The threshold as a string description ("70 (percent ...)", "BBB ...")."""
    if isinstance(value, str):
        return value.strip() or None
    if not isinstance(value, dict):
        return None
    inner = value.get("value")
    if isinstance(inner, str) and inner.strip():
        return inner.strip()
    number = _number(inner)
    if number is None:
        return None
    unit = value.get("unit") or value.get("scale")
    return f"{number:g} ({unit})" if unit else f"{number:g}"


def propose_gpa(answer: dict[str, Any], ev: dict[str, Any] | None) -> list[Proposal]:
    status = answer.get("status")
    value = answer.get("value")
    description = _short(value.get("description") if isinstance(value, dict) else value, 350)
    note = _expert_note(answer)
    if status not in {"known", "not_applicable"} or ev is None:
        return [Proposal("gpa", "unknown", notes="Expert did not establish it. " + note)]
    if status == "not_applicable":
        reason = description or "No grade threshold is published."
        return [Proposal("gpa", "not_applicable", None, reason, ev, "н/п: порога нет")]
    kind = gpa_kind(answer)
    if kind == "test":
        threshold = gpa_value(value) or "?"
        return [
            Proposal(
                "gpa",
                "not_applicable",
                None,
                "No grade/GPA threshold on the school record; the published threshold is a "
                f"test or points score, not a GPA: {description}",
                ev,
                f"н/п: порог теста {_short(threshold, 30)}",
            )
        ]
    if kind == "indicative":
        return [
            Proposal(
                "gpa",
                "unknown",
                notes="Expert gives an indicative/expected figure, not a published minimum: "
                + description,
                display="ориентир, не минимум",
            )
        ]
    rendered = gpa_value(value)
    if kind == "grade" and rendered:
        return [Proposal("gpa", "known", rendered, description or note, ev)]
    return [
        Proposal(
            "gpa",
            "unknown",
            notes=f"Could not classify the threshold: {description}",
            display="не классифицировано",
        )
    ]


def propose_deadline(
    answer: dict[str, Any], ev: dict[str, Any] | None, researched_on: date
) -> list[Proposal]:
    note = _expert_note(answer)
    if answer.get("status") != "known" or ev is None:
        return [Proposal("deadline", "unknown", notes="Expert did not establish it. " + note)]
    raw = str(answer.get("value") or "").strip()
    try:
        day = date.fromisoformat(raw)
    except ValueError:
        return [Proposal("deadline", "unknown", notes=f"Not a YYYY-MM-DD date: {raw!r}. {note}")]
    if day < researched_on or _CYCLE_2026.search(str(answer.get("notes") or "")):
        return [
            Proposal(
                "deadline",
                "unknown",
                notes=f"only the 2026 cycle is published (expert value {raw}). {note}",
                display=f"только цикл 2026 ({raw})",
            )
        ]
    if str(day.year) not in ev["excerpt"]:
        return [
            Proposal(
                "deadline",
                "unknown",
                notes="The quoted date carries no year; a deadline written without a year is "
                f"not dated (expert value {raw}). {note}",
                display=f"{raw} — год не напечатан",
            )
        ]
    return [Proposal("deadline", "known", raw, note, ev)]


def propose_tuition(
    answer: dict[str, Any], ev: dict[str, Any] | None, start_year: int | None
) -> list[Proposal]:
    note = _expert_note(answer)
    value = answer.get("value")
    if answer.get("status") != "known" or ev is None or not isinstance(value, dict):
        return [Proposal("tuition", "unknown", notes="Expert did not establish it. " + note)]
    amount = _number(value.get("amount"))
    currency = str(value.get("currency") or "").upper()
    year = value.get("academic_year")
    period = str(value.get("period") or "year").lower()
    if amount is None or not re.fullmatch(r"[A-Z]{3}", currency):
        return [
            Proposal(
                "tuition",
                "unknown",
                notes=f"No single amount and currency. {note}",
                display="нет одной суммы",
            )
        ]
    shown = show({"amount": amount, "currency": currency})
    if start_year is None or not academic_year_matches(year, start_year):
        published = _short(year, 80) or "not stated"
        wanted = f"{start_year}/{str((start_year or 0) + 1)[2:]}"
        stated = re.match(r"\s*(20\d\d(?:\s*[/-]\s*\d{2,4})?)", str(year or ""))
        label = stated.group(1) if stated else "год не указан"
        return [
            Proposal(
                "tuition",
                "unknown",
                notes=f"only the {published} fee is published, not {wanted} "
                f"(expert value {shown} per {period}). {note}",
                display=f"только {label} ({shown}/{period})",
            )
        ]
    if period not in {"year", "annual", "per year", "academic year"}:
        return [
            Proposal(
                "tuition",
                "unknown",
                notes=f"The figure is per {period}; the corpus records a yearly amount "
                f"(expert value {shown}). {note}",
                display=f"{shown} за {period}",
            )
        ]
    scoped = {
        **ev,
        "scope": {
            **ev["scope"],
        },
    }
    return [Proposal("tuition", "known", {"amount": amount, "currency": currency}, note, scoped)]


def award_slug(
    case_domain: str, name: str, url: str | None, identities: IdentityMap
) -> tuple[str, bool]:
    """(``scholarships.<slug>``, whether this exact source and name is already bound)."""
    if url:
        bound = identities.resolve("award", url, name)
        if bound:
            return bound, True
    folded = name.casefold()
    for b in identities.bindings:
        host = (b.source_url.host or "").lower()
        same_site = host == case_domain or host.endswith("." + case_domain)
        if b.kind == "award" and same_site and folded.startswith(b.subject.casefold()):
            return b.key, False
    return "scholarships." + slugify(name), False


def propose_scholarship(
    exists: dict[str, Any],
    intl: dict[str, Any],
    ev_exists: dict[str, Any] | None,
    ev_intl: dict[str, Any] | None,
    case_domain: str,
    identities: IdentityMap,
    *,
    none_statement: bool = False,
) -> tuple[list[Proposal], list[Proposal], dict[str, Any] | None, str]:
    """(exists proposals, international proposals, new binding, case note).

    ``none_statement`` (the KB builder only, ``kb_build``): an expert
    ``not_applicable`` with a URL and a quote becomes one ``not_applicable``
    proposal of the key ``scholarships`` ("no institutional scholarship for
    this applicant"), verified like any fact. The dataset converters leave it
    False and write no scholarship keys, only the case note, as before.
    """
    status = exists.get("status")
    if status == "not_applicable" and none_statement and ev_exists:
        reason = "No institutional scholarship for incoming bachelor applicants. " + _expert_note(
            exists
        )
        return (
            [Proposal("scholarships", "not_applicable", None, reason, ev_exists, "н/п")],
            [],
            None,
            "",
        )
    if status == "not_applicable":
        return (
            [],
            [],
            None,
            "Expert: no university scholarship for incoming bachelor applicants "
            f"({_short(exists.get('notes'), 200)}); no scholarship keys written.",
        )
    value = exists.get("value")
    name = value.get("name") if isinstance(value, dict) else value
    if status != "known" or not isinstance(name, str) or not name.strip():
        return [], [], None, "Expert did not establish a scholarship; no scholarship keys written."
    name = name.strip()
    url = _valid_url(exists.get("url"))
    prefix, bound = award_slug(case_domain, name, url, identities)
    binding = None
    if url and not bound:
        binding = {
            "kind": "award",
            "source_url": url,
            "subject": name,
            "key": prefix,
            "notes": BINDING_NOTE,
        }
    note = _expert_note(exists)
    exists_p = (
        [Proposal(prefix + ".exists", "known", True, f"{name}. {note}", ev_exists)]
        if ev_exists
        else [Proposal(prefix + ".exists", "unknown", notes="No URL or quote. " + note)]
    )
    key = prefix + ".applicability.international"
    inote = _expert_note(intl)
    istatus, ivalue = intl.get("status"), intl.get("value")
    if istatus == "known" and isinstance(ivalue, bool) and ev_intl:
        intl_p = [Proposal(key, "known", ivalue, inote, ev_intl)]
    elif istatus == "not_applicable" and ev_intl:
        intl_p = [Proposal(key, "not_applicable", None, inote, ev_intl, "н/п")]
    else:
        intl_p = [Proposal(key, "unknown", notes="Expert did not establish it. " + inote)]
    return exists_p, intl_p, binding, ""


def unverify(p: Proposal, reason: str) -> Proposal:
    """A known/N-A proposal without a passing evidence check becomes unknown."""
    if p.status == "unknown":
        return p
    shown = show(p.value) if p.status == "known" else "not_applicable"
    return Proposal(
        p.key,
        "unknown",
        None,
        f"expert value {shown} unverified: {reason}. {p.notes}".strip(),
        display=f"{p.display or show(p.value)} (не проверено)",
        original=p,
    )


def items_for(
    draft: dict[str, Any],
    scope: dict[str, Any],
    domain: str,
    identities: IdentityMap,
    report: Report | None,
    *,
    none_statement: bool = False,
) -> tuple[list[Item], dict[str, Any] | None, str]:
    """Every expert answer of one draft as Items, the new binding, a case note.

    ``none_statement`` is ``propose_scholarship``'s (the KB builder only).
    """
    case = str(draft["case"])
    answers = draft.get("answers") or {}
    accessed = str(draft.get("researched_on") or DRAFT_DATE)
    try:
        researched_on = date.fromisoformat(accessed)
    except ValueError:
        researched_on, accessed = date.fromisoformat(DRAFT_DATE), DRAFT_DATE

    def ev(answer: dict[str, Any]) -> dict[str, Any] | None:
        url, quote = _valid_url(answer.get("url")), str(answer.get("quote") or "").strip()
        return evidence(url, quote, label_scope(scope), accessed) if url and quote else None

    def get(item: str) -> dict[str, Any]:
        answer = answers.get(item)
        return answer if isinstance(answer, dict) else {"status": "unknown"}

    out: list[Item] = []

    def add(question: str, item: str, answer: dict[str, Any], props: list[Proposal]) -> None:
        verified, reason = verification(report, case, item)
        offered = answer.get("status") in {"known", "not_applicable"}
        if not verified:
            props = [unverify(p, reason) for p in props]
        out.append(
            Item(
                case,
                question,
                props,
                verified and offered,
                offered,
                _valid_url(answer.get("url")),
                str(answer.get("quote") or ""),
            )
        )

    english, gpa = get("english"), get("gpa")
    deadline, tuition = get("deadline"), get("tuition")
    add("english", "english", english, propose_english(english, ev(english)))
    add("gpa", "gpa", gpa, propose_gpa(gpa, ev(gpa)))
    add("deadline", "deadline", deadline, propose_deadline(deadline, ev(deadline), researched_on))
    add("tuition", "tuition", tuition, propose_tuition(tuition, ev(tuition), requested_year(scope)))
    exists, intl = get("scholarship_exists"), get("scholarship_international")
    ex_p, in_p, binding, note = propose_scholarship(
        exists, intl, ev(exists), ev(intl), domain, identities, none_statement=none_statement
    )
    if ex_p:
        add("scholarship", "scholarship_exists", exists, ex_p)
        if in_p:
            add("scholarship", "scholarship_international", intl, in_p)
    return out, binding, note


def programme_item(
    draft: dict[str, Any], scope: dict[str, Any], report: Report | None
) -> Item | None:
    programme = draft.get("programme") or {}
    url = _valid_url(programme.get("url"))
    title = _short(programme.get("title"), 300)
    if not url or not title:
        return None
    verified, _ = verification(report, str(draft["case"]), "programme")
    accessed = str(draft.get("researched_on") or DRAFT_DATE)
    ev = evidence(url, title, {**label_scope(scope), "programme": title}, accessed)
    return Item(
        str(draft["case"]),
        "programme",
        [Proposal("programme", "known", True, "", ev)],
        verified,
        True,
        url,
        title,
    )


# ----------------------------------------------------------------------- merge


def short_key(key: str) -> str:
    if key == "ielts.overall":
        return "IELTS"
    if key == "ielts.subscores":
        return "части"
    if key.startswith("english_evidence."):
        return {"toefl_ibt": "TOEFL", "duolingo": "DET"}.get(key.split(".")[1], key.split(".")[1])
    if key.endswith(".applicability.international"):
        return "иностранцам"
    if key.startswith("scholarships."):
        return key.split(".")[1]
    return ""


def row_value(labels: list[Proposal]) -> str:
    parts = []
    for p in labels:
        if p.status == "known":
            text = show(p.value)
        else:
            text = p.display or ("н/п" if p.status == "not_applicable" else "неизвестно")
        name = short_key(p.key)
        parts.append(f"{name} {text}" if name else text)
    return "; ".join(parts)


def _new_label(p: Proposal) -> dict[str, Any]:
    return {
        "key": p.key,
        "status": p.status,
        "value": p.value,
        "evidence": [p.evidence] if p.evidence and p.status != "unknown" else [],
        "critical": True,
        "notes": p.notes or f"Expert draft {DRAFT_DATE}.",
    }


def merge_cohort(
    base: dict[str, Any], items: list[Item], programme: Item | None, case_note: str = ""
) -> CaseResult:
    """reviewed9 case + expert labels, never overwriting a signed known value."""
    case = json.loads(json.dumps(base))
    result = CaseResult(case)
    labels: dict[str, dict[str, Any]] = {label["key"]: label for label in case["labels"]}
    order = [label["key"] for label in case["labels"]]
    changed = False
    for item in items:
        applied: list[Proposal] = []
        for p in item.proposals:
            old = labels.get(p.key)
            offered = p.original or p
            if old is not None and old["status"] == "known":
                result.statuses["known"] += 1  # the draft keeps the signed value
                if offered.status == "unknown" or (
                    offered.status == "known" and _same(old["value"], offered.value)
                ):
                    continue
                result.conflicts += 1
                old_url = old["evidence"][0]["url"] if old["evidence"] else None
                new_text = show(offered.value) if offered.status == "known" else offered.status
                result.notes.append(
                    f"CONFLICT {p.key}: reviewed9 {show(old['value'])} ({old_url}) kept; "
                    f"expert {new_text} ({item.url}), "
                    f"{'verified' if item.verified else 'unverified'}."
                )
                result.rows.append(
                    Row(
                        "conflict",
                        case["university"],
                        f"{QUESTION_RU[item.question]} {short_key(p.key)}".strip(),
                        f"было {show(old['value'])} → эксперт {new_text}",
                        item.quote,
                        item.url,
                        item.verified,
                        old_url,
                    )
                )
                continue
            if old is not None and old["status"] == "not_applicable" and p.status != "known":
                # A signed N/A is replaced only by a verified known value; an
                # unverified one is reported, never applied.
                result.statuses["not_applicable"] += 1
                if offered.status == "known":
                    result.rows.append(
                        Row(
                            "conflict",
                            case["university"],
                            f"{QUESTION_RU[item.question]} {short_key(p.key)}".strip(),
                            f"было н/п → эксперт {show(offered.value)}",
                            item.quote,
                            item.url,
                            item.verified,
                            old["evidence"][0]["url"] if old["evidence"] else None,
                        )
                    )
                    result.conflicts += 1
                    result.notes.append(
                        f"CONFLICT {p.key}: reviewed9 not_applicable kept; expert "
                        f"{show(offered.value)} ({item.url}), unverified."
                    )
                continue
            result.statuses[p.status] += 1
            if old is not None and p.status == "unknown":
                p = Proposal(
                    p.key,
                    "unknown",
                    None,
                    f"{p.notes} | reviewed9: {old['notes']}",
                    None,
                    p.display,
                )
            new = _new_label(p)
            if old == new:
                continue
            labels[p.key] = new
            if p.key not in order:
                order.append(p.key)
            if item.offered:
                applied.append(p)
            changed = True
        if applied:
            result.rows.append(
                Row(
                    "addition",
                    case["university"],
                    QUESTION_RU[item.question],
                    row_value(applied),
                    item.quote,
                    item.url,
                    item.verified,
                )
            )
    if programme is not None and programme.url:
        listed = {canonical_url(u) for u in case["programme_urls"]}
        if canonical_url(programme.url) not in listed:
            ev = programme.proposals[0].evidence
            if programme.verified and ev:
                case["programme_urls"].append(programme.url)
                case["programme_evidence"].append(ev)
                case["programme_status"] = "known"
                changed = True
            else:
                result.notes.append(f"Expert programme page {programme.url} unverified; not added.")
            result.rows.append(
                Row(
                    "addition",
                    case["university"],
                    QUESTION_RU["programme"],
                    "новый адрес" + ("" if programme.verified else " (не проверено)"),
                    programme.quote,
                    programme.url,
                    programme.verified,
                )
            )
    if case_note:
        result.notes.append(case_note)
    case["labels"] = [labels[k] for k in order]
    result.verified = sum(1 for i in items if i.verified)
    if changed or result.notes:
        signed = base["review"]
        case["review"] = {
            "status": "draft",
            "prepared_by": PREPARED_BY,
            "reviewer": None,
            "verified_on": None,
            "notes": (
                f"draft10 ({DRAFT_DATE}): core-question labels from independent expert drafts, "
                f"listed in docs/process/SIGN_CORE_{DRAFT_DATE}.md; unsigned. The reviewed9 "
                f"signature ({signed.get('reviewer')}, {signed.get('verified_on')}) covers the "
                "case's other labels. " + " ".join(result.notes)
            ).strip(),
        }
    return result


def build_heldout(
    draft: dict[str, Any],
    case_id: str,
    scope: dict[str, Any],
    items: list[Item],
    programme: Item | None,
    case_note: str,
) -> CaseResult:
    """A complete draft Case with labels for the core keys only."""
    result = CaseResult({})
    labels: dict[str, dict[str, Any]] = {}
    for item in items:
        for p in item.proposals:
            labels[p.key] = _new_label(p)
            result.statuses[p.status] += 1
        if item.offered:
            result.rows.append(
                Row(
                    "heldout",
                    scope["university"],
                    QUESTION_RU[item.question],
                    row_value(item.proposals),
                    item.quote,
                    item.url,
                    item.verified,
                )
            )
    split_name, sheet = (
        ("dev3", "DEV3")
        if case_id in DEV3_IDS
        else ("dev2", "DEV2")
        if case_id in DEV2_DOMAINS
        else ("heldout", "CORE")
    )
    notes = [
        f"{split_name} draft1 ({DRAFT_DATE}): core-question labels from one independent expert "
        f"draft, listed in docs/process/SIGN_{sheet}_{DRAFT_DATE}.md; unsigned."
    ]
    if case_note:
        notes.append(case_note)
    urls: list[str] = []
    prog_ev: list[dict[str, Any]] = []
    status = "unknown"
    if programme is not None and programme.url:
        ev = programme.proposals[0].evidence
        if programme.verified and ev:
            urls, prog_ev, status = [programme.url], [ev], "known"
        else:
            notes.append(f"Expert programme page {programme.url} ({programme.quote}) unverified.")
        result.rows.insert(
            0,
            Row(
                "heldout",
                scope["university"],
                QUESTION_RU["programme"],
                _short(programme.quote, 50) + ("" if programme.verified else " (не проверено)"),
                programme.quote,
                programme.url,
                programme.verified,
            ),
        )
    language = (draft.get("programme") or {}).get("teaching_language")
    if language:
        notes.append(f"Teaching language (expert): {_short(language, 120)}.")
    result.case = {
        "id": case_id,
        "dataset_version": other_version(case_id),
        "university": scope["university"],
        "domain": OTHER_DOMAINS[case_id],
        "country": COUNTRIES.get(case_id, "unknown"),
        "site_types": [],
        "request": scope,
        "programme_urls": urls,
        "programme_status": status,
        "programme_evidence": prog_ev,
        "labels": list(labels.values()),
        "review": {
            "status": "draft",
            "prepared_by": PREPARED_BY,
            "reviewer": None,
            "verified_on": None,
            "notes": " ".join(notes),
        },
    }
    result.verified = sum(1 for i in items if i.verified)
    return result


def heldout_scope(draft: dict[str, Any], template: dict[str, Any]) -> dict[str, Any]:
    """The cohort request scope with the heldout university's name."""
    name = re.sub(r"\s*\(.*?\)", "", str(draft.get("university") or "")).split(",")[0].strip()
    return {**template, "university": name or str(draft["case"])}


def merge_rows(rows: list[Row]) -> list[Row]:
    """One line per university and question (exists + international together)."""
    out: list[Row] = []
    for r in rows:
        last = out[-1] if out else None
        if (
            last is not None
            and r.group != "conflict"
            and (last.group, last.university, last.question) == (r.group, r.university, r.question)
        ):
            last.value = f"{last.value}; {r.value}"
            last.verified = last.verified and r.verified
            continue
        out.append(Row(**vars(r)))
    return out


# ------------------------------------------------------------------- worksheet

WORKSHEET_MAX_LINES = 140


def _cell(text: Any, limit: int = 120) -> str:
    return _short(text, limit).replace("|", "\\|")


def _link(url: str | None) -> str:
    if not url:
        return "—"
    host = re.sub(r"^https?://(www\.)?", "", url).split("/")[0]
    return f"[{host}]({url})"


def render_worksheet(
    rows: list[Row], counts: Counter[str], verified: int, conflicts: int, checked: bool
) -> str:
    lines = [
        f"# Подпись шести главных вопросов — {DRAFT_DATE}",
        "",
        "Черновики (ничего не подписано): `ground_truth.draft10.json` (основные), "
        "`heldout.draft1.json` (отложенные), `identity_bindings.draft2.json`.",
        "",
        f"Метки ядра в черновиках (вкл. подписанные ранее): known {counts['known']} · not_applicable {counts['not_applicable']} · "
        f"unknown {counts['unknown']} · проверено {verified} · конфликтов {conflicts}.",
        "Проверка цитат: "
        + ("отчёт verify_evidence приложен." if checked else "**отчёта нет — всё «нет»**."),
        "«нет» = записано как unknown; подпись не делает его known. Подробности — в notes JSON.",
    ]
    header = [
        "| университет | вопрос | значение | цитата | ссылка | проверено |",
        "|---|---|---|---|---|---|",
    ]
    titles = {
        "conflict": "## Основные: конфликты (в черновике оставлено подписанное)",
        "addition": "## Основные: добавления",
        "heldout": "## Отложенные",
    }
    tail = ["", "Подписываю draft10 и heldout1"]
    for group in ("conflict", "addition", "heldout"):
        chosen = [r for r in rows if r.group == group]
        lines += ["", titles[group], ""]
        if not chosen:
            lines.append("нет")
            continue
        lines += header
        for i, r in enumerate(chosen):
            if len(lines) >= WORKSHEET_MAX_LINES - len(tail) - 4:
                lines.append(f"| … | ещё {len(chosen) - i} строк — см. JSON | | | | |")
                break
            link = _link(r.url) + (f"; было {_link(r.old_url)}" if r.old_url else "")
            lines.append(
                f"| {_cell(r.university, 40)} | {_cell(r.question, 30)} | {_cell(r.value, 90)} "
                f"| {_cell(r.quote)} | {link} | {'да' if r.verified else 'нет'} |"
            )
    return "\n".join(lines + tail) + "\n"


# ------------------------------------------------------------------------ run


@dataclass
class Outputs:
    """The JSON as written (validated, not re-serialised: untouched cases stay byte-equal)."""

    cohort: dict[str, Any]
    heldout: dict[str, Any] | None
    bindings: dict[str, Any]
    worksheet: str
    unmapped: list[str]


def build(
    drafts: list[dict[str, Any]],
    reviewed: dict[str, Any],
    identities: IdentityMap,
    report: Report | None,
) -> Outputs:
    """All outputs from the expert drafts, the signed corpus and the bindings."""
    cohort = {c["id"]: c for c in reviewed["cases"]}
    template = dict(reviewed["cases"][0]["request"])
    rows: list[Row] = []
    counts: Counter[str] = Counter()
    verified = conflicts = 0
    new_bindings: list[dict[str, Any]] = []
    heldout_cases: list[dict[str, Any]] = []
    unmapped: list[str] = []
    merged: dict[str, dict[str, Any]] = {}
    known_identities: set[tuple[str, str, str]] = {
        (b.kind, canonical_url(b.source_url), b.subject) for b in identities.bindings
    }
    for draft in sorted(drafts, key=lambda d: str(d["case"])):
        case_id = str(draft["case"])
        if case_id in cohort:
            scope, domain = dict(cohort[case_id]["request"]), cohort[case_id]["domain"]
        elif case_id in OTHER_DOMAINS:
            scope, domain = heldout_scope(draft, template), OTHER_DOMAINS[case_id]
        else:
            unmapped.append(f"{case_id}: not a cohort or heldout case")
            continue
        if case_id in merged or any(c["id"] == case_id for c in heldout_cases):
            unmapped.append(f"{case_id}: duplicate draft ignored")
            continue
        items, binding, note = items_for(draft, scope, domain, identities, report)
        programme = programme_item(draft, scope, report)
        if case_id in cohort:
            res = merge_cohort(cohort[case_id], items, programme, note)
            merged[case_id] = res.case
        else:
            res = build_heldout(draft, case_id, scope, items, programme, note)
            heldout_cases.append(res.case)
        rows += res.rows
        counts += res.statuses
        verified += res.verified
        conflicts += res.conflicts
        if binding:
            identity = ("award", canonical_url(binding["source_url"]), binding["subject"])
            if identity not in known_identities:
                known_identities.add(identity)
                new_bindings.append(binding)
        unmapped += [
            f"{case_id}: answer '{k}' has no corpus mapping"
            for k in draft.get("answers") or {}
            if k not in ITEMS
        ]
    cases = [
        {**merged.get(c["id"], c), "dataset_version": COHORT_VERSION} for c in reviewed["cases"]
    ]
    cohort_data = {"schema_version": "1", "version": COHORT_VERSION, "split": reviewed["split"]}
    cohort_data["cases"] = cases
    Dataset.model_validate(cohort_data)
    heldout_order = list(OTHER_DOMAINS)
    heldout_data: dict[str, Any] | None = None
    if heldout_cases:
        # One output file per run: a dev2-only draft set is the development
        # split, anything else the heldout (validation) split. Mixing the two in
        # one file would let tuning data leak into the validation set.
        ids = {c["id"] for c in heldout_cases}
        if ids <= DEV3_IDS:
            version, split = DEV3_VERSION, DEV2_SPLIT
        elif ids & DEV3_IDS:
            raise ValueError("dev3 drafts must be converted on their own")
        elif ids <= set(DEV2_DOMAINS):
            version, split = DEV2_VERSION, DEV2_SPLIT
        elif ids & set(DEV2_DOMAINS):
            raise ValueError("dev2 and heldout drafts must be converted separately")
        else:
            version, split = HELDOUT_VERSION, HELDOUT_SPLIT
        heldout_data = {
            "schema_version": "1",
            "version": version,
            "split": split,
            "cases": sorted(heldout_cases, key=lambda c: heldout_order.index(c["id"])),
        }
        Dataset.model_validate(heldout_data)
    bindings = {
        "version": BINDINGS_VERSION,
        "bindings": [b.model_dump(mode="json") for b in identities.bindings] + new_bindings,
    }
    IdentityMap.model_validate(bindings)
    rank = {"conflict": 0, "addition": 1, "heldout": 2}
    rows = merge_rows(sorted(rows, key=lambda r: rank[r.group]))
    worksheet = render_worksheet(rows, counts, verified, conflicts, report is not None)
    return Outputs(cohort_data, heldout_data, bindings, worksheet, unmapped)


def _write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    path.write_text(text, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    repo = Path(__file__).resolve().parents[4]
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("drafts", type=Path, help="directory of expert draft JSON files")
    parser.add_argument("--evidence", type=Path, help="verify_evidence.py report (JSON rows)")
    parser.add_argument("--reviewed", type=Path, default=REVIEWED)
    parser.add_argument("--bindings", type=Path, default=BINDINGS)
    parser.add_argument("--out-cohort", type=Path, default=DATA / "ground_truth.draft10.json")
    parser.add_argument("--out-heldout", type=Path, default=DATA / "heldout.draft1.json")
    parser.add_argument("--out-bindings", type=Path, default=DATA / "identity_bindings.draft2.json")
    parser.add_argument(
        "--worksheet", type=Path, default=repo / "docs" / "process" / f"SIGN_CORE_{DRAFT_DATE}.md"
    )
    args = parser.parse_args(argv)
    targets = [args.out_cohort, args.out_heldout, args.out_bindings, args.worksheet]
    if any(".reviewed" in t.name for t in targets):
        parser.error("refusing to write over a signed corpus or binding file")
    drafts = load_drafts(args.drafts)
    if not drafts:
        parser.error(f"no expert drafts in {args.drafts}")
    reviewed = json.loads(args.reviewed.read_text(encoding="utf-8"))
    raw_bindings = json.loads(args.bindings.read_text(encoding="utf-8"))
    identities = IdentityMap.model_validate(raw_bindings)
    out = build(drafts, reviewed, identities, load_report(args.evidence))
    # Signed bindings are copied as written, not re-serialised.
    out.bindings["bindings"][: len(raw_bindings["bindings"])] = raw_bindings["bindings"]
    _write(args.out_cohort, out.cohort)
    if out.heldout is not None:
        _write(args.out_heldout, out.heldout)
    _write(args.out_bindings, out.bindings)
    _write(args.worksheet, out.worksheet)
    for line in out.unmapped:
        print("unmapped:", line, file=sys.stderr)
    print(
        f"drafts={len(drafts)} cohort={len(out.cohort['cases'])} "
        f"heldout={len(out.heldout['cases']) if out.heldout else 0} "
        f"bindings={len(out.bindings['bindings'])} "
        f"worksheet_lines={len(out.worksheet.splitlines())}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
