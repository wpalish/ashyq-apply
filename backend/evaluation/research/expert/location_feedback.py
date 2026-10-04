"""Bounded diagnostics from already supplied source views, never repaired facts.

The caller supplies only the current case's recorded ``expert_view`` objects.
This helper does no I/O and establishes neither source provenance nor semantic
support. It must run after a completed selector object has been rejected, within
the caller's metered budget. Every subsequent delta still needs the unchanged
journal, raw-log and citation gates. Missing text here means missing from the
bounded supplied views, not missing from the source or unpublished.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from app.adapters.scope_reader import read_scope

from .compact import CompactDecision, CompactFact, parse_compact_decision
from .journal import JournalDecision, parse_journal_decision

MAX_FACTS = 16
MAX_VIEWS = 8
MAX_BLOCKS = 256
MAX_CONTEXT_CHARS = 12000
MAX_SCANNED_CHARS = 128000
MAX_CANDIDATES = 3
MAX_FEEDBACK_BYTES = 20000
MAX_TEXT_WINDOW_CHARS = 800
_SCOPE_FIELDS = ("degree", "intake", "academic_year", "population", "qualification", "residency")


@dataclass(frozen=True)
class _Block:
    step: int
    view_index: int
    block_id: str
    section_path: tuple[str, ...]
    text: str
    local: str
    context: str
    layout: dict[str, Any]


def _strings(value: Any, limit: int = 16) -> tuple[str, ...] | None:
    if not isinstance(value, list | tuple) or len(value) > limit:
        return None
    if any(not isinstance(item, str) or not item or len(item) > 600 for item in value):
        return None
    return tuple(value)


def _block(raw: Any, step: int, view_index: int) -> _Block | None:
    if not isinstance(raw, Mapping):
        return None
    block_id, text, kind = raw.get("id"), raw.get("text"), raw.get("kind")
    if (
        not isinstance(block_id, str)
        or not block_id.strip()
        or len(block_id) > 200
        or not isinstance(text, str)
        or len(text) > MAX_CONTEXT_CHARS
        or not isinstance(kind, str)
        or kind not in {"heading", "paragraph", "list_item", "key_value", "table_cell"}
    ):
        return None
    path = _strings(raw.get("section_path", []))
    rows = _strings(raw.get("row_headers", []))
    columns = _strings(raw.get("column_headers", []))
    label, caption = raw.get("label", ""), raw.get("caption", "")
    if (
        path is None
        or rows is None
        or columns is None
        or not isinstance(label, str)
        or not isinstance(caption, str)
        or len(label) > 600
        or len(caption) > 600
    ):
        return None
    coordinates = {name: raw.get(name) for name in ("table_id", "row", "col")}
    if any(
        value is not None and (type(value) is not int or value < 0)
        for value in coordinates.values()
    ):
        return None
    local = " ".join([*rows, *columns, label, caption, text])
    context = " ".join([*path, local])
    if len(context) > MAX_CONTEXT_CHARS:
        return None
    return _Block(
        step,
        view_index,
        block_id,
        path,
        text,
        local,
        context,
        {
            "kind": kind,
            **coordinates,
            "row_headers": list(rows),
            "column_headers": list(columns),
            "label": label,
            "caption": caption,
        },
    )


def _scope(text: str) -> dict[str, str | None]:
    observed = read_scope(text)
    return {name: getattr(observed, name) for name in _SCOPE_FIELDS}


def _candidate(block: _Block, fact: CompactFact) -> dict[str, Any]:
    position = block.text.find(fact.quotation)
    offset = max(0, position - 100)
    return {
        "location": {
            "kind": "document_ir",
            "block_id": block.block_id,
            "section_path": list(block.section_path),
            "page": None,
        },
        "source_view_index": block.view_index,
        "match_kind": "exact_block_text" if position >= 0 else "context_only",
        "quotation_in_block_text": position >= 0,
        "layout": block.layout.copy(),
        "text_window": block.text[offset : offset + MAX_TEXT_WINDOW_CHARS],
        "text_window_offset": offset,
        "text_total_chars": len(block.text),
        "observed_local_scope": _scope(block.local),
        "observed_section_scope": _scope(block.context),
        "asserted_programme_text_visible": None
        if fact.scope.programme is None
        else fact.scope.programme in block.context,
    }


def _view_kind(view: Mapping[str, Any]) -> str:
    request = view.get("request")
    if "results" in view or (
        isinstance(request, Mapping) and request.get("tool") == "search_provider"
    ):
        return "discovery"
    if view.get("outcome_status") != "success" or view.get("policy_mode") != "same_policy":
        return "unavailable"
    content_type = view.get("content_type", "")
    if not isinstance(content_type, str):
        return "unsupported"
    if "pdf" in content_type.lower():
        return "pdf"
    if "html" in content_type.lower() or (
        not content_type and ("sections" in view or "blocks" in view)
    ):
        return "document_ir"
    if "text/plain" in content_type.lower() or "xml" in content_type.lower():
        return "text"
    return "unsupported"


def _diagnostic(
    fact: CompactFact,
    blocks: list[_Block],
    views: list[tuple[int, Mapping[str, Any], str]],
    *,
    scan_complete: bool,
    conflicting: bool,
) -> dict[str, Any] | None:
    reasons: list[str] = []
    exact = [block for block in blocks if fact.quotation in block.text]
    context_only = [
        block
        for block in blocks
        if fact.quotation not in block.text and fact.quotation in block.context
    ]
    selected = [
        block
        for block in blocks
        if block.block_id == fact.location.block_id
        and list(block.section_path) == fact.location.section_path
    ]
    kind = "document_ir" if blocks else views[0][2] if views else "unavailable"
    if not views:
        reasons.append("source_view_not_supplied")
    elif kind == "document_ir":
        if not exact:
            reasons.append("no_exact_quote_in_supplied_blocks")
        if context_only and not exact:
            reasons.append("quote_only_in_structural_context")
        if fact.location.kind == "text" and len(exact) > 1:
            reasons.append("ambiguous_text_quote")
        if fact.location.kind == "document_ir" and not any(block in exact for block in selected):
            reasons.append("asserted_location_not_in_exact_matches")
        if fact.location.kind == "pdf":
            reasons.append("source_view_kind_differs_from_asserted_location")
        programme_contexts = selected if fact.location.kind == "document_ir" else exact
        if fact.scope.programme is not None and not any(
            fact.scope.programme in block.context for block in programme_contexts
        ):
            reasons.append("asserted_programme_text_not_visible")
    elif kind in {"text", "pdf"}:
        text_views = []
        for _, view, source_kind in views:
            if source_kind != kind:
                continue
            page = view.get("pdf_page")
            if kind == "pdf" and (type(page) is not int or not 1 <= page <= 40):
                continue
            if kind == "pdf" and (fact.location.kind != "pdf" or page != fact.location.page):
                continue
            text = view.get("text")
            if isinstance(text, str) and len(text) <= MAX_CONTEXT_CHARS:
                text_views.append(text)
        if kind == "pdf" and not text_views:
            reasons.append("exact_pdf_page_not_visible")
        if not any(fact.quotation in text for text in text_views):
            reasons.append("no_exact_quote_in_supplied_text")
        if kind == "text" and fact.location.kind != "text":
            reasons.append("source_has_no_document_ir_coordinates")
        if fact.scope.programme is not None and not any(
            fact.scope.programme in text for text in text_views if fact.quotation in text
        ):
            reasons.append("asserted_programme_text_not_visible")
    else:
        reasons.append(
            {
                "discovery": "discovery_view_is_not_source_evidence",
                "unavailable": "saved_source_view_not_successful",
                "unsupported": "unsupported_source_view",
            }[kind]
        )
    if conflicting:
        reasons.append("conflicting_saved_block_views")
    if not scan_complete and reasons:
        reasons.append("supplied_view_scan_incomplete")
    if not reasons:
        return None
    matches = exact + context_only
    return {
        "fact_id": fact.id,
        "source_step": fact.source_step,
        "source_kind": kind,
        "reasons": reasons,
        "scan_complete": scan_complete,
        "matching_blocks_visible": len(matches),
        "candidates_truncated": len(matches) > MAX_CANDIDATES,
        "candidates": [_candidate(block, fact) for block in matches[:MAX_CANDIDATES]],
    }


def location_feedback(
    decision: JournalDecision | CompactDecision,
    source_views: Sequence[Mapping[str, Any]],
    *,
    fact_ids: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Locate rejected facts only within matching supplied recorded source steps.

    ``fact_ids`` optionally selects known offending IDs; otherwise all facts are
    checked in original order. Original models are revalidated without coercion.
    Block quotations are matched literally, case and whitespace included. A
    ``context_only`` candidate is a navigation diagnostic, never a citable quote.
    PDF page metadata without that selected page's saved text cannot supply a
    page coordinate. The caller owns current-case filtering, source authenticity,
    metering, and every acceptance gate; this helper reads no raw logs or paths.
    """
    if isinstance(decision, JournalDecision):
        facts = parse_journal_decision(decision.model_dump(mode="python")).facts
    elif isinstance(decision, CompactDecision):
        facts = parse_compact_decision(decision.model_dump(mode="python")).facts
    else:
        raise ValueError("Location feedback needs a completed parsed journal/compact decision")
    if not isinstance(source_views, Sequence) or isinstance(source_views, str | bytes):
        raise ValueError("Source views must be a sequence of current-case saved views")
    if fact_ids is not None:
        if not isinstance(fact_ids, Sequence) or isinstance(fact_ids, str | bytes):
            raise ValueError("fact_ids must be a sequence of unique submitted IDs")
        if len(fact_ids) > 128:
            raise ValueError("fact_ids exceeds the original compact fact limit")
        if any(not isinstance(item, str) for item in fact_ids) or len(set(fact_ids)) != len(
            fact_ids
        ):
            raise ValueError("fact_ids must be unique submitted strings")
        wanted = set(fact_ids)
        if not wanted <= {fact.id for fact in facts}:
            raise ValueError("fact_ids includes an unknown submitted ID")
        facts = [fact for fact in facts if fact.id in wanted]
    truncated = len(facts) > MAX_FACTS or len(source_views) > MAX_VIEWS
    facts = facts[:MAX_FACTS]
    steps = {fact.source_step for fact in facts}
    views_by_step: dict[int, list[tuple[int, Mapping[str, Any], str]]] = {}
    blocks_by_key: dict[tuple[int, str], _Block] = {}
    conflicts: set[tuple[int, str]] = set()
    partial_steps: set[int] = set()
    scanned_blocks, scanned_chars = 0, 0
    view_start = max(0, len(source_views) - MAX_VIEWS)
    for index, wrapper in enumerate(source_views[view_start:], start=view_start):
        if not isinstance(wrapper, Mapping):
            continue
        step = wrapper.get("step") if "step" in wrapper else wrapper.get("source_step")
        if type(step) is not int or step not in steps:
            continue
        if "step" in wrapper and "source_step" in wrapper and wrapper["source_step"] != step:
            partial_steps.add(step)
            continue
        view = wrapper.get("view", wrapper)
        if not isinstance(view, Mapping):
            partial_steps.add(step)
            continue
        kind = _view_kind(view)
        views_by_step.setdefault(step, []).append((index, view, kind))
        if kind in {"pdf", "text"}:
            text = view.get("text")
            total_chars = view.get("text_total_chars")
            if (
                not isinstance(text, str)
                or len(text) > MAX_CONTEXT_CHARS
                or view.get("text_next_offset") is not None
                or view.get("text_offset", 0) != 0
                or (type(total_chars) is int and isinstance(text, str) and total_chars > len(text))
            ):
                partial_steps.add(step)
        if kind != "document_ir":
            continue
        raw_blocks = view.get("sections", view.get("blocks", []))
        if not isinstance(raw_blocks, list | tuple):
            partial_steps.add(step)
            continue
        if view.get("sections_next_offset") is not None or view.get("sections_offset", 0) != 0:
            partial_steps.add(step)
        total = view.get("sections_total")
        if type(total) is int and total > len(raw_blocks):
            partial_steps.add(step)
        for raw in raw_blocks:
            if scanned_blocks >= MAX_BLOCKS:
                partial_steps.add(step)
                truncated = True
                break
            scanned_blocks += 1
            block = _block(raw, step, index)
            if block is None or scanned_chars + len(block.context) > MAX_SCANNED_CHARS:
                partial_steps.add(step)
                truncated = True
                continue
            scanned_chars += len(block.context)
            key = step, block.block_id
            old = blocks_by_key.get(key)
            if old is not None and (old.section_path, old.context, old.layout) != (
                block.section_path,
                block.context,
                block.layout,
            ):
                conflicts.add(key)
            else:
                blocks_by_key.setdefault(key, block)
    blocks_by_step: dict[int, list[_Block]] = {}
    for key, block in blocks_by_key.items():
        if key not in conflicts:
            blocks_by_step.setdefault(block.step, []).append(block)
    result: dict[str, Any] = {
        "schema_version": "1",
        "diagnostics": [],
        "offending_fact_ids": [],
        "truncated": truncated,
        "scanned_views": min(len(source_views), MAX_VIEWS),
        "scanned_blocks": scanned_blocks,
        "scanned_context_chars": scanned_chars,
    }
    for fact in facts:
        diagnostic = _diagnostic(
            fact,
            blocks_by_step.get(fact.source_step, []),
            views_by_step.get(fact.source_step, []),
            scan_complete=fact.source_step not in partial_steps and len(source_views) <= MAX_VIEWS,
            conflicting=any(step == fact.source_step for step, _ in conflicts),
        )
        if diagnostic is None:
            continue
        result["diagnostics"].append(diagnostic)
        result["offending_fact_ids"].append(fact.id)
        while len(json.dumps(result, ensure_ascii=False).encode("utf-8")) > MAX_FEEDBACK_BYTES:
            result["truncated"] = True
            if diagnostic["candidates"]:
                diagnostic["candidates"].pop()
                diagnostic["candidates_truncated"] = True
            else:
                result["diagnostics"].pop()
                result["offending_fact_ids"].pop()
                return result
    return result
