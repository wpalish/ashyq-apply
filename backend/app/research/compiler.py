"""Bounded native policy compiler with replayable, source-bound proof.

The supplied scope must be independently verified *source* scope, never the
applicant's request. Supported grammars deliberately abstain on alternatives,
incomplete fee units, implicit waivers and qualification equivalence. This is
not a universal admission-policy parser or a semantic entailment shortcut.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import OrderedDict
from collections.abc import Callable, Mapping
from datetime import datetime
from threading import RLock

from app.adapters.document_ir import DocumentIR, EvidenceBlock
from app.adapters.extraction import ClaimBuilder
from app.adapters.scope_reader import read_scope
from app.adapters.structured_extraction import extract_table_requirements
from app.domain.claim_scope import ClaimScope
from app.domain.enums import ClaimType
from app.research.contracts import PolicyRule, PublicScope, QuestionGroup
from app.research.evidence import source_hash, span_from_block

COMPILER_VERSION = "native-policy-v2"
_COMPILED: OrderedDict[tuple[str, ...], tuple[str, ...]] = OrderedDict()
_CACHE_LOCK = RLock()
_MAX_CACHE_ENTRIES = 128
_CONDITIONAL = re.compile(
    r"\b(if|unless|except|excluding|provided|subject to|may|normally|typically|generally|recommended|expected|waiv\w*|exempt\w*|not|only|optional|alternatively|either|applicants with|students with|applicants from|students from|citizens|nationals|nationality|residents)\b",
    re.I,
)
_EXCEPTION = re.compile(r"\b(unless|except|excluding|waiv\w*|exempt\w*|not required)\b", re.I)
_AMBIGUOUS = re.compile(r"\b(or|either|alternatively|approximately|about|up to|from)\b|[†‡*]", re.I)
_SUBJECTS = frozenset(
    {
        "mathematics",
        "further mathematics",
        "physics",
        "chemistry",
        "biology",
        "english",
        "computer science",
        "economics",
        "history",
        "business studies",
    }
)
_SCOPE_MARKERS = {
    "degree": re.compile(
        r"\b(?:undergraduate|bachelor\w*|bsc|beng|master\w*|postgraduate|msc|meng|doctoral|phd)\b",
        re.I,
    ),
    "population": re.compile(
        r"\b(?:international\s+(?:applicants|students|candidates)|domestic|home|transfer|exchange|EU/EEA|non-EU/EEA)\b",
        re.I,
    ),
    "qualification": re.compile(
        r"\b(?:attestat|NIS|IB|international baccalaureate|A-levels?|Abitur|VWO|matura|gaokao|CBSE)\b",
        re.I,
    ),
}


def _same_academic_year(left: str, right: str) -> bool:
    def key(value: str) -> str:
        match = re.fullmatch(r"(20\d{2})[/–-](\d{2}|20\d{2})", value.strip())
        return f"{match[1]}/{match[2][-2:]}" if match else value.strip().casefold()

    return key(left) == key(right)


def _local_scope_compatible(block: EvidenceBlock, scope: PublicScope) -> bool:
    context = " ".join(
        (*block.section_path, block.caption, *block.row_headers, *block.column_headers, block.text)
    )
    local = read_scope(context, title=" / ".join(block.section_path))
    for dimension, marker in _SCOPE_MARKERS.items():
        if not marker.search(context):
            continue
        value = getattr(local, dimension)
        if dimension == "qualification" and re.search(r"\bNIS\b", context):
            if not re.search(r"\bNIS Grade 12 Certificate\b", context, re.I) or value not in {
                None,
                "NIS",
            }:
                return False
            value = "NIS"
        requested = getattr(scope, dimension)
        # Explicit but unreadable/multiple qualifiers cannot inherit page scope.
        if not value or not requested or value.casefold() != requested.casefold():
            return False
    if local.intake and local.intake.casefold() != scope.cycle.casefold():
        return False
    academic_year = getattr(scope, "academic_year", None)
    return not (
        local.academic_year
        and (not academic_year or not _same_academic_year(local.academic_year, academic_year))
    )


def _annotations(document: DocumentIR) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
    conditions: list[str] = []
    exceptions: list[str] = []
    digest = source_hash(document)
    for block in document.blocks:
        if _CONDITIONAL.search(block.text):
            if len(block.text) > 600:
                return None
            predicate = f"source:{digest}:{block.id}:{block.text}"
            (exceptions if _EXCEPTION.search(block.text) else conditions).append(predicate)
    return tuple(conditions), tuple(exceptions)


def _rule(document, blocks, scope, accessed_at, valid_until, annotations, question, group, value):
    evidence = tuple(
        span_from_block(document, b.id, 0, len(b.text), accessed_at)
        for b in blocks
        if b.text and len(b.text) <= 600
    )
    if not evidence or len(evidence) != len(blocks):
        return None
    payload = {
        "compiler": COMPILER_VERSION,
        "question": question,
        "group": str(group),
        "value": value,
        "scope": scope.model_dump(mode="json"),
        "evidence": [e.model_dump(mode="json") for e in evidence],
        "conditions": annotations[0],
        "exceptions": annotations[1],
        "valid_until": valid_until.isoformat(),
    }
    identifier = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return PolicyRule(
        id=f"{COMPILER_VERSION}:{identifier}",
        question=question,
        group=group,
        value=value,
        scope=scope,
        evidence=evidence,
        conditions=annotations[0],
        exceptions=annotations[1],
        valid_until=valid_until,
    )


def _compile_document(
    document: DocumentIR, scope: PublicScope, accessed_at: datetime, valid_until: datetime
) -> list[PolicyRule]:
    """Return candidates for supported native grammars; absence proves nothing.

    This function does not grant official-source authority. Projection still
    verifies official_urls, authentic coordinates, expiry, deterministic proof
    and independent local condition resolution. The caller binds verified scope
    to this document URL and hash in ``proof_for``.
    """
    if (
        accessed_at.utcoffset() is None
        or valid_until.utcoffset() is None
        or valid_until <= accessed_at
    ):
        raise ValueError("compiler requires timezone-aware ordered validity times")
    if len(document.blocks) > 2000 or sum(len(b.text) for b in document.blocks) > 1_000_000:
        return []
    annotations = _annotations(document)
    if annotations is None:
        return []
    rules = []

    def add(blocks, question, group, value):
        rule = _rule(
            document, blocks, scope, accessed_at, valid_until, annotations, question, group, value
        )
        if rule is not None:
            rules.append(rule)

    rows: dict[tuple[int, int], list[EvidenceBlock]] = {}
    for block in document.blocks:
        if block.kind == "table_cell" and block.table_id is not None and block.row is not None:
            rows.setdefault((block.table_id, block.row), []).append(block)
    for blocks in rows.values():
        if not all(_local_scope_compatible(b, scope) for b in blocks):
            continue
        # A compound row heading can hide a different programme or route.
        # Native IELTS extraction only understands the test component; this
        # bounded compiler accepts its unambiguous canonical row label.
        if any(
            not re.fullmatch(
                r"IELTS(?: Academic)?|International English Language Testing System(?: \(Academic\))?",
                header,
                re.I,
            )
            for b in blocks
            for header in b.row_headers
        ):
            continue
        if any(
            _AMBIGUOUS.search(" ".join((*b.row_headers, *b.column_headers, b.caption, b.text)))
            for b in blocks
        ):
            continue
        row = DocumentIR(url=document.url, title=document.title, blocks=blocks)
        builder = ClaimBuilder(
            source_url=document.url,
            accessed_at=accessed_at,
            scope=ClaimScope(
                university=scope.university,
                programme=scope.programme,
                degree=scope.degree,
                population=scope.population,
                qualification=scope.qualification,
            ),
            page_text=" ".join(b.text for b in blocks),
        )
        for claim in extract_table_requirements(row, builder):
            question = {
                ClaimType.IELTS_MIN_OVERALL: "english.overall",
                ClaimType.IELTS_MIN_SUBSCORE: "english.bands",
            }.get(claim.claim_type)
            if question:
                value = claim.normalized_value
                if question == "english.bands" and isinstance(value, int | float):
                    value = {
                        name: value for name in ("listening", "reading", "writing", "speaking")
                    }
                if question == "english.bands" and (
                    not isinstance(value, dict)
                    or set(value) != {"listening", "reading", "writing", "speaking"}
                ):
                    # Preserve supported individual minima without certifying
                    # the complete four-band obligation.
                    question = "english.bands.partial"
                add(blocks, question, QuestionGroup.ENGLISH, value)

    for block in document.blocks:
        if (
            block.kind not in {"paragraph", "list_item", "key_value"}
            or not _local_scope_compatible(block, scope)
            or len(block.text) > 600
        ):
            continue
        text = block.text.strip()
        # Full-sentence grammars avoid silently dropping tail qualifications.
        m = re.fullmatch(
            r"IELTS(?: Academic)?(?: overall)?(?: score)?(?: of)?(?: at least| minimum)?\s*[:=]?\s*(\d(?:\.\d)?)\.?",
            text,
            re.I,
        )
        if m and 4 <= float(m[1]) <= 9 and (float(m[1]) * 2).is_integer():
            add([block], "english.overall", QuestionGroup.ENGLISH, float(m[1]))
        m = re.fullmatch(
            r"(?:A )?(?:minimum )?GPA(?: of)?\s*[:=]?\s*(\d(?:\.\d+)?)\s*(?:/|out of)\s*(\d(?:\.\d+)?)\s*(?:is required)?\.?",
            text,
            re.I,
        )
        if m and 0 <= float(m[1]) <= float(m[2]) <= 10:
            add(
                [block],
                "academic.grades",
                QuestionGroup.ACADEMIC,
                {"kind": "gpa", "minimum": float(m[1]), "scale": float(m[2])},
            )
        m = re.fullmatch(
            r"(?:Required qualification|Applicants must hold)\s*[:]?\s*(Attestat|NIS Grade 12 Certificate|International Baccalaureate Diploma|A-levels)\.?",
            text,
            re.I,
        )
        if m:
            # Only aliases already explicitly read by native source scope are
            # canonicalized. NIS is not silently treated as Attestat/IB.
            credential = {
                "attestat": "attestat",
                "nis grade 12 certificate": "NIS",
                "international baccalaureate diploma": "IB",
                "a-levels": "A-levels",
            }.get(m[1].casefold(), m[1])
            if scope.qualification and scope.qualification.casefold() == credential.casefold():
                add(
                    [block],
                    "academic.qualification",
                    QuestionGroup.ACADEMIC,
                    {"credential": credential, "required": True},
                )
        m = re.fullmatch(
            r"Required subjects?\s*:\s*([A-Za-z ]+(?:, [A-Za-z ]+)*)(?:\.)?", text, re.I
        )
        if m and all(subject.strip().casefold() in _SUBJECTS for subject in m[1].split(",")):
            add(
                [block],
                "academic.subjects",
                QuestionGroup.ACADEMIC,
                {"required": [s.strip() for s in m[1].split(",")]},
            )
        m = re.fullmatch(
            r"Admission route\s*:\s*(direct entry|foundation programme|preparatory year)\.?",
            text,
            re.I,
        )
        if m:
            add([block], "academic.route", QuestionGroup.ACADEMIC, {"route": m[1].casefold()})
        m = re.fullmatch(
            r"(?:Application|Admission) deadline\s*:\s*(\d{4}-\d{2}-\d{2})(?:\s*\(([^()]{1,80})\))?\.?",
            text,
            re.I,
        )
        if m:
            try:
                deadline = datetime.strptime(m[1], "%Y-%m-%d").date().isoformat()
            except ValueError:
                continue
            add(
                [block],
                "admission.deadline",
                QuestionGroup.DEADLINE,
                {
                    "date": deadline,
                    "cycle": scope.cycle,
                    "round": m[2],
                    "time": None,
                    "timezone": None,
                },
            )
        m = re.fullmatch(
            r"Tuition(?: fee)?\s*:\s*(USD|EUR|GBP|CAD|SGD|KRW|KZT)\s*([\d,]+(?:\.\d{1,2})?)\s+per\s+(academic year|year|semester|credit)\s+for\s+(20\d{2}(?:[/–-]\d{2,4})?)\.?",
            text,
            re.I,
        )
        if (
            m
            and re.fullmatch(r"(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d{1,2})?", m[2])
            and scope.academic_year is not None
            and _same_academic_year(m[4], scope.academic_year)
        ):
            amount = float(m[2].replace(",", ""))
            if amount > 0:
                add(
                    [block],
                    "tuition.schedule",
                    QuestionGroup.TUITION,
                    {
                        "amount": amount,
                        "currency": m[1].upper(),
                        "period": m[3].casefold(),
                        "year": m[4],
                        "category": "tuition",
                        "mandatory_fees_included": None,
                    },
                )
    return list({r.id: r for r in rules}.values())


def compile_document(
    document: DocumentIR, scope: PublicScope, accessed_at: datetime, valid_until: datetime
) -> list[PolicyRule]:
    """Compile candidates with bounded immutable source/version cache reuse.

    The key includes the entire IR hash, verified source scope, compiler version
    and clocks. Cached JSON is reconstructed on each return: mutating a nested
    candidate value cannot poison another applicant's compiler result.
    """
    if len(document.blocks) > 2000 or sum(len(b.text) for b in document.blocks) > 1_000_000:
        return []
    key = (
        COMPILER_VERSION,
        source_hash(document),
        scope.model_dump_json(),
        accessed_at.isoformat(),
        valid_until.isoformat(),
    )
    with _CACHE_LOCK:
        saved = _COMPILED.get(key)
        if saved is not None:
            _COMPILED.move_to_end(key)
    if saved is None:
        saved = tuple(
            rule.model_dump_json()
            for rule in _compile_document(document, scope, accessed_at, valid_until)
        )
        with _CACHE_LOCK:
            _COMPILED[key] = saved
            _COMPILED.move_to_end(key)
            while len(_COMPILED) > _MAX_CACHE_ENTRIES:
                _COMPILED.popitem(last=False)
    return [PolicyRule.model_validate_json(payload) for payload in saved]


def proof_for(
    documents: Mapping[str, DocumentIR],
    verified_scopes: Mapping[str, PublicScope],
    accessed_at: datetime,
    valid_until: datetime,
) -> Callable[[PolicyRule], bool]:
    """Proof closure bound to compiler version, source bytes, scope and times.

    Recompilation, rather than a numeric/lexical match, prevents forged values,
    removed exceptions, altered units, injected scope and invented source spans.
    Snapshot serialization prevents later mutable DocumentIR changes from
    retroactively granting proof to a new candidate.
    """
    accepted: dict[str, str] = {}
    for url, document in documents.items():
        scope = verified_scopes.get(url)
        if scope is None or document.url != url:
            continue
        for rule in compile_document(document, scope, accessed_at, valid_until):
            accepted[rule.id] = rule.model_dump_json()
    return lambda rule: accepted.get(rule.id) == rule.model_dump_json()
