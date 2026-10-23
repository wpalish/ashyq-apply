from pathlib import Path
from datetime import datetime, timezone
import hashlib,shutil,subprocess
root=Path('/Users/wpalish/Documents/Codex/2026-10-07/x20');repo=root/'work/ashyq-apply';r=root/'work/search-loop-round6';proposal=r/'reviews/expert_a/revision3'
assert not subprocess.check_output(['git','status','--porcelain'],cwd=repo).strip()
base=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip();assert base.startswith('797d263c')
expected={'proposed_page_classifier.py':'7c74866f7fe562077be36bb33379434d7e378985ccfe75f170fa94fb38746c9c','proposed_web_scholarships.py':'b7330166872b63052c58acf8d4a1c3b8748f2239090684bf8f5f236d6043fea9','programme-identity-funding-links.patch':'d388913faaec50c5e98d03798645f16a608fddca7da16ce2fe9cbd40022a77ce'}
for p,h in expected.items():assert hashlib.sha256((proposal/p).read_bytes()).hexdigest()==h
subprocess.run(['git','switch','-c','task/search-programme-purpose'],cwd=repo,check=True)
now=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%MUTC')
p=repo/'docs/process/HANDOFF.md';t=p.read_text();marker='## 5. NEXT STEP — exact and executable\n'
writeahead=f'''**[search-loop] Round6 exact write-ahead BEFORE CODE {now}:** task/search-programme-purpose explicitly from predecessor{base}, unmerged predecessor exception allowed by existing §5. Parent reviewed A revision3 patchd388913f/classifier7c74866f/callerb7330166 (report e31303e2;49external/79semantic executions, no caller loss). Apply those source bytes: PROGRAMME_IDENTITY_BEFORE_FUNDING=False; only a legacy funding index with own identity and bounded real academic proof may promote to programme, marked via SUBSIDIARY_FUNDING_INDEX_SIGNAL in existing signals. Scholarship is_index follows that marker only for programme types with unchanged index/award/URL guards; never programme award facts. Preserve off full outputs, FAQ/UNKNOWN/doc/catalog/funding/support fallback and documented conservative misses. Add local immutable old-output JSON controls and exact retained Wits body/meta; actual requirements/funding caller and index/award/URL/forged-marker regressions. Evaluation BooleanOptional --programme-identity-before-funding/--no-programme-identity-before-funding forwards/applies explicit choice and records ordinary/preSTOP bool; SPH/BL1 unchanged. Parent typing/import formatting differences, if gates require, recorded independently. Run focused/static first then freeze app/eval/tests/fixtures for full offline backend/frontend/demo/onehead, preserve originals and dependent DraftPR66 wip[skip ci]. No live, defaults, gold/heldout, provider, migrations, merge/deployment. Direct reader gain does not prove2027 or fullpipeline gain; SI-1False still blocks early Wits identity. B readguard external and120s hardwall unresolved.\n'''
assert marker in t;t=t.replace(marker,marker+'\n'+writeahead,1);s=t.index('**Current search-loop holder:');e=t.index('\n\n',s);t=t[:s]+f'**Current search-loop holder: gpt-6-astra, {now}, task/search-programme-purpose from{base}.** Applying independently reviewed off-default Round6 classifier+funding bridge; exact write-ahead in §5. SPH/query predecessors pushed DraftPR65/64. Two experts external review only; liveSTOP/hosted refusal sticky; no launch claim.'+t[e:];p.write_text(t)
shutil.copy2(proposal/'proposed_page_classifier.py',repo/'backend/app/adapters/page_classifier.py');shutil.copy2(proposal/'proposed_web_scholarships.py',repo/'backend/app/adapters/scholarship/web_scholarships.py')
shutil.copy2(r/'test_programme_funding_scope.proposed.py',repo/'backend/tests/test_programme_funding_scope.py');shutil.copy2(r/'test_programme_purpose_capture.proposed.py',repo/'backend/tests/test_programme_purpose_capture.py')
f=repo/'backend/tests/fixtures/programme_funding';f.mkdir(parents=True,exist_ok=True)
for src,dest in [('programme_funding_scope.fixture.json','scope-controls.json'),('wits-programme.html','wits-programme.html'),('wits-programme.meta.json','wits-programme.meta.json')]:shutil.copy2(r/src,f/dest)
p=repo/'backend/evaluation/research/live.py';t=p.read_text();start='def main() -> None:\n    from app.adapters.discovery import live_discovery';assert start in t;t=t.replace(start,'def main() -> None:\n    from app.adapters import page_classifier\n    from app.adapters.discovery import live_discovery',1)
needle='    parser.add_argument(\n        "--subject-phrase-match",';assert needle in t;t=t.replace(needle,'''    parser.add_argument(
        "--programme-identity-before-funding",
        action=argparse.BooleanOptionalAction,
        default=page_classifier.PROGRAMME_IDENTITY_BEFORE_FUNDING,
        help="experiment: confirm academic programme identity while preserving subsidiary funding discovery",
    )
'''+needle,1)
needle='        live_discovery.SUBJECT_PHRASE_MATCH = args.subject_phrase_match';assert needle in t;t=t.replace(needle,needle+'\n        page_classifier.PROGRAMME_IDENTITY_BEFORE_FUNDING = args.programme_identity_before_funding',1)
needle='"subject_phrase_match": args.subject_phrase_match,';assert t.count(needle)==2;t=t.replace(needle,needle+'\n                    "programme_identity_before_funding": args.programme_identity_before_funding,')
needle='                        else "--no-subject-phrase-match",';assert t.count(needle)==1;t=t.replace(needle,needle+'\n                        "--programme-identity-before-funding"\n                        if args.programme_identity_before_funding\n                        else "--no-programme-identity-before-funding",',1)
p.write_text(t)
(r/'application-start.json').write_text(__import__('json').dumps(dict(base=base,started_at=now,proposal_sha256=expected,root_source_edits=['evaluation CLI/config/child','repo fixtures/tests conversion']),indent=2)+'\n')
print('Recorded exact write-ahead; source/fixtures applied with flagFalse, no live actions.')
