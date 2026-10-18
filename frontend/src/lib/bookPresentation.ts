import type { ProgramResult } from '@/types';

export function programmeLanguage(result: ProgramResult): string {
  const values = result.claims.filter(claim=>claim.claim_type==='program_exists' && claim.status==='VERIFIED_CURRENT' && claim.official_domain && !claim.is_stale).flatMap(claim=>{
    const value=claim.normalized_value;
    return value && typeof value==='object' && 'language' in value && typeof value.language==='string' ? [value.language] : [];
  });
  const unique=[...new Set(values.map(value=>value.trim().toLowerCase()).filter(Boolean))];
  return unique.length===1 ? unique[0]??'' : '';
}
export function requirementName(key: string): string {
  const names:Record<string,string>={program_exists:'Наличие программы',ielts_min_overall:'Общий балл IELTS',ielts_min_subscore:'Минимум по секциям IELTS',toefl_min_total:'Общий балл TOEFL',min_gpa:'Минимальный средний балл',gpa_scale:'Шкала оценок',admission_deadline:'Срок подачи заявки',school_qualification:'Аттестат о среднем образовании',qualification:'Аттестат о среднем образовании',ielts_overall:'Английский язык (IELTS)',ielts:'Английский язык (IELTS)',toefl_ibt:'Английский язык (TOEFL)',gpa:'Средний балл',math:'Оценка по математике',mathematics:'Математика'};
  return names[key]??key.replace(/_/g,' ');
}
