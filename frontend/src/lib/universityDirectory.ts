import records from '@/data/universityDirectory.json';
export interface UniversityIdentity {id:string;name:string;country:string;city:string;domain:string|null;website:string|null;image:string|null;imageKind:string|null;imageSource:string|null;history:string|null;historySource:string|null;founded:number|null;type:string|null;students:number|null;internationalPercent:number|null;subjectAreas:string[];source:string;snapshotDate:string;encyclopediaTitle:string|null}
export const universityDirectory:UniversityIdentity[]=records;
export function filterUniversities(query:string,country:string){
 const norm=(value:string)=>value.normalize('NFKD').replace(/[\u0300-\u036f]/g,'').toLocaleLowerCase();
 const tokens=norm(query).trim().split(/\s+/).filter(Boolean);
 return records.filter(row=>(!country||row.country===country)&&tokens.every(token=>norm([row.name,row.city,row.country,row.domain??'',row.encyclopediaTitle??''].join(' ')).includes(token)));
}
