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
  'detail.kbUnknown.field.english': 'English requirement',
  'detail.kbUnknown.field.gpa': 'Minimum grade',
  'detail.kbUnknown.field.deadline': 'Application deadline',
  'detail.kbUnknown.field.tuition': 'Tuition fee',
  'detail.kbUnknown.field.scholarship_exists': 'Scholarships',
  'detail.kbUnknown.field.scholarship_international': 'Scholarships open to international students',
  'detail.kbUnknown.notPublished': '{fields}: not published by the university, expert check {date}.',
  'detail.kbUnknown.notPublishedUndated': '{fields}: not published by the university (expert check).',
  'detail.kbUnknown.access': '{fields}: the official page is not readable from our servers; ask the admissions office.',
  'detail.kbUnknown.notVerified': '{fields}: not yet verified.',
  'detail.noCostKb': 'No verified tuition fee in the knowledge base yet for this programme and intake.',
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
  'detail.docs.step.applicant': 'You',
  'detail.docs.step.school': 'Your school',
  'detail.docs.step.recommender': 'Your referee',
  'detail.docs.step.third_party': 'A third party',
  'detail.docs.after': 'after {what}',
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

  // --- documents & deadlines (screen 08, I18N-2) ------------------------
  'documents.eyebrow': 'Documents & deadlines',
  'documents.title': 'Prepare with {accent}',
  'documents.titleAccent': 'confidence.',
  'documents.emptyLede': 'Your document checklist appears after you save programmes in Plan and collect their official requirements.',
  'documents.emptyTitle': 'No checklists yet',
  'documents.emptyBody': 'Choose a programme in Find, then collect documents from Plan.',
  'documents.lede': 'Ordered by lead time, not by deadline. The items at the top depend on other people, so they are the ones that need starting first.',
  'documents.calendarSummary': 'Calendar and deadlines across your shortlist ({n})',
  'documents.calendarTitle': 'Every deadline across your shortlist',
  'documents.addToCalendar': 'Add to calendar (.ics)',
  'documents.passed': 'passed',
  'documents.noDeadlines': 'No dated deadlines were found.',
  'documents.admissionApplication': 'Admission application',
  'documents.ticked': '{done} of {total} items ticked off. Generated {when}.',
  'documents.completeness.official': 'from official pages',
  'documents.completeness.partial': 'partially read',
  'documents.completeness.unavailable': 'no official list found',
  'documents.owner.thirdParty': 'A third party (translator, WES/ECE, notary)',
  'documents.forScholarship': 'for a scholarship',
  'documents.forAdmission': 'for admission',
  'documents.maxWords': 'max {n} words',
  'documents.maxPages': 'max {n} pages',
  'documents.maxSize': 'max {n} MB',
  'documents.translation': 'certified translation required',
  'documents.notarisation': 'notarisation required',
  'documents.apostille': 'apostille required',
  'documents.credentialEvaluation': 'credential evaluation required',
  'documents.due': 'due {date}',
  'documents.stillToConfirm': 'Still to confirm',
  'documents.ask': 'Ask: {contact}',
  'documents.notice': 'Unimatch prepares this list. It does not upload documents, submit an application, sign anything on your behalf, or pay a fee. Those steps stay with you.',

  // --- backend sentences (app/domain/message_keys.py) ---------------------
  'msg.question.campus':
    '{university} offers {programme} on more than one campus, each a separate application. Which campus do you want?',
  'msg.question.entryRequirementsPage':
    'Which official page publishes entry requirements for {programme}?',
  'msg.question.programmePage':
    'Which official page publishes the {programme} programme?',
  'msg.question.programmeNotOffered':
    '{university} publishes no bachelor\'s in Computer Science (checked {date}).',
  'msg.question.programmeRelatedOnly':
    'No standalone bachelor\'s in Computer Science is published; the closest official route is {route} (official page: {url}). Does that route suit you?',
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
  'msg.why.programmeNotOffered':
    'The closest official programme is {route} (official page: {url}).',
  'msg.why.programmeNotOfferedNoRoute':
    'The verified knowledge base records that no such programme is offered, so nothing is shown as this programme\'s.',
  'msg.why.programmeRelatedOnly':
    'The verified knowledge base records no standalone bachelor\'s in Computer Science at {university} (expert check {date}). Whether the closest route suits you is your decision.',
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
  'msg.coverage.kb':
    'The verified knowledge base answers for {universities} of {total} catalogue '
    + 'universities (bachelor\'s in Computer Science). A university outside it, or another '
    + 'programme, gets \'No verified data yet\'; no page is read during a run.',
  'msg.coverage.live':
    'Live mode searches {institutions} curated institutions in {countries} countries. '
    + 'Results depend on the selected fields and which official pages can be accessed. '
    + 'Missing or unverified evidence stays visible in the results.',
  'research.kbNotice.title': 'Research answers from the verified knowledge base.',
  'research.kbNotice.body':
    'No university page is read and nothing is sent to a search provider during a run.',
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
  'detail.fee.perYear': '{amount} a year',
  'detail.fee.perPeriod': '{amount} per {period}',
  'detail.fee.year': 'academic year {year}',
  'detail.fee.noYear': 'no academic year stated',
  'detail.fee.notCurrent': 'not current: {reason}',
  'detail.fee.notYearly': 'published per {period}, not as a yearly figure',
  'detail.fee.perUnit': 'published per {period} (no yearly figure printed)',
  'detail.fee.range': 'published range {range}',
  'detail.fee.period.semester': 'semester',
  'detail.fee.period.credit': 'credit',
  'detail.fee.period.programme': 'full programme ({n} years)',
  'detail.costCaveat': 'Tuition is current with a caveat: {caveat}.',
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
  'msg.question.languageNoneRecorded':
    '{statement} Does {university} ask for any other language evidence? The verified knowledge base names none.',
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
  'msg.gap.kbNoFee':
    'The verified knowledge base holds no tuition fee for this programme yet, so the remaining cost is not computed.',
  'msg.gap.kbTuitionRange':
    'Tuition is published only as a range, {range}; the cost uses its upper bound, so it is not understated.',
  // I18N-2: requirement checks, award classifications, the ranking, conflicts.
  'msg.req.intakeOpen':
    'Intake accepting applications',
  'msg.req.deadline':
    'Admission deadline',
  'msg.req.minGpa':
    'Minimum GPA',
  'msg.req.satTotal':
    'SAT total',
  'msg.req.satPolicy':
    'SAT policy',
  'msg.req.portfolio':
    'Portfolio',
  'msg.req.interview':
    'Interview',
  'msg.req.entranceExam':
    'Entrance examination',
  'msg.req.credentialEvaluation':
    'Credential evaluation',
  'msg.req.requiredSubjects':
    'Required subjects',
  'msg.req.academicEntry':
    'Academic entry requirements',
  'msg.req.ieltsType':
    'Accepted IELTS test type',
  'msg.req.englishWaiver':
    'English test waiver',
  'msg.req.ieltsOverall':
    'IELTS overall',
  'msg.req.ieltsBand':
    'IELTS {band}',
  'msg.req.toeflTotal':
    'TOEFL total',
  'msg.req.scholarshipCitizenship':
    'Scholarship citizenship eligibility',
  'msg.req.scholarshipInternational':
    'Scholarship international eligibility',
  'msg.req.scholarshipFaculty':
    'Scholarship faculty restriction',
  'msg.req.scholarshipProgramme':
    'Scholarship programme restriction',
  'msg.req.scholarshipDeadline':
    'Scholarship deadline',
  'msg.req.scholarshipTest':
    'Scholarship {test} minimum',
  'msg.explain.noMinimum':
    'No official minimum for {label} was found; not treated as a barrier.',
  'msg.explain.notNumber':
    'The published {label} could not be read as a number.',
  'msg.explain.noApplicantValue':
    'The programme publishes a minimum of {published}, but the profile has no {label} value yet. Add it to resolve this check.',
  'msg.explain.minimumNotMet':
    'Published minimum {published}; applicant {applicant}. The published minimum is not met.',
  'msg.explain.minimumMet':
    'Published minimum {published}; applicant {applicant}.',
  'msg.explain.intakeClosed':
    'The programme officially states it is not accepting applications for this intake.',
  'msg.explain.deadlineUnparsed':
    'A deadline was published but could not be parsed into a date.',
  'msg.explain.deadlinePassed':
    'The published deadline {date} has passed.',
  'msg.explain.deadlineByPopulation':
    'Applications close {date} at the earliest; the deadline depends on your fee population here ({deadlines}).',
  'msg.explain.deadlineOpen':
    'Applications close {date}.',
  'msg.explain.allDeadlinesPassed':
    'Every published deadline has passed ({deadlines}).',
  'msg.explain.deadlineByPopulationPassed':
    'The deadline depends on your fee population here ({deadlines}). The one for {populations} has passed; confirm which applies to you.',
  'msg.explain.gpaScale':
    'The applicant\'s GPA is on the {scale} scale and the programme publishes a different scale. No conversion is applied without a documented method, so this cannot be decided here.',
  'msg.explain.testOptional':
    'The programme is test-optional, so a missing SAT score is not a barrier.',
  'msg.explain.satPolicyNoMinimum':
    'An SAT policy is published but no minimum score was found.',
  'msg.explain.actionRequired':
    '{label} is required. This is an action to complete, not a disqualification.',
  'msg.explain.subjectsPresent':
    'All published subject prerequisites are present in the profile.',
  'msg.explain.subjectsMissing':
    'Not listed in the profile: {subjects}. Add them if they were studied; otherwise this is a genuine gap.',
  'msg.explain.noAssessable':
    'No assessable academic entry requirements were found. A future deadline or optional test policy does not establish eligibility.',
  'msg.explain.ieltsTypes':
    'The programme accepts {accepted}; the applicant holds {held}.',
  'msg.explain.englishWaiver':
    'This programme publishes conditions under which the English test is not required. Check them against your own schooling before booking a test — whether they cover you is not something this page settles.',
  'msg.explain.citizenshipUnreadable':
    'The award publishes a citizenship restriction that could not be read as a list of countries. It needs official clarification.',
  'msg.explain.citizenshipNamed':
    'The published restriction names {phrase}, which matches the {country} citizenship in the profile.',
  'msg.explain.citizenshipMember':
    '{country} is a member of the {group}, which the award names as its restriction.',
  'msg.explain.citizenshipGroup':
    'The award is restricted to a group (\'{restrictions}\') whose membership is not published as a list of countries. Whether {held} falls inside it cannot be settled from the page, so it is left for the admissions office to confirm.',
  'msg.explain.citizenshipExcluded':
    'The award is restricted to {restrictions}. An applicant holding {held} citizenship is not eligible.',
  'msg.explain.internationalClosed':
    'The award is officially closed to international students.',
  'msg.explain.internationalOpen':
    'The award is officially open to international students of any nationality.',
  'msg.explain.restriction':
    'The page limits this award to {restriction}. Whether this programme belongs to it is not something the page settles — ask the admissions office before counting on this award.',
  'msg.explain.scholarshipTestMissing':
    'The award requires {test} {minimum}; no score is in the profile.',
  'msg.explain.scholarshipDeadlinePassed':
    'The published scholarship deadline {date} has passed.',
  'msg.degree.noText':
    'no text or no degree level to check against',
  'msg.degree.excludes':
    'the page explicitly excludes {degree} applicants',
  'msg.degree.forOther':
    'the page states the award is for {level} applicants, not {degree}',
  'msg.degree.statesFor':
    'the page states the award is for {degree} applicants',
  'msg.degree.onlyOthers':
    'the page describes the award for {levels} only and never mentions {degree}',
  'msg.degree.unstated':
    'the page does not state which degree levels the award applies to',
  'msg.degree.excludesLevel':
    'the page excludes this level.',
  'msg.missing.notCovered':
    '{category} is not covered',
  'msg.missing.unknown':
    '{category} is unknown',
  'msg.missing.partial':
    '{category} is partial',
  'msg.class.excluded':
    'Published conditions exclude this applicant.',
  'msg.class.degreeLevel':
    'Not applicable to this applicant\'s degree level: {degreeReason}',
  'msg.class.citizenship':
    'The award is restricted to {restrictions}, which does not include this applicant.',
  'msg.class.notInternational':
    'Official source states the award is not open to international students.',
  'msg.class.noCoverage':
    'No official per-category coverage information was found.',
  'msg.class.promotionalNoBreakdown':
    'Page uses promotional wording ({words}) but publishes no breakdown.',
  'msg.class.needBased':
    'Award size depends on a verified financial-need assessment that has not been filed.',
  'msg.class.fullRide':
    'Official sources confirm coverage of tuition, mandatory fees, housing and meals or an equivalent living stipend.',
  'msg.class.fullTuition':
    'Tuition is confirmed as covered, but {missing} — this is full tuition, not a full ride.',
  'msg.class.shareUnknown':
    'Coverage is partial but the award amount or the cost of attendance is not officially published, so the share cannot be computed.',
  'msg.class.largeGrant':
    'Covers roughly {share} of published cost of attendance; a substantial portion of the cost remains.',
  'msg.class.partial':
    'Covers roughly {share} of published cost of attendance.',
  'msg.class.promotional':
    'The page uses promotional wording such as \'full ride\'; the classification here follows the published coverage table instead.',
  'msg.class.onlyFullRide':
    'The profile states that only a full ride makes this affordable; this award is classified as {classification}.',
  'msg.class.noTuitionOnly':
    'The profile states that a tuition-only award would not be taken up.',
  'msg.class.noPartial':
    'The profile states that a partial award would not be taken up.',
  'msg.class.needDocuments':
    'This award is need-based and the profile states that financial documents will not be submitted, which is what a need-based application requires.',
  'msg.class.mustCover':
    'The profile requires {categories} to be covered; this award states it is not.',
  'msg.rank.academicNoMargin':
    'All published requirements are met; there are no numeric minimums to measure a margin against.',
  'msg.rank.academicMargin':
    'All published requirements are met, on average {margin} above the minimums.',
  'msg.rank.academicPending':
    'Requirements are met apart from items still pending.',
  'msg.rank.academicGap':
    'At least one published requirement is not met.',
  'msg.rank.academicUnknown':
    'Published requirements could not be verified.',
  'msg.rank.fundingUnknown':
    'No official funding information was confirmed.',
  'msg.rank.fundingConfirmed':
    'Funding fit is confirmed opportunity.',
  'msg.rank.fundingCompetitive':
    'Funding fit is competitive opportunity.',
  'msg.rank.fundingLimited':
    'Funding fit is limited opportunity.',
  'msg.rank.fundingNotEligible':
    'Funding fit is not eligible.',
  'msg.rank.gapUnknown':
    'The remaining annual cost could not be computed.',
  'msg.rank.noCeiling':
    'No family budget ceiling was stated to compare against.',
  'msg.rank.nothingRemains':
    'Nothing remains to be paid.',
  'msg.rank.zeroContribution':
    'The family states it can contribute nothing, and {gap} a year remains.',
  'msg.rank.withinCeiling':
    'The remaining {gap} a year is within the stated ceiling of {ceiling}.',
  'msg.rank.timesCeiling':
    'The remaining {gap} a year is {ratio} times the stated ceiling of {ceiling}.',
  'msg.rank.aboveCeiling':
    'The remaining {gap} a year is {over} above the stated ceiling of {ceiling}.',
  'msg.rank.preferredCountry':
    '{country} is a preferred country.',
  'msg.rank.unpreferredCountry':
    '{country} is outside the preferred list.',
  'msg.rank.noRank':
    'No ranking position was found.',
  'msg.rank.insideBand':
    'Ranked {rank}, inside the requested {band}.',
  'msg.rank.outsideTop':
    'Ranked {rank}, outside the top {top}.',
  'msg.rank.consensus':
    'Consensus ranking position {rank}.',
  'msg.rank.ranked':
    'Ranked {rank}.',
  'msg.rank.noPreference':
    'No {axis} preference was stated.',
  'msg.rank.attributeUnknown':
    'The {axis} of this university is not known.',
  'msg.rank.attributeMatches':
    '{actual} matches the stated preference.',
  'msg.rank.ladderStep':
    '{actual} against a preference for {preferred}: {steps} step apart.',
  'msg.rank.ladderSteps':
    '{actual} against a preference for {preferred}: {steps} steps apart.',
  'msg.rank.ladderDiffers':
    '{actual} differs from the preferred {preferred}.',
  'msg.rank.careersNotPriority':
    'Careers were not a stated priority.',
  'msg.rank.coop':
    'A co-op or placement year is officially offered.',
  'msg.rank.internships':
    'An internship programme is officially described.',
  'msg.rank.careersPage':
    'A careers page exists but states nothing specific enough to check.',
  'msg.rank.noCareers':
    'No official careers information was found.',
  'msg.rank.pswNotPriority':
    'Post-study work was not a stated priority.',
  'msg.rank.pswUnknown':
    'Post-study work rules were not confirmed in months.',
  'msg.rank.psw':
    'A post-study work right of {months} months is published.',
  'msg.rank.excludedCountry':
    '{country} is on the applicant\'s excluded list.',
  'msg.rank.knockoutUnmet':
    '{requirement}: a published requirement is not met',
  'msg.rank.knockout':
    '{requirement}: {explanation}',
  'msg.rank.bucketInsufficient':
    'Too little of the published requirements could be verified to place this row.',
  'msg.rank.bucketOutOfBudget':
    'The remaining cost is {ratio} times the stated ceiling, past the {limit} times this applicant said they could stretch to.',
  'msg.rank.bucketWellPlaced':
    'Requirements are met with room, funding is confirmed, and the remaining cost is within the stated ceiling.',
  'msg.rank.bucketPlausible':
    'Requirements and funding both look reachable on published data.',
  'msg.rank.bucketAmbitious':
    'Either the requirements, the funding or the remaining cost makes this a stretch.',
  'msg.rank.disclaimer':
    'How well this matches your stated priorities, on confirmed data. Not a probability of admission.',
  'msg.conflict.label.ieltsOverall':
    'the minimum overall IELTS band',
  'msg.conflict.label.ieltsSubscore':
    'the minimum IELTS band per section',
  'msg.conflict.label.minGpa':
    'the minimum GPA',
  'msg.conflict.label.satTotal':
    'the minimum SAT total',
  'msg.conflict.label.toeflTotal':
    'the minimum TOEFL total',
  'msg.conflict.label.admissionDeadline':
    'the application deadline',
  'msg.conflict.label.scholarshipDeadline':
    'the scholarship deadline',
  'msg.conflict.label.tuition':
    'the tuition fee',
  'msg.conflict.label.totalCost':
    'the total cost of attendance',
  'msg.conflict.label.awardAmount':
    'the award amount',
  'msg.conflict.label.internationalEligible':
    'eligibility for international students',
  'msg.conflict.subjectFull':
    '{what} — {subjectKey} ({programme})',
  'msg.conflict.subjectKeyed':
    '{what} — {subjectKey}',
  'msg.conflict.subjectProgramme':
    '{what} ({programme})',
  'msg.conflict.subject':
    '{what}',
  'msg.conflict.preferSpecific':
    'Preferring the more specific source ({specificity}); the disagreement is shown rather than resolved.',
  'msg.conflict.moreSpecific':
    'Not a contradiction: a programme-specific rule and a university-wide rule can both be true. The more specific source ({specificity}) applies to this application; the broader rule is kept, not discarded.',
  'msg.conflict.differentPopulation':
    'Not a contradiction: the pages state different populations, so both values can be correct. Neither is discarded.',
  'msg.conflict.differentResidency':
    'Not a contradiction: the pages state different residencys, so both values can be correct. Neither is discarded.',
  'msg.conflict.differentIntake':
    'Not a contradiction: the pages state different intakes, so both values can be correct. Neither is discarded.',
  'msg.conflict.differentAcademicYear':
    'Not a contradiction: the pages state different academic years, so both values can be correct. Neither is discarded.',
  'msg.conflict.differentDegree':
    'Not a contradiction: the pages state different degrees, so both values can be correct. Neither is discarded.',
  'msg.conflict.differentQualification':
    'Not a contradiction: the pages state different qualifications, so both values can be correct. Neither is discarded.',
  'msg.conflict.why':
    'Official sources disagree on {subject}: {values}',
  'msg.currency.staleRates':
    'These conversions use exchange rates from {date}, {days} days old. Treat converted amounts as indicative and check the current rate before relying on one.',

  // --- I18N-3: the Documents screen — the 18 document names (our vocabulary, not a
  // university's words) and the sentences of `DocumentItem.format_notes`.
  'msg.document.transcript':
    'Full academic transcript',
  'msg.document.secondary_diploma':
    'Secondary school diploma (certified copy)',
  'msg.document.translation':
    'Certified English translation of non-English documents',
  'msg.document.apostille':
    'Apostille certification',
  'msg.document.credential_evaluation':
    'Course-by-course credential evaluation (WES/ECE)',
  'msg.document.passport':
    'Passport identity page (copy)',
  'msg.document.photo':
    'Passport-size photograph (digital image)',
  'msg.document.personal_statement':
    'Personal statement',
  'msg.document.motivation_letter':
    'Statement of motivation',
  'msg.document.essay':
    'Personal Essay',
  'msg.document.recommendation_letter':
    'Letter of recommendation',
  'msg.document.academic_reference':
    'Academic reference',
  'msg.document.cv':
    'Curriculum vitae',
  'msg.document.portfolio':
    'Portfolio',
  'msg.document.financial_proof':
    'Proof of financial resources',
  'msg.document.english_test_report':
    'English language test report',
  'msg.document.entrance_test':
    'Admission test result',
  'msg.document.application_form':
    'Application form',
  'msg.document.note.optional':
    'Optional, as published.',
  'msg.document.note.conditional':
    'Conditional, as published.',
  'msg.document.note.conditionWhen':
    'Required only when: {condition}.',
  'msg.document.note.possiblyOutdated':
    'Possibly outdated: {reasons}.',

  // --- the catalogue cards in kb mode (CAT-1) -------------------------------
  'catalogue.kb.coverage': '{n} of {total} universities have verified data',
  'catalogue.kb.filter': 'Verified data only',
  'catalogue.kb.chip': 'Verified knowledge base',
  'catalogue.kb.none': 'No verified data yet',
  'catalogue.kb.answers': '{n}/6 answers',
  'catalogue.kb.documents.one': '{n} document',
  'catalogue.kb.documents.few': '{n} documents',
  'catalogue.kb.documents.many': '{n} documents',
  'catalogue.kb.documents.other': '{n} documents',
  'catalogue.kb.programme.known': 'Programme page',
  'catalogue.kb.programme.related_only': 'Related programme only',
  'catalogue.kb.programme.not_offered': 'No CS bachelor\'s published',
  'catalogue.kb.programme.unknown': 'Programme page not verified',
  'catalogue.kb.staleCount.one': '{n} fact not current',
  'catalogue.kb.staleCount.few': '{n} facts not current',
  'catalogue.kb.staleCount.many': '{n} facts not current',
  'catalogue.kb.staleCount.other': '{n} facts not current',
  'catalogue.kb.tuition': 'Verified tuition',
  'catalogue.kb.noFee': 'No verified fee yet',
  'catalogue.kb.historical': 'Historical estimate',
  'catalogue.kb.historicalValue': 'USD {min}–{max}; period and scope unverified',
  'catalogue.kb.verifiedOn': 'Verified {date} ({label})',
  'catalogue.kb.review.human': 'human verified',
  'catalogue.kb.review.expert': 'expert-checked, quote verified',
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
  'detail.kbUnknown.field.english': 'Требование к английскому',
  'detail.kbUnknown.field.gpa': 'Минимальный балл',
  'detail.kbUnknown.field.deadline': 'Срок подачи',
  'detail.kbUnknown.field.tuition': 'Плата за обучение',
  'detail.kbUnknown.field.scholarship_exists': 'Стипендии',
  'detail.kbUnknown.field.scholarship_international': 'Стипендии для иностранных студентов',
  'detail.kbUnknown.notPublished': '{fields}: университет не публикует, проверка эксперта {date}.',
  'detail.kbUnknown.notPublishedUndated': '{fields}: университет не публикует (проверка эксперта).',
  'detail.kbUnknown.access': '{fields}: официальная страница недоступна с наших серверов; уточните в приёмной комиссии.',
  'detail.kbUnknown.notVerified': '{fields}: пока не проверено.',
  'detail.noCostKb': 'В проверенной базе знаний пока нет подтверждённой платы за обучение для этой программы и набора.',
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
  'detail.docs.step.applicant': 'Вы',
  'detail.docs.step.school': 'Ваша школа',
  'detail.docs.step.recommender': 'Ваш рекомендатель',
  'detail.docs.step.third_party': 'Третья сторона',
  'detail.docs.after': 'после: {what}',
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

  'documents.eyebrow': 'Документы и сроки',
  'documents.title': 'Готовьтесь {accent}',
  'documents.titleAccent': 'уверенно.',
  'documents.emptyLede': 'Список документов появится, когда вы сохраните программы в разделе Plan и соберёте их официальные требования.',
  'documents.emptyTitle': 'Списков документов пока нет',
  'documents.emptyBody': 'Выберите программу в разделе Find, затем соберите документы в разделе Plan.',
  'documents.lede': 'Упорядочено по времени подготовки, а не по сроку. Пункты вверху зависят от других людей, поэтому начинать нужно с них.',
  'documents.calendarSummary': 'Календарь и сроки по вашему короткому списку ({n})',
  'documents.calendarTitle': 'Все сроки по вашему короткому списку',
  'documents.addToCalendar': 'Добавить в календарь (.ics)',
  'documents.passed': 'прошёл',
  'documents.noDeadlines': 'Сроков с датой не найдено.',
  'documents.admissionApplication': 'Заявление на поступление',
  'documents.ticked': 'Отмечено {done} из {total}. Составлено {when}.',
  'documents.completeness.official': 'с официальных страниц',
  'documents.completeness.partial': 'прочитано частично',
  'documents.completeness.unavailable': 'официальный список не найден',
  'documents.owner.thirdParty': 'Третья сторона (переводчик, WES/ECE, нотариус)',
  'documents.forScholarship': 'для стипендии',
  'documents.forAdmission': 'для поступления',
  'documents.maxWords': 'не более {n} слов',
  'documents.maxPages': 'не более {n} стр.',
  'documents.maxSize': 'не более {n} МБ',
  'documents.translation': 'нужен заверенный перевод',
  'documents.notarisation': 'нужно нотариальное заверение',
  'documents.apostille': 'нужен апостиль',
  'documents.credentialEvaluation': 'нужна оценка документов об образовании',
  'documents.due': 'до {date}',
  'documents.stillToConfirm': 'Ещё нужно уточнить',
  'documents.ask': 'Кого спросить: {contact}',
  'documents.notice': 'Unimatch составляет этот список. Он не загружает документы, не подаёт заявление, ничего не подписывает от вашего имени и не платит сборы. Эти шаги остаются за вами.',

  'msg.question.campus':
    '{university} предлагает {programme} в нескольких кампусах, и в каждый подаётся отдельная заявка. Какой кампус вам нужен?',
  'msg.question.entryRequirementsPage':
    'На какой официальной странице опубликованы требования для поступления на {programme}?',
  'msg.question.programmePage':
    'На какой официальной странице опубликована программа {programme}?',
  'msg.question.programmeNotOffered':
    '{university} не публикует бакалавриат по Computer Science (проверено {date}).',
  'msg.question.programmeRelatedOnly':
    'Отдельный бакалавриат по Computer Science не опубликован; ближайший официальный путь — {route} (официальная страница: {url}). Подходит ли вам этот путь?',
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
  'msg.why.programmeNotOffered':
    'Ближайшая официальная программа — {route} (официальная страница: {url}).',
  'msg.why.programmeNotOfferedNoRoute':
    'В проверенной базе знаний записано, что такой программы нет, поэтому ничего не показывается как данные этой программы.',
  'msg.why.programmeRelatedOnly':
    'В проверенной базе знаний записано, что отдельного бакалавриата по Computer Science в {university} нет (проверка эксперта {date}). Подходит ли вам ближайший путь — решать вам.',
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
  'msg.coverage.kb':
    'Проверенная база знаний отвечает по {universities} из {total} университетов каталога '
    + '(бакалавриат по Computer Science). Университет вне её или другая программа получает '
    + '«Проверенных данных пока нет»; во время исследования не читается ни одна страница.',
  'msg.coverage.live':
    'Живой режим ищет по {institutions} отобранным учебным заведениям в {countries} странах. '
    + 'Результаты зависят от выбранных направлений и от того, какие официальные страницы '
    + 'доступны. Недостающие или непроверенные данные остаются видны в результатах.',
  'research.kbNotice.title': 'Исследование отвечает по проверенной базе знаний.',
  'research.kbNotice.body':
    'Во время исследования не читается ни одна страница университета и ничего не '
    + 'отправляется поисковым сервисам.',
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
  'detail.fee.perYear': '{amount} в год',
  'detail.fee.perPeriod': '{amount} за {period}',
  'detail.fee.year': 'учебный год {year}',
  'detail.fee.noYear': 'учебный год не указан',
  'detail.fee.notCurrent': 'не актуально: {reason}',
  'detail.fee.notYearly': 'опубликовано за {period}, а не как годовая сумма',
  'detail.fee.perUnit': 'опубликовано за {period} (годовая сумма не указана)',
  'detail.fee.range': 'опубликованный диапазон {range}',
  'detail.fee.period.semester': 'семестр',
  'detail.fee.period.credit': 'кредит',
  'detail.fee.period.programme': 'всю программу (лет: {n})',
  'detail.costCaveat': 'Стоимость обучения актуальна, с оговоркой: {caveat}.',
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
  'msg.question.languageNoneRecorded':
    '{statement} Требует ли {university} какое-либо другое подтверждение знания языка? В проверенной базе знаний такого требования нет.',
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
  'msg.gap.kbNoFee':
    'В проверенной базе знаний пока нет платы за обучение для этой программы, поэтому оставшаяся сумма не рассчитана.',
  'msg.gap.kbTuitionRange':
    'Плата за обучение опубликована только диапазоном, {range}; в расчёте стоимости взята верхняя граница, чтобы не занизить её.',
  'msg.req.intakeOpen':
    'Приём заявлений на этот набор',
  'msg.req.deadline':
    'Срок подачи заявлений',
  'msg.req.minGpa':
    'Минимальный GPA',
  'msg.req.satTotal':
    'Общий балл SAT',
  'msg.req.satPolicy':
    'Правила по SAT',
  'msg.req.portfolio':
    'Портфолио',
  'msg.req.interview':
    'Собеседование',
  'msg.req.entranceExam':
    'Вступительный экзамен',
  'msg.req.credentialEvaluation':
    'Оценка документов об образовании',
  'msg.req.requiredSubjects':
    'Обязательные предметы',
  'msg.req.academicEntry':
    'Академические требования к поступлению',
  'msg.req.ieltsType':
    'Принимаемый вид IELTS',
  'msg.req.englishWaiver':
    'Освобождение от теста по английскому',
  'msg.req.ieltsOverall':
    'IELTS, общий балл',
  'msg.req.ieltsBand':
    'IELTS, раздел {band}',
  'msg.req.toeflTotal':
    'TOEFL, общий балл',
  'msg.req.scholarshipCitizenship':
    'Стипендия: требование к гражданству',
  'msg.req.scholarshipInternational':
    'Стипендия: доступность для иностранных студентов',
  'msg.req.scholarshipFaculty':
    'Стипендия: ограничение по факультету',
  'msg.req.scholarshipProgramme':
    'Стипендия: ограничение по программе',
  'msg.req.scholarshipDeadline':
    'Срок подачи на стипендию',
  'msg.req.scholarshipTest':
    'Стипендия: минимум {test}',
  'msg.explain.noMinimum':
    'Официальный минимум для «{label}» не найден; это не считается препятствием.',
  'msg.explain.notNumber':
    'Опубликованное значение «{label}» не удалось прочитать как число.',
  'msg.explain.noApplicantValue':
    'Программа публикует минимум {published}, но в профиле пока нет значения «{label}». Добавьте его, чтобы завершить эту проверку.',
  'msg.explain.minimumNotMet':
    'Опубликованный минимум {published}; у вас {applicant}. Опубликованный минимум не достигнут.',
  'msg.explain.minimumMet':
    'Опубликованный минимум {published}; у вас {applicant}.',
  'msg.explain.intakeClosed':
    'Программа официально сообщает, что на этот набор заявления не принимаются.',
  'msg.explain.deadlineUnparsed':
    'Срок опубликован, но его не удалось прочитать как дату.',
  'msg.explain.deadlinePassed':
    'Опубликованный срок {date} уже прошёл.',
  'msg.explain.deadlineByPopulation':
    'Самый ранний срок подачи — {date}; срок зависит от вашей категории оплаты в этом университете ({deadlines}).',
  'msg.explain.deadlineOpen':
    'Заявления принимаются до {date}.',
  'msg.explain.allDeadlinesPassed':
    'Все опубликованные сроки прошли ({deadlines}).',
  'msg.explain.deadlineByPopulationPassed':
    'Срок зависит от вашей категории оплаты в этом университете ({deadlines}). Срок для «{populations}» уже прошёл; уточните, какой относится к вам.',
  'msg.explain.gpaScale':
    'Ваш GPA указан по шкале {scale}, а программа публикует другую шкалу. Без документированного метода пересчёт не применяется, поэтому здесь это решить нельзя.',
  'msg.explain.testOptional':
    'Программа не требует тестов в обязательном порядке, поэтому отсутствие балла SAT не препятствие.',
  'msg.explain.satPolicyNoMinimum':
    'Правила по SAT опубликованы, но минимальный балл не найден.',
  'msg.explain.actionRequired':
    'Требуется: «{label}». Это шаг, который нужно выполнить, а не причина отказа.',
  'msg.explain.subjectsPresent':
    'Все опубликованные обязательные предметы есть в профиле.',
  'msg.explain.subjectsMissing':
    'Нет в профиле: {subjects}. Добавьте их, если вы их изучали; иначе это настоящий пробел.',
  'msg.explain.noAssessable':
    'Академические требования к поступлению, которые можно оценить, не найдены. Будущий срок подачи или необязательный тест не означают, что вы проходите по требованиям.',
  'msg.explain.ieltsTypes':
    'Программа принимает {accepted}; у вас {held}.',
  'msg.explain.englishWaiver':
    'Программа публикует условия, при которых тест по английскому не нужен. Сверьте их со своим обучением, прежде чем записываться на тест, — подходят ли они вам, эта страница не решает.',
  'msg.explain.citizenshipUnreadable':
    'Стипендия публикует требование к гражданству, которое не удалось прочитать как список стран. Нужно официальное уточнение.',
  'msg.explain.citizenshipNamed':
    'Опубликованное ограничение называет {phrase}, что совпадает с гражданством {country} в профиле.',
  'msg.explain.citizenshipMember':
    '{country} входит в {group}, которое стипендия называет своим ограничением.',
  'msg.explain.citizenshipGroup':
    'Стипендия ограничена группой («{restrictions}»), состав которой не опубликован списком стран. Входит ли в неё {held}, по странице решить нельзя, поэтому это должна подтвердить приёмная комиссия.',
  'msg.explain.citizenshipExcluded':
    'Стипендия ограничена: {restrictions}. Заявитель с гражданством {held} не подходит.',
  'msg.explain.internationalClosed':
    'Стипендия официально закрыта для иностранных студентов.',
  'msg.explain.internationalOpen':
    'Стипендия официально открыта для иностранных студентов любого гражданства.',
  'msg.explain.restriction':
    'Страница ограничивает эту стипендию: {restriction}. Относится ли к этому ваша программа, страница не решает — спросите приёмную комиссию, прежде чем рассчитывать на стипендию.',
  'msg.explain.scholarshipTestMissing':
    'Для стипендии нужен {test} {minimum}; в профиле нет балла.',
  'msg.explain.scholarshipDeadlinePassed':
    'Опубликованный срок подачи на стипендию {date} уже прошёл.',
  'msg.degree.noText':
    'нет текста или уровня образования для проверки',
  'msg.degree.excludes':
    'страница прямо исключает заявителей уровня {degree}',
  'msg.degree.forOther':
    'страница указывает, что стипендия для уровня {level}, а не {degree}',
  'msg.degree.statesFor':
    'страница указывает, что стипендия для заявителей уровня {degree}',
  'msg.degree.onlyOthers':
    'страница описывает стипендию только для {levels} и нигде не упоминает {degree}',
  'msg.degree.unstated':
    'страница не указывает, к каким уровням образования относится стипендия',
  'msg.degree.excludesLevel':
    'страница исключает этот уровень.',
  'msg.missing.notCovered':
    '{category} не покрывается',
  'msg.missing.unknown':
    '{category} — неизвестно',
  'msg.missing.partial':
    '{category} — частично',
  'msg.class.excluded':
    'Опубликованные условия исключают этого заявителя.',
  'msg.class.degreeLevel':
    'Не относится к уровню образования этого заявителя: {degreeReason}',
  'msg.class.citizenship':
    'Стипендия ограничена: {restrictions}, — и этот заявитель сюда не входит.',
  'msg.class.notInternational':
    'Официальный источник сообщает, что стипендия не открыта для иностранных студентов.',
  'msg.class.noCoverage':
    'Официальные данные о покрытии по статьям расходов не найдены.',
  'msg.class.promotionalNoBreakdown':
    'На странице есть рекламные формулировки ({words}), но разбивки нет.',
  'msg.class.needBased':
    'Размер стипендии зависит от проверки финансовой нуждаемости, документы на которую ещё не поданы.',
  'msg.class.fullRide':
    'Официальные источники подтверждают покрытие обучения, обязательных сборов, жилья и питания или равноценной стипендии на проживание.',
  'msg.class.fullTuition':
    'Покрытие платы за обучение подтверждено, но {missing} — это полная оплата обучения, а не полное покрытие.',
  'msg.class.shareUnknown':
    'Покрытие частичное, но сумма стипендии или стоимость обучения официально не опубликованы, поэтому долю рассчитать нельзя.',
  'msg.class.largeGrant':
    'Покрывает примерно {share} опубликованной стоимости обучения; значительная часть расходов остаётся.',
  'msg.class.partial':
    'Покрывает примерно {share} опубликованной стоимости обучения.',
  'msg.class.promotional':
    'На странице есть рекламные формулировки вроде «full ride»; классификация здесь следует опубликованной таблице покрытия.',
  'msg.class.onlyFullRide':
    'В профиле указано, что вариант доступен только при полном покрытии; эта стипендия классифицирована как «{classification}».',
  'msg.class.noTuitionOnly':
    'В профиле указано, что стипендию только на обучение вы не примете.',
  'msg.class.noPartial':
    'В профиле указано, что частичную стипендию вы не примете.',
  'msg.class.needDocuments':
    'Эта стипендия назначается по нуждаемости, а в профиле указано, что финансовые документы не будут поданы, — а именно они нужны для такой заявки.',
  'msg.class.mustCover':
    'Профиль требует покрытия: {categories}; эта стипендия сообщает, что не покрывает это.',
  'msg.rank.academicNoMargin':
    'Все опубликованные требования выполнены; числовых минимумов, по которым можно измерить запас, нет.',
  'msg.rank.academicMargin':
    'Все опубликованные требования выполнены, в среднем на {margin} выше минимумов.',
  'msg.rank.academicPending':
    'Требования выполнены, кроме пунктов, которые ещё ожидают решения.',
  'msg.rank.academicGap':
    'Как минимум одно опубликованное требование не выполнено.',
  'msg.rank.academicUnknown':
    'Опубликованные требования не удалось проверить.',
  'msg.rank.fundingUnknown':
    'Официальная информация о финансировании не подтверждена.',
  'msg.rank.fundingConfirmed':
    'Финансирование: подтверждённая возможность.',
  'msg.rank.fundingCompetitive':
    'Финансирование: возможность по конкурсу.',
  'msg.rank.fundingLimited':
    'Финансирование: ограниченная возможность.',
  'msg.rank.fundingNotEligible':
    'Финансирование: вы не подходите.',
  'msg.rank.gapUnknown':
    'Остаток к оплате за год рассчитать не удалось.',
  'msg.rank.noCeiling':
    'Предел семейного бюджета для сравнения не указан.',
  'msg.rank.nothingRemains':
    'Платить ничего не остаётся.',
  'msg.rank.zeroContribution':
    'Семья указала, что не может вносить ничего, а остаётся {gap} в год.',
  'msg.rank.withinCeiling':
    'Остаток {gap} в год укладывается в указанный предел {ceiling}.',
  'msg.rank.timesCeiling':
    'Остаток {gap} в год в {ratio} раза больше указанного предела {ceiling}.',
  'msg.rank.aboveCeiling':
    'Остаток {gap} в год на {over} выше указанного предела {ceiling}.',
  'msg.rank.preferredCountry':
    '{country} — предпочтительная страна.',
  'msg.rank.unpreferredCountry':
    '{country} не входит в список предпочтительных стран.',
  'msg.rank.noRank':
    'Позиция в рейтинге не найдена.',
  'msg.rank.insideBand':
    'Место в рейтинге {rank}, в пределах запрошенного диапазона «{band}».',
  'msg.rank.outsideTop':
    'Место в рейтинге {rank}, за пределами топ-{top}.',
  'msg.rank.consensus':
    'Сводная позиция в рейтинге: {rank}.',
  'msg.rank.ranked':
    'Место в рейтинге: {rank}.',
  'msg.rank.noPreference':
    'Предпочтение по параметру «{axis}» не указано.',
  'msg.rank.attributeUnknown':
    'Параметр «{axis}» этого университета неизвестен.',
  'msg.rank.attributeMatches':
    '{actual} совпадает с указанным предпочтением.',
  'msg.rank.ladderStep':
    '{actual} при предпочтении {preferred}: разница {steps} шаг.',
  'msg.rank.ladderSteps':
    '{actual} при предпочтении {preferred}: разница {steps} шага.',
  'msg.rank.ladderDiffers':
    '{actual} отличается от предпочтения {preferred}.',
  'msg.rank.careersNotPriority':
    'Карьера не была указана как приоритет.',
  'msg.rank.coop':
    'Официально предлагается co-op или год практики.',
  'msg.rank.internships':
    'Официально описана программа стажировок.',
  'msg.rank.careersPage':
    'Страница о карьере есть, но на ней нет ничего достаточно конкретного для проверки.',
  'msg.rank.noCareers':
    'Официальная информация о карьере не найдена.',
  'msg.rank.pswNotPriority':
    'Работа после учёбы не была указана как приоритет.',
  'msg.rank.pswUnknown':
    'Правила работы после учёбы не подтверждены в месяцах.',
  'msg.rank.psw':
    'Опубликовано право на работу после учёбы на {months} мес.',
  'msg.rank.excludedCountry':
    '{country} — в списке исключённых вами стран.',
  'msg.rank.knockoutUnmet':
    '{requirement}: опубликованное требование не выполнено',
  'msg.rank.knockout':
    '{requirement} — {explanation}',
  'msg.rank.bucketInsufficient':
    'Слишком мало опубликованных требований удалось проверить, чтобы определить место этого варианта.',
  'msg.rank.bucketOutOfBudget':
    'Остаток к оплате в {ratio} раза больше указанного предела — больше тех {limit} раза, на которые, по словам заявителя, можно выйти.',
  'msg.rank.bucketWellPlaced':
    'Требования выполнены с запасом, финансирование подтверждено, остаток к оплате в пределах указанного предела.',
  'msg.rank.bucketPlausible':
    'И требования, и финансирование выглядят достижимыми по опубликованным данным.',
  'msg.rank.bucketAmbitious':
    'Требования, финансирование или остаток к оплате делают этот вариант амбициозным.',
  'msg.rank.disclaimer':
    'Насколько вариант подходит под ваши приоритеты — по подтверждённым данным. Это не вероятность поступления.',
  'msg.conflict.label.ieltsOverall':
    'минимальный общий балл IELTS',
  'msg.conflict.label.ieltsSubscore':
    'минимальный балл IELTS по каждому разделу',
  'msg.conflict.label.minGpa':
    'минимальный GPA',
  'msg.conflict.label.satTotal':
    'минимальный общий балл SAT',
  'msg.conflict.label.toeflTotal':
    'минимальный общий балл TOEFL',
  'msg.conflict.label.admissionDeadline':
    'срок подачи заявлений',
  'msg.conflict.label.scholarshipDeadline':
    'срок подачи на стипендию',
  'msg.conflict.label.tuition':
    'плата за обучение',
  'msg.conflict.label.totalCost':
    'полная стоимость обучения',
  'msg.conflict.label.awardAmount':
    'сумма стипендии',
  'msg.conflict.label.internationalEligible':
    'доступность для иностранных студентов',
  'msg.conflict.subjectFull':
    '{what}, {subjectKey} — программа {programme}',
  'msg.conflict.subjectKeyed':
    '{what}, {subjectKey}',
  'msg.conflict.subjectProgramme':
    '{what} — программа {programme}',
  'msg.conflict.subject':
    '{what}',
  'msg.conflict.preferSpecific':
    'Предпочтение отдаётся более конкретному источнику ({specificity}); расхождение показано, а не устранено.',
  'msg.conflict.moreSpecific':
    'Это не противоречие: правило программы и общее правило университета могут быть верны одновременно. К этой заявке относится более конкретный источник ({specificity}); более общее правило сохранено, а не отброшено.',
  'msg.conflict.differentPopulation':
    'Это не противоречие: страницы говорят о разных категориях заявителей, поэтому оба значения могут быть верны. Ни одно не отброшено.',
  'msg.conflict.differentResidency':
    'Это не противоречие: страницы говорят о разном статусе резидентства, поэтому оба значения могут быть верны. Ни одно не отброшено.',
  'msg.conflict.differentIntake':
    'Это не противоречие: страницы говорят о разных наборах, поэтому оба значения могут быть верны. Ни одно не отброшено.',
  'msg.conflict.differentAcademicYear':
    'Это не противоречие: страницы говорят о разных учебных годах, поэтому оба значения могут быть верны. Ни одно не отброшено.',
  'msg.conflict.differentDegree':
    'Это не противоречие: страницы говорят о разных уровнях образования, поэтому оба значения могут быть верны. Ни одно не отброшено.',
  'msg.conflict.differentQualification':
    'Это не противоречие: страницы говорят о разных документах об образовании, поэтому оба значения могут быть верны. Ни одно не отброшено.',
  'msg.conflict.why':
    'Официальные источники расходятся в вопросе «{subject}»: {values}',
  'msg.currency.staleRates':
    'Пересчёт использует курсы валют на {date}, им {days} дн. Считайте пересчитанные суммы ориентировочными и проверьте текущий курс, прежде чем на них полагаться.',

  // --- I18N-3: document names and notes (provisional terms: docs/i18n/GLOSSARY.md)
  'msg.document.transcript':
    'Полная выписка оценок (транскрипт)',
  'msg.document.secondary_diploma':
    'Аттестат о среднем образовании (заверенная копия)',
  'msg.document.translation':
    'Заверенный перевод на английский документов, составленных не на английском',
  'msg.document.apostille':
    'Заверение апостилем',
  'msg.document.credential_evaluation':
    'Попредметная оценка документов об образовании (WES/ECE)',
  'msg.document.passport':
    'Страница паспорта с личными данными (копия)',
  'msg.document.photo':
    'Фотография паспортного формата (в электронном виде)',
  'msg.document.personal_statement':
    'Личное заявление',
  'msg.document.motivation_letter':
    'Мотивационное письмо',
  'msg.document.essay':
    'Личное эссе',
  'msg.document.recommendation_letter':
    'Рекомендательное письмо',
  'msg.document.academic_reference':
    'Рекомендация от преподавателя',
  'msg.document.cv':
    'Резюме (CV)',
  'msg.document.portfolio':
    'Портфолио',
  'msg.document.financial_proof':
    'Подтверждение наличия финансовых средств',
  'msg.document.english_test_report':
    'Результаты теста по английскому языку',
  'msg.document.entrance_test':
    'Результат вступительного теста',
  'msg.document.application_form':
    'Форма заявления',
  'msg.document.note.optional':
    'По желанию, как опубликовано.',
  'msg.document.note.conditional':
    'Требуется при определённых условиях, как опубликовано.',
  'msg.document.note.conditionWhen':
    'Требуется, только если: {condition}.',
  'msg.document.note.possiblyOutdated':
    'Возможно, устарело: {reasons}.',

  'catalogue.kb.coverage': 'Проверенные данные есть у {n} из {total} университетов',
  'catalogue.kb.filter': 'Только с проверенными данными',
  'catalogue.kb.chip': 'Проверенная база знаний',
  'catalogue.kb.none': 'Проверенных данных пока нет',
  'catalogue.kb.answers': 'ответов: {n}/6',
  'catalogue.kb.documents.one': '{n} документ',
  'catalogue.kb.documents.few': '{n} документа',
  'catalogue.kb.documents.many': '{n} документов',
  'catalogue.kb.documents.other': '{n} документа',
  'catalogue.kb.programme.known': 'Страница программы',
  'catalogue.kb.programme.related_only': 'Только смежная программа',
  'catalogue.kb.programme.not_offered': 'Бакалавриат по Computer Science не опубликован',
  'catalogue.kb.programme.unknown': 'Страница программы не проверена',
  'catalogue.kb.staleCount.one': '{n} факт неактуален',
  'catalogue.kb.staleCount.few': '{n} факта неактуальны',
  'catalogue.kb.staleCount.many': '{n} фактов неактуальны',
  'catalogue.kb.staleCount.other': '{n} факта неактуальны',
  'catalogue.kb.tuition': 'Проверенная плата за обучение',
  'catalogue.kb.noFee': 'Проверенной платы пока нет',
  'catalogue.kb.historical': 'Историческая оценка',
  'catalogue.kb.historicalValue': 'USD {min}–{max}; период и охват не проверены',
  'catalogue.kb.verifiedOn': 'Проверено {date} ({label})',
  'catalogue.kb.review.human': 'проверено человеком',
  'catalogue.kb.review.expert': 'проверено экспертом, цитата подтверждена',
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
  'detail.kbUnknown.field.english': 'Ағылшын тілі талабы',
  'detail.kbUnknown.field.gpa': 'Ең төменгі балл',
  'detail.kbUnknown.field.deadline': 'Өтінім беру мерзімі',
  'detail.kbUnknown.field.tuition': 'Оқу ақысы',
  'detail.kbUnknown.field.scholarship_exists': 'Стипендиялар',
  'detail.kbUnknown.field.scholarship_international': 'Шетелдік студенттерге арналған стипендиялар',
  'detail.kbUnknown.notPublished': '{fields}: университет жарияламайды, сарапшы тексерген күні {date}.',
  'detail.kbUnknown.notPublishedUndated': '{fields}: университет жарияламайды (сарапшы тексерген).',
  'detail.kbUnknown.access': '{fields}: ресми бет біздің серверлерден ашылмайды; қабылдау комиссиясынан сұраңыз.',
  'detail.kbUnknown.notVerified': '{fields}: әзірге тексерілмеген.',
  'detail.noCostKb': 'Тексерілген білім базасында бұл бағдарлама мен қабылдау үшін расталған оқу ақысы әзірге жоқ.',
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
  'detail.docs.step.applicant': 'Сіз',
  'detail.docs.step.school': 'Мектебіңіз',
  'detail.docs.step.recommender': 'Ұсыным берушіңіз',
  'detail.docs.step.third_party': 'Үшінші тарап',
  'detail.docs.after': 'алдымен: {what}',
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

  'documents.eyebrow': 'Құжаттар мен мерзімдер',
  'documents.title': '{accent} дайындалыңыз.',
  'documents.titleAccent': 'Сеніммен',
  'documents.emptyLede': 'Құжаттар тізімі Plan бөлімінде бағдарламаларды сақтап, олардың ресми талаптарын жинағаннан кейін пайда болады.',
  'documents.emptyTitle': 'Құжаттар тізімі әзірге жоқ',
  'documents.emptyBody': 'Find бөлімінде бағдарламаны таңдаңыз, содан кейін Plan бөлімінде құжаттарды жинаңыз.',
  'documents.lede': 'Мерзім бойынша емес, дайындау уақыты бойынша реттелген. Жоғарыдағы тармақтар басқа адамдарға байланысты, сондықтан оларды бірінші бастау керек.',
  'documents.calendarSummary': 'Қысқа тізіміңіз бойынша күнтізбе мен мерзімдер ({n})',
  'documents.calendarTitle': 'Қысқа тізіміңіздегі барлық мерзім',
  'documents.addToCalendar': 'Күнтізбеге қосу (.ics)',
  'documents.passed': 'өтті',
  'documents.noDeadlines': 'Күні көрсетілген мерзімдер табылмады.',
  'documents.admissionApplication': 'Түсуге өтініш',
  'documents.ticked': '{total} тармақтың {done}-і белгіленді. {when} құрастырылды.',
  'documents.completeness.official': 'ресми беттерден',
  'documents.completeness.partial': 'ішінара оқылды',
  'documents.completeness.unavailable': 'ресми тізім табылмады',
  'documents.owner.thirdParty': 'Үшінші тарап (аудармашы, WES/ECE, нотариус)',
  'documents.forScholarship': 'стипендия үшін',
  'documents.forAdmission': 'түсу үшін',
  'documents.maxWords': 'ең көбі {n} сөз',
  'documents.maxPages': 'ең көбі {n} бет',
  'documents.maxSize': 'ең көбі {n} МБ',
  'documents.translation': 'куәландырылған аударма қажет',
  'documents.notarisation': 'нотариат куәландыруы қажет',
  'documents.apostille': 'апостиль қажет',
  'documents.credentialEvaluation': 'білім туралы құжаттарды бағалау қажет',
  'documents.due': 'мерзімі {date}',
  'documents.stillToConfirm': 'Әлі нақтылау керек',
  'documents.ask': 'Кімнен сұрау керек: {contact}',
  'documents.notice': 'Бұл тізімді Unimatch құрастырады. Ол құжаттарды жүктемейді, өтініш бермейді, сіздің атыңыздан ештеңеге қол қоймайды және алым төлемейді. Бұл қадамдар сізде қалады.',

  'msg.question.campus':
    '{university} {programme} бағдарламасын бірнеше кампуста ұсынады, әрқайсысына бөлек өтінім беріледі. Сізге қай кампус керек?',
  'msg.question.entryRequirementsPage':
    '{programme} бағдарламасына түсу талаптары қай ресми бетте жарияланған?',
  'msg.question.programmePage':
    '{programme} бағдарламасы қай ресми бетте жарияланған?',
  'msg.question.programmeNotOffered':
    '{university} Computer Science бакалавриатын жарияламайды (тексерілген күні {date}).',
  'msg.question.programmeRelatedOnly':
    'Computer Science бойынша жеке бакалавриат жарияланбаған; ең жақын ресми жол — {route} (ресми беті: {url}). Бұл жол сізге сәйкес пе?',
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
  'msg.why.programmeNotOffered':
    'Ең жақын ресми бағдарлама — {route} (ресми беті: {url}).',
  'msg.why.programmeNotOfferedNoRoute':
    'Тексерілген білім базасында мұндай бағдарлама жоқ деп жазылған, сондықтан ештеңе осы бағдарламаныкі ретінде көрсетілмейді.',
  'msg.why.programmeRelatedOnly':
    'Тексерілген білім базасында {university} университетінде Computer Science бойынша жеке бакалавриат жоқ деп жазылған (сарапшы тексерген күні {date}). Ең жақын жол сізге сәйкес пе — оны өзіңіз шешесіз.',
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
  'msg.coverage.kb':
    'Тексерілген білім базасы каталогтағы {total} университеттің {universities} '
    + 'университеті бойынша жауап береді (Computer Science бакалавриаты). Одан тыс '
    + 'университет немесе басқа бағдарлама «Әзірге тексерілген дерек жоқ» деген жауап '
    + 'алады; зерттеу барысында бірде-бір бет оқылмайды.',
  'msg.coverage.live':
    'Тікелей режим {countries} елдегі {institutions} іріктелген оқу орны бойынша іздейді. '
    + 'Нәтижелер таңдалған бағыттарға және қай ресми беттер қолжетімді екеніне байланысты. '
    + 'Жетіспейтін немесе тексерілмеген дәлелдер нәтижелерде көрінеді.',
  'research.kbNotice.title': 'Зерттеу тексерілген білім базасы бойынша жауап береді.',
  'research.kbNotice.body':
    'Зерттеу барысында университеттің бірде-бір беті оқылмайды және іздеу қызметтеріне '
    + 'ештеңе жіберілмейді.',
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
  'detail.fee.perYear': 'жылына {amount}',
  'detail.fee.perPeriod': '{period} үшін {amount}',
  'detail.fee.year': '{year} оқу жылы',
  'detail.fee.noYear': 'оқу жылы көрсетілмеген',
  'detail.fee.notCurrent': 'өзекті емес: {reason}',
  'detail.fee.notYearly': '{period} үшін жарияланған, жылдық сома ретінде емес',
  'detail.fee.perUnit': '{period} үшін жарияланған (жылдық сома көрсетілмеген)',
  'detail.fee.range': 'жарияланған аралық {range}',
  'detail.fee.period.semester': 'семестр',
  'detail.fee.period.credit': 'кредит',
  'detail.fee.period.programme': 'бүкіл бағдарлама ({n} жыл)',
  'detail.costCaveat': 'Оқу ақысы өзекті, ескертпемен: {caveat}.',
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
  'msg.question.languageNoneRecorded':
    '{statement} {university} басқа тіл білімін растайтын құжатты талап ете ме? Тексерілген білім базасында ондай талап жоқ.',
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
  'msg.gap.kbNoFee':
    'Тексерілген білім базасында бұл бағдарламаның оқу ақысы әзірге жоқ, сондықтан қалған сома есептелмеді.',
  'msg.gap.kbTuitionRange':
    'Оқу ақысы тек аралықпен жарияланған, {range}; құн төмендетіп көрсетілмес үшін оның жоғарғы шегі алынды.',
  'msg.req.intakeOpen':
    'Осы қабылдауға өтініш қабылдау',
  'msg.req.deadline':
    'Өтініш беру мерзімі',
  'msg.req.minGpa':
    'Ең төменгі GPA',
  'msg.req.satTotal':
    'SAT жалпы балы',
  'msg.req.satPolicy':
    'SAT бойынша талап',
  'msg.req.portfolio':
    'Портфолио',
  'msg.req.interview':
    'Сұхбат',
  'msg.req.entranceExam':
    'Түсу емтиханы',
  'msg.req.credentialEvaluation':
    'Білім туралы құжаттарды бағалау',
  'msg.req.requiredSubjects':
    'Міндетті пәндер',
  'msg.req.academicEntry':
    'Түсуге қойылатын академиялық талаптар',
  'msg.req.ieltsType':
    'Қабылданатын IELTS түрі',
  'msg.req.englishWaiver':
    'Ағылшын тілі тестінен босату',
  'msg.req.ieltsOverall':
    'IELTS, жалпы балл',
  'msg.req.ieltsBand':
    'IELTS, {band} бөлімі',
  'msg.req.toeflTotal':
    'TOEFL, жалпы балл',
  'msg.req.scholarshipCitizenship':
    'Стипендия: азаматтық талабы',
  'msg.req.scholarshipInternational':
    'Стипендия: шетелдік студенттерге қолжетімділігі',
  'msg.req.scholarshipFaculty':
    'Стипендия: факультет бойынша шектеу',
  'msg.req.scholarshipProgramme':
    'Стипендия: бағдарлама бойынша шектеу',
  'msg.req.scholarshipDeadline':
    'Стипендияға өтініш беру мерзімі',
  'msg.req.scholarshipTest':
    'Стипендия: {test} ең төменгі шегі',
  'msg.explain.noMinimum':
    '«{label}» үшін ресми ең төменгі шек табылмады; бұл кедергі деп есептелмейді.',
  'msg.explain.notNumber':
    'Жарияланған «{label}» мәнін сан ретінде оқу мүмкін болмады.',
  'msg.explain.noApplicantValue':
    'Бағдарлама ең төменгі шекті {published} деп жариялайды, бірақ профильде «{label}» мәні әлі жоқ. Бұл тексеруді аяқтау үшін оны қосыңыз.',
  'msg.explain.minimumNotMet':
    'Жарияланған ең төменгі шек {published}; сізде {applicant}. Жарияланған ең төменгі шекке жетпейді.',
  'msg.explain.minimumMet':
    'Жарияланған ең төменгі шек {published}; сізде {applicant}.',
  'msg.explain.intakeClosed':
    'Бағдарлама бұл қабылдауға өтініштер қабылданбайтынын ресми түрде хабарлайды.',
  'msg.explain.deadlineUnparsed':
    'Мерзім жарияланған, бірақ оны күн ретінде оқу мүмкін болмады.',
  'msg.explain.deadlinePassed':
    'Жарияланған мерзім {date} өтіп кетті.',
  'msg.explain.deadlineByPopulation':
    'Ең ерте өтініш беру мерзімі — {date}; мерзім осы университеттегі сіздің ақы төлеу санатыңызға байланысты ({deadlines}).',
  'msg.explain.deadlineOpen':
    'Өтініштер {date} дейін қабылданады.',
  'msg.explain.allDeadlinesPassed':
    'Жарияланған барлық мерзім өтіп кетті ({deadlines}).',
  'msg.explain.deadlineByPopulationPassed':
    'Мерзім осы университеттегі сіздің ақы төлеу санатыңызға байланысты ({deadlines}). «{populations}» үшін мерзім өтіп кетті; сізге қайсысы қатысты екенін нақтылаңыз.',
  'msg.explain.gpaScale':
    'Сіздің GPA {scale} шкаласы бойынша көрсетілген, ал бағдарлама басқа шкаланы жариялайды. Құжатталған әдіссіз қайта есептеу қолданылмайды, сондықтан мұны мұнда шешу мүмкін емес.',
  'msg.explain.testOptional':
    'Бағдарлама тестті міндетті етпейді, сондықтан SAT балының болмауы кедергі емес.',
  'msg.explain.satPolicyNoMinimum':
    'SAT бойынша талап жарияланған, бірақ ең төменгі балл табылмады.',
  'msg.explain.actionRequired':
    'Талап етіледі: «{label}». Бұл орындалатын қадам, бас тарту себебі емес.',
  'msg.explain.subjectsPresent':
    'Жарияланған барлық міндетті пәндер профильде бар.',
  'msg.explain.subjectsMissing':
    'Профильде жоқ: {subjects}. Егер оларды оқысаңыз, қосыңыз; әйтпесе бұл нақты олқылық.',
  'msg.explain.noAssessable':
    'Бағалауға болатын академиялық талаптар табылмады. Алдағы мерзім немесе міндетті емес тест сіздің талаптарға сай екеніңізді білдірмейді.',
  'msg.explain.ieltsTypes':
    'Бағдарлама {accepted} қабылдайды; сізде {held}.',
  'msg.explain.englishWaiver':
    'Бағдарлама ағылшын тілі тестін тапсыру қажет емес жағдайларды жариялайды. Тестке жазылмас бұрын оларды өз оқуыңызбен салыстырыңыз — олар сізге қатысты ма, оны бұл бет шешпейді.',
  'msg.explain.citizenshipUnreadable':
    'Стипендия азаматтыққа қатысты талапты жариялайды, бірақ оны елдер тізімі ретінде оқу мүмкін болмады. Ресми нақтылау қажет.',
  'msg.explain.citizenshipNamed':
    'Жарияланған шектеу {phrase} деп атайды, бұл профильдегі {country} азаматтығына сәйкес келеді.',
  'msg.explain.citizenshipMember':
    '{country} {group} құрамына кіреді, оны стипендия өз шектеуі ретінде атайды.',
  'msg.explain.citizenshipGroup':
    'Стипендия құрамы елдер тізімі ретінде жарияланбаған топпен («{restrictions}») шектелген. {held} оған кіре ме, оны беттен шешу мүмкін емес, сондықтан мұны қабылдау комиссиясы растауы керек.',
  'msg.explain.citizenshipExcluded':
    'Стипендия шектелген: {restrictions}. {held} азаматтығы бар үміткер сай келмейді.',
  'msg.explain.internationalClosed':
    'Стипендия шетелдік студенттер үшін ресми түрде жабық.',
  'msg.explain.internationalOpen':
    'Стипендия кез келген азаматтығы бар шетелдік студенттер үшін ресми түрде ашық.',
  'msg.explain.restriction':
    'Бет бұл стипендияны шектейді: {restriction}. Сіздің бағдарламаңыз оған жата ма, оны бет шешпейді — стипендияға сенбес бұрын қабылдау комиссиясынан сұраңыз.',
  'msg.explain.scholarshipTestMissing':
    'Стипендия үшін {test} {minimum} қажет; профильде балл жоқ.',
  'msg.explain.scholarshipDeadlinePassed':
    'Стипендияға өтініш берудің жарияланған мерзімі {date} өтіп кетті.',
  'msg.degree.noText':
    'тексеретін мәтін немесе білім деңгейі жоқ',
  'msg.degree.excludes':
    'бет {degree} деңгейіндегі үміткерлерді тікелей шығарып тастайды',
  'msg.degree.forOther':
    'бет стипендия {degree} емес, {level} деңгейіне арналғанын көрсетеді',
  'msg.degree.statesFor':
    'бет стипендия {degree} деңгейіндегі үміткерлерге арналғанын көрсетеді',
  'msg.degree.onlyOthers':
    'бет стипендияны тек {levels} үшін сипаттайды және {degree} туралы ешқайда айтпайды',
  'msg.degree.unstated':
    'бет стипендия қай білім деңгейлеріне қатысты екенін көрсетпейді',
  'msg.degree.excludesLevel':
    'бет бұл деңгейді шығарып тастайды.',
  'msg.missing.notCovered':
    '{category} өтелмейді',
  'msg.missing.unknown':
    '{category} — белгісіз',
  'msg.missing.partial':
    '{category} — ішінара',
  'msg.class.excluded':
    'Жарияланған шарттар бұл үміткерді шығарып тастайды.',
  'msg.class.degreeLevel':
    'Бұл үміткердің білім деңгейіне қатысты емес: {degreeReason}',
  'msg.class.citizenship':
    'Стипендия шектелген: {restrictions}, — бұл үміткер оған кірмейді.',
  'msg.class.notInternational':
    'Ресми дереккөз стипендия шетелдік студенттерге ашық емес екенін хабарлайды.',
  'msg.class.noCoverage':
    'Шығын баптары бойынша өтеу туралы ресми деректер табылмады.',
  'msg.class.promotionalNoBreakdown':
    'Бетте жарнамалық тұжырымдар бар ({words}), бірақ бөлінісі жоқ.',
  'msg.class.needBased':
    'Стипендия мөлшері қаржылық мұқтаждықты тексеруге байланысты, оның құжаттары әлі тапсырылмаған.',
  'msg.class.fullRide':
    'Ресми дереккөздер оқу ақысын, міндетті алымдарды, тұрғын үйді және тамақты немесе оған тең тұру стипендиясын өтеуді растайды.',
  'msg.class.fullTuition':
    'Оқу ақысының өтелуі расталған, бірақ {missing} — бұл оқу ақысын толық өтеу, толық қамту емес.',
  'msg.class.shareUnknown':
    'Өтеу ішінара, бірақ стипендия сомасы немесе оқу құны ресми жарияланбаған, сондықтан үлесін есептеу мүмкін емес.',
  'msg.class.largeGrant':
    'Жарияланған оқу құнының шамамен {share} бөлігін өтейді; шығынның едәуір бөлігі қалады.',
  'msg.class.partial':
    'Жарияланған оқу құнының шамамен {share} бөлігін өтейді.',
  'msg.class.promotional':
    'Бетте «full ride» сияқты жарнамалық тұжырымдар бар; мұндағы жіктеу жарияланған өтеу кестесіне сүйенеді.',
  'msg.class.onlyFullRide':
    'Профильде мұны тек толық қамту ғана қолжетімді ететіні көрсетілген; бұл стипендия «{classification}» деп жіктелген.',
  'msg.class.noTuitionOnly':
    'Профильде тек оқу ақысын өтейтін стипендияны қабылдамайтыныңыз көрсетілген.',
  'msg.class.noPartial':
    'Профильде ішінара стипендияны қабылдамайтыныңыз көрсетілген.',
  'msg.class.needDocuments':
    'Бұл стипендия мұқтаждыққа қарай беріледі, ал профильде қаржылық құжаттар тапсырылмайтыны көрсетілген — ал мұндай өтінішке дәл солар қажет.',
  'msg.class.mustCover':
    'Профиль мыналарды өтеуді талап етеді: {categories}; бұл стипендия оларды өтемейтінін хабарлайды.',
  'msg.rank.academicNoMargin':
    'Жарияланған барлық талаптар орындалған; қорды өлшейтін сандық ең төменгі шектер жоқ.',
  'msg.rank.academicMargin':
    'Жарияланған барлық талаптар орындалған, орта есеппен ең төменгі шектерден {margin} жоғары.',
  'msg.rank.academicPending':
    'Әлі шешімін күтіп тұрған тармақтардан басқа талаптар орындалған.',
  'msg.rank.academicGap':
    'Кемінде бір жарияланған талап орындалмаған.',
  'msg.rank.academicUnknown':
    'Жарияланған талаптарды тексеру мүмкін болмады.',
  'msg.rank.fundingUnknown':
    'Қаржыландыру туралы ресми ақпарат расталмады.',
  'msg.rank.fundingConfirmed':
    'Қаржыландыру: расталған мүмкіндік.',
  'msg.rank.fundingCompetitive':
    'Қаржыландыру: конкурстық мүмкіндік.',
  'msg.rank.fundingLimited':
    'Қаржыландыру: шектеулі мүмкіндік.',
  'msg.rank.fundingNotEligible':
    'Қаржыландыру: сіз сай емессіз.',
  'msg.rank.gapUnknown':
    'Жылдық төленетін қалдықты есептеу мүмкін болмады.',
  'msg.rank.noCeiling':
    'Салыстыру үшін отбасы бюджетінің шегі көрсетілмеген.',
  'msg.rank.nothingRemains':
    'Төлейтін ештеңе қалмайды.',
  'msg.rank.zeroContribution':
    'Отбасы ештеңе төлей алмайтынын көрсеткен, ал жылына {gap} қалады.',
  'msg.rank.withinCeiling':
    'Жылына {gap} қалдық көрсетілген {ceiling} шегіне сыяды.',
  'msg.rank.timesCeiling':
    'Жылына {gap} қалдық көрсетілген {ceiling} шегінен {ratio} есе көп.',
  'msg.rank.aboveCeiling':
    'Жылына {gap} қалдық көрсетілген {ceiling} шегінен {over} жоғары.',
  'msg.rank.preferredCountry':
    '{country} — қалаулы ел.',
  'msg.rank.unpreferredCountry':
    '{country} қалаулы елдер тізімінде жоқ.',
  'msg.rank.noRank':
    'Рейтингтегі орны табылмады.',
  'msg.rank.insideBand':
    'Рейтингтегі орны {rank}, сұралған «{band}» ауқымының ішінде.',
  'msg.rank.outsideTop':
    'Рейтингтегі орны {rank}, үздік {top} қатарынан тыс.',
  'msg.rank.consensus':
    'Рейтингтегі жиынтық орны: {rank}.',
  'msg.rank.ranked':
    'Рейтингтегі орны: {rank}.',
  'msg.rank.noPreference':
    '«{axis}» бойынша қалау көрсетілмеген.',
  'msg.rank.attributeUnknown':
    'Бұл университеттің «{axis}» көрсеткіші белгісіз.',
  'msg.rank.attributeMatches':
    '{actual} көрсетілген қалауға сәйкес келеді.',
  'msg.rank.ladderStep':
    '{actual}, ал қалау {preferred}: айырмашылық {steps} қадам.',
  'msg.rank.ladderSteps':
    '{actual}, ал қалау {preferred}: айырмашылық {steps} қадам.',
  'msg.rank.ladderDiffers':
    '{actual} қалаған {preferred} нұсқасынан өзгеше.',
  'msg.rank.careersNotPriority':
    'Мансап басымдық ретінде көрсетілмеген.',
  'msg.rank.coop':
    'Co-op немесе тәжірибе жылы ресми түрде ұсынылады.',
  'msg.rank.internships':
    'Тағылымдама бағдарламасы ресми түрде сипатталған.',
  'msg.rank.careersPage':
    'Мансап туралы бет бар, бірақ онда тексеруге жететіндей нақты ештеңе жоқ.',
  'msg.rank.noCareers':
    'Мансап туралы ресми ақпарат табылмады.',
  'msg.rank.pswNotPriority':
    'Оқудан кейінгі жұмыс басымдық ретінде көрсетілмеген.',
  'msg.rank.pswUnknown':
    'Оқудан кейінгі жұмыс ережелері айлармен расталмаған.',
  'msg.rank.psw':
    'Оқудан кейін {months} ай жұмыс істеу құқығы жарияланған.',
  'msg.rank.excludedCountry':
    '{country} — сіз алып тастаған елдер тізімінде.',
  'msg.rank.knockoutUnmet':
    '{requirement}: жарияланған талап орындалмаған',
  'msg.rank.knockout':
    '{requirement} — {explanation}',
  'msg.rank.bucketInsufficient':
    'Бұл нұсқаның орнын анықтау үшін жарияланған талаптардың тым аз бөлігі тексерілді.',
  'msg.rank.bucketOutOfBudget':
    'Төленетін қалдық көрсетілген шектен {ratio} есе көп — үміткер шыдай алатынын айтқан {limit} еседен асады.',
  'msg.rank.bucketWellPlaced':
    'Талаптар қормен орындалған, қаржыландыру расталған, төленетін қалдық көрсетілген шектің ішінде.',
  'msg.rank.bucketPlausible':
    'Жарияланған деректер бойынша талаптар да, қаржыландыру да қолжетімді көрінеді.',
  'msg.rank.bucketAmbitious':
    'Талаптар, қаржыландыру немесе төленетін қалдық бұл нұсқаны батыл таңдау етеді.',
  'msg.rank.disclaimer':
    'Расталған деректер бойынша сіз көрсеткен басымдықтарға қаншалықты сай келетіні. Түсу ықтималдығы емес.',
  'msg.conflict.label.ieltsOverall':
    'IELTS ең төменгі жалпы балы',
  'msg.conflict.label.ieltsSubscore':
    'IELTS әр бөлімі бойынша ең төменгі балл',
  'msg.conflict.label.minGpa':
    'ең төменгі GPA',
  'msg.conflict.label.satTotal':
    'SAT ең төменгі жалпы балы',
  'msg.conflict.label.toeflTotal':
    'TOEFL ең төменгі жалпы балы',
  'msg.conflict.label.admissionDeadline':
    'өтініш беру мерзімі',
  'msg.conflict.label.scholarshipDeadline':
    'стипендияға өтініш беру мерзімі',
  'msg.conflict.label.tuition':
    'оқу ақысы',
  'msg.conflict.label.totalCost':
    'оқудың толық құны',
  'msg.conflict.label.awardAmount':
    'стипендия сомасы',
  'msg.conflict.label.internationalEligible':
    'шетелдік студенттерге қолжетімділік',
  'msg.conflict.subjectFull':
    '{what}, {subjectKey} — {programme} бағдарламасы',
  'msg.conflict.subjectKeyed':
    '{what}, {subjectKey}',
  'msg.conflict.subjectProgramme':
    '{what} — {programme} бағдарламасы',
  'msg.conflict.subject':
    '{what}',
  'msg.conflict.preferSpecific':
    'Нақтырақ дереккөзге басымдық беріледі ({specificity}); сәйкессіздік шешілмей, көрсетіледі.',
  'msg.conflict.moreSpecific':
    'Бұл қайшылық емес: бағдарлама ережесі мен университеттің жалпы ережесі қатар дұрыс болуы мүмкін. Бұл өтінішке нақтырақ дереккөз ({specificity}) қатысты; жалпы ереже алынып тасталмай, сақталады.',
  'msg.conflict.differentPopulation':
    'Бұл қайшылық емес: беттер үміткерлердің әртүрлі санаттары туралы айтады, сондықтан екі мән де дұрыс болуы мүмкін. Ешқайсысы алынып тасталмайды.',
  'msg.conflict.differentResidency':
    'Бұл қайшылық емес: беттер әртүрлі резиденттік мәртебе туралы айтады, сондықтан екі мән де дұрыс болуы мүмкін. Ешқайсысы алынып тасталмайды.',
  'msg.conflict.differentIntake':
    'Бұл қайшылық емес: беттер әртүрлі қабылдаулар туралы айтады, сондықтан екі мән де дұрыс болуы мүмкін. Ешқайсысы алынып тасталмайды.',
  'msg.conflict.differentAcademicYear':
    'Бұл қайшылық емес: беттер әртүрлі оқу жылдары туралы айтады, сондықтан екі мән де дұрыс болуы мүмкін. Ешқайсысы алынып тасталмайды.',
  'msg.conflict.differentDegree':
    'Бұл қайшылық емес: беттер әртүрлі білім деңгейлері туралы айтады, сондықтан екі мән де дұрыс болуы мүмкін. Ешқайсысы алынып тасталмайды.',
  'msg.conflict.differentQualification':
    'Бұл қайшылық емес: беттер білім туралы әртүрлі құжаттар туралы айтады, сондықтан екі мән де дұрыс болуы мүмкін. Ешқайсысы алынып тасталмайды.',
  'msg.conflict.why':
    'Ресми дереккөздер «{subject}» бойынша сәйкес келмейді: {values}',
  'msg.currency.staleRates':
    'Айырбастау {date} күнгі валюта бағамдарын пайдаланады, олардың жасы {days} күн. Айырбасталған сомаларды шамамен деп санаңыз және оларға сүйенбес бұрын ағымдағы бағамды тексеріңіз.',

  // --- I18N-3: document names and notes (provisional terms: docs/i18n/GLOSSARY.md)
  'msg.document.transcript':
    'Бағалардың толық транскрипті',
  'msg.document.secondary_diploma':
    'Орта білім туралы аттестат (куәландырылған көшірме)',
  'msg.document.translation':
    'Ағылшын тілінде емес құжаттардың ағылшын тіліне куәландырылған аудармасы',
  'msg.document.apostille':
    'Апостильмен куәландыру',
  'msg.document.credential_evaluation':
    'Білім туралы құжаттарды пән бойынша бағалау (WES/ECE)',
  'msg.document.passport':
    'Төлқұжаттың жеке деректер беті (көшірме)',
  'msg.document.photo':
    'Төлқұжат өлшеміндегі фотосурет (электрондық түрде)',
  'msg.document.personal_statement':
    'Жеке мәлімдеме',
  'msg.document.motivation_letter':
    'Мотивациялық хат',
  'msg.document.essay':
    'Жеке эссе',
  'msg.document.recommendation_letter':
    'Ұсыным хат',
  'msg.document.academic_reference':
    'Оқытушының ұсынымы',
  'msg.document.cv':
    'Түйіндеме (CV)',
  'msg.document.portfolio':
    'Портфолио',
  'msg.document.financial_proof':
    'Қаржы қаражатының бар екенін растау',
  'msg.document.english_test_report':
    'Ағылшын тілі тестінің нәтижелері',
  'msg.document.entrance_test':
    'Түсу тестінің нәтижесі',
  'msg.document.application_form':
    'Өтініш нысаны',
  'msg.document.note.optional':
    'Қалауыңыз бойынша, жарияланғандай.',
  'msg.document.note.conditional':
    'Белгілі бір шартпен талап етіледі, жарияланғандай.',
  'msg.document.note.conditionWhen':
    'Тек мына жағдайда талап етіледі: {condition}.',
  'msg.document.note.possiblyOutdated':
    'Ескірген болуы мүмкін: {reasons}.',

  'catalogue.kb.coverage': '{total} университеттің {n}-інде тексерілген деректер бар',
  'catalogue.kb.filter': 'Тек тексерілген деректері барлар',
  'catalogue.kb.chip': 'Тексерілген білім базасы',
  'catalogue.kb.none': 'Тексерілген деректер әзірге жоқ',
  'catalogue.kb.answers': 'жауаптар: {n}/6',
  'catalogue.kb.documents.one': '{n} құжат',
  'catalogue.kb.documents.few': '{n} құжат',
  'catalogue.kb.documents.many': '{n} құжат',
  'catalogue.kb.documents.other': '{n} құжат',
  'catalogue.kb.programme.known': 'Бағдарлама беті',
  'catalogue.kb.programme.related_only': 'Тек сабақтас бағдарлама',
  'catalogue.kb.programme.not_offered': 'Computer Science бакалавриаты жарияланбаған',
  'catalogue.kb.programme.unknown': 'Бағдарлама беті тексерілмеген',
  'catalogue.kb.staleCount.one': '{n} дерек өзекті емес',
  'catalogue.kb.staleCount.few': '{n} дерек өзекті емес',
  'catalogue.kb.staleCount.many': '{n} дерек өзекті емес',
  'catalogue.kb.staleCount.other': '{n} дерек өзекті емес',
  'catalogue.kb.tuition': 'Тексерілген оқу ақысы',
  'catalogue.kb.noFee': 'Тексерілген оқу ақысы әзірге жоқ',
  'catalogue.kb.historical': 'Тарихи бағалау',
  'catalogue.kb.historicalValue': 'USD {min}–{max}; кезеңі мен қамтуы тексерілмеген',
  'catalogue.kb.verifiedOn': '{date} тексерілген ({label})',
  'catalogue.kb.review.human': 'адам тексерген',
  'catalogue.kb.review.expert': 'сарапшы тексерген, дәйексөз расталған',
};
