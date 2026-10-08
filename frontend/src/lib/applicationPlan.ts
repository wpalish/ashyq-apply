import type { ClaimOut, DocumentItem, ProgramResult } from '@/types';

export type PlanStatus = 'not_collected' | 'needs_review' | 'preparing' | 'review_submission';

export interface PlanDocument {
  progressId: string;
  item: DocumentItem;
  completed: boolean;
  blocked: boolean;
  blockedDependencies: string[];
}

export interface ProgrammePlan {
  resultId: string;
  university: string;
  program: string;
  decision: 'approved' | 'maybe';
  items: PlanDocument[];
  total: number;
  prepared: number;
  pendingRequiredIds: string[];
  pendingOptionalIds: string[];
  nextItem: PlanDocument | null;
  status: PlanStatus;
  confirmedAdmissionDeadline: string | null;
  deadlineSourceUrl: string | null;
  reviewReasons: string[];
  untracked: number;
}

// The backend already sends this optional published scope. Keep it local to
// this selector until the rest of the frontend contract uses it too.
interface PublishedScope {
  university?: string | null;
  faculty?: string | null;
  programme?: string | null;
  degree?: string | null;
  intake?: string | null;
  academic_year?: string | null;
  population?: string | null;
  nationality?: string | null;
  residency?: string | null;
  qualification?: string | null;
}

type ScopedClaim = ClaimOut & { scope?: PublishedScope | null };

const OWNER_ORDER: Record<DocumentItem['owner'], number> = {
  recommender: 0, school: 1, third_party: 2, applicant: 3,
};

const normalized = (value: unknown): string =>
  typeof value === 'string' ? value.trim().replace(/\s+/gu, ' ').toLocaleLowerCase('en') : '';

const compare = (left: string, right: string): number => left < right ? -1 : left > right ? 1 : 0;

function isoDay(value: unknown): value is string {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/u.test(value)) return false;
  const parsed = new Date(`${value}T00:00:00Z`);
  return Number.isFinite(parsed.getTime()) && parsed.toISOString().slice(0, 10) === value;
}

function officialPage(value: string | null | undefined): boolean {
  if (!value) return false;
  try {
    const url = new URL(value);
    return (url.protocol === 'https:' || url.protocol === 'http:') && !url.username && !url.password;
  } catch { return false; }
}

function currentDeadlineClaim(claim: ScopedClaim, result: ProgramResult): boolean {
  const scope = claim.scope;
  if (claim.claim_type !== 'admission_deadline' || claim.status !== 'VERIFIED_CURRENT'
    || claim.is_stale !== false || !claim.official_domain || !officialPage(claim.source_url)
    || !isoDay(claim.normalized_value) || !scope) return false;
  // The result carries no applicant population. A published population,
  // residency, qualification or nationality cannot be matched from it.
  if (['faculty', 'academic_year', 'population', 'nationality', 'residency', 'qualification']
    .some((key) => normalized(scope[key as keyof PublishedScope]))) return false;
  if (!normalized(result.intake) || normalized(scope.intake) !== normalized(result.intake)
    || !normalized(result.degree) || normalized(scope.degree) !== normalized(result.degree)) return false;
  if (scope.university && normalized(scope.university) !== normalized(result.university)
    && normalized(scope.university) !== normalized(result.university_id)) return false;
  if (scope.programme && normalized(scope.programme) !== normalized(result.program)) return false;
  if (!normalized(result.program) || normalized(claim.program) !== normalized(result.program)
    || (claim.intake && normalized(claim.intake) !== normalized(result.intake))) return false;
  // A programme page accepted by the pipeline supplies programme identity;
  // a university-wide page with no published programme does not.
  return Boolean(normalized(scope.programme))
    || claim.source_specificity === 'program_intake' || claim.source_specificity === 'program';
}

function confirmedDeadline(result: ProgramResult, today: string): ScopedClaim | null {
  if (!isoDay(today) || !isoDay(result.admission_deadline)
    || result.admission_deadline < today || result.deadline_passed
    || result.conflicts?.some((conflict) => conflict.unresolved && conflict.claim_type === 'admission_deadline')) return null;
  const candidates = (result.claims ?? []).filter((claim) => currentDeadlineClaim(claim, result));
  // Two current scoped dates are an ambiguity even if no conflict was stored.
  const dates = new Set(candidates.map((claim) => claim.normalized_value));
  if (dates.size !== 1 || !dates.has(result.admission_deadline)) return null;
  return [...candidates].sort((a, b) => compare(a.id, b.id))[0] ?? null;
}

function leadDays(item: DocumentItem): number {
  const value = item.lead_time_days;
  return typeof value === 'number' && Number.isFinite(value) && value > 0 ? value : 0;
}

function orderItems(left: PlanDocument, right: PlanDocument): number {
  return Number(right.item.required) - Number(left.item.required)
    || leadDays(right.item) - leadDays(left.item)
    || (OWNER_ORDER[left.item.owner] ?? 4) - (OWNER_ORDER[right.item.owner] ?? 4)
    || compare(left.progressId, right.progressId);
}

/** Saved preparation only. No network, persistence or inferred readiness. */
export function deriveApplicationPlan(results: ProgramResult[], today: string): ProgrammePlan[] {
  return results.flatMap((result): ProgrammePlan[] => {
    const decision = result.user_decision;
    if (decision !== 'approved' && decision !== 'maybe') return [];

    const checklist = result.checklist;
    const unique = new Map<string, PlanDocument>();
    let untracked = 0;
    if (checklist) {
      for (const item of [
        ...(checklist.admission_documents ?? []), ...(checklist.scholarship_documents ?? []),
        ...(checklist.recommender_actions ?? []), ...(checklist.school_actions ?? []),
        ...(checklist.certification_actions ?? []), ...(checklist.applicant_actions ?? []),
      ]) {
        const progressId = item.progress_id;
        if (!progressId?.trim()) { untracked += 1; continue; }
        if (unique.has(progressId)) continue;
        unique.set(progressId, {
          progressId, item, completed: result.document_progress?.[progressId] === true,
          blocked: false, blockedDependencies: [],
        });
      }
    }
    const items = [...unique.values()];
    const byName = new Map<string, PlanDocument[]>();
    for (const doc of items) {
      const name = normalized(doc.item.name);
      byName.set(name, [...(byName.get(name) ?? []), doc]);
    }
    const resolvedDependency = (dependency: string, path: Set<string>): boolean => {
      const name = normalized(dependency);
      const named = byName.get(name) ?? [];
      const target = named[0];
      // Names are the backend contract. No fuzzy matching, and an absent
      // milestone such as an admission offer is not an accomplished step.
      if (!name || named.length !== 1 || !target || !target.completed || path.has(target.progressId)) return false;
      const nextPath = new Set(path).add(target.progressId);
      return (target.item.depends_on ?? []).every((prior) => resolvedDependency(prior, nextPath));
    };
    for (const doc of items) {
      doc.blockedDependencies = (doc.item.depends_on ?? []).filter((dependency) =>
        !resolvedDependency(dependency, new Set([doc.progressId])));
      doc.blocked = doc.blockedDependencies.length > 0;
    }
    items.sort(orderItems);
    const pending = items.filter((doc) => !doc.completed);
    const pendingRequiredIds = pending.filter((doc) => doc.item.required).map((doc) => doc.progressId);
    const pendingOptionalIds = pending.filter((doc) => !doc.item.required).map((doc) => doc.progressId);
    const nextItem = pending.find((doc) => !doc.blocked) ?? null;
    const questions = [...(checklist?.unresolved ?? []), ...(result.unresolved ?? [])];
    const conflicts = (result.conflicts ?? []).filter((conflict) => conflict.unresolved);
    const reviewReasons: string[] = [];
    if (checklist && checklist.completeness !== 'official') reviewReasons.push('The official requirements list is incomplete or unavailable.');
    if (checklist && items.length === 0) reviewReasons.push('No tracked document requirements have been confirmed.');
    if (untracked > 0) reviewReasons.push('Some document requirements have no saved progress identity.');
    if (questions.length > 0) reviewReasons.push(`${questions.length} unresolved source question${questions.length === 1 ? '' : 's'}.`);
    if (conflicts.length > 0) reviewReasons.push(`${conflicts.length} unresolved source conflict${conflicts.length === 1 ? '' : 's'}.`);
    if (items.some((doc) => doc.item.required && doc.blocked)) reviewReasons.push('Required tasks have unmet or unconfirmed prerequisites.');

    const needsReview = Boolean(checklist && (checklist.completeness !== 'official'
      || items.length === 0 || untracked > 0 || conflicts.length > 0 || questions.some((question) => question.blocking)
      || items.some((doc) => doc.item.required && doc.blocked && doc.completed)
      || (pendingRequiredIds.length > 0 && !pending.some((doc) => doc.item.required && !doc.blocked))
      || (!nextItem && (questions.length > 0 || items.some((doc) => doc.blocked)))));
    const status: PlanStatus = !checklist ? 'not_collected' : needsReview ? 'needs_review'
      : nextItem ? 'preparing' : 'review_submission';
    const deadline = confirmedDeadline(result, today);
    return [{
      resultId: result.id, university: result.university, program: result.program, decision,
      items, total: items.length, prepared: items.filter((doc) => doc.completed).length,
      pendingRequiredIds, pendingOptionalIds, nextItem, status,
      confirmedAdmissionDeadline: deadline ? result.admission_deadline : null,
      deadlineSourceUrl: deadline?.source_url ?? null, reviewReasons, untracked,
    }];
  }).sort((left, right) => Number(right.decision === 'approved') - Number(left.decision === 'approved')
    || compare(left.university, right.university) || compare(left.program, right.program) || compare(left.resultId, right.resultId));
}
