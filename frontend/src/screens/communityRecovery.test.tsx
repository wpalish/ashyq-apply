import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { MessagesScreen } from '@/screens/MessagesScreen';
import { DiscoverScreen } from '@/screens/DiscoverScreen';
import { FeedScreen } from '@/screens/FeedScreen';
import { api, ApiError } from '@/api/client';
import { t } from '@/lib/i18n';
import type { MessagePage, PersonCard, PostView } from '@/types';
const person = (id: string): PersonCard => ({ user_id: id, display_name: `Person ${id}`, status: null, target_city: '', target_major: '', universities: [], dm_policy: 'anyone', bio: '', can_message: true });
const msg = (id: string) => ({ id, body: `message ${id}`, created_at: '2026-10-09T00:00:00Z', mine: false });
const post = (id: string): PostView => ({ id, author: { user_id: 'me', display_name: 'Me', status: null }, body: `post ${id}`, tags: [], reply_count: 0, created_at: '2026-10-09T00:00:00Z' });
const conversation = (id: string) => ({ person: person(id), last_message: 'Latest', last_message_at: '2026-10-09T00:00:00Z', unread: 0 });
const messageProps = { onOpenChange: () => {}, onReadSomething: () => {} };
const feedProps = { joined: true, myUserId: 'me', onOpenPerson: () => {}, onJoin: () => {}, onDiscover: () => {} };
async function flush() { await act(async () => { for (let i = 0; i < 15; i++) await Promise.resolve(); }); }
function deferred<T>() { let resolve!: (v: T) => void; const promise = new Promise<T>(r => { resolve = r; }); return { promise, resolve }; }
beforeEach(() => {
  vi.spyOn(api, 'conversations').mockResolvedValue({ items: [], next_cursor: null });
  vi.spyOn(api, 'conversation').mockResolvedValue({ person: person('A'), items: [], next_cursor: null });
  vi.spyOn(api, 'people').mockResolvedValue({ items: [], next_cursor: null });
  vi.spyOn(api, 'feed').mockResolvedValue({ items: [], next_cursor: null });
  vi.spyOn(api, 'thread').mockResolvedValue({ items: [], next_cursor: null });
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

it('loads all 25 chronological messages without duplicating a page boundary', async () => {
  const calls = vi.mocked(api.conversation).mockImplementation(async (_, cursor) => ({
    person: person('A'), items: cursor ? Array.from({ length: 6 }, (_, i) => msg(String(i + 19))) : Array.from({ length: 20 }, (_, i) => msg(String(i))), next_cursor: cursor ? null : 'next20',
  }));
  render(<MessagesScreen {...messageProps} openWith="A" />); await flush();
  expect(screen.getAllByTestId(/^message-/)).toHaveLength(20);
  fireEvent.click(screen.getByRole('button', { name: 'Load more messages' })); await flush();
  expect(calls).toHaveBeenLastCalledWith('A', 'next20');
  expect(screen.getAllByTestId(/^message-/)).toHaveLength(25);
  expect(screen.getByText('message 24')).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Load more messages' })).toBeNull();
});

it('makes the 21st conversation reachable', async () => {
  const calls = vi.mocked(api.conversations).mockImplementation(async cursor => ({ items: cursor ? [conversation('20')] : Array.from({ length: 20 }, (_, i) => conversation(String(i))), next_cursor: cursor ? null : 'conversations20' }));
  render(<MessagesScreen {...messageProps} openWith={null} />); await flush();
  fireEvent.click(screen.getByRole('button', { name: 'Load more conversations' })); await flush();
  expect(calls).toHaveBeenLastCalledWith('conversations20');
  expect(screen.getAllByTestId(/^conversation-/)).toHaveLength(21);
  expect(screen.getByText('Person 20')).toBeInTheDocument();
});

it('ignores a late old-recipient message page after switching to B', async () => {
  const oldPage = deferred<MessagePage>();
  vi.mocked(api.conversation).mockImplementation((id, cursor) => cursor ? oldPage.promise : Promise.resolve({ person: person(id), items: [msg(id)], next_cursor: id === 'A' ? 'page2' : null }));
  const view = render(<MessagesScreen {...messageProps} openWith="A" />); await flush();
  fireEvent.click(screen.getByRole('button', { name: 'Load more messages' })); await flush();
  view.rerender(<MessagesScreen {...messageProps} openWith="B" />); await flush();
  oldPage.resolve({ person: person('A'), items: [msg('A late page')], next_cursor: null }); await flush();
  expect(screen.getByText('Person B')).toBeInTheDocument();
  expect(screen.queryByText('message A late page')).toBeNull();
});

it('preserves a failed DM draft and clears it once after a successful retry', async () => {
  const send = vi.spyOn(api, 'sendMessage').mockRejectedValueOnce(new ApiError(500, 'Synthetic send failure')).mockResolvedValueOnce(msg('sent'));
  render(<MessagesScreen {...messageProps} openWith="A" />); await flush();
  const box = screen.getByPlaceholderText(t('messages.placeholder'));
  fireEvent.change(box, { target: { value: 'Exact retry text' } }); fireEvent.submit(box.closest('form')!); await flush();
  expect(box).toHaveValue('Exact retry text');
  fireEvent.submit(box.closest('form')!); await flush();
  expect(send).toHaveBeenCalledTimes(2); expect(send.mock.calls.map(args => args[1])).toEqual(['Exact retry text', 'Exact retry text']);
  expect(box).toHaveValue(''); expect(screen.getAllByTestId('message-sent')).toHaveLength(1);
});

it('preserves a failed public-post draft and clears it after a successful retry', async () => {
  const create = vi.spyOn(api, 'createPost').mockRejectedValueOnce(new ApiError(500, 'Synthetic post failure')).mockResolvedValueOnce(post('created'));
  render(<FeedScreen {...feedProps} />); await flush();
  const box = screen.getByPlaceholderText(t('community.placeholder'));
  fireEvent.change(box, { target: { value: 'Exact post retry text' } }); fireEvent.submit(box.closest('form')!); await flush();
  expect(box).toHaveValue('Exact post retry text'); fireEvent.submit(box.closest('form')!); await flush();
  expect(create).toHaveBeenCalledTimes(2); expect(create.mock.calls.map(args => args[0])).toEqual(['Exact post retry text', 'Exact post retry text']); expect(box).toHaveValue('');
});

it('preserves a failed public-reply draft and clears it after a successful retry', async () => {
  vi.mocked(api.feed).mockResolvedValue({ items: [post('root')], next_cursor: null });
  const create = vi.spyOn(api, 'createReply').mockRejectedValueOnce(new ApiError(500, 'Synthetic reply failure')).mockResolvedValueOnce({ id: 'reply-created', post_id: 'root', author: { user_id: 'me', display_name: 'Me', status: null }, body: 'Exact reply retry text', created_at: '2026-10-09T00:00:00Z' });
  render(<FeedScreen {...feedProps} />); await flush(); fireEvent.click(screen.getByRole('button', { name: t('community.answer') })); await flush();
  const box = screen.getByPlaceholderText(t('community.answerPlaceholder'));
  fireEvent.change(box, { target: { value: 'Exact reply retry text' } }); fireEvent.submit(box.closest('form')!); await flush();
  expect(box).toHaveValue('Exact reply retry text'); fireEvent.submit(box.closest('form')!); await flush();
  expect(create).toHaveBeenCalledTimes(2); expect(create.mock.calls.map(args => args[1])).toEqual(['Exact reply retry text', 'Exact reply retry text']); expect(box).toHaveValue('');
});

it('clears the discovery input and prevents blur from restoring its old city', async () => {
  const calls = vi.mocked(api.people); render(<DiscoverScreen onOpenPerson={() => {}} />); await flush();
  const city = screen.getByPlaceholderText('Astana'); fireEvent.change(city, { target: { value: 'Almaty' } }); fireEvent.blur(city); await flush();
  fireEvent.click(screen.getByRole('button', { name: t('community.clearFilters') })); await flush(); expect(city).toHaveValue('');
  fireEvent.blur(city); await flush(); expect(calls.mock.calls.at(-1)?.[0]?.city ?? '').toBe('');
});

it('clears feed tag and city inputs and prevents blur from restoring them', async () => {
  const calls = vi.mocked(api.feed); render(<FeedScreen {...feedProps} />); await flush();
  const city = screen.getByPlaceholderText('Astana'); const tag = screen.getByPlaceholderText('KBTU');
  fireEvent.change(city, { target: { value: 'Almaty' } }); fireEvent.blur(city); fireEvent.change(tag, { target: { value: 'OldTag' } }); fireEvent.blur(tag); await flush();
  fireEvent.click(screen.getByRole('button', { name: t('community.clearFilters') })); await flush(); expect(city).toHaveValue(''); expect(tag).toHaveValue('');
  fireEvent.blur(city); fireEvent.blur(tag); await flush(); const filters = calls.mock.calls.at(-1)?.[0]; expect(filters?.city ?? '').toBe(''); expect(filters?.tag ?? '').toBe('');
});

it('ignores a late filtered discovery response after Clear filters', async () => {
  const old = deferred<{ items: PersonCard[]; next_cursor: null }>();
  vi.mocked(api.people).mockImplementation(filters => filters?.city === 'Almaty' ? old.promise : Promise.resolve({ items: [], next_cursor: null }));
  render(<DiscoverScreen onOpenPerson={() => {}} />); await flush(); const city = screen.getByPlaceholderText('Astana'); fireEvent.change(city, { target: { value: 'Almaty' } }); fireEvent.blur(city); await flush();
  fireEvent.click(screen.getByRole('button', { name: t('community.clearFilters') })); await flush(); old.resolve({ items: [person('Old filtered person')], next_cursor: null }); await flush();
  expect(screen.queryByText('Person Old filtered person')).toBeNull();
});
