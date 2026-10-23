"""Finite native harness: no sockets, SQL, child commands or external plugins."""
import importlib
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys

mode = sys.argv[1]
assert mode in {"off", "on"}
packet = Path(__file__).resolve().parents[1]
os.chdir(packet / "runtime" / mode)
sys.path.insert(0, str(Path.cwd() / "backend"))
# The process receives an allowlisted environment from run_native.py; there
# is no .env at this cwd and no private runtime file copied into the snapshot.
os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
os.environ["REJECTED_DIAGNOSTICS_PROOF_MODE"] = mode
os.environ["REJECTED_DIAGNOSTICS_PROOF_DIR"] = str(packet / "logs")
counts = dict(dns=0, connect=0, listen=0, db=0, child_process=0)

def denied(kind):
    def block(*args, **kwargs):
        counts[kind] += 1
        raise AssertionError(f"FORBIDDEN_RUNTIME_{kind}")
    return block

socket.getaddrinfo = denied("dns")
socket.socket.connect = denied("connect")
socket.socket.connect_ex = denied("connect")
socket.socket.listen = denied("listen")
sqlite3.connect = denied("db")
subprocess.Popen = denied("child_process")

Engine = importlib.import_module("sqlalchemy.engine").Engine
Engine.connect = denied("db")
Engine.raw_connection = denied("db")
pytest = importlib.import_module("pytest")

try:
    code = pytest.main([
        str(packet / "harness" / "test_rejected_diagnostics.py"), "-q", "-ra",
        "--tb=short", "--confcutdir=" + str(packet / "harness"),
        "--junitxml=" + str(packet / "logs" / (mode + "-junit.xml")),
    ])
finally:
    (packet / "logs" / (mode + "-guard-counts.json")).write_text(
        json.dumps(counts, indent=2) + "\n"
    )
assert not any(counts.values()), counts
sys.exit(code)
