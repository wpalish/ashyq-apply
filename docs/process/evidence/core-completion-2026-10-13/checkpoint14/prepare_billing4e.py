from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parent;repo=root.parents[1]/'work/unimatch-calendar-materials';out=root/'billing4e-proposal';out.mkdir(exist_ok=False)
paths=['frontend/src/screens/BillingScreen.tsx','frontend/src/screens/BillingScreen.test.tsx','frontend/src/screens/BillingScreen.preparation.test.tsx','frontend/src/screens/BillingScreen.case.test.tsx']
rows={}
for p in paths:
 f=repo/p;raw=f.read_bytes() if f.exists() else None;rows[p]=hashlib.sha256(raw).hexdigest() if raw is not None else None
 if raw is not None:q=root/'billing4e-preimages'/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(raw)
(root/'BILLING_4E_PREPARATION.json').write_text(json.dumps({'status':'EXTERNAL_ONLY_NOT_GRANTED_NOT_APPLIED','baseline':'9e41e0b3','paths':rows,'contract':'Bind every read/payment callback/subscription callback and displayed entitlement to synchronous currentAdmissionsCase plus rendered identity/serial. Unknown on own API read failure; no stale quota/payment modal across A→B→A. No server/payment protocol changes.'},indent=2)+'\n')
def put(p,t):q=out/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(t)
p=paths[0];t=(repo/p).read_text().replace('useEffect, useState','useCallback, useEffect, useRef, useState')
t=t.replace('savedProfile, refreshResults, unlockFromSubscription','savedProfile, refreshResults, unlockFromSubscription, currentAdmissionsCase')
a=t.index('  const [pricing,');b=t.index('  return (',a)
t=t[:a]+'''  const identity = currentAdmissionsCase();
  const key = JSON.stringify([identity.scope === undefined ? 'demo' : identity.scope, identity.profile_id, identity.case_epoch]);
  const mounted = useRef(true); const readSerial = useRef(0);
  const [stored, setStored] = useState<{ key: string; pricing: Pricing | null; entitlement: EntitlementView | null; loading: boolean; error: string } | null>(null);
  const [payment, setPayment] = useState<{ key: string; profileId: string; price: number } | null>(null);
  const [unlocking, setUnlocking] = useState<string | null>(null); const unlockBusy = useRef<string | null>(null);
  const visible = stored?.key === key ? stored : null;
  const pricing = visible?.pricing ?? null; const entitlement = visible?.entitlement ?? null;
  const loading = visible?.loading ?? true; const error = visible?.error ?? '';
  const profileId = identity.profile_id === savedProfile?.id && identity.scope !== null ? identity.profile_id : null;
  const active = useCallback(() => {
    const live = currentAdmissionsCase();
    return mounted.current && key === JSON.stringify([live.scope === undefined ? 'demo' : live.scope, live.profile_id, live.case_epoch]);
  }, [currentAdmissionsCase, key]);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; ++readSerial.current; }; }, []);
  const load = useCallback(async () => {
    if (!active()) return; const serial = ++readSerial.current;
    setStored({ key, pricing: null, entitlement: null, loading: true, error: '' });
    const [priceRead, accessRead] = await Promise.allSettled([api.pricing(), profileId ? api.entitlements(profileId) : Promise.resolve(null)]);
    if (!active() || serial !== readSerial.current) return;
    const nextPricing = priceRead.status === 'fulfilled' ? priceRead.value : null;
    const nextEntitlement = accessRead.status === 'fulfilled' && accessRead.value?.profile_id === profileId ? accessRead.value : null;
    const problem = priceRead.status === 'rejected' ? priceRead.reason : accessRead.status === 'rejected' ? accessRead.reason : null;
    setStored({ key, pricing: nextPricing, entitlement: nextEntitlement, loading: false,
      error: problem instanceof ApiError ? problem.message : problem ? 'Could not confirm access for this case. Refresh to try again.' : profileId && !nextEntitlement ? 'The access response did not match this case.' : '' });
  }, [active, key, profileId]);
  useEffect(() => { void load(); return () => { ++readSerial.current; }; }, [load]);
  const setError = (nextError: string) => {
    if (active()) setStored(old => old?.key === key ? { ...old, entitlement: null, error: nextError } : old);
  };
  const useSubscription = async () => {
    if (!active() || !profileId || !entitlement || unlockBusy.current === key) return;
    unlockBusy.current = key; setUnlocking(key);
    try { await unlockFromSubscription(profileId); if (active()) await load(); }
    catch (problem) { if (active()) setError(problem instanceof ApiError ? problem.message : 'Could not confirm access for this case. Refresh to try again.'); }
    finally { if (unlockBusy.current === key) unlockBusy.current = null; if (active()) setUnlocking(null); }
  };
  const preparationAccess = entitlement?.preparation_access ?? null;
''' + t[b:]
t=t.replace("{entitlement?.full_access ? 'Full access' : 'Free preview'}", "{entitlement?.full_access ? 'Full access' : entitlement ? 'Free preview' : 'Access not confirmed'}")
t=t.replace("{entitlement?.full_access ? 'Full research is available for this case.' : 'Unlock all matches, funding details, evidence, exports and documents for this case.'}", "{entitlement?.full_access ? 'Full research is available for this case.' : entitlement ? 'Research access does not restrict your personal document tasks and application history.' : 'Refresh access before using a subscription case or starting payment.'}")
a=t.index('disabled={!savedProfile}\n                      onClick={async');b=t.index('                      }}>\n                      Use 1 subscription',a)
t=t[:a]+"disabled={!profileId || unlocking === key}\n                      onClick={() => void useSubscription()}"+t[b:].replace('                      }}>\n                      Use 1 subscription','>\n                      Use 1 subscription',1)
t=t.replace("disabled={!savedProfile} onClick={() => setPaying(true)}", "disabled={!profileId || !entitlement || unlocking === key} onClick={() => { if (active() && profileId && entitlement) setPayment({ key, profileId, price: pricing.case_unlock_price_kzt }); }}")
a=t.index('      {paying &&');b=t.index('\n    </div>',a)
t=t[:a]+'''      {!loading && error && <button type="button" className="btn" onClick={() => void load()}>Refresh access</button>}
      {payment?.key === key && payment.profileId === profileId && <PaymentModal profileId={payment.profileId} priceKzt={payment.price}
        onClose={() => { if (active()) setPayment(old => old === payment ? null : old); }} onPaid={async () => {
          if (!active()) return;
          setPayment(old => old === payment ? null : old);
          await load();
          if (active()) await refreshResults();
        }} />}
''' +t[b:]
put(p,t)
p=paths[1];t=(repo/p).read_text().replace('    savedProfile: profileId ?', "    currentAdmissionsCase: () => ({ scope: undefined, profile_id: profileId, case_epoch: 1 }),\n    savedProfile: profileId ?");put(p,t)
p=paths[2];t=(repo/p).read_text().replace('  savedProfile: { id: state.profileId },', '  currentAdmissionsCase: () => ({ scope: undefined, profile_id: state.profileId, case_epoch: 1 }),\n  savedProfile: { id: state.profileId },');put(p,t)
put(paths[3],'''import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { api } from '@/api/client';
import { BillingScreen } from './BillingScreen';
import { deferred } from './preparationFixtures';
import type { EntitlementView } from '@/types';
const state = vi.hoisted(() => ({ id: 'A', epoch: 1, unlock: vi.fn(), refresh: vi.fn(), paid: null as null | (() => Promise<void>) }));
vi.mock('@/lib/store', () => ({ useStore: () => ({ savedProfile: { id: state.id }, currentAdmissionsCase: () => ({ scope: undefined, profile_id: state.id, case_epoch: state.epoch }), unlockFromSubscription: state.unlock, refreshResults: state.refresh }) }));
vi.mock('@/components/PaymentModal', () => ({ PaymentModal: ({ profileId, onPaid }: { profileId: string; onPaid: () => Promise<void> }) => { state.paid = onPaid; return <div>Own payment for {profileId}</div>; } }));
const access = (profile_id: string, full_access = false, left: number | null = null): EntitlementView => ({ profile_id, full_access, subscription_cases_left: left, subscription_queued: 0 });
beforeEach(() => {
  state.id = 'A'; state.epoch = 1; state.paid = null; state.unlock.mockReset(); state.refresh.mockReset();
  vi.spyOn(api, 'pricing').mockResolvedValue({ case_unlock_price_kzt: 7300, currency: 'KZT', payments_enabled: true, includes: [] });
  vi.spyOn(api, 'entitlements').mockImplementation(async id => access(id));
});
afterEach(() => vi.restoreAllMocks());
it('hides previous full research/quota when the next case read fails and keeps access unknown', async () => {
  vi.mocked(api.entitlements).mockResolvedValueOnce(access('A', true, 4)); const view = render(<BillingScreen />);
  await screen.findByText('Full access'); vi.mocked(api.entitlements).mockRejectedValueOnce(new Error('Synthetic read failure'));
  state.id = 'B'; state.epoch = 2; view.rerender(<BillingScreen />);
  expect(screen.queryByText('Full access')).toBeNull(); await screen.findByText('Access not confirmed');
  expect(screen.queryByRole('button', { name: /Use 1 subscription/ })).toBeNull();
  expect(screen.getByRole('button', { name: 'Unlock for 7,300 KZT' })).toBeDisabled();
});
it('rejects a late A response after A→B→A despite a matching profile ID', async () => {
  const old = deferred<EntitlementView>(); const fresh = deferred<EntitlementView>();
  vi.mocked(api.entitlements).mockImplementationOnce(() => old.promise).mockResolvedValueOnce(access('B')).mockImplementationOnce(() => fresh.promise);
  const view = render(<BillingScreen />); state.id = 'B'; state.epoch = 2; view.rerender(<BillingScreen />);
  await screen.findByText('Free preview'); state.id = 'A'; state.epoch = 3; view.rerender(<BillingScreen />);
  await act(async () => old.resolve(access('A', true, 5))); expect(screen.queryByText('Full access')).toBeNull();
  await act(async () => fresh.resolve(access('A'))); await screen.findByText('Free preview');
});
it('hides an old payment and fences its callback before the new case rerenders', async () => {
  const view = render(<BillingScreen />); fireEvent.click(await screen.findByRole('button', { name: 'Unlock for 7,300 KZT' }));
  await screen.findByText('Own payment for A'); const paid = state.paid; if (!paid) throw new Error('Synthetic callback');
  state.id = 'B'; state.epoch = 2; await act(async () => paid()); expect(state.refresh).not.toHaveBeenCalled();
  view.rerender(<BillingScreen />); expect(screen.queryByText('Own payment for A')).toBeNull();
});
it('fences a late subscription response and offers no stale quota', async () => {
  const done = deferred<void>(); state.unlock.mockImplementationOnce(() => done.promise);
  vi.mocked(api.entitlements).mockResolvedValueOnce(access('A', false, 2)); const view = render(<BillingScreen />);
  fireEvent.click(await screen.findByRole('button', { name: 'Use 1 subscription case · 2 left' }));
  state.id = 'B'; state.epoch = 2; view.rerender(<BillingScreen />); await act(async () => done.resolve());
  await screen.findByText('Free preview'); expect(screen.queryByRole('button', { name: /Use 1 subscription/ })).toBeNull();
  expect(vi.mocked(api.entitlements).mock.calls.filter(([id]) => id === 'A')).toHaveLength(1);
});
''')
print('External Billing case-generation proposal ready; not granted/applied/executed.')
