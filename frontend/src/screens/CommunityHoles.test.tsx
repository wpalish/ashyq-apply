import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { api, ApiError } from '@/api/client';
import { Avatar, Retract } from '@/components/social';
import { BlockButton } from '@/components/moderation';
import { setLocale, t } from '@/lib/i18n';
import { MessagesScreen } from './MessagesScreen';
import { PersonScreen } from './PersonScreen';
import { DiscoverScreen } from './DiscoverScreen';
import { FeedScreen } from './FeedScreen';
import type { PersonCard } from '@/types';

const friend: PersonCard = { user_id: 'synthetic-friend', display_name: 'Synthetic Friend', status: null, target_city: '', target_major: '', universities: [], dm_policy: 'anyone', bio: '', can_message: true };
const messagesProps = { openWith: null, onOpenChange: vi.fn(), onReadSomething: vi.fn() };
const feedProps = { joined: true, myUserId: 'synthetic-me', onOpenPerson: vi.fn(), onJoin: vi.fn(), onDiscover: vi.fn() };
const conversation = { person: friend, last_message: 'Synthetic message', last_message_at: '2026-10-23T00:00:00Z', unread: 0 };
beforeEach(() => { setLocale('en'); });
afterEach(() => { vi.restoreAllMocks(); setLocale('en'); });

it('tries a different person picture after the previous picture was absent', () => {
  const view = render(<Avatar name="First Person" userId="first" status={null}/>);
  const first = view.container.querySelector('img')!;
  fireEvent.error(first);
  expect(view.container.querySelector('img')).toBeNull();
  view.rerender(<Avatar name="Second Person" userId="second" status={null}/>);
  expect(view.container.querySelector('img')).toHaveAttribute('src', '/api/social/avatars/second');
  expect(view.container.querySelector('img')).not.toBe(first);
});

it('explains an empty conversation search and restores the loaded list on clear', async () => {
  setLocale('ru');
  vi.spyOn(api, 'conversations').mockResolvedValue({ items: [conversation], next_cursor: null });
  const view = render(<MessagesScreen {...messagesProps}/>);
  expect(await screen.findByText(friend.display_name)).toBeVisible();
  expect(view.container.querySelector('.conversation img')).toHaveAttribute('src', `/api/social/avatars/${friend.user_id}`);
  fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'No matching name' } });
  expect(screen.getByText('Диалоги не найдены')).toBeVisible();
  fireEvent.click(screen.getByRole('button', { name: 'Сбросить поиск' }));
  expect(screen.getByText(friend.display_name)).toBeVisible();
});

it('does not call a failed conversation list empty and lets the reader retry', async () => {
  const calls = vi.spyOn(api, 'conversations').mockRejectedValueOnce(new ApiError(503, 'Synthetic unavailable')).mockResolvedValueOnce({ items: [conversation], next_cursor: null });
  render(<MessagesScreen {...messagesProps}/>);
  expect(await screen.findByRole('alert')).toHaveTextContent('Synthetic unavailable');
  expect(screen.queryByText(t('messages.empty'))).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: 'Retry loading' }));
  expect(await screen.findByText(friend.display_name)).toBeVisible();
  expect(calls).toHaveBeenCalledTimes(2);
});

it('loads a public profile again after a temporary failure and requests its avatar', async () => {
  vi.spyOn(api, 'person').mockRejectedValueOnce(new ApiError(503, 'Synthetic profile unavailable')).mockResolvedValueOnce(friend);
  vi.spyOn(api, 'feed').mockResolvedValue({ items: [], next_cursor: null });
  vi.spyOn(api, 'blockedPeople').mockResolvedValue({ items: [] });
  const view = render(<PersonScreen userId={friend.user_id} myUserId="synthetic-me" onOpenPerson={vi.fn()} onOpenMessages={vi.fn()} onProfileSaved={vi.fn()} onLeft={vi.fn()}/>);
  expect(await screen.findByRole('heading', { name: 'Could not open the profile' })).toBeVisible();
  fireEvent.click(screen.getByRole('button', { name: 'Retry loading' }));
  expect(await screen.findByRole('heading', { name: friend.display_name })).toBeVisible();
  expect(view.container.querySelector('.profile-head img')).toHaveAttribute('src', `/api/social/avatars/${friend.user_id}`);
});

it('refreshes the public preview only after an avatar update succeeds and explains a failed removal', async () => {
  setLocale('ru');
  vi.spyOn(api, 'socialMe').mockResolvedValue({ joined: true, profile: friend });
  vi.spyOn(api, 'feed').mockResolvedValue({ items: [], next_cursor: null });
  const upload = vi.spyOn(api, 'uploadAvatar').mockResolvedValue(undefined);
  vi.spyOn(api, 'deleteAvatar').mockRejectedValue(new ApiError(503, 'Synthetic avatar unavailable'));
  const saved = vi.fn();
  const view = render(<PersonScreen userId={null} myUserId={friend.user_id} onOpenPerson={vi.fn()} onOpenMessages={vi.fn()} onProfileSaved={saved} onLeft={vi.fn()}/>);
  await screen.findByText('Фото, город и этап поступления');
  const original = view.container.querySelector('.public-profile-preview img');
  expect(original).toHaveAttribute('src', `/api/social/avatars/${friend.user_id}`);
  fireEvent.click(screen.getByText('Фото, город и этап поступления'));
  const file = new File(['synthetic image only'], 'synthetic.png', { type: 'image/png' });
  fireEvent.change(view.container.querySelector('input[type="file"]')!, { target: { files: [file] } });
  await waitFor(() => expect(view.container.querySelector('.public-profile-preview img')).not.toBe(original));
  expect(upload).toHaveBeenCalledWith(file);
  const updated = view.container.querySelector('.public-profile-preview img');
  fireEvent.click(screen.getByRole('button', { name: t('person.avatarRemove') }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Не удалось удалить фото');
  expect(view.container.querySelector('.public-profile-preview img')).toBe(updated);
  expect(saved).not.toHaveBeenCalled();
});

it('distinguishes unavailable people from no people and applies filters with Enter', async () => {
  const calls = vi.spyOn(api, 'people').mockRejectedValueOnce(new ApiError(503, 'Synthetic discovery unavailable')).mockResolvedValue({ items: [], next_cursor: null });
  render(<DiscoverScreen onOpenPerson={vi.fn()}/>);
  expect(await screen.findByRole('alert')).toHaveTextContent('Synthetic discovery unavailable');
  expect(screen.queryByText(t('discover.empty'))).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: 'Retry loading' }));
  await screen.findByText(t('discover.empty'));
  const city = screen.getByPlaceholderText('Astana');
  fireEvent.change(city, { target: { value: '  Almaty  ' } });
  fireEvent.keyDown(city, { key: 'Enter' });
  await waitFor(() => expect(calls).toHaveBeenLastCalledWith(expect.objectContaining({ city: 'Almaty' }), undefined));
});

it('keeps the feed recoverable after a failed read instead of claiming no posts', async () => {
  const calls = vi.spyOn(api, 'feed').mockRejectedValueOnce(new ApiError(503, 'Synthetic feed unavailable')).mockResolvedValueOnce({ items: [], next_cursor: null });
  render(<FeedScreen {...feedProps}/>);
  expect(await screen.findByRole('alert')).toHaveTextContent('Synthetic feed unavailable');
  expect(screen.queryByText(t('community.noPosts'))).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: 'Retry loading' }));
  expect(await screen.findByText(t('community.noPosts'))).toBeVisible();
  expect(calls).toHaveBeenCalledTimes(2);
});

it('keeps a failed deletion visible and requires another explicit confirmation to retry', async () => {
  const remove = vi.fn().mockRejectedValueOnce(new Error('Synthetic failure')).mockResolvedValueOnce(undefined);
  render(<Retract question="Remove synthetic post?" onConfirm={remove}/>);
  fireEvent.click(screen.getByRole('button', { name: t('community.delete') }));
  fireEvent.click(screen.getByRole('button', { name: t('community.deleteConfirm') }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Could not delete');
  expect(remove).toHaveBeenCalledTimes(1);
  fireEvent.click(screen.getByRole('button', { name: t('community.deleteConfirm') }));
  await waitFor(() => expect(screen.queryByRole('alert')).toBeNull());
  expect(remove).toHaveBeenCalledTimes(2);
});

it('shows a failed unblock without claiming a changed relationship', async () => {
  const change = vi.fn();
  const calls = vi.spyOn(api, 'unblockPerson').mockRejectedValueOnce(new ApiError(503, 'Synthetic block unavailable')).mockResolvedValueOnce(undefined);
  render(<BlockButton userId={friend.user_id} blocked onChanged={change}/>);
  fireEvent.click(screen.getByRole('button', { name: t('block.unblock') }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Synthetic block unavailable');
  expect(change).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: t('block.unblock') }));
  await waitFor(() => expect(change).toHaveBeenCalledTimes(1));
  expect(calls).toHaveBeenCalledTimes(2);
});
