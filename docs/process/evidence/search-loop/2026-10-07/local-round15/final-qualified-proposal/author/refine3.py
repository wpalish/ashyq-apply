from pathlib import Path
O=Path(__file__).resolve().parent;B=O/'proposed/backend'
p=B/'evaluation/research/local_pilot.py';s=p.read_text().replace('WALL_MS = 900_000','WALL_MS = 900_000\nNATIVE_ISOLATE = Isolation.local').replace('isolate=Isolation.local','isolate=NATIVE_ISOLATE').replace('isolate is Isolation.local','isolate is NATIVE_ISOLATE')
s=s.replace('        store(root / "receipt.json", receipt)\n        raise','        try:\n            store(root / "receipt.json", receipt)\n        except OSError:\n            pass  # Preserve the original control; no successful receipt is inferred.\n        raise')
s=s.replace('        except Exception as exc:\n            error = type(exc).__name__','        except BaseException as exc:\n            error = type(exc).__name__')
p.write_text(s)
p=B/'evaluation/research/expert/controller.py';s=p.read_text().replace('    previous = (0, 0, 0)','    previous = (0, 0, 0)\n    previous_wall = 0')
s=s.replace('                raise ValueError("Resume protective wall policy changed")','''                raise ValueError("Resume protective wall policy changed")
            if plan.get("timing_policy") == "expert_wall_only":
                wb = _integer(record, "wall_elapsed_ms_before")
                wa = _integer(record, "wall_elapsed_ms_cumulative")
                if not previous_wall <= wb <= wa <= 900_000:
                    raise ValueError("Protective wall raw counters invalid/decrease")
                previous_wall = wa''')
p.write_text(s)
p=B/'evaluation/research/expert/models.py';s=p.read_text().replace('        raise ValueError("Raw independent wall policy incomplete")','''        raise ValueError("Raw independent wall policy incomplete")
    if parsed.timing_policy == "expert_wall_only":
        wb = record.get("wall_elapsed_ms_before")
        wa = record.get("wall_elapsed_ms_cumulative")
        if type(wb) is not int or type(wa) is not int or not 0 <= wb <= wa <= 900_000:
            raise ValueError("Raw protective wall counter invalid")''')
p.write_text(s)
# Sync only owned proposed modules.
for p in B.rglob('*.py'):
 q=O/'runtime/backend'/p.relative_to(B);q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(p.read_bytes())
