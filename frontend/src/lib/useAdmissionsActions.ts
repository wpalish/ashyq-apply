/** Server current is authoritative; local storage holds only exact command recovery. */
import { useCallback, useEffect, useRef, useState } from 'react';
import { api, ApiError } from '@/api/client';
import { useStore } from '@/lib/store';
import {
  acknowledgeAdmissionsAction, admissionsActionRetryBody, admissionsRecoveryEntryRaw, admissionsRecoveryIndexRaw,
  journalAdmissionsAction, markAdmissionsActionState, openAdmissionsActionsRecovery,
  readAdmissionsActionsRecovery, reconcileAdmissionsActionsIndex, removeAcknowledgedAdmissionsActions,
  validateAdmissionsActionReceipt, validateAdmissionsActionsCurrent,
  type G3IntentEntryV1, type G3LiveCaseIdentity, type G3RecoveryBinding, type G3RecoveryFailure,
} from '@/lib/admissionsActionsRecovery';
import { isActionsHistoryOutV1, type ActionsCurrentOutV1, type ActionsHistoryOutV1, type ActionRequestV1, type ActionWriteReceiptV1 } from '@/types/admissionsActions';

export interface AdmissionsCommandOutcome {
  accepted: boolean;
  currentRefreshed: boolean;
  receipt: ActionWriteReceiptV1 | null;
}
interface CaseView {
  key: string; current: ActionsCurrentOutV1 | null; historyPage: ActionsHistoryOutV1 | null;
  entries: G3IntentEntryV1[]; indexRaw: string | null; journalError: G3RecoveryFailure | null;
  loading: boolean; sending: boolean; error: string | null; acceptedButUnrefreshed: boolean;
}
const empty = (key: string): CaseView => ({ key, current: null, historyPage: null, entries: [], indexRaw: null,
  journalError: null, loading: false, sending: false, error: null, acceptedButUnrefreshed: false });
const rejected = (): AdmissionsCommandOutcome => ({ accepted: false, currentRefreshed: false, receipt: null });
const message = (error: unknown) => error instanceof ApiError ? error.message : 'The saved actions could not be confirmed. Refresh before continuing.';
const identityKey = (identity: G3LiveCaseIdentity) => JSON.stringify([identity.scope ?? (identity.scope === undefined ? 'demo' : null), identity.profile_id, identity.case_epoch]);

export function useAdmissionsActions() {
  const { currentAdmissionsCase } = useStore();
  const live = currentAdmissionsCase();
  const key = identityKey(live);
  const [stored, setStored] = useState<CaseView>(() => empty(key));
  const view = stored.key === key ? stored : empty(key);
  const mounted = useRef(true);
  const readGeneration = useRef(0);
  const writeBusy = useRef<string | null>(null);
  const currentView = useRef(stored);
  currentView.current = stored;
  const currentBinding = useRef<{ key: string; value: G3RecoveryBinding } | null>(null);

  const active = useCallback((captured: G3LiveCaseIdentity) => mounted.current
    && captured.scope !== null && captured.profile_id !== null && identityKey(currentAdmissionsCase()) === identityKey(captured), [currentAdmissionsCase]);
  const update = useCallback((captured: G3LiveCaseIdentity, fn: (old: CaseView) => CaseView) => {
    if (!active(captured)) return;
    const ownKey = identityKey(captured);
    setStored(old => active(captured) ? fn(old.key === ownKey ? old : empty(ownKey)) : old);
  }, [active]);
  const bindingFor = useCallback((captured: G3LiveCaseIdentity): G3RecoveryBinding | null => {
    if (!active(captured) || captured.profile_id === null) return null;
    const ownKey = identityKey(captured);
    if (currentBinding.current?.key === ownKey) return currentBinding.current.value;
    const opened = openAdmissionsActionsRecovery(captured.scope, captured.profile_id, captured.case_epoch, currentAdmissionsCase);
    if (!opened.ok) { update(captured, old => ({ ...old, journalError: opened.reason })); return null; }
    currentBinding.current = { key: ownKey, value: opened.value };
    return opened.value;
  }, [active, currentAdmissionsCase, update]);
  const readJournal = useCallback(async (captured: G3LiveCaseIdentity, binding: G3RecoveryBinding) => {
    const recovered = await readAdmissionsActionsRecovery(binding);
    if (!active(captured)) return false;
    update(captured, old => recovered.ok ? { ...old, entries: recovered.value.entries, indexRaw: recovered.value.index_raw, journalError: null }
      : { ...old, journalError: recovered.reason });
    return recovered.ok;
  }, [active, update]);

  const refresh = useCallback(async (minimumRevision = 0): Promise<boolean> => {
    const captured = currentAdmissionsCase();
    if (!active(captured) || captured.profile_id === null) return false;
    const generation = ++readGeneration.current;
    update(captured, old => ({ ...old, loading: true }));
    const binding = bindingFor(captured);
    const [server] = await Promise.allSettled([
      api.admissionsActions(captured.profile_id),
      binding ? readJournal(captured, binding) : Promise.resolve(false),
    ]);
    if (!active(captured) || generation !== readGeneration.current) return false;
    try {
      if (server.status !== 'fulfilled') throw server.reason;
      const accepted = await validateAdmissionsActionsCurrent(server.value, captured.profile_id);
      if (!active(captured) || generation !== readGeneration.current) return false;
      const previous = currentView.current.key === identityKey(captured) ? currentView.current.current?.revision ?? 0 : 0;
      if (accepted === null || accepted.revision < Math.max(minimumRevision, previous)) throw new Error('Current revision did not match its immutable own head.');
      update(captured, old => ({ ...old, current: accepted, loading: false, error: null, acceptedButUnrefreshed: false }));
      return true;
    } catch (error) {
      update(captured, old => ({ ...old, loading: false, error: message(error) }));
      return false;
    }
  }, [active, bindingFor, currentAdmissionsCase, readJournal, update]);

  useEffect(() => {
    mounted.current = true;
    const reads = readGeneration;
    void refresh();
    return () => { mounted.current = false; ++reads.current; };
  }, [key, refresh]);

  const dispatch = useCallback(async (captured: G3LiveCaseIdentity, binding: G3RecoveryBinding,
    original: ActionRequestV1, raw: string): Promise<AdmissionsCommandOutcome> => {
    const sending = await markAdmissionsActionState(binding, original.client_write_uuid.toLowerCase(), raw, 'sending');
    if (!sending.ok || !active(captured) || captured.profile_id === null) {
      if (!sending.ok) update(captured, old => ({ ...old, journalError: sending.reason }));
      return rejected();
    }
    ++readGeneration.current; // A GET begun before this mutation cannot land afterwards.
    try {
      const receipt = await api.writeAdmissionsAction(captured.profile_id, sending.value.entry.body);
      if (!active(captured)) return rejected();
      const confirmed = await validateAdmissionsActionReceipt(captured.profile_id, sending.value.entry.body, receipt);
      if (!active(captured)) return rejected();
      if (!confirmed) {
        await markAdmissionsActionState(binding, original.client_write_uuid.toLowerCase(), sending.value.raw, 'uncertain');
        update(captured, old => ({ ...old, error: 'The response did not confirm the original request. Keep it for recovery.' }));
        await readJournal(captured, binding);
        return rejected();
      }
      const acknowledged = await acknowledgeAdmissionsAction(binding, sending.value.entry.body, receipt);
      if (!active(captured)) return rejected();
      await readJournal(captured, binding);
      const currentRefreshed = await refresh(receipt.revision);
      if (!active(captured)) return rejected();
      if (!acknowledged.ok) update(captured, old => ({ ...old, journalError: acknowledged.reason, error: 'The server confirmed the save, but local recovery could not be updated.' }));
      if (!currentRefreshed) update(captured, old => ({ ...old, acceptedButUnrefreshed: true }));
      return { accepted: true, currentRefreshed, receipt };
    } catch (error) {
      if (!active(captured)) return rejected();
      const state = error instanceof ApiError && error.status === 409 ? 'conflict' : 'uncertain';
      const marked = await markAdmissionsActionState(binding, original.client_write_uuid.toLowerCase(), sending.value.raw, state);
      update(captured, old => ({ ...old, error: message(error), journalError: marked.ok ? null : marked.reason }));
      await readJournal(captured, binding);
      if (state === 'conflict') await refresh(); // Comparison only; original body/CAS remains intact.
      return rejected();
    }
  }, [active, readJournal, refresh, update]);

  const runExclusive = useCallback(async (action: (captured: G3LiveCaseIdentity, binding: G3RecoveryBinding) => Promise<AdmissionsCommandOutcome>) => {
    const captured = currentAdmissionsCase();
    if (writeBusy.current === identityKey(captured) || !active(captured)) return rejected();
    const binding = bindingFor(captured); if (!binding) return rejected();
    writeBusy.current = identityKey(captured); update(captured, old => ({ ...old, sending: true }));
    try { return await action(captured, binding); }
    finally { if (writeBusy.current === identityKey(captured)) writeBusy.current = null; update(captured, old => ({ ...old, sending: false })); }
  }, [active, bindingFor, currentAdmissionsCase, update]);

  const submit = useCallback((body: ActionRequestV1) => runExclusive(async (captured, binding) => {
    const own = currentView.current;
    if (own.key !== identityKey(captured) || own.current === null || own.journalError !== null) return rejected();
    // The caller's reviewed draft revision is retained; never refresh CAS in here.
    const saved = await journalAdmissionsAction(binding, body, captured.case_epoch);
    if (!saved.ok) { update(captured, old => ({ ...old, journalError: saved.reason })); return rejected(); }
    return dispatch(captured, binding, saved.value.entry.body, saved.value.raw);
  }), [dispatch, runExclusive, update]);
  const retry = useCallback((uuid: string) => runExclusive(async (captured, binding) => {
    const journal = await readAdmissionsActionsRecovery(binding);
    if (!journal.ok) { update(captured, old => ({ ...old, journalError: journal.reason })); return rejected(); }
    const entry = journal.value.entries.find(item => item.descriptor.client_write_uuid === uuid);
    if (!entry) return rejected();
    const envelope = admissionsRecoveryEntryRaw(binding, uuid);
    if (!envelope.ok) { update(captured, old => ({ ...old, journalError: envelope.reason })); return rejected(); }
    const raw = envelope.value;
    const original = await admissionsActionRetryBody(binding, uuid, raw);
    if (!original.ok) { update(captured, old => ({ ...old, journalError: original.reason })); return rejected(); }
    return dispatch(captured, binding, original.value, raw);
  }), [dispatch, runExclusive, update]);

  const loadHistory = useCallback(async (afterRevision = 0) => {
    const captured = currentAdmissionsCase();
    if (!active(captured) || captured.profile_id === null) return false;
    try {
      const page = await api.admissionsActionsHistory(captured.profile_id, afterRevision);
      if (!active(captured)) return false;
      if (!isActionsHistoryOutV1(page) || page.profile_id !== captured.profile_id) throw new Error('History belongs to another case or has invalid ordering.');
      update(captured, old => ({ ...old, historyPage: page })); return true;
    } catch (error) { update(captured, old => ({ ...old, error: message(error) })); return false; }
  }, [active, currentAdmissionsCase, update]);

  const clearAcknowledged = useCallback(async (uuids: readonly string[]) => {
    const captured = currentAdmissionsCase(); const binding = bindingFor(captured);
    if (!binding || writeBusy.current === identityKey(captured) || !active(captured) || captured.profile_id === null) return false;
    writeBusy.current = identityKey(captured); update(captured, old => ({ ...old, sending: true }));
    try {
      const journal = await readAdmissionsActionsRecovery(binding);
      if (!journal.ok || !active(captured)) return false;
      const selected = uuids.map(uuid => journal.value.entries.find(entry => entry.descriptor.client_write_uuid === uuid));
      if (!uuids.length || selected.some(entry => !entry || entry.descriptor.status !== 'acknowledged' || entry.descriptor.receipt_ref === null)) return false;
      const receipts = await Promise.all(uuids.map(uuid => {
        const entry = journal.value.entries.find(value => value.descriptor.client_write_uuid === uuid);
        if (!entry?.descriptor.receipt_ref) throw new Error('Missing own confirmation');
        const profile = captured.profile_id;
        if (profile === null) throw new Error('No current case');
        return api.admissionsActionEvent(profile, entry.descriptor.receipt_ref.event_id);
      }));
      if (!active(captured)) return false;
      const selection = uuids.map((uuid, index) => {
        const receipt = receipts[index];
        if (!receipt) throw new Error('Missing server confirmation');
        return { client_write_uuid: uuid, receipt };
      });
      const cleaned = await removeAcknowledgedAdmissionsActions(binding, selection, journal.value.index_raw);
      if (!cleaned.ok) update(captured, old => ({ ...old, journalError: cleaned.reason }));
      await readJournal(captured, binding); return cleaned.ok;
    } catch (error) { update(captured, old => ({ ...old, error: message(error) })); return false; }
    finally { if (writeBusy.current === identityKey(captured)) writeBusy.current = null; update(captured, old => ({ ...old, sending: false })); }
  }, [active, bindingFor, currentAdmissionsCase, readJournal, update]);
  const reconcile = useCallback(async () => {
    const captured = currentAdmissionsCase(); const binding = bindingFor(captured); const own = currentView.current;
    if (!binding || !active(captured) || own.key !== identityKey(captured)
      || !['index_missing', 'index_mismatch'].includes(own.journalError ?? '') || writeBusy.current === identityKey(captured)) return false;
    writeBusy.current = identityKey(captured); update(captured, old => ({ ...old, sending: true }));
    try {
      const raw = admissionsRecoveryIndexRaw(binding); if (!raw.ok) return false;
      const result = await reconcileAdmissionsActionsIndex(binding, raw.value);
      if (!result.ok) update(captured, old => ({ ...old, journalError: result.reason }));
      else await readJournal(captured, binding);
      return result.ok;
    } finally {
      if (writeBusy.current === identityKey(captured)) writeBusy.current = null;
      update(captured, old => ({ ...old, sending: false }));
    }
  }, [active, bindingFor, currentAdmissionsCase, readJournal, update]);

  return { ...view, caseKey: key, activeCase: live.profile_id, refresh, submit, retry, loadHistory, clearAcknowledged, reconcile };
}
export type AdmissionsActionsController = ReturnType<typeof useAdmissionsActions>;
