from pathlib import Path
import shutil
O=Path(__file__).resolve().parent;B=O/'proposed/backend';h=O/'history/developing-v2';shutil.copytree(B,h)
p=B/'evaluation/research/pilot_admission.py';s=p.read_text().replace('source_manifest, require_complete_job=False','source_manifest, identities, require_complete_job=True').replace('    PLAN = plan\n','').replace('PLAN[','plan[').replace('        identities = IdentityMap.model_validate_json((Path(plan["source_snapshot"]) / "backend/evaluation/research/data/identity_bindings.reviewed.json").read_text())','        identities = IdentityMap.model_validate(identities.model_dump(mode="json"))')
p.write_text(s)
p=B/'evaluation/research/local_pilot.py';s=p.read_text().replace('import argparse\n','import argparse\nimport ast\n').replace('from contextlib import contextmanager\n','').replace('from .pilot_admission import validate_algorithm','from .pilot_admission import validate_algorithm\nfrom .identities import IdentityMap')
s=s.replace('    cases = value["cases"]','    if value["public_profile"]["education_system"] != "KZ national secondary":\n        raise ValueError("Public qualification differs from native source profile")\n    cases = value["cases"]')
s=s.replace('or request["qualification"] != "KZ national secondary":','or request["qualification"] != "KZ national secondary" or request["programme"] is not None or request["academic_year"] not in (None, "2027-2028"):\n')
# Source text AST is sufficient to bind the fixed canary profile without running it.
idx=s.index('\ndef prepare(')
s=s[:idx]+'''
def profile_contract(source: Path) -> dict[str, Any]:
    path = source / "backend/scripts/canary_discovery.py"
    tree = ast.parse(path.read_text())
    fn = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "canary_profile")
    call = next(node.value for node in fn.body if isinstance(node, ast.Return))
    kwargs = {item.arg: item.value for item in call.keywords}
    context = kwargs["context"]
    values = {item.arg: ast.literal_eval(item.value) for item in context.keywords if item.arg != "level"}
    expected = {"intended_fields": ["computer science"], "intake_term": "fall", "intake_year": 2027, "citizenship": "Kazakhstan", "country_of_residence": "Kazakhstan", "education_country": "Kazakhstan", "education_system": "KZ national secondary", "graduation_date": "2027-05-25"}
    level = next(item.value for item in context.keywords if item.arg == "level")
    if values != expected or ast.unparse(level) != "DegreeLevel.BACHELOR":
        raise ValueError("Native canary profile context differs from approved public request")
    return {"source_sha256": sha(path), "function_sha256": hashlib.sha256(ast.get_source_segment(path.read_text(), fn).encode()).hexdigest(), "context": expected, "degree": "bachelor", "synthetic_academics_and_funding_present": True, "qualification": "source plus invoked argv; raw does not serialize full profile"}


def registry_contract(source: Path, cases: list[dict[str, Any]]) -> dict[str, Any]:
    path = source / "backend/app/adapters/discovery/institution_registry.json"
    entries = read(path)
    from .live import COHORT as domains
    rows = []
    for case in cases:
        domain = domains[case["case_id"]]
        matches = [entry for entry in entries if controller._domain(entry["homepage"]) == domain]
        if len(matches) != 1 or case["domain"] != domain or case["university"] != matches[0]["name"]:
            raise ValueError("Public request differs from actual single registry selector")
        rows.append({"case_id": case["case_id"], "university": matches[0]["name"], "domain": domain})
    return {"path": str(path), "sha256": sha(path), "resolved": rows}

''' +s[idx:]
s=s.replace('*, selector_model: str, sealed_roots: list[Path])','*, selector_model: str, sealed_roots: list[Path], full_receipt: Path)')
s=s.replace('    public_cases(public)\n','    cases = public_cases(public)\n',1)
s=s.replace('    pins = []\n','''    full = read(full_receipt)
    if full.get("status") != "passed" or full.get("suite") != "full" or len(full.get("steps", [])) != 13 or any(row.get("exit_code") != 0 for row in full["steps"]) or full.get("source", {}).get("source_tree_sha256") != manifest["source_tree_sha256"]:
        raise ValueError("Actual exact-source full13 receipt required, not a declared success")
    profile = profile_contract(source)
    registry = registry_contract(source, cases)
    pins = [{"path": registry["path"], "sha256": registry["sha256"]}, {"path": str(full_receipt.resolve()), "sha256": sha(full_receipt)}]
''',1)
s=s.replace('"no_evaluator_dispatch": True}', '"no_evaluator_dispatch": True, "profile_contract": profile, "registry_contract": registry, "full_receipt": str(full_receipt.resolve())}')
s=s.replace('source_manifest=read(Path(gate.plan["source_manifest"])))','source_manifest=read(Path(gate.plan["source_manifest"])), identities=IdentityMap.model_validate_json((Path(gate.plan["source_snapshot"])/"backend/evaluation/research/data/identity_bindings.reviewed.json").read_text()), require_complete_job=False)')
s=s.replace('raw["canary"]["institutions"][0]["domain"] != case["domain"]:', 'raw["canary"]["institutions"][0]["domain"] != case["domain"] or raw["canary"]["batch"] != [case["university"]]:')
s=s.replace('"unknowns_not_absence": True}', '"unknowns_not_absence": True, "physical_files": {str(p.relative_to(out)): {"sha256": sha(p), "bytes": p.stat().st_size} for p in (captures[0], folder / f"{case_id}.json", folder / f"{case_id}.budget.json", folder / f"{case_id}.raw.json")}, "executed_argv": command, "profile_binding": gate.plan["profile_contract"], "runtime_mode": "native" if process_run is selector.run_owned_process else "offline_injected"}')
# Wrapper always seals a partial receipt and retains original raised object before gate closes.
s=s.replace('async def collect_expert(', 'async def _collect_expert(')
s=s.replace('    root.mkdir(parents=True)\n    began, started = clock(), datetime.now(UTC)','    began, started = clock(), datetime.now(UTC)\n    root.mkdir(parents=True)')
s=s.replace('"protective_wall_ms": WALL_MS, "budget_origin":', '"protective_wall_ms": WALL_MS, "wall_elapsed_before_ms": wall_elapsed(), "budget_origin":')
s=s.replace('"complete_eligible": status == "submitted_unreviewed" and processed == len(actions) and elapsed <= WALL_MS,', '"complete_eligible": status == "submitted_unreviewed" and processed == len(actions) and elapsed <= WALL_MS and isolate is Isolation.local and select is selector.select and run_tool is controller.run and clock is time.monotonic, "runtime_mode": "native" if isolate is Isolation.local and select is selector.select and run_tool is controller.run and clock is time.monotonic else "offline_injected",')
idx=s.index('\ndef authorize(')
s=s[:idx]+'''
async def collect_expert(gate, public, case, expert, **kwargs):
    try:
        return await _collect_expert(gate, public, case, expert, **kwargs)
    except BaseException as exc:
        root = gate.root / "private/experts" / expert / case["case_id"]
        root.mkdir(parents=True, exist_ok=True)
        accepted = sorted(root.glob("journal-*.accepted.json"))
        latest = read(accepted[-1]) if accepted else None
        raw_files = sorted((root / "raw").glob("*.json")) if (root / "raw").exists() else []
        receipt = {"case_id": case["case_id"], "expert": expert, "status": "partial_control_failure", "complete_eligible": False, "error_type": type(exc).__name__, "processed_through_action_count": latest["processed_through_action_count"] if latest else 0, "last_accepted_journal": latest["snapshot"] if latest else AcceptedJournal.initial().snapshot(), "source_raw_files": [{"path": str(p.relative_to(root)), "sha256": sha(p)} for p in raw_files], "attempted_model_turns": len(list(root.glob("selector-*.original.json"))), "attempted_source_actions": len(list(root.glob("tool-*.plan.json"))), "review_status": "unreviewed", "unknown_not_absence": True}
        store(root / "receipt.json", receipt)
        raise

''' +s[idx:]
s=s.replace('"evaluator_access_authorized": False, "score": None}', '"evaluator_access_authorized": False, "score": None, "runtime_mode": "native" if process_run is selector.run_owned_process and isolate is Isolation.local and select is selector.select and run_tool is controller.run else "offline_injected", "all_expert_complete_eligible": len(experts) == 20 and all(row["complete_eligible"] for row in experts)}')
s=s.replace("    parser.add_argument('--source-manifest',type=Path)", "    parser.add_argument('--source-manifest',type=Path)\n    parser.add_argument('--full-receipt',type=Path)")
s=s.replace('args.selector_model,args.sealed_root))','args.selector_model,args.sealed_root,args.full_receipt))').replace('sealed_roots=args.sealed_root))','sealed_roots=args.sealed_root,full_receipt=args.full_receipt))')
p.write_text(s)
# Controller wall meter is separate from charged tool time, preserving oldmode shape.
p=B/'evaluation/research/expert/controller.py';s=p.read_text();s=s.replace('    max_calls = _integer(plan, "max_calls")','''    wall_before = _integer(plan, "wall_elapsed_before_ms") if wall_only else 0
    if wall_only and not 0 <= wall_before < 900_000:
        raise ValueError("Original protective wall exhausted or invalid")
    max_calls = _integer(plan, "max_calls")''',1)
s=s.replace('    origin = plan.get(', '    if wall_only and exploration != "same_policy":\n        raise ValueError("Independent wall route cannot expand read/query caps")\n    origin = plan.get(',1)
s=s.replace('    initial = {','''    if wall_only and wall_before < int(state.get("wall_elapsed_ms_cumulative", 0)):
        raise ValueError("Protective wall cannot reset on resume")
    initial = {''',1)
s=s.replace('thinking_in_tool_ms=False)', 'thinking_in_tool_ms=False)',1)
s=s.replace('        summary.update(timing_policy=timing_policy, protective_wall_ms=900_000)','        summary.update(timing_policy=timing_policy, protective_wall_ms=900_000, wall_elapsed_before_ms=wall_before)')
s=s.replace('            with _reserve_log(logs_dir, name, record) as output:', '''            if wall_only:
                record["wall_elapsed_ms_before"] = wall_before + math.ceil((monotonic() - run_began) * 1000)
            with _reserve_log(logs_dir, name, record) as output:''')
s=s.replace('                exhausted = strict and (','                exhausted = strict and (\n                    (wall_only and wall_before + math.ceil((monotonic() - run_began) * 1000) >= 900_000)\n                    or')
s=s.replace('                        None if max_ms is None else max_ms if exploration', '                        max(1, 900_000 - wall_before - math.ceil((monotonic() - run_began) * 1000)) if wall_only else max_ms if exploration')
s=s.replace('                name, sha = _write_log(logs_dir, name, record, output=output)','''                if wall_only:
                    record["wall_elapsed_ms_cumulative"] = wall_before + math.ceil((monotonic() - run_began) * 1000)
                name, sha = _write_log(logs_dir, name, record, output=output)''')
s=s.replace('    return summary\n\n\nasync def run', '    if wall_only:\n        summary["final"]["wall_elapsed_ms"] = wall_before + math.ceil((monotonic() - run_began) * 1000)\n    return summary\n\n\nasync def run')
# existing_state state currently includes record fields via update? Add separately near its return.
s=s.replace('        previous = current','        previous = current')
s=s.replace('        state.update(record)', '        state.update(record)')
p.write_text(s)
print('refined six external files; no dispatch')
