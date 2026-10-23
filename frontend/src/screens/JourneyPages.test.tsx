import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { CalendarScreen, ShareScreen } from './JourneyPages';
import type { ProgramResult } from '@/types';
const state = vi.hoisted(() => ({ results: [] as ProgramResult[], profile: { id: 'case-a', display_name: 'Private Name' } }));
const drawing=vi.hoisted(()=>({draw:vi.fn()}));
vi.mock('@/lib/drawBookRouteCard',()=>({drawBookRouteCard:drawing.draw}));
vi.mock('@/lib/store', () => ({ useStore: () => ({ results: state.results, savedProfile: state.profile, run: null }) }));
vi.mock('@/lib/useAdmissionsActions',()=>({useAdmissionsActions:()=>({current:null,activeCase:'case-a'})}));
vi.mock('@/lib/useAdmissionsToday', () => ({ useAdmissionsToday: () => ({ value: null, error: '', refresh: vi.fn() }) }));
beforeEach(() => { state.results = [];drawing.draw.mockReset(); });
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
it('cancels the pending image when name disclosure changes before drawing finishes',async()=>{
 const {setLocale}=await import('@/lib/i18n');setLocale('ru');
 let finish!:(value:'drawn')=>void;
 const pending=new Promise<'drawn'>(resolve=>{finish=resolve;});drawing.draw.mockReturnValue(pending);
 const toBlob=vi.spyOn(HTMLCanvasElement.prototype,'toBlob');
 try{
  render(<ShareScreen onNavigate={vi.fn()}/>);
  fireEvent.click(screen.getByRole('switch',{name:'Показывать имя'}));
  fireEvent.click(screen.getByRole('button',{name:'Сохранить изображение'}));
  expect(drawing.draw).toHaveBeenCalledOnce();expect(drawing.draw.mock.calls[0]?.[1].signature).toBe('Private Name');
  fireEvent.click(screen.getByRole('switch',{name:'Показывать имя'}));
  await act(async()=>finish('drawn'));
  await waitFor(()=>expect(screen.getByRole('button',{name:'Сохранить изображение'})).toBeEnabled());
  expect(toBlob).not.toHaveBeenCalled();expect(screen.queryByText('Private Name')).not.toBeInTheDocument();
 }finally{toBlob.mockRestore();setLocale('en');}
});
