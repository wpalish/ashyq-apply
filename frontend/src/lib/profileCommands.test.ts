import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { clearConfirmedProfileCommands, PROFILE_COMMAND_LIMIT, readProfileCommands, saveProfileCommand, type ProfileCommand } from './profileCommands';
import { APPLICANT_OWNER_KEY } from './applicantStorage';
function original(case_key=`local:${crypto.randomUUID()}`):ProfileCommand {
  return {v:1,owner:null,case_key,kind:'create',command:{command_id:crypto.randomUUID(),creation_identity:case_key.slice(6)},body:{name:'Synthetic'},draft:{name:'Synthetic'},base:null,status:'pending'};
}
beforeEach(()=>{localStorage.clear();sessionStorage.clear();vi.restoreAllMocks();});
afterEach(()=>vi.restoreAllMocks());
it('retains exact original body/UUID through an unknown response and reload',()=>{
  const entry=original();saveProfileCommand(entry);saveProfileCommand({...entry,status:'unknown'});
  expect(readProfileCommands()).toEqual([{...entry,status:'unknown'}]);
  expect(()=>saveProfileCommand({...entry,body:{name:'changed'},status:'pending'})).toThrow(/cannot change/);
  expect(readProfileCommands()[0]!.body).toEqual(entry.body);
});
it('refuses a replacement command while the original case is unresolved',()=>{
  const entry=original();saveProfileCommand(entry);
  expect(()=>saveProfileCommand({...entry,command:{...entry.command,command_id:crypto.randomUUID()}})).toThrow(/Resolve/);
});
it('keeps unresolved commands when explicitly clearing confirmed history',()=>{
  const accepted={...original(),status:'accepted' as const};const conflict={...original(),status:'conflict' as const};
  saveProfileCommand(accepted);saveProfileCommand(conflict);clearConfirmedProfileCommands();
  expect(readProfileCommands()).toEqual([conflict]);
});
it('fails closed at its own small limit without widening G3 or evicting pending',()=>{
  for(let i=0;i<PROFILE_COMMAND_LIMIT;i++)saveProfileCommand(original());
  expect(()=>saveProfileCommand(original())).toThrow(/full/);expect(readProfileCommands()).toHaveLength(PROFILE_COMMAND_LIMIT);
});
it('rejects denied storage before anything can be dispatched',()=>{
  vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{throw new Error('Denied');});
  expect(()=>saveProfileCommand(original())).toThrow(/Denied/);expect(readProfileCommands()).toEqual([]);
});
it('retains corrupt bytes and never adopts them',()=>{
  sessionStorage.setItem('ashyq.draft.profileCommands.v1','bad original bytes');
  expect(()=>readProfileCommands()).toThrow();expect(sessionStorage.getItem('ashyq.draft.profileCommands.v1')).toBe('bad original bytes');
});
it('rejects another owner instead of borrowing its namespace',()=>{
  const entry=original();saveProfileCommand(entry);
  localStorage.setItem(APPLICANT_OWNER_KEY,'auth:new');sessionStorage.setItem(APPLICANT_OWNER_KEY,'auth:new');
  expect(()=>readProfileCommands(null)).toThrow(/workspace changed/);
});

it('does not clear accepted commands whose current server version still needs comparison',()=>{
 const entry={...original(),status:'accepted' as const,accepted_profile_id:'own-created',reconciliation_required:true};saveProfileCommand(entry);clearConfirmedProfileCommands();expect(readProfileCommands()).toEqual([entry]);
});
