import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { PaymentModal } from './PaymentModal';
import { api } from '@/api/client';
import type { OrderView } from '@/types';

const order: OrderView = {
  id: 'o1',
  profile_id: 'c1',
  status: 'pending',
  method: 'phone',
  amount_kzt: 4990,
  phone_masked: '8707***4455',
  qr_payload: '',
  qr_expires_at: null,
  created_at: '2026-09-04T10:00:00Z',
};

beforeEach(() => vi.useFakeTimers({ shouldAdvanceTime: true }));
afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

function open() {
  render(<PaymentModal profileId="c1" priceKzt={4990} onClose={() => {}} onPaid={() => {}} />);
}

describe('PaymentModal', () => {
  it('shows the price before asking for anything', () => {
    open();
    expect(screen.getByText(/4990/)).toBeInTheDocument();
  });

  it('refuses a malformed phone number without calling the API', () => {
    const openOrder = vi.spyOn(api, 'openOrder');
    open();
    fireEvent.change(screen.getByLabelText(/номер телефона/i), { target: { value: '123' } });
    fireEvent.click(screen.getByRole('button', { name: 'Оплатить' }));
    expect(openOrder).not.toHaveBeenCalled();
    expect(screen.getByRole('alert')).toHaveTextContent('8XXXXXXXXXX');
  });

  it('opens an order and polls until it is paid', async () => {
    vi.spyOn(api, 'openOrder').mockResolvedValue(order);
    const read = vi
      .spyOn(api, 'readOrder')
      .mockResolvedValueOnce(order)
      .mockResolvedValue({ ...order, status: 'paid' });
    const onPaid = vi.fn();

    render(<PaymentModal profileId="c1" priceKzt={4990} onClose={() => {}} onPaid={onPaid} />);
    fireEvent.change(screen.getByLabelText(/номер телефона/i), {
      target: { value: '87071234455' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Оплатить' }));

    await waitFor(() => expect(api.openOrder).toHaveBeenCalled());
    await vi.advanceTimersByTimeAsync(5000);
    await waitFor(() => expect(onPaid).toHaveBeenCalled());
    expect(read).toHaveBeenCalled();
  });

  it('never sends the full phone number to the screen after the invoice opens', async () => {
    vi.spyOn(api, 'openOrder').mockResolvedValue(order);
    vi.spyOn(api, 'readOrder').mockResolvedValue(order);
    open();
    fireEvent.change(screen.getByLabelText(/номер телефона/i), {
      target: { value: '87071234455' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Оплатить' }));
    await waitFor(() => expect(screen.getByText(/8707\*\*\*4455/)).toBeInTheDocument());
    expect(document.body.textContent).not.toContain('87071234455');
  });

  it('shows the QR payload when QR is chosen', async () => {
    vi.spyOn(api, 'openOrder').mockResolvedValue({
      ...order,
      method: 'qr',
      qr_payload: 'https://pay.kaspi.test/abc',
      qr_expires_at: '2099-01-01T00:00:00Z',
    });
    vi.spyOn(api, 'readOrder').mockResolvedValue({ ...order, method: 'qr' });

    open();
    fireEvent.click(screen.getByRole('button', { name: 'QR' }));
    fireEvent.click(screen.getByRole('button', { name: 'Оплатить' }));
    await waitFor(() => expect(screen.getByText(/pay.kaspi.test/)).toBeInTheDocument());
  });

  it('reports a failure to open the order instead of spinning', async () => {
    vi.spyOn(api, 'openOrder').mockRejectedValue(new Error('nope'));
    open();
    fireEvent.change(screen.getByLabelText(/номер телефона/i), {
      target: { value: '87071234455' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Оплатить' }));
    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument());
  });
});
