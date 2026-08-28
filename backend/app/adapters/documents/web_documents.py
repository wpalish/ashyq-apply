"""Building the document checklist for an approved programme.

Runs only after the applicant approves a row, because it is the expensive
stage. It separates what the applicant sends from what the school and the
referees must send, since those have different lead times and are the usual
cause of a missed deadline.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime

from app.adapters.base import AdapterResult, Candidate, CandidateProgram
from app.adapters.extraction import (
    ClaimBuilder,
    html_title,
    html_to_text,
    is_official_domain,
)
from app.adapters.fetching import Fetcher
from app.domain.enums import ClaimType, DocumentOwner, DocumentPurpose, SourceSpecificity
from app.schemas.claim import UnresolvedQuestion
from app.schemas.result import DocumentChecklist, DocumentItem, Scholarship

#: Phrases that identify a document, and how it should be classified.
_DOC_RULES: tuple[tuple[str, str, DocumentOwner, dict], ...] = (
    ("diploma", "Secondary school diploma (certified copy)", DocumentOwner.SCHOOL,
     {"needs_translation": True, "needs_notarization": True, "lead_time_days": 21}),
    ("transcript", "Full academic transcript", DocumentOwner.SCHOOL,
     {"needs_translation": True, "lead_time_days": 21}),
    ("translation", "Certified English translation of non-English documents", DocumentOwner.THIRD_PARTY,
     {"needs_translation": True, "lead_time_days": 14}),
    ("passport", "Passport identity page (copy)", DocumentOwner.APPLICANT, {"lead_time_days": 1}),
    ("personal statement", "Personal statement", DocumentOwner.APPLICANT, {"lead_time_days": 14}),
    ("statement of motivation", "Statement of motivation", DocumentOwner.APPLICANT, {"lead_time_days": 14}),
    ("leadership experience", "Leadership experience essay", DocumentOwner.APPLICANT, {"lead_time_days": 10}),
    ("reference", "Academic reference", DocumentOwner.RECOMMENDER, {"lead_time_days": 30}),
    ("recommendation", "Letter of recommendation", DocumentOwner.RECOMMENDER, {"lead_time_days": 30}),
    ("curriculum vitae", "Curriculum vitae", DocumentOwner.APPLICANT, {"lead_time_days": 5}),
    ("portfolio", "Portfolio", DocumentOwner.APPLICANT, {"lead_time_days": 30}),
    ("credential evaluation", "Course-by-course credential evaluation (WES/ECE)", DocumentOwner.THIRD_PARTY,
     {"needs_credential_evaluation": True, "lead_time_days": 45}),
    ("apostille", "Apostille certification", DocumentOwner.THIRD_PARTY,
     {"needs_apostille": True, "lead_time_days": 21}),
    ("financial", "Proof of financial resources", DocumentOwner.APPLICANT, {"lead_time_days": 10}),
)

_WORDS = re.compile(r"maximum (\d{2,4}) words|(\d{2,4})[- ]word (?:limit|maximum)", re.IGNORECASE)
_PAGES = re.compile(r"maximum (\d{1,2}) pages?", re.IGNORECASE)
_SIZE = re.compile(r"max(?:imum)? (\d{1,3})\s*MB", re.IGNORECASE)
_FORMAT = re.compile(r"\b(PDF|DOCX?|JPE?G|PNG)\b")


class WebDocumentsAdapter:
    name = "web-documents"

    def __init__(self, fetcher: Fetcher, academic_year: str) -> None:
        self.fetcher = fetcher
        self.academic_year = academic_year

    async def collect(
        self, candidate: Candidate, program: CandidateProgram, scholarships: list[Scholarship]
    ) -> tuple[DocumentChecklist, AdapterResult]:
        out = AdapterResult()
        checklist = DocumentChecklist(
            result_id="", university=candidate.name, program=program.name,
            generated_at=datetime.now(UTC),
        )

        admission_docs = await self._from_page(
            candidate, program, program.url, DocumentPurpose.ADMISSION, out
        )
        checklist.admission_documents = admission_docs

        for sch in scholarships:
            for url in sch.source_urls:
                docs = await self._from_page(candidate, program, url, DocumentPurpose.SCHOLARSHIP, out)
                for d in docs:
                    d.deadline = sch.deadline
                    d.deadline_timezone = sch.deadline_timezone
                    d.name = f"{d.name} — for {sch.name}"
                checklist.scholarship_documents.extend(docs)
            if sch.application_mode.value == "nomination":
                checklist.unresolved.append(
                    UnresolvedQuestion(
                        topic="scholarship nomination",
                        question=(
                            f"How are candidates nominated for '{sch.name}', and is any action "
                            "required from the applicant?"
                        ),
                        why_it_matters="A nomination-only award cannot be applied for directly; "
                        "missing the internal process means missing the award entirely.",
                        university=candidate.name,
                        program=program.name,
                        suggested_contact="Departmental admissions coordinator",
                        blocking=True,
                    )
                )

        everything = checklist.admission_documents + checklist.scholarship_documents
        checklist.applicant_actions = [d for d in everything if d.owner == DocumentOwner.APPLICANT]
        checklist.school_actions = [d for d in everything if d.owner == DocumentOwner.SCHOOL]
        checklist.recommender_actions = [d for d in everything if d.owner == DocumentOwner.RECOMMENDER]
        checklist.certification_actions = [d for d in everything if d.owner == DocumentOwner.THIRD_PARTY]
        checklist.ordered_steps = _order_steps(everything)

        if not everything:
            checklist.completeness = "unavailable"
            checklist.unresolved.append(
                UnresolvedQuestion(
                    topic="required documents",
                    question=f"What is the full list of required documents for {program.name}?",
                    why_it_matters="No official document list could be read, so nothing can be prepared in advance.",
                    university=candidate.name,
                    program=program.name,
                    blocking=True,
                )
            )
        else:
            checklist.completeness = "official" if out.pages_failed == 0 else "partial"
        return checklist, out

    async def _from_page(
        self, candidate: Candidate, program: CandidateProgram, url: str | None,
        purpose: DocumentPurpose, out: AdapterResult,
    ) -> list[DocumentItem]:
        if not url:
            return []
        res = await self.fetcher.get(url)
        out.pages_checked += 1
        if not res.ok:
            out.pages_failed += 1
            out.errors.append(f"{url}: {res.outcome.value} — {res.error}")
            out.retry_urls.append(url)
            return []

        text = html_to_text(res.text)
        builder = ClaimBuilder(
            source_url=url, page_title=html_title(res.text),
            specificity=SourceSpecificity.PROGRAM_INTAKE,
            program=program.name, academic_year=self.academic_year,
            official_domain=url.startswith("fixture://") or is_official_domain(url, [candidate.domain]),
            extraction_method="fixture" if url.startswith("fixture://") else "html_rule",
            accessed_at=res.fetched_at,
        )

        items: list[DocumentItem] = []
        seen: set[str] = set()
        for line in text.splitlines():
            low = line.lower().strip()
            if not low or len(low) > 300:
                continue
            for needle, name, owner, flags in _DOC_RULES:
                if needle not in low or name in seen:
                    continue
                seen.add(name)
                words = _WORDS.search(line)
                pages = _PAGES.search(line)
                size = _SIZE.search(line)
                item = DocumentItem(
                    name=name, purpose=purpose, owner=owner,
                    format_notes=", ".join(sorted(set(_FORMAT.findall(line)))) or "",
                    max_pages=int(pages.group(1)) if pages else None,
                    max_file_size_mb=float(size.group(1)) if size else None,
                    word_limit=int(words.group(1) or words.group(2)) if words else None,
                    prompt_text=line.strip()[:280] if purpose == DocumentPurpose.SCHOLARSHIP else None,
                    source_url=url, claim_ids=[url], **flags,
                )
                items.append(item)
                builder.add(ClaimType.REQUIRED_DOCUMENT, name, line.strip()[:300], confidence=0.75)
                if item.word_limit:
                    builder.add(ClaimType.ESSAY_PROMPT,
                                {"document": name, "word_limit": item.word_limit},
                                line.strip()[:300], confidence=0.8)
                if owner == DocumentOwner.RECOMMENDER:
                    builder.add(ClaimType.RECOMMENDATION_REQUIREMENT, name, line.strip()[:300], confidence=0.75)
                break
        out.claims.extend(builder.claims)
        return items


def _order_steps(items: list[DocumentItem]) -> list[str]:
    """Longest lead time first — that is the order that actually prevents misses."""
    ordered = sorted(items, key=lambda d: -(d.lead_time_days or 0))
    steps = []
    for i, d in enumerate(ordered, 1):
        lead = f" (allow ~{d.lead_time_days} days)" if d.lead_time_days else ""
        who = {
            DocumentOwner.APPLICANT: "You",
            DocumentOwner.SCHOOL: "Your school",
            DocumentOwner.RECOMMENDER: "Your referee",
            DocumentOwner.THIRD_PARTY: "A third party",
        }[d.owner]
        steps.append(f"{i}. {who}: {d.name}{lead}")
    return steps
