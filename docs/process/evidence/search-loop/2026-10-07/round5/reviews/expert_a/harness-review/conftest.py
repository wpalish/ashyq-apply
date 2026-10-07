"""Hash-pinned harness snapshot; all test modes prohibit sockets and real Settings."""
import importlib
import importlib.util
import socket
import sys
from pathlib import Path

import pytest

from app import config

name = "evaluation.research.live"
package = importlib.import_module("evaluation.research")
path = Path(__file__).resolve().parent / "source-snapshot/backend/evaluation/research/live.py"
spec = importlib.util.spec_from_file_location(name, path)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
sys.modules[name] = module
spec.loader.exec_module(module)
package.live = module


@pytest.fixture(autouse=True)
def isolated_configuration_and_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("Offline harness review attempted network")
    monkeypatch.setattr(socket, "getaddrinfo", denied)
    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(socket.socket, "connect", denied)
    class SavedTestSettings:
        def __init__(self, **kwargs):
            self.search_provider = kwargs.get("search_provider", "exa_mcp")
        def _validate_search(self):
            return None
    monkeypatch.setattr(config, "Settings", SavedTestSettings)
