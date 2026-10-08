from pathlib import Path
O=Path(__file__).resolve().parent;B=O/'proposed/backend';p=B/'evaluation/research/local_pilot.py';s=p.read_text().replace('from .expert.compact import expand_submission','from .expert.compact import expand_submission, _load_json')
s=s.replace('        capture, observed, budget, raw = (read(p) for p in (captures[0], folder / f"{case_id}.json", folder / f"{case_id}.budget.json", folder / f"{case_id}.raw.json"))','''        physical = (captures[0], folder / f"{case_id}.json", folder / f"{case_id}.budget.json", folder / f"{case_id}.raw.json")
        snapshots = [(path, path.read_bytes()) for path in physical]
        physical_pins = {str(path.relative_to(out)): {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)} for path, data in snapshots}
        capture, observed, budget, raw = (_load_json(data.decode("utf-8")) for _path, data in snapshots)''')
s=s.replace('            errors.append("Public identity differs from actual native institution")','''            errors.append("Public identity differs from actual native institution")
        if any(sha(path) != hashlib.sha256(data).hexdigest() for path, data in snapshots):
            errors.append("Physical bytes changed during admission")''')
s=s.replace('"physical_files": {str(p.relative_to(out)): {"sha256": sha(p), "bytes": p.stat().st_size} for p in (captures[0], folder / f"{case_id}.json", folder / f"{case_id}.budget.json", folder / f"{case_id}.raw.json")}', '"physical_files": physical_pins')
idx=s.index('\ndef execute(')
s=s[:idx]+'''
def verify_admitted_outputs(root, algorithms, experts):
    for record in algorithms:
        folder = root / "private/algorithm" / record["case_id"]
        if read(folder / "admission.json") != record:
            raise ValueError("Admitted algorithm receipt changed")
        for relative, pin in record["physical_files"].items():
            path = folder / relative
            if sha(path) != pin["sha256"] or path.stat().st_size != pin["bytes"]:
                raise ValueError("Admitted algorithm original changed before seal")
    for record in experts:
        folder = root / "private/experts" / record["expert"] / record["case_id"]
        if read(folder / "receipt.json") != record:
            raise ValueError("Admitted expert receipt changed")
        for action in (record["trace"] or {}).get("actions", []):
            if sha(folder / "raw" / action["raw_log_path"]) != action["raw_log_sha256"]:
                raise ValueError("Accepted expert raw changed before seal")
        for event in folder.glob("journal-*.accepted.json"):
            checkpoint = read(event)
            original = folder / event.name.replace("journal-", "selector-").replace(".accepted", ".original")
            if sha(original) != checkpoint["selector_original_sha256"]:
                raise ValueError("Accepted selector original changed before seal")

''' +s[idx:]
s=s.replace('                        experts.append(asyncio.run(collect_expert(gate, public, case, expert, isolate=isolate, select=select, run_tool=run_tool)))','                        experts.append(asyncio.run(collect_expert(gate, public, case, expert, isolate=isolate, select=select, run_tool=run_tool)))\n            verify_admitted_outputs(root, algorithms, experts)\n            gate.check()')
p.write_text(s)
p=B/'evaluation/research/expert/selector.py';s=p.read_text().replace('    except BaseException:\n','    except BaseException as exc:\n',1).replace('        process.wait()\n        raise','''        try:
            stdout, stderr = process.communicate()
            if isinstance(exc, subprocess.TimeoutExpired):
                exc.output, exc.stderr = stdout, stderr
        finally:
            process.wait()
        raise''',1)
s=s.replace('raise ValueError("Selector timeout must fit its explicit clock policy")','raise ValueError("Selector timeout must be in (0,55] seconds" if timeout_policy == "legacy_active" else "Selector timeout must fit its explicit clock policy")')
p.write_text(s)
p=B/'evaluation/research/expert/models.py';s=p.read_text().replace('    policy = record.get("tool_policy") or {}\n    if policy.get(', '    policy = record.get("tool_policy") or {}\n    if not isinstance(policy, dict):\n        raise ValueError("Controller tool policy must be structured")\n    if policy.get(',1)
s=s.replace('        for action in parsed.actions:\n            path =', '        previous_wall = 0\n        for action in parsed.actions:\n            path =',1)
s=s.replace('                _controller_budget(parsed, action, record, packet.get("comparison_mode"))', '''                _controller_budget(parsed, action, record, packet.get("comparison_mode"))
                if parsed.timing_policy == "expert_wall_only":
                    if record["wall_elapsed_ms_before"] < previous_wall:
                        raise ValueError("Protective wall counters decrease between actions")
                    previous_wall = record["wall_elapsed_ms_cumulative"]''',1)
p.write_text(s)
p=B/'tests/test_local_pilot.py';s=p.read_text().replace("        def communicate(self,**_kwargs):raise subprocess.TimeoutExpired('synthetic',1)","        def communicate(self,**kwargs):\n            if kwargs:raise subprocess.TimeoutExpired('synthetic',1)\n            return 'drained stdout','drained stderr'")
s=s.replace("    with pytest.raises(subprocess.TimeoutExpired):s.run_owned_process(['synthetic'],cwd=Path('/synthetic'),timeout=1)\n", "    with pytest.raises(subprocess.TimeoutExpired) as stopped:s.run_owned_process(['synthetic'],cwd=Path('/synthetic'),timeout=1)\n    assert stopped.value.stdout=='drained stdout' and stopped.value.stderr=='drained stderr'\n")
p.write_text(s)
for p in B.rglob('*.py'):
 q=O/'runtime/backend'/p.relative_to(B);q.write_bytes(p.read_bytes())
