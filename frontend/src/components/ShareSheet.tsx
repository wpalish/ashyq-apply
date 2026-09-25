/**
 * The share sheet (concept Q, screen 14): choose a card, choose what it
 * shows, then share it or save it.
 *
 * The card is drawn on this device and nothing is posted: "Share…" hands the
 * picture to the phone's own share sheet (Instagram, Telegram, WhatsApp are
 * there), and "Save image" downloads it. The privacy defaults, for a
 * 16-year-old: the name, the price after grants and the student's own scores
 * are off; the school, city and documents are never on a card - the sheet says
 * so under the switches, and names the exact word the name switch would add.
 */

import { useEffect, useMemo, useRef, useState } from 'react';
import {
  STORY_DEFAULTS, STORY_TITLE, firstName, storyKinds, storyModel, storyText,
  type StoryKind, type StoryOptions,
} from '@/lib/story';
import { drawStory, storyFile } from '@/lib/storyCanvas';
import type { ProgramResult } from '@/types';

export function ShareSheet({
  results, result = null, profile, demo, onClose,
}: {
  results: ProgramResult[];
  /** The programme it was opened on; without one, only the map. */
  result?: ProgramResult | null;
  profile: unknown;
  demo: boolean;
  onClose: () => void;
}) {
  const kinds = storyKinds(result);
  const [kind, setKind] = useState<StoryKind>(kinds[0]!);
  const [options, setOptions] = useState<StoryOptions>(STORY_DEFAULTS);
  const [status, setStatus] = useState('');
  const [ready, setReady] = useState(false);
  const canvas = useRef<HTMLCanvasElement>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const name = firstName(profile);
  const model = useMemo(
    () => storyModel(kind, { results, result, profile, demo }, options),
    [kind, results, result, profile, demo, options],
  );

  const sheet = useRef<HTMLDivElement>(null);
  // A modal: focus moves in, stays in, and goes back to what opened it.
  useEffect(() => {
    const opener = document.activeElement as HTMLElement | null;
    heading.current?.focus();
    return () => opener?.focus?.();
  }, []);
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
        return;
      }
      if (event.key !== 'Tab' || !sheet.current) return;
      const focusable = [...sheet.current.querySelectorAll<HTMLElement>('button:not([disabled]), input:not([disabled])')];
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (!first || !last) return;
      if (event.shiftKey && (document.activeElement === first || document.activeElement === heading.current)) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  useEffect(() => {
    let live = true;
    setReady(false);
    if (canvas.current) {
      drawStory(canvas.current, model).then(() => { if (live) setReady(true); }).catch(() => {});
    }
    return () => { live = false; };
  }, [model]);

  const fileName = `ashyq-${kind}.png`;
  const canShareFiles = typeof navigator !== 'undefined' && typeof navigator.canShare === 'function'
    && typeof File !== 'undefined'
    && navigator.canShare({ files: [new File([''], fileName, { type: 'image/png' })] });

  const share = async () => {
    if (!canvas.current) return;
    const file = await storyFile(canvas.current, fileName);
    if (!file) return;
    try {
      await navigator.share({ files: [file], title: STORY_TITLE[kind] });
      setStatus('Shared.');
    } catch (error) {
      // Closing the phone's sheet is a choice, not an error.
      if ((error as { name?: string }).name !== 'AbortError') setStatus('This device could not share the image; save it instead.');
    }
  };

  const save = async () => {
    if (!canvas.current) return;
    const file = await storyFile(canvas.current, fileName);
    if (!file) return;
    const url = URL.createObjectURL(file);
    const link = document.createElement('a');
    link.href = url;
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    setStatus(`Saved ${fileName}.`);
  };

  const toggle = (key: keyof StoryOptions) => setOptions((prev) => ({ ...prev, [key]: !prev[key] }));

  return (
    <div className="sheet-backdrop" onClick={onClose}>
      <div
        className="sheet"
        ref={sheet}
        role="dialog"
        aria-modal="true"
        aria-labelledby="share-title"
        onClick={(event) => event.stopPropagation()}
        data-testid="share-sheet"
      >
        <div className="sheet__head">
          <h2 className="sheet__title" id="share-title" tabIndex={-1} ref={heading}>Share a story</h2>
          <button type="button" className="btn btn--sm" onClick={onClose} data-testid="share-close">Close</button>
        </div>

        <div className="sheet__body">
          <div className="sheet__preview">
            <canvas
              ref={canvas}
              className="sheet__canvas"
              width={1080}
              height={1920}
              role="img"
              aria-label={`The card: ${storyText(model).replace(/([^.])\n/g, '$1. ').replace(/\n/g, ' ')}`}
              data-testid="share-canvas"
              data-ready={ready ? 'true' : undefined}
            />
          </div>

          <div className="sheet__controls">
            <fieldset className="sheet__group">
              <legend>Card</legend>
              {kinds.map((k) => (
                <label key={k} className={`sheet__choice${kind === k ? ' is-on' : ''}`}>
                  <input
                    type="radio"
                    name="story-kind"
                    value={k}
                    checked={kind === k}
                    onChange={() => setKind(k)}
                    data-testid={`share-kind-${k}`}
                  />
                  {STORY_TITLE[k]}
                </label>
              ))}
              {result && !kinds.includes('requirements') && (
                <p className="sheet__hint">"Requirements met" appears when every requirement checked for this programme is met.</p>
              )}
            </fieldset>

            <fieldset className="sheet__group">
              <legend>What it shows</legend>
              <label className="sheet__switch">
                <input
                  type="checkbox"
                  checked={options.name && Boolean(name)}
                  disabled={!name}
                  onChange={() => toggle('name')}
                  data-testid="share-name"
                />
                <span>
                  Name
                  <span className="sheet__hint">
                    {name ? `adds "${name}", the first word of this case's name` : 'no name in this case\'s label'}
                  </span>
                </span>
              </label>
              {kind === 'route' && (
                <label className="sheet__switch">
                  <input type="checkbox" checked={options.price} onChange={() => toggle('price')} data-testid="share-price" />
                  <span>
                    Price after grants
                    <span className="sheet__hint">what is left to pay a year, if awarded</span>
                  </span>
                </label>
              )}
              {kind === 'requirements' && (
                <label className="sheet__switch">
                  <input type="checkbox" checked={options.scores} onChange={() => toggle('scores')} data-testid="share-scores" />
                  <span>
                    My scores
                    <span className="sheet__hint">beside the published minimums</span>
                  </span>
                </label>
              )}
            </fieldset>

            <p className="sheet__privacy">
              Your school, city and documents are never on a card, and a name only when you add it. The
              picture is made on this device, and nothing is posted until you share it.
            </p>

            <div className="sheet__actions">
              {canShareFiles && (
                <button type="button" className="btn btn--primary" onClick={share} disabled={!ready} data-testid="share-go">
                  Share…
                </button>
              )}
              <button
                type="button"
                className={`btn${canShareFiles ? '' : ' btn--primary'}`}
                onClick={save}
                disabled={!ready}
                data-testid="share-save"
              >
                Save image
              </button>
            </div>
            <p className="sheet__status" aria-live="polite" data-testid="share-status">{status}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
