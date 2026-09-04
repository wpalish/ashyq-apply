/**
 * What a locked panel says instead of showing nothing.
 *
 * Raised from the store's paywall state, which is set whenever a gated route
 * answered 402 — so this appears wherever the locked material was asked for.
 */

import { useState } from 'react';
import { PaymentModal } from './PaymentModal';
import { useStore } from '@/lib/store';

export function PaywallNotice() {
  const { paywall, clearPaywall, refreshResults } = useStore();
  const [paying, setPaying] = useState(false);

  if (!paywall) return null;

  return (
    <div style={{ padding: 'var(--space-4) var(--space-6) 0' }}>
      <div className="notice notice--info" role="note">
        <div style={{ flex: 1 }}>
          <strong>Этот раздел открывается после оплаты кейса.</strong> Полный охват программ,
          источник под каждым значением, финансирование и экспорт.
        </div>
        <button className="btn btn--sm btn--primary" onClick={() => setPaying(true)}>
          Открыть за {paywall.priceKzt} ₸
        </button>
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
