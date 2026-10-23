from pathlib import Path
import shutil
O=Path(__file__).resolve().parent;P=O/'proposed/backend/evaluation/research'
H=O/'history/developing-v1';H.mkdir(parents=True);shutil.copytree(P,H/'research')
p=P/'expert/controller.py';s=p.read_text().replace('not max_ms is not None and 1 <= value <= max_ms','not (max_ms is not None and 1 <= value <= max_ms)')
s=s.replace('plan.get("protective_wall_ms") != 900_000','type(plan.get("protective_wall_ms")) is not int or plan.get("protective_wall_ms") != 900_000 or "max_ms" not in plan or plan.get("max_calls") != 60 or plan.get("max_search_queries") != 6')
# Parenthesize the whole wall-only invalid contract; previous replacement extends its clause.
s=s.replace('                raise ValueError("Resume timing policy differs from recorded policy")','                raise ValueError("Resume timing policy differs from recorded policy")\n            if plan.get("timing_policy") == "expert_wall_only" and (record["tool_policy"].get("protective_wall_ms") != 900_000 or record["tool_policy"].get("thinking_in_tool_ms") is not False):\n                raise ValueError("Resume protective wall policy changed")')
p.write_text(s)
p=P/'expert/models.py';s=p.read_text();s=s.replace('self.protective_wall_ms != 900_000):','self.protective_wall_ms != 900_000 or self.max_fetcher_calls != 60 or self.max_search_queries != 6):')
s=s.replace('    @model_serializer(mode="wrap")','    @model_validator(mode="before")\n    @classmethod\n    def wall_raw_types(cls, value):\n        if isinstance(value, dict) and value.get("timing_policy") == "expert_wall_only":\n            for key in ("max_fetcher_calls", "max_search_queries", "protective_wall_ms", "initial_fetcher_calls", "initial_elapsed_ms", "initial_search_queries"):\n                if type(value.get(key)) is not int:\n                    raise ValueError("Independent raw counters must be exact integers")\n        return value\n\n    @model_serializer(mode="wrap")')
p.write_text(s)
p=P/'expert/selector.py';s=p.read_text();s=s.replace('import math\n','import math\nimport os\nimport signal\n')
idx=s.index('\ndef select(')
s=s[:idx]+'''\ndef run_owned_process(command, *, cwd, input=None, env=None, timeout, text=False, capture_output=True, check=False):
    """Own one process group; deadline cleanup never leaves research children."""
    if not capture_output or check:
        raise ValueError("Owned process requires original captured streams")
    process = subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.PIPE if input is not None else None, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=text, start_new_session=True)
    try:
        stdout, stderr = process.communicate(input=input, timeout=timeout)
    except BaseException:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()
        raise
    return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)

''' +s[idx:]
s=s.replace('        completed = subprocess.run(','        runner = run_owned_process if timeout_policy == "expert_wall_only" else subprocess.run\n        completed = runner(')
p.write_text(s)
p=P/'local_pilot.py';s=p.read_text().replace('selector_model: str) -> Path','selector_model: str, sealed_roots: list[Path]) -> Path')
s=s.replace('    plan = {','    protected = tuple(p.resolve() for p in sealed_roots)\n    if not protected or not all(any(p.is_relative_to(root) for root in protected) for p in (source, Path(manifest["repository"]).resolve(), out.resolve())):\n        raise ValueError("Explicit sealed roots must cover source/repository/output history; do not probe answers")\n    plan = {',1)
s=s.replace('"sealed_roots": [str(source.parent.parent.resolve()), str(out.parent.resolve()),','"sealed_roots": [*[str(p) for p in protected],')
s=s.replace('process_run=subprocess.run','process_run=selector.run_owned_process')
s=s.replace('timeout=150','timeout=135')
s=s.replace('            turn = select(', '            remaining = (WALL_MS - wall_elapsed()) / 1000\n            if remaining <= 0:\n                status = "protective_wall_expired"\n                break\n            prompt_path = root / f"selector-{turn_index:04d}.prompt.json"\n            store(prompt_path, prompt)\n            turn = select(')
s=s.replace('            candidate, trace, proof = neutral_checkpoint(', '            candidate, trace, proof = neutral_checkpoint(')
s=s.replace('"snapshot": candidate.snapshot(), "trace": trace,','"snapshot": candidate.snapshot(), "prior_snapshot": journal.snapshot(), "decision": turn.answer, "trace": trace,')
s=s.replace('            if decision.kind == "submit":\n                status =', '            if decision.kind == "submit":\n                from .expert.blind_cli import selector_answer\n                replay = read(original)\n                if replay["returncode"] != 0 or replay["error_kind"] is not None or selector_answer(replay["stdout"], replay["answer_file"]) != turn.answer:\n                    raise ValueError("Final original streams/output do not prove a completed submit")\n                status =')
s=s.replace('            action_plan = {', '            if wall_elapsed() >= WALL_MS:\n                status = "protective_wall_expired"\n                break\n            action_plan = {')
s=s.replace('    parser.add_argument(\'--selector-model\')','    parser.add_argument(\'--selector-model\')\n    parser.add_argument(\'--sealed-root\',type=Path,action=\'append\')')
s=s.replace('args.out,args.selector_model))','args.out,args.selector_model,args.sealed_root))')
s=s.replace('selector_model=args.selector_model))','selector_model=args.selector_model,sealed_roots=args.sealed_root))')
# Attempt status is reserved independently of source-action count; failed model
# does not become an unrun expert. Earlier accepted checkpoints stay on disk.
s=s.replace('        algorithms, experts, error = [], [], None','        algorithms, experts, error = [], [], None\n        attempted_algorithms, attempted_experts = [], []')
s=s.replace('                algorithms.append(collect_algorithm','                attempted_algorithms.append(case["case_id"])\n                algorithms.append(collect_algorithm')
s=s.replace('                        experts.append(asyncio.run','                        attempted_experts.append((case["case_id"],expert))\n                        experts.append(asyncio.run')
s=s.replace('"unrun_algorithms": [c for c in COHORT if c not in {r[\'case_id\'] for r in algorithms}]','"attempted_algorithms": attempted_algorithms, "attempted_experts": [{"case_id": c,"expert": e} for c,e in attempted_experts], "unrun_algorithms": [c for c in COHORT if c not in attempted_algorithms]')
s=s.replace('if (c,e) not in {(r[\'case_id\'],r[\'expert\']) for r in experts}','if (c,e) not in attempted_experts')
p.write_text(s)
(O/'history/developing-v1/qualification.json').write_text('{"status":"external developing snapshot before tests","static_defect":"_action_deadline replacement precedence typo; fixed before native runs","not_native_application_failure":true}\n')
print('explicit clock, typed bindings, raw replay, isolation roots and attempted accounting refined')
