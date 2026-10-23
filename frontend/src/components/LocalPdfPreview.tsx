/** Lazy, local-only canvas reader. No PDF actions, scripts or external document URL. */
import { useEffect, useRef, useState } from 'react';
import { getDocument, GlobalWorkerOptions, type PDFDocumentProxy } from 'pdfjs-dist';
import workerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url';
import { ArrowLeft, ArrowRight, Minus, Plus } from '@phosphor-icons/react';
import { useTranslation } from '@/lib/useTranslation';

GlobalWorkerOptions.workerSrc = workerUrl;

export default function LocalPdfPreview({ data }: { data:Uint8Array }) {
  const { locale }=useTranslation(); const ru=locale!=='en';
  const container=useRef<HTMLDivElement>(null); const canvas=useRef<HTMLCanvasElement>(null);
  const [document,setDocument]=useState<PDFDocumentProxy|null>(null);
  const [page,setPage]=useState(1); const [zoom,setZoom]=useState(1); const [width,setWidth]=useState(600);
  const [loading,setLoading]=useState(true); const [rendering,setRendering]=useState(false);
  const [error,setError]=useState(''); const [text,setText]=useState('');
  useEffect(()=>{
    const element=container.current; if(!element)return;
    const update=()=>setWidth(Math.max(120,Math.floor(element.getBoundingClientRect().width)-24));
    update(); const observer=new ResizeObserver(update); observer.observe(element); return()=>observer.disconnect();
  },[]);
  useEffect(()=>{
    let active=true; setLoading(true); setDocument(null); setError(''); setPage(1); setText('');
    // StrictMode can replay this effect; the worker receives its own byte copy.
    const task=getDocument({data:data.slice(),disableAutoFetch:true,disableRange:true,disableStream:true,
      useWorkerFetch:false,useSystemFonts:true,useWasm:false,enableXfa:false,stopAtErrors:true,
      maxImageSize:16_000_000,canvasMaxAreaInBytes:8_000_000});
    task.promise.then(value=>{if(active){setDocument(value);setLoading(false);}}).catch(()=>{
      if(active){setError('read');setLoading(false);}
    });
    return()=>{active=false;void task.destroy().catch(()=>{});};
  },[data]);
  useEffect(()=>{
    const element=canvas.current; if(!document||!element)return;
    let active=true; let renderTask:ReturnType<Awaited<ReturnType<PDFDocumentProxy['getPage']>>['render']>|null=null;
    setRendering(true);setText('');setError('');
    const draw=async()=>{
      const current=await document.getPage(page); if(!active)return;
      const base=current.getViewport({scale:1}); const dpr=Math.min(window.devicePixelRatio||1,1.5);
      const scale=Math.min(width/base.width*zoom,Math.sqrt(2_000_000/(base.width*base.height*dpr*dpr)));
      const viewport=current.getViewport({scale});
      element.width=Math.ceil(viewport.width*dpr);element.height=Math.ceil(viewport.height*dpr);
      element.style.width=`${viewport.width}px`;element.style.height=`${viewport.height}px`;
      renderTask=current.render({canvas:element,viewport,transform:dpr===1?undefined:[dpr,0,0,dpr,0,0]});
      await renderTask.promise; if(!active)return;
      setRendering(false);
      const content=await current.getTextContent();if(active)setText(content.items.map(item=>'str' in item?item.str:'').join(' ').slice(0,50_000));
    };
    void draw().catch(()=>{if(active){setRendering(false);setError('render');}});
    return()=>{active=false;renderTask?.cancel();};
  },[document,page,width,zoom]);
  return <div className="local-pdf" ref={container}>
    <div className="local-pdf__toolbar"><button type="button" disabled={!document||page<=1} onClick={()=>setPage(old=>Math.max(1,old-1))} aria-label={ru?'Предыдущая страница':'Previous page'}><ArrowLeft size={17}/></button><span>{ru?'Страница':'Page'} {document?page:'—'} / {document?.numPages??'—'}</span><button type="button" disabled={!document||page>=document.numPages} onClick={()=>setPage(old=>Math.min(document?.numPages??old,old+1))} aria-label={ru?'Следующая страница':'Next page'}><ArrowRight size={17}/></button><span className="local-pdf__zoom"><button type="button" aria-label={ru?'Уменьшить масштаб':'Zoom out'} disabled={zoom<=0.5} onClick={()=>setZoom(old=>Math.max(0.5,old-0.25))}><Minus size={17}/></button><span>{Math.round(zoom*100)}%</span><button type="button" aria-label={ru?'Увеличить масштаб':'Zoom in'} disabled={zoom>=1.5} onClick={()=>setZoom(old=>Math.min(1.5,old+0.25))}><Plus size={17}/></button></span></div>
    {(loading||rendering)&&<p className="local-pdf__notice" role="status">{ru?'Открываем страницу на устройстве…':'Rendering page on this device…'}</p>}
    {error&&<p className="local-pdf__notice" role="alert">{ru?'Не удалось показать эту страницу. Используй ссылку локального просмотра выше.':'This page could not be rendered. Use the local preview link above.'}</p>}
    <div className="local-pdf__paper"><canvas key={`${page}:${width}:${zoom}`} ref={canvas} role="img" aria-label={ru?`Страница ${page} выбранного PDF`:`Page ${page} of the selected PDF`}/></div>
    {text&&<details className="local-pdf__text"><summary>{ru?'Текст страницы':'Page text'}</summary><p>{text}</p></details>}
  </div>;
}
