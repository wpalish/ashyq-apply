/**
 * Community — one applicant's profile, and the editor for your own.
 *
 * A profile answers three questions in order: who is this, where are they
 * aiming, and what have they said. Nothing on this screen comes from the
 * research pipeline — it is what its owner typed, and it is labelled as such.
 */

import { useCallback, useEffect, useState } from 'react';
import { api, ApiError } from '@/api/client';
import { Empty, Loading, Notice, Panel } from '@/components/primitives';
import { Avatar, BIO_MAX_CHARS, Post, StatusChip } from '@/components/social';
import { useTranslation } from '@/lib/useTranslation';
import type {
  ApplicantStatus,
  DirectMessagePolicy,
  PersonCard,
  PostView,
  ProfileInput,
} from '@/types';

const MAX_UNIVERSITIES = 10;

function ProfileForm({
  initial, onSaved,
}: { initial: PersonCard | null; onSaved: (saved: PersonCard) => void }) {
  const { t } = useTranslation();
  const [status, setStatus] = useState<ApplicantStatus | ''>(initial?.status ?? '');
  const [city, setCity] = useState(initial?.target_city ?? '');
  const [major, setMajor] = useState(initial?.target_major ?? '');
  const [bio, setBio] = useState(initial?.bio ?? '');
  const [dmPolicy, setDmPolicy] = useState<DirectMessagePolicy>(initial?.dm_policy ?? 'threads');
  const [universities, setUniversities] = useState((initial?.universities ?? []).join(', '));
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  const parsed = universities
    .split(',')
    .map((name) => name.trim())
    .filter(Boolean)
    .slice(0, MAX_UNIVERSITIES);

  return (
    <form
      className="stack"
      onSubmit={async (event) => {
        event.preventDefault();
        setSaving(true);
        const payload: ProfileInput = {
          status: status === '' ? null : status,
          target_city: city.trim(),
          target_major: major.trim(),
          bio: bio.trim(),
          dm_policy: dmPolicy,
          universities: parsed,
        };
        try {
          onSaved(await api.saveSocialProfile(payload));
          setError('');
        } catch (problem) {
          setError(problem instanceof ApiError ? problem.message : 'Could not save your profile.');
        } finally {
          setSaving(false);
        }
      }}
    >
      {error && <Notice kind="risk">{error}</Notice>}
      <div className="grid-2">
        <div className="field">
          <label className="field__label" htmlFor="profile-status">{t('person.formStatus')}</label>
          <select
            id="profile-status"
            value={status}
            onChange={(event) => setStatus(event.target.value as ApplicantStatus | '')}
          >
            <option value="">{t('person.formStatusNone')}</option>
            <option value="waitlist">{t('person.statusWaitlist')}</option>
            <option value="accepted">{t('person.statusAccepted')}</option>
          </select>
          <span className="field__hint">
            {t('person.formStatusHint')}
          </span>
        </div>
        <div className="field">
          <label className="field__label" htmlFor="profile-city">{t('person.formCity')}</label>
          <input
            id="profile-city"
            value={city}
            placeholder="Astana"
            maxLength={120}
            onChange={(event) => setCity(event.target.value)}
          />
        </div>
        <div className="field">
          <label className="field__label" htmlFor="profile-major">{t('person.formMajor')}</label>
          <input
            id="profile-major"
            value={major}
            placeholder="Computer science"
            maxLength={120}
            onChange={(event) => setMajor(event.target.value)}
          />
        </div>
        <div className="field">
          <label className="field__label" htmlFor="profile-unis">{t('person.formUniversities')}</label>
          <input
            id="profile-unis"
            value={universities}
            placeholder="KBTU, Nazarbayev University"
            onChange={(event) => setUniversities(event.target.value)}
          />
          <span className="field__hint">
            {t('person.formUniversitiesHint')} {parsed.length}/{MAX_UNIVERSITIES}
          </span>
        </div>
      </div>
      <div className="field">
        <label className="field__label" htmlFor="profile-dm">{t('person.formDmPolicy')}</label>
        <select
          id="profile-dm"
          value={dmPolicy}
          onChange={(event) => setDmPolicy(event.target.value as DirectMessagePolicy)}
        >
          <option value="threads">{t('person.formDmThreads')}</option>
          <option value="anyone">{t('person.formDmAnyone')}</option>
          <option value="nobody">{t('person.formDmNobody')}</option>
        </select>
        <span className="field__hint">{t('person.formDmHint')}</span>
      </div>
      <div className="field">
        <label className="field__label" htmlFor="profile-bio">{t('person.formBio')}</label>
        <textarea
          id="profile-bio"
          rows={3}
          value={bio}
          maxLength={BIO_MAX_CHARS}
          placeholder="What you are working on, and what you would like to be asked about."
          onChange={(event) => setBio(event.target.value)}
        />
        <span className="field__hint">
          {BIO_MAX_CHARS - bio.trim().length} {t('community.charsLeft')}
        </span>
      </div>
      <div className="row">
        <button className="btn btn--primary" type="submit" disabled={saving}>
          {saving
            ? t('person.saving')
            : t(initial ? 'person.save' : 'community.createProfile')}
        </button>
        <span className="xs faint">
          {t('person.publicWarning')}
        </span>
      </div>
    </form>
  );
}

export function PersonScreen({
  userId, myUserId, onOpenPerson, onOpenMessages, onProfileSaved, onLeft,
}: {
  userId: string | null;
  myUserId: string | null;
  onOpenPerson: (id: string) => void;
  onOpenMessages: (id: string) => void;
  onProfileSaved: (saved: PersonCard) => void;
  onLeft: () => void;
}) {
  const { t } = useTranslation();
  const isMe = userId === null || userId === myUserId;
  const [person, setPerson] = useState<PersonCard | null>(null);
  const [posts, setPosts] = useState<PostView[]>([]);
  const [state, setState] = useState<'loading' | 'ready' | 'absent' | 'error'>('loading');
  const [message, setMessage] = useState('');
  const [editing, setEditing] = useState(false);
  const [leaving, setLeaving] = useState(false);

  const load = useCallback(async () => {
    setState('loading');
    try {
      const card = isMe
        ? (await api.socialMe()).profile
        : await api.person(userId as string);
      setPerson(card);
      if (card) setPosts((await api.feed({ author: card.user_id })).items);
      setState(card ? 'ready' : 'absent');
    } catch (problem) {
      if (problem instanceof ApiError && problem.status === 404) {
        setState('absent');
        return;
      }
      setMessage(problem instanceof ApiError ? problem.message : 'Could not load this profile.');
      setState('error');
    }
  }, [isMe, userId]);

  useEffect(() => { void load(); }, [load]);

  if (state === 'loading') return <Loading label={t('person.loading')} />;
  if (state === 'error') return <Notice kind="risk">{message}</Notice>;

  if (state === 'absent') {
    return isMe ? (
      <div className="stack">
        <div className="screen__head">
          <h1 className="screen__title">{t('person.joinTitle')}</h1>
          <p className="screen__lede">{t('person.joinLede')}</p>
        </div>
        <Panel>
          <ProfileForm
            initial={null}
            onSaved={(saved) => { setPerson(saved); setState('ready'); onProfileSaved(saved); }}
          />
        </Panel>
      </div>
    ) : (
      <Empty title={t('person.noProfile')}>
        <p className="small">{t('person.noProfileHint')}</p>
      </Empty>
    );
  }

  const card = person as PersonCard;
  const aims: [string, string][] = [
    [t('person.city'), card.target_city],
    [t('person.major'), card.target_major],
    [t('person.universities'), card.universities.join(', ')],
  ];

  return (
    <div className="stack">
      <header className="profile-head">
        <Avatar name={card.display_name} status={card.status} large />
        <div className="stack stack--tight">
          <h1 className="profile-head__name">{card.display_name}</h1>
          <div className="row row--tight">
            <StatusChip status={card.status} />
            {isMe && (
              <button className="btn btn--sm" type="button" onClick={() => setEditing((v) => !v)}>
                {t(editing ? 'person.cancel' : 'person.edit')}
              </button>
            )}
            {/* Offered only when it would work. A button that leads to a 403 is
                worse than none: it invites the person to be refused. */}
            {!isMe && card.dm_policy !== 'nobody' && (
              <button
                className="btn btn--sm btn--primary"
                type="button"
                onClick={() => onOpenMessages(card.user_id)}
              >
                {t('messages.write')}
              </button>
            )}
            {!isMe && card.dm_policy === 'nobody' && (
              <span className="xs faint">{t('messages.closed')}</span>
            )}
          </div>
        </div>
      </header>

      {editing && (
        <Panel title={t('person.yourProfile')}>
          <ProfileForm
            initial={card}
            onSaved={(saved) => { setPerson(saved); setEditing(false); onProfileSaved(saved); }}
          />
        </Panel>
      )}

      <Panel title={t('person.aimingAt')} hint={t('person.aimingHint')}>
        <dl className="kv">
          {aims.map(([label, value]) => (
            <div key={label} style={{ display: 'contents' }}>
              <dt>{label}</dt>
              <dd>{value || <span className="faint">{t('person.notStated')}</span>}</dd>
            </div>
          ))}
        </dl>
        {card.bio && <p className="profile-bio">{card.bio}</p>}
      </Panel>

      <Panel title={t(isMe ? 'person.yourPosts' : 'person.postsBy')}>
        {posts.length === 0 ? (
          <Empty title={t(isMe ? 'person.noPostsYou' : 'person.noPostsThem')}>
            <p className="small">{isMe ? t('person.noPostsYouHint') : ' '}</p>
          </Empty>
        ) : (
          <div className="feed">
            {posts.map((post) => (
              <Post
                key={post.id}
                post={post}
                onOpenPerson={onOpenPerson}
                onDelete={
                  isMe
                    ? async () => {
                        await api.deletePost(post.id);
                        setPosts((prev) => prev.filter((item) => item.id !== post.id));
                      }
                    : undefined
                }
              />
            ))}
          </div>
        )}
      </Panel>

      {isMe && (
        <Panel title={t('leave.title')} hint={t('leave.hint')}>
          {leaving ? (
            <div className="row">
              <strong className="small">
                {t('leave.confirm')} {t('leave.confirmSuffix')}
              </strong>
              <button
                className="btn btn--sm btn--danger"
                type="button"
                onClick={async () => {
                  try {
                    await api.leaveCommunity();
                    onLeft();
                    setPerson(null);
                    setPosts([]);
                    setState('absent');
                  } catch (problem) {
                    setMessage(
                      problem instanceof ApiError ? problem.message : 'Could not leave.',
                    );
                    setState('error');
                  } finally {
                    setLeaving(false);
                  }
                }}
              >
                {t('leave.yes')}
              </button>
              <button className="btn btn--sm" type="button" onClick={() => setLeaving(false)}>
                {t('leave.keep')}
              </button>
            </div>
          ) : (
            <button className="btn btn--danger" type="button" onClick={() => setLeaving(true)}>
              {t('leave.title')}
            </button>
          )}
        </Panel>
      )}
    </div>
  );
}
