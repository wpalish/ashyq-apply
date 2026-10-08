"""Verify retained raw full result and source binding; does not execute tests or app."""
import hashlib,json,re,xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime,timezone
own=Path(__file__).resolve().parent
repo=own.parents[1]/"ashyq-apply"
run=Path("/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/local-runner/runs/20261008T043357Z-check-0d98eeb3")
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((run/"summary.json").read_text());source=json.loads((run/"source-manifest.json").read_text())
assert m["status"]=="passed",m["status"]
assert len(m["steps"])==13 and all(s["exit_code"]==0 for s in m["steps"])
assert source["source_head"]=="d076e435cb1a6247f171ffb2411c6ab79a0ba857"
assert source["source_tree_sha256"]=="d64864f76f0cf73cf0fa1b602ecf9ae9b2033b278bf4d877a5f68a9b949e68c0"
pins=json.loads((own/"source-after-999.json").read_text())["file_sha256"]
for p,h in pins.items():
 assert sha(repo/p)==sha(run/"source"/p)==source["files"][p]==h,p
stop=repo.parent/"local-round7/provider-STOP.json"
assert sha(stop)=="65b5ff0e9a71b1ec6cb4e72c366b0700e53ebe7d925ad55db379c8d2365a0b1d"
ids={};native={};added={}
for mode in ["backend-sqlite","backend-postgresql"]:
 cases=list(ET.parse(run/(mode+".xml")).getroot().iter("testcase"))
 assert all(not any(x.tag in ["failure","error","skipped"] for x in c) for c in cases)
 keys=[(c.get("classname"),c.get("name")) for c in cases]
 assert len(keys)==len(set(keys));ids[mode]=set(keys)
 native[mode]=sum(any(c.get("classname","")==prefix or c.get("classname","").startswith(prefix+".") for prefix in ["tests.test_hybrid_retrieval","tests.test_search_layer_budget_fixes"]) for c in cases)
 added[mode]=sum(c.get("name","").startswith(("test_native_entry_root_control_stops_before_second_get[","test_native_live_search_caller_preserves_get_control[")) for c in cases)
 assert native[mode]==99 and added[mode]==18,(native,added)
assert ids["backend-sqlite"]==ids["backend-postgresql"]
old=Path("/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/local-runner/runs/20261008T032648Z-check-16f4d81b/backend-sqlite.xml")
oldids={(c.get("classname"),c.get("name")) for c in ET.parse(old).getroot().iter("testcase")}
assert oldids<=ids["backend-sqlite"] and len(ids["backend-sqlite"]-oldids)==18
log=(run/"backend-sqlite.log").read_text();coverage=float(re.search(r"Total coverage: ([0-9.]+)%",log).group(1));assert coverage>=92
receipt={"time":datetime.now(timezone.utc).isoformat(),"status":"FRESH_FULL_13_OF_13_PASS_EXACT_SELECTED_SOURCE","run_id":run.name,"head":source["source_head"],"snapshot_sha256":source["source_tree_sha256"],"source_manifest_file_sha256":sha(run/"source-manifest.json"),"source_prefix_paths":len(pins),"SQLite_unique":len(ids["backend-sqlite"]),"PG_unique":len(ids["backend-postgresql"]),"same_backend_identities":True,"native_two_files_each_DB":native,"added_cases_each_DB":added,"old_backend_cases_preserved":len(oldids),"SQLite_coverage_percent":coverage,"full_elapsed_seconds":(datetime.fromisoformat(m["finished_at"])-datetime.fromisoformat(m["started_at"])).total_seconds(),"steps":m["steps"],"STOP_sha256":sha(stop),"quality":"UNSCORED; no fresh live, production or accepted quality gain; container/hosted CI not performed"}
(own/"final-full-verification.json").write_text(json.dumps(receipt,indent=2)+"\n")
print(json.dumps({k:v for k,v in receipt.items() if k!="steps"},indent=2))
