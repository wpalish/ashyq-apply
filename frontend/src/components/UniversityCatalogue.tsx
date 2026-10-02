import { useEffect, useRef, useState } from 'react';
import { api, type UniversityCatalogue as Catalogue } from '@/api/client';
import { useStore } from '@/lib/store';

export function UniversityCatalogue({ onStart, onProgress }: { onStart?: () => void; onProgress?: () => void }) {
  const { savedProfile, startRun, loading, run } = useStore();
  const [q, setQ] = useState('');
  const [country, setCountry] = useState('');
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<Catalogue | null>(null);
  const [error, setError] = useState('');
  const [fetching, setFetching] = useState(false);
  const [retry, setRetry] = useState(0);
  const [selected, setSelected] = useState<string[]>([]);
  const pendingRun = useRef<string | null | undefined>(undefined);

  useEffect(() => {
    let current = true;
    const timer = setTimeout(() => {
      setFetching(true);
      setError('');
      api.universities({ q, country, offset, profile_id: savedProfile?.id })
        .then((next) => { if (current) setData(next); })
        .catch((e: unknown) => { if (current) setError(e instanceof Error ? e.message : 'Cannot load universities.'); })
        .finally(() => { if (current) setFetching(false); });
    }, 200);
    return () => { current = false; clearTimeout(timer); };
  }, [q, country, offset, savedProfile?.id, retry]);

  useEffect(() => {
    if (pendingRun.current !== undefined && run?.id && run.id !== pendingRun.current) {
      pendingRun.current = undefined;
      onProgress?.();
    }
  }, [run?.id, onProgress]);

  return <section className="university-catalogue" aria-label="University catalogue">
    <div className="catalogue-heading">
      <div><p className="screen__eyebrow">EXPLORE UNIVERSITIES</p><h2>Find a place to begin.</h2>
        <p>Browse {data?.catalogue_total ?? 'our'} universities, even when live research is unavailable. Select up to 5 to check against your profile.</p></div>
      {data && <span className="chip">{data.seed_count} imported universities</span>}
    </div>
    <div className="catalogue-tools">
      <label>University, city or country<input type="search" value={q} placeholder="Try MIT, Canada or Groningen" onChange={(e) => { setQ(e.target.value); setOffset(0); }} /></label>
      <label>Country or region<select value={country} onChange={(e) => { setCountry(e.target.value); setOffset(0); }}>
        <option value="">All countries</option>
        {['Europe', 'Asia', 'North America', 'South America', 'Oceania', 'Africa'].map((c) => <option key={c}>{c}</option>)}
        {data?.countries.map((c) => <option key={c}>{c}</option>)}
      </select></label>
      <button type="button" className="btn btn--primary" disabled={loading || (!!savedProfile && selected.length === 0)} onClick={async () => {
        if (!savedProfile) { onStart?.(); return; }
        pendingRun.current = run?.id ?? null;
        await startRun(false, selected);
      }}>{loading ? 'Starting…' : savedProfile ? `Research selected (${selected.length})` : 'Complete profile to research'}</button>
    </div>
    <p className="catalogue-note">These are university candidates. Your requested programme, admission requirements, tuition and scholarships still need official verification. Missing information never means you are ineligible.</p>
    {error && <div role="alert">{error} <button className="btn btn--sm" onClick={() => setRetry((n) => n + 1)}>Try again</button></div>}
    <p role="status">{fetching ? 'Searching the local catalogue…' : data ? `${data.total} universities found` : 'Loading catalogue…'}</p>
    <div className="catalogue-grid" aria-busy={fetching}>
      {data?.items.map((u) => <article key={u.id} className="catalogue-card">
        <label className="catalogue-choice"><input type="checkbox" checked={selected.includes(u.id)} disabled={!savedProfile || (!selected.includes(u.id) && selected.length >= 5)} onChange={(e) => setSelected((ids) => e.target.checked ? [...ids, u.id] : ids.filter((id) => id !== u.id))} /><strong>{u.name}</strong></label>
        <p>{u.city}{u.city ? ' · ' : ''}{u.country}</p>
        <span className="chip">Programme verification needed</span>
        <dl><div><dt>Admission fit</dt><dd>Not assessed</dd></div><div><dt>Tuition & funding</dt><dd>Research required</dd></div></dl>
        {u.seed_ranking && <p className="xs faint">QS {u.seed_ranking.year}: #{u.seed_ranking.rank} · imported ranking</p>}
        <details><summary>Imported data & sources</summary>
          <p className="xs">Snapshot {u.seed_version?.split('/')[0] ?? 'curated registry'}. Source observation date, programme and fee population are unknown. Imported figures do not determine eligibility or affordability.</p>
          {u.seed_tuition_usd && <p className="xs">Historical estimate: USD {u.seed_tuition_usd.min.toLocaleString()}–{u.seed_tuition_usd.max.toLocaleString()}. Period and scope unverified.</p>}
          <p className="xs">Website identity: {u.domain_status === 'curated' ? 'curated registry' : u.domain_status === 'site_identity_checked' ? 'checked on the website' : 'verification needed'}.</p>
          {u.sources.ranking && <a href={u.sources.ranking} target="_blank" rel="noreferrer">Ranking publisher ↗</a>}
        </details>
      </article>)}
    </div>
    {data?.total === 0 && <p>No universities match these filters. Try another country or name.</p>}
    {data && data.total > 20 && <nav className="catalogue-pagination" aria-label="University catalogue pages">
      <button className="btn" disabled={offset === 0 || fetching} onClick={() => setOffset((n) => Math.max(0, n - 20))}>Previous</button>
      <span>{offset + 1}–{Math.min(offset + 20, data.total)} of {data.total}</span>
      <button className="btn" disabled={offset + 20 >= data.total || fetching} onClick={() => setOffset((n) => n + 20)}>Next</button>
    </nav>}
  </section>;
}
