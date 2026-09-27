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
    verification_domains,
)
from app.adapters.fetching import Fetcher
from app.adapters.scope_reader import read_scope
from app.domain.enums import ClaimType, DocumentOwner, DocumentPurpose, SourceSpecificity
from app.schemas.claim import UnresolvedQuestion
from app.schemas.result import DocumentChecklist, DocumentItem, Scholarship

#: Phrases that identify a document, and how it should be classified.
_DOC_RULES: tuple[tuple[str, str, DocumentOwner, dict], ...] = (
    (
        "diploma",
        "Secondary school diploma (certified copy)",
        DocumentOwner.SCHOOL,
        {"needs_translation": True, "needs_notarization": True, "lead_time_days": 21},
    ),
    (
        "transcript",
        "Full academic transcript",
        DocumentOwner.SCHOOL,
        {"needs_translation": True, "lead_time_days": 21},
    ),
    (
        "translation",
        "Certified English translation of non-English documents",
        DocumentOwner.THIRD_PARTY,
        {"needs_translation": True, "lead_time_days": 14},
    ),
    ("passport", "Passport identity page (copy)", DocumentOwner.APPLICANT, {"lead_time_days": 1}),
    ("personal statement", "Personal statement", DocumentOwner.APPLICANT, {"lead_time_days": 14}),
    (
        "statement of motivation",
        "Statement of motivation",
        DocumentOwner.APPLICANT,
        {"lead_time_days": 14},
    ),
    (
        "leadership experience",
        "Leadership experience essay",
        DocumentOwner.APPLICANT,
        {"lead_time_days": 10},
    ),
    ("reference", "Academic reference", DocumentOwner.RECOMMENDER, {"lead_time_days": 30}),
    (
        "recommendation",
        "Letter of recommendation",
        DocumentOwner.RECOMMENDER,
        {"lead_time_days": 30},
    ),
    ("curriculum vitae", "Curriculum vitae", DocumentOwner.APPLICANT, {"lead_time_days": 5}),
    ("portfolio", "Portfolio", DocumentOwner.APPLICANT, {"lead_time_days": 30}),
    (
        "credential evaluation",
        "Course-by-course credential evaluation (WES/ECE)",
        DocumentOwner.THIRD_PARTY,
        {"needs_credential_evaluation": True, "lead_time_days": 45},
    ),
    (
        "apostille",
        "Apostille certification",
        DocumentOwner.THIRD_PARTY,
        {"needs_apostille": True, "lead_time_days": 21},
    ),
    ("financial", "Proof of financial resources", DocumentOwner.APPLICANT, {"lead_time_days": 10}),
)

_WORDS = re.compile(r"maximum (\d{2,4}) words|(\d{2,4})[- ]word (?:limit|maximum)", re.IGNORECASE)
_PAGES = re.compile(r"maximum (\d{1,2}) pages?", re.IGNORECASE)
_SIZE = re.compile(r"max(?:imum)? (\d{1,3})\s*MB", re.IGNORECASE)
_FORMAT = re.compile(r"\b(PDF|DOCX?|JPE?G|PNG)\b")


#: What a scholarship submission waits for when the award requires an offer.
#: A phrase rather than an id: the offer letter is issued by the university
#: after a decision, so it is not one of the checklist's own items and cannot
#: be pointed at by one.
_OFFER_LETTER = "admission offer letter"


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
            result_id="",
            university=candidate.name,
            program=program.name,
            generated_at=datetime.now(UTC),
        )

        admission_docs = await self._from_page(
            candidate, program, program.url, DocumentPurpose.ADMISSION, out
        )
        checklist.admission_documents = admission_docs

        for sch in scholarships:
            for url in sch.source_urls:
                docs = await self._from_page(
                    candidate, program, url, DocumentPurpose.SCHOLARSHIP, out
                )
                for d in docs:
                    d.deadline = sch.deadline
                    d.deadline_timezone = sch.deadline_timezone
                    d.name = f"{d.name} — for {sch.name}"
                    # The guide's own example of a dependency between
                    # documents: an offer letter before a scholarship
                    # submission. Recorded only when the award page **said**
                    # an offer is required — `depends_on` was a declared field
                    # nothing ever set, and filling it with a guess about
                    # someone's paperwork order is worse than leaving it empty.
                    if sch.offer_required == "yes":
                        d.depends_on = [_OFFER_LETTER]
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
        checklist.recommender_actions = [
            d for d in everything if d.owner == DocumentOwner.RECOMMENDER
        ]
        checklist.certification_actions = [
            d for d in everything if d.owner == DocumentOwner.THIRD_PARTY
        ]
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
        self,
        candidate: Candidate,
        program: CandidateProgram,
        url: str | None,
        purpose: DocumentPurpose,
        out: AdapterResult,
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
        # Read once and given to both: the claims and the checklist rows from
        # this page describe the same population, and §9 asks the checklist to
        # store it too.
        page_scope = read_scope(text, title=html_title(res.text))
        builder = ClaimBuilder(
            source_url=url,
            page_title=html_title(res.text),
            specificity=SourceSpecificity.PROGRAM_INTAKE,
            program=program.name,
            academic_year=self.academic_year,
            official_domain=url.startswith("fixture://")
            or is_official_domain(url, [candidate.domain]),
            extraction_method="fixture" if url.startswith("fixture://") else "html_rule",
            accessed_at=res.fetched_at,
            scope=page_scope,
            page_text=text,
            allowed_domains=verification_domains(url, candidate.domain),
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
                    name=name,
                    purpose=purpose,
                    owner=owner,
                    format_notes=", ".join(sorted(set(_FORMAT.findall(line)))) or "",
                    max_pages=int(pages.group(1)) if pages else None,
                    max_file_size_mb=float(size.group(1)) if size else None,
                    word_limit=int(words.group(1) or words.group(2)) if words else None,
                    prompt_text=line.strip()[:280]
                    if purpose == DocumentPurpose.SCHOLARSHIP
                    else None,
                    source_url=url,
                    claim_ids=[url],
                    scope=page_scope,
                    **flags,
                )
                items.append(item)
                builder.add(ClaimType.REQUIRED_DOCUMENT, name, line.strip()[:300], confidence=0.75)
                if item.word_limit:
                    builder.add(
                        ClaimType.ESSAY_PROMPT,
                        {"document": name, "word_limit": item.word_limit},
                        line.strip()[:300],
                        confidence=0.8,
                    )
                if owner == DocumentOwner.RECOMMENDER:
                    builder.add(
                        ClaimType.RECOMMENDATION_REQUIREMENT,
                        name,
                        line.strip()[:300],
                        confidence=0.75,
                    )
                break
        out.claims.extend(builder.claims)
        return items


def _order_steps(items: list[DocumentItem]) -> list[str]:
    """Prerequisites first, then longest lead time — in that order of priority.

    Lead time alone used to decide, and §9's own dependencies were ignored, so
    the numbered plan could say "notarize the translation" above "get the
    translation". A numbered list is an instruction, and an impossible one is
    worse than none.
    """
    ordered = _dependency_order(items)
    steps = []
    for i, d in enumerate(ordered, 1):
        lead = f" (allow ~{d.lead_time_days} days)" if d.lead_time_days else ""
        who = {
            DocumentOwner.APPLICANT: "You",
            DocumentOwner.SCHOOL: "Your school",
            DocumentOwner.RECOMMENDER: "Your referee",
            DocumentOwner.THIRD_PARTY: "A third party",
        }[d.owner]
        # Every dependency is said, including one naming something that is
        # not itself a list item: the offer letter is a real milestone, not a
        # document the university asks for, and an applicant who is not told
        # to wait for it will not wait for it.
        after = f" — after {', '.join(d.depends_on)}" if d.depends_on else ""
        steps.append(f"{i}. {who}: {d.name}{lead}{after}")
    return steps


def _named_prerequisites(item: DocumentItem, present: set[str]) -> list[str]:
    """The dependencies that name another step on this list — the orderable ones.

    A dependency on something the list does not contain cannot order anything,
    so it is left out *here* and still printed beside the step. Dropping it
    from the ordering keeps a real prerequisite from stalling the whole plan;
    dropping it from the text would hide it.
    """
    return [name for name in item.depends_on if name in present and name != item.name]


def _dependency_order(items: list[DocumentItem]) -> list[DocumentItem]:
    """Topological order, longest lead time first among what is ready.

    A cycle is never silently reordered: its members are appended last, in the
    same lead-time order, so the list stays complete and the ordering claim is
    not made for steps that cannot honestly carry one.
    """
    by_lead = sorted(items, key=lambda d: -(d.lead_time_days or 0))
    present = {d.name for d in items}
    waiting = {d.name: set(_named_prerequisites(d, present)) for d in by_lead}

    out: list[DocumentItem] = []
    done: set[str] = set()
    remaining = list(by_lead)
    while remaining:
        ready = [d for d in remaining if waiting[d.name] <= done]
        if not ready:
            # Everything left is in, or behind, a cycle.
            out.extend(remaining)
            break
        out.extend(ready)
        done.update(d.name for d in ready)
        remaining = [d for d in remaining if d.name not in done]
    return out
