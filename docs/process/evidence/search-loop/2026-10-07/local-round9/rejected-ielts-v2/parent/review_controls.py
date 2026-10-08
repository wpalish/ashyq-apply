import asyncio
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

OWN = Path(__file__).resolve().parent
PROPOSAL = OWN.parent / "b-ielts-section-proposal-v2"
assert hashlib.sha256((PROPOSAL / "manifest.json").read_bytes()).hexdigest() == "f5ee8caa8976829d532646b3fe0913108c704b738dae81d10e5256ed6b2aec15"
manifest = json.loads((PROPOSAL / "manifest.json").read_text())
assert all(hashlib.sha256((PROPOSAL / k).read_bytes()).hexdigest() == v for k, v in manifest["files"].items())
repo = OWN.parent.parent / "ashyq-apply"
for k, v in json.loads((PROPOSAL / "source-compatibility.receipt.json").read_text()).items():
    assert hashlib.sha256((repo / "backend" / k).read_bytes()).hexdigest() == v["parent_current_sha256"]
sys.path.insert(0, str(PROPOSAL))
import replay_proposal as replay

URL = "https://admissions.example.edu/admission-requirements"
IELTS = {"ielts_min_overall", "ielts_min_subscore", "ielts_accepted_types"}
CASES = [
    ("minimum_inline", "<p>IELTS Academic minimum 6.5 is required.</p>", {"ielts_min_overall": 6.5}),
    ("score_of_inline", "<p>IELTS Academic score of 6.5 is required.</p>", {"ielts_min_overall": 6.5}),
    ("postfix_overall", "<p>IELTS Academic 6.5 overall is required.</p>", {"ielts_min_overall": 6.5}),
    ("spelled_out_with_floor", "<p>International English Language Testing System (Academic) 6.5, with no part below 6.0.</p>", {"ielts_min_overall": 6.5, "ielts_min_subscore": 6.0}),
    ("heading_list", "<h2>IELTS Academic</h2><ul><li>Minimum overall 6.5.</li><li>No part below 6.0.</li></ul>", {"ielts_min_overall": 6.5, "ielts_min_subscore": 6.0}),
    ("section_heading_list", "<section><h2>IELTS Academic</h2><ul><li>Minimum overall 6.5.</li><li>No part below 6.0.</li></ul></section>", {"ielts_min_overall": 6.5, "ielts_min_subscore": 6.0}),
    ("div_direct_statement", "<div>IELTS Academic minimum overall 6.5 is required.</div>", {"ielts_min_overall": 6.5}),
    ("each_component_only", "<p>IELTS Academic minimum 6.0 in each component.</p>", {"ielts_min_subscore": 6.0, "ielts_min_overall": None}),
    ("processing_fee_is_not_overall", "<h2>IELTS Academic</h2><p>Overall processing fee is USD 6.50.</p>", {"ielts_min_overall": None, "ielts_min_subscore": None}),
    ("overall_gpa_is_not_band", "<h2>IELTS Academic</h2><p>Overall minimum GPA is 6.5 on a ten-point scale.</p>", {"ielts_min_overall": None}),
    ("will_not_be_accepted", "<h2>IELTS Academic</h2><p>IELTS Academic will not be accepted. Minimum overall 6.5.</p>", {"all_ielts_absent": True}),
    ("not_currently_accepted", "<h2>IELTS Academic</h2><p>IELTS Academic is not currently accepted. Minimum overall 6.5.</p>", {"all_ielts_absent": True}),
    ("no_longer_accepted_control", "<h2>IELTS Academic</h2><p>IELTS Academic is no longer accepted. Minimum overall 6.5.</p>", {"all_ielts_absent": True}),
    ("explicit_overall_positive", "<h2>IELTS Academic</h2><p>Minimum overall score of 6.5. Writing score of 6.0.</p>", {"ielts_min_overall": 6.5, "ielts_min_subscore": {"writing": 6.0}}),
    ("other_exam_boundary", "<h2>IELTS Academic</h2><p>Minimum overall 6.5.</p><h2>TOEFL</h2><p>Overall 100. Writing 20.</p>", {"ielts_min_overall": 6.5, "ielts_min_subscore": None}),
]


async def main():
    results = []
    for name, inner, expected in CASES:
        body = "<html><head><title>Bachelor admission requirements</title></head><body><main><h1>Bachelor admission requirements</h1>" + inner + "</main></body></html>"
        old = await replay.read(URL, body, domain="example.edu", on=False, old=True)
        new = await replay.read(URL, body, domain="example.edu", on=True)
        assert all(o["page_type"] != "unknown" for o in new["page_outcomes"]), name
        assert len(new["fetcher_calls"]) == 1
        claims = {c["claim_type"]: c["normalized_value"] for c in new["claims"] if c["claim_type"] in IELTS}
        old_claims = {c["claim_type"]: c["normalized_value"] for c in old["claims"] if c["claim_type"] in IELTS}
        issues = []
        for key, value in expected.items():
            if key == "all_ielts_absent":
                if claims:
                    issues.append("declined exam yielded " + repr(claims))
            elif claims.get(key) != value:
                issues.append(f"{key}: expected {value!r}, got {claims.get(key)!r}")
        row = {"case": name, "expected": expected, "body": body, "passed": not issues, "issues": issues, "old_ielts": old_claims, "new_ielts": claims, "old_output": old, "new_output": new}
        results.append(row)
        print(json.dumps({k: row[k] for k in ["case", "passed", "issues", "old_ielts", "new_ielts"]}))
    receipt = {"at_utc": datetime.now(UTC).isoformat(), "proposal_manifest_sha256": "f5ee8caa8976829d532646b3fe0913108c704b738dae81d10e5256ed6b2aec15", "controls": len(results), "passed": sum(r["passed"] for r in results), "failed": sum(not r["passed"] for r in results), "classifier_overrides": 0, "HTTP_DNS_provider_model_calls": 0, "repo_source_writes": 0, "results": results}
    (OWN / "original-controls.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({k: v for k, v in receipt.items() if k != "results"}))


asyncio.run(main())
