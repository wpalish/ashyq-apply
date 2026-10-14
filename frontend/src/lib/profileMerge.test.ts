import { describe, expect, it } from 'vitest';
import { compareProfiles, mergeProfiles } from './profileMerge';
describe('explicit profile comparison', () => {
  it('combines independent reviewed GPA/budget edits without overwriting either', () => {
    const base={funding:{budget:6000},academics:{gpa:4.8}};
    const local={funding:{budget:12000},academics:{gpa:4.8}};
    const server={funding:{budget:6000},academics:{gpa:3.1}};
    const rows=compareProfiles(base,local,server);
    expect(rows).toHaveLength(2);expect(rows.every(r=>!r.conflict)).toBe(true);
    expect(mergeProfiles(server,rows,{})).toEqual({funding:{budget:12000},academics:{gpa:3.1}});
    expect(base.funding.budget).toBe(6000);expect(server.funding.budget).toBe(6000);
  });
  it('requires an explicit choice for the same field', () => {
    const rows=compareProfiles({name:'old'},{name:'mine'},{name:'theirs'});
    expect(rows[0]!.conflict).toBe(true);
    expect(()=>mergeProfiles({name:'theirs'},rows,{})).toThrow(/Choose/);
    expect(mergeProfiles({name:'theirs'},rows,{'["name"]':'local'})).toEqual({name:'mine'});
  });
  it('distinguishes absent, null, and empty values', () => {
    const rows=compareProfiles({value:'a'},{value:null},{});
    expect(rows[0]!.local).toEqual({present:true,value:null});
    expect(rows[0]!.server).toEqual({present:false});
    expect(mergeProfiles({},rows,{'["value"]':'local'})).toEqual({value:null});
    expect(mergeProfiles({},rows,{'["value"]':'server'})).toEqual({});
  });
  it('keeps arrays atomic instead of accidentally merging by index', () => {
    const rows=compareProfiles({fields:['a']},{fields:['b']},{fields:['a','c']});
    expect(rows).toHaveLength(1);expect(rows[0]!.path).toEqual(['fields']);expect(rows[0]!.conflict).toBe(true);
    expect(mergeProfiles({fields:['a','c']},rows,{'["fields"]':'local'})).toEqual({fields:['b']});
  });
  it('compares objects semantically even when keys were reordered', () => {
    expect(compareProfiles({o:{a:1,b:2}},{o:{b:2,a:1}},{o:{a:1,b:2}})).toEqual([]);
  });
});
