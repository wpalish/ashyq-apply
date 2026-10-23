import { GraduationCap, Plus } from '@phosphor-icons/react';
import { get } from '@/lib/immutable';

export function BookAcademics({ draft, onGrades, onTests }: {
  draft: Record<string, unknown>; onGrades: () => void; onTests: () => void;
}) {
  const value = (path: string[]) => get(draft, path);
  const grades = (value(['academics','subject_grades']) ?? []) as { subject?: string; grade?: { raw_value?: number } }[];
  const gpa = value(['academics','gpa','raw_value']);
  return <div className="book-academics">
    <section className="panel"><header><h2>Среднее образование</h2><button type="button" className="book-text-action" onClick={onGrades}>Изменить</button></header>
      <div className="book-academics__school"><div><small>Страна</small><strong>{String(value(['context','education_country']) || 'Не указана')}</strong></div><div><small>Система образования</small><strong>{String(value(['context','education_system']) || 'Не указана')}</strong></div><div><small>Окончание обучения</small><strong>{String(value(['context','graduation_date']) || 'Не указано')}</strong></div></div>
      <div className="book-academics__grades"><section><h3>Средний балл (GPA)</h3><strong>{gpa == null ? 'Не указан' : `${String(gpa)} из ${String(value(['academics','gpa','raw_scale_max']) ?? '?')}`}</strong><p>Исходная шкала, без автоматического пересчёта</p></section><section><h3>Оценки по предметам</h3>{grades.length ? grades.map((grade,index) => <button type="button" key={index} onClick={onGrades}><span>{grade.subject || 'Предмет не указан'}</span><span>{grade.grade?.raw_value ?? 'Нет оценки'} ›</span></button>) : <button type="button" onClick={onGrades}>Добавить оценки по предметам ›</button>}</section></div>
    </section>
    <section className="panel"><h2>Экзамены</h2><p>Добавь результаты экзаменов, если они у тебя есть. Не все экзамены обязательны — это зависит от программы и университета.</p>
      {[{key:'ielts',name:'IELTS',path:['academics','ielts','overall']},{key:'sat',name:'SAT',path:['academics','sat','total']}].map(exam => <article className="book-academics__exam" key={exam.key}><span className={`book-academics__exam-logo book-academics__exam-logo--${exam.key}`}>{exam.name}</span><div><strong>{exam.name}</strong><span>{value(exam.path) == null ? 'Результат не указан' : String(value(exam.path))}</span></div><button className="btn btn--sm" type="button" onClick={onTests}>{value(exam.path) == null ? <><Plus size={17}/>Добавить</> : 'Изменить'}</button></article>)}
      <button className="book-academics__add" type="button" onClick={onTests}><GraduationCap size={28}/><span><strong>Добавить другой экзамен</strong><small>Например, TOEFL, IB, AP и другие</small></span><span>›</span></button>
    </section>
  </div>;
}
