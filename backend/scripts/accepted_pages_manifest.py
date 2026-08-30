#!/usr/bin/env python
"""List every programme page the live canary accepted, from its own output.

Three documents said 12, 14 and 20 accepted pages, and the list printed under
the words "All 20" did not have twenty entries in it. Prose cannot be counted,
so the count comes from a manifest and the prose quotes the manifest.

    python scripts/accepted_pages_manifest.py CANARY_DIR [--out FILE]

Records, per page: the institution, the URL, the programme name and level the
classifier assigned, the run it came from, and a reviewer field that starts
unreviewed. No applicant data is involved: these are public university pages.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_OUT = ROOT / "artifacts" / "accepted-pages.json"


def collect(canary_dir: Path) -> dict[str, Any]:
    runs: list[dict[str, Any]] = []
    for report_path in sorted(canary_dir.glob("run*/canary-*.json")):
        report = json.loads(report_path.read_text())
        rows = report if isinstance(report, list) else report.get("institutions", [])
        pages = []
        for row in rows:
            for program in row.get("programs") or []:
                url = program if isinstance(program, str) else program.get("url", "")
                confirmed = {
                    entry[0]: entry[1:]
                    for entry in ((row.get("discovery_trace") or {}).get("confirmed_programs") or [])
                }
                subject, page_type = (confirmed.get(url) or ("", ""))[:2] or ("", "")
                pages.append(
                    {
                        "institution": row["institution"],
                        "country": row.get("country", ""),
                        "url": url,
                        "classified_subject": subject,
                        "classified_page_type": page_type,
                        # Filled by a person; never inferred from the classifier
                        # it is meant to be checking.
                        "reviewer_verdict": "unreviewed",
                        "reviewer_reason": "",
                    }
                )
        runs.append(
            {
                "run_dir": report_path.parent.name,
                "report": report_path.name,
                "accepted_count": len(pages),
                "pages": pages,
            }
        )

    head_file = canary_dir / "HEAD.txt"
    unique = sorted({p["url"] for run in runs for p in run["pages"]})
    manifest: dict[str, Any] = {
        "measured_at_commit": head_file.read_text().strip() if head_file.exists() else None,
        "runs": runs,
        "accepted_per_run": [r["accepted_count"] for r in runs],
        "unique_accepted_urls": len(unique),
        "urls": unique,
    }
    manifest["digest"] = hashlib.sha256(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("canary_dir", type=Path)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    manifest = collect(args.canary_dir)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"wrote {args.out}")
    print(f"  accepted per run: {manifest['accepted_per_run']}")
    print(f"  unique URLs: {manifest['unique_accepted_urls']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
