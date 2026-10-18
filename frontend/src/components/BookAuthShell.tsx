import type { ReactNode } from 'react';
import { ArrowLeft, FileText, GraduationCap, UsersThree } from '@phosphor-icons/react';
import { useTranslation } from '@/lib/useTranslation';
import type { Locale } from '@/lib/i18n';
import { BookFooter, BookGlobe } from './BookUI';

/** A stable visual shell. Forms keep their own identity and transaction handlers. */
export function BookAuthShell({ children, split = false, variant='standard' }: { children: ReactNode; split?: boolean; variant?:'standard'|'register'|'reset' }) {
  const { locale, setLocale } = useTranslation(); const ru = locale !== 'en';
  return <div className={`book-auth book-window ${split ? 'book-auth--split' : 'book-auth--single'} book-auth--${variant}`}>
    <header className="book-auth__header"><a className="landing__brand" href="#/welcome"><img src="/brand/unimatch-orbit.svg" alt=""/>unimatch</a><label className="book-language"><span className="visually-hidden">{ru?'Язык':'Language'}</span><select value={locale} onChange={event=>setLocale(event.target.value as Locale)}><option value="ru">Рус</option><option value="kk">Қаз</option><option value="en">Eng</option></select></label><a className="book-auth__back" href="#/welcome"><ArrowLeft size={17}/>{ru?'На сайт':'Back to site'}</a></header>
    <main className="book-auth__body">
      {split&&<aside className="book-auth__intro"><h2>{ru?<>Образование<br/>открывает<br/>больше горизонтов</>:<>Education<br/>opens up<br/>more horizons.</>}</h2><p>{ru?<>Поступай в международные университеты вместе с Unimatch. Подбор программ,<br/>сроки, документы — мы рядом<br/>на каждом этапе.</>:'Explore international universities with Unimatch. Programmes, dates and documents — together at every step.'}</p><BookGlobe/>{variant==='register'&&<ul className="book-auth__benefits"><li><GraduationCap size={24}/><span>{ru?<>Программы<br/>разных стран</>:<>Programmes<br/>across countries</>}</span></li><li><FileText size={24}/><span>{ru?<>Понятные сроки<br/>и требования</>:<>Dates and<br/>requirements</>}</span></li><li><UsersThree size={24}/><span>{ru?<>Твой план<br/>на каждом этапе</>:<>Your plan,<br/>step by step</>}</span></li></ul>}</aside>}
      {variant==='reset'&&<div className="book-auth__reset-globe" aria-hidden="true"><BookGlobe note={false}/></div>}
      {children}
      {split&&<div className="book-auth__mobile-globe"><BookGlobe/></div>}
    </main><BookFooter/>
  </div>;
}
