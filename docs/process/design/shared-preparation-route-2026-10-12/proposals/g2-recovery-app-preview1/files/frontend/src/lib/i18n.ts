import { G1_EN, G1_RU, G1_KK } from './preparationGraphMessages';
/**
 * The groundwork for Russian and Kazakh, and an honest gap where the words are
 * not settled yet.
 *
 * Two decisions shape this file.
 *
 * **A missing translation falls back to English, visibly and by design.** The
 * alternative — machine-translating everything so no string looks untranslated
 * — is the same mistake the rest of the product refuses to make: it turns "we
 * do not know" into a confident answer. A Kazakh applicant reading an invented
 * term for "funding gap" cannot tell it apart from a reviewed one.
 *
 * **The product's own vocabulary is not translated here at all.** Words like
 * claim, shortlist, funding gap and conditional offer carry exact meanings the
 * whole product rests on, and choosing their Russian and Kazakh equivalents is
 * a decision for a person who knows the admissions vocabulary in those
 * languages. Every one of them is listed in `docs/i18n/GLOSSARY.md` with the
 * question that has to be answered before it can be translated. Until then the
 * strings containing them stay in English, and that is the correct behaviour,
 * not a gap to be quietly filled.
 *
 * No i18n library: this is a lookup with a fallback. A framework would bring
 * plural rules and interpolation for a dictionary of forty strings.
 */

export type Locale = 'en' | 'ru' | 'kk';

export const LOCALES: { id: Locale; label: string }[] = [
  { id: 'en', label: 'English' },
  { id: 'ru', label: 'Русский' },
  { id: 'kk', label: 'Қазақша' },
];

const STORAGE_KEY = 'ashyq.locale';

/**
 * English is the source of truth: every key exists here, and a key missing
 * from `ru` or `kk` renders this text rather than the raw key.
 */
const EN = {
  ...G1_EN,
  'shared.title': 'Shared preparation route',
  'shared.recoveryDraft': 'Browser draft restored or changed — it is not a server save. This tab keeps your personal inputs.',
  'shared.recoveryUnavailable': 'Browser recovery is unavailable. Your input remains here; a new request cannot be sent until its original command is recorded.',
  'shared.recoveryInvalid': 'This case has an unsupported or changed browser journal. It was not adopted or overwritten. Reset this local case draft explicitly to continue.',
  'shared.recoveryCleanup': 'A matching server receipt was observed, but its browser journal could not be safely retired. Keep the original command and refresh the saved route.',
  'shared.recoveryNewer': 'The exact request was saved. Your newer edits remain an unsaved browser draft.',
  'shared.recoveryNotSent': 'This new command was not sent: its browser journal could not be recorded. Retry the same original command explicitly.',
  'shared.recoveryReset': 'Reset this local route draft',
  'shared.recoveryResetConfirm': 'Discard this tab’s route draft and unresolved command for this case? Server plans and history will stay unchanged.',
  'shared.recoveryLeave': 'You have unsaved route inputs or an unresolved save. Leave this screen? This tab keeps its recovery journal when browser storage is available; leaving does not save to the server.',
  'shared.nav': 'Shared route',
  'shared.goalsNav': 'Goals & evidence',
  'shared.legacyHistory': 'Earlier personal study plan',
  'shared.legacyInactive': 'The shared route is the active weekly budget. This earlier plan remains in history and cannot create a second active budget.',
  'shared.legacyUnknown': 'The active shared route could not be confirmed. Earlier study history is available read-only until this check succeeds.',
  'shared.intro': 'Choose your own programmes and exam dates. This route uses one weekly study budget for your selected exams.',
  'shared.oneBudget': 'One shared weekly budget',
  'shared.readonly': 'Your saved route and history remain readable. A current preparation term is required to preview, save or open lessons.',
  'shared.loading': 'Loading your saved route…',
  'shared.error': 'The shared route could not be loaded.',
  'shared.mismatch': 'The response did not match this case and exact request. Reload before continuing.',
  'shared.refresh': 'Refresh saved route',
  'shared.acceptedRevision': 'Accepted revision',
  'shared.current': 'Current saved route',
  'shared.history': 'Earlier saved revisions',
  'shared.historyHint': 'Open an exact revision of your own saved route.',
  'shared.revision': 'Revision',
  'shared.openHistory': 'Open revision',
  'shared.historical': 'Earlier saved route',
  'shared.historyInvalid': 'Enter a saved revision number.',
  'shared.newPlan': 'Plan a shared route',
  'shared.selectionHint': 'Select 2–20 of your own approved or maybe results in your preferred order. Suggestions below come only from the latest loaded run; an older saved result can be entered by ID. The server verifies every selection.',
  'shared.goalReference': 'Result reference',
  'shared.programmeNumber': 'Saved programme',
  'shared.reference': 'Show exact ID',
  'shared.remove': 'Remove',
  'shared.up': 'Move earlier',
  'shared.add': 'Add',
  'shared.savedId': 'Older saved result ID',
  'shared.savedIdHint': 'Enter the exact ID from your own saved result. It is not assumed eligible until the server checks it.',
  'shared.invalidId': 'Enter an exact saved result ID without extra spaces.',
  'shared.addId': 'Add saved ID',
  'shared.startsOn': 'Planning starts on',
  'shared.timezone': 'Your time zone',
  'shared.weeklyMinutes': 'Minutes available each week across all exams',
  'shared.days': 'Study days',
  'shared.day0': 'Mon', 'shared.day1': 'Tue', 'shared.day2': 'Wed', 'shared.day3': 'Thu',
  'shared.day4': 'Fri', 'shared.day5': 'Sat', 'shared.day6': 'Sun',
  'shared.ielts': 'IELTS Academic', 'shared.sat': 'Digital SAT',
  'shared.includeExam': 'Include this personal exam',
  'shared.priorityFirst': 'Make this exam first in the allocation order',
  'shared.firstExam': 'First exam date',
  'shared.retake': 'Retake date, if planned',
  'shared.certificateDeadline': 'Date by which you want the certificate',
  'shared.latestSafe': 'Calculated latest exam date under your entered buffers',
  'shared.personalTargetHint': 'Your optional personal targets, not university minima',
  'shared.wait': 'Days for results',
  'shared.delivery': 'Delivery days',
  'shared.safety': 'Safety buffer days',
  'shared.optionalTargets': 'Optional personal targets',
  'shared.confirmExam': 'I entered these personal dates and buffers myself',
  'shared.ownReviews': 'My saved attempt reviews',
  'shared.reviewHint': 'A review uses your exact saved attempt and the minutes you enter. It does not repeat or replace a lesson.',
  'shared.addReview': 'Add own review',
  'shared.olderReview': 'Older own attempt by exact reference',
  'shared.attemptId': 'Own attempt UUID', 'shared.lessonId': 'Exact lesson ID',
  'shared.contentVersion': 'Exact content version', 'shared.chooseExam': 'Choose exam explicitly',
  'shared.invalidReview': 'Enter an exact own attempt UUID, lesson ID and content version without extra spaces.',
  'shared.exam': 'Exam stream',
  'shared.reviewMinutes': 'Minutes for this review',
  'shared.confirmInputs': 'I chose these programmes, study capacity and personal exam plans explicitly',
  'shared.previewOnly': 'Preview is unsaved. The lesson allocation is planning time, not a course completion or admission verdict.',
  'shared.preview': 'Preview route',
  'shared.invalid': 'Check programme count, dates, exam confirmations, review minutes and the shared weekly budget.',
  'shared.previewResult': 'Route preview',
  'shared.unsaved': 'Preview only — nothing has been saved.',
  'shared.save': 'Save this exact preview',
  'shared.saving': 'Saving this exact request…',
  'shared.saved': 'The server accepted this route. The saved revision is being refreshed.',
  'shared.conflict': 'The planning inputs changed elsewhere. Keep your draft, refresh and review a new preview before a new save.',
  'shared.uncertain': 'The outcome is uncertain. Retry only the original request ID and inputs; a new intent is not automatic.',
  'shared.originalIntent': 'Original request ID',
  'shared.retryOriginal': 'Retry original request',
  'shared.newIntent': 'Start a new save intent from this fresh preview',
  'shared.acceptedOn': 'Accepted at',
  'shared.status': 'Current status:',
  'shared.evidenceHint': 'Open Goals & evidence for current programme sources, scope and unresolved policies. Saved route references do not freeze premium evidence.',
  'shared.needsReview': 'Needs review against current evidence or content',
  'shared.reviewReasons': 'Reasons to review current route',
  'shared.noCurrentChange': 'No current change reported',
  'shared.legacyStatus': 'Earlier plan structure:',
  'shared.contentStatus': 'Imported references:',
  'shared.savedTruth': 'Saved allocation records the exact references and planned minutes. It does not claim mastery, an official score or admission eligibility.',
  'shared.minutesWeek': 'minutes per week',
  'shared.minutes': 'minutes',
  'shared.notReadiness': 'Personal practice only; readiness has not been assessed.',
  'shared.lesson': 'Lesson', 'shared.review': 'Own attempt review',
  'shared.openLesson': 'Open exact lesson', 'shared.openReview': 'Open my exact review',
  'shared.exactUnavailable': 'Exact content currently unavailable',
  'shared.noSlots': 'No dated actions fit the entered windows and capacity.',
  'shared.unallocated': 'Actions not allocated',
  'shared.targetOverall': 'Overall target', 'shared.targetListening': 'Listening target',
  'shared.targetReading': 'Reading target', 'shared.targetWriting': 'Writing target',
  'shared.targetSpeaking': 'Speaking target', 'shared.targetTotal': 'Total target',
  'shared.targetMath': 'Math target', 'shared.targetReadingWriting': 'Reading and Writing target',
  'shared.stateEligible': 'Your saved programme is still selected', 'shared.stateDecision': 'Your saved decision changed',
  'shared.stateMissing': 'Result unavailable', 'shared.stateLocked': 'Research locked',
  'shared.stateSource': 'Source changed', 'shared.stateUnknown': 'Unknown; review needed',
  'shared.stateUnchanged': 'Unchanged', 'shared.stateChanged': 'Changed',
  'shared.stateNotUsed': 'Not used', 'shared.stateAvailable': 'Available',
  'shared.stateVersion': 'Exact version unavailable', 'shared.stateReview': 'Own review unavailable',
  'shared.timingWithin': 'Within entered buffers', 'shared.timingRisk': 'At risk under entered buffers',
  'shared.timingPassed': 'Entered deadline passed',
  'shared.reasonCapacity': 'Insufficient shared capacity', 'shared.reasonWindow': 'Practice window elapsed',
  'shared.reasonDay': 'Longer than a study day', 'shared.reasonWeek': 'Longer than the weekly budget',
  'shared.reasonLimit': 'Route slot limit reached',
  'learning.title': 'Learning calendar',
  'learning.open': 'View learning calendar',
  'learning.preview': 'Preview updated learning path',
  'learning.save': 'Use this updated path',
  'learning.cancel': 'Close preview',
  'learning.loading': 'Loading learning calendar…',
  'learning.loaded': 'Learning calendar saved. Original task checkmarks remain in their history.',
  'learning.previewNotice': 'Preview only. Review these exact materials and dates before saving. The original calendar and its reported checkmarks are preserved.',
  'learning.dirty': 'Save or discard the original form changes before previewing this path.',
  'learning.conflict': 'The calendar changed elsewhere. Reload and preview the latest version before saving again. Your original form inputs remain unchanged.',
  'learning.stale': 'Original planning settings changed. Review a fresh preview before using this path.',
  'learning.history': 'Original reported checkmarks',
  'learning.lesson': 'Open lesson',
  'learning.review': 'Review my saved attempt',
  'learning.submitted': 'Saved submission — not mastery',
  'learning.no_local_content': 'Local material is not available for this skill.',
  'learning.attempt_required': 'No saved attempt was selected. Preview again after submitting your own practice.',
  'learning.not_implemented': 'This assessment is not available here.',
  'learning.version_unavailable': 'The exact saved material version is unavailable.',
  'learning.unallocated': 'Units without enough allocated time',
  'learning.details': 'Material details',
  'learning.other': 'Other dated tasks, including past dates',
  'learning.empty': 'Save the original study plan first.',
  'learning.error': 'Learning calendar could not load or save. Nothing was saved.',
  'learning.readonly': 'Own history remains readable. New lessons and plan changes require preparation access.',
  'learning.note': 'At least twenty minutes per unit is a planning allocation. Tasks and saved submissions do not establish mastery, official scores or exam readiness.',

  'nav.group.prepare': 'Prepare',
  'nav.group.research': 'Research',
  'nav.group.decide': 'Decide',
  'nav.group.community': 'Community',
  'nav.group.about': 'About',

  'nav.profile': 'Applicant profile',
  'nav.preparation': 'Exam preparation',
  'nav.preferences': 'Preferences & budget',
  'nav.progress': 'Research progress',
  'nav.shortlist': 'University shortlist',
  'nav.funding': 'Funding comparison',
  'nav.sources': 'Sources & conflicts',
  'nav.approved': 'Approved universities',
  'nav.documents': 'Documents & deadlines',
  'nav.export': 'Export & data deletion',
  'nav.feed': 'Feed',
  'nav.discover': 'Find applicants',
  'nav.me': 'My community profile',
  'nav.legal': 'Privacy & terms',

  'topbar.applicant': 'Applicant',
  'topbar.newApplicant': 'New applicant',
  'topbar.newCase': 'New case',
  'topbar.signOut': 'Sign out',
  'topbar.demoData': 'Demo data',
  'topbar.liveSources': 'Live sources',
  'topbar.connecting': 'connecting…',

  'appearance.label': 'Appearance',
  'appearance.system': 'Match system',
  'appearance.light': 'Light',
  'appearance.dark': 'Dark',

  'language.label': 'Language',

  'brand.tagline': 'Evidence-backed university & scholarship shortlisting',
  'brand.disclaimer':
    'Published criteria only. Unimatch never predicts admission or funding outcomes.',

  // --- Community -------------------------------------------------------
  // These are ordinary words - post, answer, city, major - not the admissions
  // vocabulary the glossary holds back. Nothing here needs a specialist to
  // choose it, so all three languages are filled in.
  'community.title': 'Community',
  'community.lede':
    'Applicants aiming at the same cities and universities. What people write here is their '
    + 'own experience — it is not verified against a university page.',
  'community.joinPrompt':
    'You can read the feed now. Create a community profile to post, reply and be findable by '
    + 'people applying where you are.',
  'community.createProfile': 'Create profile',
  'community.write': 'Write a post',
  'community.writeHint': 'Tag a university or a city with # so the right people find it.',
  'community.placeholder': 'Ask something, or say where you are applying',
  'community.post': 'Post',
  'community.posting': 'Posting…',
  'community.willBeTagged': 'Will be tagged',
  'community.charsLeft': 'left',
  'community.charsOver': 'over',
  'community.answerPlaceholder': 'Answer this',
  'community.reply': 'Reply',
  'community.answer': 'Answer',
  'community.hideAnswers': 'Hide answers',
  'community.noAnswers': 'No answers yet. Be the first.',
  'community.earlierAnswers': 'Show earlier answers',
  'community.openingThread': 'Opening the thread',
  'community.loadingPosts': 'Loading posts',
  'community.olderPosts': 'Load older posts',
  'community.noPosts': 'No posts yet',
  'community.noPostsHint':
    'The first post here sets the tone. Ask the question you could not find an answer to.',
  'community.noMatch': 'Nothing matches those filters',
  'community.noMatchHint': 'Widen the filters, or clear them to see everything.',
  'community.clearFilters': 'Clear filters',
  'community.filterTag': 'Tag',
  'community.filterCity': 'Applying to city',
  'community.filterAuthorStatus': 'Author status',
  'community.anyone': 'Anyone',

  'community.delete': 'Delete',
  'community.deleteConfirm': 'Yes, delete',
  'community.keepIt': 'Keep it',
  'community.deleting': 'Deleting…',
  // Whole questions rather than a noun slotted into a sentence: Russian and
  // Kazakh decline the noun, and this dictionary has no interpolation.
  'community.deletePostQ': 'Delete this post?',
  'community.deletePostThreadQ': 'Delete this post and its answers?',
  'community.deleteAnswerQ': 'Delete this answer?',

  'discover.title': 'Find applicants like you',
  'discover.lede':
    'Everyone listed here chose to be listed. Spelling does not matter — KBTU, kbtu and '
    + 'K.B.T.U. are one university to the filter.',
  'discover.city': 'City',
  'discover.university': 'University',
  'discover.major': 'Major',
  'discover.status': 'Status',
  'discover.anyStatus': 'Any status',
  'discover.looking': 'Looking',
  'discover.more': 'Show more people',
  'discover.noMatch': 'Nobody matches yet',
  'discover.noMatchHint': 'Try one filter at a time — city alone usually finds the most people.',
  'discover.empty': 'Nobody has joined yet',
  'discover.emptyHint': 'Create your own profile and you will be the first person here.',
  'discover.noAim': 'Has not said where they are aiming',

  'person.statusAccepted': 'Accepted',
  'person.statusWaitlist': 'On a waitlist',
  'person.statusUnstated': 'Status not stated',
  'person.statusStatedTitle': 'What this applicant says about their own applications.',
  'person.statusUnstatedTitle': 'This applicant has not said where they stand.',
  'person.joinTitle': 'Join the community',
  'person.joinLede':
    'Registering an account did not publish anything about you. This form is what puts you in '
    + 'Discover, and you can edit it or leave again at any time.',
  'person.noProfile': 'No profile here',
  'person.noProfileHint': 'This applicant has not joined the community.',
  'person.loading': 'Loading profile',
  'person.edit': 'Edit profile',
  'person.cancel': 'Cancel',
  'person.yourProfile': 'Your profile',
  'person.aimingAt': 'Aiming at',
  'person.aimingHint': 'Stated by this applicant. Not checked against a university page.',
  'person.city': 'City',
  'person.major': 'Major',
  'person.universities': 'Universities',
  'person.notStated': 'not stated',
  'person.yourPosts': 'Your posts',
  'person.noPostsYou': 'You have not posted yet',
  'person.noPostsYouHint': 'Anything you post in the community shows up here.',
  'person.noPostsThem': 'Nothing posted yet',
  'person.postsBy': 'Posts',

  'person.formStatus': 'Where you stand',
  'person.formStatusNone': 'Prefer not to say',
  'person.formStatusHint':
    'Left unset, your profile says "not stated" rather than guessing.',
  'person.formCity': 'City you are applying to',
  'person.formMajor': 'Major',
  'person.formUniversities': 'Universities you are aiming at',
  'person.formUniversitiesHint': 'Separate with commas.',
  'person.formBio': 'About you',
  'person.formBioPlaceholder':
    'What you are working on, and what you would like to be asked about.',
  'person.save': 'Save profile',
  'person.saving': 'Saving…',
  'person.publicWarning':
    'Everything here is public to other applicants. Your applicant case is not.',

  'nav.messages': 'Messages',
  'nav.moderation': 'Moderation queue',

  'report.action': 'Report',
  'report.title': 'Report this to a moderator',
  'report.reason': 'What is wrong with it',
  'report.harassment': 'Harassment or abuse',
  'report.personal_information': "Someone's private information",
  'report.impersonation': 'Pretending to be someone else',
  'report.spam': 'Spam or advertising',
  'report.misleading_advice': 'A rumour about a university stated as fact',
  'report.other': 'Something else',
  'report.note': 'Anything the moderator should know (optional)',
  'report.send': 'Send report',
  'report.sending': 'Sending…',
  'report.cancel': 'Cancel',
  'report.sent': 'Reported. A moderator will look at it.',
  'report.already': 'You have already reported this.',
  'report.slow':
    'Reports are read by a person, so this is not instant. If someone is reaching you and you '
    + 'want it to stop now, block them — that works immediately.',

  'block.action': 'Block',
  'block.unblock': 'Unblock',
  'block.confirm': 'Block this applicant?',
  'block.explain':
    'They will not be able to write to you or answer your posts, and neither of you will see '
    + 'the other in the feed or in Discover. They are not told.',
  'block.blocked': 'Blocked',
  'block.list': 'People you blocked',
  'block.listEmpty': 'You have not blocked anyone.',

  'moderation.title': 'Moderation queue',
  'moderation.lede':
    'Reports from the community, oldest first. Removing something deletes it for everyone and '
    + 'records who did it.',
  'moderation.open': 'Open',
  'moderation.actioned': 'Acted on',
  'moderation.dismissed': 'Dismissed',
  'moderation.empty': 'Nothing waiting',
  'moderation.emptyHint': 'Reports appear here as the community files them.',
  'moderation.loading': 'Loading the queue',
  'moderation.reportedBy': 'Reported by',
  'moderation.about': 'About',
  'moderation.excerpt': 'What it said when it was reported',
  'moderation.gone': 'This content has since been deleted.',
  'moderation.remove': 'Remove it',
  'moderation.dismiss': 'Leave it',
  'moderation.resolutionNote': 'Why (recorded with your name)',
  'moderation.resolvedBy': 'Resolved by',
  'moderation.subjectPost': 'a post',
  'moderation.subjectReply': 'an answer',
  'moderation.subjectMessage': 'a private message',
  'moderation.subjectProfile': 'a profile',
  'messages.title': 'Messages',
  'messages.lede':
    'Private conversations. Nobody else can read them, and nothing you write here appears in '
    + 'the feed or on your profile.',
  'messages.loading': 'Loading your messages',
  'messages.opening': 'Opening the conversation',
  'messages.empty': 'No conversations yet',
  'messages.emptyHint':
    'Answer someone in the feed, or open a profile and write to them. Who may write to you '
    + 'first is up to you — the setting is on your own profile.',
  'messages.emptyThread': 'Nothing here yet',
  'messages.emptyThreadHint': 'Write the first message.',
  'messages.placeholder': 'Write a message',
  'messages.send': 'Send',
  'messages.back': 'All conversations',
  'messages.write': 'Send a message',
  'messages.closed': 'This applicant does not accept messages.',
  'messages.needsThread':
    'This applicant only accepts messages from people they have answered in public. '
    + 'Answer one of their posts, or ask a question they can answer.',

  'person.avatar': 'Your picture',
  'person.avatarChoose': 'Choose a picture',
  'person.avatarRemove': 'Remove it',
  'person.avatarUploading': 'Uploading…',
  'person.avatarHint':
    'A JPEG or a PNG, up to 512 kB. Where the photo was taken is removed before it is stored, '
    + 'and the picture is shown to every applicant who can see your profile.',

  'person.formDmPolicy': 'Who may write to you first',
  'person.formDmAnyone': 'Anyone in the community',
  'person.formDmThreads': 'Only people I have answered, or who answered me',
  'person.formDmNobody': 'Nobody — keep my inbox closed',
  'person.formDmHint':
    'This guards the first message only. Someone you are already talking to can still reach '
    + 'you, whatever you choose here.',

  'leave.title': 'Leave the community',
  'leave.hint':
    'Your account and your applicant research stay. Your profile, your posts and your replies '
    + 'are deleted, and you disappear from Discover.',
  'leave.confirm': 'Delete your profile and everything you posted?',
  'leave.confirmSuffix': 'This cannot be undone.',
  'leave.yes': 'Yes, delete it',
  'leave.keep': 'Keep my profile',
} as const;

export type MessageKey = keyof typeof EN;

/**
 * Russian. Absent keys are deliberate, not unfinished: each one contains a term
 * from the glossary whose Russian equivalent a person has to choose.
 */
const RU: Partial<Record<MessageKey, string>> = {
  ...G1_RU,
  'shared.title': 'Общий маршрут подготовки',
  'shared.recoveryDraft': 'Черновик браузера восстановлен или изменён — серверу он не сохранён. В этой вкладке остаётся ваш ввод.',
  'shared.recoveryUnavailable': 'Восстановление в браузере недоступно. Ввод остаётся здесь; новый запрос нельзя отправить, пока исходная команда не записана.',
  'shared.recoveryInvalid': 'Журнал этой заявки не поддерживается или изменился. Он не принят и не перезаписан. Для продолжения явно сбросьте локальный черновик этой заявки.',
  'shared.recoveryCleanup': 'Найдено точное подтверждение сервера, но журнал браузера не удалось безопасно очистить. Сохраните исходную команду и обновите сохранённый маршрут.',
  'shared.recoveryNewer': 'Исходный запрос сохранён. Более новые изменения остаются несохранённым черновиком браузера.',
  'shared.recoveryNotSent': 'Новая команда не отправлена: её не удалось записать в браузере. Явно повторите ту же исходную команду.',
  'shared.recoveryReset': 'Сбросить локальный черновик маршрута',
  'shared.recoveryResetConfirm': 'Удалить черновик маршрута и непримирённую команду этой заявки в данной вкладке? Серверные планы и история останутся без изменений.',
  'shared.recoveryLeave': 'Есть несохранённый ввод маршрута или запрос без подтверждения. Покинуть экран? Эта вкладка сохраняет журнал восстановления, если хранилище доступно; уход не сохраняет данные серверу.',
  'shared.nav': 'Общий маршрут',
  'shared.goalsNav': 'Цели и доказательства',
  'shared.legacyHistory': 'Прежний личный план занятий',
  'shared.legacyInactive': 'Активен общий недельный бюджет. Прежний план остался в истории и не создаёт второй активный бюджет.',
  'shared.legacyUnknown': 'Не удалось проверить активный общий маршрут. Прежняя история доступна только для чтения до успешной проверки.',
  'shared.intro': 'Выберите свои программы и даты экзаменов. На выбранные экзамены действует один недельный бюджет занятий.',
  'shared.oneBudget': 'Один общий недельный бюджет',
  'shared.readonly': 'Сохранённый маршрут и история доступны для чтения. Для просмотра нового плана, сохранения и открытия уроков нужен действующий срок подготовки.',
  'shared.loading': 'Загружаем сохранённый маршрут…',
  'shared.error': 'Не удалось загрузить общий маршрут.',
  'shared.mismatch': 'Ответ не совпадает с этим профилем и точным запросом. Обновите данные.',
  'shared.refresh': 'Обновить сохранённый маршрут',
  'shared.acceptedRevision': 'Принятая версия',
  'shared.current': 'Текущий сохранённый маршрут',
  'shared.history': 'Прежние сохранённые версии',
  'shared.historyHint': 'Откройте точную версию своего сохранённого маршрута.',
  'shared.revision': 'Версия',
  'shared.openHistory': 'Открыть версию',
  'shared.historical': 'Прежний сохранённый маршрут',
  'shared.historyInvalid': 'Введите номер сохранённой версии.',
  'shared.newPlan': 'Составить общий маршрут',
  'shared.selectionHint': 'Выберите по порядку 2–20 собственных результатов с решением «одобрено» или «возможно». Подсказки ниже относятся только к последнему загруженному поиску. ID более раннего результата можно ввести вручную; сервер проверит каждый выбор.',
  'shared.goalReference': 'ID результата',
  'shared.programmeNumber': 'Сохранённая программа',
  'shared.reference': 'Показать точный ID',
  'shared.remove': 'Убрать',
  'shared.up': 'Переместить выше',
  'shared.add': 'Добавить',
  'shared.savedId': 'ID прежнего сохранённого результата',
  'shared.savedIdHint': 'Введите точный ID собственного сохранённого результата. Сервер проверит, можно ли его выбрать.',
  'shared.invalidId': 'Введите точный ID сохранённого результата без лишних пробелов.',
  'shared.addId': 'Добавить ID',
  'shared.startsOn': 'Начало планирования',
  'shared.timezone': 'Ваш часовой пояс',
  'shared.weeklyMinutes': 'Минут в неделю на все экзамены',
  'shared.days': 'Дни занятий',
  'shared.day0': 'Пн', 'shared.day1': 'Вт', 'shared.day2': 'Ср', 'shared.day3': 'Чт',
  'shared.day4': 'Пт', 'shared.day5': 'Сб', 'shared.day6': 'Вс',
  'shared.ielts': 'IELTS Academic', 'shared.sat': 'Digital SAT',
  'shared.includeExam': 'Добавить этот личный экзамен',
  'shared.priorityFirst': 'Поставить этот экзамен первым в распределении',
  'shared.firstExam': 'Дата первого экзамена',
  'shared.retake': 'Дата пересдачи, если планируется',
  'shared.certificateDeadline': 'Когда вам нужен сертификат',
  'shared.latestSafe': 'Расчётная последняя дата экзамена по указанным вами срокам',
  'shared.personalTargetHint': 'Ваши необязательные цели, не требования вузов',
  'shared.wait': 'Дней до результата',
  'shared.delivery': 'Дней на доставку',
  'shared.safety': 'Дней запаса',
  'shared.optionalTargets': 'Необязательные личные цели',
  'shared.confirmExam': 'Я сам(а) ввёл(а) эти личные даты и сроки',
  'shared.ownReviews': 'Разборы моих сохранённых попыток',
  'shared.reviewHint': 'Для разбора используются ваша точная попытка и указанные вами минуты. Он не заменяет урок.',
  'shared.addReview': 'Добавить свой разбор',
  'shared.olderReview': 'Прежняя собственная попытка по точной ссылке',
  'shared.attemptId': 'UUID своей попытки', 'shared.lessonId': 'Точный ID урока',
  'shared.contentVersion': 'Точная версия материала', 'shared.chooseExam': 'Выберите экзамен явно',
  'shared.invalidReview': 'Введите точные UUID своей попытки, ID урока и версию материала без лишних пробелов.',
  'shared.exam': 'Экзамен',
  'shared.reviewMinutes': 'Минут на этот разбор',
  'shared.confirmInputs': 'Я явно выбрал(а) программы, общий бюджет и личные экзаменационные планы',
  'shared.previewOnly': 'Предпросмотр не сохраняется. Время уроков — распределение нагрузки, а не подтверждение освоения или поступления.',
  'shared.preview': 'Предпросмотр маршрута',
  'shared.invalid': 'Проверьте число программ, даты, подтверждения, минуты разбора и общий недельный бюджет.',
  'shared.previewResult': 'Предпросмотр маршрута',
  'shared.unsaved': 'Только предпросмотр — ничего не сохранено.',
  'shared.save': 'Сохранить этот точный предпросмотр',
  'shared.saving': 'Сохраняем точный запрос…',
  'shared.saved': 'Сервер принял маршрут. Обновляем сохранённую версию.',
  'shared.conflict': 'Плановые данные изменились в другом месте. Черновик сохранён; обновите данные и просмотрите новый план перед сохранением.',
  'shared.uncertain': 'Итог запроса неизвестен. Повторите только исходный запрос с тем же ID и полями; новая попытка автоматически не создаётся.',
  'shared.originalIntent': 'ID исходного запроса',
  'shared.retryOriginal': 'Повторить исходный запрос',
  'shared.newIntent': 'Начать новое сохранение из свежего предпросмотра',
  'shared.acceptedOn': 'Принято',
  'shared.status': 'Текущий статус:',
  'shared.evidenceHint': 'В разделе «Цели и доказательства» доступны текущие источники, область применимости и неясные правила. Сохранённый маршрут не копирует закрытые доказательства.',
  'shared.needsReview': 'Нужно сверить текущие доказательства или материалы',
  'shared.reviewReasons': 'Причины повторной проверки маршрута',
  'shared.noCurrentChange': 'Текущие изменения не отмечены',
  'shared.legacyStatus': 'Структура прежнего плана:',
  'shared.contentStatus': 'Импортированные ссылки:',
  'shared.savedTruth': 'Сохранены точные ссылки и плановые минуты. Освоение, официальный балл и возможность поступления этим не подтверждаются.',
  'shared.minutesWeek': 'минут в неделю',
  'shared.minutes': 'минут',
  'shared.notReadiness': 'Только личная практика; готовность не оценивалась.',
  'shared.lesson': 'Урок', 'shared.review': 'Разбор своей попытки',
  'shared.openLesson': 'Открыть точный урок', 'shared.openReview': 'Открыть точный разбор',
  'shared.exactUnavailable': 'Точный материал сейчас недоступен',
  'shared.noSlots': 'В указанные сроки и нагрузку задания не поместились.',
  'shared.unallocated': 'Задания без даты',
  'shared.targetOverall': 'Личная цель: общий балл', 'shared.targetListening': 'Личная цель: аудирование',
  'shared.targetReading': 'Личная цель: чтение', 'shared.targetWriting': 'Личная цель: письмо',
  'shared.targetSpeaking': 'Личная цель: речь', 'shared.targetTotal': 'Личная цель: общий балл',
  'shared.targetMath': 'Личная цель: математика', 'shared.targetReadingWriting': 'Личная цель: чтение и письмо',
  'shared.stateEligible': 'Эта программа остаётся в вашем выборе', 'shared.stateDecision': 'Ваше решение по программе изменилось',
  'shared.stateMissing': 'Результат недоступен', 'shared.stateLocked': 'Исследование закрыто',
  'shared.stateSource': 'Источник изменился', 'shared.stateUnknown': 'Неизвестно; нужна проверка',
  'shared.stateUnchanged': 'Без изменений', 'shared.stateChanged': 'Изменилось',
  'shared.stateNotUsed': 'Не использовалось', 'shared.stateAvailable': 'Доступно',
  'shared.stateVersion': 'Точная версия недоступна', 'shared.stateReview': 'Свой разбор недоступен',
  'shared.timingWithin': 'В пределах указанных сроков', 'shared.timingRisk': 'Риск по указанным срокам',
  'shared.timingPassed': 'Указанный срок прошёл',
  'shared.reasonCapacity': 'Не хватило общего времени', 'shared.reasonWindow': 'Срок практики прошёл',
  'shared.reasonDay': 'Дольше одного учебного дня', 'shared.reasonWeek': 'Дольше недельного бюджета',
  'shared.reasonLimit': 'Достигнут предел заданий маршрута',
  'learning.title': 'Учебный календарь',
  'learning.open': 'Открыть учебный календарь',
  'learning.preview': 'Посмотреть обновлённый маршрут',
  'learning.save': 'Сохранить этот маршрут',
  'learning.cancel': 'Закрыть просмотр',
  'learning.loading': 'Загружаем учебный календарь…',
  'learning.loaded': 'Учебный календарь сохранён. Прежние отметки остались в истории.',
  'learning.previewNotice': 'Это предварительный просмотр. Проверьте материалы и даты перед сохранением. Исходный календарь и ваши отметки сохраняются.',
  'learning.dirty': 'Сначала сохраните или отмените изменения исходного плана.',
  'learning.conflict': 'Календарь изменился в другом окне. Загрузите и просмотрите свежую версию перед новым сохранением. Поля исходной формы сохранены.',
  'learning.stale': 'Настройки исходного плана изменились. Просмотрите новый маршрут перед использованием.',
  'learning.history': 'История отметок о выполнении',
  'learning.lesson': 'Открыть урок',
  'learning.review': 'Разобрать мою попытку',
  'learning.submitted': 'Попытка сохранена — освоение не подтверждено',
  'learning.no_local_content': 'Для этого навыка пока нет материалов в приложении.',
  'learning.attempt_required': 'Сохранённая попытка не выбрана. После практики просмотрите маршрут заново.',
  'learning.not_implemented': 'Это оценивание пока недоступно.',
  'learning.version_unavailable': 'Точная сохранённая версия материала недоступна.',
  'learning.unallocated': 'Уроки, на которые не хватило времени в плане',
  'learning.details': 'Сведения о материале',
  'learning.other': 'Другие задачи, включая прошедшие даты',
  'learning.empty': 'Сначала сохраните исходный учебный план.',
  'learning.error': 'Не удалось загрузить или сохранить календарь. Сохранение не подтверждено.',
  'learning.readonly': 'Ваша история доступна. Для новых уроков и изменений нужен доступ к подготовке.',
  'learning.note': 'Не менее двадцати минут на урок — плановое распределение. Задачи и сохранённые попытки не подтверждают освоение, официальный балл или готовность к экзамену.',

  'nav.group.prepare': 'Подготовка',
  'nav.group.decide': 'Решение',
  'nav.group.community': 'Сообщество',
  'nav.group.about': 'О сервисе',

  'nav.profile': 'Профиль абитуриента',
  'nav.preparation': 'Подготовка к экзаменам',
  'nav.progress': 'Ход исследования',
  'nav.approved': 'Одобренные университеты',
  'nav.documents': 'Документы и сроки',
  'nav.feed': 'Лента',
  'nav.discover': 'Поиск абитуриентов',
  'nav.me': 'Мой профиль в сообществе',
  'nav.legal': 'Конфиденциальность и условия',

  'topbar.applicant': 'Абитуриент',
  'topbar.newApplicant': 'Новый абитуриент',
  'topbar.signOut': 'Выйти',
  'topbar.connecting': 'соединение…',

  'appearance.label': 'Оформление',
  'appearance.system': 'Как в системе',
  'appearance.light': 'Светлое',
  'appearance.dark': 'Тёмное',

  'language.label': 'Язык',

  'community.title': 'Сообщество',
  'community.lede':
    'Абитуриенты, которые метят в те же города и вузы. Всё, что здесь пишут, — личный опыт '
    + 'людей, а не проверенные данные с сайта университета.',
  'community.joinPrompt':
    'Ленту можно читать уже сейчас. Создайте профиль, чтобы писать, отвечать и попадаться на '
    + 'глаза тем, кто подаётся туда же.',
  'community.createProfile': 'Создать профиль',
  'community.write': 'Написать пост',
  'community.writeHint': 'Отметьте вуз или город через #, чтобы вас нашли нужные люди.',
  'community.placeholder': 'Спросите что-нибудь или расскажите, куда подаётесь',
  'community.post': 'Опубликовать',
  'community.posting': 'Публикуем…',
  'community.willBeTagged': 'Будут отмечены',
  'community.charsLeft': 'осталось',
  'community.charsOver': 'лишних',
  'community.answerPlaceholder': 'Ответьте на это',
  'community.reply': 'Ответить',
  'community.answer': 'Ответить',
  'community.hideAnswers': 'Скрыть ответы',
  'community.noAnswers': 'Ответов пока нет. Будьте первым.',
  'community.earlierAnswers': 'Показать ранние ответы',
  'community.openingThread': 'Открываем ветку',
  'community.loadingPosts': 'Загружаем посты',
  'community.olderPosts': 'Показать старые посты',
  'community.noPosts': 'Постов пока нет',
  'community.noPostsHint':
    'Первый пост задаёт тон. Задайте вопрос, ответ на который вы так и не нашли.',
  'community.noMatch': 'Под эти фильтры ничего не подходит',
  'community.noMatchHint': 'Ослабьте фильтры или сбросьте их, чтобы увидеть всё.',
  'community.clearFilters': 'Сбросить фильтры',
  'community.filterTag': 'Тег',
  'community.filterCity': 'Город поступления',
  'community.filterAuthorStatus': 'Статус автора',
  'community.anyone': 'Любой',

  'community.delete': 'Удалить',
  'community.deleteConfirm': 'Да, удалить',
  'community.keepIt': 'Оставить',
  'community.deleting': 'Удаляем…',
  'community.deletePostQ': 'Удалить этот пост?',
  'community.deletePostThreadQ': 'Удалить пост вместе с ответами?',
  'community.deleteAnswerQ': 'Удалить этот ответ?',

  'discover.title': 'Найдите таких же абитуриентов',
  'discover.lede':
    'Все, кто здесь есть, сами решили здесь быть. Написание не важно: KBTU, kbtu и K.B.T.U. — '
    + 'для фильтра один и тот же вуз.',
  'discover.city': 'Город',
  'discover.university': 'Университет',
  'discover.major': 'Специальность',
  'discover.status': 'Статус',
  'discover.anyStatus': 'Любой статус',
  'discover.looking': 'Ищем',
  'discover.more': 'Показать ещё',
  'discover.noMatch': 'Пока никто не подходит',
  'discover.noMatchHint':
    'Пробуйте по одному фильтру — по городу обычно находится больше всего людей.',
  'discover.empty': 'Пока никто не вступил',
  'discover.emptyHint': 'Создайте свой профиль — и вы будете здесь первым.',
  'discover.noAim': 'Не указал, куда поступает',

  'person.statusAccepted': 'Поступил',
  'person.statusWaitlist': 'В листе ожидания',
  'person.statusUnstated': 'Статус не указан',
  'person.statusStatedTitle': 'То, что абитуриент сам говорит о своих заявках.',
  'person.statusUnstatedTitle': 'Абитуриент не сказал, на каком он этапе.',
  'person.joinTitle': 'Вступить в сообщество',
  'person.joinLede':
    'Регистрация ничего о вас не опубликовала. Именно эта форма помещает вас в поиск, и её '
    + 'можно изменить или выйти обратно в любой момент.',
  'person.noProfile': 'Здесь нет профиля',
  'person.noProfileHint': 'Этот абитуриент не вступал в сообщество.',
  'person.loading': 'Загружаем профиль',
  'person.edit': 'Изменить профиль',
  'person.cancel': 'Отмена',
  'person.yourProfile': 'Ваш профиль',
  'person.aimingAt': 'Куда поступает',
  'person.aimingHint': 'Со слов самого абитуриента. Не сверялось с сайтом университета.',
  'person.city': 'Город',
  'person.major': 'Специальность',
  'person.universities': 'Университеты',
  'person.notStated': 'не указано',
  'person.yourPosts': 'Ваши посты',
  'person.noPostsYou': 'Вы ещё ничего не писали',
  'person.noPostsYouHint': 'Всё, что вы напишете в сообществе, появится здесь.',
  'person.noPostsThem': 'Постов пока нет',
  'person.postsBy': 'Посты',

  'person.formStatus': 'На каком вы этапе',
  'person.formStatusNone': 'Предпочитаю не говорить',
  'person.formStatusHint':
    'Если не выбрать, в профиле будет написано «не указан», а не придуманный статус.',
  'person.formCity': 'Город, куда вы поступаете',
  'person.formMajor': 'Специальность',
  'person.formUniversities': 'Университеты, куда метите',
  'person.formUniversitiesHint': 'Через запятую.',
  'person.formBio': 'О себе',
  'person.formBioPlaceholder': 'Чем вы заняты и о чём вас стоит спрашивать.',
  'person.save': 'Сохранить профиль',
  'person.saving': 'Сохраняем…',
  'person.publicWarning':
    'Всё это видно другим абитуриентам. Ваше дело по поступлению — нет.',

  'nav.messages': 'Сообщения',
  'nav.moderation': 'Очередь модерации',

  'report.action': 'Пожаловаться',
  'report.title': 'Пожаловаться модератору',
  'report.reason': 'Что здесь не так',
  'report.harassment': 'Травля или оскорбления',
  'report.personal_information': 'Чужие личные данные',
  'report.impersonation': 'Выдаёт себя за другого',
  'report.spam': 'Спам или реклама',
  'report.misleading_advice': 'Слух о вузе подан как факт',
  'report.other': 'Другое',
  'report.note': 'Что стоит знать модератору (необязательно)',
  'report.send': 'Отправить жалобу',
  'report.sending': 'Отправляем…',
  'report.cancel': 'Отмена',
  'report.sent': 'Жалоба отправлена. Её посмотрит человек.',
  'report.already': 'Вы уже жаловались на это.',
  'report.slow':
    'Жалобы читает человек, поэтому это не мгновенно. Если вас достают прямо сейчас — '
    + 'заблокируйте: это срабатывает сразу.',

  'block.action': 'Заблокировать',
  'block.unblock': 'Разблокировать',
  'block.confirm': 'Заблокировать этого абитуриента?',
  'block.explain':
    'Он не сможет вам писать и отвечать на ваши посты, и вы перестанете видеть друг друга в '
    + 'ленте и в поиске. Ему об этом не сообщат.',
  'block.blocked': 'Заблокирован',
  'block.list': 'Заблокированные',
  'block.listEmpty': 'Вы никого не блокировали.',

  'moderation.title': 'Очередь модерации',
  'moderation.lede':
    'Жалобы сообщества, старые сверху. Удаление убирает содержимое у всех и записывает, кто '
    + 'это сделал.',
  'moderation.open': 'Открытые',
  'moderation.actioned': 'Удалено',
  'moderation.dismissed': 'Отклонено',
  'moderation.empty': 'Ничего не ждёт',
  'moderation.emptyHint': 'Жалобы появятся здесь, как только их подадут.',
  'moderation.loading': 'Загружаем очередь',
  'moderation.reportedBy': 'Пожаловался',
  'moderation.about': 'На что',
  'moderation.excerpt': 'Что там было написано на момент жалобы',
  'moderation.gone': 'Это содержимое уже удалено.',
  'moderation.remove': 'Удалить',
  'moderation.dismiss': 'Оставить',
  'moderation.resolutionNote': 'Почему (запишется вместе с вашим именем)',
  'moderation.resolvedBy': 'Решение принял',
  'moderation.subjectPost': 'пост',
  'moderation.subjectReply': 'ответ',
  'moderation.subjectMessage': 'личное сообщение',
  'moderation.subjectProfile': 'профиль',
  'messages.title': 'Сообщения',
  'messages.lede':
    'Личная переписка. Её не видит никто посторонний, и написанное здесь не попадает ни в '
    + 'ленту, ни в ваш профиль.',
  'messages.loading': 'Загружаем переписку',
  'messages.opening': 'Открываем разговор',
  'messages.empty': 'Переписок пока нет',
  'messages.emptyHint':
    'Ответьте кому-нибудь в ленте или откройте профиль и напишите. Кто может написать вам '
    + 'первым — решаете вы: настройка в вашем профиле.',
  'messages.emptyThread': 'Здесь пока пусто',
  'messages.emptyThreadHint': 'Напишите первое сообщение.',
  'messages.placeholder': 'Напишите сообщение',
  'messages.send': 'Отправить',
  'messages.back': 'Все переписки',
  'messages.write': 'Написать сообщение',
  'messages.closed': 'Этот абитуриент не принимает сообщения.',
  'messages.needsThread':
    'Этот абитуриент принимает сообщения только от тех, кому отвечал публично. Ответьте на '
    + 'его пост или задайте вопрос, на который он сможет ответить.',

  'person.avatar': 'Ваше фото',
  'person.avatarChoose': 'Выбрать фото',
  'person.avatarRemove': 'Удалить',
  'person.avatarUploading': 'Загружаем…',
  'person.avatarHint':
    'JPEG или PNG, до 512 КБ. Место съёмки удаляется до сохранения, а само фото видят все '
    + 'абитуриенты, которым доступен ваш профиль.',

  'person.formDmPolicy': 'Кто может написать вам первым',
  'person.formDmAnyone': 'Любой участник сообщества',
  'person.formDmThreads': 'Только те, кому я отвечал, или кто отвечал мне',
  'person.formDmNobody': 'Никто — входящие закрыты',
  'person.formDmHint':
    'Это правило только для первого сообщения. Тот, с кем вы уже переписываетесь, сможет '
    + 'написать вам при любом выборе.',

  'leave.title': 'Выйти из сообщества',
  'leave.hint':
    'Аккаунт и ваше исследование останутся. Профиль, посты и ответы будут удалены, и вы '
    + 'исчезнете из поиска.',
  'leave.confirm': 'Удалить профиль и всё, что вы написали?',
  'leave.confirmSuffix': 'Это необратимо.',
  'leave.yes': 'Да, удалить',
  'leave.keep': 'Оставить профиль',
};

/** Kazakh, on the same rule. */
const KK: Partial<Record<MessageKey, string>> = {
  ...G1_KK,
  'shared.title': 'Ортақ дайындық бағыты',
  'shared.recoveryDraft': 'Браузердегі жоба қалпына келтірілді немесе өзгерді — ол серверге сақталмаған. Енгізілген деректер осы қойындыда қалады.',
  'shared.recoveryUnavailable': 'Браузерде қалпына келтіру қолжетімсіз. Деректер осында қалады; бастапқы команда жазылмайынша жаңа сұрау жіберілмейді.',
  'shared.recoveryInvalid': 'Осы өтінімнің жергілікті журналы қолдау таппайды немесе өзгерген. Ол қабылданбады және қайта жазылмады. Жалғастыру үшін осы өтінімнің жергілікті жобасын өзіңіз тазалаңыз.',
  'shared.recoveryCleanup': 'Сервердің дәл растауы табылды, бірақ браузер журналы қауіпсіз тазаланбады. Бастапқы команданы сақтап, сақталған бағытты жаңартыңыз.',
  'shared.recoveryNewer': 'Бастапқы сұрау сақталды. Кейінгі өзгерістер браузерде сақталмаған жоба болып қалды.',
  'shared.recoveryNotSent': 'Жаңа команда жіберілмеді: оны браузерге жазу мүмкін болмады. Сол бастапқы команданы өзіңіз қайта жіберіңіз.',
  'shared.recoveryReset': 'Бағыттың жергілікті жобасын тазалау',
  'shared.recoveryResetConfirm': 'Осы қойындыдағы өтінімнің бағыт жобасы мен расталмаған командасын жою керек пе? Сервердегі жоспарлар мен тарих өзгермейді.',
  'shared.recoveryLeave': 'Бағыттың сақталмаған деректері немесе расталмаған сұрау бар. Экраннан шығасыз ба? Хранилище қолжетімді болса, журнал осы қойындыда қалады; шығу деректерді серверге сақтамайды.',
  'shared.nav': 'Ортақ бағыт',
  'shared.goalsNav': 'Мақсаттар мен деректер',
  'shared.legacyHistory': 'Бұрынғы жеке оқу жоспары',
  'shared.legacyInactive': 'Ортақ апталық уақыт белсенді. Бұрынғы жоспар тарихта қалады және екінші белсенді уақыт шегін жасамайды.',
  'shared.legacyUnknown': 'Белсенді ортақ бағытты тексеру мүмкін болмады. Тексеру сәтті аяқталғанша бұрынғы тарих тек оқуға қолжетімді.',
  'shared.intro': 'Өз бағдарламаларыңыз бен емтихан күндерін таңдаңыз. Таңдалған емтихандарға бір ортақ апталық оқу уақыты қолданылады.',
  'shared.oneBudget': 'Бір ортақ апталық уақыт шегі',
  'shared.readonly': 'Сақталған бағыт пен тарихты оқуға болады. Жаңа жоспарды қарау, сақтау және сабақты ашу үшін дайындық мерзімі белсенді болуы керек.',
  'shared.loading': 'Сақталған бағыт жүктелуде…',
  'shared.error': 'Ортақ бағытты жүктеу мүмкін болмады.',
  'shared.mismatch': 'Жауап осы профиль мен нақты сұрауға сәйкес келмейді. Деректерді жаңартыңыз.',
  'shared.refresh': 'Сақталған бағытты жаңарту',
  'shared.acceptedRevision': 'Қабылданған нұсқа',
  'shared.current': 'Қазіргі сақталған бағыт',
  'shared.history': 'Бұрын сақталған нұсқалар',
  'shared.historyHint': 'Өз сақталған бағытыңыздың нақты нұсқасын ашыңыз.',
  'shared.revision': 'Нұсқа',
  'shared.openHistory': 'Нұсқаны ашу',
  'shared.historical': 'Бұрын сақталған бағыт',
  'shared.historyInvalid': 'Сақталған нұсқаның нөмірін енгізіңіз.',
  'shared.newPlan': 'Ортақ бағыт құру',
  'shared.selectionHint': 'Өзіңіздің «мақұлданған» не «мүмкін» деген шешімі бар 2–20 нәтижені ретімен таңдаңыз. Төмендегі ұсыныстар тек соңғы жүктелген іздеуден алынған. Бұрын сақталған нәтиженің ID-н қолмен енгізуге болады; сервер әр таңдауды тексереді.',
  'shared.goalReference': 'Нәтиженің ID-і',
  'shared.programmeNumber': 'Сақталған бағдарлама',
  'shared.reference': 'Нақты ID-н көрсету',
  'shared.remove': 'Алып тастау',
  'shared.up': 'Жоғары жылжыту',
  'shared.add': 'Қосу',
  'shared.savedId': 'Бұрын сақталған нәтиженің ID-і',
  'shared.savedIdHint': 'Өзіңіздің сақталған нәтижеңіздің нақты ID-н енгізіңіз. Оны таңдауға болатынын сервер тексереді.',
  'shared.invalidId': 'Сақталған нәтиженің нақты ID-н артық бос орынсыз енгізіңіз.',
  'shared.addId': 'ID қосу',
  'shared.startsOn': 'Жоспар басталатын күн',
  'shared.timezone': 'Уақыт белдеуі',
  'shared.weeklyMinutes': 'Барлық емтиханға арналған апталық минут',
  'shared.days': 'Оқу күндері',
  'shared.day0': 'Дс', 'shared.day1': 'Сс', 'shared.day2': 'Ср', 'shared.day3': 'Бс',
  'shared.day4': 'Жм', 'shared.day5': 'Сб', 'shared.day6': 'Жс',
  'shared.ielts': 'IELTS Academic', 'shared.sat': 'Digital SAT',
  'shared.includeExam': 'Осы жеке емтиханды қосу',
  'shared.priorityFirst': 'Осы емтиханды бөлу кезегінде бірінші қою',
  'shared.firstExam': 'Бірінші емтихан күні',
  'shared.retake': 'Қайта тапсыру күні, жоспарланса',
  'shared.certificateDeadline': 'Сертификат қажет күн',
  'shared.latestSafe': 'Өзіңіз енгізген мерзімдер бойынша есептелген ең соңғы емтихан күні',
  'shared.personalTargetHint': 'Өз жеке мақсаттарыңыз, университет талабы емес',
  'shared.wait': 'Нәтижені күту күндері',
  'shared.delivery': 'Жеткізу күндері',
  'shared.safety': 'Қосымша сақтық күндері',
  'shared.optionalTargets': 'Міндетті емес жеке мақсаттар',
  'shared.confirmExam': 'Бұл жеке күндер мен мерзімдерді өзім енгіздім',
  'shared.ownReviews': 'Сақталған өз әрекеттерімді талдау',
  'shared.reviewHint': 'Талдауда өзіңіздің нақты сақталған әрекетіңіз және енгізген минутыңыз қолданылады. Ол сабақты алмастырмайды.',
  'shared.addReview': 'Өз талдауымды қосу',
  'shared.olderReview': 'Бұрынғы өз әрекетімнің нақты сілтемесі',
  'shared.attemptId': 'Өз әрекетімнің UUID-і', 'shared.lessonId': 'Сабақтың нақты ID-і',
  'shared.contentVersion': 'Материалдың нақты нұсқасы', 'shared.chooseExam': 'Емтиханды анық таңдаңыз',
  'shared.invalidReview': 'Өз әрекетіңіздің UUID-ін, сабақ ID-н және материал нұсқасын артық бос орынсыз енгізіңіз.',
  'shared.exam': 'Емтихан',
  'shared.reviewMinutes': 'Осы талдауға минут',
  'shared.confirmInputs': 'Бағдарламаларды, ортақ уақытты және жеке емтихан жоспарларын өзім таңдадым',
  'shared.previewOnly': 'Алдын ала қарау сақталмайды. Сабаққа бөлінген уақыт меңгеруді не оқуға қабылдануды растамайды.',
  'shared.preview': 'Бағытты алдын ала қарау',
  'shared.invalid': 'Бағдарламалар санын, күндерді, растауларды, талдау минутын және ортақ апталық уақытты тексеріңіз.',
  'shared.previewResult': 'Бағыттың алдын ала көрінісі',
  'shared.unsaved': 'Тек алдын ала қарау — ештеңе сақталмады.',
  'shared.save': 'Осы нақты көріністі сақтау',
  'shared.saving': 'Нақты сұрау сақталуда…',
  'shared.saved': 'Сервер бағытты қабылдады. Сақталған нұсқа жаңартылуда.',
  'shared.conflict': 'Жоспар деректері басқа жерде өзгерді. Нобай сақталды; қайта сақтау алдында деректерді жаңартып, жаңа көріністі қараңыз.',
  'shared.uncertain': 'Сұраудың нәтижесі белгісіз. Тек бастапқы ID мен деректерді қайталаңыз; жаңа сұрау автоматты түрде жасалмайды.',
  'shared.originalIntent': 'Бастапқы сұраудың ID-і',
  'shared.retryOriginal': 'Бастапқы сұрауды қайталау',
  'shared.newIntent': 'Жаңа көріністен жаңа сақтау сұрауын бастау',
  'shared.acceptedOn': 'Қабылданған уақыты',
  'shared.status': 'Қазіргі күй:',
  'shared.evidenceHint': 'Бағдарламаның қазіргі дереккөздері, қолданылу аясы және анықталмаған ережелері «Мақсаттар мен деректер» бөлімінде. Сақталған бағыт жабық деректердің көшірмесін жасамайды.',
  'shared.needsReview': 'Қазіргі дереккөзді немесе материалды қайта қарау қажет',
  'shared.reviewReasons': 'Бағытты қайта қарау себептері',
  'shared.noCurrentChange': 'Қазіргі өзгеріс көрсетілмеді',
  'shared.legacyStatus': 'Бұрынғы жоспар құрылымы:',
  'shared.contentStatus': 'Импортталған сілтемелер:',
  'shared.savedTruth': 'Нақты сілтемелер мен жоспар минуттары сақталды. Бұл меңгеруді, ресми балды немесе оқуға түсу мүмкіндігін растамайды.',
  'shared.minutesWeek': 'минут аптасына',
  'shared.minutes': 'минут',
  'shared.notReadiness': 'Тек жеке жаттығу; дайындық бағаланбады.',
  'shared.lesson': 'Сабақ', 'shared.review': 'Өз әрекетін талдау',
  'shared.openLesson': 'Нақты сабақты ашу', 'shared.openReview': 'Өз талдауымды ашу',
  'shared.exactUnavailable': 'Нақты материал қазір қолжетімсіз',
  'shared.noSlots': 'Көрсетілген күндер мен уақытқа тапсырма сыймады.',
  'shared.unallocated': 'Күні бөлінбеген тапсырмалар',
  'shared.targetOverall': 'Жеке мақсат: жалпы балл', 'shared.targetListening': 'Жеке мақсат: тыңдалым',
  'shared.targetReading': 'Жеке мақсат: оқылым', 'shared.targetWriting': 'Жеке мақсат: жазылым',
  'shared.targetSpeaking': 'Жеке мақсат: айтылым', 'shared.targetTotal': 'Жеке мақсат: жалпы балл',
  'shared.targetMath': 'Жеке мақсат: математика', 'shared.targetReadingWriting': 'Жеке мақсат: оқылым және жазылым',
  'shared.stateEligible': 'Бұл бағдарлама өз таңдауыңызда қалды', 'shared.stateDecision': 'Бағдарлама туралы өз шешіміңіз өзгерді',
  'shared.stateMissing': 'Нәтиже қолжетімсіз', 'shared.stateLocked': 'Зерттеу жабық',
  'shared.stateSource': 'Дереккөз өзгерді', 'shared.stateUnknown': 'Белгісіз; тексеру қажет',
  'shared.stateUnchanged': 'Өзгермеген', 'shared.stateChanged': 'Өзгерген',
  'shared.stateNotUsed': 'Қолданылмаған', 'shared.stateAvailable': 'Қолжетімді',
  'shared.stateVersion': 'Нақты нұсқа қолжетімсіз', 'shared.stateReview': 'Өз талдауым қолжетімсіз',
  'shared.timingWithin': 'Енгізілген мерзімге сыяды', 'shared.timingRisk': 'Енгізілген мерзімде тәуекел бар',
  'shared.timingPassed': 'Енгізілген мерзім өтті',
  'shared.reasonCapacity': 'Ортақ уақыт жетпеді', 'shared.reasonWindow': 'Жаттығу мерзімі өтті',
  'shared.reasonDay': 'Бір оқу күнінен ұзақ', 'shared.reasonWeek': 'Апталық уақыттан ұзақ',
  'shared.reasonLimit': 'Бағыттағы тапсырмалар шегіне жетті',
  'learning.title': 'Оқу күнтізбесі',
  'learning.open': 'Оқу күнтізбесін ашу',
  'learning.preview': 'Жаңартылған жоспарды қарау',
  'learning.save': 'Осы жоспарды сақтау',
  'learning.cancel': 'Алдын ала қарауды жабу',
  'learning.loading': 'Оқу күнтізбесі жүктелуде…',
  'learning.loaded': 'Оқу күнтізбесі сақталды. Бұрынғы белгілер тарихта қалды.',
  'learning.previewNotice': 'Бұл алдын ала қарау. Сақтамас бұрын материалдар мен күндерді тексеріңіз. Бастапқы күнтізбе мен белгілер сақталады.',
  'learning.dirty': 'Алдымен бастапқы жоспардағы өзгерістерді сақтаңыз немесе болдырмаңыз.',
  'learning.conflict': 'Күнтізбе басқа терезеде өзгерді. Қайта сақтамас бұрын жаңа нұсқаны жүктеп қараңыз. Бастапқы нысанның мәндері сақталды.',
  'learning.stale': 'Бастапқы жоспардың параметрлері өзгерді. Жаңа жоспарды қарап шығыңыз.',
  'learning.history': 'Орындалды деп белгіленген тапсырмалар тарихы',
  'learning.lesson': 'Сабақты ашу',
  'learning.review': 'Өз әрекетімді талдау',
  'learning.submitted': 'Әрекет сақталды — меңгеру расталмады',
  'learning.no_local_content': 'Бұл дағды үшін қолданбада әзірге материал жоқ.',
  'learning.attempt_required': 'Сақталған әрекет таңдалмаған. Жаттығудан кейін жоспарды қайта қараңыз.',
  'learning.not_implemented': 'Бұл бағалау әзірге қолжетімсіз.',
  'learning.version_unavailable': 'Материалдың нақты сақталған нұсқасы қолжетімсіз.',
  'learning.unallocated': 'Жоспарда уақыт жетпеген сабақтар',
  'learning.details': 'Материал туралы мәлімет',
  'learning.other': 'Басқа тапсырмалар, өткен күндерді қоса',
  'learning.empty': 'Алдымен бастапқы оқу жоспарын сақтаңыз.',
  'learning.error': 'Күнтізбені жүктеу немесе сақтау мүмкін болмады. Сақтау расталмады.',
  'learning.readonly': 'Өз тарихыңыз қолжетімді. Жаңа сабақтар мен өзгерістерге дайындыққа рұқсат қажет.',
  'learning.note': 'Сабаққа кемінде жиырма минут — жоспардағы уақыт. Тапсырмалар мен сақталған әрекеттер меңгеруді, ресми балды немесе емтиханға дайындықты растамайды.',

  'nav.group.prepare': 'Дайындық',
  'nav.group.decide': 'Шешім',
  'nav.group.community': 'Қауымдастық',
  'nav.group.about': 'Сервис туралы',

  'nav.profile': 'Талапкер профилі',
  'nav.preparation': 'Емтиханға дайындық',
  'nav.progress': 'Зерттеу барысы',
  'nav.approved': 'Мақұлданған университеттер',
  'nav.documents': 'Құжаттар мен мерзімдер',
  'nav.feed': 'Таспа',
  'nav.discover': 'Талапкерлерді іздеу',
  'nav.me': 'Қауымдастықтағы профилім',
  'nav.legal': 'Құпиялылық және шарттар',

  'topbar.applicant': 'Талапкер',
  'topbar.newApplicant': 'Жаңа талапкер',
  'topbar.signOut': 'Шығу',
  'topbar.connecting': 'қосылуда…',

  'appearance.label': 'Безендіру',
  'appearance.system': 'Жүйедегідей',
  'appearance.light': 'Ашық',
  'appearance.dark': 'Күңгірт',

  'language.label': 'Тіл',

  'community.title': 'Қауымдастық',
  'community.lede':
    'Сол қалалар мен университеттерге ұмтылатын талапкерлер. Мұнда жазылғанның бәрі — '
    + 'адамдардың жеке тәжірибесі, университет сайтынан тексерілген дерек емес.',
  'community.joinPrompt':
    'Таспаны қазір де оқуға болады. Жазу, жауап беру және сол жаққа құжат тапсырып жүргендерге '
    + 'көріну үшін профиль жасаңыз.',
  'community.createProfile': 'Профиль жасау',
  'community.write': 'Жазба жазу',
  'community.writeHint': 'Университет пен қаланы # арқылы белгілеңіз — керек адам табады.',
  'community.placeholder': 'Бірдеңе сұраңыз немесе қайда тапсырғаныңызды жазыңыз',
  'community.post': 'Жариялау',
  'community.posting': 'Жарияланып жатыр…',
  'community.willBeTagged': 'Белгіленеді',
  'community.charsLeft': 'қалды',
  'community.charsOver': 'артық',
  'community.answerPlaceholder': 'Осыған жауап беріңіз',
  'community.reply': 'Жауап беру',
  'community.answer': 'Жауап беру',
  'community.hideAnswers': 'Жауаптарды жасыру',
  'community.noAnswers': 'Әзірге жауап жоқ. Бірінші болыңыз.',
  'community.earlierAnswers': 'Ертерек жауаптарды көрсету',
  'community.openingThread': 'Тармақ ашылып жатыр',
  'community.loadingPosts': 'Жазбалар жүктелуде',
  'community.olderPosts': 'Ескі жазбаларды көрсету',
  'community.noPosts': 'Әзірге жазба жоқ',
  'community.noPostsHint':
    'Алғашқы жазба үлгі болады. Жауабын таба алмаған сұрағыңызды қойыңыз.',
  'community.noMatch': 'Бұл сүзгілерге ештеңе сай келмейді',
  'community.noMatchHint': 'Сүзгіні босаңсытыңыз немесе бәрін көру үшін тазалаңыз.',
  'community.clearFilters': 'Сүзгілерді тазалау',
  'community.filterTag': 'Тег',
  'community.filterCity': 'Түсетін қала',
  'community.filterAuthorStatus': 'Автордың мәртебесі',
  'community.anyone': 'Кез келген',

  'community.delete': 'Жою',
  'community.deleteConfirm': 'Иә, жою',
  'community.keepIt': 'Қалдыру',
  'community.deleting': 'Жойылып жатыр…',
  'community.deletePostQ': 'Осы жазба жойылсын ба?',
  'community.deletePostThreadQ': 'Жазба жауаптарымен бірге жойылсын ба?',
  'community.deleteAnswerQ': 'Осы жауап жойылсын ба?',

  'discover.title': 'Өзіңізге ұқсас талапкерлерді табыңыз',
  'discover.lede':
    'Мұндағылардың бәрі өз қалауымен тіркелген. Жазылуы маңызды емес: KBTU, kbtu және '
    + 'K.B.T.U. — сүзгі үшін бір университет.',
  'discover.city': 'Қала',
  'discover.university': 'Университет',
  'discover.major': 'Мамандық',
  'discover.status': 'Мәртебе',
  'discover.anyStatus': 'Кез келген мәртебе',
  'discover.looking': 'Ізделуде',
  'discover.more': 'Тағы көрсету',
  'discover.noMatch': 'Әзірге ешкім сай келмейді',
  'discover.noMatchHint': 'Сүзгіні бір-бірлеп қолданыңыз — қала бойынша көбірек адам табылады.',
  'discover.empty': 'Әзірге ешкім қосылмаған',
  'discover.emptyHint': 'Өз профиліңізді жасаңыз — мұндағы бірінші адам боласыз.',
  'discover.noAim': 'Қайда түсетінін айтпаған',

  'person.statusAccepted': 'Қабылданған',
  'person.statusWaitlist': 'Күту тізімінде',
  'person.statusUnstated': 'Мәртебесі көрсетілмеген',
  'person.statusStatedTitle': 'Талапкердің өз өтініштері туралы айтқаны.',
  'person.statusUnstatedTitle': 'Талапкер қай кезеңде екенін айтпаған.',
  'person.joinTitle': 'Қауымдастыққа қосылу',
  'person.joinLede':
    'Тіркелу сіз туралы ештеңе жарияламады. Дәл осы форма сізді іздеуге қосады, оны кез келген '
    + 'уақытта өзгертуге немесе қайта шығуға болады.',
  'person.noProfile': 'Мұнда профиль жоқ',
  'person.noProfileHint': 'Бұл талапкер қауымдастыққа қосылмаған.',
  'person.loading': 'Профиль жүктелуде',
  'person.edit': 'Профильді өзгерту',
  'person.cancel': 'Болдырмау',
  'person.yourProfile': 'Сіздің профиліңіз',
  'person.aimingAt': 'Қайда түседі',
  'person.aimingHint': 'Талапкердің өз сөзінен. Университет сайтымен салыстырылмаған.',
  'person.city': 'Қала',
  'person.major': 'Мамандық',
  'person.universities': 'Университеттер',
  'person.notStated': 'көрсетілмеген',
  'person.yourPosts': 'Сіздің жазбаларыңыз',
  'person.noPostsYou': 'Сіз әлі ештеңе жазбадыңыз',
  'person.noPostsYouHint': 'Қауымдастықта жазғаныңыздың бәрі осында шығады.',
  'person.noPostsThem': 'Әзірге жазба жоқ',
  'person.postsBy': 'Жазбалар',

  'person.formStatus': 'Қай кезеңдесіз',
  'person.formStatusNone': 'Айтпағанды жөн көремін',
  'person.formStatusHint':
    'Таңдамасаңыз, профильде ойдан шығарылған мәртебе емес, «көрсетілмеген» деп тұрады.',
  'person.formCity': 'Түсетін қалаңыз',
  'person.formMajor': 'Мамандық',
  'person.formUniversities': 'Мақсат еткен университеттер',
  'person.formUniversitiesHint': 'Үтір арқылы жазыңыз.',
  'person.formBio': 'Өзіңіз туралы',
  'person.formBioPlaceholder': 'Немен айналысасыз және сізден не сұраған жөн.',
  'person.save': 'Профильді сақтау',
  'person.saving': 'Сақталуда…',
  'person.publicWarning':
    'Мұның бәрін басқа талапкерлер көреді. Түсу бойынша ісіңізді — көрмейді.',

  'nav.messages': 'Хабарламалар',
  'nav.moderation': 'Модерация кезегі',

  'report.action': 'Шағымдану',
  'report.title': 'Модераторға шағымдану',
  'report.reason': 'Мұнда не дұрыс емес',
  'report.harassment': 'Қудалау немесе қорлау',
  'report.personal_information': 'Бөгде адамның жеке деректері',
  'report.impersonation': 'Өзін басқа адам етіп көрсетеді',
  'report.spam': 'Спам немесе жарнама',
  'report.misleading_advice': 'Университет туралы қауесет факт ретінде айтылған',
  'report.other': 'Басқа',
  'report.note': 'Модератор білуі керек нәрсе (міндетті емес)',
  'report.send': 'Шағым жіберу',
  'report.sending': 'Жіберілуде…',
  'report.cancel': 'Болдырмау',
  'report.sent': 'Шағым жіберілді. Оны адам қарайды.',
  'report.already': 'Сіз бұған бұрын шағымдансыз.',
  'report.slow':
    'Шағымды адам оқиды, сондықтан бұл бірден болмайды. Егер сізді дәл қазір мазаласа — '
    + 'бұғаттаңыз: ол лезде жұмыс істейді.',

  'block.action': 'Бұғаттау',
  'block.unblock': 'Бұғаттан шығару',
  'block.confirm': 'Осы талапкер бұғатталсын ба?',
  'block.explain':
    'Ол сізге жаза алмайды және жазбаларыңызға жауап бере алмайды, әрі екеуіңіз бір-біріңізді '
    + 'таспадан да, іздеуден де көрмейсіздер. Оған бұл айтылмайды.',
  'block.blocked': 'Бұғатталған',
  'block.list': 'Бұғатталғандар',
  'block.listEmpty': 'Сіз ешкімді бұғаттамағансыз.',

  'moderation.title': 'Модерация кезегі',
  'moderation.lede':
    'Қауымдастықтың шағымдары, ескісі жоғарыда. Жою мазмұнды бәрінен алып тастайды және оны '
    + 'кім жасағанын жазып қояды.',
  'moderation.open': 'Ашық',
  'moderation.actioned': 'Жойылған',
  'moderation.dismissed': 'Қабылданбаған',
  'moderation.empty': 'Күтіп тұрған ештеңе жоқ',
  'moderation.emptyHint': 'Шағымдар түскен сайын осында шығады.',
  'moderation.loading': 'Кезек жүктелуде',
  'moderation.reportedBy': 'Шағымданған',
  'moderation.about': 'Не туралы',
  'moderation.excerpt': 'Шағым түскен кездегі мәтін',
  'moderation.gone': 'Бұл мазмұн әлдеқашан жойылған.',
  'moderation.remove': 'Жою',
  'moderation.dismiss': 'Қалдыру',
  'moderation.resolutionNote': 'Себебі (атыңызбен бірге жазылады)',
  'moderation.resolvedBy': 'Шешім қабылдаған',
  'moderation.subjectPost': 'жазба',
  'moderation.subjectReply': 'жауап',
  'moderation.subjectMessage': 'жеке хабарлама',
  'moderation.subjectProfile': 'профиль',
  'messages.title': 'Хабарламалар',
  'messages.lede':
    'Жеке хат алмасу. Оны бөгде адам көрмейді, әрі мұнда жазылған нәрсе таспаға да, '
    + 'профиліңізге де түспейді.',
  'messages.loading': 'Хат алмасу жүктелуде',
  'messages.opening': 'Әңгіме ашылып жатыр',
  'messages.empty': 'Әзірге әңгіме жоқ',
  'messages.emptyHint':
    'Таспада біреуге жауап беріңіз немесе профильді ашып жазыңыз. Сізге кім бірінші жаза '
    + 'алатынын өзіңіз шешесіз — баптау профиліңізде.',
  'messages.emptyThread': 'Мұнда әзірге бос',
  'messages.emptyThreadHint': 'Алғашқы хабарламаны жазыңыз.',
  'messages.placeholder': 'Хабарлама жазыңыз',
  'messages.send': 'Жіберу',
  'messages.back': 'Барлық әңгімелер',
  'messages.write': 'Хабарлама жазу',
  'messages.closed': 'Бұл талапкер хабарлама қабылдамайды.',
  'messages.needsThread':
    'Бұл талапкер тек өзі жауап берген адамдардан хабарлама қабылдайды. Оның жазбасына жауап '
    + 'беріңіз немесе ол жауап бере алатын сұрақ қойыңыз.',

  'person.avatar': 'Сіздің фотоңыз',
  'person.avatarChoose': 'Фото таңдау',
  'person.avatarRemove': 'Жою',
  'person.avatarUploading': 'Жүктелуде…',
  'person.avatarHint':
    'JPEG немесе PNG, 512 КБ дейін. Түсірілген жер сақтауға дейін өшіріледі, ал фотоны '
    + 'профиліңізді көре алатын әрбір талапкер көреді.',

  'person.formDmPolicy': 'Сізге кім бірінші жаза алады',
  'person.formDmAnyone': 'Қауымдастықтағы кез келген адам',
  'person.formDmThreads': 'Тек мен жауап бергендер немесе маған жауап бергендер',
  'person.formDmNobody': 'Ешкім — кіріс жабық',
  'person.formDmHint':
    'Бұл ереже тек алғашқы хабарламаға қатысты. Сіз хат алысып жүрген адам таңдауыңызға '
    + 'қарамастан жаза алады.',

  'leave.title': 'Қауымдастықтан шығу',
  'leave.hint':
    'Аккаунт пен зерттеуіңіз қалады. Профиль, жазбалар және жауаптар жойылады, сіз іздеуден '
    + 'жоғаласыз.',
  'leave.confirm': 'Профиль мен жазғаныңыздың бәрі жойылсын ба?',
  'leave.confirmSuffix': 'Мұны қайтару мүмкін емес.',
  'leave.yes': 'Иә, жою',
  'leave.keep': 'Профильді қалдыру',
};

const DICTIONARIES: Record<Locale, Partial<Record<MessageKey, string>>> = {
  en: EN,
  ru: RU,
  kk: KK,
};

function detect(): Locale {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored === 'en' || stored === 'ru' || stored === 'kk') return stored;
  } catch {
    /* a browser blocking storage should not decide the language */
  }
  const tag = (navigator.language || 'en').toLowerCase();
  if (tag.startsWith('kk')) return 'kk';
  if (tag.startsWith('ru')) return 'ru';
  return 'en';
}

let current: Locale = detect();
const listeners = new Set<() => void>();

export function getLocale(): Locale {
  return current;
}

export function setLocale(locale: Locale): void {
  current = locale;
  try {
    window.localStorage.setItem(STORAGE_KEY, locale);
  } catch {
    /* the choice still holds for this session */
  }
  document.documentElement.lang = locale;
  listeners.forEach((notify) => notify());
}

export function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** The message for this key, in the current locale, falling back to English. */
export function t(key: MessageKey): string {
  return DICTIONARIES[current][key] ?? EN[key];
}

/** Which keys a locale has not settled yet — read by the glossary test. */
export function untranslated(locale: Locale): MessageKey[] {
  const dictionary = DICTIONARIES[locale];
  return (Object.keys(EN) as MessageKey[]).filter((key) => dictionary[key] === undefined);
}
