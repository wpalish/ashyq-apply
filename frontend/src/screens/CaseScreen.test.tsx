import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { CaseScreen } from './CaseScreen';
import { redesignCopy } from '@/lib/redesignCopy';
import type { Locale } from '@/lib/i18n';

let state: { hydrated: boolean; savedProfile: object | null; run: object | null; results: { user_decision: string }[]; summary: { with_open_questions: number } | null; dirty: boolean };
let locale: Locale = 'ru';
vi.mock('@/lib/store', () => ({ useStore: () => state }));
vi.mock('@/lib/useTranslation', () => ({ useTranslation: () => ({ locale }) }));
const onNavigate = vi.fn();
beforeEach(() => {
  state = { hydrated: true, savedProfile: null, run: null, results: [], summary: null, dirty: false };
  locale = 'ru'; onNavigate.mockReset();
});
describe('Case next step', () => {
  it('waits for hydration without inventing readiness', () => {
    state.hydrated = false;
    render(<CaseScreen onNavigate={onNavigate} />);
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });
  it('takes a new applicant to the profile', () => {
    render(<CaseScreen onNavigate={onNavigate} />);
    fireEvent.click(screen.getByRole('button', { name: redesignCopy.ru.edit }));
    expect(onNavigate).toHaveBeenCalledWith('profile');
  });
  it('offers preferences after saving a profile', () => {
    state.savedProfile = { id: 'p1' };
    render(<CaseScreen onNavigate={onNavigate} />);
    fireEvent.click(screen.getByRole('button', { name: redesignCopy.ru.preferences }));
    expect(onNavigate).toHaveBeenCalledWith('preferences');
  });
  it.each(['queued', 'running'])('keeps %s research visible even with partial results', (job_status) => {
    state.run = { job_status }; state.results = [{ user_decision: 'approved' }];
    render(<CaseScreen onNavigate={onNavigate} />);
    expect(screen.getByRole('heading', { name: redesignCopy.ru.working })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: redesignCopy.ru.progress }));
    expect(onNavigate).toHaveBeenCalledWith('progress');
  });
  it('prioritizes recovery over partial results', () => {
    state.run = { stage: 'failed' }; state.results = [{ user_decision: 'maybe' }];
    render(<CaseScreen onNavigate={onNavigate} />);
    expect(screen.getByRole('heading', { name: redesignCopy.ru.failed })).toBeInTheDocument();
  });
  it('opens real results and shows unknown summary as unavailable', () => {
    state.results = [{ user_decision: 'approved' }, { user_decision: 'rejected' }];
    render(<CaseScreen onNavigate={onNavigate} />);
    fireEvent.click(screen.getByRole('button', { name: redesignCopy.ru.review }));
    expect(onNavigate).toHaveBeenCalledWith('shortlist');
    expect(screen.getByText(redesignCopy.ru.unavailable)).toBeInTheDocument();
    expect(screen.getByText('2', { selector: 'dd' })).toBeInTheDocument();
    expect(screen.getByText('1', { selector: 'dd' })).toBeInTheDocument();
  });
  it.each<Locale>(['ru', 'kk', 'en'])('renders the %s dashboard', (language) => {
    locale = language;
    render(<CaseScreen onNavigate={onNavigate} />);
    expect(screen.getByRole('heading', { level: 1, name: redesignCopy[language].title })).toBeInTheDocument();
  });
});
