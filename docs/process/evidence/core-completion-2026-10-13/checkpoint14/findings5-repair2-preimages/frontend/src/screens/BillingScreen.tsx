import { t as translate } from '@/lib/i18n';
import { useTranslation } from '@/lib/useTranslation';
import { useCallback, useEffect, useRef, useState } from 'react';
import { api, ApiError } from '@/api/client';
import { PaymentModal } from '@/components/PaymentModal';
import { Chip, Loading, Notice, Panel } from '@/components/primitives';
import { useStore } from '@/lib/store';
import type { EntitlementView, Pricing } from '@/types';

export function BillingScreen({ onPrepare }: { onPrepare?: () => void } = {}) {
  const { t } = useTranslation();
  const { savedProfile, refreshResults, unlockFromSubscription, currentAdmissionsCase } = useStore();
  const identity = currentAdmissionsCase();
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
      error: problem instanceof ApiError ? problem.message : problem ? translate('billing.accessReadFailure') : profileId && !nextEntitlement ? translate('billing.accessMismatch') : '' });
  }, [active, key, profileId]);
  useEffect(() => { void load(); return () => { ++readSerial.current; }; }, [load]);
  const setError = (nextError: string) => {
    if (active()) setStored(old => old?.key === key ? { ...old, entitlement: null, error: nextError } : old);
  };
  const useSubscription = async () => {
    if (!active() || !profileId || !entitlement || unlockBusy.current === key) return;
    unlockBusy.current = key; setUnlocking(key);
    try { await unlockFromSubscription(profileId); if (active()) await load(); }
    catch (problem) { if (active()) setError(problem instanceof ApiError ? problem.message : translate('billing.accessReadFailure')); }
    finally { if (unlockBusy.current === key) unlockBusy.current = null; if (active()) setUnlocking(null); }
  };
  const preparationAccess = entitlement?.preparation_access ?? null;
  return (
    <div className="stack stack--loose">
      <div className="screen__head">
        <p className="screen__eyebrow">BILLING</p>
        <h1 className="screen__title">Unlock more <span className="find-yellow">clarity.</span></h1>
        <p className="screen__lede">Access is granted per applicant case. Prices and availability come from this deployment.</p>
      </div>
      {loading && <Loading label="Loading access for this case…" />}
      {error && <Notice kind="risk">{error}</Notice>}
      {!loading && pricing && (
        <Panel title="Full research for this case" hint={savedProfile ? 'Your current applicant case' : 'Create or select an applicant case to unlock research.'}>
          <div className="billing-summary">
            <div>
              <span className="home-eyebrow">CURRENT ACCESS</span>
              <h2>{entitlement?.full_access ? 'Full access' : entitlement ? 'Free preview' : t('billing.accessUnknown')}</h2>
              <p className="muted small">{entitlement?.full_access ? 'Full research is available for this case.' : entitlement ? t('billing.personalUngated') : t('billing.refreshBeforeAction')}</p>
            </div>
            <div className="billing-summary__action">
              {entitlement?.full_access ? <Chip tone="ok">Unlocked</Chip> : (
                <>
                  {entitlement?.subscription_cases_left != null && entitlement.subscription_cases_left > 0 ? (
                    <button className="btn btn--primary" type="button" disabled={!profileId || unlocking === key}
                      onClick={() => void useSubscription()}>
                      Use 1 subscription case · {entitlement.subscription_cases_left} left
                    </button>
                  ) : pricing.payments_enabled ? (
                    <button className="btn btn--primary" type="button" disabled={!profileId || !entitlement || unlocking === key} onClick={() => { if (active() && profileId && entitlement) setPayment({ key, profileId, price: pricing.case_unlock_price_kzt }); }}>
                      Unlock for {pricing.case_unlock_price_kzt.toLocaleString()} {pricing.currency}
                    </button>
                  ) : <Chip>Payments are unavailable here</Chip>}
                </>
              )}
            </div>
          </div>
          {pricing.includes.length > 0 && <ul className="billing-includes">{pricing.includes.map((item) => <li key={item}>{item}</li>)}</ul>}
        </Panel>
      )}
      {!loading && preparationAccess && <Panel title="Exam preparation access">
        <p className="small muted">{t('preparation.optionalHint')}</p>
        <p>{preparationAccess.development_only ? 'Development starter access — not a paid subscription.'
          : preparationAccess.allowed ? 'Your eligible started subscription includes original starter preparation.'
            : 'No eligible started subscription term was confirmed for preparation.'}</p>
        <p className="small muted">IELTS Reading, SAT Math and SAT Reading &amp; Writing starters. This is not a full course, official mock or score guarantee. Case quota and research access do not decide this entitlement.</p>
        <p className="xs">Access reason: {preparationAccess.reason.replace(/_/g, ' ')}</p>
        {onPrepare && <button type="button" className="btn" onClick={onPrepare}>Open preparation &amp; history</button>}
      </Panel>}
      {!loading && error && <button type="button" className="btn" onClick={() => void load()}>{t('billing.refreshAccess')}</button>}
      {payment?.key === key && payment.profileId === profileId && <PaymentModal profileId={payment.profileId} priceKzt={payment.price}
        onClose={() => { if (active()) setPayment(old => old === payment ? null : old); }} onPaid={async () => {
          if (!active()) return;
          setPayment(old => old === payment ? null : old);
          await load();
          if (active()) await refreshResults();
        }} />}

    </div>
  );
}
