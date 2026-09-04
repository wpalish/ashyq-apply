/**
 * Community — the feed.
 *
 * A chronological column, newest first. Threads open in place rather than on
 * their own page, which is the same drawer language the shortlist already uses:
 * you keep your position in the list while you read an answer.
 */

import { useCallback, useEffect, useState } from 'react';
import { api, ApiError } from '@/api/client';
import { Empty, Loading, Notice, Panel } from '@/components/primitives';
import { Byline, Composer, Post } from '@/components/social';
import type { FeedFilters, Page, PostView, ReplyView } from '@/types';

function Thread({ postId, onOpenPerson }: { postId: string; onOpenPerson: (id: string) => void }) {
  const [page, setPage] = useState<Page<ReplyView> | null>(null);
  const [replies, setReplies] = useState<ReplyView[]>([]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const load = useCallback(async (cursor?: string | null) => {
    try {
      const next = await api.thread(postId, cursor);
      setPage(next);
      setReplies((prev) => (cursor ? [...prev, ...next.items] : next.items));
    } catch (problem) {
      setError(problem instanceof ApiError ? problem.message : 'Could not load this thread.');
    }
  }, [postId]);

  useEffect(() => { void load(); }, [load]);

  return (
    <div className="thread">
      {error && <Notice kind="risk">{error}</Notice>}
      {page === null && !error && <Loading label="Opening the thread" />}
      {replies.map((reply) => (
        <div className="reply" key={reply.id} data-testid={`reply-${reply.id}`}>
          <Byline author={reply.author} at={reply.created_at} onOpenPerson={onOpenPerson} />
          <p className="post__body">{reply.body}</p>
        </div>
      ))}
      {page !== null && replies.length === 0 && (
        <p className="small muted">No answers yet. Be the first.</p>
      )}
      {page?.next_cursor && (
        <button className="btn btn--sm btn--ghost" type="button" onClick={() => load(page.next_cursor)}>
          Show earlier answers
        </button>
      )}
      <Composer
        placeholder="Answer this"
        submitLabel="Reply"
        busy={busy}
        onSubmit={async (body) => {
          setBusy(true);
          try {
            const created = await api.createReply(postId, body);
            setReplies((prev) => [...prev, created]);
            setError('');
          } catch (problem) {
            setError(problem instanceof ApiError ? problem.message : 'Could not post that reply.');
          } finally {
            setBusy(false);
          }
        }}
      />
    </div>
  );
}

export function FeedScreen({
  joined, onOpenPerson, onJoin,
}: { joined: boolean; onOpenPerson: (id: string) => void; onJoin: () => void }) {
  const [filters, setFilters] = useState<FeedFilters>({});
  const [posts, setPosts] = useState<PostView[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [openThread, setOpenThread] = useState<string | null>(null);
  const [posting, setPosting] = useState(false);

  const load = useCallback(async (active: FeedFilters, from?: string | null) => {
    setLoading(true);
    try {
      const page = await api.feed(active, from);
      setPosts((prev) => (from ? [...prev, ...page.items] : page.items));
      setCursor(page.next_cursor);
      setError('');
    } catch (problem) {
      setError(problem instanceof ApiError ? problem.message : 'Could not load the feed.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(filters); }, [load, filters]);

  const filtered = Object.values(filters).some(Boolean);

  return (
    <div className="stack community-column">
      <div className="screen__head">
        <h1 className="screen__title">Community</h1>
        <p className="screen__lede">
          Applicants aiming at the same cities and universities. What people write here is
          their own experience — it is not verified against a university page.
        </p>
      </div>

      {!joined && (
        <Notice kind="info">
          <div style={{ flex: 1 }}>
            You can read the feed now. Create a community profile to post, reply and be
            findable by people applying where you are.
          </div>
          <button className="btn btn--sm btn--primary" type="button" onClick={onJoin}>
            Create profile
          </button>
        </Notice>
      )}

      {joined && (
        <Panel title="Write a post" hint="Tag a university or a city with # so the right people find it.">
          <Composer
            placeholder="Ask something, or say where you are applying"
            submitLabel="Post"
            busy={posting}
            onSubmit={async (body) => {
              setPosting(true);
              try {
                const created = await api.createPost(body);
                setPosts((prev) => [created, ...prev]);
                setError('');
              } catch (problem) {
                setError(problem instanceof ApiError ? problem.message : 'Could not post that.');
              } finally {
                setPosting(false);
              }
            }}
          />
        </Panel>
      )}

      <div className="filters">
        <div className="field">
          <label className="field__label xs" htmlFor="feed-tag">Tag</label>
          <input
            id="feed-tag"
            placeholder="KBTU"
            defaultValue={filters.tag ?? ''}
            onBlur={(event) => setFilters((f) => ({ ...f, tag: event.target.value.trim() }))}
          />
        </div>
        <div className="field">
          <label className="field__label xs" htmlFor="feed-city">Applying to city</label>
          <input
            id="feed-city"
            placeholder="Astana"
            defaultValue={filters.city ?? ''}
            onBlur={(event) => setFilters((f) => ({ ...f, city: event.target.value.trim() }))}
          />
        </div>
        <div className="field">
          <label className="field__label xs" htmlFor="feed-status">Author status</label>
          <select
            id="feed-status"
            value={filters.status ?? ''}
            onChange={(event) => setFilters((f) => ({ ...f, status: event.target.value }))}
          >
            <option value="">Anyone</option>
            <option value="accepted">Accepted</option>
            <option value="waitlist">On a waitlist</option>
          </select>
        </div>
        {filtered && (
          <button className="btn btn--sm btn--ghost" type="button" onClick={() => setFilters({})}>
            Clear filters
          </button>
        )}
      </div>

      {error && <Notice kind="risk">{error}</Notice>}

      <div className="feed">
        {posts.map((post) => (
          <Post
            key={post.id}
            post={post}
            onOpenPerson={onOpenPerson}
            footer={
              <div className="post__foot">
                <button
                  type="button"
                  className="linkish"
                  aria-expanded={openThread === post.id}
                  onClick={() => setOpenThread((open) => (open === post.id ? null : post.id))}
                >
                  {openThread === post.id
                    ? 'Hide answers'
                    : post.reply_count === 0
                      ? 'Answer'
                      : `${post.reply_count} answer${post.reply_count === 1 ? '' : 's'}`}
                </button>
              </div>
            }
          >
            {openThread === post.id && <Thread postId={post.id} onOpenPerson={onOpenPerson} />}
          </Post>
        ))}
      </div>

      {loading && <Loading label="Loading posts" />}
      {!loading && posts.length === 0 && (
        <Empty title={filtered ? 'Nothing matches those filters' : 'No posts yet'}>
          <p className="small">
            {filtered
              ? 'Widen the filters, or clear them to see everything.'
              : 'The first post here sets the tone. Ask the question you could not find an answer to.'}
          </p>
        </Empty>
      )}
      {cursor && !loading && (
        <button className="btn" type="button" onClick={() => load(filters, cursor)}>
          Load older posts
        </button>
      )}
    </div>
  );
}
