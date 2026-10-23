import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { api } from '@/api/client';
import { MessagesScreen } from '@/screens/MessagesScreen';
import type { MessagePage, MessageView, PersonCard } from '@/types';

const person: PersonCard = {
  user_id: 'synthetic-loading-peer', display_name: 'Synthetic loading peer', status: null,
  target_city: '', target_major: '', universities: [], dm_policy: 'anyone',
  bio: '', can_message: true,
};
const incoming: MessageView = {
  id: 'loading-incoming', body: 'Incoming history before the reply',
  created_at: '2026-10-09T00:00:01.000Z', mine: false,
};
const reply: MessageView = {
  id: 'loading-reply', body: 'Reply after the initial conversation loads',
  created_at: '2026-10-09T00:00:02.000Z', mine: true,
};
function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => { resolve = done; });
  return { promise, resolve };
}
async function flush() {
  await act(async () => { for (let i = 0; i < 15; i++) await Promise.resolve(); });
}
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

it('blocks sending during the initial conversation read and allows the retained draft after it resolves', async () => {
  const initial = deferred<MessagePage>();
  vi.spyOn(api, 'conversations').mockResolvedValue({ items: [], next_cursor: null });
  const read = vi.spyOn(api, 'conversation').mockReturnValue(initial.promise);
  const send = vi.spyOn(api, 'sendMessage').mockResolvedValue(reply);
  render(<MessagesScreen openWith={person.user_id} onOpenChange={() => {}} onReadSomething={() => {}} />);
  await flush();
  expect(read).toHaveBeenCalledWith(person.user_id, undefined);

  const composer = screen.getByRole('textbox');
  fireEvent.change(composer, { target: { value: reply.body } });
  expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled();
  // A form submission must obey the same pending-read guard as the button.
  fireEvent.submit(composer.closest('form')!);
  await flush();
  expect(send).not.toHaveBeenCalled();
  expect(composer).toHaveValue(reply.body);

  initial.resolve({ person, items: [incoming], next_cursor: null });
  await flush();
  expect(screen.getByText(person.display_name)).toBeInTheDocument();
  expect(screen.getByText(incoming.body)).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Send' })).toBeEnabled();
  expect(composer).toHaveValue(reply.body);
  fireEvent.submit(composer.closest('form')!);
  await flush();
  expect(send).toHaveBeenCalledTimes(1);
  expect(send).toHaveBeenCalledWith(person.user_id, reply.body);
  expect(screen.getAllByTestId(/^message-/)).toHaveLength(2);
  expect(screen.getByText(incoming.body)).toBeInTheDocument();
  expect(screen.getAllByText(reply.body)).toHaveLength(1);
  expect(composer).toHaveValue('');
});
