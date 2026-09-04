/**
 * React's view of the locale.
 *
 * Kept apart from `i18n.ts` so the dictionary can be read and tested without
 * React, and so a screen that only needs `t()` does not have to care that the
 * locale lives outside the component tree.
 */

import { useSyncExternalStore } from 'react';
import { getLocale, setLocale, subscribe, t, type Locale, type MessageKey } from '@/lib/i18n';

export function useTranslation(): {
  t: (key: MessageKey) => string;
  locale: Locale;
  setLocale: (locale: Locale) => void;
} {
  const locale = useSyncExternalStore(subscribe, getLocale, getLocale);
  return { t, locale, setLocale };
}
