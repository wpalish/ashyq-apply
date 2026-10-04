"""Offline safeguards for strict, resumable expert pilots."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from app.adapters.search.base import SearchFailureReason, SearchUnavailable
from evaluation.research.expert.controller import blocked, execute, expert_view, run


@dataclass
class _Outcome:
    value: str


@dataclass
class _Page:
    url: str
    content: bytes = b"<h1>Admissions</h1><p>Official text</p>"
    ok: bool = True
    status_code: int = 200
    final_url: str = ""
    content_type: str = "text/html"
    from_cache: bool = False
    fetch_tier: str = "http"
    error: str = ""
    fetched_at: datetime = datetime(2026, 10, 4, tzinfo=UTC)
    outcome: _Outcome = field(default_factory=lambda: _Outcome("ok"))


@dataclass
class _Hit:
    rank: int
    url: str
    title: str = "Programme"
    snippet: str = "Discovery hint"


@dataclass
class _Answer:
    results: tuple[_Hit, ...] = ()


def _plan(**extra: Any) -> dict[str, Any]:
    return {
        "case_id": "guard",
        "max_calls": 60,
        "max_ms": 120_000,
        "max_search_queries": 6,
        "strict_budget": True,
        "official_domains": ["u.edu"],
        **extra,
    }


async def _get(url: str) -> _Page:
    return _Page(url)


def _record(tmp_path: Path, entry: dict[str, Any]) -> dict[str, Any]:
    data = (tmp_path / entry["raw_log_path"]).read_bytes()
    assert hashlib.sha256(data).hexdigest() == entry["raw_log_sha256"]
    return json.loads(data)


def _execute(tmp_path: Path, plan: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    return asyncio.run(
        execute(
            plan,
            tmp_path,
            get=kwargs.pop("get", _get),
            search=kwargs.pop("search", None),
            provider_name=kwargs.pop("provider_name", "exa_mcp"),
            **kwargs,
        )
    )


def test_six_search_queries_include_failed_attempts_and_refuse_seventh(tmp_path: Path) -> None:
    called: list[dict[str, Any]] = []

    async def search(**kwargs: Any) -> _Answer:
        called.append(kwargs)
        if len(called) == 2:
            raise SearchUnavailable(
                "vendor body must not appear", reason=SearchFailureReason.TRANSPORT
            )
        return _Answer((_Hit(1, "https://u.edu/programme"),))

    summary = _execute(
        tmp_path,
        _plan(actions=[{"tool": "search_provider", "query": f"programme {i}"} for i in range(7)]),
        search=search,
    )
    assert len(called) == 6
    assert all(c["domains"] == ["u.edu"] for c in called)
    assert summary["final"]["search_queries"] == 6
    assert summary["final"]["fetcher_calls"] == 0
    assert [entry["search_queries_cumulative"] for entry in summary["actions"]] == [
        1,
        2,
        3,
        4,
        5,
        6,
        6,
    ]
    assert summary["actions"][1]["outcome_status"] == "failure"
    assert summary["actions"][-1]["outcome"] == "budget_exhausted"
    assert summary["actions"][-1]["policy_mode"] == "outside_policy"
    assert "vendor body" not in json.dumps(_record(tmp_path, summary["actions"][1]))


def test_provider_429_is_sanitized_stops_calls_and_survives_resume(tmp_path: Path) -> None:
    calls = 0

    async def search(**kwargs: Any) -> _Answer:
        nonlocal calls
        calls += 1
        raise SearchUnavailable("Bearer sk-secret vendor URL ?api_key=hidden", http_status=429)

    action = {"tool": "search_provider", "query": "programme"}
    first = _execute(tmp_path, _plan(actions=[action, action]), search=search)
    assert calls == 1
    assert first["actions"][0]["outcome_status"] == "failure"
    record = _record(tmp_path, first["actions"][0])
    assert record["response"]["http_status"] == record["response"]["status_code"] == 429
    assert "sk-secret" not in json.dumps(record) and "api_key" not in json.dumps(record)
    assert first["actions"][1]["outcome"] == "stopped_after_http_429"
    assert first["final"]["stop_reason"] == "http_429"
    resumed = _execute(
        tmp_path,
        _plan(
            actions=[action],
            resume_summary=first,
            start_ms=first["final"]["elapsed_ms"] + 200,
            stop_reason=None,
        ),
        search=search,
    )
    assert calls == 1
    assert resumed["actions"][0]["raw_log_path"] == "guard-003.json"
    assert resumed["actions"][0]["outcome"] == "stopped_after_http_429"
    assert resumed["final"]["search_queries"] == 1
    assert resumed["final"]["stop_reason"] == "http_429"


def test_replay_and_incremental_actions_share_fetch_search_and_time_budget(tmp_path: Path) -> None:
    clock = [1.0]

    async def get(url: str) -> _Page:
        clock[0] += 0.04
        return _Page(url)

    first = _execute(
        tmp_path,
        _plan(max_calls=2, replay=["https://u.edu/baseline"]),
        get=get,
        monotonic=lambda: clock[0],
    )
    resumed = _execute(
        tmp_path,
        _plan(
            max_calls=2,
            actions=["https://u.edu/action", "https://u.edu/extra"],
            resume_summary=first,
            start_ms=first["final"]["elapsed_ms"] + 500,
        ),
        get=get,
        monotonic=lambda: clock[0],
    )
    assert resumed["initial"]["start_calls"] == 1
    assert resumed["final"]["fetcher_calls"] == 2
    assert resumed["final"]["elapsed_ms"] >= 580
    assert resumed["actions"][0]["executed"] is True
    assert resumed["actions"][1]["executed"] is False
    assert resumed["actions"][1]["outcome_status"] == "blocked"


@pytest.mark.parametrize("extra", [{"start_calls": 60}, {"start_ms": 120_000}])
def test_exhausted_initial_budget_makes_no_fetcher_call(
    tmp_path: Path, extra: dict[str, int]
) -> None:
    async def get(url: str) -> _Page:
        raise AssertionError("budget must refuse before get")

    summary = _execute(tmp_path, _plan(actions=["https://u.edu/"], **extra), get=get)
    assert summary["actions"][0]["executed"] is False
    assert summary["actions"][0]["outcome"] == "budget_exhausted"


def test_monotonic_wall_time_between_actions_is_also_charged(tmp_path: Path) -> None:
    ticks = iter([0.0, 0.121, 0.121])

    async def get(url: str) -> _Page:
        raise AssertionError("elapsed selection/overhead time spent the remaining budget")

    summary = _execute(
        tmp_path,
        _plan(max_ms=120, actions=["https://u.edu/"]),
        get=get,
        monotonic=lambda: next(ticks),
    )
    assert summary["final"]["elapsed_ms"] == 121
    assert summary["actions"][0]["executed"] is False


def test_asyncio_deadline_cancels_hanging_action_and_preserves_attempt_count(
    tmp_path: Path,
) -> None:
    cancelled = False
    called: list[str] = []

    async def get(url: str) -> _Page:
        nonlocal cancelled
        called.append(url)
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            cancelled = True
            raise
        raise AssertionError("cannot finish")

    # A controlled measurement clock does not disable the real asyncio deadline.
    summary = _execute(
        tmp_path,
        _plan(max_ms=10, actions=["https://u.edu/a", "https://u.edu/b"]),
        get=get,
        monotonic=lambda: 0.0,
    )
    assert cancelled
    assert called == ["https://u.edu/a"]
    assert summary["actions"][0]["outcome"] == "action_timeout"
    assert summary["actions"][0]["outcome_status"] == "failure"
    assert summary["actions"][1]["executed"] is False
    assert summary["final"]["fetcher_calls"] == 1
    assert summary["final"]["elapsed_ms"] == 10


def test_explicit_diagnostic_exploration_is_always_outside_policy(tmp_path: Path) -> None:
    summary = _execute(
        tmp_path,
        _plan(
            max_calls=1,
            start_calls=1,
            exploration_mode="outside_policy",
            actions=["https://u.edu/a", "https://u.edu/b"],
        ),
    )
    assert summary["final"]["fetcher_calls"] == 3
    assert all(entry["policy_mode"] == "outside_policy" for entry in summary["actions"])
    early = _execute(
        tmp_path / "early",
        _plan(
            exploration_mode="outside_policy",
            actions=["https://u.edu/a"],
        ),
    )
    assert early["actions"][0]["policy_mode"] == "outside_policy"


@pytest.mark.parametrize("provider", ["serper", "tavily", "fake", "none"])
def test_strict_provider_selection_never_calls_other_providers(
    tmp_path: Path, provider: str
) -> None:
    async def search(**kwargs: Any) -> _Answer:
        raise AssertionError("provider selection must fail before search")

    with pytest.raises(ValueError, match="configured exa or exa_mcp"):
        _execute(
            tmp_path,
            _plan(actions=[{"tool": "search_provider", "query": "q"}]),
            search=search,
            provider_name=provider,
        )
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    "extra", [{"max_calls": 61}, {"max_ms": 120_001}, {"max_search_queries": 7}]
)
def test_fresh_strict_plan_cannot_expand_caps(tmp_path: Path, extra: dict[str, int]) -> None:
    with pytest.raises(ValueError, match="Strict run budget exceeds"):
        _execute(tmp_path, _plan(**extra))


def test_domain_guards_distinguish_blocked_inputs_from_executed_redirect_or_robots(
    tmp_path: Path,
) -> None:
    called: list[str] = []

    async def get(url: str) -> _Page:
        called.append(url)
        if url.endswith("redirect"):
            return _Page(url, final_url="https://u.edu.evil/programme")
        return _Page(
            url,
            content=b"",
            ok=False,
            outcome=_Outcome("robots_disallowed"),
            error="robots disallowed",
        )

    summary = _execute(
        tmp_path,
        _plan(
            actions=[
                "https://u.edu.evil/a",
                "https://github.com./repo",
                "https://u.edu/redirect",
                "https://u.edu/robots",
            ]
        ),
        get=get,
    )
    assert called == ["https://u.edu/redirect", "https://u.edu/robots"]
    assert [a["fetcher_calls_cumulative"] for a in summary["actions"]] == [0, 0, 1, 2]
    assert summary["actions"][2]["outcome"] == "blocked_by_final_url_policy"
    assert summary["actions"][2]["policy_mode"] == "outside_policy"
    assert summary["actions"][3]["policy_mode"] == "same_policy"
    assert all(a["outcome_status"] == "blocked" for a in summary["actions"])
    redirect = _record(tmp_path, summary["actions"][2])
    assert redirect["response"]["content_b64"] == ""
    assert redirect["response"]["final_url"] == "https://u.edu.evil/programme"
    assert blocked("https://raw.githubusercontent.com./answer")


def test_exact_official_subdomain_restricts_redirect_and_search_results(tmp_path: Path) -> None:
    async def get(url: str) -> _Page:
        return _Page(url, final_url="https://www.u.edu/page")

    async def search(**kwargs: Any) -> _Answer:
        return _Answer(
            (_Hit(1, "https://admissions.u.edu/page"), _Hit(2, "https://www.u.edu/page"))
        )

    summary = _execute(
        tmp_path,
        _plan(
            official_domains=["admissions.u.edu"],
            actions=[
                "https://admissions.u.edu/start",
                {"tool": "search_provider", "query": "requirements"},
            ],
        ),
        get=get,
        search=search,
    )
    assert summary["actions"][0]["outcome_status"] == "blocked"
    result = _record(tmp_path, summary["actions"][1])["response"]
    assert result["results"] == [
        {
            "rank": 1,
            "url": "https://admissions.u.edu/page",
            "title": "Programme",
            "snippet": "Discovery hint",
        }
    ]
    assert result["dropped_by_tool_policy"] == 1


@pytest.mark.parametrize(
    "action",
    [
        {"tool": "search_provider", "query": "q", "domains": ["u.edu.evil"]},
        {"tool": "search_provider", "query": "site:github.com/answers q"},
        {"tool": "search_provider", "query": "site:https://u.edu.evil/ q"},
        {"tool": "search_provider", "query": "q", "domains": ["u.edu/path"]},
        {"tool": "search_provider", "query": "q https://github.com/answers"},
        {"tool": "search_provider", "query": "q", "max_results": "wrong"},
    ],
)
def test_foreign_search_domain_or_query_restriction_is_refused(
    tmp_path: Path, action: dict[str, Any]
) -> None:
    async def search(**kwargs: Any) -> _Answer:
        raise AssertionError("must not query outside allowed domains")

    summary = _execute(tmp_path, _plan(actions=[action]), search=search)
    assert summary["final"]["search_queries"] == 0
    assert summary["actions"][0]["outcome_status"] == "blocked"


@pytest.mark.parametrize("domains", [[], None, "u.edu"])
def test_strict_unknown_official_domains_fail_before_any_outbound_action(
    tmp_path: Path,
    domains: Any,
) -> None:
    async def get(url: str) -> _Page:
        raise AssertionError("unknown official identity must be independently resolved first")

    async def search(**kwargs: Any) -> _Answer:
        raise AssertionError("cannot search without strict official domains")

    with pytest.raises(ValueError, match="official_domains"):
        _execute(
            tmp_path,
            _plan(
                official_domains=domains,
                actions=[
                    "https://unknown.edu/",
                    {"tool": "search_provider", "query": "unknown institution"},
                ],
            ),
            get=get,
            search=search,
        )
    assert not list(tmp_path.iterdir())


def test_separate_search_start_counter_is_enforced_on_resumed_plan(tmp_path: Path) -> None:
    called = 0

    async def search(**kwargs: Any) -> _Answer:
        nonlocal called
        called += 1
        return _Answer()

    action = {"tool": "search_provider", "query": "programme"}
    summary = _execute(
        tmp_path, _plan(start_search_queries=5, actions=[action, action]), search=search
    )
    assert called == 1
    assert summary["final"]["search_queries"] == 6
    with pytest.raises(ValueError, match="cannot decrease"):
        _execute(tmp_path, _plan(start_search_queries=0, actions=[action]), search=search)
    assert called == 1


@pytest.mark.parametrize(
    "extra",
    [
        {"case_id": "../escape"},
        {"log_prefix": "/absolute"},
        {"log_prefix": "a/b"},
        {"log_prefix": ".."},
        {"first_log_number": 0},
    ],
)
def test_unsafe_log_identity_is_refused_before_tools(tmp_path: Path, extra: dict[str, Any]) -> None:
    async def get(url: str) -> _Page:
        raise AssertionError("unsafe log plan must not run")

    with pytest.raises(ValueError):
        _execute(tmp_path, _plan(actions=["https://u.edu/a"], **extra), get=get)


def test_resume_cannot_overwrite_reset_or_tamper_previous_raw_logs(tmp_path: Path) -> None:
    first = _execute(tmp_path, _plan(actions=["https://u.edu/a"]))
    initial_bytes = (tmp_path / "guard-001.json").read_bytes()
    with pytest.raises(ValueError, match="overwrite"):
        _execute(tmp_path, _plan(first_log_number=1, actions=["https://u.edu/b"]))
    with pytest.raises(ValueError, match="cannot decrease"):
        _execute(tmp_path, _plan(start_calls=0, actions=["https://u.edu/b"]))
    with pytest.raises(ValueError, match="budget differs"):
        _execute(tmp_path, _plan(max_calls=2, actions=["https://u.edu/b"]))
    assert (tmp_path / "guard-001.json").read_bytes() == initial_bytes
    record = json.loads(initial_bytes)
    record["response"]["content_b64"] = base64.b64encode(b"fabricated page").decode()
    (tmp_path / "guard-001.json").write_text(json.dumps(record))
    with pytest.raises(ValueError, match="hash mismatch"):
        _execute(tmp_path, _plan(resume_summary=first, actions=["https://u.edu/b"]))
    assert not (tmp_path / "guard-002.json").exists()
    with pytest.raises(ValueError, match="content hash mismatch"):
        expert_view(record)


def test_resume_summary_retains_hashes_of_earlier_incremental_invocations(tmp_path: Path) -> None:
    first = _execute(tmp_path, _plan(actions=["https://u.edu/a"]))
    second = _execute(tmp_path, _plan(resume_summary=first, actions=["https://u.edu/b"]))
    assert set(second["raw_logs"]) == {"guard-001.json", "guard-002.json"}
    record = json.loads((tmp_path / "guard-001.json").read_bytes())
    record["response"]["fetched_at"] = "2020-01-01T00:00:00+00:00"
    (tmp_path / "guard-001.json").write_text(json.dumps(record))
    with pytest.raises(ValueError, match="hash mismatch"):
        _execute(tmp_path, _plan(resume_summary=second, actions=["https://u.edu/c"]))


@pytest.mark.parametrize("prior_failure", ["http_429", "fetcher_budget"])
@pytest.mark.parametrize("old_summary", [False, True])
def test_resume_summary_cannot_reset_counters_or_clear_429_by_changing_prefix(
    tmp_path: Path,
    prior_failure: str,
    old_summary: bool,
) -> None:
    fetch_calls = search_calls = 0

    async def get(url: str) -> _Page:
        nonlocal fetch_calls
        fetch_calls += 1
        return _Page(url)

    async def search(**kwargs: Any) -> _Answer:
        nonlocal search_calls
        search_calls += 1
        raise SearchUnavailable("quota response withheld", http_status=429)

    action = {"tool": "search_provider", "query": "programme"}
    first_plan = _plan(
        max_calls=1, actions=[action] if prior_failure == "http_429" else ["https://u.edu/a"]
    )
    first = _execute(tmp_path, first_plan, get=get, search=search)
    if old_summary:
        first.pop("log_prefix", None)
    before = (fetch_calls, search_calls)
    with pytest.raises(ValueError, match="log_prefix"):
        _execute(
            tmp_path,
            _plan(
                max_calls=1,
                log_prefix="renamed",
                resume_summary=first,
                start_calls=0,
                start_ms=0,
                start_search_queries=0,
                stop_reason=None,
                actions=[action, "https://u.edu/b"],
            ),
            get=get,
            search=search,
        )
    assert (fetch_calls, search_calls) == before
    assert not (tmp_path / "renamed-001.json").exists()


def test_resume_summary_cannot_relabel_independent_budget_as_baseline_intervention(
    tmp_path: Path,
) -> None:
    first = _execute(tmp_path, _plan(actions=["https://u.edu/a"]))
    with pytest.raises(ValueError, match="budget_origin"):
        _execute(
            tmp_path,
            _plan(
                resume_summary=first,
                budget_origin="baseline_intervention",
                actions=["https://u.edu/b"],
            ),
        )


def test_pending_log_is_reserved_before_tool_call_and_blocks_a_competing_run(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        entered, release = asyncio.Event(), asyncio.Event()
        called = 0

        async def get(url: str) -> _Page:
            nonlocal called
            called += 1
            assert json.loads((tmp_path / "guard-001.json").read_bytes())["outcome"] == "pending"
            entered.set()
            await release.wait()
            return _Page(url)

        task = asyncio.create_task(
            execute(
                _plan(actions=["https://u.edu/a"]),
                tmp_path,
                get=get,
                search=None,
                provider_name="exa_mcp",
            )
        )
        await entered.wait()
        with pytest.raises(ValueError, match="Incomplete raw log"):
            await execute(
                _plan(actions=["https://u.edu/b"]),
                tmp_path,
                get=get,
                search=None,
                provider_name="exa_mcp",
            )
        assert called == 1
        release.set()
        summary = await task
        assert _record(tmp_path, summary["actions"][0])["response"]["ok"] is True

    asyncio.run(scenario())


def test_cancelled_tool_leaves_pending_log_and_refuses_unadjudicated_resume(tmp_path: Path) -> None:
    async def scenario() -> None:
        entered = asyncio.Event()

        async def get(url: str) -> _Page:
            entered.set()
            await asyncio.Event().wait()
            raise AssertionError("cannot finish")

        task = asyncio.create_task(
            execute(
                _plan(actions=["https://u.edu/a"]),
                tmp_path,
                get=get,
                search=None,
                provider_name="exa_mcp",
            )
        )
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert json.loads((tmp_path / "guard-001.json").read_bytes())["outcome"] == "pending"
        with pytest.raises(ValueError, match="Incomplete raw log"):
            await execute(
                _plan(actions=["https://u.edu/b"]),
                tmp_path,
                get=get,
                search=None,
                provider_name="exa_mcp",
            )

    asyncio.run(scenario())


def test_paginated_view_exposes_exact_full_text_named_sections_links_and_provenance(
    tmp_path: Path,
) -> None:
    paragraphs = "".join(f"<p>Requirement {i}: {'complete evidence ' * 100}</p>" for i in range(4))
    body = f"<title>Computer Science</title><h1>Admission requirements</h1>{paragraphs}<h2>English</h2><p>IELTS Academic 6.5</p><a href='/fees'>Annual tuition fees and funding</a><a href='https://github.com/answers'>Repository</a>".encode()

    async def get(url: str) -> _Page:
        return _Page(url, body)

    summary = _execute(tmp_path, _plan(actions=["https://u.edu/programme"]), get=get)
    record = _record(tmp_path, summary["actions"][0])
    first = expert_view(record, chars=90, sections=2, links=1)
    assert first["fetched_at"] == "2026-10-04T00:00:00+00:00"
    assert first["content_sha256"] == hashlib.sha256(body).hexdigest()
    assert first["title"] == "Computer Science"
    assert first["sections"][0]["text"] == "Admission requirements"
    assert first["sections"][1]["section_path"] == ("Admission requirements",)
    assert first["links"] == [
        {"url": "https://u.edu/fees", "text": "Annual tuition fees and funding"}
    ]
    text_parts = []
    offset = 0
    while True:
        page = expert_view(record, chars=1000, offset=offset)
        text_parts.append(page["text"])
        if page["text_next_offset"] is None:
            break
        offset = page["text_next_offset"]
    text = "".join(text_parts)
    assert "IELTS Academic 6.5" in text
    assert len(text) == first["text_total_chars"]
    assert hashlib.sha256(text.encode()).hexdigest() == first["text_sha256"]
    section_page = expert_view(record, section_offset=first["sections_next_offset"], sections=2)
    assert section_page["sections"][0]["id"] == "b2"


def test_production_run_uses_configured_provider_cold_reads_and_respects_robots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from types import SimpleNamespace

    import app.adapters.fetching
    import app.adapters.search
    import app.config

    calls: list[tuple[str, bool]] = []
    construction: list[dict[str, Any]] = []

    class Fetcher:
        def __init__(self, cache_dir: Path, **kwargs: Any) -> None:
            construction.append(kwargs)

        async def __aenter__(self) -> Fetcher:
            return self

        async def __aexit__(self, *args: Any) -> None:
            pass

        async def get(self, url: str, *, use_cache: bool = True) -> _Page:
            calls.append((url, use_cache))
            return _Page(url)

    settings = SimpleNamespace(
        search_provider="exa_mcp",
        respect_robots=False,
        fetch_delay_seconds=1.5,
        fetch_timeout_seconds=20,
        fetch_contact="public contact",
    )
    monkeypatch.setattr(app.config, "get_settings", lambda: settings)
    monkeypatch.setattr(app.adapters.fetching, "Fetcher", Fetcher)
    monkeypatch.setattr(
        app.adapters.search,
        "get_search_provider",
        lambda: SimpleNamespace(name="exa_mcp", search=None),
    )
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(_plan(actions=["https://u.edu/page"])))
    result = asyncio.run(run(plan_path, tmp_path / "logs", tmp_path / "cache"))
    assert calls == [("https://u.edu/page", False)]
    assert construction[0]["respect_robots"] is True
    assert result["provider"] == "exa_mcp"
    settings.search_provider = "serper"
    monkeypatch.setattr(
        app.adapters.search,
        "get_search_provider",
        lambda: pytest.fail("must not construct an unauthorized provider"),
    )
    with pytest.raises(ValueError, match="configured exa or exa_mcp"):
        asyncio.run(run(plan_path, tmp_path / "other_logs", tmp_path / "other_cache"))
