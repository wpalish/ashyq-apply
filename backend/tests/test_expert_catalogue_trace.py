"""Q0-Q6 answers must remain linked to independent saved official-source reads."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import ValidationError

from evaluation.research.expert.controller import execute
from evaluation.research.expert.models import (
    QUESTIONS,
    ExpertTrace,
    TraceAdjudication,
    validate_trace,
    validate_trace_adjudication,
)
from evaluation.research.expert.packet import digest

URL = "https://u.edu/admissions"
START = datetime(2026, 10, 4, tzinfo=UTC)
QUOTES = [
    "BSc Computer Science is a bachelor programme.",
    "International applicants need IELTS Academic overall 6.5.",
    "A KZ national secondary diploma is accepted for bachelor admission.",
    "International applications for fall 2027 close on 15 January 2027.",
    "International tuition for 2027/2028 is GBP 9500 per year.",
    "The bachelor scholarship awards GBP 2000.",
    "International bachelor applicants are eligible for the scholarship.",
]
SCOPE = {
    "degree": "bachelor",
    "programme": "BSc Computer Science",
    "population": "international",
    "qualification": "KZ national secondary",
    "intake": "fall 2027",
    "academic_year": "2027/2028",
}


@pytest.fixture
def packet() -> dict[str, Any]:
    return {
        "schema_version": "1",
        "baseline_pipeline_sha": "abcdef0123456789",
        "baseline_budget": {
            "max_fetcher_calls": 60,
            "max_elapsed_ms": 90000,
            "max_search_queries": 6,
            "browser_enabled": False,
        },
        "public_profile": {"education_system": "KZ national secondary"},
        "cases": [
            {
                "case_id": "u",
                "university": "U",
                "domain": "u.edu",
                "request": {
                    "university": "U",
                    "programme": None,
                    "degree": "bachelor",
                    "field": "computer science",
                    "intake": "fall 2027",
                    "population": None,
                    "qualification": None,
                    "academic_year": None,
                },
                "baseline": {},
            }
        ],
    }


def unresolved() -> list[dict[str, Any]]:
    return [
        {
            "question": question,
            "status": "unresolved",
            "supporting_steps": [],
            "proposal_indices": [],
            "evidence": [],
            "scope": {},
            "observation": "The recorded evidence does not settle this question.",
        }
        for question in QUESTIONS
    ]


def source_record(html: str | None = None) -> dict[str, Any]:
    html = html or (
        "<html><body><main><h1>International bachelor admissions</h1>"
        + "".join(f"<p>{quote}</p>" for quote in QUOTES)
        + "</main></body></html>"
    )
    body = html.encode()
    return {
        "request": {"tool": "fetcher", "url": URL},
        "at": (START + timedelta(seconds=2)).isoformat(),
        "phase": "actions",
        "executed": True,
        "outcome_status": "success",
        "strict_budget": True,
        "response": {
            "outcome": "ok",
            "outcome_status": "success",
            "ok": True,
            "status_code": 200,
            "final_url": URL,
            "content_type": "text/html",
            "fetch_tier": "http",
            "fetched_at": START.isoformat(),
            "error": "",
            "from_cache": False,
            "content_sha256": hashlib.sha256(body).hexdigest(),
            "content_b64": base64.b64encode(body).decode(),
        },
        "elapsed_ms": 20,
        "elapsed_ms_cumulative": 20,
        "fetcher_calls_cumulative": 1,
        "search_queries_cumulative": 0,
        "policy_mode": "same_policy",
        "budgets": {"max_calls": 60, "max_ms": 90000, "max_search_queries": 6},
        "tool_policy": {
            "max_fetcher_calls": 60,
            "max_elapsed_ms": 90000,
            "max_search_queries": 6,
        },
    }


def save_record(tmp_path: Path, trace: dict[str, Any], record: dict[str, Any]) -> None:
    raw = json.dumps(record, ensure_ascii=False).encode()
    (tmp_path / "action-001.json").write_bytes(raw)
    trace["actions"][0]["raw_log_sha256"] = hashlib.sha256(raw).hexdigest()


def trace_for(packet: dict[str, Any], tmp_path: Path, *, found: bool = True) -> dict[str, Any]:
    record = source_record()
    proposals = (
        [
            {
                "claim_key": question,
                "value": {"answer": QUOTES[index]},
                "source_url": URL,
                "excerpt": QUOTES[index],
                "accessed_on": "2026-10-04",
                "scope": dict(SCOPE),
                "supporting_steps": [1],
                "status": "unreviewed",
            }
            for index, question in enumerate(QUESTIONS)
        ]
        if found
        else []
    )
    findings = (
        [
            {
                "question": question,
                "status": "found",
                "supporting_steps": [1],
                "proposal_indices": [index],
                "scope": dict(SCOPE),
                "observation": "The official page states the proposed fact; adjudication is pending.",
                "evidence": [
                    {
                        "action_step": 1,
                        "source_url": URL,
                        "excerpt": QUOTES[index],
                        "location": {
                            "kind": "document_ir",
                            "block_id": f"b{index + 1}",
                            "section_path": ["International bachelor admissions"],
                        },
                    }
                ],
            }
            for index, question in enumerate(QUESTIONS)
        ]
        if found
        else unresolved()
    )
    trace = {
        "case_id": "u",
        "packet_sha256": digest(packet),
        "baseline_pipeline_sha": packet["baseline_pipeline_sha"],
        "max_fetcher_calls": 60,
        "max_elapsed_ms": 90000,
        "max_search_queries": 6,
        "initial_fetcher_calls": 0,
        "initial_elapsed_ms": 0,
        "initial_search_queries": 0,
        "started_at": START.isoformat(),
        "ended_at": (START + timedelta(seconds=10)).isoformat(),
        "actions": [
            {
                "step": 1,
                "at": record["at"],
                "observed_before": "Start with the public request.",
                "observed_from_step": None,
                "tool": "fetcher",
                "url": URL,
                "final_url": URL,
                "request": record["request"],
                "action": "Read the official admissions page.",
                "outcome_status": "success",
                "outcome": "ok",
                "stage": "extraction",
                "policy_mode": "same_policy",
                "elapsed_ms": 20,
                "fetcher_calls_cumulative": 1,
                "search_queries_cumulative": 0,
                "elapsed_ms_cumulative": 20,
                "raw_log_path": "action-001.json",
                "raw_log_sha256": "0" * 64,
            }
        ],
        "proposals": proposals,
        "question_findings": findings,
        "review_status": "unreviewed",
    }
    save_record(tmp_path, trace, record)
    return trace


@pytest.mark.parametrize("excerpt", [" ", "\t\n", "\u00a0\u2003"])
def test_whitespace_only_excerpt_cannot_prove_an_official_fact(tmp_path, packet, excerpt) -> None:
    trace = trace_for(packet, tmp_path)
    trace["proposals"][1]["excerpt"] = excerpt
    trace["question_findings"][1]["evidence"][0]["excerpt"] = excerpt
    with pytest.raises(ValueError, match="Proposed quote"):
        validate_trace(trace, packet, logs_dir=tmp_path)


def test_complete_findings_are_unreviewed_and_match_the_saved_source(
    packet: dict[str, Any],
    tmp_path: Path,
) -> None:
    trace = trace_for(packet, tmp_path)
    parsed = validate_trace(trace, packet, logs_dir=tmp_path)
    assert parsed.question_findings is not None
    assert [finding.question for finding in parsed.question_findings] == list(QUESTIONS)
    assert all(proposal.status == "unreviewed" for proposal in parsed.proposals)
    assert parsed.review_status == "unreviewed"
    schema = (
        Path(__file__).resolve().parents[1] / "evaluation/research/expert/data/trace.schema.json"
    )
    assert json.loads(schema.read_text()) == ExpertTrace.model_json_schema()


@pytest.mark.parametrize("change", ["missing", "duplicate"])
def test_question_extension_requires_all_seven_questions_once(
    packet: dict[str, Any],
    tmp_path: Path,
    change: str,
) -> None:
    trace = trace_for(packet, tmp_path)
    if change == "missing":
        trace["question_findings"].pop()
    else:
        trace["question_findings"][-1]["question"] = "Q0"
    with pytest.raises(ValueError, match="Q0-Q6 exactly once"):
        validate_trace(trace, packet)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("tool", "browser"),
        ("url", "https://u.edu/different"),
        ("final_url", "https://u.edu/different"),
        ("request", {"tool": "fetcher", "url": "https://u.edu/forged"}),
        ("at", (START + timedelta(seconds=3)).isoformat()),
        ("outcome", "The page states invented IELTS 8.5."),
        ("outcome_status", "failure"),
        ("elapsed_ms", 10),
        ("fetcher_calls_cumulative", 2),
        ("elapsed_ms_cumulative", 21),
        ("search_queries_cumulative", 1),
        ("policy_mode", "outside_policy"),
    ],
)
def test_trace_cannot_replace_controller_request_summary_time_or_accounting(
    packet: dict[str, Any],
    tmp_path: Path,
    field: str,
    value: Any,
) -> None:
    trace = trace_for(packet, tmp_path, found=False)
    trace["actions"][0][field] = value
    with pytest.raises(ValueError):
        validate_trace(trace, packet, logs_dir=tmp_path)


@pytest.mark.parametrize(
    "tamper", ["replay", "missing_request", "payload_hash", "http_status", "executed", "budgets"]
)
def test_controller_record_inconsistencies_fail_even_with_a_new_log_hash(
    packet: dict[str, Any],
    tmp_path: Path,
    tamper: str,
) -> None:
    trace = trace_for(packet, tmp_path)
    record = source_record()
    if tamper == "replay":
        record["phase"] = "replay"
    elif tamper == "missing_request":
        del record["request"]
    elif tamper == "payload_hash":
        record["response"]["content_b64"] = base64.b64encode(b"Fake").decode()
    elif tamper == "http_status":
        record["response"]["status_code"] = 403
    elif tamper == "executed":
        record["executed"] = False
    else:
        record["budgets"]["max_calls"] = 61
    save_record(tmp_path, trace, record)
    with pytest.raises(ValueError):
        validate_trace(trace, packet, logs_dir=tmp_path)


def test_log_bytes_cannot_change_after_submission(packet: dict[str, Any], tmp_path: Path) -> None:
    trace = trace_for(packet, tmp_path)
    path = tmp_path / "action-001.json"
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="Raw tool log hash mismatch"):
        validate_trace(trace, packet, logs_dir=tmp_path)


@pytest.mark.parametrize("change", ["quote", "block", "heading", "hidden_script"])
def test_found_quote_must_be_in_the_real_production_text_at_its_claimed_location(
    packet: dict[str, Any],
    tmp_path: Path,
    change: str,
) -> None:
    trace = trace_for(packet, tmp_path)
    evidence = trace["question_findings"][1]["evidence"][0]
    if change == "quote":
        trace["proposals"][1]["excerpt"] = evidence["excerpt"] = "IELTS overall 8.5 is required."
    elif change == "block":
        evidence["location"]["block_id"] = "b3"
    elif change == "heading":
        evidence["location"]["section_path"] = ["Domestic students"]
    else:
        html = (
            "<main><h1>International bachelor admissions</h1>"
            + "".join(f"<p>{quote}</p>" for index, quote in enumerate(QUOTES) if index != 1)
            + f"<script>{QUOTES[1]}</script></main>"
        )
        save_record(tmp_path, trace, source_record(html))
    with pytest.raises(ValueError, match="quote|payload"):
        validate_trace(trace, packet, logs_dir=tmp_path)


@pytest.mark.parametrize(
    ("question", "key", "value"),
    [
        ("Q0", "degree", "master"),
        ("Q1", "population", "domestic"),
        ("Q2", "qualification", "US secondary diploma"),
        ("Q3", "intake", "fall 2026"),
        ("Q4", "academic_year", "2026"),
        ("Q5", "degree", "master"),
        ("Q6", "population", "domestic"),
    ],
)
def test_found_question_scope_must_match_the_public_applicant_and_intake(
    packet: dict[str, Any],
    tmp_path: Path,
    question: str,
    key: str,
    value: str,
) -> None:
    trace = trace_for(packet, tmp_path)
    index = list(QUESTIONS).index(question)
    trace["question_findings"][index]["scope"][key] = value
    trace["proposals"][index]["scope"][key] = value
    with pytest.raises(ValueError, match="scope|fee year"):
        validate_trace(trace, packet, logs_dir=tmp_path)


@pytest.mark.parametrize(
    ("question", "key"),
    [
        ("Q0", "programme"),
        ("Q1", "population"),
        ("Q2", "qualification"),
        ("Q3", "intake"),
        ("Q4", "academic_year"),
        ("Q5", "degree"),
        ("Q6", "population"),
    ],
)
def test_found_answers_cannot_omit_their_required_scope(
    packet: dict[str, Any],
    tmp_path: Path,
    question: str,
    key: str,
) -> None:
    trace = trace_for(packet, tmp_path)
    del trace["question_findings"][list(QUESTIONS).index(question)]["scope"][key]
    with pytest.raises(ValueError, match="explicit scope"):
        validate_trace(trace, packet)


def test_found_answer_needs_the_same_proposal_quote_and_actions(
    packet: dict[str, Any],
    tmp_path: Path,
) -> None:
    trace = trace_for(packet, tmp_path)
    trace["question_findings"][0]["proposal_indices"] = [1]
    with pytest.raises(ValueError, match="matching source, quote and action"):
        validate_trace(trace, packet)


@pytest.mark.parametrize(
    ("index", "wrong_quote"),
    [
        (0, "BSc Data Science is a bachelor programme."),
        (1, "Domestic applicants need IELTS Academic overall 6.5."),
        (3, "International applications for fall 2026 close on 15 January 2026."),
        (4, "International tuition for 2026/2027 is GBP 9500 per year."),
        (5, "The master programme scholarship awards GBP 2000."),
    ],
)
def test_scope_cannot_be_copied_from_the_request_onto_contradicting_source_words(
    packet: dict[str, Any],
    tmp_path: Path,
    index: int,
    wrong_quote: str,
) -> None:
    trace = trace_for(packet, tmp_path)
    quotes = list(QUOTES)
    quotes[index] = wrong_quote
    trace["proposals"][index]["excerpt"] = wrong_quote
    trace["question_findings"][index]["evidence"][0]["excerpt"] = wrong_quote
    heading = "International bachelor admissions 2027/2028"
    for finding in trace["question_findings"]:
        finding["evidence"][0]["location"]["section_path"] = [heading]
    html = f"<main><h1>{heading}</h1>" + "".join(f"<p>{quote}</p>" for quote in quotes) + "</main>"
    save_record(tmp_path, trace, source_record(html))
    with pytest.raises(ValueError, match="scope|programme name|fee year"):
        validate_trace(trace, packet, logs_dir=tmp_path)


def test_ielts_table_keeps_the_local_applicant_row_scope(
    packet: dict[str, Any],
    tmp_path: Path,
) -> None:
    trace = trace_for(packet, tmp_path, found=False)
    html = """<main><h1>Bachelor English requirements for International applicants</h1><table>
    <tr><th>Population</th><th>IELTS overall</th></tr>
    <tr><td>International applicants</td><td>7.0</td></tr>
    <tr><td>Domestic applicants</td><td>6.5</td></tr></table></main>"""
    scope = {"degree": "bachelor", "population": "international"}
    trace["proposals"] = [
        {
            "claim_key": "ielts.overall",
            "value": 6.5,
            "source_url": URL,
            "excerpt": "6.5",
            "accessed_on": "2026-10-04",
            "scope": scope,
            "supporting_steps": [1],
        }
    ]
    trace["question_findings"][1].update(
        status="found",
        supporting_steps=[1],
        proposal_indices=[0],
        scope=scope,
        evidence=[
            {
                "action_step": 1,
                "source_url": URL,
                "excerpt": "6.5",
                "location": {
                    "kind": "document_ir",
                    "block_id": "b4",
                    "section_path": ["Bachelor English requirements for International applicants"],
                },
            }
        ],
    )
    save_record(tmp_path, trace, source_record(html))
    with pytest.raises(ValueError, match="domestic applicant scope"):
        validate_trace(trace, packet, logs_dir=tmp_path)
    trace["proposals"][0].update(value=7.0, excerpt="7.0")
    trace["question_findings"][1]["evidence"][0]["excerpt"] = "7.0"
    trace["question_findings"][1]["evidence"][0]["location"]["block_id"] = "b2"
    validate_trace(trace, packet, logs_dir=tmp_path)


def test_structured_source_access_date_cannot_be_fabricated(
    packet: dict[str, Any],
    tmp_path: Path,
) -> None:
    trace = trace_for(packet, tmp_path)
    trace["proposals"][0]["accessed_on"] = "2027-10-04"
    with pytest.raises(ValueError, match="exact source payload"):
        validate_trace(trace, packet, logs_dir=tmp_path)


def test_pdf_evidence_matches_the_saved_bytes_on_the_exact_page(
    packet: dict[str, Any],
    tmp_path: Path,
) -> None:
    import io

    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    trace = trace_for(packet, tmp_path, found=False)
    writer = PdfWriter()
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    for quote in ["International tuition for 2026/2027 is GBP 9000 per year.", QUOTES[4]]:
        page = writer.add_blank_page(width=300, height=200)
        page[NameObject("/Resources")] = DictionaryObject(
            {
                NameObject("/Font"): DictionaryObject(
                    {NameObject("/F1"): writer._add_object(font)}
                ),
            }
        )
        stream = DecodedStreamObject()
        stream.set_data(f"BT /F1 12 Tf 20 40 Td ({quote}) Tj ET".encode())
        page[NameObject("/Contents")] = writer._add_object(stream)
    buffer = io.BytesIO()
    writer.write(buffer)
    body = buffer.getvalue()
    record = source_record()
    record["response"].update(
        content_type="application/pdf",
        content_b64=base64.b64encode(body).decode(),
        content_sha256=hashlib.sha256(body).hexdigest(),
    )
    trace["proposals"] = [
        {
            "claim_key": "fee.international",
            "value": 9500,
            "source_url": URL,
            "excerpt": QUOTES[4],
            "accessed_on": "2026-10-04",
            "scope": dict(SCOPE),
            "supporting_steps": [1],
        }
    ]
    trace["question_findings"][4].update(
        status="found",
        supporting_steps=[1],
        proposal_indices=[0],
        scope=dict(SCOPE),
        evidence=[
            {
                "action_step": 1,
                "source_url": URL,
                "excerpt": QUOTES[4],
                "location": {"kind": "pdf", "page": 2},
            }
        ],
    )
    save_record(tmp_path, trace, record)
    validate_trace(trace, packet, logs_dir=tmp_path)
    trace["question_findings"][4]["evidence"][0]["location"]["page"] = 1
    with pytest.raises(ValueError, match="structural location"):
        validate_trace(trace, packet, logs_dir=tmp_path)


def test_real_controller_records_match_with_wall_time_gaps_and_suppressed_redirects(
    packet: dict[str, Any],
    tmp_path: Path,
) -> None:
    trace = trace_for(packet, tmp_path)
    body = base64.b64decode(source_record()["response"]["content_b64"])

    async def get(url: str) -> Any:
        return SimpleNamespace(
            url=url,
            final_url="https://attacker.example/" if url.endswith("redirect") else url,
            content=body,
            content_type="text/html",
            outcome=SimpleNamespace(value="ok"),
            ok=True,
            status_code=200,
            error="",
            fetched_at=START,
            from_cache=False,
            fetch_tier="http",
        )

    ticks = iter([0.0, 0.013, 0.019, 0.041, 0.051, 0.057, 0.071])
    summary = asyncio.run(
        execute(
            {
                "case_id": "u",
                "log_prefix": "controlled",
                "max_calls": 60,
                "max_ms": 90000,
                "max_search_queries": 6,
                "strict_budget": True,
                "official_domains": ["u.edu"],
                "actions": [URL, URL + "/redirect"],
            },
            tmp_path,
            get=get,
            search=None,
            provider_name="exa",
            now=lambda: START + timedelta(seconds=2),
            monotonic=lambda: next(ticks),
        )
    )
    base = trace["actions"][0]
    trace["actions"] = [
        {
            **base,
            **{key: value for key, value in entry.items() if key in base},
            "step": index + 1,
            "observed_from_step": index or None,
            "url": entry["request"]["url"],
        }
        for index, entry in enumerate(summary["actions"])
    ]
    assert trace["actions"][0]["elapsed_ms_cumulative"] > trace["actions"][0]["elapsed_ms"]
    assert trace["actions"][1]["outcome_status"] == "blocked"
    validate_trace(trace, packet, logs_dir=tmp_path)


def test_real_controller_search_429_failure_and_stop_keep_the_query_charge(
    packet: dict[str, Any],
    tmp_path: Path,
) -> None:
    trace = trace_for(packet, tmp_path, found=False)

    class QuotaError(RuntimeError):
        http_status = 429

    async def search(**kwargs: Any) -> Any:
        raise QuotaError("Provider quota exhausted")

    async def get(url: str) -> Any:
        raise AssertionError("No page read was requested")

    request = {
        "tool": "search_provider",
        "query": "computer science site:u.edu",
        "domains": ["u.edu"],
    }
    summary = asyncio.run(
        execute(
            {
                "case_id": "u",
                "log_prefix": "search",
                "max_calls": 60,
                "max_ms": 90000,
                "max_search_queries": 6,
                "strict_budget": True,
                "official_domains": ["u.edu"],
                "actions": [request, request],
            },
            tmp_path,
            get=get,
            search=search,
            provider_name="exa_mcp",
            now=lambda: START + timedelta(seconds=2),
            monotonic=lambda: 0.0,
        )
    )
    base = trace["actions"][0]
    trace["actions"] = [
        {
            **base,
            **{key: value for key, value in entry.items() if key in base},
            "step": index + 1,
            "observed_from_step": index or None,
            "url": None,
        }
        for index, entry in enumerate(summary["actions"])
    ]
    assert summary["final"]["search_queries"] == 1
    validate_trace(trace, packet, logs_dir=tmp_path)
    trace["actions"][0]["search_queries_cumulative"] = 0
    with pytest.raises(ValueError, match="search accounting"):
        validate_trace(trace, packet, logs_dir=tmp_path)


def test_not_published_requires_an_explicit_official_statement(
    packet: dict[str, Any],
    tmp_path: Path,
) -> None:
    trace = trace_for(packet, tmp_path, found=False)
    statement = "Fees for 2027/2028 have not yet been published."
    trace["question_findings"][4].update(
        status="not_published",
        supporting_steps=[1],
        scope=dict(SCOPE),
        evidence=[
            {
                "action_step": 1,
                "source_url": URL,
                "excerpt": statement,
                "location": {"kind": "text"},
            }
        ],
    )
    save_record(tmp_path, trace, source_record(f"<main><p>{statement}</p></main>"))
    validate_trace(trace, packet, logs_dir=tmp_path)

    trace["question_findings"][4]["evidence"][0]["excerpt"] = (
        "We searched two pages and did not find fees."
    )
    with pytest.raises(ValueError, match="explicit official publication statement"):
        validate_trace(trace, packet)

    trace["question_findings"][4]["status"] = "unresolved"
    trace["question_findings"][4]["evidence"] = []
    validate_trace(trace, packet, logs_dir=tmp_path)


def test_not_published_statement_must_be_in_the_saved_official_payload(
    packet: dict[str, Any],
    tmp_path: Path,
) -> None:
    trace = trace_for(packet, tmp_path, found=False)
    trace["question_findings"][4].update(
        status="not_published",
        supporting_steps=[1],
        scope=dict(SCOPE),
        evidence=[
            {
                "action_step": 1,
                "source_url": URL,
                "excerpt": "The tuition fee has not yet been published.",
                "location": {"kind": "text"},
            }
        ],
    )
    with pytest.raises(ValueError, match="absent from its exact official source"):
        validate_trace(trace, packet, logs_dir=tmp_path)


def test_inaccessible_is_supported_by_an_actual_failure_and_cannot_supply_a_found_fact(
    packet: dict[str, Any],
    tmp_path: Path,
) -> None:
    trace = trace_for(packet, tmp_path, found=False)
    record = source_record()
    record["response"].update(
        outcome="http_error", outcome_status="failure", ok=False, status_code=403
    )
    record["outcome_status"] = "failure"
    trace["actions"][0].update(outcome="http_error", outcome_status="failure")
    trace["question_findings"][2].update(status="inaccessible", supporting_steps=[1])
    save_record(tmp_path, trace, record)
    validate_trace(trace, packet, logs_dir=tmp_path)
    trace["question_findings"][2]["status"] = "found"
    with pytest.raises(ValueError, match="source evidence"):
        validate_trace(trace, packet, logs_dir=tmp_path)


def test_search_failure_does_not_prove_official_page_inaccessibility(
    packet: dict[str, Any],
    tmp_path: Path,
) -> None:
    trace = trace_for(packet, tmp_path, found=False)
    trace["actions"][0].update(tool="search_provider", outcome_status="failure")
    trace["question_findings"][2].update(status="inaccessible", supporting_steps=[1])
    with pytest.raises(ValueError, match="failed or blocked page read"):
        validate_trace(trace, packet)


def test_safe_redirect_uses_the_exact_final_source_url(
    packet: dict[str, Any], tmp_path: Path
) -> None:
    trace = trace_for(packet, tmp_path)
    record = source_record()
    final = "https://admissions.u.edu/2027"
    record["response"]["final_url"] = final
    trace["actions"][0]["final_url"] = final
    for proposal, finding in zip(trace["proposals"], trace["question_findings"], strict=True):
        proposal["source_url"] = finding["evidence"][0]["source_url"] = final
    save_record(tmp_path, trace, record)
    validate_trace(trace, packet, logs_dir=tmp_path)
    trace["proposals"][0]["source_url"] = trace["question_findings"][0]["evidence"][0][
        "source_url"
    ] = URL
    with pytest.raises(ValueError, match="exact source payload"):
        validate_trace(trace, packet, logs_dir=tmp_path)


@pytest.mark.parametrize(
    "final",
    [
        "https://u.edu.attacker.example/admissions",
        "https://attacker.example/?source=u.edu",
        "https://u.edu@attacker.example/admissions",
    ],
)
def test_source_authority_cannot_be_obtained_from_redirect_path_query_or_userinfo(
    packet: dict[str, Any],
    tmp_path: Path,
    final: str,
) -> None:
    trace = trace_for(packet, tmp_path)
    record = source_record()
    record["response"]["final_url"] = trace["actions"][0]["final_url"] = final
    for proposal, finding in zip(trace["proposals"], trace["question_findings"], strict=True):
        proposal["source_url"] = finding["evidence"][0]["source_url"] = final
    save_record(tmp_path, trace, record)
    with pytest.raises(ValueError, match="official exact source payload"):
        validate_trace(trace, packet, logs_dir=tmp_path)


def test_legacy_unstructured_logs_retain_byte_only_semantics(
    packet: dict[str, Any],
    tmp_path: Path,
) -> None:
    trace = trace_for(packet, tmp_path)
    del trace["question_findings"]
    trace["actions"][0]["outcome"] = "Legacy narrative, without independently structured output."
    save_record(tmp_path, trace, {"status": "observed"})
    validate_trace(trace, packet, logs_dir=tmp_path)
    trace["question_findings"] = unresolved()
    with pytest.raises(ValueError, match="independent structured controller logs"):
        validate_trace(trace, packet, logs_dir=tmp_path)


def test_miss_causes_remain_separate_and_need_observable_post_submission_support(
    packet: dict[str, Any],
    tmp_path: Path,
) -> None:
    trace = trace_for(packet, tmp_path, found=False)
    adjudication: dict[str, Any] = {
        "trace_sha256": digest(trace),
        "misses": [
            {
                "question": "Q2",
                "cause": "EXTRACTOR",
                "supporting_steps": [1],
                "observations": [{"action_step": 1, "field": "response.status_code", "value": 200}],
                "reason": "The saved page was readable; the proposed rule still needs evaluation.",
            }
        ],
    }
    assert isinstance(
        validate_trace_adjudication(adjudication, trace, logs_dir=tmp_path), TraceAdjudication
    )
    trace["misses"] = adjudication["misses"]
    with pytest.raises(ValidationError):
        ExpertTrace.model_validate(trace)
    del trace["misses"]
    adjudication["misses"][0]["observations"][0]["value"] = 403
    with pytest.raises(ValueError, match="differs from the recorded controller field"):
        validate_trace_adjudication(adjudication, trace, logs_dir=tmp_path)
    adjudication["trace_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="exact submitted trace"):
        validate_trace_adjudication(adjudication, trace, logs_dir=tmp_path)


@pytest.mark.parametrize(
    "cause",
    [
        "NOT_DISCOVERED",
        "BUDGET",
        "SLOT",
        "CLASSIFIER",
        "EXTRACTOR",
        "OTHER_PAGE",
        "PDF",
        "JS",
        "SCOPE",
        "ACCESS",
    ],
)
def test_miss_vocabulary_requires_recorded_observations(cause: str) -> None:
    miss: dict[str, Any] = {
        "trace_sha256": "a" * 64,
        "misses": [
            {
                "question": "Q0",
                "cause": cause,
                "supporting_steps": [1],
                "observations": [{"action_step": 1, "field": "response.outcome", "value": "ok"}],
                "reason": "Observable controller evidence supports a provisional evaluator diagnosis.",
            }
        ],
    }
    TraceAdjudication.model_validate(miss)
    empty = deepcopy(miss)
    empty["misses"][0]["observations"] = []
    with pytest.raises(ValidationError):
        TraceAdjudication.model_validate(empty)
