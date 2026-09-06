/**
 * What a locked panel says instead of showing nothing.
 *
 * A school with quota left is offered its own subscription first — asking for
 * 4990 ₸ when the school has already paid for the year would be wrong.
 */

import { useState } from 'react';
import { PaymentModal } from './PaymentModal';
import { useStore } from '@/lib/store';

interface Props {
  /** Test seam: drive the component without a 402 round trip. */
  testPaywall?: { profileId: string; priceKzt: number; casesLeft: number | null };
}

export function PaywallNotice({ testPaywall }: Props) {
  const {
    paywall: storePaywall,
    clearPaywall,
    refreshResults,
    unlockFromSubscription,
  } = useStore();
  const [paying, setPaying] = useState(false);
  const paywall = testPaywall ?? storePaywall;

  if (!paywall) return null;

  const fromSubscription = paywall.casesLeft !== null && paywall.casesLeft > 0;

  return (
    <div style={{ padding: 'var(--space-4) var(--space-6) 0' }}>
      <div className="notice notice--info" role="note">
        <div style={{ flex: 1 }}>
          <strong>Этот раздел открывается после оплаты кейса.</strong> Полный охват программ,
          источник под каждым значением, финансирование и экспорт.
        </div>
        {fromSubscription ? (
          <button
            className="btn btn--sm btn--primary"
            onClick={() => void unlockFromSubscription(paywall.profileId)}
          >
            Открыть из подписки (осталось {paywall.casesLeft})
          </button>
        ) : (
          <button className="btn btn--sm btn--primary" onClick={() => setPaying(true)}>
            Открыть за {paywall.priceKzt} ₸
          </button>
        )}
        <button className="btn btn--sm btn--ghost" onClick={clearPaywall}>
          Не сейчас
        </button>
      </div>

      {paying && (
        <PaymentModal
          profileId={paywall.profileId}
          priceKzt={paywall.priceKzt}
          onClose={() => setPaying(false)}
          onPaid={() => {
            setPaying(false);
            clearPaywall();
            void refreshResults();
          }}
        />
      )}
    </div>
  );
}
