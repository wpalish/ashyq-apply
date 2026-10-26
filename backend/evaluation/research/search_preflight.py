"""One search call before a paired run spends its budget: is the provider alive?

``python -m evaluation.research.search_preflight``

Between 23:42 and 05:11 UTC on 2026-10-19 every Serper call answered HTTP 400,
and eight paired runs measured that outage as if it were the pipeline. This
sends a single public query (no applicant data, no case) through the product's
own client (``get_search_provider``, the configured provider exactly as a
capture builds it) and exits non-zero, printing the provider's HTTP status and
the adapter's capped, key-masked excerpt of its error body, when it fails.

It never prints the API key or the request headers: the adapter masks the key
in the body excerpt before truncating it, and nothing else about the request
is printed.

With ``--search-ledger PATH --max-search-queries N`` (free-search ticket 02)
its one query is charged to the run's query ledger before it is sent, and a
spent ledger fails the pre-flight with no request sent.

Evaluation tooling only: nothing under ``app/`` may import it.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from app.adapters.search import get_search_provider
from app.adapters.search.base import SearchError, SearchUnavailable

from .search_cap import SearchCapError, SearchQueryLedger

#: A query any working web index answers, naming no applicant and no case.
PREFLIGHT_QUERY = "university bachelor programme admission requirements"


async def preflight(
    query: str = PREFLIGHT_QUERY, ledger: SearchQueryLedger | None = None
) -> tuple[bool, str]:
    """(provider answered, one line saying how), after at most one search call."""
    try:
        provider = get_search_provider()
    except SearchError as exc:
        return False, f"search pre-flight: no provider ({type(exc).__name__})"
    if ledger is not None and not ledger.reserve():
        return False, (
            "search pre-flight FAILED: the run's search query cap is already spent;"
            " no request was sent and no capture was started."
        )
    try:
        response = await provider.search(query=query, max_results=1)
    except SearchUnavailable as exc:
        body = exc.body_excerpt or ""
        return False, (
            f"search pre-flight FAILED: {provider.name} answered http {exc.http_status}"
            f" (reason {exc.reason.value if exc.reason else 'none'}, body {body!r})."
            " No capture was started, so no budget was spent on a dead provider."
        )
    return True, (
        f"search pre-flight ok: {provider.name} answered with {len(response.results)} result(s)"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--query", default=PREFLIGHT_QUERY, help=argparse.SUPPRESS)
    parser.add_argument("--max-search-queries", type=int, default=None, metavar="N")
    parser.add_argument("--search-ledger", type=Path, default=None, metavar="PATH")
    args = parser.parse_args(argv)
    if (args.max_search_queries is None) != (args.search_ledger is None):
        parser.error("--search-ledger and --max-search-queries go together")
    ledger = None
    if args.search_ledger is not None:
        try:
            ledger = SearchQueryLedger.open(args.search_ledger, args.max_search_queries)
        except SearchCapError as exc:
            parser.error(f"--search-ledger: {exc}")
    ok, message = asyncio.run(preflight(args.query, ledger))
    print(message, file=sys.stdout if ok else sys.stderr, flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
