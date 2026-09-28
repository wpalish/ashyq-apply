/**
 * The start screen writes the same draft as the profile and starts the same
 * run, and a comma can be typed into its lists.
 */

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { StartScreen } from './StartScreen';

let draft: Record<string, unknown>;
let validation: { can_proceed: boolean; summary: string } | null;
const startRun = vi.fn().mockResolvedValue(undefined);
const setProfileDraft = vi.fn((update: (d: Record<string, unknown>) => Record<string, unknown>) => {
  draft = update(draft);
});

vi.mock('@/lib/store', () => ({
  useStore: () => ({
    profileDraft: draft,
    setProfileDraft,
    startRun,
    loading: false,
    capabilities: { demo_mode: true, currency: { supported: ['USD', 'EUR'] } },
    validation,
    run: null,
    results: [],
  }),
}));

const noop = () => {};
const renderStart = (onStarted = noop) => render(
  <StartScreen onStarted={onStarted} onOpenProfile={noop} onOpenPreferences={noop} onOpenResults={noop} />,
);

beforeEach(() => {
  draft = {
    display_name: 'New applicant',
    context: { intended_fields: ['computer science'] },
    preferences: { preferred_countries: [] },
    funding: { max_annual_budget: 6000, budget_currency: 'USD' },
  };
  validation = { can_proceed: true, summary: '' };
  startRun.mockClear();
  setProfileDraft.mockClear();
});

describe('the start screen', () => {
  it('shows the three fields from the draft', () => {
    renderStart();
    expect(screen.getByTestId('start-fields')).toHaveValue('computer science');
    expect(screen.getByTestId('start-countries')).toHaveValue('');
    expect(screen.getByTestId('start-countries')).toHaveAttribute('placeholder', 'Anywhere');
    expect(screen.getByTestId('start-budget')).toHaveValue(6000);
  });

  it('keeps the comma while a second item is typed', () => {
    renderStart();
    const countries = screen.getByTestId('start-countries');
    fireEvent.change(countries, { target: { value: 'Netherlands, ' } });
    expect(countries).toHaveValue('Netherlands, ');
    fireEvent.change(countries, { target: { value: 'Netherlands, Japan' } });
    expect((draft.preferences as Record<string, unknown>).preferred_countries).toEqual(['Netherlands', 'Japan']);
  });

  it('starts the same run as Start research, in demo mode', async () => {
    const onStarted = vi.fn();
    renderStart(onStarted);
    fireEvent.click(screen.getByTestId('start-search'));
    await waitFor(() => expect(onStarted).toHaveBeenCalled());
    expect(startRun).toHaveBeenCalledWith(true);
  });

  it('says why it cannot start, and does not', () => {
    validation = { can_proceed: false, summary: 'Add at least one field of study.' };
    renderStart();
    expect(screen.getByTestId('start-search')).toBeDisabled();
    expect(screen.getByTestId('start-blocked')).toHaveTextContent('Add at least one field of study.');
  });

  it('labels demo data and never promises an outcome', () => {
    renderStart();
    const text = document.body.textContent ?? '';
    expect(text).toMatch(/Demo data/);
    expect(text).not.toMatch(/%|chance|probab/i);
  });
});
