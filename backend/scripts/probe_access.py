"""Access probe: can the production network read the corpus's evidence pages?

Error analysis 2026-10-05 put 17 of 46 benchmark misses down to ACCESS: the
page the gold label cites refused or stalled the fetcher on a GitHub runner,
while the same page opens from a developer container. This script answers the
question that matters for applicants: does it open from production?

Run it on the deployed machine: ``fly ssh console -a ashyq-apply-alisher``,
then ``cd /app/backend && python scripts/probe_access.py``. It uses the production ``Fetcher``
unchanged: our own user agent, robots.txt honoured, no cache, no proxy, no
browser tier. A refusal is recorded as a refusal; nothing retries around it.

Output is one tab-separated row per URL (case, outcome, HTTP status,
readable characters, URL, error) and a count per outcome at the end. It reads only
public gold evidence URLs; it never touches applicant data.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import tempfile
from collections import Counter
from pathlib import Path

from app.adapters.extraction import readable_text
from app.adapters.fetching import Fetcher

#: The corpus is not in the production image (``.dockerignore`` drops
#: ``evaluation/``), so its public evidence URLs ship beside this script.
DEFAULT_URLS = Path(__file__).with_name("probe_access_urls.txt")


def evidence_urls(dataset: Path, only: set[str]) -> list[tuple[str, str]]:
    data = json.loads(dataset.read_text(encoding="utf-8"))
    urls: dict[str, str] = {}
    for case in data["cases"]:
        if only and case["id"] not in only:
            continue
        for label in case["labels"]:
            for evidence in label.get("evidence") or []:
                urls.setdefault(evidence["url"], case["id"])
    return [(case, url) for url, case in urls.items()]


def listed_urls(path: Path, only: set[str]) -> list[tuple[str, str]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        case, url = line.split("\t", 1)
        if not only or case in only:
            rows.append((case, url))
    return rows


async def probe(urls: list[tuple[str, str]], timeout: float) -> Counter[str]:
    counts: Counter[str] = Counter()
    with tempfile.TemporaryDirectory() as cache:
        async with Fetcher(Path(cache), timeout=timeout) as fetcher:
            for case, url in urls:
                result = await fetcher.get(url, use_cache=False)
                chars = len(readable_text(result.text)) if result.text else 0
                outcome = result.outcome.value
                counts[outcome] += 1
                print(
                    f"{case}\t{outcome}\t{result.status_code or '-'}\t{chars}\t{url}\t"
                    f"{result.error}",
                    flush=True,
                )
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dataset", type=Path, help="read URLs from a corpus instead")
    parser.add_argument("--list", action="store_true", help="print the URL list and exit")
    parser.add_argument("--case", action="append", default=[], help="limit to a case id")
    parser.add_argument("--timeout", type=float, default=20.0)
    args = parser.parse_args()
    only = set(args.case)
    urls = evidence_urls(args.dataset, only) if args.dataset else listed_urls(DEFAULT_URLS, only)
    if args.list:
        for case, url in urls:
            print(f"{case}\t{url}")
        return
    counts = asyncio.run(probe(urls, args.timeout))
    print("\n" + "  ".join(f"{k}={v}" for k, v in sorted(counts.items())))


if __name__ == "__main__":
    main()
