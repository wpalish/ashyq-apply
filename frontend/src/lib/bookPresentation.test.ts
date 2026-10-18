import { describe, expect, it } from 'vitest';
import type { ClaimOut, ProgramResult } from '@/types';
import { programmeLanguage } from './bookPresentation';

const claim = (language: string, extra: Partial<ClaimOut> = {}): ClaimOut => ({
  claim_type: 'program_exists', normalized_value: { language }, status: 'VERIFIED_CURRENT',
  official_domain: true, is_stale: false, ...extra,
} as ClaimOut);
const result = (claims: ClaimOut[]) => ({ claims } as ProgramResult);

describe('teaching language in result controls', () => {
  it('does not turn a language test requirement or an unverified observation into a teaching language', () => {
    expect(programmeLanguage(result([
      claim('English', { claim_type: 'ielts_overall' }),
      claim('English', { status: 'UNVERIFIED' }),
      claim('English', { official_domain: false }),
      claim('English', { is_stale: true }),
    ]))).toBe('');
  });
  it('normalises identical current claims and keeps conflicting languages unknown', () => {
    expect(programmeLanguage(result([claim('English'), claim(' english ')]))).toBe('english');
    expect(programmeLanguage(result([claim('English'), claim('German')]))).toBe('');
  });
});
