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
    <div className="modal-overlay">
      <div className="panel auth-card stack" role="dialog" aria-label="Оплата кейса">
        <div>
          <p className="screen__eyebrow">Kaspi</p>
          <h2>Полный отчёт по кейсу</h2>
          <p className="muted small">
            Разовая оплата — <strong>{priceKzt} ₸</strong>. Открывает полный охват программ,
            источник под каждым значением, финансирование и экспорт. Кейс остаётся открытым.
          </p>
        </div>

        {!order && (
          <>
            <div className="decision-group" role="group" aria-label="Способ оплаты">
              <button
                type="button"
                className={`decision-btn${method === 'phone' ? ' decision-btn--approve' : ''}`}
                aria-pressed={method === 'phone'}
                onClick={() => setMethod('phone')}
              >
                По номеру Kaspi
              </button>
              <button
                type="button"
                className={`decision-btn${method === 'qr' ? ' decision-btn--approve' : ''}`}
                aria-pressed={method === 'qr'}
                onClick={() => setMethod('qr')}
              >
                QR
              </button>
            </div>

            {method === 'phone' && (
              <label className="field" htmlFor="kaspi-phone">
                <span className="field__label">Номер телефона</span>
                <input
                  id="kaspi-phone"
                  inputMode="numeric"
                  value={phone}
                  onChange={(event) => setPhone(event.target.value.trim())}
                  placeholder="87071234455"
                />
                <span className="field__hint">
                  Счёт придёт в приложение Kaspi на этот номер.
                </span>
              </label>
            )}

            <button className="btn btn--primary" type="button" onClick={start} disabled={busy}>
              {busy ? 'Выставляем счёт…' : `Оплатить ${priceKzt} ₸`}
            </button>
          </>
        )}

        {order?.method === 'phone' && order.status === 'pending' && (
          <div className="notice notice--info">
            Счёт отправлен на {order.phone_masked}. Подтвердите его в приложении Kaspi — страница
            обновится сама.
          </div>
        )}

        {order?.method === 'qr' && order.qr_payload && (
          <div className="notice notice--info">
            Отсканируйте в приложении Kaspi: <code>{order.qr_payload}</code>
          </div>
        )}

        {order?.status === 'paid' && (
          <div className="notice notice--demo">Оплачено. Открываем полный отчёт…</div>
        )}

        {error && (
          <div className="notice notice--risk" role="alert">
            {error}
          </div>
        )}

        <button className="btn btn--ghost" type="button" onClick={onClose}>
          Закрыть
        </button>
      </div>
    </div>
  );
}
