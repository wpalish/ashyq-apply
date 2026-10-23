from pathlib import Path
O=Path(__file__).resolve().parent;B=O/'proposed/backend';p=B/'evaluation/research/local_pilot.py';s=p.read_text().replace('import shutil\n','import shutil\nimport sys\n')
s=s.replace('    source = Path(plan["source_snapshot"])','''    for name, link in plan.get("executable_bindings", {}).items():
        path = Path(plan["executables"][name])
        if str(path.resolve()) != link["resolved"] or sha(path.resolve()) != link["sha256"]:
            raise ValueError("Dispatched executable link/bytes changed")
    source = Path(plan["source_snapshot"])''',1)
s=s.replace('    for name, path in executables.items():','    executable_bindings = {}\n    for name, path in executables.items():',1).replace('        executables[name] = str(path)','        executables[name] = str(path)\n        executable_bindings[name] = {"resolved": str(resolved), "sha256": sha(resolved)}',1)
s=s.replace('    protected = tuple(p.resolve() for p in sealed_roots)','''    # Existing wheel provenance is pinned without installations or key inspection.
    dependency_records = [path for path in Path(sys.prefix).rglob("*.dist-info/RECORD") if path.is_file() and not path.is_symlink()]
    if not dependency_records:
        raise ValueError("Existing dependency RECORD provenance required")
    pins.extend({"path": str(path), "sha256": sha(path)} for path in dependency_records)
    protected = tuple(p.resolve() for p in sealed_roots)''',1)
s=s.replace('"executables": executables,', '"executables": executables, "executable_bindings": executable_bindings, "dependency_provenance": "opaque wheel RECORD hashes plus exact tested full receipt; not independently rehashed full third-party file closure",',1)
s=s.replace('        snapshots = [(path, path.read_bytes()) for path in physical]','        snapshots = []\n        for path in physical:\n            regular_sha = sha(path)\n            data = path.read_bytes()\n            if hashlib.sha256(data).hexdigest() != regular_sha:\n                raise ValueError("Physical artifact changed during snapshot")\n            snapshots.append((path, data))')
s=s.replace('    store(root / "receipt.json", receipt)\n    return receipt','''    store(root / "receipt-data.original.json", receipt)
    receipt["wall_elapsed_ms"] = wall_elapsed()
    receipt["active_time_basis"] = "one original case wall; setup, isolation, selector waits, source actions, checkpoint validation and receipt-data persistence included; final metering envelope and later collection hash audit are audit only"
    if receipt["wall_elapsed_ms"] > WALL_MS:
        receipt["status"] = "protective_wall_expired"
        receipt["complete_eligible"] = False
    store(root / "receipt.json", receipt)
    return receipt''',1)
s=s.replace('        for event in folder.glob("journal-*.accepted.json"):', '''        from .expert.blind_cli import selector_answer
        journal = AcceptedJournal.initial()
        packet = read(folder / "packet.original.json")
        for event in sorted(folder.glob("journal-*.accepted.json")):''')
s=s.replace('                raise ValueError("Accepted selector original changed before seal")','''                raise ValueError("Accepted selector original changed before seal")
            replay = read(original)
            if replay["returncode"] != 0 or replay["error_kind"] is not None or selector_answer(replay["stdout"], replay["answer_file"]) != checkpoint["decision"] or checkpoint["prior_snapshot"] != journal.snapshot():
                raise ValueError("Accepted original/journal chain does not replay")
            decision = parse_bound_journal_decision(checkpoint["decision"], journal_sha256=journal.sha256, canonical_university=packet["cases"][0]["university"])
            trace = checkpoint["trace"]
            actions = [Action.model_validate(value) for value in (trace or {}).get("actions", [])]
            if checkpoint["processed_through_action_count"] != len(actions):
                raise ValueError("Accepted checkpoint action prefix differs")
            begun = datetime.fromisoformat(trace["started_at"]) if trace else datetime.now(UTC)
            ended = datetime.fromisoformat(trace["ended_at"]) if trace else begun
            candidate, rebuilt_trace, _proof = neutral_checkpoint(journal, decision, actions, packet, folder / "raw", begun, ended)
            if candidate.snapshot() != checkpoint["snapshot"] or rebuilt_trace != trace:
                raise ValueError("Accepted journal/trace failed complete reconstruction")
            journal = candidate
        if journal.sha256 != record["journal_sha256"]:
            raise ValueError("Final receipt differs from replayed complete journal")''')
s=s.replace('        admission = None','        admission = None\n        current_case, current_expert, current_phase = "neutral", None, "neutral_admission"',1)
s=s.replace('            for case in cases:\n                algorithms.append(', '            for case in cases:\n                current_case, current_expert, current_phase = case["case_id"], None, "algorithm"\n                algorithms.append(',1)
s=s.replace('                    for expert in ("A", "B"):\n                        experts.append(', '                    for expert in ("A", "B"):\n                        current_case, current_expert, current_phase = case["case_id"], expert, "expert"\n                        experts.append(',1)
s=s.replace('gate.refuse("protocol_failure", cases[min(len(algorithms),9)]["case_id"],', 'gate.refuse("protocol_failure", current_case,').replace('diagnostic={"type": error})','diagnostic={"type": error, "expert": current_expert, "phase": current_phase})',1)
s=s.replace('        gate.check() if error is None else None\n','')
p.write_text(s)
p=B/'evaluation/research/expert/selector.py';s=p.read_text().replace('raise ValueError("Selector timeout exceeds its declared policy")','raise ValueError("Selector timeout must be in (0,55] seconds" if timeout_policy == "legacy_active" else "Selector timeout exceeds its declared policy")');p.write_text(s)
p=B/'evaluation/research/expert/controller.py';s=p.read_text().replace('            previous_policy = resume.get("tool_policy", {})','''            previous_policy = resume.get("tool_policy", {})
            if plan.get("timing_policy") == "expert_wall_only":
                if resume.get("timing_policy") != "expert_wall_only" or type(resume.get("protective_wall_ms")) is not int or resume["protective_wall_ms"] != 900_000 or not isinstance(previous_policy, dict) or previous_policy.get("timing_policy") != "expert_wall_only" or previous_policy.get("thinking_in_tool_ms") is not False or (previous_policy.get("max_fetcher_calls"), previous_policy.get("max_search_queries"), previous_policy.get("max_elapsed_ms")) != (60, 6, None):
                    raise ValueError("Resume summary wall policy incomplete or contradictory")''',1)
s=s.replace('if not previous_wall <= wb <= wa <= 900_000:', 'if not previous_wall <= wb <= wa <= 900_000 or wa-wb < _integer(record, "elapsed_ms"):')
p.write_text(s)
p=B/'evaluation/research/expert/models.py';s=p.read_text().replace('not 0 <= wb <= wa <= 900_000:', 'not 0 <= wb <= wa <= 900_000 or wa-wb < record.get("elapsed_ms",0):');p.write_text(s)
for p in B.rglob('*.py'):
 q=O/'runtime/backend'/p.relative_to(B);q.write_bytes(p.read_bytes())
