/**
 * Merging feed pages with posts created on this screen.
 *
 * The feed is loaded and written concurrently: a person can post while the
 * first page is still in flight. The server may then return the new post in
 * that page *and* the create call returns it too, so every merge here is keyed
 * by post id — a post appears once however the two responses interleave.
 */

import type { PostView } from '@/types';

function withoutIds(posts: PostView[], ids: ReadonlySet<string>): PostView[] {
  return posts.filter((post) => !ids.has(post.id));
}

/** A post just created here goes on top, replacing any copy a load already put in. */
export function prependPost(posts: PostView[], created: PostView): PostView[] {
  return [created, ...withoutIds(posts, new Set([created.id]))];
}

/** "Older posts": the next page goes underneath, skipping anything already shown. */
export function appendPage(posts: PostView[], page: PostView[]): PostView[] {
  return [...posts, ...withoutIds(page, new Set(posts.map((post) => post.id)))];
}

/**
 * A fresh first page replaces the list, except for posts created here while it
 * was in flight (`createdIds`): the server may have read before they were
 * written, and dropping them would make a just-published post vanish.
 */
export function firstPage(
  page: PostView[],
  previous: PostView[],
  createdIds: ReadonlySet<string>,
): PostView[] {
  const onPage = new Set(page.map((post) => post.id));
  const kept = previous.filter((post) => createdIds.has(post.id) && !onPage.has(post.id));
  return [...kept, ...page];
}
