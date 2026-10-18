import { lazy, Suspense, useEffect, useId, useRef, useState } from 'react';
import { useTranslation } from '@/lib/useTranslation';
import { FileImage, FilePdf, UploadSimple } from '@phosphor-icons/react';

const LocalPdfPreview = lazy(() => import('./LocalPdfPreview'));
type Preview = { name:string; size:number; url:string; image:boolean; pdfBytes:Uint8Array|null };

/** Local inspection only. A selected file is never a saved/uploaded document. */
export function LocalDocumentPreview({ label }: { label:string }) {
  const id = useId();
  const { locale } = useTranslation();
  const ru = locale !== 'en';
  const generation = useRef(0);
  const [value, setValue] = useState<Preview|null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  useEffect(() => { const token = generation; return () => { ++token.current; }; }, []);
  useEffect(() => () => { if (value) URL.revokeObjectURL(value.url); }, [value]);

  const choose = async (file:File|undefined) => {
    const request = ++generation.current;
    setError(''); setValue(null); setBusy(false);
    if (!file) return;
    if (file.size > 10 * 1024 * 1024) {
      setError(ru ? 'Выбери PDF, PNG или JPEG размером до 10 МБ.' : 'Choose a PDF, PNG or JPEG up to 10 MB.');
      return;
    }
    setBusy(true);
    try {
      const bytes = new Uint8Array(await file.slice(0, 12).arrayBuffer());
      if (generation.current !== request) return;
      const pdf = new TextDecoder().decode(bytes.slice(0, 5)) === '%PDF-';
      const png = [137, 80, 78, 71, 13, 10, 26, 10].every((byte, i) => bytes[i] === byte);
      const jpeg = bytes[0] === 255 && bytes[1] === 216 && bytes[2] === 255;
      if (!pdf && !png && !jpeg) {
        throw new Error(ru ? 'Формат файла не соответствует PDF, PNG или JPEG.' : 'This file is not a supported PDF, PNG or JPEG.');
      }
      const blob = file.slice(0, file.size, pdf ? 'application/pdf' : png ? 'image/png' : 'image/jpeg');
      const pdfBytes = pdf ? new Uint8Array(await file.arrayBuffer()) : null;
      if (generation.current !== request) return;
      setValue({ name:file.name, size:file.size, url:URL.createObjectURL(blob), image:!pdf, pdfBytes });
    } catch (failure) {
      if (generation.current === request) setError(failure instanceof Error ? failure.message : (ru ? 'Не удалось прочитать файл.' : 'The file could not be read.'));
    } finally {
      if (generation.current === request) setBusy(false);
    }
  };

  return <div className="local-document stack">
    <p className="small muted">{ru
      ? <>Проверь файл «{label}» на этом устройстве. Он не загружается на сервер и не отмечается готовым. Просмотр очистится при выходе со страницы или смене дела.</>
      : <>Inspect a file for “{label}” on this device. It is not uploaded, saved or marked as prepared. The preview is cleared when you leave this page or switch applicant.</>}
    </p>
    <label className="local-document__picker" htmlFor={id}
      onDragOver={event => event.preventDefault()}
      onDrop={event => { event.preventDefault(); void choose(event.dataTransfer.files[0]); }}>
      <UploadSimple size={24}/>
      <strong>{ru ? 'Перетащи файл сюда или выбери на компьютере' : 'Choose a file to inspect'}</strong>
      <span className="xs muted">{ru ? 'PDF, PNG или JPEG · не более 10 МБ' : 'PDF, PNG or JPEG · up to 10 MB'}</span>
      <input id={id} type="file" accept="application/pdf,image/png,image/jpeg" onChange={event => {
        const file = event.target.files?.[0]; event.currentTarget.value = ''; void choose(file);
      }}/>
    </label>
    {busy && <p role="status">{ru ? 'Читаем файл на устройстве…' : 'Reading file on this device…'}</p>}
    {error && <p role="alert">{error}</p>}
    {value && <div className="stack stack--tight">
      <div className="row">
        {value.image ? <FileImage size={24}/> : <FilePdf size={24}/>}
        <strong className="small">{value.name}</strong>
        <span className="xs muted">{(value.size / 1024).toFixed(0)} KB · {ru ? 'только на устройстве' : 'local only'}</span>
      </div>
      <a className="btn" href={value.url} target="_blank" rel="noopener noreferrer">
        {ru ? 'Открыть файл в новой вкладке' : 'Open file preview in a new tab'}
      </a>
      <button className="btn btn--ghost" onClick={() => { ++generation.current; setValue(null); setBusy(false); }}>
        {ru ? 'Очистить просмотр' : 'Clear preview'}
      </button>
      {value.image
        ? <img className="local-document__image" src={value.url} alt={ru ? 'Локальный просмотр выбранного документа' : 'Local preview of the selected document'}/>
        : value.pdfBytes
          ? <Suspense fallback={<p role="status">{ru ? 'Загружаем локальный просмотр PDF…' : 'Loading local PDF reader…'}</p>}><LocalPdfPreview data={value.pdfBytes}/></Suspense>
          : null}
    </div>}
  </div>;
}
