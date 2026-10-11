import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { api, ApiError, isPaymentRequired } from './client';
import { access, attempt, catalogue, deferred, lesson, plan, progress } from '@/screens/preparationFixtures';
import type { PreparationAttemptInput } from '@/types';
const ownerA = 'auth:["synthetic-a","workspace-a"]';
const ownerB = 'auth:["synthetic-b","workspace-b"]';
const response = (body: unknown, status = 200) => new Response(JSON.stringify(body), {
  status, headers: { 'Content-Type': 'application/json' },
});
const input = (): PreparationAttemptInput => ({
  attempt_id: '024706d1-04c0-4bdf-9024-70333102eaa1', lesson_id: 'ielts-reading-1', version: catalogue().version,
  answers: [{ question_id: 'ielts-reading-1-q1', choice_id: 'a' }],
});
beforeEach(() => {
  localStorage.clear(); sessionStorage.clear();
  localStorage.setItem('ashyq.applicantOwner', ownerA); sessionStorage.setItem('ashyq.applicantOwner', ownerA);
});
afterEach(() => { vi.unstubAllGlobals(); });

describe('preparation API contract through the native owner boundary', () => {
  it('uses encoded case and lesson identifiers, version and own progress limit', async () => {
    const transport = vi.fn()
      .mockResolvedValueOnce(response(catalogue()))
      .mockResolvedValueOnce(response(access()))
      .mockResolvedValueOnce(response(plan('case/a ?')))
      .mockResolvedValueOnce(response(lesson()))
      .mockResolvedValueOnce(response(progress('case/a ?')));
    vi.stubGlobal('fetch', transport);
    await api.preparationCatalogue(); await api.preparationAccess('case/a ?');
    await api.preparationPlan('case/a ?', 'result/a ?');
    await api.preparationLesson('case/a ?', 'lesson/a ?', 'version/a ?');
    await api.preparationProgress('case/a ?');
    const urls = transport.mock.calls.map(call => call[0]);
    expect(urls).toEqual([
      '/api/preparation/catalogue', '/api/profiles/case%2Fa%20%3F/preparation/access',
      '/api/profiles/case%2Fa%20%3F/preparation/plan?result_id=result%2Fa+%3F',
      '/api/profiles/case%2Fa%20%3F/preparation/lessons/lesson%2Fa%20%3F?version=version%2Fa%20%3F',
      '/api/profiles/case%2Fa%20%3F/preparation/progress?limit=20',
    ]);
    expect(transport.mock.calls.every(call => call[1].credentials === 'include')).toBe(true);
  });

  it('sends the exact immutable attempt payload again without generating a new id in the client', async () => {
    const payload = input();
    const transport = vi.fn().mockImplementation(async () => response(attempt(payload)));
    vi.stubGlobal('fetch', transport);
    expect(await api.submitPreparation('case/a', payload)).toEqual(attempt(payload));
    expect(await api.submitPreparation('case/a', payload)).toEqual(attempt(payload));
    expect(transport).toHaveBeenNthCalledWith(1, '/api/profiles/case%2Fa/preparation/attempts', {
      method: 'POST', body: JSON.stringify(payload), credentials: 'include', headers: { 'Content-Type': 'application/json' },
    });
    expect(transport.mock.calls[1]).toEqual(transport.mock.calls[0]);
  });

  it('retains the preparation access error and does not misclassify it as a case purchase', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({ detail: {
      code: 'preparation_subscription_required', message: 'An eligible started subscription term is required for preparation.',
    } }, 402)));
    const error: unknown = await api.preparationLesson('case-a', 'ielts-reading-1', catalogue().version).catch(problem => problem);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 402, code: 'preparation_subscription_required',
      message: 'An eligible started subscription term is required for preparation.' });
    expect(isPaymentRequired(error)).toBe(false);
  });

  it('preserves the pre-existing case-unlock 402 classification', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({ code: 'payment_required', detail: 'Unlock this case',
      profile_id: 'case-a', price_kzt: 7300, subscription_cases_left: 0 }, 402)));
    const error: unknown = await api.preparationProgress('case-a').catch(problem => problem);
    expect(isPaymentRequired(error)).toBe(true);
  });

  it('refuses a stale-tab attempt before any transport under the new shared cookie owner', async () => {
    const transport = vi.fn().mockResolvedValue(response(attempt(input())));
    vi.stubGlobal('fetch', transport); localStorage.setItem('ashyq.applicantOwner', ownerB);
    await expect(api.submitPreparation('case-a', input())).rejects.toThrow(/workspace changed/);
    expect(transport).not.toHaveBeenCalled();
  });

  it('rejects late history after another tab changes the owner', async () => {
    const pending = deferred<Response>();
    const transport = vi.fn().mockReturnValue(pending.promise);
    vi.stubGlobal('fetch', transport);
    const read = api.preparationProgress('case-a');
    localStorage.setItem('ashyq.applicantOwner', ownerB);
    pending.resolve(response(progress()));
    await expect(read).rejects.toThrow(/workspace changed/);
    expect(transport).toHaveBeenCalledTimes(1);
  });

  it('omits an empty programme rather than sending a fabricated result id', async () => {
    const transport = vi.fn().mockResolvedValue(response(plan())); vi.stubGlobal('fetch', transport);
    await api.preparationPlan('case-a', null);
    expect(transport.mock.calls[0]![0]).toBe('/api/profiles/case-a/preparation/plan');
  });
});
