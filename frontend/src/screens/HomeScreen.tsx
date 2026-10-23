import { HomeAgenda } from '@/components/HomeAgenda';
import { AdmissionsTodayPanel } from '@/components/AdmissionsTodayPanel';
import { useStore } from '@/lib/store';
import { useTranslation } from '@/lib/useTranslation';
import { ArrowRight, ChartBar, CaretRight } from '@phosphor-icons/react';
import { BookGlobe, BookIntake, BookLogo } from '@/components/BookUI';
import { Chip } from '@/components/primitives';
import { date } from '@/lib/format';
import type { ScreenId } from '@/App';

type HomeScreenProps = { onNavigate: (screen: ScreenId) => void };

/** A single next step, selected only from real case/run state. */
export function HomeScreen({ onNavigate }: HomeScreenProps) {
  const { t, locale } = useTranslation(); const ru = locale !== 'en';
  const { savedProfile, profileDraft, run, results, hydrated, capabilities } = useStore();
  const context = (profileDraft?.context ?? {}) as { intake_year?: number; intake_term?: string };
  const selected = results.filter((result) => result.user_decision === 'approved' || result.user_decision === 'maybe');
  const needsAttention = run && (run.stale || run.cancelled
    || ['failed', 'retryable_failed', 'cancelled'].includes(run.stage)
    || ['failed', 'dead', 'cancelled'].includes(run.job_status ?? ''));
  const active = run?.job_status === 'running' || run?.job_status === 'queued' || run?.job_running;
  const emptyResearch = run && ['awaiting_user_decision', 'completed'].includes(run.stage) && !results.length;
  const documentsReady = selected.length > 0 && selected.every((result) => result.checklist);
  const next: { title: string; detail: string; action: string; screen: ScreenId } = !savedProfile
    ? {
      title: 'Build your profile',
      detail: 'Tell us what you want to study so your research starts with your own goals.',
      action: 'Create profile', screen: 'profile',
    }
    : needsAttention || emptyResearch
      ? {
        title: needsAttention ? 'Your research needs attention' : 'Review your research findings',
        detail: 'Review where the research stopped and what remains unknown before choosing your next step.',
        action: 'Review research', screen: 'progress',
      }
      : active
      ? {
        title: 'Your research is in progress',
        detail: 'Follow what has been checked and see any source limitations as they appear.',
        action: 'View progress', screen: 'progress',
      }
      : documentsReady
        ? {
          title: 'Work through your document checklists',
          detail: 'Review the requirements and unresolved questions for your selected programmes. A collected checklist does not mean an application is ready.',
          action: 'Open documents', screen: 'documents',
        }
      : results.length > 0 && selected.length > 0
        ? {
          title: 'Plan your next steps',
          detail: 'Collect the document requirements for the programmes you selected.',
          action: 'Open plan', screen: 'approved',
        }
        : results.length > 0
          ? {
            title: 'Review your matches',
            detail: 'Compare confirmed information and choose which programmes to keep.',
            action: 'Explore matches', screen: 'shortlist',
          }
          : {
            title: 'Set your preferences',
            detail: 'Choose your priorities and budget before starting university research.',
            action: 'Set preferences', screen: 'preferences',
          };

  if (hydrated === false) return <div className="home-loading" role="status">Loading your journey…</div>;

  const titleRU = next.screen === 'profile' ? 'Расскажи о себе' : next.screen === 'documents' ? 'Подготовь документы для поступления' : next.screen === 'approved' ? 'Проверь требования выбранных программ' : next.screen === 'shortlist' ? 'Выбери подходящие программы' : next.screen === 'progress' ? active ? 'Проверяем программы и требования' : 'Проверь результаты исследования' : 'Укажи направление и бюджет';
  const detailRU = next.screen === 'documents' ? 'Открой требования выбранных программ. Прочитанный список ещё не означает, что документы готовы.' : next.screen === 'profile' ? 'Заполни основную информацию, чтобы мы могли подобрать подходящие программы.' : next.screen === 'approved' ? 'Открой программу в плане и собери её требования к документам.' : 'Продолжи с сохранённого этапа. Непроверенные требования отмечены отдельно.';
  const name = savedProfile?.display_name?.split(' ')[0];
  return <div className="home-page">
    <section className="home-hero"><div className="home-hero__copy"><h1>{ru ? name ? `${name}, за дело` : 'Твой план поступления' : 'Your application workspace'}</h1><p>{ru ? 'Открой ближайшую задачу, обнови профиль или продолжи работу с программами.' : 'Open a task, update your profile or continue reviewing programmes.'}</p><BookIntake year={context.intake_year} term={context.intake_term}/></div><BookGlobe compact note={false}/></section>
    {ru && savedProfile && <HomeAgenda/>}
    <section className="home-next" aria-labelledby="home-next-title"><span className="book-icon-tile"><ChartBar size={30} weight="fill"/></span><div><div className="home-next__caption">{ru?'СЛЕДУЮЩИЙ ШАГ':'NEXT STEP'}</div><h2 id="home-next-title">{ru?titleRU:next.title}</h2><p>{ru?detailRU:next.detail}</p></div><button className="btn btn--primary" type="button" onClick={()=>onNavigate(next.screen)}>{ru?next.screen==='profile'?'Открыть профиль':next.screen==='documents'?'Открыть документы':next.screen==='shortlist'?'Перейти к подбору':next.screen==='approved'?'Проверить требования':next.screen==='progress'?'Открыть исследование':'Указать предпочтения':next.action}<ArrowRight size={18}/></button></section>
    <nav className="workspace-links" aria-label={ru?'Рабочие разделы':'Workspace sections'}><a href="#/profile">{ru?'Редактировать профиль':'Edit profile'}<ArrowRight size={17}/></a><a href="#/shortlist">{ru?`Подбор · ${results.length} программ`:'Explore programmes'}<ArrowRight size={17}/></a><a href="#/approved">{ru?'Открыть план':'Open plan'}<ArrowRight size={17}/></a></nav>
    <section className="home-selected"><div className="home-selected__head"><h2>{ru?'Выбранные программы':'Selected programmes'}<span>{selected.length}</span></h2><button type="button" className="btn btn--ghost btn--sm" onClick={()=>onNavigate('shortlist')}>{ru?'Перейти к подбору':'Explore programmes'}<ArrowRight size={16}/></button></div>
      {!selected.length&&<p className="small muted">{ru?'Сохрани подходящие программы из подбора — они появятся здесь.':'Save programmes from your research to keep them here.'}</p>}
      {selected.slice(0,3).map(result=><article className="home-selected__row" key={result.id}><BookLogo university={result.university}/><div><h3>{result.university}</h3><p>{result.program}</p></div><div><small>{ru?'Требования':'Requirements'}</small><Chip tone={result.eligibility==='MET'?'info':'warn'}>{ru?result.eligibility==='MET'?'Проверь источники':'Требования уточняются':result.eligibility==='MET'?'Review sources':'Needs clarification'}</Chip></div><div><small>{ru?'Крайний срок':'Deadline'}</small><strong className="small">{result.admission_deadline?date(result.admission_deadline):ru?'Уточняется':'Not confirmed'}</strong></div><a className="btn btn--sm" href={`#/approved?case=${encodeURIComponent(savedProfile?.id??'')}&programme=${encodeURIComponent(result.id)}`} aria-label={`${ru?'Открыть':'Open'} ${result.university}`}>{ru?'Открыть':'Open'}<CaretRight size={16}/></a></article>)}
    </section>
    {!ru&&savedProfile&&<details className="home-today-details"><summary>{ru?'Личные задачи и сроки':'Your personal tasks and dates'}</summary><AdmissionsTodayPanel/></details>}
    <details className="home-today-details" open={locale==='en'}><summary>{ru?'Дополнительная подготовка':'Optional preparation'}</summary><section className="home-optional"><h2>{ru?'Дополнительная подготовка':'A clearer way forward.'}</h2><p>{t('preparation.optionalHint')}</p><button type="button" className="btn btn--sm" onClick={()=>onNavigate('preparation')}>{ru?'Подготовка к экзаменам':'Exam preparation'}</button></section></details>
    <p className="visually-hidden">{t('preparation.optionalHint')}{capabilities?.demo_mode?'Synthetic demonstration data.':''}</p>
  </div>;
}
