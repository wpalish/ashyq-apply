"""Apply reviewed DRAFT documents only after exact final local/UI qualification."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json

ROOT=Path('/Users/wpalish/Documents/Codex/2026-10-07/x20')
TASK=ROOT/'work/security-round1';REPO=ROOT/'work/ashyq-apply'
B=TASK/'b-security-release-doc-review';PLAN=TASK/'b-final-doc-qualification-plan'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
accept=json.loads((TASK/'root-final-acceptance.json').read_text())
assert accept['status']=='QUALIFIED_LOCAL_SECURITY_INCREMENT_ACCEPT'
head=(TASK/'final-head.txt').read_text().strip()
assert accept['source_head']==head
pins=json.loads((TASK/'final-source-pins.json').read_text())
assert len(pins)==20 and sha(TASK/'final-source-pins.json')==accept['source20_sha256']
assert all(sha(REPO/n)==h for n,h in pins.items())
assert sha(ROOT/'work/local-round7/provider-STOP.json')=='65b5ff0e9a71b1ec6cb4e72c366b0700e53ebe7d925ad55db379c8d2365a0b1d'
assert accept['full_steps']==13 and accept['full_status']=='passed'
assert accept['immediate_ACK_JSON_clear_verified'] is True
assert accept['same_owner_reload_absence_verified'] is True
cleanup=TASK/'preview-auth-export-final/cleanup-receipt.json'
assert sha(cleanup)==accept['cleanup_sha256']
c=json.loads(cleanup.read_text())
assert c['errors']==[] and c['source_and_config_postcheck_passed'] and c['ports_free_before_unlock']
for directory,name,expected in [(B,'ready-manifest.json','85335e02496a3fecc54d77052a0fa04acc2d56cbdf45b67bceb52ffa313e98f1'),
 (PLAN,'READY.json','e493d743780e7d12698edda0d9cd8565a7a7ce002296c512c80dc04b93637fdd')]:
 ready=directory/name;assert sha(ready)==expected
 for rel,record in json.loads(ready.read_text())['files'].items():
  p=directory/rel;assert p.resolve().is_relative_to(directory.resolve()) and not p.is_symlink()
  assert sha(p)==record['sha256'] and p.stat().st_size==record['bytes'],rel
receipt=json.loads((B/'receipt.json').read_text())
names={'SECURITY.md','docs/legal/RELEASE_READINESS.md','docs/legal/PRIVACY_POLICY_RU.md'}
assert set(receipt['baseline_documents'])==set(receipt['proposed_documents'])==names
texts={}
for rel in names:
 assert sha(REPO/rel)==receipt['baseline_documents'][rel]['sha256'],rel
 p=B/'proposed'/rel;assert sha(p)==receipt['proposed_documents'][rel]['sha256']
 texts[rel]=p.read_text()
history=texts['docs/legal/RELEASE_READINESS.md'].split('<details>',1)[1]
items=json.loads((PLAN/'exact-replacements.json').read_text())['items']
assert len(items)==11
for item in items:
 rel=item['document'];old=item['exact_old'];assert texts[rel].count(old)==1,rel
 texts[rel]=texts[rel].replace(old,item['candidate_new'].replace('<FINAL_SOURCE_HEAD>',head),1)
assert texts['docs/legal/RELEASE_READINESS.md'].split('<details>',1)[1]==history
closure=(TASK/'final-local-closure.md').read_text()
assert head in closure and accept['initial_source_tree_sha256'] in closure
marker='## История проверки и незакрытый итог'
assert texts['docs/legal/RELEASE_READINESS.md'].count(marker)==1
texts['docs/legal/RELEASE_READINESS.md']=texts['docs/legal/RELEASE_READINESS.md'].replace(marker,
 '## Квалифицированная локальная проверка\n\n'+closure+'\n\n'+marker,1)
assert '2026-10-09.draft1' in texts['docs/legal/PRIVACY_POLICY_RU.md']
assert all('<FINAL_SOURCE_HEAD>' not in text for text in texts.values())
out=TASK/'final-docs-application-receipt.json';assert not out.exists()
for rel,text in texts.items():(REPO/rel).write_text(text)
assert all(sha(REPO/n)==h for n,h in pins.items())
out.write_text(json.dumps({'created_at':datetime.now(timezone.utc).isoformat(),
 'status':'QUALIFIED_DRAFT_DOCS_SOURCE_AND_LOCAL_PROOF_RECONCILED_NOT_LEGAL_READY',
 'source_head':head,'root_acceptance_sha256':sha(TASK/'root-final-acceptance.json'),
 'approved3_READY_sha256':sha(B/'ready-manifest.json'),'qualification_plan_READY_sha256':sha(PLAN/'READY.json'),
 'output_documents':{n:{'sha256':sha(REPO/n),'bytes':(REPO/n).stat().st_size} for n in sorted(names)},
 'historical_details_unchanged':True,'operator_version_consent_facts_changed':False,
 'scope':'Exactly3 reviewed DRAFT docs plus conditional11 replacements/actual local closure; no executable code or policy/operator approval.'},indent=2)+'\n')
print(json.dumps({'applied_documents':sorted(names),'receipt_sha256':sha(out)}))
