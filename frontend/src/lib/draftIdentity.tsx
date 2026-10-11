import { createContext } from 'react';
import type { AuthPrincipal } from '@/types';

/**
 * One browser-storage owner per authenticated tree. Never keep the current
 * owner in a module variable: two mounted trees may have different identities.
 * Undefined preserves the helpers' legacy embedding contract; AuthGate always
 * supplies a verified scope or null (storage disabled when identity is absent).
 */
export const DraftIdentityContext = createContext<string | null | undefined>(undefined);

export function draftIdentity(principal: AuthPrincipal | null): string | null {
  if (!principal || typeof principal.user_id !== 'string' || !principal.user_id ||
      typeof principal.organization_id !== 'string' || !principal.organization_id) return null;
  return JSON.stringify([principal.user_id, principal.organization_id]);
}
