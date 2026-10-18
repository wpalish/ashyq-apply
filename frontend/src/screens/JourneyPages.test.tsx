import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { CalendarScreen, ShareScreen } from './JourneyPages';
import type { ProgramResult } from '@/types';
const state = vi.hoisted(() => ({ results: [] as ProgramResult[], profile: { id: 'case-a', display_name: 'Private Name' } }));
vi.mock('@/lib/store', () => ({ useStore: () => ({ results: state.results, savedProfile: state.profile, run: null }) }));
vi.mock('@/lib/useAdmissionsToday', () => ({ useAdmissionsToday: () => ({ value: null, error: '', refresh: vi.fn() }) }));
beforeEach(() => { state.results = []; });
it('does not describe a missing deadline as an open application', () => {
  render(<CalendarScreen />);
  expect(screen.getByText('No confirmed dates yet')).toBeInTheDocument();
  expect(screen.getByText(/does not mean applications are open/)).toBeInTheDocument();
});
it('shows the exact source calendar day without inventing a timezone', () => {
  const now = new Date(); const key = `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-${String(now.getDate()).padStart(2,'0')}`;
  state.results = [{ id: 'r1', university: 'Example University', program: 'Example Programme', admission_deadline: key, scholarships: [] } as unknown as ProgramResult];
  render(<CalendarScreen />);
  expect(screen.getByText('Timezone not confirmed')).toBeInTheDocument();
  expect(screen.getByRole('button', { pressed: true })).toHaveAttribute('aria-current', 'date');
});
it('excludes applicant name by default and makes inclusion an explicit choice', () => {
  render(<ShareScreen onNavigate={vi.fn()} />);
  expect(screen.queryByText('Private Name')).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('checkbox', { name: 'Include my name' }));
  expect(screen.getByText('Private Name')).toBeInTheDocument();
  expect(screen.getByText(/never published automatically/)).toBeInTheDocument();
});
it('resets the route name disclosure when switching applicant cases in the book view', async()=>{
 const {setLocale}=await import('@/lib/i18n');setLocale('ru');
 try{
  const view=render(<ShareScreen onNavigate={vi.fn()}/>);
  fireEvent.click(screen.getByRole('switch',{name:'Показывать имя'}));
  expect(screen.getByText('Private Name')).toBeInTheDocument();
  state.profile={id:'case-b',display_name:'Second private name'};
  view.rerender(<ShareScreen onNavigate={vi.fn()}/>);
  expect(screen.getByRole('switch',{name:'Показывать имя'})).not.toBeChecked();
  expect(screen.queryByText('Second private name')).not.toBeInTheDocument();
 }finally{state.profile={id:'case-a',display_name:'Private Name'};setLocale('en');}
});
