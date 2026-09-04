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
