import { useEffect, useRef, useState, type ReactNode } from 'react';
import { ArrowRight, Coins, GraduationCap, Trophy, User, X } from '@phosphor-icons/react';
import { useStore } from '@/lib/store';
import { castInput, get, setIn, type Path } from '@/lib/immutable';
import { CommaSeparatedInput } from './CommaSeparatedInput';
import { BookHelp, BookProfileProgress } from './BookUI';
import { Field, SaveFeedback } from './primitives';
import { ProfileRecoveryPanel } from './ProfileRecoveryPanel';

export function BookPreferences({ advanced, demoMode, onDemoMode, onStart, disabled }: {
  advanced: ReactNode; demoMode: boolean | undefined; onDemoMode: (value: boolean) => void;
  onStart: () => Promise<void>; disabled: boolean;
}) {
  const { profileDraft, setProfileDraft, saveProfile, dirty, loading, profileRecovery, capabilities, savedProfile, caseEpoch, currentAdmissionsCase, validation } = useStore();
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');
  const writeIntent = useRef(0);
  useEffect(() => { ++writeIntent.current; setSaved(false); setError(''); setSaving(false); }, [caseEpoch]);
  const countries = (get(profileDraft,['preferences','preferred_countries']) ?? []) as string[];
  const bind = (path: Path, cast: 'string' | 'number' | 'float' = 'string') => ({ value: String(get(profileDraft,path) ?? ''), onChange: (event: {target:{value:string}}) => { setProfileDraft(draft => setIn(draft,path,castInput(event.target.value,cast))); setSaved(false); } });
  const check = (key: string) => ({ checked: Boolean(get(profileDraft,['funding',key])), onChange: (event:{target:{checked:boolean}}) => { setProfileDraft(draft => setIn(draft,['funding',key],event.target.checked)); setSaved(false); } });
  const changeCountries = (items: string[]) => { setProfileDraft(draft => setIn(draft,['preferences','preferred_countries'],items)); setSaved(false); };
  const save = async () => {
    const identity = currentAdmissionsCase(); const intent = ++writeIntent.current;
    const current = () => { const now=currentAdmissionsCase(); return intent===writeIntent.current && now.scope===identity.scope && now.case_epoch===identity.case_epoch && (identity.profile_id===null || identity.profile_id===now.profile_id); };
    setSaving(true); setError(''); setSaved(false);
    try { await saveProfile(); if(current()) setSaved(true); }
    catch (failure) { if(current()) setError(failure instanceof Error ? failure.message : String(failure)); }
    finally { if(current()) setSaving(false); }
  };
  const start = async () => { setError(''); try { await onStart(); } catch (failure) { setError(failure instanceof Error ? failure.message : String(failure)); } };
  const year = Number(get(profileDraft,['context','intake_year']));
  const years = [...new Set([...(year ? [year] : []), ...Array.from({length:6},(_,i) => new Date().getFullYear()+i)])].sort();
  const currencyOptions = [...new Set([String(get(profileDraft,['funding','budget_currency']) ?? ''), ...(capabilities?.currency?.supported ?? ['USD','EUR','GBP'])])].filter(Boolean);
  return <div className="book-preferences"><BookProfileProgress step={2}/>
    <header className="screen__head"><p className="screen__eyebrow">Профиль абитуриента</p><h1 className="screen__title">Направление и бюджет</h1><p className="screen__lede">Укажи, что и где ты хочешь изучать, и какой бюджет ты планируешь.</p></header>
    <div className="profile-layout book-russian"><aside className="profile-rail"><nav className="profile-steps" aria-label="Разделы профиля"><div className="profile-rail-heading"><h2>Мой профиль</h2><p>Заполни профиль, чтобы мы могли подобрать для тебя подходящие программы.</p></div>{[{label:'Личные данные',href:'#/profile',Icon:User},{label:'Направление и бюджет',href:'#/preferences',Icon:Coins},{label:'Учёба и экзамены',href:'#/profile?section=academics',Icon:GraduationCap},{label:'Активности',href:'#/profile?section=activities',Icon:Trophy}].map(({label,href,Icon}) => <a key={href} href={href} className={href==='#/preferences'?'is-current':''}><Icon size={22}/>{label}<span>›</span></a>)}</nav><section className="profile-rail-progress"><strong>{dirty?'Есть несохранённые изменения':savedProfile?'Сохранённый профиль':'Анкета ещё не сохранена'}</strong><p>Настройки остаются редактируемыми.</p></section><BookHelp>Мы подберём программы, которые соответствуют твоим интересам, возможностям и бюджету.</BookHelp></aside>
      <div className="book-preferences__main"><div className="book-preferences__columns">
        <section><h2>Направление и локация</h2><p>Выбери предметную область и страны, которые тебя интересуют.</p><Field label="Что изучать" htmlFor="book-pref-field"><CommaSeparatedInput id="book-pref-field" items={(get(profileDraft,['context','intended_fields']) ?? []) as string[]} onItemsChange={items => setProfileDraft(draft => setIn(draft,['context','intended_fields'],items))}/></Field>
          <div className="field"><label className="field__label" htmlFor="book-pref-country">Страны обучения</label><div className="book-preferences__countries">{countries.map(country => <button type="button" key={country} onClick={() => changeCountries(countries.filter(value => value!==country))}>{country}<X size={13}/><span className="visually-hidden">Убрать страну</span></button>)}<select id="book-pref-country" value="" onChange={event => { if(event.target.value&&!countries.includes(event.target.value)) changeCountries([...countries,event.target.value]); }}><option value="">Добавить страну</option>{['United States','Canada','United Kingdom','Germany','Netherlands','Australia','Japan','Finland','Belgium','France','Singapore'].map(country => <option key={country} disabled={countries.includes(country)}>{country}</option>)}</select></div><details><summary>Указать другую страну</summary><CommaSeparatedInput aria-label="Другие страны обучения" items={countries} onItemsChange={changeCountries}/></details></div>
          <Field label="Год поступления" htmlFor="book-pref-year"><select id="book-pref-year" {...bind(['context','intake_year'],'number')}><option value="">Укажи год</option>{years.map(value => <option value={value} key={value}>{value}</option>)}</select></Field><Field label="Период поступления" htmlFor="book-pref-term"><select id="book-pref-term" {...bind(['context','intake_term'])}>{[['fall','Осень'],['spring','Весна'],['summer','Лето'],['winter','Зима']].map(([value,label]) => <option key={value} value={value}>{label}</option>)}</select></Field><BookHelp>В подборе учитываются направление, ступень и период поступления. Имя, контакты, оценки и бюджет в поисковые запросы не передаются.</BookHelp>
        </section>
        <section><h2>Бюджет и покрытие</h2><p>Укажи, какой бюджет семья может выделить, и какие условия финансирования тебе подходят.</p><div className="book-preferences__budget"><Field label="Годовой бюджет семьи" htmlFor="book-pref-budget"><input id="book-pref-budget" type="number" min={0} {...bind(['funding','max_annual_budget'],'float')}/></Field><Field label="Валюта" htmlFor="book-pref-currency"><select id="book-pref-currency" {...bind(['funding','budget_currency'])}>{currencyOptions.map(currency => <option key={currency}>{currency}</option>)}</select></Field></div>
          {capabilities?.currency?.stale_warning && <p className="notice notice--warn">{capabilities.currency.stale_warning}</p>}
          <h3>Какая помощь подходит</h3><div className="book-preferences__checks">{[['accepts_full_tuition','Полная оплата обучения подходит'],['must_cover_housing','Стипендия должна покрывать проживание'],['must_cover_meals','Стипендия должна покрывать питание'],['must_cover_health_insurance','Стипендия должна покрывать страховку'],['must_cover_books','Стипендия должна покрывать учебные материалы']].map(([key,label]) => <label key={key}><input type="checkbox" {...check(key!)}/><span>{label}</span></label>)}</div><details className="book-preferences__funding-extra"><summary>Дополнительные условия финансирования</summary><div className="book-preferences__checks">{[['accepts_partial','Частичное финансирование подходит'],['requires_full_ride','Необходимо полное покрытие расходов']].map(([key,label])=><label key={key}><input type="checkbox" {...check(key!)}/><span>{label}</span></label>)}</div></details><BookHelp><strong>Стипендии и гранты</strong><br/>Наличие финансирования зависит от университета и не гарантировано. Требование к покрытию — условие подбора, а не подтверждение присуждения стипендии.</BookHelp>
        </section>
      </div><details className="book-preferences__advanced"><summary>Расширенные условия, приоритеты и пересчёт результатов</summary>{advanced}</details><div className="book-preferences__mode"><label><input type="checkbox" checked={demoMode ?? false} disabled={demoMode===undefined} onChange={event => onDemoMode(event.target.checked)}/>Демонстрационный подбор — синтетические данные, без чтения сайтов</label>{demoMode===false&&<p>Живой подбор читает публичные официальные страницы с учётом robots.txt. Недоступные страницы и неизвестные факты будут отмечены.</p>}</div>
      {validation&&!validation.can_proceed&&<p className="notice notice--risk">Нельзя начать подбор: {validation.summary}</p>}{demoMode===undefined&&<p role="status">Загружаем режим поиска…</p>}{profileRecovery&&<ProfileRecoveryPanel/>}{error&&<p role="alert">{error}</p>}<SaveFeedback saving={saving||Boolean(profileRecovery?.dispatching)} saved={saved} dirty={dirty} failed={Boolean(error)} uncertain={Boolean(profileRecovery&&profileRecovery.entry&&['pending','unknown','accepted'].includes(profileRecovery.entry.status))}/><footer className="book-preferences__actions"><button className="btn" type="button" disabled={loading||saving} onClick={()=>void save()}>Сохранить как черновик</button><button className="btn btn--primary" type="button" disabled={disabled||saving||Boolean(profileRecovery)} onClick={()=>void start()}>{loading?'Запускаем…':'Начать подбор'}<ArrowRight size={19}/></button></footer><p className="book-preferences__note">Ты можешь изменить эти данные позже.</p></div>
    </div>
  </div>;
}
