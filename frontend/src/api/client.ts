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
  ConversationView,
  FeedFilters,
  MessagePage,
  MessageView,
  MyProfile,
  Page,
  PeopleFilters,
  PersonCard,
  PostView,
  ProfileInput,
  ProfileValidationReport,
  ProgramResult,
  ReplyView,
  ReporterRef,
  ReportReason,
  ReportStatus,
  ReportTarget,
  ReportView,
  RunView,
  ShortlistSummary,
  StoredProfile,
  TranscriptReading,
  UserDecision,
} from '@/types';

/** Drop empty filters, then build the query string. `?city=` matches nothing. */
function query(params: Record<string, string | null | undefined>): string {
  const pairs = Object.entries(params).filter(([, value]) => value);
  if (pairs.length === 0) return '';
  return `?${new URLSearchParams(pairs as [string, string][]).toString()}`;
}

export class ApiError extends Error {
  constructor(public status: number, message: string, public code?: string) {
    super(message);
    this.name = 'ApiError';
  }
}

/**
 * The same request, with the response headers kept.
 *
 * Paged endpoints put the whole count in `X-Total-Count`, which `request`
 * throws away with the rest of the response. Reaching for a bare `fetch` to
 * read one header is how this codebase previously ended up writing `{detail}`
 * into an applicant's profile, so the header-reading path goes through the
 * same error handling as everything else.
 */
async function requestWithHeaders<T>(
  path: string,
  init?: RequestInit,
): Promise<{ body: T; headers: Headers }> {
  let response: Response;
  try {
    response = await fetch(path, {
      ...init,
      credentials: 'include',
      headers: {
        // A multipart upload must be left to the browser: it appends the
        // boundary to the content type, and a hand-written header omits it,
        // which makes the body unparseable at the other end.
        ...(init?.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
        ...(init?.headers ?? {}),
      },
    });
  } catch {
    // A network-level failure has no HTTP status; say what to check instead.
    throw new ApiError(0, 'Cannot reach the ASHYQ Apply API. Is the backend running on port 8099?');
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

  if (response.status === 204) return { body: undefined as T, headers: response.headers };
  return { body: (await response.json()) as T, headers: response.headers };
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  return (await requestWithHeaders<T>(path, init)).body;
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
  changePassword: (currentPassword: string, newPassword: string) =>
    request<AuthPrincipal>('/api/auth/password', {
      method: 'POST',
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    }),
  // The answer is the same whether or not the address has an account, so the
  // form can never be used to find out who is registered.
  requestPasswordReset: (email: string) =>
    request<{ detail: string; reset_link?: string }>('/api/auth/password/reset-request', {
      method: 'POST',
      body: JSON.stringify({ email }),
    }),
  confirmPasswordReset: (token: string, newPassword: string) =>
    request<AuthPrincipal>('/api/auth/password/reset', {
      method: 'POST',
      body: JSON.stringify({ token, new_password: newPassword }),
    }),
  organizations: () =>
    request<{ id: string; name: string; role: string; current: boolean }[]>(
      '/api/auth/organizations',
    ),
  switchOrganization: (organizationId: string) =>
    request<AuthPrincipal>('/api/auth/session/organization', {
      method: 'POST',
      body: JSON.stringify({ organization_id: organizationId }),
    }),
  deleteAccount: (password: string, confirmDeleteData: boolean) =>
    request<void>('/api/auth/me/delete', {
      method: 'POST',
      body: JSON.stringify({ password, confirm_delete_data: confirmDeleteData }),
    }),
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
  /**
   * Read a transcript PDF into suggestions. The answer is never applied here:
   * the screen shows each one with the line it was read from, and the
   * applicant decides — the same contract as a grade conversion.
   */
  readTranscript: (file: File) => {
    const form = new FormData();
    form.append('file', file);
    return request<TranscriptReading>('/api/profiles/transcript', { method: 'POST', body: form });
  },
  deleteProfile: (id: string) => request<void>(`/api/profiles/${id}`, { method: 'DELETE' }),
  // Typed, and error-checked: ProfileScreen used a bare fetch().then(json)
  // here, so a 400 wrote {detail: "..."} into the applicant's GPA field.
  previewConversion: (grade: unknown, methodKey: string) =>
    request<Record<string, unknown>>(
      `/api/profiles/conversions/preview?method_key=${encodeURIComponent(methodKey)}`,
      { method: 'POST', body: JSON.stringify(grade) },
    ),

  conversionMethods: (scale: string) =>
    request<{ methods: { key: string; description: string; source: string; caveat: string; to_scale: string }[]; note: string }>(
      `/api/profiles/conversions/methods?scale_label=${encodeURIComponent(scale)}`,
    ),

  // The key makes a retried request replay its own run instead of starting a
  // second one; the caller keeps it stable for as long as one click lasts.
  startRun: (profileId: string, demoMode: boolean, idempotencyKey?: string) =>
    request<RunView>('/api/runs', {
      method: 'POST',
      body: JSON.stringify({ profile_id: profileId, demo_mode: demoMode }),
      headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {},
    }),
  // Filtered server-side: switchCase used to pull fifty runs across every
  // applicant and search them in the browser for the one it wanted.
  listRuns: (profileId?: string, limit = 50) =>
    request<RunView[]>(
      `/api/runs?limit=${limit}${profileId ? `&profile_id=${encodeURIComponent(profileId)}` : ''}`,
    ),
  getRun: (id: string) => request<RunView>(`/api/runs/${id}`),
  cancelRun: (id: string) => request<RunView>(`/api/runs/${id}/cancel`, { method: 'POST' }),
  // Without a stage the server resets every stage; with one it resets that
  // stage and everything after it. The two buttons in ProgressScreen are the
  // two calls, so the label the user reads matches what actually happens.
  retryRun: (id: string, stage?: string) =>
    request<RunView>(`/api/runs/${id}/retry${stage ? `?stage=${encodeURIComponent(stage)}` : ''}`, {
      method: 'POST',
    }),
  recheckNow: (id: string) => request<RunView>(`/api/runs/${id}/recheck`, { method: 'POST' }),
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

  // A note is not a decision: this route leaves user_decision and decided_at
  // alone, which the decision endpoint cannot.
  saveNotes: (runId: string, resultId: string, notes: string) =>
    request<ProgramResult>(`/api/runs/${runId}/results/${resultId}/notes`, {
      method: 'PATCH',
      body: JSON.stringify({ notes }),
    }),

  // A deadline in a table is something to remember; in a calendar it reminds
  // you. Only confirmed dates become events.
  deadlinesUrl: (runId: string) => `/api/runs/${runId}/deadlines.ics`,

  /**
   * How many jobs of this workspace the queue gave up on.
   *
   * Only the count is fetched — one row, and the total from the header — so
   * the screen can say that something needs attention without pulling a page
   * of job rows nobody has asked to see yet.
   */
  deadJobCount: async (): Promise<number> => {
    const { headers } = await requestWithHeaders<unknown[]>('/api/admin/jobs?status=dead&limit=1');
    return Number(headers.get('X-Total-Count') ?? 0);
  },

  exportUrl: (runId: string, fmt: 'csv' | 'json' | 'xlsx', decision?: string) =>
    `/api/runs/${runId}/export.${fmt}${decision ? `?decision=${decision}` : ''}`,

  // --- Community ---
  // Paging is a cursor, never an offset: two posts written in the same second
  // would make an offset page repeat one and drop the other.
  socialMe: () => request<MyProfile>('/api/social/me'),
  leaveCommunity: () => request<void>('/api/social/me', { method: 'DELETE' }),

  // --- Blocking and moderation ---
  // Multipart, so the content type is left to the browser: it appends the
  // boundary, and a hand-written header omits it.
  uploadAvatar: (file: File) => {
    const form = new FormData();
    form.append('file', file);
    return request<void>('/api/social/me/avatar', { method: 'PUT', body: form });
  },
  deleteAvatar: () => request<void>('/api/social/me/avatar', { method: 'DELETE' }),

  blockedPeople: () => request<{ items: ReporterRef[] }>('/api/social/blocks'),
  blockPerson: (userId: string) =>
    request<void>(`/api/social/blocks/${userId}`, { method: 'POST' }),
  unblockPerson: (userId: string) =>
    request<void>(`/api/social/blocks/${userId}`, { method: 'DELETE' }),
  reportContent: (payload: {
    subject_type: ReportTarget;
    subject_id: string;
    reason: ReportReason;
    note: string;
  }) => request<ReportView>('/api/social/reports', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  moderationQueue: (status: ReportStatus = 'open', cursor?: string | null) =>
    request<Page<ReportView>>(`/api/social/moderation/reports${query({ status, cursor })}`),
  resolveReport: (reportId: string, action: 'remove' | 'dismiss', note: string) =>
    request<ReportView>(`/api/social/moderation/reports/${reportId}`, {
      method: 'POST',
      body: JSON.stringify({ action, note }),
    }),
  conversations: (cursor?: string | null) =>
    request<Page<ConversationView>>(`/api/social/messages${query({ cursor })}`),
  // One number for the badge, so the navigation costs one request rather than
  // one per conversation.
  unreadMessages: () => request<{ unread: number }>('/api/social/messages/unread'),
  conversation: (userId: string, cursor?: string | null) =>
    request<MessagePage>(`/api/social/messages/${userId}${query({ cursor })}`),
  sendMessage: (userId: string, body: string) =>
    request<MessageView>(`/api/social/messages/${userId}`, {
      method: 'POST',
      body: JSON.stringify({ body }),
    }),
  saveSocialProfile: (payload: ProfileInput) =>
    request<PersonCard>('/api/social/me', { method: 'PUT', body: JSON.stringify(payload) }),
  people: (filters: PeopleFilters = {}, cursor?: string | null) =>
    request<Page<PersonCard>>(`/api/social/people${query({ ...filters, cursor })}`),
  person: (userId: string) => request<PersonCard>(`/api/social/people/${userId}`),
  feed: (filters: FeedFilters = {}, cursor?: string | null) =>
    request<Page<PostView>>(`/api/social/feed${query({ ...filters, cursor })}`),
  createPost: (body: string) =>
    request<PostView>('/api/social/posts', { method: 'POST', body: JSON.stringify({ body }) }),
  thread: (postId: string, cursor?: string | null) =>
    request<Page<ReplyView>>(`/api/social/posts/${postId}/replies${query({ cursor })}`),
  deletePost: (postId: string) =>
    request<void>(`/api/social/posts/${postId}`, { method: 'DELETE' }),
  deleteReply: (postId: string, replyId: string) =>
    request<void>(`/api/social/posts/${postId}/replies/${replyId}`, { method: 'DELETE' }),
  createReply: (postId: string, body: string) =>
    request<ReplyView>(`/api/social/posts/${postId}/replies`, {
      method: 'POST',
      body: JSON.stringify({ body }),
    }),
};
