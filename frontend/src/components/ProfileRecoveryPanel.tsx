import { FileText, User, GraduationCap, Trophy, Coins } from '@phosphor-icons/react';
import { getLocale } from '@/lib/i18n';
import { useTranslation } from '@/lib/useTranslation';
import { BookHelp } from './BookUI';
import { useEffect, useMemo, useRef, useState } from 'react';
import { useStore, toDraft } from '@/lib/store';
import { compareProfiles, type ProfileFieldValue } from '@/lib/profileMerge';
function describe(field: ProfileFieldValue): string { const ru=getLocale()!=='en'; return !field.present ? ru?'Не указано':'Not provided' : field.value === null ? ru?'Пустое значение (null)':'Empty (null)' : typeof field.value === 'object' ? JSON.stringify(field.value) : String(field.value); }
function fieldName(path: string[]): string {
  const labels: Record<string, string> = { display_name: 'Applicant display name', 'academics.gpa.raw_value': 'GPA / average', 'academics.gpa.raw_scale_max': 'Maximum on your grade scale', 'context.intake_year': 'Intake year', 'context.intended_fields': 'Field of study', 'funding.max_annual_budget': 'Annual budget' };
  const ruLabels:Record<string,string>={display_name:'Имя в профиле','academics.gpa.raw_value':'Средний балл','academics.gpa.raw_scale_max':'Максимум шкалы оценок','context.intake_year':'Год поступления','context.intended_fields':'Направление обучения','funding.max_annual_budget':'Годовой бюджет'};
  return (getLocale()==='en'?labels:ruLabels)[path.join('.')] ?? path.map(part => part.replace(/_/g, ' ').replace(/^./, letter => letter.toUpperCase())).join(' → ');
}
export function ProfileRecoveryPanel({onContinue,asPage=false}:{onContinue?:()=>void;asPage?:boolean}={}) {
  const Title=asPage?'h1':'h2';
  const headingRef=useRef<HTMLHeadingElement>(null);
  const {locale}=useTranslation(); const ru=locale!=='en';
  const { profileRecovery:view, profileDraft, loading, retryProfileWrite, compareSavedProfile,
    applyProfileComparison, clearConfirmedProfileWrites, exportProfileWrites } = useStore();
  const [choices,setChoices] = useState<Record<string,'local'|'server'>>({});
  const [localError,setLocalError] = useState<string|null>(null);
  const fingerprint = JSON.stringify(profileDraft);
  useEffect(()=>{ if(asPage&&view) headingRef.current?.focus({preventScroll:true}); },[asPage,view?.entry?.command.command_id,view?.server?.revision]);
  const rows = useMemo(() => view?.server ? compareProfiles(view.base,profileDraft,toDraft(view.server)) : [], [view,profileDraft]);
  useEffect(() => { setChoices({}); setLocalError(null); }, [view?.server?.revision, view?.entry?.command.command_id, fingerprint]);
  if (!view) return <details className="recovery-history"><summary>Profile recovery history for this tab</summary>
    {localError && <p role="alert">{localError}</p>}
    <button className="btn" type="button" onClick={() => { try { clearConfirmedProfileWrites(); } catch (e) { setLocalError(String(e)); } }}>Clear confirmed profile recovery history</button>
  </details>;
  const exportOriginals = () => {
    try {
      const blob = new Blob([exportProfileWrites()], { type:'application/json' });
      const url = URL.createObjectURL(blob);
      try { const link = document.createElement('a'); link.href=url; link.download='unimatch-profile-recovery.json'; link.click(); }
      finally { URL.revokeObjectURL(url); }
    } catch (e) { setLocalError(String(e)); }
  };
  if(ru) return <section aria-label="Восстановление сохранения профиля" className={`book-recovery ${view.server?'book-recovery--comparison':''}`}>
    {view.server&&<aside className="book-community-nav"><h3>Мой профиль</h3><p>Сравни значения перед сохранением.</p>{[['Личные данные',User],['Учёба',GraduationCap],['Активности',Trophy],['Бюджет',Coins]].map(([label,Icon])=>{const Symbol=Icon as typeof User;return <a href="#/profile" key={String(label)} onClick={event=>{event.preventDefault();document.querySelector('#profile-editing')?.scrollIntoView({block:'start'});}}><Symbol size={22}/>{String(label)}</a>;})}</aside>}
    <div className="book-recovery__main"><p className="book-breadcrumb">← Профиль абитуриента</p><Title ref={headingRef} tabIndex={-1}>{view.server?'Профиль изменился в другой вкладке':view.entry?.status==='conflict'?'Профиль изменился в другой вкладке':view.entry?.status==='failed'?'Изменения не сохранены':'Проверяем сохранение'}</Title><p className="book-recovery__lede">{view.server?'Выбери, какую версию использовать для каждого поля. Ты можешь объединить изменения в черновике, а затем сохранить профиль.':view.entry?.status==='conflict'?'Нужно загрузить текущую версию сервера и сравнить её с твоими изменениями. Исходный запрос сохранён отдельно.':view.entry?.status==='failed'?'Сервер подтвердил отказ. Твой черновик и исходный запрос сохранены отдельно.':'Ответ не пришёл или ещё не подтверждён. Сохранение могло пройти. Не создавай новую анкету — проверь исходное сохранение.'}</p>
    <BookHelp><strong>{view.server?'Конфликт сохранения':view.entry?.status==='failed'?'Сохранение отклонено':'Ответ не подтверждён'}</strong><br/>{view.server?'После применения выбранных значений к черновику нажми «Сохранить», чтобы обновить профиль.':'Исходный запрос не заменяется новой записью. Текущий ввод остаётся отдельным черновиком.'}</BookHelp>
    <details className="book-recovery__diagnostic"><summary>Подробности состояния</summary><p role="status">{view.message}</p>{view.entry&&<p>Статус: {view.entry.status}. Исходный запрос хранится в этой вкладке до подтверждения результата; при выходе из аккаунта он удаляется.</p>}</details>{localError&&<p role="alert">{localError}</p>}
    {view.server?<><p className="book-muted">Сохранённая версия: {view.server.revision}. Сравнение само по себе ничего не отправляет на сервер.</p>{rows.length===0&&<BookHelp><strong>Значения уже совпадают</strong><br/>Применение обновит основу черновика до прочитанной ревизии. Новый запрос сохранения не отправляется.</BookHelp>}{rows.map(row=><fieldset className="book-recovery__field" key={JSON.stringify(row.path)}><legend>{fieldName(row.path)}</legend><p>Значение отличается в разных версиях профиля.</p><div className="book-recovery__versions"><label className={(choices[JSON.stringify(row.path)]??(row.conflict?undefined:row.proposed))==='local'?'is-selected':''}><strong>Мой черновик</strong><small>Твои последние изменения (текущий ввод).</small><span><input type="radio" name={JSON.stringify(row.path)} value="local" checked={(choices[JSON.stringify(row.path)]??(row.conflict?undefined:row.proposed))==='local'} onChange={()=>setChoices(previous=>({...previous,[JSON.stringify(row.path)]:'local'}))}/>{describe(row.local)}</span></label><div><strong>Исходное значение</strong><small>Значение в профиле до изменений.</small><span>{describe(row.base)}</span></div><label className={(choices[JSON.stringify(row.path)]??(row.conflict?undefined:row.proposed))==='server'?'is-selected':''}><strong>Текущее значение на сервере</strong><small>Сохранённая версия при последнем чтении.</small><span><input type="radio" name={JSON.stringify(row.path)} value="server" checked={(choices[JSON.stringify(row.path)]??(row.conflict?undefined:row.proposed))==='server'} onChange={()=>setChoices(previous=>({...previous,[JSON.stringify(row.path)]:'server'}))}/>{describe(row.server)}</span></label></div></fieldset>)}<BookHelp><strong>Объединить и внести другие изменения</strong><br/>Применение меняет только текущий черновик. Затем можно продолжить редактирование и сохранить его явно.</BookHelp><button className="btn btn--primary" type="button" disabled={loading||rows.some(row=>row.conflict&&!choices[JSON.stringify(row.path)])} onClick={()=>{try{applyProfileComparison(choices,fingerprint);}catch(error){setLocalError(String(error));}}}>Применить к черновику</button><p className="book-recovery__after">Затем нажми «Сохранить», чтобы обновить профиль.</p></>:<>
    {view.entry&&<div className="book-recovery__snapshots"><article className="book-card"><h3><span className="book-icon-tile"><FileText size={28}/></span>Отправленные изменения</h3><dl><dt>Имя</dt><dd>{String(view.entry.draft.display_name??'Не указано')}</dd><dt>Время отправки</dt><dd>Не записано в журнале</dd></dl><p>Исходный запрос сохраняется до подтверждения результата.</p></article><article className="book-card"><h3><span className="book-icon-tile"><FileText size={28}/></span>Текущий черновик</h3><dl><dt>Имя</dt><dd>{String(profileDraft.display_name??'Не указано')}</dd><dt>Статус</dt><dd>Текущий ввод хранится отдельно от исходного запроса.</dd></dl></article></div>}
    {view.entry&&['pending','unknown','accepted'].includes(view.entry.status)&&<button className="btn btn--primary" type="button" disabled={loading} onClick={()=>void retryProfileWrite()}>Проверить исходное сохранение →</button>}
    {(view.entry?.status==='conflict'||!view.entry)&&<button className="btn btn--primary" type="button" disabled={loading} onClick={()=>void compareSavedProfile()}>Загрузить сохранённый профиль для сравнения</button>}
    {view.entry?.status==='failed'&&<button className="btn" type="button" onClick={()=>{try{clearConfirmedProfileWrites();}catch(error){setLocalError(String(error));}}}>Убрать подтверждённый отказ и оставить черновик</button>}
    </>}
    <button className="btn btn--ghost book-recovery__continue" type="button" onClick={()=>{onContinue?.();window.requestAnimationFrame(()=>{document.querySelector('#profile-editing')?.scrollIntoView({block:'start'});(document.querySelector('#profile-editing input') as HTMLInputElement|null)?.focus();});}}>Продолжить редактирование</button><details className="book-recovery__tools"><summary>Экспорт и подтверждённая история</summary><button className="btn" type="button" onClick={exportOriginals}>Экспортировать данные восстановления</button><button className="btn" type="button" onClick={()=>{try{clearConfirmedProfileWrites();}catch(error){setLocalError(String(error));}}}>Очистить подтверждённую историю</button></details></div>
  </section>;
  return <section aria-label="Profile save recovery" className="panel recovery-panel">
    <h2>{view.entry?.status === 'conflict' ? 'Your profile changed in another tab' : view.server ? 'Review your profile changes' : view.entry?.status === 'failed' ? 'Your profile was not saved' : 'Confirm your last save'}</h2><p role="status">{view.message}</p>
    {view.entry && !view.server && <div className="recovery-snapshots"><article><h3>Changes you sent</h3><p>{String(view.entry.draft.display_name ?? 'Applicant profile')}</p><span className="small muted">The original request is retained until its outcome is confirmed.</span></article><article><h3>Your current draft</h3><p>{String(profileDraft.display_name ?? 'Applicant profile')}</p><span className="small muted">Current form content is kept separately from the original request.</span></article></div>}
    {view.entry && <details className="recovery-history"><summary>Save details</summary><p>Status: {view.entry.status}. This browser tab retains the original request; it is removed on sign-out.</p></details>}
    {localError && <p role="alert">{localError}</p>}
    {view.server ? <>
      <p>Saved version {view.server.revision}. Review each difference. This comparison does not save to the server.</p>
      {rows.map(row => <fieldset key={JSON.stringify(row.path)}>
        <legend>{fieldName(row.path)}{row.conflict ? ' — choose a value' : ''}</legend>
        <p>Before: {describe(row.base)}</p>
        {(['local','server'] as const).map(choice => <label key={choice}>
          <input type="radio" name={JSON.stringify(row.path)} value={choice}
            checked={(choices[JSON.stringify(row.path)] ?? (row.conflict ? undefined : row.proposed)) === choice}
            onChange={() => setChoices(previous => ({ ...previous,[JSON.stringify(row.path)]:choice }))} />
          {choice === 'local' ? 'Your current edits' : 'Saved profile'}: {describe(row[choice])}
        </label>)}
      </fieldset>)}
      <button className="btn" type="button" disabled={loading || rows.some(row => row.conflict && !choices[JSON.stringify(row.path)])}
        onClick={() => { try { applyProfileComparison(choices,fingerprint); } catch(e) { setLocalError(String(e)); } }}>Apply comparison to draft</button>
      <p>You can keep editing or leave this comparison. After applying, press Save explicitly.</p>
    </> : <>
      {view.entry && ['pending','unknown','accepted'].includes(view.entry.status) && <button className="btn" type="button" disabled={loading} onClick={() => void retryProfileWrite()}>Confirm original save</button>}
      {(view.entry?.status === 'conflict' || !view.entry) && <button className="btn" type="button" disabled={loading} onClick={() => void compareSavedProfile()}>Load saved profile for comparison</button>}
      {view.entry?.status === 'failed' && <button className="btn" type="button" onClick={() => { try { clearConfirmedProfileWrites(); } catch(e) { setLocalError(String(e)); } }}>Clear confirmed refusal and keep edits</button>}
    </>}
    <button className="btn" type="button" onClick={exportOriginals}>Export profile recovery for this tab</button>
    <button className="btn" type="button" onClick={() => { try { clearConfirmedProfileWrites(); } catch(e) { setLocalError(String(e)); } }}>Clear confirmed recovery history</button>
  </section>;
}
