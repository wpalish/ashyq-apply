/**
 * Screen 10 — Export and data deletion.
 *
 * Export the saved profile and run list, or delete this case and its linked
 * research records. These controls are not an account-wide export or a promise
 * about audit retention or backups — hence the explicit case confirmation.
 */

import { useTranslation } from '@/lib/useTranslation';
import { useLayoutEffect, useRef, useState } from 'react';
import { api } from '@/api/client';
import { Chip, Empty, Notice, Panel, Stat } from '@/components/primitives';
import { dateTime } from '@/lib/format';
import { useStore } from '@/lib/store';
import { PrintableReport } from '@/components/PrintableReport';

const CONFIRM_WORD = 'DELETE';

export function ExportScreen() {
  const {locale}=useTranslation(); const ru=locale!=='en';
  const { run, results, summary, savedProfile, profileDraft, caseEpoch, capabilities, deleteEverything, exportShortlist } =
    useStore();
  const caseId = savedProfile?.id ?? run?.profile_id ?? null;
  // Epoch changes when a switch starts, before the new profile id commits.
  const caseOwner = JSON.stringify([caseId, caseEpoch]);
  const ownerRef = useRef(caseOwner);
  ownerRef.current = caseOwner;
  const scope = useRef({ owner: caseOwner, previousOwner: caseOwner,
    id: caseId, previousId: caseId, draft: profileDraft, generation: 0 });
  const mounted = useRef(false);
  const acknowledgedCase = useRef<{ owner: string; id: string; blankOwner: string } | null>(null);
  const [confirmation, setConfirmation] = useState({ owner: caseOwner, value: '' });
  const [shown, setShown] = useState<{ owner: string; value: Record<string, unknown> } | null>(null);
  const [deletedOwner, setDeletedOwner] = useState<string | null>(null);
  // Filter on the first render, before any effect clears the previous case.
  const confirm = confirmation.owner === caseOwner ? confirmation.value : '';
  const exported = shown?.owner === caseOwner ? shown.value : null;
  const retired = acknowledgedCase.current?.owner === caseOwner;
  const deleted = deletedOwner === caseOwner
    || (retired && deletedOwner === acknowledgedCase.current?.blankOwner);

  useLayoutEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; ++scope.current.generation; };
  }, []);

  useLayoutEffect(() => {
    const previous = scope.current;
    // A later unsaved draft is distinct from the blank left by our deletion.
    if (previous.owner === caseOwner && (caseId !== null || previous.draft === profileDraft)) return;
    scope.current = { owner: caseOwner, previousOwner: previous.owner,
      id: caseId, previousId: previous.id, draft: profileDraft,
      generation: previous.generation + 1 };
    setConfirmation({ owner: caseOwner, value: '' });
    setShown(null);
    const acknowledged = acknowledgedCase.current;
    const ownBlankTransition = caseId === null && previous.id === acknowledged?.id
      && previous.owner === acknowledged?.owner && caseOwner === acknowledged?.blankOwner;
    setDeletedOwner((receiptOwner) => ownBlankTransition && receiptOwner === caseOwner ? receiptOwner : null);
  }, [caseId, caseOwner, profileDraft]);

  const currentExport = (owner: string, id: string, generation: number) => mounted.current
    && ownerRef.current === owner && scope.current.owner === owner
    && scope.current.id === id && scope.current.generation === generation
    && acknowledgedCase.current?.owner !== owner;

  const showProfile = async () => {
    if (!savedProfile || ownerRef.current !== caseOwner || acknowledgedCase.current?.owner === caseOwner) return;
    const { id } = savedProfile;
    const generation = scope.current.generation;
    const record = await api.exportProfile(id);
    if (currentExport(caseOwner, id, generation)) setShown({ owner: caseOwner, value: record });
  };

  const downloadProfile = async () => {
    if (!savedProfile || ownerRef.current !== caseOwner || acknowledgedCase.current?.owner === caseOwner) return;
    const { id } = savedProfile;
    const generation = scope.current.generation;
    // Read fresh; the retirement fence applies before creating a downloadable file.
    const record = await api.exportProfile(id);
    if (!currentExport(caseOwner, id, generation)) return;
    const blob = new Blob([JSON.stringify(record, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `ashyq-${id.slice(0, 8)}-my-data.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const deleteCase = async () => {
    if (!savedProfile || confirm !== CONFIRM_WORD || ownerRef.current !== caseOwner
        || acknowledgedCase.current?.owner === caseOwner) return;
    const { id } = savedProfile;
    const generation = scope.current.generation;
    const acknowledgedBlank = JSON.stringify([null, caseEpoch + 1]);
    let accepted: boolean;
    try { accepted = await deleteEverything(); }
    catch { return; } // The store normally records an error and returns false.
    if (!accepted || !mounted.current) return;
    const current = scope.current;
    const sameCase = ownerRef.current === caseOwner && current.owner === caseOwner
      && current.id === id && current.generation === generation;
    // Native Store can render its acknowledged A-to-blank transition before resuming.
    const clearedCase = ownerRef.current === acknowledgedBlank && current.owner === acknowledgedBlank
      && current.id === null && current.previousOwner === caseOwner && current.previousId === id
      && current.generation === generation + 1;
    if (!sameCase && !clearedCase) return;
    acknowledgedCase.current = { owner: caseOwner, id, blankOwner: acknowledgedBlank };
    ++scope.current.generation; // Close pending exports immediately, before a later render.
    setShown(null);
    setConfirmation({ owner: acknowledgedBlank, value: '' });
    setDeletedOwner(acknowledgedBlank);
  };

  if (!run && !savedProfile && !deleted) return <Empty title="Nothing to export yet">Save an applicant case first.</Empty>;

  const approved = results.filter((r) => r.user_decision === 'approved').length;

  return (
    <div className="export-page">
      {!ru&&<div className="screen__head">
        <p className="screen__eyebrow">Step 09</p>
        <h1 className="screen__title">Export your report</h1>
        <p className="screen__lede">
          Shortlist exports carry the source link and verification date for each row.
          You can also export or delete a saved case before research.
        </p>
      </div>}
      <PrintableReport key={caseOwner} results={results} name={savedProfile?.display_name} demo={Boolean(capabilities?.demo_mode || summary?.demo_data || run?.demo_mode)} onCSV={run?()=>{void exportShortlist('csv');}:undefined} />

      <details className="book-advanced" open={ru?undefined:true}><summary>{ru?'Другие форматы, данные дела и удаление':'Data, other formats and deletion'}</summary><div className="stack stack--loose">
        {run && <div className="statband">
          <Stat value={results.length} label="Programmes" />
          <Stat value={approved} label="Approved" />
          <Stat value={summary?.with_conflicts ?? 0} label="Conflicts" />
          <Stat value={run.claims_recorded} label="Claims" />
          <Stat value={run.pages_checked} label="Pages read" />
        </div>}

        {run && <Panel
          title="Export the shortlist"
          hint="CSV for a spreadsheet, JSON for everything including every claim, XLSX for a three-sheet workbook: shortlist, evidence, and open questions."
        >
          {/* Buttons, not links: a plain <a href> bypasses the API client, so a
              402 would open raw JSON in a tab instead of raising the paywall. */}
          <div className="row">
            {(['csv', 'json', 'xlsx'] as const).map((fmt) => (
              <button
                key={fmt}
                type="button"
                className="btn"
                onClick={() => exportShortlist(fmt)}
                data-testid={`export-${fmt}`}
              >
                Download .{fmt}
              </button>
            ))}
            {approved > 0 && (
              <button
                type="button"
                className="btn btn--primary"
                onClick={() => exportShortlist('xlsx', 'approved')}
              >
                Approved only (.xlsx)
              </button>
            )}
          </div>
          {capabilities?.demo_mode && (
            <Notice kind="demo">
              <div>
                Every exported row is marked <strong>DEMO FIXTURE (synthetic)</strong> in its data
                origin column, so a demo export can never be mistaken for researched figures.
              </div>
            </Notice>
          )}
        </Panel>}

        <Panel
          title="Export your own data"
          hint="This saved case: the profile as entered and a list of its runs. This is not an account-wide export."
        >
          <div className="row">
            <button
              className="btn"
              disabled={!savedProfile || deleted || retired}
              onClick={showProfile}
              data-testid="export-profile"
            >
              Show my stored data
            </button>
            <button
              className="btn"
              disabled={!savedProfile || deleted || retired}
              onClick={downloadProfile}
              data-testid="download-profile"
            >
              Download my data (.json)
            </button>
            {savedProfile && <Chip mono>profile {savedProfile.id.slice(0, 8)}</Chip>}
          </div>
          {exported && (
            <pre
              className="xs mono"
              tabIndex={0}
              aria-label="Stored profile data"
              style={{
                marginTop: 'var(--space-4)', maxHeight: '20rem', overflow: 'auto',
                background: 'var(--surface-sunken)', padding: 'var(--space-3)',
                borderRadius: 'var(--radius)',
              }}
            >
              {JSON.stringify(exported, null, 2)}
            </pre>
          )}
        </Panel>

        {capabilities && (
          <Panel title="What this build does and does not do">
            <div className="stack stack--tight">
              <div>
                <h3 style={{ fontSize: 'var(--text-base)' }}>Guarantees</h3>
                <ul className="small muted" style={{ paddingLeft: '1.1rem', margin: '4px 0 0' }}>
                  {capabilities.guarantees.map((g) => <li key={g}>{g}</li>)}
                </ul>
              </div>
              <div>
                <h3 style={{ fontSize: 'var(--text-base)', marginTop: 'var(--space-3)' }}>Limits</h3>
                <ul className="small muted" style={{ paddingLeft: '1.1rem', margin: '4px 0 0' }}>
                  {capabilities.limits.map((l) => <li key={l}>{l}</li>)}
                </ul>
              </div>
              <p className="xs faint" style={{ marginTop: 'var(--space-3)' }}>
                Currency figures converted using a static snapshot dated{' '}
                {capabilities.currency.rate_date}. {capabilities.currency.rate_source}
              </p>
            </div>
          </Panel>
        )}

        <Panel title="Delete this case">
          {deleted ? (
            <Notice kind="info">
              <div>Deleted. The profile and its linked research records were removed from the active service.</div>
            </Notice>
          ) : (
            <div className="stack">
              <Notice kind="risk">
                <div>
                  This erases the applicant profile and every research run, result, claim,
                  conflict and checklist attached to it. It cannot be undone here.
                  Account data, audit records and backups are outside this case control.
                </div>
              </Notice>
              <div className="row">
                <input
                  aria-label={`Type ${CONFIRM_WORD} to confirm`}
                  placeholder={`Type ${CONFIRM_WORD} to confirm`}
                  value={confirm}
                  onChange={(e) => setConfirmation({ owner: caseOwner, value: e.target.value })}
                  style={{ maxWidth: '16rem' }}
                  data-testid="delete-confirm"
                />
                <button
                  className="btn btn--danger"
                  disabled={confirm !== CONFIRM_WORD || !savedProfile || retired}
                  onClick={deleteCase}
                  data-testid="delete-everything"
                >
                  Delete permanently
                </button>
              </div>
            </div>
          )}
        </Panel>

        {run && <p className="xs faint">
          Run {run.id} · started {dateTime(run.started_at)} ·{' '}
          {run.demo_mode ? 'demo corpus' : 'live sources'} · schema-backed audit log available at
          /api/audit. Audit retention is separate from case deletion.
        </p>}
      </div></details>
    </div>
  );
}
