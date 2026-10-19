import {it,expect} from 'vitest';
import {universityDirectory,filterUniversities} from './universityDirectory';
it('loads exactly 500 unique institution identities without invented history placeholders',()=>{
 expect(universityDirectory).toHaveLength(500);expect(universityDirectory.filter(row=>row.history&&row.historySource)).toHaveLength(500);expect(new Set(universityDirectory.map(row=>row.id)).size).toBe(500);
 for(const row of universityDirectory){expect(row.name.length).toBeGreaterThan(1);expect(row.country).toBeTruthy();expect(row.source).toMatch(/^https:\/\//);if(row.history){expect(row.history).not.toMatch(/Description not found|^It is a /);expect(row.historySource).toMatch(/^https:\/\//);}if(row.image)expect(row.image).toMatch(/^(https:\/\/|\/universities\/)/);}
});
it('searches names, alternate encyclopedia identities and country without changing programme facts',()=>{
 expect(filterUniversities('Oxford','').some(row=>row.name==='University of Oxford')).toBe(true);
 expect(filterUniversities('Tokyo','Canada')).toHaveLength(0);
 expect(filterUniversities('nonexistent-university-xyz','')).toHaveLength(0);
});
