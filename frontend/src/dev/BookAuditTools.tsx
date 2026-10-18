/** Opt-in local development control. No application API calls or production entry. */
import { useEffect, useRef, useState } from 'react';
import type { AxeResults } from 'axe-core';
function summarize(result:AxeResults){
 const rows=(items:AxeResults['violations'])=>items.map(item=>({id:item.id,impact:item.impact,help:item.help,helpUrl:item.helpUrl,nodes:item.nodes.map(node=>({target:node.target,failureSummary:node.failureSummary}))}));
 return {engine:result.testEngine,at:result.timestamp,path:location.pathname+location.hash,width:innerWidth,height:innerHeight,violations:rows(result.violations),incomplete:rows(result.incomplete),passes:result.passes.map(item=>item.id)};
}
export function BookAuditTools(){
 const [busy,setBusy]=useState(false);const [output,setOutput]=useState('');const alive=useRef(true);
 useEffect(()=>{alive.current=true;return()=>{alive.current=false;};},[]);
 const run=async()=>{
  if(busy)return;setBusy(true);setOutput('');const route=location.href;
  try{
   const {default:axe}=await import('axe-core');
   if(!alive.current||location.href!==route)return;
   const result=await axe.run({exclude:[['.ui-book-audit-tools']]},{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa','best-practice']}});
   if(alive.current&&location.href===route)setOutput(JSON.stringify(summarize(result),null,2));
  }catch(error){if(alive.current)setOutput(JSON.stringify({error:String(error)}));}
  finally{if(alive.current)setBusy(false);}
 };
 return <aside className="ui-book-audit-tools" aria-label="Локальная проверка доступности" style={{position:'fixed',right:12,bottom:12,zIndex:10000,background:'var(--surface)',border:'2px solid var(--accent)',borderRadius:10,padding:10,width:330,maxWidth:'calc(100vw - 24px)',boxShadow:'var(--shadow-lg)'}}><details><summary style={{cursor:'pointer',fontSize:12}}>Только локальная QA · axe</summary><p style={{fontSize:11,marginTop:8}}>Проверка текущей страницы на устройстве. Результаты не отправляются на сервер. В production этот инструмент отсутствует.</p><button type="button" disabled={busy} onClick={()=>void run()} className="btn btn--sm">{busy?'Проверяем разметку…':'Проверить доступность страницы'}</button><p role="status" style={{fontSize:12,marginTop:8}}>{busy?'Идёт проверка':output?'Проверка завершена':'Ожидает запуска'}</p>{output&&<pre data-testid="book-a11y-output" tabIndex={0} aria-label="Результат проверки доступности" style={{maxHeight:'55vh',overflow:'auto',fontSize:10,whiteSpace:'pre-wrap',overflowWrap:'anywhere'}}>{output}</pre>}</details></aside>;
}
