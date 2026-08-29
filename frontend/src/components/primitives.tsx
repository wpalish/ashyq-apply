/** Small shared building blocks. */

import type { ReactNode } from 'react';
import { STATUS_LABEL, STATUS_MEANING, humanize, type Tone } from '@/lib/format';

const TONE_CLASS: Record<Tone, string> = {
  ok: 'chip--ok',
  info: 'chip--info',
  warn: 'chip--warn',
  risk: 'chip--risk',
  demo: 'chip--demo',
  accent: 'chip--accent',
  neutral: '',
};

export function Chip({
  tone = 'neutral', children, title, mono = false,
}: { tone?: Tone; children: ReactNode; title?: string; mono?: boolean }) {
  return (
    <span className={`chip ${TONE_CLASS[tone]} ${mono ? 'chip--mono' : ''}`} title={title}>
      {children}
    </span>
  );
}

/**
 * A status chip.
 *
 * Shows the short label where one exists, and always carries the full
 * plain-English meaning as its tooltip so the abbreviation is never the only
 * thing the reader can get at.
 */
export function StatusChip({ status, tone }: { status: string; tone: Tone }) {
  return (
    <Chip tone={tone} title={STATUS_MEANING[status] ?? status}>
      {STATUS_LABEL[status] ?? humanize(status)}
    </Chip>
  );
}

/**
 * A panel, optionally foldable.
 *
 * The applicant form runs to ten panels and about forty fields, and most of
 * them are lists — subject grades, curriculum results, activities,
 * achievements — that a first-time applicant has nothing to put in. Open, they
 * bury the fields that decide whether a search can run at all.
 *
 * Folding uses <details>, so it is keyboard-operable and announced as a
 * disclosure without any state or ARIA of our own. A folded panel still says
 * what it holds, so nothing is hidden without a count.
 */
export function Panel({
  title, hint, children, sunken = false, actions,
  collapsible = false, defaultOpen = false, summary,
}: {
  title?: string; hint?: string; children: ReactNode; sunken?: boolean;
  actions?: ReactNode; collapsible?: boolean; defaultOpen?: boolean; summary?: string;
}) {
  const body = (
    <>
      {hint && <p className="panel__hint" style={{ marginBottom: 'var(--space-4)' }}>{hint}</p>}
      {children}
    </>
  );

  if (collapsible) {
    return (
      <details className={`panel panel--foldable ${sunken ? 'panel--sunken' : ''}`} open={defaultOpen}>
        <summary className="panel__summary">
          <h2 className="panel__title">{title}</h2>
          {summary && <span className="panel__count small muted">{summary}</span>}
        </summary>
        <div className="panel__body">{body}</div>
      </details>
    );
  }

  return (
    <section className={`panel ${sunken ? 'panel--sunken' : ''}`}>
      {(title || actions) && (
        <div className="row" style={{ justifyContent: 'space-between', marginBottom: hint ? 4 : 12 }}>
          {title && <h2 className="panel__title">{title}</h2>}
          {actions}
        </div>
      )}
      {body}
    </section>
  );
}

export function Notice({
  kind = 'info', children,
}: { kind?: 'info' | 'warn' | 'risk' | 'demo'; children: ReactNode }) {
  return <div className={`notice notice--${kind}`} role="note">{children}</div>;
}

export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="empty">
      <p className="empty__title">{title}</p>
      {children}
    </div>
  );
}

export function Loading({ label }: { label: string }) {
  return (
    <div className="row" role="status" aria-live="polite">
      <span className="spinner" aria-hidden="true" />
      <span className="muted small">{label}</span>
    </div>
  );
}

export function Stat({ value, label }: { value: ReactNode; label: string }) {
  return (
    <div className="stat">
      <div className="stat__value">{value}</div>
      <div className="stat__label">{label}</div>
    </div>
  );
}

export function Field({
  label, hint, children, htmlFor,
}: { label: string; hint?: string; children: ReactNode; htmlFor?: string }) {
  return (
    <div className="field">
      <label className="field__label" htmlFor={htmlFor}>{label}</label>
      {children}
      {hint && <span className="field__hint">{hint}</span>}
    </div>
  );
}

/**
 * A source link. Fixture URLs are rendered as text with a demo badge, because
 * a link that cannot be opened would imply an external source that isn't there.
 */
export function SourceLink({ url }: { url: string }) {
  if (url.startsWith('fixture://')) {
    return (
      <span className="row row--tight" style={{ display: 'inline-flex' }}>
        <code className="xs">{url}</code>
        <Chip tone="demo">demo fixture</Chip>
      </span>
    );
  }
  return (
    <a className="xs mono" href={url} target="_blank" rel="noopener noreferrer">
      {url}
    </a>
  );
}
