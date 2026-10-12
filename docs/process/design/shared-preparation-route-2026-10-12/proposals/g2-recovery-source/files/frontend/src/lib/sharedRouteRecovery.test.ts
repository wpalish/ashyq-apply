import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  acknowledgeSharedRouteRecovery, newSharedRouteRecovery, readSharedRouteRecovery,
  RECOVERY_RAW_BYTES, resetSharedRouteRecovery, sharedRouteRecoveryBinding, validRecoveryBody,
  writeSharedRouteRecovery, type SharedRouteDraft, type SharedRouteRecovery,
} from './sharedRouteRecovery';
import type { SharedRouteWriteV1 } from '@/types';

const ownerKey = 'ashyq.applicantOwner';
const uuid = '11111111-2222-4333-8444-555555555555';
const write: SharedRouteWriteV1 = {
  applicant_input: { schema_version: 'shared-route-v1', selected_result_ids: ['owned-a', 'owned-b'],
    starts_on: '2026-10-12', timezone: 'UTC', study_days: [0, 2, 4], shared_weekly_minutes: 120,
    exam_choices: [{ exam: 'ielts_academic', priority: 0, first_exam_on: '2026-10-25', retake_on: null,
      certificate_deadline: '2026-11-10', result_wait_days: 3, delivery_days: 2, safety_days: 3,
      personal_targets: { reading: 6.5 }, confirmed_exam_dates_and_buffers: true }],
    own_reviews: [{ ref: { kind: 'attempt_review', id: `attempt:${uuid}`, attempt_id: uuid,
      lesson_id: 'ielts-reading-1', content_version: 'starter-2026-10-11-v1' }, exam: 'ielts_academic', planned_minutes: 30 }],
    confirmed_shared_planning_inputs: true }, expected_revision: 2, client_write_uuid: uuid,
  preview_fingerprint: 'a'.repeat(64), source_fingerprint: 'b'.repeat(64),
  legacy_anchor: { technical_revision: 0, structural_fingerprint: null, imported_learning_refs_fingerprint: null }, planned_on: '2026-10-12',
};
const draft = (): SharedRouteDraft => ({ ids: ['owned-a', 'owned-b'], starts_on: '2026-10-12', timezone: 'UTC',
  days: [0, 2, 4], weekly: '120', confirmed: true, reviews: [{ attempt_id: uuid, lesson_id: 'ielts-reading-1',
    content_version: 'starter-2026-10-11-v1', exam: 'ielts_academic', minutes: '30' }], exams: [
    { exam: 'ielts_academic', enabled: true, first_exam_on: '2026-10-25', retake_on: '', certificate_deadline: '2026-11-10',
      result_wait_days: '3', delivery_days: '2', safety_days: '3', confirmed: true, targets: { reading: '6.5' } },
    { exam: 'digital_sat', enabled: false, first_exam_on: '', retake_on: '', certificate_deadline: '',
      result_wait_days: '', delivery_days: '', safety_days: '', confirmed: false, targets: {} },
  ] });
function bind(value = 'demo') { localStorage.setItem(ownerKey, value); sessionStorage.setItem(ownerKey, value); }
function binding(caseId = 'case-a') {
  const out = sharedRouteRecoveryBinding(undefined, caseId); if (!out) throw new Error('Explicit demo binding expected'); return out;
}
function pendingRecord(): SharedRouteRecovery {
  return { ...newSharedRouteRecovery(binding(), draft()), draft_generation: 3, dirty: true,
    pending: { body: structuredClone(write), state: 'sending', submitted_generation: 3, dispatched: true } };
}
function save(record = pendingRecord()) {
  const out = writeSharedRouteRecovery(binding(), record, null); if (!out.ok) throw new Error('Synthetic journal write expected'); return out;
}
beforeEach(() => { localStorage.clear(); sessionStorage.clear(); bind(); });
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe('strict per-tab own-case reference journal', () => {
  it('requires a native explicit demo or the exact owning React auth scope', () => {
    localStorage.clear(); sessionStorage.clear(); expect(sharedRouteRecoveryBinding(undefined, 'case-a')).toBeNull();
    bind('auth:["user-a","org-a"]'); expect(sharedRouteRecoveryBinding(undefined, 'case-a')).toBeNull();
    expect(sharedRouteRecoveryBinding(null, 'case-a')).toBeNull();
    expect(sharedRouteRecoveryBinding('["user-b","org-b"]', 'case-a')).toBeNull();
    expect(sharedRouteRecoveryBinding('["user-a","org-a"]', 'case-a')?.owner).toBe('auth:["user-a","org-a"]');
  });
  it('never reads, writes or resets an old owner after native binding changes', () => {
    const captured = binding(); const stored = save(); bind('auth:["user-b","org-b"]');
    expect(readSharedRouteRecovery(captured).state).toBe('unavailable');
    expect(writeSharedRouteRecovery(captured, stored.record, stored.raw)).toEqual({ ok: false, reason: 'owner' });
    expect(resetSharedRouteRecovery(captured, stored.raw)).toBe(false);
    expect(sessionStorage.getItem(captured.key)).toBe(stored.raw);
  });
  it('persists exact original body and supplied partial targets without server or material payloads', () => {
    const saved = save(); const loaded = readSharedRouteRecovery(binding()); expect(loaded.state).toBe('valid');
    if (loaded.state !== 'valid') throw new Error('Own valid record expected');
    expect(loaded.record.pending?.body).toEqual(write);
    expect(loaded.record.pending?.body.applicant_input.exam_choices[0]?.personal_targets).toEqual({ reading: 6.5 });
    expect(JSON.parse(saved.raw).pending.body.applicant_input.own_reviews[0].ref).toEqual(write.applicant_input.own_reviews[0]?.ref);
    expect(Object.keys(JSON.parse(saved.raw))).not.toContain('allocation');
  });
  it.each(['version', 'owner', 'profile_id', 'extra_material', 'nonfinite', 'oversize', 'malformed'])('refuses %s bytes without changing or deleting them', corruption => {
    const saved = save(); const value = JSON.parse(saved.raw) as Record<string, unknown>;
    if (corruption === 'version') value.version = 2;
    if (corruption === 'owner') value.owner = 'demo-other';
    if (corruption === 'profile_id') value.profile_id = 'case-b';
    if (corruption === 'extra_material') value.lesson_body = 'Must not be stored';
    let raw = JSON.stringify(value);
    if (corruption === 'nonfinite') raw = raw.replace('"journal_revision":1', '"journal_revision":1e309');
    if (corruption === 'oversize') raw = ' '.repeat(RECOVERY_RAW_BYTES + 1);
    if (corruption === 'malformed') raw = '{';
    sessionStorage.setItem(binding().key, raw);
    expect(readSharedRouteRecovery(binding()).state).toBe('invalid');
    expect(writeSharedRouteRecovery(binding(), saved.record, raw).ok).toBe(false);
    expect(sessionStorage.getItem(binding().key)).toBe(raw);
  });
  it.each([NaN, Infinity, -Infinity, 29, 1261, true])('refuses invalid pending numeric capacity %s', value => {
    const body = structuredClone(write); (body.applicant_input as unknown as Record<string, unknown>).shared_weekly_minutes = value;
    expect(validRecoveryBody(body)).toBe(false);
  });
  it('rejects malformed exact refs, a false confirmation and an impossible planning date', () => {
    const ref = structuredClone(write); ref.applicant_input.own_reviews[0]!.ref.id = 'attempt:different';
    expect(validRecoveryBody(ref)).toBe(false);
    const input = structuredClone(write); (input.applicant_input as unknown as Record<string, unknown>).confirmed_shared_planning_inputs = false;
    expect(validRecoveryBody(input)).toBe(false);
    const date = structuredClone(write); date.applicant_input.starts_on = '2026-02-30'; expect(validRecoveryBody(date)).toBe(false);
    const target = structuredClone(write); target.applicant_input.exam_choices[0]!.personal_targets = { reading: Infinity };
    expect(validRecoveryBody(target)).toBe(false);
  });
  it('reports read/write failure without claiming a durable journal', () => {
    const out = save(); const captured = binding();
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('Synthetic storage refusal'); });
    expect(writeSharedRouteRecovery(captured, out.record, out.raw)).toEqual({ ok: false, reason: 'storage' });
    expect(sessionStorage.getItem(captured.key)).toBe(out.raw);
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => { throw new Error('Synthetic read refusal'); });
    expect(readSharedRouteRecovery(captured).state).toBe('unavailable');
  });
  it('refuses a journal revision overflow before replacing any stored bytes', () => {
    const record = { ...pendingRecord(), journal_revision: Number.MAX_SAFE_INTEGER - 1 };
    expect(writeSharedRouteRecovery(binding(), record, null)).toEqual({ ok: false, reason: 'invalid' });
    expect(sessionStorage.getItem(binding().key)).toBeNull();
  });
  it('keeps a newer edited draft after the exact old command ACK', () => {
    const original = save(); const edited = writeSharedRouteRecovery(binding(), { ...original.record,
      draft_generation: 4, draft: { ...original.record.draft, weekly: '150' }, manual_id: 'owned-c' }, original.raw);
    if (!edited.ok) throw new Error('Edited record expected');
    const ack = acknowledgeSharedRouteRecovery(binding(), edited.record, write, edited.raw);
    expect(ack.ok).toBe(true); if (!ack.ok) return;
    expect(ack.record.pending).toBeNull(); expect(ack.record.dirty).toBe(true);
    expect(ack.record.draft.weekly).toBe('150'); expect(ack.record.manual_id).toBe('owned-c');
  });
  it.each(['manual-id', 'manual-review', 'disabled-exam'])('keeps %s unsent form data dirty even without a later generation', omitted => {
    const record = pendingRecord();
    if (omitted === 'manual-id') record.manual_id = 'owned-extra';
    if (omitted === 'manual-review') record.manual_review.lesson_id = 'not-added-yet';
    if (omitted === 'disabled-exam') record.draft.exams[1]!.first_exam_on = '2026-10-28';
    const saved = save(record); const ack = acknowledgeSharedRouteRecovery(binding(), saved.record, write, saved.raw);
    expect(ack.ok).toBe(true); if (ack.ok) expect(ack.record.dirty).toBe(true);
  });
  it('marks only fully represented acknowledged form state clean', () => {
    const original = save(); const ack = acknowledgeSharedRouteRecovery(binding(), original.record, write, original.raw);
    expect(ack.ok).toBe(true); if (ack.ok) { expect(ack.record.pending).toBeNull(); expect(ack.record.dirty).toBe(false); }
  });
  it('does not retire another original UUID, a newer journal revision or replaced raw bytes', () => {
    const original = save(); const nextBody = { ...write, client_write_uuid: 'aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee' };
    const next = writeSharedRouteRecovery(binding(), { ...original.record,
      pending: { ...original.record.pending!, body: nextBody } }, original.raw);
    if (!next.ok) throw new Error('New pending expected');
    expect(acknowledgeSharedRouteRecovery(binding(), original.record, write, original.raw).ok).toBe(false);
    expect(acknowledgeSharedRouteRecovery(binding(), next.record, write, next.raw).ok).toBe(false);
    expect(sessionStorage.getItem(binding().key)).toBe(next.raw);
    expect(resetSharedRouteRecovery(binding(), original.raw)).toBe(false);
    expect(sessionStorage.getItem(binding().key)).toBe(next.raw);
  });
  it('an exact own reset removes only this case and keeps a different case draft', () => {
    const first = save(); const other = binding('case-b'); const second = writeSharedRouteRecovery(other, newSharedRouteRecovery(other, draft()), null);
    if (!second.ok) throw new Error('Other case draft expected');
    expect(resetSharedRouteRecovery(binding(), first.raw)).toBe(true);
    expect(sessionStorage.getItem(binding().key)).toBeNull(); expect(sessionStorage.getItem(other.key)).toBe(second.raw);
  });
  it('independent tab session stores keep different drafts for the same owner/case', () => {
    class TabStorage implements Storage {
      [name: string]: unknown;
      values = new Map<string, string>([[ownerKey, 'demo']]);
      get length() { return this.values.size; }
      clear() { this.values.clear(); } key(index: number) { return [...this.values.keys()][index] ?? null; }
      getItem(key: string) { return this.values.get(key) ?? null; } removeItem(key: string) { this.values.delete(key); }
      setItem(key: string, value: string) { this.values.set(key, value); }
    }
    const a = new TabStorage(); const b = new TabStorage();
    const tab = vi.spyOn(window, 'sessionStorage', 'get').mockReturnValue(a);
    const first = save(); tab.mockReturnValue(b); expect(readSharedRouteRecovery(binding()).state).toBe('empty');
    const second = save({ ...pendingRecord(), draft: { ...draft(), weekly: '180' } });
    tab.mockReturnValue(a); expect(readSharedRouteRecovery(binding())).toMatchObject({ state: 'valid', raw: first.raw });
    tab.mockReturnValue(b); expect(readSharedRouteRecovery(binding())).toMatchObject({ state: 'valid', raw: second.raw });
  });
});
