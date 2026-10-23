import { expect, it } from 'vitest';
import { emptyToday } from '@/test/admissionsTodayFixtures';
import { acceptedActions } from '@/test/admissionsFixtures';
import type { TodayCardV1 } from '@/types/admissionsActions';
import { bookTaskView } from './bookPlanPresentation';

function fixture() {
  const projection=emptyToday('A'); projection.action_revision=1;
  const card:TodayCardV1={id:'task-card',reason:'personal_document_action',target:{kind:'document_task',id:'task-a'},target_result_id:null,
    date:{local_date:'2026-10-20',timezone:null,certainty:'applicant_entered',comparison_zone:'UTC',fallback_display_only:false,official_closure:'not_assessed'},
    dependency_reasons:[],workload_origin:'personal_unallocated',planned_minutes:null,source_state:'applicant_entered',actionable:true};
  return {projection,card,current:acceptedActions().current};
}
it('opens the exact case-owned task while preserving a personal date and its unknown timezone',()=>{
  const {projection,card,current}=fixture();
  expect(bookTaskView(card,projection,current)).toMatchObject({label:'Synthetic document task',href:'#/documents?case=A&kind=document_task&id=task-a',sourceLabel:'Личная задача'});
  expect(card.date).toMatchObject({local_date:'2026-10-20',timezone:null,official_closure:'not_assessed'});
});
it('does not borrow a document label from another case or action revision',()=>{
  const {projection,card,current}=fixture();
  expect(bookTaskView(card,projection,{...current,profile_id:'B'}).label).toBe('Задача по документам');
  expect(bookTaskView(card,projection,{...current,revision:2}).label).toBe('Задача по документам');
});
it.each(['refresh','mixed','nonactionable'] as const)('does not publish an actionable link for %s data',reason=>{
  const {projection,card,current}=fixture();
  if(reason==='refresh')projection.needs_refresh=true;
  if(reason==='mixed')projection.consistency='mixed_revision';
  if(reason==='nonactionable')card.actionable=false;
  expect(bookTaskView(card,projection,current).href).toBeNull();
});
