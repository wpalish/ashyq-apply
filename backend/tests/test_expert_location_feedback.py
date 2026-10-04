"""Same-source diagnostics retain literal values and never accept a repaired delta."""

from __future__ import annotations

import base64
import hashlib
import json
from collections.abc import Iterator, Mapping
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from evaluation.research.expert.compact import SCOPE_DIMENSIONS, parse_compact_decision
from evaluation.research.expert.controller import expert_view
from evaluation.research.expert.journal import AcceptedJournal, parse_journal_decision
from evaluation.research.expert.location_feedback import (
    MAX_BLOCKS,
    MAX_CANDIDATES,
    MAX_CONTEXT_CHARS,
    MAX_FACTS,
    MAX_FEEDBACK_BYTES,
    MAX_SCANNED_CHARS,
    MAX_TEXT_WINDOW_CHARS,
    MAX_VIEWS,
    location_feedback,
)

QUOTE = "The published minimum is 6.5."


def fact(**changes: Any) -> dict[str, Any]:
    return {
        "id": "synthetic_fact",
        "question": "OTHER",
        "claim_key": "unmapped.synthetic",
        "value_json": '{"preserved": [false, null, "literal"]}',
        "source_step": 1,
        "quotation": QUOTE,
        "location": {"kind": "text", "block_id": None, "section_path": [], "page": None},
        "scope": {**dict.fromkeys(SCOPE_DIMENSIONS), "university": "Example University"},
        **changes,
    }


def decision(*facts: dict[str, Any], compact: bool = False) -> Any:
    raw = {
        "kind": "submit",
        "observation": "Synthetic completed decision.",
        "action": None,
        "facts": list(facts) or [fact()],
        "question_findings": [],
    }
    if compact:
        return parse_compact_decision(raw)
    return parse_journal_decision({**raw, "journal_sha256": AcceptedJournal.initial().sha256})


def block(block_id: str, text: str = QUOTE, **changes: Any) -> dict[str, Any]:
    return {
        "id": block_id,
        "kind": "paragraph",
        "text": text,
        "section_path": ["Published requirements"],
        "row_headers": [],
        "column_headers": [],
        "label": "",
        "caption": "",
        "table_id": None,
        "row": None,
        "col": None,
        **changes,
    }


def view(*blocks: dict[str, Any], step: int = 1, **changes: Any) -> dict[str, Any]:
    return {
        "step": step,
        "view": {
            "request": {"tool": "fetcher", "url": "https://example.invalid/source"},
            "policy_mode": "same_policy",
            "outcome_status": "success",
            "content_type": "text/html",
            "sections": list(blocks),
            "sections_total": len(blocks),
            "sections_offset": 0,
            "sections_next_offset": None,
            **changes,
        },
    }


def diagnostic(result: dict[str, Any]) -> dict[str, Any]:
    assert result["offending_fact_ids"] == ["synthetic_fact"]
    return result["diagnostics"][0]


def html_view(html: str) -> dict[str, Any]:
    content = html.encode()
    raw = {
        "request": {"tool": "fetcher", "url": "https://example.invalid/source"},
        "policy_mode": "same_policy",
        "outcome_status": "success",
        "response": {
            "content_type": "text/html",
            "final_url": "https://example.invalid/source",
            "content_b64": base64.b64encode(content).decode(),
            "content_sha256": hashlib.sha256(content).hexdigest(),
        },
    }
    return {"step": 1, "view": expert_view(raw)}


@pytest.mark.parametrize("compact", [False, True])
def test_actual_controller_view_exposes_ambiguous_text_coordinates_without_acceptance(
    compact: bool,
) -> None:
    saved = html_view(f"<h1>Published requirements</h1><p>{QUOTE}</p><p>{QUOTE}</p>")
    chosen = decision(fact(), compact=compact)
    before = chosen.model_dump(mode="json")
    result = location_feedback(chosen, [saved])
    item = diagnostic(result)
    assert item["reasons"] == ["ambiguous_text_quote"]
    assert item["source_step"] == 1
    assert len(item["candidates"]) == 2
    for candidate in item["candidates"]:
        coordinate = candidate["location"]
        recorded = next(b for b in saved["view"]["sections"] if b["id"] == coordinate["block_id"])
        assert coordinate == {
            "kind": "document_ir",
            "block_id": recorded["id"],
            "section_path": list(recorded["section_path"]),
            "page": None,
        }
        assert candidate["quotation_in_block_text"] is True
        assert candidate["text_window"] == QUOTE
    assert chosen.model_dump(mode="json") == before
    assert AcceptedJournal.initial().facts == ()


def test_explicit_exact_coordinate_is_not_reported_as_ambiguous() -> None:
    chosen = decision(
        fact(
            location={
                "kind": "document_ir",
                "block_id": "p2",
                "section_path": ["Published requirements"],
                "page": None,
            }
        )
    )
    result = location_feedback(chosen, [view(block("p1"), block("p2"))])
    assert result["diagnostics"] == []


@pytest.mark.parametrize(
    "location",
    [
        {
            "kind": "document_ir",
            "block_id": "missing",
            "section_path": ["Published requirements"],
            "page": None,
        },
        {
            "kind": "document_ir",
            "block_id": "p1",
            "section_path": ["Wrong literal section"],
            "page": None,
        },
        {"kind": "pdf", "block_id": None, "section_path": [], "page": 1},
    ],
)
def test_wrong_asserted_coordinate_keeps_original_fact_and_returns_saved_coordinate(
    location: dict[str, Any],
) -> None:
    chosen = decision(fact(location=location))
    before = chosen.model_dump(mode="json")
    item = diagnostic(location_feedback(chosen, [view(block("p1"))]))
    assert item["candidates"][0]["location"]["block_id"] == "p1"
    assert chosen.model_dump(mode="json") == before


def test_structural_context_only_match_does_not_become_a_citable_quote() -> None:
    saved = view(
        block(
            "cell",
            "6.5",
            kind="table_cell",
            row_headers=[QUOTE],
            column_headers=["International applicants", "Bachelor applicants"],
            table_id=0,
            row=2,
            col=1,
        )
    )
    item = diagnostic(location_feedback(decision(fact()), [saved]))
    assert item["reasons"] == [
        "no_exact_quote_in_supplied_blocks",
        "quote_only_in_structural_context",
    ]
    candidate = item["candidates"][0]
    assert candidate["match_kind"] == "context_only"
    assert candidate["quotation_in_block_text"] is False
    assert candidate["text_window"] == "6.5"
    assert candidate["layout"]["row_headers"] == [QUOTE]
    assert candidate["layout"]["row"] == 2
    assert candidate["observed_local_scope"]["population"] == "international"
    assert candidate["observed_local_scope"]["degree"] == "bachelor"


def test_local_and_section_scope_are_observed_separately_without_request_fill() -> None:
    saved = view(
        block(
            "p1",
            section_path=["Bachelor programme: fall 2031 intake"],
            row_headers=["International applicants"],
            column_headers=["Academic year 2031/2032"],
        )
    )
    chosen = decision(
        fact(
            location={"kind": "document_ir", "block_id": "wrong", "section_path": [], "page": None}
        )
    )
    candidate = diagnostic(location_feedback(chosen, [saved]))["candidates"][0]
    assert candidate["observed_local_scope"]["degree"] is None
    assert candidate["observed_section_scope"]["degree"] == "bachelor"
    assert candidate["observed_section_scope"]["intake"] == "Fall 2031"
    assert candidate["observed_section_scope"]["academic_year"] == "2031/32"
    assert candidate["observed_local_scope"]["qualification"] is None
    assert chosen.facts[0].scope.degree is None
    assert chosen.facts[0].scope.intake is None


@pytest.mark.parametrize(
    "programme", ["Invented programme", "literal programme", " Literal Programme "]
)
def test_missing_exact_programme_label_is_reported_without_new_scope(programme: str) -> None:
    item = fact()
    item["scope"]["programme"] = programme
    result = diagnostic(
        location_feedback(
            decision(item),
            [view(block("p1", section_path=["Literal Programme", "Bachelor programme"]))],
        )
    )
    assert result["reasons"] == ["asserted_programme_text_not_visible"]
    assert result["candidates"][0]["asserted_programme_text_visible"] is False
    assert "programme" not in result["candidates"][0]["observed_section_scope"]


def test_programme_is_checked_in_selected_block_context_not_unrelated_page_text() -> None:
    item = fact(
        location={
            "kind": "document_ir",
            "block_id": "p1",
            "section_path": ["Published requirements"],
            "page": None,
        }
    )
    item["scope"]["programme"] = "Literal Programme"
    saved = view(
        block("p1"), block("unrelated", "Literal Programme"), text=f"Literal Programme {QUOTE}"
    )
    assert diagnostic(location_feedback(decision(item), [saved]))["reasons"] == [
        "asserted_programme_text_not_visible"
    ]


def test_exact_programme_in_selected_structural_context_is_not_filled_or_rewritten() -> None:
    item = fact()
    item["scope"]["programme"] = "Literal Programme"
    chosen = decision(item)
    assert (
        location_feedback(chosen, [view(block("p1", section_path=["Literal Programme"]))])[
            "diagnostics"
        ]
        == []
    )
    assert chosen.facts[0].scope.programme == "Literal Programme"


@pytest.mark.parametrize(
    "quotation",
    [
        QUOTE.lower(),
        QUOTE.replace("minimum is", "minimum  is"),
        "The published minimum is 6.0.",
        QUOTE.replace(".", "!"),
    ],
)
def test_quote_matching_is_literal_without_case_whitespace_number_or_punctuation_repair(
    quotation: str,
) -> None:
    item = diagnostic(location_feedback(decision(fact(quotation=quotation)), [view(block("p1"))]))
    assert "no_exact_quote_in_supplied_blocks" in item["reasons"]
    assert item["candidates"] == []


def test_exact_matches_precede_context_only_candidates() -> None:
    saved = view(block("context", "different", label=QUOTE), block("exact1"), block("exact2"))
    candidates = diagnostic(location_feedback(decision(fact()), [saved]))["candidates"]
    assert [candidate["location"]["block_id"] for candidate in candidates] == [
        "exact1",
        "exact2",
        "context",
    ]


@pytest.mark.parametrize(
    "format_name",
    [
        "nested_sections",
        "nested_blocks",
        "flat_sections",
        "flat_blocks",
        "tuple_sections",
        "source_step",
    ],
)
def test_current_and_compatible_saved_block_formats(format_name: str) -> None:
    saved = view(block("p1"), block("p2"))
    if "blocks" in format_name:
        saved["view"]["blocks"] = saved["view"].pop("sections")
    if format_name.startswith("flat"):
        saved = {"step": 1, **saved["view"]}
    if format_name == "tuple_sections":
        saved["view"]["sections"] = tuple(saved["view"]["sections"])
        for entry in saved["view"]["sections"]:
            entry["section_path"] = tuple(entry["section_path"])
    if format_name == "source_step":
        saved["source_step"] = saved.pop("step")
    assert diagnostic(location_feedback(decision(fact()), [saved]))["reasons"] == [
        "ambiguous_text_quote"
    ]


@pytest.mark.parametrize(
    "changes",
    [
        {"id": None},
        {"id": []},
        {"id": " "},
        {"id": "x" * 201},
        {"text": None},
        {"text": []},
        {"text": "x" * (MAX_CONTEXT_CHARS + 1)},
        {"kind": {}},
        {"kind": "unknown"},
        {"section_path": None},
        {"section_path": [None]},
        {"section_path": ["x"] * 17},
        {"section_path": ["x" * 601]},
        {"row_headers": "not a sequence"},
        {"column_headers": [True]},
        {"caption": None},
        {"label": []},
        {"row": True},
        {"row": -1},
        {"col": "1"},
    ],
)
def test_malformed_or_oversized_blocks_are_defensively_skipped(changes: dict[str, Any]) -> None:
    item = diagnostic(location_feedback(decision(fact()), [view(block("p1", **changes))]))
    assert item["candidates"] == []
    assert item["scan_complete"] is False
    assert "supplied_view_scan_incomplete" in item["reasons"]


@pytest.mark.parametrize("raw", [None, 1, "not a block", [], {}])
def test_malformed_block_entries_do_not_crash(raw: Any) -> None:
    saved = view(sections=[raw])
    assert diagnostic(location_feedback(decision(fact()), [saved]))["candidates"] == []


@pytest.mark.parametrize("step", [None, 0, -1, True, "1", 2])
def test_only_exact_integer_matching_source_step_is_inspected(step: Any) -> None:
    saved = view(block("foreign1"), block("foreign2"))
    saved["step"] = step
    item = diagnostic(location_feedback(decision(fact()), [saved]))
    assert item["reasons"] == ["source_view_not_supplied"]
    assert item["candidates"] == []


class ForeignView(Mapping[str, Any]):
    def __getitem__(self, key: str) -> Any:
        if key == "step":
            return 999
        raise AssertionError("Foreign source contents must not be inspected")

    def __iter__(self) -> Iterator[str]:
        return iter(["step", "view"])

    def __len__(self) -> int:
        return 2


def test_unrelated_source_contents_are_not_read() -> None:
    assert diagnostic(location_feedback(decision(fact()), [ForeignView()]))["candidates"] == []


def test_conflicting_step_aliases_are_not_used_as_a_source() -> None:
    saved = {**view(block("p1")), "source_step": 2}
    item = diagnostic(location_feedback(decision(fact()), [saved]))
    assert item["candidates"] == []
    assert item["scan_complete"] is False


@pytest.mark.parametrize(
    "changes,reason",
    [
        ({"results": [{"text": QUOTE}]}, "discovery_view_is_not_source_evidence"),
        ({"request": {"tool": "search_provider"}}, "discovery_view_is_not_source_evidence"),
        ({"outcome_status": "error"}, "saved_source_view_not_successful"),
        ({"policy_mode": "outside_policy"}, "saved_source_view_not_successful"),
        ({"content_type": "application/octet-stream"}, "unsupported_source_view"),
        ({"content_type": None}, "unsupported_source_view"),
    ],
)
def test_discovery_failed_policy_and_unsupported_views_cannot_supply_coordinates(
    changes: dict[str, Any], reason: str
) -> None:
    item = diagnostic(
        location_feedback(decision(fact()), [view(block("p1"), block("p2"), **changes)])
    )
    assert item["reasons"] == [reason]
    assert item["candidates"] == []


def test_duplicate_identical_saved_blocks_are_not_fabricated_ambiguity() -> None:
    saved = view(block("p1"))
    assert location_feedback(decision(fact()), [saved, deepcopy(saved)])["diagnostics"] == []


@pytest.mark.parametrize(
    "change",
    [{"text": "different"}, {"section_path": ["Different"]}, {"row_headers": ["Different"]}],
)
def test_conflicting_saved_versions_are_excluded_instead_of_choosing_one(
    change: dict[str, Any],
) -> None:
    item = diagnostic(
        location_feedback(decision(fact()), [view(block("p1")), view(block("p1", **change))])
    )
    assert "conflicting_saved_block_views" in item["reasons"]
    assert item["candidates"] == []


@pytest.mark.parametrize("page", [None, True, 0, 41, "2"])
def test_pdf_aggregate_or_metadata_without_exact_selected_page_cannot_invent_coordinates(
    page: Any,
) -> None:
    saved = view(
        content_type="application/pdf",
        pdf_page=page,
        pdf_pages=[{"page": 2, "has_text": True}],
        text=QUOTE,
    )
    chosen = decision(
        fact(location={"kind": "pdf", "block_id": None, "section_path": [], "page": 2})
    )
    item = diagnostic(location_feedback(chosen, [saved]))
    assert "exact_pdf_page_not_visible" in item["reasons"]
    assert item["candidates"] == []


def test_correct_selected_pdf_quote_has_no_ir_rejection() -> None:
    saved = view(content_type="application/pdf", pdf_page=2, text=QUOTE)
    chosen = decision(
        fact(location={"kind": "pdf", "block_id": None, "section_path": [], "page": 2})
    )
    assert location_feedback(chosen, [saved])["diagnostics"] == []


@pytest.mark.parametrize("content_type", ["text/plain", "application/xml", "text/xml"])
def test_saved_plain_source_is_supported_without_made_up_blocks(content_type: str) -> None:
    saved = view(content_type=content_type, text=QUOTE)
    assert location_feedback(decision(fact()), [saved])["diagnostics"] == []
    item = diagnostic(
        location_feedback(decision(fact(quotation="Absent literal quotation.")), [saved])
    )
    assert item["reasons"] == ["no_exact_quote_in_supplied_text"]
    assert item["candidates"] == []


@pytest.mark.parametrize(
    "pagination", [{"sections_next_offset": 2}, {"sections_offset": 2}, {"sections_total": 10}]
)
def test_partial_ir_views_qualify_negative_diagnostics(pagination: dict[str, Any]) -> None:
    item = diagnostic(
        location_feedback(
            decision(fact(quotation="Not visible.")), [view(block("p1"), **pagination)]
        )
    )
    assert item["scan_complete"] is False
    assert "supplied_view_scan_incomplete" in item["reasons"]


def test_partial_view_alone_does_not_call_a_correct_coordinate_offending() -> None:
    chosen = decision(
        fact(
            location={
                "kind": "document_ir",
                "block_id": "p1",
                "section_path": ["Published requirements"],
                "page": None,
            }
        )
    )
    assert (
        location_feedback(chosen, [view(block("p1"), sections_next_offset=1)])["diagnostics"] == []
    )


@pytest.mark.parametrize(
    "pagination", [{"text_next_offset": 100}, {"text_offset": 100}, {"text_total_chars": 1000}]
)
def test_partial_plain_view_qualifies_missing_text(pagination: dict[str, Any]) -> None:
    item = diagnostic(
        location_feedback(
            decision(fact()), [view(content_type="text/plain", text="different", **pagination)]
        )
    )
    assert item["scan_complete"] is False


def test_candidate_count_and_exact_text_window_are_bounded() -> None:
    text = "x" * 2000 + QUOTE + "y" * 2000
    saved = view(*(block(f"p{number}", text) for number in range(MAX_CANDIDATES + 2)))
    item = diagnostic(location_feedback(decision(fact()), [saved]))
    assert item["matching_blocks_visible"] == MAX_CANDIDATES + 2
    assert len(item["candidates"]) == MAX_CANDIDATES
    assert item["candidates_truncated"] is True
    window = item["candidates"][0]
    assert len(window["text_window"]) <= MAX_TEXT_WINDOW_CHARS
    assert QUOTE in window["text_window"]
    assert (
        text[
            window["text_window_offset"] : window["text_window_offset"] + len(window["text_window"])
        ]
        == window["text_window"]
    )


def test_total_block_scan_is_bounded_and_truncation_explicit() -> None:
    result = location_feedback(
        decision(fact()), [view(*(block(f"p{number}") for number in range(MAX_BLOCKS + 50)))]
    )
    assert result["scanned_blocks"] == MAX_BLOCKS
    assert result["truncated"] is True
    assert diagnostic(result)["scan_complete"] is False


def test_total_inspected_context_characters_are_bounded() -> None:
    result = location_feedback(
        decision(fact()),
        [view(*(block(f"p{number}", QUOTE + "x" * 11000) for number in range(25)))],
    )
    assert result["scanned_context_chars"] <= MAX_SCANNED_CHARS
    assert result["truncated"] is True


def test_latest_view_cap_preserves_original_view_indices() -> None:
    saved = [view(step=100 + index) for index in range(MAX_VIEWS)]
    saved.append(view(block("p1"), block("p2")))
    result = location_feedback(decision(fact()), saved)
    assert result["scanned_views"] == MAX_VIEWS
    assert result["truncated"] is True
    assert diagnostic(result)["candidates"][0]["source_view_index"] == MAX_VIEWS


def test_fact_cap_is_explicit_for_full_compact_submission() -> None:
    chosen = decision(*(fact(id=f"fact_{index}") for index in range(MAX_FACTS + 2)), compact=True)
    result = location_feedback(chosen, [])
    assert result["offending_fact_ids"] == [f"fact_{index}" for index in range(MAX_FACTS)]
    assert result["truncated"] is True


def test_utf8_serialized_feedback_size_is_bounded_even_for_many_large_layouts() -> None:
    saved = view(
        *(
            block(f"p{index}", section_path=["中" * 500], row_headers=["界" * 500])
            for index in range(4)
        )
    )
    chosen = decision(*(fact(id=f"fact_{index}") for index in range(MAX_FACTS)))
    result = location_feedback(chosen, [saved])
    assert len(json.dumps(result, ensure_ascii=False).encode("utf-8")) <= MAX_FEEDBACK_BYTES
    assert result["truncated"] is True
    assert all(entry["source_step"] == 1 for entry in result["diagnostics"])


def test_fact_filter_checks_only_selected_submitted_ids_and_preserves_fact_order() -> None:
    chosen = decision(fact(id="first"), fact(id="second"), fact(id="third"))
    result = location_feedback(chosen, [], fact_ids=["third", "first"])
    assert result["offending_fact_ids"] == ["first", "third"]
    assert location_feedback(chosen, [], fact_ids=[])["diagnostics"] == []


@pytest.mark.parametrize(
    "ids",
    [
        ["unknown"],
        ["synthetic_fact", "synthetic_fact"],
        [True],
        "synthetic_fact",
        ["synthetic_fact"] * 129,
    ],
)
def test_invalid_fact_filter_is_rejected(ids: Any) -> None:
    with pytest.raises(ValueError):
        location_feedback(decision(fact()), [], fact_ids=ids)


@pytest.mark.parametrize("source_views", [None, {}, "a string", b"bytes"])
def test_invalid_source_view_container_is_rejected(source_views: Any) -> None:
    with pytest.raises(ValueError):
        location_feedback(decision(fact()), source_views)


@pytest.mark.parametrize("raw", [None, {}, "{}"])
def test_unparsed_or_partial_decision_is_not_treated_as_completed(raw: Any) -> None:
    with pytest.raises(ValueError):
        location_feedback(raw, [])


def test_mutated_model_is_revalidated_before_source_inspection() -> None:
    chosen = decision(fact())
    chosen.facts[0].source_step = True
    with pytest.raises(ValueError):
        location_feedback(chosen, [])


def test_inputs_and_rejected_delta_are_unchanged_and_diagnostics_deterministic() -> None:
    chosen = decision(fact())
    saved = [view(block("p1"), block("p2"))]
    before_decision, before_views = chosen.model_dump(mode="json"), deepcopy(saved)
    result = location_feedback(chosen, saved)
    assert result == location_feedback(chosen, saved)
    assert chosen.model_dump(mode="json") == before_decision
    assert saved == before_views
    keys: set[str] = set()

    def collect(value: Any) -> None:
        if isinstance(value, dict):
            keys.update(value)
            for nested in value.values():
                collect(nested)
        elif isinstance(value, list):
            for nested in value:
                collect(nested)

    collect(result)
    assert not keys & {
        "facts",
        "value",
        "value_json",
        "claim_key",
        "quotation",
        "proposed_scope",
        "accepted",
        "answer",
        "journal_sha256",
        "university",
    }


def test_diagnostics_do_not_read_files_or_invoke_sources(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("Same-source feedback must perform no I/O")

    chosen = decision(fact())
    monkeypatch.setattr(Path, "read_text", forbidden)
    monkeypatch.setattr(Path, "read_bytes", forbidden)
    monkeypatch.setattr("builtins.open", forbidden)
    assert diagnostic(location_feedback(chosen, [view(block("p1"), block("p2"))]))["reasons"] == [
        "ambiguous_text_quote"
    ]
