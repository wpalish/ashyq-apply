/**
 * React's view of the locale.
 *
 * Kept apart from `i18n.ts` so the dictionary can be read and tested without
 * React, and so a screen that only needs `t()` does not have to care that the
 * locale lives outside the component tree.
 */

import { Fragment, createElement, useSyncExternalStore, type ReactNode } from 'react';
import {
  getLocale, setLocale, subscribe, t, tf, tn, tOr, type Locale, type MessageKey,
} from '@/lib/i18n';

export function useTranslation(): {
  t: (key: MessageKey) => string;
  tf: typeof tf;
  tn: typeof tn;
  tOr: typeof tOr;
  locale: Locale;
  setLocale: (locale: Locale) => void;
} {
  const locale = useSyncExternalStore(subscribe, getLocale, getLocale);
  return { t, tf, tn, tOr, locale, setLocale };
}

/**
 * A translated sentence with elements in it: `{name}` placeholders are
 * replaced by the given nodes (a `<strong>`, a `<code>`), so the word order
 * stays the translator's rather than being stitched together in English order.
 */
export function rich(template: string, nodes: Record<string, ReactNode>): ReactNode {
  const parts = template.split(/\{(\w+)\}/g);
  return parts.map((part, i) =>
    createElement(Fragment, { key: i }, i % 2 === 1 ? (nodes[part] ?? `{${part}}`) : part),
  );
}
