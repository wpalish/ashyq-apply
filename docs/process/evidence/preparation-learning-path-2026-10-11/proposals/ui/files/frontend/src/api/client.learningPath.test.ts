import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { api } from './client';
import { attempt, deferred, learningCatalogue, learningVersion, progress } from '@/screens/preparationFixtures';
import type { PreparationAttemptInput } from '@/types';
const ownerA = 'auth:["synthetic-a","workspace-a"]';
const ownerB = 'auth:["synthetic-b","workspace-b"]';
const response = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
const shortInput = (): PreparationAttemptInput => ({
  attempt_id: '024706d1-04c0-4bdf-9024-70333102eaa1', lesson_id: 'ielts-reading-completion-1', version: learningVersion,
  answers: [{ question_id: 'short-1', text: '  Dividers.  ' }],
});
beforeEach(() => {
  localStorage.clear(); sessionStorage.clear();
  localStorage.setItem('ashyq.applicantOwner', ownerA); sessionStorage.setItem('ashyq.applicantOwner', ownerA);
});
afterEach(() => { vi.unstubAllGlobals(); });
describe('opt-in learning-pack API compatibility', () => {
  it('encodes optional catalogue version while preserving the legacy no-argument URLs', async () => {
    const transport = vi.fn().mockImplementation(async () => response(learningCatalogue())); vi.stubGlobal('fetch', transport);
    await api.preparationCatalogue(); await api.preparationCatalogue(learningVersion);
    transport.mockImplementation(async () => response(progress('case/a ?')));
    await api.preparationProgress('case/a ?'); await api.preparationProgress('case/a ?', learningVersion);
    await api.preparationCatalogue('version/a ?');
    expect(transport.mock.calls.map(call => call[0])).toEqual([
      '/api/preparation/catalogue', `/api/preparation/catalogue?catalogue_version=${learningVersion}`,
      '/api/profiles/case%2Fa%20%3F/preparation/progress?limit=20',
      `/api/profiles/case%2Fa%20%3F/preparation/progress?catalogue_version=${learningVersion}&limit=20`,
      '/api/preparation/catalogue?catalogue_version=version%2Fa+%3F',
    ]);
  });
  it('preserves exact short text and immutable UUID/payload on replay without client-side grading', async () => {
    const payload = shortInput(); const transport = vi.fn().mockImplementation(async () => response(attempt(payload)));
    vi.stubGlobal('fetch', transport);
    expect(await api.submitPreparation('case/a ?', payload)).toEqual(attempt(payload));
    expect(await api.submitPreparation('case/a ?', payload)).toEqual(attempt(payload));
    expect(transport).toHaveBeenNthCalledWith(1, '/api/profiles/case%2Fa%20%3F/preparation/attempts', {
      method: 'POST', body: JSON.stringify(payload), credentials: 'include', headers: { 'Content-Type': 'application/json' },
    });
    expect(transport.mock.calls[1]).toEqual(transport.mock.calls[0]);
    expect(payload.answers).toEqual([{ question_id: 'short-1', text: '  Dividers.  ' }]);
  });
  it('reads an encoded owned attempt UUID review without requiring a new lesson or write', async () => {
    const saved = attempt(shortInput()); const body = { attempt: saved, lesson: null, notice: 'Saved exact version not available.' };
    const transport = vi.fn().mockResolvedValue(response(body)); vi.stubGlobal('fetch', transport);
    expect(await api.preparationAttemptReview('case/a ?', 'uuid/a ?')).toEqual(body);
    expect(transport).toHaveBeenCalledWith('/api/profiles/case%2Fa%20%3F/preparation/attempts/uuid%2Fa%20%3F/review', {
      credentials: 'include', headers: { 'Content-Type': 'application/json' },
    });
    expect(transport).toHaveBeenCalledTimes(1);
  });
  it('fences short writes before transport and late opt-in history under a changed shared owner', async () => {
    const pending = deferred<Response>(); const transport = vi.fn().mockReturnValue(pending.promise); vi.stubGlobal('fetch', transport);
    const read = api.preparationProgress('case-a', learningVersion);
    localStorage.setItem('ashyq.applicantOwner', ownerB);
    await expect(api.submitPreparation('case-a', shortInput())).rejects.toThrow(/workspace changed/);
    pending.resolve(response(progress())); await expect(read).rejects.toThrow(/workspace changed/);
    expect(transport).toHaveBeenCalledTimes(1);
  });
});
