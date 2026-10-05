/**
 * A programme as a pass (concept «Пропуск», palette E).
 *
 * The pass wears its country's colour - never a verdict - and reads like a
 * ticket: the country and the city on top, the price a year on the right,
 * a tear line, then the university and the programme. Whatever the screen
 * adds (the three answers, the buttons, a route) goes under the tear line as
 * children. The price is the one the run computed after the grants it found;
 * when there is none, the pass says so instead of showing a number.
 */

import type { ReactNode } from 'react';
import {
  STATUS_LABEL, admissionsFitTone, eligibilityTone, fundingClassTone, humanize,
} from '@/lib/format';
import type { PassColour } from '@/lib/passColour';
import type { ProgramResult } from '@/types';

const DECISION_WORD: Partial<Record<ProgramResult['user_decision'], string>> = {
  approved: 'kept',
  maybe: 'maybe',
  rejected: 'not for me',
};

/** "1,848" and "USD a year, if awarded"; or no amount, and why. */
export function passPrice(result: ProgramResult): { amount: string | null; unit: string } {
  const gap = result.funding_gap;
  if (!gap?.computable || !gap.gap) return { amount: null, unit: 'no official cost found' };
  const awarded = (gap.confirmed_aid?.amount ?? 0) > 0;
  const est = gap.gap.is_estimate ? ', estimate' : '';
  return {
    amount: Math.round(gap.gap.amount).toLocaleString('en-US'),
    unit: `${gap.gap.currency} a year${awarded ? ', if awarded' : ''}${est}`,
  };
}

export function passStyle(colour: PassColour | undefined): Record<string, string> | undefined {
  return colour ? { ['--pass' as string]: `var(--pass-${colour.slot})` } : undefined;
}

export function Pass({
  result, colour, tag, title, heading = 'h3', className = '', children, testId,
}: {
  result: ProgramResult;
  colour: PassColour | undefined;
  /** After the country in the eyebrow; the applicant's answer when omitted. */
  tag?: string;
  /** The city by default; a button when the pass opens something. */
  title?: ReactNode;
  heading?: 'h2' | 'h3';
  className?: string;
  children?: ReactNode;
  testId?: string;
}) {
  const price = passPrice(result);
  const word = tag ?? DECISION_WORD[result.user_decision];
  const Heading = heading;
  return (
    <article
      className={`pass${colour?.pattern ? ' pass--pattern' : ''}${className ? ` ${className}` : ''}`}
      style={passStyle(colour)}
      data-pass={colour?.slot}
      data-testid={testId}
    >
      <div className="pass__top">
        <div className="pass__where">
          <p className="pass__country">{result.country}{word ? ` · ${word}` : ''}</p>
          <Heading className="pass__city">{title ?? (result.city || result.university)}</Heading>
        </div>
        <p className="pass__price">
          {price.amount ? <strong>{price.amount}</strong> : <strong className="pass__price--none">Cost not computed</strong>}
          <span>{price.unit}</span>
        </p>
      </div>
      <p className="pass__line">{result.university} · {result.program}</p>
      {children}
    </article>
  );
}

/**
 * The three answers, small enough for a pass: one mark each, in the tone of
 * its own status, and their words for a screen reader. Three marks, never
 * one score.
 */
export function PassAnswers({ result }: { result: ProgramResult }) {
  const word = (s: string) => STATUS_LABEL[s] ?? humanize(s);
  const marks = [
    { key: 'requirements', tone: eligibilityTone[result.eligibility], text: word(result.eligibility) },
    { key: 'profile', tone: admissionsFitTone[result.admissions_fit], text: word(result.admissions_fit) },
    { key: 'money', tone: fundingClassTone[result.best_funding_classification], text: word(result.best_funding_classification) },
  ];
  return (
    <p className="pass__answers">
      <span className="pass__marks" aria-hidden="true">
        {marks.map((m) => <i key={m.key} className={`tone-${m.tone ?? 'neutral'}`} />)}
      </span>
      <span aria-hidden="true">requirements · profile · money</span>
      <span className="visually-hidden">
        {marks.map((m) => `${m.key}: ${m.text}`).join('; ')}
      </span>
    </p>
  );
}
