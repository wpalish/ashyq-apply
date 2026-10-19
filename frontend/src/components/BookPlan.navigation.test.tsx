import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { BookPlan } from './BookPlan';
import { emptyToday } from '@/test/admissionsTodayFixtures';
import type { ProgramResult } from '@/types';
const row = { id:'programme-a', program:'BSc Example', university:'Example University', degree:'bachelor', country:'Example', user_decision:'approved', admission_deadline:null } as ProgramResult;
const rows = [row];
let owner = 'A'; let epoch = 0;
vi.mock('@/lib/store', () => ({ useStore: () => ({ results:rows, savedProfile:{id:owner}, run:{profile_id:owner}, caseEpoch:epoch, collectDocuments:vi.fn(), decide:vi.fn() }) }));
vi.mock('@/lib/useAdmissionsToday', () => ({ useAdmissionsToday: () => ({ value:emptyToday(owner), refresh:vi.fn(), loading:false }) }));
vi.mock('@/lib/useAdmissionsActions', () => ({ useAdmissionsActions: () => ({ current:null, refresh:vi.fn() }) }));
vi.mock('@/screens/ApplicationsPanel', () => ({ ApplicationsPanel: () => <div>Applications</div> }));
vi.mock('./BookProgramme', () => ({ BookProgramme: ({ result, onBack }: { result:ProgramResult; onBack:()=>void }) => <section><h1>{result.program}</h1><button onClick={onBack}>Вернуться к плану</button></section> }));
beforeEach(() => { owner = 'A'; epoch = 0; window.history.replaceState(null,'','#/approved'); });
it('opens the programme named by a current-case home link and preserves the route on reload', () => {
  window.history.replaceState(null,'','#/approved?case=A&programme=programme-a');
  const view=render(<BookPlan onCollect={()=>{}}/>);
  expect(screen.getByRole('heading',{level:1})).toHaveTextContent('BSc Example');
  view.unmount(); render(<BookPlan onCollect={()=>{}}/>);
  expect(screen.getByRole('heading',{level:1})).toHaveTextContent('BSc Example');
});
it.each(['B','missing'] as const)('does not open an unrelated %s programme link', wrong => {
  window.history.replaceState(null,'',wrong==='B'?'#/approved?case=B&programme=programme-a':'#/approved?case=A&programme=missing');
  render(<BookPlan onCollect={()=>{}}/>);
  expect(screen.getByRole('heading',{level:1})).toHaveTextContent('Мой план');
  expect(screen.getByRole('status')).toHaveTextContent('недоступна в текущем профиле');
});
it('does not carry an open programme into the next case', () => {
  window.history.replaceState(null,'','#/approved?case=A&programme=programme-a');
  const view=render(<BookPlan onCollect={()=>{}}/>);
  owner='B'; epoch=1; view.rerender(<BookPlan onCollect={()=>{}}/>);
  expect(screen.getByRole('heading',{level:1})).toHaveTextContent('Мой план');
});
it('puts tasks before programmes, while programme actions still open their own view', () => {
  render(<BookPlan onCollect={()=>{}}/>);
  const tasks=screen.getByRole('heading',{name:'Задачи и личные сроки'});
  const programmes=screen.getByRole('heading',{name:'Сохранённые программы (1)'});
  expect(tasks.compareDocumentPosition(programmes) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  fireEvent.click(screen.getByRole('button',{name:/BSc Example/}));
  expect(screen.getByRole('heading',{level:1})).toHaveTextContent('BSc Example');
});
