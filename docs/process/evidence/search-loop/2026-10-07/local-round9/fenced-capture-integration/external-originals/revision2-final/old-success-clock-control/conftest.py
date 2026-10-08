"""External review loader for ONLY the two proposed harness modules, never app."""

import importlib.util
import sys
from pathlib import Path

import evaluation.research
import scripts

P = Path('/Users/wpalish/Documents/Codex/2026-10-07/x20/work/local-round8/a-genuine-canary/revision2/proposed')
for name, rel, parent, attr in [
    ("scripts.canary_discovery", "scripts/canary_discovery.py", scripts, "canary_discovery"),
    ("evaluation.research.live", "evaluation/research/live.py", evaluation.research, "live"),
]:
    spec = importlib.util.spec_from_file_location(name, P / rel)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    setattr(parent, attr, module)


def pytest_sessionfinish(session, exitstatus):
    import hashlib
    import importlib
    import json

    records = []
    for name in [
        "app.jobs.worker",
        "app.jobs.store",
        "app.pipeline.runner",
        "app.pipeline.control",
        "app.pipeline.read_budget",
        "app.adapters.fetching",
    ]:
        module = importlib.import_module(name)
        path = Path(module.__file__).resolve()
        records.append(
            {
                "name": name,
                "path": str(path),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    (
        Path(__file__).parent
        / ("runtime-imports-" + Path(session.config.getoption("basetemp")).name + ".json")
    ).write_text(
        json.dumps(
            {
                "actual_modules": records,
                "proposal_harness_only": ["scripts.canary_discovery", "evaluation.research.live"],
                "app_shadow_loader": False,
                "final_source_flag": sys.modules["app.pipeline.read_budget"].UNIVERSITY_READ_BUDGET,
            },
            indent=2,
        )
        + "\n"
    )
