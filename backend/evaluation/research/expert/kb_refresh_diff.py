"""A KB re-verification report vs the previous checks -> the re-draft queue.

Free-search ticket 07 (``docs/process/wayfinder/free-search/issues/07-scheduled-kb-refresh.md``).
``scripts/verify_evidence.py --from-kb`` re-reads every URL of the knowledge
base through the production fetcher. This tool classifies each new row, sets
it beside the previous checks of the same (case, item, URL) — the CI and
recheck reports the KB was built from, or an earlier refresh — adds the KB's
own staleness (``app.knowledge.stale_reasons``), and writes one queue file
listing what to re-draft, by university and question, with the reason.

It never edits the KB JSON: ``kb_build --refresh`` does that. Run from
``backend``::

    python -m evaluation.research.expert.kb_refresh_diff REPORT.json \\
        --previous evaluation/research/expert/data/kb_drafts.*/*/evidence_check.*.json \\
        --kb app/knowledge/kb_cs_bachelor.json app/knowledge/kb_imported_dev.json \\
        --queue ../docs/process/KB_REFRESH_<date>.md [--summary counts.json]

Classes of a row: ``verified`` (official page, quote found), ``quote_gone``
(page read, quote not on it), ``moved`` (redirected elsewhere and the quote not
found), ``http_404`` (404/410), ``http_403`` (401/403: refused, usually the
vantage point), ``robots_refused`` (robots.txt disallow or a Crawl-delay too
long), ``robots_unreachable`` (robots.txt could not be read, so RFC 9309 makes
the fetcher treat the site as disallowed: a vantage-point problem, not the
site's answer), ``timeout``, ``fetch_error`` (anything else) and
``not_official``.
Against the previous checks a row is ``unchanged``, ``newly_verified``,
``lost`` (verified before, not now) or ``new`` (no previous row).
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from app.knowledge import stale_reasons

from ..metrics import canonical_url

Row = dict[str, Any]

VERIFIED = "verified"
#: Classes that say the page itself changed: the entry needs a re-draft.
CONTENT_CLASSES = ("quote_gone", "moved", "http_404", "not_official")
#: Classes that say this vantage point could not read the page: a recheck from
#: another vantage point (the sandbox proxy, later the owner's computer) first.
BLOCKED_CLASSES = ("http_403", "robots_refused", "robots_unreachable", "timeout", "fetch_error")
CLASSES = (VERIFIED, *CONTENT_CLASSES, *BLOCKED_CLASSES)
CHANGES = ("unchanged", "newly_verified", "lost", "new")


#: The reasons ``app.knowledge.stale_reasons`` derives from the date alone; any
#: other stored reason (the build's year rules: "the academic year is not
#: stated", "published for academic year …") is about the value and is kept.
_DATED_REASON = re.compile(
    r"^(no verification date|verified on |academic year .* is (past|before)|deadline .* has passed)"
)


def current_stale_reasons(fact: Row, today: date, intake: str | None) -> list[str]:
    """The fact's stored value-based reasons plus its date-based ones recomputed for ``today``."""
    kept = [r for r in fact.get("stale_reasons") or [] if not _DATED_REASON.match(str(r))]
    return list(dict.fromkeys([*kept, *stale_reasons(fact, today, intake)]))


def passed(row: Row | None) -> bool:
    return row is not None and row.get("official") is True and row.get("quote_found") is True


def classify(row: Row) -> str:
    """The class of one evidence-check row (see the module docstring)."""
    if passed(row):
        return VERIFIED
    if row.get("official") is False:
        return "not_official"
    outcome = str(row.get("outcome") or "")
    code = row.get("status_code")
    if outcome == "robots_disallowed" and "unreachable" in str(row.get("note") or ""):
        return "robots_unreachable"
    if outcome in ("robots_disallowed", "robots_crawl_delay"):
        return "robots_refused"
    if code in (401, 403):
        return "http_403"
    if code in (404, 410):
        return "http_404"
    if outcome == "timeout":
        return "timeout"
    if outcome in ("ok", "cached"):
        final = str(row.get("final_url") or "")
        if final and canonical_url(final) != canonical_url(str(row.get("url") or "")):
            return "moved"
        return "quote_gone"
    return "fetch_error"


def _key(row: Row) -> tuple[str, str, str]:
    return (str(row.get("case")), str(row.get("item")), canonical_url(str(row.get("url") or "")))


def load_rows(paths: list[Path]) -> list[Row]:
    """Every row of every report; a report from an agent's container is not evidence."""
    out: list[Row] = []
    for path in paths:
        if "container" in path.name:
            continue
        rows = json.loads(path.read_text(encoding="utf-8"))
        out += [r for r in rows if isinstance(r, dict) and r.get("url")]
    return out


class Previous:
    """The previous checks per (case, item, URL), with (item, URL) as a fallback.

    A passing row wins (the value was verified there), else the latest check.
    """

    def __init__(self, rows: list[Row]) -> None:
        self.by_key: dict[tuple[str, ...], Row] = {}
        self.by_url: dict[tuple[str, ...], Row] = {}
        for row in rows:
            key = _key(row)
            _keep(self.by_key, key, row)
            _keep(self.by_url, key[1:], row)

    def find(self, row: Row) -> Row | None:
        key = _key(row)
        return self.by_key.get(key) or self.by_url.get(key[1:])


def _keep(index: dict[tuple[str, ...], Row], key: tuple[str, ...], row: Row) -> None:
    held = index.get(key)
    if held is None or (not passed(held) and (passed(row) or _date(row) >= _date(held))):
        index[key] = row


def _date(row: Row) -> str:
    return str(row.get("checked_on") or "")


def change(new: Row, previous: Row | None) -> str:
    if previous is None:
        return "new"
    before, now = passed(previous), passed(new)
    if before == now:
        return "unchanged"
    return "newly_verified" if now else "lost"


def compare(rows: list[Row], previous: list[Row]) -> list[Row]:
    """Each new row with its ``class``, the previous row's class and the ``change``."""
    index = Previous(previous)
    out: list[Row] = []
    for row in rows:
        before = index.find(row)
        out.append(
            {
                **row,
                "class": classify(row),
                "previous_class": classify(before) if before else None,
                "previous_checked_on": (before or {}).get("checked_on"),
                "change": change(row, before),
            }
        )
    return out


def stale_in_kb(paths: list[Path], today: date) -> list[Row]:
    """The KB's own staleness, recomputed for ``today``: one row per stale fact."""
    out: list[Row] = []
    for path in paths:
        document = json.loads(path.read_text(encoding="utf-8"))
        intake = document.get("intake") or "fall 2027"
        for seed_id, entry in sorted((document.get("entries") or {}).items()):
            for question, facts in (entry.get("facts") or {}).items():
                for fact in facts or []:
                    reasons = current_stale_reasons(fact, today, intake)
                    if reasons:
                        out.append(
                            {
                                "kb": path.name,
                                "seed_id": seed_id,
                                "university": entry.get("university") or seed_id,
                                "question": question,
                                "key": fact.get("key"),
                                "url": fact.get("source_url"),
                                "reasons": reasons,
                            }
                        )
    return out


def universities(paths: list[Path]) -> dict[str, str]:
    out: dict[str, str] = {}
    for path in paths:
        document = json.loads(path.read_text(encoding="utf-8"))
        for seed_id, entry in (document.get("entries") or {}).items():
            out.setdefault(str(seed_id), str(entry.get("university") or seed_id))
    return out


def summary(compared: list[Row], stale: list[Row]) -> Row:
    """Counts per class, per change, and the queue's size."""
    urls = {str(r.get("url")) for r in compared}
    return {
        "rows": len(compared),
        "urls": len(urls),
        "hosts": len({canonical_url(u).split("/")[2] for u in urls if "//" in u}),
        "classes": {c: n for c in CLASSES if (n := sum(r["class"] == c for r in compared))},
        "changes": {c: n for c in CHANGES if (n := sum(r["change"] == c for r in compared))},
        "redraft": sum(r["class"] in CONTENT_CLASSES for r in compared),
        "blocked": sum(r["class"] in BLOCKED_CLASSES for r in compared),
        "stale_facts": len(stale),
    }


def _cell(text: Any) -> str:
    return str(text if text is not None else "").replace("|", "\\|").replace("\n", " ")


def _reason(row: Row) -> str:
    code = f" {row['status_code']}" if row.get("status_code") else ""
    detail = f"{row['class']} ({row.get('outcome') or '-'}{code})"
    if row["class"] == "moved":
        detail += f" -> {row.get('final_url')}"
    if row.get("previous_class"):
        detail += f"; before: {row['previous_class']} on {row.get('previous_checked_on') or '?'}"
    return detail


def _table(rows: list[Row], names: dict[str, str]) -> list[str]:
    lines = [
        "| university | seed_id | question | key | source | reason | URL |",
        "|---|---|---|---|---|---|---|",
    ]
    order = sorted(rows, key=lambda r: (names.get(str(r.get("seed_id")), ""), str(r.get("item"))))
    for r in order:
        seed = str(r.get("seed_id") or r.get("case"))
        lines.append(
            f"| {_cell(names.get(seed, seed))} | {seed} | {r.get('item')} | {_cell(r.get('key'))} "
            f"| {r.get('source') or '-'} | {_cell(_reason(r))} | {_cell(r.get('url'))} |"
        )
    return lines


def queue_markdown(
    compared: list[Row], stale: list[Row], names: dict[str, str], *, day: str, report: str
) -> str:
    """The queue file: counts, then re-draft, blocked and stale lists."""
    counts = summary(compared, stale)
    redraft = [r for r in compared if r["class"] in CONTENT_CLASSES]
    blocked = [r for r in compared if r["class"] in BLOCKED_CLASSES]
    lines = [
        f"# KB refresh queue — {day}",
        "",
        f"Generated by `evaluation/research/expert/kb_refresh_diff.py` from `{report}` "
        "(`scripts/verify_evidence.py --from-kb`, the production fetcher). Free-search ticket 07. "
        "This file never changes the KB: `kb_build --refresh` stamps `verified_on` on what still "
        "verifies and marks the rest for expert review; nothing is dropped or altered.",
        "",
        "## Counts",
        "",
        f"- rows checked: **{counts['rows']}** ({counts['urls']} URLs on {counts['hosts']} hosts)",
        "- by class: " + ", ".join(f"{c} **{n}**" for c, n in counts["classes"].items()),
        "- against the previous checks: "
        + ", ".join(f"{c} **{n}**" for c, n in counts["changes"].items()),
        f"- to re-draft (page changed): **{counts['redraft']}**; blocked from this vantage "
        f"point: **{counts['blocked']}**; stale in the KB: **{counts['stale_facts']}**",
        "",
        "## Re-draft: the page changed",
        "",
        "The quote is gone, the page moved or is gone, or the host is not official. Re-draft "
        "these with `university-admissions-research`, re-check the batch and rebuild.",
        "",
        *(_table(redraft, names) if redraft else ["(none)"]),
        "",
        "## Blocked from this vantage point",
        "",
        "HTTP 401/403, robots.txt refusals, time-outs and other fetch errors. Not evidence that "
        "the page changed: recheck from another vantage point (`--trust-env-proxy` from a sandbox; "
        "the owner's computer once 01-Q4 is answered). A robots.txt refusal is final; an unreachable "
        "robots.txt is not a refusal.",
        "",
        *(_table(blocked, names) if blocked else ["(none)"]),
        "",
        "## Stale in the KB",
        "",
        "Facts the product already shows as possibly stale (`app.knowledge.stale_reasons` as of "
        f"{day}): re-draft when the next year's value is published.",
        "",
    ]
    if stale:
        lines += [
            "| university | seed_id | question | key | reasons | URL |",
            "|---|---|---|---|---|---|",
        ]
        for s in sorted(stale, key=lambda s: (s["university"], s["question"])):
            lines.append(
                f"| {_cell(s['university'])} | {s['seed_id']} | {s['question']} | "
                f"{_cell(s['key'])} | {_cell('; '.join(s['reasons']))} | {_cell(s['url'])} |"
            )
    else:
        lines.append("(none)")
    return "\n".join(lines) + "\n"


def summary_markdown(counts: Row) -> str:
    """A short job summary for ``$GITHUB_STEP_SUMMARY``."""
    lines = ["### KB refresh", "", "| class | rows |", "|---|---|"]
    lines += [f"| {c} | {n} |" for c, n in counts["classes"].items()]
    lines += ["", "| against previous | rows |", "|---|---|"]
    lines += [f"| {c} | {n} |" for c, n in counts["changes"].items()]
    lines += [
        "",
        f"rows {counts['rows']}, URLs {counts['urls']}, hosts {counts['hosts']}; "
        f"re-draft {counts['redraft']}, blocked {counts['blocked']}, "
        f"stale in KB {counts['stale_facts']}",
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("report", type=Path, help="the --from-kb report")
    parser.add_argument("--previous", type=Path, nargs="*", default=[])
    parser.add_argument("--kb", type=Path, nargs="*", default=[])
    parser.add_argument("--queue", type=Path, help="write the queue Markdown here")
    parser.add_argument("--summary", type=Path, help="write the counts as JSON here")
    parser.add_argument("--summary-md", action="store_true", help="print a job summary")
    parser.add_argument("--today", help="YYYY-MM-DD (default: today, UTC)")
    args = parser.parse_args(argv)
    day = args.today or datetime.now(UTC).date().isoformat()
    rows = load_rows([args.report])
    compared = compare(rows, load_rows(args.previous))
    stale = stale_in_kb(args.kb, date.fromisoformat(day))
    counts = summary(compared, stale)
    if args.queue:
        args.queue.parent.mkdir(parents=True, exist_ok=True)
        text = queue_markdown(
            compared, stale, universities(args.kb), day=day, report=args.report.name
        )
        args.queue.write_text(text, encoding="utf-8")
    if args.summary:
        args.summary.write_text(json.dumps(counts, indent=1) + "\n", encoding="utf-8")
    if args.summary_md:
        print(summary_markdown(counts))
    else:
        print(json.dumps(counts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
