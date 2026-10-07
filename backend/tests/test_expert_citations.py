"""Synthetic saved sources check every compact fact without network or labels."""

from __future__ import annotations

import base64
import hashlib
import io
import json
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from evaluation.research.expert.citations import validate_fact_citations
from evaluation.research.expert.compact import parse_compact_decision
from evaluation.research.expert.models import Action

START = datetime(2026, 10, 4, tzinfo=UTC)
URL = "https://example.edu/admissions"
QUOTE = "International bachelor applicants need Example English overall 7.25."
HEADING = "International bachelor admissions"


def _scope(**changes: str | None) -> dict[str, str | None]:
    return {
        "university": "Example University",
        "programme": None,
        "degree": "bachelor",
        "field": None,
        "intake": None,
        "population": "international",
        "qualification": None,
        "academic_year": None,
        **changes,
    }


def _fact(**changes: Any) -> dict[str, Any]:
    return {
        "id": "example_english",
        "question": "Q1",
        "claim_key": "english_evidence.example.minimum",
        "value_json": "7.25",
        "source_step": 1,
        "quotation": QUOTE,
        "location": {"kind": "text", "block_id": None, "section_path": [], "page": None},
        "scope": _scope(),
        **changes,
    }


def _decision(*facts: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": "submit",
        "observation": "Explicit synthetic source facts; applicability remains unreviewed.",
        "action": None,
        "facts": list(facts) or [_fact()],
        "question_findings": [],
    }


def _packet(**changes: Any) -> dict[str, Any]:
    return {
        "cases": [
            {
                "case_id": "example",
                "university": "Example University",
                "domain": "example.edu",
                **changes,
            }
        ]
    }


def _save(tmp_path: Path, action: dict[str, Any], record: dict[str, Any]) -> None:
    data = json.dumps(record, ensure_ascii=False).encode()
    path = tmp_path / action["raw_log_path"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    action["raw_log_sha256"] = hashlib.sha256(data).hexdigest()


def _source(
    tmp_path: Path,
    *,
    step: int = 1,
    body: bytes | None = None,
    content_type: str = "text/html",
    final_url: str = URL,
) -> tuple[dict[str, Any], dict[str, Any]]:
    body = body if body is not None else f"<main><h1>{HEADING}</h1><p>{QUOTE}</p></main>".encode()
    action = {
        "step": step,
        "at": (START + timedelta(seconds=step)).isoformat(),
        "observed_before": "An explicit public source is available.",
        "observed_from_step": step - 1 if step > 1 else None,
        "tool": "fetcher",
        "action": "Read the synthetic official source.",
        "outcome_status": "success",
        "outcome": "ok",
        "stage": "extraction",
        "policy_mode": "same_policy",
        "url": URL,
        "final_url": final_url,
        "request": {"tool": "fetcher", "url": URL},
        "raw_log_path": f"action-{step:03}.json",
        "raw_log_sha256": "0" * 64,
        "elapsed_ms": 20,
        "fetcher_calls_cumulative": step,
        "search_queries_cumulative": 0,
        "elapsed_ms_cumulative": step * 20,
    }
    record = {
        "case_id": "example",
        "request": action["request"],
        "at": action["at"],
        "phase": "actions",
        "executed": True,
        "outcome_status": "success",
        "response": {
            "outcome": "ok",
            "outcome_status": "success",
            "ok": True,
            "status_code": 200,
            "final_url": final_url,
            "content_type": content_type,
            "fetch_tier": "http",
            "content_sha256": hashlib.sha256(body).hexdigest(),
            "content_b64": base64.b64encode(body).decode(),
        },
        "elapsed_ms": 20,
        "elapsed_ms_before": (step - 1) * 20,
        "charged_elapsed_ms": 20,
        "elapsed_ms_cumulative": action["elapsed_ms_cumulative"],
        "fetcher_calls_cumulative": action["fetcher_calls_cumulative"],
        "search_queries_cumulative": 0,
        "policy_mode": "same_policy",
    }
    _save(tmp_path, action, record)
    return action, record


def _validate(
    tmp_path: Path, decision: Any, actions: list[Any], packet: dict[str, Any] | None = None
) -> list[dict[str, Any]]:
    return validate_fact_citations(
        decision, actions, logs_dir=tmp_path, packet=packet if packet is not None else _packet()
    )


def _pdf(*quotes: str) -> bytes:
    writer = PdfWriter()
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    for quote in quotes:
        page = writer.add_blank_page(width=600, height=200)
        page[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})}
        )
        stream = DecodedStreamObject()
        stream.set_data(f"BT /F1 10 Tf 10 40 Td ({quote}) Tj ET".encode())
        page[NameObject("/Contents")] = writer._add_object(stream)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


@pytest.mark.parametrize("input_kind", ["mapping", "json", "model"])
def test_typed_inputs_preserve_complete_literal_proof_and_proposal_order(
    tmp_path: Path, input_kind: str
) -> None:
    action, _record = _source(tmp_path)
    facts = [_fact(), _fact(id="unreferenced_other", question="OTHER")]
    decision: Any = _decision(*facts)
    if input_kind == "json":
        decision = json.dumps(decision)
    if input_kind == "model":
        decision = parse_compact_decision(decision)
    proof = _validate(tmp_path, decision, [Action.model_validate(action)])
    assert proof == [
        {
            "fact_id": fact["id"],
            "proposal_index": index,
            "source_step": 1,
            "raw_log_sha256": action["raw_log_sha256"],
            "source_url": URL,
            "quotation_sha256": hashlib.sha256(QUOTE.encode()).hexdigest(),
            "location": fact["location"],
            "scope": fact["scope"],
        }
        for index, fact in enumerate(facts)
    ]


@pytest.mark.parametrize("question", ["Q1", "OTHER"])
def test_unreferenced_facts_cannot_bypass_wrong_quote_or_normalized_empty_quote(
    tmp_path: Path, question: str
) -> None:
    action, _record = _source(tmp_path)
    for quotation in ["International applicants need Example English overall 1.0.", "---"]:
        with pytest.raises(ValueError, match="quote or location"):
            _validate(tmp_path, _decision(_fact(question=question, quotation=quotation)), [action])


def test_a_later_bad_other_fact_rejects_the_entire_citation_proof(tmp_path: Path) -> None:
    action, _record = _source(tmp_path)
    decision = _decision(
        _fact(), _fact(id="other_bad", question="OTHER", quotation="This source never states this.")
    )
    with pytest.raises(ValueError, match="quote or location"):
        _validate(tmp_path, decision, [action])


def test_document_ir_quote_requires_its_exact_block_and_section_path(tmp_path: Path) -> None:
    action, _record = _source(tmp_path)
    location: dict[str, Any] = {
        "kind": "document_ir",
        "block_id": "b1",
        "section_path": [HEADING],
        "page": None,
    }
    assert (
        _validate(tmp_path, _decision(_fact(location=location)), [action])[0]["location"]
        == location
    )
    wrong_coordinates: list[dict[str, Any]] = [
        {"block_id": "b0"},
        {"section_path": ["Domestic master admissions"]},
    ]
    for changes in wrong_coordinates:
        with pytest.raises(ValueError, match="quote or location"):
            _validate(tmp_path, _decision(_fact(location={**location, **changes})), [action])


def test_pdf_requires_the_exact_page_instead_of_aggregate_text(tmp_path: Path) -> None:
    action, _record = _source(
        tmp_path,
        body=_pdf("Domestic master policy differs.", QUOTE),
        content_type="application/pdf",
    )
    location: dict[str, Any] = {"kind": "pdf", "block_id": None, "section_path": [], "page": 2}
    assert (
        _validate(tmp_path, _decision(_fact(location=location)), [action])[0]["location"]
        == location
    )
    for wrong in [{**location, "page": 1}, {**location, "page": 3}, _fact()["location"]]:
        with pytest.raises(ValueError, match="quote or location"):
            _validate(tmp_path, _decision(_fact(location=wrong)), [action])


@pytest.mark.parametrize("question", ["Q1", "OTHER"])
def test_visible_degree_and_domestic_scope_conflicts_apply_to_every_fact(
    tmp_path: Path, question: str
) -> None:
    for quote, message in [
        ("International master applicants need Example English overall 7.25.", "degree scope"),
        (
            "Domestic applicants in the bachelor programme need Example English overall 7.25.",
            "domestic",
        ),
    ]:
        action, _record = _source(tmp_path, body=f"<p>{quote}</p>".encode())
        with pytest.raises(ValueError, match=message):
            _validate(tmp_path, _decision(_fact(question=question, quotation=quote)), [action])


def test_ir_scope_checks_heading_and_local_evidence_context(tmp_path: Path) -> None:
    quote = "Example English overall 7.25 is required."
    heading = "Bachelor admissions for Domestic applicants"
    action, _record = _source(tmp_path, body=f"<h1>{heading}</h1><p>{quote}</p>".encode())
    location = {"kind": "document_ir", "block_id": "b1", "section_path": [heading], "page": None}
    with pytest.raises(ValueError, match="domestic"):
        _validate(tmp_path, _decision(_fact(quotation=quote, location=location)), [action])


@pytest.mark.parametrize(
    "question,quote,scope,message",
    [
        (
            "Q0",
            "Bachelor Fictional Studies is a bachelor programme.",
            _scope(programme="Bachelor Different Studies"),
            "exact programme",
        ),
        (
            "Q3",
            "International bachelor applications for fall 2030 close on 1 February 2030.",
            _scope(intake="fall 2031"),
            "intake scope",
        ),
        (
            "Q4",
            "International bachelor tuition for 2030/2031 is EUR 1234 per year.",
            _scope(academic_year="2031/2032"),
            "academic_year",
        ),
    ],
)
def test_question_specific_visible_scope_conflicts_are_preserved(
    tmp_path: Path, question: str, quote: str, scope: dict[str, str | None], message: str
) -> None:
    action, _record = _source(tmp_path, body=f"<p>{quote}</p>".encode())
    with pytest.raises(ValueError, match=message):
        _validate(
            tmp_path, _decision(_fact(question=question, quotation=quote, scope=scope)), [action]
        )


@pytest.mark.parametrize("question", ["OTHER", "Q1"])
@pytest.mark.parametrize(
    "dimension,quote,incorrect,correct,message",
    [
        (
            "programme",
            "Bachelor Fictional Studies is a bachelor programme.",
            "Bachelor Different Studies",
            "Bachelor Fictional Studies",
            "exact programme",
        ),
        (
            "intake",
            "International bachelor applications for fall 2030 close on 1 February 2030.",
            "fall 2031",
            "fall 2030",
            "intake scope",
        ),
        (
            "academic_year",
            "International bachelor tuition for 2030/2031 is EUR 1234 per year.",
            "2031/2032",
            "2030/2031",
            "academic_year",
        ),
    ],
)
def test_declared_scope_guards_apply_to_other_and_unreferenced_questions(
    tmp_path: Path,
    question: str,
    dimension: str,
    quote: str,
    incorrect: str,
    correct: str,
    message: str,
) -> None:
    action, _record = _source(tmp_path, body=f"<p>{quote}</p>".encode())
    with pytest.raises(ValueError, match=message):
        _validate(
            tmp_path,
            _decision(
                _fact(question=question, quotation=quote, scope=_scope(**{dimension: incorrect}))
            ),
            [action],
        )
    proof = _validate(
        tmp_path,
        _decision(_fact(question=question, quotation=quote, scope=_scope(**{dimension: correct}))),
        [action],
    )
    assert proof[0]["scope"][dimension] == correct


@pytest.mark.parametrize("question", ["OTHER", "Q1"])
def test_unknown_programme_intake_and_year_stay_null_without_forced_scope(
    tmp_path: Path, question: str
) -> None:
    action, _record = _source(tmp_path)
    proof = _validate(tmp_path, _decision(_fact(question=question)), [action])
    assert {key: proof[0]["scope"][key] for key in ("programme", "intake", "academic_year")} == {
        "programme": None,
        "intake": None,
        "academic_year": None,
    }


@pytest.mark.parametrize("question", ["OTHER", "Q1"])
def test_html_text_quote_cannot_hide_its_actual_master_heading(
    tmp_path: Path, question: str
) -> None:
    quote = "Example English overall 7.25 is required."
    heading = "International master programme"
    action, _record = _source(tmp_path, body=f"<h1>{heading}</h1><p>{quote}</p>".encode())
    with pytest.raises(ValueError, match="degree scope"):
        _validate(tmp_path, _decision(_fact(question=question, quotation=quote)), [action])


def test_ambiguous_html_text_requires_precise_ir_without_using_other_blocks(
    tmp_path: Path,
) -> None:
    quote = "Example English overall 7.25 is required."
    heading = "International bachelor programme"
    body = (
        f"<h1>International master programme</h1><p>{quote}</p><h1>{heading}</h1><p>{quote}</p>"
    ).encode()
    action, _record = _source(tmp_path, body=body)
    with pytest.raises(ValueError, match="unambiguous|explicit structural"):
        _validate(tmp_path, _decision(_fact(quotation=quote)), [action])
    location = {"kind": "document_ir", "block_id": "b3", "section_path": [heading], "page": None}
    proof = _validate(tmp_path, _decision(_fact(quotation=quote, location=location)), [action])
    assert proof[0]["location"] == location


def test_pdf_scope_uses_the_selected_page_with_its_neutral_quote(tmp_path: Path) -> None:
    quote = "Example English overall 7.25 is required."
    action, _record = _source(
        tmp_path,
        body=_pdf(
            "International master programme. " + quote,
            "International bachelor programme. " + quote,
        ),
        content_type="application/pdf",
    )
    location: dict[str, Any] = {"kind": "pdf", "block_id": None, "section_path": [], "page": 1}
    with pytest.raises(ValueError, match="degree scope"):
        _validate(tmp_path, _decision(_fact(quotation=quote, location=location)), [action])
    location["page"] = 2
    proof = _validate(tmp_path, _decision(_fact(quotation=quote, location=location)), [action])
    assert proof[0]["location"] == location


@pytest.mark.parametrize("content_type", ["text/plain", "application/xml"])
def test_plain_saved_context_cannot_omit_an_explicit_master_scope(
    tmp_path: Path, content_type: str
) -> None:
    quote = "Example English overall 7.25 is required."
    body = f"International master programme\n{quote}".encode()
    action, _record = _source(tmp_path, body=body, content_type=content_type)
    with pytest.raises(ValueError, match="degree scope"):
        _validate(tmp_path, _decision(_fact(quotation=quote)), [action])


@pytest.mark.parametrize("content_type", ["application/pdf", "text/plain", "application/xml"])
@pytest.mark.parametrize(
    "quote,message",
    [
        ("International master applicants need Example English overall 7.25.", "degree scope"),
        (
            "Domestic applicants in the bachelor programme need Example English overall 7.25.",
            "domestic",
        ),
    ],
)
def test_mixed_saved_context_cannot_mask_an_explicit_conflict_in_the_original_quote(
    tmp_path: Path, content_type: str, quote: str, message: str
) -> None:
    context = quote + " International applicants follow a different bachelor programme policy."
    body = _pdf(context) if content_type == "application/pdf" else context.encode()
    action, _record = _source(tmp_path, body=body, content_type=content_type)
    location = (
        {"kind": "pdf", "block_id": None, "section_path": [], "page": 1}
        if content_type == "application/pdf"
        else _fact()["location"]
    )
    with pytest.raises(ValueError, match=message):
        _validate(
            tmp_path,
            _decision(_fact(question="OTHER", quotation=quote, location=location)),
            [action],
        )


def test_short_pdf_quote_can_use_its_selected_page_for_the_declared_fee_year(
    tmp_path: Path,
) -> None:
    quote = "International bachelor tuition is EUR 1234 per year."
    action, _record = _source(
        tmp_path, body=_pdf("Fees for 2030/2031. " + quote), content_type="application/pdf"
    )
    location: dict[str, Any] = {"kind": "pdf", "block_id": None, "section_path": [], "page": 1}
    proof = _validate(
        tmp_path,
        _decision(
            _fact(
                question="Q4",
                quotation=quote,
                location=location,
                scope=_scope(academic_year="2030/2031"),
            )
        ),
        [action],
    )
    assert proof[0]["scope"]["academic_year"] == "2030/2031"


@pytest.mark.parametrize("question", ["OTHER", "Q1"])
@pytest.mark.parametrize(
    "content_type", ["application/pdf", "text/plain", "application/xml", "text/html"]
)
@pytest.mark.parametrize(
    "dimension,quote,tail,incorrect,correct,message",
    [
        (
            "intake",
            "International bachelor applications for fall 2030 close on 1 February 2030.",
            " Applications for fall 2031 follow a different policy.",
            "fall 2031",
            "fall 2030",
            "intake scope",
        ),
        (
            "academic_year",
            "International bachelor tuition for 2030/2031 is EUR 1234 per year.",
            " Fees for 2031/2032 follow a different policy.",
            "2031/2032",
            "2030/2031",
            "academic_year",
        ),
    ],
)
def test_mixed_context_cannot_mask_the_original_quotes_declared_intake_or_year(
    tmp_path: Path,
    question: str,
    content_type: str,
    dimension: str,
    quote: str,
    tail: str,
    incorrect: str,
    correct: str,
    message: str,
) -> None:
    context = quote + tail
    location: dict[str, Any] = _fact()["location"]
    if content_type == "application/pdf":
        body = _pdf(context)
        location = {"kind": "pdf", "block_id": None, "section_path": [], "page": 1}
    elif content_type == "text/html":
        body = f"<p>{context}</p>".encode()
        location = {"kind": "document_ir", "block_id": "b0", "section_path": [], "page": None}
    else:
        body = context.encode()
    action, _record = _source(tmp_path, body=body, content_type=content_type)
    with pytest.raises(ValueError, match=message):
        _validate(
            tmp_path,
            _decision(
                _fact(
                    question=question,
                    quotation=quote,
                    location=location,
                    scope=_scope(**{dimension: incorrect}),
                )
            ),
            [action],
        )
    proof = _validate(
        tmp_path,
        _decision(
            _fact(
                question=question,
                quotation=quote,
                location=location,
                scope=_scope(**{dimension: correct}),
            )
        ),
        [action],
    )
    assert proof[0]["scope"][dimension] == correct


@pytest.mark.parametrize("tampering", ["outer_hash", "payload_hash", "log_case"])
def test_independent_raw_hash_payload_hash_and_case_identity_are_required(
    tmp_path: Path, tampering: str
) -> None:
    action, record = _source(tmp_path)
    if tampering == "outer_hash":
        with (tmp_path / action["raw_log_path"]).open("ab") as output:
            output.write(b" ")
        message = "raw log hash"
    else:
        if tampering == "payload_hash":
            record["response"]["content_sha256"] = "0" * 64
            message = "payload hash"
        else:
            record["case_id"] = "another-case"
            message = "another case"
        _save(tmp_path, action, record)
    with pytest.raises(ValueError, match=message):
        _validate(tmp_path, _decision(), [action])


@pytest.mark.parametrize(
    "final_url", ["https://example.edu.attacker.invalid/fact", "https://foreign.invalid/fact"]
)
def test_matching_declared_final_url_cannot_approve_a_foreign_source(
    tmp_path: Path, final_url: str
) -> None:
    action, _record = _source(tmp_path, final_url=final_url)
    with pytest.raises(ValueError, match="exact official page"):
        _validate(tmp_path, _decision(), [action])


def test_explicitly_approved_official_redirect_uses_actual_final_url(tmp_path: Path) -> None:
    final_url = "https://catalogue.secondary.edu/policy"
    action, _record = _source(tmp_path, final_url=final_url)
    proof = _validate(tmp_path, _decision(), [action], _packet(official_domains=["secondary.edu"]))
    assert proof[0]["source_url"] == final_url


def test_repository_hosts_cannot_become_citable_through_a_packet_alias(tmp_path: Path) -> None:
    action, _record = _source(tmp_path, final_url="https://github.com/synthetic/source")
    with pytest.raises(ValueError, match="exact official page"):
        _validate(tmp_path, _decision(), [action], _packet(official_domains=["github.com"]))


def test_a_first_citation_preserves_independent_preexisting_budget_floors(tmp_path: Path) -> None:
    action, record = _source(tmp_path)
    action["fetcher_calls_cumulative"] = record["fetcher_calls_cumulative"] = 5
    action["elapsed_ms_cumulative"] = record["elapsed_ms_cumulative"] = 520
    record["elapsed_ms_before"] = 500
    action["search_queries_cumulative"] = record["search_queries_cumulative"] = 2
    _save(tmp_path, action, record)
    assert _validate(tmp_path, _decision(), [action])[0]["source_step"] == 1


@pytest.mark.parametrize("declared_final", [None, "https://example.edu/another-page"])
def test_redirect_cannot_be_cited_as_a_different_requested_or_declared_page(
    tmp_path: Path, declared_final: str | None
) -> None:
    action, _record = _source(tmp_path, final_url="https://example.edu/actual-page")
    action["final_url"] = declared_final
    with pytest.raises(ValueError, match="final URL mismatch|exact official page"):
        _validate(tmp_path, _decision(), [action])


@pytest.mark.parametrize(
    "field,value",
    [("tool", "browser"), ("policy_mode", "outside_policy"), ("outcome_status", "failure")],
)
def test_facts_need_successful_controlled_fetcher_actions(
    tmp_path: Path, field: str, value: str
) -> None:
    action, _record = _source(tmp_path)
    action[field] = value
    with pytest.raises(ValueError, match="successful controlled"):
        _validate(tmp_path, _decision(), [action])


@pytest.mark.parametrize("tampering", ["request", "policy", "http", "executed", "raw_tool"])
def test_raw_controlled_source_must_agree_with_its_declared_successful_action(
    tmp_path: Path, tampering: str
) -> None:
    action, record = _source(tmp_path)
    record = deepcopy(record)
    if tampering == "request":
        record["request"]["url"] = "https://example.edu/different-request"
    elif tampering == "policy":
        record["policy_mode"] = "outside_policy"
    elif tampering == "http":
        record["response"]["status_code"] = 429
    elif tampering == "executed":
        record["executed"] = False
    else:
        record["request"]["tool"] = "browser"
    _save(tmp_path, action, record)
    with pytest.raises(ValueError, match="Controller|controller"):
        _validate(tmp_path, _decision(), [action])


@pytest.mark.parametrize("alias", ["file", "directory"])
def test_in_directory_symlink_aliases_are_rejected(tmp_path: Path, alias: str) -> None:
    action, _record = _source(tmp_path)
    if alias == "file":
        (tmp_path / "alias.json").symlink_to(tmp_path / action["raw_log_path"])
        action["raw_log_path"] = "alias.json"
    else:
        (tmp_path / "alias").symlink_to(tmp_path, target_is_directory=True)
        action["raw_log_path"] = "alias/" + action["raw_log_path"]
    with pytest.raises(ValueError, match="symlinks"):
        _validate(tmp_path, _decision(), [action])


@pytest.mark.parametrize("path", ["../outside.json", "/tmp/outside.json"])
def test_raw_log_path_cannot_escape_even_before_lookup(tmp_path: Path, path: str) -> None:
    action, _record = _source(tmp_path)
    action["raw_log_path"] = path
    with pytest.raises(ValueError, match="relative"):
        _validate(tmp_path, _decision(), [action])


@pytest.mark.parametrize(
    "invalid,message",
    [
        ("duplicate_step", "consecutive unique"),
        ("gap", "consecutive unique"),
        ("reversed_time", "chronological"),
        ("naive_time", "timezone"),
        ("case", "different case"),
        ("calls", "Fetcher calls"),
        ("time", "cumulative time"),
        ("queries", "search query counters"),
        ("shared_log", "own raw tool log"),
    ],
)
def test_entire_action_sequence_is_checked_before_fact_source_lookup(
    tmp_path: Path, invalid: str, message: str
) -> None:
    first, _record = _source(tmp_path)
    second, _record = _source(tmp_path, step=2)
    if invalid == "duplicate_step":
        second["step"] = 1
    elif invalid == "gap":
        second["step"] = 3
    elif invalid == "reversed_time":
        second["at"] = START.isoformat()
    elif invalid == "naive_time":
        second["at"] = START.replace(tzinfo=None).isoformat()
    elif invalid == "case":
        second["case_id"] = "another-case"
    elif invalid == "calls":
        second["fetcher_calls_cumulative"] = 0
    elif invalid == "time":
        second["elapsed_ms_cumulative"] = 20
    elif invalid == "queries":
        first["search_queries_cumulative"] = 1
    else:
        second["raw_log_path"] = "./" + first["raw_log_path"]
    (tmp_path / first["raw_log_path"]).unlink()
    with pytest.raises(ValueError, match=message):
        _validate(tmp_path, _decision(), [first, second])


def test_duplicate_fact_ids_and_json_fields_preserve_strict_compact_validation(
    tmp_path: Path,
) -> None:
    action, _record = _source(tmp_path)
    with pytest.raises(ValueError, match="fact IDs"):
        _validate(tmp_path, _decision(_fact(), _fact()), [action])
    decision = json.dumps(_decision()).replace(
        '"kind": "submit"', '"kind": "submit", "kind": "submit"'
    )
    with pytest.raises(ValueError, match="Duplicate JSON field"):
        _validate(tmp_path, decision, [action])


def test_ambiguous_multi_case_packet_is_rejected(tmp_path: Path) -> None:
    action, _record = _source(tmp_path)
    packet = _packet()
    packet["cases"].append({**packet["cases"][0], "case_id": "another-case"})
    with pytest.raises(ValueError, match="one current-case"):
        _validate(tmp_path, _decision(), [action], packet)


# Prospective year-provenance regressions; all source bytes below are synthetic.
def _ir_fact_for_html(html: str, quote: str, **changes: Any) -> dict[str, Any]:
    from app.adapters.document_ir import build_document_ir

    block = next(b for b in build_document_ir(html, URL).blocks if b.text == quote)
    return _fact(
        quotation=quote,
        location={
            "kind": "document_ir",
            "block_id": block.id,
            "section_path": list(block.section_path),
            "page": None,
        },
        **changes,
    )


def test_qualification_note_year_uses_only_its_explicit_adjacent_heading_label(
    tmp_path: Path,
) -> None:
    quote = "Foundation years are not considered."
    html = f"""<main><div><div><h1>International bachelor qualifications</h1>
    <div>Academic year 2030/2031</div></div><div><p>{quote}</p></div></div></main>"""
    action, _ = _source(tmp_path, body=html.encode())
    fact = _ir_fact_for_html(
        html,
        quote,
        question="Q2",
        id="foundation_note",
        claim_key="country_credential",
        value_json=json.dumps(quote),
        scope=_scope(academic_year="2030/2031"),
    )
    proof = _validate(tmp_path, _decision(fact), [action])
    assert proof[0]["quotation_sha256"] == hashlib.sha256(quote.encode()).hexdigest()
    assert proof[0]["scope"]["academic_year"] == "2030/2031"
    (support,) = proof[0]["academic_year_support"]
    assert support["kind"] == "section_label"
    assert support["text"] == "Academic year 2030/2031"
    assert support["heading_dom_path"].endswith("/h1[1]")
    assert support["dom_path"].endswith("/div[1]")


def test_fee_year_support_is_exact_same_table_row_with_source_coordinates(tmp_path: Path) -> None:
    html = """<h1>International bachelor tuition</h1><table>
    <tr><th>Applicant</th><th>Year</th><th>Fee</th></tr>
    <tr><td>International</td><td>2030/2031</td><td>EUR 19800</td></tr>
    <tr><td>International</td><td>2031/2032</td><td>EUR 19800</td></tr></table>"""
    action, _ = _source(tmp_path, body=html.encode())
    fact = _ir_fact_for_html(
        html,
        "EUR 19800",
        question="Q4",
        id="fee",
        claim_key="tuition",
        value_json='"EUR 19800"',
        scope=_scope(academic_year="2030/2031"),
    )
    proof = _validate(tmp_path, _decision(fact), [action])
    (support,) = proof[0]["academic_year_support"]
    assert (support["kind"], support["table_id"], support["row"], support["col"]) == (
        "table_cell",
        0,
        1,
        1,
    )
    assert support["text"] == "2030/2031"
    assert support["block_id"] == "b2"
    assert support["dom_path"] == "/html[1]/body[1]/table[1]/tr[2]/td[2]"
    fact["scope"]["academic_year"] = "2031/2032"
    with pytest.raises(ValueError, match="Q4 fact fee: academic_year"):
        _validate(tmp_path, _decision(fact), [action])


@pytest.mark.parametrize("row_year", ["", "unknown", "2031/2032"])
def test_page_label_cannot_fill_missing_or_wrong_year_in_the_selected_fee_row(
    tmp_path: Path, row_year: str
) -> None:
    html = f"""<h1>International bachelor tuition</h1>
    <div>Academic year 2030/2031</div><table>
    <tr><th>Applicant</th><th>Year</th><th>Fee</th></tr>
    <tr><td>International</td><td>{row_year}</td><td>EUR 19800</td></tr></table>"""
    action, _ = _source(tmp_path, body=html.encode())
    fact = _ir_fact_for_html(
        html, "EUR 19800", question="Q4", scope=_scope(academic_year="2030/2031")
    )
    with pytest.raises(ValueError, match="academic_year"):
        _validate(tmp_path, _decision(fact), [action])


@pytest.mark.parametrize("other_table", [False, True])
def test_matching_year_in_another_campus_row_or_table_cannot_rescue_fee(
    tmp_path: Path, other_table: bool
) -> None:
    boundary = (
        "</table><table><tr><th>Campus</th><th>Year</th><th>Fee</th></tr>" if other_table else ""
    )
    html = f"""<h1>International bachelor tuition</h1><table>
    <tr><th>Campus</th><th>Year</th><th>Fee</th></tr>
    <tr><td>Campus A</td><td>2031/2032</td><td>EUR 19800</td></tr>{boundary}
    <tr><td>Campus B</td><td>2030/2031</td><td>EUR 19800</td></tr></table>"""
    action, _ = _source(tmp_path, body=html.encode())
    fact = _ir_fact_for_html(
        html, "EUR 19800", question="Q4", scope=_scope(academic_year="2030/2031")
    )
    with pytest.raises(ValueError, match="academic_year"):
        _validate(tmp_path, _decision(fact), [action])


@pytest.mark.parametrize(
    "years",
    [
        "<th>Year</th><th>Year</th></tr><tr><td>2030/2031</td><td>2031/2032</td>",
        "<th>Year</th><th>Year</th></tr><tr><td>2030/2031</td><td>2030/2031</td>",
        '<th>Year</th></tr><tr><td colspan="2">2030/2031</td>',
        '<th>Year</th></tr><tr><td rowspan="2">2030/2031</td>',
    ],
)
def test_ambiguous_year_columns_and_merged_cells_fail_without_union(
    tmp_path: Path, years: str
) -> None:
    html = (
        f"<h1>International bachelor tuition</h1><table><tr>{years}<td>EUR 19800</td></tr></table>"
    )
    # Give the fee column its explicit header, including malformed/merged layout variants.
    html = html.replace("</tr><tr>", "<th>Fee</th></tr><tr>", 1)
    action, _ = _source(tmp_path, body=html.encode())
    fact = _ir_fact_for_html(
        html, "EUR 19800", question="Q4", scope=_scope(academic_year="2030/2031")
    )
    with pytest.raises(ValueError, match="academic_year"):
        _validate(tmp_path, _decision(fact), [action])


@pytest.mark.parametrize(
    "context,scope,message",
    [
        (
            "Domestic applicants in a bachelor programme tuition",
            _scope(academic_year="2030/2031"),
            "domestic",
        ),
        (
            "International applicants in a master programme tuition",
            _scope(academic_year="2030/2031"),
            "degree scope",
        ),
        (
            "International bachelor Fictional Studies tuition",
            _scope(programme="Different Studies", academic_year="2030/2031"),
            "exact programme",
        ),
        (
            "International bachelor tuition for fall 2030",
            _scope(intake="fall 2031", academic_year="2030/2031"),
            "intake scope",
        ),
    ],
)
def test_year_support_never_supplies_or_changes_other_declared_scope(
    tmp_path: Path, context: str, scope: dict[str, str | None], message: str
) -> None:
    html = f"<h1>{context}</h1><div>Academic year 2030/2031</div><p>EUR 19800</p>"
    action, _ = _source(tmp_path, body=html.encode())
    fact = _ir_fact_for_html(html, "EUR 19800", question="Q4", scope=scope)
    with pytest.raises(ValueError, match=message):
        _validate(tmp_path, _decision(fact), [action])


@pytest.mark.parametrize("question", ["Q2", "OTHER", "Q4"])
def test_year_error_names_original_question_fact_dimension_and_source(
    tmp_path: Path, question: str
) -> None:
    quote = "Foundation years are not considered."
    html = f"<h1>International bachelor qualifications</h1><p>{quote}</p>"
    action, _ = _source(tmp_path, body=html.encode())
    fact = _ir_fact_for_html(
        html,
        quote,
        id="qualification_note",
        question=question,
        scope=_scope(academic_year="2030/2031"),
    )
    with pytest.raises(ValueError) as caught:
        _validate(tmp_path, _decision(fact), [action])
    message = str(caught.value)
    assert f"{question} fact qualification_note: academic_year" in message
    assert "source_step=1" in message and "document_ir" in message
    assert "declared='2030/2031'" in message
    assert ("Q4" in message) is (question == "Q4")


def test_explicit_quotation_year_cannot_be_masked_by_matching_section_label(tmp_path: Path) -> None:
    quote = "International bachelor tuition for 2031/2032 is EUR 19800."
    html = (
        f"<h1>International bachelor tuition</h1><div>Academic year 2030/2031</div><p>{quote}</p>"
    )
    action, _ = _source(tmp_path, body=html.encode())
    fact = _ir_fact_for_html(html, quote, question="Q4", scope=_scope(academic_year="2030/2031"))
    with pytest.raises(ValueError, match="academic_year"):
        _validate(tmp_path, _decision(fact), [action])


def test_year_requirement_is_not_inferred_from_request_or_silently_filled(tmp_path: Path) -> None:
    quote = "Foundation years are not considered."
    html = f"<h1>International bachelor qualifications</h1><p>{quote}</p>"
    action, _ = _source(tmp_path, body=html.encode())
    fact = _ir_fact_for_html(html, quote, question="Q2", scope=_scope(academic_year=None))
    proof = _validate(tmp_path, _decision(fact), [action])
    assert proof[0]["scope"]["academic_year"] is None
    assert "academic_year_support" not in proof[0]
    fact["scope"]["academic_year"] = "2030/2031"
    with pytest.raises(ValueError, match="academic_year"):
        _validate(
            tmp_path, _decision(fact), [action], _packet(request={"academic_year": "2030/2031"})
        )


def test_table_caption_year_cannot_override_the_selected_rows_year(tmp_path: Path) -> None:
    html = """<h1>International bachelor tuition</h1><table><caption>Fees for 2030/2031</caption>
    <tr><th>Applicant</th><th>Year</th><th>Fee</th></tr>
    <tr><td>International</td><td>2031/2032</td><td>EUR 19800</td></tr></table>"""
    action, _ = _source(tmp_path, body=html.encode())
    fact = _ir_fact_for_html(
        html, "EUR 19800", question="Q4", scope=_scope(academic_year="2030/2031")
    )
    with pytest.raises(ValueError, match="academic_year"):
        _validate(tmp_path, _decision(fact), [action])


def test_multiple_adjacent_year_labels_do_not_allow_any_matching_year(tmp_path: Path) -> None:
    quote = "Foundation years are not considered."
    html = f"""<h1>International bachelor qualifications</h1>
    <div>Academic year 2030/2031</div><div>Academic year 2031/2032</div><p>{quote}</p>"""
    action, _ = _source(tmp_path, body=html.encode())
    fact = _ir_fact_for_html(html, quote, question="Q2", scope=_scope(academic_year="2030/2031"))
    with pytest.raises(ValueError, match="academic_year evidence ambiguous"):
        _validate(tmp_path, _decision(fact), [action])


def test_a_year_in_another_heading_scope_cannot_rescue_the_selected_note(tmp_path: Path) -> None:
    quote = "Foundation years are not considered."
    html = f"""<h1>International bachelor qualifications</h1><p>{quote}</p>
    <h1>Other campus</h1><div>Academic year 2030/2031</div><p>Unrelated policy.</p>"""
    action, _ = _source(tmp_path, body=html.encode())
    fact = _ir_fact_for_html(html, quote, question="Q2", scope=_scope(academic_year="2030/2031"))
    with pytest.raises(ValueError, match="academic_year"):
        _validate(tmp_path, _decision(fact), [action])


def test_valid_year_cannot_change_a_domestic_applicant_row_to_international(tmp_path: Path) -> None:
    html = """<h1>Bachelor tuition</h1><table><tr><th>Applicant</th><th>Year</th><th>Fee</th></tr>
    <tr><td>Domestic applicants</td><td>2030/2031</td><td>EUR 19800</td></tr>
    <tr><td>International applicants</td><td>2030/2031</td><td>EUR 19800</td></tr></table>"""
    action, _ = _source(tmp_path, body=html.encode())
    fact = _ir_fact_for_html(
        html, "EUR 19800", question="Q4", scope=_scope(academic_year="2030/2031")
    )
    with pytest.raises(ValueError, match="domestic"):
        _validate(tmp_path, _decision(fact), [action])


@pytest.mark.parametrize("container", ["main", "article", "section"])
def test_a_label_cannot_supply_year_after_exiting_its_semantic_container(
    tmp_path: Path, container: str
) -> None:
    quote = "Foundation years are not considered."
    html = f"""<{container}><h2>International bachelor qualifications</h2>
    <div>Academic year 2030/2031</div><p>First policy.</p></{container}>
    <{container}><p>{quote}</p></{container}>"""
    action, _ = _source(tmp_path, body=html.encode())
    fact = _ir_fact_for_html(html, quote, question="Q2", scope=_scope(academic_year="2030/2031"))
    with pytest.raises(ValueError, match="Q2 fact .*academic_year"):
        _validate(tmp_path, _decision(fact), [action])


@pytest.mark.parametrize(
    "label",
    [
        "<div><span hidden>Academic year 2030/2031</span></div>",
        '<div><span style="visibility: hidden">Academic year 2030/2031</span></div>',
        "<div><nav>Academic year 2030/2031</nav></div>",
        "<div><button>Academic year 2030/2031</button></div>",
    ],
)
def test_non_content_label_descendants_cannot_become_citable_year_support(
    tmp_path: Path, label: str
) -> None:
    quote = "Foundation years are not considered."
    html = f"<main><h1>International bachelor qualifications</h1>{label}<p>{quote}</p></main>"
    action, _ = _source(tmp_path, body=html.encode())
    fact = _ir_fact_for_html(html, quote, question="Q2", scope=_scope(academic_year="2030/2031"))
    with pytest.raises(ValueError, match="academic_year"):
        _validate(tmp_path, _decision(fact), [action])


@pytest.mark.parametrize(
    "year_cell,year_header",
    [
        ("<td hidden>2030/2031</td>", '<th id="y">Year</th>'),
        ("<td><nav>2030/2031</nav></td>", '<th id="y">Year</th>'),
        ("<td><form>2030/2031</form></td>", '<th id="y">Year</th>'),
        ("<td>2030/2031</td>", '<th id="y" hidden>Year</th>'),
        ('<td headers="y">2030/2031</td>', '<th id="y"><span hidden>Year</span></th>'),
        ("<td>2030/2031</td>", '<th id="y"><nav>Year</nav></th>'),
    ],
)
def test_hidden_year_value_or_header_cannot_be_rescued_by_a_matching_page_label(
    tmp_path: Path, year_cell: str, year_header: str
) -> None:
    html = f"""<h1>International bachelor tuition</h1><div>Academic year 2030/2031</div>
    <table><tr><th>Applicant</th>{year_header}<th>Fee</th></tr>
    <tr><td>International applicants</td>{year_cell}<td>EUR 19800</td></tr></table>"""
    action, _ = _source(tmp_path, body=html.encode())
    fact = _ir_fact_for_html(
        html, "EUR 19800", question="Q4", scope=_scope(academic_year="2030/2031")
    )
    with pytest.raises(ValueError, match="academic_year evidence ambiguous"):
        _validate(tmp_path, _decision(fact), [action])


@pytest.mark.parametrize(
    "headers,duplicate_id",
    [("a", False), ("missing", False), ("", False), ("y y", False), ("y", True)],
)
def test_authoritative_year_headers_reject_unknown_non_year_and_duplicate_references(
    tmp_path: Path, headers: str, duplicate_id: bool
) -> None:
    applicant_id = "y" if duplicate_id else "a"
    html = f"""<h1>International bachelor tuition</h1><div>Academic year 2030/2031</div><table>
    <tr><th id="{applicant_id}">Applicant</th><th id="y">Year</th><th>Fee</th></tr>
    <tr><td>International applicants</td><td headers="{headers}">2030/2031</td>
    <td>EUR 19800</td></tr></table>"""
    action, _ = _source(tmp_path, body=html.encode())
    fact = _ir_fact_for_html(
        html, "EUR 19800", question="Q4", scope=_scope(academic_year="2030/2031")
    )
    with pytest.raises(ValueError, match="academic_year evidence ambiguous"):
        _validate(tmp_path, _decision(fact), [action])


def test_exact_explicit_year_header_list_is_valid_and_conserves_header_coordinates(
    tmp_path: Path,
) -> None:
    html = """<h1>International bachelor tuition</h1><table>
    <tr><th>Applicant</th><th id="y">Year</th><th>Fee</th></tr>
    <tr><td>International applicants</td><td headers="y">2030/2031</td><td>EUR 19800</td></tr></table>"""
    action, _ = _source(tmp_path, body=html.encode())
    fact = _ir_fact_for_html(
        html, "EUR 19800", question="Q4", scope=_scope(academic_year="2030/2031")
    )
    (support,) = _validate(tmp_path, _decision(fact), [action])[0]["academic_year_support"]
    assert support["header_origin"] == "explicit"
    assert support["header_dom_paths"] == ("/html[1]/body[1]/table[1]/tr[1]/th[2]",)
    assert support["blocked_reason"] is None


@pytest.mark.parametrize("row_scope", ['scope="row"', ""])
def test_real_year_row_header_is_valid_without_nonexistent_value_block(
    tmp_path: Path, row_scope: str
) -> None:
    html = f"""<h1>International bachelor tuition</h1><table>
    <tr><th>Year</th><th>Fee</th></tr>
    <tr><th {row_scope}>2030/2031</th><td>EUR 19800</td></tr></table>"""
    action, _ = _source(tmp_path, body=html.encode())
    fact = _ir_fact_for_html(
        html, "EUR 19800", question="Q4", scope=_scope(academic_year="2030/2031")
    )
    (support,) = _validate(tmp_path, _decision(fact), [action])[0]["academic_year_support"]
    assert support["source_kind"] == "row_header" and support["source_tag"] == "th"
    assert support["block_id"] is None and support["dom_path"].endswith("/tr[2]/th[1]")
    assert support["header_dom_paths"] == ("/html[1]/body[1]/table[1]/tr[1]/th[1]",)
    fact["scope"]["academic_year"] = "2031/2032"
    with pytest.raises(ValueError, match="academic_year"):
        _validate(tmp_path, _decision(fact), [action])


def test_removing_a_control_keeps_original_year_header_unusable(tmp_path: Path) -> None:
    html = (
        "<h1>International bachelor tuition</h1><div>Academic year 2030/2031</div>"
        "<table><tr><th><form>Year</form></th><th>Fee</th></tr>"
        "<tr><td>2030/2031</td><td>EUR 19800</td></tr></table>"
    )
    action, _ = _source(tmp_path, body=html.encode())
    fact = _ir_fact_for_html(
        html, "EUR 19800", question="Q4", scope=_scope(academic_year="2030/2031")
    )
    with pytest.raises(ValueError, match="academic_year evidence ambiguous"):
        _validate(tmp_path, _decision(fact), [action])
