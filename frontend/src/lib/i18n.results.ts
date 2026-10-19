/**
 * The results screens in English, Russian and Kazakh (gap B6).
 *
 * Shortlist, result detail, funding, costs, sources and the comparison panel,
 * plus `msg.*`: the sentences the backend writes (open questions, funding
 * outcomes, why a fact is stale). The backend serves those in English with a
 * stable key beside them (`MessageRef`); `lib/messages.ts` renders the key here
 * and falls back to the served English whenever a key or a translation is
 * missing. The English of every `msg.*` entry is the backend template word for
 * word — `backend/tests/test_message_keys.py` checks it.
 *
 * `RU_RESULTS` and `KK_RESULTS` are full `Record`s, not `Partial`s, so a key
 * added in English without both translations does not compile.
 *
 * Several strings here use product terms that `docs/i18n/GLOSSARY.md` lists as
 * needing a person's decision (claim, shortlist, funding gap, full ride,
 * unknown). The words chosen are recorded there as provisional, to be reviewed;
 * they are deliberately no stronger than the English.
 *
 * `{name}` is a parameter, filled by `tf()` or by `localize()`.
 */

export const EN_RESULTS = {
  // --- shared --------------------------------------------------------------
  'results.empty.title': 'No results yet',
  'results.empty.runFirst': 'Run the research first.',
  'results.notEnoughData': 'Not enough comparable data',
  'results.notConfirmed': 'Not confirmed',
  'results.notFound': 'not found',
  'results.notPublished': 'not published',
  'results.notComputable': 'not computable',
  'results.notComparable': 'not comparable',
  'results.blocking': 'blocking',
  'results.open': 'open',
  'results.yes': 'Yes',
  'results.no': 'No',
  'results.remove': 'Remove',
  'results.compare': 'Compare',
  'results.cancel': 'Cancel',
  'results.demoData': 'Demo data.',
  'results.notCurrent': 'Not current: {reason}.',
  'results.staleAge': '{days}d old',
  'results.staleNoAge': 'not current',
  'results.currentWithCaveat': 'Current, with caveat',
  'results.caveat': 'Caveat: {caveat}.',
  'results.conflictCount.one': '{n} conflict',
  'results.conflictCount.other': '{n} conflicts',
  'results.questionCount.one': '{n} open question',
  'results.questionCount.other': '{n} open questions',
  'results.fitDisclaimer':
    'How well this matches your stated priorities, on confirmed data. Not a probability of admission.',

  'col.university': 'University & programme',
  'col.eligibility': 'Eligibility',
  'col.admissionsFit': 'Admissions fit',
  'col.funding': 'Funding',
  'col.remaining': 'Remaining / year',
  'col.remainingPerYear': 'Remaining per year',
  'col.deadline': 'Deadline',
  'col.match': 'Match',
  'col.confirmed': 'Confirmed',
  'col.confirmedHint': 'How much of the weight rests on data we confirmed.',
  'col.bucket': 'Bucket',
  'col.decision': 'Decision',

  // --- shortlist (screen 04) ---------------------------------------------
  'shortlist.hint.OUT_OF_BUDGET':
    'Kept with the number, not hidden: you may know something about the money that we do not.',
  'shortlist.hint.NEEDS_CLARIFICATION':
    'Too little could be verified to place these. Ask the admissions office the open questions on the row.',
  'shortlist.hint.EXCLUDED': 'A published requirement that is not met, or a country you excluded.',
  'shortlist.reason.cost': 'cost',
  'shortlist.reason.deadline passed': 'deadline passed',
  'shortlist.reason.no funding': 'no funding',
  'shortlist.reason.not a fit': 'not a fit',
  'shortlist.emptyEyebrow': 'FIND YOUR PATH',
  'shortlist.title': 'Find your best {highlight}',
  'shortlist.titleHighlight': 'matches.',
  'shortlist.emptyLede': 'Research begins with your profile and preferences.',
  'shortlist.emptyBody': 'Start research to find programmes supported by available sources.',
  'shortlist.start': 'Start research →',
  'shortlist.passed': 'passed',
  'shortlist.previousCycle': 'previous cycle: {date}',
  'shortlist.notRanked': 'not ranked',
  'shortlist.decisionFor': 'Decision for {university}',
  'shortlist.maybe': 'Maybe',
  'shortlist.whyNot': 'Why not this one? (optional — it is kept with the row)',
  'shortlist.whyNotPlaceholder': 'cost, deadline, fit…',
  'shortlist.saveRejection': 'Save rejection',
  'shortlist.rejected': 'Rejected: {reason}',
  'shortlist.editNote': 'Edit note',
  'shortlist.addNote': 'Add note',
  'shortlist.notePlaceholder': 'Why this one?',
  'shortlist.saveNote': 'Save note',
  'shortlist.exploreCatalogue': 'Explore more universities from the local catalogue',
  'shortlist.eyebrow': 'GLOBAL OPPORTUNITIES. REAL MATCHES.',
  'shortlist.lede':
    'Explore programmes that fit your goals, budget and future. Open any result to see the evidence and what is still unknown.',
  'shortlist.mascotAlt': 'Unimatch mascot exploring a mountain landscape',
  'shortlist.demoBody':
    'These figures come from a bundled synthetic corpus, not from real university pages. Every source below is a {code} address.',
  'shortlist.search': 'Search universities, programmes or countries',
  'shortlist.searchPlaceholder': 'Search universities, programmes or countries…',
  'shortlist.filters': 'Filters',
  'shortlist.compareCount': 'Compare ({n})',
  'shortlist.matchList': 'Match list',
  'shortlist.tab.all': 'All',
  'shortlist.tab.priority': 'Priority',
  'shortlist.tab.saved': 'Saved',
  'shortlist.tab.exploring': 'Exploring',
  'shortlist.filterSort': 'Filter and sort results',
  'shortlist.country': 'Country',
  'shortlist.sortBy': 'Sort by',
  'shortlist.allCount': 'All ({n})',
  'shortlist.any': 'Any',
  'shortlist.sort.key': 'Match, discounted by what is unverified',
  'shortlist.sort.fit': 'Match with your priorities',
  'shortlist.sort.coverage': 'Most confirmed',
  'shortlist.sort.gap': 'Smallest remaining cost',
  'shortlist.sort.deadline': 'Earliest deadline',
  'shortlist.sort.university': 'University name',
  'shortlist.hideRejected': 'Hide rejected',
  'shortlist.resultCount.one': '{n} result from this research run',
  'shortlist.resultCount.other': '{n} results from this research run',
  'shortlist.noMatchTitle': 'Nothing matches these filters yet.',
  'shortlist.noMatchBody': 'Try another search or clear the filters.',
  'shortlist.clearFilters': 'Clear filters',
  'shortlist.hideDetails': 'Hide details',
  'shortlist.viewDetails': 'View details',
  'shortlist.saved': 'Saved',
  'shortlist.save': 'Save',
  'shortlist.evidenceTable': 'Detailed evidence table',
  'shortlist.balancedTitle': 'A balanced shortlist',
  'shortlist.balancedHint':
    'Filled to quota before the ranking speaks: a top ten of ten ambitious options is a list nobody can act on.',
  'shortlist.caption':
    'Shortlisted university programmes with eligibility, fit, funding and remaining cost',
  'shortlist.captionSetAside':
    'Shortlisted university programmes set aside as {bucket}, with eligibility, fit, funding and remaining cost',
  'shortlist.nothingRanked':
    'Nothing here is both affordable and verified enough to rank. Every option is in a section below, with the reason it is there.',
  'shortlist.rankedFootnote':
    'Showing {shown} of {total} ranked rows. {match} is how well a place fits the priorities you stated, on confirmed data — not a probability of admission. The {confirmed} percentage is how much of that judgement rests on data we could verify.',
  'shortlist.footnote':
    'Showing {shown} of {total}. Rejected rows are kept with their reason so the same programme is not proposed again without new information.',

  // --- comparison panel ----------------------------------------------------
  'compare.aria': 'Compare selected programmes',
  'compare.eyebrow': 'COMPARE WITH CLARITY',
  'compare.title': 'Different strengths. A clearer choice.',
  'compare.clear': 'Clear',
  'compare.lede':
    'Compare what the sources actually support. A match score describes your stated preferences, not your chance of admission.',
  'compare.preferenceFit': 'Preference fit',
  'compare.coverage': 'Evidence coverage',
  'compare.coverageHint': 'How much of the evidence needed for this assessment was confirmed',
  'compare.notAssessed': 'Not assessed',
  'compare.toClarify': '{n} to clarify',
  'compare.whyFit': 'Why this fit?',

  // --- result detail (screen 05) -----------------------------------------
  'detail.tab.requirements': 'Requirements',
  'detail.tab.funding': 'Funding',
  'detail.tab.costs': 'Costs',
  'detail.tab.documents': 'Documents',
  'detail.tab.score': 'Why this order',
  'detail.tab.sources': 'Sources & evidence',
  'detail.eyebrow': 'PROGRAMME DETAILS · {country}',
  'detail.assessment': 'YOUR ASSESSMENT',
  'detail.assessmentNote':
    'Eligibility is separate from admissions fit. Neither is a probability of admission.',
  'detail.evidence': 'Evidence',
  'detail.tabsAria': '{university} details',
  'detail.requirementNotMet': 'Confirmed requirement not met:',
  'detail.requirementNotMetNote':
    'This is drawn from an official page, so it is treated as a real barrier rather than a gap in our data.',
  'detail.published': 'published',
  'detail.you': 'you',
  'detail.deadlineLine': 'Deadline: {date}',
  'detail.deadlinePassed': 'deadline passed',
  'detail.previousCycle': 'Previous cycle: {date}',
  'detail.noScholarship':
    'No official scholarship page could be read for this programme. Funding is {unknown} — that is not the same as there being none.',
  'detail.unknown': 'unknown',
  'detail.value': 'Value',
  'detail.percentOfTuition': '{pct}% of tuition',
  'detail.openToYou': 'Open to you',
  'detail.restrictedTo': 'restricted to {list}',
  'detail.internationalEligible': 'international students eligible',
  'detail.notInternational': 'not open to international students',
  'detail.eligibilityNotPublished': 'eligibility not published',
  'detail.howToApply': 'How to apply',
  'detail.extraEssays': ' · extra essays required',
  'detail.offerRequired': 'An admission offer must be held before applying for this award.',
  'detail.offerNotRequired': 'You can apply for this award before receiving an admission offer.',
  'detail.needBased': 'Decided on demonstrated financial need.',
  'detail.renewal': 'Renewal',
  'detail.renewable': 'Renewable',
  'detail.renewableYears': 'Renewable for up to {n} years',
  'detail.oneTime': 'One-time award',
  'detail.stackable': 'Combines with others',
  'detail.covers': 'Covers',
  'detail.awardsOffered': 'Awards offered',
  'detail.officiallyPublished': '{n} (officially published)',
  'detail.noCost': 'No official cost of attendance was found for this programme and intake.',
  'detail.publishedTotal': 'Published total',
  'detail.knownSoFar': 'Cost of attendance known so far',
  'detail.lowerBound':
    'Only some core cost categories are itemised, so this figure is the known subtotal — a lower bound on the real cost of attendance, never the full cost. No remaining-cost figure is computed against a half-known cost.',
  'detail.notItemised': '{category}: not itemised',
  'detail.remainingAnnual': 'Remaining annual cost',
  'detail.costOfAttendance': 'Cost of attendance',
  'detail.confirmedAid': 'Confirmed aid',
  'detail.stackedAid': 'Stacked aid',
  'detail.notComputed': 'Not computed.',
  'detail.documentsLater':
    'Documents are collected only for programmes you approve — it is the expensive step, so it runs on your shortlist rather than on all candidates. Approve this row, then run “Collect documents”.',
  'detail.docs.official': 'read from official pages',
  'detail.docs.partial': 'partially read',
  'detail.docs.unavailable': 'no official list found',
  'detail.docs.kb.official': 'from the verified knowledge base',
  'detail.docs.kb.partial': 'verified, some items not current',
  'detail.docs.kb.unavailable': 'no list in the verified knowledge base',
  'detail.docs.leadTime.one': 'allow ~{n} day',
  'detail.docs.leadTime.few': 'allow ~{n} days',
  'detail.docs.leadTime.many': 'allow ~{n} days',
  'detail.docs.leadTime.other': 'allow ~{n} days',
  'detail.generated': 'generated {when}',
  'detail.docs.required': 'Required',
  'detail.docs.optional': 'Optional',
  'detail.docs.conditional': 'Conditional',
  'detail.docs.condition': 'Condition, as published: {condition}.',
  'detail.docs.order': 'Suggested order, longest lead time first',
  'detail.docs.owner.applicant': 'You prepare it',
  'detail.docs.owner.school': 'Your school',
  'detail.docs.owner.recommender': 'Your referee',
  'detail.docs.owner.third_party': 'A third party (translator, notary, test centre)',
  'detail.listedNotRanked': 'Listed, not ranked.',
  'detail.notVerified': ' · not verified',
  'detail.didNotAsk': ' · you did not ask',
  'detail.weight': '× weight',
  'detail.axesFootnote':
    'Match is a geometric mean over the axes above, so a near-zero one cannot be bought back by the others. Unverified axes stay out of it and lower {confirmed} instead.',
  'detail.noScore': 'No score was computed for this row.',
  'detail.noData': ' · no data',
  'detail.total': 'Total {total} of {max} possible',
  'detail.missingPenalty': '−{pct}% for {n} missing fields',
  'detail.disagree': 'Sources that disagree',
  'detail.askAdmissions': 'Question to send the admissions office',
  'detail.openQuestions': 'Open questions',
  'detail.evidenceCount': 'Evidence ({n} claims)',
  'detail.lastVerified': 'last verified {when} · {pct}% of decision-grade fields verified',

  'apply.automatic': 'Automatic',
  'apply.separate': 'Separate',
  'apply.nomination': 'Nomination',
  'apply.unknown': 'Unknown',
  'coverage.yes': 'yes',
  'coverage.no': 'no',
  'coverage.partial': 'partial',
  'coverage.unknown': 'unknown',
  'cost.tuition': 'Tuition',
  'cost.mandatory_fees': 'Mandatory fees',
  'cost.housing': 'Housing',
  'cost.meals': 'Meals',
  'cost.health_insurance': 'Health insurance',
  'cost.books': 'Books',
  'cost.travel': 'Travel',
  'cost.visa': 'Visa',
  'cost.personal': 'Personal',
  'axis.academic_fit': 'Academic fit',
  'axis.funding_fit': 'Funding fit',
  'axis.affordability': 'Affordability',
  'axis.country': 'Country',
  'axis.programme_standing': 'Programme standing',
  'axis.city': 'City',
  'axis.climate': 'Climate',
  'axis.university_size': 'University size',
  'axis.campus': 'Campus',
  'axis.workload': 'Workload',
  'axis.career': 'Career',
  'axis.post_study_work': 'Post study work',

  // --- funding comparison (screen 06) ------------------------------------
  'funding.eyebrow': 'Step 05',
  'funding.title': 'What you would actually pay',
  'funding.lede':
    'Cost of attendance against confirmed aid, in one currency. A hatched bar means the two figures are not comparable — different academic years, or an award with no published amount — and a zero is never shown in that case.',
  'funding.onlyFunded': 'Only substantially funded options',
  'funding.legendCovered': 'covered by aid',
  'funding.legendPay': 'you pay',
  'funding.barAria': '{pct} percent covered, {gap} remaining',
  'funding.costAid': '{cost} cost · {aid} aid',
  'funding.noCostInfo': 'No cost information was found.',
  'funding.yearMismatch': 'year mismatch',
  'funding.categoryMismatch': 'category mismatch',
  'funding.fullRideNote':
    'An award classified {label} means an official page confirms it covers tuition, mandatory fees, housing and meals or an equivalent stipend. It does not mean you will receive it — most of these are awarded competitively.',

  // --- sources & conflicts (screen 09) -----------------------------------
  'sources.eyebrow': 'Sources & evidence',
  'sources.title': 'See the proof behind every {highlight}',
  'sources.titleHighlight': 'match.',
  'sources.lede':
    'Explore verified claims, conflicting pages and unanswered questions. Open the original source whenever you need a closer look.',
  'sources.demoBody': 'These claims and source addresses come from a bundled synthetic corpus.',
  'sources.overviewAria': 'Evidence status',
  'sources.verifiedClaims': 'current verified claims',
  'sources.conflictsToReview': 'conflicts to review',
  'sources.openQuestions': 'open questions',
  'sources.filter.all': 'All ({n})',
  'sources.filter.conflicts': 'Conflicts ({n})',
  'sources.filter.questions': 'Open questions ({n})',
  'sources.filter.stale':
    'Possibly outdated claims ({n})',
  'sources.disagreeTitle': 'Sources that disagree ({n})',
  'sources.noConflicts': 'No contradictions were found between official sources.',
  'sources.unresolved': 'unresolved',
  'sources.moreSpecific': 'more specific source',
  'sources.draftQuestion': 'Draft question for the admissions office',
  'sources.copied': 'Copied',
  'sources.copy': 'Copy',
  'sources.questionsTitle': 'Open questions ({n})',
  'sources.questionsHint':
    'Things no official source answered. They are reported rather than filled in with a guess.',
  'sources.nothingOutstanding': 'Nothing outstanding.',
  'sources.staleTitle':
    'Possibly outdated claims ({n})',
  'sources.staleHint':
    'Read from an official page, but possibly not current: a fee for an earlier academic year, a date that has passed, or a check made too long ago. Each says why. Re-check them before you rely on them.',
  'sources.noStale':
    'No claim is marked as possibly outdated.',
  'sources.everySource': 'Every source consulted ({n})',
  'sources.everySourceAria': 'All consulted sources',
  'sources.schedule':
    'Claims are re-checked on a schedule that depends on what they are: deadlines and prices after 30 days, costs and award amounts after 120, policies after 180. Anything older is marked, not silently trusted. Last verification times are on each result.',
  'sources.mostRecent': ' Most recent: {when}.',

  // --- status chips (format.ts STATUS_LABEL / STATUS_MEANING) -------------
  // English is never read from here: the chip keeps format.ts's own English,
  // so a wording change there is not undone by a stale copy in this file.
  'status.MET': 'Met',
  'status.PENDING': 'Pending',
  'status.GAP': 'Gap',
  'status.NOT_APPLICABLE': 'N/A',
  'status.NEEDS_OFFICIAL_CLARIFICATION': 'Unverified',
  'status.STRONGER_FIT': 'Stronger',
  'status.PLAUSIBLE_FIT': 'Plausible',
  'status.AMBITIOUS': 'Ambitious',
  'status.INSUFFICIENT_DATA': 'No data',
  'status.FULL_RIDE_CONFIRMED': 'Full ride',
  'status.FULL_TUITION': 'Full tuition',
  'status.LARGE_GRANT': 'Large grant',
  'status.PARTIAL': 'Partial',
  'status.NEED_BASED_POSSIBLE': 'Need-based',
  'status.NOT_ELIGIBLE': 'Not eligible',
  'status.UNKNOWN': 'Unknown',
  'status.CONFIRMED_OPPORTUNITY': 'Confirmed',
  'status.COMPETITIVE_OPPORTUNITY': 'Competitive',
  'status.LIMITED_OPPORTUNITY': 'Limited',
  'status.WELL_PLACED': 'Well placed',
  'status.PLAUSIBLE': 'Plausible',
  'status.OUT_OF_BUDGET': 'Out of budget',
  'status.NEEDS_CLARIFICATION': 'Needs clarification',
  'status.EXCLUDED': 'Excluded',
  'status.VERIFIED_CURRENT': 'Verified',
  'status.POSSIBLY_STALE':
    'Possibly outdated',
  'status.CONFLICTING': 'Conflicting',
  'status.UNVERIFIED': 'Unverified',
  'status.NOT_FOUND': 'Not found',
  'status.SUPERSEDED': 'Superseded',

  'statusMeaning.MET': 'Every published requirement that could be checked is satisfied.',
  'statusMeaning.PENDING':
    'Nothing is failing, but something is still outstanding — a test, a document, or a profile field.',
  'statusMeaning.GAP': 'At least one published requirement is currently not met.',
  'statusMeaning.NOT_APPLICABLE': 'The requirement does not apply to this applicant.',
  'statusMeaning.NEEDS_OFFICIAL_CLARIFICATION':
    'The published requirement could not be verified against an official source.',
  'statusMeaning.STRONGER_FIT':
    'Scores sit clearly above the published minimums. Selection is still competitive.',
  'statusMeaning.PLAUSIBLE_FIT':
    'Formal requirements are met. The outcome depends on competitive selection.',
  'statusMeaning.AMBITIOUS': 'The profile sits at or below the published range.',
  'statusMeaning.INSUFFICIENT_DATA': 'Not enough verified data to compare the profile against.',
  'statusMeaning.FULL_RIDE_CONFIRMED':
    'An official source confirms tuition, mandatory fees, housing and meals (or a living stipend) are covered.',
  'statusMeaning.FULL_TUITION': 'Tuition is covered. Living costs are not fully covered.',
  'statusMeaning.LARGE_GRANT': 'A substantial award, but a meaningful part of the cost remains.',
  'statusMeaning.PARTIAL': 'Covers a limited share of the total cost.',
  'statusMeaning.NEED_BASED_POSSIBLE':
    'Depends on a financial-need assessment that has not been filed, so it cannot be sized.',
  'statusMeaning.NOT_ELIGIBLE': 'Published conditions exclude this applicant.',
  'statusMeaning.UNKNOWN': 'Not enough official information to classify.',
  'statusMeaning.CONFIRMED_OPPORTUNITY':
    'There is a confirmed opportunity to apply. The decision still rests with the university.',
  'statusMeaning.COMPETITIVE_OPPORTUNITY':
    'Eligible to apply by published criteria; awarded competitively.',
  'statusMeaning.LIMITED_OPPORTUNITY':
    'Funding exists but covers little, or cannot be assessed in advance.',
  'statusMeaning.VERIFIED_CURRENT': 'Read from an official page within its freshness window.',
  'statusMeaning.POSSIBLY_STALE':
    'Read from an official page, but it may no longer be current (an earlier academic year, a passed date, or a long time since it was checked). Re-check it before relying on it.',
  'statusMeaning.CONFLICTING': 'Two official sources disagree. Neither has been chosen as correct.',
  'statusMeaning.UNVERIFIED': 'Not confirmed against an official source.',
  'statusMeaning.NOT_FOUND': 'No source published this value.',
  'statusMeaning.WELL_PLACED':
    'Requirements met with room, funding confirmed, and the remaining cost within your ceiling.',
  'statusMeaning.PLAUSIBLE': 'Requirements and funding both look reachable on published data.',
  'statusMeaning.OUT_OF_BUDGET':
    'What remains to pay is past the ceiling you stated. The row is kept, with the number.',
  'statusMeaning.EXCLUDED':
    'A published requirement you do not meet, or a country you excluded. Listed, not ranked.',
  'statusMeaning.NEEDS_CLARIFICATION': 'Too little could be verified to place this row at all.',

  // --- backend sentences (app/domain/message_keys.py) ---------------------
  'msg.question.campus':
    '{university} offers {programme} on more than one campus, each a separate application. Which campus do you want?',
  'msg.question.entryRequirementsPage':
    'Which official page publishes entry requirements for {programme}?',
  'msg.question.programmePage':
    'Which official page publishes the {programme} programme?',
  'msg.question.noVerifiedDataInScope':
    'No verified data yet for {university}: the bachelor\'s in Computer Science.',
  'msg.question.noVerifiedDataOutOfScope':
    'No verified data yet for {university}: this programme (the knowledge base covers only the bachelor\'s in Computer Science).',
  'msg.question.supportForUncovered':
    'Is there any support for {categories} alongside {award}?',
  'msg.question.coop':
    'Does {programme} offer a co-op or placement year?',
  'msg.question.workHours':
    'How many hours a week may an international student work while studying in {country}?',
  'msg.question.researchGroups':
    'Which groups at {university} work on {interest}?',
  'msg.question.scholarshipsOpen':
    'What scholarships are open to international students on {programme}?',
  'msg.question.fundingPage':
    'Which official page publishes funding for {programme} at {university}?',
  'msg.question.pageScope':
    'Does {url} also apply to {programme} for the intake you are applying to? It is the only page we found stating this, and it {reason}.',
  'msg.question.previousCycleDeadline':
    '{url} states {value} as the deadline, which belongs to an earlier cycle than {intake}. When is the deadline for your intake?',
  'msg.question.satForAward':
    '{programme} is published as test-optional, but {award} requires an SAT score. Does the award\'s requirement still apply to applicants admitted without a test?',
  'msg.question.documents':
    'What documents does {university} require for {programme}?',
  'msg.question.awardStillOffered':
    'Is {award} still offered, and open to international applicants, for the {intake} intake?',
  'msg.question.confirmOnOfficialPage':
    'Confirm {field} on an official university page (current value {value} came from a non-official source).',
  'msg.question.nomination':
    'How are candidates nominated for \'{award}\', and is any action required from the applicant?',
  'msg.question.documentList':
    'What is the full list of required documents for {programme}?',
  'msg.why.campus':
    'Requirements, fees and deadlines can differ by campus. What was read on the {campuses} pages is not shown as this programme\'s.',
  'msg.why.catalogueOnly':
    'This university was found through a catalogue only. Nothing about it has been verified against an official source.',
  'msg.why.programmePageUnverified':
    'The facts shown for this university were verified on its official site, but the verified knowledge base has no verified page for this programme yet, so that the programme is offered for this intake is not confirmed.',
  'msg.why.noKbEntry':
    'Live research is switched off and this university has no entry in the verified knowledge base, so nothing about it is shown or guessed. Its official site or admissions office is the source until it is added.',
  'msg.why.kbOutOfScope':
    'Live research is switched off and the verified knowledge base answers only for the bachelor\'s in Computer Science, so nothing about this programme is shown or guessed. Its official site or admissions office is the source until it is added.',
  'msg.why.uncoveredCosts':
    'The profile lists {categories} as costs that must be covered, and this award excludes them. The gap is real money the family would have to find.',
  'msg.why.coop':
    'The profile says co-op programmes matter. Nothing on the pages read states whether this programme has one.',
  'msg.why.workHours':
    'The profile says work during study is necessary, and no official statement of the limit was found.',
  'msg.why.researchInterest':
    'The profile lists {interest} as a research interest. The pages read do not mention it, which is not the same as it being absent.',
  'msg.why.noFundingPage':
    'No official funding page could be read, so funding is unknown, not absent.',
  'msg.why.unmatchedFunding':
    'This programme could not be matched back to a discovered university, so no scholarship page was read for it. Nothing here is assumed.',
  'msg.why.pageScope':
    'The page was read correctly, but it states it is about something else, so nothing here is claimed from it. An admissions office can confirm in one reply whether the same rule applies to your intake.',
  'msg.why.previousCycleDeadline':
    'The page has not yet published the dates for your intake; the previous cycle\'s date is shown only as a guide.',
  'msg.why.satForAward':
    'Skipping the SAT on the strength of the admissions page can cost this award rather than the offer, and the two pages are published by different offices.',
  'msg.why.unmatchedDocuments':
    'This approved programme could not be matched back to a discovered university, so its document list was never read.',
  'msg.why.kbNoDocuments':
    'The verified knowledge base does not hold document lists yet, and live research is switched off, so nothing was read or assumed.',
  'msg.why.awardStale':
    'What the verified knowledge base holds about this award is stale ({reasons}), so it is not shown as current and does not count as funding until the scholarships office confirms it.',
  'msg.why.aggregator':
    'Aggregator data is frequently out of date for this field.',
  'msg.why.nomination':
    'A nomination-only award cannot be applied for directly; missing the internal process means missing the award entirely.',
  'msg.why.noDocumentList':
    'No official document list could be read, so nothing can be prepared in advance.',
  'msg.stale.noDate':
    'no verification date',
  'msg.stale.tooOld':
    'verified on {date}, more than {days} days ago',
  'msg.stale.yearBeforeIntake':
    'academic year {year} is before the {intake} intake\'s {wanted}',
  'msg.stale.yearPast':
    'academic year {year} is past',
  'msg.stale.deadlinePassed':
    'deadline {date} has passed',
  'msg.stale.publishedForYear':
    'published for academic year {year}',
  'msg.stale.yearNotStated':
    'the academic year is not stated',
  'msg.stale.publishedForCycle':
    'published for the {year} cycle',
  'msg.stale.documentsForCycle':
    'document list published for "{cycle}", not the {intake} intake',
  'msg.stale.documentsAnotherCycle':
    'document list published for another cycle, not the {intake} intake',
  'msg.stale.documentItem':
    '{document} ({reasons})',
  'msg.caveat.yearInferred':
    'year not printed on the page; assumed current application cycle',
  'msg.caveat.feePolicy':
    'fee policy page; no academic year printed',
  'msg.gap.mixedYears':
    'Published cost components come from different academic years ({years}). They are not summed, because a mixed-year total would misstate the real cost.',
  'msg.gap.noCost':
    'No official cost of attendance was found for this programme and intake.',
  'msg.gap.partialCost':
    'Only part of the core cost of attendance is published, so the full annual cost is unknown and no remaining-cost figure is computed.',
  'msg.gap.noAwardAmount':
    'Cost of attendance is known, but no scholarship with an officially published amount was found, so the remaining cost cannot be estimated.',
  'msg.gap.zeroNotComparable':
    'The arithmetic reaches zero, but the cost and coverage figures are not comparable, so a zero remaining cost would be misleading.',
  'msg.gap.computed':
    'Remaining annual cost after officially published, applicable aid.',
  'msg.gap.recheckSingleYear':
    'Re-check the cost pages for a single academic year.',
  'msg.gap.costUnverified':
    'Cost pages could not be verified; the gap cannot be estimated.',
  'msg.gap.needBasedExcluded':
    'A need-based award was found but cannot be sized before a need assessment is filed; it is excluded from this calculation.',
  'msg.gap.awardNoAmount':
    '\'{award}\': no officially published amount, excluded from the arithmetic.',
  'msg.gap.notItemised':
    'The cost table does not itemise {categories}; the figure shown is the known subtotal, a lower bound on the real cost of attendance.',
  'msg.gap.notStackable':
    '\'{award}\' states it may not be combined with other awards, so other scholarships are not added on top even where they permit stacking.',
  'msg.gap.yearMismatch':
    'Cost is published for {costYear} but the award amount for {awardYear}. The figures below are not directly comparable.',
  'msg.gap.coverageIncomplete':
    'Award coverage does not name every cost category the university publishes: {categories}',
  'msg.gap.costRange':
    'Cost of attendance is published as a range; the gap is shown as a range.',
  'msg.gap.aidExceedsCost':
    'Confirmed aid exceeds the published cost of attendance. The surplus is not assumed to be paid out; the remaining cost is reported as zero.',
  'msg.funding.noInformation':
    'No scholarship information was found on official sources for this programme.',
  'msg.funding.allExclude':
    'Every scholarship found for this programme officially excludes this applicant.',
  'msg.funding.wrongShape':
    'Awards were found, but none is the kind of funding this profile says it needs; each says why on its own row.',
  'msg.funding.coverageUnclear':
    'Scholarships exist but official coverage detail is insufficient to classify them.',
  'msg.funding.needBased':
    'Support depends on a financial-need assessment that cannot be evaluated in advance.',
  'msg.funding.automatic':
    '\'{award}\' is awarded automatically on the admission application against published criteria; the award decision still depends on the university.',
  'msg.funding.nomination':
    '\'{award}\' requires a departmental nomination, so it cannot be applied for directly.',
  'msg.funding.competitive':
    '\'{award}\' is open to this applicant by published criteria and is awarded by competitive selection.',
  'msg.funding.limited':
    'The strongest confirmed option, \'{award}\', covers only a limited share of cost.',
  'msg.funding.noneOffered':
    'No institutional scholarship: {university} states that it offers none for this applicant ("{quote}", {url}).',
  'msg.funding.noneStale':
    'No institutional scholarship was stated by {university}, but the statement is stale ({reasons}), so funding is unknown, not confirmed absent.',
  'detail.noRequirementsLive':
    'No published requirements could be read for this programme, so nothing has been compared against your profile.',
  'detail.noRequirementsKb':
    'The verified knowledge base holds no requirement for this programme that could be compared against your profile.',
  'detail.reportedUnknown':
    'This is reported as unknown, not as a pass.',
  'detail.noScholarshipKb':
    'The verified knowledge base names no scholarship for this programme, and live research is switched off, so no scholarship page was read. Funding is {unknown} — that is not the same as there being none.',
  'detail.openQuestion':
    'Open question:',
  'detail.unusedTuition':
    'An official tuition fee was found, but not as this intake\'s yearly cost, so it is not in the cost table:',
  'msg.question.kbScholarships':
    'Which scholarships does {university} offer international students on {programme}?',
  'msg.question.kbEntryRequirements':
    'Which entry requirements does {university} publish for {programme}, and does your profile meet them?',
  'msg.question.languageInstead':
    '{statement} Which language certificate does {university} require instead, and do you hold it?',
  'msg.question.gradesInstead':
    '{statement} Which grades or scores does {university} use instead, and does your record meet them?',
  'msg.question.requireInstead':
    '{statement} What does {university} require instead?',
  'msg.why.kbNoAward':
    'The verified knowledge base names no award for this programme, and live research is switched off, so no scholarship page was read. Funding is unknown, not confirmed absent.',
  'msg.why.kbRequirementsUnsettled':
    'The verified knowledge base holds facts for this programme, but its {requirements} could not be settled from them, so eligibility is shown as needing clarification rather than as met.',
  'msg.why.kbNoComparableRequirement':
    'The verified knowledge base holds facts for this programme, but none of them is an entry requirement this profile can be compared against, so eligibility is shown as needing clarification rather than as met.',
  'msg.why.verifiedStatement':
    'Verified on the official page {url}: "{quote}". The profile has no field this can be compared against, so it is not counted as met or as failed.',
  'msg.question.documentListCurrent':
    'Is the document list for {programme} at {university} still the one for the {intake} intake?',
  'msg.why.documentsNotCurrent':
    'The verified knowledge base holds these documents, but not as current: {documents}. They are listed so you can prepare, not as confirmed.',
  'msg.gap.feeOtherYear':
    'An official tuition fee was found, but for another academic year than the {intake} intake: {fees}. It is not used as this intake\'s cost, so the remaining cost is not computed.',
  'msg.gap.feeNotYearly':
    'An official tuition fee was found, but not as a current yearly figure for the {intake} intake: {fees}. It is not used as this intake\'s cost, so the remaining cost is not computed.',
  'msg.gap.confirmIntakeFee':
    'Confirm the {intake} fee with the university before relying on a cost figure.',
} as const;

export type ResultsKey = keyof typeof EN_RESULTS;

/** Russian. Plain, everyday words; product terms as recorded in the glossary. */
export const RU_RESULTS: Record<ResultsKey, string> = {
  'results.empty.title': 'Результатов пока нет',
  'results.empty.runFirst': 'Сначала запустите исследование.',
  'results.notEnoughData': 'Недостаточно сопоставимых данных',
  'results.notConfirmed': 'Не подтверждено',
  'results.notFound': 'не найдено',
  'results.notPublished': 'не опубликовано',
  'results.notComputable': 'нельзя рассчитать',
  'results.notComparable': 'нельзя сравнить',
  'results.blocking': 'важно',
  'results.open': 'открыт',
  'results.yes': 'Да',
  'results.no': 'Нет',
  'results.remove': 'Убрать',
  'results.compare': 'Сравнить',
  'results.cancel': 'Отмена',
  'results.demoData': 'Демо-данные.',
  'results.notCurrent': 'Не актуально: {reason}.',
  'results.staleAge': '{days} дн. назад',
  'results.staleNoAge': 'не актуально',
  'results.currentWithCaveat': 'Актуально, с оговоркой',
  'results.caveat': 'Оговорка: {caveat}.',
  'results.conflictCount.one': 'Расхождений: {n}',
  'results.conflictCount.other': 'Расхождений: {n}',
  'results.questionCount.one': 'Открытых вопросов: {n}',
  'results.questionCount.other': 'Открытых вопросов: {n}',
  'results.fitDisclaimer':
    'Насколько вариант подходит под ваши приоритеты — по подтверждённым данным. Это не вероятность поступления.',

  'col.university': 'Университет и программа',
  'col.eligibility': 'Требования',
  'col.admissionsFit': 'Уровень профиля',
  'col.funding': 'Финансирование',
  'col.remaining': 'Остаток в год',
  'col.remainingPerYear': 'Остаток к оплате в год',
  'col.deadline': 'Срок подачи',
  'col.match': 'Совпадение',
  'col.confirmed': 'Подтверждено',
  'col.confirmedHint': 'Какая часть оценки опирается на данные, которые мы подтвердили.',
  'col.bucket': 'Группа',
  'col.decision': 'Решение',

  'shortlist.hint.OUT_OF_BUDGET':
    'Не скрываем, а показываем с суммой: возможно, вы знаете о деньгах то, чего не знаем мы.',
  'shortlist.hint.NEEDS_CLARIFICATION':
    'Подтвердить удалось слишком мало, чтобы их распределить. Задайте приёмной комиссии открытые вопросы из строки.',
  'shortlist.hint.EXCLUDED': 'Не выполнено опубликованное требование, или это страна, которую вы исключили.',
  'shortlist.reason.cost': 'дорого',
  'shortlist.reason.deadline passed': 'срок прошёл',
  'shortlist.reason.no funding': 'нет финансирования',
  'shortlist.reason.not a fit': 'не подходит',
  'shortlist.emptyEyebrow': 'НАЙДИТЕ СВОЙ ПУТЬ',
  'shortlist.title': 'Найдите лучшие {highlight}',
  'shortlist.titleHighlight': 'варианты.',
  'shortlist.emptyLede': 'Исследование начинается с вашего профиля и предпочтений.',
  'shortlist.emptyBody': 'Запустите исследование, чтобы найти программы, подкреплённые доступными источниками.',
  'shortlist.start': 'Начать исследование →',
  'shortlist.passed': 'прошёл',
  'shortlist.previousCycle': 'прошлый набор: {date}',
  'shortlist.notRanked': 'без места в рейтинге',
  'shortlist.decisionFor': 'Решение по {university}',
  'shortlist.maybe': 'Может быть',
  'shortlist.whyNot': 'Почему не этот? (необязательно — причина сохранится в строке)',
  'shortlist.whyNotPlaceholder': 'дорого, сроки, не подходит…',
  'shortlist.saveRejection': 'Сохранить отказ',
  'shortlist.rejected': 'Отклонено: {reason}',
  'shortlist.editNote': 'Изменить заметку',
  'shortlist.addNote': 'Добавить заметку',
  'shortlist.notePlaceholder': 'Почему этот?',
  'shortlist.saveNote': 'Сохранить заметку',
  'shortlist.exploreCatalogue': 'Посмотреть другие университеты из каталога',
  'shortlist.eyebrow': 'ВОЗМОЖНОСТИ ПО ВСЕМУ МИРУ. ЧЕСТНЫЙ ПОДБОР.',
  'shortlist.lede':
    'Программы, которые подходят под ваши цели, бюджет и планы. Откройте любой результат, чтобы увидеть источники и то, что пока неизвестно.',
  'shortlist.mascotAlt': 'Талисман Unimatch исследует горный пейзаж',
  'shortlist.demoBody':
    'Эти цифры взяты из встроенного синтетического набора, а не с настоящих страниц университетов. Каждый источник ниже — адрес {code}.',
  'shortlist.search': 'Поиск по университетам, программам и странам',
  'shortlist.searchPlaceholder': 'Университет, программа или страна…',
  'shortlist.filters': 'Фильтры',
  'shortlist.compareCount': 'Сравнить ({n})',
  'shortlist.matchList': 'Список вариантов',
  'shortlist.tab.all': 'Все',
  'shortlist.tab.priority': 'Приоритетные',
  'shortlist.tab.saved': 'Сохранённые',
  'shortlist.tab.exploring': 'Изучаю',
  'shortlist.filterSort': 'Фильтры и сортировка',
  'shortlist.country': 'Страна',
  'shortlist.sortBy': 'Сортировка',
  'shortlist.allCount': 'Все ({n})',
  'shortlist.any': 'Любое',
  'shortlist.sort.key': 'Совпадение с поправкой на неподтверждённое',
  'shortlist.sort.fit': 'Совпадение с вашими приоритетами',
  'shortlist.sort.coverage': 'Больше всего подтверждено',
  'shortlist.sort.gap': 'Наименьший остаток к оплате',
  'shortlist.sort.deadline': 'Ближайший срок подачи',
  'shortlist.sort.university': 'Название университета',
  'shortlist.hideRejected': 'Скрыть отклонённые',
  'shortlist.resultCount.one': 'Результатов этого исследования: {n}',
  'shortlist.resultCount.other': 'Результатов этого исследования: {n}',
  'shortlist.noMatchTitle': 'Под эти фильтры пока ничего не подходит.',
  'shortlist.noMatchBody': 'Попробуйте другой запрос или сбросьте фильтры.',
  'shortlist.clearFilters': 'Сбросить фильтры',
  'shortlist.hideDetails': 'Скрыть подробности',
  'shortlist.viewDetails': 'Подробнее',
  'shortlist.saved': 'Сохранено',
  'shortlist.save': 'Сохранить',
  'shortlist.evidenceTable': 'Подробная таблица с источниками',
  'shortlist.balancedTitle': 'Сбалансированный короткий список',
  'shortlist.balancedHint':
    'Сначала заполняются квоты, потом работает рейтинг: десять самых амбициозных вариантов — это список, с которым ничего не сделаешь.',
  'shortlist.caption':
    'Программы из короткого списка: требования, уровень профиля, финансирование и остаток к оплате',
  'shortlist.captionSetAside':
    'Программы, отложенные в группу «{bucket}»: требования, уровень профиля, финансирование и остаток к оплате',
  'shortlist.nothingRanked':
    'Здесь нет вариантов, которые одновременно по карману и достаточно подтверждены для рейтинга. Каждый вариант — в одном из разделов ниже, с причиной.',
  'shortlist.rankedFootnote':
    'Показано {shown} из {total} строк рейтинга. {match} — насколько место подходит под указанные вами приоритеты, по подтверждённым данным; это не вероятность поступления. Процент {confirmed} — какая часть этой оценки опирается на данные, которые удалось проверить.',
  'shortlist.footnote':
    'Показано {shown} из {total}. Отклонённые строки хранятся вместе с причиной, чтобы та же программа не предлагалась снова без новых сведений.',

  'compare.aria': 'Сравнение выбранных программ',
  'compare.eyebrow': 'СРАВНИТЕ СПОКОЙНО',
  'compare.title': 'Разные сильные стороны. Более ясный выбор.',
  'compare.clear': 'Очистить',
  'compare.lede':
    'Сравнивайте то, что действительно подтверждают источники. Совпадение описывает ваши приоритеты, а не шансы на поступление.',
  'compare.preferenceFit': 'Совпадение с приоритетами',
  'compare.coverage': 'Подтверждённость',
  'compare.coverageHint': 'Какая часть данных, нужных для этой оценки, подтверждена',
  'compare.notAssessed': 'Не оценивалось',
  'compare.toClarify': 'Уточнить: {n}',
  'compare.whyFit': 'Почему такая оценка?',

  'detail.tab.requirements': 'Требования',
  'detail.tab.funding': 'Финансирование',
  'detail.tab.costs': 'Расходы',
  'detail.tab.documents': 'Документы',
  'detail.tab.score': 'Почему такой порядок',
  'detail.tab.sources': 'Источники',
  'detail.eyebrow': 'О ПРОГРАММЕ · {country}',
  'detail.assessment': 'ВАША ОЦЕНКА',
  'detail.assessmentNote':
    'Соответствие требованиям и уровень профиля — разные вещи. Ни то, ни другое не вероятность поступления.',
  'detail.evidence': 'Источники',
  'detail.tabsAria': '{university}: подробности',
  'detail.requirementNotMet': 'Подтверждённое требование не выполнено:',
  'detail.requirementNotMetNote':
    'Это взято с официальной страницы, поэтому считается реальным препятствием, а не пробелом в наших данных.',
  'detail.published': 'требуется',
  'detail.you': 'у вас',
  'detail.deadlineLine': 'Срок подачи: {date}',
  'detail.deadlinePassed': 'срок подачи прошёл',
  'detail.previousCycle': 'Прошлый набор: {date}',
  'detail.noScholarship':
    'Не удалось прочитать ни одной официальной страницы о стипендиях для этой программы. Финансирование {unknown} — это не то же самое, что его нет.',
  'detail.unknown': 'неизвестно',
  'detail.value': 'Размер',
  'detail.percentOfTuition': '{pct}% стоимости обучения',
  'detail.openToYou': 'Доступна вам',
  'detail.restrictedTo': 'только для: {list}',
  'detail.internationalEligible': 'доступна иностранным студентам',
  'detail.notInternational': 'недоступна иностранным студентам',
  'detail.eligibilityNotPublished': 'условия не опубликованы',
  'detail.howToApply': 'Как подать заявку',
  'detail.extraEssays': ' · нужны дополнительные эссе',
  'detail.offerRequired': 'Подать на эту стипендию можно только после получения приглашения на учёбу.',
  'detail.offerNotRequired': 'На эту стипендию можно подать до получения приглашения на учёбу.',
  'detail.needBased': 'Решение принимается с учётом подтверждённой финансовой нужды.',
  'detail.renewal': 'Продление',
  'detail.renewable': 'Продлевается',
  'detail.renewableYears': 'Продлевается, до {n} лет',
  'detail.oneTime': 'Разовая выплата',
  'detail.stackable': 'Сочетается с другими',
  'detail.covers': 'Покрывает',
  'detail.awardsOffered': 'Число стипендий',
  'detail.officiallyPublished': '{n} (по официальным данным)',
  'detail.noCost': 'Официальная стоимость обучения и проживания для этой программы и набора не найдена.',
  'detail.publishedTotal': 'Опубликованный итог',
  'detail.knownSoFar': 'Известная на сейчас стоимость',
  'detail.lowerBound':
    'Расписаны только некоторые основные статьи расходов, поэтому эта сумма — известная часть, нижняя граница реальной стоимости, а не полная стоимость. Остаток к оплате от наполовину известной суммы не считается.',
  'detail.notItemised': '{category}: не указано',
  'detail.remainingAnnual': 'Остаток к оплате за год',
  'detail.costOfAttendance': 'Стоимость обучения и проживания',
  'detail.confirmedAid': 'Подтверждённая помощь',
  'detail.stackedAid': 'Дополнительная помощь',
  'detail.notComputed': 'Не рассчитано.',
  'detail.documentsLater':
    'Документы собираются только для одобренных вами программ — это самый затратный шаг, поэтому он выполняется для вашего короткого списка, а не для всех вариантов. Одобрите эту строку и запустите «Собрать документы».',
  'detail.docs.official': 'прочитано с официальных страниц',
  'detail.docs.partial': 'прочитано частично',
  'detail.docs.unavailable': 'официальный список не найден',
  'detail.docs.kb.official': 'из проверенной базы знаний',
  'detail.docs.kb.partial': 'проверено, часть пунктов не актуальна',
  'detail.docs.kb.unavailable': 'в проверенной базе знаний списка нет',
  'detail.docs.leadTime.one': 'заложите ~{n} день',
  'detail.docs.leadTime.few': 'заложите ~{n} дня',
  'detail.docs.leadTime.many': 'заложите ~{n} дней',
  'detail.docs.leadTime.other': 'заложите ~{n} дня',
  'detail.generated': 'составлено {when}',
  'detail.docs.required': 'Обязательно',
  'detail.docs.optional': 'По желанию',
  'detail.docs.conditional': 'При условии',
  'detail.docs.condition': 'Условие, как опубликовано: {condition}.',
  'detail.docs.order': 'Рекомендуемый порядок: сначала то, что готовится дольше',
  'detail.docs.owner.applicant': 'Готовите вы',
  'detail.docs.owner.school': 'Ваша школа',
  'detail.docs.owner.recommender': 'Ваш рекомендатель',
  'detail.docs.owner.third_party': 'Третья сторона (переводчик, нотариус, тестовый центр)',
  'detail.listedNotRanked': 'В списке, но без места в рейтинге.',
  'detail.notVerified': ' · не подтверждено',
  'detail.didNotAsk': ' · вы не указывали',
  'detail.weight': '× вес',
  'detail.axesFootnote':
    'Совпадение — среднее геометрическое по критериям выше, поэтому почти нулевой критерий не перекрыть остальными. Неподтверждённые критерии в расчёт не входят и вместо этого снижают {confirmed}.',
  'detail.noScore': 'Для этой строки оценка не рассчитывалась.',
  'detail.noData': ' · нет данных',
  'detail.total': 'Итого {total} из {max} возможных',
  'detail.missingPenalty': '−{pct}% за {n} незаполненных полей',
  'detail.disagree': 'Источники расходятся',
  'detail.askAdmissions': 'Вопрос для приёмной комиссии',
  'detail.openQuestions': 'Открытые вопросы',
  'detail.evidenceCount': 'Факты из источников ({n})',
  'detail.lastVerified': 'последняя проверка {when} · подтверждено {pct}% ключевых полей',

  'apply.automatic': 'Автоматически',
  'apply.separate': 'Отдельная заявка',
  'apply.nomination': 'По выдвижению',
  'apply.unknown': 'Неизвестно',
  'coverage.yes': 'да',
  'coverage.no': 'нет',
  'coverage.partial': 'частично',
  'coverage.unknown': 'неизвестно',
  'cost.tuition': 'Обучение',
  'cost.mandatory_fees': 'Обязательные сборы',
  'cost.housing': 'Жильё',
  'cost.meals': 'Питание',
  'cost.health_insurance': 'Медицинская страховка',
  'cost.books': 'Книги',
  'cost.travel': 'Дорога',
  'cost.visa': 'Виза',
  'cost.personal': 'Личные расходы',
  'axis.academic_fit': 'Академический уровень',
  'axis.funding_fit': 'Финансирование',
  'axis.affordability': 'Доступность по цене',
  'axis.country': 'Страна',
  'axis.programme_standing': 'Позиция программы',
  'axis.city': 'Город',
  'axis.climate': 'Климат',
  'axis.university_size': 'Размер университета',
  'axis.campus': 'Кампус',
  'axis.workload': 'Нагрузка',
  'axis.career': 'Карьера',
  'axis.post_study_work': 'Работа после учёбы',

  'funding.eyebrow': 'Шаг 05',
  'funding.title': 'Сколько вы заплатите на самом деле',
  'funding.lede':
    'Стоимость обучения и проживания против подтверждённой помощи, в одной валюте. Заштрихованная полоса значит, что эти две суммы нельзя сравнить — разные учебные годы или стипендия без опубликованной суммы, — и ноль в таком случае не показывается.',
  'funding.onlyFunded': 'Только варианты с существенным финансированием',
  'funding.legendCovered': 'покрыто помощью',
  'funding.legendPay': 'платите вы',
  'funding.barAria': 'покрыто {pct} процентов, остаток {gap}',
  'funding.costAid': 'стоимость {cost} · помощь {aid}',
  'funding.noCostInfo': 'Сведений о стоимости не найдено.',
  'funding.yearMismatch': 'разные годы',
  'funding.categoryMismatch': 'разные статьи расходов',
  'funding.fullRideNote':
    'Статус {label} значит, что официальная страница подтверждает: стипендия покрывает обучение, обязательные сборы, жильё и питание или равноценную ежемесячную выплату. Это не значит, что вы её получите — большинство таких стипендий дают по конкурсу.',

  'sources.eyebrow': 'Источники',
  'sources.title': 'Доказательства за каждым {highlight}',
  'sources.titleHighlight': 'вариантом.',
  'sources.lede':
    'Подтверждённые факты, страницы с расхождениями и вопросы без ответа. Открывайте исходную страницу, когда нужно присмотреться.',
  'sources.demoBody': 'Эти факты и адреса источников взяты из встроенного синтетического набора.',
  'sources.overviewAria': 'Состояние источников',
  'sources.verifiedClaims': 'актуальных подтверждённых фактов',
  'sources.conflictsToReview': 'расхождений проверить',
  'sources.openQuestions': 'открытых вопросов',
  'sources.filter.all': 'Все ({n})',
  'sources.filter.conflicts': 'Расхождения ({n})',
  'sources.filter.questions': 'Открытые вопросы ({n})',
  'sources.filter.stale':
    'Возможно устаревшие факты ({n})',
  'sources.disagreeTitle': 'Источники расходятся ({n})',
  'sources.noConflicts': 'Расхождений между официальными источниками не найдено.',
  'sources.unresolved': 'не решено',
  'sources.moreSpecific': 'более точный источник',
  'sources.draftQuestion': 'Черновик вопроса для приёмной комиссии',
  'sources.copied': 'Скопировано',
  'sources.copy': 'Копировать',
  'sources.questionsTitle': 'Открытые вопросы ({n})',
  'sources.questionsHint':
    'То, на что не ответил ни один официальный источник. Мы сообщаем об этом, а не заполняем догадкой.',
  'sources.nothingOutstanding': 'Открытых вопросов нет.',
  'sources.staleTitle':
    'Возможно устаревшие факты ({n})',
  'sources.staleHint':
    'Прочитано на официальной странице, но, возможно, уже не актуально: стоимость за прошлый учебный год, прошедшая дата или слишком давняя проверка. У каждого указана причина. Перепроверьте, прежде чем на них полагаться.',
  'sources.noStale':
    'Ни один факт не помечен как возможно устаревший.',
  'sources.everySource': 'Все просмотренные источники ({n})',
  'sources.everySourceAria': 'Все просмотренные источники',
  'sources.schedule':
    'Факты перепроверяются по графику, который зависит от их вида: сроки и цены — через 30 дней, стоимость и размеры стипендий — через 120, правила — через 180. Всё, что старше, помечается, а не принимается на веру. Время последней проверки указано у каждого результата.',
  'sources.mostRecent': ' Последняя: {when}.',

  'status.MET': 'Выполнено',
  'status.PENDING': 'Ожидается',
  'status.GAP': 'Не выполнено',
  'status.NOT_APPLICABLE': 'Не относится',
  'status.NEEDS_OFFICIAL_CLARIFICATION': 'Не подтверждено',
  'status.STRONGER_FIT': 'Выше требований',
  'status.PLAUSIBLE_FIT': 'Достижимо',
  'status.AMBITIOUS': 'Амбициозно',
  'status.INSUFFICIENT_DATA': 'Нет данных',
  'status.FULL_RIDE_CONFIRMED': 'Полное покрытие',
  'status.FULL_TUITION': 'Обучение полностью',
  'status.LARGE_GRANT': 'Крупный грант',
  'status.PARTIAL': 'Частично',
  'status.NEED_BASED_POSSIBLE': 'По нуждаемости',
  'status.NOT_ELIGIBLE': 'Не подходит',
  'status.UNKNOWN': 'Неизвестно',
  'status.CONFIRMED_OPPORTUNITY': 'Подтверждено',
  'status.COMPETITIVE_OPPORTUNITY': 'По конкурсу',
  'status.LIMITED_OPPORTUNITY': 'Ограничено',
  'status.WELL_PLACED': 'Хорошая позиция',
  'status.PLAUSIBLE': 'Достижимо',
  'status.OUT_OF_BUDGET': 'Сверх бюджета',
  'status.NEEDS_CLARIFICATION': 'Нужно уточнить',
  'status.EXCLUDED': 'Исключено',
  'status.VERIFIED_CURRENT': 'Проверено',
  'status.POSSIBLY_STALE':
    'Возможно устарело',
  'status.CONFLICTING': 'Источники расходятся',
  'status.UNVERIFIED': 'Не проверено',
  'status.NOT_FOUND': 'Не найдено',
  'status.SUPERSEDED': 'Заменено',

  'statusMeaning.MET': 'Все опубликованные требования, которые удалось проверить, выполнены.',
  'statusMeaning.PENDING':
    'Ничего не нарушено, но кое-что ещё не готово — экзамен, документ или поле профиля.',
  'statusMeaning.GAP': 'Хотя бы одно опубликованное требование сейчас не выполнено.',
  'statusMeaning.NOT_APPLICABLE': 'Это требование к вам не относится.',
  'statusMeaning.NEEDS_OFFICIAL_CLARIFICATION':
    'Опубликованное требование не удалось подтвердить по официальному источнику.',
  'statusMeaning.STRONGER_FIT':
    'Баллы заметно выше опубликованных минимумов. Отбор всё равно конкурсный.',
  'statusMeaning.PLAUSIBLE_FIT':
    'Формальные требования выполнены. Результат зависит от конкурсного отбора.',
  'statusMeaning.AMBITIOUS': 'Профиль на уровне опубликованного диапазона или ниже.',
  'statusMeaning.INSUFFICIENT_DATA': 'Недостаточно подтверждённых данных, чтобы сравнить с ними профиль.',
  'statusMeaning.FULL_RIDE_CONFIRMED':
    'Официальный источник подтверждает, что покрыты обучение, обязательные сборы, жильё и питание (или ежемесячная выплата на жизнь).',
  'statusMeaning.FULL_TUITION': 'Обучение покрыто. Расходы на жизнь покрыты не полностью.',
  'statusMeaning.LARGE_GRANT': 'Крупная стипендия, но заметная часть стоимости остаётся.',
  'statusMeaning.PARTIAL': 'Покрывает небольшую часть общей стоимости.',
  'statusMeaning.NEED_BASED_POSSIBLE':
    'Зависит от оценки финансовой нужды, заявка на которую не подана, поэтому размер неизвестен.',
  'statusMeaning.NOT_ELIGIBLE': 'Опубликованные условия вас исключают.',
  'statusMeaning.UNKNOWN': 'Недостаточно официальных сведений, чтобы классифицировать.',
  'statusMeaning.CONFIRMED_OPPORTUNITY':
    'Подтверждена возможность подать заявку. Решение всё равно за университетом.',
  'statusMeaning.COMPETITIVE_OPPORTUNITY':
    'По опубликованным условиям подать можно; присуждается по конкурсу.',
  'statusMeaning.LIMITED_OPPORTUNITY':
    'Финансирование есть, но покрывает мало или его нельзя оценить заранее.',
  'statusMeaning.VERIFIED_CURRENT': 'Прочитано на официальной странице, срок актуальности не истёк.',
  'statusMeaning.POSSIBLY_STALE':
    'Прочитано на официальной странице, но может быть уже не актуально (прошлый учебный год, прошедшая дата или давняя проверка). Перепроверьте, прежде чем на это полагаться.',
  'statusMeaning.CONFLICTING': 'Два официальных источника расходятся. Ни один не выбран как верный.',
  'statusMeaning.UNVERIFIED': 'Не подтверждено официальным источником.',
  'statusMeaning.NOT_FOUND': 'Ни один источник не публиковал это значение.',
  'statusMeaning.WELL_PLACED':
    'Требования выполнены с запасом, финансирование подтверждено, а остаток к оплате укладывается в ваш потолок.',
  'statusMeaning.PLAUSIBLE': 'И требования, и финансирование по опубликованным данным выглядят достижимыми.',
  'statusMeaning.OUT_OF_BUDGET':
    'Остаток к оплате выше указанного вами потолка. Строка сохранена вместе с суммой.',
  'statusMeaning.EXCLUDED':
    'Опубликованное требование, которое вы не выполняете, или страна, которую вы исключили. В списке, но без места в рейтинге.',
  'statusMeaning.NEEDS_CLARIFICATION': 'Подтвердить удалось слишком мало, чтобы вообще распределить эту строку.',

  'msg.question.campus':
    '{university} предлагает {programme} в нескольких кампусах, и в каждый подаётся отдельная заявка. Какой кампус вам нужен?',
  'msg.question.entryRequirementsPage':
    'На какой официальной странице опубликованы требования для поступления на {programme}?',
  'msg.question.programmePage':
    'На какой официальной странице опубликована программа {programme}?',
  'msg.question.noVerifiedDataInScope':
    'Проверенных данных по {university} пока нет: бакалавриат по Computer Science.',
  'msg.question.noVerifiedDataOutOfScope':
    'Проверенных данных по {university} пока нет: эта программа (база знаний охватывает только бакалавриат по Computer Science).',
  'msg.question.supportForUncovered':
    'Есть ли какая-то поддержка на {categories} помимо стипендии {award}?',
  'msg.question.coop':
    'Есть ли в программе {programme} co-op или год практики?',
  'msg.question.workHours':
    'Сколько часов в неделю иностранный студент может работать во время учёбы (страна: {country})?',
  'msg.question.researchGroups':
    'Какие группы в {university} занимаются темой «{interest}»?',
  'msg.question.scholarshipsOpen':
    'Какие стипендии доступны иностранным студентам программы {programme}?',
  'msg.question.fundingPage':
    'На какой официальной странице опубликовано финансирование программы {programme} в {university}?',
  'msg.question.pageScope':
    'Относится ли {url} также к программе {programme} на ваш набор? Это единственная найденная страница с этими сведениями, и она {reason}.',
  'msg.question.previousCycleDeadline':
    'На {url} указан срок подачи {value}, но он относится к более раннему набору, чем {intake}. Какой срок подачи на ваш набор?',
  'msg.question.satForAward':
    'Программа {programme} объявлена как test-optional, но для стипендии {award} нужен балл SAT. Действует ли это требование для принятых без экзамена?',
  'msg.question.documents':
    'Какие документы {university} требует для программы {programme}?',
  'msg.question.awardStillOffered':
    'Предлагается ли ещё стипендия {award} и доступна ли она иностранным абитуриентам на набор {intake}?',
  'msg.question.confirmOnOfficialPage':
    'Подтвердите «{field}» на официальной странице университета (текущее значение {value} взято из неофициального источника).',
  'msg.question.nomination':
    'Как выдвигают кандидатов на «{award}» и нужно ли что-то сделать самому абитуриенту?',
  'msg.question.documentList':
    'Каков полный список документов для программы {programme}?',
  'msg.why.campus':
    'Требования, стоимость и сроки в разных кампусах могут отличаться. Прочитанное на страницах кампусов {campuses} не показывается как данные этой программы.',
  'msg.why.catalogueOnly':
    'Этот университет найден только через каталог. Ничего о нём не проверено по официальному источнику.',
  'msg.why.programmePageUnverified':
    'Факты об этом университете проверены на его официальном сайте, но в проверенной базе знаний пока нет проверенной страницы этой программы, поэтому то, что программа открыта на этот набор, не подтверждено.',
  'msg.why.noKbEntry':
    'Живое исследование отключено, а в проверенной базе знаний этого университета нет, поэтому о нём ничего не показывается и не додумывается. Пока его не добавят, источник — его официальный сайт или приёмная комиссия.',
  'msg.why.kbOutOfScope':
    'Живое исследование отключено, а проверенная база знаний отвечает только по бакалавриату Computer Science, поэтому об этой программе ничего не показывается и не додумывается. Пока её не добавят, источник — официальный сайт или приёмная комиссия.',
  'msg.why.uncoveredCosts':
    'В профиле {categories} указаны как расходы, которые обязательно должны быть покрыты, а эта стипендия их не покрывает. Эту разницу семье придётся найти реальными деньгами.',
  'msg.why.coop':
    'В профиле сказано, что co-op важен. На прочитанных страницах не сказано, есть ли он в этой программе.',
  'msg.why.workHours':
    'В профиле сказано, что работа во время учёбы необходима, а официального ограничения часов не найдено.',
  'msg.why.researchInterest':
    'В профиле «{interest}» указано как научный интерес. На прочитанных страницах это не упоминается, но это не значит, что такого направления нет.',
  'msg.why.noFundingPage':
    'Не удалось прочитать ни одной официальной страницы о финансировании, поэтому оно неизвестно, а не отсутствует.',
  'msg.why.unmatchedFunding':
    'Эту программу не удалось связать с найденным университетом, поэтому страницы о стипендиях для неё не читались. Ничего не предполагается.',
  'msg.why.pageScope':
    'Страница прочитана правильно, но в ней сказано, что она о другом, поэтому из неё ничего не берётся. Приёмная комиссия может одним ответом подтвердить, действует ли то же правило для вашего набора.',
  'msg.why.previousCycleDeadline':
    'Сроки на ваш набор на странице ещё не опубликованы; дата прошлого набора показана только для ориентира.',
  'msg.why.satForAward':
    'Если отказаться от SAT, опираясь на страницу приёма, можно потерять стипендию, а не место, — а эти две страницы публикуют разные отделы.',
  'msg.why.unmatchedDocuments':
    'Эту одобренную программу не удалось связать с найденным университетом, поэтому её список документов не читался.',
  'msg.why.kbNoDocuments':
    'В проверенной базе знаний пока нет списков документов, а живое исследование отключено, поэтому ничего не прочитано и не додумано.',
  'msg.why.awardStale':
    'Сведения проверенной базы знаний об этой стипендии устарели ({reasons}), поэтому она не показывается как актуальная и не считается финансированием, пока отдел стипендий её не подтвердит.',
  'msg.why.aggregator':
    'Данные агрегаторов по этому полю часто устаревают.',
  'msg.why.nomination':
    'На стипендию только по выдвижению нельзя подать напрямую; пропустить внутренний отбор — значит остаться без стипендии.',
  'msg.why.noDocumentList':
    'Не удалось прочитать официальный список документов, поэтому заранее ничего подготовить нельзя.',
  'msg.stale.noDate':
    'нет даты проверки',
  'msg.stale.tooOld':
    'проверено {date}, больше {days} дней назад',
  'msg.stale.yearBeforeIntake':
    'учебный год {year} раньше нужного для набора {intake} ({wanted})',
  'msg.stale.yearPast':
    'учебный год {year} уже прошёл',
  'msg.stale.deadlinePassed':
    'срок {date} уже прошёл',
  'msg.stale.publishedForYear':
    'опубликовано для учебного года {year}',
  'msg.stale.yearNotStated':
    'учебный год не указан',
  'msg.stale.publishedForCycle':
    'опубликовано для цикла приёма {year}',
  'msg.stale.documentsForCycle':
    'список документов опубликован для «{cycle}», а не для набора {intake}',
  'msg.stale.documentsAnotherCycle':
    'список документов опубликован для другого цикла, а не для набора {intake}',
  'msg.stale.documentItem':
    '«{document}» ({reasons})',
  'msg.caveat.yearInferred':
    'год на странице не указан; принят текущий цикл приёма',
  'msg.caveat.feePolicy':
    'страница с правилами оплаты; учебный год не указан',
  'msg.gap.mixedYears':
    'Опубликованные статьи расходов относятся к разным учебным годам ({years}). Они не складываются: сумма за разные годы исказила бы реальную стоимость.',
  'msg.gap.noCost':
    'Официальная стоимость обучения и проживания для этой программы и набора не найдена.',
  'msg.gap.partialCost':
    'Опубликована только часть основных расходов, поэтому полная годовая стоимость неизвестна и остаток к оплате не рассчитывается.',
  'msg.gap.noAwardAmount':
    'Стоимость известна, но не найдено ни одной стипендии с официально опубликованной суммой, поэтому остаток к оплате оценить нельзя.',
  'msg.gap.zeroNotComparable':
    'По расчёту выходит ноль, но суммы стоимости и покрытия несопоставимы, поэтому нулевой остаток вводил бы в заблуждение.',
  'msg.gap.computed':
    'Остаток к оплате за год после официально опубликованной помощи, которая вам подходит.',
  'msg.gap.recheckSingleYear':
    'Перепроверьте страницы со стоимостью за один учебный год.',
  'msg.gap.costUnverified':
    'Страницы со стоимостью проверить не удалось; остаток к оплате оценить нельзя.',
  'msg.gap.needBasedExcluded':
    'Найдена стипендия по нуждаемости, но её размер не известен до подачи оценки нуждаемости; в расчёт она не входит.',
  'msg.gap.awardNoAmount':
    '«{award}»: официальная сумма не опубликована, в расчёт не входит.',
  'msg.gap.notItemised':
    'В таблице расходов не указаны: {categories}; показанная сумма — известная часть, нижняя граница реальной стоимости.',
  'msg.gap.notStackable':
    'По условиям «{award}» её нельзя совмещать с другими стипендиями, поэтому другие не прибавляются, даже если сами это допускают.',
  'msg.gap.yearMismatch':
    'Стоимость опубликована за {costYear}, а сумма стипендии — за {awardYear}. Цифры ниже напрямую несопоставимы.',
  'msg.gap.coverageIncomplete':
    'В покрытии стипендии названы не все статьи расходов, которые публикует университет: {categories}',
  'msg.gap.costRange':
    'Стоимость опубликована диапазоном, поэтому и остаток показан диапазоном.',
  'msg.gap.aidExceedsCost':
    'Подтверждённая помощь больше опубликованной стоимости. Мы не считаем, что излишек выплатят; остаток к оплате указан как ноль.',
  'msg.funding.noInformation':
    'В официальных источниках не найдено сведений о стипендиях для этой программы.',
  'msg.funding.allExclude':
    'Все найденные для этой программы стипендии по официальным условиям вам не подходят.',
  'msg.funding.wrongShape':
    'Стипендии найдены, но ни одна не того вида, который нужен по вашему профилю; почему — сказано в строке каждой.',
  'msg.funding.coverageUnclear':
    'Стипендии есть, но официальных сведений о покрытии недостаточно, чтобы их классифицировать.',
  'msg.funding.needBased':
    'Поддержка зависит от оценки финансовой нужды, которую нельзя сделать заранее.',
  'msg.funding.automatic':
    '«{award}» присуждается автоматически по заявке на поступление по опубликованным критериям; решение всё равно за университетом.',
  'msg.funding.nomination':
    'На «{award}» нужно выдвижение от факультета, напрямую подать нельзя.',
  'msg.funding.competitive':
    '«{award}» вам доступна по опубликованным условиям и присуждается по конкурсу.',
  'msg.funding.limited':
    'Лучший подтверждённый вариант, «{award}», покрывает лишь небольшую часть стоимости.',
  'msg.funding.noneOffered':
    'Стипендий от университета нет: {university} сообщает, что для вас их не предлагает («{quote}», {url}).',
  'msg.funding.noneStale':
    '{university} сообщал, что стипендий от университета нет, но эти сведения устарели ({reasons}), поэтому финансирование неизвестно, а не точно отсутствует.',
  'detail.noRequirementsLive':
    'Не удалось прочитать ни одного опубликованного требования для этой программы, поэтому с вашим профилем ничего не сравнивалось.',
  'detail.noRequirementsKb':
    'В проверенной базе знаний нет ни одного требования этой программы, которое можно сравнить с вашим профилем.',
  'detail.reportedUnknown':
    'Это считается «неизвестно», а не «подходит».',
  'detail.noScholarshipKb':
    'Проверенная база знаний не называет ни одной стипендии для этой программы, а живое исследование отключено, поэтому страницы о стипендиях не читались. Финансирование {unknown} — это не то же самое, что его нет.',
  'detail.openQuestion':
    'Открытый вопрос:',
  'detail.unusedTuition':
    'Официальная стоимость обучения найдена, но не как годовая стоимость для этого набора, поэтому её нет в таблице расходов:',
  'msg.question.kbScholarships':
    'Какие стипендии {university} предлагает иностранным студентам программы {programme}?',
  'msg.question.kbEntryRequirements':
    'Какие требования для поступления на {programme} публикует {university} и подходит ли под них ваш профиль?',
  'msg.question.languageInstead':
    '{statement} Какой языковой сертификат {university} требует вместо этого и есть ли он у вас?',
  'msg.question.gradesInstead':
    '{statement} Какие оценки или баллы {university} учитывает вместо этого и подходят ли ваши?',
  'msg.question.requireInstead':
    '{statement} Что {university} требует вместо этого?',
  'msg.why.kbNoAward':
    'Проверенная база знаний не называет ни одной стипендии для этой программы, а живое исследование отключено, поэтому страницы о стипендиях не читались. Финансирование неизвестно, а не точно отсутствует.',
  'msg.why.kbRequirementsUnsettled':
    'В проверенной базе знаний есть факты об этой программе, но по ним не удалось определить: {requirements}, поэтому соответствие требованиям показано как «нужно уточнить», а не «выполнено».',
  'msg.why.kbNoComparableRequirement':
    'В проверенной базе знаний есть факты об этой программе, но ни один из них не является требованием для поступления, с которым можно сравнить ваш профиль, поэтому соответствие показано как «нужно уточнить», а не «выполнено».',
  'msg.why.verifiedStatement':
    'Проверено на официальной странице {url}: «{quote}». В профиле нет поля, с которым это можно сравнить, поэтому это не считается ни выполненным, ни невыполненным.',
  'msg.question.documentListCurrent':
    'Действует ли список документов для программы {programme} в {university} для набора {intake}?',
  'msg.why.documentsNotCurrent':
    'В проверенной базе знаний есть эти документы, но не как актуальные: {documents}. Они показаны, чтобы вы могли подготовиться, а не как подтверждённые.',
  'msg.gap.feeOtherYear':
    'Официальная стоимость обучения найдена, но за другой учебный год, чем у набора {intake}: {fees}. Она не используется как стоимость этого набора, поэтому остаток к оплате не рассчитывается.',
  'msg.gap.feeNotYearly':
    'Официальная стоимость обучения найдена, но не как актуальная годовая сумма для набора {intake}: {fees}. Она не используется как стоимость этого набора, поэтому остаток к оплате не рассчитывается.',
  'msg.gap.confirmIntakeFee':
    'Прежде чем полагаться на сумму, уточните в университете стоимость для набора {intake}.',
};

/** Kazakh, on the same rule. */
export const KK_RESULTS: Record<ResultsKey, string> = {
  'results.empty.title': 'Әзірге нәтиже жоқ',
  'results.empty.runFirst': 'Алдымен зерттеуді іске қосыңыз.',
  'results.notEnoughData': 'Салыстыруға дерек жеткіліксіз',
  'results.notConfirmed': 'Расталмаған',
  'results.notFound': 'табылмады',
  'results.notPublished': 'жарияланбаған',
  'results.notComputable': 'есептеу мүмкін емес',
  'results.notComparable': 'салыстыру мүмкін емес',
  'results.blocking': 'маңызды',
  'results.open': 'ашық',
  'results.yes': 'Иә',
  'results.no': 'Жоқ',
  'results.remove': 'Алып тастау',
  'results.compare': 'Салыстыру',
  'results.cancel': 'Болдырмау',
  'results.demoData': 'Демо деректер.',
  'results.notCurrent': 'Өзекті емес: {reason}.',
  'results.staleAge': '{days} күн бұрын',
  'results.staleNoAge': 'өзекті емес',
  'results.currentWithCaveat': 'Өзекті, ескертпемен',
  'results.caveat': 'Ескертпе: {caveat}.',
  'results.conflictCount.one': 'Сәйкессіздік: {n}',
  'results.conflictCount.other': 'Сәйкессіздік: {n}',
  'results.questionCount.one': 'Ашық сұрақ: {n}',
  'results.questionCount.other': 'Ашық сұрақ: {n}',
  'results.fitDisclaimer':
    'Расталған деректер бойынша сіз көрсеткен басымдықтарға қаншалықты сай келетіні. Түсу ықтималдығы емес.',

  'col.university': 'Университет және бағдарлама',
  'col.eligibility': 'Талаптар',
  'col.admissionsFit': 'Профиль деңгейі',
  'col.funding': 'Қаржыландыру',
  'col.remaining': 'Жылына қалдық',
  'col.remainingPerYear': 'Жылына төленетін қалдық',
  'col.deadline': 'Тапсыру мерзімі',
  'col.match': 'Үйлесім',
  'col.confirmed': 'Расталған',
  'col.confirmedHint': 'Бағаның қанша бөлігі біз растаған деректерге сүйенеді.',
  'col.bucket': 'Топ',
  'col.decision': 'Шешім',

  'shortlist.hint.OUT_OF_BUDGET':
    'Жасырылмайды, сомасымен көрсетіледі: ақша туралы біз білмейтін нәрсені сіз білуіңіз мүмкін.',
  'shortlist.hint.NEEDS_CLARIFICATION':
    'Бұларды орналастыруға тым аз нәрсе расталды. Жолдағы ашық сұрақтарды қабылдау комиссиясына қойыңыз.',
  'shortlist.hint.EXCLUDED': 'Жарияланған талап орындалмаған немесе сіз алып тастаған ел.',
  'shortlist.reason.cost': 'қымбат',
  'shortlist.reason.deadline passed': 'мерзім өтіп кетті',
  'shortlist.reason.no funding': 'қаржыландыру жоқ',
  'shortlist.reason.not a fit': 'сай келмейді',
  'shortlist.emptyEyebrow': 'ӨЗ ЖОЛЫҢЫЗДЫ ТАБЫҢЫЗ',
  'shortlist.title': 'Өзіңізге ең {highlight}',
  'shortlist.titleHighlight': 'лайықтысын табыңыз.',
  'shortlist.emptyLede': 'Зерттеу сіздің профиліңіз бен қалауларыңыздан басталады.',
  'shortlist.emptyBody': 'Қолжетімді дереккөздер растайтын бағдарламаларды табу үшін зерттеуді бастаңыз.',
  'shortlist.start': 'Зерттеуді бастау →',
  'shortlist.passed': 'өтті',
  'shortlist.previousCycle': 'өткен қабылдау: {date}',
  'shortlist.notRanked': 'рейтингте орны жоқ',
  'shortlist.decisionFor': '{university} бойынша шешім',
  'shortlist.maybe': 'Мүмкін',
  'shortlist.whyNot': 'Неге бұл емес? (міндетті емес — себебі жолда сақталады)',
  'shortlist.whyNotPlaceholder': 'қымбат, мерзім, сай емес…',
  'shortlist.saveRejection': 'Бас тартуды сақтау',
  'shortlist.rejected': 'Бас тартылды: {reason}',
  'shortlist.editNote': 'Жазбаны өзгерту',
  'shortlist.addNote': 'Жазба қосу',
  'shortlist.notePlaceholder': 'Неге дәл осы?',
  'shortlist.saveNote': 'Жазбаны сақтау',
  'shortlist.exploreCatalogue': 'Каталогтағы басқа университеттерді қарау',
  'shortlist.eyebrow': 'ӘЛЕМ БОЙЫНША МҮМКІНДІКТЕР. ШЫНАЙЫ ІРІКТЕУ.',
  'shortlist.lede':
    'Мақсатыңызға, бюджетіңізге және жоспарыңызға сай бағдарламалар. Дереккөздерді және әлі белгісіз нәрсені көру үшін кез келген нәтижені ашыңыз.',
  'shortlist.mascotAlt': 'Unimatch талисманы тау көрінісін зерттеп жүр',
  'shortlist.demoBody':
    'Бұл сандар нақты университет беттерінен емес, кірістірілген синтетикалық жинақтан алынған. Төмендегі әр дереккөз — {code} мекенжайы.',
  'shortlist.search': 'Университет, бағдарлама немесе ел бойынша іздеу',
  'shortlist.searchPlaceholder': 'Университет, бағдарлама немесе ел…',
  'shortlist.filters': 'Сүзгілер',
  'shortlist.compareCount': 'Салыстыру ({n})',
  'shortlist.matchList': 'Нұсқалар тізімі',
  'shortlist.tab.all': 'Барлығы',
  'shortlist.tab.priority': 'Басым',
  'shortlist.tab.saved': 'Сақталған',
  'shortlist.tab.exploring': 'Қарастырып жүрмін',
  'shortlist.filterSort': 'Сүзу және сұрыптау',
  'shortlist.country': 'Ел',
  'shortlist.sortBy': 'Сұрыптау',
  'shortlist.allCount': 'Барлығы ({n})',
  'shortlist.any': 'Кез келген',
  'shortlist.sort.key': 'Расталмағанын ескергендегі үйлесім',
  'shortlist.sort.fit': 'Басымдықтарыңызбен үйлесім',
  'shortlist.sort.coverage': 'Ең көп расталғаны',
  'shortlist.sort.gap': 'Ең аз төленетін қалдық',
  'shortlist.sort.deadline': 'Ең жақын мерзім',
  'shortlist.sort.university': 'Университет атауы',
  'shortlist.hideRejected': 'Бас тартылғандарды жасыру',
  'shortlist.resultCount.one': 'Осы зерттеудің нәтижесі: {n}',
  'shortlist.resultCount.other': 'Осы зерттеудің нәтижесі: {n}',
  'shortlist.noMatchTitle': 'Бұл сүзгілерге әзірге ештеңе сай келмейді.',
  'shortlist.noMatchBody': 'Басқаша іздеп көріңіз немесе сүзгілерді тазалаңыз.',
  'shortlist.clearFilters': 'Сүзгілерді тазалау',
  'shortlist.hideDetails': 'Толығын жасыру',
  'shortlist.viewDetails': 'Толығырақ',
  'shortlist.saved': 'Сақталды',
  'shortlist.save': 'Сақтау',
  'shortlist.evidenceTable': 'Дереккөздері бар толық кесте',
  'shortlist.balancedTitle': 'Теңгерімді қысқа тізім',
  'shortlist.balancedHint':
    'Алдымен квоталар толтырылады, содан кейін рейтинг: он батыл нұсқадан тұратын тізіммен ештеңе істей алмайсыз.',
  'shortlist.caption':
    'Қысқа тізімдегі бағдарламалар: талаптар, профиль деңгейі, қаржыландыру және төленетін қалдық',
  'shortlist.captionSetAside':
    '«{bucket}» тобына бөлінген бағдарламалар: талаптар, профиль деңгейі, қаржыландыру және төленетін қалдық',
  'shortlist.nothingRanked':
    'Мұнда әрі қалтаға шақ, әрі рейтингке жеткілікті расталған нұсқа жоқ. Әр нұсқа төмендегі бөлімдердің бірінде, себебімен бірге тұр.',
  'shortlist.rankedFootnote':
    'Рейтингтегі {total} жолдың {shown} көрсетілді. {match} — расталған деректер бойынша орынның сіз көрсеткен басымдықтарға қаншалықты сай келетіні; түсу ықтималдығы емес. {confirmed} пайызы — бұл бағаның қанша бөлігі тексерілген деректерге сүйенетіні.',
  'shortlist.footnote':
    '{total} ішінен {shown} көрсетілді. Бас тартылған жолдар себебімен сақталады, сонда сол бағдарлама жаңа мәліметсіз қайта ұсынылмайды.',

  'compare.aria': 'Таңдалған бағдарламаларды салыстыру',
  'compare.eyebrow': 'АНЫҚ САЛЫСТЫРУ',
  'compare.title': 'Артықшылықтары әртүрлі. Таңдау анығырақ.',
  'compare.clear': 'Тазалау',
  'compare.lede':
    'Дереккөздер шынында растайтын нәрсені салыстырыңыз. Үйлесім сіздің басымдықтарыңызды сипаттайды, түсу мүмкіндігіңізді емес.',
  'compare.preferenceFit': 'Басымдықтармен үйлесім',
  'compare.coverage': 'Расталу деңгейі',
  'compare.coverageHint': 'Осы бағаға қажет деректердің қанша бөлігі расталды',
  'compare.notAssessed': 'Бағаланбаған',
  'compare.toClarify': 'Нақтылау керек: {n}',
  'compare.whyFit': 'Неге осындай баға?',

  'detail.tab.requirements': 'Талаптар',
  'detail.tab.funding': 'Қаржыландыру',
  'detail.tab.costs': 'Шығындар',
  'detail.tab.documents': 'Құжаттар',
  'detail.tab.score': 'Неге осындай рет',
  'detail.tab.sources': 'Дереккөздер',
  'detail.eyebrow': 'БАҒДАРЛАМА ТУРАЛЫ · {country}',
  'detail.assessment': 'СІЗДІҢ БАҒАҢЫЗ',
  'detail.assessmentNote':
    'Талаптарға сәйкестік пен профиль деңгейі — бөлек нәрселер. Екеуі де түсу ықтималдығы емес.',
  'detail.evidence': 'Дереккөздер',
  'detail.tabsAria': '{university}: толығырақ',
  'detail.requirementNotMet': 'Расталған талап орындалмаған:',
  'detail.requirementNotMetNote':
    'Бұл ресми беттен алынған, сондықтан біздің деректегі олқылық емес, нақты кедергі деп саналады.',
  'detail.published': 'талап',
  'detail.you': 'сізде',
  'detail.deadlineLine': 'Тапсыру мерзімі: {date}',
  'detail.deadlinePassed': 'тапсыру мерзімі өтті',
  'detail.previousCycle': 'Өткен қабылдау: {date}',
  'detail.noScholarship':
    'Бұл бағдарлама бойынша стипендия туралы бірде-бір ресми бетті оқу мүмкін болмады. Қаржыландыру {unknown} — бұл оның жоқ екенін білдірмейді.',
  'detail.unknown': 'белгісіз',
  'detail.value': 'Мөлшері',
  'detail.percentOfTuition': 'оқу ақысының {pct}%',
  'detail.openToYou': 'Сізге қолжетімді ме',
  'detail.restrictedTo': 'тек: {list}',
  'detail.internationalEligible': 'шетелдік студенттерге қолжетімді',
  'detail.notInternational': 'шетелдік студенттерге қолжетімсіз',
  'detail.eligibilityNotPublished': 'шарттары жарияланбаған',
  'detail.howToApply': 'Қалай өтінім беруге болады',
  'detail.extraEssays': ' · қосымша эссе керек',
  'detail.offerRequired': 'Бұл стипендияға оқуға шақыру алғаннан кейін ғана өтінім беруге болады.',
  'detail.offerNotRequired': 'Бұл стипендияға оқуға шақыру алмай тұрып та өтінім беруге болады.',
  'detail.needBased': 'Шешім расталған қаржылық мұқтаждыққа қарай қабылданады.',
  'detail.renewal': 'Ұзарту',
  'detail.renewable': 'Ұзартылады',
  'detail.renewableYears': 'Ұзартылады, {n} жылға дейін',
  'detail.oneTime': 'Бір реттік төлем',
  'detail.stackable': 'Басқалармен қоса беріле ме',
  'detail.covers': 'Нені жабады',
  'detail.awardsOffered': 'Стипендиялар саны',
  'detail.officiallyPublished': '{n} (ресми жарияланған)',
  'detail.noCost': 'Бұл бағдарлама мен қабылдау үшін оқу мен тұрудың ресми құны табылмады.',
  'detail.publishedTotal': 'Жарияланған жиыны',
  'detail.knownSoFar': 'Әзірге белгілі құн',
  'detail.lowerBound':
    'Негізгі шығын баптарының бір бөлігі ғана көрсетілген, сондықтан бұл сома — белгілі бөлігі, нақты құнның төменгі шегі, толық құн емес. Жартылай белгілі құннан төленетін қалдық есептелмейді.',
  'detail.notItemised': '{category}: көрсетілмеген',
  'detail.remainingAnnual': 'Жылына төленетін қалдық',
  'detail.costOfAttendance': 'Оқу мен тұрудың құны',
  'detail.confirmedAid': 'Расталған көмек',
  'detail.stackedAid': 'Қосымша көмек',
  'detail.notComputed': 'Есептелмеді.',
  'detail.documentsLater':
    'Құжаттар тек сіз мақұлдаған бағдарламалар үшін жиналады — бұл ең қымбат қадам, сондықтан ол барлық нұсқаға емес, қысқа тізіміңізге ғана орындалады. Осы жолды мақұлдап, «Құжаттарды жинау» батырмасын басыңыз.',
  'detail.docs.official': 'ресми беттерден оқылды',
  'detail.docs.partial': 'ішінара оқылды',
  'detail.docs.unavailable': 'ресми тізім табылмады',
  'detail.docs.kb.official': 'тексерілген білім базасынан',
  'detail.docs.kb.partial': 'тексерілген, кейбір тармақтар өзекті емес',
  'detail.docs.kb.unavailable': 'тексерілген білім базасында тізім жоқ',
  'detail.docs.leadTime.one': '~{n} күн уақыт бөліңіз',
  'detail.docs.leadTime.few': '~{n} күн уақыт бөліңіз',
  'detail.docs.leadTime.many': '~{n} күн уақыт бөліңіз',
  'detail.docs.leadTime.other': '~{n} күн уақыт бөліңіз',
  'detail.generated': 'жасалған уақыты: {when}',
  'detail.docs.required': 'Міндетті',
  'detail.docs.optional': 'Қалауыңыз бойынша',
  'detail.docs.conditional': 'Шартпен',
  'detail.docs.condition': 'Жарияланған шарт: {condition}.',
  'detail.docs.order': 'Ұсынылатын рет: ұзақ дайындалатыны бірінші',
  'detail.docs.owner.applicant': 'Өзіңіз дайындайсыз',
  'detail.docs.owner.school': 'Мектебіңіз',
  'detail.docs.owner.recommender': 'Ұсыным берушіңіз',
  'detail.docs.owner.third_party': 'Үшінші тарап (аудармашы, нотариус, тест орталығы)',
  'detail.listedNotRanked': 'Тізімде бар, бірақ рейтингте орны жоқ.',
  'detail.notVerified': ' · расталмаған',
  'detail.didNotAsk': ' · сіз көрсетпедіңіз',
  'detail.weight': '× салмақ',
  'detail.axesFootnote':
    'Үйлесім — жоғарыдағы өлшемдердің геометриялық ортасы, сондықтан нөлге жақын өлшемді басқалары өтей алмайды. Расталмаған өлшемдер есепке кірмейді, оның орнына {confirmed} көрсеткішін төмендетеді.',
  'detail.noScore': 'Бұл жол үшін баға есептелмеді.',
  'detail.noData': ' · дерек жоқ',
  'detail.total': 'Барлығы {max} мүмкіннің {total}',
  'detail.missingPenalty': '−{pct}%: {n} өріс толтырылмаған',
  'detail.disagree': 'Дереккөздер сәйкес келмейді',
  'detail.askAdmissions': 'Қабылдау комиссиясына жіберетін сұрақ',
  'detail.openQuestions': 'Ашық сұрақтар',
  'detail.evidenceCount': 'Дереккөздегі деректер ({n})',
  'detail.lastVerified': 'соңғы тексеру {when} · негізгі өрістердің {pct}% расталған',

  'apply.automatic': 'Автоматты түрде',
  'apply.separate': 'Бөлек өтінім',
  'apply.nomination': 'Ұсыныс бойынша',
  'apply.unknown': 'Белгісіз',
  'coverage.yes': 'иә',
  'coverage.no': 'жоқ',
  'coverage.partial': 'ішінара',
  'coverage.unknown': 'белгісіз',
  'cost.tuition': 'Оқу ақысы',
  'cost.mandatory_fees': 'Міндетті алымдар',
  'cost.housing': 'Тұрғын үй',
  'cost.meals': 'Тамақ',
  'cost.health_insurance': 'Медициналық сақтандыру',
  'cost.books': 'Кітаптар',
  'cost.travel': 'Жол',
  'cost.visa': 'Виза',
  'cost.personal': 'Жеке шығындар',
  'axis.academic_fit': 'Академиялық деңгей',
  'axis.funding_fit': 'Қаржыландыру',
  'axis.affordability': 'Бағаның қолжетімділігі',
  'axis.country': 'Ел',
  'axis.programme_standing': 'Бағдарламаның орны',
  'axis.city': 'Қала',
  'axis.climate': 'Климат',
  'axis.university_size': 'Университет көлемі',
  'axis.campus': 'Кампус',
  'axis.workload': 'Оқу жүктемесі',
  'axis.career': 'Мансап',
  'axis.post_study_work': 'Оқудан кейінгі жұмыс',

  'funding.eyebrow': '05-қадам',
  'funding.title': 'Шын мәнінде қанша төлейсіз',
  'funding.lede':
    'Оқу мен тұрудың құны расталған көмекпен салыстырылады, бір валютада. Штрихталған жолақ бұл екі соманы салыстыруға болмайтынын білдіреді — оқу жылдары әртүрлі немесе стипендияның сомасы жарияланбаған — мұндайда нөл ешқашан көрсетілмейді.',
  'funding.onlyFunded': 'Тек едәуір қаржыландырылатын нұсқалар',
  'funding.legendCovered': 'көмекпен жабылады',
  'funding.legendPay': 'сіз төлейсіз',
  'funding.barAria': '{pct} пайызы жабылған, қалдығы {gap}',
  'funding.costAid': 'құны {cost} · көмек {aid}',
  'funding.noCostInfo': 'Құн туралы мәлімет табылмады.',
  'funding.yearMismatch': 'жылдары әртүрлі',
  'funding.categoryMismatch': 'шығын баптары әртүрлі',
  'funding.fullRideNote':
    '{label} мәртебесі ресми бет стипендияның оқу ақысын, міндетті алымдарды, тұрғын үй мен тамақты немесе оларға тең ай сайынғы төлемді жабатынын растайтынын білдіреді. Бұл оны міндетті түрде аласыз деген сөз емес — мұндай стипендиялардың көбі конкурспен беріледі.',

  'sources.eyebrow': 'Дереккөздер',
  'sources.title': 'Әр {highlight}',
  'sources.titleHighlight': 'нұсқаның дәлелі.',
  'sources.lede':
    'Расталған деректер, бір-біріне қайшы беттер және жауапсыз сұрақтар. Мұқият қарау керек болса, бастапқы бетті ашыңыз.',
  'sources.demoBody': 'Бұл деректер мен дереккөз мекенжайлары кірістірілген синтетикалық жинақтан алынған.',
  'sources.overviewAria': 'Дереккөздердің күйі',
  'sources.verifiedClaims': 'өзекті расталған дерек',
  'sources.conflictsToReview': 'тексеретін сәйкессіздік',
  'sources.openQuestions': 'ашық сұрақ',
  'sources.filter.all': 'Барлығы ({n})',
  'sources.filter.conflicts': 'Сәйкессіздіктер ({n})',
  'sources.filter.questions': 'Ашық сұрақтар ({n})',
  'sources.filter.stale':
    'Ескіруі мүмкін деректер ({n})',
  'sources.disagreeTitle': 'Дереккөздер сәйкес келмейді ({n})',
  'sources.noConflicts': 'Ресми дереккөздер арасында сәйкессіздік табылмады.',
  'sources.unresolved': 'шешілмеген',
  'sources.moreSpecific': 'нақтырақ дереккөз',
  'sources.draftQuestion': 'Қабылдау комиссиясына сұрақтың жобасы',
  'sources.copied': 'Көшірілді',
  'sources.copy': 'Көшіру',
  'sources.questionsTitle': 'Ашық сұрақтар ({n})',
  'sources.questionsHint':
    'Ешбір ресми дереккөз жауап бермеген нәрселер. Біз оларды болжаммен толтырмаймыз, бар күйінде хабарлаймыз.',
  'sources.nothingOutstanding': 'Ашық сұрақ жоқ.',
  'sources.staleTitle':
    'Ескіруі мүмкін деректер ({n})',
  'sources.staleHint':
    'Ресми беттен оқылған, бірақ өзекті болмауы мүмкін: өткен оқу жылының ақысы, өтіп кеткен күн немесе тым ертеде жасалған тексеру. Әрқайсысында себебі жазылған. Оларға сүйенбес бұрын қайта тексеріңіз.',
  'sources.noStale':
    'Ешбір дерек ескіруі мүмкін деп белгіленбеген.',
  'sources.everySource': 'Қаралған барлық дереккөз ({n})',
  'sources.everySourceAria': 'Қаралған барлық дереккөз',
  'sources.schedule':
    'Деректер түріне қарай кесте бойынша қайта тексеріледі: мерзімдер мен бағалар — 30 күннен кейін, құн мен стипендия сомалары — 120 күннен кейін, ережелер — 180 күннен кейін. Одан ескісі белгіленеді, көзсіз сенілмейді. Соңғы тексеру уақыты әр нәтижеде көрсетілген.',
  'sources.mostRecent': ' Ең соңғысы: {when}.',

  'status.MET': 'Орындалды',
  'status.PENDING': 'Күтілуде',
  'status.GAP': 'Орындалмаған',
  'status.NOT_APPLICABLE': 'Қатысы жоқ',
  'status.NEEDS_OFFICIAL_CLARIFICATION': 'Расталмаған',
  'status.STRONGER_FIT': 'Талаптан жоғары',
  'status.PLAUSIBLE_FIT': 'Қолжетімді',
  'status.AMBITIOUS': 'Батыл таңдау',
  'status.INSUFFICIENT_DATA': 'Дерек жоқ',
  'status.FULL_RIDE_CONFIRMED': 'Толық қамту',
  'status.FULL_TUITION': 'Оқу ақысы толық',
  'status.LARGE_GRANT': 'Ірі грант',
  'status.PARTIAL': 'Ішінара',
  'status.NEED_BASED_POSSIBLE': 'Мұқтаждыққа қарай',
  'status.NOT_ELIGIBLE': 'Сай емес',
  'status.UNKNOWN': 'Белгісіз',
  'status.CONFIRMED_OPPORTUNITY': 'Расталған',
  'status.COMPETITIVE_OPPORTUNITY': 'Конкурстық',
  'status.LIMITED_OPPORTUNITY': 'Шектеулі',
  'status.WELL_PLACED': 'Жақсы позиция',
  'status.PLAUSIBLE': 'Қолжетімді',
  'status.OUT_OF_BUDGET': 'Бюджеттен тыс',
  'status.NEEDS_CLARIFICATION': 'Нақтылау керек',
  'status.EXCLUDED': 'Алып тасталған',
  'status.VERIFIED_CURRENT': 'Тексерілген',
  'status.POSSIBLY_STALE':
    'Ескіруі мүмкін',
  'status.CONFLICTING': 'Дереккөздер қайшы',
  'status.UNVERIFIED': 'Тексерілмеген',
  'status.NOT_FOUND': 'Табылмады',
  'status.SUPERSEDED': 'Ауыстырылған',

  'statusMeaning.MET': 'Тексеруге болатын барлық жарияланған талап орындалған.',
  'statusMeaning.PENDING':
    'Ештеңе бұзылмаған, бірақ бірдеңе әлі дайын емес — емтихан, құжат немесе профиль өрісі.',
  'statusMeaning.GAP': 'Кемінде бір жарияланған талап қазір орындалмаған.',
  'statusMeaning.NOT_APPLICABLE': 'Бұл талаптың сізге қатысы жоқ.',
  'statusMeaning.NEEDS_OFFICIAL_CLARIFICATION':
    'Жарияланған талапты ресми дереккөз бойынша растау мүмкін болмады.',
  'statusMeaning.STRONGER_FIT':
    'Балдар жарияланған ең төменгі шектен айтарлықтай жоғары. Іріктеу бәрібір конкурстық.',
  'statusMeaning.PLAUSIBLE_FIT':
    'Ресми талаптар орындалған. Нәтиже конкурстық іріктеуге байланысты.',
  'statusMeaning.AMBITIOUS': 'Профиль жарияланған ауқымның деңгейінде немесе одан төмен.',
  'statusMeaning.INSUFFICIENT_DATA': 'Профильді салыстыруға расталған дерек жеткіліксіз.',
  'statusMeaning.FULL_RIDE_CONFIRMED':
    'Ресми дереккөз оқу ақысы, міндетті алымдар, тұрғын үй мен тамақ (немесе тұруға арналған ай сайынғы төлем) жабылатынын растайды.',
  'statusMeaning.FULL_TUITION': 'Оқу ақысы жабылады. Тұру шығындары толық жабылмайды.',
  'statusMeaning.LARGE_GRANT': 'Үлкен стипендия, бірақ құнның едәуір бөлігі қалады.',
  'statusMeaning.PARTIAL': 'Жалпы құнның шағын бөлігін жабады.',
  'statusMeaning.NEED_BASED_POSSIBLE':
    'Әлі тапсырылмаған қаржылық мұқтаждықты бағалауға байланысты, сондықтан мөлшері белгісіз.',
  'statusMeaning.NOT_ELIGIBLE': 'Жарияланған шарттар бойынша сізге сай емес.',
  'statusMeaning.UNKNOWN': 'Жіктеуге ресми мәлімет жеткіліксіз.',
  'statusMeaning.CONFIRMED_OPPORTUNITY':
    'Өтінім беру мүмкіндігі расталған. Шешімді бәрібір университет қабылдайды.',
  'statusMeaning.COMPETITIVE_OPPORTUNITY':
    'Жарияланған шарттар бойынша өтінім беруге болады; конкурспен беріледі.',
  'statusMeaning.LIMITED_OPPORTUNITY':
    'Қаржыландыру бар, бірақ аз бөлігін жабады немесе алдын ала бағалау мүмкін емес.',
  'statusMeaning.VERIFIED_CURRENT': 'Ресми беттен оқылған, өзектілік мерзімі өтпеген.',
  'statusMeaning.POSSIBLY_STALE':
    'Ресми беттен оқылған, бірақ енді өзекті болмауы мүмкін (өткен оқу жылы, өтіп кеткен күн немесе тексерілгеніне көп болған). Сүйенбес бұрын қайта тексеріңіз.',
  'statusMeaning.CONFLICTING': 'Екі ресми дереккөз бір-біріне қайшы. Ешқайсысы дұрыс деп таңдалмаған.',
  'statusMeaning.UNVERIFIED': 'Ресми дереккөз бойынша расталмаған.',
  'statusMeaning.NOT_FOUND': 'Бұл мәнді ешбір дереккөз жарияламаған.',
  'statusMeaning.WELL_PLACED':
    'Талаптар артығымен орындалған, қаржыландыру расталған, төленетін қалдық сіз көрсеткен шектен аспайды.',
  'statusMeaning.PLAUSIBLE': 'Жарияланған деректер бойынша талаптар да, қаржыландыру да қолжетімді көрінеді.',
  'statusMeaning.OUT_OF_BUDGET':
    'Төленетін қалдық сіз көрсеткен шектен асады. Жол сомасымен бірге сақталады.',
  'statusMeaning.EXCLUDED':
    'Сіз орындамайтын жарияланған талап немесе сіз алып тастаған ел. Тізімде бар, бірақ рейтингте орны жоқ.',
  'statusMeaning.NEEDS_CLARIFICATION': 'Бұл жолды орналастыруға тым аз нәрсе расталды.',

  'msg.question.campus':
    '{university} {programme} бағдарламасын бірнеше кампуста ұсынады, әрқайсысына бөлек өтінім беріледі. Сізге қай кампус керек?',
  'msg.question.entryRequirementsPage':
    '{programme} бағдарламасына түсу талаптары қай ресми бетте жарияланған?',
  'msg.question.programmePage':
    '{programme} бағдарламасы қай ресми бетте жарияланған?',
  'msg.question.noVerifiedDataInScope':
    '{university} бойынша әзірге тексерілген дерек жоқ: Computer Science бакалавриаты.',
  'msg.question.noVerifiedDataOutOfScope':
    '{university} бойынша әзірге тексерілген дерек жоқ: бұл бағдарлама (білім базасы тек Computer Science бакалавриатын қамтиды).',
  'msg.question.supportForUncovered':
    '{award} стипендиясынан бөлек {categories} үшін қандай да бір көмек бар ма?',
  'msg.question.coop':
    '{programme} бағдарламасында co-op немесе тәжірибе жылы бар ма?',
  'msg.question.workHours':
    'Шетелдік студент оқу кезінде аптасына неше сағат жұмыс істей алады (ел: {country})?',
  'msg.question.researchGroups':
    '{university} университетінде «{interest}» тақырыбымен қай топтар айналысады?',
  'msg.question.scholarshipsOpen':
    '{programme} бағдарламасының шетелдік студенттеріне қандай стипендиялар қолжетімді?',
  'msg.question.fundingPage':
    '{university} университетіндегі {programme} бағдарламасының қаржыландыруы қай ресми бетте жарияланған?',
  'msg.question.pageScope':
    '{url} сіз тапсыратын қабылдаудағы {programme} бағдарламасына да қатысты ма? Бұл мәлімет тек осы бетте табылды, ал онда былай делінген: {reason}.',
  'msg.question.previousCycleDeadline':
    '{url} бетінде тапсыру мерзімі {value} деп көрсетілген, бірақ ол {intake} қабылдауынан бұрынғы кезеңге жатады. Сіздің қабылдауыңыздың мерзімі қашан?',
  'msg.question.satForAward':
    '{programme} бағдарламасы test-optional деп жарияланған, бірақ {award} стипендиясына SAT балы керек. Бұл талап емтихансыз қабылданғандарға да қолданыла ма?',
  'msg.question.documents':
    '{university} {programme} бағдарламасы үшін қандай құжаттар талап етеді?',
  'msg.question.awardStillOffered':
    '{award} стипендиясы әлі беріле ме және {intake} қабылдауында шетелдік талапкерлерге қолжетімді ме?',
  'msg.question.confirmOnOfficialPage':
    '«{field}» мәнін университеттің ресми бетінде растаңыз (қазіргі {value} мәні ресми емес дереккөзден алынған).',
  'msg.question.nomination':
    '«{award}» стипендиясына үміткерлер қалай ұсынылады және талапкердің өзі бірдеңе істеуі керек пе?',
  'msg.question.documentList':
    '{programme} бағдарламасына қажет құжаттардың толық тізімі қандай?',
  'msg.why.campus':
    'Талаптар, ақы және мерзімдер кампусқа қарай өзгеше болуы мүмкін. {campuses} кампус беттерінде оқылғаны осы бағдарламаныкі ретінде көрсетілмейді.',
  'msg.why.catalogueOnly':
    'Бұл университет тек каталог арқылы табылды. Ол туралы ештеңе ресми дереккөз бойынша тексерілмеген.',
  'msg.why.programmePageUnverified':
    'Бұл университет туралы деректер оның ресми сайтында тексерілген, бірақ тексерілген білім базасында бұл бағдарламаның тексерілген беті әлі жоқ, сондықтан бағдарламаның осы қабылдауда ашық екені расталмаған.',
  'msg.why.noKbEntry':
    'Тікелей зерттеу өшірулі, ал тексерілген білім базасында бұл университет жоқ, сондықтан ол туралы ештеңе көрсетілмейді және болжанбайды. Қосылғанша дереккөз — оның ресми сайты немесе қабылдау комиссиясы.',
  'msg.why.kbOutOfScope':
    'Тікелей зерттеу өшірулі, ал тексерілген білім базасы тек Computer Science бакалавриаты бойынша жауап береді, сондықтан бұл бағдарлама туралы ештеңе көрсетілмейді және болжанбайды. Қосылғанша дереккөз — ресми сайт немесе қабылдау комиссиясы.',
  'msg.why.uncoveredCosts':
    'Профильде {categories} міндетті түрде жабылуы тиіс шығындар ретінде көрсетілген, ал бұл стипендия оларды жаппайды. Бұл айырманы отбасы нақты ақшамен табуы керек.',
  'msg.why.coop':
    'Профильде co-op маңызды деп көрсетілген. Оқылған беттерде бұл бағдарламада оның бар-жоғы айтылмаған.',
  'msg.why.workHours':
    'Профильде оқу кезінде жұмыс істеу қажет деп көрсетілген, ал сағат шегі туралы ресми мәлімет табылмады.',
  'msg.why.researchInterest':
    'Профильде «{interest}» ғылыми қызығушылық ретінде көрсетілген. Оқылған беттерде ол айтылмайды, бірақ бұл оның жоқ екенін білдірмейді.',
  'msg.why.noFundingPage':
    'Қаржыландыру туралы бірде-бір ресми бетті оқу мүмкін болмады, сондықтан қаржыландыру жоқ емес, белгісіз.',
  'msg.why.unmatchedFunding':
    'Бұл бағдарламаны табылған университетпен байланыстыру мүмкін болмады, сондықтан ол үшін стипендия беті оқылмады. Мұнда ештеңе болжанбайды.',
  'msg.why.pageScope':
    'Бет дұрыс оқылды, бірақ онда басқа нәрсе туралы екені айтылған, сондықтан одан ештеңе алынбайды. Қабылдау комиссиясы бір жауаппен сол ереже сіздің қабылдауыңызға да қолданыла ма, растай алады.',
  'msg.why.previousCycleDeadline':
    'Бетте сіздің қабылдауыңыздың күндері әлі жарияланбаған; өткен қабылдаудың күні тек бағдар үшін көрсетілген.',
  'msg.why.satForAward':
    'Қабылдау бетіне сүйеніп SAT-тан бас тартсаңыз, орыннан емес, осы стипендиядан айырылуыңыз мүмкін — ал бұл екі бетті әртүрлі бөлімдер жариялайды.',
  'msg.why.unmatchedDocuments':
    'Бұл мақұлданған бағдарламаны табылған университетпен байланыстыру мүмкін болмады, сондықтан оның құжаттар тізімі оқылмады.',
  'msg.why.kbNoDocuments':
    'Тексерілген білім базасында құжаттар тізімі әлі жоқ, ал тікелей зерттеу өшірулі, сондықтан ештеңе оқылмады және болжанбады.',
  'msg.why.awardStale':
    'Тексерілген білім базасындағы бұл стипендия туралы мәлімет ескірген ({reasons}), сондықтан ол өзекті ретінде көрсетілмейді және стипендия бөлімі растағанша қаржыландыру деп саналмайды.',
  'msg.why.aggregator':
    'Агрегаторлардың бұл өріс бойынша деректері жиі ескіреді.',
  'msg.why.nomination':
    'Тек ұсыныс бойынша берілетін стипендияға тікелей өтінім беруге болмайды; ішкі іріктеуді өткізіп алу — стипендиядан мүлде айырылу деген сөз.',
  'msg.why.noDocumentList':
    'Ресми құжаттар тізімін оқу мүмкін болмады, сондықтан алдын ала ештеңе дайындауға болмайды.',
  'msg.stale.noDate':
    'тексерілген күні жоқ',
  'msg.stale.tooOld':
    '{date} күні тексерілген, {days} күннен бұрын',
  'msg.stale.yearBeforeIntake':
    '{year} оқу жылы {intake} қабылдауына керек жылдан ({wanted}) ерте',
  'msg.stale.yearPast':
    '{year} оқу жылы өтіп кетті',
  'msg.stale.deadlinePassed':
    '{date} мерзімі өтіп кетті',
  'msg.stale.publishedForYear':
    '{year} оқу жылына жарияланған',
  'msg.stale.yearNotStated':
    'оқу жылы көрсетілмеген',
  'msg.stale.publishedForCycle':
    '{year} қабылдау цикліне жарияланған',
  'msg.stale.documentsForCycle':
    'құжаттар тізімі {intake} қабылдауына емес, «{cycle}» үшін жарияланған',
  'msg.stale.documentsAnotherCycle':
    'құжаттар тізімі {intake} қабылдауына емес, басқа циклге жарияланған',
  'msg.stale.documentItem':
    '«{document}» ({reasons})',
  'msg.caveat.yearInferred':
    'бетте жыл көрсетілмеген; ағымдағы қабылдау циклі деп алынды',
  'msg.caveat.feePolicy':
    'төлем ережелері беті; оқу жылы көрсетілмеген',
  'msg.gap.mixedYears':
    'Жарияланған шығын баптары әртүрлі оқу жылдарына жатады ({years}). Олар қосылмайды: әртүрлі жылдардың жиынтығы нақты құнды бұрмалайды.',
  'msg.gap.noCost':
    'Бұл бағдарлама мен қабылдау үшін оқу мен тұрудың ресми құны табылмады.',
  'msg.gap.partialCost':
    'Негізгі шығындардың бір бөлігі ғана жарияланған, сондықтан толық жылдық құн белгісіз және төленетін қалдық есептелмейді.',
  'msg.gap.noAwardAmount':
    'Құны белгілі, бірақ сомасы ресми жарияланған стипендия табылмады, сондықтан төленетін қалдықты бағалау мүмкін емес.',
  'msg.gap.zeroNotComparable':
    'Есеп бойынша нөл шығады, бірақ құн мен жабу сомаларын салыстыруға болмайды, сондықтан нөлдік қалдық адастырар еді.',
  'msg.gap.computed':
    'Сізге сай, ресми жарияланған көмектен кейінгі жылдық төленетін қалдық.',
  'msg.gap.recheckSingleYear':
    'Құн беттерін бір оқу жылы бойынша қайта тексеріңіз.',
  'msg.gap.costUnverified':
    'Құн беттерін тексеру мүмкін болмады; төленетін қалдықты бағалауға болмайды.',
  'msg.gap.needBasedExcluded':
    'Мұқтаждыққа қарай берілетін стипендия табылды, бірақ мұқтаждықты бағалау тапсырылмайынша оның мөлшері белгісіз; ол бұл есепке кірмейді.',
  'msg.gap.awardNoAmount':
    '«{award}»: ресми сомасы жарияланбаған, есепке кірмейді.',
  'msg.gap.notItemised':
    'Шығындар кестесінде мыналар көрсетілмеген: {categories}; көрсетілген сома — белгілі бөлігі, нақты құнның төменгі шегі.',
  'msg.gap.notStackable':
    '«{award}» шарты бойынша оны басқа стипендиялармен қосуға болмайды, сондықтан басқалары рұқсат етсе де қосылмайды.',
  'msg.gap.yearMismatch':
    'Құн {costYear} жылға, ал стипендия сомасы {awardYear} жылға жарияланған. Төмендегі сандарды тікелей салыстыруға болмайды.',
  'msg.gap.coverageIncomplete':
    'Стипендияның жабу тізімінде университет жариялайтын барлық шығын баптары аталмаған: {categories}',
  'msg.gap.costRange':
    'Құн аралықпен жарияланған, сондықтан қалдық та аралықпен көрсетілген.',
  'msg.gap.aidExceedsCost':
    'Расталған көмек жарияланған құннан асады. Артығы төленеді деп есептелмейді; төленетін қалдық нөл деп көрсетілген.',
  'msg.funding.noInformation':
    'Ресми дереккөздерден бұл бағдарлама бойынша стипендия туралы мәлімет табылмады.',
  'msg.funding.allExclude':
    'Бұл бағдарлама бойынша табылған барлық стипендия ресми шарттары бойынша сізге сай емес.',
  'msg.funding.wrongShape':
    'Стипендиялар табылды, бірақ біреуі де профиліңізге керек түрге жатпайды; себебі әрқайсысының өз жолында жазылған.',
  'msg.funding.coverageUnclear':
    'Стипендиялар бар, бірақ оларды жіктеуге жабу туралы ресми мәлімет жеткіліксіз.',
  'msg.funding.needBased':
    'Көмек алдын ала бағалау мүмкін емес қаржылық мұқтаждықты бағалауға байланысты.',
  'msg.funding.automatic':
    '«{award}» жарияланған критерийлер бойынша түсу өтініміне қарай автоматты түрде беріледі; шешімді бәрібір университет қабылдайды.',
  'msg.funding.nomination':
    '«{award}» үшін факультеттің ұсынысы керек, сондықтан тікелей өтінім беруге болмайды.',
  'msg.funding.competitive':
    '«{award}» жарияланған шарттар бойынша сізге қолжетімді және конкурспен беріледі.',
  'msg.funding.limited':
    'Ең күшті расталған нұсқа — «{award}» — құнның шағын бөлігін ғана жабады.',
  'msg.funding.noneOffered':
    'Университеттің стипендиясы жоқ: {university} сізге стипендия ұсынбайтынын хабарлайды («{quote}», {url}).',
  'msg.funding.noneStale':
    '{university} университеттің стипендиясы жоқ екенін айтқан, бірақ бұл мәлімет ескірген ({reasons}), сондықтан қаржыландыру нақты жоқ емес, белгісіз.',
  'detail.noRequirementsLive':
    'Бұл бағдарламаның жарияланған бірде-бір талабын оқу мүмкін болмады, сондықтан профиліңізбен ештеңе салыстырылған жоқ.',
  'detail.noRequirementsKb':
    'Тексерілген білім базасында бұл бағдарламаның профиліңізбен салыстыруға болатын бірде-бір талабы жоқ.',
  'detail.reportedUnknown':
    'Бұл «сай келеді» емес, «белгісіз» деп есептеледі.',
  'detail.noScholarshipKb':
    'Тексерілген білім базасы бұл бағдарлама үшін бірде-бір стипендияны атамайды, ал тікелей зерттеу өшірулі, сондықтан стипендия беттері оқылмады. Қаржыландыру {unknown} — бұл оның жоқ екенін білдірмейді.',
  'detail.openQuestion':
    'Ашық сұрақ:',
  'detail.unusedTuition':
    'Ресми оқу ақысы табылды, бірақ осы қабылдаудың жылдық құны ретінде емес, сондықтан ол шығындар кестесінде жоқ:',
  'msg.question.kbScholarships':
    '{university} {programme} бағдарламасының шетелдік студенттеріне қандай стипендиялар ұсынады?',
  'msg.question.kbEntryRequirements':
    '{university} {programme} бағдарламасына қандай түсу талаптарын жариялайды және профиліңіз оларға сай ма?',
  'msg.question.languageInstead':
    '{statement} Оның орнына {university} қандай тіл сертификатын талап етеді және ол сізде бар ма?',
  'msg.question.gradesInstead':
    '{statement} Оның орнына {university} қандай бағалар мен балдарды қарайды және сіздікі оларға сай ма?',
  'msg.question.requireInstead':
    '{statement} Оның орнына {university} не талап етеді?',
  'msg.why.kbNoAward':
    'Тексерілген білім базасы бұл бағдарлама үшін бірде-бір стипендияны атамайды, ал тікелей зерттеу өшірулі, сондықтан стипендия беттері оқылмады. Қаржыландыру нақты жоқ емес, белгісіз.',
  'msg.why.kbRequirementsUnsettled':
    'Тексерілген білім базасында бұл бағдарлама туралы деректер бар, бірақ олардан мынаны анықтау мүмкін болмады: {requirements}, сондықтан талаптарға сәйкестік «орындалды» емес, «нақтылау керек» деп көрсетілген.',
  'msg.why.kbNoComparableRequirement':
    'Тексерілген білім базасында бұл бағдарлама туралы деректер бар, бірақ олардың ешқайсысы профиліңізбен салыстыруға болатын түсу талабы емес, сондықтан сәйкестік «орындалды» емес, «нақтылау керек» деп көрсетілген.',
  'msg.why.verifiedStatement':
    '{url} ресми бетінде тексерілген: «{quote}». Профильде мұны салыстыратын өріс жоқ, сондықтан ол орындалды да, орындалмады да деп саналмайды.',
  'msg.question.documentListCurrent':
    '{university} {programme} бағдарламасының құжаттар тізімі {intake} қабылдауына әлі де жарамды ма?',
  'msg.why.documentsNotCurrent':
    'Тексерілген білім базасында бұл құжаттар бар, бірақ өзекті ретінде емес: {documents}. Олар расталған ретінде емес, дайындалуыңыз үшін көрсетілген.',
  'msg.gap.feeOtherYear':
    'Ресми оқу ақысы табылды, бірақ {intake} қабылдауынан басқа оқу жылына: {fees}. Ол осы қабылдаудың құны ретінде қолданылмайды, сондықтан төленетін қалдық есептелмейді.',
  'msg.gap.feeNotYearly':
    'Ресми оқу ақысы табылды, бірақ {intake} қабылдауы үшін өзекті жылдық сома ретінде емес: {fees}. Ол осы қабылдаудың құны ретінде қолданылмайды, сондықтан төленетін қалдық есептелмейді.',
  'msg.gap.confirmIntakeFee':
    'Сомаға сүйенбес бұрын {intake} қабылдауының ақысын университеттен нақтылаңыз.',
};
