/**
 * Home (concept «Пропуск»): one question - what still waits for an answer -
 * the applicant's passes, and the next deadline on them. Every number is
 * counted from the results; none of them is a chance.
 */

import { fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { HomeScreen } from './HomeScreen';
import type { ProgramResult } from '@/types';

let results: ProgramResult[] = [];
let savedProfile: unknown = null;
let run: unknown = null;

vi.mock('@/lib/store', () => ({
  useStore: () => ({ results, savedProfile, run, hydrated: true, capabilities: { demo_mode: true } }),
}));

function programme(id: string, country: string, decision: string, deadline: string | null): ProgramResult {
  return {
    id, university: `University ${id}`, program: 'BSc Computing', city: `City ${id}`, country,
    user_decision: decision, eligibility: 'MET', admissions_fit: 'PLAUSIBLE_FIT',
    best_funding_classification: 'NO_AWARD_FOUND', admission_deadline: deadline, deadline_passed: false,
    scholarships: [], source_urls: ['fixture://demo/page'], last_verified: '2026-10-05T10:00:00Z',
    user_notes: '', user_decision_reason: '',
    funding_gap: {
      computable: true, gap: { amount: 1847.82, currency: 'USD', academic_year: '2026/27', is_estimate: false },
      confirmed_aid: { amount: 30815, currency: 'USD' },
    },
  } as unknown as ProgramResult;
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] });
  vi.setSystemTime(new Date(2026, 9, 5, 12));
  savedProfile = { id: 'p', display_name: 'A', preferences: { preferred_countries: ['Belgium'] } };
  run = { job_status: 'succeeded', claims_recorded: 12 };
});

afterEach(() => {
  vi.useRealTimers();
});

describe('the question at the top', () => {
  it('counts the programmes still waiting for an answer, and opens deciding', () => {
    results = [
      programme('a', 'Netherlands', 'undecided', null),
      programme('b', 'Japan', 'undecided', null),
      programme('c', 'Belgium', 'approved', '2026-12-01'),
    ];
    const onDecide = vi.fn();
    render(<HomeScreen onNavigate={() => {}} onDecide={onDecide} />);
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('2 programmeswait for your answer');
    fireEvent.click(screen.getByTestId('home-cta'));
    expect(onDecide).toHaveBeenCalledOnce();
  });

  it('starts with the profile when there is none, and shows no passes', () => {
    savedProfile = null;
    results = [];
    const onNavigate = vi.fn();
    render(<HomeScreen onNavigate={onNavigate} />);
    expect(screen.getByTestId('home-cta')).toHaveTextContent('Start with your profile');
    fireEvent.click(screen.getByTestId('home-cta'));
    expect(onNavigate).toHaveBeenCalledWith('profile');
    expect(screen.queryByText('Your passes')).toBeNull();
  });

  it('goes to the plan once every programme has an answer', () => {
    results = [programme('c', 'Belgium', 'approved', '2026-12-01')];
    render(<HomeScreen onNavigate={() => {}} />);
    expect(screen.getByTestId('home-cta')).toHaveTextContent('Open your plan');
  });
});

describe('passes and the next deadline', () => {
  it('shows kept and maybe programmes as passes in their country colour', () => {
    results = [
      programme('a', 'Netherlands', 'undecided', null),
      programme('c', 'Belgium', 'approved', '2026-12-01'),
      programme('d', 'Japan', 'maybe', '2027-02-01'),
    ];
    render(<HomeScreen onNavigate={() => {}} />);
    expect(screen.getByText('1 kept · 1 maybe')).toBeInTheDocument();
    // Belgium is the applicant's pick, so it takes the first colour.
    expect(screen.getByTestId('home-pass-c')).toHaveAttribute('data-pass', '1');
    expect(screen.getByTestId('home-pass-c')).toHaveTextContent('Belgium · kept');
    expect(screen.getByTestId('home-pass-c')).toHaveTextContent('1,848USD a year, if awarded');
    expect(screen.queryByTestId('home-pass-a')).toBeNull();
  });

  it('names the next deadline with its days, its standing and its source', () => {
    results = [programme('c', 'Belgium', 'approved', '2026-12-01')];
    render(<HomeScreen onNavigate={() => {}} />);
    const ticket = screen.getByTestId('ticket-c');
    expect(ticket).toHaveTextContent('in 57 days');
    expect(ticket).toHaveTextContent('Requirements met');
    expect(ticket).toHaveTextContent('demo fixture');
    expect(ticket).toHaveTextContent('Deadline 1 December 2026.');
  });

  it('never words a count as a chance', () => {
    results = [programme('a', 'Netherlands', 'undecided', null), programme('c', 'Belgium', 'approved', '2026-12-01')];
    const { container } = render(<HomeScreen onNavigate={() => {}} />);
    expect(container.textContent).not.toMatch(/chance|probab|%/i);
  });
});
