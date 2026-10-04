"""Execute model-chosen actions through production tools and record their bytes.

Legacy plans retain diagnostic overflow accounting. Fresh pilots opt in with
``strict_budget: true``: at most 60 cumulative Fetcher.get calls, 120000 ms,
and six configured Exa queries. Exhaustion refuses a call before invoking it.
Only an explicit ``exploration_mode: outside_policy`` permits extra diagnostic
calls, and every action in that mode is outside policy, including early ones.

``budget_origin`` distinguishes an ``independent_full_budget`` expert run from
a ``baseline_intervention`` sharing the pipeline's already spent budget. For
incremental plans the caller supplies ``start_ms`` including model selection
time since the original run began, alongside ``start_calls`` and
``start_search_queries``. Time within this invocation is measured with the
monotonic clock; an asyncio deadline also bounds each actual tool action.
An optional strict ``action_deadline_ms`` is an absolute cumulative active
ceiling for navigation, within ``max_ms``. It preserves time for a final
submission without tool I/O and cannot be extended when resuming. Explicit
outside-policy exploration also respects this navigation ceiling.

Prospective ``independent_network_budget`` plans instead use the shared
``network_actions_v1`` contract: exactly 60 reads and six queries, with model
thinking excluded from the source ledger. Their 900000 ms ceiling is an
immutable absolute wall hang guard. Fresh source counters start at zero;
resumes use the exact measured counters, and every diagnostic action also
respects that same wall deadline. Legacy plans keep their original semantics.

Raw logs belong in ignored artifacts, never Git. ``resume_summary`` may hold
the preceding returned summary to recheck raw-log hashes before resuming.
Existing logs establish counter floors and retain a provider's HTTP 429 stop.
The Fetcher continues to own robots, SSRF, privacy, and redirect behavior.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import math
import re
import time
from collections.abc import Awaitable, Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, BinaryIO
from urllib.parse import urlsplit

from .network_budget import (
    BUDGET_MODEL,
    MAX_FETCHER_CALLS,
    MAX_SEARCH_QUERIES,
    NETWORK_COMPARISON_MODE,
    WALL_GUARD_MS,
    WallGuard,
    expert_budget,
    parse_timestamp,
    parse_wall_guard,
)

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
STRICT_PROVIDERS = frozenset({"exa", "exa_mcp"})
STRICT_MAX_CALLS = 60
STRICT_MAX_MS = 120_000
STRICT_MAX_SEARCH_QUERIES = 6
MAX_LOG_CONTENT_BYTES = 8 * 1024 * 1024
MAX_VIEW_CHARS = 50_000
MAX_VIEW_ITEMS = 500
_SAFE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,119}\Z")
_SAFE_FILENAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,239}\Z")
_DOMAIN = re.compile(
    r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)*\Z"
)
_QUERY_DOMAIN = re.compile(r"\b(?:site|domain):\s*([^\s)]+)", re.IGNORECASE)
_QUERY_URL = re.compile(r"https?://[^\s\"'()]+", re.IGNORECASE)

TOOL_POLICY = {
    "allowed": [
        "fetcher (production Fetcher, robots respected, browser tier off)",
        "search_provider",
    ],
    "blocked_hosts": list(BLOCKED_HOSTS),
    "expert_tools": "none: the expert names actions; the controller executes and logs them",
}


class _WallGuardRefused(Exception):
    """The wall expired during timeout setup, before any actual tool call."""


def _host(url: str) -> str:
    try:
        return (urlsplit(url).hostname or "").lower().rstrip(".")
    except ValueError:
        return ""


def blocked(url: str) -> bool:
    host = _host(url)
    return any(host == h or host.endswith("." + h) for h in BLOCKED_HOSTS)


def _domain(value: str) -> str:
    domain = value.lower().strip().rstrip(".")
    if not _DOMAIN.fullmatch(domain) or len(domain) > 253:
        raise ValueError("Official and query domains must be plain hostnames")
    return domain


def _allowed_url(url: str, domains: tuple[str, ...]) -> bool:
    try:
        parts = urlsplit(url)
        if parts.scheme not in {"http", "https"} or parts.username or parts.password:
            return False
        host = _host(url)
        _domain(host)
        _port = parts.port  # reject malformed ports before passing the URL to a tool
    except ValueError:
        return False
    return not blocked(url) and (
        not domains or any(host == d or host.endswith("." + d) for d in domains)
    )


def _integer(plan: dict[str, Any], key: str, default: int | None = None) -> int:
    value = plan.get(key, default)
    if type(value) is not int or value < 0:
        raise ValueError(f"{key} must be a nonnegative integer")
    return value


def _action_deadline(plan: dict[str, Any], max_ms: int) -> int | None:
    value = plan.get("action_deadline_ms")
    if value is not None and (type(value) is not int or not 1 <= value <= max_ms):
        raise ValueError("action_deadline_ms must be an integer from 1 to max_ms")
    return value


@dataclass
class Ledger:
    max_calls: int
    max_ms: int
    calls: int = 0
    ms: int = 0
    entries: list[dict[str, Any]] = field(default_factory=list)
    max_search_queries: int | None = None
    search_queries: int = 0

    def charge(self, *, calls: int, ms: int, search_queries: int = 0) -> str:
        self.calls += calls
        self.ms += ms
        self.search_queries += search_queries
        within = (
            self.calls <= self.max_calls
            and self.ms <= self.max_ms
            and (self.max_search_queries is None or self.search_queries <= self.max_search_queries)
        )
        return "same_policy" if within else "outside_policy"


@contextmanager
def _reserve_log(logs_dir: Path, name: str, record: dict[str, Any]) -> Iterator[BinaryIO]:
    """Reserve before I/O; interrupted calls leave an explicitly incomplete log."""
    if Path(name).name != name or not _SAFE_FILENAME.fullmatch(name):
        raise ValueError("Raw log name must be a safe filename")
    logs_dir.mkdir(parents=True, exist_ok=True)
    with (logs_dir / name).open("xb") as output:
        output.write(json.dumps({**record, "outcome": "pending"}).encode("utf-8"))
        output.flush()
        yield output


def _write_log(
    logs_dir: Path,
    name: str,
    record: dict[str, Any],
    *,
    output: BinaryIO | None = None,
) -> tuple[str, str]:
    """Complete only this action's reserved file, never replace an existing log."""
    data = json.dumps(record, ensure_ascii=False, sort_keys=True, indent=1).encode("utf-8")
    if output is None:
        with _reserve_log(logs_dir, name, record) as reserved:
            return _write_log(logs_dir, name, record, output=reserved)
    output.seek(0)
    output.truncate()
    output.write(data)
    output.flush()
    return name, hashlib.sha256(data).hexdigest()


def _existing_state(
    plan: dict[str, Any],
    logs_dir: Path,
    prefix: str,
    provider_name: str,
    strict: bool,
    budget_origin: str,
    action_deadline_ms: int | None,
    wall_guard: WallGuard | None = None,
) -> tuple[int, dict[str, Any]]:
    """Locate the next log and reject counter resets or changed resume bytes."""
    pattern = re.compile(re.escape(prefix) + r"-(\d+)\.json\Z")
    expected: dict[str, str] = {}
    resume = plan.get("resume_summary")
    if resume is not None:
        if not isinstance(resume, dict) or resume.get("case_id") != plan["case_id"]:
            raise ValueError("Resume summary belongs to a different case")
        if resume.get("provider") != provider_name:
            raise ValueError("Resume summary belongs to a different provider")
        expected.update(resume.get("raw_logs", {}))
        for entry in resume.get("replay", []) + resume.get("actions", []):
            expected[entry["raw_log_path"]] = entry["raw_log_sha256"]
        if strict:
            # Earlier summaries lack the explicit field; their recorded names
            # still bind the prefix. Never verify one run's bytes but rebuild
            # budget/429 state from a different, empty filename namespace.
            if resume.get("log_prefix", prefix) != prefix or any(
                not isinstance(name, str) or not pattern.fullmatch(name) for name in expected
            ):
                raise ValueError("Resume log_prefix differs from the recorded run")
            if resume.get("budget_origin", budget_origin) != budget_origin:
                raise ValueError("Resume budget_origin differs from the recorded run")
            previous_policy = resume.get("tool_policy", {})
            if not isinstance(previous_policy, dict) or (
                _action_deadline(previous_policy, plan["max_ms"]) != action_deadline_ms
            ):
                raise ValueError("Resume action_deadline_ms differs from recorded policy")
            if "action_deadline_ms" in resume and (
                _action_deadline(resume, plan["max_ms"]) != action_deadline_ms
            ):
                raise ValueError("Resume action_deadline_ms differs from the recorded summary")
            if wall_guard is not None:
                _check_network_identity(resume, wall_guard)
                _check_network_identity(previous_policy, wall_guard)
        for name, sha in expected.items():
            if (
                not isinstance(name, str)
                or Path(name).name != name
                or not _SAFE_FILENAME.fullmatch(name)
            ):
                raise ValueError("Resume raw log path must be a safe filename")
            path = logs_dir / name
            if path.is_symlink() or not path.is_file():
                raise ValueError("Resume raw logs must be regular files")
            data = path.read_bytes()
            if hashlib.sha256(data).hexdigest() != sha:
                raise ValueError("Resume raw log hash mismatch")
    numbered = []
    for path in logs_dir.iterdir() if logs_dir.exists() else []:
        match = pattern.fullmatch(path.name)
        if wall_guard is not None and path.suffix == ".json" and not match:
            # A new prefix cannot turn the same case directory into a fresh
            # budget or hide its quota stop when resume_summary is omitted.
            if path.is_symlink() or not path.is_file():
                raise ValueError("Network raw logs must be regular files")
            if path.is_file():
                try:
                    other = json.loads(path.read_bytes())
                except (ValueError, UnicodeDecodeError):
                    other = None
                if (
                    isinstance(other, dict)
                    and other.get("case_id") == plan["case_id"]
                    and "request" in other
                    and "tool_policy" in other
                ):
                    raise ValueError("Network case already belongs to a different log_prefix")
        if match:
            if path.is_symlink() or not path.is_file():
                raise ValueError("Raw logs must be regular files")
            numbered.append((int(match[1]), path))
    state: dict[str, Any] = {}
    previous = (0, 0, 0)
    previous_completed_at = wall_guard.started_at if wall_guard is not None else None
    provider_stopped = False
    for _number, path in sorted(numbered):
        data = path.read_bytes()
        if path.name in expected and hashlib.sha256(data).hexdigest() != expected[path.name]:
            raise ValueError("Resume raw log hash mismatch")
        expected[path.name] = hashlib.sha256(data).hexdigest()
        record = json.loads(data)
        if record.get("outcome") == "pending":
            raise ValueError("Incomplete raw log: adjudicate the interrupted call before resuming")
        if strict:
            if record.get("case_id") != plan["case_id"] or record.get("provider") != provider_name:
                raise ValueError("Existing log case/provider differs from this run")
            if not (record.get("tool_policy") or {}).get("strict_budget"):
                raise ValueError("Cannot resume legacy logs as a strict run")
            if record["tool_policy"].get("budget_origin") != budget_origin:
                raise ValueError("Resume budget_origin differs from recorded policy")
            if wall_guard is not None:
                _check_network_identity(record, wall_guard)
                _check_network_identity(record["tool_policy"], wall_guard)
            for key, plan_key in (
                ("max_fetcher_calls", "max_calls"),
                ("max_elapsed_ms", "max_ms"),
                ("max_search_queries", "max_search_queries"),
            ):
                expected_cap = plan.get(plan_key, STRICT_MAX_SEARCH_QUERIES)
                if record["tool_policy"].get(key) != expected_cap:
                    raise ValueError("Resume budget differs from recorded policy")
            if _action_deadline(record["tool_policy"], plan["max_ms"]) != action_deadline_ms:
                raise ValueError("Resume action_deadline_ms differs from recorded policy")
            if record["tool_policy"].get("official_domains", []) != [
                _domain(d) for d in plan.get("official_domains", [])
            ]:
                raise ValueError("Resume official domains differ from recorded policy")
            counters = (
                _integer(record, "fetcher_calls_cumulative"),
                _integer(record, "elapsed_ms_cumulative"),
                _integer(record, "search_queries_cumulative", 0),
            )
            if any(value < old for value, old in zip(counters, previous, strict=True)):
                raise ValueError("Existing raw log counters decrease")
            if wall_guard is not None:
                at = parse_timestamp(record.get("at", ""))
                completed_at = parse_timestamp(record.get("completed_at", ""))
                if previous_completed_at is None or not previous_completed_at <= at <= completed_at:
                    raise ValueError("Existing network wall timestamps decrease")
                executed = record.get("executed")
                request = record.get("request") or {}
                if type(executed) is not bool or executed != bool(record.get("response")):
                    raise ValueError("Existing network executed flag disagrees with its response")
                calls = int(executed and request.get("tool") == "fetcher")
                queries = int(executed and request.get("tool") == "search_provider")
                elapsed = _integer(record, "elapsed_ms")
                if (
                    _integer(record, "elapsed_ms_before") != previous[1]
                    or _integer(record, "charged_elapsed_ms") != elapsed
                    or counters
                    != (previous[0] + calls, previous[1] + elapsed, previous[2] + queries)
                    or (not executed and elapsed != 0)
                ):
                    raise ValueError(
                        "Existing network counters differ from measured controlled actions"
                    )
                dispatch = record.get("dispatch_at")
                if executed:
                    if not isinstance(dispatch, str) or not (
                        at <= parse_timestamp(dispatch) < wall_guard.deadline_at
                        and parse_timestamp(dispatch) <= completed_at
                    ):
                        raise ValueError(
                            "Existing network dispatch exceeds its original wall guard"
                        )
                elif dispatch is not None:
                    raise ValueError("A refused network action cannot have a dispatch timestamp")
                previous_completed_at = completed_at
            previous = counters
        state = record
        provider_stopped = provider_stopped or record.get("stop_reason") == "http_429"
    if provider_stopped:
        state["stop_reason"] = "http_429"
    first = _integer(plan, "first_log_number", max((n for n, _p in numbered), default=0) + 1)
    if first < 1 or any(first <= number for number, _path in numbered):
        raise ValueError("first_log_number would overwrite an existing log")
    state["raw_logs"] = expected
    return first, state


def _check_network_identity(record: dict[str, Any], wall_guard: WallGuard) -> None:
    """Bind both a summary and its independently saved raw policy to one wall."""
    if record.get("budget_model") != BUDGET_MODEL:
        raise ValueError("Resume budget_model differs from recorded network policy")
    try:
        recorded_guard = parse_wall_guard(
            wall_started_at=record.get("wall_started_at", ""),
            wall_deadline_at=record.get("wall_deadline_at", ""),
        )
    except ValueError as exc:
        raise ValueError("Resume wall guard is missing or invalid") from exc
    if recorded_guard != wall_guard or record.get("wall_guard_ms") != WALL_GUARD_MS:
        raise ValueError("Resume wall guard differs from the recorded case")
    if any(
        type(record.get(key)) is not type(value) or record.get(key) != value
        for key, value in expert_budget().items()
    ):
        raise ValueError("Resume network policy metadata differs from the recorded case")


def _failure(exc: Exception, *, provider_name: str | None = None) -> dict[str, Any]:
    """Use only fixed categories/status; arbitrary exception text may contain keys."""
    from app.adapters.search.base import SearchFailureReason, search_failure_diagnostic

    status = getattr(exc, "http_status", None)
    if type(status) is not int or not 100 <= status <= 599:
        response = getattr(exc, "response", None)
        status = getattr(response, "status_code", None)
    if type(status) is not int or not 100 <= status <= 599:
        status = None
    reason = getattr(exc, "reason", None)
    return {
        "outcome": "provider_unavailable" if provider_name else "exception",
        "outcome_status": "failure",
        "error": search_failure_diagnostic(provider_name, exc)
        if provider_name
        else "Fetcher action failed; exception text withheld.",
        "http_status": status,
        "status_code": status,
        "failure_reason": reason.value if isinstance(reason, SearchFailureReason) else None,
    }


async def _fetch(get: Callable[[str], Awaitable[Any]], url: str) -> dict[str, Any]:
    result = await get(url)
    outcome = getattr(result.outcome, "value", str(result.outcome))
    body = result.content or b""
    response = {
        "outcome": outcome,
        "outcome_status": "success"
        if result.ok
        else "blocked"
        if outcome in {"blocked", "refused_privacy", "robots_disallowed", "robots_crawl_delay"}
        else "failure",
        "ok": bool(result.ok),
        "status_code": result.status_code,
        "final_url": result.final_url or result.url,
        "content_type": result.content_type,
        "from_cache": bool(result.from_cache),
        "fetch_tier": result.fetch_tier,
        "error": "" if not result.error else "Fetcher reported a failure; detail withheld.",
        "fetched_at": result.fetched_at.isoformat(),
        "content_sha256": hashlib.sha256(body).hexdigest(),
        "content_b64": base64.b64encode(body[:MAX_LOG_CONTENT_BYTES]).decode("ascii"),
    }
    if len(body) > MAX_LOG_CONTENT_BYTES:
        response.update(
            outcome="raw_content_limit_exceeded",
            outcome_status="failure",
            ok=False,
            content_b64="",
            content_bytes=len(body),
        )
    return response


def _search_domains(action: dict[str, Any], official_domains: tuple[str, ...]) -> list[str]:
    values = action.get("domains", [])
    if not isinstance(values, list) or any(not isinstance(d, str) for d in values):
        raise ValueError("Search domains must be a list of hostnames")
    domains = [_domain(d) for d in values] or list(official_domains)
    restrictions = list(domains)
    if any(
        not _allowed_url(match[0], official_domains)
        for match in _QUERY_URL.finditer(str(action["query"]))
    ):
        raise ValueError("Search query URL leaves the official tool policy")
    for match in _QUERY_DOMAIN.finditer(str(action["query"])):
        restriction = match[1].strip("\"'")
        restriction = _host(restriction) if "://" in restriction else restriction.split("/", 1)[0]
        restrictions.append(_domain(restriction))
    if any(not _allowed_url("https://" + domain, official_domains) for domain in restrictions):
        raise ValueError("Search query/domain leaves the official tool policy")
    return domains


async def execute(
    plan: dict[str, Any],
    logs_dir: Path,
    *,
    get: Callable[[str], Awaitable[Any]],
    search: Callable[..., Awaitable[Any]] | None,
    provider_name: str,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
    monotonic: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    """Execute a bounded plan. Injectable clocks/tools keep verification offline."""
    strict = plan.get("strict_budget", False)
    if type(strict) is not bool:
        raise ValueError("strict_budget must be a boolean")
    if strict and provider_name not in STRICT_PROVIDERS:
        raise ValueError("Strict expert runs require configured exa or exa_mcp")
    if plan.get("provider", provider_name) != provider_name:
        raise ValueError("Plan provider differs from the configured provider")
    max_calls, max_ms = _integer(plan, "max_calls"), _integer(plan, "max_ms")
    max_queries = _integer(plan, "max_search_queries", STRICT_MAX_SEARCH_QUERIES)
    if max_calls < 1 or max_ms < 1 or max_queries < 1:
        raise ValueError("Run budgets must be positive")
    origin = plan.get(
        "budget_origin", "independent_full_budget" if strict else "baseline_intervention"
    )
    if origin not in {
        "independent_full_budget",
        "baseline_intervention",
        NETWORK_COMPARISON_MODE,
    }:
        raise ValueError("Unsupported budget_origin")
    network = origin == NETWORK_COMPARISON_MODE
    wall_guard: WallGuard | None = None
    if network:
        if not strict or plan.get("budget_model") != BUDGET_MODEL:
            raise ValueError("Network mode requires strict network_actions_v1 policy")
        if (max_calls, max_queries, max_ms) != (
            MAX_FETCHER_CALLS,
            MAX_SEARCH_QUERIES,
            WALL_GUARD_MS,
        ):
            raise ValueError("Network mode requires exactly 60 reads, six queries and a 900s guard")
        if any(
            key in plan and (type(plan[key]) is not type(value) or plan[key] != value)
            for key, value in expert_budget().items()
        ):
            raise ValueError("Network plan metadata must declare the exact network policy")
        wall_guard = parse_wall_guard(
            wall_started_at=plan.get("wall_started_at", ""),
            wall_deadline_at=plan.get("wall_deadline_at", ""),
        )
        wall_guard.remaining_seconds(now=now())
        if plan.get("action_deadline_ms") is not None:
            raise ValueError("Network mode uses only its absolute wall hang guard")
    elif any(
        key in plan
        for key in ("budget_model", "wall_started_at", "wall_deadline_at", "wall_guard_ms")
    ):
        raise ValueError("Network wall policy requires the explicit network comparison mode")
    action_deadline_ms = _action_deadline(plan, max_ms)
    if (
        strict
        and not network
        and (
            max_calls > STRICT_MAX_CALLS
            or max_ms > STRICT_MAX_MS
            or max_queries > STRICT_MAX_SEARCH_QUERIES
        )
    ):
        raise ValueError("Strict run budget exceeds 60 Fetcher calls, 120 seconds or six queries")
    exploration = plan.get("exploration_mode", "same_policy")
    if exploration not in {"same_policy", "outside_policy"}:
        raise ValueError("exploration_mode must be same_policy or outside_policy")
    prefix = plan.get("log_prefix", plan["case_id"])
    if not isinstance(prefix, str) or not _SAFE_ID.fullmatch(prefix):
        raise ValueError("log_prefix/case_id must be a safe identifier")
    if not isinstance(plan["case_id"], str) or not _SAFE_ID.fullmatch(plan["case_id"]):
        raise ValueError("case_id must be a safe identifier")
    domains = plan.get("official_domains", [])
    if not isinstance(domains, list) or any(not isinstance(d, str) for d in domains):
        raise ValueError("official_domains must be a list of hostnames")
    official_domains = tuple(_domain(d) for d in domains)
    if strict and not official_domains:
        raise ValueError("Strict expert runs require independently resolved official_domains")
    if any(blocked("https://" + d) for d in official_domains):
        raise ValueError("Official domains cannot include a blocked repository host")
    number, state = _existing_state(
        plan, logs_dir, prefix, provider_name, strict, origin, action_deadline_ms, wall_guard
    )
    initial = {
        key: _integer(plan, key, int(state.get(record_key, 0)))
        for key, record_key in (
            ("start_calls", "fetcher_calls_cumulative"),
            ("start_ms", "elapsed_ms_cumulative"),
            ("start_search_queries", "search_queries_cumulative"),
        )
    }
    if strict and any(
        initial[key] < int(state.get(record_key, 0))
        for key, record_key in (
            ("start_calls", "fetcher_calls_cumulative"),
            ("start_ms", "elapsed_ms_cumulative"),
            ("start_search_queries", "search_queries_cumulative"),
        )
    ):
        raise ValueError("Resume counters cannot decrease")
    if network and any(
        initial[key] != int(state.get(record_key, 0))
        for key, record_key in (
            ("start_calls", "fetcher_calls_cumulative"),
            ("start_ms", "elapsed_ms_cumulative"),
            ("start_search_queries", "search_queries_cumulative"),
        )
    ):
        raise ValueError(
            "Network source counters must equal the independently measured previous counters"
        )
    ledger = Ledger(
        max_calls,
        max_ms,
        calls=initial["start_calls"],
        ms=initial["start_ms"],
        max_search_queries=max_queries if strict else None,
        search_queries=initial["start_search_queries"],
    )
    stop_reason = plan.get("stop_reason", state.get("stop_reason"))
    allowed_stops = {None, "http_429", "budget_exhausted", "action_deadline_exhausted"}
    if network:
        allowed_stops.add("wall_guard_exhausted")
    if stop_reason not in allowed_stops:
        raise ValueError("Unsupported stop_reason")
    if state.get("stop_reason") in {
        "http_429",
        "action_deadline_exhausted",
        "wall_guard_exhausted",
    }:
        stop_reason = state["stop_reason"]
    policy = {
        **TOOL_POLICY,
        "strict_budget": strict,
        "official_domains": list(official_domains),
        "allowed_search_providers": sorted(STRICT_PROVIDERS) if strict else [provider_name],
        "max_search_queries": max_queries if strict else None,
        "max_fetcher_calls": max_calls,
        "max_elapsed_ms": max_ms,
        "budget_origin": origin,
    }
    if action_deadline_ms is not None:
        policy["action_deadline_ms"] = action_deadline_ms
    network_metadata = {**expert_budget(), **wall_guard.as_dict()} if wall_guard is not None else {}
    policy.update(network_metadata)
    if network:
        policy["exploration_mode"] = exploration
    summary: dict[str, Any] = {
        "case_id": plan["case_id"],
        "provider": provider_name,
        "log_prefix": prefix,
        "tool_policy": policy,
        "budget_origin": origin,
        "initial": initial,
        "raw_logs": state.get("raw_logs", {}),
        "replay": [],
        "actions": [],
    }
    if action_deadline_ms is not None:
        summary["action_deadline_ms"] = action_deadline_ms
    summary.update(network_metadata)
    run_began = monotonic()
    previous_wall_at = (
        parse_timestamp(state["completed_at"], field="completed_at")
        if wall_guard is not None and "completed_at" in state
        else wall_guard.started_at
        if wall_guard is not None
        else None
    )
    for kind, items in (("replay", plan.get("replay", [])), ("actions", plan.get("actions", []))):
        for item in items:
            action: dict[str, Any] = (
                {"tool": "fetcher", "url": item} if isinstance(item, str) else dict(item)
            )
            tool = action.get("tool")
            if tool not in {"fetcher", "search_provider"}:
                raise ValueError("Unsupported expert tool")
            name = f"{prefix}-{number:03d}.json"
            if (logs_dir / name).exists() or (logs_dir / name).is_symlink():
                raise ValueError("Raw log already exists")
            at = now().isoformat()
            if wall_guard is not None:
                action_at = parse_timestamp(at)
                wall_guard.remaining_seconds(now=action_at)
                if previous_wall_at is not None and action_at < previous_wall_at:
                    raise ValueError("Wall clock precedes the preceding controller action")
                at = action_at.isoformat()
            began = monotonic()
            if strict and not network:
                ledger.ms = max(
                    ledger.ms, initial["start_ms"] + math.ceil((began - run_began) * 1000)
                )
            record: dict[str, Any] = {
                "request": action,
                "at": at,
                "phase": kind,
                "case_id": plan["case_id"],
                "provider": provider_name,
                "log_prefix": prefix,
                "tool_policy": policy,
                "budget_origin": origin,
                "elapsed_ms_before": ledger.ms,
                "budgets": {
                    "max_calls": max_calls,
                    "max_ms": max_ms,
                    "max_search_queries": max_queries if strict else None,
                },
                **network_metadata,
            }
            with _reserve_log(logs_dir, name, record) as output:
                refusal: str | None = None
                if tool == "fetcher":
                    url = str(action["url"])
                    if blocked(url):
                        refusal = "blocked_by_tool_policy"
                    elif (official_domains or strict) and not _allowed_url(url, official_domains):
                        refusal = "blocked_by_official_domains"
                else:
                    if search is None:
                        refusal = "search_provider_not_configured"
                    try:
                        action["domains"] = _search_domains(action, official_domains)
                        if not isinstance(action["query"], str) or not action["query"].strip():
                            raise ValueError("Search query must be nonempty text")
                        if (
                            type(action.get("max_results", 10)) is not int
                            or not 1 <= action.get("max_results", 10) <= 100
                        ):
                            raise ValueError("Search result limit must be 1..100")
                    except ValueError:
                        refusal = "blocked_by_tool_policy"
                if tool == "search_provider" and stop_reason == "http_429":
                    refusal = "stopped_after_http_429"
                wall_remaining_seconds: float | None = None
                network_timeout_at: float | None = None
                if wall_guard is not None:
                    # Capture the loop anchor before reading UTC. Setup after
                    # this point consumes the existing period, never renews it.
                    loop_anchor = asyncio.get_running_loop().time()
                    dispatch_at = parse_timestamp(now().isoformat())
                    wall_remaining_seconds = wall_guard.remaining_seconds(now=dispatch_at)
                    network_timeout_at = loop_anchor + wall_remaining_seconds
                    if dispatch_at < action_at:
                        raise ValueError("Wall clock decreased before dispatch")
                    if wall_remaining_seconds <= 0 or stop_reason == "wall_guard_exhausted":
                        refusal = "wall_guard_exhausted"
                        stop_reason = stop_reason or "wall_guard_exhausted"
                    record["dispatch_at"] = dispatch_at.isoformat() if refusal is None else None
                action_start_ms = ledger.ms
                if strict and action_deadline_ms is not None:
                    # Log reservation and input checks consume active time too.
                    # Recheck immediately before allowing any outbound action.
                    action_start_ms = max(
                        ledger.ms,
                        initial["start_ms"] + math.ceil((monotonic() - run_began) * 1000),
                    )
                exhausted = strict and (
                    (not network and action_start_ms >= ledger.max_ms)
                    or (tool == "fetcher" and ledger.calls >= ledger.max_calls)
                    or (tool == "search_provider" and ledger.search_queries >= max_queries)
                )
                if refusal is None and exhausted and exploration != "outside_policy":
                    refusal = "budget_exhausted"
                    stop_reason = stop_reason or "budget_exhausted"
                if (
                    refusal is None
                    and strict
                    and action_deadline_ms is not None
                    and action_start_ms >= action_deadline_ms
                ):
                    refusal = "action_deadline_exhausted"
                    stop_reason = stop_reason or "action_deadline_exhausted"
                calls = queries = 0
                deadline_floor = 0
                if refusal:
                    if network:
                        record["dispatch_at"] = None
                    record.update(outcome=refusal, outcome_status="blocked", executed=False)
                    elapsed = 0
                else:
                    record["executed"] = not network
                    calls = int(not network and tool == "fetcher")
                    queries = int(not network and tool == "search_provider")
                    action_budget_ms = (
                        max_ms if exploration == "outside_policy" else max_ms - action_start_ms
                    )
                    navigation_limited = (
                        strict
                        and action_deadline_ms is not None
                        and action_deadline_ms - action_start_ms < action_budget_ms
                    )
                    if strict and action_deadline_ms is not None:
                        action_budget_ms = min(
                            action_budget_ms, action_deadline_ms - action_start_ms
                        )
                    try:
                        timeout_seconds = (
                            wall_remaining_seconds
                            if network
                            else max(1, action_budget_ms) / 1000
                            if strict
                            else None
                        )
                        deadline_context = (
                            asyncio.timeout_at(network_timeout_at)
                            if network
                            else asyncio.timeout(timeout_seconds)
                        )
                        async with deadline_context as deadline:
                            if wall_guard is not None:
                                actual_dispatch = parse_timestamp(now().isoformat())
                                if actual_dispatch < dispatch_at:
                                    raise ValueError("Wall clock decreased during timeout setup")
                                if wall_guard.remaining_seconds(now=actual_dispatch) <= 0 or (
                                    network_timeout_at is not None
                                    and asyncio.get_running_loop().time() >= network_timeout_at
                                ):
                                    raise _WallGuardRefused
                                record["dispatch_at"] = actual_dispatch.isoformat()
                                record["executed"] = True
                                calls = int(tool == "fetcher")
                                queries = int(tool == "search_provider")
                            if tool == "fetcher":
                                response = await _fetch(get, url)
                                final_url = response["final_url"]
                                if blocked(final_url) or (
                                    (official_domains or strict)
                                    and not _allowed_url(final_url, official_domains)
                                ):
                                    response.update(
                                        outcome="blocked_by_final_url_policy",
                                        outcome_status="blocked",
                                        ok=False,
                                        content_b64="",
                                        error="Final URL is outside tool policy.",
                                    )
                                record["response"] = response
                            else:
                                assert search is not None
                                answer = await search(
                                    query=str(action["query"]),
                                    domains=action["domains"],
                                    max_results=action.get("max_results", 10),
                                )
                                results = [
                                    {
                                        "rank": r.rank,
                                        "url": r.url,
                                        "title": r.title,
                                        "snippet": r.snippet,
                                    }
                                    for r in answer.results
                                ]
                                record["response"] = {
                                    "outcome": "ok",
                                    "outcome_status": "success",
                                    "results": [
                                        r
                                        for r in results
                                        if _allowed_url(r["url"], official_domains)
                                    ],
                                    "dropped_by_tool_policy": sum(
                                        not _allowed_url(r["url"], official_domains)
                                        for r in results
                                    ),
                                }
                            if network and deadline.expired():
                                raise TimeoutError
                    except _WallGuardRefused:
                        refusal = "wall_guard_exhausted"
                        calls = queries = 0
                        stop_reason = stop_reason or "wall_guard_exhausted"
                        record.update(
                            outcome=refusal,
                            outcome_status="blocked",
                            executed=False,
                            dispatch_at=None,
                        )
                    except TimeoutError:
                        record["response"] = {
                            "outcome": "action_timeout",
                            "outcome_status": "failure",
                            "error": "Action exceeded the remaining run deadline.",
                        }
                        if strict:
                            stop_reason = stop_reason or (
                                "wall_guard_exhausted"
                                if network
                                else "action_deadline_exhausted"
                                if navigation_limited
                                else "budget_exhausted"
                            )
                            if network:
                                record["timeout_reason"] = "wall_guard_exhausted"
                            elif navigation_limited:
                                assert action_deadline_ms is not None
                                deadline_floor = action_deadline_ms
                            else:
                                deadline_floor = max_ms
                    except Exception as exc:
                        if network and not record["executed"]:
                            # Keep the reserved pending record rather than
                            # inventing a source attempt for invalid setup.
                            raise
                        record["response"] = _failure(
                            exc, provider_name=provider_name if tool == "search_provider" else None
                        )
                        if tool == "search_provider" and record["response"]["http_status"] == 429:
                            stop_reason = "http_429"
                    elapsed = (
                        max(0, math.ceil((monotonic() - began) * 1000)) if record["executed"] else 0
                    )
                    if record["executed"]:
                        record["outcome_status"] = record["response"]["outcome_status"]
                if wall_guard is not None:
                    completed_at = parse_timestamp(now().isoformat())
                    wall_guard.remaining_seconds(now=completed_at)
                    if completed_at < action_at or (
                        record["dispatch_at"] is not None
                        and completed_at < parse_timestamp(record["dispatch_at"])
                    ):
                        raise ValueError("Wall clock decreased during a controller action")
                    if completed_at >= wall_guard.deadline_at:
                        stop_reason = stop_reason or "wall_guard_exhausted"
                        if record["executed"] and record["outcome_status"] == "success":
                            # Bytes returned after cancellation/deadline cannot
                            # become successful evidence, even if a tool catches
                            # cancellation or blocks the loop while serializing.
                            record["response"].update(
                                outcome="action_timeout",
                                outcome_status="failure",
                                ok=False,
                                content_b64="",
                                results=[],
                                error="Action returned after the absolute wall hang guard.",
                            )
                            record["outcome_status"] = "failure"
                            record["timeout_reason"] = "wall_guard_exhausted"
                    record["completed_at"] = completed_at.isoformat()
                    record["wall_elapsed_ms"] = math.ceil(
                        (completed_at - wall_guard.started_at).total_seconds() * 1000
                    )
                    previous_wall_at = completed_at
                if strict and not network:
                    elapsed_total = max(
                        ledger.ms + elapsed,
                        initial["start_ms"] + math.ceil((monotonic() - run_began) * 1000),
                        deadline_floor,
                    )
                    charge_ms = elapsed_total - ledger.ms
                else:
                    charge_ms = elapsed
                mode = ledger.charge(calls=calls, ms=charge_ms, search_queries=queries)
                if (
                    exploration == "outside_policy"
                    or refusal
                    or (record.get("response") or {}).get("outcome")
                    == "blocked_by_final_url_policy"
                ):
                    mode = "outside_policy"
                record.update(
                    elapsed_ms=elapsed,
                    charged_elapsed_ms=charge_ms,
                    fetcher_calls_cumulative=ledger.calls,
                    elapsed_ms_cumulative=ledger.ms,
                    search_queries_cumulative=ledger.search_queries,
                    policy_mode=mode,
                    stop_reason=stop_reason,
                )
                name, sha = _write_log(logs_dir, name, record, output=output)
                summary["raw_logs"][name] = sha
                number += 1
                response = record.get("response") or {}
                summary[kind].append(
                    {
                        "raw_log_path": name,
                        "raw_log_sha256": sha,
                        "at": at,
                        "tool": tool,
                        "request": action,
                        "outcome": record.get("outcome") or response.get("outcome") or "ok",
                        "outcome_status": record["outcome_status"],
                        "executed": record["executed"],
                        "final_url": response.get("final_url"),
                        "elapsed_ms": elapsed,
                        "fetcher_calls_cumulative": ledger.calls,
                        "elapsed_ms_cumulative": ledger.ms,
                        "search_queries_cumulative": ledger.search_queries,
                        "policy_mode": mode,
                    }
                )
    summary["final"] = {
        "fetcher_calls": ledger.calls,
        "elapsed_ms": ledger.ms,
        "search_queries": ledger.search_queries,
        "stop_reason": stop_reason,
        "next_log_number": number,
    }
    if wall_guard is not None:
        completed_at = parse_timestamp(now().isoformat())
        wall_guard.remaining_seconds(now=completed_at)
        if previous_wall_at is not None and completed_at < previous_wall_at:
            raise ValueError("Wall clock precedes the preceding controller action")
        wall_expired = completed_at >= wall_guard.deadline_at
        summary["final"].update(
            wall_elapsed_ms=math.ceil(
                (completed_at - wall_guard.started_at).total_seconds() * 1000
            ),
            completed_at=completed_at.isoformat(),
            wall_guard_exhausted=wall_expired or stop_reason == "wall_guard_exhausted",
            stop_reason=stop_reason or ("wall_guard_exhausted" if wall_expired else None),
        )
    return summary


async def run(plan_path: Path, logs_dir: Path, cache_dir: Path) -> dict[str, Any]:
    """Use the configured provider, cold Fetcher reads in strict mode, no fallback."""
    from app.adapters.fetching import Fetcher
    from app.adapters.search import SearchProviderNotConfigured, get_search_provider
    from app.config import get_settings

    settings = get_settings()
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    strict = plan.get("strict_budget", False)
    if strict and settings.search_provider not in STRICT_PROVIDERS:
        raise ValueError("Strict expert runs require configured exa or exa_mcp")
    try:
        provider = get_search_provider()
        search = provider.search
        provider_name = settings.search_provider
        if strict and provider.name != provider_name:
            raise ValueError("Configured provider identity mismatch")
    except SearchProviderNotConfigured:
        search, provider_name = None, "none"
    async with Fetcher(
        cache_dir,
        delay_seconds=settings.fetch_delay_seconds,
        respect_robots=True if strict else settings.respect_robots,
        timeout=settings.fetch_timeout_seconds,
        contact=settings.fetch_contact,
    ) as fetcher:

        async def get(url: str) -> Any:
            return await fetcher.get(url, use_cache=not strict)

        return await execute(plan, logs_dir, get=get, search=search, provider_name=provider_name)


def expert_view(
    record: dict[str, Any],
    *,
    chars: int = 6000,
    links: int = 120,
    offset: int = 0,
    link_offset: int = 0,
    sections: int = 80,
    section_offset: int = 0,
    page: int | None = None,
) -> dict[str, Any]:
    """Paginate exact readable text, named IR blocks and discovery links from a raw log.

    Pagination reads stored bytes only. Text and section hashes cover the full
    representation, so later pages can be verified against the same source.
    PDF ``page`` is one-based and selects the exact page text; omitting it
    returns the production aggregate. Only the first forty pages are parsed.
    """
    from app.adapters.document_ir import build_document_ir
    from app.adapters.extraction import pdf_to_text, readable_text

    if any(
        type(n) is not int or n < 0
        for n in (chars, links, offset, link_offset, sections, section_offset)
    ):
        raise ValueError("View limits and offsets must be nonnegative integers")
    if page is not None and (type(page) is not int or not 1 <= page <= 40):
        raise ValueError("PDF page must be an integer from 1 to 40")
    chars, links, sections = (
        min(chars, MAX_VIEW_CHARS),
        min(links, MAX_VIEW_ITEMS),
        min(sections, MAX_VIEW_ITEMS),
    )
    view: dict[str, Any] = {
        "request": record["request"],
        "policy_mode": record["policy_mode"],
        "outcome_status": record.get("outcome_status"),
    }
    response = record.get("response") or {}
    if "results" in response or record.get("outcome"):
        view.update(dict(response))
        view["outcome"] = record.get("outcome", view.get("outcome"))
        return view
    view.update(
        {
            k: response.get(k)
            for k in (
                "outcome",
                "status_code",
                "http_status",
                "final_url",
                "content_type",
                "error",
                "failure_reason",
                "fetched_at",
                "content_sha256",
                "from_cache",
                "fetch_tier",
            )
        }
    )
    body = base64.b64decode(response.get("content_b64", "") or b"", validate=True)
    expected_hash = response.get("content_sha256")
    if body and expected_hash and hashlib.sha256(body).hexdigest() != expected_hash:
        raise ValueError("Stored content hash mismatch")
    content_type = (response.get("content_type") or "").lower()
    if page is not None and "pdf" not in content_type:
        raise ValueError("A page number requires a stored PDF response")
    text = ""
    if body and "html" in (response.get("content_type") or "").lower():
        html = body.decode("utf-8", errors="replace")
        text = readable_text(html)
        doc = build_document_ir(html, response.get("final_url") or record["request"]["url"])
        view["title"] = doc.title
        blocks = [asdict(block) for block in doc.blocks]
        view.update(
            sections=blocks[section_offset : section_offset + sections],
            sections_total=len(blocks),
            sections_sha256=hashlib.sha256(
                json.dumps(blocks, sort_keys=True, ensure_ascii=False).encode("utf-8")
            ).hexdigest(),
            sections_offset=section_offset,
            sections_next_offset=section_offset + sections
            if section_offset + sections < len(blocks) and sections
            else None,
        )
        domains = tuple((record.get("tool_policy") or {}).get("official_domains", []))
        seen: list[dict[str, str]] = []
        for link in doc.links:
            if _allowed_url(link.url, domains) and all(s["url"] != link.url for s in seen):
                seen.append({"url": link.url, "text": link.text})
        view.update(
            links=seen[link_offset : link_offset + links],
            links_total=len(seen),
            links_offset=link_offset,
            links_next_offset=link_offset + links
            if link_offset + links < len(seen) and links
            else None,
        )
    elif "pdf" in content_type:
        import io

        view.update(
            pdf_page=page,
            pdf_pages=[],
            pdf_pages_total=None,
            pdf_pages_read=0,
            pdf_page_limit_reached=False,
            pdf_status="unresolved",
            pdf_error="pdf_payload_unavailable",
            text="",
            text_offset=offset,
            text_total_chars=0,
            text_sha256=hashlib.sha256(b"").hexdigest(),
            text_next_offset=None,
        )
        if body:
            try:
                from pypdf import PdfReader

                reader = PdfReader(io.BytesIO(body))
                total_pages = len(reader.pages)
                page_texts = [(item.extract_text() or "") for item in reader.pages[:40]]
                aggregate = pdf_to_text(body, max_pages=40)
            except ImportError:
                view["pdf_error"] = "pdf_parser_unavailable"
            except Exception:
                # PDF content is untrusted. Keep a fixed observable failure,
                # never a byte placeholder or arbitrary exception text.
                view["pdf_error"] = "pdf_decode_error"
            else:
                if page is not None and page > len(page_texts):
                    raise ValueError("PDF page does not exist in the stored document")
                view.update(
                    pdf_pages=[
                        {
                            "page": index + 1,
                            "text_total_chars": len(value),
                            "text_sha256": hashlib.sha256(value.encode("utf-8")).hexdigest(),
                            "has_text": bool(value.strip()),
                        }
                        for index, value in enumerate(page_texts)
                    ],
                    pdf_pages_total=total_pages,
                    pdf_pages_read=len(page_texts),
                    pdf_page_limit_reached=total_pages > 40,
                )
                text = page_texts[page - 1] if page is not None else aggregate
                if text.strip() and aggregate.strip():
                    view.update(pdf_status="readable", pdf_error=None)
                else:
                    text = ""
                    view["pdf_error"] = (
                        "pdf_decode_error"
                        if any(value.strip() for value in page_texts) and not aggregate.strip()
                        else "pdf_no_extractable_text"
                    )
    elif body and any(
        t in (response.get("content_type") or "").lower() for t in ("xml", "text/plain")
    ):
        text = body.decode("utf-8", errors="replace")
    elif body:
        text = f"[{len(body)} bytes of {response.get('content_type')}; pure parsing required]"
    if text:
        view.update(
            text=text[offset : offset + chars],
            text_offset=offset,
            text_total_chars=len(text),
            text_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
            text_next_offset=offset + chars if offset + chars < len(text) and chars else None,
        )
    return view


def main(argv: Sequence[str] | None = None) -> None:
    import argparse

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
