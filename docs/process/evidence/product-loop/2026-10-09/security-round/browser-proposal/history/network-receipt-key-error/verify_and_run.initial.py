from pathlib import Path
import hashlib,json,subprocess,os,datetime
ROOT=Path(__file__).resolve().parent.parent
REPO=Path('/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply')
STOP=REPO.parent/'local-round7/provider-STOP.json'
SHA_STOP='65b5ff0e9a71b1ec6cb4e72c366b0700e53ebe7d925ad55db379c8d2365a0b1d'
def info(p):
 b=p.read_bytes();return {'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
def pins():
 files={}
 for tree in ['original','proposed']:
  for p in sorted((ROOT/tree).rglob('*')):
   if p.is_file():files[str(p.relative_to(ROOT))]=info(p)
 return files
base=json.loads((ROOT/'base-source-pins.json').read_text())['files']
for rel,expected in base.items():assert info(REPO/rel)==expected,(rel,'base drift')
assert info(STOP)['sha256']==SHA_STOP
before=pins()
(ROOT/'ready-source-before.json').write_text(json.dumps({'files':before,'stop':info(STOP)},indent=2)+'\n')
front=ROOT/'runtime/on/frontend'
for p in (ROOT/'proposed/frontend').rglob('*'):
 if p.is_file():assert info(front/p.relative_to(ROOT/'proposed/frontend'))==info(p)
env={'PATH':'/Users/wpalish/.local/bin:/usr/bin:/bin:/usr/sbin:/sbin','NODE_OPTIONS':'--require='+str(ROOT/'support/deny-network.cjs'),'REVIEW_NETWORK_LOG_DIR':str(ROOT/'logs/ready-on')}
node='/Users/wpalish/.local/bin/node'
commands=[
 ('native',[node,'node_modules/vitest/vitest.mjs','run','src/AuthGate.test.tsx','src/lib/store.test.tsx','src/api/client.privacy.test.ts','src/screens/DocumentsScreen.privacy.test.tsx','--reporter=default','--reporter=junit','--outputFile.junit='+str(ROOT/'logs/ready-on/junit.xml')]),
 ('typecheck',[node,'node_modules/typescript/bin/tsc','--noEmit']),
 ('lint',[node,'node_modules/eslint/bin/eslint.js',*[str(p.relative_to(ROOT/'proposed/frontend')) for p in sorted((ROOT/'proposed/frontend/src').rglob('*')) if p.is_file()]]),
 ('old-body',[node,str(ROOT/'support/old-body-audit.cjs')]),
]
records=[]
for name,argv in commands:
 started=datetime.datetime.now(datetime.timezone.utc).isoformat()
 with (ROOT/f'logs/ready-on/{name}.stdout.log').open('wb') as out,(ROOT/f'logs/ready-on/{name}.stderr.log').open('wb') as err:
  result=subprocess.run(argv,cwd=front,env=env,stdout=out,stderr=err,timeout=60)
 records.append({'name':name,'argv':argv,'cwd':str(front),'started_at':started,'exit_code':result.returncode})
 assert result.returncode==0,(name,result.returncode)
assert before==pins()
for rel,expected in base.items():assert info(REPO/rel)==expected,(rel,'base drift after')
assert info(STOP)['sha256']==SHA_STOP
net=[json.loads(p.read_text()) for p in (ROOT/'logs').rglob('network-*.json')]
assert all(r['attempts']==0 for r in net),net
(ROOT/'ready-source-after.json').write_text(json.dumps({'files':pins(),'stop':info(STOP)},indent=2)+'\n')
(ROOT/'execution.json').write_text(json.dumps({'commands':records,'primary_source_base_unchanged':True,'proposal_prepost_equal':True,'stop_unchanged':True,'denied_network_attempts':sum(r['attempts'] for r in net),'network_process_receipts':len(net),'qualification':'Owned focused frontend tests only. Actual API calls are vi.fn/Response mocks. No server/SQL/browser/backend/full/live.'},indent=2)+'\n')
print(json.dumps({'status':'PASS','commands':len(records),'network_process_receipts':len(net),'attempts':0}))
