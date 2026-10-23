"""Load hash-verified external reverse-reconstructed frozen copies, without changing repository files."""
import importlib
import importlib.util
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent / "reverse-reconstruction" / "backend"
for name in ("app.adapters.base", "app.adapters.discovery.live_discovery", "app.adapters.search.retrieval", "app.catalogue.discovery"):
    parent, child = name.rsplit(".", 1)
    package = importlib.import_module(parent)
    spec = importlib.util.spec_from_file_location(name, root.joinpath(*name.split(".")).with_suffix(".py"))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    setattr(package, child, module)
