from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,shutil,subprocess,sys
ROOT=Path("/Users/wpalish/Documents/Codex/2026-10-07/x20")
REPO=ROOT/"work/ashyq-apply"; TASK=ROOT/"work/security-round2"; P=TASK/"log-capture-repair"
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
peer_sha=sys.argv[1]
peer=TASK/"a-log-capture-repair-review-final/READY.json"
assert sha(peer)==peer_sha
assert sha(P/"READY.json")=="179eff402d6257ba357031de3bfc174a2eb69381fe000029b13caefc4883027b"
assert subprocess.check_output(["git","-C",str(REPO),"branch","--show-current"],text=True).strip()=="task/product-privacy-diagnostics"
assert not subprocess.check_output(["git","-C",str(REPO),"status","--porcelain"],text=True).strip()
prehead=subprocess.check_output(["git","-C",str(REPO),"rev-parse","HEAD"],text=True).strip()
assert prehead==(TASK/"test-repair-pre-apply-head.txt").read_text().strip()
assert sha(TASK/"applied-source-pins.json")=="bc960dfdf50a140698ff399c7929cc503f6fee24ef5f050c34d3ef9f72a71dd6"
old=json.loads((TASK/"applied-source-pins.json").read_text()); assert len(old)==34
assert all(sha(REPO/n)==h for n,h in old.items())
plan=json.loads((P/"proposal-plan.json").read_text()); assert len(plan["proposed"])==2
for n,h in plan["proposed"].items():
 assert n in old and n.startswith("backend/tests/test_rejected_diagnostics")
 assert sha(P/"proposed"/n)==h and old[n]==plan["original"][n]
for n in ["repaired-source-pins.json","test-repair-application-receipt.json"]:assert not (TASK/n).exists()
assert sha(ROOT/"work/local-round7/provider-STOP.json")=="65b5ff0e9a71b1ec6cb4e72c366b0700e53ebe7d925ad55db379c8d2365a0b1d"
new=dict(old);new.update(plan["proposed"])
assert new==json.loads((TASK/"prospective-repaired-source-pins.json").read_text())
for n,h in plan["proposed"].items():
 shutil.copyfile(P/"proposed"/n,REPO/n);assert sha(REPO/n)==h
assert all(sha(REPO/n)==h for n,h in new.items())
shutil.copyfile(TASK/"prospective-repaired-source-pins.json",TASK/"repaired-source-pins.json")
r={"utc":datetime.now(timezone.utc).isoformat(),"status":"EXACT_TEST_REPAIR_APPLIED_FULL_PENDING","pre_apply_head":prehead,"original_failed_source_head":"08450f71e6bbeadd9a2212fbd6c9f96f5c428755","original_source34_sha256":sha(TASK/"applied-source-pins.json"),"source34_pins_sha256":sha(TASK/"repaired-source-pins.json"),"test_changes":plan["proposed"],"unchanged_selected_paths":32,"root_repair_READY_sha256":sha(P/"READY.json"),"independent_peer_READY_sha256":peer_sha,"qualification":"Only stronger capture state/positive controls in2tests; application11 and predecessor20+oldhop unchanged. Originalfailed receipts remain immutable. Full pending."}
(TASK/"test-repair-application-receipt.json").write_text(json.dumps(r,indent=2)+"\n")
print(json.dumps(r,indent=2))
