/**
 * A row's admission deadline, as every summary shows it (card, hero, compare).
 *
 * A deadline that has passed is said to have passed: Oxford's 15 October,
 * already behind the applicant, read as a plain "Oct 15, 2026" on the card and
 * the hero, as if it were the date to apply by (KB v18 smoke U2).
 */

import { Chip } from '@/components/primitives';
import { date } from '@/lib/format';
import { useTranslation } from '@/lib/useTranslation';
import type { ProgramResult } from '@/types';

export function Deadline({ result, fallback }: {
  result: Pick<ProgramResult, 'admission_deadline' | 'deadline_passed'>;
  /** What to say when no deadline was confirmed. */
  fallback: string;
}) {
  const { t } = useTranslation();
  if (!result.admission_deadline) return <>{fallback}</>;
  return (
    <>
      {date(result.admission_deadline)}
      {result.deadline_passed && (
        <>{' '}<span data-testid="deadline-passed"><Chip tone="risk">{t('detail.deadlinePassed')}</Chip></span></>
      )}
    </>
  );
}
