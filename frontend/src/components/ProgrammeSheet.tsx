/**
 * A programme opened (concept «Пропуск», the "detail" screen): the pass grown
 * into a page. Its head wears the country's colour and carries the route
 * home and the applicant's answer; under it, on white, the money line by
 * line, the three answers and the rest of the detail.
 *
 * On a phone it is the screen, with the way back to Find at the top; on a
 * desk it is a panel at the right of the list, which stays in view.
 */

import { useEffect, useRef, type ReactNode } from 'react';
import { X } from '@phosphor-icons/react';
import { PassRoute } from '@/components/PassRoute';
import { passStyle } from '@/components/Pass';
import type { PassColour } from '@/lib/passColour';
import type { ProgramResult } from '@/types';

/** "Fall 2027", when the profile says both. */
export function intakeWords(profile: unknown): string {
  const c = (profile as { context?: { intake_term?: unknown; intake_year?: unknown } } | null)?.context;
  const term = typeof c?.intake_term === 'string' ? c.intake_term : '';
  const year = typeof c?.intake_year === 'number' ? c.intake_year : null;
  return term && year ? `${term.charAt(0).toUpperCase()}${term.slice(1)} ${year}` : '';
}

export function ProgrammeSheet({
  result, colour, side, intake, home, actions, children, onClose,
}: {
  result: ProgramResult;
  colour: PassColour | undefined;
  /** A panel beside the list (desk), rather than the whole screen (phone). */
  side: boolean;
  intake: string;
  /** Home's city, for the route; nothing is drawn without it. */
  home: string | null;
  /** The answer and the other things to do with this programme. */
  actions: ReactNode;
  /** The detail under the head: the money, the three answers, the tabs. */
  children: ReactNode;
  onClose: () => void;
}) {
  const title = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    title.current?.focus();
  }, [result.id]);
  useEffect(() => {
    if (!side) return undefined;
    const escape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', escape);
    return () => document.removeEventListener('keydown', escape);
  }, [side, onClose]);

  const kicker = [result.country, intake].filter(Boolean).join(' · ');
  return (
    <section
      className={`psheet${side ? ' psheet--side' : ''}${colour?.pattern ? ' pass--pattern' : ''}`}
      style={passStyle(colour)}
      aria-labelledby="psheet-title"
      data-testid={`sheet-${result.id}`}
    >
      <header className="psheet__head">
        <button type="button" className="psheet__close" onClick={onClose} data-testid="sheet-close">
          {side
            ? <><X size={20} weight="bold" aria-hidden="true" /><span className="visually-hidden">Close</span></>
            : <>← Find</>}
        </button>
        <p className="psheet__kicker">{kicker}</p>
        <h2 className="psheet__city" id="psheet-title" ref={title} tabIndex={-1}>{result.city || result.university}</h2>
        <p className="psheet__line">{result.university} · {result.program}</p>
        <PassRoute city={result.city} home={home} />
        <div className="psheet__actions">{actions}</div>
      </header>
      <div className="psheet__body">{children}</div>
    </section>
  );
}
