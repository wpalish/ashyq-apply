"""Finite local checks of published snapshots, sources and the 500 x 2 gap ledger."""
import argparse, datetime, hashlib, json, re
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument('discovery', type=Path)
args = parser.parse_args()
data = json.loads((ROOT / 'frontend/src/data/officialProgrammes.json').read_text())
coverage = json.loads((ROOT / 'frontend/src/data/officialProgrammeCoverage.json').read_text())
directory = {p['id']: p for p in json.loads((ROOT / 'frontend/src/data/universityDirectory.json').read_text())}
domains = {'qs2027-001': ['mit.edu', 'mitadmissions.org'], 'qs2027-004': ['ox.ac.uk'],
           'qs2027-005': ['harvard.edu'], 'qs2027-161': ['york.ac.uk'], 'qs2027-247': ['surrey.ac.uk'], 'qs2027-048': ['tudelft.nl'],
           'qs2027-117': ['st-andrews.ac.uk'], 'qs2027-113': ['southampton.ac.uk'], 'qs2027-274': ['sussex.ac.uk']}
source_count = 0
saved_hashes = set()
for programme in [*data['programmes'], *data['history']]:
    row = {k: v for k, v in programme.items() if k != 'version'}
    assert hashlib.sha256(json.dumps(row, sort_keys=True, ensure_ascii=False).encode()).hexdigest() == programme['version'], programme['id']
    assert programme['universityId'] in directory and programme['level'] in {'bachelor', 'master'}
    assert programme['access'] in {'external_applicants', 'internal_only', 'not_open'}
    datetime.date.fromisoformat(programme['checkedAt'])
    for cost in programme['costs']:
        assert cost['amount'] > 0 and re.fullmatch('[A-Z]{3}', cost['currency'])
        assert cost['period'] in {'term', 'academic_year', 'total_course', 'estimated_course_total'}
        assert cost['population'] and cost['academicYear'] and cost['excludes']
    for deadline in programme['deadlines']:
        if deadline['date'] is not None:
            datetime.date.fromisoformat(deadline['date'])
        if deadline['timezone'] is not None:
            ZoneInfo(deadline['timezone'])
        if deadline['time'] is not None:
            datetime.time.fromisoformat(deadline['time'])
        assert deadline['scope'] and deadline['cycle']
    for fact in [*programme['requirements'], *programme['costs'], *programme['funding'], *programme['deadlines'], *programme['documents']]:
        source = fact['source']; source_count += 1
        parsed = urlsplit(source['url'])
        assert parsed.scheme == 'https' and not parsed.username and not parsed.password
        assert any(parsed.hostname == d or parsed.hostname.endswith('.' + d) for d in domains[programme['universityId']]), source
        datetime.date.fromisoformat(source['checkedAt'])
        if source.get('contentSha256'):
            sha = source['contentSha256']; body = args.discovery / 'pages' / (sha + '.bin')
            assert hashlib.sha256(body.read_bytes()).hexdigest() == sha
            saved_hashes.add(sha)
        else:
            assert source['method'] == 'editorial_official_page_read'
assert len({p['id'] for p in data['programmes']}) == len(data['programmes'])
assert len(coverage['rows']) == 1000
assert len({(r['universityId'], r['level']) for r in coverage['rows']}) == 1000
for row in coverage['rows']:
    published = [p for p in data['programmes'] if p['universityId'] == row['universityId'] and p['level'] == row['level']]
    assert row['published'] == len(published) and row['complete'] is False
print(json.dumps({'status': 'PASS', 'publishedProgrammeRecords': len(data['programmes']),
                  'publishedInstitutions': len({p['universityId'] for p in data['programmes']}),
                  'archivedSnapshots': len(data['history']), 'factSourceReferencesIncludingHistory': source_count,
                  'exactSavedSourceBodies': len(saved_hashes), 'degreeSlots': 1000,
                  'full500ProgrammeCompletion': False, 'runtimeOrAdmissionsAcceptance': False}))
