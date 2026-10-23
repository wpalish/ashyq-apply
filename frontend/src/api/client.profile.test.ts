import { beforeEach, expect, it, vi } from 'vitest';
import { api } from './client';
beforeEach(()=>{localStorage.clear();sessionStorage.clear();vi.stubGlobal('fetch',vi.fn().mockImplementation(async()=>new Response('{}',{status:200,headers:{'Content-Type':'application/json'}})));});
it('sends creation identity and UUID only as headers',async()=>{
 const command={command_id:crypto.randomUUID(),creation_identity:crypto.randomUUID()};
 await api.createProfile({display_name:'Synthetic'},command);
 const [,init]=vi.mocked(fetch).mock.calls[0]!;expect(init?.headers).toMatchObject({'Idempotency-Key':command.command_id,'X-Profile-Creation-Identity':command.creation_identity});
 expect(JSON.parse(String(init?.body))).toEqual({display_name:'Synthetic'});
});
it('sends the captured revision for PUT and persisted rerank',async()=>{
 const command={command_id:crypto.randomUUID(),expected_revision:4};
 await api.updateProfile('own',{display_name:'Synthetic'},command);await api.rerank('run',{persist:true},command);
 for(const [,init] of vi.mocked(fetch).mock.calls)expect(init?.headers).toMatchObject({'X-Expected-Profile-Revision':'4','Idempotency-Key':command.command_id});
});

it('represents a real fetch rejection as unknown transport status0',async()=>{
 vi.mocked(fetch).mockRejectedValueOnce(new TypeError('Synthetic dropped committed response'));
 await expect(api.createProfile({display_name:'Synthetic'},{command_id:crypto.randomUUID(),creation_identity:crypto.randomUUID()})).rejects.toMatchObject({status:0});
});
