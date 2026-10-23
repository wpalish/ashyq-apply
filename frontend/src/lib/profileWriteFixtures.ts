/** Synthetic acknowledgement fixture, bound to the actual captured API command. */
import type { ProfileCommandHeaders, StoredProfile } from '@/types';
export function profileAck(profile: StoredProfile, command: ProfileCommandHeaders | undefined, kind: 'create' | 'update' | 'persisted_rerank' = 'update'): StoredProfile {
  if (!command) throw new Error('Synthetic profile write omitted command headers.');
  const revision = (command.expected_revision ?? 0) + 1;
  return { ...profile, revision, write_receipt: { command_id:command.command_id, kind, profile_id:profile.id, expected_revision:command.expected_revision ?? null, accepted_revision:revision } };
}
