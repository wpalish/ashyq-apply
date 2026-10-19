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

Evaluation tooling only: nothing under ``app/`` may import it.
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from app.adapters.search import get_search_provider
from app.adapters.search.base import SearchError, SearchUnavailable

#: A query any working web index answers, naming no applicant and no case.
PREFLIGHT_QUERY = "university bachelor programme admission requirements"


async def preflight(query: str = PREFLIGHT_QUERY) -> tuple[bool, str]:
    """(provider answered, one line saying how), after exactly one search call."""
    try:
        provider = get_search_provider()
    except SearchError as exc:
        return False, f"search pre-flight: no provider ({type(exc).__name__})"
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
    args = parser.parse_args(argv)
    ok, message = asyncio.run(preflight(args.query))
    print(message, file=sys.stdout if ok else sys.stderr, flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
