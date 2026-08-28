/**
 * Typed API client.
 *
 * Errors carry the backend's `detail` message rather than a bare status code,
 * because every screen surfaces the reason a request failed instead of showing
 * an unexplained spinner.
 */

import type {
  Capabilities,
  ClaimOut,
  Conflict,
  ProfileValidationReport,
  ProgramResult,
  RunView,
  ShortlistSummary,
  StoredProfile,
  UserDecision,
} from '@/types';

export class ApiError extends Error {
  constructor(public status: number, message: string, public code?: string) {
    super(message);
    this.name = 'ApiError';
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    });
  } catch {
    // A network-level failure has no HTTP status; say what to check instead.
    throw new ApiError(0, 'Cannot reach the UniMatch API. Is the backend running on port 8099?');
  }

  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    let code: string | undefined;
    try {
      const body = await response.json();
      if (typeof body?.detail === 'string') detail = body.detail;
      else if (Array.isArray(body?.detail)) {
        detail = body.detail
          .map((d: { loc?: unknown[]; msg?: string }) => `${d.loc?.slice(1).join('.')}: ${d.msg}`)
          .join('; ');
      }
      code = body?.code;
    } catch {
      /* a non-JSON error body is still reported by status */
    }
    throw new ApiError(response.status, detail, code);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export const api = {
  health: () => request<{ status: string; demo_mode: boolean; schema_version: number }>('/api/health'),
  capabilities: () => request<Capabilities>('/api/capabilities'),
  vocabulary: () => request<Record<string, string[]>>('/api/vocabulary'),
  audit: () => request<Record<string, unknown>[]>('/api/audit?limit=100'),

  listProfiles: () => request<StoredProfile[]>('/api/profiles'),
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
};
