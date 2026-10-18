import type { ReactNode } from 'react';
import { ArrowLeft } from '@phosphor-icons/react';
import { useTranslation } from '@/lib/useTranslation';
import type { Locale } from '@/lib/i18n';
import { BookFooter, BookGlobe } from './BookUI';

/** A stable visual shell. Forms keep their own identity and transaction handlers. */
export function BookAuthShell({ children, split = false }: { children: ReactNode; split?: boolean }) {
  const { locale, setLocale } = useTranslation(); const ru = locale !== 'en';
  return <div className={`book-auth book-window ${split ? 'book-auth--split' : 'book-auth--single'}`}>
    <header className="book-auth__header"><a className="landing__brand" href="#/welcome"><img src="/brand/unimatch-orbit.svg" alt=""/>unimatch</a><label className="book-language"><span className="visually-hidden">{ru?'Язык':'Language'}</span><select value={locale} onChange={event=>setLocale(event.target.value as Locale)}><option value="ru">Рус</option><option value="kk">Қаз</option><option value="en">Eng</option></select></label><a className="book-auth__back" href="#/welcome"><ArrowLeft size={17}/>{ru?'На сайт':'Back to site'}</a></header>
    <main className="book-auth__body">
      {split&&<aside className="book-auth__intro"><h2>{ru?<>Образование<br/>открывает<br/>больше горизонтов</>:<>Education<br/>opens up<br/>more horizons.</>}</h2><p>{ru?<>Поступай в международные университеты вместе с Unimatch. Подбор программ,<br/>сроки, документы — мы рядом<br/>на каждом этапе.</>:'Explore international universities with Unimatch. Programmes, dates and documents — together at every step.'}</p><BookGlobe/></aside>}
      {children}
      {split&&<div className="book-auth__mobile-globe"><BookGlobe/></div>}
    </main><BookFooter/>
  </div>;
}
