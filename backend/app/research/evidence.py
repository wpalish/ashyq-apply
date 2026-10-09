"""Compile public source blocks and project only complete, current policies.

The store contains no profiles. Callers supply official-source authority from
the existing identity verifier; having a same-domain URL is insufficient.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from pydantic import TypeAdapter

from app.adapters.document_ir import DocumentIR
from app.research.contracts import (
    DecisionAnswer,
    EvidenceSpan,
    PolicyRule,
    QuestionState,
    ResearchQuestion,
)

RULES = TypeAdapter(list[PolicyRule])


def source_hash(document: DocumentIR) -> str:
    """Hash the structured extraction input, including headers and links."""
    from dataclasses import asdict

    payload = json.dumps(asdict(document), sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def span_from_block(
    document: DocumentIR, block_id: str, start: int, end: int, accessed_at: datetime
) -> EvidenceSpan:
    block = next(b for b in document.blocks if b.id == block_id)
    if not 0 <= start < end <= len(block.text) or end - start > 600:
        raise ValueError("invalid evidence coordinates")
    if accessed_at.utcoffset() is None:
        raise ValueError("access time must include timezone")
    return EvidenceSpan(
        source_url=document.url,
        source_hash=source_hash(document),
        accessed_at=accessed_at,
        block_id=block.id,
        start=start,
        end=end,
        quote=block.text[start:end],
        section_path=block.section_path,
        row=block.row,
        column=block.col,
    )


def authentic(span: EvidenceSpan, document: DocumentIR) -> bool:
    block = next((b for b in document.blocks if b.id == span.block_id), None)
    return bool(
        block
        and str(span.source_url) == document.url
        and span.source_hash == source_hash(document)
        and 0 <= span.start < span.end <= len(block.text)
        and block.text[span.start : span.end] == span.quote
        and block.section_path == span.section_path
        and block.row == span.row
        and block.col == span.column
    )


def validate_rule(
    rule: PolicyRule, documents: dict[str, DocumentIR], official_urls: set[str], now: datetime
) -> None:
    if now.utcoffset() is None or rule.valid_until.utcoffset() is None:
        raise ValueError("policy times must include timezone")
    if rule.valid_until <= now:
        raise ValueError("expired policy")
    for span in rule.evidence:
        url = str(span.source_url)
        if span.accessed_at.utcoffset() is None or span.accessed_at > now:
            raise ValueError("invalid access date")
        if url not in official_urls or url not in documents or not authentic(span, documents[url]):
            raise ValueError("evidence is not authenticated official source text")


def project(
    question: ResearchQuestion,
    rules: list[PolicyRule],
    documents: dict[str, DocumentIR],
    official_urls: set[str],
    now: datetime,
    *,
    proof: Callable[[PolicyRule], bool],
    condition_applies: Callable[[str], bool | None] = lambda _: None,
    unavailable_reason: str | None = None,
) -> DecisionAnswer:
    accepted = []
    for rule in rules:
        if not rule.scope.covers(question.scope):
            continue
        try:
            validate_rule(rule, documents, official_urls, now)
        except ValueError:
            continue
        # Authentic source text cannot by itself prove a value or exception.
        if not proof(rule):
            continue
        if any(condition_applies(c) is not True for c in rule.conditions):
            continue
        if any(condition_applies(e) is not False for e in rule.exceptions):
            continue
        accepted.append(rule)
    # Resolve the dependency DAG across groups. Missing parents and cycles
    # cannot establish each other's applicability.
    counts: dict[str, int] = {}
    for rule in accepted:
        counts[rule.id] = counts.get(rule.id, 0) + 1
    accepted = [r for r in accepted if counts[r.id] == 1]
    resolved: set[str] = set()
    while True:
        ready = {r.id for r in accepted if set(r.dependencies) <= resolved}
        if ready <= resolved:
            break
        resolved |= ready
    accepted = [r for r in accepted if r.id in resolved and r.group == question.group]
    required = set(question.required)
    accepted = [r for r in accepted if r.question in required]
    missing = tuple(sorted(required - {r.question for r in accepted}))
    conflict = any(
        a.question == b.question and a.value != b.value
        for i, a in enumerate(accepted)
        for b in accepted[i + 1 :]
    )
    if conflict:
        state, reason = QuestionState.CONFLICT, "Applicable official policies disagree"
    elif not missing:
        state, reason = QuestionState.ANSWERED, "Every required policy has current scoped evidence"
    elif accepted:
        state, reason = QuestionState.PARTIAL, "Some required policies remain unproved"
    elif unavailable_reason:
        state, reason = QuestionState.UNAVAILABLE, unavailable_reason
    else:
        state, reason = QuestionState.PENDING, "No complete authenticated policy yet"
    return DecisionAnswer(
        question_id=question.id, state=state, reason=reason, rules=tuple(accepted), missing=missing
    )


class PublicEvidenceStore:
    """Atomic institution/cycle cache, invalidated against current source hashes."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def _path(self, university: str, cycle: str) -> Path:
        key = hashlib.sha256(json.dumps([university, cycle]).encode()).hexdigest()
        return self.directory / f"{key}.json"

    def save(self, university: str, cycle: str, rules: list[PolicyRule]) -> None:
        if any(r.scope.university != university or r.scope.cycle != cycle for r in rules):
            raise ValueError("cache identity mismatch")
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self._path(university, cycle)
        # A unique sibling avoids collision between concurrent cache compilers.
        import os
        import tempfile

        fd, name = tempfile.mkstemp(dir=self.directory, suffix=".tmp")
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(RULES.dump_json(rules))
            os.replace(name, path)
        finally:
            Path(name).unlink(missing_ok=True)

    def load(
        self,
        university: str,
        cycle: str,
        documents: dict[str, DocumentIR],
        official_urls: set[str],
        now: datetime,
    ) -> list[PolicyRule]:
        path = self._path(university, cycle)
        if not path.exists():
            return []
        result = []
        for rule in RULES.validate_json(path.read_bytes()):
            if rule.scope.university != university or rule.scope.cycle != cycle:
                continue
            try:
                validate_rule(rule, documents, official_urls, now)
            except ValueError:
                continue
            result.append(rule)
        return result
