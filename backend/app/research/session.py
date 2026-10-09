"""Native pipeline hooks for public source reuse and local decision projection.

No profile is written to the shared cache. A fetched URL must independently
receive native official-source authority before its records are considered.
Source scope comes from that source's words, never from the requested scope.
"""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from pydantic import Field, model_validator
from sqlalchemy import select

from app.adapters.discovery.registry_identities import institution_identities
from app.adapters.document_ir import DocumentIR, build_document_ir
from app.adapters.fetching import FetchResult
from app.adapters.scope_reader import read_scope
from app.adapters.search.ontology import titles_name_same_programme
from app.domain.claim_verifier import url_matches_domains
from app.domain.programme_identity import Verdict
from app.models.university import University
from app.research.contracts import DecisionAnswer, PublicScope, QuestionState, StrictModel
from app.research.evidence import PublicEvidenceStore, project
from app.research.questions import core_questions
from app.schemas.result import ProgramResult


class PublicSource(StrictModel):
    document: DocumentIR
    accessed_at: datetime
    valid_until: datetime
    # This records the Fetcher's response, not an applicant-derived scope.
    fetched_url: str = Field(min_length=1)

    @model_validator(mode="after")
    def times(self) -> PublicSource:
        if self.accessed_at.utcoffset() is None or self.valid_until.utcoffset() is None:
            raise ValueError("source timestamps must include timezone")
        if self.valid_until <= self.accessed_at:
            raise ValueError("invalid source validity interval")
        return self


class ProjectionLimit(ValueError):
    """An omitted subset cannot establish the absence of conflicting policies."""


def observe_fetch(runner: Any, url: str, result: FetchResult) -> None:
    """Observe native successful HTML fetches without issuing another read."""
    if not result.ok or result.is_pdf or not (result.final_url or url).startswith("https://"):
        return
    if not result.text or len(result.text) > 5_000_000:
        return
    final_url = result.final_url or url
    document = build_document_ir(result.text, final_url)
    if len(document.blocks) > 2000:
        return
    records = getattr(runner, "_recall_public_sources", None)
    if records is None:
        records = {}
        runner._recall_public_sources = records
    accessed = result.fetched_at
    if accessed.utcoffset() is None or runner.settings.cache_ttl_seconds <= 0:
        return
    records[final_url] = PublicSource(
        document=document,
        fetched_url=url,
        accessed_at=accessed,
        valid_until=accessed + timedelta(seconds=runner.settings.cache_ttl_seconds),
    )


def _qualification(value: str) -> str | None:
    if re.search(r"\bNIS\b|Nazarbayev Intellectual Schools", value, re.I):
        return "NIS"
    if re.search(r"\battestat\b|Kazakhstan (?:national )?(?:secondary|school)", value, re.I):
        return "attestat"
    return None


def _source_scope(record: PublicSource, university: str, programme: str) -> PublicScope | None:
    document = record.document
    text = "\n".join(b.text for b in document.blocks)
    stated = read_scope(text, title=document.title)
    # Missing cycle cannot inherit the applicant's cycle or the machine year.
    if not stated.intake:
        return None
    names_programme = titles_name_same_programme(document.title, programme) is Verdict.YES
    qualification = stated.qualification
    # NIS is a specific named qualification only in a certificate/entry context.
    if re.search(r"\bNIS\s+(?:grade\s*12\s+)?(?:certificate|qualification|diploma)\b", text, re.I):
        if qualification not in (None, "NIS") or re.search(r"\battestat\b", text, re.I):
            return None
        qualification = "NIS"
    campus = None
    campus_names = re.findall(r"\bCampus\s*:\s*([^.;\n]{1,80})", text, re.I)
    if re.search(r"\bcampus\b", document.title + "\n" + text, re.I) and len(set(campus_names)) != 1:
        return None
    if len(set(campus_names)) == 1:
        campus = campus_names[0].strip()
    return PublicScope(
        university=university,
        cycle=stated.intake,
        academic_year=stated.academic_year,
        programme=programme if names_programme else None,
        campus=campus,
        degree=stated.degree,
        population=stated.population,
        qualification=qualification,
    )


def _directory(runner: Any, university: str, cycle: str) -> Path:
    university, cycle = PublicEvidenceStore._identity(university, cycle)
    identity = hashlib.sha256(f"{university}\0{cycle}".encode()).hexdigest()
    return Path(runner.settings.cache_dir) / "public-research" / identity


def _trusted_domains(runner: Any, result: ProgramResult) -> tuple[str, ...]:
    def equal(left: str, right: str) -> bool:
        return " ".join(left.casefold().split()) == " ".join(right.casefold().split())

    domains = {
        domain
        for identity in institution_identities()
        if equal(identity.name, result.university) and equal(identity.country, result.country)
        for domain in identity.domains
    }
    session = getattr(runner, "session", None)
    if session is not None:
        for institution in session.scalars(
            select(University).where(
                University.name == result.university, University.country == result.country
            )
        ):
            if (
                institution.domain_status in {"curated", "site_identity_checked"}
                and institution.domain
            ):
                domains.add(institution.domain)
    return tuple(sorted(domains))


def _sources(
    runner: Any, university: str, cycle: str, domains: tuple[str, ...]
) -> dict[str, PublicSource]:
    directory = _directory(runner, university, cycle)
    records: dict[str, PublicSource] = {}
    now = datetime.now(UTC)
    if directory.exists():
        for path in directory.glob("source-*.json"):
            if path.stat().st_size > 5_000_000:
                continue
            try:
                record = PublicSource.model_validate_json(path.read_bytes())
            except ValueError:
                continue
            if not record.accessed_at <= now < record.valid_until:
                continue
            if url_matches_domains(record.document.url, domains) and url_matches_domains(
                record.fetched_url, domains
            ):
                records[record.document.url] = record
                if len(records) > 240:
                    raise ProjectionLimit("Too many active sources for bounded projection")
    for url, record in getattr(runner, "_recall_public_sources", {}).items():
        if not url_matches_domains(url, domains) or not url_matches_domains(
            record.fetched_url, domains
        ):
            continue
        records[url] = record
        if len(records) > 240:
            raise ProjectionLimit("Too many active sources for bounded projection")
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"source-{hashlib.sha256(url.encode()).hexdigest()}.json"
        # Cache records are replaceable public evidence, never a run checkpoint.
        import os
        import tempfile

        fd, name = tempfile.mkstemp(dir=directory, suffix=".tmp")
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(record.model_dump_json().encode())
            os.replace(name, path)
        finally:
            Path(name).unlink(missing_ok=True)
    return records


def project_run_questions(runner: Any) -> dict[str, dict]:
    """Expose all six groups, including pending ones, after native assessment."""
    from app.research.compiler import compile_document, proof_for

    now = datetime.now(UTC)
    output = {}
    for row in runner._rows():
        result = ProgramResult.model_validate(row.payload)
        requested = PublicScope(
            university=result.university,
            cycle=runner.intake,
            academic_year=runner._academic_year(),
            programme=result.program,
            degree=str(result.degree),
            population="international",
            qualification=_qualification(runner.profile.context.education_system),
        )
        try:
            sources = _sources(
                runner, result.university, runner.intake, _trusted_domains(runner, result)
            )
        except ProjectionLimit as exc:
            output[result.id] = _unavailable(requested, str(exc))
            continue
        sources = {url: r for url, r in sources.items() if r.accessed_at <= now < r.valid_until}
        official_urls = set(sources)
        if sum(len(b.text) for r in sources.values() for b in r.document.blocks) > 8_000_000:
            output[result.id] = _unavailable(
                requested, "Public source text exceeds projection work limit"
            )
            continue
        scopes = {
            url: scope
            for url, record in sources.items()
            if (scope := _source_scope(record, result.university, result.program)) is not None
        }
        documents = {url: r.document for url, r in sources.items() if url in scopes}
        rules = []
        for url, document in documents.items():
            record = sources[url]
            rules.extend(
                compile_document(document, scopes[url], record.accessed_at, record.valid_until)
            )
            if len(rules) > 512:
                break
        if len(rules) > 512:
            output[result.id] = _unavailable(
                requested, "Policy count exceeds projection work limit"
            )
            continue
        # Compilation is deterministic and cheap relative to source work.
        # Replay proof binds rules to each original source/access/expiry tuple.
        proofs = [
            proof_for(
                {url: document},
                {url: scopes[url]},
                sources[url].accessed_at,
                sources[url].valid_until,
            )
            for url, document in documents.items()
        ]
        store = PublicEvidenceStore(_directory(runner, result.university, runner.intake) / "rules")
        store.save(result.university, runner.intake, rules)

        def proved(rule, checks=proofs):
            return any(check(rule) for check in checks)

        answers = [
            project(q, rules, documents, official_urls, now, proof=proved)
            for q in core_questions(requested)
        ]
        output[result.id] = {a.question_id: a.model_dump(mode="json") for a in answers}
    return output


def _unavailable(scope: PublicScope, reason: str) -> dict[str, dict]:
    return {
        q.id: DecisionAnswer(
            question_id=q.id,
            state=QuestionState.UNAVAILABLE,
            reason=reason,
            rules=(),
            missing=q.required,
        ).model_dump(mode="json")
        for q in core_questions(scope)
    }
