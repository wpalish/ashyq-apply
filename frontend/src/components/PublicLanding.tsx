import { useState } from 'react';
import { Coins, FileText, GraduationCap, MagnifyingGlass, MapPin, X } from '@phosphor-icons/react';
import { savePublicSearchIntent } from '@/lib/publicSearchIntent';
import { useTranslation } from '@/lib/useTranslation';
import type { Locale } from '@/lib/i18n';
import { BookFooter, BookGlobe } from './BookUI';

export function PublicLanding() {
  const { locale, setLocale } = useTranslation(); const ru=locale!=='en';
  const [subject, setSubject] = useState('Computer Science');
  const [country, setCountry] = useState(''); const [budget, setBudget] = useState('60000');
  const features = ru ? [
    {Icon:GraduationCap,title:<>Требования<br />и сроки</>,text:<>Узнай, что нужно<br />для поступления</>},
    {Icon:Coins,title:<>Варианты<br />финансирования</>,text:<>Стипендии, гранты<br />и примерные расходы</>},
    {Icon:FileText,title:'Следующие шаги',text:<>План под твои цели<br />и сроки</>},
  ] : [{Icon:GraduationCap,title:'Requirements and dates',text:'Understand what is needed to apply'},{Icon:Coins,title:'Funding options',text:'Scholarships, grants and comparable costs'},{Icon:FileText,title:'Next steps',text:'A plan for your goals and dates'}];
  return <div className="landing book-window">
    <header className="landing__header"><a className="landing__brand" href="#/welcome" aria-label="Unimatch home"><img src="/brand/unimatch-orbit.svg" alt="" />unimatch</a><nav aria-label="Public navigation"><a href="#how-it-works">{ru?'Как это работает':'How it works'}</a><a href="#/sign-in?create=1">{ru?'Программы':'Programmes'}</a></nav><label className="book-language"><span className="visually-hidden">{ru?'Язык':'Language'}</span><select value={locale} onChange={event=>setLocale(event.target.value as Locale)}><option value="ru">Рус</option><option value="kk">Қаз</option><option value="en">Eng</option></select></label><a className="landing__sign-in" href="#/sign-in">{ru?'Войти':'Sign in'}</a><a className="btn btn--primary landing__start" href="#/sign-in?create=1">{ru?'Начать':'Start'}</a></header>
    <main>
      <section className="landing__hero" aria-labelledby="landing-title"><div className="landing__hero-copy"><p className="book-caption">{ru?'ОБРАЗОВАНИЕ ЗА РУБЕЖОМ':'STUDY ABROAD'}</p><h1 id="landing-title">{ru?<>Найди, где учиться.<br />Пойми, что делать дальше.</>:<>Find where to study.<br />Know what comes next.</>}</h1><p>{ru?<>Программы, куда ты можешь поступить, требования,<br className="desktop-only" /> варианты финансирования и следующие шаги —<br className="desktop-only" /> в одном месте.</>:'Programmes, requirements, funding options and next steps — together in one place.'}</p></div><BookGlobe note={false}/></section>
      <form className="landing__search" aria-label="Plan your university search" onSubmit={event=>{event.preventDefault();savePublicSearchIntent({subject:subject.trim(),country,budget:budget===''?null:Number(budget)});window.location.hash='#/sign-in?create=1';}}>
        <label><span>{ru?'Что изучать?':'What do you want to study?'}</span><span className="book-search-field"><MagnifyingGlass size={20}/><input value={subject} maxLength={120} required onChange={event=>setSubject(event.target.value)} aria-label={ru?'Что изучать?':'What do you want to study?'}/><button type="button" aria-label={ru?'Очистить направление':'Clear subject'} onClick={()=>setSubject('')}><X size={16}/></button></span></label>
        <label><span>{ru?'Куда?':'Where?'}</span><span className="book-search-field"><MapPin size={20}/><select value={country} onChange={event=>setCountry(event.target.value)} aria-label={ru?'Куда?':'Where?'}><option value="">{ru?'Весь мир':'Explore worldwide'}</option>{['Canada','Germany','Netherlands','United Kingdom','United States','Japan','Australia'].map(value=><option key={value}>{value}</option>)}</select></span></label>
        <label><span>{ru?'Годовой бюджет семьи':'Annual family budget (USD)'}</span><span className="book-search-field"><Coins size={20}/><span className="book-budget-prefix">{ru?'До $':'USD '}</span><input aria-label={ru?'Годовой бюджет семьи':'Annual family budget (USD)'} type="number" min={0} max={1000000} placeholder={ru?'Уточняется':'Not decided yet'} value={budget} onChange={event=>setBudget(event.target.value)}/></span></label>
        <button className="btn btn--primary" type="submit"><MagnifyingGlass size={20}/>{ru?'Найти программы':'Find programmes'}</button>
      </form>
      <div className="landing__topics"><span>{ru?'Популярные направления:':'Popular fields:'}</span>{['Computer Science','Business','Engineering','Medicine','Art & Design'].map(value=><button type="button" key={value} aria-pressed={subject===value} onClick={()=>setSubject(value)}>{value}</button>)}</div>
      <div className="landing__mobile-globe"><BookGlobe note={false}/></div>
      <section className="landing__steps" id="how-it-works" aria-label={ru?'Как это работает':'How it works'}>{features.map(({Icon,title,text},i)=><article key={i}><span className="book-feature-icon"><Icon size={32}/></span><div><h2>{title}</h2><p>{text}</p></div></article>)}</section>
      <section className="landing__promise"><div><h2>{ru?'Готов разобраться подробнее?':'Ready to explore further?'}</h2><p>{ru?'Создай аккаунт, чтобы сохранять программы, сравнивать их и составлять свой план.':'Create an account to save programmes, compare them and build your plan.'}</p></div><a className="btn btn--primary" href="#/sign-in?create=1">{ru?'Создать аккаунт':'Create an account'}</a><a className="btn btn--ghost" href="#how-it-works">{ru?'Узнать больше':'Learn more'}</a><img className="landing__promise-art" src="/book/documents.webp" alt=""/></section>
    </main><BookFooter/>
  </div>;
}
