"""Import only explicitly proposed modules; every other dependency remains production code."""

from __future__ import annotations

import importlib.abc
import importlib.util
import os
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
MODULES = {
    "app.adapters.base",
    "app.pipeline.runner",
    "app.catalogue.discovery",
    "app.adapters.discovery.live_discovery",
    "app.adapters.discovery.catalog_walker",
    "app.pipeline.control",
    "app.pipeline.read_budget",
}


class ProposedModules(importlib.abc.MetaPathFinder):
    def __init__(self, modules, base):
        self.modules = modules
        self.base = base

    def find_spec(self, fullname, path=None, target=None):
        if fullname in self.modules:
            file = self.base / "proposed" / Path(*fullname.split(".")).with_suffix(".py")
            return importlib.util.spec_from_file_location(fullname, file)
        return None


def install():
    mode = os.environ.get("READGUARD_REVIEW_TARGET", "proposal")
    if mode not in {"proposal", "legacy", "v1"}:
        raise RuntimeError(f"Unknown offline target: {mode}")
    modules = MODULES if mode != "legacy" else {"app.pipeline.control", "app.pipeline.read_budget"}
    loaded = modules.intersection(sys.modules)
    if loaded:
        raise RuntimeError(
            f"Shadow must install before patched production imports: {sorted(loaded)}"
        )
    base = BASE.parent / "expert_b-readguard" if mode == "v1" else BASE
    sys.meta_path.insert(0, ProposedModules(modules, base))
