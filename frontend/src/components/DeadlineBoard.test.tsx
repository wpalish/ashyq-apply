/**
 * The departures board: the nearest deadline on tiles, every one after it,
 * and a last column that says what the requirements ask - never a chance.
 */

import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { DeadlineBoard } from './DeadlineBoard';
import { planDeadlines } from '@/lib/deadlines';
import type { ProgramResult } from '@/types';

const today = new Date(2026, 8, 25);

function row(overrides: Partial<ProgramResult>): ProgramResult {
  return {
    id: 'r', university: 'University of Tokyo', program: 'PEAK Environmental Sciences',
    city: 'Tokyo', country: 'Japan', eligibility: 'MET', user_decision: 'approved',
    admission_deadline: '2026-12-01', deadline_passed: false,
    source_urls: ['https://www.u-tokyo.ac.jp/peak'], last_verified: '2026-09-14T10:00:00Z',
    scholarships: [],
    ...overrides,
  } as unknown as ProgramResult;
}

const list = () => planDeadlines([
  row({ id: 'tokyo' }),
  row({ id: 'groningen', university: 'University of Groningen', program: 'BSc Computing Science', city: 'Groningen', eligibility: 'PENDING', admission_deadline: '2027-05-01', user_decision: 'maybe', source_urls: ['https://www.rug.nl/x'] }),
  row({ id: 'leuven', university: 'KU Leuven', city: 'Leuven', eligibility: 'NEEDS_OFFICIAL_CLARIFICATION', admission_deadline: '2026-03-01' }),
  row({ id: 'nus', university: 'NUS', city: 'Singapore', admission_deadline: null }),
], today);

describe('the deadline board', () => {
  it('puts the nearest upcoming deadline on the tiles with the days left', () => {
    render(<DeadlineBoard planned={list()} />);
    const next = screen.getByTestId('board-next');
    expect(next).toHaveTextContent('1 December 2026, 67 days left: University of Tokyo');
    expect(next.querySelectorAll('.flaps__tile').length).toBeGreaterThan(4);
  });

  it('lists every deadline in order, a passed one marked and a missing one not guessed', () => {
    render(<DeadlineBoard planned={list()} />);
    const rows = within(screen.getByRole('list', { name: 'Every deadline on your list' }))
      .getAllByRole('listitem').filter((li) => li.dataset.testid);
    expect(rows.map((li) => li.dataset.testid)).toEqual([
      'board-row-tokyo', 'board-row-groningen', 'board-row-leuven', 'board-row-nus',
    ]);
    expect(screen.getByTestId('board-row-leuven')).toHaveTextContent('passed');
    expect(screen.getByTestId('board-row-nus')).toHaveTextContent('not found');
    expect(screen.getByTestId('board-row-groningen')).toHaveTextContent('maybe');
  });

  it('says what the requirements ask, in one word per row', () => {
    render(<DeadlineBoard planned={list()} />);
    expect(screen.getByTestId('board-row-tokyo')).toHaveTextContent('Met');
    expect(screen.getByTestId('board-row-groningen')).toHaveTextContent('Action needed');
    expect(screen.getByTestId('board-row-leuven')).toHaveTextContent('Ask the university');
  });

  it('names where the dates come from and when they were read', () => {
    render(<DeadlineBoard planned={list()} />);
    const foot = screen.getByText(/Dates as each university publishes them/);
    expect(foot).toHaveTextContent('u-tokyo.ac.jp · rug.nl');
    expect(foot).toHaveTextContent('14 September 2026');
  });

  it('never states a chance', () => {
    const { container } = render(<DeadlineBoard planned={list()} />);
    expect(container.textContent).not.toMatch(/%|chance|probab/i);
  });

  it('explains an empty plan instead of showing an empty board', () => {
    render(<DeadlineBoard planned={[]} />);
    expect(screen.getByTestId('board-next')).toHaveTextContent('Nothing on your plan yet');
    expect(screen.queryByRole('list')).toBeNull();
  });

  it('says so when no deadline is still ahead', () => {
    render(<DeadlineBoard planned={planDeadlines([row({ admission_deadline: '2026-01-01' })], today)} />);
    expect(screen.getByTestId('board-next')).toHaveTextContent('No upcoming deadline on your list');
  });

  it('shows a grant deadline as its own row, flagged when it comes before the admission date', () => {
    const planned = planDeadlines([row({
      id: 'groningen', university: 'University of Groningen', city: 'Groningen', admission_deadline: '2027-05-01',
      scholarships: [{
        id: 'talent', name: 'Groningen Talent Grant', application_mode: 'separate', applicant_eligible: 'unknown',
        deadline: '2027-02-01', deadline_passed: false, requires_extra_essays: true,
        eligibility_checks: [{ requirement: 'GPA', status: 'MET' }],
        source_urls: ['https://www.rug.nl/talent-grant'], last_verified: '2026-09-10T10:00:00Z',
      }],
    } as unknown as Partial<ProgramResult>)], today);
    render(<DeadlineBoard planned={planned} />);
    const grant = screen.getByTestId('board-row-groningen:talent');
    expect(grant).toHaveAttribute('data-kind', 'award');
    expect(grant).toHaveTextContent('Groningen Talent Grant');
    expect(grant).toHaveTextContent('Grant application · essays · University of Groningen');
    expect(grant).toHaveTextContent('before the admission deadline');
    expect(screen.getByTestId('board-next')).toHaveTextContent('Due before the admission deadline');
    // The award's own page and read date, not the programme's.
    const foot = screen.getByText(/Dates as each university publishes them/);
    expect(foot).toHaveTextContent('rug.nl');
    expect(foot).toHaveTextContent('10 September 2026');
  });
});
