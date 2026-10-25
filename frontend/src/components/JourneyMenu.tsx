/**
 * The header's "Explore" menu: every screen in journey order, each named in
 * the reader's language (the labels are `nav.*` keys, never English literals).
 */

import type { ScreenId } from '@/App';
import { SCREENS } from '@/lib/screens';
import { useTranslation } from '@/lib/useTranslation';

export function JourneyMenu({
  moderator,
  gate,
  onSelect,
}: {
  /** The moderation queue is listed only for a moderator. */
  moderator: boolean;
  /** A screen whose entry is a reason (not null) cannot be opened yet. */
  gate: Partial<Record<ScreenId, string | null>>;
  onSelect: (id: ScreenId) => void;
}) {
  const { t } = useTranslation();
  return (
    <details className="journey-menu">
      <summary>{t('topbar.explore')}</summary>
      <div className="journey-menu__list">
        {SCREENS.filter((item) => item.id !== 'moderation' || moderator).map((item) => (
          <button key={item.id} type="button" onClick={() => onSelect(item.id)} disabled={Boolean(gate[item.id])}>
            {t(item.label)}
          </button>
        ))}
      </div>
    </details>
  );
}
