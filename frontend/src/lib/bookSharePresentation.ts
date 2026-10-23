import type { ProgramResult } from '@/types';
export interface BookRouteCardModel {
 title:string;
 destinations:{id:string;university:string;detail:string}[];
 signature:string|null;
 empty:string|null;
 quote:string[];
 notice:string;
}
/** The explicit public subset shared by the preview and local image export. */
export function bookRouteCardModel(programmes:ProgramResult[],name:string|undefined,includeName:boolean,includeProgrammes:boolean):BookRouteCardModel {
 return {title:includeProgrammes&&programmes[0]?programmes[0].country:'Твой следующий шаг',destinations:includeProgrammes?programmes.map(item=>({id:item.id,university:item.university,detail:`${item.program} · ${item.country}`})):[],signature:includeName&&name?name:null,empty:!programmes.length?'Выбери программу, чтобы добавить направление.':null,quote:['«Большие цели начинаются','с первого шага»'],notice:'Изучаю возможности. Выбор программы не означает поступление.'};
}
