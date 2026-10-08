/**
 * The route printed on a pass (concept «Пропуск»): a dotted arc from the
 * programme's city to home, both ends named. A drawing, not a map: the globe
 * stays on the screens that have room for it. Drawn only when both ends are
 * known; otherwise the pass says nothing rather than guess.
 */

export function PassRoute({ city, home }: { city: string; home: string | null | undefined }) {
  if (!city || !home) return null;
  return (
    <figure className="pass-route" aria-label={`Route from ${city} to ${home}`}>
      <svg viewBox="0 0 300 54" preserveAspectRatio="none" aria-hidden="true" focusable="false">
        <path d="M8 34 Q150 -6 292 46" fill="none" stroke="currentColor" strokeWidth="2" strokeDasharray="1 7" strokeLinecap="round" vectorEffect="non-scaling-stroke" />
      </svg>
      <span className="pass-route__end pass-route__end--from" aria-hidden="true" />
      <span className="pass-route__end pass-route__end--to" aria-hidden="true" />
      <figcaption aria-hidden="true">
        <span>{city}</span>
        <span>{home}</span>
      </figcaption>
    </figure>
  );
}
