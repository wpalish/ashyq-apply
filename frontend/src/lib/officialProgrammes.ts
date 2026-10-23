import data from '@/data/officialProgrammes.json';
import type { ActionRequest, ApplicationRecord } from '@/types/admissionsActions';
export interface OfficialSource {url:string;title:string;checkedAt:string;method:string}
export interface OfficialFact {text:string;source:OfficialSource;scope:string}
export interface OfficialCost {amount:number;currency:string;period:string;population:string;academicYear:string;source:OfficialSource;excludes:string}
export interface OfficialDeadline {label:string;date:string|null;time:string|null;timezone:string|null;cycle:string;source:OfficialSource;scope:string}
export interface OfficialProgramme {id:string;universityId:string;universityName?:string;title:string;level:'bachelor'|'master';url:string;cycle:string;scope:string;checkedAt:string;access:'external_applicants'|'internal_only'|'not_open';version:string;requirements:OfficialFact[];costs:OfficialCost[];funding:OfficialFact[];deadlines:OfficialDeadline[];documents:OfficialFact[];unknowns:string[]}
export const officialProgrammes=data.programmes as OfficialProgramme[];
export const programmeVersions=[...officialProgrammes,...data.history as OfficialProgramme[]];
export const catalogueMarker=(p:OfficialProgramme)=>`unimatch-catalogue:${p.id}@${p.version}`;
export function planProgramme(notes:string){const marker=notes.split('\n')[0];return programmeVersions.find(p=>catalogueMarker(p)===marker)??null;}
export function programmeNotes(p:OfficialProgramme){
 const sources=[p.url,...p.requirements.map(f=>f.source.url),...p.costs.map(f=>f.source.url),...p.funding.map(f=>f.source.url),...p.deadlines.map(f=>f.source.url)];
 const lines=[catalogueMarker(p),`Programme snapshot checked ${p.checkedAt}; ${p.cycle}. Not an applicant eligibility assessment.`,p.scope,...p.costs.map(c=>`${c.amount} ${c.currency}/${c.period}; ${c.population}; ${c.academicYear}`),...p.deadlines.map(d=>`${d.label}: ${d.date??d.scope} ${d.time??''} ${d.timezone??'timezone unknown'}`),...new Set(sources)];
 const notes=lines.join('\n');if(notes.length>2000)throw new Error('Source snapshot exceeds the saved-note limit');return notes;
}
export function programmeIntakes(p:OfficialProgramme){const choices=[...new Set(p.deadlines.map(d=>d.cycle))];return choices.length>1?choices:[p.cycle];}
export function programmeApplication(p:OfficialProgramme,university:string,revision:number,uuid:string,intake?:string):ActionRequest {
 if(p.access!=='external_applicants')throw new Error('This programme has no external application route');
 const choices=programmeIntakes(p);const chosen=intake??(choices.length===1?choices[0]:undefined);if(!chosen||!choices.includes(chosen))throw new Error('Choose a verified intake');
 return {schema_version:'admissions-actions-v2',kind:'create_application',client_write_uuid:uuid,expected_revision:revision,label:`${university} — ${p.title}`.slice(0,200),details:{due:null,notes:programmeNotes(p)},target:{origin:'applicant_entered',result_id:null,award_id:null,purpose:'admission',university,programme:{state:'applicant_entered',value:p.title},award:{state:'unknown'},intake:{state:'applicant_entered',value:chosen},route:{state:'applicant_entered',value:p.url},confirmed_entered_context:true,official_verification:'not_performed'}};
}
export function sameProgramme(app:ApplicationRecord,p:OfficialProgramme){return programmeForApplication(app)?.id===p.id;}
export function programmeHref(p:OfficialProgramme){return `#/shortlist?view=catalogue&university=${encodeURIComponent(p.universityId)}&course=${encodeURIComponent(p.id)}&version=${p.version}`;}
export function catalogueCalendarEntries(applications:ApplicationRecord[],profileId:string|null){
 return applications.flatMap(app=>{if(app.profile_id!==profileId||app.status==='withdrawn_declared')return [];const p=programmeForApplication(app);if(!p)return [];
  return p.deadlines.filter(d=>d.date!==null&&(programmeIntakes(p).length===1||app.target.intake.state==='applicant_entered'&&app.target.intake.value===d.cycle)).map((d,index)=>({id:`catalogue:${app.id}:${index}`,day:d.date!,title:d.label,context:`${app.label} · ${d.cycle} · источник прочитан ${d.source.checkedAt}`,type:'catalogue' as const,zone:d.timezone,time:d.time,sourceUrl:d.source.url,href:`#/applications?case=${encodeURIComponent(app.profile_id)}&kind=application&id=${encodeURIComponent(app.id)}&tab=dates`}));
 });
}
const cataloguePrefix=/^unimatch-catalogue:[a-z0-9-]+@[a-f0-9]{64}$/;
export function catalogueUserNotes(notes:string){if(!cataloguePrefix.test(notes.split('\n')[0]??''))return notes;return notes.includes('\n---\n')?notes.split('\n---\n').slice(1).join('\n---\n'):'';}
export function preserveCatalogueNotes(original:string,personal:string){if(!cataloguePrefix.test(original.split('\n')[0]??''))return personal;return original.split('\n---\n')[0]+'\n---\n'+personal;}
export function programmeForApplication(app:ApplicationRecord){const p=planProgramme(app.details.notes);if(!p||!app.target||!('university'in app.target)||!('programme'in app.target)||app.target.programme.state!=='applicant_entered'||app.target.programme.value!==p.title||app.target.route.state!=='applicant_entered'||app.target.route.value!==p.url||app.target.intake.state!=='applicant_entered'||!programmeIntakes(p).includes(app.target.intake.value))return null;
 const names=data.institutions as Record<string,string>;if(app.target.university!==(p.universityName??names[p.universityId]))return null;return p;}
export function catalogueNoteSpace(original:string){return cataloguePrefix.test(original.split('\n')[0]??'')?Math.max(0,2000-preserveCatalogueNotes(original,'').length):2000;}
