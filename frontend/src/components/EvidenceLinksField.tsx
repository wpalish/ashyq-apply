import { useEffect, useRef, useState } from 'react';
import { Field } from '@/components/primitives';

const MAX_LINKS = 5;
const MAX_LINK_LENGTH = 200;

type EvidenceRow = {
  id: number;
  value: string;
  materialized: boolean;
};

let nextEvidenceRowId = 0;

const makeRow = (value = '', materialized = true): EvidenceRow => ({
  id: nextEvidenceRowId++,
  value,
  materialized,
});

const rowValues = (rows: EvidenceRow[]): string[] =>
  rows.filter((row) => row.materialized).map((row) => row.value);

const equalLinks = (left: string[], right: string[]): boolean =>
  left.length === right.length && left.every((link, index) => link === right[index]);

export function isEvidenceUrl(value: string): boolean {
  if (value === '') return true;
  if (value.length > MAX_LINK_LENGTH || value !== value.trim()) return false;
  try {
    const parsed = new URL(value);
    return (parsed.protocol === 'http:' || parsed.protocol === 'https:') && Boolean(parsed.hostname);
  } catch {
    return false;
  }
}

export type EvidenceLinksCopy = {
  label: string;
  hint: string;
  rowLabel: string;
  add: string;
  remove: string;
  invalid: string;
  limit: string;
};

export function EvidenceLinksField({
  idPrefix,
  scopeKey,
  value,
  onChange,
  copy,
}: {
  idPrefix: string;
  scopeKey: string;
  value: string[];
  onChange: (value: string[]) => void;
  copy: EvidenceLinksCopy;
}) {
  const [rows, setRows] = useState<EvidenceRow[]>(() => value.map((link) => makeRow(link)));
  const pendingFocus = useRef<number | 'add' | null>(null);
  const lastEmitted = useRef<string[] | null>(null);
  const addRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (lastEmitted.current && equalLinks(value, lastEmitted.current)) {
      lastEmitted.current = null;
      return;
    }
    setRows(value.map((link) => makeRow(link)));
  }, [scopeKey, value]);

  useEffect(() => {
    const target = pendingFocus.current;
    if (target === null) return;
    pendingFocus.current = null;
    if (target === 'add') addRef.current?.focus();
    else document.getElementById(`${idPrefix}-${target}`)?.focus();
  }, [idPrefix, rows]);

  const updateRows = (nextRows: EvidenceRow[]) => {
    setRows(nextRows);
    const nextValue = rowValues(nextRows);
    if (equalLinks(nextValue, value)) return;
    lastEmitted.current = nextValue;
    onChange(nextValue);
  };

  const addRow = () => {
    if (rows.length >= MAX_LINKS) return;
    const row = makeRow('', false);
    pendingFocus.current = row.id;
    setRows((current) => [...current, row]);
  };

  const removeRow = (index: number) => {
    const nextRows = rows.filter((_, rowIndex) => rowIndex !== index);
    pendingFocus.current = nextRows[index]?.id ?? nextRows[index - 1]?.id ?? 'add';
    updateRows(nextRows);
  };

  const hintId = `${idPrefix}-hint`;

  return (
    <fieldset className="evidence-links" data-testid={idPrefix}>
      <legend className="field__label">{copy.label}</legend>
      <p className="field__hint" id={hintId}>{copy.hint}</p>
      <div className="evidence-links__rows">
        {rows.map((row, index) => {
          const inputId = `${idPrefix}-${row.id}`;
          const errorId = `${inputId}-error`;
          const invalid = row.value !== '' && !isEvidenceUrl(row.value);
          return (
            <div className="evidence-links__row" key={row.id}>
              <div className="evidence-links__control">
                <Field label={`${copy.rowLabel} ${index + 1}`} htmlFor={inputId}>
                  <input
                    id={inputId}
                    type="url"
                    inputMode="url"
                    autoCapitalize="none"
                    autoComplete="url"
                    spellCheck={false}
                    maxLength={MAX_LINK_LENGTH}
                    value={row.value}
                    aria-invalid={invalid || undefined}
                    aria-describedby={`${hintId}${invalid ? ` ${errorId}` : ''}`}
                    onChange={(event) => {
                      const nextRows = rows.map((candidate, rowIndex) => rowIndex === index
                        ? { ...candidate, value: event.target.value, materialized: event.target.value !== '' }
                        : candidate);
                      updateRows(nextRows);
                    }}
                  />
                </Field>
                {invalid && <p className="field__error" id={errorId}>{copy.invalid}</p>}
              </div>
              <button
                className="btn btn--sm"
                type="button"
                aria-label={`${copy.remove}: ${copy.rowLabel} ${index + 1}`}
                onClick={() => removeRow(index)}
              >
                {copy.remove}
              </button>
            </div>
          );
        })}
      </div>
      <div className="evidence-links__add">
        <button
          ref={addRef}
          className="btn btn--sm"
          type="button"
          disabled={rows.length >= MAX_LINKS}
          title={rows.length >= MAX_LINKS ? copy.limit : undefined}
          onClick={addRow}
        >
          {copy.add}
        </button>
        {rows.length >= MAX_LINKS && <span className="field__hint">{copy.limit}</span>}
      </div>
    </fieldset>
  );
}
