"""Optional external-source loading. The repository is never edited."""

import importlib
import importlib.util
import os
import sys
from pathlib import Path

if os.environ.get("EXPERT_B_PROPOSED_SOURCE") == "1":
    root = Path(__file__).resolve().parent / "source" / "backend"
    for name in (
        "app.adapters.base",
        "app.adapters.discovery.live_discovery",
        "app.adapters.search.retrieval",
        "app.catalogue.discovery",
    ):
        parent, child = name.rsplit(".", 1)
        package = importlib.import_module(parent)
        spec = importlib.util.spec_from_file_location(
            name, root.joinpath(*name.split(".")).with_suffix(".py")
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        setattr(package, child, module)
