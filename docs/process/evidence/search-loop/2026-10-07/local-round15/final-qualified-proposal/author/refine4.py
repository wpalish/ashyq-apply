from pathlib import Path
O=Path(__file__).resolve().parent;B=O/'proposed/backend';p=B/'evaluation/research/local_pilot.py';s=p.read_text()
s=s.replace('    from .live import COHORT as domains','    from .live import COHORT as domains\n    from urllib.parse import urlsplit\n    from app.adapters.discovery.live_discovery import registrable_domain').replace('controller._domain(entry["homepage"]) == domain','registrable_domain(urlsplit(entry["homepage"]).hostname or "") == domain')
s=s.replace('if relative.startswith(("backend/app/", "backend/evaluation/", "backend/scripts/", "backend/tests/", "frontend/")) and Path(relative).suffix in {".py", ".ts", ".tsx", ".js", ".css"}:','if True:  # Opaque hashes of every manifest artifact; no semantic corpus parsing.')
s=s.replace('"sealed_roots": [*[str(p) for p in protected], str(Path.home() / ".codex/memories"), str(Path.home() / ".codex/skills")]', '"sealed_roots": [*[str(p) for p in protected], str(Path.home() / "Documents/Codex"), str(Path.home() / ".codex/memories"), str(Path.home() / ".codex/sessions"), str(Path.home() / ".codex/skills")]')
s=s.replace('def collect_algorithm(gate:', 'def _collect_algorithm(gate:')
s=s.replace('    try:\n        completed = process_run(command,', '    gate.check()\n    store(out / "launch.original.json", {"argv": command, "cwd": str(Path(gate.plan["source_snapshot"]) / "backend"), "status": "launcher-entered"})\n    try:\n        completed = process_run(command,',1)
idx=s.index('\ndef expert_packet(')
s=s[:idx]+'''
def collect_algorithm(gate, case, process_run=selector.run_owned_process):
    try:
        return _collect_algorithm(gate, case, process_run)
    except BaseException as exc:
        out = gate.root / "private/algorithm" / case["case_id"]
        out.mkdir(parents=True, exist_ok=True)
        store(out / "admission.json", {"case_id": case["case_id"], "terminal_kind": "partial_protocol_failure", "error_type": type(exc).__name__, "complete_eligible": False, "launcher_entered": (out / "launch.original.json").is_file(), "unknowns_not_absence": True})
        raise


def neutral_admission(gate, *, isolate=NATIVE_ISOLATE, select=selector.select):
    """Exactly two original tool-free neutral probes, one for each expert."""
    from .expert.blind_cli import selector_answer
    root = gate.root / "private/neutral"
    root.mkdir(parents=True)
    receipts = []
    for expert in ("A", "B"):
        gate.check()
        with tempfile.TemporaryDirectory(prefix="ashyq-neutral-") as temporary:
            workspace = Path(temporary)
            allowed = workspace / "allowed.sentinel"
            allowed.write_text("harmless public sentinel")
            sealed = root / f"{expert}.sealed.sentinel"
            sealed.write_text("harmless sealed sentinel")
            isolation = isolate(workspace, [Path(path) for path in gate.plan["sealed_roots"]] + [gate.root])
            if isolation.codex_executable != gate.plan["executables"]["codex"] or isolation.sandbox_executable != gate.plan["executables"]["sandbox"]:
                raise ValueError("Neutral executables differ from pinned runtime")
            gate.reserve("neutral_isolation", "neutral", expert, {"workspace": str(workspace)})
            proof = isolation.prove_access(allowed, sealed)
            proof_path = root / f"{expert}.isolation.original.json"
            store(proof_path, proof)
            nonce = uuid.uuid4().hex
            answer = {"status": "ready", "nonce": nonce}
            schema = {"type": "object", "additionalProperties": False, "properties": {"status": {"type": "string", "enum": ["ready"]}, "nonce": {"type": "string", "enum": [nonce]}}, "required": ["status", "nonce"]}
            schema_path = workspace / "neutral.schema.json"
            schema_path.write_text(json.dumps(schema))
            output = workspace / "answer.json"
            prompt = {"instructions": "Return this exact source-free neutral transport acknowledgment only; no tools.", "acknowledgment": answer}
            gate.reserve("neutral_model", "neutral", expert, {"schema_sha256": sha(schema_path), "model": gate.plan["selector_model"], "timeout_seconds": 900})
            turn = select(isolation, schema_path, output, prompt, timeout_seconds=900, model=gate.plan["selector_model"], timeout_policy="expert_wall_only")
            original = root / f"{expert}.selector.original.json"
            store(original, {"stdout": turn.stdout, "stderr": turn.stderr, "returncode": turn.returncode, "error_kind": turn.error_kind, "answer_file": output.read_text() if output.is_file() else None, "elapsed_ms": turn.elapsed_ms, "schema": schema, "prompt": prompt, "source_tree_sha256": gate.plan["source_tree_sha256"], "executables": gate.plan["executables"], "selector_model": gate.plan["selector_model"]})
            if turn.returncode != 0 or turn.error_kind is not None or turn.answer != answer or selector_answer(turn.stdout, output.read_text() if output.is_file() else None) != answer:
                gate.refuse("neutral_model_or_protocol_failure", "neutral", raw_paths=[original, proof_path], diagnostic={"expert": expert, "error_kind": turn.error_kind, "returncode": turn.returncode})
            receipts.append({"expert": expert, "original_sha256": sha(original), "isolation_sha256": sha(proof_path), "schema_sha256": sha(schema_path)})
    result = {"status": "original_neutral_probes_validated", "runtime_admitted": isolate is NATIVE_ISOLATE and select is selector.select, "runtime_mode": "native" if isolate is NATIVE_ISOLATE and select is selector.select else "offline_injected", "probes": receipts, "source_tree_sha256": gate.plan["source_tree_sha256"], "model": gate.plan["selector_model"]}
    store(root / "admission.json", result)
    return result

''' +s[idx:]
s=s.replace('        algorithms, experts, error = [], [], None','        algorithms, experts, error = [], [], None\n        admission = None')
s=s.replace('        try:\n            for case in cases:', '        try:\n            with patch.dict(os.environ, clean_env(), clear=True):\n                admission = neutral_admission(gate, isolate=isolate, select=select)\n            for case in cases:',1)
s=s.replace('                attempted_algorithms.append(case["case_id"])\n','').replace('                        attempted_experts.append((case["case_id"],expert))\n','')
s=s.replace('        result = {"cycle_id":', '''        attempted_algorithms = [case for case in COHORT if (root / "private/algorithm" / case / "launch.original.json").is_file()]
        attempted_experts = [(case, expert) for case in COHORT for expert in ("A", "B") if (root / "private/experts" / expert / case / "isolation.original.json").is_file() or list((root / "private/experts" / expert / case).glob("selector-*.original.json"))]
        partial_algorithms = [read(path) for path in sorted((root / "private/algorithm").glob("*/admission.json")) if read(path).get("terminal_kind") == "partial_protocol_failure"]
        partial_experts = [read(path) for path in sorted((root / "private/experts").glob("*/*/receipt.json")) if read(path).get("status") == "partial_control_failure"]
        result = {"neutral_admission": admission, "partial_algorithms": partial_algorithms, "partial_experts": partial_experts, "cycle_id":''')
s=s.replace('"all_expert_complete_eligible": len(experts) == 20 and all(row["complete_eligible"] for row in experts)', '"all_expert_complete_eligible": admission is not None and admission["runtime_admitted"] and len(experts) == 20 and all(row["complete_eligible"] for row in experts)')
p.write_text(s)
p=B/'tests/test_local_pilot.py';s=p.read_text().replace("s.run_owned_process(['synthetic'],timeout=1)","s.run_owned_process(['synthetic'],cwd=Path('/synthetic'),timeout=1)")
s=s.replace("    case=prompt['public_packet']['cases'][0];observed=bool(prompt['source_views'])", "    if 'acknowledgment' in prompt:\n        answer=prompt['acknowledgment'];output.write_text(json.dumps(answer));return s.SelectorTurn(answer,1000,streams(answer),'',0,None)\n    case=prompt['public_packet']['cases'][0];observed=bool(prompt['source_views'])")
p.write_text(s)
for p in B.rglob('*.py'):
 q=O/'runtime/backend'/p.relative_to(B);q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(p.read_bytes())
