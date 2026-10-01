import { useEffect, useState } from 'react';
import { api, ApiError } from '@/api/client';
import { PaymentModal } from '@/components/PaymentModal';
import { Chip, Loading, Notice, Panel } from '@/components/primitives';
import { useStore } from '@/lib/store';
import type { EntitlementView, Pricing } from '@/types';

export function BillingScreen() {
  const { savedProfile, refreshResults, unlockFromSubscription } = useStore();
  const [pricing, setPricing] = useState<Pricing | null>(null);
  const [entitlement, setEntitlement] = useState<EntitlementView | null>(null);
  const [loading, setLoading] = useState(true);
  const [paying, setPaying] = useState(false);
  const [error, setError] = useState('');
  const profileId = savedProfile?.id ?? null;

  useEffect(() => {
    let alive = true;
    setLoading(true);
    Promise.all([
      api.pricing(),
      profileId ? api.entitlements(profileId) : Promise.resolve(null),
    ]).then(([nextPricing, nextEntitlement]) => {
      if (!alive) return;
      setPricing(nextPricing);
      setEntitlement(nextEntitlement);
      setError('');
    }).catch((problem) => {
      if (alive) setError(problem instanceof ApiError ? problem.message : 'Could not load billing information.');
    }).finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [profileId]);

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
              <h2>{entitlement?.full_access ? 'Full access' : 'Free preview'}</h2>
              <p className="muted small">{entitlement?.full_access ? 'Full research is available for this case.' : 'Unlock all matches, funding details, evidence, exports and documents for this case.'}</p>
            </div>
            <div className="billing-summary__action">
              {entitlement?.full_access ? <Chip tone="ok">Unlocked</Chip> : (
                <>
                  {entitlement?.subscription_cases_left != null && entitlement.subscription_cases_left > 0 ? (
                    <button className="btn btn--primary" type="button" disabled={!savedProfile}
                      onClick={async () => {
                        if (!savedProfile) return;
                        try { await unlockFromSubscription(savedProfile.id); setEntitlement(await api.entitlements(savedProfile.id)); }
                        catch (problem) { setError(problem instanceof ApiError ? problem.message : 'Could not unlock this case.'); }
                      }}>
                      Use 1 subscription case · {entitlement.subscription_cases_left} left
                    </button>
                  ) : pricing.payments_enabled ? (
                    <button className="btn btn--primary" type="button" disabled={!savedProfile} onClick={() => setPaying(true)}>
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
      {paying && savedProfile && pricing && <PaymentModal profileId={savedProfile.id} priceKzt={pricing.case_unlock_price_kzt} onClose={() => setPaying(false)} onPaid={async () => {
        setPaying(false);
        try { setEntitlement(await api.entitlements(savedProfile.id)); await refreshResults(); }
        catch { setError('Payment was received, but the access status could not be refreshed. Reload this page.'); }
      }} />}
    </div>
  );
}
