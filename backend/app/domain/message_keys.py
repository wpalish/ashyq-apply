"""Stable keys for the English sentences the backend writes to an applicant (gap B6).

The interface offers Russian and Kazakh, but open questions, funding outcomes
and stale reasons are composed here, in English, and stored that way. Changing
what is stored would move every saved run and the golden demo hash, so the
English stays exactly as it is. Instead each sentence is *recognised* when a
result is served: a template below matches it, and the result carries a
:class:`MessageRef` (key + parameters) beside the English. The interface looks
the key up in its ru/kk catalogue and fills the parameters in.

Recognising rather than emitting keys has one honest failure mode, and it is
the safe one: a sentence whose wording changed and whose template was not
updated gets no key, and the applicant reads the English, unchanged. Nothing is
ever shown in another language that the English does not say.

Every template's English text is mirrored in
``frontend/src/lib/i18n.results.ts`` under ``msg.<key>``; a test keeps the
two in step.

Pure: no I/O, no adapters.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.schemas.claim import ClaimOut, MessageRef, UnresolvedQuestion
from app.schemas.result import FundingGap, ProgramResult

_PLACEHOLDER = re.compile(r"\\\{(\w+)\\\}")


@dataclass(frozen=True)
class Template:
    """One English sentence with ``{name}`` placeholders, and its key."""

    key: str
    text: str

    @property
    def pattern(self) -> re.Pattern[str]:
        return _compiled(self.text)

    def match(self, text: str) -> MessageRef | None:
        found = self.pattern.fullmatch(text.strip())
        if found is None:
            return None
        return MessageRef(key=self.key, params=dict(found.groupdict()))


_CACHE: dict[str, re.Pattern[str]] = {}


def _compiled(text: str) -> re.Pattern[str]:
    if text not in _CACHE:
        _CACHE[text] = re.compile(_PLACEHOLDER.sub(r"(?P<\1>.+?)", re.escape(text)), re.DOTALL)
    return _CACHE[text]


def _t(key: str, text: str) -> Template:
    return Template(key, text)


# --- open questions: the question ------------------------------------------

QUESTIONS: tuple[Template, ...] = (
    _t(
        "question.campus",
        "{university} offers {programme} on more than one campus, each a separate "
        "application. Which campus do you want?",
    ),
    _t(
        "question.entryRequirementsPage",
        "Which official page publishes entry requirements for {programme}?",
    ),
    _t("question.programmePage", "Which official page publishes the {programme} programme?"),
    _t(
        "question.noVerifiedDataInScope",
        "No verified data yet for {university}: the bachelor's in Computer Science.",
    ),
    _t(
        "question.noVerifiedDataOutOfScope",
        "No verified data yet for {university}: this programme (the knowledge base covers "
        "only the bachelor's in Computer Science).",
    ),
    _t("question.supportForUncovered", "Is there any support for {categories} alongside {award}?"),
    _t("question.coop", "Does {programme} offer a co-op or placement year?"),
    _t(
        "question.workHours",
        "How many hours a week may an international student work while studying in {country}?",
    ),
    _t("question.researchGroups", "Which groups at {university} work on {interest}?"),
    _t(
        "question.scholarshipsOpen",
        "What scholarships are open to international students on {programme}?",
    ),
    _t(
        "question.fundingPage",
        "Which official page publishes funding for {programme} at {university}?",
    ),
    _t(
        "question.pageScope",
        "Does {url} also apply to {programme} for the intake you are applying to? It is the "
        "only page we found stating this, and it {reason}.",
    ),
    _t(
        "question.previousCycleDeadline",
        "{url} states {value} as the deadline, which belongs to an earlier cycle than "
        "{intake}. When is the deadline for your intake?",
    ),
    _t(
        "question.satForAward",
        "{programme} is published as test-optional, but {award} requires an SAT score. Does "
        "the award's requirement still apply to applicants admitted without a test?",
    ),
    _t("question.documents", "What documents does {university} require for {programme}?"),
    _t(
        "question.awardStillOffered",
        "Is {award} still offered, and open to international applicants, for the {intake} intake?",
    ),
    _t(
        "question.confirmOnOfficialPage",
        "Confirm {field} on an official university page (current value {value} came from a "
        "non-official source).",
    ),
    _t(
        "question.nomination",
        "How are candidates nominated for '{award}', and is any action required from the "
        "applicant?",
    ),
    _t(
        "question.documentList",
        "What is the full list of required documents for {programme}?",
    ),
    _t(
        "question.kbScholarships",
        "Which scholarships does {university} offer international students on {programme}?",
    ),
    _t(
        "question.kbEntryRequirements",
        "Which entry requirements does {university} publish for {programme}, and does your "
        "profile meet them?",
    ),
    _t(
        "question.languageInstead",
        "{statement} Which language certificate does {university} require instead, and do you "
        "hold it?",
    ),
    _t(
        "question.gradesInstead",
        "{statement} Which grades or scores does {university} use instead, and does your record "
        "meet them?",
    ),
    _t("question.requireInstead", "{statement} What does {university} require instead?"),
    _t(
        "question.languageNoneRecorded",
        "{statement} Does {university} ask for any other language evidence? The verified "
        "knowledge base names none.",
    ),
    _t(
        "question.documentListCurrent",
        "Is the document list for {programme} at {university} still the one for the {intake} "
        "intake?",
    ),
)

# --- open questions: why it matters ----------------------------------------

WHYS: tuple[Template, ...] = (
    _t(
        "why.campus",
        "Requirements, fees and deadlines can differ by campus. What was read on the "
        "{campuses} pages is not shown as this programme's.",
    ),
    _t(
        "why.catalogueOnly",
        "This university was found through a catalogue only. Nothing about it has been "
        "verified against an official source.",
    ),
    _t(
        "why.programmePageUnverified",
        "The facts shown for this university were verified on its official site, but the "
        "verified knowledge base has no verified page for this programme yet, so that the "
        "programme is offered for this intake is not confirmed.",
    ),
    _t(
        "why.noKbEntry",
        "Live research is switched off and this university has no entry in the verified "
        "knowledge base, so nothing about it is shown or guessed. Its official site or "
        "admissions office is the source until it is added.",
    ),
    _t(
        "why.kbOutOfScope",
        "Live research is switched off and the verified knowledge base answers only for the "
        "bachelor's in Computer Science, so nothing about this programme is shown or guessed. "
        "Its official site or admissions office is the source until it is added.",
    ),
    _t(
        "why.uncoveredCosts",
        "The profile lists {categories} as costs that must be covered, and this award "
        "excludes them. The gap is real money the family would have to find.",
    ),
    _t(
        "why.coop",
        "The profile says co-op programmes matter. Nothing on the pages read states whether "
        "this programme has one.",
    ),
    _t(
        "why.workHours",
        "The profile says work during study is necessary, and no official statement of the "
        "limit was found.",
    ),
    _t(
        "why.researchInterest",
        "The profile lists {interest} as a research interest. The pages read do not mention "
        "it, which is not the same as it being absent.",
    ),
    _t(
        "why.noFundingPage",
        "No official funding page could be read, so funding is unknown, not absent.",
    ),
    _t(
        "why.unmatchedFunding",
        "This programme could not be matched back to a discovered university, so no "
        "scholarship page was read for it. Nothing here is assumed.",
    ),
    _t(
        "why.pageScope",
        "The page was read correctly, but it states it is about something else, so nothing "
        "here is claimed from it. An admissions office can confirm in one reply whether the "
        "same rule applies to your intake.",
    ),
    _t(
        "why.previousCycleDeadline",
        "The page has not yet published the dates for your intake; the previous cycle's date "
        "is shown only as a guide.",
    ),
    _t(
        "why.satForAward",
        "Skipping the SAT on the strength of the admissions page can cost this award rather "
        "than the offer, and the two pages are published by different offices.",
    ),
    _t(
        "why.unmatchedDocuments",
        "This approved programme could not be matched back to a discovered university, so its "
        "document list was never read.",
    ),
    _t(
        "why.kbNoDocuments",
        "The verified knowledge base does not hold document lists yet, and live research is "
        "switched off, so nothing was read or assumed.",
    ),
    _t(
        "why.awardStale",
        "What the verified knowledge base holds about this award is stale ({reasons}), so it "
        "is not shown as current and does not count as funding until the scholarships office "
        "confirms it.",
    ),
    _t("why.aggregator", "Aggregator data is frequently out of date for this field."),
    _t(
        "why.nomination",
        "A nomination-only award cannot be applied for directly; missing the internal process "
        "means missing the award entirely.",
    ),
    _t(
        "why.noDocumentList",
        "No official document list could be read, so nothing can be prepared in advance.",
    ),
    _t(
        "why.kbNoAward",
        "The verified knowledge base names no award for this programme, and live research is "
        "switched off, so no scholarship page was read. Funding is unknown, not confirmed "
        "absent.",
    ),
    _t(
        "why.kbRequirementsUnsettled",
        "The verified knowledge base holds facts for this programme, but its {requirements} "
        "could not be settled from them, so eligibility is shown as needing clarification "
        "rather than as met.",
    ),
    _t(
        "why.kbNoComparableRequirement",
        "The verified knowledge base holds facts for this programme, but none of them is an "
        "entry requirement this profile can be compared against, so eligibility is shown as "
        "needing clarification rather than as met.",
    ),
    _t(
        "why.verifiedStatement",
        'Verified on the official page {url}: "{quote}". The profile has no field this can be '
        "compared against, so it is not counted as met or as failed.",
    ),
    _t(
        "why.documentsNotCurrent",
        "The verified knowledge base holds these documents, but not as current: {documents}. "
        "They are listed so you can prepare, not as confirmed.",
    ),
)

# --- why a fact is stale (the "Stale, not current:" sentence in claim notes) --
# Computed by ``app.knowledge.stale_reasons`` (the first five), or written by
# the KB build and carried (``evaluation/research/expert/kb_build.py``: a fee
# for another or no stated year, a 2026-cycle date, a document list for
# another cycle). ``{cycle}`` is the page's own words and stays as printed.

STALE_REASONS: tuple[Template, ...] = (
    _t("stale.noDate", "no verification date"),
    _t("stale.tooOld", "verified on {date}, more than {days} days ago"),
    _t("stale.yearBeforeIntake", "academic year {year} is before the {intake} intake's {wanted}"),
    _t("stale.yearPast", "academic year {year} is past"),
    _t("stale.deadlinePassed", "deadline {date} has passed"),
    _t("stale.publishedForYear", "published for academic year {year}"),
    _t("stale.yearNotStated", "the academic year is not stated"),
    _t("stale.publishedForCycle", "published for the {year} cycle"),
    _t(
        "stale.documentsForCycle",
        'document list published for "{cycle}", not the {intake} intake',
    ),
    _t(
        "stale.documentsAnotherCycle",
        "document list published for another cycle, not the {intake} intake",
    ),
)

#: One stale item in the documents question's ``{documents}`` list:
#: ``app.knowledge.documents.kb_checklist`` writes "Passport (reason, reason)".
DOCUMENT_ITEMS: tuple[Template, ...] = (_t("stale.documentItem", "{document} ({reasons})"),)

# --- funding: the remaining-cost reason, warnings and the funding outcome ----

FUNDING: tuple[Template, ...] = (
    _t(
        "gap.mixedYears",
        "Published cost components come from different academic years ({years}). They are "
        "not summed, because a mixed-year total would misstate the real cost.",
    ),
    _t("gap.noCost", "No official cost of attendance was found for this programme and intake."),
    _t(
        "gap.partialCost",
        "Only part of the core cost of attendance is published, so the full annual cost is "
        "unknown and no remaining-cost figure is computed.",
    ),
    _t(
        "gap.noAwardAmount",
        "Cost of attendance is known, but no scholarship with an officially published amount "
        "was found, so the remaining cost cannot be estimated.",
    ),
    _t(
        "gap.zeroNotComparable",
        "The arithmetic reaches zero, but the cost and coverage figures are not comparable, "
        "so a zero remaining cost would be misleading.",
    ),
    _t("gap.computed", "Remaining annual cost after officially published, applicable aid."),
    _t("gap.recheckSingleYear", "Re-check the cost pages for a single academic year."),
    _t("gap.costUnverified", "Cost pages could not be verified; the gap cannot be estimated."),
    _t(
        "gap.needBasedExcluded",
        "A need-based award was found but cannot be sized before a need assessment is filed; "
        "it is excluded from this calculation.",
    ),
    _t(
        "gap.awardNoAmount",
        "'{award}': no officially published amount, excluded from the arithmetic.",
    ),
    _t(
        "gap.notItemised",
        "The cost table does not itemise {categories}; the figure shown is the known "
        "subtotal, a lower bound on the real cost of attendance.",
    ),
    _t(
        "gap.notStackable",
        "'{award}' states it may not be combined with other awards, so other scholarships are "
        "not added on top even where they permit stacking.",
    ),
    _t(
        "gap.yearMismatch",
        "Cost is published for {costYear} but the award amount for {awardYear}. The figures "
        "below are not directly comparable.",
    ),
    _t(
        "gap.coverageIncomplete",
        "Award coverage does not name every cost category the university publishes: {categories}",
    ),
    _t("gap.costRange", "Cost of attendance is published as a range; the gap is shown as a range."),
    _t(
        "gap.aidExceedsCost",
        "Confirmed aid exceeds the published cost of attendance. The surplus is not assumed "
        "to be paid out; the remaining cost is reported as zero.",
    ),
    _t(
        "funding.noInformation",
        "No scholarship information was found on official sources for this programme.",
    ),
    _t(
        "funding.allExclude",
        "Every scholarship found for this programme officially excludes this applicant.",
    ),
    _t(
        "funding.wrongShape",
        "Awards were found, but none is the kind of funding this profile says it needs; each "
        "says why on its own row.",
    ),
    _t(
        "funding.coverageUnclear",
        "Scholarships exist but official coverage detail is insufficient to classify them.",
    ),
    _t(
        "funding.needBased",
        "Support depends on a financial-need assessment that cannot be evaluated in advance.",
    ),
    _t(
        "funding.automatic",
        "'{award}' is awarded automatically on the admission application against published "
        "criteria; the award decision still depends on the university.",
    ),
    _t(
        "funding.nomination",
        "'{award}' requires a departmental nomination, so it cannot be applied for directly.",
    ),
    _t(
        "funding.competitive",
        "'{award}' is open to this applicant by published criteria and is awarded by "
        "competitive selection.",
    ),
    _t(
        "funding.limited",
        "The strongest confirmed option, '{award}', covers only a limited share of cost.",
    ),
    _t(
        "funding.noneOffered",
        "No institutional scholarship: {university} states that it offers none for this "
        'applicant ("{quote}", {url}).',
    ),
    _t(
        "funding.noneStale",
        "No institutional scholarship was stated by {university}, but the statement is stale "
        "({reasons}), so funding is unknown, not confirmed absent.",
    ),
    _t(
        "gap.feeOtherYear",
        "An official tuition fee was found, but for another academic year than the {intake} "
        "intake: {fees}. It is not used as this intake's cost, so the remaining cost is not "
        "computed.",
    ),
    _t(
        "gap.feeNotYearly",
        "An official tuition fee was found, but not as a current yearly figure for the "
        "{intake} intake: {fees}. It is not used as this intake's cost, so the remaining cost "
        "is not computed.",
    ),
    _t(
        "gap.kbNoFee",
        "The verified knowledge base holds no tuition fee for this programme yet, so the "
        "remaining cost is not computed.",
    ),
    _t(
        "gap.kbTuitionRange",
        "Tuition is published only as a range, {range}; the cost uses its upper bound, so it "
        "is not understated.",
    ),
    _t(
        "gap.confirmIntakeFee",
        "Confirm the {intake} fee with the university before relying on a cost figure.",
    ),
)

# --- why a current KB fact is not fully verified (the "Caveat:" sentence) ----
# Mirrors ``app.knowledge.YEAR_INFERRED_CAVEAT`` / ``STANDING_FEE_POLICY_CAVEAT``.

CAVEATS: tuple[Template, ...] = (
    _t("caveat.yearInferred", "year not printed on the page; assumed current application cycle"),
    _t("caveat.feePolicy", "fee policy page; no academic year printed"),
)

CATALOGUE: tuple[Template, ...] = (
    QUESTIONS + WHYS + STALE_REASONS + DOCUMENT_ITEMS + FUNDING + CAVEATS
)

_STALE_MARK = "Stale, not current: "
#: ``app.knowledge.CAVEAT_MARK``: a caveat never holds a full stop.
_CAVEAT = re.compile(r"(?:^|\s)Caveat: ([^.]+)\.")


def caveat_of(notes: str) -> str | None:
    """The caveat a KB claim's notes carry ("Caveat: …."), or None."""
    found = _CAVEAT.search(notes or "")
    return found.group(1).strip() if found else None


def match(templates: tuple[Template, ...], text: str) -> MessageRef | None:
    """The first template that matches all of ``text``, or None."""
    for template in templates:
        ref = template.match(text)
        if ref is not None:
            return _with_parts(ref)
    return None


def _with_parts(ref: MessageRef) -> MessageRef:
    """Key the stale reasons inside a ``{reasons}`` parameter (one per reason)
    and the stale items inside a ``{documents}`` parameter (one per document)."""
    reasons = ref.params.get("reasons")
    if reasons:
        ref.parts["reasons"] = [stale_reason_message(r) for r in reasons.split("; ")]
    documents = ref.params.get("documents")
    if documents:
        ref.parts["documents"] = [_document_item(d) for d in documents.split("; ")]
    return ref


def stale_reason_message(reason: str) -> MessageRef | None:
    """The key and parameters of one stored English stale reason; None for an unknown shape.

    Read from the English as stored, so neither the committed KB nor a saved
    claim needs a rebuild: a reason no template knows keeps its English.
    """
    return match(STALE_REASONS, reason)


def _split_reasons(text: str, sep: str) -> list[MessageRef] | None:
    """``text`` cut at ``sep`` into recognised reasons; None when no cut is all recognised.

    A reason can itself hold ``sep`` ("verified on …, more than 365 days ago", a
    quoted cycle with a comma), so the pieces are regrouped, and the cut with
    the most reasons, every one recognised, wins.
    """
    pieces = text.split(sep)
    best: list[list[MessageRef] | None] = [[]] + [None] * len(pieces)
    for end in range(1, len(pieces) + 1):
        for start in range(end):
            before = best[start]
            if before is None:
                continue
            ref = stale_reason_message(sep.join(pieces[start:end]))
            current = best[end]
            if ref is not None and (current is None or len(before) + 1 > len(current)):
                best[end] = [*before, ref]
    return best[-1]


def _document_item(text: str) -> MessageRef | None:
    """One "Name (reason, reason)" item of the stale documents list, keyed; None if unknown."""
    if not text.endswith(")"):
        return None
    for found in re.finditer(r" \(", text):
        document, inner = text[: found.start()], text[found.end() : -1]
        reasons = _split_reasons(inner, ", ") if document else None
        if reasons:
            return MessageRef(
                key="stale.documentItem",
                params={"document": document, "reasons": inner},
                parts={"reasons": list(reasons)},
            )
    return None


def stale_reasons(notes: str) -> list[MessageRef | None] | None:
    """The keyed reasons of a claim's "Stale, not current: …" sentence; None if it has none."""
    at = notes.find(_STALE_MARK)
    if at < 0:
        return None
    text = notes[at + len(_STALE_MARK) :].strip().removesuffix(".")
    if not text:
        return None
    return [stale_reason_message(reason) for reason in text.split("; ")]


def annotate_question(question: UnresolvedQuestion) -> None:
    question.question_message = match(QUESTIONS, question.question)
    question.why_message = match(WHYS, question.why_it_matters)


def annotate_claim(claim: ClaimOut) -> None:
    claim.stale_messages = stale_reasons(claim.notes)
    caveat = caveat_of(claim.notes)
    claim.caveat_message = match(CAVEATS, caveat) if caveat else None


def annotate_gap(gap: FundingGap) -> None:
    gap.reason_message = match(FUNDING, gap.reason) if gap.reason else None
    gap.warning_messages = [match(FUNDING, w) for w in gap.warnings]


def annotate_result(result: ProgramResult) -> ProgramResult:
    """Attach message keys to a result about to be served; returns it for chaining.

    Call it on the object the API returns, never on one about to be stored.
    """
    for question in result.unresolved:
        annotate_question(question)
    for claim in result.claims:
        annotate_claim(claim)
    if result.funding_gap is not None:
        annotate_gap(result.funding_gap)
    if result.checklist is not None:
        for question in result.checklist.unresolved:
            annotate_question(question)
    return result
