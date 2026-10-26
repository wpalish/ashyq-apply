/**
 * Posting while the feed is still loading.
 *
 * CI run 39386144462 rendered one post twice on mobile: the first feed page was
 * still in flight when the post was sent, the server read the page after the
 * post was written, and the create response was prepended onto a page that
 * already held it. One POST, two `.post__body` elements with the same text.
 */

import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { api } from '@/api/client';
import { appendPage, firstPage, prependPost } from '@/lib/feed';
import type { Page, PostView } from '@/types';
import { FeedScreen } from './FeedScreen';

function post(id: string, body = `body ${id}`): PostView {
  return {
    id,
    author: { user_id: 'me', display_name: 'Me', status: null },
    body,
    tags: [],
    reply_count: 0,
    created_at: '2026-10-20T07:26:29Z',
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => { resolve = done; });
  return { promise, resolve };
}

const ids = (posts: PostView[]) => posts.map((item) => item.id);

describe('feed merges', () => {
  it('a created post replaces a copy the feed already holds', () => {
    expect(ids(prependPost([post('a'), post('b')], post('a')))).toEqual(['a', 'b']);
    expect(ids(prependPost([post('b')], post('a')))).toEqual(['a', 'b']);
  });

  it('an older page skips posts already shown', () => {
    expect(ids(appendPage([post('a'), post('b')], [post('b'), post('c')]))).toEqual(['a', 'b', 'c']);
  });

  it('a first page keeps a post created during it, once', () => {
    const created = new Set(['new']);
    // The page was read before the post was written: keep the post.
    expect(ids(firstPage([post('old')], [post('new')], created))).toEqual(['new', 'old']);
    // The page was read after: the page's copy is the only one.
    expect(ids(firstPage([post('new'), post('old')], [post('new')], created))).toEqual(['new', 'old']);
    // Anything else on screen is replaced, as before.
    expect(ids(firstPage([post('old')], [post('stale')], created))).toEqual(['old']);
  });
});

describe('FeedScreen', () => {
  afterEach(() => vi.restoreAllMocks());

  async function postWhileLoading(pageHasPost: boolean, createFirst: boolean) {
    const body = 'Кто сдаёт IELTS в #e2e1187435?';
    const created = post('new', body);
    const feed = deferred<Page<PostView>>();
    const create = deferred<PostView>();
    vi.spyOn(api, 'feed').mockReturnValue(feed.promise);
    vi.spyOn(api, 'createPost').mockReturnValue(create.promise);

    render(
      <FeedScreen joined myUserId="me" onOpenPerson={() => {}} onJoin={() => {}} onDiscover={() => {}} />,
    );
    fireEvent.change(screen.getByRole('textbox', { name: /ask something/i }), { target: { value: body } });
    fireEvent.click(screen.getByRole('button', { name: 'Post' }));

    const items = pageHasPost ? [created, post('old')] : [post('old')];
    const steps = [
      () => create.resolve(created),
      () => feed.resolve({ items, next_cursor: null } as Page<PostView>),
    ];
    for (const step of createFirst ? steps : steps.reverse()) {
      await act(async () => { step(); await Promise.resolve(); });
    }
    // The body renders its tags as links, so match the paragraph's whole text
    // the way Playwright's getByText did in CI.
    return Array.from(document.querySelectorAll('.post__body')).filter(
      (element) => element.textContent === body,
    );
  }

  it.each([
    ['the page already holds the post, create resolves last', true, false],
    ['the page already holds the post, create resolves first', true, true],
    ['the page was read before the post, create resolves first', false, true],
    ['the page was read before the post, create resolves last', false, false],
  ])('shows the post exactly once when %s', async (_name, pageHasPost, createFirst) => {
    expect(await postWhileLoading(pageHasPost, createFirst)).toHaveLength(1);
  });
});
