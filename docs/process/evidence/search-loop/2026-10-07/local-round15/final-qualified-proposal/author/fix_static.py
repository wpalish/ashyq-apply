from pathlib import Path
import ast
O=Path(__file__).resolve().parent;B=O/'runtime/backend'
p=B/'tests/test_local_pilot.py';s=p.read_text();tree=ast.parse(s);lines=s.splitlines(keepends=True);starts=[];n=0
for line in lines:starts.append(n);n+=len(line)
changes=[]
for node in ast.walk(tree):
 if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='dict' and not node.args and all(k.arg is not None for k in node.keywords):
  replacement=ast.unparse(ast.Dict(keys=[ast.Constant(k.arg) for k in node.keywords],values=[k.value for k in node.keywords]));changes.append((starts[node.lineno-1]+node.col_offset,starts[node.end_lineno-1]+node.end_col_offset,replacement))
for a,b,text in sorted(changes,reverse=True):s=s[:a]+text+s[b:]
p.write_text(s)
p=B/'evaluation/research/local_pilot.py';s=p.read_text().replace('import uuid\n','import uuid\nfrom contextlib import suppress\n').replace('        try:\n            store(self.stop, value)\n        except FileExistsError:\n            pass','        with suppress(FileExistsError):\n            store(self.stop, value)')
s=s.replace('    wall_elapsed = lambda: max(0, math.ceil((clock() - began) * 1000))','    def wall_elapsed():\n        return max(0, math.ceil((clock() - began) * 1000))')
s=s.replace('        try:\n            store(root / "receipt.json", receipt)\n        except OSError:\n            pass  # Preserve the original control; no successful receipt is inferred.','        with suppress(OSError):  # Preserve original control if persistence fails.\n            store(root / "receipt.json", receipt)')
s=s.replace('                try:\n                    gate.refuse(', '                with suppress(Stopped):\n                    gate.refuse(').replace('                except Stopped:\n                    pass\n','')
p.write_text(s)
p=B/'evaluation/research/expert/selector.py';s=p.read_text().replace('import signal\n','import signal\nfrom contextlib import suppress\n').replace('        try:\n            os.killpg(process.pid, signal.SIGKILL)\n        except ProcessLookupError:\n            pass','        with suppress(ProcessLookupError):\n            os.killpg(process.pid, signal.SIGKILL)');p.write_text(s)
p=B/'evaluation/research/expert/controller.py';s=p.read_text();s=s.replace('            if plan.get("timing_policy") == "expert_wall_only":\n                if (','            if plan.get("timing_policy") == "expert_wall_only" and (',1)
start=s.index('            if plan.get("timing_policy") == "expert_wall_only" and (');end=s.index('            if not isinstance(previous_policy',start)
part=s[start:end];part=part.replace('                    ', '                ').replace('                ):','            ):').replace('                raise ValueError', '            raise ValueError');s=s[:start]+part+s[end:];p.write_text(s)
# Preserve all formatted/check-ready bytes into proposal.
for p in (O/'proposed/backend').rglob('*.py'):
 q=B/p.relative_to(O/'proposed/backend');p.write_bytes(q.read_bytes())
print('manual literal/context fixes complete')
