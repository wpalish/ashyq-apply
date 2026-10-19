"""Offline finite packaging; no requests, DB writes or test execution."""
import csv,hashlib,html,json,shutil,subprocess
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
OUT=Path(__file__).resolve().parent
REPO=Path('/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/unimatch-web/2026-10-18/source')
RAW=Path('/Users/wpalish/Documents/Codex/2026-10-07/x20/work/official-programme-catalogue-2026-10-19')
CANON=REPO/'docs/design/official-programmes-2026-10-19'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def dump(name,value): (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
for source in ['STARTED.json','TERMINAL.json','reads.jsonl','institutions.jsonl','candidates.json']:
 shutil.copy2(RAW/source,OUT/('discovery-'+source))
for folder,tag in [('official-programme-identity-corrections-2026-10-19','identity-corrections'),('official-programme-identity-images-2026-10-19','identity-images')]:
 p=RAW.parent/folder/'RECEIPTS.json';shutil.copy2(p,OUT/(tag+'-RECEIPTS.json'))
for source in Path('/tmp').glob('unimatch-official-*'):
 if source.is_file() and source.suffix in {'.log','.json'}:shutil.copy2(source,OUT/source.name)
for name in ['officialProgrammes.json','officialProgrammeCoverage.json','universityProgrammeIdentityImages.receipt.json']:
 shutil.copy2(REPO/'frontend/src/data'/name,OUT/name)
reads=[json.loads(line) for line in (RAW/'reads.jsonl').read_text().splitlines()]
pages=[]
for p in sorted((RAW/'pages').iterdir()):
 if not p.is_file():continue
 digest=sha(p);assert p.stem==digest
 pages.append({'relativePath':'pages/'+p.name,'bytes':p.stat().st_size,'sha256':digest})
dump('RAW_SOURCE_INDEX.json',{'root':str(RAW),'scope':'Retained local public HTML; not copied into this report or Git. Filename/content hashes verified. This is storage integrity, not editorial acceptance.','pages':pages})
data=json.loads((OUT/'officialProgrammes.json').read_text());coverage=json.loads((OUT/'officialProgrammeCoverage.json').read_text())
summary=coverage['summary'];summary['externalProgrammeRoutes']=sum(p['access']=='external_applicants' for p in data['programmes'])
summary['restrictedOrClosedRecords']=sum(p['access']!='external_applicants' for p in data['programmes'])
dump('DISCOVERY_SUMMARY.json',{'identityAttempts':500,'reads':len(reads),'outcomes':dict(Counter(r['outcome'] for r in reads)),'statusCodes':dict(Counter(str(r['status_code']) for r in reads)),'unreviewedCandidates':127,'no429Observed':all(r['status_code']!=429 for r in reads),'qualifiedByDiscovery':0,'rawSourceFiles':len(pages),'rawBytes':sum(p['bytes'] for p in pages),'coverage':summary,'identityCorrections':'Lancaster UK and Texas A&M College Station corrected after original discovery; earlier wrong-campus candidates remain quarantined.'})
with (OUT/'PROGRAMME_FIELDS.csv').open('w') as f:
 w=csv.writer(f);w.writerow(['id','university','level','cycle','access','requirements','costs','funding','deadlines','documents','unknowns','source','version'])
 for p in data['programmes']:w.writerow([p['id'],p.get('universityName'),p['level'],p['cycle'],p['access'],len(p['requirements']),len(p['costs']),len(p['funding']),len(p['deadlines']),len(p['documents']),' | '.join(p['unknowns']),p['url'],p['version']])
dump('NATIVE_OBSERVATIONS.json',{'environment':'retained owned synthetic preview 18140 / API 18141 only','profileB':'8f86257ecca249c7a1339cd78d1be5b9','restoredProfileA':'eb6861322a0245c1b2ec493c8f59b311','writes':[{'application':'6ec828566d334dd1a7271728a7ec52b8','programme':'oxford-advanced-computer-science-msc','snapshot':'c38e1c70834d16de41e5d412327d28c716efb8dcb3b410df46b262796929c342','task':'31d95dd388944815a86a99a677e86f7e','verified':['explicit review and server ACK','linked personal document task; parent checklist immediately updated','personal note edited, ACK and reload','archived source version remains addressable','source calendar 2027-01-06 12:00 Europe/London and exact application link']},{'application':'a0d811037d684573ad10dc7397386ec1','programme':'st-andrews-data-science-online-msc','intake':'January2027','verified':['specific intake selection required','explicit review and server ACK','plan reload retains January2027','only January2027 deadline appears in Plan; other intakes excluded']}],'otherChecks':['published-university filter shows 9 of 500','MIT internal-only master has no external plan action','source dates and personal dates remain separate','wrong-case St Andrews application link is fenced after restoring A','desktop1280 and mobile390 observations','A original state retained; inherited known conflicts preserved, not replayed or removed'],'notPerformed':['actual university application or file upload','live provider/model/evaluation pilot','production acceptance','full backend/mypy/auth suites'],'clickLimit':'One offscreen source-return click did not navigate through CUA; keyboard Enter opened the exact archived route. No reproducible code defect was established or claimed fixed.'})
roots=['frontend/src','frontend/public/universities','scripts/catalogue','scripts/programmes']
paths=set()
for root in roots:
 paths.update(p for p in (REPO/root).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
for relative in ['backend/app/catalogue/unimatch_top500_seed.json','backend/tests/test_university_catalogue.py','frontend/package.json','frontend/package-lock.json','frontend/vite.config.ts','frontend/tsconfig.json']:
 p=REPO/relative
 if p.is_file():paths.add(p)
manifest=[{'path':str(p.relative_to(REPO)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(paths)]
dump('SOURCE_MANIFEST.json',{'baseline':'32d0585bd9c0efa453161640aaefc2102d79a59d','lastIntermediateCommit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),'scope':'Entire frontend/src and local university image directory; catalogue/programme scripts; listed seed/test/build files. Not a whole physical tree or whole backend audit.','paths':manifest})
report='''# Official programmes and connected plan — 19 October 2026

**PARTIAL DATA DELIVERY / FULL 500-INSTITUTION REQUEST OPEN.** The UI path is implemented and locally exercised. The directory still contains 500 institution identities, while the programme library currently publishes **14 reviewed records at 9 institutions: 7 bachelor and 7 master records**. Twelve records allow an external personal-plan route; one is internal-only and one closed for the cited intake. Many fields remain explicitly unknown. None of the 500 institutions is claimed comprehensively covered.

The catalogue card now contains programme-specific requirements, fee units and population/year, funding information, dated official links, document actions and remaining questions. Confirming a programme creates a durable, case-owned personal application through the existing G3 journal. It does not create a synthetic research result or an applicant eligibility assessment. Document tasks are personal tasks linked to that application with source URLs, not server-verified source-reference bindings. Official source deadlines appear separately from personal dates. Multi-intake courses require choosing an intake; the Plan/calendar project only that intake’s dates.

Saved source versions remain archived and addressable. Editing personal notes preserves the source snapshot; changing university, programme, route or intake outside the known snapshot retires its projection. Pending unknown commands block replacement writes. A known CAS rejection remains in history but permits a new explicitly reviewed command against the refreshed revision. Case switches fence late feedback and redirects.

## Coverage and sources

A finite, robot-respecting, single-attempt discovery pass visited 500 imported institution identities, making 1526 reads. It produced 127 UNREVIEWED candidates, including admissions tests, faculty pages, news, integrated undergraduate MEng routes and wrong-campus matches. They were not bulk-published as programmes. No HTTP429 occurred in this pass. Robots exclusions, access errors, blocked URLs and missing current programme facts remain gaps, not proof that courses or scholarships are absent. Discovery alone qualified zero programmes.

[COVERAGE.csv](COVERAGE.csv) records all 1000 institution/degree slots, with no fabricated completion. [PROGRAMME_FIELDS.csv](PROGRAMME_FIELDS.csv) shows fields and gaps for the 14 published records. [DISCOVERY_SUMMARY.json](DISCOVERY_SUMMARY.json) reports access outcomes. [RAW_SOURCE_INDEX.json](RAW_SOURCE_INDEX.json) pins locally retained public HTML; raw pages are not copied into Git. Four initial records use actual web-page reads without a saved raw-body receipt. Ten further records are based on nine exact saved official bodies. The method is visible in each source record; do not conflate those evidence types.

Lancaster University’s UK identity and Texas A&M College Station had wrong-campus source sites in the imported directory. The seed, offline overrides and local identity images were corrected using official primary sites. Earlier discovery candidates from Lancaster Ghana/TAMIU remain quarantined. Existing500 local selected images still verify; the chosen breakdown is now490 site icons,2 emblems,8 institutional logos, not500 full brand kits.

## Observed user path and checks

In the owned synthetic profile B, Oxford MSc was explicitly saved, appeared in Plan, created a linked personal document task, retained a personal note after reload and exposed the exact source deadline with time and timezone. The source-return keyboard action opened the archived version. St Andrews January2027 was then saved and retained after reload, with only8January2027 projected. MIT’s internal route has no external-create action. The original profile A was restored; B’s exact application link was fenced there. Screenshots and [NATIVE_OBSERVATIONS.json](NATIVE_OBSERVATIONS.json) state the observed scope and limitations. No actual submission or upload occurred.

Final full frontend:1049tests/111files PASS; production build with TypeScript PASS; lint0errors/9inherited warnings. The >500kB chunk warning remains. Focused catalogue backend53PASS with1inherited warning; full backend/mypy/auth not rerun. The two identity corrections were imported only into the owned synthetic DB:500seed/501total; all36non-catalogue tables had equal hashes during that import, before separate native test writes. No schema or backend application logic changed. The all-record contract check verifies each external published plan fits the existing server validator and note bounds.

## Remaining work

The request to populate both degree levels across all500 universities is **not complete**. Most institutions have no published programme records; several published records lack confirmed costs, scholarships or exact dates. Continue editorial qualification of official programme/admissions/fee/funding pages, with intake and applicant-category boundaries, and add only supported facts. Some sites require another authorized official information route because of robots/access barriers; do not bypass them or infer missing data. The public data task did not resume historical provider/model/security/heldout queues, real expert pilots or production deployment. Platform/release acceptance remains open.

![Connected Plan](official-programmes-plan-desktop.png)
![Source deadline and exact application](catalogue-official-deadline-calendar.png)
'''
(OUT/'REPORT.md').write_text(report)
# Simple local HTML: preserve source links and readable parallel coverage without libraries.
lines=[]
for line in report.splitlines():
 if line.startswith('# '):lines.append('<h1>'+html.escape(line[2:])+'</h1>')
 elif line.startswith('## '):lines.append('<h2>'+html.escape(line[3:])+'</h2>')
 elif line.startswith('!['):
  label,url=line[2:].split('](',1);lines.append('<img alt="'+html.escape(label)+'" src="'+html.escape(url[:-1])+'">')
 elif line:lines.append('<p>'+html.escape(line)+'</p>')
(OUT/'REPORT.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>Unimatch official programmes — partial data delivery</title><style>body{font:16px/1.65 system-ui;margin:48px auto;max-width:1050px;color:#16284a;padding:0 24px}h1,h2{color:#173cf2}img{max-width:100%;border:1px solid #ddd;border-radius:14px}a{color:#173cf2}p{max-width:95ch}</style><body>'+''.join(lines)+'<h2>Published programme source pages</h2><ul>'+''.join('<li><a href="'+html.escape(p['url'])+'">'+html.escape(p.get('universityName','')+' — '+p['title'])+'</a> · '+html.escape(p['cycle']+' · '+p['access'])+'</li>' for p in data['programmes'])+'</ul><p><a href="COVERAGE.csv">1000-slot coverage CSV</a> · <a href="PROGRAMME_FIELDS.csv">Programme fields</a> · <a href="VERIFICATION.json">Verification</a></p></body></html>')
verification={'generatedAt':datetime.now(timezone.utc).isoformat(),'status':'LOCAL_CONNECTED_PATH_PASS__DATA_PARTIAL__500_REQUEST_OPEN','coverage':summary,'frontend':{'tests':1049,'files':111,'status':'PASS','log':'unimatch-official-tests-final3.log'},'build':'PASS_WITH_CHUNK_WARNING','lint':{'errors':0,'inheritedWarnings':9},'backendCatalogue':{'passed':53,'warnings':1,'fullSuite':'NOT_RERUN'},'native':'See NATIVE_OBSERVATIONS.json; synthetic environment only','data':json.loads((OUT/'unimatch-official-data-verification.json').read_text()),'sourcePins':len(manifest),'sourcePinsMatch':all(sha(REPO/r['path'])==r['sha256'] for r in manifest),'noProductionAcceptance':True,'historicalStopsUnchanged':True}
dump('VERIFICATION.json',verification)
files=[p for p in sorted(OUT.iterdir()) if p.is_file() and p.name!='ARTIFACT_INDEX.json']
dump('ARTIFACT_INDEX.json',{'scope':'Finite local evidence package; excludes raw HTML/cache/DB/auth material','files':[{'path':p.name,'bytes':p.stat().st_size,'sha256':sha(p)} for p in files]})
CANON.mkdir(parents=True,exist_ok=True)
for p in OUT.iterdir():
 if p.is_file():shutil.copy2(p,CANON/p.name)
print(json.dumps({'proofMembers':len(files),'sourcePins':len(manifest),'rawSourceFiles':len(pages),'sourcePinsMatch':verification['sourcePinsMatch'],'canonical':str(CANON)}))
