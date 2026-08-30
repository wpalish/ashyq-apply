/**
 * Screen 10 — Export and data deletion.
 *
 * Both directions of data portability in one place: take everything out, or
 * erase all of it. Deletion is real and cascades to every run, result and
 * claim — hence the typed confirmation.
 */

import { useState } from 'react';
import { api } from '@/api/client';
import { Chip, Empty, Notice, Panel, Stat } from '@/components/primitives';
import { dateTime } from '@/lib/format';
import { useStore } from '@/lib/store';

const CONFIRM_WORD = 'DELETE';

export function ExportScreen() {
  const { run, results, summary, savedProfile, capabilities, deleteEverything } = useStore();
  const [confirm, setConfirm] = useState('');
  const [exported, setExported] = useState<Record<string, unknown> | null>(null);
  const [deleted, setDeleted] = useState(false);

  if (!run) return <Empty title="Nothing to export yet">Start a research run first.</Empty>;

  const approved = results.filter((r) => r.user_decision === 'approved').length;

  return (
    <>
      <div className="screen__head">
        <p className="screen__eyebrow">Step 09</p>
        <h1 className="screen__title">Take it with you, or erase it</h1>
        <p className="screen__lede">
          Every export carries the source link and the verification date for each row, so a
          spreadsheet is as auditable as this screen. Deletion is immediate and complete.
        </p>
      </div>

      <div className="stack stack--loose">
        <div className="statband">
          <Stat value={results.length} label="Programmes" />
          <Stat value={approved} label="Approved" />
          <Stat value={summary?.with_conflicts ?? 0} label="Conflicts" />
          <Stat value={run.claims_recorded} label="Claims" />
          <Stat value={run.pages_checked} label="Pages read" />
        </div>

        <Panel
          title="Export the shortlist"
          hint="CSV for a spreadsheet, JSON for everything including every claim, XLSX for a three-sheet workbook: shortlist, evidence, and open questions."
        >
          <div className="row">
            {(['csv', 'json', 'xlsx'] as const).map((fmt) => (
              <a
                key={fmt}
                className="btn"
                href={api.exportUrl(run.id, fmt)}
                download
                data-testid={`export-${fmt}`}
              >
                Download .{fmt}
              </a>
            ))}
            {approved > 0 && (
              <a className="btn btn--primary" href={api.exportUrl(run.id, 'xlsx', 'approved')} download>
                Approved only (.xlsx)
              </a>
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
        </Panel>

        <Panel
          title="Export your own data"
          hint="Everything held about this applicant: the profile as entered and a list of every run."
        >
          <div className="row">
            <button
              className="btn"
              disabled={!savedProfile}
              onClick={async () => savedProfile && setExported(await api.exportProfile(savedProfile.id))}
              data-testid="export-profile"
            >
              Show my stored data
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
                {!capabilities.currency.available
                  ? `No exchange rate is available (${capabilities.currency.reason ?? 'unknown reason'}). Amounts are shown in their original currency and funding gaps are reported as not computable.`
                  : capabilities.currency.authoritative
                    ? `Currency figures converted at ${capabilities.currency.provider} rates observed on ${capabilities.currency.rate_date}. ${capabilities.currency.rate_source}`
                    : `Currency figures converted using a bundled snapshot dated ${capabilities.currency.rate_date}, which is not a live rate. Converted amounts are shown as estimates.`}
              </p>
            </div>
          </Panel>
        )}

        <Panel title="Delete everything">
          {deleted ? (
            <Notice kind="info">
              <div>Deleted. The profile, every run, result, claim and checklist are gone.</div>
            </Notice>
          ) : (
            <div className="stack">
              <Notice kind="risk">
                <div>
                  This erases the applicant profile and every research run, result, claim,
                  conflict and checklist attached to it. It cannot be undone.
                </div>
              </Notice>
              <div className="row">
                <input
                  aria-label={`Type ${CONFIRM_WORD} to confirm`}
                  placeholder={`Type ${CONFIRM_WORD} to confirm`}
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                  style={{ maxWidth: '16rem' }}
                  data-testid="delete-confirm"
                />
                <button
                  className="btn btn--danger"
                  disabled={confirm !== CONFIRM_WORD || !savedProfile}
                  onClick={async () => {
                    await deleteEverything();
                    setDeleted(true);
                  }}
                  data-testid="delete-everything"
                >
                  Delete permanently
                </button>
              </div>
            </div>
          )}
        </Panel>

        <p className="xs faint">
          Run {run.id} · started {dateTime(run.started_at)} ·{' '}
          {run.demo_mode ? 'demo corpus' : 'live sources'} · schema-backed audit log available at
          /api/audit (identifiers and actions only, never applicant data).
        </p>
      </div>
    </>
  );
}
