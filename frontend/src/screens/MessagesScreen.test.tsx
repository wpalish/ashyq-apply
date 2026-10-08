import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { api } from '@/api/client';
import { setLocale } from '@/lib/i18n';
import type { MessagePage, PersonCard } from '@/types';
import { MessagesScreen } from './MessagesScreen';

function person(id: string): PersonCard {
  return { user_id: id, display_name: id, status: null, target_city: '', target_major: '', universities: [], dm_policy: 'anyone', bio: '' };
}

function page(id: string, next_cursor: string | null = null): MessagePage {
  return { person: person(id), items: [{ id: `line-${id}`, body: `Message from ${id}`, mine: false, created_at: '2026-10-08T10:00:00Z' }], next_cursor, latest_cursor: next_cursor ?? `latest-${id}` };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((accept) => { resolve = accept; });
  return { promise, resolve };
}

beforeEach(() => {
  vi.restoreAllMocks();
  setLocale('en');
  vi.spyOn(api, 'conversations').mockResolvedValue({ items: [], next_cursor: null });
});

it('never shows a late response from the previous recipient in the current thread', async () => {
  const first = deferred<MessagePage>();
  const second = deferred<MessagePage>();
  vi.spyOn(api, 'conversation').mockImplementation((id) => id === 'Alice' ? first.promise : second.promise);
  const props = { onOpenChange: vi.fn(), onReadSomething: vi.fn() };
  const view = render(<MessagesScreen {...props} openWith="Alice" />);
  view.rerender(<MessagesScreen {...props} openWith="Bob" />);
  await act(async () => { second.resolve(page('Bob')); });
  expect(screen.getByText('Message from Bob')).toBeInTheDocument();
  await act(async () => { first.resolve(page('Alice')); });
  expect(screen.queryByText('Message from Alice')).not.toBeInTheDocument();
  expect(screen.getByText('Message from Bob')).toBeInTheDocument();
});

it('does not carry a draft into a different recipient and sends only to the displayed person', async () => {
  vi.spyOn(api, 'conversation').mockImplementation(async (id) => page(id));
  const send = vi.spyOn(api, 'sendMessage').mockResolvedValue({ id: 'sent', body: 'Hello Bob', mine: true, created_at: '2026-10-08T11:00:00Z' });
  const props = { onOpenChange: vi.fn(), onReadSomething: vi.fn() };
  const view = render(<MessagesScreen {...props} openWith="Alice" />);
  await screen.findByText('Message from Alice');
  fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Private draft for Alice' } });
  view.rerender(<MessagesScreen {...props} openWith="Bob" />);
  await screen.findByText('Message from Bob');
  expect(screen.getByRole('textbox')).toHaveValue('');
  fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Hello Bob' } });
  await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Send' })); });
  expect(send).toHaveBeenCalledExactlyOnceWith('Bob', 'Hello Bob');
});

it('keeps a message after a server failure and sends that draft on retry', async () => {
  vi.spyOn(api, 'conversation').mockResolvedValue(page('Alice'));
  const send = vi.spyOn(api, 'sendMessage').mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce({ id: 'sent', body: 'My question', mine: true, created_at: '2026-10-08T11:00:00Z' });
  render(<MessagesScreen openWith="Alice" onOpenChange={vi.fn()} onReadSomething={vi.fn()} />);
  await screen.findByText('Message from Alice');
  fireEvent.change(screen.getByRole('textbox'), { target: { value: 'My question' } });
  await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Send' })); });
  expect(screen.getByRole('textbox')).toHaveValue('My question');
  expect(screen.getByText('Could not send that.')).toBeInTheDocument();
  await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Send' })); });
  expect(screen.getByRole('textbox')).toHaveValue('');
  expect(send).toHaveBeenCalledTimes(2);
});

it('cannot send while the recipient is still loading or its read failed', async () => {
  vi.spyOn(api, 'conversation').mockRejectedValue(new Error('offline'));
  const send = vi.spyOn(api, 'sendMessage');
  render(<MessagesScreen openWith="Alice" onOpenChange={vi.fn()} onReadSomething={vi.fn()} />);
  expect(screen.getByRole('textbox')).toBeDisabled();
  await screen.findByText('Could not open this conversation.');
  expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled();
  expect(send).not.toHaveBeenCalled();
});

it('shows the next page instead of silently ending the thread at twenty messages', async () => {
  const conversation = vi.spyOn(api, 'conversation').mockResolvedValueOnce(page('Alice', 'next-page')).mockResolvedValueOnce({ ...page('Alice'), items: [{ id: 'last', body: 'The newest question', mine: false, created_at: '2026-10-08T11:00:00Z' }] });
  render(<MessagesScreen openWith="Alice" onOpenChange={vi.fn()} onReadSomething={vi.fn()} />);
  await screen.findByText('Message from Alice');
  expect(screen.getByRole('textbox')).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: 'Load more recent messages to continue' }));
  await screen.findByText('The newest question');
  expect(conversation).toHaveBeenLastCalledWith('Alice', 'next-page');
  expect(screen.getByText('Message from Alice')).toBeInTheDocument();
  await waitFor(() => expect(screen.getByRole('textbox')).toBeEnabled());
});


it('restores only the same recipient draft after switching away and back', async () => {
  vi.spyOn(api, 'conversation').mockImplementation(async (id) => page(id));
  const props = { onOpenChange: vi.fn(), onReadSomething: vi.fn() };
  const view = render(<MessagesScreen {...props} openWith="Alice" />);
  await screen.findByText('Message from Alice');
  fireEvent.change(screen.getByRole('textbox'), { target: { value: 'For Alice only' } });
  view.rerender(<MessagesScreen {...props} openWith="Bob" />);
  await screen.findByText('Message from Bob');
  expect(screen.getByRole('textbox')).toHaveValue('');
  view.rerender(<MessagesScreen {...props} openWith="Alice" />);
  await screen.findByText('Message from Alice');
  expect(screen.getByRole('textbox')).toHaveValue('For Alice only');
});

it('loads more conversations and keeps the list after a paging failure', async () => {
  const calls = vi.mocked(api.conversations).mockResolvedValueOnce({ items: [{ person: person('Alice'), last_message: 'Hello', last_message_at: '2026-10-08T10:00:00Z', unread: 0 }], next_cursor: 'inbox-2' }).mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce({ items: [{ person: person('Bob'), last_message: 'More', last_message_at: '2026-10-08T10:00:00Z', unread: 1 }], next_cursor: null });
  render(<MessagesScreen openWith={null} onOpenChange={vi.fn()} onReadSomething={vi.fn()} />);
  await screen.findByTestId('conversation-Alice');
  fireEvent.click(screen.getByRole('button', { name: 'More conversations' }));
  await screen.findByText('Could not load your messages.');
  expect(screen.getByTestId('conversation-Alice')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'More conversations' }));
  await screen.findByTestId('conversation-Bob');
  expect(calls).toHaveBeenLastCalledWith('inbox-2');
});

it('refreshes only newer incoming messages without dropping the draft or history', async () => {
  const calls = vi.spyOn(api, 'conversation').mockResolvedValueOnce(page('Alice')).mockResolvedValueOnce({ ...page('Alice'), items: [{ id: 'new', body: 'A new answer', created_at: '2026-10-09T10:00:00Z', mine: false }], latest_cursor: 'latest-new' });
  render(<MessagesScreen openWith="Alice" onOpenChange={vi.fn()} onReadSomething={vi.fn()} />);
  await screen.findByText('Message from Alice');
  fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Keep this question' } });
  fireEvent.click(screen.getByRole('button', { name: 'Refresh messages' }));
  await screen.findByText('A new answer');
  expect(calls).toHaveBeenLastCalledWith('Alice', 'latest-Alice');
  expect(screen.getByText('Message from Alice')).toBeInTheDocument();
  expect(screen.getByRole('textbox')).toHaveValue('Keep this question');
});
