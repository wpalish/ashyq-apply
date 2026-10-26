/**
 * Screen 06 — Funding comparison.
 *
 * One bar per programme showing covered versus remaining cost. A programme
 * whose figures cannot be compared gets a hatched bar rather than a full one,
 * so "we don't know" never looks like "fully covered".
 */

import { useMemo, useState } from 'react';
import { Chip, Empty, Notice, Panel, StatusChip } from '@/components/primitives';
import { fundingClassTone, money } from '@/lib/format';
import { localize } from '@/lib/messages';
import { useStore } from '@/lib/store';
import { rich, useTranslation } from '@/lib/useTranslation';

export function FundingScreen() {
  const { results, capabilities } = useStore();
  const [onlyFunded, setOnlyFunded] = useState(false);
  const { t, tf } = useTranslation();

  const rows = useMemo(() => {
    const list = results.filter(
      (r) => !onlyFunded || ['FULL_RIDE_CONFIRMED', 'FULL_TUITION', 'LARGE_GRANT'].includes(r.best_funding_classification),
    );
    return [...list].sort((a, b) => {
      const ga = a.funding_gap?.computable && a.funding_gap.gap ? a.funding_gap.gap.amount : Number.MAX_SAFE_INTEGER;
      const gb = b.funding_gap?.computable && b.funding_gap.gap ? b.funding_gap.gap.amount : Number.MAX_SAFE_INTEGER;
      return ga - gb;
    });
  }, [results, onlyFunded]);

  if (results.length === 0) return <Empty title={t('results.empty.title')}>{t('results.empty.runFirst')}</Empty>;

  const maxCost = Math.max(
    1,
    ...results.map((r) => r.funding_gap?.total_cost?.amount ?? 0),
  );

  return (
    <>
      <div className="screen__head">
        <p className="screen__eyebrow">{t('funding.eyebrow')}</p>
        <h1 className="screen__title">{t('funding.title')}</h1>
        <p className="screen__lede">{t('funding.lede')}</p>
      </div>

      <div className="stack stack--loose">
        {capabilities?.currency.stale_warning && (
          <Notice kind="warn">
            <div data-testid="stale-rates">
              {localize(capabilities.currency.stale_warning_message, capabilities.currency.stale_warning)}
            </div>
          </Notice>
        )}
        <div className="row" style={{ justifyContent: 'space-between' }}>
          <label className="row row--tight small">
            <input type="checkbox" checked={onlyFunded} onChange={(e) => setOnlyFunded(e.target.checked)} />
            {t('funding.onlyFunded')}
          </label>
          <div className="fund-legend">
            <span><i style={{ background: 'var(--ok)' }} /> {t('funding.legendCovered')}</span>
            <span><i style={{ background: 'var(--risk)' }} /> {t('funding.legendPay')}</span>
            <span><i style={{ background: 'var(--unknown-border)' }} /> {t('results.notComparable')}</span>
          </div>
        </div>

        <Panel>
          {rows.map((r) => {
            const g = r.funding_gap;
            const cost = g?.total_cost?.amount ?? 0;
            const aid = g?.confirmed_aid?.amount ?? 0;
            const computable = Boolean(g?.computable && g.gap);
            const widthPct = cost > 0 ? (cost / maxCost) * 100 : 100;
            const coveredPct = cost > 0 ? Math.min(100, (aid / cost) * 100) : 0;

            return (
              <div className="fund-row" key={r.id} data-testid={`fund-${r.id}`}>
                <div>
                  <div className="small" style={{ fontWeight: 600 }}>{r.university}</div>
                  <div className="xs muted">{r.city}, {r.country}</div>
                  <div style={{ marginTop: 4 }}>
                    <StatusChip
                      status={r.best_funding_classification}
                      tone={fundingClassTone[r.best_funding_classification]}
                    />
                  </div>
                </div>
                <div>
                  <div className="fund-bar" style={{ width: `${Math.max(12, widthPct)}%` }}
                       role="img"
                       aria-label={
                         computable
                           ? tf('funding.barAria', { pct: Math.round(coveredPct), gap: money(g!.gap) })
                           : t('results.notComparable')
                       }>
                    {computable ? (
                      <>
                        <div className="fund-bar__covered" style={{ width: `${coveredPct}%` }} />
                        <div className="fund-bar__gap" style={{ width: `${100 - coveredPct}%` }} />
                      </>
                    ) : (
                      <div className="fund-bar__unknown" />
                    )}
                  </div>
                  <div className="xs muted" style={{ marginTop: 4 }}>
                    {computable
                      ? tf('funding.costAid', { cost: money(g!.total_cost), aid: money(g!.confirmed_aid) })
                      : (g ? localize(g.reason_message, g.reason) : t('funding.noCostInfo'))}
                  </div>
                </div>
                <div className="num" style={{ textAlign: 'right', minWidth: '9rem' }}>
                  {computable ? (
                    <strong>{money(g!.gap)}</strong>
                  ) : (
                    <Chip tone="neutral">{t('results.notComputable')}</Chip>
                  )}
                  {g && (g.year_mismatch || g.category_mismatch) && (
                    <div style={{ marginTop: 4 }}>
                      <Chip tone="warn">{g.year_mismatch ? t('funding.yearMismatch') : t('funding.categoryMismatch')}</Chip>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </Panel>

        <Notice kind="info">
          <div>
            {rich(t('funding.fullRideNote'), { label: <strong>FULL_RIDE_CONFIRMED</strong> })}
          </div>
        </Notice>
      </div>
    </>
  );
}
