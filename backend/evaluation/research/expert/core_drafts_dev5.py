"""dev5 expert drafts -> ``dev5.draft1.json`` and its identity bindings.

dev5 is the second set of country proxies for the heldout nine (thirteen
universities, ``live.DEV5_DOMAINS``). Unlike dev4, its programme pages and its
six core questions arrive together, so draft1 carries both:

* **Programme rows** come from ``programme_drafts_dev5.<date>/``: one file per
  page, the quote in the ``title`` slot. A page counts only when the CI
  ``scripts/verify_evidence.py`` report has its case and URL with ``official``
  and ``quote_found``. The file's role (its name's suffix) says what the page
  is: ``local``/``twin``/``site``/``department`` a page of the programme,
  ``language`` a language-of-instruction quote (kept in the notes),
  ``related`` a related programme. A twin whose quote the check could not find
  is kept as a URL of the programme (never as evidence) when the local page of
  the same case is verified, and the note says so.
* **Related cases** (``RELATED``): no bachelor titled computer science; the
  closest programme is labelled as related, as dev4 did for boun/itu
  (``programme_status`` unknown, its pages in ``related_programme_urls``,
  ``programme.exists`` known on their evidence). Owner rulings are open.
* **Access cases** (``ACCESS``): the site could not be read (robots.txt
  unreachable over TLS), so ``programme_status`` and ``programme.exists`` stay
  unknown and only the expert's related pages are kept.
* **Core labels** are ``core_drafts_dev4.build`` (``core_drafts.items_for``'s
  rules), against the CI report of the core drafts.

Run from ``backend``::

    python -m evaluation.research.expert.core_drafts_dev5 \\
        evaluation/research/expert/data/programme_drafts_dev5.2026-10-19 \\
        evaluation/research/expert/data/core_drafts_dev5.2026-10-19
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from ..identities import IdentityMap
from ..live import DEV5_DOMAINS, dev2_entry
from ..metrics import canonical_url
from .core_drafts import DATA, evidence, load_drafts, load_report
from .core_drafts import DRAFT_DATE as CORE_DRAFT_DATE
from .core_drafts_dev4 import build as build_core

DRAFT_DATE = "2026-10-19"
VERSION = f"{DRAFT_DATE}.dev5-draft1"
OUT = DATA / "dev5.draft1.json"
OUT_BINDINGS = DATA / "identity_bindings.dev5-draft1.json"
EVIDENCE = f"evidence_check.ci-{DRAFT_DATE}.json"
SIGN = f"docs/process/SIGN_DEV5_{DRAFT_DATE}.md"

#: Case -> country, in the spelling dev4 uses.
COUNTRIES = {
    "kbtu": "Kazakhstan",
    "satbayev": "Kazakhstan",
    "aitu": "Kazakhstan",
    "hacettepe": "Türkiye",
    "bilkent": "Türkiye",
    "ytu": "Türkiye",
    "upol": "Czechia",
    "zcu": "Czechia",
    "tud": "Germany",
    "lmu": "Germany",
    "unipd": "Italy",
    "sapienza": "Italy",
    "vilniustech": "Lithuania",
}
#: No bachelor titled computer science: the closest programme is related
#: (owner rulings open in SIGN_DEV5: Turkish computer engineering, VILNIUS
#: TECH Information Technologies).
RELATED = frozenset({"hacettepe", "bilkent", "ytu", "vilniustech"})
#: Sites the checker could not read (robots.txt unreachable: TLS chain without
#: its intermediate). Recorded as access cases.
ACCESS = frozenset({"kbtu", "satbayev"})
PROGRAMME_ROLES = frozenset({"local", "twin", "site", "department"})

_BOILERPLATE = re.compile(r"^dev5 [\w.-]+: programme-page item only.*?word for word\.?\s*")

Verified = dict[tuple[str, str], tuple[bool, str]]


def load_programme_report(path: Path) -> Verified:
    """(case, canonical url) -> (verified, reason). One page may have several rows."""
    out: Verified = {}
    for row in json.loads(path.read_text(encoding="utf-8")):
        if row.get("item") != "programme" or not row.get("url"):
            continue
        key = (str(row["case"]), canonical_url(str(row["url"])))
        ok = row.get("official") is True and row.get("quote_found") is True
        reason = (
            ""
            if ok
            else "source host is not an official domain"
            if row.get("official") is not True
            else f"quote not found on the page (fetch outcome {row.get('outcome') or '-'}"
            + (f": {row['note']}" if row.get("note") else "")
            + ")"
        )
        previous = out.get(key)
        if previous is None or (previous[0] and not ok):
            out[key] = (ok, reason)
    return out


def load_programme_drafts(directory: Path) -> dict[str, list[tuple[str, dict[str, Any]]]]:
    """Case -> [(role, draft)] in file order (``<case>.<n>-<role>.json``)."""
    out: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    for path in sorted(directory.glob("*.json")):
        match = re.fullmatch(r"([a-z]+)\.\d+-([a-z]+)\.json", path.name)
        if not match:
            continue
        draft = json.loads(path.read_text(encoding="utf-8"))
        out.setdefault(match[1], []).append((match[2], draft))
    return out


def _note(draft: dict[str, Any]) -> str:
    return _BOILERPLATE.sub("", str(draft.get("note") or "")).strip()


def programme_case(
    case_id: str,
    pages: list[tuple[str, dict[str, Any]]],
    core: dict[str, Any] | None,
    verified: Verified,
) -> dict[str, Any]:
    """One dev5 case with its programme rows (``programme.exists`` only)."""
    entry = dev2_entry(case_id)
    university = entry["name"]
    request = {
        "university": university,
        "programme": None,
        "degree": "bachelor",
        "field": "computer science",
        "intake": "fall 2027",
        "population": None,
        "qualification": None,
        "academic_year": None,
    }
    label_scope = {**request, "field": None, "intake": None}
    core_programme = (core or {}).get("programme") or {}
    core_url = core_programme.get("page_url") or core_programme.get("url")
    first = pages[0][1] if pages else {}

    urls: list[str] = []
    page_evidence: list[dict[str, Any]] = []
    label_evidence: list[dict[str, Any]] = []
    remarks: list[str] = []
    local_ok = False
    for role, draft in pages:
        programme = draft.get("programme") or {}
        url, quote = str(programme.get("url") or ""), str(programme.get("title") or "")
        if not url or not quote:
            continue
        ok, reason = verified.get((case_id, canonical_url(url)), (False, "no evidence-check row"))
        if role == "language":
            remarks.append(
                f"Language of instruction quoted: '{quote}' ({url}; "
                + ("verified by the CI evidence check)." if ok else f"not verified: {reason}).")
            )
            continue
        if role == "related" or case_id in ACCESS:
            continue
        if role == "local":
            local_ok = ok
        if not ok:
            if role == "twin" and local_ok and url not in urls:
                urls.append(url)
                remarks.append(
                    f"Twin {url} kept as a URL of the programme, not as evidence: its quote "
                    f"'{quote}' was not verified ({reason})."
                )
            else:
                remarks.append(f"Page {url} left out: quote '{quote}' not verified ({reason}).")
            continue
        if url not in urls:
            urls.append(url)
        title = core_programme.get("title") if core_url and url == core_url else None
        page_evidence.append(evidence(url, quote, {**label_scope, "programme": title}, DRAFT_DATE))
        if not any(e["url"] == url for e in label_evidence):
            label_evidence.append(evidence(url, quote, label_scope, DRAFT_DATE))

    related_listed = [str(u) for u in first.get("related_programme_urls") or []]
    case_note = _note(first)
    details = [
        f"{name}: {str(core_programme[key]).rstrip('.')}."
        for key, name in (
            ("degree", "Degree"),
            ("teaching_language", "Language of instruction"),
            ("how_found", "How found"),
            ("notes", "Expert"),
        )
        if core_programme.get(key) and str(core_programme[key]) not in case_note
    ]
    review: list[str] = []
    if case_id in ACCESS:
        status, related, exists = "unknown", related_listed, None
        review.append(
            "ACCESS CASE: the site could not be read (robots.txt unreachable: the server sends "
            "its TLS leaf certificate without the intermediate; RFC 9309 treats the whole site "
            "as disallowed), so programme_status and every core question stay unknown; only "
            "the expert's related pages (from a search index, not opened) are kept."
        )
    elif case_id in RELATED:
        status, related, exists = "unknown", urls, bool(label_evidence)
        urls = []
        review.append(
            "No bachelor titled computer science: the closest programme is labelled as a "
            "related programme (owner ruling open in the sign-off table)."
        )
    else:
        status = "known" if label_evidence else "unknown"
        related, exists = related_listed, bool(label_evidence)
        if related_listed:
            review.append(
                "Related programmes listed by the expert (not opened by the CI check): "
                + ", ".join(related_listed)
                + "."
            )
    label: dict[str, Any] = {
        "key": "programme.exists",
        "status": "known" if exists else "unknown",
        "value": True if exists else None,
        "evidence": label_evidence if exists else [],
        "critical": True,
        "notes": " ".join(
            part
            for part in (
                "Programme page only." if exists else "Programme page not verified: unknown.",
                case_note,
                *details,
                *remarks,
            )
            if part
        ),
    }
    case: dict[str, Any] = {
        "id": case_id,
        "dataset_version": VERSION,
        "university": university,
        "domain": DEV5_DOMAINS[case_id],
        "country": COUNTRIES[case_id],
        "site_types": [],
        "request": request,
        "programme_urls": urls if status == "known" else [],
        "programme_status": status,
        "programme_evidence": page_evidence if case_id not in ACCESS else [],
        "labels": [label],
        "review": {
            "status": "draft",
            "prepared_by": "expert pass (dev5 country proxies)",
            "reviewer": None,
            "verified_on": None,
            "notes": " ".join(review),
        },
    }
    if related:
        case["related_programme_urls"] = related
    return case


def build(
    programme_dir: Path, core_dir: Path
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    """(dataset, bindings, worksheet rows) for dev5.draft1."""
    pages = load_programme_drafts(programme_dir)
    cores = {str(d["case"]): d for d in load_drafts(core_dir)}
    verified = load_programme_report(programme_dir / EVIDENCE)
    base = {
        "schema_version": "1",
        "version": VERSION,
        "split": "development",
        "cases": [
            programme_case(case_id, pages.get(case_id, []), cores.get(case_id), verified)
            for case_id in DEV5_DOMAINS
        ],
    }

    data, bindings, rows = build_core(
        base,
        IdentityMap(version=VERSION, bindings=[]),
        list(cores.values()),
        load_report(core_dir / EVIDENCE),
        version=VERSION,
        draft_date=DRAFT_DATE,
        case_note=(
            f"dev5 draft1 ({DRAFT_DATE}): programme page, its twins and the six core "
            f"questions from one expert draft each, listed in {SIGN}; unsigned. Only quotes "
            "the CI verify_evidence check found are known."
        ),
    )
    return redate(data), redate(bindings), rows


def redate(document: dict[str, Any]) -> dict[str, Any]:
    """``core_drafts`` stamps its own draft date on expert notes; dev5's is DRAFT_DATE."""
    text = json.dumps(document, ensure_ascii=False)
    for stamp in ("Expert ({})", "Expert draft {}", "expert draft {}"):
        text = text.replace(stamp.format(CORE_DRAFT_DATE), stamp.format(DRAFT_DATE))
    redated: dict[str, Any] = json.loads(text)
    return redated


def label_counts(data: dict[str, Any]) -> dict[str, dict[str, int]]:
    """Case -> {status: count} over every label."""
    out: dict[str, dict[str, int]] = {}
    for case in data["cases"]:
        counts = out.setdefault(case["id"], {"known": 0, "not_applicable": 0, "unknown": 0})
        for label in case["labels"]:
            counts[label["status"]] += 1
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("programme_drafts", type=Path)
    parser.add_argument("core_drafts", type=Path)
    parser.add_argument("--rows", type=Path, help="write the worksheet rows as JSON here")
    args = parser.parse_args(argv)
    data, bindings, rows = build(args.programme_drafts, args.core_drafts)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    OUT_BINDINGS.write_text(
        json.dumps(bindings, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    if args.rows:
        args.rows.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    for case_id, counts in label_counts(data).items():
        print(case_id, counts)
    print(f"cases={len(data['cases'])} bindings={len(bindings['bindings'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
