import { useEffect, useRef, useState } from 'react';
import { api, type UniversityCandidate, type UniversityCatalogue as Catalogue } from '@/api/client';
import { Chip } from '@/components/primitives';
import { claimValue, date } from '@/lib/format';
import { localize, localPeriod } from '@/lib/messages';
import { useStore } from '@/lib/store';
import { useTranslation } from '@/lib/useTranslation';
import type { MessageKey } from '@/lib/i18n';
import type { CatalogueKbTuition, CatalogueKnowledge, KbProgrammePage } from '@/types';

/** Periods the cost table takes as a yearly figure (`app.knowledge.claims._ANNUAL`). */
const ANNUAL = new Set(['year', 'annual', 'per year', 'academic year', 'yearly']);

const PROGRAMME_PAGE: Record<KbProgrammePage, MessageKey> = {
  known: 'catalogue.kb.programme.known',
  related_only: 'catalogue.kb.programme.related_only',
  not_offered: 'catalogue.kb.programme.not_offered',
  unknown: 'catalogue.kb.programme.unknown',
};

export function UniversityCatalogue({ onStart, onProgress }: { onStart?: () => void; onProgress?: () => void }) {
  const { savedProfile, startRun, loading, run } = useStore();
  const { t, tf, tn } = useTranslation();
  const [q, setQ] = useState('');
  const [country, setCountry] = useState('');
  const [verifiedOnly, setVerifiedOnly] = useState(false);
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<Catalogue | null>(null);
  const [error, setError] = useState('');
  const [fetching, setFetching] = useState(false);
  const [retry, setRetry] = useState(0);
  const [selected, setSelected] = useState<string[]>([]);
  const pendingRun = useRef<string | null | undefined>(undefined);
  // kb mode is the API's own statement: `kb_total` is null in live and demo mode.
  const kbMode = data?.kb_total != null;

  useEffect(() => {
    setOffset(0);
    setSelected([]);
    pendingRun.current = undefined;
  }, [savedProfile?.id]);

  useEffect(() => {
    let current = true;
    const timer = setTimeout(() => {
      setFetching(true);
      setError('');
      api.universities({ q, country, offset, profile_id: savedProfile?.id, ...(verifiedOnly ? { verified: true } : {}) })
        .then((next) => { if (current) setData(next); })
        .catch((e: unknown) => { if (current) setError(e instanceof Error ? e.message : 'Cannot load universities.'); })
        .finally(() => { if (current) setFetching(false); });
    }, 200);
    return () => { current = false; clearTimeout(timer); };
  }, [q, country, verifiedOnly, offset, savedProfile?.id, retry]);

  useEffect(() => {
    if (pendingRun.current !== undefined && run?.id && run.id !== pendingRun.current) {
      pendingRun.current = undefined;
      onProgress?.();
    }
  }, [run?.id, onProgress]);

  /** The KB fee as published: "2,190 CHF per semester · academic year 2026/27". */
  const feeLine = (fee: CatalogueKbTuition): string => {
    const amount = claimValue(fee);
    const money = fee.period && !ANNUAL.has(fee.period.toLowerCase())
      ? tf('detail.fee.perPeriod', { amount, period: localPeriod(fee.period) })
      : tf('detail.fee.perYear', { amount });
    return fee.academic_year ? `${money} · ${tf('detail.fee.year', { year: fee.academic_year })}` : money;
  };
  const staleText = (fee: CatalogueKbTuition): string =>
    fee.stale_reasons.map((reason, i) => localize(fee.stale_messages[i], reason)).join('; ');
  const reviewLabel = (label: string | null): string =>
    label === 'human verified' ? t('catalogue.kb.review.human')
      : label === 'expert-checked, quote verified' ? t('catalogue.kb.review.expert')
        : (label ?? '');
  const historical = (u: UniversityCandidate) => u.seed_tuition_usd
    && tf('catalogue.kb.historicalValue', { min: u.seed_tuition_usd.min.toLocaleString(), max: u.seed_tuition_usd.max.toLocaleString() });

  const kbChips = (k: CatalogueKnowledge) => k.in_kb
    ? <div className="catalogue-kb-chips">
      <Chip tone="ok" name={t('catalogue.kb.chip')}>{t('catalogue.kb.chip')}</Chip>
      <Chip>{tf('catalogue.kb.answers', { n: k.core_answered })}</Chip>
      {k.documents > 0 && <Chip>{tn('catalogue.kb.documents', k.documents)}</Chip>}
      <Chip tone={k.programme_page === 'known' ? 'ok' : 'warn'}>{t(PROGRAMME_PAGE[k.programme_page])}</Chip>
      {k.stale_count > 0 && <Chip tone="warn">{tn('catalogue.kb.staleCount', k.stale_count)}</Chip>}
    </div>
    : <Chip>{t('catalogue.kb.none')}</Chip>;

  return <section className="university-catalogue" aria-label="University catalogue">
    <div className="catalogue-heading">
      <div><p className="screen__eyebrow">EXPLORE UNIVERSITIES</p><h2>Find a place to begin.</h2>
        <p>Browse {data?.catalogue_total ?? 'our'} universities, even when live research is unavailable. Select up to 5 to check against your profile.</p></div>
      {data && (kbMode
        ? <span className="chip">{tf('catalogue.kb.coverage', { n: data.kb_total ?? 0, total: data.catalogue_total })}</span>
        : <span className="chip">{data.seed_count} imported universities</span>)}
    </div>
    <div className="catalogue-tools">
      <label>University, city or country<input type="search" value={q} placeholder="Try MIT, Canada or Groningen" onChange={(e) => { setQ(e.target.value); setOffset(0); }} /></label>
      <label>Country or region<select value={country} onChange={(e) => { setCountry(e.target.value); setOffset(0); }}>
        <option value="">All countries</option>
        {['Europe', 'Asia', 'North America', 'South America', 'Oceania', 'Africa'].map((c) => <option key={c}>{c}</option>)}
        {data?.countries.map((c) => <option key={c}>{c}</option>)}
      </select></label>
      {(kbMode || verifiedOnly) && <label className="catalogue-verified"><input type="checkbox" checked={verifiedOnly} onChange={(e) => { setVerifiedOnly(e.target.checked); setOffset(0); }} />{t('catalogue.kb.filter')}</label>}
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
      {data?.items.map((u) => {
        const k = kbMode ? u.knowledge ?? null : null;
        const fee = k?.tuition ?? null;
        return <article key={u.id} className="catalogue-card">
          <label className="catalogue-choice"><input type="checkbox" checked={selected.includes(u.id)} disabled={!savedProfile || (!selected.includes(u.id) && selected.length >= 5)} onChange={(e) => setSelected((ids) => e.target.checked ? [...ids, u.id] : ids.filter((id) => id !== u.id))} /><strong>{u.name}</strong></label>
          <p>{u.city}{u.city ? ' · ' : ''}{u.country}</p>
          {k ? kbChips(k) : <span className="chip">Programme verification needed</span>}
          {k
            ? <dl>
              <div><dt>Admission fit</dt><dd>Not assessed</dd></div>
              <div><dt>{t('catalogue.kb.tuition')}</dt><dd>
                {fee ? <>
                  {feeLine(fee)}
                  {fee.stale && <> <Chip tone="warn" title={staleText(fee)}>{t('results.staleNoAge')}</Chip></>}
                  {fee.stale && <span className="xs faint"> {tf('results.notCurrent', { reason: staleText(fee) })}</span>}
                  {fee.caveat && <span className="xs faint"> {tf('results.caveat', { caveat: localize(fee.caveat_message, fee.caveat) })}</span>}
                </> : t('catalogue.kb.noFee')}
              </dd></div>
              {u.seed_tuition_usd && <div><dt>{t('catalogue.kb.historical')}</dt><dd className="xs">{historical(u)}</dd></div>}
            </dl>
            : <dl><div><dt>Admission fit</dt><dd>Not assessed</dd></div><div><dt>Tuition & funding</dt><dd>Research required</dd></div></dl>}
          {k?.in_kb && k.verified_on && <p className="xs faint">{tf('catalogue.kb.verifiedOn', { date: date(k.verified_on), label: reviewLabel(k.review_label) })}</p>}
          {u.seed_ranking && <p className="xs faint">QS {u.seed_ranking.year}: #{u.seed_ranking.rank} · imported ranking</p>}
          <details><summary>Imported data & sources</summary>
            <p className="xs">Snapshot {u.seed_version?.split('/')[0] ?? 'curated registry'}. Source observation date, programme and fee population are unknown. Imported figures do not determine eligibility or affordability.</p>
            {!k && u.seed_tuition_usd && <p className="xs">Historical estimate: USD {u.seed_tuition_usd.min.toLocaleString()}–{u.seed_tuition_usd.max.toLocaleString()}. Period and scope unverified.</p>}
            <p className="xs">Website identity: {u.domain_status === 'curated' ? 'curated registry' : u.domain_status === 'site_identity_checked' ? 'checked on the website' : 'verification needed'}.</p>
            {u.sources.ranking && <a href={u.sources.ranking} target="_blank" rel="noreferrer">Ranking publisher ↗</a>}
          </details>
        </article>;
      })}
    </div>
    {data?.total === 0 && <p>No universities match these filters. Try another country or name.</p>}
    {data && data.total > 20 && <nav className="catalogue-pagination" aria-label="University catalogue pages">
      <button className="btn" disabled={offset === 0 || fetching} onClick={() => setOffset((n) => Math.max(0, n - 20))}>Previous</button>
      <span>{offset + 1}–{Math.min(offset + 20, data.total)} of {data.total}</span>
      <button className="btn" disabled={offset + 20 >= data.total || fetching} onClick={() => setOffset((n) => n + 20)}>Next</button>
    </nav>}
  </section>;
}
