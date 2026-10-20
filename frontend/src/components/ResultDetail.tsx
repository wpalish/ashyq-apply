/**
 * Screen 05 — University detail, rendered inline under its shortlist row.
 *
 * Tabbed rather than stacked, because a single row carries five different
 * kinds of information and putting them all on screen at once is what makes
 * these tables unreadable.
 */

import { useState } from 'react';
import { Deadline } from '@/components/Deadline';
import { Chip, Notice, SourceLink, StatusChip } from '@/components/primitives';
import {
  FIT_DISCLAIMER, bucketTone, claimStatusTone, claimValue, date, dateTime, documentRequirement,
  eligibilityTone, fundingClassTone, humanize, money, openQuestionCount, percent, ratio,
  type DocumentRequirement,
} from '@/lib/format';
import {
  localCaveat, localGapReason, localStaleChip, localStaleReason, localStep, localUnusedTuitionLines, localize,
} from '@/lib/messages';
import { rich, useTranslation } from '@/lib/useTranslation';
import type { ProgramResult, UnresolvedQuestion } from '@/types';

type Tab = 'requirements' | 'funding' | 'costs' | 'documents' | 'sources' | 'score';

const TABS: Tab[] = ['requirements', 'funding', 'costs', 'documents', 'score', 'sources'];

/**
 * `knowledgeMode` is the deployment's (`/api/capabilities`): in `kb` mode no
 * page is read during a run, so copy that says a page "could not be read"
 * would be false.
 */
export function ResultDetail({ result, knowledgeMode }: { result: ProgramResult; knowledgeMode?: string }) {
  const [tab, setTab] = useState<Tab>('requirements');
  const { t, tf, tn } = useTranslation();

  return (
    <div className="detail" data-testid={`detail-${result.id}`}>
      <header className="programme-hero">
        <div>
          <span className="home-eyebrow">{tf('detail.eyebrow', { country: result.country })}</span>
          <h2>{result.university}</h2>
          <p className="programme-hero__programme">{result.program}</p>
          <p className="programme-hero__place">{result.city}, {result.country}{result.degree ? ` · ${humanize(result.degree)}` : ''}</p>
          {result.program_url && <SourceLink url={result.program_url} />}
        </div>
        <div className="programme-hero__status">
          <span className="home-eyebrow">{t('detail.assessment')}</span>
          <StatusChip status={result.eligibility} tone={eligibilityTone[result.eligibility]} />
          <p>{t('detail.assessmentNote')}</p>
        </div>
      </header>
      <div className="programme-facts">
        <div><span>{t('col.funding')}</span><StatusChip status={result.best_funding_classification} tone={fundingClassTone[result.best_funding_classification]} /></div>
        <div><span>{t('col.remainingPerYear')}</span><strong>{result.funding_gap?.computable && result.funding_gap.gap ? money(result.funding_gap.gap) : t('results.notEnoughData')}</strong></div>
        <div><span>{t('col.deadline')}</span><strong><Deadline result={result} fallback={t('results.notConfirmed')} /></strong></div>
        <div><span>{t('detail.evidence')}</span><strong>{tn('results.conflictCount', result.conflicts.length)} · {tn('results.questionCount', openQuestionCount(result))}</strong></div>
      </div>
      <div className="tabs" role="tablist" aria-label={tf('detail.tabsAria', { university: result.university })}>
        {TABS.map((id) => (
          <button
            key={id}
            role="tab"
            className="tab"
            aria-selected={tab === id}
            onClick={() => setTab(id)}
            data-testid={`tab-${id}`}
          >
            {t(`detail.tab.${id}`)}
            {id === 'sources' && result.conflicts.length > 0 && (
              <span style={{ marginLeft: 6 }}><Chip tone="risk">{result.conflicts.length}</Chip></span>
            )}
          </button>
        ))}
      </div>

      {tab === 'requirements' && <Requirements result={result} knowledgeMode={knowledgeMode} />}
      {tab === 'funding' && <Funding result={result} knowledgeMode={knowledgeMode} />}
      {tab === 'costs' && <Costs result={result} />}
      {tab === 'documents' && <Documents result={result} knowledgeMode={knowledgeMode} />}
      {tab === 'score' && <Score result={result} />}
      {tab === 'sources' && <Sources result={result} />}
    </div>
  );
}

/** Open questions the knowledge base raises about entry requirements (kb mode). */
const KB_REQUIREMENT_TOPICS = new Set(['language requirement', 'grade requirement', 'entry requirements']);

function RequirementQuestions({ result, knowledgeMode }: { result: ProgramResult; knowledgeMode?: string }) {
  if (knowledgeMode !== 'kb') return null;
  const questions = result.unresolved.filter((q) => KB_REQUIREMENT_TOPICS.has(q.topic));
  if (questions.length === 0) return null;
  return (
    <div className="stack stack--tight" data-testid="requirement-questions">
      {questions.map((q, i) => (
        <div key={i}>
          <p className="small" style={{ margin: 0 }}><strong>{localize(q.question_message, q.question)}</strong></p>
          <p className="xs muted" style={{ margin: '2px 0 0' }}>{localize(q.why_message, q.why_it_matters)}</p>
        </div>
      ))}
    </div>
  );
}

function Requirements({ result, knowledgeMode }: { result: ProgramResult; knowledgeMode?: string }) {
  const { t, tf } = useTranslation();
  // A deadline whose year the page did not print is shown with its caveat.
  const deadlineClaim = result.claims.find(
    (c) => c.claim_type === 'admission_deadline'
      && result.admission_deadline_raw !== null
      && String(c.normalized_value) === result.admission_deadline_raw,
  );
  const deadlineCaveat = deadlineClaim ? localCaveat(deadlineClaim) : null;
  if (result.requirement_checks.length === 0) {
    return (
      <div className="stack stack--tight">
        <Notice kind="warn">
          <div>
            {knowledgeMode === 'kb' ? t('detail.noRequirementsKb') : t('detail.noRequirementsLive')}
            {' '}{t('detail.reportedUnknown')}
          </div>
        </Notice>
        <RequirementQuestions result={result} knowledgeMode={knowledgeMode} />
      </div>
    );
  }
  return (
    <div className="stack stack--tight">
      <RequirementQuestions result={result} knowledgeMode={knowledgeMode} />
      {result.hard_filter_failures.length > 0 && (
        <Notice kind="risk">
          <div>
            <strong>{t('detail.requirementNotMet')}</strong> {result.hard_filter_failures.join(', ')}.{' '}
            {t('detail.requirementNotMetNote')}
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
                    {t('detail.published')} <strong>{formatValue(c.published_value)}</strong>
                  </span>
                )}
                {c.applicant_value != null && (
                  <span className="num small muted">{t('detail.you')} {formatValue(c.applicant_value)}</span>
                )}
              </div>
              <p className="xs muted" style={{ margin: '3px 0 0' }}>{c.explanation}</p>
              {c.published_scope && (
                <p className="xs faint" style={{ margin: '2px 0 0' }}>{c.published_scope}</p>
              )}
            </dd>
          </div>
        ))}
      </dl>
      <div className="row" style={{ marginTop: 'var(--space-3)' }}>
        <span className="xs faint">
          {tf('detail.deadlineLine', { date: result.admission_deadline ? date(result.admission_deadline) : t('results.notFound') })}
          {result.admission_deadline_timezone ? ` (${result.admission_deadline_timezone})` : ''}
        </span>
        {deadlineCaveat && (
          <span className="xs muted" data-testid="deadline-caveat">
            {tf('results.caveat', { caveat: deadlineCaveat })}
          </span>
        )}
        {result.deadline_passed && <Chip tone="risk">{t('detail.deadlinePassed')}</Chip>}
        {result.previous_cycle_deadline && (
          <span className="xs muted"> {tf('detail.previousCycle', { date: date(result.previous_cycle_deadline) })}</span>
        )}
      </div>
    </div>
  );
}

const NO_INSTITUTIONAL_AWARD = 'No institutional scholarship';

function Funding({ result, knowledgeMode }: { result: ProgramResult; knowledgeMode?: string }) {
  const { t, tf, tOr } = useTranslation();
  if (result.scholarships.length === 0) {
    // A verified "none offered" (kb mode) is an outcome, said as the backend wrote it.
    const noneAt = result.funding_gap?.warnings.findIndex((w) => w.startsWith(NO_INSTITUTIONAL_AWARD)) ?? -1;
    const none = noneAt >= 0 && result.funding_gap
      ? localize(result.funding_gap.warning_messages?.[noneAt], result.funding_gap.warnings[noneAt] ?? '')
      : undefined;
    const questions = knowledgeMode === 'kb' ? result.unresolved.filter((q) => q.topic === 'funding') : [];
    return (
      <div className="stack stack--tight">
        <Notice kind="warn">
          <div>
            {none ? none
              : knowledgeMode === 'kb' ? (
                rich(t('detail.noScholarshipKb'), { unknown: <strong>{t('detail.unknown')}</strong> })
              ) : (
                rich(t('detail.noScholarship'), { unknown: <strong>{t('detail.unknown')}</strong> })
              )}
          </div>
        </Notice>
        {questions.map((q, i) => (
          <p key={i} className="xs muted" style={{ margin: 0 }}>
            <strong>{t('detail.openQuestion')}</strong> {localize(q.question_message, q.question)}
          </p>
        ))}
      </div>
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
            <dt>{t('detail.value')}</dt>
            <dd className="num">
              {s.amount ? money(s.amount)
                : s.amount_is_percentage_of_tuition != null
                  ? tf('detail.percentOfTuition', { pct: s.amount_is_percentage_of_tuition })
                  : t('results.notPublished')}
            </dd>
            <dt>{t('detail.openToYou')}</dt>
            <dd>
              {s.citizenship_restrictions.length > 0 ? (
                <Chip tone="risk">{tf('detail.restrictedTo', { list: s.citizenship_restrictions.join(', ') })}</Chip>
              ) : s.international_eligible === 'yes' ? (
                <Chip tone="ok">{t('detail.internationalEligible')}</Chip>
              ) : s.international_eligible === 'no' ? (
                <Chip tone="risk">{t('detail.notInternational')}</Chip>
              ) : (
                <Chip>{t('detail.eligibilityNotPublished')}</Chip>
              )}
            </dd>
            <dt>{t('detail.howToApply')}</dt>
            <dd>
              <Chip tone={s.application_mode === 'automatic' ? 'ok' : s.application_mode === 'nomination' ? 'warn' : 'info'}>
                {tOr(`apply.${s.application_mode}`, humanize(s.application_mode))}
              </Chip>
              {s.requires_extra_essays && <span className="xs muted">{t('detail.extraEssays')}</span>}
              {s.offer_required === 'yes' && (
                <p className="xs muted" style={{ margin: '3px 0 0' }}>
                  {t('detail.offerRequired')}
                </p>
              )}
              {s.offer_required === 'no' && (
                <p className="xs muted" style={{ margin: '3px 0 0' }}>
                  {t('detail.offerNotRequired')}
                </p>
              )}
              {s.financial_need_required === 'yes' && (
                <p className="xs muted" style={{ margin: '3px 0 0' }}>
                  {t('detail.needBased')}
                </p>
              )}
            </dd>
            <dt>{t('col.deadline')}</dt>
            <dd className="num">
              {s.deadline ? `${date(s.deadline)}${s.deadline_timezone ? ` (${s.deadline_timezone})` : ''}` : t('results.notFound')}
            </dd>
            <dt>{t('detail.renewal')}</dt>
            <dd>
              {s.renewable === null ? t('results.notPublished')
                : s.renewable
                  ? (s.duration_years ? tf('detail.renewableYears', { n: s.duration_years }) : t('detail.renewable'))
                  : t('detail.oneTime')}
              {s.renewal_requirements.length > 0 && (
                <ul className="xs muted" style={{ margin: '4px 0 0', paddingLeft: '1.1rem' }}>
                  {s.renewal_requirements.map((r, i) => <li key={i}>{r}</li>)}
                </ul>
              )}
            </dd>
            <dt>{t('detail.stackable')}</dt>
            <dd>{s.stackable === 'unknown' ? t('results.notPublished') : s.stackable === 'yes' ? t('results.yes') : t('results.no')}</dd>
            {s.coverage.length > 0 && (
              <>
                <dt>{t('detail.covers')}</dt>
                <dd>
                  <div className="row row--tight">
                    {s.coverage.map((c) => (
                      <Chip key={c.category}
                            tone={c.covered === 'yes' ? 'ok' : c.covered === 'no' ? 'risk' : c.covered === 'partial' ? 'warn' : 'neutral'}>
                        {tOr(`cost.${c.category}`, humanize(c.category))}: {tOr(`coverage.${c.covered}`, c.covered)}
                      </Chip>
                    ))}
                  </div>
                </dd>
              </>
            )}
            {s.published_count != null && (
              <>
                <dt>{t('detail.awardsOffered')}</dt>
                <dd className="num">{tf('detail.officiallyPublished', { n: s.published_count })}</dd>
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
  const { t, tf, tOr } = useTranslation();
  const gap = result.funding_gap;
  const items = Object.entries(result.costs.items);
  const warnings = gap
    ? gap.warnings.map((w, i) => localize(gap.warning_messages?.[i], w))
    : [];
  // A verified fee for another year (or not per year) was found; it is just not this intake's cost.
  const unused = items.length === 0 ? localUnusedTuitionLines(result.claims) : [];
  const reason = gap ? localGapReason(gap, result.claims) : '';
  // The table took a current fee the page printed no year for: never shown as fully verified.
  const tuition = result.costs.items.tuition;
  const feeCaveat = tuition
    ? result.claims
      .filter((c) => c.claim_type === 'tuition' && c.status === 'VERIFIED_CURRENT' && c.source_url === tuition.source_url)
      .map((c) => localCaveat(c))
      .find((c) => c !== null) ?? null
    : null;

  return (
    <div className="stack">
      {items.length === 0 ? (
        <Notice kind="warn">
          {unused.length > 0 ? (
            <div data-testid="unused-tuition">
              {t('detail.unusedTuition')}
              <ul style={{ margin: '4px 0 0', paddingLeft: '1.1rem' }}>
                {unused.map((line) => <li key={line} className="small">{line}</li>)}
              </ul>
            </div>
          ) : (
            <div>{t('detail.noCost')}</div>
          )}
        </Notice>
      ) : (
        <dl className="kv">
          {items.map(([cat, m]) => (
            <div key={cat} style={{ display: 'contents' }}>
              <dt>{tOr(`cost.${cat}`, humanize(cat))}</dt>
              <dd className="num">{money(m ?? null)}</dd>
            </div>
          ))}
          {result.costs.total && (
            <>
              <dt><strong>{t('detail.publishedTotal')}</strong></dt>
              <dd className="num"><strong>{money(result.costs.total)}</strong></dd>
            </>
          )}
        </dl>
      )}
      {feeCaveat && (
        <p className="xs claim__stale-reason" style={{ margin: 0 }} data-testid="cost-caveat">
          {tf('detail.costCaveat', { caveat: feeCaveat })}
        </p>
      )}

      {gap && gap.cost_basis === 'itemised_partial' && gap.total_cost ? (
        <div className="panel panel--sunken">
          <h3 style={{ fontSize: 'var(--text-base)', marginBottom: 8 }}>{t('detail.knownSoFar')}</h3>
          <p className="num" style={{ fontSize: 'var(--text-xl)', fontFamily: 'var(--font-display)', margin: 0 }}>
            ≥ {money(gap.total_cost)}
          </p>
          <p className="xs muted" style={{ marginTop: 4 }}>
            {t('detail.lowerBound')}
          </p>
          {gap.missing_categories.length > 0 && (
            <div className="row row--tight" style={{ marginTop: 'var(--space-3)' }}>
              {gap.missing_categories.map((c) => (
                <Chip key={c} tone="warn">{tf('detail.notItemised', { category: tOr(`cost.${c}`, humanize(c)) })}</Chip>
              ))}
            </div>
          )}
          {warnings.length > 0 && (
            <ul className="xs muted" style={{ marginTop: 'var(--space-3)', paddingLeft: '1.1rem' }}>
              {warnings.map((w, i) => <li key={i}>{w}</li>)}
            </ul>
          )}
        </div>
      ) : gap && (
        <div className="panel panel--sunken">
          <h3 style={{ fontSize: 'var(--text-base)', marginBottom: 8 }}>{t('detail.remainingAnnual')}</h3>
          {gap.computable && gap.gap ? (
            <>
              <p className="num" style={{ fontSize: 'var(--text-xl)', fontFamily: 'var(--font-display)', margin: 0 }}>
                {money(gap.gap)}
              </p>
              <p className="xs muted" style={{ marginTop: 4 }}>{reason}</p>
              <dl className="kv" style={{ marginTop: 'var(--space-3)' }}>
                <dt>{t('detail.costOfAttendance')}</dt><dd className="num">{money(gap.total_cost)}</dd>
                <dt>{t('detail.confirmedAid')}</dt><dd className="num">{money(gap.confirmed_aid)}</dd>
                {gap.stackable_aid && (<><dt>{t('detail.stackedAid')}</dt><dd className="num">{money(gap.stackable_aid)}</dd></>)}
              </dl>
            </>
          ) : (
            <Notice kind="warn">
              <div>
                <strong>{t('detail.notComputed')}</strong> {reason}
              </div>
            </Notice>
          )}
          {warnings.length > 0 && (
            <ul className="xs muted" style={{ marginTop: 'var(--space-3)', paddingLeft: '1.1rem' }}>
              {warnings.map((w, i) => <li key={i}>{w}</li>)}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

const requirementTone: Record<DocumentRequirement, 'ok' | 'neutral' | 'warn'> = {
  required: 'ok',
  optional: 'neutral',
  conditional: 'warn',
};

function DocumentQuestions({ questions }: { questions: UnresolvedQuestion[] }) {
  if (questions.length === 0) return null;
  return (
    <div className="stack stack--tight" data-testid="document-questions">
      {questions.map((q, i) => (
        <Notice key={i} kind={q.blocking ? 'risk' : 'warn'}>
          <div>
            <strong>{localize(q.question_message, q.question)}</strong>
            <div className="xs" style={{ marginTop: 3 }}>{localize(q.why_message, q.why_it_matters)}</div>
          </div>
        </Notice>
      ))}
    </div>
  );
}

/**
 * The approved row's checklist: every item with who acts on it, whether the
 * page says it is required, optional or conditional (and on what), why a
 * stale item is not current, and its official source; then the questions the
 * checklist leaves open. A row with no checklist shows why there is none when
 * the document stage said so, instead of asking to approve it again.
 */
function Documents({ result, knowledgeMode }: { result: ProgramResult; knowledgeMode?: string }) {
  const { t, tf } = useTranslation();
  const c = result.checklist;
  if (!c) {
    const asked = result.unresolved.filter((q) => DOCUMENT_TOPICS.has(q.topic));
    if (asked.length > 0) return <DocumentQuestions questions={asked} />;
    return (
      <Notice kind="info">
        <div>{t('detail.documentsLater')}</div>
      </Notice>
    );
  }
  const items = [...c.admission_documents, ...c.scholarship_documents];
  return (
    <div className="stack stack--tight">
      <div className="row">
        <Chip tone={c.completeness === 'official' ? 'ok' : c.completeness === 'partial' ? 'warn' : 'risk'}>
          {/* kb mode reads no page: "partially read" would be false (KB v10 smoke D3). */}
          {t(knowledgeMode === 'kb' ? `detail.docs.kb.${c.completeness}` : `detail.docs.${c.completeness}`)}
        </Chip>
        <span className="xs faint">{tf('detail.generated', { when: dateTime(c.generated_at) })}</span>
      </div>
      <ul className="stack stack--tight" style={{ listStyle: 'none', padding: 0, margin: 0 }}>
        {items.map((d, i) => {
          const { requirement, condition, claim } = documentRequirement(d, result.claims);
          const stale = claim?.is_stale ? localStaleReason(claim) : null;
          return (
            <li key={`${d.name}-${i}`} className="small" data-testid="document-item">
              <div className="row row--tight">
                <strong>{d.name}</strong>
                <Chip tone={requirementTone[requirement]}>{t(`detail.docs.${requirement}`)}</Chip>
                <span className="xs muted">{t(`detail.docs.owner.${d.owner}`)}</span>
                {claim?.is_stale && <Chip tone="warn">{localStaleChip(claim.age_days, stale !== null)}</Chip>}
              </div>
              {condition && (
                <div className="xs muted">{tf('detail.docs.condition', { condition: condition.replace(/\.$/, '') })}</div>
              )}
              {stale && <div className="xs claim__stale-reason">{tf('results.notCurrent', { reason: stale })}</div>}
              {d.source_url && <SourceLink url={d.source_url} />}
            </li>
          );
        })}
      </ul>
      {c.ordered_steps.length > 0 && (
        <>
          <p className="xs faint" style={{ margin: 0 }}>{t('detail.docs.order')}</p>
          <ol className="stack stack--tight" style={{ paddingLeft: '1.1rem', margin: 0 }}>
            {c.ordered_steps.map((s, i) => <li key={i} className="small">{localStep(s.replace(/^\d+\.\s*/, ''))}</li>)}
          </ol>
        </>
      )}
      <DocumentQuestions questions={c.unresolved} />
    </div>
  );
}

/** The topics the document stage asks under ("documents") and the checklist's own. */
const DOCUMENT_TOPICS = new Set(['documents', 'required documents']);

/**
 * One line per axis: what it scored, what it weighed, and why.
 *
 * An axis with no value says which kind of nothing it is — unverified, or a
 * question the applicant did not ask — because those are different answers and
 * only one of them is a gap worth chasing.
 */
function Axes({ result }: { result: ProgramResult }) {
  const { t, tOr } = useTranslation();
  const r = result.ranking;
  if (!r) return null;
  return (
    <div className="stack stack--tight">
      <Notice kind="info"><div>{tOr('results.fitDisclaimer', r.disclaimer || FIT_DISCLAIMER)}</div></Notice>
      <div className="row">
        <span className="num small">{t('col.match')} <strong>{ratio(r.fit)}</strong></span>
        <span className="num small">{t('col.confirmed')} <strong>{percent(r.coverage)}</strong></span>
        <Chip tone={bucketTone[r.bucket]}>{tOr(`status.${r.bucket}`, humanize(r.bucket))}</Chip>
        <span className="xs muted">{r.bucket_reason}</span>
      </div>
      {r.knocked_out_by.length > 0 && (
        <Notice kind="risk">
          <div>
            <strong>{t('detail.listedNotRanked')}</strong>
            <ul style={{ margin: '4px 0 0', paddingLeft: '1.1rem' }}>
              {r.knocked_out_by.map((reason) => <li key={reason} className="small">{reason}</li>)}
            </ul>
          </div>
        </Notice>
      )}
      <dl className="kv">
        {r.axes.map((a) => (
          <div key={a.axis} style={{ display: 'contents' }}>
            <dt>
              {tOr(`axis.${a.axis}`, humanize(a.axis))}
              {a.state === 'unknown' && <span className="xs faint">{t('detail.notVerified')}</span>}
              {a.state === 'not_applicable' && <span className="xs faint">{t('detail.didNotAsk')}</span>}
            </dt>
            <dd>
              <span className="num small">
                {ratio(a.value)} {t('detail.weight')} {a.weight.toFixed(3)}
              </span>
              <p className="xs muted" style={{ margin: '2px 0 0' }}>{a.reason}</p>
            </dd>
          </div>
        ))}
      </dl>
      <p className="xs faint">
        {rich(t('detail.axesFootnote'), { confirmed: <em>{t('col.confirmed')}</em> })}
      </p>
    </div>
  );
}

function Score({ result }: { result: ProgramResult }) {
  const { t, tf } = useTranslation();
  const s = result.preference_score;
  if (result.ranking) return <Axes result={result} />;
  if (!s) return <p className="muted small">{t('detail.noScore')}</p>;
  return (
    <div className="stack stack--tight">
      <Notice kind="info"><div>{s.disclaimer}</div></Notice>
      <dl className="kv">
        {s.components.map((c, i) => (
          <div key={i} style={{ display: 'contents' }}>
            <dt>
              {c.name}
              {!c.data_present && <span className="xs faint">{t('detail.noData')}</span>}
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
          {rich(tf('detail.total', { max: s.max_possible.toFixed(2) }), { total: <strong>{s.total.toFixed(2)}</strong> })}
        </span>
        {s.missing_data_penalty > 0 && (
          <Chip tone="warn">
            {tf('detail.missingPenalty', { pct: Math.round(s.missing_data_penalty * 100), n: s.missing_fields.length })}
          </Chip>
        )}
      </div>
    </div>
  );
}

function Sources({ result }: { result: ProgramResult }) {
  const { t, tf } = useTranslation();
  return (
    <div className="stack">
      {result.conflicts.length > 0 && (
        <div className="stack stack--tight">
          <h3 style={{ fontSize: 'var(--text-base)' }}>{t('detail.disagree')}</h3>
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
                  {t('detail.askAdmissions')}
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
          <h3 style={{ fontSize: 'var(--text-base)' }}>{t('detail.openQuestions')}</h3>
          {result.unresolved.map((q, i) => (
            <div key={i} className="gap-item gap-item--medium">
              <Chip tone={q.blocking ? 'risk' : 'warn'}>{q.blocking ? t('results.blocking') : t('results.open')}</Chip>
              <div>
                <div className="small"><strong>{localize(q.question_message, q.question)}</strong></div>
                <p className="xs muted" style={{ margin: '2px 0 0' }}>{localize(q.why_message, q.why_it_matters)}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="stack stack--tight">
        <div className="row" style={{ justifyContent: 'space-between' }}>
          <h3 style={{ fontSize: 'var(--text-base)' }}>{tf('detail.evidenceCount', { n: result.claims.length })}</h3>
          <span className="xs faint">
            {tf('detail.lastVerified', {
              when: dateTime(result.last_verified),
              pct: Math.round(result.verification_completeness * 100),
            })}
          </span>
        </div>
        <div className="stack stack--tight" style={{ maxHeight: '28rem', overflowY: 'auto' }}>
          {result.claims.map((c) => {
            const caveat = localCaveat(c);
            // Current, but the page did not print the year: never "Verified".
            const caveated = caveat !== null && c.status === 'VERIFIED_CURRENT';
            return (
            <div
              key={c.id}
              className={`claim claim--${
                caveated ? 'caveat'
                : c.status === 'VERIFIED_CURRENT' ? 'verified'
                : c.status === 'POSSIBLY_STALE' ? 'stale'
                : c.status === 'CONFLICTING' ? 'conflict' : 'unverified'
              }`}
            >
              <div className="claim__head">
                <span className="claim__type">{c.claim_type}</span>
                <span className="claim__value">{formatValue(c.normalized_value)}</span>
                {caveated
                  ? <Chip tone="warn">{t('results.currentWithCaveat')}</Chip>
                  : <StatusChip status={c.status} tone={claimStatusTone[c.status]} />}
                <Chip mono>{c.source_specificity}</Chip>
                {c.is_stale && <Chip tone="warn">{localStaleChip(c.age_days, localStaleReason(c) !== null)}</Chip>}
              </div>
              {c.is_stale && localStaleReason(c) && (
                <div className="xs claim__stale-reason">{tf('results.notCurrent', { reason: localStaleReason(c) ?? '' })}</div>
              )}
              {caveat && (
                <div className="xs claim__stale-reason" data-testid="claim-caveat">{tf('results.caveat', { caveat })}</div>
              )}
              {c.original_text_excerpt && (
                <div className="claim__excerpt">“{c.original_text_excerpt}”</div>
              )}
              <div className="claim__src"><SourceLink url={c.source_url} /></div>
            </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

const formatValue = claimValue;
