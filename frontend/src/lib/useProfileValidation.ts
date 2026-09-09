import { useCallback, useEffect, useState } from 'react';
import { ApiError, api } from '@/api/client';
import type { ProfileValidationReport } from '@/types';

export type ValidationStatus = 'pending' | 'ready' | 'invalid' | 'error';

/** A report is usable only for the draft and retry that requested it. */
export function useProfileValidation(draft: Record<string, unknown>, enabled: boolean) {
  const [attempt, setAttempt] = useState(0);
  const [result, setResult] = useState<{
    draft: Record<string, unknown>; attempt: number;
    status: ValidationStatus; report: ProfileValidationReport | null;
  } | null>(null);
  const retryValidation = useCallback(() => setAttempt((value) => value + 1), []);

  useEffect(() => {
    if (!enabled) { setResult(null); return; }
    let cancelled = false;
    const timer = window.setTimeout(() => {
      api.validateProfile(draft).then((report) => {
        if (!cancelled) setResult({ draft, attempt, status: 'ready', report });
      }).catch((error: unknown) => {
        if (!cancelled) setResult({ draft, attempt, report: null,
          status: error instanceof ApiError && error.status === 422 ? 'invalid' : 'error' });
      });
    }, 400);
    return () => { cancelled = true; window.clearTimeout(timer); };
  }, [draft, enabled, attempt]);

  const current = enabled && result?.draft === draft && result.attempt === attempt;
  return {
    validation: current ? result.report : null,
    validationStatus: current ? result.status : 'pending' as ValidationStatus,
    retryValidation,
  };
}
