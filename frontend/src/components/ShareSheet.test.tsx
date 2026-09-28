/**
 * The share sheet: the cards it offers for what it was opened on, the
 * privacy switches and their defaults, and a modal that gives the focus back.
 */

import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { ShareSheet } from './ShareSheet';
import type { ProgramResult } from '@/types';

const profile = {
  display_name: 'Aruzhan Sadykova',
  context: { country_of_residence: 'Kazakhstan', intake_year: 2027 },
};

function result(eligibility = 'MET'): ProgramResult {
  return {
    id: 'tokyo', university: 'University of Tokyo', program: 'PEAK', intake: 'fall 2027',
    city: 'Tokyo', country: 'Japan', eligibility, admission_deadline: '2026-12-01', deadline_passed: false,
    source_urls: ['https://www.u-tokyo.ac.jp/peak'], last_verified: '2026-09-14T10:00:00Z',
    best_funding_classification: 'FULL_TUITION', scholarships: [], costs: { items: {} },
    funding_gap: { computable: true, gap: { amount: 1986, currency: 'USD' } },
    requirement_checks: [{ requirement: 'IELTS overall', published_value: 6.5, applicant_value: 7, status: 'MET' }],
  } as unknown as ProgramResult;
}

describe('the share sheet', () => {
  it('offers only the map when opened on the whole search', () => {
    render(<ShareSheet results={[result()]} profile={profile} demo={false} onClose={() => {}} />);
    expect(screen.getByTestId('share-kind-map')).toBeChecked();
    expect(screen.queryByTestId('share-kind-route')).toBeNull();
    expect(screen.getByRole('heading', { name: 'Share a story' })).toHaveFocus();
  });

  it('offers the route and "requirements met" on a programme that meets them', () => {
    render(<ShareSheet results={[result()]} result={result()} profile={profile} demo={false} onClose={() => {}} />);
    expect(screen.getByTestId('share-kind-route')).toBeChecked();
    expect(screen.getByTestId('share-kind-requirements')).toBeInTheDocument();
  });

  it('says why "requirements met" is missing on a programme that does not meet them', () => {
    render(<ShareSheet results={[result('PENDING')]} result={result('PENDING')} profile={profile} demo={false} onClose={() => {}} />);
    expect(screen.queryByTestId('share-kind-requirements')).toBeNull();
    expect(screen.getByText(/appears when every requirement checked/)).toBeInTheDocument();
  });

  it('starts with the name, the price and the scores off, and names the word the name would add', () => {
    render(<ShareSheet results={[result()]} result={result()} profile={profile} demo={false} onClose={() => {}} />);
    expect(screen.getByTestId('share-name')).not.toBeChecked();
    expect(screen.getByText('adds "Aruzhan", the first word of this case\'s name')).toBeInTheDocument();
    expect(screen.getByTestId('share-price')).not.toBeChecked();
    const card = screen.getByTestId('share-canvas');
    expect(card.getAttribute('aria-label')).not.toContain('Aruzhan');
    expect(card.getAttribute('aria-label')).not.toContain('1,986');

    fireEvent.click(screen.getByTestId('share-price'));
    expect(card.getAttribute('aria-label')).toContain('1,986 USD a year left to pay, if awarded');
    fireEvent.click(screen.getByTestId('share-name'));
    expect(card.getAttribute('aria-label')).toContain('Aruzhan · 2027');
    expect(card.getAttribute('aria-label')).not.toContain('Sadykova');

    fireEvent.click(screen.getByTestId('share-kind-requirements'));
    expect(screen.getByTestId('share-scores')).not.toBeChecked();
    expect(card.getAttribute('aria-label')).not.toContain('mine 7');
    fireEvent.click(screen.getByTestId('share-scores'));
    expect(card.getAttribute('aria-label')).toContain('minimum 6.5 · mine 7');
  });

  it('has no name to offer when the case label is a placeholder', () => {
    render(<ShareSheet results={[result()]} profile={{ ...profile, display_name: 'Demo Applicant (synthetic)' }} demo onClose={() => {}} />);
    expect(screen.getByTestId('share-name')).toBeDisabled();
    expect(screen.getByText("no name in this case's label")).toBeInTheDocument();
  });

  it('closes on Escape and gives the focus back to what opened it', () => {
    const opener = document.createElement('button');
    document.body.appendChild(opener);
    opener.focus();
    const onClose = vi.fn();
    const { unmount } = render(<ShareSheet results={[result()]} profile={profile} demo={false} onClose={onClose} />);
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(onClose).toHaveBeenCalled();
    unmount();
    expect(opener).toHaveFocus();
    opener.remove();
  });

  it('says that nothing is posted and what is never on a card', () => {
    render(<ShareSheet results={[result()]} profile={profile} demo={false} onClose={() => {}} />);
    expect(screen.getByText(/school, city and documents are never on a card, and a name only when you add it/)).toBeInTheDocument();
    expect(screen.getByText(/nothing is posted until you share it/)).toBeInTheDocument();
  });
});
