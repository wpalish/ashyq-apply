/**
 * Community — Discover.
 *
 * Filters first, then people. The filters are the product here: the question
 * is not "who is on this service" but "who is going where I am going".
 */

import { useCallback, useEffect, useState } from 'react';
import { api, ApiError } from '@/api/client';
import { Empty, Loading, Notice } from '@/components/primitives';
import { PersonTile } from '@/components/social';
import type { MessageKey } from '@/lib/i18n';
import { useTranslation } from '@/lib/useTranslation';
import type { PeopleFilters, PersonCard } from '@/types';

const FIELDS: { key: keyof PeopleFilters; label: MessageKey; placeholder: string }[] = [
  // The placeholders are proper nouns, so they read the same in every language.
  { key: 'city', label: 'discover.city', placeholder: 'Astana' },
  { key: 'university', label: 'discover.university', placeholder: 'KBTU' },
  { key: 'major', label: 'discover.major', placeholder: 'Computer science' },
];

export function DiscoverScreen({ onOpenPerson }: { onOpenPerson: (id: string) => void }) {
  const { t } = useTranslation();
  const [filters, setFilters] = useState<PeopleFilters>({});
  const [people, setPeople] = useState<PersonCard[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async (active: PeopleFilters, from?: string | null) => {
    setLoading(true);
    try {
      const page = await api.people(active, from);
      setPeople((prev) => (from ? [...prev, ...page.items] : page.items));
      setCursor(page.next_cursor);
      setError('');
    } catch (problem) {
      setError(problem instanceof ApiError ? problem.message : 'Could not load people.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(filters); }, [load, filters]);

  const filtered = Object.values(filters).some(Boolean);

  return (
    <div className="stack">
      <div className="screen__head">
        <h1 className="screen__title">{t('discover.title')}</h1>
        <p className="screen__lede">{t('discover.lede')}</p>
      </div>

      <div className="filters">
        {FIELDS.map((field) => (
          <div className="field" key={field.key}>
            <label className="field__label xs" htmlFor={`discover-${field.key}`}>
              {t(field.label)}
            </label>
            <input
              id={`discover-${field.key}`}
              placeholder={field.placeholder}
              defaultValue={filters[field.key] ?? ''}
              onBlur={(event) =>
                setFilters((f) => ({ ...f, [field.key]: event.target.value.trim() }))
              }
            />
          </div>
        ))}
        <div className="field">
          <label className="field__label xs" htmlFor="discover-status">{t('discover.status')}</label>
          <select
            id="discover-status"
            value={filters.status ?? ''}
            onChange={(event) => setFilters((f) => ({ ...f, status: event.target.value }))}
          >
            <option value="">{t('discover.anyStatus')}</option>
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

      <div className="person-grid">
        {people.map((person) => (
          <PersonTile key={person.user_id} person={person} onOpen={onOpenPerson} />
        ))}
      </div>

      {loading && <Loading label={t('discover.looking')} />}
      {!loading && people.length === 0 && (
        <Empty title={t(filtered ? 'discover.noMatch' : 'discover.empty')}>
          <p className="small">{t(filtered ? 'discover.noMatchHint' : 'discover.emptyHint')}</p>
        </Empty>
      )}
      {cursor && !loading && (
        <button className="btn" type="button" onClick={() => load(filters, cursor)}>
          {t('discover.more')}
        </button>
      )}
    </div>
  );
}
