import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ExportScreen } from './ExportScreen';
import type { StoredProfile } from '@/types';

const mocks = vi.hoisted(() => ({ exportProfile: vi.fn(), deleteEverything: vi.fn() }));
let profile: StoredProfile | null;
let epoch: number;
let draft: Record<string, unknown>;
vi.mock('@/api/client', () => ({ api: { exportProfile: mocks.exportProfile } }));
vi.mock('@/lib/store', () => ({ useStore: () => ({ savedProfile: profile, caseEpoch: epoch,
  profileDraft: draft, run: null, results: [], summary: null, capabilities: null,
  deleteEverything: mocks.deleteEverything, exportShortlist: vi.fn(),
}) }));
const CASE = { id: 'synthetic-integration-case', display_name: 'Synthetic case' } as StoredProfile;
const RECORD = { profile: { display_name: 'Synthetic exported record' } };
function pending<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => { resolve = done; });
  return { promise, resolve };
}
async function settle<T>(answer: ReturnType<typeof pending<T>>, value: T) {
  await act(async () => { answer.resolve(value); await answer.promise; });
}
function confirm() {
  fireEvent.change(screen.getByTestId('delete-confirm'), { target: { value: 'DELETE' } });
  fireEvent.click(screen.getByTestId('delete-everything'));
}
beforeEach(() => {
  profile = CASE; epoch = 1; draft = { display_name: 'Synthetic case' };
  mocks.exportProfile.mockReset(); mocks.deleteEverything.mockReset();
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe('integrated export identity and deletion feedback', () => {
  it.each(['show', 'download'] as const)('rejects pending %s at switch intent before the case id changes', async (action) => {
    const answer = pending<Record<string, unknown>>();
    mocks.exportProfile.mockReturnValue(answer.promise);
    const download = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined);
    const view = render(<ExportScreen />);
    fireEvent.click(screen.getByTestId(action === 'show' ? 'export-profile' : 'download-profile'));
    epoch += 1; view.rerender(<ExportScreen />);
    await settle(answer, RECORD);
    expect(screen.queryByLabelText('Stored profile data')).not.toBeInTheDocument();
    expect(download).not.toHaveBeenCalled();
  });
  it('clears opened JSON and confirmation on a same-id new intent', async () => {
    mocks.exportProfile.mockResolvedValue(RECORD);
    const view = render(<ExportScreen />);
    fireEvent.click(screen.getByTestId('export-profile'));
    await screen.findByLabelText('Stored profile data');
    fireEvent.change(screen.getByTestId('delete-confirm'), { target: { value: 'DELETE' } });
    epoch += 1; view.rerender(<ExportScreen />);
    expect(screen.queryByLabelText('Stored profile data')).not.toBeInTheDocument();
    expect(screen.getByTestId('delete-confirm')).toHaveValue('');
    expect(screen.getByTestId('delete-everything')).toBeDisabled();
  });
  it('keeps only its own delete receipt when the blank render precedes the callback', async () => {
    const deletion = pending<boolean>();
    mocks.deleteEverything.mockReturnValue(deletion.promise);
    const view = render(<ExportScreen />); confirm();
    profile = null; epoch += 1; draft = {}; view.rerender(<ExportScreen />);
    await settle(deletion, true);
    expect(screen.getByText(/^Deleted\./)).toBeInTheDocument();
    draft = { display_name: 'Later new draft' }; epoch += 1; view.rerender(<ExportScreen />);
    expect(screen.queryByText(/^Deleted\./)).not.toBeInTheDocument();
  });
  it('retires export immediately after ACK while the old case is still rendered', async () => {
    const answer = pending<Record<string, unknown>>();
    const deletion = pending<boolean>();
    mocks.exportProfile.mockReturnValue(answer.promise); mocks.deleteEverything.mockReturnValue(deletion.promise);
    render(<ExportScreen />); fireEvent.click(screen.getByTestId('export-profile')); confirm();
    await settle(deletion, true); await settle(answer, RECORD);
    expect(screen.getByText(/^Deleted\./)).toBeInTheDocument();
    expect(screen.queryByLabelText('Stored profile data')).not.toBeInTheDocument();
    expect(screen.getByTestId('export-profile')).toBeDisabled();
    expect(screen.getByTestId('download-profile')).toBeDisabled();
  });
  it('does not accept an old delete acknowledgment after a new switch intent', async () => {
    const deletion = pending<boolean>(); mocks.deleteEverything.mockReturnValue(deletion.promise);
    const view = render(<ExportScreen />); confirm();
    epoch += 1; view.rerender(<ExportScreen />); await settle(deletion, true);
    expect(screen.queryByText(/^Deleted\./)).not.toBeInTheDocument();
    expect(screen.getByTestId('export-profile')).toBeEnabled();
  });
});
