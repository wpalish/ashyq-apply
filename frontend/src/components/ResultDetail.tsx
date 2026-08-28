/**
 * Screen 05 — University detail, rendered inline under its shortlist row.
 *
 * Tabbed rather than stacked, because a single row carries five different
 * kinds of information and putting them all on screen at once is what makes
 * these tables unreadable.
 */

import { useState } from 'react';
import { Chip, Notice, SourceLink, StatusChip } from '@/components/primitives';
import {
  claimStatusTone, date, dateTime, eligibilityTone, fundingClassTone, humanize, money,
} from '@/lib/format';
import type { ProgramResult } from '@/types';

type Tab = 'requirements' | 'funding' | 'costs' | 'documents' | 'sources' | 'score';

const TABS: { id: Tab; label: string }[] = [
  { id: 'requirements', label: 'Requirements' },
  { id: 'funding', label: 'Funding' },
  { id: 'costs', label: 'Costs' },
  { id: 'documents', label: 'Documents' },
  { id: 'score', label: 'Why this score' },
  { id: 'sources', label: 'Sources & evidence' },
];

export function ResultDetail({ result }: { result: ProgramResult }) {
  const [tab, setTab] = useState<Tab>('requirements');

  return (
    <div className="detail" data-testid={`detail-${result.id}`}>
      <div className="tabs" role="tablist" aria-label={`${result.university} details`}>
        {TABS.map((t) => (
          <button
            key={t.id}
            role="tab"
            className="tab"
            aria-selected={tab === t.id}
            onClick={() => setTab(t.id)}
            data-testid={`tab-${t.id}`}
          >
            {t.label}
            {t.id === 'sources' && result.conflicts.length > 0 && (
              <span style={{ marginLeft: 6 }}><Chip tone="risk">{result.conflicts.length}</Chip></span>
            )}
          </button>
        ))}
      </div>

      {tab === 'requirements' && <Requirements result={result} />}
      {tab === 'funding' && <Funding result={result} />}
      {tab === 'costs' && <Costs result={result} />}
      {tab === 'documents' && <Documents result={result} />}
      {tab === 'score' && <Score result={result} />}
      {tab === 'sources' && <Sources result={result} />}
    </div>
  );
}

function Requirements({ result }: { result: ProgramResult }) {
  if (result.requirement_checks.length === 0) {
    return (
      <Notice kind="warn">
        <div>
          No published requirements could be read for this programme, so nothing has been
          compared against your profile. This is reported as unknown, not as a pass.
        </div>
      </Notice>
    );
  }
  return (
    <div className="stack stack--tight">
      {result.hard_filter_failures.length > 0 && (
        <Notice kind="risk">
          <div>
            <strong>Confirmed requirement not met:</strong> {result.hard_filter_failures.join(', ')}.
            This is drawn from an official page, so it is treated as a real barrier rather than a gap
            in our data.
          </div>
        </Notice>
      )}
      <dl className="kv">
        {result.requirement_checks.map((c, i) => (
          <div key={i} style={{ display: 'contents' }}>
            <dt>{c.requirement}</dt>
            <dd>
              <div className="row row--tight">
                <StatusChip status={c.status} tone={eligibilityTone[c.status]} />
                {c.published_value != null && (
                  <span className="num small">
                    published <strong>{formatValue(c.published_value)}</strong>
                  </span>
                )}
                {c.applicant_value != null && (
                  <span className="num small muted">you {formatValue(c.applicant_value)}</span>
                )}
              </div>
              <p className="xs muted" style={{ margin: '3px 0 0' }}>{c.explanation}</p>
            </dd>
          </div>
        ))}
      </dl>
      <div className="row" style={{ marginTop: 'var(--space-3)' }}>
        <span className="xs faint">
          Deadline: {result.admission_deadline ? date(result.admission_deadline) : 'not found'}
          {result.admission_deadline_timezone ? ` (${result.admission_deadline_timezone})` : ''}
        </span>
        {result.deadline_passed && <Chip tone="risk">deadline passed</Chip>}
      </div>
    </div>
  );
}

function Funding({ result }: { result: ProgramResult }) {
  if (result.scholarships.length === 0) {
    return (
      <Notice kind="warn">
        <div>
          No official scholarship page could be read for this programme. Funding is
          <strong> unknown</strong> — that is not the same as there being none.
        </div>
      </Notice>
    );
  }
  return (
    <div className="stack">
      {result.scholarships.map((s) => (
        <div key={s.id} className="panel panel--sunken" data-testid={`scholarship-${s.name}`}>
          <div className="row" style={{ justifyContent: 'space-between', marginBottom: 8 }}>
            <h3 style={{ fontSize: 'var(--text-base)' }}>{s.name}</h3>
            <StatusChip status={s.classification} tone={fundingClassTone[s.classification]} />
          </div>
          <p className="small muted">{s.classification_reason}</p>

          <dl className="kv" style={{ marginTop: 'var(--space-3)' }}>
            <dt>Value</dt>
            <dd className="num">
              {s.amount ? money(s.amount)
                : s.amount_is_percentage_of_tuition != null
                  ? `${s.amount_is_percentage_of_tuition}% of tuition`
                  : 'not published'}
            </dd>
            <dt>Open to you</dt>
            <dd>
              {s.citizenship_restrictions.length > 0 ? (
                <Chip tone="risk">restricted to {s.citizenship_restrictions.join(', ')}</Chip>
              ) : s.international_eligible === 'yes' ? (
                <Chip tone="ok">international students eligible</Chip>
              ) : s.international_eligible === 'no' ? (
                <Chip tone="risk">not open to international students</Chip>
              ) : (
                <Chip>eligibility not published</Chip>
              )}
            </dd>
            <dt>How to apply</dt>
            <dd>
              <Chip tone={s.application_mode === 'automatic' ? 'ok' : s.application_mode === 'nomination' ? 'warn' : 'info'}>
                {humanize(s.application_mode)}
              </Chip>
              {s.requires_extra_essays && <span className="xs muted"> · extra essays required</span>}
            </dd>
            <dt>Deadline</dt>
            <dd className="num">
              {s.deadline ? `${date(s.deadline)}${s.deadline_timezone ? ` (${s.deadline_timezone})` : ''}` : 'not found'}
            </dd>
            <dt>Renewal</dt>
            <dd>
              {s.renewable === null ? 'not published'
                : s.renewable
                  ? `Renewable${s.duration_years ? ` for up to ${s.duration_years} years` : ''}`
                  : 'One-time award'}
              {s.renewal_requirements.length > 0 && (
                <ul className="xs muted" style={{ margin: '4px 0 0', paddingLeft: '1.1rem' }}>
                  {s.renewal_requirements.map((r, i) => <li key={i}>{r}</li>)}
                </ul>
              )}
            </dd>
            <dt>Combines with others</dt>
            <dd>{s.stackable === 'unknown' ? 'not published' : s.stackable === 'yes' ? 'Yes' : 'No'}</dd>
            {s.coverage.length > 0 && (
              <>
                <dt>Covers</dt>
                <dd>
                  <div className="row row--tight">
                    {s.coverage.map((c) => (
                      <Chip key={c.category}
                            tone={c.covered === 'yes' ? 'ok' : c.covered === 'no' ? 'risk' : c.covered === 'partial' ? 'warn' : 'neutral'}>
                        {humanize(c.category)}: {c.covered}
                      </Chip>
                    ))}
                  </div>
                </dd>
              </>
            )}
            {s.published_count != null && (
              <>
                <dt>Awards offered</dt>
                <dd className="num">{s.published_count} (officially published)</dd>
              </>
            )}
          </dl>

          {s.eligibility_checks.length > 0 && (
            <div className="stack stack--tight" style={{ marginTop: 'var(--space-3)' }}>
              {s.eligibility_checks.map((c, i) => (
                <div key={i} className="row row--tight">
                  <StatusChip status={c.status} tone={eligibilityTone[c.status]} />
                  <span className="xs muted">{c.explanation}</span>
                </div>
              ))}
            </div>
          )}

          <div className="row row--tight" style={{ marginTop: 'var(--space-3)' }}>
            {s.source_urls.map((u) => <SourceLink key={u} url={u} />)}
          </div>
        </div>
      ))}
    </div>
  );
}

function Costs({ result }: { result: ProgramResult }) {
  const gap = result.funding_gap;
  const items = Object.entries(result.costs.items);

  return (
    <div className="stack">
      {items.length === 0 ? (
        <Notice kind="warn">
          <div>No official cost of attendance was found for this programme and intake.</div>
        </Notice>
      ) : (
        <dl className="kv">
          {items.map(([cat, m]) => (
            <div key={cat} style={{ display: 'contents' }}>
              <dt>{humanize(cat)}</dt>
              <dd className="num">{money(m ?? null)}</dd>
            </div>
          ))}
          {result.costs.total && (
            <>
              <dt><strong>Published total</strong></dt>
              <dd className="num"><strong>{money(result.costs.total)}</strong></dd>
            </>
          )}
        </dl>
      )}

      {gap && (
        <div className="panel panel--sunken">
          <h3 style={{ fontSize: 'var(--text-base)', marginBottom: 8 }}>Remaining annual cost</h3>
          {gap.computable && gap.gap ? (
            <>
              <p className="num" style={{ fontSize: 'var(--text-xl)', fontFamily: 'var(--font-display)', margin: 0 }}>
                {money(gap.gap)}
              </p>
              <p className="xs muted" style={{ marginTop: 4 }}>{gap.reason}</p>
              <dl className="kv" style={{ marginTop: 'var(--space-3)' }}>
                <dt>Cost of attendance</dt><dd className="num">{money(gap.total_cost)}</dd>
                <dt>Confirmed aid</dt><dd className="num">{money(gap.confirmed_aid)}</dd>
                {gap.stackable_aid && (<><dt>Stacked aid</dt><dd className="num">{money(gap.stackable_aid)}</dd></>)}
              </dl>
            </>
          ) : (
            <Notice kind="warn">
              <div>
                <strong>Not computed.</strong> {gap.reason}
              </div>
            </Notice>
          )}
          {gap.warnings.length > 0 && (
            <ul className="xs muted" style={{ marginTop: 'var(--space-3)', paddingLeft: '1.1rem' }}>
              {gap.warnings.map((w, i) => <li key={i}>{w}</li>)}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

function Documents({ result }: { result: ProgramResult }) {
  const c = result.checklist;
  if (!c) {
    return (
      <Notice kind="info">
        <div>
          Documents are collected only for programmes you approve — it is the expensive step, so it
          runs on your shortlist rather than on all {result.university ? '' : ''}candidates. Approve
          this row, then run “Collect documents”.
        </div>
      </Notice>
    );
  }
  return (
    <div className="stack stack--tight">
      <div className="row">
        <Chip tone={c.completeness === 'official' ? 'ok' : c.completeness === 'partial' ? 'warn' : 'risk'}>
          {c.completeness === 'official' ? 'read from official pages'
            : c.completeness === 'partial' ? 'partially read' : 'no official list found'}
        </Chip>
        <span className="xs faint">generated {dateTime(c.generated_at)}</span>
      </div>
      <ol className="stack stack--tight" style={{ paddingLeft: '1.1rem', margin: 0 }}>
        {c.ordered_steps.map((s, i) => <li key={i} className="small">{s.replace(/^\d+\.\s*/, '')}</li>)}
      </ol>
    </div>
  );
}

function Score({ result }: { result: ProgramResult }) {
  const s = result.preference_score;
  if (!s) return <p className="muted small">No score was computed for this row.</p>;
  return (
    <div className="stack stack--tight">
      <Notice kind="info"><div>{s.disclaimer}</div></Notice>
      <dl className="kv">
        {s.components.map((c, i) => (
          <div key={i} style={{ display: 'contents' }}>
            <dt>
              {c.name}
              {!c.data_present && <span className="xs faint"> · no data</span>}
            </dt>
            <dd>
              {c.weight > 0 && (
                <span className="num small">
                  {c.raw.toFixed(2)} × {c.weight.toFixed(1)} = <strong>{c.weighted.toFixed(2)}</strong>
                </span>
              )}
              <p className="xs muted" style={{ margin: '2px 0 0' }}>{c.explanation}</p>
            </dd>
          </div>
        ))}
      </dl>
      <div className="row" style={{ marginTop: 'var(--space-3)' }}>
        <span className="num small">
          Total <strong>{s.total.toFixed(2)}</strong> of {s.max_possible.toFixed(2)} possible
        </span>
        {s.missing_data_penalty > 0 && (
          <Chip tone="warn">
            −{Math.round(s.missing_data_penalty * 100)}% for {s.missing_fields.length} missing fields
          </Chip>
        )}
      </div>
    </div>
  );
}

function Sources({ result }: { result: ProgramResult }) {
  return (
    <div className="stack">
      {result.conflicts.length > 0 && (
        <div className="stack stack--tight">
          <h3 style={{ fontSize: 'var(--text-base)' }}>Sources that disagree</h3>
          {result.conflicts.map((c, i) => (
            <div key={i} className="notice notice--risk" style={{ flexDirection: 'column', alignItems: 'stretch' }}>
              <div><strong>{c.subject}</strong></div>
              <div className="xs" style={{ marginTop: 4 }}>
                {c.values.map((v, j) => (
                  <div key={j} className="mono">
                    {formatValue(v)} — {c.source_urls[j]}
                  </div>
                ))}
              </div>
              <div className="xs" style={{ marginTop: 6 }}>{c.resolution_rule}</div>
              <details style={{ marginTop: 6 }}>
                <summary className="xs" style={{ cursor: 'pointer' }}>
                  Question to send the admissions office
                </summary>
                <pre className="xs mono" style={{ whiteSpace: 'pre-wrap', marginTop: 6 }}>
                  {c.question_for_admissions}
                </pre>
              </details>
            </div>
          ))}
        </div>
      )}

      {result.unresolved.length > 0 && (
        <div className="stack stack--tight">
          <h3 style={{ fontSize: 'var(--text-base)' }}>Open questions</h3>
          {result.unresolved.map((q, i) => (
            <div key={i} className="gap-item gap-item--medium">
              <Chip tone={q.blocking ? 'risk' : 'warn'}>{q.blocking ? 'blocking' : 'open'}</Chip>
              <div>
                <div className="small"><strong>{q.question}</strong></div>
                <p className="xs muted" style={{ margin: '2px 0 0' }}>{q.why_it_matters}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="stack stack--tight">
        <div className="row" style={{ justifyContent: 'space-between' }}>
          <h3 style={{ fontSize: 'var(--text-base)' }}>Evidence ({result.claims.length} claims)</h3>
          <span className="xs faint">
            last verified {dateTime(result.last_verified)} ·{' '}
            {Math.round(result.verification_completeness * 100)}% of decision-grade fields verified
          </span>
        </div>
        <div className="stack stack--tight" style={{ maxHeight: '28rem', overflowY: 'auto' }}>
          {result.claims.map((c) => (
            <div
              key={c.id}
              className={`claim claim--${
                c.status === 'VERIFIED_CURRENT' ? 'verified'
                : c.status === 'POSSIBLY_STALE' ? 'stale'
                : c.status === 'CONFLICTING' ? 'conflict' : 'unverified'
              }`}
            >
              <div className="claim__head">
                <span className="claim__type">{c.claim_type}</span>
                <span className="claim__value">{formatValue(c.normalized_value)}</span>
                <StatusChip status={c.status} tone={claimStatusTone[c.status]} />
                <Chip mono>{c.source_specificity}</Chip>
                {c.is_stale && <Chip tone="warn">{c.age_days}d old</Chip>}
              </div>
              {c.original_text_excerpt && (
                <div className="claim__excerpt">“{c.original_text_excerpt}”</div>
              )}
              <div className="claim__src"><SourceLink url={c.source_url} /></div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function formatValue(v: unknown): string {
  if (v === null || v === undefined) return '—';
  if (typeof v === 'boolean') return v ? 'yes' : 'no';
  if (Array.isArray(v)) return v.map(formatValue).join(', ');
  if (typeof v === 'object') {
    const o = v as Record<string, unknown>;
    if ('amount' in o && 'currency' in o) return `${Number(o.amount).toLocaleString('en-US')} ${o.currency}`;
    return Object.entries(o).map(([k, val]) => `${k}: ${formatValue(val)}`).join(', ');
  }
  return String(v);
}
