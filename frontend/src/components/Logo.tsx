/**
 * The Unimatch wordmark (src/lib/logo.ts). It takes the colour of the text around it and its
 * size from CSS (height; the width follows), and it is announced as "Unimatch" unless the
 * place it sits already names the brand (decorative).
 */

import { LOGO_H, LOGO_PATHS, LOGO_TRANSFORM, LOGO_W } from '@/lib/logo';

export function Logo({ className = '', decorative = false }: { className?: string; decorative?: boolean }) {
  return (
    <svg
      className={`logo${className ? ` ${className}` : ''}`}
      viewBox={`0 0 ${LOGO_W} ${LOGO_H}`}
      fill="currentColor"
      {...(decorative ? { 'aria-hidden': true } : { role: 'img', 'aria-label': 'Unimatch' })}
      focusable="false"
    >
      <g transform={LOGO_TRANSFORM}>
        {LOGO_PATHS.map((d, i) => <path key={i} d={d} />)}
      </g>
    </svg>
  );
}
