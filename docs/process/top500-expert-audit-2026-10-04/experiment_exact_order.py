"""Development experiment: reorder existing matches; no production implementation."""
from __future__ import annotations

import hashlib
import json
import socket
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'backend'))
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.catalogue.importer import SEED_PATH, identity_key, import_catalogue
from app.catalogue.retrieval import retrieve
from app.domain.dedupe import normalize
from app.models import Base, University


def deny_network(*args, **kwargs):
    raise AssertionError('This development experiment must remain offline')


def exact_first(found, query):
    normalized = normalize(query)
    if not normalized:
        return found
    return sorted(found, key=lambda u: 0 if normalized in {normalize(u.name), *(normalize(a) for a in u.aliases or [])} else 1)


def main():
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    records = json.loads(SEED_PATH.read_text())['universities']
    outcomes = []
    with Session(engine) as session:
        import_catalogue(session)
        by_key = {u.identity_key: u for u in session.scalars(select(University))}
        for record in records:
            uni = by_key[identity_key(record['name'], record['country'])]
            query = record['name']
            before = retrieve(session, query=query)
            after = exact_first(before, query)
            assert {u.id for u in before} == {u.id for u in after}
            outcomes.append({
                'seed_id': record['seed_id'], 'name': record['name'], 'query': query,
                'before_rank': next(i+1 for i,u in enumerate(before) if u.id == uni.id),
                'after_rank': next(i+1 for i,u in enumerate(after) if u.id == uni.id),
                'before_first': before[0].name, 'after_first': after[0].name,
                'result_count': len(before), 'result_set_preserved': True,
            })
        empty = retrieve(session)
        assert exact_first(empty, '') == empty
    engine.dispose()
    result = {
        'source_sha': '144881b', 'seed_sha256': hashlib.sha256(SEED_PATH.read_bytes()).hexdigest(),
        'status': 'candidate_development_experiment',
        'scope': 'Same500 supplied exact-name queries; post-sort only; no network, no production patch, no held-out proof or admission-fact improvement',
        'queries': len(outcomes),
        'before_top_one': sum(r['before_rank']==1 for r in outcomes),
        'after_top_one': sum(r['after_rank']==1 for r in outcomes),
        'target_rank_regressions': sum(r['after_rank']>r['before_rank'] for r in outcomes),
        'result_sets_preserved': len(outcomes), 'empty_query_order_preserved': True,
        'rows': outcomes,
    }
    Path(__file__).with_suffix('.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))


if __name__ == '__main__':
    with patch.object(socket.socket,'connect',deny_network), patch.object(socket,'create_connection',deny_network):
        main()
