import { useEffect, useState } from 'react';

/**
 * Whether a media query matches, kept current. False where there is no
 * matchMedia (jsdom), so a screen renders its phone layout under test.
 */
export function useMedia(query: string): boolean {
  const read = () => typeof window !== 'undefined' && typeof window.matchMedia === 'function'
    && window.matchMedia(query).matches;
  const [matches, setMatches] = useState(read);
  useEffect(() => {
    if (typeof window.matchMedia !== 'function') return undefined;
    const media = window.matchMedia(query);
    const update = () => setMatches(media.matches);
    update();
    media.addEventListener?.('change', update);
    return () => media.removeEventListener?.('change', update);
  }, [query]);
  return matches;
}

/** The desk layout: the sidebar, not the floating capsule. */
export const WIDE = '(min-width: 901px)';
