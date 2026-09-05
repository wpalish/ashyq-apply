/**
 * Typed API client.
 *
 * Errors carry the backend's `detail` message rather than a bare status code,
 * because every screen surfaces the reason a request failed instead of showing
 * an unexplained spinner.
 */

import type {
  Capabilities,
  ApplicantCase,
  AuthPrincipal,
  AuthStatus,
  ClaimOut,
  Conflict,
  EntitlementView,
  OrderView,
  PaymentMethod,
  Pricing,
  ProfileValidationReport,
  ProgramResult,
  RunView,
  ShortlistSummary,
  StoredProfile,
  UserDecision,
} from '@/types';

export class ApiError extends Error {
  /** Set only on a 402: which case to sell, and for how much. */
  profileId?: string;
  priceKzt?: number;
  /** Cases left on the organization's subscription, when a 402 reported one. */
  subscriptionCasesLeft?: number | null;

  constructor(public status: number, message: string, public code?: string) {
    super(message);
    this.name = 'ApiError';
  }
}

/** A 402 from a gated route, carrying everything the paywall needs to sell. */
export function isPaymentRequired(
  error: unknown,
): error is ApiError & { profileId: string; priceKzt: number } {
  return (
    error instanceof ApiError &&
    error.status === 402 &&
    error.code === 'payment_required' &&
    typeof error.profileId === 'string' &&
    typeof error.priceKzt === 'number'
  );
}

/** Build the error for a failed response. Shared so downloads report like calls. */
async function failureFrom(response: Response): Promise<ApiError> {
  let detail = `${response.status} ${response.statusText}`;
  let code: string | undefined;
  let profileId: string | undefined;
  let priceKzt: number | undefined;
  let casesLeft: number | null | undefined;
  try {
    const body = await response.json();
    if (typeof body?.detail === 'string') detail = body.detail;
    else if (Array.isArray(body?.detail)) {
      detail = body.detail
        .map((d: { loc?: unknown[]; msg?: string }) => `${d.loc?.slice(1).join('.')}: ${d.msg}`)
        .join('; ');
    }
    code = body?.code;
    // A 402 names the case to sell, its price, and whether the organization can
    // pay from a subscription instead. No other status carries these.
    if (typeof body?.profile_id === 'string') profileId = body.profile_id;
    if (typeof body?.price_kzt === 'number') priceKzt = body.price_kzt;
    if (typeof body?.subscription_cases_left === 'number') {
      casesLeft = body.subscription_cases_left;
    }
  } catch {
    /* a non-JSON error body is still reported by status */
  }
  const failure = new ApiError(response.status, detail, code);
  failure.profileId = profileId;
  failure.priceKzt = priceKzt;
  failure.subscriptionCasesLeft = casesLeft;
  return failure;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, {
      ...init,
      credentials: 'include',
      headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    });
  } catch {
    // A network-level failure has no HTTP status; say what to check instead.
    throw new ApiError(0, 'Cannot reach the UniMatch API. Is the backend running on port 8099?');
  }

  if (!response.ok) throw await failureFrom(response);

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export const api = {
  authStatus: () => request<AuthStatus>('/api/auth/status'),
  register: (payload: { email: string; password: string; display_name: string; organization_name: string }) =>
    request<AuthPrincipal>('/api/auth/register', { method: 'POST', body: JSON.stringify(payload) }),
  login: (email: string, password: string) =>
    request<AuthPrincipal>('/api/auth/login', {
      method: 'POST', body: JSON.stringify({ email, password }),
    }),
  logout: () => request<void>('/api/auth/logout', { method: 'POST' }),
  cases: () => request<ApplicantCase[]>('/api/cases'),
  health: () => request<{ status: string; demo_mode: boolean; schema_version: number }>('/api/health'),
  capabilities: () => request<Capabilities>('/api/capabilities'),
  vocabulary: () => request<Record<string, string[]>>('/api/vocabulary'),
  audit: () => request<Record<string, unknown>[]>('/api/audit?limit=100'),

  listProfiles: () => request<StoredProfile[]>('/api/profiles'),
  getProfile: (id: string) => request<StoredProfile>(`/api/profiles/${id}`),
  createProfile: (payload: unknown) =>
    request<StoredProfile>('/api/profiles', { method: 'POST', body: JSON.stringify(payload) }),
  updateProfile: (id: string, payload: unknown) =>
    request<StoredProfile>(`/api/profiles/${id}`, { method: 'PUT', body: JSON.stringify(payload) }),
  validateProfile: (payload: unknown) =>
    request<ProfileValidationReport>('/api/profiles/validate', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  exportProfile: (id: string) => request<Record<string, unknown>>(`/api/profiles/${id}/export`),
  deleteProfile: (id: string) => request<void>(`/api/profiles/${id}`, { method: 'DELETE' }),
  conversionMethods: (scale: string) =>
    request<{ methods: { key: string; description: string; source: string; caveat: string; to_scale: string }[]; note: string }>(
      `/api/profiles/conversions/methods?scale_label=${encodeURIComponent(scale)}`,
    ),

  startRun: (profileId: string, demoMode: boolean) =>
    request<RunView>('/api/runs', {
      method: 'POST',
      body: JSON.stringify({ profile_id: profileId, demo_mode: demoMode }),
    }),
  listRuns: () => request<RunView[]>('/api/runs'),
  getRun: (id: string) => request<RunView>(`/api/runs/${id}`),
  cancelRun: (id: string) => request<RunView>(`/api/runs/${id}/cancel`, { method: 'POST' }),
  retryRun: (id: string) => request<RunView>(`/api/runs/${id}/retry`, { method: 'POST' }),
  collectDocuments: (id: string) =>
    request<RunView>(`/api/runs/${id}/collect-documents`, { method: 'POST' }),

  results: (runId: string, filters: Record<string, string> = {}) => {
    const qs = new URLSearchParams(Object.entries(filters).filter(([, v]) => v)).toString();
    return request<ProgramResult[]>(`/api/runs/${runId}/results${qs ? `?${qs}` : ''}`);
  },
  summary: (runId: string) => request<ShortlistSummary>(`/api/runs/${runId}/summary`),
  claims: (runId: string) => request<ClaimOut[]>(`/api/runs/${runId}/claims`),
  conflicts: (runId: string) => request<Conflict[]>(`/api/runs/${runId}/conflicts`),
  questions: (runId: string) => request<Record<string, unknown>[]>(`/api/runs/${runId}/questions`),
  decide: (runId: string, resultId: string, decision: UserDecision, reason: string, notes: string) =>
    request<ProgramResult>(`/api/runs/${runId}/results/${resultId}/decision`, {
      method: 'POST',
      body: JSON.stringify({ decision, reason, notes }),
    }),

  exportUrl: (runId: string, fmt: 'csv' | 'json' | 'xlsx', decision?: string) =>
    `/api/runs/${runId}/export.${fmt}${decision ? `?decision=${decision}` : ''}`,

  /**
   * Download an export through the client rather than as a plain link.
   *
   * A bare <a href> bypasses this module entirely, so a 402 would render as
   * raw JSON in a new tab instead of raising the paywall. Fetching it means
   * the export fails the same way every other call does.
   */
  downloadExport: async (runId: string, fmt: 'csv' | 'json' | 'xlsx', decision?: string) => {
    const url = api.exportUrl(runId, fmt, decision);
    const response = await fetch(url, { credentials: 'include' });
    if (!response.ok) throw await failureFrom(response);

    const blob = await response.blob();
    const href = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = href;
    link.download = `unimatch-${runId.slice(0, 8)}${decision ? `-${decision}` : ''}.${fmt}`;
    document.body.append(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(href);
  },

  pricing: () => request<Pricing>('/api/billing/pricing'),
  entitlements: (profileId: string) =>
    request<EntitlementView>(
      `/api/billing/entitlements?profile_id=${encodeURIComponent(profileId)}`,
    ),
  // No price field: the server decides what a case costs.
  openOrder: (input: { profile_id: string; method: PaymentMethod; phone?: string }) =>
    request<OrderView>('/api/billing/orders', { method: 'POST', body: JSON.stringify(input) }),
  unlockFromSubscription: (profileId: string) =>
    request<EntitlementView>('/api/billing/unlock-from-subscription', {
      method: 'POST',
      body: JSON.stringify({ profile_id: profileId }),
    }),
  readOrder: (orderId: string) => request<OrderView>(`/api/billing/orders/${orderId}`),
  cancelOrder: (orderId: string) =>
    request<OrderView>(`/api/billing/orders/${orderId}/cancel`, { method: 'POST' }),
};
