import {expect,it} from 'vitest';
import {officialProgrammes,programmeApplication,programmeNotes,planProgramme,sameProgramme} from './officialProgrammes';
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
 const p=officialProgrammes[0]!;const app={details:{notes:programmeNotes(p)}} as ApplicationRecord;
 expect(sameProgramme(app,p)).toBe(true);expect(sameProgramme({...app,details:{...app.details,notes:p.title}},p)).toBe(false);
});
