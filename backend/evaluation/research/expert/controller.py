"""Run controller: execute an expert's chosen actions and log them independently.

The expert never touches the network. It names one action at a time; this
controller performs it through the production ``Fetcher`` or the configured
search-provider seam, and writes the raw tool output to a numbered log file
whose SHA-256 is computed here, not by the expert. The trace the expert later
submits must cite these files; ``validate --logs-dir`` re-hashes them.

Budget accounting follows the handoff's equal-budget rule. ``replay`` re-reads
the baseline's own path up to the intervention point first, so the calls and
time it costs are counted the way the pipeline spent them; every later action
is counted cumulatively on top. An action that would exceed the packet's call
or time cap is still executed and logged, but marked ``outside_policy``.

The tool policy is enforced here, not requested of the expert: repository
hosts and public mirrors of this benchmark are refused before any request, and
search results pointing at them are dropped from the log the expert reads.
"""

from __future__ import annotations

import base64
import hashlib
import json
import time
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

#: Hosts the expert may not reach: the repository, its mirrors, and anywhere a
#: copy of the signed benchmark could be published.
BLOCKED_HOSTS = (
    "github.com",
    "githubusercontent.com",
    "github.io",
    "gitlab.com",
    "bitbucket.org",
    "sourcegraph.com",
    "huggingface.co",
    "kaggle.com",
)

TOOL_POLICY = {
    "allowed": [
        "fetcher (production Fetcher, robots respected, browser tier off)",
        "search_provider",
    ],
    "blocked_hosts": list(BLOCKED_HOSTS),
    "expert_tools": "none: the expert names actions; the controller executes and logs them",
}


def blocked(url: str) -> bool:
    host = (urlsplit(url).hostname or "").lower()
    return any(host == h or host.endswith("." + h) for h in BLOCKED_HOSTS)


@dataclass
class Ledger:
    max_calls: int
    max_ms: int
    calls: int = 0
    ms: int = 0
    entries: list[dict[str, Any]] = field(default_factory=list)

    def charge(self, *, calls: int, ms: int) -> str:
        self.calls += calls
        self.ms += ms
        within = self.calls <= self.max_calls and self.ms <= self.max_ms
        return "same_policy" if within else "outside_policy"


def _write_log(logs_dir: Path, name: str, record: dict[str, Any]) -> tuple[str, str]:
    data = json.dumps(record, ensure_ascii=False, sort_keys=True, indent=1).encode("utf-8")
    logs_dir.mkdir(parents=True, exist_ok=True)
    (logs_dir / name).write_bytes(data)
    return name, hashlib.sha256(data).hexdigest()


async def _fetch(get: Callable[[str], Awaitable[Any]], url: str) -> tuple[dict[str, Any], int]:
    began = time.monotonic()
    try:
        result = await get(url)
    except Exception as exc:  # a failed call is still a recorded call
        return {"error": f"{type(exc).__name__}: {exc}", "outcome": "exception"}, int(
            (time.monotonic() - began) * 1000
        )
    elapsed = int((time.monotonic() - began) * 1000)
    outcome = getattr(result.outcome, "value", str(result.outcome))
    return {
        "outcome": outcome,
        "ok": bool(result.ok),
        "status_code": result.status_code,
        "final_url": result.final_url or result.url,
        "content_type": result.content_type,
        "from_cache": bool(result.from_cache),
        "fetch_tier": result.fetch_tier,
        "error": result.error,
        "fetched_at": result.fetched_at.isoformat(),
        "content_sha256": hashlib.sha256(result.content or b"").hexdigest(),
        "content_b64": base64.b64encode(result.content or b"").decode("ascii"),
    }, elapsed


async def execute(
    plan: dict[str, Any],
    logs_dir: Path,
    *,
    get: Callable[[str], Awaitable[Any]],
    search: Callable[..., Awaitable[Any]] | None,
    provider_name: str,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> dict[str, Any]:
    """Perform ``plan``'s replay and actions; return the summary the trace cites."""
    ledger = Ledger(
        max_calls=int(plan["max_calls"]),
        max_ms=int(plan["max_ms"]),
        calls=int(plan.get("start_calls", 0)),
        ms=int(plan.get("start_ms", 0)),
    )
    first = int(plan.get("first_log_number", 1))
    prefix = str(plan.get("log_prefix", plan["case_id"]))
    summary: dict[str, Any] = {
        "case_id": plan["case_id"],
        "provider": provider_name,
        "tool_policy": TOOL_POLICY,
        "replay": [],
        "actions": [],
    }
    number = first
    for kind, items in (("replay", plan.get("replay", [])), ("actions", plan.get("actions", []))):
        for item in items:
            action = {"tool": "fetcher", "url": item} if isinstance(item, str) else dict(item)
            at = now().isoformat()
            record: dict[str, Any] = {"request": action, "at": at, "phase": kind}
            calls = 0
            if action["tool"] == "fetcher":
                url = str(action["url"])
                if blocked(url):
                    record["outcome"] = "blocked_by_tool_policy"
                    elapsed = 0
                else:
                    response, elapsed = await _fetch(get, url)
                    record["response"] = response
                    calls = 1
            elif action["tool"] == "search_provider":
                if search is None:
                    record["outcome"] = "search_provider_not_configured"
                    elapsed = 0
                else:
                    began = time.monotonic()
                    try:
                        answer = await search(
                            query=str(action["query"]),
                            domains=list(action.get("domains", [])),
                            max_results=int(action.get("max_results", 10)),
                        )
                        results = [
                            {"rank": r.rank, "url": r.url, "title": r.title, "snippet": r.snippet}
                            for r in answer.results
                        ]
                        record["response"] = {
                            "results": [r for r in results if not blocked(r["url"])],
                            "dropped_by_tool_policy": sum(blocked(r["url"]) for r in results),
                        }
                    except Exception as exc:
                        record["response"] = {"error": f"{type(exc).__name__}: {exc}"}
                    elapsed = int((time.monotonic() - began) * 1000)
            else:
                raise ValueError(f"Unsupported tool {action['tool']!r}")
            policy = ledger.charge(calls=calls, ms=elapsed)
            record.update(
                elapsed_ms=elapsed,
                fetcher_calls_cumulative=ledger.calls,
                elapsed_ms_cumulative=ledger.ms,
                policy_mode=policy,
            )
            name, sha = _write_log(logs_dir, f"{prefix}-{number:03d}.json", record)
            number += 1
            summary[kind].append(
                {
                    "raw_log_path": name,
                    "raw_log_sha256": sha,
                    "at": at,
                    "tool": action["tool"],
                    "request": action,
                    "outcome": record.get("outcome")
                    or (record.get("response") or {}).get("outcome")
                    or ("error" if "error" in (record.get("response") or {}) else "ok"),
                    "elapsed_ms": elapsed,
                    "fetcher_calls_cumulative": ledger.calls,
                    "elapsed_ms_cumulative": ledger.ms,
                    "policy_mode": policy,
                }
            )
    summary["final"] = {"fetcher_calls": ledger.calls, "elapsed_ms": ledger.ms}
    return summary


async def run(plan_path: Path, logs_dir: Path, cache_dir: Path) -> dict[str, Any]:
    """Execute a plan with the production Fetcher and configured search provider."""
    from app.adapters.fetching import Fetcher
    from app.adapters.search import SearchProviderNotConfigured, get_search_provider
    from app.config import get_settings

    settings = get_settings()
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    try:
        provider = get_search_provider()
        search = provider.search
        provider_name = settings.search_provider
    except SearchProviderNotConfigured:
        search, provider_name = None, "none"
    async with Fetcher(
        cache_dir,
        delay_seconds=settings.fetch_delay_seconds,
        respect_robots=settings.respect_robots,
        timeout=settings.fetch_timeout_seconds,
        contact=settings.fetch_contact,
    ) as fetcher:
        return await execute(
            plan, logs_dir, get=fetcher.get, search=search, provider_name=provider_name
        )


def expert_view(record: dict[str, Any], *, chars: int = 6000, links: int = 120) -> dict[str, Any]:
    """What the expert reads of one raw log: status, readable text, links."""
    from app.adapters.document_ir import build_document_ir
    from app.adapters.extraction import readable_text

    view: dict[str, Any] = {"request": record["request"], "policy_mode": record["policy_mode"]}
    response = record.get("response") or {}
    if "results" in response or record.get("outcome"):
        view.update(dict(response))
        view["outcome"] = record.get("outcome", view.get("outcome"))
        return view
    view.update(
        {
            k: response.get(k)
            for k in ("outcome", "status_code", "final_url", "content_type", "error")
        }
    )
    body = base64.b64decode(response.get("content_b64", "") or b"")
    if body and "html" in (response.get("content_type") or "").lower():
        html = body.decode("utf-8", errors="replace")
        view["text"] = readable_text(html)[:chars]
        doc = build_document_ir(html, response.get("final_url") or record["request"]["url"])
        seen: list[dict[str, str]] = []
        for link in doc.links:
            if not blocked(link.url) and all(s["url"] != link.url for s in seen):
                seen.append({"url": link.url, "text": link.text[:80]})
        view["links"] = seen[:links]
        view["links_total"] = len(seen)
    elif body:
        view["text"] = f"[{len(body)} bytes of {response.get('content_type')}]"
    return view


def main(argv: Sequence[str] | None = None) -> None:
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--logs-dir", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args(argv)
    summary = asyncio.run(run(args.plan, args.logs_dir, args.cache_dir))
    args.summary.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary["final"]))


if __name__ == "__main__":
    main()
