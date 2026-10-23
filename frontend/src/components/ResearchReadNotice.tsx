import { Notice } from './primitives';
import { useResearchInputRead } from '@/lib/useResearchInputRead';
import { useStore } from '@/lib/store';
import { useTranslation } from '@/lib/useTranslation';
import { isResultFreshness } from '@/lib/researchReadContext';
import { dateTime } from '@/lib/format';
import type { ResearchProfileSection } from '@/types';
import type { MessageKey } from '@/lib/i18n';
const sectionLabels: Record<ResearchProfileSection, MessageKey> = { context: 'inputs.context', academics: 'inputs.academics',
  activities: 'inputs.activities', achievements: 'inputs.achievements', preferences: 'inputs.preferences', funding: 'inputs.funding', weights: 'inputs.weights', weights_override: 'inputs.weights' };
export function ResearchReadNotice() {
  const read = useResearchInputRead(); const { run, results, savedProfile, currentAdmissionsCase } = useStore(); const { t } = useTranslation();
  const live = currentAdmissionsCase();
  if (!run || !savedProfile || run.profile_id !== savedProfile.id || live.profile_id !== savedProfile.id || live.scope === null) return null;
  const status = read.status; const changed = status?.state === 'changed' || status?.state === 'mixed';
  const ownedResults = run.profile_id === live.profile_id ? results.filter(result => result.run_id === run.id) : [];
  const aged = ownedResults.some(result => isResultFreshness(result.read_freshness) && result.read_freshness.evidence === 'observed' && (result.read_freshness.stale_claim_count ?? 0) > 0);
  return <div className="stack" data-testid="research-read-notice">
    {(changed || read.error || (read.applicable && (!status || status.state === 'unknown' || status.state === 'pending'))) && <Notice kind="warn"><div className="stack stack--tight">
      <strong>{t(status?.state === 'mixed' ? 'inputs.mixed' : changed ? 'inputs.changed' : 'inputs.unknown')}</strong>
      {status && status.changed_sections.length > 0 && <p className="small">{t('inputs.sections')}: {status.changed_sections.map(section => t(sectionLabels[section])).join(', ')}</p>}
      <p className="small">{t('inputs.hint')}</p>{status && <p className="xs muted">{t('inputs.observed')}: {dateTime(status.observed_at)}</p>}
      {read.error && <p className="small">{read.error} {status && t('inputs.lastConfirmed')}</p>}
      <button type="button" className="btn btn--sm" disabled={read.loading} onClick={() => void read.refresh()}>{t('inputs.refresh')}</button>
    </div></Notice>}
    {ownedResults.length > 0 && <Notice kind={aged ? 'warn' : 'info'}><div>
      <strong>{t('inputs.storedAssessment')}</strong> <span className="small">{t(aged ? 'inputs.aged' : 'inputs.assessmentHint')}</span>
    </div></Notice>}
  </div>;
}
