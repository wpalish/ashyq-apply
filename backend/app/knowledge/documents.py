"""Application documents from the verified knowledge base (kb mode).

A KB entry's ``documents`` question holds one fact per document the official
page lists for an international applicant: its kind (``DOCUMENT_KINDS``),
whether it is ``required``, ``optional`` or ``conditional`` (with the page's
condition), the verbatim quote and its URL. The build keeps only the items the
evidence check found on an official page; an item that is not quoted is not
there, and nothing is inferred.

The document stage turns those facts into the same ``DocumentChecklist`` a
live read builds (``app.adapters.documents.web_documents``): the live reader's
document names, owners and flags, the same action split and step order, and
one ``REQUIRED_DOCUMENT`` claim per item with the official quote. A stale fact
(``app.knowledge.stale_reasons``) stays on the list, says so, and makes the
checklist ``partial``. Nothing here touches the network.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from app.adapters.documents.web_documents import document_rule, populate_actions
from app.domain.enums import ClaimType, DocumentOwner, DocumentPurpose, SourceSpecificity
from app.knowledge import DOCUMENTS, KnowledgeEntry
from app.knowledge.claims import fact_claim, kb_today
from app.schemas.claim import Claim, UnresolvedQuestion
from app.schemas.result import DocumentChecklist, DocumentItem

#: KB document kind -> the name the live document reader gives that document.
#: Each name is one of the live reader's rules, so the owner and the flags
#: (translation, notarisation, apostille, lead time) are the live ones.
LIVE_KINDS: dict[str, str] = {
    "transcript": "Full academic transcript",
    "secondary_diploma": "Secondary school diploma (certified copy)",
    "translation": "Certified English translation of non-English documents",
    "apostille": "Apostille certification",
    "credential_evaluation": "Course-by-course credential evaluation (WES/ECE)",
    "passport": "Passport identity page (copy)",
    "photo": "Passport-size photograph (digital image)",
    "personal_statement": "Personal statement",
    "motivation_letter": "Statement of motivation",
    "essay": "Personal Essay",
    "recommendation_letter": "Letter of recommendation",
    "academic_reference": "Academic reference",
    "cv": "Curriculum vitae",
    "portfolio": "Portfolio",
    "financial_proof": "Proof of financial resources",
}
#: Kinds the live reader has no rule for: named and owned here, with no lead
#: time (a lead time would be a guess the page did not make).
EXTRA_KINDS: dict[str, tuple[str, DocumentOwner]] = {
    "english_test_report": ("English language test report", DocumentOwner.THIRD_PARTY),
    "entrance_test": ("Admission test result", DocumentOwner.THIRD_PARTY),
    "application_form": ("Application form", DocumentOwner.APPLICANT),
}
#: Every kind a draft may name. Anything else stays unknown in the build.
DOCUMENT_KINDS: frozenset[str] = frozenset((*LIVE_KINDS, *EXTRA_KINDS))
#: How an item applies, as the page states it.
REQUIREMENTS = ("required", "optional", "conditional")


def document_kind(kind: str) -> tuple[str, DocumentOwner, dict[str, Any]] | None:
    """(name, owner, checklist flags) of a KB document kind; None for an unknown kind."""
    if kind in LIVE_KINDS:
        name = LIVE_KINDS[kind]
        rule = document_rule(name)
        if rule is None:  # the live vocabulary lost a name: fail loudly in tests
            raise KeyError(f"live document reader has no rule named {name!r}")
        owner, flags = rule
        return name, owner, flags
    if kind in EXTRA_KINDS:
        name, owner = EXTRA_KINDS[kind]
        return name, owner, {}
    return None


def document_facts(entry: KnowledgeEntry) -> list[dict[str, Any]]:
    """The entry's document facts the checklist can use: a known kind, a URL and a quote."""
    out = []
    for fact in entry.facts.get(DOCUMENTS) or []:
        value = fact.get("value")
        if (
            isinstance(value, dict)
            and str(value.get("kind")) in DOCUMENT_KINDS
            and fact.get("source_url")
            and fact.get("quote")
        ):
            out.append(fact)
    return out


def _requirement_note(value: dict[str, Any]) -> tuple[str, str]:
    requirement = str(value.get("requirement") or "required")
    if requirement not in REQUIREMENTS:
        requirement = "required"
    condition = str(value.get("condition") or "").strip()
    if requirement == "optional":
        return requirement, "Optional, as published."
    if requirement == "conditional":
        return requirement, (
            f"Required only when: {condition}." if condition else "Conditional, as published."
        )
    return requirement, ""


def kb_checklist(
    entry: KnowledgeEntry,
    *,
    university: str,
    programme: str,
    intake: str,
    today: date | None = None,
) -> tuple[DocumentChecklist, list[Claim]] | None:
    """The document checklist and its claims from the KB; None when the KB holds no list.

    Built as ``WebDocumentsAdapter.collect`` builds one: admission documents
    with the live names, owners and flags, split by who acts and ordered. An
    optional or conditional item keeps ``required=False`` and says why in its
    notes. Completeness is ``official`` when every item is current and no
    drafted item failed the evidence check, else ``partial``.
    """
    facts = document_facts(entry)
    if not facts:
        return None
    day = today or kb_today()
    checklist = DocumentChecklist(
        result_id="",
        university=university,
        program=programme,
        generated_at=datetime.now(UTC),
    )
    claims: list[Claim] = []
    stale: list[tuple[str, list[str]]] = []
    seen: set[str] = set()
    for fact in facts:
        value = fact["value"]
        found = document_kind(str(value["kind"]))
        assert found is not None  # document_facts kept known kinds only
        name, owner, flags = found
        if name in seen:
            continue
        seen.add(name)
        requirement, note = _requirement_note(value)
        claim_value: Any = (
            name
            if requirement == "required"
            else {
                "document": name,
                "requirement": requirement,
                **({"condition": value["condition"]} if value.get("condition") else {}),
            }
        )
        claim, reasons = fact_claim(
            entry,
            fact,
            ClaimType.REQUIRED_DOCUMENT,
            claim_value,
            programme=programme,
            intake=intake,
            today=day,
            specificity=SourceSpecificity.UNIVERSITY_ADMISSIONS,
            note=note or None,
        )
        claims.append(claim)
        notes = [note] if note else []
        if reasons:
            stale.append((name, reasons))
            notes.append("Possibly outdated: " + "; ".join(reasons) + ".")
        checklist.admission_documents.append(
            DocumentItem(
                name=name,
                purpose=DocumentPurpose.ADMISSION,
                owner=owner,
                required=requirement == "required",
                format_notes=" ".join(notes),
                source_url=claim.source_url,
                claim_ids=[claim.source_url],
                scope=claim.scope,
                **flags,
            )
        )
    populate_actions(checklist)
    unverified = [
        u
        for u in entry.unknown
        if str(u.get("question")) == DOCUMENTS
        and str(u.get("key") or "").startswith(f"{DOCUMENTS}.")
        and str(u.get("key")) not in {str(f.get("key")) for f in facts}
    ]
    if stale:
        listed = "; ".join(f"{name} ({', '.join(reasons)})" for name, reasons in stale)
        checklist.unresolved.append(
            UnresolvedQuestion(
                topic="required documents",
                question=(
                    f"Is the document list for {programme} at {university} still the one for "
                    f"the {intake} intake?"
                ),
                why_it_matters=(
                    "The verified knowledge base holds these documents, but not as current: "
                    f"{listed}. They are listed so you can prepare, not as confirmed."
                ),
                university=university,
                program=programme,
                suggested_contact="admissions office",
                blocking=False,
            )
        )
    if unverified:
        checklist.unresolved.append(
            UnresolvedQuestion(
                topic="required documents",
                question=(f"Which other documents does {university} require for {programme}?"),
                why_it_matters=(
                    f"{len(unverified)} document item(s) drafted for the verified knowledge base "
                    "could not be confirmed word for word on an official page, so they are not "
                    "listed. The list shown may be incomplete."
                ),
                university=university,
                program=programme,
                suggested_contact="admissions office",
                blocking=False,
            )
        )
    checklist.completeness = "partial" if stale or unverified else "official"
    return checklist, claims
