#!/usr/bin/env python
"""Show one page the way a person auditing it needs to see it.

Building the gold set means reading an institution's own page and writing down
what it says. That is slow by nature, and it must not become "read what the
extractor produced and agree with it" — a benchmark built from the machine's
output measures nothing but the machine's consistency.

So this prints the page's readable text, which is what the audit is written
from, and separately what the current extractor makes of it, which is the thing
being graded. The two are never merged.

    ./.venv/bin/python scripts/audit_page.py https://www.rug.nl/... --grep tuition
    ./.venv/bin/python scripts/audit_page.py URL --claims-only

Fetching goes through the project's own fetcher: robots.txt respected, the
shared cache used, one request per page.
"""

from __future__ import annotations

import argparse
import asyncio
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.adapters.extraction import (  # noqa: E402
    ClaimBuilder,
    extract_cost_tables,
    extract_costs,
    extract_requirement_tables,
    extract_requirements,
    pdf_to_text,
    readable_text,
)
from app.adapters.fetching import Fetcher  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.domain.enums import SourceSpecificity  # noqa: E402


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url")
    parser.add_argument("--grep", help="show only lines matching this pattern")
    parser.add_argument("--claims-only", action="store_true")
    parser.add_argument("--text-only", action="store_true")
    parser.add_argument("--context", type=int, default=0,
                        help="lines of context around each --grep match")
    args = parser.parse_args()

    settings = get_settings()
    async with Fetcher(
        settings.cache_dir,
        delay_seconds=settings.fetch_delay_seconds or 1.0,
        respect_robots=True,
        contact="gold-audit",
    ) as fetcher:
        res = await fetcher.get(args.url)

    accessed_at = datetime.now(UTC).date().isoformat()
    if not res.ok:
        print(f"FETCH FAILED  {res.outcome.value}  {res.error}")
        return 1
    text = pdf_to_text(res.content) if res.is_pdf else readable_text(res.text)
    print(f"# {args.url}")
    print(f"# accessed_at: {accessed_at}   {'PDF' if res.is_pdf else 'HTML'}   "
          f"{len(text)} chars of readable text")

    if not args.claims_only:
        lines = text.splitlines()
        if args.grep:
            pattern = re.compile(args.grep, re.IGNORECASE)
            keep: set[int] = set()
            for i, line in enumerate(lines):
                if pattern.search(line):
                    keep.update(range(max(0, i - args.context),
                                      min(len(lines), i + args.context + 1)))
            shown = sorted(keep)
        else:
            shown = list(range(len(lines)))
        for i in shown:
            if lines[i].strip():
                print(f"{i + 1:5} | {lines[i]}")

    if args.text_only:
        return 0

    builder = ClaimBuilder(
        source_url=args.url,
        specificity=SourceSpecificity.PROGRAM,
        official_domain=True,
    )
    claims = (
        extract_requirements(text, builder)
        + extract_costs(text, builder)
        + (
            extract_cost_tables(res.text, builder)
            + extract_requirement_tables(res.text, builder)
            if not res.is_pdf
            else []
        )
    )
    print(f"\n# the current extractor produces {len(claims)} claim(s):")
    for claim in claims:
        print(
            f"  {claim.claim_type.value:36} {str(claim.normalized_value)[:52]:52} "
            f"{claim.status.value}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
