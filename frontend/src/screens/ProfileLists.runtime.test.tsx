/** Real keystrokes must survive the controlled fields and reach the API as lists. */
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { setLocale } from '@/lib/i18n';
import { api } from '@/api/client';
import { StoreProvider } from '@/lib/store';
import type { Capabilities } from '@/types';
import { ProfileScreen } from './ProfileScreen';
import { PreferencesScreen } from './PreferencesScreen';

beforeEach(() => {
  setLocale('en');
  window.localStorage.clear();
  window.sessionStorage.clear();
  vi.spyOn(api, 'capabilities').mockResolvedValue({
    demo_mode: false, currency: { supported: ['USD'], rate_date: '2026-10-01', rate_source: 'ECB' },
  } as Capabilities);
  vi.spyOn(api, 'cases').mockResolvedValue([]);
  vi.spyOn(api, 'validateProfile').mockResolvedValue({
    gaps: [], can_proceed: true, blocking_count: 0, summary: 'ok',
  });
});

afterEach(() => {
  setLocale('en');
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

function typeCharacters(input: HTMLInputElement, text: string) {
  for (const character of text) {
    // Read back the rendered value after each event, like a browser does.
    // A single fill of the complete string masks lost commas and spaces.
    fireEvent.change(input, { target: { value: input.value + character } });
  }
}

it('keeps typed separators and submits each complete list without inventing entries', async () => {
  const fetchRequest = vi.fn(async (_url: string, request: RequestInit) => new Response(JSON.stringify({
    ...JSON.parse(String(request.body)), id: 'typed-profile', revision:1, write_receipt:{ command_id:(request.headers as Record<string,string>)['Idempotency-Key'],kind:'create',profile_id:'typed-profile',expected_revision:null,accepted_revision:1 },
    created_at: '2026-10-01T00:00:00Z', updated_at: '2026-10-01T00:00:00Z',
  }), { status: 201, headers: { 'Content-Type': 'application/json' } }));
  vi.stubGlobal('fetch', fetchRequest);
  render(<StoreProvider>
    <ProfileScreen onNext={() => {}} />
    <PreferencesScreen onStarted={() => {}} />
  </StoreProvider>);
  await waitFor(() => expect(screen.getByTestId('demo-toggle')).toBeEnabled());
  fireEvent.click(screen.getByRole('button', { name: '4 Activities & achievements' }));
  fireEvent.click(screen.getByRole('button', { name: '+ Add activity' }));
  fireEvent.click(screen.getByRole('button', { name: '+ Add achievement' }));

  const inputs: [HTMLInputElement, string][] = [
    [screen.getByLabelText('Field of study'), 'Computer Science, Mathematics, '],
    [screen.getByLabelText('Preferred countries'), 'Singapore, United Kingdom, '],
    [screen.getByLabelText('Excluded countries'), 'Austria, Canada, Czech Republic, '],
    [screen.getByLabelText('Research interests'), 'machine learning, data science, '],
    [screen.getByLabelText('Planned retakes'), 'SAT in November, IELTS in December, '],
    [screen.getAllByLabelText<HTMLInputElement>('Evidence links')[0]!, 'https://a.example/one, https://b.example/two, '],
    [screen.getAllByLabelText<HTMLInputElement>('Evidence links')[1]!, 'https://c.example/award, https://d.example/award, '],
  ];
  for (const [input, text] of inputs) {
    typeCharacters(input, text);
    expect(input).toHaveValue(text);
  }
  // Saving cannot rely on blur to apply the last edit to the payload.
  fireEvent.click(screen.getByTestId('save-profile'));
  expect(await screen.findByText('Saved', { exact: true })).toBeVisible();
  expect(fetchRequest).toHaveBeenCalledOnce();
  const [url, request] = fetchRequest.mock.calls[0]!;
  expect(url).toBe('/api/profiles');
  expect(request.method).toBe('POST');
  expect(JSON.parse(String(request.body))).toMatchObject({
    context: { intended_fields: ['Computer Science', 'Mathematics'] },
    preferences: {
      preferred_countries: ['Singapore', 'United Kingdom'],
      excluded_countries: ['Austria', 'Canada', 'Czech Republic'],
      research_interests: ['machine learning', 'data science'],
    },
    academics: { planned_retakes: ['SAT in November', 'IELTS in December'] },
    activities: [{ evidence_links: ['https://a.example/one', 'https://b.example/two'] }],
    achievements: [{ evidence_links: ['https://c.example/award', 'https://d.example/award'] }],
  });
});


it('keeps book activity fields, fractional hours and evidence links in the real profile command',async()=>{
  setLocale('ru');
  const fetchRequest=vi.fn(async(_url:string,request:RequestInit)=>new Response(JSON.stringify({
    ...JSON.parse(String(request.body)),id:'book-profile',revision:1,
    write_receipt:{command_id:(request.headers as Record<string,string>)['Idempotency-Key'],kind:'create',profile_id:'book-profile',expected_revision:null,accepted_revision:1},
    created_at:'2026-10-18T00:00:00Z',updated_at:'2026-10-18T00:00:00Z',
  }),{status:201,headers:{'Content-Type':'application/json'}}));
  vi.stubGlobal('fetch',fetchRequest);
  render(<StoreProvider><ProfileScreen onNext={()=>{}}/></StoreProvider>);
  fireEvent.click(await screen.findByRole('button',{name:'Активности'}));
  fireEvent.click(screen.getByRole('button',{name:'Добавить ещё активность'}));
  fireEvent.change(screen.getAllByLabelText('Название активности').at(-1)!,{target:{value:'Robotics club'}});
  const activity=within(screen.getByDisplayValue('Robotics club').closest('article')!);
  fireEvent.change(activity.getByLabelText('Роль'),{target:{value:'Coordinator'}});
  fireEvent.change(activity.getByLabelText('Продолжительность, месяцев'),{target:{value:'12'}});
  fireEvent.change(activity.getByLabelText('Часов в неделю'),{target:{value:'2.5'}});
  const evidence=activity.getByLabelText<HTMLInputElement>('Ссылка на подтверждение (необязательно)');
  typeCharacters(evidence,'https://one.example/item, https://two.example/item, ');
  fireEvent.click(screen.getByTestId('save-profile'));
  await waitFor(()=>expect(screen.getByRole('status')).toHaveTextContent(/Saved|Сохранено/));
  expect(fetchRequest).toHaveBeenCalledOnce();
  expect(JSON.parse(String(fetchRequest.mock.calls[0]![1].body)).activities).toEqual(expect.arrayContaining([expect.objectContaining({
    name:'Robotics club',role:'Coordinator',duration_months:12,hours_per_week:2.5,
    evidence_links:['https://one.example/item','https://two.example/item'],
  })]));
});

it('saves the book budget, direction and scholarship conditions through the actual profile client',async()=>{
  setLocale('ru');
  const fetchRequest=vi.fn(async(_url:string,request:RequestInit)=>new Response(JSON.stringify({
    ...JSON.parse(String(request.body)),id:'book-budget',revision:1,
    write_receipt:{command_id:(request.headers as Record<string,string>)['Idempotency-Key'],kind:'create',profile_id:'book-budget',expected_revision:null,accepted_revision:1},
    created_at:'2026-10-18T00:00:00Z',updated_at:'2026-10-18T00:00:00Z',
  }),{status:201,headers:{'Content-Type':'application/json'}}));
  vi.stubGlobal('fetch',fetchRequest);
  render(<StoreProvider><PreferencesScreen onStarted={()=>{}}/></StoreProvider>);
  fireEvent.change(screen.getByLabelText('Годовой бюджет семьи'),{target:{value:'7400.5'}});
  fireEvent.change(screen.getByLabelText('Страны обучения'),{target:{value:'Canada'}});
  fireEvent.change(screen.getByLabelText('Что изучать'),{target:{value:'Computer Science, Mathematics, '}});
  fireEvent.click(screen.getByLabelText('Стипендия должна покрывать проживание'));
  fireEvent.click(screen.getByRole('button',{name:'Сохранить как черновик'}));
  await waitFor(()=>expect(fetchRequest).toHaveBeenCalledOnce());
  const [url,request]=fetchRequest.mock.calls[0]!;
  expect(url).toBe('/api/profiles');
  expect(JSON.parse(String(request.body))).toMatchObject({
    context:{intended_fields:['Computer Science','Mathematics']},
    preferences:{preferred_countries:['Canada']},
    funding:{max_annual_budget:7400.5,must_cover_housing:false},
  });
});
