/**
 * The plan: the next documents to start across the kept list, ticked here or
 * on the documents screen alike.
 */

import { fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ApprovedScreen } from './ApprovedScreen';
import type { ProgramResult } from '@/types';

let results: ProgramResult[] = [];

vi.mock('@/lib/store', () => ({
  useStore: () => ({ results, run: null, collectDocuments: vi.fn(), decide: vi.fn() }),
}));

function programme(id: string, decision: string, withList: boolean): ProgramResult {
  const doc = (name: string, lead: number) => ({ name, lead_time_days: lead, deadline: null });
  return {
    id, university: `University ${id}`, program: 'BSc', city: id, country: 'X', user_decision: decision,
    eligibility: 'MET', admissions_fit: 'PLAUSIBLE_FIT', best_funding_classification: 'NO_AWARD_FOUND',
    admission_deadline: '2026-11-01', deadline_passed: false, scholarships: [], source_urls: [],
    user_notes: '', user_decision_reason: '', funding_gap: null,
    checklist: withList ? {
      recommender_actions: [doc('Academic reference', 30)], school_actions: [doc('Transcript', 21)],
      certification_actions: [], applicant_actions: [doc('CV', 5), doc('Passport copy', 1)],
    } : null,
  } as unknown as ProgramResult;
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] });
  vi.setSystemTime(new Date(2026, 8, 25, 12));
  window.localStorage.removeItem('ashyq.docsDone');
});

afterEach(() => {
  vi.useRealTimers();
});

describe('next to start', () => {
  it('asks for a documents collection before it can say anything', () => {
    results = [programme('a', 'approved', false)];
    render(<ApprovedScreen onCollect={() => {}} />);
    expect(screen.getByTestId('next-to-start')).toHaveTextContent('Collect documents for what you keep');
  });

  it('shows the three earliest starts, marks this week, and counts the rest', () => {
    results = [programme('a', 'approved', true), programme('b', 'undecided', true)];
    render(<ApprovedScreen onCollect={() => {}} />);
    const panel = screen.getByTestId('next-to-start');
    // 1 November minus 30 days is 2 October: within seven days of 25 September.
    expect(panel).toHaveTextContent('Academic reference');
    expect(panel).toHaveTextContent('this week');
    expect(panel).toHaveTextContent('and 1 more on the documents screen');
    expect(panel).not.toHaveTextContent('University b');
  });

  it('keeps a ticked document in place so a slip can be undone, and shares the tick', () => {
    results = [programme('a', 'approved', true)];
    render(<ApprovedScreen onCollect={() => {}} />);
    const box = screen.getByLabelText('Academic reference, University a: ready');
    fireEvent.click(box);
    expect(box).toBeChecked();
    expect(screen.getByTestId('next-to-start')).toHaveTextContent('Academic reference');
    expect(JSON.parse(window.localStorage.getItem('ashyq.docsDone') ?? '{}')).toEqual({ 'a::Academic reference': true });
    fireEvent.click(box);
    expect(box).not.toBeChecked();
  });

  it('leaves out what was ticked before this visit', () => {
    window.localStorage.setItem('ashyq.docsDone', JSON.stringify({ 'a::Academic reference': true }));
    results = [programme('a', 'approved', true)];
    render(<ApprovedScreen onCollect={() => {}} />);
    expect(screen.getByTestId('next-to-start')).not.toHaveTextContent('Academic reference');
  });
});
