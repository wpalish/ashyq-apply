/**
 * Every screen with a name in the navigation, in journey order: the sidebar,
 * the header's "Explore" menu and the screen names in sentences all read it.
 */

import type { ScreenId } from '@/App';
import type { MessageKey } from '@/lib/i18n';

/**
 * The numbers are not decoration: the case screens are a sequence, and 04
 * genuinely cannot be read before 03 has produced anything. Community is not a
 * sequence, so those entries carry no number.
 */
export const SCREENS: { id: ScreenId; num?: string; label: MessageKey; group: MessageKey }[] = [
  { id: 'profile', num: '01', label: 'nav.profile', group: 'nav.group.prepare' },
  { id: 'preferences', num: '02', label: 'nav.preferences', group: 'nav.group.prepare' },
  { id: 'progress', num: '03', label: 'nav.progress', group: 'nav.group.research' },
  { id: 'shortlist', num: '04', label: 'nav.shortlist', group: 'nav.group.research' },
  { id: 'funding', num: '05', label: 'nav.funding', group: 'nav.group.research' },
  { id: 'sources', num: '06', label: 'nav.sources', group: 'nav.group.research' },
  { id: 'approved', num: '07', label: 'nav.approved', group: 'nav.group.decide' },
  { id: 'documents', num: '08', label: 'nav.documents', group: 'nav.group.decide' },
  { id: 'export', num: '09', label: 'nav.export', group: 'nav.group.decide' },
  { id: 'feed', label: 'nav.feed', group: 'nav.group.community' },
  { id: 'discover', label: 'nav.discover', group: 'nav.group.community' },
  { id: 'messages', label: 'nav.messages', group: 'nav.group.community' },
  { id: 'me', label: 'nav.me', group: 'nav.group.community' },
  { id: 'moderation', label: 'nav.moderation', group: 'nav.group.community' },
  // Listed rather than tucked into the footer, so that it has an address a
  // person can be sent to: "read the privacy policy" is a link, not a hunt.
  { id: 'legal', label: 'nav.legal', group: 'nav.group.about' },
];
