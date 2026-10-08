import { act, fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { api } from '@/api/client';
import { setLocale } from '@/lib/i18n';
import type { Page, PostView } from '@/types';
import { FeedScreen } from './FeedScreen';
const props = { joined: true, myUserId: 'me', onOpenPerson: vi.fn(), onJoin: vi.fn(), onDiscover: vi.fn() };
const post = (id: string): PostView => ({ id, author: { user_id: 'me', display_name: 'Me', status: null }, body: id, tags: [], reply_count: 0, created_at: '2026-10-08T10:00:00Z' });
function deferred<T>() { let resolve!: (v: T) => void; const promise = new Promise<T>((r) => { resolve = r; }); return { promise, resolve }; }
beforeEach(() => { vi.restoreAllMocks(); setLocale('en'); });
it('ignores late rows from an older filter and clears visible filter fields', async () => {
  const old = deferred<Page<PostView>>();
  vi.spyOn(api, 'feed').mockResolvedValueOnce({ items: [], next_cursor: null }).mockReturnValueOnce(old.promise).mockResolvedValueOnce({ items: [post('Current city B')], next_cursor: null }).mockResolvedValue({ items: [], next_cursor: null });
  render(<FeedScreen {...props} />);
  await act(async () => {});
  const city = screen.getByLabelText('Applying to city');
  fireEvent.change(city, { target: { value: 'A' } }); fireEvent.blur(city);
  fireEvent.change(city, { target: { value: 'B' } }); fireEvent.blur(city);
  await screen.findByText('Current city B');
  await act(async () => { old.resolve({ items: [post('Obsolete city A')], next_cursor: null }); });
  expect(screen.queryByText('Obsolete city A')).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Clear filters' }));
  expect(city).toHaveValue('');
});
it('keeps the post draft when the server refuses it', async () => {
  vi.spyOn(api, 'feed').mockResolvedValue({ items: [], next_cursor: null });
  vi.spyOn(api, 'createPost').mockRejectedValue(new Error('offline'));
  render(<FeedScreen {...props} />); const box = screen.getByRole('textbox', { name: 'Ask something, or say where you are applying' });
  fireEvent.change(box, { target: { value: 'Keep my question' } });
  await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Post' })); });
  expect(box).toHaveValue('Keep my question');
});
