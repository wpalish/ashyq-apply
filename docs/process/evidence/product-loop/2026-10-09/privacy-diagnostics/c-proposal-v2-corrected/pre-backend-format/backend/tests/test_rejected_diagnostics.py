"""Six bounded scenarios; all identifiers are disposable synthetic values."""

import asyncio
import json
import logging
import os
import socket
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace as NS
from typing import ClassVar
from unittest.mock import AsyncMock
from urllib.parse import quote

import httpx
import pytest
from app.adapters.base import AdapterResult, Candidate, CandidateProgram, PageOutcome
from app.adapters.cost.web_costs import WebCostAdapter
from app.adapters.discovery.catalog_walker import CatalogWalk, CatalogWalker, WalkerLink
from app.adapters.discovery.live_discovery import (
    DiscoveryTrace,
    LiveDiscoveryAdapter,
    PageCategory,
    SitemapReader,
    _public_requested_fields,
)
from app.adapters.documents.web_documents import WebDocumentsAdapter
from app.adapters.fetching import Fetcher, FetchResult, find_pii
from app.adapters.government.web_government import WebGovernmentAdapter
from app.adapters.requirements.web_requirements import WebRequirementsAdapter
from app.adapters.scholarship.web_scholarships import WebScholarshipAdapter
from app.adapters.search.intent import (
    DEFAULT_QUERY_BUDGET,
    SCHOLARSHIP_QUERY_RESERVE,
    SHARED_QUERY_BUDGET,
    DiscoveryIntent,
    QueryPrivacyError,
    queries_for,
)
from app.config import Settings
from app.domain.enums import DegreeLevel, DocumentPurpose, FetchOutcome, PipelineStage
from app.jobs.worker import Worker
from app.logging_setup import JsonFormatter
from app.pipeline.runner import LeaseLost, ResearchRunner, RunCancelled

PROOF_DIR = os.environ.get("REJECTED_DIAGNOSTICS_PROOF_DIR")
MODE = os.environ.get("REJECTED_DIAGNOSTICS_PROOF_MODE", "native")
SOURCE = "https://public.invalid/start"


def proof(case, payload):
    if not PROOF_DIR:
        return
    (Path(PROOF_DIR) / f"{MODE}-{case}-observations.json").write_text(
        json.dumps(payload, indent=2, default=repr) + "\n"
    )


def captured(caplog):
    formatter = JsonFormatter()
    return [
        {
            "message": r.getMessage(),
            "args": repr(r.args),
            "extra": repr(r.__dict__),
            "json": formatter.format(r),
        }
        for r in caplog.records
    ]


def absent(marker, payload):
    blob = json.dumps(payload, default=repr)
    assert marker not in blob, "rejected synthetic sentinel retained"
    assert quote(marker, safe="") not in blob, "encoded rejected sentinel retained"


def intent(field="Mathematics", **kwargs):
    return DiscoveryIntent(
        institution="Public University",
        domain="public.invalid",
        degree=DegreeLevel.BACHELOR,
        field=field,
        **kwargs,
    )


def fake_profile(fields=None):
    return NS(
        context=NS(
            level=DegreeLevel.BACHELOR,
            intended_fields=fields or ["Mathematics"],
            intake_term="fall",
            intake_year=2027,
        )
    )


def runner(monkeypatch):
    row = NS(
        id="synthetic-run",
        stage_state={},
        demo_mode=True,
        candidate_limit=None,
        verify_limit=None,
        settings_snapshot={},
        started_at=None,
        university_ids=[],
        errors=[],
        unknowns=[],
        retry_urls=[],
        profile=NS(organization_id="synthetic-org"),
    )
    events = []
    session = NS(
        add=lambda item: events.append({"action": item.action, "detail": item.detail}),
        rollback=lambda: None,
    )
    settings = Settings(
        _env_file=None, enable_browser_tier=False, search_provider="none", decision_provider="none"
    )
    r = ResearchRunner(session, row, fake_profile(), settings, worker_id="synthetic-worker")
    monkeypatch.setattr(r, "_save", lambda: None)
    return r, row, events


def public_dns(url):
    from app.adapters.network_policy import check_url

    return check_url(
        url,
        resolver=lambda host, port, **kw: [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", port))
        ],
    )


async def ordinary_adapter_controls():
    """Real adapter branches with scripted fetch results, never a network call."""

    class ScriptedFetcher:
        def __init__(self, results):
            self.results = results
            self.calls = []

        async def get(self, url):
            self.calls.append(url)
            return self.results[url]

    offsite = []
    failed_source = "https://public.invalid/prior404"
    offsite_source = "https://public.invalid/admissions"
    for prior_failure in (False, True):
        scripted = ScriptedFetcher(
            {
                failed_source: FetchResult(
                    url=failed_source,
                    outcome=FetchOutcome.HTTP_ERROR,
                    status_code=404,
                    error="HTTP 404",
                ),
                offsite_source: FetchResult(
                    url=offsite_source,
                    outcome=FetchOutcome.OK,
                    status_code=200,
                    final_url="https://other.invalid/landing",
                    text="ordinary off-site response",
                ),
            }
        )
        c = Candidate(
            name="Public University",
            country="Synthetic",
            city="Synthetic",
            domain="public.invalid",
            admissions_url=offsite_source if prior_failure else None,
        )
        program = CandidateProgram(
            name="BSc Mathematics",
            field="Mathematics",
            degree=DegreeLevel.BACHELOR,
            url=failed_source if prior_failure else offsite_source,
        )
        try:
            result = await WebRequirementsAdapter(scripted, "2027/28").verify(
                c, program, "fall 2027"
            )
            observation = {"output": asdict(result), "exception": None}
        except Exception as exc:
            # Preserve native authoring regression, then finish all other controls.
            observation = {"exception": type(exc).__name__, "message": str(exc)}
        observation.update({"prior_failure": prior_failure, "calls": scripted.calls})
        offsite.append(observation)

    documents = []
    ordinary_url = "https://public.invalid/documents"
    c = Candidate(name="Public University", country="Synthetic", city="Synthetic")
    program = CandidateProgram(
        name="BSc Mathematics",
        field="Mathematics",
        degree=DegreeLevel.BACHELOR,
        url=ordinary_url,
    )
    for outcome, status, reason in [
        (FetchOutcome.HTTP_ERROR, 404, "HTTP 404"),
        (FetchOutcome.ROBOTS_DISALLOWED, None, "Disallow: /documents"),
        (FetchOutcome.TIMEOUT, None, "ordinary read timed out"),
        (FetchOutcome.BLOCKED, None, "ordinary SSRF policy block"),
        (FetchOutcome.TOO_LARGE, 200, "ordinary response exceeds MAX_BYTES"),
    ]:
        scripted = ScriptedFetcher(
            {
                ordinary_url: FetchResult(
                    url=ordinary_url,
                    outcome=outcome,
                    status_code=status,
                    error=reason,
                )
            }
        )
        actual = AdapterResult()
        docs = await WebDocumentsAdapter(scripted, "2027/28")._from_page(
            c, program, ordinary_url, DocumentPurpose.ADMISSION, actual
        )
        # Exact legacy ordinary diagnostic contract, including empty detail.
        expected = AdapterResult(
            errors=[f"{ordinary_url}: {outcome.value} — {reason}"],
            pages_checked=1,
            pages_failed=1,
            retry_urls=[ordinary_url],
            page_outcomes=[PageOutcome(ordinary_url, "fetch-failed")],
        )
        documents.append(
            {
                "outcome": outcome.value,
                "scripted_status": status,
                "output": asdict(actual),
                "legacy_expected": asdict(expected),
                "documents": docs,
                "calls": scripted.calls,
            }
        )
    return {"requirements_offsite": offsite, "documents_ordinary": documents}


def test_p1_initial_refusal_has_no_rejected_diagnostic(tmp_path, monkeypatch, caplog):
    marker = "SYNTH_P1_ALPHA@example.invalid"
    url = "https://public.invalid/" + marker
    counts = {"cache_read": 0, "cache_write": 0, "resolve": 0, "request": 0}

    def forbidden(key):
        def call(*a, **kw):
            counts[key] += 1
            raise AssertionError(key)

        return call

    f = Fetcher(tmp_path / "p1", respect_robots=False)
    monkeypatch.setattr(f.cache, "get", forbidden("cache_read"))
    monkeypatch.setattr(f.cache, "put", forbidden("cache_write"))
    monkeypatch.setattr("app.adapters.fetching._resolve_checked", forbidden("resolve"))
    monkeypatch.setattr(f, "_request_with_redirects", forbidden("request"))
    res = asyncio.run(f.get(url))
    payload = {
        "result": asdict(res),
        "logs": captured(caplog),
        "counts": counts,
        "stats": f.stats,
        "cache_files": [str(p) for p in (tmp_path / "p1").rglob("*")],
    }
    proof("P1", payload)
    assert res.outcome == FetchOutcome.REFUSED_PRIVACY
    assert res.status_code is None and res.content == b"" and not res.ok
    assert not any(counts.values()) and not payload["cache_files"]
    assert f.stats[FetchOutcome.REFUSED_PRIVACY.value] == 1
    absent(marker, payload)
    assert res.url == "https://public.invalid/"
    assert "email address" in res.error


def test_p2_poisoned_redirect_keeps_safe_requested_identity(tmp_path, monkeypatch, caplog):
    marker = "SYNTH_P2_TOKEN"
    hop = "https://public.invalid/jump?token=" + marker
    resolved, requests = [], []

    def resolve(url):
        resolved.append(url)
        return public_dns(url)

    monkeypatch.setattr("app.adapters.fetching.check_url", resolve)

    async def exercise():
        async with Fetcher(tmp_path / "p2", delay_seconds=0, respect_robots=False) as f:
            await f._client.aclose()

            def response(req):
                requests.append(str(req.url))
                return httpx.Response(302, headers={"location": hop})

            f._client = httpx.AsyncClient(transport=httpx.MockTransport(response))
            result = await f.get(SOURCE)
            return result, dict(f.stats)

    res, stats = asyncio.run(exercise())
    payload = {
        "result": asdict(res),
        "logs": captured(caplog),
        "resolved": resolved,
        "mocked_requests": requests,
        "stats": stats,
    }
    proof("P2", payload)
    assert resolved == [SOURCE, SOURCE] and len(requests) == 1
    assert res.outcome == FetchOutcome.REFUSED_PRIVACY and res.status_code is None
    assert stats[FetchOutcome.REFUSED_PRIVACY.value] == 1
    assert res.url == SOURCE and not res.ok
    absent(marker, payload)
    assert res.final_url == SOURCE and "credential-like parameter" in res.error


def test_p3_rejected_intent_has_typed_safe_reason():
    marker = "SYNTH_P3_EMAIL@example.invalid"
    with pytest.raises(QueryPrivacyError) as caught:
        intent(field="Mathematics " + marker)
    exc = caught.value
    payload = {"text": str(exc), "representation": repr(exc), "args": exc.args, "attrs": vars(exc)}
    proof("P3", payload)
    assert isinstance(exc, ValueError)
    absent(marker, payload)
    assert exc.field == "field" and exc.reason == "email"
    assert "email address" in str(exc)
    # Useful ordinary policy diagnostics remain distinguishable without the value.
    for value, reason, phrase in [
        ("fees $40", "currency", "currency amount"),
        ("gpa 4.8", "grade", "grade"),
        ("score 1234", "long-number", "long number"),
    ]:
        with pytest.raises(QueryPrivacyError) as policy:
            intent(field=value)
        assert policy.value.reason == reason and phrase in str(policy.value)
        assert value not in str(policy.value) and value not in repr(policy.value.args)
    with pytest.raises(QueryPrivacyError) as population:
        intent(population_marker="unlisted audience")
    assert population.value.reason == "population-not-allowed"
    assert population.value.field == "population_marker"
    assert "unlisted audience" not in str(population.value)


def test_p4_native_consumers_do_not_reintroduce_refused_url(tmp_path, monkeypatch, caplog):
    marker = "SYNTH_P4_TOKEN"
    url = "https://public.invalid/page?token=" + marker
    c = Candidate(
        name="Public University",
        country="Synthetic",
        city="Synthetic",
        domain="public.invalid",
        costs_url=url,
        scholarships_url=url,
    )
    program = CandidateProgram(
        name="BSc Mathematics", field="Mathematics", degree=DegreeLevel.BACHELOR, url=url
    )
    monkeypatch.setattr("app.adapters.requirements.web_requirements.TOPIC_SEARCH", False)
    r, row, events = runner(monkeypatch)

    async def exercise():
        f = Fetcher(tmp_path / "p4", delay_seconds=0, respect_robots=False)
        cost, out = await WebCostAdapter(f, "2027/28").fetch(c)
        r._record_diagnostics(out.errors)
        r._record_page_outcomes(out.page_outcomes)
        row.retry_urls = sorted(set(row.retry_urls + out.retry_urls))[:200]
        req = await WebRequirementsAdapter(f, "2027/28").verify(c, program, "fall 2027")
        doc = AdapterResult()
        docs = await WebDocumentsAdapter(f, "2027/28")._from_page(
            c, program, url, DocumentPurpose.ADMISSION, doc
        )
        gov = await WebGovernmentAdapter(f, lambda _: url).post_study_work("Synthetic")
        scholarships, award = await WebScholarshipAdapter(f, "2027/28").find(
            c, program, fake_profile(), allow_search=False
        )
        walk = CatalogWalk(
            catalogue_url=SOURCE, candidates=[WalkerLink(url, "BSc Mathematics", 5, "html")]
        )
        await CatalogWalker(
            fetcher=f, domain=c.domain, degree="bachelor", fields=["Mathematics"]
        )._read_lead(WalkerLink(url, "BSc Mathematics", 5, "html"), walk)
        catalogue = await CatalogWalker(
            fetcher=f, domain=c.domain, degree="bachelor", fields=["Mathematics"]
        ).walk_catalog(url)
        sitemap = SitemapReader(f)
        monkeypatch.setattr(sitemap, "_declared_sitemaps", AsyncMock(return_value=[url]))
        sitemap_trace = DiscoveryTrace(c.name, c.domain)
        sitemap_pages = await sitemap.collect(SOURCE, c.domain, sitemap_trace)
        trace = DiscoveryTrace(c.name, c.domain)
        selected = {PageCategory.PROGRAM_PAGE: [url]}
        await LiveDiscoveryAdapter(f)._confirm_programs(
            selected, {PageCategory.PROGRAM_PAGE: []}, trace, fake_profile()
        )
        ordinary = await ordinary_adapter_controls()
        return (
            cost,
            [out, req, doc, gov, award],
            docs,
            scholarships,
            walk,
            trace,
            selected,
            catalogue,
            sitemap_trace,
            sitemap_pages,
            ordinary,
        )

    (
        cost,
        outputs,
        docs,
        awards,
        walk,
        trace,
        selected,
        catalogue,
        sitemap_trace,
        sitemap_pages,
        ordinary,
    ) = asyncio.run(exercise())
    payload = {
        "cost": cost.model_dump(),
        "adapters": [asdict(o) for o in outputs],
        "run": {"errors": row.errors, "unknowns": row.unknowns, "retry_urls": row.retry_urls},
        "walk_outcomes": walk.outcomes,
        "trace": trace.as_dict(),
        "logs": captured(caplog),
        "catalogue_outcomes": catalogue.outcomes,
        "catalogue_identity": catalogue.catalogue_url,
        "walk_candidates": [asdict(link) for link in walk.candidates],
        "sitemap_trace": sitemap_trace.as_dict(),
        "ordinary_controls": ordinary,
    }
    proof("P4", payload)
    control_failures = []
    for case in ordinary["requirements_offsite"]:
        if case["exception"]:
            control_failures.append(case)
            continue
        outcome = case["output"]
        expected_checked = 2 if case["prior_failure"] else 1
        if (
            outcome["pages_checked"] != expected_checked
            or outcome["pages_failed"] != expected_checked
            or outcome["claims"]
            or outcome["page_outcomes"][-1]["url"] != "https://public.invalid/admissions"
            or outcome["page_outcomes"][-1]["category"] != "fetch-failed"
            or outcome["page_outcomes"][-1]["detail"] != "redirected off the source site"
            or outcome["errors"][-1]
            != (
                "https://public.invalid/admissions: redirected off the source site; "
                "no requirements verified"
            )
            or outcome["retry_urls"]
            != (["https://public.invalid/prior404"] if case["prior_failure"] else [])
        ):
            control_failures.append(case)
    for case in ordinary["documents_ordinary"]:
        if case["output"] != case["legacy_expected"] or case["documents"]:
            control_failures.append(case)
    assert not control_failures, "ordinary adapter compatibility regression: " + repr(
        control_failures
    )
    assert all(o.pages_checked == 1 and o.pages_failed == 1 and not o.claims for o in outputs)
    assert not docs and not awards and not walk.confirmed and not catalogue.confirmed
    assert not sitemap_pages
    assert len(catalogue.outcomes) == 1 and catalogue.outcomes[0][1] == "refused_privacy"
    assert not selected[PageCategory.PROGRAM_PAGE]
    absent(marker, payload)
    assert all(not o.retry_urls for o in outputs) and not row.retry_urls
    assert all(o.page_outcomes[0].url == "https://public.invalid/" for o in outputs)
    assert "refused_privacy" in " ".join(row.errors) and "fetch-failed" in " ".join(row.errors)
    assert not row.unknowns
    assert "refused_privacy" in outputs[2].page_outcomes[0].detail


def test_p5_actual_runner_worker_typed_escape_sinks(tmp_path, monkeypatch, caplog):
    marker = "SYNTH_P5_EMAIL@example.invalid"
    r, row, audits = runner(monkeypatch)
    caplog.set_level(logging.INFO)

    class MemoryFetcher:
        tier_counts: ClassVar[dict] = {}

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return None

    browser = NS(enabled=False, close=AsyncMock())
    monkeypatch.setattr(r, "_make_fetcher", MemoryFetcher)
    monkeypatch.setattr(r, "_make_browser", lambda _: browser)
    monkeypatch.setattr(r, "_stage_validate", AsyncMock())

    async def rejected_stage(*a):
        # Explicit synthetic exception-chain control, not a claim about current discovery.
        try:
            raise ValueError(marker)
        except ValueError:
            intent(field="Mathematics " + marker)

    monkeypatch.setattr(r, "_stage_discover", rejected_stage)
    failures = []

    @contextmanager
    def memory_scope():
        yield NS()

    class MemoryStore:
        def __init__(self, *a, **kw):
            pass

        def get(self, job_id):
            return NS(id=job_id, kind="research", attempts=3)

        def fail(self, job_id, error, *, lease_token):
            failures.append({"job_id": job_id, "error": error, "lease_token": lease_token})
            return "retry"

    monkeypatch.setattr("app.jobs.worker.session_scope", memory_scope)
    monkeypatch.setattr("app.jobs.worker.JobStore", MemoryStore)
    w = Worker(r.settings, worker_id="synthetic-worker")

    async def dispatch(*a, **kw):
        await r.run_to_decision()

    monkeypatch.setattr(w, "_dispatch", dispatch)
    monkeypatch.setattr(w, "_beat", AsyncMock())
    asyncio.run(w.execute("synthetic-job"))
    payload = {
        "run": {"stage": row.stage, "errors": row.errors},
        "audits": audits,
        "job_failures": failures,
        "logs": captured(caplog),
        "worker_failed": w.jobs_failed,
        "worker_done": w.jobs_done,
        "browser_close_calls": browser.close.await_count,
    }
    proof("P5", payload)
    assert row.stage == PipelineStage.FAILED.value and w.jobs_failed == 1 and w.jobs_done == 0
    assert failures[0]["lease_token"] == 3 and browser.close.await_count == 1
    assert "QueryPrivacyError" in failures[0]["error"]
    assert audits[0]["action"] == "run_failed"
    absent(marker, payload)
    assert "email address" in failures[0]["error"] and "field" in failures[0]["error"]
    # Privacy sinks must suppress chained traceback, not merely sanitize str(exc).
    assert all("Traceback" not in log["json"] for log in payload["logs"])


def test_p6_ordinary_source_status_budget_and_controlflow(tmp_path, monkeypatch, caplog):
    url = "https://public.invalid/en/node/1008496?year=2027&language=en"
    assert find_pii(url) is None
    resolved, requests = [], []

    def resolve(value):
        resolved.append(value)
        return public_dns(value)

    monkeypatch.setattr("app.adapters.fetching.check_url", resolve)

    async def exercise():
        async with Fetcher(tmp_path / "p6", delay_seconds=0, respect_robots=False) as f:
            await f._client.aclose()

            def response(req):
                requests.append(str(req.url))
                return httpx.Response(404, headers={"content-type": "text/html"}, text="Not found")

            f._client = httpx.AsyncClient(transport=httpx.MockTransport(response))
            res = await f.get(url)
            _, out = await WebCostAdapter(f, "2027/28").fetch(
                Candidate(
                    name="Public University", country="Synthetic", city="Synthetic", costs_url=url
                )
            )
            return res, out

    res, out = asyncio.run(exercise())
    safe = intent(intake_year=2027, population_marker="international")
    queries = queries_for(safe)
    trace = DiscoveryTrace("Public University", "public.invalid")
    assert _public_requested_fields(fake_profile(["gpa 4.8", "Mathematics"]), trace) == [
        "Mathematics"
    ]
    # Generic exceptions still retain their useful ordinary traceback/diagnostic.
    r, row, audits = runner(monkeypatch)

    class MemoryFetcher:
        tier_counts: ClassVar[dict] = {}

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return None

    monkeypatch.setattr(r, "_make_fetcher", MemoryFetcher)
    monkeypatch.setattr(r, "_make_browser", lambda _: NS(enabled=False, close=AsyncMock()))
    monkeypatch.setattr(r, "_stage_validate", AsyncMock())
    failure = ValueError("ordinary bounded parse failure")
    monkeypatch.setattr(r, "_stage_discover", AsyncMock(side_effect=failure))
    with pytest.raises(ValueError, match="ordinary bounded parse failure") as caught:
        asyncio.run(r.run_to_decision())
    assert caught.value is failure
    assert audits[0]["detail"]["error"] == "ordinary bounded parse failure"
    assert any("Traceback" in log["json"] for log in captured(caplog))
    # Stale lease remains no-write/rethrow, cancellation retains its typed exit.
    for control in [LeaseLost("ordinary stale lease"), RunCancelled("ordinary cancellation")]:
        before = len(audits)
        monkeypatch.setattr(r, "_stage_discover", AsyncMock(side_effect=control))
        with pytest.raises(type(control)) as stopped:
            asyncio.run(r.run_to_decision())
        assert stopped.value is control
        if isinstance(control, LeaseLost):
            assert len(audits) == before
        else:
            assert row.stage == PipelineStage.CANCELLED.value
            assert audits[-1]["action"] == "run_cancelled"
    payload = {
        "result": asdict(res),
        "adapter": asdict(out),
        "resolved": resolved,
        "requests": requests,
        "query_count": len(queries),
        "queries": [q.text for q in queries],
        "budgets": [DEFAULT_QUERY_BUDGET, SHARED_QUERY_BUDGET, SCHOLARSHIP_QUERY_RESERVE],
        "safe_fields": trace.public_fields,
        "ordinary_errors": row.errors,
        "logs": captured(caplog),
    }
    proof("P6", payload)
    assert res.outcome == FetchOutcome.HTTP_ERROR and res.status_code == 404 and res.url == url
    assert out.page_outcomes[0].url == url and out.retry_urls == [url]
    assert "HTTP 404" in res.error and url in out.errors[0]
    assert len(queries) <= 6 and DEFAULT_QUERY_BUDGET == 6
    assert SHARED_QUERY_BUDGET is True and SCHOLARSHIP_QUERY_RESERVE == 1
