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

I18N-2 extends the same recognition to the rest of the results screens:
requirement checks (label and explanation), an award's classification reason
(sentence by sentence, :func:`match_sentences`), the v2 ranking's axis reasons,
bucket reason, knock-outs and disclaimer, conflicts' subject and resolution
rule, the /questions endpoint's conflict "why", and the exchange-rate warning.
A parameter that is itself a keyed sentence (a requirement label inside an
explanation, an explanation inside a knock-out) is keyed again in
``MessageRef.parts`` (:data:`_PART_PARAMS`).

I18N-3 does the same for the Documents screen: a document's name when it is
one of the 18 document kinds, and the sentences of its ``format_notes``
(optional, conditional, "Possibly outdated" with the stale reasons inside).

Every template's English text is mirrored in
``frontend/src/lib/i18n.results.ts`` under ``msg.<key>``; a test keeps the
two in step.

Pure: no I/O, no adapters.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.schemas.claim import ClaimOut, Conflict, MessageRef, UnresolvedQuestion
from app.schemas.result import (
    DocumentChecklist,
    DocumentItem,
    FundingGap,
    ProgramResult,
    RankingV2,
    RequirementCheck,
    Scholarship,
)

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
        "question.programmeNotOffered",
        "{university} publishes no bachelor's in Computer Science (checked {date}).",
    ),
    _t(
        "question.programmeRelatedOnly",
        "No standalone bachelor's in Computer Science is published; the closest official route "
        "is {route} (official page: {url}). Does that route suit you?",
    ),
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
        "why.programmeNotOffered",
        "The closest official programme is {route} (official page: {url}).",
    ),
    _t(
        "why.programmeNotOfferedNoRoute",
        "The verified knowledge base records that no such programme is offered, so nothing is "
        "shown as this programme's.",
    ),
    _t(
        "why.programmeRelatedOnly",
        "The verified knowledge base records no standalone bachelor's in Computer Science at "
        "{university} (expert check {date}). Whether the closest route suits you is your "
        "decision.",
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

# --- what a research run reaches (``routes_meta.live_coverage``, RM-1) ------

COVERAGE: tuple[Template, ...] = (
    _t(
        "coverage.kb",
        "The verified knowledge base answers for {universities} of {total} catalogue "
        "universities (bachelor's in Computer Science). A university outside it, or another "
        "programme, gets 'No verified data yet'; no page is read during a run.",
    ),
    _t(
        "coverage.live",
        "Live mode searches {institutions} curated institutions in {countries} countries. "
        "Results depend on the selected fields and which official pages can be accessed. "
        "Missing or unverified evidence stays visible in the results.",
    ),
)

# --- I18N-2: requirement checks (``app.domain.eligibility``, ``runner._scholarship_eligibility``)

#: The ``requirement`` label of a check. Also a part of the sentences that name
#: it (``{label}``, ``{requirement}``), so ru and kk can say it inside them.
REQUIREMENT_LABELS: tuple[Template, ...] = (
    _t("req.intakeOpen", "Intake accepting applications"),
    _t("req.deadline", "Admission deadline"),
    _t("req.minGpa", "Minimum GPA"),
    _t("req.satTotal", "SAT total"),
    _t("req.satPolicy", "SAT policy"),
    _t("req.portfolio", "Portfolio"),
    _t("req.interview", "Interview"),
    _t("req.entranceExam", "Entrance examination"),
    _t("req.credentialEvaluation", "Credential evaluation"),
    _t("req.requiredSubjects", "Required subjects"),
    _t("req.academicEntry", "Academic entry requirements"),
    _t("req.ieltsType", "Accepted IELTS test type"),
    _t("req.englishWaiver", "English test waiver"),
    _t("req.ieltsOverall", "IELTS overall"),
    _t("req.ieltsBand", "IELTS {band}"),
    _t("req.toeflTotal", "TOEFL total"),
    _t("req.scholarshipCitizenship", "Scholarship citizenship eligibility"),
    _t("req.scholarshipInternational", "Scholarship international eligibility"),
    _t("req.scholarshipFaculty", "Scholarship faculty restriction"),
    _t("req.scholarshipProgramme", "Scholarship programme restriction"),
    _t("req.scholarshipDeadline", "Scholarship deadline"),
    _t("req.scholarshipTest", "Scholarship {test} minimum"),
)

#: ``RequirementCheck.explanation``, for programmes and for awards. Where one
#: sentence is the start of another, the longer one comes first: a parameter
#: would otherwise swallow the rest of the longer sentence.
REQUIREMENT_EXPLANATIONS: tuple[Template, ...] = (
    _t(
        "explain.noMinimum",
        "No official minimum for {label} was found; not treated as a barrier.",
    ),
    _t("explain.notNumber", "The published {label} could not be read as a number."),
    _t(
        "explain.noApplicantValue",
        "The programme publishes a minimum of {published}, but the profile has no {label} "
        "value yet. Add it to resolve this check.",
    ),
    _t(
        "explain.minimumNotMet",
        "Published minimum {published}; applicant {applicant}. The published minimum is not met.",
    ),
    _t("explain.minimumMet", "Published minimum {published}; applicant {applicant}."),
    _t(
        "explain.intakeClosed",
        "The programme officially states it is not accepting applications for this intake.",
    ),
    _t(
        "explain.deadlineUnparsed",
        "A deadline was published but could not be parsed into a date.",
    ),
    _t("explain.deadlinePassed", "The published deadline {date} has passed."),
    _t(
        "explain.deadlineByPopulation",
        "Applications close {date} at the earliest; the deadline depends on your fee "
        "population here ({deadlines}).",
    ),
    _t("explain.deadlineOpen", "Applications close {date}."),
    _t("explain.allDeadlinesPassed", "Every published deadline has passed ({deadlines})."),
    _t(
        "explain.deadlineByPopulationPassed",
        "The deadline depends on your fee population here ({deadlines}). The one for "
        "{populations} has passed; confirm which applies to you.",
    ),
    _t(
        "explain.gpaScale",
        "The applicant's GPA is on the {scale} scale and the programme publishes a different "
        "scale. No conversion is applied without a documented method, so this cannot be "
        "decided here.",
    ),
    _t(
        "explain.testOptional",
        "The programme is test-optional, so a missing SAT score is not a barrier.",
    ),
    _t(
        "explain.satPolicyNoMinimum",
        "An SAT policy is published but no minimum score was found.",
    ),
    _t(
        "explain.actionRequired",
        "{label} is required. This is an action to complete, not a disqualification.",
    ),
    _t(
        "explain.subjectsPresent",
        "All published subject prerequisites are present in the profile.",
    ),
    _t(
        "explain.subjectsMissing",
        "Not listed in the profile: {subjects}. Add them if they were studied; otherwise this "
        "is a genuine gap.",
    ),
    _t(
        "explain.noAssessable",
        "No assessable academic entry requirements were found. A future deadline or optional "
        "test policy does not establish eligibility.",
    ),
    _t("explain.ieltsTypes", "The programme accepts {accepted}; the applicant holds {held}."),
    _t(
        "explain.englishWaiver",
        "This programme publishes conditions under which the English test is not required. "
        "Check them against your own schooling before booking a test — whether they cover "
        "you is not something this page settles.",
    ),
    # Awards (``runner._scholarship_eligibility``, ``app.domain.citizenship``).
    _t(
        "explain.citizenshipUnreadable",
        "The award publishes a citizenship restriction that could not be read as a list of "
        "countries. It needs official clarification.",
    ),
    _t(
        "explain.citizenshipNamed",
        "The published restriction names {phrase}, which matches the {country} citizenship "
        "in the profile.",
    ),
    _t(
        "explain.citizenshipMember",
        "{country} is a member of the {group}, which the award names as its restriction.",
    ),
    _t(
        "explain.citizenshipGroup",
        "The award is restricted to a group ('{restrictions}') whose membership is not "
        "published as a list of countries. Whether {held} falls inside it cannot be settled "
        "from the page, so it is left for the admissions office to confirm.",
    ),
    _t(
        "explain.citizenshipExcluded",
        "The award is restricted to {restrictions}. An applicant holding {held} citizenship "
        "is not eligible.",
    ),
    _t(
        "explain.internationalClosed",
        "The award is officially closed to international students.",
    ),
    _t(
        "explain.internationalOpen",
        "The award is officially open to international students of any nationality.",
    ),
    _t(
        "explain.restriction",
        "The page limits this award to {restriction}. Whether this programme belongs to it is "
        "not something the page settles — ask the admissions office before counting on this "
        "award.",
    ),
    _t(
        "explain.scholarshipTestMissing",
        "The award requires {test} {minimum}; no score is in the profile.",
    ),
    _t(
        "explain.scholarshipDeadlinePassed",
        "The published scholarship deadline {date} has passed.",
    ),
)

# --- I18N-2: why an award is classified as it is (``app.domain.funding``) ----

#: ``app.adapters.applicability``'s degree-level reasons, said inside
#: "Not applicable to this applicant's degree level: …".
DEGREE_REASONS: tuple[Template, ...] = (
    _t("degree.noText", "no text or no degree level to check against"),
    _t("degree.excludes", "the page explicitly excludes {degree} applicants"),
    _t("degree.forOther", "the page states the award is for {level} applicants, not {degree}"),
    _t("degree.statesFor", "the page states the award is for {degree} applicants"),
    _t(
        "degree.onlyOthers",
        "the page describes the award for {levels} only and never mentions {degree}",
    ),
    _t("degree.unstated", "the page does not state which degree levels the award applies to"),
    _t("degree.excludesLevel", "the page excludes this level."),
)

_EXCLUDED = _t("class.excluded", "Published conditions exclude this applicant.")

#: One missing category in "Tuition is confirmed as covered, but {missing} — …".
MISSING_COVERAGE: tuple[Template, ...] = (
    _t("missing.notCovered", "{category} is not covered"),
    _t("missing.unknown", "{category} is unknown"),
    _t("missing.partial", "{category} is partial"),
)

#: The sentences ``classification_reason`` is built from: the verdict
#: (``funding.classify``), then the runner's additions (promotional wording,
#: the shape of award the profile asked for, a cost it must cover).
CLASSIFICATION: tuple[Template, ...] = (
    _EXCLUDED,
    _t("class.degreeLevel", "Not applicable to this applicant's degree level: {degreeReason}"),
    _t(
        "class.citizenship",
        "The award is restricted to {restrictions}, which does not include this applicant.",
    ),
    _t(
        "class.notInternational",
        "Official source states the award is not open to international students.",
    ),
    _t("class.noCoverage", "No official per-category coverage information was found."),
    _t(
        "class.promotionalNoBreakdown",
        "Page uses promotional wording ({words}) but publishes no breakdown.",
    ),
    _t(
        "class.needBased",
        "Award size depends on a verified financial-need assessment that has not been filed.",
    ),
    _t(
        "class.fullRide",
        "Official sources confirm coverage of tuition, mandatory fees, housing and meals or an "
        "equivalent living stipend.",
    ),
    _t(
        "class.fullTuition",
        "Tuition is confirmed as covered, but {missing} — this is full tuition, not a full ride.",
    ),
    _t(
        "class.shareUnknown",
        "Coverage is partial but the award amount or the cost of attendance is not officially "
        "published, so the share cannot be computed.",
    ),
    _t(
        "class.largeGrant",
        "Covers roughly {share} of published cost of attendance; a substantial portion of the "
        "cost remains.",
    ),
    _t("class.partial", "Covers roughly {share} of published cost of attendance."),
    _t(
        "class.promotional",
        "The page uses promotional wording such as 'full ride'; the classification here "
        "follows the published coverage table instead.",
    ),
    _t(
        "class.onlyFullRide",
        "The profile states that only a full ride makes this affordable; this award is "
        "classified as {classification}.",
    ),
    _t(
        "class.noTuitionOnly",
        "The profile states that a tuition-only award would not be taken up.",
    ),
    _t("class.noPartial", "The profile states that a partial award would not be taken up."),
    _t(
        "class.needDocuments",
        "This award is need-based and the profile states that financial documents will not be "
        "submitted, which is what a need-based application requires.",
    ),
    _t(
        "class.mustCover",
        "The profile requires {categories} to be covered; this award states it is not.",
    ),
)

#: A bare degree reason can stand as the whole verdict ("Published conditions
#: exclude this applicant" is replaced by the adapter's own reason).
CLASSIFICATION_SENTENCES = CLASSIFICATION + DEGREE_REASONS[:-1]

# --- I18N-2: the v2 ranking (``app.domain.ranking_v2``) ---------------------

AXIS_REASONS: tuple[Template, ...] = (
    _t(
        "rank.academicNoMargin",
        "All published requirements are met; there are no numeric minimums to measure a "
        "margin against.",
    ),
    _t(
        "rank.academicMargin",
        "All published requirements are met, on average {margin} above the minimums.",
    ),
    _t("rank.academicPending", "Requirements are met apart from items still pending."),
    _t("rank.academicGap", "At least one published requirement is not met."),
    _t("rank.academicUnknown", "Published requirements could not be verified."),
    _t("rank.fundingUnknown", "No official funding information was confirmed."),
    _t("rank.fundingConfirmed", "Funding fit is confirmed opportunity."),
    _t("rank.fundingCompetitive", "Funding fit is competitive opportunity."),
    _t("rank.fundingLimited", "Funding fit is limited opportunity."),
    _t("rank.fundingNotEligible", "Funding fit is not eligible."),
    _t("rank.gapUnknown", "The remaining annual cost could not be computed."),
    _t("rank.noCeiling", "No family budget ceiling was stated to compare against."),
    _t("rank.nothingRemains", "Nothing remains to be paid."),
    _t(
        "rank.zeroContribution",
        "The family states it can contribute nothing, and {gap} a year remains.",
    ),
    _t(
        "rank.withinCeiling",
        "The remaining {gap} a year is within the stated ceiling of {ceiling}.",
    ),
    _t(
        "rank.timesCeiling",
        "The remaining {gap} a year is {ratio} times the stated ceiling of {ceiling}.",
    ),
    _t(
        "rank.aboveCeiling",
        "The remaining {gap} a year is {over} above the stated ceiling of {ceiling}.",
    ),
    _t("rank.preferredCountry", "{country} is a preferred country."),
    _t("rank.unpreferredCountry", "{country} is outside the preferred list."),
    _t("rank.noRank", "No ranking position was found."),
    _t("rank.insideBand", "Ranked {rank}, inside the requested {band}."),
    _t("rank.outsideTop", "Ranked {rank}, outside the top {top}."),
    _t("rank.consensus", "Consensus ranking position {rank}."),
    _t("rank.ranked", "Ranked {rank}."),
    _t("rank.noPreference", "No {axis} preference was stated."),
    _t("rank.attributeUnknown", "The {axis} of this university is not known."),
    _t("rank.attributeMatches", "{actual} matches the stated preference."),
    _t("rank.ladderStep", "{actual} against a preference for {preferred}: {steps} step apart."),
    _t(
        "rank.ladderSteps",
        "{actual} against a preference for {preferred}: {steps} steps apart.",
    ),
    _t("rank.ladderDiffers", "{actual} differs from the preferred {preferred}."),
    _t("rank.careersNotPriority", "Careers were not a stated priority."),
    _t("rank.coop", "A co-op or placement year is officially offered."),
    _t("rank.internships", "An internship programme is officially described."),
    _t(
        "rank.careersPage",
        "A careers page exists but states nothing specific enough to check.",
    ),
    _t("rank.noCareers", "No official careers information was found."),
    _t("rank.pswNotPriority", "Post-study work was not a stated priority."),
    _t("rank.pswUnknown", "Post-study work rules were not confirmed in months."),
    _t("rank.psw", "A post-study work right of {months} months is published."),
)

#: Why a row is listed and not ranked: a confirmed hard filter, or an excluded country.
KNOCKOUTS: tuple[Template, ...] = (
    _t("rank.excludedCountry", "{country} is on the applicant's excluded list."),
    _t("rank.knockoutUnmet", "{requirement}: a published requirement is not met"),
    _t("rank.knockout", "{requirement}: {explanation}"),
)

BUCKET_REASONS: tuple[Template, ...] = (
    _t(
        "rank.bucketInsufficient",
        "Too little of the published requirements could be verified to place this row.",
    ),
    _t(
        "rank.bucketOutOfBudget",
        "The remaining cost is {ratio} times the stated ceiling, past the {limit} times this "
        "applicant said they could stretch to.",
    ),
    _t(
        "rank.bucketWellPlaced",
        "Requirements are met with room, funding is confirmed, and the remaining cost is "
        "within the stated ceiling.",
    ),
    _t(
        "rank.bucketPlausible",
        "Requirements and funding both look reachable on published data.",
    ),
    _t(
        "rank.bucketAmbitious",
        "Either the requirements, the funding or the remaining cost makes this a stretch.",
    ),
)

DISCLAIMERS: tuple[Template, ...] = (
    _t(
        "rank.disclaimer",
        "How well this matches your stated priorities, on confirmed data. Not a probability "
        "of admission.",
    ),
)

# --- I18N-2: conflicts (``app.domain.conflicts``) and the /questions endpoint --

#: ``conflicts._LABELS``: what two official sources disagree about.
CONFLICT_LABELS: tuple[Template, ...] = (
    _t("conflict.label.ieltsOverall", "the minimum overall IELTS band"),
    _t("conflict.label.ieltsSubscore", "the minimum IELTS band per section"),
    _t("conflict.label.minGpa", "the minimum GPA"),
    _t("conflict.label.satTotal", "the minimum SAT total"),
    _t("conflict.label.toeflTotal", "the minimum TOEFL total"),
    _t("conflict.label.admissionDeadline", "the application deadline"),
    _t("conflict.label.scholarshipDeadline", "the scholarship deadline"),
    _t("conflict.label.tuition", "the tuition fee"),
    _t("conflict.label.totalCost", "the total cost of attendance"),
    _t("conflict.label.awardAmount", "the award amount"),
    _t("conflict.label.internationalEligible", "eligibility for international students"),
)

#: ``Conflict.subject``: the label, then the subject key and the programme when known.
CONFLICT_SUBJECTS: tuple[Template, ...] = (
    _t("conflict.subjectFull", "{what} — {subjectKey} ({programme})"),
    _t("conflict.subjectKeyed", "{what} — {subjectKey}"),
    _t("conflict.subjectProgramme", "{what} ({programme})"),
    _t("conflict.subject", "{what}"),
)

#: ``Conflict.resolution_rule``. The scope dimension is spelled out per
#: dimension, as the backend writes it ("residencys" included): a plural
#: built by appending "s" cannot be translated as a parameter.
CONFLICT_RULES: tuple[Template, ...] = (
    _t(
        "conflict.preferSpecific",
        "Preferring the more specific source ({specificity}); the disagreement is shown "
        "rather than resolved.",
    ),
    _t(
        "conflict.moreSpecific",
        "Not a contradiction: a programme-specific rule and a university-wide rule can both "
        "be true. The more specific source ({specificity}) applies to this application; the "
        "broader rule is kept, not discarded.",
    ),
    _t(
        "conflict.differentPopulation",
        "Not a contradiction: the pages state different populations, so both values can be "
        "correct. Neither is discarded.",
    ),
    _t(
        "conflict.differentResidency",
        "Not a contradiction: the pages state different residencys, so both values can be "
        "correct. Neither is discarded.",
    ),
    _t(
        "conflict.differentIntake",
        "Not a contradiction: the pages state different intakes, so both values can be "
        "correct. Neither is discarded.",
    ),
    _t(
        "conflict.differentAcademicYear",
        "Not a contradiction: the pages state different academic years, so both values can "
        "be correct. Neither is discarded.",
    ),
    _t(
        "conflict.differentDegree",
        "Not a contradiction: the pages state different degrees, so both values can be "
        "correct. Neither is discarded.",
    ),
    _t(
        "conflict.differentQualification",
        "Not a contradiction: the pages state different qualifications, so both values can "
        "be correct. Neither is discarded.",
    ),
)

#: The /questions endpoint's "why it matters" for a conflict it lists.
CONFLICT_WHYS: tuple[Template, ...] = (
    _t("conflict.why", "Official sources disagree on {subject}: {values}"),
)

# --- I18N-2: the exchange-rate warning (``routes_meta.capabilities``) --------

CURRENCY: tuple[Template, ...] = (
    _t(
        "currency.staleRates",
        "These conversions use exchange rates from {date}, {days} days old. Treat converted "
        "amounts as indicative and check the current rate before relying on one.",
    ),
)

# --- I18N-3: the Documents screen (``app.knowledge.documents``) ---------------

#: One name per document kind: ``app.knowledge.documents.LIVE_KINDS`` (the live
#: reader's own names, ``web_documents._DOC_RULES``) and ``EXTRA_KINDS``. The
#: names are our vocabulary, not a university's words, so they translate. The
#: key is ``document.<kind>``. Written out rather than imported: the domain
#: imports nothing that reaches ``app.adapters``, and
#: ``test_message_keys`` holds the two tables equal, kind for kind and word for word.
DOCUMENT_NAMES: tuple[Template, ...] = (
    _t("document.transcript", "Full academic transcript"),
    _t("document.secondary_diploma", "Secondary school diploma (certified copy)"),
    _t("document.translation", "Certified English translation of non-English documents"),
    _t("document.apostille", "Apostille certification"),
    _t("document.credential_evaluation", "Course-by-course credential evaluation (WES/ECE)"),
    _t("document.passport", "Passport identity page (copy)"),
    _t("document.photo", "Passport-size photograph (digital image)"),
    _t("document.personal_statement", "Personal statement"),
    _t("document.motivation_letter", "Statement of motivation"),
    _t("document.essay", "Personal Essay"),
    _t("document.recommendation_letter", "Letter of recommendation"),
    _t("document.academic_reference", "Academic reference"),
    _t("document.cv", "Curriculum vitae"),
    _t("document.portfolio", "Portfolio"),
    _t("document.financial_proof", "Proof of financial resources"),
    _t("document.english_test_report", "English language test report"),
    _t("document.entrance_test", "Admission test result"),
    _t("document.application_form", "Application form"),
)

#: The sentences ``app.knowledge.documents.kb_checklist`` writes into
#: ``DocumentItem.format_notes``: how an item applies (``_requirement_note``),
#: then why it may be stale, with the claim's own stale reasons inside.
DOCUMENT_NOTES: tuple[Template, ...] = (
    _t("document.note.optional", "Optional, as published."),
    _t("document.note.conditional", "Conditional, as published."),
    _t("document.note.conditionWhen", "Required only when: {condition}."),
    _t("document.note.possiblyOutdated", "Possibly outdated: {reasons}."),
)

#: Where ``format_notes`` is cut into sentences: a full stop, spaces, a capital.
#: ``DocumentsScreen.tsx`` cuts the served English at the same place, so the
#: n-th entry of ``notes_messages`` is the n-th sentence it shows.
_NOTE_END = re.compile(r"(?<=\.) +(?=[A-Z])")


def document_name_message(name: str) -> MessageRef | None:
    """The key of a document name from the 18-kind vocabulary; None for any other name."""
    return match(DOCUMENT_NAMES, name)


def _document_note(sentence: str) -> MessageRef | None:
    ref = match(DOCUMENT_NOTES, sentence)
    if ref is not None and ref.key == "document.note.possiblyOutdated":
        # A reason may hold "; " itself (a quoted list title): regroup the cut.
        reasons = _split_reasons(ref.params["reasons"], "; ")
        if reasons:
            ref.parts["reasons"] = list(reasons)
    return ref if _complete(ref) else None


def document_notes_messages(notes: str) -> list[MessageRef | None]:
    """One key per sentence of ``format_notes``; None for a sentence no template knows."""
    text = notes.strip()
    return [_document_note(sentence) for sentence in _NOTE_END.split(text)] if text else []


def annotate_document(item: DocumentItem) -> None:
    item.name_message = document_name_message(item.name)
    item.notes_messages = document_notes_messages(item.format_notes)


def annotate_checklist(checklist: DocumentChecklist) -> None:
    for items in (
        checklist.admission_documents,
        checklist.scholarship_documents,
        checklist.applicant_actions,
        checklist.school_actions,
        checklist.recommender_actions,
        checklist.certification_actions,
    ):
        for item in items:
            annotate_document(item)
    for question in checklist.unresolved:
        annotate_question(question)


CATALOGUE: tuple[Template, ...] = (
    QUESTIONS
    + WHYS
    + STALE_REASONS
    + DOCUMENT_ITEMS
    + FUNDING
    + CAVEATS
    + COVERAGE
    + REQUIREMENT_LABELS
    + REQUIREMENT_EXPLANATIONS
    + DEGREE_REASONS
    + MISSING_COVERAGE
    + CLASSIFICATION
    + AXIS_REASONS
    + KNOCKOUTS
    + BUCKET_REASONS
    + DISCLAIMERS
    + CONFLICT_LABELS
    + CONFLICT_SUBJECTS
    + CONFLICT_RULES
    + CONFLICT_WHYS
    + CURRENCY
    + DOCUMENT_NAMES
    + DOCUMENT_NOTES
)

#: Parameters that are themselves keyed sentences, and the catalogue and
#: separator to key them with (``MessageRef.parts``). ``reasons`` and
#: ``documents`` are cut by their own rules in :func:`_with_parts`.
_PART_PARAMS: dict[str, tuple[tuple[Template, ...], str | None]] = {
    "label": (REQUIREMENT_LABELS, None),
    "requirement": (REQUIREMENT_LABELS, None),
    "explanation": (REQUIREMENT_EXPLANATIONS, None),
    "degreeReason": ((*DEGREE_REASONS, _EXCLUDED), None),
    "missing": (MISSING_COVERAGE, "; "),
    "what": (CONFLICT_LABELS, None),
    "subject": (CONFLICT_SUBJECTS, None),
}

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
    for name, (templates, sep) in _PART_PARAMS.items():
        value = ref.params.get(name)
        if value:
            pieces = value.split(sep) if sep else [value]
            ref.parts[name] = [match(templates, piece) for piece in pieces]
    return ref


def _complete(ref: MessageRef | None) -> bool:
    """Whether ``ref`` and every part inside it, at any depth, is keyed."""
    if ref is None:
        return False
    return all(_complete(part) for parts in ref.parts.values() for part in parts)


_SENTENCE_END = re.compile(r"(?<=[.?!]) +")


def match_sentences(templates: tuple[Template, ...], text: str) -> list[MessageRef] | None:
    """``text`` as a run of keyed sentences, each fully keyed; None when it is not.

    For a field built by appending sentences (an award's classification
    reason). The cut with the most sentences wins, so a parameter cannot
    swallow the sentence after it; a sentence no template knows, or one with
    an unkeyed part, leaves the whole field in English.
    """
    pieces = _SENTENCE_END.split(text.strip())
    best: list[list[MessageRef] | None] = [[]] + [None] * len(pieces)
    for end in range(1, len(pieces) + 1):
        for start in range(end):
            before = best[start]
            if before is None:
                continue
            ref = match(templates, " ".join(pieces[start:end]))
            current = best[end]
            if _complete(ref) and (current is None or len(before) + 1 > len(current)):
                best[end] = [*before, ref]  # type: ignore[list-item]
    found = best[-1]
    return found or None


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
            name = document_name_message(document)  # I18N-3: the name in the reader's words
            return MessageRef(
                key="stale.documentItem",
                params={"document": document, "reasons": inner},
                parts={"reasons": list(reasons), **({"document": [name]} if name else {})},
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


def annotate_check(check: RequirementCheck) -> None:
    check.requirement_message = match(REQUIREMENT_LABELS, check.requirement)
    check.explanation_message = (
        match(REQUIREMENT_EXPLANATIONS, check.explanation) if check.explanation else None
    )


def annotate_scholarship(scholarship: Scholarship) -> None:
    reason = scholarship.classification_reason
    scholarship.classification_messages = (
        match_sentences(CLASSIFICATION_SENTENCES, reason) if reason else None
    )
    for check in scholarship.eligibility_checks:
        annotate_check(check)


def annotate_ranking(ranking: RankingV2) -> None:
    for axis in ranking.axes:
        axis.reason_message = match(AXIS_REASONS, axis.reason)
    ranking.bucket_reason_message = (
        match(BUCKET_REASONS + KNOCKOUTS, ranking.bucket_reason) if ranking.bucket_reason else None
    )
    ranking.knocked_out_messages = (
        [match(KNOCKOUTS, reason) for reason in ranking.knocked_out_by]
        if ranking.knocked_out_by
        else None
    )
    ranking.disclaimer_message = match(DISCLAIMERS, ranking.disclaimer)


def annotate_conflict(conflict: Conflict) -> None:
    conflict.subject_message = match(CONFLICT_SUBJECTS, conflict.subject)
    conflict.resolution_message = (
        match(CONFLICT_RULES, conflict.resolution_rule) if conflict.resolution_rule else None
    )


def conflict_why(conflict: Conflict) -> tuple[str, MessageRef | None]:
    """The /questions endpoint's "why it matters" for a conflict, and its key."""
    text = f"Official sources disagree on {conflict.subject}: {conflict.values}"
    return text, match(CONFLICT_WHYS, text)


def stale_rates_message(warning: str) -> MessageRef | None:
    """The key of ``capabilities.currency.stale_warning``; None when there is none."""
    return match(CURRENCY, warning) if warning else None


def annotate_result(result: ProgramResult) -> ProgramResult:
    """Attach message keys to a result about to be served; returns it for chaining.

    Call it on the object the API returns, never on one about to be stored.
    """
    for check in result.requirement_checks:
        annotate_check(check)
    for scholarship in result.scholarships:
        annotate_scholarship(scholarship)
    if result.ranking is not None:
        annotate_ranking(result.ranking)
    for conflict in result.conflicts:
        annotate_conflict(conflict)
    for question in result.unresolved:
        annotate_question(question)
    for claim in result.claims:
        annotate_claim(claim)
    if result.funding_gap is not None:
        annotate_gap(result.funding_gap)
    if result.checklist is not None:
        annotate_checklist(result.checklist)
    return result
