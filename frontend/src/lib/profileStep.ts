import { useCallback, useState } from 'react';

const slot = (key: string) => `ashyq.profileStep.v1.${key}`;
const valid = (step: number) => Number.isInteger(step) && step >= 0 && step < 6;

export function readProfileStep(key: string | null): number {
  if (key === null) return 0;
  try {
    const raw = sessionStorage.getItem(slot(key));
    if (raw === null || !/^[0-5]$/.test(raw)) return 0;
    return Number(raw);
  } catch { return 0; }
}

function writeProfileStep(key: string | null, step: number): void {
  if (key === null) return;
  try { sessionStorage.setItem(slot(key), String(step)); } catch { /* best-effort UI state */ }
}

export function clearProfileStep(key: string): void {
  try { sessionStorage.removeItem(slot(key)); } catch { /* best-effort UI state */ }
}

export function migrateProfileStep(from: string | null, to: string, step: number): void {
  if (valid(step)) writeProfileStep(to, step);
  if (from !== null && from !== to) clearProfileStep(from);
}

/** Read the target case synchronously: never render or write another case's step. */
export function useProfileStep(key: string | null) {
  const [selection, setSelection] = useState(() => ({ key, step: readProfileStep(key) }));
  const step = selection.key === key ? selection.step : readProfileStep(key);
  if (selection.key !== key) setSelection({ key, step });
  const setStep = useCallback((next: number) => {
    if (!valid(next)) return;
    writeProfileStep(key, next);
    setSelection({ key, step: next });
  }, [key]);
  return [step, setStep] as const;
}
