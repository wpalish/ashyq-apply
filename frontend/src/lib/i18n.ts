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
  'nav.group.prepare': 'Prepare',
  'nav.group.research': 'Research',
  'nav.group.decide': 'Decide',
  'nav.group.community': 'Community',
  'nav.group.about': 'About',

  'nav.profile': 'Applicant profile',
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
    'Published criteria only. ASHYQ Apply never predicts admission or funding outcomes.',

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
  'nav.group.prepare': 'Подготовка',
  'nav.group.decide': 'Решение',
  'nav.group.community': 'Сообщество',
  'nav.group.about': 'О сервисе',

  'nav.profile': 'Профиль абитуриента',
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
  'nav.group.prepare': 'Дайындық',
  'nav.group.decide': 'Шешім',
  'nav.group.community': 'Қауымдастық',
  'nav.group.about': 'Сервис туралы',

  'nav.profile': 'Талапкер профилі',
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
