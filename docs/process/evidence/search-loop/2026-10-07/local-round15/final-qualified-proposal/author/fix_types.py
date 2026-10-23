from pathlib import Path
O=Path(__file__).resolve().parent;B=O/'runtime/backend';p=B/'evaluation/research/expert/controller.py';s=p.read_text();a=s.index('                    action_budget_ms = (');b=s.index('                    navigation_limited = (',a)
s=s[:a]+'''                    if wall_only:
                        action_budget_ms = max(1, 900_000 - wall_before - math.ceil((monotonic() - run_began) * 1000))
                    else:
                        assert max_ms is not None
                        action_budget_ms = max_ms if exploration == "outside_policy" else max_ms - action_start_ms
'''+s[b:];p.write_text(s)
p=B/'evaluation/research/local_pilot.py';s=p.read_text();s=s.replace('    kwargs = {item.arg: item.value for item in call.keywords}','    if not isinstance(call, ast.Call):\n        raise ValueError("Native profile return must be an explicit constructor")\n    kwargs = {item.arg: item.value for item in call.keywords}',1).replace('    context = kwargs["context"]','    context = kwargs["context"]\n    if not isinstance(context, ast.Call):\n        raise ValueError("Native context must be an explicit constructor")',1)
s=s.replace('    return {\n        "source_sha256": sha(path),','    function_source = ast.get_source_segment(path.read_text(), fn)\n    if function_source is None:\n        raise ValueError("Native profile source is unavailable")\n    return {\n        "source_sha256": sha(path),',1)
s=s.replace('ast.get_source_segment(path.read_text(), fn).encode()', 'function_source.encode()',1)
s=s.replace('    executables = {\n', '    executable_paths = {\n',1).replace('executables.values()', 'executable_paths.values()',1).replace('    executable_bindings = {}\n    for name, path in executables.items():','    executable_bindings = {}\n    executables: dict[str,str] = {}\n    for name, path in executable_paths.items():',1)
s=s.replace('        self.events = []','        self.events: list[str] = []',1)
s=s.replace('        if location.kind == "pdf":\n            context = source.pdf_pages[location.page - 1]','        if location.kind == "pdf":\n            if source.pdf_pages is None or location.page is None:\n                raise ValueError("Selected PDF location has no saved page")\n            context = source.pdf_pages[location.page - 1]',1)
s=s.replace('    journal, actions, summary = AcceptedJournal.initial(), [], None','    journal = AcceptedJournal.initial()\n    actions: list[Action] = []\n    summary: dict[str,Any] | None = None',1).replace('        outputs = []','        outputs: list[dict[str,Any]] = []',1)
s=s.replace('            action = decision.action\n','            action = decision.action\n            if action is None:\n                raise ValueError("Navigation decision has no action")\n',1).replace('            if action.tool == "view":\n                recorded =','            if action.tool == "view":\n                if action.source_step is None:\n                    raise ValueError("View has no completed source step")\n                recorded =',1)
s=s.replace('            store(root / f"tool-{len(actions) + 1:04d}.summary.json", summary)','            if not isinstance(summary, dict):\n                raise ValueError("Controller did not supply a native summary")\n            store(root / f"tool-{len(actions) + 1:04d}.summary.json", summary)',1)
p.write_text(s)
for p in (O/'proposed/backend').rglob('*.py'):p.write_bytes((B/p.relative_to(O/'proposed/backend')).read_bytes())
