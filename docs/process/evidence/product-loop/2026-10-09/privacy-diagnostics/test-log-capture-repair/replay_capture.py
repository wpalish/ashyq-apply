import json,logging,socket,subprocess
from pathlib import Path
import pytest
counts={"dns":0,"connect":0,"listen":0,"child":0}
@pytest.fixture(scope="session",autouse=True)
def synthetic_migration_disabled_state():
    # Reproduce the established fileConfig effect, without calling migrations.
    original={n:logging.getLogger(n).disabled for n in ("unimatch.fetch","unimatch.pipeline","unimatch.worker")}
    for name in original: logging.getLogger(name).disabled=True
    yield
    for name,value in original.items(): logging.getLogger(name).disabled=value
@pytest.fixture(autouse=True)
def no_real_network_or_children(monkeypatch):
    def denied(kind):
        def call(*a,**kw):
            counts[kind]+=1
            raise AssertionError("forbidden real "+kind)
        return call
    monkeypatch.setattr(socket,"getaddrinfo",denied("dns"))
    monkeypatch.setattr(socket.socket,"connect",denied("connect"))
    monkeypatch.setattr(socket.socket,"listen",denied("listen"))
    monkeypatch.setattr(subprocess,"Popen",denied("child"))
def pytest_sessionfinish(session,exitstatus):
    import os
    Path(os.environ["CAPTURE_GUARD_RESULT"]).write_text(json.dumps({"exitstatus":exitstatus,"counts":counts,"qualification":"Synthetic predisabling replay only; own SQLite permitted; no real migration or production proof."},indent=2)+"\n")
