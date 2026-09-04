/**
 * Shared pieces of the community screens.
 *
 * The house style is an editorial dossier, so a feed here is a column of ruled
 * entries rather than a stack of cards. The one place colour is spent is the
 * avatar, and it is spent on meaning: a person's tile carries their stated
 * status, so "who is already in" is legible before you read a word. Grey is
 * "has not said", and it is never quietly upgraded to a waitlist.
 */

import { useState, type ReactNode } from 'react';
import { Chip } from '@/components/primitives';
import type { Tone } from '@/lib/format';
import type { ApplicantStatus, AuthorRef, PersonCard, PostView } from '@/types';

/** Mirrors POST_MAX_CHARS in `backend/app/domain/social.py`.
 *  `test_frontend_contract.py` fails if the two drift apart. */
export const POST_MAX_CHARS = 500;
export const BIO_MAX_CHARS = 280;

export const STATUS_LABEL: Record<string, string> = {
  accepted: 'Accepted',
  waitlist: 'On a waitlist',
};

export const STATUS_TONE: Record<string, Tone> = {
  accepted: 'ok',
  waitlist: 'warn',
};

export function statusLabel(status: ApplicantStatus | null): string {
  return (status && STATUS_LABEL[status]) || 'Status not stated';
}

export function StatusChip({ status }: { status: ApplicantStatus | null }) {
  return (
    <Chip
      tone={status ? STATUS_TONE[status] : 'neutral'}
      title={
        status
          ? 'What this applicant says about their own applications.'
          : 'This applicant has not said where they stand.'
      }
    >
      {statusLabel(status)}
    </Chip>
  );
}

/** Up to two initials, taken from the name as written. */
export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  const first = parts[0] ?? '';
  if (!first) return '?';
  const second = parts[1] ?? '';
  const letters = second ? first.charAt(0) + second.charAt(0) : first.slice(0, 2);
  return letters.toLocaleUpperCase();
}

export function Avatar({
  name, status, large = false,
}: { name: string; status: ApplicantStatus | null; large?: boolean }) {
  return (
    <span
      className={`avatar ${status ? `avatar--${status}` : 'avatar--unstated'} ${large ? 'avatar--lg' : ''}`}
      aria-hidden="true"
    >
      {initials(name)}
    </span>
  );
}

/** "4 minutes ago", and a full timestamp on hover. */
export function when(iso: string): { label: string; exact: string } {
  const at = new Date(iso);
  const exact = at.toLocaleString();
  const seconds = Math.round((at.getTime() - Date.now()) / 1000);
  const steps: [Intl.RelativeTimeFormatUnit, number][] = [
    ['second', 60], ['minute', 60], ['hour', 24], ['day', 7], ['week', 4.35], ['month', 12],
  ];
  let value = seconds;
  for (const [unit, size] of steps) {
    if (Math.abs(value) < size) {
      return { label: new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' }).format(Math.round(value), unit), exact };
    }
    value /= size;
  }
  return { label: new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' }).format(Math.round(value), 'year'), exact };
}

export function Byline({
  author, at, onOpenPerson,
}: { author: AuthorRef; at: string; onOpenPerson?: (userId: string) => void }) {
  const moment = when(at);
  return (
    <div className="byline">
      <Avatar name={author.display_name} status={author.status} />
      <div className="byline__who">
        {onOpenPerson ? (
          <button type="button" className="linkish" onClick={() => onOpenPerson(author.user_id)}>
            {author.display_name}
          </button>
        ) : (
          <span className="byline__name">{author.display_name}</span>
        )}
        <span className="byline__meta">
          <StatusChip status={author.status} />
          <time dateTime={at} title={moment.exact}>{moment.label}</time>
        </span>
      </div>
    </div>
  );
}

/** Renders `#tag` runs in a post body as marked text, leaving the rest alone. */
export function Body({ text }: { text: string }) {
  const parts = text.split(/(#[0-9A-Za-zЀ-ӿ_]{2,40})/g);
  return (
    <p className="post__body">
      {parts.map((part, index) =>
        part.startsWith('#') ? <b className="tagref" key={index}>{part}</b> : part,
      )}
    </p>
  );
}

/**
 * Take something back.
 *
 * Asks first, and names what goes. Deleting a post takes its answers with it,
 * so the question is not the same question for a post and for a reply.
 */
export function Retract({
  what, onConfirm,
}: { what: string; onConfirm: () => Promise<void> }) {
  const [asking, setAsking] = useState(false);
  const [busy, setBusy] = useState(false);

  if (!asking) {
    return (
      <button type="button" className="linkish linkish--quiet" onClick={() => setAsking(true)}>
        Delete
      </button>
    );
  }
  return (
    <span className="row row--tight">
      <span className="xs muted">Delete this {what}?</span>
      <button
        type="button"
        className="btn btn--sm btn--danger"
        disabled={busy}
        onClick={async () => {
          setBusy(true);
          try {
            await onConfirm();
          } finally {
            setBusy(false);
            setAsking(false);
          }
        }}
      >
        {busy ? 'Deleting…' : 'Yes, delete'}
      </button>
      <button type="button" className="btn btn--sm" onClick={() => setAsking(false)}>
        Keep it
      </button>
    </span>
  );
}

export function Post({
  post, onOpenPerson, onDelete, footer, children,
}: {
  post: PostView;
  onOpenPerson?: (userId: string) => void;
  /** Passed only when the reader wrote this post. */
  onDelete?: () => Promise<void>;
  footer?: ReactNode;
  children?: ReactNode;
}) {
  return (
    <article className="post" data-testid={`post-${post.id}`}>
      <Byline author={post.author} at={post.created_at} onOpenPerson={onOpenPerson} />
      <Body text={post.body} />
      {(footer || onDelete) && (
        <div className="post__foot">
          {footer}
          {onDelete && (
            <Retract
              what={post.reply_count > 0 ? 'post and its answers' : 'post'}
              onConfirm={onDelete}
            />
          )}
        </div>
      )}
      {children}
    </article>
  );
}

export function PersonTile({
  person, onOpen,
}: { person: PersonCard; onOpen: (userId: string) => void }) {
  const aims = [person.target_city, person.target_major].filter(Boolean).join(' · ');
  return (
    <button
      type="button"
      className="person"
      onClick={() => onOpen(person.user_id)}
      data-testid={`person-${person.user_id}`}
    >
      <Avatar name={person.display_name} status={person.status} large />
      <span className="person__body">
        <span className="person__name">{person.display_name}</span>
        <span className="person__aim">{aims || 'Has not said where they are aiming'}</span>
        {/* The status sits under the name rather than in a column of its own:
            a third column squeezed every name onto two lines. */}
        <span className="person__meta">
          <StatusChip status={person.status} />
          {person.universities.map((uni) => (
            <Chip key={uni} tone="neutral" mono>{uni}</Chip>
          ))}
        </span>
      </span>
    </button>
  );
}

/**
 * Writing box.
 *
 * The tags it found are shown while you type, so what gets published is never
 * a surprise — the parse happens in front of you rather than on the server.
 */
export function Composer({
  placeholder, submitLabel, max = POST_MAX_CHARS, busy, onSubmit,
}: {
  placeholder: string;
  submitLabel: string;
  max?: number;
  busy?: boolean;
  onSubmit: (body: string) => Promise<void>;
}) {
  const [text, setText] = useState('');
  const tags = Array.from(
    new Map(
      (text.match(/#[0-9A-Za-zЀ-ӿ_]{2,40}/g) ?? []).map((tag) => [
        tag.slice(1).toLocaleLowerCase().replace(/ё/g, 'е'),
        tag,
      ]),
    ).values(),
  ).slice(0, 5);

  const left = max - text.trim().length;
  const canSend = text.trim().length > 0 && left >= 0 && !busy;

  return (
    <form
      className="composer"
      onSubmit={async (event) => {
        event.preventDefault();
        if (!canSend) return;
        await onSubmit(text.trim());
        setText('');
      }}
    >
      <label className="visually-hidden" htmlFor="composer-body">{placeholder}</label>
      <textarea
        id="composer-body"
        className="composer__input"
        rows={3}
        value={text}
        placeholder={placeholder}
        onChange={(event) => setText(event.target.value)}
      />
      <div className="composer__foot">
        <div className="composer__tags">
          {tags.length > 0 && <span className="xs faint">Will be tagged</span>}
          {tags.map((tag) => (
            <Chip key={tag} tone="accent" mono>{tag}</Chip>
          ))}
        </div>
        <span className={`composer__count ${left < 0 ? 'is-over' : ''}`} aria-live="polite">
          {left < 0 ? `${-left} over` : `${left} left`}
        </span>
        <button className="btn btn--primary btn--sm" type="submit" disabled={!canSend}>
          {busy ? 'Posting…' : submitLabel}
        </button>
      </div>
    </form>
  );
}
