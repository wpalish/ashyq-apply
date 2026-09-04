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
import type { ApplicantStatus, PersonCard, PostView, ProfileInput } from '@/types';

const MAX_UNIVERSITIES = 10;

function ProfileForm({
  initial, onSaved,
}: { initial: PersonCard | null; onSaved: (saved: PersonCard) => void }) {
  const [status, setStatus] = useState<ApplicantStatus | ''>(initial?.status ?? '');
  const [city, setCity] = useState(initial?.target_city ?? '');
  const [major, setMajor] = useState(initial?.target_major ?? '');
  const [bio, setBio] = useState(initial?.bio ?? '');
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
          <label className="field__label" htmlFor="profile-status">Where you stand</label>
          <select
            id="profile-status"
            value={status}
            onChange={(event) => setStatus(event.target.value as ApplicantStatus | '')}
          >
            <option value="">Prefer not to say</option>
            <option value="waitlist">On a waitlist</option>
            <option value="accepted">Accepted</option>
          </select>
          <span className="field__hint">
            Left unset, your profile says "not stated" rather than guessing.
          </span>
        </div>
        <div className="field">
          <label className="field__label" htmlFor="profile-city">City you are applying to</label>
          <input
            id="profile-city"
            value={city}
            placeholder="Astana"
            maxLength={120}
            onChange={(event) => setCity(event.target.value)}
          />
        </div>
        <div className="field">
          <label className="field__label" htmlFor="profile-major">Major</label>
          <input
            id="profile-major"
            value={major}
            placeholder="Computer science"
            maxLength={120}
            onChange={(event) => setMajor(event.target.value)}
          />
        </div>
        <div className="field">
          <label className="field__label" htmlFor="profile-unis">Universities you are aiming at</label>
          <input
            id="profile-unis"
            value={universities}
            placeholder="KBTU, Nazarbayev University"
            onChange={(event) => setUniversities(event.target.value)}
          />
          <span className="field__hint">
            Separate with commas. Up to {MAX_UNIVERSITIES}; {parsed.length} so far.
          </span>
        </div>
      </div>
      <div className="field">
        <label className="field__label" htmlFor="profile-bio">About you</label>
        <textarea
          id="profile-bio"
          rows={3}
          value={bio}
          maxLength={BIO_MAX_CHARS}
          placeholder="What you are working on, and what you would like to be asked about."
          onChange={(event) => setBio(event.target.value)}
        />
        <span className="field__hint">{BIO_MAX_CHARS - bio.trim().length} characters left</span>
      </div>
      <div className="row">
        <button className="btn btn--primary" type="submit" disabled={saving}>
          {saving ? 'Saving…' : initial ? 'Save profile' : 'Create profile'}
        </button>
        <span className="xs faint">
          Everything here is public to other applicants. Your applicant case is not.
        </span>
      </div>
    </form>
  );
}

export function PersonScreen({
  userId, myUserId, onOpenPerson, onProfileSaved, onLeft,
}: {
  userId: string | null;
  myUserId: string | null;
  onOpenPerson: (id: string) => void;
  onProfileSaved: (saved: PersonCard) => void;
  onLeft: () => void;
}) {
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

  if (state === 'loading') return <Loading label="Loading profile" />;
  if (state === 'error') return <Notice kind="risk">{message}</Notice>;

  if (state === 'absent') {
    return isMe ? (
      <div className="stack">
        <div className="screen__head">
          <h1 className="screen__title">Join the community</h1>
          <p className="screen__lede">
            Registering an account did not publish anything about you. This form is what
            puts you in Discover, and you can edit it or leave again at any time.
          </p>
        </div>
        <Panel>
          <ProfileForm
            initial={null}
            onSaved={(saved) => { setPerson(saved); setState('ready'); onProfileSaved(saved); }}
          />
        </Panel>
      </div>
    ) : (
      <Empty title="No profile here">
        <p className="small">This applicant has not joined the community.</p>
      </Empty>
    );
  }

  const card = person as PersonCard;
  const aims: [string, string][] = [
    ['City', card.target_city],
    ['Major', card.target_major],
    ['Universities', card.universities.join(', ')],
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
                {editing ? 'Cancel' : 'Edit profile'}
              </button>
            )}
          </div>
        </div>
      </header>

      {editing && (
        <Panel title="Your profile">
          <ProfileForm
            initial={card}
            onSaved={(saved) => { setPerson(saved); setEditing(false); onProfileSaved(saved); }}
          />
        </Panel>
      )}

      <Panel title="Aiming at" hint="Stated by this applicant. Not checked against a university page.">
        <dl className="kv">
          {aims.map(([label, value]) => (
            <div key={label} style={{ display: 'contents' }}>
              <dt>{label}</dt>
              <dd>{value || <span className="faint">not stated</span>}</dd>
            </div>
          ))}
        </dl>
        {card.bio && <p className="profile-bio">{card.bio}</p>}
      </Panel>

      <Panel title={isMe ? 'Your posts' : `Posts by ${card.display_name}`}>
        {posts.length === 0 ? (
          <Empty title={isMe ? 'You have not posted yet' : 'Nothing posted yet'}>
            <p className="small">
              {isMe ? 'Anything you post in the community shows up here.' : ' '}
            </p>
          </Empty>
        ) : (
          <div className="feed">
            {posts.map((post) => (
              <Post key={post.id} post={post} onOpenPerson={onOpenPerson} />
            ))}
          </div>
        )}
      </Panel>

      {isMe && (
        <Panel
          title="Leave the community"
          hint="Your account and your applicant research stay. Your profile, your posts and your replies are deleted, and you disappear from Discover."
        >
          {leaving ? (
            <div className="row">
              <strong className="small">
                Delete your profile and {posts.length === 1 ? 'your post' : `${posts.length} posts`}?
                This cannot be undone.
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
                Yes, delete it
              </button>
              <button className="btn btn--sm" type="button" onClick={() => setLeaving(false)}>
                Keep my profile
              </button>
            </div>
          ) : (
            <button className="btn btn--danger" type="button" onClick={() => setLeaving(true)}>
              Leave the community
            </button>
          )}
        </Panel>
      )}
    </div>
  );
}
