import type { BookRouteCardModel } from './bookSharePresentation';
type DrawResult='drawn'|'stale'|'too_long'|'unavailable';
function wrap(ctx:CanvasRenderingContext2D,text:string,width:number){
 const lines:string[]=[];let line='';
 for(const word of text.split(/\s+/)){
  const candidate=line?`${line} ${word}`:word;
  if(ctx.measureText(candidate).width<=width){line=candidate;continue;}
  if(line){lines.push(line);line='';}
  for(const character of word){if(line&&ctx.measureText(line+character).width>width){lines.push(line);line='';}line+=character;}
 }
 if(line)lines.push(line);return lines;
}
/** Canvas uses the same disclosure model and composition as BookShare. No upload. */
export async function drawBookRouteCard(canvas:HTMLCanvasElement,model:BookRouteCardModel,current:()=>boolean):Promise<DrawResult>{
 const ctx=canvas.getContext('2d');if(!ctx)return 'unavailable';
 try{await document.fonts.ready;}catch{/* System fallback keeps text export usable. */}
 if(!current())return 'stale';
 ctx.font='700 60px Inter, sans-serif';const title=wrap(ctx,model.title,900);
 const blocks=model.destinations.map(item=>{ctx.font='700 26px Inter, sans-serif';const name=wrap(ctx,item.university,770);ctx.font='400 24px Inter, sans-serif';return {name,detail:wrap(ctx,item.detail,770)};});
 ctx.font='500 23px Inter, sans-serif';const signature=model.signature?wrap(ctx,`— ${model.signature}`,720):[];
 const bodyHeight=blocks.reduce((n,item)=>n+(item.name.length+item.detail.length)*35+22,0);
 const bodyStart=214+title.length*68;
 const height=Math.max(780,bodyStart+bodyHeight+230+signature.length*32);
 if(height>16000)return 'too_long';canvas.width=1200;canvas.height=height;
 const gradient=ctx.createLinearGradient(0,0,1200,height);gradient.addColorStop(0,'#020d26');gradient.addColorStop(1,'#082e82');
 ctx.save();ctx.beginPath();if(typeof ctx.roundRect==='function')ctx.roundRect(0,0,1200,height,24);else ctx.rect(0,0,1200,height);ctx.clip();ctx.fillStyle=gradient;ctx.fillRect(0,0,1200,height);
 const art=new Image();art.src='/book/globe.webp';try{await art.decode();if(!current()){ctx.restore();return 'stale';}ctx.save();ctx.globalAlpha=.8;ctx.globalCompositeOperation='screen';ctx.filter='invert(1) hue-rotate(180deg) saturate(2) brightness(1.2)';ctx.drawImage(art,510,130,1000,1000);ctx.restore();}catch{/* Decorative art can fail without losing the selected text. */}
 if(!current()){ctx.restore();return 'stale';}
 ctx.strokeStyle='#305cff';ctx.lineWidth=6;ctx.beginPath();ctx.arc(82,82,17,-.9,4.9);ctx.stroke();ctx.fillStyle='#305cff';ctx.beginPath();ctx.arc(94,68,4.5,0,Math.PI*2);ctx.fill();
 ctx.fillStyle='#fff';ctx.font='700 42px Inter, sans-serif';ctx.fillText('unimatch',116,98);ctx.font='400 22px Inter, sans-serif';ctx.fillStyle='#c6dcff';ctx.textAlign='right';ctx.fillText('Мой маршрут',1140,94);ctx.textAlign='left';
 ctx.fillStyle='#fff';ctx.font='700 60px Inter, sans-serif';let y=214;for(const line of title){ctx.fillText(line,60,y);y+=68;}y+=18;
 for(const block of blocks){ctx.font='700 26px Inter, sans-serif';for(const line of block.name){ctx.fillText(line,60,y);y+=35;}ctx.font='400 24px Inter, sans-serif';for(const line of block.detail){ctx.fillText(line,60,y);y+=35;}y+=22;}
 if(model.empty){ctx.font='400 24px Inter, sans-serif';for(const line of wrap(ctx,model.empty,770)){ctx.fillText(line,60,y);y+=35;}}
 let footer=height-150-signature.length*32;ctx.font='400 23px Inter, sans-serif';for(const line of model.quote){ctx.fillText(line,60,footer);footer+=32;}ctx.font='500 23px Inter, sans-serif';for(const line of signature){ctx.fillText(line,60,footer+10);footer+=32;}
 ctx.textAlign='right';ctx.font='700 23px Inter, sans-serif';ctx.fillText('unimatch',1140,height-135);ctx.font='400 18px Inter, sans-serif';ctx.fillStyle='#c7d8ff';ctx.fillText('Больше возможностей',1140,height-102);ctx.fillText('для твоего завтра',1140,height-74);ctx.textAlign='left';ctx.font='400 16px Inter, sans-serif';ctx.fillText(model.notice,60,height-28);ctx.restore();return 'drawn';
}
