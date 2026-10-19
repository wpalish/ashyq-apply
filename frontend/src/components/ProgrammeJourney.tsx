import { programmeHref, type OfficialProgramme } from '@/lib/officialProgrammes';
import { ArrowRight } from '@phosphor-icons/react';
import { journeyHref } from '@/lib/programmeJourney';
export function ProgrammeJourney({profileId,resultId,applicationId,current,catalogue}:{profileId:string;resultId?:string;applicationId?:string;current:'requirements'|'documents'|'applications';catalogue?:OfficialProgramme|null}) {
  return <nav className="programme-journey" aria-label="Путь по программе">
    <a href={catalogue?programmeHref(catalogue):resultId?journeyHref({screen:'shortlist',profileId,resultId}):'#/shortlist'}>Подбор</a><ArrowRight size={15} aria-hidden="true"/>
    {catalogue?<a href={programmeHref(catalogue)}>Требования</a>:resultId?<a aria-current={current==='requirements'?'page':undefined} href={journeyHref({screen:'approved',profileId,resultId,view:'requirements'})}>Требования</a>:<span>Требования уточняются</span>}<ArrowRight size={15} aria-hidden="true"/>
    <a aria-current={current==='documents'?'page':undefined} href={journeyHref({screen:'documents',profileId,resultId,applicationId})}>Документы</a><ArrowRight size={15} aria-hidden="true"/>
    <a aria-current={current==='applications'?'page':undefined} href={journeyHref({screen:'applications',profileId,resultId,applicationId})}>Заявка и сроки</a>
  </nav>;
}
