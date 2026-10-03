"""Building the document checklist for an approved programme.

Runs only after the applicant approves a row, because it is the expensive
stage. It separates what the applicant sends from what the school and the
referees must send, since those have different lead times and are the usual
cause of a missed deadline.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import replace
from datetime import UTC, datetime

from app.adapters.base import AdapterResult, Candidate, CandidateProgram, PageOutcome
from app.adapters.document_ir import DocumentIR, build_document_ir
from app.adapters.documents.structured_documents import read_supplemental_tables
from app.adapters.extraction import (
    ClaimBuilder,
    html_title,
    html_to_text,
    is_official_domain,
    verification_domains,
)
from app.adapters.fetching import Fetcher, same_source_site
from app.adapters.scope_reader import read_scope
from app.domain.claim_scope import ClaimScope
from app.domain.enums import ClaimType, DocumentOwner, DocumentPurpose, SourceSpecificity
from app.schemas.claim import MAX_EXCERPT_CHARS, UnresolvedQuestion
from app.schemas.result import DocumentChecklist, DocumentItem, Scholarship

DOCUMENT_CLAIM_TYPES = frozenset(
    {
        ClaimType.REQUIRED_DOCUMENT,
        ClaimType.ESSAY_PROMPT,
        ClaimType.RECOMMENDATION_REQUIREMENT,
        ClaimType.DOCUMENT_BY_COMPLETION,
    }
)

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
    (
        "passport-size photo",
        "Passport-size photograph (digital image)",
        DocumentOwner.APPLICANT,
        {"lead_time_days": 1},
    ),
    ("passport", "Passport identity page (copy)", DocumentOwner.APPLICANT, {"lead_time_days": 1}),
    ("personal essay", "Personal Essay", DocumentOwner.APPLICANT, {"lead_time_days": 14}),
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
    ("referee's appraisal", "Referee appraisal", DocumentOwner.RECOMMENDER, {"lead_time_days": 30}),
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

_WORDS = re.compile(
    r"(?:maximum|not more than) (\d{2,4}) words|(\d{2,4})[- ]word (?:limit|maximum)",
    re.IGNORECASE,
)
_PAGES = re.compile(r"maximum (\d{1,2}) pages?", re.IGNORECASE)
_SIZE = re.compile(r"max(?:imum)? (\d{1,3})\s*MB", re.IGNORECASE)
_FORMAT = re.compile(r"\b(PDF|DOCX?|JPE?G|PNG)\b")
_DOCUMENT_LIST = re.compile(
    r"^(?:(?:required|supporting|application)\s+)?documents(?:\s+(?:required|checklist|to submit))?$",
    re.I,
)
_OPTIONAL_DOCUMENT = re.compile(
    r"\boptional(?:ly)?\b|\bnot\s+(?:required|mandatory|compulsory)\b|"
    r"\b(?:do|does|need)\s+not\s+(?:submit|upload|provide|attach)\b",
    re.I,
)
_DOCUMENT_ACTION = re.compile(
    r"^(?:please\s+)?(?:submit|upload|provide|attach)\b|"
    r"\b(?:must|are required to|is required to|need to)\s+(?:submit|upload|provide|attach)\b|"
    r"\b(?:submit|upload|provide|attach)[^.!?]{0,100}\b(?:required|mandatory)\b",
    re.I,
)
_REQUIRED_WORD = re.compile(r"\b(?:required|mandatory|compulsory)\b", re.I)
_QUALIFICATION_WORD = re.compile(r"\b(?:possess|hold|qualifications?|achievements?)\b", re.I)


def _document_statements(text: str, document: DocumentIR | None) -> Iterator[tuple[str, bool, str]]:
    """Local complete clauses, with an explicit document-list context only.

    A long application paragraph can contain a short required essay or
    appraisal statement. Splitting at sentence boundaries preserves its whole
    proof; it never clips a requirement to fit the claim's quote cap.
    """
    if document is None or not document.blocks:
        # Plain-text responses retain their explicit one-line reader.
        for line in text.splitlines():
            if line.strip() and len(line) <= 300:
                yield line.strip(), True, line.strip()
        return
    for block in document.blocks:
        if block.kind not in {"paragraph", "list_item", "key_value", "table_cell"}:
            continue
        listed = block.kind in {"list_item", "table_cell", "key_value"} and any(
            _DOCUMENT_LIST.fullmatch(heading) for heading in block.section_path
        )
        clauses = re.split(r"(?<=[.!?])\s+", block.text)
        for i, clause in enumerate(clauses):
            if "referee's appraisal" in clause.casefold() and i + 1 < len(clauses):
                following = clauses[i + 1]
                if following.casefold().startswith("the appraisal"):
                    clause += " " + following
            if clause and len(clause) <= MAX_EXCERPT_CHARS:
                yield clause, listed, " ".join([*block.section_path, *block.row_headers, clause])


def _required_document_statement(line: str, listed: bool) -> bool:
    if _OPTIONAL_DOCUMENT.search(line):
        return False
    return bool(
        listed
        or _DOCUMENT_ACTION.search(line)
        or (_REQUIRED_WORD.search(line) and not _QUALIFICATION_WORD.search(line))
    )


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
        _populate_actions(checklist)

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
            out.page_outcomes.append(PageOutcome(url, "fetch-failed"))
            return []

        source_url = res.final_url or url
        if not same_source_site(url, source_url):
            out.pages_failed += 1
            out.errors.append(f"{url}: document source redirected outside the institution")
            out.page_outcomes.append(
                PageOutcome(url, "classifier-rejected", detail="cross-site redirect")
            )
            return []

        text = html_to_text(res.text)
        if not text.strip():
            out.pages_failed += 1
            out.errors.append(f"{url}: unreadable — empty response after extracting document text.")
            out.retry_urls.append(url)
            out.page_outcomes.append(PageOutcome(url, "unreadable"))
            return []
        # Read page scope once; the reader narrows population to each document
        # statement and gives claims and checklist rows the same local scope.
        page_scope = read_scope(text, title=html_title(res.text))
        builder = ClaimBuilder(
            source_url=source_url,
            page_title=html_title(res.text),
            specificity=SourceSpecificity.PROGRAM_INTAKE,
            program=program.name,
            academic_year=self.academic_year,
            official_domain=source_url.startswith("fixture://")
            or is_official_domain(source_url, [candidate.domain]),
            extraction_method="fixture" if source_url.startswith("fixture://") else "html_rule",
            accessed_at=res.fetched_at,
            scope=page_scope,
            page_text=text,
            allowed_domains=verification_domains(source_url, candidate.domain),
        )

        items = read_documents(
            text,
            source_url,
            purpose,
            page_scope,
            builder,
            document=build_document_ir(res.text, source_url),
        )
        out.claims.extend(builder.claims)
        out.page_outcomes.append(
            PageOutcome(
                url,
                "fetched-ok" if builder.claims else "no-pattern-match",
                readable_chars=len(text),
            )
        )
        return items


#: A document whose form depends on whether schooling is finished, stated on
#: one line: "Transcript: scan of your academic record and/or if not yet
#: completed: school-issued list of your courses" (Groningen, 2026-09-28).
_BY_COMPLETION = re.compile(
    r"^(?P<label>transcripts?|(?:secondary\s+school\s+)?diplomas?)\b(?P<done>.*?)"
    r"(?:and/?or|or)?\s*if\s+(?:you\s+have\s+)?not\s+yet\s+(?:completed|finished|graduated)"
    r"\s*[:,]?\s*(?P<pending>.+)$",
    re.I,
)
_LABEL_DOCUMENT = (
    (re.compile(r"transcript", re.I), "Full academic transcript"),
    (re.compile(r"diploma", re.I), "Secondary school diploma (certified copy)"),
)
_COMPLETION_LABEL = re.compile(r"transcripts?|(?:secondary\s+school\s+)?diplomas?", re.I)
#: The forms a document takes, in the page's words, to one vocabulary.
_FORMS = (
    (
        re.compile(r"academic record|final grade list|report card|grade transcript", re.I),
        "academic_record",
    ),
    (re.compile(r"list of (?:your )?courses|course list", re.I), "school_course_list"),
    (
        re.compile(
            r"(?:statement|proof|certificate) of enrol?ment|enrol?ment (?:statement|certificate)",
            re.I,
        ),
        "school_enrolment_statement",
    ),
    (re.compile(r"\bdiploma\b", re.I), "diploma"),
)


def _form_of(words: str) -> str | None:
    return next((form for pattern, form in _FORMS if pattern.search(words)), None)


def _completion_forms(text: str, builder: ClaimBuilder) -> None:
    """Each document the page names in a completed and a not-yet-completed form.

    Both forms must be recognised; a half-read line says nothing.
    """
    for line in text.splitlines():
        match = _BY_COMPLETION.match(line.strip())
        if match is None:
            continue
        _add_completion_forms(match, builder, line.strip()[:300])


def _add_completion_forms(
    match: re.Match[str], builder: ClaimBuilder, excerpt: str, section: str = ""
) -> None:
    name = next((n for p, n in _LABEL_DOCUMENT if p.search(match.group("label"))), None)
    done, pending = _form_of(match.group("done")), _form_of(match.group("pending"))
    if name is None or done is None or pending is None or done == pending:
        return
    for status, form in (("completed", done), ("not_completed", pending)):
        builder.add(
            ClaimType.DOCUMENT_BY_COMPLETION,
            {"document": name, "status": status, "form": form},
            excerpt,
            section=section,
            confidence=0.75,
        )


def _structured_completion_forms(document: DocumentIR, builder: ClaimBuilder) -> None:
    """An explicit label and one block containing both forms; no text windows."""
    page_scope = builder.meta.get("scope")
    try:
        for block in document.blocks:
            if block.kind not in {"table_cell", "key_value", "paragraph", "list_item"}:
                continue
            if len(block.text) > MAX_EXCERPT_CHARS:
                continue
            context = (
                block.row_headers
                if block.kind == "table_cell"
                else (block.label,)
                if block.kind == "key_value"
                else block.section_path[-1:]
            )
            labels = {label for label in context if _COMPLETION_LABEL.fullmatch(label)}
            if len(labels) > 1:
                continue
            match = _BY_COMPLETION.match(block.text)
            if match is not None and labels:
                labelled = next(iter(labels))
                labelled_name = next(n for p, n in _LABEL_DOCUMENT if p.search(labelled))
                own_name = next(n for p, n in _LABEL_DOCUMENT if p.search(match.group("label")))
                if labelled_name != own_name:
                    continue
            if match is None and labels:
                # The label is structural context, not part of the quoted body.
                match = _BY_COMPLETION.match(f"{next(iter(labels))} {block.text}")
            if match is None:
                continue
            if isinstance(page_scope, ClaimScope):
                local = read_scope(
                    " ".join([*block.section_path, block.caption, *block.row_headers])
                )
                builder.meta["scope"] = replace(page_scope, population=local.population)
            _add_completion_forms(
                match,
                builder,
                block.text,
                " / ".join([*block.section_path, *context]),
            )
    finally:
        builder.meta["scope"] = page_scope


def _referee_conditions(name: str, statement: str) -> str | dict[str, object]:
    """Keep explicit recommender constraints with the document they describe.

    A conditional instruction or a mention in a neighbouring clause cannot
    establish an unconditional role or family exclusion.
    """
    if re.search(r"\b(?:if|unless|when|except|may|might|optional)\b", statement, re.I):
        return name
    role = re.search(
        r"\b(?:appraisal|reference|recommendation) (?:is to|must) be completed by "
        r"(?:your |a |an )?(school teacher|university lecturer|professor)\b",
        statement,
        re.I,
    )
    if role is None:
        return name
    value: dict[str, object] = {"document": name, "role": role.group(1).lower().replace(" ", "_")}
    # The exclusion must qualify the same person, immediately after their role.
    if re.match(
        r",?\s+who must not be (?:your |a |any )?(?:family or relative|relative or family)\b",
        statement[role.end() :],
        re.I,
    ):
        value["family_or_relative_allowed"] = False
    return value


_TRANSLATION_EXCEPTION = re.compile(
    r"^(?:Note\s*:\s*|NB:\s*)?If (?:your|the) documents are not in "
    r"(?P<languages>[A-Za-z, ]+), (?:you (?:will )?need to upload the original documents "
    r"and translations|please also provide a translation(?: in [A-Za-z, ]+)?)\.$",
    re.I,
)
_LANGUAGE_NAMES = frozenset(
    {
        "English",
        "Dutch",
        "French",
        "German",
        "Spanish",
        "Italian",
        "Portuguese",
        "Chinese",
        "Japanese",
        "Korean",
    }
)


def _translation_exception(statement: str) -> list[str] | None:
    """Only a complete exception clause establishes the exempt languages."""
    match = _TRANSLATION_EXCEPTION.fullmatch(statement)
    if match is None:
        return None
    languages = [
        part.strip().title() for part in re.split(r",|\bor\b", match["languages"], flags=re.I)
    ]
    if not languages or any(language not in _LANGUAGE_NAMES for language in languages):
        return None
    if len(set(languages)) != len(languages):
        return None
    return languages


def read_documents(
    text: str,
    url: str,
    purpose: DocumentPurpose,
    page_scope,
    builder: ClaimBuilder,
    *,
    document: DocumentIR | None = None,
) -> list[DocumentItem]:
    """Checklist rows and document claims from one page's readable text.

    Pure: no fetch. The adapter and the evaluation oracle both call it.
    """
    items: list[DocumentItem] = []
    seen: set[str] = set()
    original_scope = builder.meta.get("scope")
    try:
        for line, listed, context in _document_statements(text, document):
            local_scope = (
                replace(page_scope, population=read_scope(context).population)
                if isinstance(page_scope, ClaimScope)
                else page_scope
            )
            builder.meta["scope"] = local_scope
            low = line.lower().strip()
            languages = _translation_exception(line)
            if languages is not None:
                name = "Translation of application documents"
                identity = name + ":" + ",".join(languages)
                if identity not in seen:
                    claim = builder.add(
                        ClaimType.REQUIRED_DOCUMENT,
                        {"document": name, "required_unless_language_in": languages},
                        line,
                        confidence=0.8,
                    )
                    if claim is not None:
                        seen.add(identity)
                        items.append(
                            DocumentItem(
                                name=f"Translation (if originals are not in {', '.join(languages)})",
                                purpose=purpose,
                                owner=DocumentOwner.APPLICANT,
                                needs_translation=True,
                                format_notes=line,
                                source_url=url,
                                claim_ids=[url],
                                scope=local_scope,
                            )
                        )
                continue
            # An unparsed condition must not become the generic, unconditional
            # certified-English-translation rule below.
            if "translation" in low and (
                re.search(r"\b(?:if|unless|when|except)\b", low)
                or not (_DOCUMENT_ACTION.search(line) or _REQUIRED_WORD.search(line))
            ):
                continue
            if not _required_document_statement(line, listed):
                continue
            for needle, name, owner, flags in _DOC_RULES:
                if needle not in low:
                    continue
                if name in seen:
                    # A repeated specific document must not fall through into a
                    # broader overlapping rule (photo -> passport identity copy).
                    break
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
                    scope=local_scope,
                    **flags,
                )
                claim = builder.add(ClaimType.REQUIRED_DOCUMENT, name, line, confidence=0.75)
                if claim is None:
                    continue
                seen.add(name)
                items.append(item)
                if item.word_limit:
                    builder.add(
                        ClaimType.ESSAY_PROMPT,
                        {"document": name, "word_limit": item.word_limit},
                        line,
                        confidence=0.8,
                    )
                if owner == DocumentOwner.RECOMMENDER:
                    builder.add(
                        ClaimType.RECOMMENDATION_REQUIREMENT,
                        _referee_conditions(name, line),
                        line,
                        confidence=0.75,
                    )
                break
    finally:
        builder.meta["scope"] = original_scope
    if document is not None:
        items.extend(read_supplemental_tables(document, builder, purpose))
    before_forms = len(builder.claims)
    if document is None or not document.blocks:
        # Fetcher also accepts plain text. With no structural blocks, preserve
        # the explicit one-line reader; never fall back across parsed blocks.
        _completion_forms(text, builder)
    else:
        _structured_completion_forms(document, builder)
    # A structural document label with both completion-dependent forms is
    # already source-backed evidence. Keep its checklist item even when the
    # body names the forms rather than repeating "Transcript" from the h3.
    for claim in builder.claims[before_forms:]:
        if claim.claim_type is not ClaimType.DOCUMENT_BY_COMPLETION:
            continue
        if _OPTIONAL_DOCUMENT.search(claim.original_text_excerpt):
            continue
        name = claim.normalized_value["document"]
        if name in seen:
            continue
        rule = next((rule for rule in _DOC_RULES if rule[1] == name), None)
        if rule is None:
            continue
        seen.add(name)
        items.append(
            DocumentItem(
                name=name,
                purpose=purpose,
                owner=rule[2],
                source_url=url,
                claim_ids=[url],
                scope=claim.scope,
                **rule[3],
            )
        )
    return items


def _populate_actions(checklist: DocumentChecklist) -> None:
    everything = checklist.admission_documents + checklist.scholarship_documents
    checklist.applicant_actions = [d for d in everything if d.owner == DocumentOwner.APPLICANT]
    checklist.school_actions = [d for d in everything if d.owner == DocumentOwner.SCHOOL]
    checklist.recommender_actions = [d for d in everything if d.owner == DocumentOwner.RECOMMENDER]
    checklist.certification_actions = [
        d for d in everything if d.owner == DocumentOwner.THIRD_PARTY
    ]
    checklist.ordered_steps = _order_steps(everything)


def retain_failed_documents(
    checklist: DocumentChecklist, previous: DocumentChecklist | None, failed_urls: set[str]
) -> None:
    """An unreadable source cannot withdraw its previously read checklist.

    Successful reads, including an empty document list, replace their old
    items normally. No claim or verification date is refreshed here.
    """
    if previous is None or not failed_urls:
        return
    retained = False
    for field in ("admission_documents", "scholarship_documents"):
        current: list[DocumentItem] = getattr(checklist, field)
        present = {item.model_dump_json() for item in current}
        for item in getattr(previous, field):
            identity = item.model_dump_json()
            if item.source_url in failed_urls and identity not in present:
                current.append(item)
                present.add(identity)
                retained = True
    if retained:
        checklist.completeness = "partial"
        _populate_actions(checklist)


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
