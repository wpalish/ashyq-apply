import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { api, ApiError } from './client';
import type { ActionRequestV1 } from '@/types/admissionsActions';

const OWNER = 'ashyq.applicantOwner';
const ownerA = 'auth:["synthetic-a","workspace-a"]';
const ownerB = 'auth:["synthetic-b","workspace-b"]';
const command: ActionRequestV1 = { schema_version: 'admissions-actions-v1', kind: 'create_personal_task',
  client_write_uuid: '11111111-2222-4333-8444-555555555555', expected_revision: 0, application_id: null,
  personal: { label: '  Жеке / personal task  ', responsible_actor: 'applicant', details: { due: null, notes: '  Keep exact text  ' }, depends_on_task_ids: [] } };
const response = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
function owner(value = ownerA) { localStorage.setItem(OWNER, value); sessionStorage.setItem(OWNER, value); }
beforeEach(() => { localStorage.clear(); sessionStorage.clear(); owner(); });
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe('additive G3 API transport on the native owner boundary', () => {
  it('encodes exact case/event IDs and preserves revision zero, history limit and display timezone', async () => {
    const transport = vi.fn().mockImplementation(async () => response({ synthetic: true })); vi.stubGlobal('fetch', transport);
    await api.admissionsActions('case/a ?'); await api.admissionsActionsHistory('case/a ?', 0, 100);
    await api.admissionsActionEvent('case/a ?', 'event/a ?'); await api.admissionsToday('case/a ?', 'Asia/Almaty');
    await api.admissionsToday('case/a ?');
    expect(transport.mock.calls.map(call => call[0])).toEqual([
      '/api/profiles/case%2Fa%20%3F/admissions-actions',
      '/api/profiles/case%2Fa%20%3F/admissions-actions/events?after_revision=0&limit=100',
      '/api/profiles/case%2Fa%20%3F/admissions-actions/events/event%2Fa%20%3F',
      '/api/profiles/case%2Fa%20%3F/today?timezone=Asia%2FAlmaty', '/api/profiles/case%2Fa%20%3F/today',
    ]);
    for (const call of transport.mock.calls) expect(call[1]).toMatchObject({ credentials: 'include', headers: { 'Content-Type': 'application/json' } });
  });
  it('sends the direct frozen body and original UUID unchanged on an explicit retry', async () => {
    const ack = { synthetic_ack: true }; const transport = vi.fn().mockImplementation(async () => response(ack)); vi.stubGlobal('fetch', transport);
    const before = JSON.stringify(command);
    expect(await api.writeAdmissionsAction('case-a', command)).toEqual(ack);
    expect(await api.writeAdmissionsAction('case-a', command)).toEqual(ack);
    expect(transport).toHaveBeenNthCalledWith(1, '/api/profiles/case-a/admissions-actions/commands', {
      method: 'POST', body: before, credentials: 'include', headers: { 'Content-Type': 'application/json' },
    });
    expect(transport.mock.calls[1]).toEqual(transport.mock.calls[0]); expect(JSON.stringify(command)).toBe(before);
  });
  it('uses unsaved strict previews without a write or raw legacy browser-key payload', async () => {
    const transport = vi.fn().mockImplementation(async () => response({ synthetic: true })); vi.stubGlobal('fetch', transport);
    const source = { result_id: 'result-a', purpose: 'admission' as const, award_id: null,
      occurrences: [{ location: 'admission_documents' as const, index: 2 }] };
    const imported = { expected_revision: 0, legacy_snapshot_digest: 'a'.repeat(64), mappings: [{ task_id: 'task-a', legacy_key_digest: 'b'.repeat(64),
      expected_binding_digest: null, source_preview_digest: null, legacy_value: true as const, confirmed_prepared_report: true as const,
      source_version: 'unknown' as const, original_reported_at: null }] };
    await api.previewAdmissionsSource('case-a', source); await api.previewAdmissionsImport('case-a', imported);
    expect(transport.mock.calls.map(call => call[0])).toEqual(['/api/profiles/case-a/admissions-actions/preview', '/api/profiles/case-a/admissions-actions/import-preview']);
    expect(transport.mock.calls[0]?.[1].body).toBe(JSON.stringify(source));
    expect(transport.mock.calls[1]?.[1].body).toBe(JSON.stringify(imported)); expect(transport).toHaveBeenCalledTimes(2);
  });
  it('refuses stale owner before any command or Today request', async () => {
    const transport = vi.fn(); vi.stubGlobal('fetch', transport); localStorage.setItem(OWNER, ownerB);
    await expect(api.writeAdmissionsAction('case-a', command)).rejects.toMatchObject({ status: 401 });
    await expect(api.admissionsToday('case-a')).rejects.toThrow(/workspace changed/); expect(transport).not.toHaveBeenCalled();
  });
  it('rejects a late ACK at response headers and never returns it to old owner memory', async () => {
    let resolve!: (value: Response) => void;
    const transport = vi.fn().mockReturnValue(new Promise<Response>(done => { resolve = done; })); vi.stubGlobal('fetch', transport);
    const pending = api.writeAdmissionsAction('case-a', command); localStorage.setItem(OWNER, ownerB);
    resolve(response({ event_id: 'must-not-hydrate' })); await expect(pending).rejects.toMatchObject({ status: 401 });
  });
  it('rechecks the owner after reading a successful response body', async () => {
    let resolveBody!: (value: unknown) => void;
    let started!: () => void; const bodyStarted = new Promise<void>(done => { started = done; });
    const incoming = response({}); const body = new Promise<unknown>(done => { resolveBody = done; });
    vi.spyOn(incoming, 'json').mockImplementation(() => { started(); return body; });
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(incoming));
    const pending = api.admissionsActions('case-a'); await bodyStarted;
    expect(incoming.json).toHaveBeenCalled(); owner(ownerB); resolveBody({ profile_id: 'case-a', state: 'old-owner-private' });
    await expect(pending).rejects.toMatchObject({ status: 401 });
  });
  it.each([409, 422, 503])('preserves fixed backend error detail/code for status %s without pretending a write succeeded', async status => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({ detail: { code: 'admissions_actions_write_unconfirmed', message: 'Keep the original request and retry.' } }, status)));
    try { await api.writeAdmissionsAction('case-a', command); throw new Error('Expected synthetic refusal'); }
    catch (error) { expect(error).toBeInstanceOf(ApiError); expect(error).toMatchObject({ status, code: 'admissions_actions_write_unconfirmed', message: 'Keep the original request and retry.' }); }
  });
  it('network uncertainty performs one request and leaves retries to the explicitly journaled caller', async () => {
    const transport = vi.fn().mockRejectedValue(new Error('Synthetic disconnected')); vi.stubGlobal('fetch', transport);
    await expect(api.writeAdmissionsAction('case-a', command)).rejects.toMatchObject({ status: 0 }); expect(transport).toHaveBeenCalledTimes(1);
  });
});


type HeadOrigin = 'g2' | 'legacy_v2' | 'legacy_v1';
function preparationHeadBody(origin: HeadOrigin, profileId = 'case-a') {
  const base = { origin, profile_id: profileId, revision: 1 };
  if (origin === 'g2') return { ...base, native_schema_version: 'shared-route-v1',
    client_write_uuid: '11111111-2222-4333-8444-555555555555', snapshot_digest: 'a'.repeat(64),
    allocation_digest: 'b'.repeat(64), accepted_at: '2026-10-13T06:00:00.123456Z' };
  if (origin === 'legacy_v2') return { ...base, native_schema_version: 'schedule-v2',
    persisted_sidecar_digest: 'a'.repeat(64), draft_fingerprint: 'b'.repeat(64),
    legacy_fingerprint: 'c'.repeat(64), observed_structural_fingerprint: 'd'.repeat(64) };
  return { ...base, native_schema_version: 'schedule-v1', saved_settings_digest: 'a'.repeat(64),
    settings_fingerprint: 'b'.repeat(64) };
}

describe('owned explicit preparation-head transport', () => {
  it.each(['g2', 'legacy_v2', 'legacy_v1'] as const)('reads exactly %s with no automatic command or retry', async origin => {
    const expected = preparationHeadBody(origin, 'case/a ?');
    const transport = vi.fn().mockResolvedValue(response(expected)); vi.stubGlobal('fetch', transport);
    expect(await api.admissionsPreparationHead('case/a ?', origin)).toEqual(expected);
    expect(transport).toHaveBeenCalledTimes(1);
    expect(transport).toHaveBeenCalledWith(`/api/profiles/case%2Fa%20%3F/admissions-actions/preparation-head?origin=${origin}`, {
      credentials: 'include', headers: { 'Content-Type': 'application/json' },
    });
    expect(transport.mock.calls[0]?.[1]).not.toHaveProperty('method');
    expect(transport.mock.calls[0]?.[1]).not.toHaveProperty('body');
  });
  it('retains the maximum saved revision and exact UTC microseconds', async () => {
    const expected = { ...preparationHeadBody('g2'), revision: 2147483647 };
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response(expected)));
    expect(await api.admissionsPreparationHead('case-a', 'g2')).toEqual(expected);
  });
  it.each([
    ['foreign case', { ...preparationHeadBody('g2'), profile_id: 'case-b' }],
    ['different requested origin', preparationHeadBody('legacy_v1')],
    ['none origin', { ...preparationHeadBody('g2'), origin: 'none' }],
    ['wrong native version', { ...preparationHeadBody('g2'), native_schema_version: 'schedule-v1' }],
    ['string revision', { ...preparationHeadBody('g2'), revision: '1' }],
    ['boolean revision', { ...preparationHeadBody('g2'), revision: true }],
    ['bad UUID', { ...preparationHeadBody('g2'), client_write_uuid: 'not-a-uuid' }],
    ['non-UTC time', { ...preparationHeadBody('g2'), accepted_at: '2026-10-13T08:00:00.123456+02:00' }],
    ['bad digest', { ...preparationHeadBody('g2'), snapshot_digest: 'bad' }],
    ['private extra field', { ...preparationHeadBody('g2'), private_marker: 'PRIVATE_HEAD_DO_NOT_ECHO' }],
    ['wrapper instead of head', { head: preparationHeadBody('g2') }],
    ['null body', null],
  ])('fails closed for %s without copying response values into errors', async (_label, body) => {
    const transport = vi.fn().mockResolvedValue(response(body)); vi.stubGlobal('fetch', transport);
    await expect(api.admissionsPreparationHead('case-a', 'g2')).rejects.toMatchObject({
      status: 503, code: 'admissions_actions_plan_unreadable',
      message: 'The selected saved plan could not be read safely.',
    });
    expect(transport).toHaveBeenCalledTimes(1);
  });
  it.each([409, 422, 503])('keeps the fixed server refusal %s and never selects a plan', async status => {
    const transport = vi.fn().mockResolvedValue(response({ detail: {
      code: 'admissions_actions_plan_head_changed', message: 'Review the current accepted head.',
    } }, status)); vi.stubGlobal('fetch', transport);
    await expect(api.admissionsPreparationHead('case-a', 'g2')).rejects.toMatchObject({
      status, code: 'admissions_actions_plan_head_changed', message: 'Review the current accepted head.',
    });
    expect(transport).toHaveBeenCalledTimes(1);
  });
  it('refuses a stale owner before any head request', async () => {
    const transport = vi.fn(); vi.stubGlobal('fetch', transport); localStorage.setItem(OWNER, ownerB);
    await expect(api.admissionsPreparationHead('case-a', 'legacy_v2')).rejects.toMatchObject({ status: 401 });
    expect(transport).not.toHaveBeenCalled();
  });
  it('withholds a valid head if the owner changes before response headers', async () => {
    let finish!: (value: Response) => void;
    const transport = vi.fn().mockReturnValue(new Promise<Response>(done => { finish = done; })); vi.stubGlobal('fetch', transport);
    const pending = api.admissionsPreparationHead('case-a', 'g2'); owner(ownerB);
    finish(response(preparationHeadBody('g2')));
    await expect(pending).rejects.toMatchObject({ status: 401 });
    expect(transport).toHaveBeenCalledTimes(1);
  });
  it('withholds a valid head if the owner changes while its JSON is read', async () => {
    let finish!: (value: unknown) => void;
    let started!: () => void; const reading = new Promise<void>(done => { started = done; });
    const incoming = response({});
    vi.spyOn(incoming, 'json').mockImplementation(() => { started(); return new Promise<unknown>(done => { finish = done; }); });
    const transport = vi.fn().mockResolvedValue(incoming); vi.stubGlobal('fetch', transport);
    const pending = api.admissionsPreparationHead('case-a', 'legacy_v1'); await reading;
    owner(ownerB); finish(preparationHeadBody('legacy_v1'));
    await expect(pending).rejects.toMatchObject({ status: 401 });
    expect(transport).toHaveBeenCalledTimes(1);
  });
  it('performs one failed GET and leaves any retry or new intent to the caller', async () => {
    const transport = vi.fn().mockRejectedValue(new Error('Synthetic unavailable')); vi.stubGlobal('fetch', transport);
    await expect(api.admissionsPreparationHead('case-a', 'g2')).rejects.toMatchObject({ status: 0 });
    expect(transport).toHaveBeenCalledTimes(1);
  });
});
