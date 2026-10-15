from pathlib import Path
import json,hashlib,difflib
r=Path(__file__).resolve().parent;p=r/'applications4d-proposal';old=r/'applications4d-preimages';manifest=json.loads((r/'APPLICATIONS_4D_PREPARATION.json').read_text());h=lambda x:hashlib.sha256(x).hexdigest();rows={}
for path,sha in manifest['paths'].items():
 q=p/path;assert q.is_file(),path
 before=(old/path).read_bytes() if sha is not None else b'';after=q.read_bytes();assert sha is None or h(before)==sha
 rows[path]={'preimage':sha,'postimage':h(after),'bytes':len(after)}
 (r/('applications4d-'+Path(path).name+'.diff')).write_text(''.join(difflib.unified_diff(before.decode().splitlines(True),after.decode().splitlines(True),fromfile=path+' before',tofile=path+' proposed')))
a=(old/'frontend/src/types/admissionsActions.ts').read_text();b=(p/'frontend/src/types/admissionsActions.ts').read_text()
def block(t,n):
 start=t.index('export function '+n+'(');opening=t.index('{',start);depth=1;i=opening+1
 while depth:
  if t[i]=='{':depth+=1
  if t[i]=='}':depth-=1
  i+=1
 return t[start:i]
names=['isActionRequestV1','isActionWriteReceiptShapeV1','isActionsCurrentOutV1','isActionsHistoryOutV1']
checks={n:h(block(a,n).encode()) for n in names};assert all(block(a,n)==block(b,n) for n in names)
review={'status':'ROOT_SOURCE_REVIEW_ONLY_NOT_APPLIED_OR_EXECUTED','source_postimages':rows,'unchanged_frozen_v1_functions_sha256':checks,'review':['Closed version2 operations, original V1 guards unchanged','Removal immutable retained snapshot, exact own IDs/expected revision, explicit confirm, no linked-task cascade','Context keeps exact saved award/programme and locks declared target changes in UI; native API repeats ownership/context guards','Metadata sends full explicit personal fields and dependencies without rebinding or transferring old report','Unknown response freezes reviewed draft; original journal UUID/body preserved; selected own ACK only cleanup unchanged','Case rendered+synchronous controller fence retained; no name-based navigation or fake manual result IDs','Native backend full4c still source-frozen; synthetic Node fixtures never native API evidence'],'acceptance':'Pending native frontend type/lint/unit/build and later real UI/API persistence journey'}
(r/'APPLICATIONS_4D_ROOT_REVIEW.json').write_text(json.dumps(review,indent=2)+'\n');print(len(rows),'external proposed paths; frozen V1 functions byte-equal; native frontend NOT_RUN')
