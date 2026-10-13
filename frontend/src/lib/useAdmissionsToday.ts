import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '@/api/client';
import { useStore } from './store';
import { isTodayProjection, type TodayProjectionV1 } from '@/types/admissionsActions';
import { t } from './i18n';
const caseKey = (v: ReturnType<ReturnType<typeof useStore>['currentAdmissionsCase']>) => JSON.stringify([v.scope === undefined ? 'demo' : v.scope, v.profile_id, v.case_epoch]);
export function useAdmissionsToday() {
  const { currentAdmissionsCase } = useStore(); const live = currentAdmissionsCase(); const key = caseKey(live);
  const getter = useRef(currentAdmissionsCase); getter.current = currentAdmissionsCase;
  const mounted = useRef(true); const serial = useRef(0);
  const [stored, setStored] = useState<{ key: string; value: TodayProjectionV1 | null; loading: boolean; error: string } | null>(null);
  const active = useCallback(() => mounted.current && key === caseKey(getter.current()), [key]);
  const refresh = useCallback(async () => {
    const captured = getter.current(); if (!active() || captured.scope === null || captured.profile_id === null) return false;
    const request = ++serial.current; setStored(old => ({ key, value: old?.key === key ? old.value : null, loading: true, error: '' }));
    try {
      let timezone: string | null = null; try { timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || null; } catch { /* server uses explicit fallback */ }
      const out: unknown = await api.admissionsToday(captured.profile_id, timezone);
      if (!active() || request !== serial.current) return false;
      if (!isTodayProjection(out) || out.profile_id !== captured.profile_id) throw new Error('Unconfirmed Today response');
      setStored({ key, value: out, loading: false, error: '' }); return true;
    } catch {
      if (active() && request === serial.current) setStored(old => ({ key, value: old?.key === key ? old.value : null, loading: false, error: t('today.unavailable') }));
      return false;
    }
  }, [active, key]);
  useEffect(() => { const token = serial; mounted.current = true; return () => { mounted.current = false; ++token.current; }; }, []);
  useEffect(() => { const token = serial; void refresh(); return () => { ++token.current; }; }, [refresh]);
  const view = stored?.key === key ? stored : null;
  return { caseKey: key, profileId: live.profile_id, value: view?.value ?? null, loading: view?.loading ?? (live.profile_id !== null && live.scope !== null), error: view?.error ?? '', refresh };
}
