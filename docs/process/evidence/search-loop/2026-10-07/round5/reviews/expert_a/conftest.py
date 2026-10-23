"""Load the external proposed matcher module; no repository mutations."""

import importlib
import importlib.util
import sys
from pathlib import Path

name = "app.adapters.discovery.live_discovery"
package = importlib.import_module("app.adapters.discovery")
path = Path(__file__).resolve().parent / "proposed/backend/app/adapters/discovery/live_discovery.py"
spec = importlib.util.spec_from_file_location(name, path)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
sys.modules[name] = module
spec.loader.exec_module(module)
package.live_discovery = module
