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
import type { PeopleFilters, PersonCard } from '@/types';

const FIELDS: { key: keyof PeopleFilters; label: string; placeholder: string }[] = [
  { key: 'city', label: 'City', placeholder: 'Astana' },
  { key: 'university', label: 'University', placeholder: 'KBTU' },
  { key: 'major', label: 'Major', placeholder: 'Computer science' },
];

export function DiscoverScreen({ onOpenPerson }: { onOpenPerson: (id: string) => void }) {
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
        <h1 className="screen__title">Find applicants like you</h1>
        <p className="screen__lede">
          Everyone listed here chose to be listed. Spelling does not matter — KBTU, kbtu and
          K.B.T.U. are one university to the filter.
        </p>
      </div>

      <div className="filters">
        {FIELDS.map((field) => (
          <div className="field" key={field.key}>
            <label className="field__label xs" htmlFor={`discover-${field.key}`}>{field.label}</label>
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
          <label className="field__label xs" htmlFor="discover-status">Status</label>
          <select
            id="discover-status"
            value={filters.status ?? ''}
            onChange={(event) => setFilters((f) => ({ ...f, status: event.target.value }))}
          >
            <option value="">Any status</option>
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

      <div className="person-grid">
        {people.map((person) => (
          <PersonTile key={person.user_id} person={person} onOpen={onOpenPerson} />
        ))}
      </div>

      {loading && <Loading label="Looking" />}
      {!loading && people.length === 0 && (
        <Empty title={filtered ? 'Nobody matches yet' : 'Nobody has joined yet'}>
          <p className="small">
            {filtered
              ? 'Try one filter at a time — city alone usually finds the most people.'
              : 'Create your own profile and you will be the first person here.'}
          </p>
        </Empty>
      )}
      {cursor && !loading && (
        <button className="btn" type="button" onClick={() => load(filters, cursor)}>
          Show more people
        </button>
      )}
    </div>
  );
}
