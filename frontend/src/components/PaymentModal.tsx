/**
 * Unlocking one case.
 *
 * Two paths, because Kaspi has two: an invoice pushed to the payer's phone,
 * which works from any device, and a QR for when the payer is at a desktop.
 * Neither reports success to the browser, so both end in polling.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '@/api/client';
import type { OrderView, PaymentMethod } from '@/types';

const PHONE = /^8\d{10}$/;
const POLL_MS = 2000;
const MAX_POLLS = 150; // five minutes

interface Props {
  profileId: string;
  priceKzt: number;
  onClose: () => void;
  onPaid: () => void;
}

export function PaymentModal({ profileId, priceKzt, onClose, onPaid }: Props) {
  const [method, setMethod] = useState<PaymentMethod>('phone');
  const [phone, setPhone] = useState('');
  const [order, setOrder] = useState<OrderView | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const polls = useRef(0);

  const start = useCallback(async () => {
    setError('');
    if (method === 'phone' && !PHONE.test(phone)) {
      setError('Введите номер в формате 8XXXXXXXXXX');
      return;
    }
    setBusy(true);
    try {
      setOrder(
        await api.openOrder({
          profile_id: profileId,
          method,
          ...(method === 'phone' ? { phone } : {}),
        }),
      );
    } catch {
      setError('Не удалось выставить счёт. Попробуйте ещё раз.');
    } finally {
      setBusy(false);
    }
  }, [method, phone, profileId]);

  useEffect(() => {
    if (!order || order.status !== 'pending') return undefined;
    const timer = setInterval(async () => {
      polls.current += 1;
      if (polls.current > MAX_POLLS) {
        clearInterval(timer);
        setError('Счёт истёк. Откройте новый.');
        return;
      }
      try {
        const latest = await api.readOrder(order.id);
        setOrder(latest);
        if (latest.status === 'paid') {
          clearInterval(timer);
          onPaid();
        } else if (latest.status !== 'pending') {
          clearInterval(timer);
          setError('Счёт закрыт без оплаты.');
        }
      } catch {
        /* a transient read failure is not worth interrupting the wait */
      }
    }, POLL_MS);
    return () => clearInterval(timer);
  }, [order, onPaid]);

  return (
    <div className="modal" role="dialog" aria-label="Оплата кейса">
      <h2>Полный отчёт по кейсу</h2>
      <p>
        Разовая оплата — <strong>{priceKzt} ₸</strong>. Открывает полный охват программ,
        источник под каждым значением, финансирование и экспорт.
      </p>

      {!order && (
        <>
          <div role="group" aria-label="Способ оплаты">
            <button
              type="button"
              aria-pressed={method === 'phone'}
              onClick={() => setMethod('phone')}
            >
              По номеру Kaspi
            </button>
            <button type="button" aria-pressed={method === 'qr'} onClick={() => setMethod('qr')}>
              QR
            </button>
          </div>

          {method === 'phone' && (
            <label htmlFor="kaspi-phone">
              Номер телефона
              <input
                id="kaspi-phone"
                inputMode="numeric"
                value={phone}
                onChange={(event) => setPhone(event.target.value.trim())}
                placeholder="87071234455"
              />
            </label>
          )}

          <button type="button" onClick={start} disabled={busy}>
            {busy ? 'Выставляем счёт…' : 'Оплатить'}
          </button>
        </>
      )}

      {order?.method === 'phone' && order.status === 'pending' && (
        <p>Счёт отправлен на {order.phone_masked}. Подтвердите его в приложении Kaspi.</p>
      )}

      {order?.method === 'qr' && order.qr_payload && (
        <p>
          Отсканируйте в Kaspi: <code>{order.qr_payload}</code>
        </p>
      )}

      {order?.status === 'paid' && <p>Оплачено. Открываем полный отчёт…</p>}

      {error && <p role="alert">{error}</p>}

      <button type="button" onClick={onClose}>
        Закрыть
      </button>
    </div>
  );
}
