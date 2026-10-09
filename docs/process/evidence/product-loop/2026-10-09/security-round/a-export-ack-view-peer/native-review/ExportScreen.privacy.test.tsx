import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi, type Mock } from 'vitest';
import { ExportScreen } from './ExportScreen';
import type { StoredProfile } from '@/types';

const mocks = vi.hoisted(() => ({
  exportProfile: vi.fn(), deleteEverything: vi.fn(), exportShortlist: vi.fn(),
}));
let savedProfile: StoredProfile | null;
let profileDraft: Record<string, unknown>;
vi.mock('@/api/client', () => ({ api: { exportProfile: mocks.exportProfile } }));
vi.mock('@/lib/store', () => ({ useStore: () => ({ savedProfile, profileDraft,
  run: null, results: [], summary: null, capabilities: null,
  deleteEverything: mocks.deleteEverything, exportShortlist: mocks.exportShortlist,
}) }));

const PROFILE_A = { id: 'synthetic-case-a', display_name: 'Synthetic case A' } as StoredProfile;
const PROFILE_B = { id: 'synthetic-case-b', display_name: 'Synthetic case B' } as StoredProfile;
const RECORD_A = { profile: { display_name: 'Synthetic case A' }, runs: [] };
const RECORD_B = { profile: { display_name: 'Synthetic case B' }, runs: [] };
let createObjectURL: Mock<(object: Blob | MediaSource) => string>;
let revokeObjectURL: Mock<(url: string) => void>;
let anchorClick: ReturnType<typeof vi.spyOn>;

function pending<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: Error) => void;
  const promise = new Promise<T>((done, fail) => { resolve = done; reject = fail; });
  return { promise, resolve, reject };
}
function confirmDelete() {
  fireEvent.change(screen.getByTestId('delete-confirm'), { target: { value: 'DELETE' } });
  fireEvent.click(screen.getByTestId('delete-everything'));
}
async function opened() {
  mocks.exportProfile.mockResolvedValueOnce(RECORD_A);
  const view = render(<ExportScreen />);
  fireEvent.click(screen.getByTestId('export-profile'));
  expect(await screen.findByLabelText('Stored profile data')).toHaveTextContent('Synthetic case A');
  return view;
}
function switched(view: ReturnType<typeof render>, profile: StoredProfile | null) {
  savedProfile = profile;
  profileDraft = { display_name: profile?.display_name ?? '' };
  view.rerender(<ExportScreen />);
}
async function settle<T>(deferred: ReturnType<typeof pending<T>>, value: T) {
  await act(async () => { deferred.resolve(value); await deferred.promise; });
}

beforeEach(() => {
  savedProfile = PROFILE_A;
  profileDraft = { display_name: 'Synthetic case A' };
  mocks.exportProfile.mockReset();
  mocks.deleteEverything.mockReset().mockResolvedValue(false);
  mocks.exportShortlist.mockReset();
  createObjectURL = vi.fn<(object: Blob | MediaSource) => string>().mockReturnValue('blob:synthetic-case');
  revokeObjectURL = vi.fn<(url: string) => void>();
  vi.stubGlobal('URL', class extends URL {
    static createObjectURL = createObjectURL;
    static revokeObjectURL = revokeObjectURL;
  });
  anchorClick = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe('acknowledged case export privacy', () => {
  it('allows a saved no-run case to show the API record and download normally', async () => {
    await opened();
    mocks.exportProfile.mockResolvedValueOnce(RECORD_A);
    fireEvent.click(screen.getByTestId('download-profile'));
    await waitFor(() => expect(anchorClick).toHaveBeenCalledOnce());
    expect(mocks.exportProfile.mock.calls).toEqual([['synthetic-case-a'], ['synthetic-case-a']]);
    expect(createObjectURL).toHaveBeenCalledOnce();
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:synthetic-case');
    const anchor = anchorClick.mock.instances[0] as HTMLAnchorElement;
    expect(anchor.download).toBe('ashyq-syntheti-my-data.json');
    expect(screen.queryByText(/^Deleted\./)).not.toBeInTheDocument();
  });

  it('clears an already opened JSON record only after acknowledgment', async () => {
    await opened();
    const deletion = pending<boolean>();
    mocks.deleteEverything.mockReturnValueOnce(deletion.promise);
    confirmDelete();
    expect(screen.getByLabelText('Stored profile data')).toHaveTextContent('Synthetic case A');
    expect(screen.queryByText(/^Deleted\./)).not.toBeInTheDocument();
    await settle(deletion, true);
    expect(screen.queryByLabelText('Stored profile data')).not.toBeInTheDocument();
    expect(screen.getByText(/^Deleted\./)).toBeInTheDocument();
    expect(screen.getByTestId('export-profile')).toBeDisabled();
    expect(screen.getByTestId('download-profile')).toBeDisabled();
    expect(mocks.deleteEverything).toHaveBeenCalledOnce();
    expect(mocks.exportShortlist).not.toHaveBeenCalled();
  });

  it('retains opened JSON and never claims success when deletion returns false', async () => {
    await opened();
    confirmDelete();
    await waitFor(() => expect(mocks.deleteEverything).toHaveBeenCalledOnce());
    expect(screen.getByLabelText('Stored profile data')).toHaveTextContent('Synthetic case A');
    expect(screen.queryByText(/^Deleted\./)).not.toBeInTheDocument();
    expect(screen.getByTestId('delete-confirm')).toHaveValue('DELETE');
    expect(screen.getByTestId('export-profile')).toBeEnabled();
  });

  it('does not report success or clear JSON if the deletion callback rejects', async () => {
    await opened();
    const deletion = pending<boolean>();
    mocks.deleteEverything.mockReturnValueOnce(deletion.promise);
    confirmDelete();
    await act(async () => { deletion.reject(new Error('synthetic deletion refused')); await deletion.promise.catch(() => undefined); });
    expect(screen.getByLabelText('Stored profile data')).toHaveTextContent('Synthetic case A');
    expect(screen.queryByText(/^Deleted\./)).not.toBeInTheDocument();
  });

  it('does not let a late Show answer restore JSON after an acknowledged deletion', async () => {
    const answer = pending<Record<string, unknown>>();
    mocks.exportProfile.mockReturnValueOnce(answer.promise);
    mocks.deleteEverything.mockResolvedValueOnce(true);
    render(<ExportScreen />);
    fireEvent.click(screen.getByTestId('export-profile'));
    confirmDelete();
    await screen.findByText(/^Deleted\./);
    await settle(answer, RECORD_A);
    expect(screen.queryByLabelText('Stored profile data')).not.toBeInTheDocument();
    expect(createObjectURL).not.toHaveBeenCalled();
  });

  it('does not create a file from a pending Download after acknowledged deletion', async () => {
    const answer = pending<Record<string, unknown>>();
    mocks.exportProfile.mockReturnValueOnce(answer.promise);
    mocks.deleteEverything.mockResolvedValueOnce(true);
    render(<ExportScreen />);
    fireEvent.click(screen.getByTestId('download-profile'));
    confirmDelete();
    await screen.findByText(/^Deleted\./);
    await settle(answer, RECORD_A);
    expect(createObjectURL).not.toHaveBeenCalled();
    expect(anchorClick).not.toHaveBeenCalled();
    expect(revokeObjectURL).not.toHaveBeenCalled();
  });

  it('keeps a pending Show usable when deletion is refused', async () => {
    const answer = pending<Record<string, unknown>>();
    mocks.exportProfile.mockReturnValueOnce(answer.promise);
    render(<ExportScreen />);
    fireEvent.click(screen.getByTestId('export-profile'));
    confirmDelete();
    await waitFor(() => expect(mocks.deleteEverything).toHaveBeenCalledOnce());
    await settle(answer, RECORD_A);
    expect(screen.getByLabelText('Stored profile data')).toHaveTextContent('Synthetic case A');
    expect(screen.queryByText(/^Deleted\./)).not.toBeInTheDocument();
  });

  it('retires the mounted previous JSON and confirmation when switching cases', async () => {
    const view = await opened();
    fireEvent.change(screen.getByTestId('delete-confirm'), { target: { value: 'DELETE' } });
    switched(view, PROFILE_B);
    expect(screen.queryByLabelText('Stored profile data')).not.toBeInTheDocument();
    expect(screen.getByTestId('delete-confirm')).toHaveValue('');
    expect(screen.getByTestId('delete-everything')).toBeDisabled();
    mocks.exportProfile.mockResolvedValueOnce(RECORD_B);
    fireEvent.click(screen.getByTestId('export-profile'));
    expect(await screen.findByLabelText('Stored profile data')).toHaveTextContent('Synthetic case B');
    expect(mocks.exportProfile.mock.lastCall).toEqual(['synthetic-case-b']);
  });

  it.each(['show', 'download'] as const)('ignores a late %s answer after a mounted case switch', async (action) => {
    const answer = pending<Record<string, unknown>>();
    mocks.exportProfile.mockReturnValueOnce(answer.promise);
    const view = render(<ExportScreen />);
    fireEvent.click(screen.getByTestId(action === 'show' ? 'export-profile' : 'download-profile'));
    switched(view, PROFILE_B);
    await settle(answer, RECORD_A);
    expect(screen.queryByLabelText('Stored profile data')).not.toBeInTheDocument();
    expect(createObjectURL).not.toHaveBeenCalled();
    expect(anchorClick).not.toHaveBeenCalled();
  });

  it('does not mark a newly selected case Deleted or clear its JSON from an old acknowledgment', async () => {
    const deletion = pending<boolean>();
    mocks.deleteEverything.mockReturnValueOnce(deletion.promise);
    const view = render(<ExportScreen />);
    confirmDelete();
    switched(view, PROFILE_B);
    mocks.exportProfile.mockResolvedValueOnce(RECORD_B);
    fireEvent.click(screen.getByTestId('export-profile'));
    await screen.findByLabelText('Stored profile data');
    await settle(deletion, true);
    expect(screen.queryByText(/^Deleted\./)).not.toBeInTheDocument();
    expect(screen.getByLabelText('Stored profile data')).toHaveTextContent('Synthetic case B');
    expect(screen.getByTestId('export-profile')).toBeEnabled();
  });

  it('drops the old Deleted state for a different saved case', async () => {
    mocks.deleteEverything.mockResolvedValueOnce(true);
    const view = render(<ExportScreen />);
    confirmDelete();
    await screen.findByText(/^Deleted\./);
    switched(view, PROFILE_B);
    expect(screen.queryByText(/^Deleted\./)).not.toBeInTheDocument();
    expect(screen.getByTestId('delete-confirm')).toHaveValue('');
    expect(screen.getByTestId('export-profile')).toBeEnabled();
  });

  it('keeps honest acknowledgment if Store clears the case before callback resumes, then retires it for a new blank case', async () => {
    const view = await opened();
    const deletion = pending<boolean>();
    mocks.deleteEverything.mockReturnValueOnce(deletion.promise);
    confirmDelete();
    switched(view, null);
    await settle(deletion, true);
    expect(screen.queryByLabelText('Stored profile data')).not.toBeInTheDocument();
    expect(screen.getByText(/^Deleted\./)).toBeInTheDocument();
    switched(view, null);
    expect(screen.queryByText(/^Deleted\./)).not.toBeInTheDocument();
    expect(screen.getByText('Nothing to export yet')).toBeInTheDocument();
  });

  it('ignores an earlier Show after A to B to A rather than trusting only a matching id', async () => {
    const answer = pending<Record<string, unknown>>();
    mocks.exportProfile.mockReturnValueOnce(answer.promise);
    const view = render(<ExportScreen />);
    fireEvent.click(screen.getByTestId('export-profile'));
    switched(view, PROFILE_B);
    switched(view, PROFILE_A);
    await settle(answer, RECORD_A);
    expect(screen.queryByLabelText('Stored profile data')).not.toBeInTheDocument();
    mocks.exportProfile.mockResolvedValueOnce(RECORD_A);
    fireEvent.click(screen.getByTestId('export-profile'));
    expect(await screen.findByLabelText('Stored profile data')).toHaveTextContent('Synthetic case A');
  });

  it('does not create a pending file after the component unmounts', async () => {
    const answer = pending<Record<string, unknown>>();
    mocks.exportProfile.mockReturnValueOnce(answer.promise);
    const view = render(<ExportScreen />);
    fireEvent.click(screen.getByTestId('download-profile'));
    view.unmount();
    await settle(answer, RECORD_A);
    expect(createObjectURL).not.toHaveBeenCalled();
    expect(anchorClick).not.toHaveBeenCalled();
  });
});
