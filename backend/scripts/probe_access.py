"""Access probe: can the production network read the corpus's evidence pages?

Error analysis 2026-10-05 put 17 of 46 benchmark misses down to ACCESS: the
page the gold label cites refused or stalled the fetcher on a GitHub runner,
while the same page opens from a developer container. This script answers the
question that matters for applicants: does it open from production?

Run it on the deployed machine (``fly ssh console``, then
``python scripts/probe_access.py``). It uses the production ``Fetcher``
unchanged: our own user agent, robots.txt honoured, no cache, no proxy, no
browser tier. A refusal is recorded as a refusal; nothing retries around it.

Output is one tab-separated row per URL (outcome, HTTP status, readable
characters, URL, error) and a count per outcome at the end. It reads only
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

DEFAULT_DATASET = Path("evaluation/research/data/ground_truth.draft8.json")


def evidence_urls(dataset: Path, only: set[str]) -> list[str]:
    data = json.loads(dataset.read_text(encoding="utf-8"))
    urls: dict[str, None] = {}
    for case in data["cases"]:
        if only and case["id"] not in only:
            continue
        for label in case["labels"]:
            for evidence in label.get("evidence") or []:
                urls.setdefault(evidence["url"], None)
    return list(urls)


async def probe(urls: list[str], timeout: float) -> Counter[str]:
    counts: Counter[str] = Counter()
    with tempfile.TemporaryDirectory() as cache:
        async with Fetcher(Path(cache), timeout=timeout) as fetcher:
            for url in urls:
                result = await fetcher.get(url, use_cache=False)
                chars = len(readable_text(result.text)) if result.text else 0
                outcome = result.outcome.value
                counts[outcome] += 1
                print(
                    f"{outcome}\t{result.status_code or '-'}\t{chars}\t{url}\t{result.error}",
                    flush=True,
                )
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--case", action="append", default=[], help="limit to a case id")
    parser.add_argument("--timeout", type=float, default=20.0)
    args = parser.parse_args()
    urls = evidence_urls(args.dataset, set(args.case))
    counts = asyncio.run(probe(urls, args.timeout))
    print("\n" + "  ".join(f"{k}={v}" for k, v in sorted(counts.items())))


if __name__ == "__main__":
    main()
