/** Native shell navigation with synthetic API/store; actual Preparation, Home and Plan components. */
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import App from '@/App';
import { api } from '@/api/client';
import { caseRow, profile, result } from '@/lib/securityMergeFixtures';
import { access, learningCatalogue as catalogue, plan, progress } from '@/screens/preparationFixtures';
const state = vi.hoisted(() => ({ value: {} as Record<string, unknown> }));
vi.mock('@/lib/store', () => ({ useStore: () => state.value }));
async function flush() { await act(async () => { for (let i = 0; i < 8; ++i) await Promise.resolve(); }); }
beforeEach(() => {
  localStorage.clear(); sessionStorage.clear(); window.location.hash = '#/home';
  const owner = 'demo'; // Explicit native demo owner; this tree has no authenticated DraftIdentityContext.
  localStorage.setItem('ashyq.applicantOwner', owner); sessionStorage.setItem('ashyq.applicantOwner', owner);
  vi.spyOn(window, 'scrollTo').mockImplementation(() => {});
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected transport in synthetic preparation navigation control'); }));
  vi.spyOn(api, 'authStatus').mockResolvedValue({ enabled: false, authenticated: true, registration_enabled: false, principal: null });
  vi.spyOn(api, 'socialMe').mockResolvedValue({ joined: false, profile: null });
  vi.spyOn(api, 'unreadMessages').mockResolvedValue({ unread: 0 });
  vi.spyOn(api, 'preparationAccess').mockResolvedValue(access());
  vi.spyOn(api, 'preparationCatalogue').mockResolvedValue(catalogue());
  vi.spyOn(api, 'preparationProgress').mockResolvedValue(progress());
  vi.spyOn(api, 'sharedRouteCurrent').mockImplementation(async id => ({ profile_id: id, revision: 0, view: null }));
  vi.spyOn(api, 'previewSharedRoute'); vi.spyOn(api, 'saveSharedRoute');
  vi.spyOn(api, 'preparationPlan').mockImplementation(async (id, resultId) => plan(id, resultId ?? null));
  state.value = { run: null, results: [], summary: null, error: null, clearError: vi.fn(), capabilities: null,
    cases: [caseRow('case-a')], savedProfile: profile('case-a'), dirty: false, hydrated: true, loading: false,
    caseEpoch: 0, paywall: null, newCase: vi.fn(), switchCase: vi.fn(), collectDocuments: vi.fn(), decide: vi.fn() };
});

describe('shared-route unsaved input remains protected by the native shell', () => {
  async function openDraft() {
    render(<App />); await flush();
    fireEvent.click(screen.getByTestId('nav-preparation'));
    await screen.findByRole('heading', { name: 'Prepare for your next step.' });
    fireEvent.click(within(screen.getByRole('navigation', { name: 'Preparation views' })).getByRole('button', { name: /^Shared route$/ }));
    const field = screen.getByLabelText('Minutes available each week across all exams');
    fireEvent.change(field, { target: { value: '145' } });
    return field;
  }
  it('cancels primary navigation even when the meaningful draft is durably journalled', async () => {
    const field = await openDraft();
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false);
    fireEvent.click(screen.getByTestId('nav-home'));
    expect(confirm).toHaveBeenCalledTimes(1);
    expect(window.location.hash).toBe('#/preparation');
    expect(field).toHaveValue(145);
    expect(screen.getByTestId('nav-preparation')).toHaveAttribute('aria-current', 'page');
    expect(api.previewSharedRoute).not.toHaveBeenCalled();
    expect(api.saveSharedRoute).not.toHaveBeenCalled();
  });
  it('guards switching cases and creating a new case before either store action is dispatched', async () => {
    state.value.cases = [caseRow('case-a'), caseRow('case-b')];
    const field = await openDraft();
    vi.spyOn(window, 'confirm').mockReturnValue(false);
    fireEvent.change(screen.getByLabelText('Applicant'), { target: { value: 'case-b' } });
    expect(state.value.switchCase).not.toHaveBeenCalled();
    expect(screen.getByLabelText('Applicant')).toHaveValue('case-a');
    fireEvent.click(screen.getByRole('button', { name: /^New case$/ }));
    expect(state.value.newCase).not.toHaveBeenCalled();
    expect(field).toHaveValue(145);
  });
  it('rolls back a cancelled direct legal hash before the private route form unmounts', async () => {
    const field = await openDraft();
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false);
    await act(async () => {
      window.history.pushState(null, '', '#/legal');
      window.dispatchEvent(new HashChangeEvent('hashchange'));
    });
    expect(confirm).toHaveBeenCalledTimes(1);
    expect(window.location.hash).toBe('#/preparation');
    expect(field).toHaveValue(145);
    expect(screen.queryByTestId('legal-draft')).not.toBeInTheDocument();
  });
  it('restores the same case journal after accepted navigation without an automatic preview or write', async () => {
    await openDraft();
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    fireEvent.click(screen.getByTestId('nav-home'));
    expect(await screen.findByRole('heading', { name: 'A clearer way forward.' })).toBeInTheDocument();
    fireEvent.click(screen.getByTestId('nav-preparation'));
    await screen.findByRole('heading', { name: 'Prepare for your next step.' });
    fireEvent.click(within(screen.getByRole('navigation', { name: 'Preparation views' })).getByRole('button', { name: /^Shared route$/ }));
    expect(screen.getByLabelText('Minutes available each week across all exams')).toHaveValue(145);
    await waitFor(() => expect(api.sharedRouteCurrent).toHaveBeenCalledWith('case-a'));
    expect(api.previewSharedRoute).not.toHaveBeenCalled();
    expect(api.saveSharedRoute).not.toHaveBeenCalled();
  });
  it('protects beforeunload while dirty and removes its risk token after accepted departure', async () => {
    render(<App />); await flush();
    const clean = new Event('beforeunload', { cancelable: true });
    fireEvent(window, clean); expect(clean.defaultPrevented).toBe(false);
    fireEvent.click(screen.getByTestId('nav-preparation'));
    await screen.findByRole('heading', { name: 'Prepare for your next step.' });
    fireEvent.click(within(screen.getByRole('navigation', { name: 'Preparation views' })).getByRole('button', { name: /^Shared route$/ }));
    fireEvent.change(screen.getByLabelText('Minutes available each week across all exams'), { target: { value: '145' } });
    const dirty = new Event('beforeunload', { cancelable: true });
    fireEvent(window, dirty); expect(dirty.defaultPrevented).toBe(true);
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    fireEvent.click(screen.getByTestId('nav-home'));
    await screen.findByRole('heading', { name: 'A clearer way forward.' });
    const departed = new Event('beforeunload', { cancelable: true });
    fireEvent(window, departed); expect(departed.defaultPrevented).toBe(false);
  });
  it('protects logout and failed-persistence typing without trying to log out or send a route', async () => {
    const field = await openDraft();
    const storage = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('Synthetic quota refusal'); });
    fireEvent.change(field, { target: { value: '160' } });
    expect(screen.getByText(/Browser recovery is unavailable/)).toBeInTheDocument();
    vi.spyOn(window, 'confirm').mockReturnValue(false);
    const logout = vi.spyOn(api, 'logout');
    fireEvent.click(screen.getByTestId('sign-out'));
    expect(logout).not.toHaveBeenCalled();
    expect(field).toHaveValue(160);
    const unload = new Event('beforeunload', { cancelable: true });
    fireEvent(window, unload); expect(unload.defaultPrevented).toBe(true);
    storage.mockRestore();
  });
});
afterEach(() => { expect(fetch).not.toHaveBeenCalled(); cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe('preparation entry points', () => {
  it('opens from primary navigation with address, selected state and native main focus', async () => {
    render(<App />); await flush();
    fireEvent.click(screen.getByTestId('nav-preparation'));
    expect(await screen.findByRole('heading', { name: 'Prepare for your next step.' })).toBeInTheDocument();
    expect(window.location.hash).toBe('#/preparation');
    expect(screen.getByRole('main', { name: 'Exam preparation' })).toHaveFocus();
    expect(screen.getByTestId('nav-preparation')).toHaveAttribute('aria-current', 'page');
  });
  it('supports a direct preparation address without requiring research results', async () => {
    window.location.hash = '#/preparation'; render(<App />);
    expect(await screen.findByRole('heading', { name: 'Prepare for your next step.' })).toBeInTheDocument();
    expect(await screen.findByText('Evidence: unknown')).toBeInTheDocument();
    expect(api.preparationPlan).toHaveBeenCalledWith('case-a', null);
  });
  it('opens from the Home path action without changing the real research next step', async () => {
    render(<App />); await flush();
    expect(screen.getByRole('button', { name: /Set preferences/ })).toBeInTheDocument();
    const homeActions = screen.getByRole('heading', { name: 'A clearer way forward.' }).closest('section')!;
    fireEvent.click(within(homeActions).getByRole('button', { name: /Exam preparation/ }));
    expect(await screen.findByRole('heading', { name: 'Prepare for your next step.' })).toBeInTheDocument();
    expect(window.location.hash).toBe('#/preparation');
  });
  it('opens selected programme goals from Plan while keeping document collection present', async () => {
    window.location.hash = '#/approved'; state.value.results = [result('selected-a', 'run-a')];
    render(<App />); await flush();
    expect(screen.getByTestId('collect-documents')).toBeEnabled();
    fireEvent.click(screen.getByRole('button', { name: 'Open exam goals & practice' }));
    await screen.findByRole('heading', { name: 'Prepare for your next step.' });
    expect(screen.getByLabelText('Programme evidence')).toHaveValue('selected-a');
    expect(api.preparationPlan).toHaveBeenCalledWith('case-a', 'selected-a');
    expect(state.value.collectDocuments).not.toHaveBeenCalled();
  });
  it('gives a safe save-case entry from empty Plan rather than fabricating requirements', async () => {
    window.location.hash = '#/approved'; state.value.savedProfile = null; render(<App />); await flush();
    fireEvent.click(screen.getByRole('button', { name: 'Explore exam preparation' }));
    expect(screen.getByText('Save or select an applicant case first')).toBeInTheDocument();
    expect(api.preparationPlan).not.toHaveBeenCalled(); expect(api.preparationCatalogue).not.toHaveBeenCalled();
  });
});
