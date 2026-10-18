import { ArrowRight, Buildings, CalendarBlank, Check, Info } from '@phosphor-icons/react';
import type { ReactNode } from 'react';
import type { ScreenId } from '@/App';
import { useTranslation } from '@/lib/useTranslation';
import { getLocale } from '@/lib/i18n';

export function bookCopy(english: string, russian: string): string { return getLocale() === 'en' ? english : russian; }
export function BookGlobe({ compact = false, note = true }: { compact?: boolean; note?: boolean }) {
  return <div className={`book-globe${compact ? ' book-globe--compact' : ''}`} aria-hidden="true">
    <img src="/book/globe.webp" alt="" width="1254" height="1254" />
    <span className="book-globe__place book-globe__place--groningen">Гронинген</span><span className="book-globe__place book-globe__place--tokyo">Токио</span><span className="book-globe__place book-globe__place--astana">Астана</span>
    {note && <p className="book-handnote">Больше возможностей<br />для твоего завтра<span /></p>}
  </div>;
}
export function BookLogo({ university, className = '' }: { university: string; className?: string }) {
  const source = /groningen/i.test(university) ? 'rug' : /leuven/i.test(university) ? 'kuleuven' : /tokyo/i.test(university) ? 'tokyo' : null;
  return <span className={`book-university-logo ${source==='rug'?'book-university-logo--rug':source==='kuleuven'?'book-university-logo--ku':''} ${className}`}>{source==='rug'?'RUG':source==='kuleuven'?'KU':source ? <img src={`/book/${source}.${source==='tokyo'?'png':'ico'}`} alt="" /> : <Buildings size={24} aria-hidden="true" />}</span>;
}
export function BookFooter({ demo = false }: { demo?: boolean }) {
  const { locale } = useTranslation();
  return <footer className="book-footer"><span>{demo ? locale === 'en' ? 'Demonstration data. University information must be checked against official sources.' : 'Демонстрационные данные. Требования проверяй по официальным источникам.' : locale === 'en' ? 'Your decisions, supported by sources.' : 'Твои решения — с опорой на источники.'}</span><span><strong>unimatch</strong><i />{locale === 'en' ? 'More possibilities for your tomorrow' : 'Больше возможностей для твоего завтра'}</span></footer>;
}
export function BookWorkflow({ stage = 1, resultCount = 0, onNavigate }: { stage?: number; resultCount?: number; onNavigate: (screen: ScreenId) => void }) {
  const { locale } = useTranslation();
  const items: { title:string; detail:string; screen:ScreenId }[] = locale === 'en' ? [
    {title:'Profile',detail:'Your application context',screen:'profile'},{title:'Find',detail:`${resultCount} programmes`,screen:'shortlist'},{title:'Plan',detail:'Dates and tasks',screen:'approved'},{title:'Applications',detail:'Track your next steps',screen:'applications'},
  ] : [{title:'Профиль',detail:'Твои данные и цели',screen:'profile'},{title:'Подбор',detail:`${resultCount} программ`,screen:'shortlist'},{title:'План',detail:'Сроки и задачи',screen:'approved'},{title:'Заявки',detail:'Следующие шаги',screen:'applications'}];
  return <nav className="book-workflow" aria-label={locale==='en'?'Admissions journey':'Путь поступления'}>{items.map((item,i)=><button key={item.screen} type="button" aria-current={stage===i?'step':undefined} onClick={()=>onNavigate(item.screen)}><span className={`book-workflow__number ${stage>=i?'is-reached':''}`}>{stage>i?<Check size={20} weight="bold" />:i+1}</span><span><strong>{item.title}</strong><small>{item.detail}</small></span>{i<3&&<i />}</button>)}</nav>;
}
export function BookPageHeading({ title, children, globe = false, crumb }: { title:ReactNode; children?:ReactNode; globe?:boolean; crumb?:string }) {
 return <div className={`book-page-heading${globe?' book-page-heading--globe':''}`}>{crumb&&<p className="book-breadcrumb">{crumb}</p>}<h1>{title}</h1>{children&&<p>{children}</p>}{globe&&<BookGlobe compact />}</div>;
}
export function BookIntake({ year, term }: {year?: number;term?:string}) {
 const { locale }=useTranslation();return <div className="book-intake"><span className="book-icon-tile"><CalendarBlank size={23} /></span><span><strong>{locale==='en'?'Intake':'Поступление'} {year??'—'}</strong><small>{term ? (locale==='en'?term:`${({fall:'Осень',spring:'Весна',summer:'Лето',winter:'Зима'} as Record<string,string>)[term.toLowerCase()]??term}`):locale==='en'?'Choose your target intake':'Укажи планируемый период поступления'}</small></span></div>;
}
export function BookHelp({children}:{children:ReactNode}) {return <div className="book-help" role="note"><Info size={22} weight="fill" /><span>{children}</span></div>;}
export function BookProfileProgress({ step,total=4,showSteps=true }: { step:number;total?:4|5;showSteps?:boolean }) {
  return <div className="book-profile-progress"><a href="#/home"><span aria-hidden="true">←</span>Профиль абитуриента</a>{showSteps&&<><p>Шаг {step} из {total}</p><div aria-hidden="true">{Array.from({length:total},(_,index)=>index+1).map(index=><i className={index<=step?'is-reached':''} key={index}/>)}</div></>}</div>;
}
export function BookAction({children,onClick}:{children:ReactNode;onClick:()=>void}) {return <button className="btn btn--primary" type="button" onClick={onClick}>{children}<ArrowRight size={18}/></button>;}
