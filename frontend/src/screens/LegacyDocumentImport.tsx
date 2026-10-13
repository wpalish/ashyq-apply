/** Reviewed personal marks only, restricted to exact references in this own loaded case. */
import { useRef, useState } from 'react';
import { api } from '@/api/client';
import { Notice, Panel } from '@/components/primitives';
import { useStore } from '@/lib/store';
import { useTranslation } from '@/lib/useTranslation';
import { admissionsLegacyKeyDigest, g3Canonical, openAdmissionsActionsRecovery, readAdmissionsLegacyCandidates, type G3LegacyBrowserSnapshotV1 } from '@/lib/admissionsActionsRecovery';
import type { AdmissionsActionsController } from '@/lib/useAdmissionsActions';
import { isLegacyImportPreviewOutV1, type LegacyImportMappingV1, type LegacyImportPreviewOutV1 } from '@/types/admissionsActions';
interface LoadedMarks { key: string; snapshot: G3LegacyBrowserSnapshotV1; labels: Map<string, string> }
interface ImportChoice { key: string; legacy: string; task: string; confirmed: boolean }
export function LegacyDocumentImport({ controller }: { controller: AdmissionsActionsController }) {
  const { results, run, savedProfile, currentAdmissionsCase } = useStore(); const { t } = useTranslation();
  const [loaded, setLoaded] = useState<LoadedMarks | null>(null);
  const [choice, setChoice] = useState<ImportChoice>({ key: controller.caseKey, legacy: '', task: '', confirmed: false });
  const [preview, setPreview] = useState<{ attempted: boolean; key: string; body: LegacyImportPreviewOutV1 } | null>(null);
  const [error, setError] = useState<{ key: string; value: boolean }>({ key: controller.caseKey, value: false });
  const attemptedPreview = useRef<LegacyImportPreviewOutV1 | null>(null); const serial = useRef(0); const liveKey = useRef(controller.caseKey); liveKey.current = controller.caseKey;
  const own = controller.activeCase === savedProfile?.id && run?.profile_id === savedProfile?.id
    ? results.filter(result => result.run_id === run.id && result.checklist) : [];
  const known = own.flatMap(result => [result.checklist?.applicant_actions ?? [], result.checklist?.school_actions ?? [],
    result.checklist?.recommender_actions ?? [], result.checklist?.certification_actions ?? []].flat().map(item => ({ key: `${result.id}::${item.name}`, label: `${result.university} · ${result.program} · ${item.name}` })));
  const counts = new Map<string, number>(); for (const value of known) counts.set(value.key, (counts.get(value.key) ?? 0) + 1);
  const unambiguous = known.filter(value => counts.get(value.key) === 1);
  const marks = loaded?.key === controller.caseKey ? loaded : null;
  const selected = choice.key === controller.caseKey ? choice : { key: controller.caseKey, legacy: '', task: '', confirmed: false };
  const manualTasks = controller.current?.state?.document_tasks.filter(task => task.binding === null && task.report.origin === 'unreported') ?? [];
  const activePreview = preview?.key === controller.caseKey ? preview.body : null;
  const invalidated = (patch: Partial<ImportChoice>) => { ++serial.current; setPreview(null); setChoice({ ...selected, ...patch, key: controller.caseKey }); };
  const load = async () => {
    const identity = currentAdmissionsCase();
    if (identity.profile_id !== controller.activeCase || identity.profile_id === null || identity.scope === null) return;
    const binding = openAdmissionsActionsRecovery(identity.scope, identity.profile_id, identity.case_epoch, currentAdmissionsCase);
    if (!binding.ok) { setError({ key: controller.caseKey, value: true }); return; }
    const capturedKey = controller.caseKey; const generation = ++serial.current;
    const labels = new Map<string, string>();
    for (const item of unambiguous) labels.set(await admissionsLegacyKeyDigest(item.key), item.label);
    const found = await readAdmissionsLegacyCandidates(binding.value, unambiguous.map(item => item.key));
    if (liveKey.current !== capturedKey || serial.current !== generation || JSON.stringify(currentAdmissionsCase()) !== JSON.stringify(identity)) return;
    if (!found.ok) { setError({ key: capturedKey, value: true }); return; }
    setLoaded({ key: capturedKey, snapshot: found.value, labels }); setChoice({ key: capturedKey, legacy: '', task: '', confirmed: false });
    setPreview(null); setError({ key: capturedKey, value: false });
  };
  const check = async () => {
    const task = manualTasks.find(item => item.id === selected.task);
    const mark = marks?.snapshot.candidates.find(item => item.legacy_key_digest === selected.legacy);
    if (!marks || !task || !mark || !selected.confirmed || !controller.current) return;
    const identity = currentAdmissionsCase(); const capturedKey = controller.caseKey; const generation = ++serial.current;
    const mapping: LegacyImportMappingV1 = { task_id: task.id, legacy_key_digest: mark.legacy_key_digest, expected_binding_digest: null,
      source_preview_digest: null, legacy_value: true, confirmed_prepared_report: true, source_version: 'unknown', original_reported_at: null };
    try {
      const value = await api.previewAdmissionsImport(controller.activeCase ?? '', { expected_revision: controller.current.revision,
        legacy_snapshot_digest: marks.snapshot.legacy_snapshot_digest, mappings: [mapping] });
      if (liveKey.current !== capturedKey || serial.current !== generation || JSON.stringify(currentAdmissionsCase()) !== JSON.stringify(identity)) return;
      if (!isLegacyImportPreviewOutV1(value) || value.profile_id !== controller.activeCase || value.revision !== controller.current.revision
        || value.legacy_snapshot_digest !== marks.snapshot.legacy_snapshot_digest || g3Canonical(value.mappings) !== g3Canonical([mapping])) throw new Error('Import preview mismatch');
      setPreview({ attempted: false, key: capturedKey, body: value }); setError({ key: capturedKey, value: false });
    } catch { if (liveKey.current === capturedKey && serial.current === generation) setError({ key: capturedKey, value: true }); }
  };
  const save = async () => {
    if (!activePreview || preview?.attempted || attemptedPreview.current === activePreview || !marks || activePreview.revision !== controller.current?.revision || !selected.confirmed) return;
    const capturedKey = controller.caseKey; const generation = serial.current;
    const identity = currentAdmissionsCase();
    if (identity.profile_id !== controller.activeCase || identity.profile_id === null || identity.scope === null) return;
    attemptedPreview.current = activePreview;
    try {
      const binding = openAdmissionsActionsRecovery(identity.scope, identity.profile_id, identity.case_epoch, currentAdmissionsCase);
      if (!binding.ok) throw new Error('Own recovery context unavailable');
      const latest = await readAdmissionsLegacyCandidates(binding.value, unambiguous.map(item => item.key));
      if (!latest.ok || latest.value.legacy_snapshot_digest !== activePreview.legacy_snapshot_digest || liveKey.current !== capturedKey
        || serial.current !== generation || JSON.stringify(currentAdmissionsCase()) !== JSON.stringify(identity)) {
        if (liveKey.current === capturedKey && serial.current === generation) { setPreview(null); setError({ key: capturedKey, value: true }); } return;
      }
      const uuid = crypto.randomUUID();
      setPreview(old => old?.key === capturedKey && old.body === activePreview ? { ...old, attempted: true } : old);
      const result = await controller.submit({ schema_version: 'admissions-actions-v1', kind: 'import_legacy_marks', client_write_uuid: uuid,
        expected_revision: activePreview.revision, legacy_snapshot_digest: activePreview.legacy_snapshot_digest,
        mappings: activePreview.mappings, entered_at: null });
      if (liveKey.current !== capturedKey || serial.current !== generation) return;
      if (result.accepted) { setPreview(null); setChoice({ key: capturedKey, legacy: '', task: '', confirmed: false }); }
    } catch { if (liveKey.current === capturedKey && serial.current === generation) setError({ key: capturedKey, value: true }); }
  };
  return <Panel title={t('documents.legacyImportTitle')}>
    <div className="stack">
      <p className="small muted">{t('documents.legacyImportHint')}</p>
      <button type="button" className="btn btn--ghost" disabled={!controller.current || controller.sending} onClick={() => { void load(); }}>{t('documents.readOwnMarks')}</button>
      {error.key === controller.caseKey && error.value && <Notice kind="warn">{t('documents.legacyImportUnavailable')}</Notice>}
      {marks && <>
        {marks.snapshot.candidates.length === 0 && <p className="small muted">{t('documents.noSafeMarks')}</p>}
        <label className="stack stack--tight">{t('documents.chooseLegacyMark')}<select value={selected.legacy} onChange={event => invalidated({ legacy: event.target.value, confirmed: false })}>
          <option value="">{t('documents.chooseLegacyMark')}</option>{marks.snapshot.candidates.map(mark => <option key={mark.legacy_key_digest} value={mark.legacy_key_digest}>{marks.labels.get(mark.legacy_key_digest)}</option>)}
        </select></label>
        <label className="stack stack--tight">{t('documents.chooseOwnTask')}<select value={selected.task} onChange={event => invalidated({ task: event.target.value, confirmed: false })}>
          <option value="">{t('documents.chooseOwnTask')}</option>{manualTasks.map(task => <option key={task.id} value={task.id}>{task.personal.label}</option>)}
        </select></label>
        <label className="row"><input type="checkbox" checked={selected.confirmed} onChange={event => invalidated({ confirmed: event.target.checked })} />{t('documents.confirmLegacyMapping')}</label>
        <button type="button" className="btn btn--ghost" disabled={!selected.confirmed || !selected.legacy || !selected.task || controller.sending} onClick={() => { void check(); }}>{t('documents.previewLegacyImport')}</button>
      </>}
      {activePreview && <>
        <p className="small muted">{t('documents.legacyUnknownVersion')}</p>
        {preview?.attempted && <Notice kind="warn">{t('documents.saveUnknown')}</Notice>}
        <button type="button" className="btn btn--primary" disabled={preview?.attempted || controller.sending || controller.journalError !== null || activePreview.revision !== controller.current?.revision}
          onClick={() => { void save(); }}>{t('documents.saveLegacyImport')}</button>
      </>}
    </div>
  </Panel>;
}
