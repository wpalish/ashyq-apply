from pathlib import Path
import ast
import datetime as dt
import hashlib
import json
import plistlib
import shutil

BASE = Path('/Users/wpalish/Documents/Codex/2026-10-07/x20')
REPO = BASE / 'work/ashyq-apply'
OWN = Path(__file__).resolve().parent
FULL = Path('/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/local-runner/runs/20261008T053629Z-check-6693acd5')
STOP = BASE / 'work/local-round7/provider-STOP.json'

def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()

def read(p):
    return json.loads(p.read_text())

def save(n, value):
    p = OWN / n
    assert not p.exists(), n
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

plan = read(OWN / 'PLAN.json')
assert sha(STOP) == plan['STOP']['sha256'] == '65b5ff0e9a71b1ec6cb4e72c366b0700e53ebe7d925ad55db379c8d2365a0b1d'
paths = list(plan['source_pins']) + [
 'backend/evaluation/research/expert/packet.py', 'backend/evaluation/research/expert/catalogue.py',
 'backend/evaluation/research/expert/citations.py', 'backend/evaluation/research/expert/compact.py',
 'backend/evaluation/research/expert/representation.py',
 'backend/evaluation/research/live.py', 'backend/app/adapters/search/exa_mcp.py',
 'backend/app/adapters/search/__init__.py', 'backend/app/catalogue/importer.py',
 'backend/tests/test_expert_controller_guard.py', 'backend/tests/test_expert_blind_cli.py',
 'backend/tests/test_expert_selector.py', 'docs/process/EXPERT500_PHASE1_PROTOCOL_V2_2026-10-04.md',
 'docs/process/EXPERT500_PHASE1_PROTOCOL_V3_2026-10-04.md',
 'backend/evaluation/research/expert/data/protocol.2026-10-04/v4/unimatch-expert500-journal-pilot-v4.py.txt',
 'backend/evaluation/research/expert/data/protocol.2026-10-04/v4/unimatch-expert500-pilot-v1-frozen.py.txt',
]
paths = sorted(set(paths))
pins = {n: {'sha256':sha(REPO/n), 'bytes':(REPO/n).stat().st_size} for n in paths}
assert all(pins[n] == rec for n, rec in plan['source_pins'].items())
full_manifest = read(FULL/'source-manifest.json')
source_binding = {n: full_manifest['files'].get(n) == p['sha256'] for n, p in pins.items() if n.startswith(('backend/app/', 'backend/evaluation/', 'backend/tests/'))}
assert all(source_binding.values()), source_binding
save('source-pins.json', {'repo':str(REPO),'files':pins,'selected_files':len(pins),'tested_source_head':full_manifest['source_head'],'tested_full_tree_sha256':full_manifest['source_tree_sha256'],'full_source_manifest_sha256':sha(FULL/'source-manifest.json'),'eligible_static_module_prefix_bindings':source_binding,'full_or_test_execution_by_this_audit':False})

def assignment(path, variable):
    tree = ast.parse(path.read_text())
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(t, ast.Name) and t.id == variable for t in targets):
                return ast.literal_eval(node.value)
    raise ValueError(variable)

cohort = assignment(REPO/'backend/evaluation/research/live.py', 'COHORT')
pilot = assignment(REPO/'backend/evaluation/research/expert/catalogue.py', 'PILOT_IDENTITIES')
assert list(cohort) == [row[0] for row in pilot]
save('canonical-original10.public-metadata.json', {'source_only_no_corpus_read':True,'original10':[{'case_id':slug,'university':name,'country':country,'official_domain_hint':cohort[slug]} for slug,name,country in pilot], 'identity_contract':'Original pilot IDs are these ten exact slugs; prepare-catalogue accepts independently imported stable32hex catalogue IDs and requires same-ID baseline. Do not silently substitute seed IDs/aliases or mix both packet namespaces. Names/domains are public identifiers, not current source facts.','public_profile':assignment(REPO/'backend/evaluation/research/expert/catalogue.py','PUBLIC_PROFILE')})
cli = Path('/Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex')
sandbox = Path('/usr/bin/sandbox-exec')
npm = Path('/Users/wpalish/.npm-global/lib/node_modules/@openai/codex/package.json')
info = cli.parent.parent/'Info.plist'
runtime = {'static_only':True,'PATH_resolution':{'codex':shutil.which('codex'),'sandbox-exec':shutil.which('sandbox-exec')},'bundled_cli':{'path':str(cli),'exists':cli.is_file(),'bytes':cli.stat().st_size,'sha256':sha(cli),'Info_plist':str(info),'Info_plist_sha256':sha(info),'CFBundleVersion':plistlib.loads(info.read_bytes()).get('CFBundleVersion'),'actual_CLI_version':'UNKNOWN_NOT_EXECUTED'},'sandbox_executable':{'path':str(sandbox),'exists':sandbox.is_file(),'sha256':sha(sandbox)},'npm_CLI_package':{'path':str(npm),'sha256':sha(npm),'version':read(npm)['version']},'real_flag_help_model_login_access_sentinels_neutral_probe': 'NOT_RUN: no CLI invoked, no model/provider/DNS/HTTP/socket activity'}
save('runtime-metadata.json', runtime)
findings = [
 {'id':'E1','severity':'ADMISSION_BLOCKER','status':'CONFIRMED_STATIC','finding':'Ordinary collaboration experts share the repository/filesystem and possess tools/history; they are not the OS-isolated tool-free selectors required by expert500. Neither fork_turns=none nor per-university folders establishes deny access or measured selector streams.','source':['backend/evaluation/research/expert/README.md:68-76','docs/process/EXPERT500_PHASE0_2026-10-04.md:63-78','backend/evaluation/research/expert/blind_cli.py:1-11,23-58,137-179']},
 {'id':'E2','severity':'ADMISSION_BLOCKER','status':'CONFIRMED_STATIC','finding':'expert.controller strict route records/stops only HTTP429, has no shared stop-file CLI, permits Fetcher after that search-only stop, and directly uses provider.search. It does not provide current owner first refusal global cutoff for statusNone typed RATE_LIMITED, other auth/quota/provider failures, or model refusals; retryflags remain native defaults. This is separate from current app process throttle and stronger strict live capture.','source':['backend/evaluation/research/expert/controller.py:280-282,444-448,530-531,642-647,708-738,915-929','backend/app/adapters/search/exa_mcp.py:32-42,243-255','backend/evaluation/research/live.py:149-201,762-774'],'legacy_invariant':'test_expert_controller_guard.py:88-120 explicitly continues a TRANSPORT failure and charges6attempts; a future opt-in first-refusal pilot contract must preserve/qualify legacy behavior, not silently rewrite it.'},
 {'id':'E3','severity':'ADMISSION_BLOCKER','status':'CONFIRMED_STATIC_CONTRACT_MISMATCH','finding':'Owner allowance for new independent expert:60reads/6queries, thinking excluded,900s protective wall. Algorithm same_policy stays120s/60/6. Existing controller STRICT_MAX_MS120000 and frozen journalV4 selector-inclusive120000clock do not express the new independent expert clock; frozen900second occurrence bounds GitHub poll, not local selector episode. Do not raise STRICT_MAX_MS to900000 or present independent exploration as baseline intervention.','source':['backend/evaluation/research/expert/controller.py:4-18,53-56,384-401','backend/evaluation/research/expert/selector.py:45-74','backend/evaluation/research/expert/data/protocol.2026-10-04/v4/unimatch-expert500-journal-pilot-v4.py.txt:48-51,280-288,375-386,784-801','backend/evaluation/research/expert/data/protocol.2026-10-04/v4/unimatch-expert500-pilot-v1-frozen.py.txt:75-88'],'owner_instruction':'Parent trusted steering clarified independent thinking-excluded60/6 +900protective, not an equal120second intervention.'},
 {'id':'E4','severity':'ADMISSION_BLOCKER','status':'CONFIRMED_STATIC_ROUTE_MISSING_CURRENT_PROOF','finding':'blind_cli/selector/journal/controller are reusable enforcement primitives, not a current admitted batch. Package __main__ offers prepare/prepare-catalogue/split/validate/diagnose only; controller CLI executes a plan, not a selector loop. Frozen parent .py.txt imports /tmp legacy and dispatches gh benchmark workflows. A new pinned local external orchestrator/control route with current STOP and clock contract is required; unchanged prepared local checks do not by themselves provide it.','source':['backend/evaluation/research/expert/__main__.py:27-61','backend/evaluation/research/expert/controller.py:915-929','backend/evaluation/research/expert/data/protocol.2026-10-04/v4/unimatch-expert500-journal-pilot-v4.py.txt:41-44,818-821','backend/evaluation/research/expert/data/protocol.2026-10-04/v4/unimatch-expert500-pilot-v1-frozen.py.txt:49-95']},
 {'id':'E5','severity':'PREFLIGHT_NOT_RUN','status':'CONFIRMED_METADATA_AND_UNKNOWN_RUNTIME','finding':'Installed PATH CLI metadata0.147.0 differs from frozen parent bundled exactpath. V2 documented0.147 model unsupported and bundled0.159.2. Current bundled binary exists and is hash-pinned, but current CLI version/support of ignore config/rules, featuredisable, schema/model and authenticated completed streams unknown; neither file existence nor current native subagent model names proves that route.','source':['backend/evaluation/research/expert/blind_cli.py:79-135','backend/evaluation/research/expert/data/protocol.2026-10-04/v4/unimatch-expert500-journal-pilot-v4.py.txt:46-47,256','docs/process/EXPERT500_PHASE1_PROTOCOL_V2_2026-10-04.md:23-35'],'required':'Fresh exact-executable harmless OS sentinel allow/deny proof + two completed real tool-free neutral bound schema/closing probes after explicit owner approval; no university I/O.'},
 {'id':'E6','severity':'PENDING_OWNER_APPROVAL','status':'CONFIRMED_CURRENT_STOP','finding':'Global provider STOP65b5 remains sticky; source full technical acceptance does not authorize its reset or a fresh pilot. Existing already-unscored closures cannot become fresh/admitted receipts by source tagging, counter reset or old preflight reuse.','source':['PLAN.json:STOP','docs/process/EXPERT500_PHASE1_PROTOCOL_V4_2026-10-04.md:59-74'],'required':'Owner explicit fresh-cycle admission, immutable old closure, source/route preflight, separate declared expert clock/comparison contract. No execution in current task.'},
]
save('findings.json', {'status':'NOT_ADMITTED_STATIC_PREPARATION_ONLY','findings':findings,'new_source_or_test_proposal':None,'source_or_model_runtime_PASS_inferred':False})
save('read-receipt.json', {'time':dt.datetime.now(dt.timezone.utc).isoformat(),'status':'STATIC_AUDIT_COMPLETED_FRESH_EXPERT_ROUTE_NOT_ADMITTED','source_plan_sha256':sha(OWN/'PLAN.json'),'source_pins_sha256':sha(OWN/'source-pins.json'),'current_HEAD_metadata':'09559f36ce27ad946e581738f01618b368e01c90','tested_source_head':full_manifest['source_head'],'STOP_before_after_sha256':sha(STOP),'source_pre_post_equal':all(sha(REPO/n)==r['sha256'] and (REPO/n).stat().st_size==r['bytes'] for n,r in pins.items()),'module_bindings_to_saved_tested_snapshot':len(source_binding),'module_bindings_equal':all(source_binding.values()),'canonical_original10_count':len(cohort),'runtime_probes':'NOT_RUN','prior_answer_or_labels_gold_scorer_content_opened':False,'prior_refusal_artifacts_opened':False,'protocol_documents_read':'Public historical aggregate metadata may appear in protocol docs; no prior answers, gold bodies, semantic labels or scorer source read.','executed':'stdlib AST/literal extraction, filesystem metadata/hashing, own report writes only; no imported app/evaluation or model CLI','no_tests_full_seed_SQL_live_provider_model_DNS_HTTP_Git_source_STOP_actions':True,'memory':'MEMORY.md lines27-34 used as historical refusal caution; current contracts checked source, not old state assumed current.'})
assert all(sha(REPO/n)==r['sha256'] for n,r in pins.items()) and sha(STOP)==plan['STOP']['sha256']
print(json.dumps({'status':'STATIC_AUDIT_COMPLETED_FRESH_EXPERT_ROUTE_NOT_ADMITTED','source_pins':len(pins),'tested_module_bindings':len(source_binding),'original10':len(cohort),'findings':len(findings),'source_prepost_equal':True,'STOP_sha256':sha(STOP),'runtime_NOT_RUN':True},indent=2))
