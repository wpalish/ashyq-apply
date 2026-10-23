"""Source/text and sealed synthetic-routing inspection; no native imports/calls."""

import ast
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path('/Users/wpalish/Documents/Codex/2026-10-07/x20')
REPO = ROOT / 'work/ashyq-apply'
OWN = Path(__file__).resolve().parent
RUN = Path('/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/local-runner/runs/20261008T053629Z-check-6693acd5')
B = ROOT / 'work/local-round13/b-stopped-trace-proposal'
STOP = ROOT / 'work/local-round7/provider-STOP.json'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def state():
    mapping = json.loads((ROOT / 'work/local-round13/root-stopped-trace-accounting/source-after-999.json').read_text())['file_sha256']
    frozen = json.loads((RUN / 'source-manifest.json').read_text())
    assert len(mapping) == 999
    assert frozen['source_tree_sha256'] == '75497406d33bb8c4fe3015d44b13e20786d8cf9a74d4e6138c16d3341164d446'
    assert all(sha(REPO / rel) == digest == sha(RUN / 'source' / rel) == frozen['files'][rel] for rel,digest in mapping.items())
    assert sha(STOP) == '65b5ff0e9a71b1ec6cb4e72c366b0700e53ebe7d925ad55db379c8d2365a0b1d'
    return {'source999_primary_frozen_saved_equal': True, 'frozen_tree_sha256': frozen['source_tree_sha256'], 'source_after_map_sha256': sha(ROOT / 'work/local-round13/root-stopped-trace-accounting/source-after-999.json'), 'STOP_sha256': sha(STOP)}


def snippets():
    # Explicit finite source ranges; scoring/recall code is neither retained nor run.
    ranges = {
        'backend/scripts/canary_discovery.py': [(365, 388), (567, 585), (622, 629), (759, 763), (775, 781), (790, 815), (832, 836)],
        'backend/app/catalogue/importer.py': [(46, 55), (146, 174), (179, 199)],
        'backend/app/catalogue/discovery.py': [(100, 114), (150, 178), (297, 300)],
        'backend/app/adapters/discovery/live_discovery.py': [(1156, 1185)],
        'backend/app/pipeline/runner.py': [(185, 201), (748, 753), (834, 843), (1607, 1615)],
        'backend/app/adapters/base.py': [(28, 47)],
        'backend/app/domain/dedupe.py': [(37, 48)],
        'backend/app/models/university.py': [(13, 27)],
        'backend/app/schemas/result.py': [(316, 329)],
        'backend/tests/test_live_discovery.py': [(2122, 2143)],
    }
    result = []
    for rel, portions in ranges.items():
        p = REPO / rel
        source = p.read_text()
        ast.parse(source)  # Parse code only, no import or compile/execution.
        lines = source.splitlines(keepends=True)
        for start,end in portions:
            excerpt = ''.join(lines[start-1:end])
            result.append({'file': rel, 'source_sha256': sha(p), 'start_line': start, 'end_line': end, 'excerpt': excerpt, 'excerpt_sha256': hashlib.sha256(excerpt.encode()).hexdigest()})
    return result


def main():
    before = state()
    manifest = B / 'ready-manifest.json'
    assert sha(manifest) == 'b95a950c8cfc3cee5583dbe17d6a0f66843dbcc8e41db674bff38b620a558872'
    m = json.loads(manifest.read_text())
    source = B / 'whole-output.final.on.json'
    assert sha(source) == m['files']['whole-output.final.on.json']['sha256']
    row = json.loads(source.read_text())['rows']['catalogue-normal-alias-subdomain']
    routing = {
        'origin': str(source), 'raw_sha256': sha(source), 'B_ready_sha256': sha(manifest),
        'row_key': 'catalogue-normal-alias-subdomain',
        'candidate_fields': [{k:c.get(k) for k in ['name', 'country', 'catalogue_id', 'domain', 'search_queries_used']} for snapshot in row['captured'] for c in snapshot['candidates']],
        'trace_fields': [{k:t.get(k) for k in ['institution', 'domain', 'search_queries_attempted']} for snapshot in row['captured'] for t in snapshot['traces']],
        'exceptions': row['exception'],
        'native_proof_scope': 'Synthetic discovery methods/report-input only. No Runner, SQL, canary report or quality scoring executed.'
    }
    assert routing['candidate_fields'][0]['name'] == routing['trace_fields'][0]['institution'] == 'Registry Alias University'
    assert routing['candidate_fields'][0]['catalogue_id'] == 'offline-0'
    source_excerpts = snippets()
    after = state(); assert after == before
    result = {'time': datetime.now(UTC).isoformat(), 'status': 'CONDITIONAL_NAME_ONLY_JOIN_RISK; B19_ACTUAL_CANARY_REACHABILITY_NOT_PROVEN', 'before':before, 'after':after,
              'confirmed_source_facts':[
                  'select_catalogue_entries emits University.name/id/domain; it does not use registry_entry.name.',
                  'Normal Catalogue enrichment emits entry.name as Candidate.name and trace institution; catalogue_id preserves uni.id.',
                  'Runner ProgramResult university follows Candidate.name; persisted university_id is dedupe.university_key, not imported32hex catalogue_id.',
                  'Canary gathers Candidate/Trace/Result by exact registry display name, with no catalogue_id fallback.',
                  'Fresh canary DB imports curated registry before seed records; first curated identity creates University.name from the same entry.name.',
                  'Native identity probe returns uni.name, so new homepage branding alone cannot create this normal alias mismatch.',
                  'Importer reuses canonical identity keys, retains existing University.name and replaces registry_entry; conditional key collisions or prior imported-name history permit display-name differences.',
                  'Curated registry key uniqueness is not checked in its importer loop; seed snapshot uniqueness validation is separate.',
                  'Name joins lack country/id discrimination; result and trace dicts are last-wins while Candidate lookup is first-match. No actual current collision is established.'
              ],
              'saved_B19_qualification': 'The synthetic helper attaches a foreign registry name directly and uses id offline-0. This cannot serve as an actual32hex selected canary identity or establish its fresh-import binding.',
              'unproven': ['Occurrence of duplicate canonical identity keys in current curated registry', 'Actual selected canary name mismatch under current approved inputs', 'Any current report/capture loss, genuine Worker outcome or scored quality direction'],
              'not_executed': ['app imports or tests', '_gather_report', 'recall_metrics', 'scorer/gold', 'SQL/Git/full/live/provider/model'],
              'next_evidence_only_requirement': 'If a separate next task is authorized, first establish an approved identity-only binding or controlled native fresh-import fixture that actually creates a display-name mismatch. This preflight proposes no source repair.'}
    (OWN / 'saved-routing.original.json').write_text(json.dumps(routing,indent=2)+'\n')
    (OWN / 'source-excerpts.original.json').write_text(json.dumps(source_excerpts,indent=2)+'\n')
    (OWN / 'audit.original.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'status':result['status'], 'source999_unchanged':True, 'STOP_unchanged':True, 'native_imports_or_calls':0, 'scoring_or_gold_operations':0}))


if __name__ == '__main__':
    main()
