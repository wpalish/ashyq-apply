import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { DocumentsScreen } from '@/screens/DocumentsScreen';
import { applicantStorageKey, bindApplicantOwner } from '@/lib/applicantStorage';
import { result } from '@/lib/securityMergeFixtures';
import type { AuthStatus } from '@/types';

const rows = [result('synthetic-result', 'synthetic-run')];
vi.mock('@/lib/store', () => ({ useStore: () => ({ results: rows, run: null }) }));
const status: AuthStatus = { enabled: true, registration_enabled: false, authenticated: true,
  principal: { user_id: 'synthetic-A', organization_id: 'synthetic-org-A',
    email: 'synthetic-a@example.invalid', display_name: 'A', organization_name: 'A',
    role: 'owner', local_development: false } };
beforeEach(() => { localStorage.clear(); sessionStorage.clear(); bindApplicantOwner(status); });
afterEach(() => { cleanup(); });
it('an old mounted checklist cannot write its ticks into a newly bound owner before storage-event remount', () => {
  const a = render(<DocumentsScreen />); const oldKey = applicantStorageKey('ashyq.docsDone')!;
  fireEvent.click(screen.getByRole('checkbox')); expect(screen.getByRole('checkbox')).toBeChecked();
  bindApplicantOwner({ ...status, principal: { ...status.principal!, user_id: 'synthetic-B', organization_id: 'synthetic-org-B' } });
  const newKey = applicantStorageKey('ashyq.docsDone')!;
  expect(newKey).not.toBe(oldKey); expect(localStorage.getItem(oldKey)).toBeNull();
  // The old handler runs before AuthGate has handled an owner storage event.
  fireEvent.click(screen.getByRole('checkbox'));
  expect(localStorage.getItem(oldKey)).toBeNull(); expect(localStorage.getItem(newKey)).toBeNull();
  a.unmount(); render(<DocumentsScreen />);
  expect(screen.getByRole('checkbox')).not.toBeChecked();
});
