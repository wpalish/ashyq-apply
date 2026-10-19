import {expect,it} from 'vitest';
import {officialProgrammes,programmeApplication,programmeNotes,planProgramme,sameProgramme,catalogueCalendarEntries,catalogueUserNotes,preserveCatalogueNotes,programmeForApplication} from './officialProgrammes';
import {isActionRequest,type ApplicationRecord} from '@/types/admissionsActions';
it('keeps official price units/populations and independent entry-year deadlines',()=>{
 const mit=officialProgrammes.find(p=>p.id==='mit-computer-science-engineering-sb')!;
 expect(mit.costs[0]).toMatchObject({amount:33360,period:'term',academicYear:'2026–27'});
 expect(mit.deadlines.every(d=>d.date===null)).toBe(true);
 const ba=officialProgrammes.find(p=>p.id==='oxford-computer-science-ba')!;const msc=officialProgrammes.find(p=>p.id==='oxford-advanced-computer-science-msc')!;
 expect(ba.deadlines[0]?.date).toBe('2026-10-15');expect(msc.deadlines[0]?.date).toBe('2027-01-06');expect(ba.costs[0]?.amount).not.toBe(msc.costs[0]?.amount);
});
it('creates a valid owned-journal command with no fabricated result, personal deadline or eligibility',()=>{
 const p=officialProgrammes.find(p=>p.id==='oxford-advanced-computer-science-msc')!;
 const body=programmeApplication(p,'University of Oxford',7,'a548c6ad-d306-4e8f-927d-82503c30a5bd');
 expect(isActionRequest(body)).toBe(true);expect(body).toMatchObject({expected_revision:7,target:{origin:'applicant_entered',result_id:null,official_verification:'not_performed'},details:{due:null}});
 expect(programmeNotes(p).length).toBeLessThanOrEqual(2000);expect(planProgramme(programmeNotes(p))).toBe(p);
 expect(planProgramme(programmeNotes(p).replace(p.version,'0'.repeat(64)))).toBeNull();
});
it('does not create an external application for an internal-only graduate route',()=>{
 const p=officialProgrammes.find(p=>p.id==='mit-eecs-meng')!;expect(()=>programmeApplication(p,'MIT',0,'uuid')).toThrow('external');
});
it('recognises the saved programme snapshot without using programme-name fuzzy matching',()=>{
 const p=officialProgrammes[0]!;const app={details:{notes:programmeNotes(p)},target:{university:p.universityName,programme:{state:'applicant_entered',value:p.title},route:{state:'applicant_entered',value:p.url},intake:{state:'applicant_entered',value:p.cycle}}} as ApplicationRecord;
 expect(sameProgramme(app,p)).toBe(true);expect(sameProgramme({...app,details:{...app.details,notes:p.title}},p)).toBe(false);
});

it('projects exact catalogue source dates only for their owner without inventing a personal date or zone',()=>{
 const p=officialProgrammes.find(p=>p.id==='oxford-advanced-computer-science-msc')!;
 const app={id:'b'.repeat(32),profile_id:'owner-a',status:'planning',label:'Oxford MSc',target:{university:p.universityName,programme:{state:'applicant_entered',value:p.title},route:{state:'applicant_entered',value:p.url},intake:{state:'applicant_entered',value:p.cycle}},details:{notes:programmeNotes(p),due:null}} as ApplicationRecord;
 const entries=catalogueCalendarEntries([app],'owner-a');expect(entries).toHaveLength(1);expect(entries[0]).toMatchObject({day:'2027-01-06',time:'12:00',zone:'Europe/London',type:'catalogue',sourceUrl:p.url});
 expect(entries[0]?.href).toContain('case=owner-a');expect(catalogueCalendarEntries([app],'owner-b')).toHaveLength(0);expect(app.details.due).toBeNull();
 expect(catalogueCalendarEntries([{...app,details:{...app.details,notes:programmeNotes(officialProgrammes.find(x=>x.id==='mit-computer-science-engineering-sb')!)}}],'owner-a')).toHaveLength(0);
});

it('keeps the source snapshot when editing personal notes and retires its projection after changing intake',()=>{
 const p=officialProgrammes.find(p=>p.id==='oxford-advanced-computer-science-msc')!;
 const original=programmeNotes(p);expect(catalogueUserNotes(original)).toBe('');
 const saved=preserveCatalogueNotes(original,'My preparation note');expect(catalogueUserNotes(saved)).toBe('My preparation note');expect(planProgramme(saved)?.version).toBe(p.version);
 const target={university:p.universityName,programme:{state:'applicant_entered',value:p.title},route:{state:'applicant_entered',value:p.url},intake:{state:'applicant_entered',value:p.cycle}};
 const app={profile_id:'owner',target,details:{notes:saved}} as ApplicationRecord;expect(programmeForApplication(app)).toBe(p);
 expect(programmeForApplication({...app,target:{...app.target,intake:{state:'applicant_entered',value:'2028'}}} as ApplicationRecord)).toBeNull();
 expect(programmeForApplication({...app,target:{...target,university:'Other university'}} as ApplicationRecord)).toBeNull();
});

it('requires an exact intake for multi-intake courses and projects only its deadline',()=>{
 const p=officialProgrammes.find(p=>p.id==='st-andrews-data-science-online-msc')!;
 expect(()=>programmeApplication(p,p.universityName!,1,'uuid')).toThrow('intake');
 const body=programmeApplication(p,p.universityName!,1,'uuid','January2027');
 expect(body).toMatchObject({target:{intake:{value:'January2027'}}});
 const app={id:'a',profile_id:'owner',status:'planning',label:'St Andrews',target:'target'in body?body.target:null,details:'details'in body?body.details:null} as ApplicationRecord;
 const dates=catalogueCalendarEntries([app],'owner');expect(dates.map(d=>d.day)).toEqual(['2027-01-08']);
 expect(catalogueCalendarEntries([{...app,target:{...app.target,intake:{state:'applicant_entered',value:'Unknown intake'}}} as ApplicationRecord],'owner')).toHaveLength(0);
});
it('keeps every external published programme inside the server command and note limits',()=>{
 for(const p of officialProgrammes.filter(p=>p.access==='external_applicants')){
  const intake=new Set(p.deadlines.map(d=>d.cycle)).size>1?p.deadlines[0]!.cycle:p.cycle;
  const command=programmeApplication(p,p.universityName!,1,'a548c6ad-d306-4e8f-927d-82503c30a5bd',intake);
  expect(isActionRequest(command),p.id).toBe(true);expect(programmeNotes(p).length,p.id).toBeLessThanOrEqual(2000);
 }
});
