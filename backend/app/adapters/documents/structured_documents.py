"""Document obligations from a labelled row with explicit programme context."""

from __future__ import annotations

import re
from dataclasses import replace

from app.adapters.document_ir import DocumentIR
from app.adapters.extraction import ClaimBuilder
from app.adapters.scope_reader import read_scope
from app.adapters.search.ontology import titles_name_same_programme
from app.domain.claim_scope import ClaimScope
from app.domain.enums import ClaimStatus, ClaimType, DocumentOwner, DocumentPurpose
from app.domain.programme_identity import Verdict
from app.schemas.result import DocumentItem

_SUPPLEMENT = re.compile(r"supplement(?:al|ary) application", re.I)
_CAMPUS = re.compile(r"^(.+?)\s+campus$", re.I)
_OSSD = re.compile(r"\bOntario Secondary School Diploma\s*\(OSSD\)", re.I)


def read_supplemental_tables(
    doc: DocumentIR, builder: ClaimBuilder, purpose: DocumentPurpose
) -> list[DocumentItem]:
    """Never apply another campus's row or borrow the requested degree as evidence."""
    requested = builder.meta.get("program")
    if not isinstance(requested, str):
        return []
    campuses = {
        match[1]
        for block in doc.blocks
        for heading in block.section_path
        if (match := _CAMPUS.fullmatch(heading))
    }
    wanted_campuses = {c for c in campuses if c.casefold() in requested.casefold()}
    if len(wanted_campuses) > 1 or (len(campuses) > 1 and not wanted_campuses):
        return []
    original_scope = builder.meta.get("scope")
    items: list[DocumentItem] = []
    seen: set[tuple[str, str | None]] = set()
    try:
        for i, block in enumerate(doc.blocks):
            if (
                block.kind != "table_cell"
                or block.text.casefold() != "required"
                or len(block.row_headers) != 1
                or not _SUPPLEMENT.fullmatch(block.row_headers[0])
                or block.column_headers
            ):
                continue
            named = [
                heading
                for heading in block.section_path
                if titles_name_same_programme(requested, heading) is Verdict.YES
            ]
            if len(named) != 1:
                continue
            local_campuses = {
                match[1] for heading in block.section_path if (match := _CAMPUS.fullmatch(heading))
            }
            if len(local_campuses) > 1 or (wanted_campuses and local_campuses != wanted_campuses):
                continue
            campus = next(iter(local_campuses), None)
            if (
                campus
                and re.search(r"\([^()]+\)", requested)
                and campus.casefold() not in requested.casefold()
            ):
                continue
            programme = named[0] + (f" ({campus})" if campus else "")
            # Only preceding evidence inside this exact section may qualify the row.
            context = [
                b.text
                for b in doc.blocks[:i]
                if b.section_path == block.section_path and b.kind in {"paragraph", "list_item"}
            ]
            local = read_scope(" ".join(context), title=" ".join(block.section_path))
            qualifications = {m.group(0) for text in context if (m := _OSSD.search(text))}
            if len(qualifications) > 1 or (qualifications and local.qualification):
                continue
            qualification = next(iter(qualifications), local.qualification)
            identity = (programme, qualification)
            if identity in seen:
                continue
            scope = replace(
                original_scope if isinstance(original_scope, ClaimScope) else ClaimScope(),
                programme=programme,
                degree=local.degree,
                population=local.population,
                qualification=qualification,
            )
            builder.meta["scope"] = scope
            excerpt = f"{block.row_headers[0]} {block.text}"
            notes = (
                "The degree level is not stated in this section." if scope.degree is None else ""
            )
            claim = builder.add(
                ClaimType.REQUIRED_DOCUMENT,
                "Supplemental Application",
                excerpt,
                programme=programme,
                section=" / ".join([*block.section_path, *context]),
                status=ClaimStatus.NEEDS_OFFICIAL_CLARIFICATION if notes else None,
                notes=notes,
            )
            if claim is None:
                continue
            seen.add(identity)
            suffix = f"; {qualification}" if qualification else ""
            items.append(
                DocumentItem(
                    name=f"Supplemental Application — {programme}{suffix}",
                    purpose=purpose,
                    owner=DocumentOwner.APPLICANT,
                    format_notes=f"Applies to {programme}{suffix}. {notes}".strip(),
                    source_url=doc.url,
                    claim_ids=[doc.url],
                    scope=scope,
                )
            )
    finally:
        builder.meta["scope"] = original_scope
    return items
