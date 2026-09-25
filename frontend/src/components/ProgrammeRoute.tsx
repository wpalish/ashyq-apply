/**
 * A programme's route from home, on the globe (concept 10, and concept P's
 * one-at-a-time card): "Astana → Groningen", both ends named.
 *
 * Only what is known is drawn. The city comes from the checked table and
 * home from the country of residence; without the city there is no route and
 * the page says why, and without a home the city stands alone and the page
 * says what would draw the route.
 */

import { useMemo } from 'react';
import { Globe } from '@/components/Globe';
import { defaultView, markersFor, placeOf, type LatLon } from '@/lib/globe';
import type { ProgramResult } from '@/types';

export function ProgrammeRoute({
  result, home, tone, height, testId, steady = false, covered = 0,
}: {
  result: ProgramResult;
  home: (LatLon & { city: string }) | null;
  tone: 'day' | 'night';
  height: number;
  testId: string;
  /**
   * Keep the globe even when the city cannot be placed, so a run of cards
   * (the triage) does not jump; the reason then sits over the globe.
   */
  steady?: boolean;
  /** Pixels at the bottom a card sits over. */
  covered?: number;
}) {
  const place = placeOf(result);
  const markers = useMemo(() => markersFor([result]).markers, [result]);
  const city = result.city || 'this city';
  const none = `No route on the globe: ${city} is not in its table of cities yet.`;
  const noHome = 'Add your country of residence to your profile to draw the route from home.';
  if (!place && !steady) {
    return <p className={`route__note route__note--${tone}`} data-testid={`${testId}-none`}>{none}</p>;
  }
  const fit = place ? (home ? [home, place] : [place]) : home ? [home] : undefined;
  return (
    <div className={`route route--${tone}${steady ? ' route--steady' : ''}`}>
      <Globe
        layout="band"
        tone={tone}
        height={height}
        markers={place ? markers : []}
        home={home}
        focus={place ?? defaultView(home)}
        fit={fit}
        covered={covered}
        routes={Boolean(home && place)}
        names
        caption={place
          ? home ? `The route from ${home.city} to ${place.city}.` : `${place.city} on the globe.`
          : none}
        testId={testId}
      />
      {!place && <p className={`route__note route__note--${tone}`} data-testid={`${testId}-none`}>{none}</p>}
      {place && !home && <p className={`route__note route__note--${tone}`} data-testid={`${testId}-no-home`}>{noHome}</p>}
    </div>
  );
}
