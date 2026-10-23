import { useCallback, useEffect, useRef, useState } from 'react';
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
