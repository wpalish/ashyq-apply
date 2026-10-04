"""Stored PDF representations are readable evidence, with no new tool calls.

The existing Groningen file is a synthetic demo fixture in real PDF format.
These tests establish representation/linkage, never live official facts.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import io
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject

from app.adapters.extraction import pdf_to_text
from app.adapters.fetching import FetchResult
from app.domain.enums import FetchOutcome
from evaluation.research.expert.controller import MAX_VIEW_CHARS, execute, expert_view
from evaluation.research.expert.models import QUESTIONS, validate_trace
from evaluation.research.expert.packet import digest

FIXTURE = Path(__file__).resolve().parents[1] / "app/corpus/pages/u-groningen/fees.pdf"
URL = "https://www.rug.nl/education/fees.pdf"
START = datetime(2026, 10, 4, tzinfo=UTC)


def record_for(body: bytes) -> dict[str, Any]:
    return {
        "request": {"tool": "fetcher", "url": URL},
        "policy_mode": "same_policy",
        "outcome_status": "success",
        "response": {
            "outcome": "ok",
            "ok": True,
            "outcome_status": "success",
            "status_code": 200,
            "final_url": URL,
            "content_type": "application/pdf",
            "fetch_tier": "http",
            "content_b64": base64.b64encode(body).decode(),
            "content_sha256": hashlib.sha256(body).hexdigest(),
            "fetched_at": START.isoformat(),
            "from_cache": False,
            "error": "",
        },
    }


def multi_page_pdf(
    *, blank_first: bool = False, repeats: int = 1, long_page: bool = False
) -> bytes:
    reader = PdfReader(io.BytesIO(FIXTURE.read_bytes()))
    writer = PdfWriter()
    if blank_first:
        writer.add_blank_page(width=300, height=200)
    for _ in range(repeats):
        page = writer.add_page(reader.pages[0])
        if long_page:
            stream = DecodedStreamObject()
            contents = reader.pages[0].get_contents()
            assert contents is not None
            stream.set_data(contents.get_data() * 200)
            page[NameObject("/Contents")] = writer._add_object(stream)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def test_existing_pdf_fixture_has_readable_production_text_and_page_fingerprints() -> None:
    body = FIXTURE.read_bytes()
    view = expert_view(record_for(body))
    page_text = PdfReader(io.BytesIO(body)).pages[0].extract_text()
    assert view["text"] == pdf_to_text(body, max_pages=40)
    assert "SYNTHETIC DEMO FIXTURE" in view["text"]
    assert view["content_sha256"] == hashlib.sha256(body).hexdigest()
    assert view["text_sha256"] == hashlib.sha256(view["text"].encode()).hexdigest()
    assert view["pdf_status"] == "readable"
    assert view["pdf_error"] is None
    assert view["pdf_page"] is None
    assert view["pdf_pages_total"] == view["pdf_pages_read"] == 1
    assert view["pdf_page_limit_reached"] is False
    assert view["pdf_pages"] == [
        {
            "page": 1,
            "text_total_chars": len(page_text),
            "text_sha256": hashlib.sha256(page_text.encode()).hexdigest(),
            "has_text": True,
        }
    ]
    assert "text" not in view["pdf_pages"][0]


def test_page_selection_uses_exact_one_based_pdf_locations() -> None:
    body = multi_page_pdf(blank_first=True)
    record = record_for(body)
    page_text = PdfReader(io.BytesIO(body)).pages[1].extract_text()
    view = expert_view(record, page=2)
    assert view["text"] == page_text
    assert view["pdf_page"] == 2
    assert [item["page"] for item in view["pdf_pages"]] == [1, 2]
    assert view["pdf_pages"][0]["has_text"] is False
    assert view["pdf_pages"][1]["text_sha256"] == view["text_sha256"]
    empty = expert_view(record, page=1)
    assert empty["pdf_status"] == "unresolved"
    assert empty["pdf_error"] == "pdf_no_extractable_text"
    assert empty["text"] == ""


@pytest.mark.parametrize("page", [None, 2])
def test_pdf_text_pagination_reconstructs_one_stable_representation(page: int | None) -> None:
    body = multi_page_pdf(blank_first=True)
    record = record_for(body)
    expected = (
        pdf_to_text(body) if page is None else PdfReader(io.BytesIO(body)).pages[1].extract_text()
    )
    parts = []
    offset = 0
    while True:
        view = expert_view(record, page=page, chars=31, offset=offset)
        assert len(view["text"]) <= 31
        assert view["text_offset"] == offset
        assert view["text_total_chars"] == len(expected)
        assert view["text_sha256"] == hashlib.sha256(expected.encode()).hexdigest()
        parts.append(view["text"])
        if view["text_next_offset"] is None:
            break
        offset = view["text_next_offset"]
    assert "".join(parts) == expected


def test_large_pdf_text_obeys_the_existing_global_character_limit() -> None:
    body = multi_page_pdf(long_page=True)
    expected = pdf_to_text(body)
    assert len(expected) > MAX_VIEW_CHARS
    view = expert_view(record_for(body), chars=MAX_VIEW_CHARS + 100000)
    assert view["text"] == expected[:MAX_VIEW_CHARS]
    assert view["text_next_offset"] == MAX_VIEW_CHARS
    assert all("text" not in page for page in view["pdf_pages"])


def test_pdf_extraction_stops_at_forty_pages_and_reports_the_limit() -> None:
    body = multi_page_pdf(repeats=41)
    view = expert_view(record_for(body), chars=MAX_VIEW_CHARS)
    assert view["pdf_pages_total"] == 41
    assert view["pdf_pages_read"] == 40
    assert view["pdf_page_limit_reached"] is True
    assert len(view["pdf_pages"]) == 40
    assert view["text"] == pdf_to_text(body, max_pages=40)
    with pytest.raises(ValueError, match="page"):
        expert_view(record_for(body), page=41)


@pytest.mark.parametrize("body", [b"%PDF-1.7 malformed", b"not a PDF"])
def test_malformed_pdf_is_explicitly_unresolved_and_has_no_evidence_text(body: bytes) -> None:
    view = expert_view(record_for(body))
    assert view["pdf_status"] == "unresolved"
    assert view["pdf_error"] == "pdf_decode_error"
    assert view["pdf_pages"] == []
    assert view["pdf_pages_read"] == 0
    assert view["text"] == ""
    assert view["text_total_chars"] == 0
    assert view["text_next_offset"] is None


def test_scanned_or_empty_pdf_stays_unknown_without_ocr() -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=200)
    output = io.BytesIO()
    writer.write(output)
    view = expert_view(record_for(output.getvalue()))
    assert view["pdf_pages_total"] == view["pdf_pages_read"] == 1
    assert view["pdf_status"] == "unresolved"
    assert view["pdf_error"] == "pdf_no_extractable_text"
    assert view["text"] == ""
    assert view["pdf_pages"][0]["has_text"] is False


def test_missing_pdf_payload_is_explicitly_unresolved() -> None:
    view = expert_view(record_for(b""))
    assert view["pdf_status"] == "unresolved"
    assert view["pdf_error"] == "pdf_payload_unavailable"
    assert view["text"] == ""


@pytest.mark.parametrize("page", [0, -1, True, "1", 3])
def test_invalid_or_nonexistent_page_number_is_rejected(page: Any) -> None:
    with pytest.raises(ValueError, match="page"):
        expert_view(record_for(multi_page_pdf(blank_first=True)), page=page)


def test_pdf_payload_hash_mismatch_is_rejected_before_parsing() -> None:
    record = record_for(FIXTURE.read_bytes())
    record["response"]["content_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="Stored content hash mismatch"):
        expert_view(record)


def test_pdf_view_quote_validates_against_the_same_controller_log_and_exact_page(
    tmp_path: Path,
) -> None:
    body = multi_page_pdf(blank_first=True)
    get_calls = search_calls = 0

    async def get(url: str) -> FetchResult:
        nonlocal get_calls
        get_calls += 1
        return FetchResult(
            url,
            FetchOutcome.OK,
            status_code=200,
            content=body,
            final_url=url,
            content_type="application/pdf",
            fetched_at=START,
        )

    async def search(**kwargs: Any) -> Any:
        nonlocal search_calls
        search_calls += 1
        raise AssertionError("No search query is requested")

    plan = {
        "case_id": "pdf-fixture",
        "strict_budget": True,
        "max_calls": 60,
        "max_ms": 120000,
        "max_search_queries": 6,
        "official_domains": ["rug.nl"],
        "actions": [URL],
    }
    summary = asyncio.run(
        execute(
            plan,
            tmp_path,
            get=get,
            search=search,
            provider_name="exa_mcp",
            now=lambda: START + timedelta(seconds=2),
            monotonic=lambda: 0.0,
        )
    )
    entry = summary["actions"][0]
    log = tmp_path / entry["raw_log_path"]
    original = log.read_bytes()
    view = expert_view(json.loads(original), page=2)
    excerpt = "Academic year 2026/27 - SYNTHETIC DEMO FIXTURE\nTuition fee [non-EEA students]: EUR 16,500 per year"
    assert excerpt in view["text"]
    packet = {
        "baseline_pipeline_sha": "abcdef0123456789",
        "comparison_mode": "independent_full_budget",
        "baseline_budget": {
            "max_fetcher_calls": 60,
            "max_elapsed_ms": 120000,
            "max_search_queries": 6,
            "browser_enabled": False,
        },
        "cases": [
            {
                "case_id": "pdf-fixture",
                "domain": "rug.nl",
                "request": {
                    "degree": "bachelor",
                    "intake": "fall 2026",
                    "academic_year": "2026/27",
                    "population": "international",
                    "programme": None,
                },
            }
        ],
    }
    scope = {"degree": "bachelor", "population": "international", "academic_year": "2026/27"}
    findings: list[dict[str, Any]] = [
        {"question": question, "status": "unresolved", "observation": "Not examined."}
        for question in QUESTIONS
    ]
    findings[4].update(
        status="found",
        scope=scope,
        supporting_steps=[1],
        proposal_indices=[0],
        evidence=[
            {
                "action_step": 1,
                "source_url": URL,
                "excerpt": excerpt,
                "location": {"kind": "pdf", "page": view["pdf_page"]},
            }
        ],
    )
    trace = {
        "case_id": "pdf-fixture",
        "packet_sha256": digest(packet),
        "baseline_pipeline_sha": packet["baseline_pipeline_sha"],
        "max_fetcher_calls": 60,
        "max_elapsed_ms": 120000,
        "max_search_queries": 6,
        "initial_fetcher_calls": 0,
        "initial_elapsed_ms": 0,
        "started_at": START.isoformat(),
        "ended_at": (START + timedelta(seconds=10)).isoformat(),
        "actions": [
            {
                **{key: value for key, value in entry.items() if key != "executed"},
                "step": 1,
                "observed_before": "Inspect the stored synthetic PDF fixture.",
                "url": URL,
                "action": "Read saved PDF",
                "stage": "representation",
            }
        ],
        "proposals": [
            {
                "claim_key": "fee.international",
                "value": {"amount": 16500, "currency": "EUR"},
                "source_url": URL,
                "excerpt": excerpt,
                "accessed_on": "2026-10-04",
                "scope": scope,
                "supporting_steps": [1],
            }
        ],
        "question_findings": findings,
    }
    validate_trace(trace, packet, logs_dir=tmp_path)
    findings[4]["evidence"][0]["location"]["page"] = 1
    with pytest.raises(ValueError, match="structural location"):
        validate_trace(trace, packet, logs_dir=tmp_path)
    assert log.read_bytes() == original
    assert get_calls == summary["final"]["fetcher_calls"] == 1
    assert search_calls == summary["final"]["search_queries"] == 0
