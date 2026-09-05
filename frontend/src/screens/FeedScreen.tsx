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
import { Byline, Composer, Post, Retract } from '@/components/social';
import { ReportButton } from '@/components/moderation';
import { useTranslation } from '@/lib/useTranslation';
import type { FeedFilters, Page, PostView, ReplyView } from '@/types';

function Thread({
  postId, myUserId, onOpenPerson, onCountChange,
}: {
  postId: string;
  myUserId: string | null;
  onOpenPerson: (id: string) => void;
  /** The count lives on the post in the feed's list, not in this component.
   *  Without this the footer kept saying "Answer" under a thread you had just
   *  answered, and "2 answers" over a thread showing one. */
  onCountChange: (delta: number) => void;
}) {
  const { t } = useTranslation();
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
      {page === null && !error && <Loading label={t('community.openingThread')} />}
      {replies.map((reply) => (
        <div className="reply" key={reply.id} data-testid={`reply-${reply.id}`}>
          <Byline author={reply.author} at={reply.created_at} onOpenPerson={onOpenPerson} />
          <p className="post__body">{reply.body}</p>
          <div className="post__foot">
            {reply.author.user_id === myUserId ? (
              <Retract
                question={t('community.deleteAnswerQ')}
                onConfirm={async () => {
                  await api.deleteReply(postId, reply.id);
                  setReplies((prev) => prev.filter((item) => item.id !== reply.id));
                  onCountChange(-1);
                }}
              />
            ) : (
              <ReportButton subjectType="reply" subjectId={reply.id} />
            )}
          </div>
        </div>
      ))}
      {page !== null && replies.length === 0 && (
        <p className="small muted">{t('community.noAnswers')}</p>
      )}
      {page?.next_cursor && (
        <button className="btn btn--sm btn--ghost" type="button" onClick={() => load(page.next_cursor)}>
          {t('community.earlierAnswers')}
        </button>
      )}
      <Composer
        placeholder={t('community.answerPlaceholder')}
        submitLabel={t('community.reply')}
        busy={busy}
        onSubmit={async (body) => {
          setBusy(true);
          try {
            const created = await api.createReply(postId, body);
            setReplies((prev) => [...prev, created]);
            onCountChange(1);
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
  joined, myUserId, onOpenPerson, onJoin,
}: {
  joined: boolean;
  myUserId: string | null;
  onOpenPerson: (id: string) => void;
  onJoin: () => void;
}) {
  const { t } = useTranslation();
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

  /**
   * "Answer" with the count beside it, rather than "2 answers".
   *
   * Russian has three plural forms and Kazakh has none, and this dictionary has
   * no plural rules. A parenthesised count is right in all three languages and
   * needs no rule to be invented for two of them.
   */
  const answersLabel = (count: number) =>
    count === 0 ? t('community.answer') : `${t('community.answer')} (${count})`;

  return (
    <div className="stack community-column">
      <div className="screen__head">
        <h1 className="screen__title">{t('community.title')}</h1>
        <p className="screen__lede">{t('community.lede')}</p>
      </div>

      {!joined && (
        <Notice kind="info">
          <div style={{ flex: 1 }}>{t('community.joinPrompt')}</div>
          <button className="btn btn--sm btn--primary" type="button" onClick={onJoin}>
            {t('community.createProfile')}
          </button>
        </Notice>
      )}

      {joined && (
        <Panel title={t('community.write')} hint={t('community.writeHint')}>
          <Composer
            placeholder={t('community.placeholder')}
            submitLabel={t('community.post')}
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
          <label className="field__label xs" htmlFor="feed-tag">{t('community.filterTag')}</label>
          <input
            id="feed-tag"
            placeholder="KBTU"
            defaultValue={filters.tag ?? ''}
            onBlur={(event) => setFilters((f) => ({ ...f, tag: event.target.value.trim() }))}
          />
        </div>
        <div className="field">
          <label className="field__label xs" htmlFor="feed-city">{t('community.filterCity')}</label>
          <input
            id="feed-city"
            placeholder="Astana"
            defaultValue={filters.city ?? ''}
            onBlur={(event) => setFilters((f) => ({ ...f, city: event.target.value.trim() }))}
          />
        </div>
        <div className="field">
          <label className="field__label xs" htmlFor="feed-status">
            {t('community.filterAuthorStatus')}
          </label>
          <select
            id="feed-status"
            value={filters.status ?? ''}
            onChange={(event) => setFilters((f) => ({ ...f, status: event.target.value }))}
          >
            <option value="">{t('community.anyone')}</option>
            <option value="accepted">{t('person.statusAccepted')}</option>
            <option value="waitlist">{t('person.statusWaitlist')}</option>
          </select>
        </div>
        {filtered && (
          <button className="btn btn--sm btn--ghost" type="button" onClick={() => setFilters({})}>
            {t('community.clearFilters')}
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
            reportable={post.author.user_id !== myUserId}
            onDelete={
              post.author.user_id === myUserId
                ? async () => {
                    await api.deletePost(post.id);
                    setPosts((prev) => prev.filter((item) => item.id !== post.id));
                  }
                : undefined
            }
            footer={
              <button
                type="button"
                className="linkish"
                aria-expanded={openThread === post.id}
                onClick={() => setOpenThread((open) => (open === post.id ? null : post.id))}
              >
                {openThread === post.id
                  ? t('community.hideAnswers')
                  : answersLabel(post.reply_count)}
              </button>
            }
          >
            {openThread === post.id && (
              <Thread
                postId={post.id}
                myUserId={myUserId}
                onOpenPerson={onOpenPerson}
                onCountChange={(delta) =>
                  setPosts((prev) =>
                    prev.map((item) =>
                      item.id === post.id
                        ? { ...item, reply_count: Math.max(0, item.reply_count + delta) }
                        : item,
                    ),
                  )
                }
              />
            )}
          </Post>
        ))}
      </div>

      {loading && <Loading label={t('community.loadingPosts')} />}
      {!loading && posts.length === 0 && (
        <Empty title={t(filtered ? 'community.noMatch' : 'community.noPosts')}>
          <p className="small">
            {t(filtered ? 'community.noMatchHint' : 'community.noPostsHint')}
          </p>
        </Empty>
      )}
      {cursor && !loading && (
        <button className="btn" type="button" onClick={() => load(filters, cursor)}>
          {t('community.olderPosts')}
        </button>
      )}
    </div>
  );
}
