"""Read official university pages on the CI runner, for KB expert drafting.

The agent container's egress is refused by many university sites (HTTP 403,
TLS chain errors, resets) that the GitHub Actions runner reads fine. A
drafting worker commits a list of official URLs, dispatches
``benchmark-capture.yml`` with ``mode=read_pages``, and reads the pages from
the artifact instead of from its own container.

The list lives under ``evaluation/research/expert/data/`` and is either JSON
(a list of ``{"seed_id": ..., "url": ...}`` objects, or an object whose
``rows`` is that list) or text (one ``<seed_id> <url>`` per line, ``#``
comments). From ``backend``::

    python scripts/read_pages.py evaluation/research/expert/data/read_pages/<list>.json \\
        --out <dir> [--robots-override-kb]

Every read goes through the production ``Fetcher`` exactly as
``verify_evidence.py`` reads a quote's page: our own user agent, robots.txt
honoured, Crawl-delay waited out up to ``MAX_CRAWL_DELAY_WAIT`` seconds, the
fetcher's size and time limits, no cache, and the production HTML and PDF
extractors. A URL whose host is not an official domain of its ``seed_id``
(``verify_evidence.official_domains``: the curated cases plus the KB list's
``official_domain``, ``official_site`` and ``extra_domains``) is not read at
all, and neither is any URL of a heldout case.

``--robots-override-kb`` is the owner's KB exception (AGENTS.md §6) through
the same code path as ``verify_evidence.py --robots-override-kb``: after the
ordinary pass, the official URLs that robots.txt refused are read once more
by a fresh production ``Fetcher`` given exactly those URLs as
``kb_evidence_robots_override_urls`` (one request, no retry, Crawl-delay
honoured, a redirect elsewhere still refused).

Output, in ``--out``:

- ``pages.jsonl``: one record per URL, in list order: ``seed_id``, ``url``,
  ``final_url``, ``status`` (the fetch outcome), ``status_code``, ``robots``
  (``allowed``, ``disallowed``, ``unreachable``, ``crawl_delay``,
  ``overridden``, ``not_reached`` or ``not_read``), ``official``,
  ``content_type``, ``chars`` (readable characters), ``sha256`` (of the full
  readable text, UTF-8), ``truncated``, ``text`` (capped at ``MAX_TEXT_CHARS``),
  ``note`` and ``read_on``;
- ``index.tsv``: the same rows without the text, for a quick look.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.adapters.fetching import Fetcher, FetchResult
from app.domain.enums import FetchOutcome
from scripts import verify_evidence

BACKEND = Path(__file__).resolve().parents[1]
#: Lists are read from here and nowhere else.
DATA_DIR = BACKEND / "evaluation/research/expert/data"
#: The path a list may be given as, relative to ``backend`` (the workflow
#: checks the same pattern before the script runs). No segment starts with a
#: dot, so ``..`` cannot appear.
#: Plain groups only: the workflow uses this exact string as a bash ERE.
LIST_PATH = re.compile(
    r"^evaluation/research/expert/data/([A-Za-z0-9_-][A-Za-z0-9_.-]*/)*"
    r"[A-Za-z0-9_-][A-Za-z0-9_.-]*\.(json|txt)$"
)
#: Readable characters kept per page in the artifact (the hash covers all).
MAX_TEXT_CHARS = 200_000
#: URLs per list: a reading list for one drafting round, not a crawl.
MAX_ROWS = 300
_SEED = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")

_TSV = (
    "seed_id",
    "status",
    "status_code",
    "robots",
    "official",
    "chars",
    "truncated",
    "sha256",
    "url",
    "final_url",
    "note",
)


@dataclass(frozen=True)
class Row:
    seed_id: str
    url: str


def resolve_list(path: str | Path) -> Path:
    """The list's real path, or ValueError when it is not a list under ``DATA_DIR``."""
    text = str(path)
    candidate = Path(text)
    if candidate.is_absolute():
        try:
            text = candidate.resolve().relative_to(BACKEND).as_posix()
        except ValueError:
            raise ValueError(f"{path}: not under {DATA_DIR}") from None
    if not LIST_PATH.fullmatch(text):
        raise ValueError(
            f"{path}: a list must be evaluation/research/expert/data/<name>.json or .txt"
        )
    resolved = (BACKEND / text).resolve()
    if not resolved.is_relative_to(DATA_DIR.resolve()):
        raise ValueError(f"{path}: resolves outside {DATA_DIR}")
    return resolved


def parse_rows(path: Path) -> list[Row]:
    """The list's rows, deduplicated by URL in order; a malformed row is an error."""
    raw: list[Any]
    if path.suffix == ".json":
        document = json.loads(path.read_text(encoding="utf-8"))
        found = document.get("rows") if isinstance(document, dict) else document
        if not isinstance(found, list):
            raise ValueError(f"{path.name}: expected a list of rows, or an object with rows")
        raw = found
    else:
        raw = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.split("#", 1)[0].strip()
            if line:
                parts = line.split()
                if len(parts) != 2:
                    raise ValueError(f"{path.name}: expected '<seed_id> <url>', got {line!r}")
                raw.append({"seed_id": parts[0], "url": parts[1]})
    rows: list[Row] = []
    seen: set[str] = set()
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"{path.name}: row {index} is not an object")
        seed_id, url = str(item.get("seed_id") or ""), str(item.get("url") or "")
        if not _SEED.match(seed_id) or not url.startswith(("https://", "http://")):
            raise ValueError(f"{path.name}: row {index} needs a seed_id and an http(s) url")
        if url not in seen:
            seen.add(url)
            rows.append(Row(seed_id, url))
    if len(rows) > MAX_ROWS:
        raise ValueError(f"{path.name}: {len(rows)} URLs, more than {MAX_ROWS}")
    return rows


def _existing_cases() -> dict[str, str]:
    """KB seed_id -> its development case id, where it has one."""
    try:
        rows = json.loads(verify_evidence.KB_LIST.read_text(encoding="utf-8")).get("rows") or []
    except (OSError, ValueError, AttributeError):
        return {}
    return {
        str(r["seed_id"]): str(r["existing_case"])
        for r in rows
        if isinstance(r, dict) and r.get("seed_id") and r.get("existing_case")
    }


def heldout(seed_id: str) -> bool:
    return (
        seed_id in verify_evidence.HELDOUT_CASES
        or _existing_cases().get(seed_id, "") in verify_evidence.HELDOUT_CASES
    )


def is_official(row: Row) -> bool:
    """The URL's host is an official domain of the row's ``seed_id`` (or case id)."""
    return verify_evidence.is_official(row.url, row.seed_id, row.seed_id)


def robots_verdict(result: FetchResult, overridden: dict[str, str]) -> str:
    if result.url in overridden:
        return "overridden"
    if result.outcome == FetchOutcome.ROBOTS_DISALLOWED:
        return "unreachable" if "unreachable" in result.error else "disallowed"
    if result.outcome == FetchOutcome.ROBOTS_CRAWL_DELAY:
        return "crawl_delay"
    if result.status_code is not None or result.outcome == FetchOutcome.OK:
        return "allowed"
    # Refused by the network policy, a timeout or a reset before any answer:
    # whether robots.txt allowed it is not known from here.
    return "not_reached"


def record(
    row: Row,
    result: FetchResult | None,
    *,
    official: bool,
    note: str = "",
    overridden: dict[str, str] | None = None,
    max_chars: int = MAX_TEXT_CHARS,
) -> dict[str, Any]:
    """One output record; ``result`` None means the URL was not read."""
    out: dict[str, Any] = {
        "seed_id": row.seed_id,
        "url": row.url,
        "final_url": "",
        "status": "not_read",
        "status_code": None,
        "robots": "not_read",
        "official": official,
        "content_type": "",
        "chars": 0,
        "sha256": "",
        "truncated": False,
        "text": "",
        "note": note,
        "read_on": datetime.now(UTC).date().isoformat(),
    }
    if result is None:
        return out
    text = verify_evidence.page_text(result) if result.ok else ""
    out.update(
        final_url=result.final_url or "",
        status=result.outcome.value,
        status_code=result.status_code,
        robots=robots_verdict(result, overridden or {}),
        content_type=result.content_type,
        chars=len(text),
        sha256=hashlib.sha256(text.encode("utf-8")).hexdigest() if text else "",
        truncated=len(text) > max_chars,
        text=text[:max_chars],
        note=(note or result.error or "")[:160],
    )
    if result.url in (overridden or {}):
        out["robots_override_used"] = True
        out["robots_refusal"] = (overridden or {})[result.url][:160]
    return out


def _fetcher(cache: Path, timeout: float, override: frozenset[str] = frozenset()) -> Fetcher:
    """The production fetcher, built as ``verify_evidence`` builds it."""
    return Fetcher(
        cache,
        timeout=timeout,
        max_crawl_delay=verify_evidence.MAX_CRAWL_DELAY_WAIT,
        kb_evidence_robots_override_urls=override,
    )


async def read_with(
    fetcher: Fetcher,
    rows: list[Row],
    *,
    max_chars: int = MAX_TEXT_CHARS,
    overridden: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """One record per row; non-official and heldout rows are never handed to the fetcher."""
    out: list[dict[str, Any]] = []
    for row in rows:
        if heldout(row.seed_id):
            out.append(record(row, None, official=False, note="heldout case; never read"))
            continue
        if not is_official(row):
            note = f"not an official domain of {row.seed_id}; not read"
            out.append(record(row, None, official=False, note=note))
            continue
        result = await fetcher.get(row.url, use_cache=False)
        out.append(record(row, result, official=True, overridden=overridden, max_chars=max_chars))
        print("\t".join(str(out[-1][k]) for k in _TSV), flush=True)
    return out


async def read(
    rows: list[Row],
    timeout: float,
    *,
    robots_override_kb: bool = False,
    max_chars: int = MAX_TEXT_CHARS,
) -> list[dict[str, Any]]:
    """Read every row; with the override, re-read the robots-refused official ones once."""
    with tempfile.TemporaryDirectory() as cache:
        async with _fetcher(Path(cache), timeout) as fetcher:
            out = await read_with(fetcher, rows, max_chars=max_chars)
    if not robots_override_kb:
        return out
    # Only official, non-heldout URLs robots.txt refused (SR-02's rule): read_with
    # never passed any other URL to a fetcher, so no other can be in this set.
    refused = [
        i
        for i, rec in enumerate(out)
        if rec["official"] and rec["status"] == FetchOutcome.ROBOTS_DISALLOWED.value
    ]
    if not refused:
        return out
    urls = frozenset(rows[i].url for i in refused)
    with tempfile.TemporaryDirectory() as cache:
        async with _fetcher(Path(cache), timeout, urls) as fetcher:
            again = await read_with(
                fetcher,
                [rows[i] for i in refused],
                max_chars=max_chars,
                overridden=fetcher.kb_robots_overridden,
            )
    for i, rec in zip(refused, again, strict=True):
        out[i] = {**rec, "robots_override": True}
        out[i].setdefault("robots_override_used", False)
    return out


def write(out_dir: Path, records: list[dict[str, Any]]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "pages.jsonl").open("w", encoding="utf-8") as handle:
        for rec in records:
            handle.write(json.dumps(rec, ensure_ascii=False) + "\n")
    lines = ["\t".join(_TSV)]
    lines += [
        "\t".join(str(rec[k]).replace("\t", " ").replace("\n", " ") for k in _TSV)
        for rec in records
    ]
    (out_dir / "index.tsv").write_text("\n".join(lines) + "\n", encoding="utf-8")


def summary(records: list[dict[str, Any]]) -> str:
    counts: dict[str, int] = {}
    for rec in records:
        counts[rec["status"]] = counts.get(rec["status"], 0) + 1
    with_text = sum(1 for rec in records if rec["chars"])
    return f"urls={len(records)}  with_text={with_text}  " + "  ".join(
        f"{k}={v}" for k, v in sorted(counts.items())
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("list", help="evaluation/research/expert/data/<...>.json or .txt")
    parser.add_argument("--out", type=Path, required=True, help="output directory")
    parser.add_argument("--timeout", type=float, default=25.0)
    parser.add_argument(
        "--robots-override-kb",
        action="store_true",
        help="owner's KB exception: re-read official URLs robots.txt refused, once",
    )
    args = parser.parse_args(argv)
    try:
        rows = parse_rows(resolve_list(args.list))
    except (ValueError, OSError) as error:
        parser.error(str(error))
    records = asyncio.run(read(rows, args.timeout, robots_override_kb=args.robots_override_kb))
    write(args.out, records)
    print("\n" + summary(records))


if __name__ == "__main__":
    main()
