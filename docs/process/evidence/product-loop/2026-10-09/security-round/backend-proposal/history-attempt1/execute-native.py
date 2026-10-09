from pathlib import Path
import os, sys, json, subprocess, time, hashlib
P=Path(__file__).resolve().parent
MODE=sys.argv[1]
BACKEND=P/f"runtime-{MODE}"/"backend"
PYTHON=Path("/Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply/backend/.venv/bin/python")
if MODE=="on":
    targets=["tests/test_social_moderation.py","tests/test_security.py"]
else:
    targets=["tests/test_social_moderation.py::TestModeratorAccountProvisioning::test_registering_the_configured_email_does_not_grant_moderation","tests/test_social_moderation.py::TestModeratorAccountProvisioning::test_claimed_email_cannot_remove_another_tenants_reported_content","tests/test_security.py::TestPrivateApiStorage"]
CMD=[str(PYTHON),"-m","pytest","-q",*targets,"--junitxml="+str(P/f"{MODE}.junit.xml")]
ENV={"PATH":"/usr/bin:/bin","PYTHONPATH":str(BACKEND)+os.pathsep+str(P/f"runtime-{MODE}"/"guard"),"PYTEST_DISABLE_PLUGIN_AUTOLOAD":"1","AUDIT_NETWORK_LOG":str(P/f"{MODE}.network.json"),"UNIMATCH_DATABASE_URL":"sqlite:///"+str(P/f"runtime-{MODE}"/"bootstrap.db"),"UNIMATCH_CACHE_DIR":str(P/f"runtime-{MODE}"/"cache"),"UNIMATCH_EXPORT_DIR":str(P/f"runtime-{MODE}"/"exports"),"UNIMATCH_DEMO_MODE":"true","UNIMATCH_ENABLE_BROWSER_TIER":"false","UNIMATCH_ENVIRONMENT":"development"}
record={"argv":CMD,"cwd":str(BACKEND),"environment":ENV,"executable_sha256":hashlib.sha256(PYTHON.resolve().read_bytes()).hexdigest(),"mode":MODE,"primary_env_file_read":False}
(P/f"{MODE}.execution.json").write_text(json.dumps(record,indent=2)+"\n")
began=time.monotonic()
with (P/f"{MODE}.stdout.txt").open("w") as out, (P/f"{MODE}.stderr.txt").open("w") as err:
    result=subprocess.run(CMD,cwd=BACKEND,env=ENV,stdout=out,stderr=err)
record.update(exit_code=result.returncode,elapsed_seconds=round(time.monotonic()-began,3))
(P/f"{MODE}.result.json").write_text(json.dumps(record,indent=2)+"\n")
print(json.dumps({"mode":MODE,"exit_code":result.returncode,"elapsed_seconds":record["elapsed_seconds"]}))
