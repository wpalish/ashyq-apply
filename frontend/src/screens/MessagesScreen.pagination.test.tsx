import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { api } from '@/api/client';
import { MessagesScreen } from '@/screens/MessagesScreen';
import type { MessageView, PersonCard } from '@/types';

const person: PersonCard = {
  user_id: 'synthetic-peer', display_name: 'Synthetic peer', status: null,
  target_city: '', target_major: '', universities: [], dm_policy: 'anyone',
  bio: '', can_message: true,
};
const incoming = (number: number): MessageView => ({
  id: `m-${String(number).padStart(2, '0')}`,
  body: `Incoming ${String(number).padStart(2, '0')}`,
  created_at: new Date(Date.UTC(2026, 9, 9, 0, 0, number)).toISOString(),
  mine: false,
});
const reply: MessageView = {
  id: 'm-26', body: 'Outgoing reply 26',
  created_at: '2026-10-09T00:00:26.000Z', mine: true,
};
async function flush() {
  await act(async () => { for (let i = 0; i < 15; i++) await Promise.resolve(); });
}
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

it('keeps a reply after all earlier incoming messages when the remaining page is loaded', async () => {
  vi.spyOn(api, 'conversations').mockResolvedValue({ items: [], next_cursor: null });
  const pages = vi.spyOn(api, 'conversation').mockImplementation(async (id, cursor) => {
    expect(id).toBe(person.user_id);
    return {
      person,
      // The second GET also returns the reply already appended by POST.
      items: cursor ? [...Array.from({ length: 5 }, (_, i) => incoming(i + 21)), reply]
        : Array.from({ length: 20 }, (_, i) => incoming(i + 1)),
      next_cursor: cursor ? null : 'after-20',
    };
  });
  const send = vi.spyOn(api, 'sendMessage').mockResolvedValue(reply);
  render(<MessagesScreen openWith={person.user_id} onOpenChange={() => {}} onReadSomething={() => {}} />);
  await flush();
  expect(screen.getAllByTestId(/^message-/)).toHaveLength(20);
  expect(screen.queryByText('Incoming 25')).toBeNull();

  const composer = screen.getByRole('textbox');
  fireEvent.change(composer, { target: { value: reply.body } });
  fireEvent.submit(composer.closest('form')!);
  await flush();
  expect(send).toHaveBeenCalledWith(person.user_id, reply.body);
  expect(screen.getByText(reply.body)).toBeInTheDocument();
  expect(composer).toHaveValue('');

  fireEvent.click(screen.getByRole('button', { name: 'Load more messages' }));
  await flush();
  expect(pages).toHaveBeenLastCalledWith(person.user_id, 'after-20');
  expect(screen.getAllByTestId(/^message-/)).toHaveLength(26);
  expect(screen.getAllByText(reply.body)).toHaveLength(1);
  expect(screen.queryByRole('button', { name: 'Load more messages' })).toBeNull();
  const visibleBodies = screen.getAllByText(/^(?:Incoming \d{2}|Outgoing reply 26)$/)
    .map((node) => node.textContent);
  expect(visibleBodies).toEqual([
    ...Array.from({ length: 25 }, (_, i) => `Incoming ${String(i + 1).padStart(2, '0')}`),
    reply.body,
  ]);
});
