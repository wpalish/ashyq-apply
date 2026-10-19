"""Offline coverage ledger. Discovery is never promoted to admission facts."""
import argparse, csv, json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument('discovery', type=Path)
parser.add_argument('--csv', type=Path)
args = parser.parse_args()
institutions = {r['institution_id']: r for r in map(json.loads, (args.discovery / 'institutions.jsonl').read_text().splitlines())}
directory = json.loads((ROOT / 'frontend/src/data/universityDirectory.json').read_text())
programmes = json.loads((ROOT / 'frontend/src/data/officialProgrammes.json').read_text())['programmes']
rows = []
for university in directory:
    discovery = institutions[university['id']]
    for level in ('bachelor', 'master'):
        published = [p for p in programmes if p['universityId'] == university['id'] and p['level'] == level]
        candidates = [p for p in discovery['programmes'] if p['level'] == level]
        quarantined = university['id'] in {'qs2027-164', 'qs2027-169'}
        rows.append({'universityId': university['id'], 'level': level, 'published': len(published),
                     'externalRoutes': sum(p['access'] == 'external_applicants' for p in published),
                     'state': 'partial_published' if published else 'not_published',
                     'unreviewedCandidates': 0 if quarantined else len(candidates),
                     'quarantinedCandidates': len(candidates) if quarantined else 0,
                     'readIssues': sorted(set(x['outcome'] for x in discovery['issues'])),
                     'complete': False})
summary = {'institutions': len(directory), 'degreeSlots': len(rows), 'programmeRecords': len(programmes),
           'publishedInstitutions': len({p['universityId'] for p in programmes}),
           'publishedDegreeSlots': sum(r['published'] > 0 for r in rows),
           'completeInstitutions': 0, 'completeDegreeSlots': 0,
           'byLevel': dict(Counter(p['level'] for p in programmes))}
output = {'schemaVersion': 'official-programme-coverage-v1', 'builtAt': '2026-10-19', 'summary': summary, 'rows': rows}
(ROOT / 'frontend/src/data/officialProgrammeCoverage.json').write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
if args.csv:
    args.csv.parent.mkdir(parents=True, exist_ok=True)
    with args.csv.open('w') as stream:
        fields = ['universityId', 'level', 'published', 'externalRoutes', 'state', 'unreviewedCandidates', 'quarantinedCandidates', 'readIssues', 'complete']
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows({**r, 'readIssues': '|'.join(r['readIssues'])} for r in rows)
print(json.dumps(summary))
