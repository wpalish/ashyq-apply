import data from '@/data/officialProgrammes.json';
import type { ActionRequest, ApplicationRecord } from '@/types/admissionsActions';
export interface OfficialSource {url:string;title:string;checkedAt:string;method:string}
export interface OfficialFact {text:string;source:OfficialSource;scope:string}
export interface OfficialCost {amount:number;currency:string;period:string;population:string;academicYear:string;source:OfficialSource;excludes:string}
export interface OfficialDeadline {label:string;date:string|null;time:string|null;timezone:string|null;cycle:string;source:OfficialSource;scope:string}
export interface OfficialProgramme {id:string;universityId:string;title:string;level:'bachelor'|'master';url:string;cycle:string;scope:string;checkedAt:string;access:'external_applicants'|'internal_only'|'not_open';version:string;requirements:OfficialFact[];costs:OfficialCost[];funding:OfficialFact[];deadlines:OfficialDeadline[];documents:OfficialFact[];unknowns:string[]}
export const officialProgrammes=data.programmes as OfficialProgramme[];
export const catalogueMarker=(p:OfficialProgramme)=>`unimatch-catalogue:${p.id}@${p.version}`;
export function planProgramme(notes:string){const marker=notes.split('\n')[0];return officialProgrammes.find(p=>catalogueMarker(p)===marker)??null;}
export function programmeNotes(p:OfficialProgramme){
 const sources=[p.url,...p.requirements.map(f=>f.source.url),...p.costs.map(f=>f.source.url),...p.funding.map(f=>f.source.url),...p.deadlines.map(f=>f.source.url)];
 const lines=[catalogueMarker(p),`Programme snapshot checked ${p.checkedAt}; ${p.cycle}. Not an applicant eligibility assessment.`,p.scope,...p.costs.map(c=>`${c.amount} ${c.currency}/${c.period}; ${c.population}; ${c.academicYear}`),...p.deadlines.map(d=>`${d.label}: ${d.date??d.scope} ${d.time??''} ${d.timezone??'timezone unknown'}`),...new Set(sources)];
 const notes=lines.join('\n');if(notes.length>2000)throw new Error('Source snapshot exceeds the saved-note limit');return notes;
}
export function programmeApplication(p:OfficialProgramme,university:string,revision:number,uuid:string):ActionRequest {
 if(p.access!=='external_applicants')throw new Error('This programme has no external application route');
 return {schema_version:'admissions-actions-v2',kind:'create_application',client_write_uuid:uuid,expected_revision:revision,label:`${university} — ${p.title}`.slice(0,200),details:{due:null,notes:programmeNotes(p)},target:{origin:'applicant_entered',result_id:null,award_id:null,purpose:'admission',university,programme:{state:'applicant_entered',value:p.title},award:{state:'unknown'},intake:{state:'applicant_entered',value:p.cycle},route:{state:'applicant_entered',value:p.url},confirmed_entered_context:true,official_verification:'not_performed'}};
}
export function sameProgramme(app:ApplicationRecord,p:OfficialProgramme){return app.details.notes.split('\n')[0]===catalogueMarker(p);}
export function programmeHref(p:OfficialProgramme){return `#/shortlist?view=catalogue&university=${encodeURIComponent(p.universityId)}&course=${encodeURIComponent(p.id)}&version=${p.version}`;}
