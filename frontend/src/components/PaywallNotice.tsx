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
    <div className="paywall" role="note">
      <h3>Этот раздел открывается после оплаты кейса</h3>
      <ul>
        <li>Все найденные программы, а не первые пять</li>
        <li>Источник под каждым значением</li>
        <li>Стипендии, стоимость и разрыв между ними</li>
        <li>Чек-лист документов и экспорт</li>
      </ul>
      <button type="button" onClick={() => setPaying(true)}>
        Открыть за {paywall.priceKzt} ₸
      </button>

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
