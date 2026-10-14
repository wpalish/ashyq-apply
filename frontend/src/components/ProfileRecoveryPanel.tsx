import { useEffect, useMemo, useState } from 'react';
import { useStore, toDraft } from '@/lib/store';
import { compareProfiles, type ProfileFieldValue } from '@/lib/profileMerge';
function describe(field: ProfileFieldValue): string { return !field.present ? 'Not provided' : field.value === null ? 'Empty (null)' : typeof field.value === 'object' ? JSON.stringify(field.value) : String(field.value); }
export function ProfileRecoveryPanel() {
  const { profileRecovery:view, profileDraft, loading, retryProfileWrite, compareSavedProfile,
    applyProfileComparison, clearConfirmedProfileWrites, exportProfileWrites } = useStore();
  const [choices,setChoices] = useState<Record<string,'local'|'server'>>({});
  const [localError,setLocalError] = useState<string|null>(null);
  const fingerprint = JSON.stringify(profileDraft);
  const rows = useMemo(() => view?.server ? compareProfiles(view.base,profileDraft,toDraft(view.server)) : [], [view,profileDraft]);
  useEffect(() => { setChoices({}); setLocalError(null); }, [view?.server?.revision, view?.entry?.command.command_id, fingerprint]);
  if (!view) return <details><summary>Profile recovery history for this tab</summary>
    {localError && <p role="alert">{localError}</p>}
    <button type="button" onClick={() => { try { clearConfirmedProfileWrites(); } catch (e) { setLocalError(String(e)); } }}>Clear confirmed profile recovery history</button>
  </details>;
  const exportOriginals = () => {
    try {
      const blob = new Blob([exportProfileWrites()], { type:'application/json' });
      const url = URL.createObjectURL(blob);
      try { const link = document.createElement('a'); link.href=url; link.download='unimatch-profile-recovery.json'; link.click(); }
      finally { URL.revokeObjectURL(url); }
    } catch (e) { setLocalError(String(e)); }
  };
  return <section aria-label="Profile save recovery" className="panel">
    <h2>Keep your profile edits</h2><p role="status">{view.message}</p>
    {view.entry && <p>Command: {view.entry.status}. This browser tab retains the original request; it is removed on sign-out.</p>}
    {localError && <p role="alert">{localError}</p>}
    {view.server ? <>
      <p>Saved version {view.server.revision}. Review each difference. This comparison does not save to the server.</p>
      {rows.map(row => <fieldset key={JSON.stringify(row.path)}>
        <legend>{row.path.join(' → ')}{row.conflict ? ' — choose a value' : ''}</legend>
        <p>Before: {describe(row.base)}</p>
        {(['local','server'] as const).map(choice => <label key={choice}>
          <input type="radio" name={JSON.stringify(row.path)} value={choice}
            checked={(choices[JSON.stringify(row.path)] ?? (row.conflict ? undefined : row.proposed)) === choice}
            onChange={() => setChoices(previous => ({ ...previous,[JSON.stringify(row.path)]:choice }))} />
          {choice === 'local' ? 'Your current edits' : 'Saved profile'}: {describe(row[choice])}
        </label>)}
      </fieldset>)}
      <button type="button" disabled={loading || rows.some(row => row.conflict && !choices[JSON.stringify(row.path)])}
        onClick={() => { try { applyProfileComparison(choices,fingerprint); } catch(e) { setLocalError(String(e)); } }}>Apply comparison to draft</button>
      <p>You can keep editing or leave this comparison. After applying, press Save explicitly.</p>
    </> : <>
      {view.entry && ['pending','unknown','accepted'].includes(view.entry.status) && <button type="button" disabled={loading} onClick={() => void retryProfileWrite()}>Confirm original save</button>}
      {(view.entry?.status === 'conflict' || !view.entry) && <button type="button" disabled={loading} onClick={() => void compareSavedProfile()}>Load saved profile for comparison</button>}
      {view.entry?.status === 'failed' && <button type="button" onClick={() => { try { clearConfirmedProfileWrites(); } catch(e) { setLocalError(String(e)); } }}>Clear confirmed refusal and keep edits</button>}
    </>}
    <button type="button" onClick={exportOriginals}>Export profile recovery for this tab</button>
    <button type="button" onClick={() => { try { clearConfirmedProfileWrites(); } catch(e) { setLocalError(String(e)); } }}>Clear confirmed recovery history</button>
  </section>;
}
