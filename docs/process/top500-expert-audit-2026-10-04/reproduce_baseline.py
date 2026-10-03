"""Reproduce the catalogue-only control without network or persistent databases."""
import hashlib
import json
import time
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.catalogue.importer import SEED_PATH, identity_key, import_catalogue
from app.catalogue.retrieval import retrieve
from app.db import create_all_for_tests
from app.models import University


def main():
    start = time.perf_counter()
    engine = create_engine("sqlite://")
    create_all_for_tests(engine)
    seed = json.loads(SEED_PATH.read_text())["universities"]
    rows = []
    with Session(engine) as session:
        imported = import_catalogue(session)
        by_key = {u.identity_key: u for u in session.scalars(select(University))}
        for item in seed:
            uni = by_key[identity_key(item["name"], item["country"])]
            found = retrieve(session, query=item["name"])
            position = next((i + 1 for i, u in enumerate(found) if u.id == uni.id), None)
            rows.append({
                "seed_id": item["seed_id"], "university_id": uni.id,
                "exact_name_position": position, "result_count": len(found),
                "curated": bool(uni.registry_entry), "domain_status": uni.domain_status,
                "domain": uni.domain,
                "official_site_has_path": urlsplit(item.get("official_site") or "").path not in ("", "/"),
            })
    engine.dispose()
    report = {
        "source_sha": "144881b", "seed_sha256": hashlib.sha256(SEED_PATH.read_bytes()).hexdigest(),
        "scope": "offline full-catalogue import and name retrieval; no network or admissions verification",
        "import": imported, "seed_rows_audited": len(rows),
        "exact_name_found": sum(r["exact_name_position"] is not None for r in rows),
        "exact_name_first_page": sum(r["exact_name_position"] is not None and r["exact_name_position"] <= 20 for r in rows),
        "seed_curated": sum(r["curated"] for r in rows),
        "seed_domain_status": dict(Counter(r["domain_status"] for r in rows)),
        "seed_site_paths": sum(r["official_site_has_path"] for r in rows),
        "elapsed_seconds": round(time.perf_counter() - start, 3), "rows": rows,
    }
    Path(__file__).with_name("baseline.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "rows"}, indent=2))


if __name__ == "__main__":
    main()
