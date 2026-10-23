import { Plus, Trash, Trophy } from '@phosphor-icons/react';
import { CommaSeparatedInput } from './CommaSeparatedInput';
import { Field } from './primitives';
import { castInput, get, setIn, type Path } from '@/lib/immutable';
import { useStore } from '@/lib/store';

export function BookActivities() {
  const { profileDraft, setProfileDraft } = useStore();
  const activities = (get(profileDraft,['activities']) ?? []) as Record<string,unknown>[];
  const achievements = (get(profileDraft,['achievements']) ?? []) as Record<string,unknown>[];
  const bind = (path: Path, cast: 'string' | 'number' | 'float' = 'string') => ({
    value: String(get(profileDraft,path) ?? ''),
    onChange: (event: { target: { value: string } }) => setProfileDraft(draft => setIn(draft,path,castInput(event.target.value,cast))),
  });
  const remove = (kind: 'activities' | 'achievements', index: number) => setProfileDraft(draft => setIn(draft,[kind],((get(draft,[kind]) ?? []) as unknown[]).filter((_,i) => i !== index)));
  const append = (kind: 'activities' | 'achievements', value: Record<string,unknown>) => setProfileDraft(draft => setIn(draft,[kind],[...((get(draft,[kind]) ?? []) as unknown[]),value]));
  const evidence = (kind: 'activities' | 'achievements', index: number) => <Field label="Ссылка на подтверждение (необязательно)" htmlFor={`book-${kind}-evidence-${index}`} hint="Ссылки на сертификат, статью, фото или видео. Несколько адресов разделяй запятыми."><CommaSeparatedInput id={`book-${kind}-evidence-${index}`} items={(get(profileDraft,[kind,index,'evidence_links']) ?? []) as string[]} onItemsChange={items => setProfileDraft(draft => setIn(draft,[kind,index,'evidence_links'],items))}/></Field>;
  return <div className="book-activities">
    <section className="panel"><h2>Активности</h2><p>Добавь проекты, клубы, волонтёрство или другую значимую деятельность.</p>
      {activities.map((_,index) => <article className="book-activities__item" key={index}>
        <div className="book-activities__delete"><button type="button" onClick={() => remove('activities',index)}><Trash size={16}/>Удалить</button></div>
        <div className="grid-2"><Field label="Название активности" htmlFor={`book-activity-name-${index}`}><input id={`book-activity-name-${index}`} {...bind(['activities',index,'name'])}/></Field><Field label="Роль" htmlFor={`book-activity-role-${index}`}><input id={`book-activity-role-${index}`} {...bind(['activities',index,'role'])}/></Field><Field label="Продолжительность, месяцев" htmlFor={`book-activity-months-${index}`}><input id={`book-activity-months-${index}`} type="number" min={0} {...bind(['activities',index,'duration_months'],'number')}/></Field><Field label="Часов в неделю" htmlFor={`book-activity-hours-${index}`}><input id={`book-activity-hours-${index}`} type="number" min={0} step="0.5" {...bind(['activities',index,'hours_per_week'],'float')}/></Field></div>
        <Field label="Описание и результат" htmlFor={`book-activity-result-${index}`}><textarea id={`book-activity-result-${index}`} rows={3} {...bind(['activities',index,'measurable_outcome'])}/></Field>{evidence('activities',index)}
        <details className="book-activities__extra"><summary>Категория, ответственность и другие сведения</summary><div className="grid-2"><Field label="Категория" htmlFor={`book-activity-category-${index}`}><input id={`book-activity-category-${index}`} {...bind(['activities',index,'category'])}/></Field><Field label="Ответственность" htmlFor={`book-activity-responsibility-${index}`}><select id={`book-activity-responsibility-${index}`} {...bind(['activities',index,'responsibility_level'])}>{[['participant','Участник'],['contributor','Исполнитель'],['coordinator','Координатор'],['leader','Руководитель'],['founder','Основатель']].map(([value,label]) => <option value={value} key={value}>{label}</option>)}</select></Field><Field label="Недель в году" htmlFor={`book-activity-weeks-${index}`}><input id={`book-activity-weeks-${index}`} type="number" {...bind(['activities',index,'weeks_per_year'],'number')}/></Field><Field label="Влияние на других" htmlFor={`book-activity-impact-${index}`}><textarea id={`book-activity-impact-${index}`} {...bind(['activities',index,'impact_on_others'])}/></Field></div></details>
      </article>)}
      <button className="book-academics__add" type="button" onClick={() => append('activities',{name:'',category:'',role:'',duration_months:null,hours_per_week:null,weeks_per_year:null,responsibility_level:'participant',measurable_outcome:null,impact_on_others:null,evidence_links:[]})}><Plus size={24}/><strong>Добавить ещё активность</strong></button>
    </section>
    <section className="panel"><h2>Достижения</h2><p>Добавь награды, стипендии, призовые места или другие значимые достижения (необязательно).</p>
      {!achievements.length && <div className="book-activities__empty"><Trophy size={28}/><strong>Пока нет достижений</strong><p>Ты можешь добавить свои достижения, если хочешь.</p></div>}
      {achievements.map((_,index) => <article className="book-activities__item" key={index}><div className="book-activities__delete"><button type="button" onClick={() => remove('achievements',index)}><Trash size={16}/>Удалить</button></div><div className="grid-2"><Field label="Название достижения" htmlFor={`book-achievement-name-${index}`}><input id={`book-achievement-name-${index}`} {...bind(['achievements',index,'name'])}/></Field><Field label="Уровень" htmlFor={`book-achievement-level-${index}`}><select id={`book-achievement-level-${index}`} {...bind(['achievements',index,'level'])}>{[['school','Школьный'],['city','Городской'],['regional','Региональный'],['national','Национальный'],['international','Международный']].map(([value,label]) => <option key={value} value={value}>{label}</option>)}</select></Field><Field label="Год" htmlFor={`book-achievement-year-${index}`}><input id={`book-achievement-year-${index}`} type="number" {...bind(['achievements',index,'year'],'number')}/></Field><Field label="Призовое место" htmlFor={`book-achievement-place-${index}`}><input id={`book-achievement-place-${index}`} {...bind(['achievements',index,'placement'])}/></Field></div><Field label="Критерий отбора" htmlFor={`book-achievement-selection-${index}`}><textarea id={`book-achievement-selection-${index}`} {...bind(['achievements',index,'selection_criterion'])}/></Field>{evidence('achievements',index)}</article>)}
      <button className="btn" type="button" onClick={() => append('achievements',{name:'',level:'school',year:new Date().getFullYear(),placement:null,selection_criterion:null,evidence_links:[]})}><Plus size={19}/>Добавить достижение</button>
    </section>
  </div>;
}
