from pathlib import Path
import json,hashlib
s=Path(__file__).resolve().parent;b=s.parents[1];r=b/'work/unimatch-calendar-materials';out=s/'inputs6b-proposal';out.mkdir(exist_ok=False)
paths=['frontend/src/types.ts','frontend/src/lib/researchReadContext.ts','frontend/src/lib/useResearchInputRead.ts','frontend/src/lib/useResearchInputRead.test.tsx','frontend/src/components/ResearchReadNotice.tsx','frontend/src/components/ResearchReadNotice.test.tsx','frontend/src/App.tsx','frontend/src/lib/i18n.ts'];rows={};h=lambda raw:hashlib.sha256(raw).hexdigest()
for p in paths:
 f=r/p;raw=f.read_bytes() if f.exists() else None;rows[p]=h(raw) if raw is not None else None
 if raw is not None:q=s/'inputs6b-preimages'/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(raw)
(s/'INPUTS_6B_PREPARATION.json').write_text(json.dumps({'status':'EXTERNAL_ONLY_NOT_GRANTED_NOT_APPLIED','baseline':'ab8e3d4e','paths':rows,'scope':'Typed owned read context, common historical assessment/source-age and named profile-section notice; separate read of existing GET run on saved profile object/case generation/run ID change with rendered/synchronous/serial fence. No local profile hashing/fake server status, no Store data overwrite/auto re-run/rerank/network provider. Real native full6a1 currently frozen.'},indent=2)+'\n')
def put(p,t):q=out/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(t)
p='frontend/src/types.ts';t=(r/p).read_text();marker='export interface ProgramResult {';assert marker in t
new='''export type ResearchProfileSection = 'context' | 'academics' | 'activities' | 'achievements' | 'preferences' | 'funding' | 'weights' | 'weights_override';
export interface ResearchInputStatusRead {
  schema_version: 'research-input-status-v1'; state: 'unknown' | 'pending' | 'current' | 'changed' | 'mixed';
  changed_sections: ResearchProfileSection[]; observed_at: string; applicability: 'not_assessed';
}
export interface ResultFreshnessRead {
  schema_version: 'result-freshness-read-v1'; observed_at: string; evidence: 'observed' | 'not_available';
  stale_claim_count: number | null; assessment: 'stored_evaluation';
}
''';t=t.replace(marker,new+marker+'\n  read_freshness?: ResultFreshnessRead;',1).replace('export interface RunView {','export interface RunView {\n  profile_input_status?: ResearchInputStatusRead;',1);put(p,t)
put('frontend/src/lib/researchReadContext.ts','''import type { ResearchInputStatusRead, ResearchProfileSection, ResultFreshnessRead } from '@/types';
const object = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null && !Array.isArray(v);
const fields = (v: Record<string, unknown>, names: string[]) => Object.keys(v).length === names.length && names.every(name => Object.hasOwn(v, name));
const instant = (v: unknown) => typeof v === 'string' && /T.*(?:Z|[+-]\\d{2}:\\d{2})$/.test(v) && !Number.isNaN(Date.parse(v));
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
''')
put('frontend/src/lib/useResearchInputRead.ts','''import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '@/api/client';
import { useStore } from './store';
import { isResearchInputStatus } from './researchReadContext';
import type { ResearchInputStatusRead, StoredProfile } from '@/types';
import { t } from './i18n';
export function useResearchInputRead() {
  const { currentAdmissionsCase, savedProfile, run } = useStore(); const live = currentAdmissionsCase();
  const key = JSON.stringify([live.scope === undefined ? 'demo' : live.scope, live.profile_id, live.case_epoch, run?.id ?? null]);
  const getter = useRef(currentAdmissionsCase); getter.current = currentAdmissionsCase;
  const rendered = useRef({ key, profile: savedProfile }); rendered.current = { key, profile: savedProfile };
  const mounted = useRef(true); const serial = useRef(0);
  const runId = run?.profile_id === savedProfile?.id ? run?.id ?? null : null;
  const [stored, setStored] = useState<{ key: string; profile: StoredProfile; status: ResearchInputStatusRead | null; loading: boolean; error: string } | null>(null);
  const active = useCallback((profile: StoredProfile) => {
    const current = getter.current();
    return mounted.current && rendered.current.key === key && rendered.current.profile === profile && current.scope !== null
      && profile.id === current.profile_id && key === JSON.stringify([current.scope === undefined ? 'demo' : current.scope, current.profile_id, current.case_epoch, runId]);
  }, [key, runId]);
  const refresh = useCallback(async () => {
    const profile = savedProfile; if (!profile || !runId || !active(profile)) return false;
    const request = ++serial.current; setStored(old => ({ key, profile, status: old?.key === key && old.profile === profile ? old.status : null, loading: true, error: '' }));
    try {
      const out = await api.getRun(runId); if (!active(profile) || request !== serial.current) return false;
      if (out.id !== runId || out.profile_id !== profile.id || !isResearchInputStatus(out.profile_input_status)) throw new Error('Unconfirmed read context');
      setStored({ key, profile, status: out.profile_input_status, loading: false, error: '' }); return true;
    } catch {
      if (active(profile) && request === serial.current) setStored(old => ({ key, profile, status: old?.key === key && old.profile === profile ? old.status : null, loading: false, error: t('inputs.readFailed') }));
      return false;
    }
  }, [savedProfile, runId, active, key]);
  useEffect(() => { const intent = serial; mounted.current = true; return () => { mounted.current = false; ++intent.current; }; }, []);
  useEffect(() => { const intent = serial; void refresh(); return () => { ++intent.current; }; }, [refresh]);
  const view = stored?.key === key && stored.profile === savedProfile ? stored : null;
  return { applicable: runId !== null && savedProfile?.id === live.profile_id, status: view?.status ?? null, loading: view?.loading ?? false, error: view?.error ?? '', refresh };
}
''')
print('External typed read-context and fenced input-read hook ready; UI/messages/tests pending, current full source unchanged.')
