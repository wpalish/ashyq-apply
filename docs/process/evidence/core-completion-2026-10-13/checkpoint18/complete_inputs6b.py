from pathlib import Path
import json,re
s=Path(__file__).resolve().parent;out=s/'inputs6b-proposal';pre=s/'inputs6b-preimages'
def put(p,t):q=out/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(t)
put('frontend/src/components/ResearchReadNotice.tsx','''import { Notice } from './primitives';
import { useResearchInputRead } from '@/lib/useResearchInputRead';
import { useStore } from '@/lib/store';
import { useTranslation } from '@/lib/useTranslation';
import { isResultFreshness } from '@/lib/researchReadContext';
import { dateTime } from '@/lib/format';
import type { ResearchProfileSection } from '@/types';
import type { MessageKey } from '@/lib/i18n';
const sectionLabels: Record<ResearchProfileSection, MessageKey> = { context: 'inputs.context', academics: 'inputs.academics',
  activities: 'inputs.activities', achievements: 'inputs.achievements', preferences: 'inputs.preferences', funding: 'inputs.funding', weights: 'inputs.weights', weights_override: 'inputs.weights' };
export function ResearchReadNotice() {
  const read = useResearchInputRead(); const { run, results, savedProfile, currentAdmissionsCase } = useStore(); const { t } = useTranslation();
  const live = currentAdmissionsCase();
  if (!run || !savedProfile || run.profile_id !== savedProfile.id || live.profile_id !== savedProfile.id || live.scope === null) return null;
  const status = read.status; const changed = status?.state === 'changed' || status?.state === 'mixed';
  const ownedResults = run.profile_id === live.profile_id ? results.filter(result => result.run_id === run.id) : [];
  const aged = ownedResults.some(result => isResultFreshness(result.read_freshness) && result.read_freshness.evidence === 'observed' && (result.read_freshness.stale_claim_count ?? 0) > 0);
  return <div className="stack" data-testid="research-read-notice">
    {(changed || read.error || (read.applicable && (!status || status.state === 'unknown' || status.state === 'pending'))) && <Notice kind="warn"><div className="stack stack--tight">
      <strong>{t(status?.state === 'mixed' ? 'inputs.mixed' : changed ? 'inputs.changed' : 'inputs.unknown')}</strong>
      {status && status.changed_sections.length > 0 && <p className="small">{t('inputs.sections')}: {status.changed_sections.map(section => t(sectionLabels[section])).join(', ')}</p>}
      <p className="small">{t('inputs.hint')}</p>{status && <p className="xs muted">{t('inputs.observed')}: {dateTime(status.observed_at)}</p>}
      {read.error && <p className="small">{read.error} {status && t('inputs.lastConfirmed')}</p>}
      <button type="button" className="btn btn--sm" disabled={read.loading} onClick={() => void read.refresh()}>{t('inputs.refresh')}</button>
    </div></Notice>}
    {ownedResults.length > 0 && <Notice kind={aged ? 'warn' : 'info'}><div>
      <strong>{t('inputs.storedAssessment')}</strong> <span className="small">{t(aged ? 'inputs.aged' : 'inputs.assessmentHint')}</span>
    </div></Notice>}
  </div>;
}
''')
p='frontend/src/App.tsx';t=(pre/p).read_text().replace("import { PaywallNotice }", "import { ResearchReadNotice } from '@/components/ResearchReadNotice';\nimport { PaywallNotice }",1);marker='          <ErrorBoundary label={`the ${screen} screen`} key={screen}>';assert marker in t;t=t.replace(marker,"          <ErrorBoundary label=\"the research read context\"><ResearchReadNotice /></ErrorBoundary>\n"+marker,1);put(p,t)
rows=[
('inputs.readFailed','Could not confirm which profile inputs the research used. Refresh to try again.','Не удалось подтвердить, какую анкету использовало исследование. Обновите сведения.','Зерттеу қай анкета мәліметтерін пайдаланғаны расталмады. Мәліметтерді жаңартыңыз.'),
('inputs.changed','Your profile inputs have changed since this research.','После этого исследования ваша анкета изменилась.','Осы зерттеуден кейін анкетаңыз өзгерді.'),('inputs.mixed','This research used more than one version of your inputs.','Исследование использовало несколько версий вашей анкеты.','Зерттеу анкетаңыздың бірнеше нұсқасын пайдаланды.'),('inputs.unknown','The research input version is not confirmed.','Версия анкеты для исследования не подтверждена.','Зерттеудегі анкета нұсқасы расталмаған.'),
('inputs.hint','Keep earlier results and personal records. Review requirements and source limitations before relying on the previous assessment. Refreshing this note does not start research.','Прежние результаты и личные записи сохраняются. Проверьте требования и ограничения источников перед использованием прежней оценки. Обновление этого сообщения не запускает исследование.','Бұрынғы нәтижелер мен жеке жазбалар сақталады. Алдыңғы бағалауды пайдаланбас бұрын талаптар мен дереккөз шектеулерін тексеріңіз. Бұл хабарламаны жаңарту зерттеуді бастамайды.'),
('inputs.sections','Changed sections','Изменённые разделы','Өзгерген бөлімдер'),('inputs.observed','Last read','Последнее чтение','Соңғы оқу'),('inputs.lastConfirmed','Showing the last confirmed input read.','Показано последнее подтверждённое чтение входных данных.','Кіріс мәліметтерінің соңғы расталған оқылуы көрсетілген.'),('inputs.refresh','Refresh input context','Обновить сведения об анкете','Анкета туралы мәліметтерді жаңарту'),
('inputs.storedAssessment','Recorded assessment.','Сохранённая оценка.','Сақталған бағалау.'),('inputs.assessmentHint','The evaluation reflects the research at that time. It does not establish current readiness or an admission probability.','Оценка отражает состояние исследования на тот момент. Она не подтверждает текущую готовность и не является вероятностью поступления.','Бағалау сол кездегі зерттеу күйін көрсетеді. Ол қазіргі дайындықты немесе қабылдану ықтималдығын растамайды.'),('inputs.aged','Some evidence has aged or is historical. Recheck the relevant requirements; the saved evaluation has not been recalculated.','Некоторые сведения устарели или относятся к истории. Перепроверьте соответствующие требования; сохранённая оценка не пересчитывалась.','Кейбір деректер ескірген немесе тарихқа қатысты. Тиісті талаптарды қайта тексеріңіз; сақталған бағалау қайта есептелмеген.'),
('inputs.context','Study context','Контекст поступления','Қабылдау контексті'),('inputs.academics','Academic record','Учебные результаты','Оқу нәтижелері'),('inputs.activities','Activities','Активности','Әрекеттер'),('inputs.achievements','Achievements','Достижения','Жетістіктер'),('inputs.preferences','Preferences','Предпочтения','Қалаулар'),('inputs.funding','Funding and budget','Финансирование и бюджет','Қаржыландыру мен бюджет'),('inputs.weights','Scoring priorities','Приоритеты оценки','Бағалау басымдықтары')]
p='frontend/src/lib/i18n.ts';t=(pre/p).read_text()
for i,name in enumerate(['EN','RU','KK'],1):
 m=re.search(r'const '+name+r'[^\n]*\{',t);assert m;pos=m.end();t=t[:pos]+'\n'+''.join('  '+json.dumps(row[0],ensure_ascii=False)+': '+json.dumps(row[i],ensure_ascii=False)+',\n' for row in rows)+t[pos:]
put(p,t)
put('frontend/src/lib/useResearchInputRead.test.tsx','''import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { useResearchInputRead } from './useResearchInputRead';
import { api } from '@/api/client';
import { deferred } from '@/screens/preparationFixtures';
import { isResearchInputStatus, isResultFreshness } from './researchReadContext';
import type { RunView, StoredProfile } from '@/types';
const state = vi.hoisted(() => ({ id: 'A', epoch: 1, profile: { id: 'A', display_name: 'Synthetic', created_at: '', updated_at: '' } as StoredProfile, runId: 'run-A' }));
vi.mock('./store', () => ({ useStore: () => ({ currentAdmissionsCase: () => ({ scope: undefined, profile_id: state.id, case_epoch: state.epoch }), savedProfile: state.profile, run: { id: state.runId, profile_id: state.id } }) }));
function wire(id: string, profile: string, status: 'current' | 'changed' = 'current'): RunView {
  return { id, profile_id: profile, profile_input_status: { schema_version: 'research-input-status-v1', state: status, changed_sections: status === 'changed' ? ['academics'] : [], observed_at: '2026-10-14T00:00:00Z', applicability: 'not_assessed' } } as RunView;
}
beforeEach(() => { state.id = 'A'; state.epoch = 1; state.runId = 'run-A'; state.profile = { id: 'A', display_name: 'Synthetic', created_at: '', updated_at: '' }; vi.spyOn(api, 'getRun').mockImplementation(async id => wire(id, state.id)); });
afterEach(() => vi.restoreAllMocks());
it('reads the owned run once and refreshes after a newly saved profile even with equal timestamp precision', async () => {
  const { result, rerender } = renderHook(() => useResearchInputRead()); await waitFor(() => expect(result.current.status?.state).toBe('current'));
  rerender(); expect(api.getRun).toHaveBeenCalledOnce();
  vi.mocked(api.getRun).mockResolvedValueOnce(wire('run-A', 'A', 'changed')); state.profile = { ...state.profile }; rerender();
  expect(result.current.status).toBeNull(); await waitFor(() => expect(result.current.status?.state).toBe('changed')); expect(api.getRun).toHaveBeenCalledTimes(2);
});
it('rejects stale callbacks and late responses after A→B→A and preserves only confirmed same-profile reads on error', async () => {
  const old = deferred<RunView>(); vi.mocked(api.getRun).mockImplementationOnce(() => old.promise);
  const { result, rerender } = renderHook(() => useResearchInputRead()); const refreshA = result.current.refresh;
  state.id = 'B'; state.runId = 'run-B'; state.epoch = 2; state.profile = { ...state.profile, id: 'B' };
  await act(async () => expect(await refreshA()).toBe(false)); expect(api.getRun).toHaveBeenCalledOnce(); rerender(); await waitFor(() => expect(result.current.status?.state).toBe('current'));
  state.id = 'A'; state.runId = 'run-A'; state.epoch = 3; state.profile = { ...state.profile, id: 'A' }; rerender();
  await act(async () => old.resolve(wire('run-A', 'A', 'changed'))); await waitFor(() => expect(result.current.status?.state).toBe('current'));
  vi.mocked(api.getRun).mockRejectedValueOnce(new Error('Synthetic failure')); await act(async () => { await result.current.refresh(); });
  expect(result.current.status?.state).toBe('current'); expect(result.current.error).not.toBe('');
});
it('rejects copied readiness or malformed sections and keeps unavailable evidence without a fabricated zero', () => {
  expect(isResearchInputStatus(wire('run-A', 'A').profile_input_status)).toBe(true);
  expect(isResearchInputStatus({ ...wire('run-A', 'A').profile_input_status, applicability: 'ready' })).toBe(false);
  expect(isResearchInputStatus({ ...wire('run-A', 'A').profile_input_status, changed_sections: ['academics', 'academics'] })).toBe(false);
  expect(isResultFreshness({ schema_version: 'result-freshness-read-v1', observed_at: '2026-10-14T00:00:00Z', evidence: 'not_available', stale_claim_count: null, assessment: 'stored_evaluation' })).toBe(true);
  expect(isResultFreshness({ schema_version: 'result-freshness-read-v1', observed_at: '2026-10-14T00:00:00Z', evidence: 'not_available', stale_claim_count: 0, assessment: 'stored_evaluation' })).toBe(false);
});
''')
put('frontend/src/components/ResearchReadNotice.test.tsx','''import { render, screen } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { ResearchReadNotice } from './ResearchReadNotice';
import { setLocale } from '@/lib/i18n';
import type { ResearchInputStatusRead } from '@/types';
let id = 'A'; let status: ResearchInputStatusRead | null;
vi.mock('@/lib/useResearchInputRead', () => ({ useResearchInputRead: () => ({ applicable: true, status, loading: false, error: '', refresh: vi.fn() }) }));
vi.mock('@/lib/store', () => ({ useStore: () => ({ currentAdmissionsCase: () => ({ scope: undefined, profile_id: id, case_epoch: 1 }), savedProfile: { id: 'A' }, run: { id: 'run-A', profile_id: 'A' },
  results: [{ id: 'r1', run_id: 'run-A', read_freshness: { schema_version: 'result-freshness-read-v1', observed_at: '2026-10-14T00:00:00Z', evidence: 'observed', stale_claim_count: 1, assessment: 'stored_evaluation' } }] }) }));
beforeEach(() => { id = 'A'; setLocale('en'); status = { schema_version: 'research-input-status-v1', state: 'changed', changed_sections: ['academics'], observed_at: '2026-10-14T00:00:00Z', applicability: 'not_assessed' }; });
it('shows exact changed section and historical source/evaluation limits without calculating a new result', () => {
  render(<ResearchReadNotice />); expect(screen.getByText('Your profile inputs have changed since this research.')).toBeInTheDocument();
  expect(screen.getByText(/Changed sections: Academic record/)).toBeInTheDocument(); expect(screen.getByText('Recorded assessment.')).toBeInTheDocument();
  expect(screen.getByText(/saved evaluation has not been recalculated/)).toBeInTheDocument();
});
it('hides all old-case read notices before another case rerenders its private records', () => {
  id = 'B'; render(<ResearchReadNotice />); expect(screen.queryByTestId('research-read-notice')).toBeNull();
});
''')
print('External read context notices and own-case/profile replacement controls ready; review/application/gates pending.')
