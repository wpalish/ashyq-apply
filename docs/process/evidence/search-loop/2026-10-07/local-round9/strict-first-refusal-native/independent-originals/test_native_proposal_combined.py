"""CLI/child/preSTOP and strict-provider mocks; no external process or network."""

from __future__ import annotations

import asyncio
import json
import socket
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from app import config
from app.adapters.network_policy import check_url as actual_check_url
from app.adapters.search import exa_mcp
from app.adapters.search.base import SearchUnavailable
from app.pipeline import read_budget
from evaluation.research import live
from evaluation.research.schema import Observation, Telemetry
from scripts import canary_discovery as canary
from tests.readguard_support import offline as offline

# Stored before the autouse offline fixture; only explicit MockTransport sends allowed.
_MOCK_ONLY_SEND = httpx.AsyncClient.send


@pytest.fixture
def cli(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(
        config,
        "Settings",
        lambda **kwargs: SimpleNamespace(search_provider="exa", _validate_search=lambda: None),
    )
    monkeypatch.setattr(
        live.subprocess, "check_output", lambda *args, **kwargs: b"frozen-source".decode()
    )

    def run(command, **kwargs):
        calls.append(command)
        output = Path(command[command.index("--out") + 1])
        output.write_text(Observation(case_id="groningen", telemetry=Telemetry()).model_dump_json())
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(live.subprocess, "run", run)
    return SimpleNamespace(root=tmp_path, calls=calls)


@pytest.mark.parametrize(
    "flags,source,native,fenced",
    [
        ([], False, False, False),
        (["--no-university-read-budget"], True, False, False),
        (["--fenced-research-job", "--university-read-budget"], False, True, True),
        (
            ["--university-read-budget", "--no-university-read-budget", "--fenced-research-job"],
            True,
            False,
            True,
        ),
        (["--no-fenced-research-job", "--fenced-research-job"], False, False, True),
        (["--fenced-research-job", "--no-fenced-research-job"], False, False, False),
    ],
)
def test_batch_resolved_flags_forwarded_and_recorded(
    cli, monkeypatch, flags, source, native, fenced
):
    monkeypatch.setattr(read_budget, "UNIVERSITY_READ_BUDGET", source)
    monkeypatch.setattr(
        sys,
        "argv",
        ["live", "--live", "--case", "groningen", "--out", str(cli.root / "out"), *flags],
    )
    live.main()
    command = cli.calls[0]
    assert ("--university-read-budget" if native else "--no-university-read-budget") in command
    assert ("--fenced-research-job" if fenced else "--no-fenced-research-job") in command
    capture = json.loads(next((cli.root / "out").rglob("capture.json")).read_text())
    assert (
        capture["config"]["university_read_budget"] is native
        and capture["config"]["fenced_research_job"] is fenced
    )
    assert capture["config"]["research_job_protocol"] == (
        "genuine-research-job" if fenced else "legacy-direct-unfenced"
    )


@pytest.mark.parametrize(
    "flags",
    [
        ["--university-read-budget"],
        ["--fenced-research-job", "--with-documents", "1"],
        ["--fenced-research-job"],
    ],
)
def test_invalid_before_child_or_settings(cli, monkeypatch, flags):
    monkeypatch.setattr(sys, "argv", ["live", "--live", "--out", str(cli.root / "out"), *flags])
    with pytest.raises(SystemExit) as info:
        live.main()
    assert info.value.code == 2 and cli.calls == [] and not (cli.root / "out").exists()


@pytest.mark.parametrize("native", [False, True])
def test_pre_stop_envelope_effective_flags_without_job(cli, monkeypatch, native):
    stop = cli.root / "stop.json"
    stop.write_text('{"reason":"synthetic"}')
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "live",
            "--live",
            "--case",
            "groningen",
            "--out",
            str(cli.root / "out"),
            "--strict-expert-budget",
            "--stop-file",
            str(stop),
            "--fenced-research-job",
            "--university-read-budget" if native else "--no-university-read-budget",
        ],
    )
    live.main()
    capture = json.loads(next((cli.root / "out").rglob("capture.json")).read_text())
    assert cli.calls == [] and capture["observations"] == []
    assert (
        capture["config"]["university_read_budget"] is native
        and capture["config"]["fenced_research_job"] is True
    )
    assert capture["config"]["batch_attempted_case_ids"] == []


@pytest.mark.parametrize("native", [False, True])
def test_child_flags_are_passed_to_capture_without_global_promotion(cli, monkeypatch, native):
    got = []

    async def capture(*args, **kwargs):
        got.append(kwargs)

    monkeypatch.setattr(live, "capture_one", capture)
    monkeypatch.setattr(read_budget, "UNIVERSITY_READ_BUDGET", True)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "live",
            "--live",
            "--child",
            "--case",
            "groningen",
            "--out",
            str(cli.root / "child.json"),
            "--fenced-research-job",
            "--university-read-budget" if native else "--no-university-read-budget",
        ],
    )
    live.main()
    assert got[0]["university_read_budget"] is native and got[0]["fenced_research_job"] is True
    assert read_budget.UNIVERSITY_READ_BUDGET is True and cli.calls == []


@pytest.mark.parametrize(
    "flags",
    [
        ["--check-seeds", "--fenced-research-job", "--only", "example.edu"],
        ["--university-read-budget", "--only", "example.edu"],
        ["--fenced-research-job", "--batch", "example.edu,second.edu"],
    ],
)
def test_canary_cli_rejects_excluded_protocol_before_seed_calls(monkeypatch, flags):
    called = []

    async def forbidden(*args, **kwargs):
        called.append(True)
        raise AssertionError

    monkeypatch.setattr(canary, "check_seeds", forbidden)
    monkeypatch.setattr(canary, "run_canary", forbidden)
    monkeypatch.setattr(sys, "argv", ["canary", *flags])
    with pytest.raises(SystemExit):
        asyncio.run(canary.main())
    assert called == []


def test_outer_clock_is_original_entry_and_limits_unchanged():
    clock = [10.0]
    b = live._ExpertBudget(60, 120, "exa", clock[0], clock=lambda: clock[0])
    clock[0] += 17
    assert b.remaining() == 103 and b.started == 10
    assert (
        live.STRICT_MAX_FETCHER_CALLS == 60
        and live.STRICT_MAX_SEARCH_QUERIES == 6
        and live.STRICT_MAX_SECONDS == 120
    )
    assert "setup" in b.active_time_basis


@pytest.fixture
def no_retry_external(monkeypatch, tmp_path):
    def deny(*args, **kwargs):
        raise AssertionError("Provider test forbids external DNS/network/process/model I/O")

    monkeypatch.setattr(socket, "getaddrinfo", deny)
    monkeypatch.setattr(socket, "create_connection", deny)
    monkeypatch.setattr(socket.socket, "connect", deny)
    monkeypatch.setattr(subprocess, "Popen", deny)
    monkeypatch.setattr(subprocess, "run", deny)
    monkeypatch.setattr(subprocess, "check_output", deny)
    monkeypatch.setattr(httpx.Client, "send", deny)

    async def send_mock_only(client, *args, **kwargs):
        assert isinstance(client._transport, httpx.MockTransport)
        return await _MOCK_ONLY_SEND(client, *args, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "send", send_mock_only)
    # Keep real URL/policy validation; the resolver is wholly synthetic.
    monkeypatch.setattr(
        exa_mcp,
        "check_url",
        lambda url: actual_check_url(
            url,
            resolver=lambda *a, **kw: [
                (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", 443))
            ],
        ),
    )
    monkeypatch.setattr(exa_mcp, "RATE_LIMIT_RETRY", True)
    monkeypatch.setattr(exa_mcp, "RETRY_429_ONCE", True)
    monkeypatch.setattr(exa_mcp, "RATE_LIMIT_BACKOFF_SECONDS", 0.0)
    monkeypatch.setattr(exa_mcp, "THROTTLE_BACKOFF_SECONDS", 0.0)
    monkeypatch.setattr(exa_mcp, "MIN_QUERY_INTERVAL_SECONDS", 0.0)
    monkeypatch.setattr(exa_mcp, "_last_query_at", None)
    monkeypatch.setattr(
        config,
        "get_settings",
        lambda: SimpleNamespace(
            search_provider="exa_mcp",
            enable_browser_tier=False,
            respect_robots=True,
        ),
    )
    bindings = tmp_path / "synthetic-empty-bindings.json"
    bindings.write_text('{"version":"synthetic-no-output-identities","bindings":[]}')
    monkeypatch.setattr(live, "REVIEWED_BINDINGS", bindings)
    monkeypatch.setattr(live, "DOCUMENT_SECONDS", 0.0)
    return SimpleNamespace(bindings=bindings, root=tmp_path, monkeypatch=monkeypatch)


class _RetryServer:
    def __init__(self, failure, *, fail_phase="tools/call", forever=False):
        self.failure = failure
        self.fail_phase = fail_phase
        self.forever = forever
        self.calls = []
        self.phase_calls = 0

    def __call__(self, request):
        payload = json.loads(request.content)
        method = payload["method"]
        self.calls.append({"method": method, "id": payload.get("id")})
        if method == self.fail_phase:
            self.phase_calls += 1
            if self.phase_calls == 1 or self.forever:
                failure = self.failure
                if type(failure) is int:
                    return httpx.Response(failure)
                if failure == "timeout":
                    raise httpx.ReadTimeout("SYNTHETIC_PRIVATE_VENDOR_MARKER", request=request)
                if failure == "transport":
                    raise httpx.ConnectError("SYNTHETIC_PRIVATE_VENDOR_MARKER", request=request)
                if failure == "malformed":
                    return httpx.Response(
                        200, content=b"SYNTHETIC_PRIVATE_VENDOR_MARKER invalid JSON"
                    )
                if failure == "rpc":
                    return httpx.Response(
                        200,
                        json={
                            "jsonrpc": "2.0",
                            "id": payload["id"],
                            "error": {"code": -32000, "message": "SYNTHETIC_PRIVATE_VENDOR_MARKER"},
                        },
                    )
                result = (
                    {"_meta": {"ai.exa/rateLimited": True}}
                    if failure == "rate"
                    else {
                        "isError": True,
                        "content": [{"type": "text", "text": "SYNTHETIC_PRIVATE_VENDOR_MARKER"}],
                    }
                )
                return httpx.Response(
                    200, json={"jsonrpc": "2.0", "id": payload["id"], "result": result}
                )
        if method == "initialize":
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "id": payload["id"],
                    "result": {"protocolVersion": exa_mcp.PROTOCOL_VERSION},
                },
            )
        if method == "notifications/initialized":
            return httpx.Response(202)
        assert method == "tools/call"
        return httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": payload["id"],
                "result": {"structuredContent": {"results": []}},
            },
        )


def _execute_probe(
    module,
    fixture,
    server,
    *,
    initialized=False,
    strict=True,
    followup=True,
    extra_error=None,
    output_name="capture",
):
    fixture.monkeypatch.setattr(module, "REVIEWED_BINDINGS", fixture.bindings)
    fixture.monkeypatch.setattr(module, "DOCUMENT_SECONDS", 0.0)
    output = fixture.root / (output_name + ".json")
    stop = fixture.root / "synthetic-provider-STOP.json"
    caught = []
    original_search = exa_mcp.ExaMcpSearchProvider.search
    flags_before = (exa_mcp.RATE_LIMIT_RETRY, exa_mcp.RETRY_429_ONCE)
    flags_during = []

    async def run(*args, **kwargs):
        flags_during.append((exa_mcp.RATE_LIMIT_RETRY, exa_mcp.RETRY_429_ONCE))
        async with httpx.AsyncClient(transport=httpx.MockTransport(server)) as client:
            provider = exa_mcp.ExaMcpSearchProvider(client=client)
            # Warm-session control only; cold controls exercise genuine initialization.
            provider._initialized = initialized
            try:
                await provider.search(query="public offline transport control")
            except SearchUnavailable as exc:
                caught.append(
                    {"reason": getattr(exc.reason, "value", None), "http_status": exc.http_status}
                )
            if followup and caught:
                # New instance/stage under the same real capture ledger; STOP must block before transport.
                second = exa_mcp.ExaMcpSearchProvider(client=client)
                try:
                    await second.search(query="second public offline control")
                except SearchUnavailable as exc:
                    caught.append(
                        {
                            "reason": getattr(exc.reason, "value", None),
                            "http_status": exc.http_status,
                        }
                    )
            if extra_error:
                raise extra_error
        return {"institutions": [{"programs": []}], "run_error": ""}

    fixture.monkeypatch.setattr(canary, "run_canary", run)
    kwargs = {"strict_expert_budget": strict, "university_read_budget": False}
    if strict:
        kwargs.update(stop_file=stop, finalization_reserve_ms=1000)
    escaped = None
    try:
        asyncio.run(module.capture_one("groningen", output, 60, 120, **kwargs))
    except BaseException as exc:
        escaped = type(exc).__name__
    flags_after = (exa_mcp.RATE_LIMIT_RETRY, exa_mcp.RETRY_429_ONCE)
    assert flags_after == flags_before and exa_mcp.ExaMcpSearchProvider.search is original_search
    budget_path = output.with_suffix(".budget.json")
    observation = json.loads(output.read_text()) if output.exists() else None
    budget = json.loads(budget_path.read_text()) if budget_path.exists() else None
    result = {
        "server_calls": server.calls,
        "failed_phase_calls": server.phase_calls,
        "caught": caught,
        "escaped": escaped,
        "flags_before": flags_before,
        "flags_during": flags_during,
        "flags_after": flags_after,
        "sticky_stop": json.loads(stop.read_text()) if stop.exists() else None,
        "budget": budget,
        "observation": observation,
        "orchestration": "SYNTHETIC_NO_UNIVERSITY_NO_JOB",
        "actual_provider_search_unmodified": True,
        "strict": strict,
        "initialized": initialized,
    }
    (fixture.root / (output_name + ".receipt.json")).write_text(json.dumps(result, indent=2) + "\n")
    return result


@pytest.mark.parametrize(
    "failure",
    ["rate", 401, 402, 403, 429, 500, "rpc", "tool", "malformed", "timeout", "transport", 302],
)
@pytest.mark.parametrize("initialized", [False, True])
def test_current_strict_first_refusal_stops_transport_and_restores_flags(
    no_retry_external, failure, initialized
):
    result = _execute_probe(live, no_retry_external, _RetryServer(failure), initialized=initialized)
    assert len(result["server_calls"]) == (1 if initialized else 3)
    assert sum(x["method"] == "tools/call" for x in result["server_calls"]) == 1
    assert result["flags_during"] == [(False, False)] and result["flags_after"] == (True, True)
    assert result["sticky_stop"] is not None and result["budget"]["provider_failure"] is not None
    assert (
        result["budget"]["search_queries"] == 1 and result["budget"]["blocked_search_queries"] == 1
    )
    assert result["observation"]["error"] == "BENCHMARK_PROVIDER_FAILURE"
    encoded = json.dumps(result["budget"]) + json.dumps(result["sticky_stop"])
    assert "SYNTHETIC_PRIVATE_VENDOR_MARKER" not in encoded
    stop = no_retry_external.root / "synthetic-provider-STOP.json"
    before = stop.read_bytes()
    followup_server = _RetryServer("rate")
    second = _execute_probe(
        live, no_retry_external, followup_server, output_name="fresh-capture", followup=False
    )
    assert second["server_calls"] == [] and second["budget"]["search_queries"] == 0
    assert (
        second["budget"]["stop_reason"] == "external_provider_failure"
        and stop.read_bytes() == before
    )


@pytest.mark.parametrize("failure", [401, 402, 429])
def test_refusal_on_cold_initialize_is_exactly_one_total_transport(no_retry_external, failure):
    result = _execute_probe(live, no_retry_external, _RetryServer(failure, fail_phase="initialize"))
    assert len(result["server_calls"]) == 1 and result["server_calls"][0]["method"] == "initialize"
    assert result["sticky_stop"] is not None and result["budget"]["search_queries"] == 1


@pytest.mark.parametrize("control", [RuntimeError("synthetic_control"), asyncio.CancelledError()])
def test_scoped_retry_flags_restore_on_exception_and_cancellation(no_retry_external, control):
    result = _execute_probe(live, no_retry_external, _RetryServer("rate"), extra_error=control)
    assert result["escaped"] == type(control).__name__ and result["flags_after"] == (True, True)
    assert sum(x["method"] == "tools/call" for x in result["server_calls"]) == 1


def test_legacy_capture_retains_retry_behavior(no_retry_external):
    result = _execute_probe(live, no_retry_external, _RetryServer("rate"), strict=False)
    assert result["flags_during"] == [(True, True)] and len(result["server_calls"]) == 4
    assert (
        result["budget"] is None
        and result["sticky_stop"] is None
        and result["observation"]["error"] is None
    )


def test_current_strict_empty_success_is_not_provider_refusal(no_retry_external):
    result = _execute_probe(live, no_retry_external, _RetryServer("rate", fail_phase="never"))
    assert len(result["server_calls"]) == 3 and result["flags_during"] == [(False, False)]
    assert result["flags_after"] == (True, True) and result["budget"]["search_queries"] == 1
    assert result["budget"]["provider_failure"] is None and result["sticky_stop"] is None
    assert result["observation"]["error"] is None
