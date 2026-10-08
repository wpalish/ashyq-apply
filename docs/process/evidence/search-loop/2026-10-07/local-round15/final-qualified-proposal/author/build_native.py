from pathlib import Path
import hashlib,json
OWN=Path(__file__).resolve().parent
REPO=OWN.parents[2]/'work/ashyq-apply'
base=OWN/'proposed/backend/evaluation/research'
(base/'expert').mkdir(parents=True)
(OWN/'originals').mkdir()
pins={}
def native(name,changes):
 p=REPO/'backend/evaluation/research/expert'/name; old=p.read_text(); new=old
 for a,b in changes:
  assert a in new,(name,a[:90])
  new=new.replace(a,b,1)
 (OWN/'originals'/name).write_bytes(p.read_bytes());(base/'expert'/name).write_text(new)
 pins[str(p.relative_to(REPO))]={'original_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'proposed_sha256':hashlib.sha256(new.encode()).hexdigest()}

native('controller.py',[
 ('def _action_deadline(plan: dict[str, Any], max_ms: int)', 'def _action_deadline(plan: dict[str, Any], max_ms: int | None)'),
 ('1 <= value <= max_ms', 'max_ms is not None and 1 <= value <= max_ms'),
 ('    max_ms: int\n', '    max_ms: int | None\n'),
 ('and self.ms <= self.max_ms', 'and (self.max_ms is None or self.ms <= self.max_ms)'),
 ('            if record["tool_policy"].get("budget_origin") != budget_origin:', '            if record["tool_policy"].get("timing_policy", "legacy_active") != plan.get("timing_policy", "legacy_active"):\n                raise ValueError("Resume timing policy differs from recorded policy")\n            if record["tool_policy"].get("budget_origin") != budget_origin:'),
 ('    max_calls, max_ms = _integer(plan, "max_calls"), _integer(plan, "max_ms")\n', '    timing_policy = plan.get("timing_policy", "legacy_active")\n    if timing_policy not in {"legacy_active", "expert_wall_only"}:\n        raise ValueError("Unknown expert timing policy")\n    wall_only = timing_policy == "expert_wall_only"\n    if wall_only and (not strict or plan.get("budget_origin") != "independent_full_budget" or plan.get("max_ms") is not None or plan.get("protective_wall_ms") != 900_000):\n        raise ValueError("Wall-only requires explicit independent strict60/6 policy, null active cap and900s wall")\n    max_calls = _integer(plan, "max_calls")\n    max_ms = None if wall_only else _integer(plan, "max_ms")\n'),
 ('if max_calls < 1 or max_ms < 1 or max_queries < 1:', 'if max_calls < 1 or (max_ms is not None and max_ms < 1) or max_queries < 1:'),
 ('        or max_ms > STRICT_MAX_MS', '        or (max_ms is not None and max_ms > STRICT_MAX_MS)'),
 ('    if action_deadline_ms is not None:\n        policy["action_deadline_ms"]', '    if wall_only:\n        policy.update(timing_policy=timing_policy, protective_wall_ms=900_000, thinking_in_tool_ms=False)\n    if action_deadline_ms is not None:\n        policy["action_deadline_ms"]'),
 ('    for kind, items in (("replay", plan.get("replay", [])),', '    if wall_only:\n        summary.update(timing_policy=timing_policy, protective_wall_ms=900_000)\n    for kind, items in (("replay", plan.get("replay", [])),'),
 ('                    action_start_ms >= ledger.max_ms', '                    (ledger.max_ms is not None and action_start_ms >= ledger.max_ms)'),
 ('                        max_ms if exploration == "outside_policy" else max_ms - action_start_ms', '                        None if max_ms is None else max_ms if exploration == "outside_policy" else max_ms - action_start_ms'),
 ('                            max(1, action_budget_ms) / 1000 if strict else None', '                            max(1, action_budget_ms) / 1000 if strict and action_budget_ms is not None else None'),
 ('                                deadline_floor = max_ms', '                                deadline_floor = max_ms or 0'),
])
# A new trace policy changes only opted-in validation. Legacy dumps retain their prior fields.
native('models.py',[
 ('TypeAdapter, model_validator', 'TypeAdapter, model_serializer, model_validator'),
 ('    max_elapsed_ms: int = Field(ge=1)\n', '    max_elapsed_ms: int | None = Field(ge=1)\n    timing_policy: Literal["legacy_active", "expert_wall_only"] = "legacy_active"\n    protective_wall_ms: int | None = Field(default=None, ge=1)\n'),
 ('    @model_validator(mode="after")\n    def ordered_actions', '    @model_serializer(mode="wrap")\n    def keep_legacy_fields(self, handler):\n        value = handler(self)\n        if self.timing_policy == "legacy_active":\n            value.pop("timing_policy", None)\n            value.pop("protective_wall_ms", None)\n        return value\n\n    @model_validator(mode="after")\n    def ordered_actions'),
 ('        if self.started_at.tzinfo is None', '        if self.timing_policy == "legacy_active" and (self.max_elapsed_ms is None or self.protective_wall_ms is not None):\n            raise ValueError("Legacy trace requires its active cap")\n        if self.timing_policy == "expert_wall_only" and (self.max_elapsed_ms is not None or self.protective_wall_ms != 900_000):\n            raise ValueError("Wall-only trace requires null active cap and900s wall")\n        if self.started_at.tzinfo is None'),
 ('        if self.ended_at < self.started_at:', '        if self.timing_policy == "expert_wall_only" and (self.ended_at - self.started_at).total_seconds() > 900:\n            raise ValueError("Expert trace exceeds protective wall")\n        if self.ended_at < self.started_at:'),
 ('                or action.elapsed_ms_cumulative > self.max_elapsed_ms', '                or (self.max_elapsed_ms is not None and action.elapsed_ms_cumulative > self.max_elapsed_ms)'),
 ('    if "case_id" in record and record["case_id"] != parsed.case_id:', '    policy = record.get("tool_policy") or {}\n    if policy.get("timing_policy", "legacy_active") != parsed.timing_policy:\n        raise ValueError("Raw timing policy differs from trace")\n    if parsed.timing_policy == "expert_wall_only" and (policy.get("protective_wall_ms") != 900_000 or policy.get("thinking_in_tool_ms") is not False or record.get("budget_origin") != "independent_full_budget"):\n        raise ValueError("Raw independent wall policy incomplete")\n    if "case_id" in record and record["case_id"] != parsed.case_id:'),
 ('    budget = packet["baseline_budget"]', '    budget = packet["baseline_budget"]\n    if parsed.timing_policy != budget.get("timing_policy", "legacy_active"):\n        raise ValueError("Packet timing policy differs from trace")\n    if parsed.timing_policy == "expert_wall_only" and (packet.get("comparison_mode") != "independent_full_budget" or budget.get("protective_wall_ms") != 900_000):\n        raise ValueError("Independent packet wall policy incomplete")'),
])
native('selector.py',[
 ('    model: str | None = None,\n', '    model: str | None = None,\n    timeout_policy: str = "legacy_active",\n'),
 ('    if not 0 < timeout_seconds <= 55:\n        raise ValueError("Selector timeout must be in (0,55] seconds")', '    if timeout_policy not in {"legacy_active", "expert_wall_only"}:\n        raise ValueError("Unknown selector timeout policy")\n    ceiling = 900 if timeout_policy == "expert_wall_only" else 55\n    if not 0 < timeout_seconds <= ceiling:\n        raise ValueError("Selector timeout exceeds its declared policy")'),
])
(OWN/'native-source-pins.json').write_text(json.dumps(pins,indent=2)+'\n')
# Port the reviewed neutral admission function, with explicit per-plan dependencies.
p=REPO.parent/'local-round10/genuine-baseline/execute_baseline.py'
import ast
s=p.read_text(); t=ast.parse(s); f=next(n for n in t.body if isinstance(n,ast.FunctionDef) and n.name=='validate')
text='\n'.join(s.splitlines()[f.lineno-1:f.end_lineno])
text=text.replace('def validate(case, capture, observed, budget, raw, *, require_complete_job=True):','def validate_algorithm(case, capture, observed, budget, raw, *, plan, source_manifest, require_complete_job=False):\n    PLAN = plan')
text=text.replace('manifest = json.loads((FULL / "source-manifest.json").read_text())','manifest = source_manifest')
(base/'pilot_admission.py').write_text('"""Neutral native capture admission; no gold, scorer or network.\n\nPort of reviewed4fa validator. All original assertions retained.\n"""\nimport json\nimport math\nfrom pathlib import Path\nfrom datetime import datetime, timezone\n\n'+text+'\n')
(OWN/'validator-origin.json').write_text(json.dumps({'original':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'changes':['explicit plan/source_manifest parameters replace external global PLAN/FULL','default bounded terminal lane False; original assertion bodies otherwise unchanged'],'no_original_expectations_modified':True},indent=2)+'\n')
print('native proposal and neutral validator written')
