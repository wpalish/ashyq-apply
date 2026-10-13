import { useState } from 'react';
import { Notice, Panel } from '@/components/primitives';
import type { MessageKey } from '@/lib/i18n';
import { useTranslation } from '@/lib/useTranslation';
import type { AdmissionsActionsController } from '@/lib/useAdmissionsActions';
import type { G3IntentEntryV1 } from '@/lib/admissionsActionsRecovery';

function entryLabel(entry: G3IntentEntryV1, t: (key: MessageKey) => string): string {
  if ('personal' in entry.body) return entry.body.personal.label;
  if ('label' in entry.body) return entry.body.label;
  const labels: Record<G3IntentEntryV1['body']['kind'], MessageKey> = {
    create_application: 'actions.changePlanning', create_personal_task: 'actions.changeDetails', bind_source_task: 'actions.rebindDocument',
    rebind_source_task: 'actions.rebindDocument', set_document_self_report: 'actions.changeDocument', set_personal_details: 'actions.changeDetails',
    set_planning_status: 'actions.changePlanning', declare_submission: 'actions.declareSubmission', declare_withdrawal: 'actions.declareWithdrawal',
    correct_declaration: 'actions.correctDeclaration', import_legacy_marks: 'actions.importMarks', select_active_preparation: 'actions.selectPreparation',
  };
  return t(labels[entry.body.kind]);
}
export function AdmissionsRecoveryPanel({ controller }: { controller: AdmissionsActionsController }) {
  const { t } = useTranslation();
  const [selection, setSelection] = useState<{ key: string; ids: string[] }>({ key: controller.caseKey, ids: [] });
  const selected = selection.key === controller.caseKey ? selection.ids : [];
  const acknowledged = controller.entries.filter(entry => entry.descriptor.status === 'acknowledged');
  const selectable = selected.filter(uuid => acknowledged.some(entry => entry.descriptor.client_write_uuid === uuid));
  if (!controller.activeCase) return null;
  return (
    <Panel title={t('actions.recoveryTitle')}>
      <div className="stack" data-testid="admissions-recovery">
        <p className="small muted">{t('actions.recoveryHint')}</p>
        {controller.error && <Notice kind="risk">{controller.error}</Notice>}
        {controller.acceptedButUnrefreshed && <Notice kind="warn">{t('actions.savedViewUnknown')}</Notice>}
        {controller.journalError && <Notice kind="warn">{controller.journalError === 'limit' ? t('actions.recoveryFull') : t('actions.recoveryUnavailable')}</Notice>}
        {controller.entries.length === 0 && !controller.journalError && <p className="small muted">{t('actions.recoveryEmpty')}</p>}
        {controller.entries.map(entry => (
          <div key={entry.descriptor.client_write_uuid} className="row" style={{ justifyContent: 'space-between' }}>
            <div className="stack stack--tight">
              <strong>{entryLabel(entry, t)}</strong>
              <span className="small muted">{entry.descriptor.status === 'acknowledged' ? t('actions.commandAcknowledged')
                : entry.pending_state === 'conflict' ? t('actions.commandConflict')
                  : entry.pending_state === 'not_sent' ? t('actions.commandNotSent') : t('actions.commandUnknown')}</span>
            </div>
            {entry.descriptor.status === 'acknowledged' ? (
              <label className="row small">
                <input type="checkbox" aria-label={`${t('actions.selectConfirmation')}: ${entryLabel(entry, t)}`}
                  disabled={controller.sending || controller.journalError !== null}
                  checked={selectable.includes(entry.descriptor.client_write_uuid)}
                  onChange={event => setSelection({ key: controller.caseKey, ids: event.target.checked
                    ? [...selectable, entry.descriptor.client_write_uuid] : selectable.filter(id => id !== entry.descriptor.client_write_uuid) })} />
                {t('actions.selectConfirmation')}
              </label>
            ) : entry.pending_state !== 'conflict' && (
              <button type="button" className="btn btn--ghost" disabled={controller.sending || controller.journalError !== null}
                onClick={() => { void controller.retry(entry.descriptor.client_write_uuid); }}>{t('actions.retryOriginal')}</button>
            )}
          </div>
        ))}
        {controller.entries.length >= 64 && <Notice kind="warn">{t('actions.recoveryFull')}</Notice>}
        {acknowledged.length > 0 && <div className="stack stack--tight">
          <p className="small muted">{t('actions.cleanupHint')}</p>
          <button type="button" className="btn btn--ghost" disabled={!selectable.length || controller.sending || controller.journalError !== null}
            onClick={async () => {
              const capturedKey = controller.caseKey;
              const removed = await controller.clearAcknowledged(selectable);
              if (removed) setSelection(old => old.key === capturedKey ? { key: capturedKey, ids: [] } : old);
            }}>
            {t('actions.cleanupSelected')}
          </button>
        </div>}
        <div className="row">
          <button type="button" className="btn btn--ghost" disabled={controller.loading || controller.sending} onClick={() => { void controller.refresh(); }}>{t('actions.refreshSaved')}</button>
          {['index_missing', 'index_mismatch'].includes(controller.journalError ?? '') && <button type="button" className="btn btn--ghost" disabled={controller.sending}
            onClick={() => { void controller.reconcile(); }}>{t('actions.reconcileLocal')}</button>}
        </div>
      </div>
    </Panel>
  );
}
