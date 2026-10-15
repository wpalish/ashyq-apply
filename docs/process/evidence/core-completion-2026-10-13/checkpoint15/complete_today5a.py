from pathlib import Path
import json
s=Path(__file__).resolve().parent;repo=s.parents[1]/'work/unimatch-calendar-materials';out=s/'today5a-proposal';pre=s/'today5a-preimages'
def get(p):return(pre/p).read_text()
def put(p,t):q=out/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(t)
put('frontend/src/components/AdmissionsTodayPanel.tsx','''import { Chip, Loading, Notice, Panel } from './primitives';
import { useAdmissionsToday } from '@/lib/useAdmissionsToday';
import { useAdmissionsActions } from '@/lib/useAdmissionsActions';
import { targetHref } from '@/lib/admissionsNavigation';
import { dateTime, localDate } from '@/lib/format';
import { useTranslation } from '@/lib/useTranslation';
import type { TodayCardV1 } from '@/types/admissionsActions';
import type { MessageKey } from '@/lib/i18n';
const reasons: Record<TodayCardV1['dependency_reasons'][number], MessageKey> = {
  dependency_missing: 'today.dependencyMissing', dependency_cycle: 'today.dependencyCycle', dependency_not_reported_ready: 'today.dependencyNotReady',
  report_refers_to_previous_binding: 'today.previousBinding', not_needed_is_not_a_waiver: 'today.notWaiver', application_context_changed: 'today.contextChanged',
};
export function AdmissionsTodayPanel() {
  const today = useAdmissionsToday(); const actions = useAdmissionsActions(); const { t } = useTranslation();
  const value = today.value;
  if (!today.profileId) return null;
  const groups: { title: MessageKey; cards: TodayCardV1[] }[] = value ? [
    { title: 'today.earlierDates', cards: value.overdue_personal }, { title: 'today.current', cards: value.today_personal },
    { title: 'today.future', cards: value.future.filter(card => card.reason !== 'accepted_study_action') }, { title: 'today.undated', cards: value.undated_personal },
  ] : [];
  const study = value ? [...value.today_study, ...value.future.filter(card => card.reason === 'accepted_study_action')] : [];
  const matchingDetails = value && actions.current?.profile_id === value.profile_id && actions.current.revision === value.action_revision;
  const renderCard = (card: TodayCardV1) => {
    const ref = card.target;
    const name = matchingDetails && ref?.kind === 'document_task' ? actions.current?.state?.document_tasks.find(task => task.id === ref.id)?.personal.label
      : ref?.kind === 'application' ? value?.application_summaries.find(app => app.id === ref.id)?.label : null;
    const href = value && ref && card.actionable && !value.needs_refresh ? ref.kind === 'document_task' ? targetHref({ profileId: value.profile_id, screen: 'documents', target: ref })
      : ref.kind === 'application' ? targetHref({ profileId: value.profile_id, screen: 'approved', target: ref })
        : ref.kind === 'lesson' || ref.kind === 'attempt_review' ? targetHref({ profileId: value.profile_id, screen: 'preparation', target: ref }) : null : null;
    return <article className="stack stack--tight" key={card.id} data-testid="today-action">
      <h4>{name || t(card.reason === 'personal_application_action' ? 'today.application' : card.reason === 'personal_document_action' ? 'today.document' : 'today.study')}</h4>
      <p className="small">{card.date.local_date ? localDate(card.date.local_date) : t('today.dateUnknown')} · {card.date.timezone ?? t('dates.zoneUnknown')}</p>
      {card.date.fallback_display_only && <p className="xs muted">{t('today.fallbackDate')}</p>}
      {card.planned_minutes !== null && <p className="small">{card.planned_minutes} {t('today.minutes')}</p>}
      {card.dependency_reasons.length > 0 && <ul className="small">{card.dependency_reasons.map(reason => <li key={reason}>{t(reasons[reason])}</li>)}</ul>}
      {card.source_state !== 'applicant_entered' && card.source_state !== 'current_reference' && <Chip tone="warn">{t('today.sourceReview')}</Chip>}
      <div className="row">{href ? <a className="btn btn--sm" href={href}>{t('today.openExact')}</a> : <span className="small muted">{t('today.targetUnavailable')}</span>}
        {value && card.target_result_id && <a className="btn btn--sm btn--ghost" href={targetHref({ profileId: value.profile_id, screen: 'sources', target: { kind: 'result', id: card.target_result_id } })}>{t('today.openEvidence')}</a>}</div>
    </article>;
  };
  return <Panel title={t('today.title')}><div className="stack" data-testid="admissions-today">
    <p className="small muted">{t('today.hint')}</p>
    {today.loading && <Loading label={t('today.loading')} />}
    {today.error && <Notice kind="warn">{today.error}{value && ` ${t('today.lastConfirmed')}`}</Notice>}
    {value && <>
      <p className="xs muted">{t('today.observed')}: {dateTime(value.as_of)}</p>
      {(value.needs_refresh || (actions.current && !matchingDetails)) && <Notice kind="warn">{t('today.refreshNeeded')}</Notice>}
      {value.action_state === 'unavailable' && <Notice kind="warn">{t('today.unavailable')}</Notice>}
      {groups.every(group => group.cards.length === 0) && value.action_state !== 'unavailable' && <p>{t('today.empty')}</p>}
      {groups.filter(group => group.cards.length > 0).map(group => <section className="stack" key={group.title}><h3>{t(group.title)}</h3>{group.cards.map(renderCard)}</section>)}
      {study.length > 0 && <details><summary>{t('today.optionalStudy')}</summary><p className="small muted">{t('preparation.optionalHint')}</p><div className="stack">{study.map(renderCard)}</div></details>}
    </>}
    <div className="row"><button type="button" className="btn btn--sm" disabled={today.loading} onClick={() => { void today.refresh(); void actions.refresh(); }}>{t('today.refresh')}</button>
      <a className="btn btn--sm" href="#/documents">{t('documents.addPersonal')}</a><a className="btn btn--sm" href="#/approved">{t('applications.add')}</a></div>
  </div></Panel>;
}
''')
p='frontend/src/screens/HomeScreen.tsx';t=get(p).replace("import { useStore }", "import { AdmissionsTodayPanel } from '@/components/AdmissionsTodayPanel';\nimport { useStore }",1).replace('      <section className="home-next"', '      {savedProfile && <AdmissionsTodayPanel />}\n\n      <section className="home-next"',1);put(p,t)
# Exact personal targets reuse existing form; no similar-object fallback or automatic case switch.
for p,kind,record,openMode in [('frontend/src/screens/PersonalDocumentsPanel.tsx','document_task','tasks','details'),('frontend/src/screens/ApplicationsPanel.tsx','application','applications','details')]:
 t=get(p).replace('useRef, useState','useEffect, useRef, useState',1).replace("import { useTranslation }", "import { useAdmissionsTarget } from '@/lib/admissionsNavigation';\nimport { useTranslation }",1)
 marker='  const attemptedDraft = useRef<Draft | null>(null);';t=t.replace(marker,"  const target = useAdmissionsTarget(); const openedTarget = useRef<string | null>(null);\n"+marker,1)
 marker='  const change = (patch: Partial<Draft>)'
 position=t.index(marker);end=t.index('\n',position)
 # open() is defined before change in docs and after change in applications; insert effect immediately before startPreparing or save after complete open.
 effect=f'''  const targetKey = target?.target.kind === '{kind}' ? JSON.stringify([actions.caseKey, target]) : null;
  const targetMissing = targetKey !== null && (target?.profileId !== actions.activeCase || (actions.current !== null && !{record}.some(item => item.id === target?.target.id)));
  useEffect(() => {{
    if (!targetKey || openedTarget.current === targetKey || targetMissing || !canEdit || target?.profileId !== actions.activeCase) return;
    const exact = {record}.find(item => item.id === target?.target.id); if (!exact) return;
    openedTarget.current = targetKey; open('{openMode}', exact);
  }}, [targetKey, targetMissing, canEdit, target, actions.activeCase, {record}, open]);
'''
 # open is stable via useCallback in both panels to avoid redundant effects from own draft changes.
 t=t.replace('useEffect, useRef, useState','useCallback, useEffect, useRef, useState',1)
 t=t.replace("  const open = (mode: Draft['mode'], task?: DocumentTaskV1) => {", "  const open = useCallback((mode: Draft['mode'], task?: DocumentTaskV1) => {",1).replace("  const open = (mode: Draft['mode'], app?: ApplicationRecord, prior?: ActionEventRefV1) => {", "  const open = useCallback((mode: Draft['mode'], app?: ApplicationRecord, prior?: ActionEventRefV1) => {",1)
 # Replace only open closing marker adjacent next declared function.
 for marker in ['  };\n  const change =','  };\n  const startPreparing =']:
  if marker in t:t=t.replace(marker,'  }, [actions, canEdit]);\n'+marker.split('\n',1)[1],1);break
 insert='  const startPreparing =' if kind=='application' else '  const save ='
 t=t.replace(insert,effect+insert,1)
 t=t.replace("        <p className=\"small muted\">{t('documents.personalHint')}</p>","        <p className=\"small muted\">{t('documents.personalHint')}</p>\n        {targetMissing && <Notice kind=\"warn\">{t('today.targetMissing')}</Notice>}",1) if kind=='document_task' else t.replace("        <p className=\"small muted\">{t('applications.hint')}</p>","        <p className=\"small muted\">{t('applications.hint')}</p>\n        {targetMissing && <Notice kind=\"warn\">{t('today.targetMissing')}</Notice>}",1)
 put(p,t)
p='frontend/src/screens/SourcesScreen.tsx';t=get(p).replace("import { useStore }", "import { useTranslation } from '@/lib/useTranslation';\nimport { useAdmissionsTarget } from '@/lib/admissionsNavigation';\nimport { useStore }",1)
t=t.replace("  const { results, summary, run } = useStore();", """  const { results: allResults, summary, run, savedProfile } = useStore(); const { t } = useTranslation(); const target = useAdmissionsTarget();
  const exactTarget = target?.target.kind === 'result' ? target : null;
  const exactUnavailable = exactTarget !== null && (exactTarget.profileId !== savedProfile?.id || !allResults.some(result => result.id === exactTarget.target.id));
  const results = exactTarget ? exactUnavailable ? [] : allResults.filter(result => result.id === exactTarget.target.id) : allResults;""",1)
t=t.replace("  if (results.length === 0) return <Empty", "  if (exactUnavailable) return <Notice kind=\"warn\">{t('today.targetMissing')}</Notice>;\n  if (results.length === 0) return <Empty",1);put(p,t)
# Preparation resolves exact existing target after its own data read, once; existing typed opener/access guards remain.
p='frontend/src/screens/PreparationScreen.tsx';t=get(p).replace("import { api }", "import { useAdmissionsTarget } from '@/lib/admissionsNavigation';\nimport { api }",1)
marker="  useSyncExternalStore(subscribe, () => t('shared.nav'));";t=t.replace(marker,marker+"\n  const exactTarget = useAdmissionsTarget(); const openedExact = useRef<string | null>(null);",1)
marker='  return <div className="preparation-page stack stack--loose">';insert='''  const exactKey = exactTarget?.screen === 'preparation' ? JSON.stringify(exactTarget) : null;
  const exactWrongCase = exactKey !== null && exactTarget?.profileId !== profileId;
  useEffect(() => {
    if (!exactKey || openedExact.current === exactKey || exactWrongCase || loading || !data || !isCurrent() || !exactTarget) return;
    const ref = exactTarget.target;
    if (ref.kind !== 'lesson' && ref.kind !== 'attempt_review') return;
    openedExact.current = exactKey;
    if (ref.kind === 'lesson') void startLesson(ref.lesson_id, ref.content_version);
    else { chooseMode('progress'); void openReview({ attempt_id: ref.attempt_id, lesson_id: ref.lesson_id, version: ref.content_version }); }
  }, [exactKey, exactWrongCase, loading, data, isCurrent, exactTarget, startLesson, chooseMode, openReview]);
''';assert marker in t;t=t.replace(marker,insert+marker+"\n    {exactWrongCase && <Notice kind=\"warn\">{t('today.targetMissing')}</Notice>}",1);put(p,t)
keys=[
('today.title','Your admissions Today','Поступление: ваши действия','Қабылдау: бүгінгі әрекеттеріңіз'),('today.hint','Saved personal actions and dates from your case. University acceptance is not assessed.','Сохранённые личные действия и даты вашего дела. Зачисление университетом здесь не оценивается.','Ісіңіздегі сақталған жеке әрекеттер мен күндер. Университетке қабылдану мұнда бағаланбайды.'),
('today.unavailable','Saved actions could not be confirmed. Refresh to try again.','Не удалось подтвердить сохранённые действия. Обновите сведения.','Сақталған әрекеттер расталмады. Мәліметтерді жаңартыңыз.'),('today.loading','Loading saved actions…','Загружаем сохранённые действия…','Сақталған әрекеттер жүктелуде…'),('today.lastConfirmed','Showing the last confirmed view.','Показано последнее подтверждённое состояние.','Соңғы расталған көрініс көрсетілген.'),('today.observed','Read from server','Прочитано с сервера','Серверден оқылды'),('today.refreshNeeded','The saved parts changed during reading. Refresh before opening an action.','Сведения изменились во время чтения. Обновите их перед переходом к действию.','Оқу кезінде мәліметтер өзгерді. Әрекетті ашпас бұрын жаңартыңыз.'),
('today.earlierDates','Earlier planning dates','Предыдущие даты планирования','Өткен жоспарлау күндері'),('today.current','Today','Сегодня','Бүгін'),('today.future','Upcoming personal actions','Предстоящие личные действия','Алдағы жеке әрекеттер'),('today.undated','Personal actions without a date','Личные действия без даты','Күні белгіленбеген жеке әрекеттер'),('today.optionalStudy','Optional study actions','Дополнительные учебные задачи','Қосымша оқу тапсырмалары'),('today.empty','No active personal actions are recorded yet. Add a document task or application.','Активных личных действий пока нет. Добавьте задачу по документу или заявку.','Белсенді жеке әрекеттер әлі жоқ. Құжат тапсырмасын не өтінішті қосыңыз.'),('today.document','Document task','Задача по документу','Құжат тапсырмасы'),('today.application','Application action','Действие по заявке','Өтініш әрекеті'),('today.study','Study task','Учебная задача','Оқу тапсырмасы'),('today.dateUnknown','Date not entered','Дата не указана','Күн көрсетілмеген'),('today.fallbackDate','Grouped using the display time zone; the original time zone is unknown.','Группа определяется в зоне отображения; исходный часовой пояс неизвестен.','Топ көрсетілім уақыт белдеуімен анықталған; бастапқы белдеу белгісіз.'),('today.minutes','planned study minutes','запланированных минут учёбы','жоспарланған оқу минуты'),('today.openExact','Open this record','Открыть эту запись','Осы жазбаны ашу'),('today.openEvidence','Review this programme evidence','Проверить источники этой программы','Осы бағдарламаның дереккөздерін тексеру'),('today.targetUnavailable','Action is unavailable or needs review.','Действие недоступно или требует пересмотра.','Әрекет қолжетімсіз немесе қайта қарауды қажет етеді.'),('today.targetMissing','This exact record is unavailable in the selected case. Refresh or select its original case.','Эта запись недоступна в выбранном деле. Обновите сведения или выберите исходное дело.','Бұл жазба таңдалған істе қолжетімсіз. Мәліметтерді жаңартыңыз не бастапқы істі таңдаңыз.'),('today.refresh','Refresh Today','Обновить Today','Today көрінісін жаңарту'),('today.sourceReview','Requirement reference needs review','Ссылку на требование нужно проверить','Талап сілтемесін тексеру қажет'),('today.dependencyMissing','An earlier required task is unavailable.','Предыдущая необходимая задача недоступна.','Алдыңғы қажетті тапсырма қолжетімсіз.'),('today.dependencyCycle','The task dependencies form a cycle. Edit them before continuing.','Зависимости образуют цикл. Исправьте их перед продолжением.','Тапсырма тәуелділіктері цикл құрайды. Жалғастырмас бұрын түзетіңіз.'),('today.dependencyNotReady','An earlier task has no completion report.','Для предыдущей задачи нет отметки о подготовке.','Алдыңғы тапсырмада аяқталу белгісі жоқ.'),('today.previousBinding','The completion report belongs to an earlier requirement.','Отметка о выполнении относится к прежнему требованию.','Орындалу белгісі бұрынғы талапқа қатысты.'),('today.notWaiver','Your not-needed mark does not waive an official requirement.','Ваша отметка «не нужно» не отменяет официальное требование.','«Қажет емес» белгіңіз ресми талапты жоймайды.'),('today.contextChanged','The application context changed. Review the earlier document report.','Сведения заявки изменились. Пересмотрите прежнюю отметку документа.','Өтініш мәліметтері өзгерді. Бұрынғы құжат белгісін қайта қараңыз.')]
p='frontend/src/lib/i18n.ts';t=get(p);import re
for i,name in enumerate(['EN','RU','KK'],1):
 m=re.search(r'const '+name+r'[^\n]*\{',t);assert m;pos=m.end();t=t[:pos]+'\n'+''.join('  '+json.dumps(row[0],ensure_ascii=False)+': '+json.dumps(row[i],ensure_ascii=False)+',\n' for row in keys)+t[pos:]
put(p,t)
print('External Today and exact target surfaces prepared; test proposals/root review pending, nothing applied.')
