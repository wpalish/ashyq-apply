/**
 * Community — private conversations.
 *
 * The list and the open thread share one screen: on a phone the list gives way
 * to the conversation, on a desktop they sit side by side. There is no separate
 * address for a conversation, so nothing here can be linked to by accident.
 *
 * It does not stream. Opening a conversation fetches it, and sending appends
 * what the server returned; a message that arrives while you are looking shows
 * up the next time you open the thread. That is a real limitation and it is
 * better named than papered over with a poll that drains a phone battery.
 */

import { useCallback, useEffect, useState } from 'react';
import { api, ApiError } from '@/api/client';
import { Empty, Loading, Notice } from '@/components/primitives';
import { Avatar, Composer, MESSAGE_MAX_CHARS, when } from '@/components/social';
import { useTranslation } from '@/lib/useTranslation';
import type { ConversationView, MessageView, PersonCard } from '@/types';

function Conversation({
  userId, onBack,
}: { userId: string; onBack: () => void }) {
  const { t } = useTranslation();
  const [person, setPerson] = useState<PersonCard | null>(null);
  const [messages, setMessages] = useState<MessageView[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const page = await api.conversation(userId);
      setPerson(page.person);
      setMessages(page.items);
      setError('');
    } catch (problem) {
      setError(problem instanceof ApiError ? problem.message : 'Could not open this conversation.');
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => { void load(); }, [load]);

  return (
    <div className="stack">
      <div className="row">
        <button type="button" className="btn btn--sm" onClick={onBack}>
          {t('messages.back')}
        </button>
        {person && (
          <span className="row row--tight">
            <Avatar name={person.display_name} status={person.status} />
            <strong>{person.display_name}</strong>
          </span>
        )}
      </div>

      {error && <Notice kind="risk">{error}</Notice>}
      {loading && <Loading label={t('messages.opening')} />}

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

      <Composer
        placeholder={t('messages.placeholder')}
        submitLabel={t('messages.send')}
        max={MESSAGE_MAX_CHARS}
        busy={sending}
        onSubmit={async (body) => {
          setSending(true);
          try {
            const sent = await api.sendMessage(userId, body);
            setMessages((prev) => [...prev, sent]);
            setError('');
          } catch (problem) {
            setError(problem instanceof ApiError ? problem.message : 'Could not send that.');
          } finally {
            setSending(false);
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

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setItems((await api.conversations()).items);
      setError('');
    } catch (problem) {
      setError(problem instanceof ApiError ? problem.message : 'Could not load your messages.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  if (openWith) {
    return (
      <div className="stack community-column">
        <Conversation
          userId={openWith}
          onBack={() => { onOpenChange(null); onReadSomething(); void load(); }}
        />
      </div>
    );
  }

  return (
    <div className="stack community-column">
      <div className="screen__head">
        <h1 className="screen__title">{t('messages.title')}</h1>
        <p className="screen__lede">{t('messages.lede')}</p>
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
    </div>
  );
}
