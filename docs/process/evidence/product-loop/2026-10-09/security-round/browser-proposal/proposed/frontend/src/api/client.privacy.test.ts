import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { api } from './client';
import type { AuthPrincipal } from '@/types';

const OWNER = 'ashyq.applicantOwner';
const personA = 'auth:["user-a","org-a"]';
const personB = 'auth:["user-b","org-b"]';
const principalB: AuthPrincipal = {
  user_id: 'user-b', organization_id: 'org-b', email: 'b@example.test',
  display_name: 'Synthetic B', organization_name: 'B workspace', role: 'owner', local_development: false,
};
const response = (body: unknown, status = 200) => new Response(JSON.stringify(body), {
  status, headers: { 'Content-Type': 'application/json' },
});
function owner(value = personA) {
  localStorage.setItem(OWNER, value);
  sessionStorage.setItem(OWNER, value);
}
function applicantData() {
  localStorage.setItem('ashyq.draft.local:synthetic-a', 'private synthetic draft');
  localStorage.setItem('ashyq.docsDone', '{"synthetic-a::Passport":true}');
  sessionStorage.setItem('ashyq.activeProfile', 'local:synthetic-a');
  localStorage.setItem('ashyq.theme', 'dark');
}
beforeEach(() => { localStorage.clear(); sessionStorage.clear(); owner(); });
afterEach(() => { vi.unstubAllGlobals(); });

describe('actual API owner boundary around shared cookies', () => {
  it('refuses stale-tab applicant mutation before any fetch under another owner', async () => {
    const transport = vi.fn().mockResolvedValue(response({ id: 'badly-created' }));
    vi.stubGlobal('fetch', transport);
    localStorage.setItem(OWNER, personB); // Other tab changed the shared session; this tab still owns A memory.
    await expect(api.createProfile({ display_name: 'Synthetic A private draft' })).rejects.toThrow(/workspace changed/);
    expect(transport).not.toHaveBeenCalled();
  });
  it('rejects a late response after ownership changes instead of returning it into old memory', async () => {
    let resolve!: (value: Response) => void;
    const transport = vi.fn().mockReturnValue(new Promise<Response>((done) => { resolve = done; }));
    vi.stubGlobal('fetch', transport);
    const pending = api.getProfile('synthetic-a');
    expect(transport).toHaveBeenCalledTimes(1);
    localStorage.setItem(OWNER, personB);
    resolve(response({ id: 'synthetic-a', display_name: 'A response' }));
    await expect(pending).rejects.toThrow(/workspace changed/);
  });
  it('keeps ordinary same-owner request payload, URL, and cookie mode unchanged', async () => {
    const returned = { id: 'synthetic-a', display_name: 'Synthetic A' };
    const transport = vi.fn().mockResolvedValue(response(returned));
    vi.stubGlobal('fetch', transport);
    expect(await api.createProfile({ display_name: 'Synthetic A' })).toEqual(returned);
    expect(transport).toHaveBeenCalledWith('/api/profiles', {
      method: 'POST', body: '{"display_name":"Synthetic A"}', credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
    });
  });
  it('locks old tab data while a login is pending and binds only the acknowledged new principal', async () => {
    let resolve!: (value: Response) => void;
    const transport = vi.fn().mockReturnValue(new Promise<Response>((done) => { resolve = done; }));
    vi.stubGlobal('fetch', transport);
    applicantData();
    const login = api.login('b@example.test', 'synthetic password');
    expect(localStorage.getItem(OWNER)).toMatch(/^transition:/);
    await expect(api.createProfile({ display_name: 'A must not be sent' })).rejects.toThrow(/workspace changed/);
    expect(transport).toHaveBeenCalledTimes(1);
    resolve(response(principalB));
    expect(await login).toEqual(principalB);
    expect(localStorage.getItem(OWNER)).toBe(personB);
    expect(sessionStorage.getItem(OWNER)).toBe(personB);
    expect(localStorage.getItem('ashyq.draft.local:synthetic-a')).toBeNull();
  });
  it('does not let a late auth acknowledgment erase or replace a newer owner', async () => {
    let resolve!: (value: Response) => void;
    vi.stubGlobal('fetch', vi.fn().mockReturnValue(new Promise<Response>((done) => { resolve = done; })));
    applicantData();
    const logout = api.logout();
    localStorage.setItem(OWNER, personB);
    localStorage.setItem('ashyq.draft.local:synthetic-b', 'new owner draft');
    resolve(new Response(null, { status: 204 }));
    await expect(logout).rejects.toThrow(/workspace changed/);
    expect(localStorage.getItem(OWNER)).toBe(personB);
    expect(localStorage.getItem('ashyq.draft.local:synthetic-b')).toBe('new owner draft');
  });
  it.each(['logout', 'deleteAccount'] as const)('clears applicant browser data only after %s succeeds', async (operation) => {
    applicantData();
    const transport = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal('fetch', transport);
    if (operation === 'logout') await api.logout();
    else await api.deleteAccount('synthetic password', true);
    expect(transport).toHaveBeenCalledTimes(1);
    expect(localStorage.getItem('ashyq.draft.local:synthetic-a')).toBeNull();
    expect(localStorage.getItem('ashyq.docsDone')).toBeNull();
    expect(sessionStorage.getItem('ashyq.activeProfile')).toBeNull();
    expect(localStorage.getItem('ashyq.theme')).toBe('dark');
  });
  it.each(['logout', 'deleteAccount'] as const)('retains applicant data and restores binding when %s fails', async (operation) => {
    applicantData();
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({ detail: 'Synthetic refusal' }, 403)));
    const pending = operation === 'logout' ? api.logout() : api.deleteAccount('bad password', true);
    await expect(pending).rejects.toThrow('Synthetic refusal');
    expect(localStorage.getItem(OWNER)).toBe(personA);
    expect(sessionStorage.getItem(OWNER)).toBe(personA);
    expect(localStorage.getItem('ashyq.draft.local:synthetic-a')).toBe('private synthetic draft');
    expect(sessionStorage.getItem('ashyq.activeProfile')).toBe('local:synthetic-a');
  });
});
