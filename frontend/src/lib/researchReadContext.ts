import type { ResearchInputStatusRead, ResearchProfileSection, ResultFreshnessRead } from '@/types';
const object = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null && !Array.isArray(v);
const fields = (v: Record<string, unknown>, names: string[]) => Object.keys(v).length === names.length && names.every(name => Object.hasOwn(v, name));
const instant = (v: unknown) => typeof v === 'string' && /T.*(?:Z|[+-]\d{2}:\d{2})$/.test(v) && !Number.isNaN(Date.parse(v));
const sections: ResearchProfileSection[] = ['context', 'academics', 'activities', 'achievements', 'preferences', 'funding', 'weights', 'weights_override'];
export function isResearchInputStatus(v: unknown): v is ResearchInputStatusRead {
  return object(v) && fields(v, ['schema_version', 'state', 'changed_sections', 'observed_at', 'applicability']) && v.schema_version === 'research-input-status-v1'
    && ['unknown', 'pending', 'current', 'changed', 'mixed'].some(value => value === v.state) && v.applicability === 'not_assessed' && instant(v.observed_at)
    && Array.isArray(v.changed_sections) && v.changed_sections.length <= 8 && new Set(v.changed_sections).size === v.changed_sections.length
    && v.changed_sections.every(value => sections.some(section => section === value));
}
export function isResultFreshness(v: unknown): v is ResultFreshnessRead {
  return object(v) && fields(v, ['schema_version', 'observed_at', 'evidence', 'stale_claim_count', 'assessment']) && v.schema_version === 'result-freshness-read-v1'
    && instant(v.observed_at) && ['observed', 'not_available'].some(value => value === v.evidence) && v.assessment === 'stored_evaluation'
    && (v.stale_claim_count === null || (typeof v.stale_claim_count === 'number' && Number.isSafeInteger(v.stale_claim_count) && v.stale_claim_count >= 0))
    && (v.evidence !== 'not_available' || v.stale_claim_count === null);
}
