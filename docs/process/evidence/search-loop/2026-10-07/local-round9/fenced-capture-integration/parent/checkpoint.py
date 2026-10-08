import hashlib
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

own = Path(__file__).resolve().parent
repo = own.parent.parent / "ashyq-apply"
proposal = own.parent.parent / "local-round8/a-genuine-canary/revision2-final"
dest = repo / "docs/process/evidence/search-loop/2026-10-07/local-round9/fenced-capture-integration"
sha = lambda data: hashlib.sha256(data).hexdigest()
suite = ET.parse(own / "pytest-actual-2.xml").getroot().find("testsuite")
assert suite is not None
assert (suite.get("tests"), suite.get("failures"), suite.get("errors"), suite.get("skipped")) == ("199", "0", "0", "0")
assert "Success: no issues found in 383 source files" in (own / "mypy-3.log").read_text()
assert "All checks passed!" in (own / "ruff-check-2.log").read_text()
assert "already formatted" in (own / "ruff-format-2.log").read_text()
assert "UNIVERSITY_READ_BUDGET = False" in (repo / "backend/app/pipeline/read_budget.py").read_text()
dest.mkdir(parents=True, exist_ok=False)
secrets = []
for line in (repo / "backend/.env").read_text().splitlines():
    match = re.match(r'(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)', line)
    if match and re.search("KEY|TOKEN|SECRET|PASSWORD", match[1]):
        value = match[2].strip().strip("\"'")
        if len(value) >= 12 and not value.startswith(("#", "${")):
            secrets.append(value.encode())
files = {}
def copy(source, relative):
    assert source.is_file() and not source.is_symlink(), source
    data = source.read_bytes()
    assert not any(secret in data for secret in secrets), "Configured secret detected"
    target = dest / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    files[relative] = {"sha256": sha(data), "bytes": len(data), "original": str(source)}

manifest = json.loads((proposal / "sealed-evidence-manifest.json").read_text())
assert manifest["file_count"] == 624
for entry in manifest["files"]:
    source = proposal / "sealed-evidence" / entry["relative_path"]
    assert sha(source.read_bytes()) == entry["sha256"], entry["relative_path"]
    copy(source, "external-originals/" + entry["relative_path"])
for name in ["final-seal.json", "sealed-evidence-manifest.json", "receipt.json", "REPORT.ru.md", "parent-control-commands.txt"]:
    copy(proposal / name, "external-seal/" + name)
for name in ["PLAN.json", "apply.py", "apply.receipt.json", "checkpoint.py", "pytest-actual-1.log", "pytest-actual-1.xml", "pytest-actual-2.log", "pytest-actual-2.xml", "ruff-check-1.log", "ruff-format-1.log", "mypy-1.log", "mypy-2.log", "ruff-check-2.log", "ruff-format-2.log", "mypy-3.log"]:
    copy(own / name, "parent/" + name)
paths = ["backend/scripts/canary_discovery.py", "backend/evaluation/research/live.py", "backend/tests/test_canary_fenced_job.py", "backend/tests/test_readguard_capture_protocol.py"]
for path in paths:
    copy(repo / path, "actual-source/" + path)
tracked = subprocess.check_output(["git", "ls-files"], cwd=repo, text=True).splitlines()
tracked += [path for path in paths if path not in tracked]
code = {path: sha((repo / path).read_bytes()) for path in sorted(set(tracked))
        if path.startswith(("backend/app/", "backend/tests/", "backend/evaluation/", "backend/scripts/", "frontend/src/", "frontend/tests/", "frontend/e2e/"))
        and (repo / path).is_file()}
(own / "code-freeze.json").write_text(json.dumps(code, indent=2) + "\n")
copy(own / "code-freeze.json", "parent/code-freeze.json")
receipt = {"at_utc": datetime.now(UTC).isoformat(), "status": "ACTUAL_MODULE_FOCUSED_PASS_FULL_LOCAL_PENDING",
           "parent_controls": {"passed": 199, "failed": 0, "skipped": 0, "seconds": float(suite.get("time"))},
           "first_actual_attempt": {"passed": 185, "failed": 14, "cause": "unconditional False keyword forwarding broke legacy test call shape; assertions unchanged"},
           "mypy": {"passed": True, "source_files": 383, "original_errors": 4, "initial_direct_script_command_collision": True},
           "ruff": "PASS", "format": "PASS", "native_default": False, "configured_secret_matches": 0,
           "actual_files": {path: sha((repo / path).read_bytes()) for path in paths},
           "code_freeze_files": len(code), "network_calls": 0, "files": files,
           "limits": ["No new full/PG suite result yet", "No quality score or live comparison", "Outer60 may stop before native61", "One isolated child/case; no concurrent interpreter patch guarantee", "Final meter cannot time own last byte", "No default/gold/STOP/production/source-app change", "Runtime DB/cache/env/private Git excluded"]}
(dest / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
receipt_sha = sha((dest / "receipt.json").read_bytes())
handoff = repo / "docs/process/HANDOFF.md"
text = handoff.read_text()
insertions = {
"## 2. Current task\n": "\n**[search-fenced-capture] actual-module integration PASS, full LOCAL pending.** Four harness/test files applied after sealed receipt3fd85544. Parent legacy forwarding/type-narrowing repairs keep previous assertions intact. Actual199PASS/0skip19.27s; Ruff/format PASS, mypy383 PASS. App/Fetcher/default/gold unchanged. Freeze source/test files while exact-source LOCAL full runs.\n",
"## 3. Done in this task (commit hash per item — a claim without a hash is not done)\n": f"\n**[search-fenced-capture] source checkpoint awaiting WIP commit:** genuine isolated enqueue/claim/Worker capture applied; parent199PASS/static PASS; full pending. Selected external624 + parent originals preserved at local-round9/fenced-capture-integration, receipt{receipt_sha}. Initial185PASS/14legacyRED and4mypy errors retained; repaired without weakening old assertions. Native defaultFalse; no fresh fact-quality metric.\n",
"## 5. NEXT STEP — exact and executable\n": "\n**Current next step:** commit/push WIP exact four harness/test files + focused evidence and handoff, then existing local runner `./local.sh --repo /Users/wpalish/Documents/Codex/2026-10-07/x20/work/ashyq-apply check --suite full`. Keep source/tests frozen; no live before full protocol acceptance. After real full success archive original gates and open dependent Draft against task/search-production-read-budget/#67. Then independently accepted IELTS v3/new language-route quality work, fresh same-protocol pairs; all closed original cohorts stay immutable.\n",
"## 6. Gate status at last run\n": "\n**2026-10-08 fenced focused gates:** actual-module199PASS/0skip19.27s; Ruff app/tests+two harness PASS, format355PASS; configured mypy app/tests/evaluation383PASS. Full LOCAL NOT YET RUN for changed harness/tests; predecessor budget full13/13 remains valid only for source3b3a2fb8. No live/provider/model calls.\n",
"## 8. Contract changes since the brief (append-only; the other agent reads this before coding)\n": "\n**Fenced local capture:** explicit BooleanOptionalAction native budget/job protocol flags; native requires genuine research Job, one isolated SQLite identity and no documents/recheck/check-seeds. New raw job_protocol records real status/claim/heartbeat/native ledger separately from outer counts; unavailable counters remain null. Partial new fenced canary exits2; legacy call/report preserved. Native moduleFalse. Typed original control survives artifact failure; successful Job can still have partial late capture under original strict6/60/120 clock.\n",
"## 9. Traps and lessons (things that cost a session; keep them)\n": "\n**2026-10-08 harness port:** external50 controls did not cover fourteen native legacy mock signatures. Preserve legacy call shape when no new Job option is active; do not loosen old assertions. Direct mypy script path alongside namespace imports causes duplicate module names; configured app/tests/evaluation checks transitive scripts correctly. Separate optional reporting/timeout values from previously narrow inferred variables. All original reds retained.\n"
}
for anchor, addition in insertions.items():
    assert text.count(anchor) == 1, anchor
    text = text.replace(anchor, anchor + addition, 1)
handoff.write_text(text)
now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
summary = f"\n\n### {now}: genuine Job capture integrated, full pending\n\nParent actual-module199PASS/0skip19.27s; Ruff/format/mypy383 PASS. Four harness/test files applied with legacy call-shape/type repairs; initial14reds retained. Archive receipt{receipt_sha}, {len(files)} originals/{sum(f['bytes'] for f in files.values())}bytes. UNIVERSITY_READ_BUDGET=False; no source app/Fetcher/STOP/gold/live changes. IELTSv3 external95 controls pending independent review; v1/v2 rejected immutable; two experts active on v3 review and narrow language routing. Full local must pass before new live quality comparison; no launch/quality-rate claim.\n"
for name in ["CLAUDE_SEARCH_RELAY_2026-10-07.md", "SEARCH_LOOP_LEDGER_2026-10-07.md"]:
    path = repo / "docs/process" / name
    path.write_text(path.read_text() + summary)
outputs = repo.parent.parent / "outputs"
continue_text = f"""# Claude: точка продолжения — {now}

Цель ACTIVE: проверяемый поиск для запуска Unimatch / ASHYQ Apply. Репозиторий `{repo}`; ветка **task/search-fenced-capture**, base41836a86/Draft67. Текущие source изменения прошли focused gates, full LOCAL сейчас pending. Канонический baton — docs/process/HANDOFF.md §1–§6. Другой dirty checkout b41b49e/11paths не трогать.

Перенесены только два harness модуля и два normal-import test файла. Реальные enqueue→claim token1→Worker.execute/_dispatch→ResearchRunner, isolated SQLite. Fresh reporting после Worker cleanup, heartbeat joined; реальные Job status/native ledger отличены от outer attempts. Artifact/time failure сохраняет исходную typed cause. Strict6queries/60reads/120seconds unchanged; slow raw/output даёт partial capture даже при succeeded Job. Final metering не измеряет собственный последний байт. **UNIVERSITY_READ_BUDGET=False**.

Parent actual-module **199PASS/0skip19.27s**, Ruff/format/mypy383 PASS. Первые14 legacy-call failures и4 type errors сохранены; исправлены без ослабления assertions. External50controls не заменяют full. Evidence: docs/process/evidence/search-loop/2026-10-07/local-round9/fenced-capture-integration/receipt.json ({receipt_sha}). Старые rejected41/48 proposals неизменны.

Следующий шаг: WIP source commit/push, один exact-source full LOCAL (~15min) существующим local-runner, source/tests frozen. При успехе архив original13gates + зависимый Draft к task/search-production-read-budget/#67. Прежний budget source3b3a2fb8 full13/13,4211SQLite+теже4211PG,coverage95.15%,frontend232,demo79PASS/1skip,auth6 иnative134 уже preserved/pushed. Эти прежние цифры не являются новой full проверкой harness.

Два эксперта: A независимо проверяет IELTSv3 во внешней local-round9/a-ielts-v3-independent; B узкий language-purpose/per-IELTS route во внешних folder без live. IELTSv1/v2 rejected; rootv2 3/15PASS,12RED preserved/pushed. V3 manifest6c1b368f, helper17ad707e, author95PASS; пока не applied/parent accepted. Широкое UNKNOWN→ADMISSIONS и простой early-stopWS1 запрещённые rejected решения не переносить. OFF/table/PDF/nonIELTS semantics сохранять.

Fresh original10 baseline:413 Fetcher/58search/0provider refusals,6/10programmeURL,125predictionrecords, **UNSCORED**. Старые20DEV observations не доказали стабильный core gain. Нужны fresh same genuine protocol pairs, принятые precision≥95%,core≥80%,wrong scope≤3%,page coverage,heldoutgap≤15pp, независимый40/62pilot и опубликованный logged-in путь. Ни запуск, ни default promotion не заявлены.

HistoricalSTOP work/development-STOP.json SHA dd669c6d73d89ba2586676b46b120e4c8af2ea95e4e15cd7ae75c554f9557cad сохранять. Новый work/local-round7/provider-STOP.json проверить перед live; первый новый model/provider/auth/quota refusal глобально останавливает live без retry/substitution/purchase/effortchange. Закрытые V9/V13/V14 не возобновлять. No hosted CI minutes/merge/deploy/purchase/gold signature authorization.
"""
(outputs / "CLAUDE_CONTINUE.md").write_text(continue_text)
for name in ["CLAUDE_SEARCH_RELAY_2026-10-07.md", "SEARCH_LOOP_LEDGER_2026-10-07.md"]:
    (outputs / name).write_bytes((repo / "docs/process" / name).read_bytes())
progress = outputs / "PROGRESS_2026-10-08.md"
progress.write_text(f"# Новый checkpoint — {now}\n\nGenuine Job capture перенесён:199 actual-module PASS/0skip, Ruff/format/mypy383 PASS. Full LOCAL новой версии pending; старые full13/13/4211×2 относятся к предыдущему source3b3a2fb8. IELTSv3 author95PASS, independent review pending; no live/new quality score. Ветка task/search-fenced-capture. [Claude continue]({outputs / 'CLAUDE_CONTINUE.md'}).\n\n---\n\n" + progress.read_text())
print(json.dumps({"files": len(files), "bytes": sum(f["bytes"] for f in files.values()), "receipt_sha256": receipt_sha, "code_freeze_files": len(code), "tests": 199}))
