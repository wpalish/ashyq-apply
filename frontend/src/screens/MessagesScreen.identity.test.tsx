import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { MessagesScreen } from '@/screens/MessagesScreen';
import { api } from '@/api/client';
import type { MessagePage, PersonCard } from '@/types';
const person = (id: string): PersonCard => ({ user_id: id, display_name: `Person ${id}`, status: null, target_city: '', target_major: '', universities: [], dm_policy: 'anyone', bio: '', can_message: true });
const msg = (id: string) => ({ id, body: `message ${id}`, created_at: '2026-10-09T00:00:00Z', mine: false });
async function flush() { await act(async () => { for (let i = 0; i < 15; i++)
  await Promise.resolve(); }); }
function deferred<T>() { let resolve!: (v: T) => void; const promise = new Promise<T>(r => { resolve = r; }); return { promise, resolve }; }
const props = { onOpenChange: () => { }, onReadSomething: () => { } };
beforeEach(() => { vi.spyOn(api, 'conversations').mockResolvedValue({ items: [], next_cursor: null }); });
afterEach(() => { cleanup(); vi.restoreAllMocks(); });
it('late conversation A response cannot label recipient B as A', async () => {
  const old = deferred<MessagePage>();
  vi.spyOn(api, 'conversation').mockImplementation(id => id === 'A' ? old.promise : Promise.resolve({ person: person('B'), items: [msg('B')], next_cursor: null }) as never);
  const send = vi.spyOn(api, 'sendMessage').mockResolvedValue(msg('sent') as never);
  const v = render(<MessagesScreen {...props} openWith="A"/>);
  await flush();
  v.rerender(<MessagesScreen {...props} openWith="B"/>);
  await flush();
  expect(screen.getByText('Person B')).toBeInTheDocument();
  old.resolve({ person: person('A'), items: [msg('A')], next_cursor: null });
  await flush();
  expect(screen.getByText('Person B')).toBeInTheDocument();
  expect(screen.queryByText('Person A')).toBeNull();
  expect(screen.queryByText('message A')).toBeNull();
  fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Intended for the visible Person B' } });
  fireEvent.submit(screen.getByRole('textbox').closest('form')!);
  await flush();
  expect(send).toHaveBeenCalledWith('B', 'Intended for the visible Person B');
});
it('switching recipients resets the composer instead of sending A draft to B', async () => {
  vi.spyOn(api, 'conversation').mockImplementation(async (id) => ({ person: person(id), items: [msg(id)], next_cursor: null }) as never);
  const v = render(<MessagesScreen {...props} openWith="A"/>);
  await flush();
  fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Draft for Person A only' } });
  v.rerender(<MessagesScreen {...props} openWith="B"/>);
  await flush();
  expect(screen.getByText('Person B')).toBeInTheDocument();
  expect(screen.getByRole('textbox')).toHaveValue('');
  expect(screen.queryByText('message A')).toBeNull();
});
