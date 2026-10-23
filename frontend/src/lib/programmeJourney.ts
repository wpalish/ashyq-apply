import { useSyncExternalStore } from 'react';
export type JourneyRoute = { screen:'shortlist'|'approved'|'documents'|'applications'; profileId:string; resultId?:string; applicationId?:string; action?:'new'|'bind'; view?:'requirements'|'costs'|'documents'|'sources' };
export function journeyHref(route:JourneyRoute):string {
  const query=new URLSearchParams({case:route.profileId});
  if(route.resultId)query.set('programme',route.resultId);
  if(route.applicationId)query.set('application',route.applicationId);
  if(route.action)query.set('action',route.action);
  if(route.view)query.set('view',route.view);
  return `#/${route.screen}?${query}`;
}
export function parseJourneyRoute(hash:string):JourneyRoute|null {
  if(hash.length>1500||!hash.startsWith('#/')||hash.split('?').length!==2)return null;
  const [path,search]=hash.split('?');const screen=path?.slice(2);
  if(!['shortlist','approved','documents','applications'].includes(screen??'')||!search)return null;
  const query=new URLSearchParams(search);const keys=[...query.keys()];
  if(new Set(keys).size!==keys.length||keys.some(key=>!['case','programme','application','action','view'].includes(key)))return null;
  const valid=(value:string|null)=>value!==null&&value.length>0&&value.length<=200&&value.trim()===value&&!Array.from(value).some(char=>char.charCodeAt(0)<32||char.charCodeAt(0)===127);
  const profileId=query.get('case');if(!valid(profileId)||!profileId)return null;
  for(const key of ['programme','application'])if(query.has(key)&&!valid(query.get(key)))return null;
  const action=query.get('action');const view=query.get('view');
  if(action!==null&&action!=='new'&&action!=='bind'||view!==null&&!['requirements','costs','documents','sources'].includes(view))return null;
  if(action==='new'&&screen!=='applications'||action==='bind'&&screen!=='documents'||view&&screen!=='approved'&&screen!=='shortlist')return null;
  if(!query.has('programme')&&!query.has('application'))return null;
  return {screen:screen as JourneyRoute['screen'],profileId,...(query.has('programme')?{resultId:query.get('programme')!}:{}),...(query.has('application')?{applicationId:query.get('application')!}:{}),...(action?{action}:{}),...(view?{view:view as JourneyRoute['view']}:{} )};
}
const subscribe=(fn:()=>void)=>{window.addEventListener('hashchange',fn);return()=>window.removeEventListener('hashchange',fn);};
export function useJourneyRoute(){return parseJourneyRoute(useSyncExternalStore(subscribe,()=>window.location.hash));}

export const programmeTab=(view?:JourneyRoute['view'])=>view==='requirements'?'Требования':view==='costs'?'Стоимость':view==='documents'?'Документы':view==='sources'?'Источники':'Обзор';
