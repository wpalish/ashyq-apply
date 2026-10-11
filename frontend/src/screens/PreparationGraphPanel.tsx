import { useEffect, useRef, useState, useSyncExternalStore } from 'react';
import { api } from '@/api/client';
import { Panel, SourceLink } from '@/components/primitives';
import { getLocale, subscribe, t, type MessageKey } from '@/lib/i18n';
import type {
  ClaimScope, GraphClaimProof, GraphDocumentAction, GraphPolicyGroup,
  GraphProgrammeProjection, GraphReasonCode, GraphRequirementAtom,
  GraphScopeProof, PreparationGraph, ProgramResult,
} from '@/types';

interface Props {
  profileId: string;
  programmes: ProgramResult[];
  isCurrent: () => boolean;
}

const same = (a: unknown, b: readonly string[]): boolean =>
  Array.isArray(a) && a.length === b.length && a.every((value, index) => value === b[index]);
const eligibleDecision = (value: string) => value === 'approved' || value === 'maybe';
const values = (value: unknown): string => {
  if (value == null || value === '') return t('graph.none');
  if (Array.isArray(value)) return value.map(values).join('; ') || t('graph.none');
  if (typeof value === 'object') return Object.entries(value)
    .map(([key, item]) => `${key.replace(/_/g, ' ')}: ${values(item)}`).join('; ') || t('graph.none');
  return String(value);
};
const scopeText = (scope: ClaimScope | null): string => scope
  ? Object.entries(scope).filter(([, value]) => value).map(([key, value]) => `${key.replace(/_/g, ' ')}: ${value}`).join(' · ') || t('graph.none')
  : t('graph.scopeUnknown');

function reasonKey(reason: GraphReasonCode): MessageKey {
  if (reason === 'research_locked' || reason.startsWith('evidence_') || reason === 'checks_missing') return 'graph.reasonEvidence';
  if (reason.startsWith('scope_') || reason.startsWith('document_scope_')) return 'graph.reasonScope';
  if (reason.includes('claim_reference') || reason === 'legacy_url_ambiguous') return 'graph.reasonSource';
  if (reason.startsWith('dependency_')) return 'graph.reasonDependency';
  if (reason.startsWith('checklist_') || reason.startsWith('document_')) return 'graph.reasonDocument';
  if (reason.startsWith('exam_')) return 'graph.reasonExam';
  if (reason.startsWith('scholarship_')) return 'graph.reasonScholarship';
  if (reason === 'non_exam_checks_not_projected') return 'graph.reasonNotProjected';
  if (reason === 'requirement_purpose_unestablished') return 'graph.reasonPurpose';
  if (reason.includes('policy') || reason.includes('waiver') || reason.includes('alternatives')) return 'graph.reasonPolicy';
  return 'graph.reasonOther';
}
const stateKey = (state: string): MessageKey => {
  switch (state) {
    case 'current': return 'graph.stateCurrent';
    case 'stale': return 'graph.stateStale';
    case 'conflicted': return 'graph.stateConflicted';
    case 'locked': return 'graph.stateLocked';
    case 'projected': return 'graph.stateProjected';
    case 'partial': return 'graph.statePartial';
    case 'unavailable': return 'graph.stateUnavailable';
    default: return 'graph.stateUnknown';
  }
};
const policyText = (policy: string): string => {
  if (policy === 'waiver_check') return t('graph.waiver');
  if (policy === 'alternatives_unresolved') return t('graph.alternatives');
  if (policy === 'unknown') return t('graph.policyUnknown');
  // The native per-atom label is deliberately separate from any cross-programme relation.
  return policy === 'required' ? t('graph.policyRequired') : t('graph.policyOptional');
};
const decisionText = (decision: string) => t(decision === 'approved' ? 'graph.decisionApproved' : 'graph.decisionMaybe');
const dependencyText = (resolution: string) => {
  switch (resolution) {
    case 'linked': return t('graph.dependencyLinked');
    case 'missing': return t('graph.dependencyMissing');
    case 'ambiguous': return t('graph.dependencyAmbiguous');
    case 'scope_unresolved': return t('graph.dependencyScope');
    default: return t('graph.dependencyCycle');
  }
};
const checkText = (status: string) => t(({
  MET: 'graph.checkMet', PENDING: 'graph.checkPending', GAP: 'graph.checkGap',
  NOT_APPLICABLE: 'graph.checkNotApplicable', NEEDS_OFFICIAL_CLARIFICATION: 'graph.checkClarify',
} as Record<string, MessageKey>)[status] ?? 'graph.checkClarify');
const claimText = (status: string) => t(({
  VERIFIED_CURRENT: 'graph.claimCurrent', POSSIBLY_STALE: 'graph.claimStale',
  CONFLICTING: 'graph.claimConflict', UNVERIFIED: 'graph.claimUnverified',
  NOT_FOUND: 'graph.claimNotFound', NEEDS_OFFICIAL_CLARIFICATION: 'graph.claimClarify',
  SUPERSEDED: 'graph.claimSuperseded',
} as Record<string, MessageKey>)[status] ?? 'graph.claimUnverified');
const ownerText = (owner: string) => t(({
  applicant: 'graph.ownerApplicant', school: 'graph.ownerSchool',
  recommender: 'graph.ownerRecommender', third_party: 'graph.ownerThirdParty',
} as Record<string, MessageKey>)[owner] ?? 'graph.ownerThirdParty');
const locationText = (location: string) => t(({
  admission_documents: 'graph.locationAdmission', scholarship_documents: 'graph.locationScholarship',
  applicant_actions: 'graph.locationApplicant', school_actions: 'graph.locationSchool',
  recommender_actions: 'graph.locationRecommender', certification_actions: 'graph.locationCertification',
} as Record<string, MessageKey>)[location] ?? 'graph.reasonOther');
const identityText = (dimension: string) => t(({
  edition: 'graph.identityEdition', accepted_variant: 'graph.identityVariant',
  retake_policy: 'graph.identityRetake', route: 'graph.identityRoute',
} as Record<string, MessageKey>)[dimension] ?? 'graph.reasonOther');
const documentPurpose = (purpose: string) => t(purpose === 'scholarship' ? 'graph.purposeScholarship'
  : purpose === 'both' ? 'graph.purposeBoth' : 'graph.purposeAdmission');

/** Reject an incomplete, re-ordered, foreign or cross-linked response before any cards render. */
export function matchesGraph(graph: PreparationGraph, profileId: string, ids: readonly string[], eligibleIds: ReadonlySet<string>): boolean {
  if (graph.schema_version !== 'preparation-graph-v1' || graph.profile_id !== profileId
    || graph.selection_source !== 'server_verified_owned_explicit'
    || !same(graph.requested_result_ids, ids) || !same(graph.selected_result_ids, ids)
    || !Array.isArray(graph.programmes) || !same(graph.programmes.map(item => item.result_id), ids)
    || !Array.isArray(graph.source_manifest) || !same(graph.source_manifest.map(item => item.result_id), ids)
    || !Array.isArray(graph.requirements) || !Array.isArray(graph.document_actions)
    || !Array.isArray(graph.policy_groups) || !Array.isArray(graph.exam_workstreams)
    || ids.some(id => !eligibleIds.has(id)) || new Set(ids).size !== ids.length) return false;
  const ownerByRequirement = new Map<string, string>();
  const ownerByDocument = new Map<string, string>();
  for (const atom of graph.requirements) {
    if (ownerByRequirement.has(atom.id) || !eligibleIds.has(atom.result_id)) return false;
    ownerByRequirement.set(atom.id, atom.result_id);
  }
  for (const item of graph.document_actions) {
    if (ownerByDocument.has(item.id) || !eligibleIds.has(item.result_id)) return false;
    ownerByDocument.set(item.id, item.result_id);
  }
  const linkedRequirements: string[] = []; const linkedDocuments: string[] = [];
  for (const [index, programme] of graph.programmes.entries()) {
    const manifest = graph.source_manifest[index];
    if (!manifest) return false;
    if (!eligibleDecision(programme.user_decision)) return false;
    const locked = !programme.research_access || programme.evidence_state === 'locked' || programme.projection_state === 'locked';
    if (locked && (programme.research_access || programme.evidence_state !== 'locked' || programme.projection_state !== 'locked'
      || programme.run_id !== null || programme.university !== null || programme.programme !== null
      || programme.requested_scope !== null || programme.requirement_ids.length || programme.document_action_ids.length
      || programme.unprojected_checks.length || programme.unresolved_questions.length
      || !same(programme.unresolved_reasons, ['research_locked'])
      || manifest.run_id !== null || manifest.result_snapshot_digest !== null
      || manifest.authoritative_evidence_digest !== null || manifest.resolved_claim_ids.length)) return false;
    for (const id of programme.requirement_ids) {
      if (ownerByRequirement.get(id) !== programme.result_id) return false;
      linkedRequirements.push(id);
    }
    for (const id of programme.document_action_ids) {
      if (ownerByDocument.get(id) !== programme.result_id) return false;
      linkedDocuments.push(id);
    }
  }
  if (linkedRequirements.length !== ownerByRequirement.size || new Set(linkedRequirements).size !== ownerByRequirement.size
    || linkedDocuments.length !== ownerByDocument.size || new Set(linkedDocuments).size !== ownerByDocument.size) return false;
  if (graph.policy_groups.some(group => !eligibleIds.has(group.result_id) || !group.requirement_ids.length
    || group.requirement_ids.some(id => ownerByRequirement.get(id) !== group.result_id))) return false;
  if (graph.exam_workstreams.some(stream => !stream.requirement_ids.length
    || stream.grouping !== 'family_only' || stream.identity_state !== 'unknown' || stream.edition !== null
    || stream.requirement_ids.some(id => !ownerByRequirement.has(id))
    || !same(stream.contributing_result_ids, ids.filter(id => stream.requirement_ids.some(key => ownerByRequirement.get(key) === id))))) return false;
  if (graph.document_actions.some(item => item.dependencies.some(dep => dep.target_document_id !== null
    && ownerByDocument.get(dep.target_document_id) !== item.result_id))) return false;
  return true;
}

function Reasons({ reasons }: { reasons: GraphReasonCode[] }) {
  if (!reasons.length) return null;
  return <div className="stack stack--tight"><strong>{t('graph.unresolved')}</strong>
    <ul>{[...new Set(reasons.map(reasonKey))].map(key => <li key={key}>{t(key)}</li>)}</ul>
  </div>;
}

function Scope({ proof }: { proof: GraphScopeProof }) {
  return <div className="stack stack--tight">
    <p className="small"><strong>{t('graph.scope')}:</strong> {proof.verdict === 'yes' ? t('graph.scopeYes')
      : proof.verdict === 'no' ? t('graph.scopeNo') : t('graph.scopeUnknown')}</p>
    <p className="xs muted">{scopeText(proof.published)}</p>
    {!!proof.gaps.length && <p className="xs muted">{t('graph.gaps')}: {proof.gaps.join(', ')}</p>}
    {!!proof.contradictions.length && <p className="xs muted">{t('graph.contradictions')}: {proof.contradictions.join(', ')}</p>}
  </div>;
}

function Proofs({ proofs }: { proofs: GraphClaimProof[] }) {
  if (!proofs.length) return <p className="small muted">{t('graph.noExactProof')}</p>;
  return <div className="stack stack--tight">{proofs.map(({ claim, scope }) => <div key={claim.id} className="panel panel--sunken stack stack--tight">
    <p className="small">{claim.original_text_excerpt}</p>
    <p className="xs muted">{claim.page_title} · {claim.relevant_section} · {claim.accessed_at}</p>
    <p className="xs muted">{t('graph.storedVerification')}: {claimText(claim.status)}</p>
    <p className="xs muted">{t('graph.freshness')}: {claim.is_stale ? t('graph.freshnessStale') : t('graph.freshnessNotMarked')} · {t('graph.ageDays')}: {claim.age_days}</p>
    <SourceLink url={claim.source_url} />
    <Scope proof={scope} />
  </div>)}</div>;
}

function Requirement({ atom }: { atom: GraphRequirementAtom }) {
  const check = atom.original_check;
  return <section className="panel panel--sunken stack stack--tight" aria-label={check.requirement}>
    <h5>{check.requirement}</h5>
    <p className="xs muted">{atom.purpose === 'admission' ? t('graph.purposeAdmission')
      : `${t('graph.purposeScholarship')}: ${atom.scholarship_subject || atom.scholarship_id || t('graph.none')}`}</p>
    <p className="small">{t('graph.published')}: {values(check.published_value)}</p>
    <p className="small">{t('graph.applicant')}: {check.applicant_value == null ? t('graph.notEntered') : values(check.applicant_value)}</p>
    <p className="small">{t('graph.savedStatus')}: {checkText(check.status)} · {t('graph.evidence')}: {t(stateKey(atom.evidence_state))}</p>
    <p className="small">{check.explanation}</p>
    <p className="small">{t('graph.policy')}: {policyText(atom.policy)}</p>
    <p className="xs muted">{t('graph.scope')}: {check.published_scope || t('graph.scopeUnknown')}</p>
    <Reasons reasons={atom.unresolved_reasons} />
    <details><summary>{t('graph.source')}</summary>
      <p className="xs">{t('graph.originalRefs')}: {atom.original_reference_ids.join(', ') || t('graph.none')}</p>
      <p className="xs">{t('graph.resolvedRefs')}: {atom.resolved_claim_ids.join(', ') || t('graph.none')}</p>
      <Proofs proofs={atom.proofs} />
      {atom.source_urls.filter(url => !atom.proofs.some(proof => proof.claim.source_url === url)).map(url => <SourceLink key={url} url={url} />)}
    </details>
  </section>;
}

function requirementContext(atom: GraphRequirementAtom): string {
  return `${atom.original_check.requirement} · ${atom.purpose === 'admission' ? t('graph.purposeAdmission')
    : `${t('graph.purposeScholarship')}: ${atom.scholarship_subject || atom.scholarship_id || t('graph.none')}`}`;
}

function Group({ group, atoms }: { group: GraphPolicyGroup; atoms: GraphRequirementAtom[] }) {
  return <section className="panel panel--sunken stack stack--tight">
    <p>{group.kind === 'waiver_check' ? t('graph.waiver') : group.kind === 'alternatives_unresolved'
      ? t('graph.alternatives') : t('graph.policyUnknown')}</p>
    <p className="xs muted">{group.purpose === 'admission' ? t('graph.purposeAdmission')
      : `${t('graph.purposeScholarship')}: ${group.scholarship_id || t('graph.none')}`}</p>
    <ul>{atoms.filter(atom => group.requirement_ids.includes(atom.id)).map(atom => <li key={atom.id}>{requirementContext(atom)}</li>)}</ul>
    <Reasons reasons={group.unresolved_reasons} />
    <details><summary>{t('graph.source')}</summary>
      <p className="xs">{t('graph.occurrences')}: {group.requirement_ids.join(', ')}</p>
      <Proofs proofs={group.context_proofs} />
    </details>
  </section>;
}

function Document({ item }: { item: GraphDocumentAction }) {
  return <section className="panel panel--sunken stack stack--tight" aria-label={item.original_item.name}>
    <h5>{item.original_item.name}</h5><p className="small">{t('graph.documentReview')}</p>
    <p className="small">{t('graph.evidence')}: {t(stateKey(item.evidence_state))}</p>
    <p className="xs">{ownerText(item.original_item.owner)} · {documentPurpose(item.original_item.purpose)} · {item.original_item.deadline || t('graph.none')}</p>
    {item.original_items.length > 1 && <ul>{item.original_items.map((original, index) =>
      <li key={`${original.name}-${index}`}>{original.name} · {ownerText(original.owner)} · {original.deadline || t('graph.none')}</li>)}</ul>}
    {!!item.source_locations.length && <p className="xs muted">{item.source_locations.map(locationText).join(', ')}</p>}
    <Scope proof={item.scope} /><Reasons reasons={item.unresolved_reasons} />
    {!!item.dependencies.length && <div><strong>{t('graph.dependencies')}</strong><ul>{item.dependencies.map((dep, index) =>
      <li key={`${dep.original_name}-${index}`}>{dep.original_name} · {dependencyText(dep.resolution)}</li>)}</ul></div>}
    <details><summary>{t('graph.source')}</summary>
      <p className="xs">{t('graph.originalRefs')}: {item.original_item.claim_ids.join(', ') || t('graph.none')}</p>
      <Proofs proofs={item.proofs} />
      {item.original_items.map((original, index) => original.source_url
        ? <SourceLink key={`${original.name}-${index}`} url={original.source_url} /> : null)}
    </details>
    <details><summary>{t('graph.documentDetails')}</summary>
      {item.original_items.map((original, index) => <div className="stack stack--tight" key={`${original.name}-${index}`}>
        <p className="small">{original.name} · {original.required ? t('graph.recordedRequired') : t('graph.recordedOptional')}</p>
        {original.prompt_text && <p className="small" style={{ whiteSpace: 'pre-wrap' }}>{t('graph.prompt')}: {original.prompt_text}</p>}
        {original.format_notes && <p className="small">{t('graph.format')}: {original.format_notes}</p>}
        <p className="xs">{t('graph.limits')}: {values({ pages: original.max_pages, megabytes: original.max_file_size_mb,
          words: original.word_limit, characters: original.character_limit, naming: original.naming_convention })}</p>
        <p className="xs">{t('graph.timing')}: {original.deadline || t('graph.none')} · {original.deadline_timezone || t('graph.none')} · {t('graph.leadDays')}: {original.lead_time_days ?? t('graph.none')}</p>
        <p className="xs">{t('graph.processing')}: {[
          original.needs_translation && t('graph.translation'), original.needs_notarization && t('graph.notarization'),
          original.needs_apostille && t('graph.apostille'), original.needs_credential_evaluation && t('graph.credentialEvaluation'),
        ].filter(Boolean).join(', ') || t('graph.none')}</p>
      </div>)}
    </details>
  </section>;
}

function Programme({ programme, graph }: { programme: GraphProgrammeProjection; graph: PreparationGraph }) {
  // A locked card never looks up the local ProgramResult name or any other local record.
  if (!programme.research_access || programme.projection_state === 'locked') return <section className="panel panel--sunken stack stack--tight" aria-label={`${t('graph.programme')} ${programme.result_id}`}>
    <h3>{t('graph.programme')}: {programme.result_id}</h3>
    <p className="small">{decisionText(programme.user_decision)}</p><p>{t('graph.locked')}</p>
  </section>;
  const atoms = programme.requirement_ids.map(id => graph.requirements.find(item => item.id === id)!).filter(Boolean);
  const groups = graph.policy_groups.filter(item => item.result_id === programme.result_id);
  const documents = programme.document_action_ids.map(id => graph.document_actions.find(item => item.id === id)!).filter(Boolean);
  return <section className="panel panel--sunken stack" aria-label={`${t('graph.programme')} ${programme.result_id}`}>
    <h3>{programme.university && programme.programme ? `${programme.university} — ${programme.programme}` : programme.result_id}</h3>
    <p className="xs muted">{decisionText(programme.user_decision)}</p>
    <p className="small">{t('graph.evidence')}: {t(stateKey(programme.evidence_state))} · {t('graph.projection')}: {t(stateKey(programme.projection_state))}</p>
    {programme.projection_state === 'unavailable' && <p>{t('graph.unavailable')}</p>}
    {programme.requested_scope && <p className="xs muted">{t('graph.requestedScope')}: {scopeText(programme.requested_scope)}</p>}
    <Reasons reasons={programme.unresolved_reasons} />
    <h4>{t('graph.requirements')}</h4>
    {atoms.length ? atoms.map(atom => <Requirement key={atom.id} atom={atom} />) : <p>{t('graph.requirementsUnknown')}</p>}
    {groups.map(group => <Group key={group.id} group={group} atoms={atoms} />)}
    {!!programme.unprojected_checks.length && <details><summary>{t('graph.unprojected')}</summary>
      <ul>{programme.unprojected_checks.map((check, index) => <li key={`${check.requirement}-${index}`}>
        {check.requirement} · {checkText(check.status)} · {check.explanation}
        <p className="xs">{t('graph.published')}: {values(check.published_value)} · {t('graph.applicant')}: {values(check.applicant_value)}</p>
        <p className="xs">{t('graph.scope')}: {check.published_scope || t('graph.scopeUnknown')}</p>
        <p className="xs">{t('graph.originalRefs')}: {check.claim_ids.join(', ') || t('graph.none')}</p>
      </li>)}</ul>
    </details>}
    {!!programme.unresolved_questions.length && <details><summary>{t('graph.questions')}</summary>
      <ul>{programme.unresolved_questions.map((item, index) => <li key={`${item.topic}-${index}`}>{item.question} · {item.why_it_matters}</li>)}</ul>
    </details>}
    <h4>{t('graph.documents')}</h4>
    {documents.length ? documents.map(item => <Document key={item.id} item={item} />) : <p>{t('graph.documentsUnknown')}</p>}
  </section>;
}

export function PreparationGraphPanel({ profileId, programmes, isCurrent }: Props) {
  useSyncExternalStore(subscribe, getLocale);
  const eligible = programmes.filter(item => eligibleDecision(item.user_decision))
    .filter((item, index, list) => list.findIndex(other => other.id === item.id) === index);
  const eligibleIds = new Set(eligible.map(item => item.id));
  const eligibleKey = JSON.stringify(eligible.map(item => [item.id, item.user_decision]));
  const contextKey = JSON.stringify([profileId, eligibleKey]);
  const [selected, setSelected] = useState<string[]>([]);
  const selectedIds = selected.filter(id => eligibleIds.has(id)).slice(0, 20);
  const selectionKey = JSON.stringify(selectedIds);
  const [requested, setRequested] = useState(false);
  const [graph, setGraph] = useState<PreparationGraph | null>(null);
  const [acceptedKey, setAcceptedKey] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);
  const generation = useRef(0);
  const mounted = useRef(false);
  const liveCurrent = useRef(isCurrent);
  liveCurrent.current = isCurrent;
  const key = JSON.stringify([profileId, selectedIds, eligibleKey]);
  const liveKey = useRef(key);
  liveKey.current = key;
  const previousContext = useRef(contextKey);
  const current = () => { try { return mounted.current && liveCurrent.current(); } catch { return false; } };
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; ++generation.current; }; }, []);
  useEffect(() => {
    if (previousContext.current !== contextKey || JSON.stringify(selected) !== selectionKey) {
      previousContext.current = contextKey;
      ++generation.current; setSelected(JSON.parse(selectionKey) as string[]); setRequested(false); setGraph(null);
      setAcceptedKey(''); setLoading(false); setError(false);
    }
  }, [contextKey, selectionKey, selected]);
  const change = (id: string) => {
    if (!current() || !eligibleIds.has(id)) return;
    if (!selectedIds.includes(id) && selectedIds.length >= 20) return;
    ++generation.current;
    setSelected(selectedIds.includes(id) ? selectedIds.filter(value => value !== id) : [...selectedIds, id]);
    setRequested(false); setGraph(null); setAcceptedKey(''); setLoading(false); setError(false);
  };
  const read = async () => {
    if (!current() || selectedIds.length < 2 || selectedIds.length > 20 || loading) return;
    const token = ++generation.current;
    const requestedIds = [...selectedIds];
    const requestKey = key;
    const requestEligible = new Set(eligibleIds);
    setRequested(true); setGraph(null); setAcceptedKey(''); setLoading(true); setError(false);
    try {
      const next = await api.preparationGraph(profileId, requestedIds);
      if (!current() || token !== generation.current || liveKey.current !== requestKey) return;
      if (!matchesGraph(next, profileId, requestedIds, requestEligible)) throw new Error('G1 response fence');
      setGraph(next); setAcceptedKey(requestKey);
    } catch {
      if (current() && token === generation.current && liveKey.current === requestKey) setError(true);
    } finally {
      if (current() && token === generation.current && liveKey.current === requestKey) setLoading(false);
    }
  };
  const visible = requested && acceptedKey === key && current() ? graph : null;
  return <Panel title={t('graph.title')} hint={t('graph.intro')}>
    <div className="stack" style={{ minWidth: 0, overflowWrap: 'anywhere' }}>
      {!eligible.length ? <p>{t('graph.noneEligible')}</p> : <fieldset className="stack stack--tight">
        <legend>{t('graph.select')}</legend>
        {eligible.map(item => <label key={item.id} className="row" style={{ minHeight: 44 }}>
          <input type="checkbox" checked={selectedIds.includes(item.id)} onChange={() => change(item.id)}
            disabled={!selectedIds.includes(item.id) && selectedIds.length >= 20} />
          <span>{item.university} — {item.program} · {item.intake || t('graph.stateUnknown')} · {decisionText(item.user_decision)}</span>
        </label>)}
      </fieldset>}
      <p className="small">{selectedIds.length} / 20 · {selectedIds.length < 2 ? t('graph.choose') : t('graph.limit')}</p>
      <button type="button" className="btn btn--primary" disabled={selectedIds.length < 2 || loading}
        onClick={() => void read()}>{error ? t('graph.retry') : t('graph.view')}</button>
      {loading && <p role="status" aria-live="polite">{t('graph.loading')}</p>}
      {error && <p role="alert">{t('graph.error')}</p>}
      {visible && <div className="stack stack--loose" data-testid="preparation-graph">
        {visible.programmes.map(item => <Programme key={item.result_id} programme={item} graph={visible} />)}
        {!!visible.exam_workstreams.length && <section className="panel panel--sunken stack stack--tight">
          <h3>{t('graph.families')}</h3><p>{t('graph.familyOnly')}</p>
          {visible.exam_workstreams.map(stream => <div key={stream.id} className="stack stack--tight">
            <h4>{stream.family.toUpperCase()}</h4>
            <ul>{visible.requirements.filter(atom => stream.requirement_ids.includes(atom.id)).map(atom => {
              const programme = visible.programmes.find(item => item.result_id === atom.result_id);
              return <li key={atom.id}>{programme?.university} — {programme?.programme} · {requirementContext(atom)}</li>;
            })}</ul>
            <details><summary>{t('graph.source')}</summary><p className="xs">{t('graph.occurrences')}: {stream.requirement_ids.join(', ')} · {stream.contributing_result_ids.join(', ')}</p></details>
            <p className="xs muted">{t('graph.identityMissing')}: {stream.missing_identity_dimensions.map(identityText).join(', ')}</p>
          </div>)}
        </section>}
      </div>}
      <p className="xs muted">{t('graph.notSaved')}</p>
    </div>
  </Panel>;
}
