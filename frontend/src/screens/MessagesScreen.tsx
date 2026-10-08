/**
 * Community — private conversations.
 *
 * The list and the open thread share one screen: on a phone the list gives way
 * to the conversation, on a desktop they sit side by side. There is no separate
 * address for a conversation, so nothing here can be linked to by accident.
 *
 * Incoming messages can be fetched explicitly after the last delivered cursor.
 * Each request is bounded; reading never marks hidden pages read.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { api, ApiError } from '@/api/client';
import { Empty, Loading, Notice } from '@/components/primitives';
import { Avatar, Composer, MESSAGE_MAX_CHARS, when } from '@/components/social';
import { useTranslation } from '@/lib/useTranslation';
import type { ConversationView, MessageView, PersonCard } from '@/types';

function Conversation({
  userId, onBack, draft, onDraftChange, onDelivered,
}: { userId: string; onBack: () => void; draft: string; onDraftChange: (text: string) => void; onDelivered: () => void }) {
  const { t } = useTranslation();
  const [person, setPerson] = useState<PersonCard | null>(null);
  const [messages, setMessages] = useState<MessageView[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const latestCursor = useRef<string | null>(null);
  const requestGeneration = useRef(0);
  const mounted = useRef(true);
  const delivered = useRef(onDelivered);
  useEffect(() => { delivered.current = onDelivered; }, [onDelivered]);

  const load = useCallback(async (cursor?: string | null) => {
    const generation = ++requestGeneration.current;
    setLoading(true);
    try {
      const page = await api.conversation(userId, cursor);
      if (!mounted.current || generation !== requestGeneration.current) return;
      setPerson(page.person);
      setMessages((prev) => cursor
        ? [...new Map([...prev, ...page.items].map((message) => [message.id, message])).values()]
        : page.items);
      setNextCursor(page.next_cursor);
      latestCursor.current = page.latest_cursor ?? page.next_cursor ?? latestCursor.current;
      delivered.current();
      setError('');
    } catch (problem) {
      if (!mounted.current || generation !== requestGeneration.current) return;
      setError(problem instanceof ApiError ? problem.message : 'Could not open this conversation.');
    } finally {
      if (mounted.current && generation === requestGeneration.current) setLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    mounted.current = true;
    void load();
    return () => { mounted.current = false; requestGeneration.current += 1; };
  }, [load]);

  return (
    <div className="stack conversation-view">
      <div className="row">
        <button type="button" className="btn btn--sm" onClick={onBack}>
          {t('messages.back')}
        </button>
        <button className="btn btn--sm" type="button" disabled={loading || sending || !person} onClick={() => void load(nextCursor ?? latestCursor.current)}>{t('messages.refresh')}</button>
        {person && (
          <span className="row row--tight">
            <Avatar name={person.display_name} status={person.status} />
            <strong>{person.display_name}</strong>
          </span>
        )}
      </div>

      {error && <Notice kind="risk">{error}</Notice>}
      {loading && <Loading label={t('messages.opening')} />}
      {!loading && !person && error && (
        <button className="btn btn--sm" type="button" onClick={() => void load()}>{t('messages.retry')}</button>
      )}

      {!loading && messages.length === 0 && (
        <Empty title={t('messages.emptyThread')}>
          <p className="small">{t('messages.emptyThreadHint')}</p>
        </Empty>
      )}

      <div className="chat">
        {messages.map((message) => {
          const moment = when(message.created_at);
          return (
            <div
              key={message.id}
              className={`bubble ${message.mine ? 'bubble--mine' : ''}`}
              data-testid={`message-${message.id}`}
            >
              <p className="bubble__body">{message.body}</p>
              <time className="bubble__at" dateTime={message.created_at} title={moment.exact}>
                {moment.label}
              </time>
            </div>
          );
        })}
      </div>

      {nextCursor && (
        <button className="btn btn--sm" type="button" disabled={loading} onClick={() => void load(nextCursor)}>
          {t('messages.moreRecent')}
        </button>
      )}

      <Composer
        placeholder={t('messages.placeholder')}
        submitLabel={t('messages.send')}
        max={MESSAGE_MAX_CHARS}
        busy={sending}
        draft={draft}
        onDraftChange={onDraftChange}
        disabled={loading || !person || nextCursor !== null}
        onSubmit={async (body) => {
          if (!person || loading || nextCursor !== null) return false;
          setSending(true);
          try {
            const sent = await api.sendMessage(userId, body);
            if (!mounted.current) return false;
            setMessages((prev) => [...prev, sent]);
            setError('');
            return true;
          } catch (problem) {
            if (!mounted.current) return false;
            setError(problem instanceof ApiError ? problem.message : 'Could not send that.');
            return false;
          } finally {
            if (mounted.current) setSending(false);
          }
        }}
      />
    </div>
  );
}

export function MessagesScreen({
  openWith, onOpenChange, onReadSomething,
}: {
  /** A conversation asked for from elsewhere — the button on a profile. */
  openWith: string | null;
  onOpenChange: (userId: string | null) => void;
  /** Reading a conversation clears its unread, so the badge has to be told. */
  onReadSomething: () => void;
}) {
  const { t } = useTranslation();
  const [items, setItems] = useState<ConversationView[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [cursor, setCursor] = useState<string | null>(null);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const generation = useRef(0);
  const mounted = useRef(true);

  const load = useCallback(async (from?: string | null) => {
    const request = ++generation.current;
    setLoading(true);
    try {
      const page = await api.conversations(from);
      if (!mounted.current || request !== generation.current) return;
      setItems((prev) => from ? [...new Map([...prev, ...page.items].map((item) => [item.person.user_id, item])).values()] : page.items);
      setCursor(page.next_cursor);
      setError('');
    } catch (problem) {
      if (mounted.current && request === generation.current) setError(problem instanceof ApiError ? problem.message : 'Could not load your messages.');
    } finally {
      if (mounted.current && request === generation.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    mounted.current = true; void load();
    return () => { mounted.current = false; generation.current += 1; };
  }, [load]);

  return (
    <div className={`messages-page${openWith ? ' messages-page--open' : ''}`}>
      <div className="messages-page__list">
      <div className="screen__head">
        <p className="screen__eyebrow">COMMUNITY</p>
        <h1 className="screen__title">Messages</h1>
        <p className="screen__lede">Real conversations with other students.</p>
      </div>

      {error && <Notice kind="risk">{error}</Notice>}
      {loading && <Loading label={t('messages.loading')} />}

      {!loading && items.length === 0 && (
        <Empty title={t('messages.empty')}>
          <p className="small">{t('messages.emptyHint')}</p>
        </Empty>
      )}

      <div className="feed">
        {items.map((conversation) => {
          const moment = when(conversation.last_message_at);
          return (
            <button
              key={conversation.person.user_id}
              type="button"
              className="conversation"
              data-testid={`conversation-${conversation.person.user_id}`}
              onClick={() => onOpenChange(conversation.person.user_id)}
            >
              <Avatar
                name={conversation.person.display_name}
                status={conversation.person.status}
                large
              />
              <span className="conversation__body">
                <span className="conversation__head">
                  <strong>{conversation.person.display_name}</strong>
                  <time dateTime={conversation.last_message_at} title={moment.exact}>
                    {moment.label}
                  </time>
                </span>
                <span className="conversation__last">{conversation.last_message}</span>
              </span>
              {conversation.unread > 0 && (
                <span className="conversation__unread">{conversation.unread}</span>
              )}
            </button>
          );
        })}
      </div>
      {cursor && <button type="button" className="btn btn--sm" disabled={loading} onClick={() => void load(cursor)}>{t('messages.moreConversations')}</button>}
      <button type="button" className="btn btn--sm" disabled={loading} onClick={() => void load()}>{t('messages.refreshList')}</button>
      </div>
      <div className="messages-page__thread">
        {openWith ? <Conversation key={openWith} userId={openWith} draft={drafts[openWith] ?? ''} onDraftChange={(text) => setDrafts((prev) => ({ ...prev, [openWith]: text }))} onDelivered={onReadSomething} onBack={() => { onOpenChange(null); onReadSomething(); void load(); }} /> : (
          <div className="messages-page__welcome"><img src="/brand/unimatch-mark.png" alt="" /><h2>Select a conversation</h2><p>Ask clearly. Plan confidently. Your messages stay between you and the other student unless one of you reports them.</p></div>
        )}
      </div>
    </div>
  );
}
