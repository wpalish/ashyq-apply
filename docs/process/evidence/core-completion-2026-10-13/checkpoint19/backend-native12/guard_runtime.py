"""Proposal-only isolation layer: no application imports, no secret loading."""
from __future__ import annotations

import atexit
import json
import os
import re
import socket
import sys
from pathlib import Path

STATE: dict = {"outside_attempts": [], "allowed_pg_connections": [], "app_preimported": False,
               "ipv6_trait_restored": True, "driver_guard_installed": False,
               "startup_stage": "stdlib"}
RUNTIME = Path(os.environ["FULL_BACKEND_RUNTIME"]).resolve()
EVIDENCE = Path(os.environ["FULL_BACKEND_EVIDENCE"]).resolve()
SOURCE = Path(os.environ["FULL_BACKEND_SOURCE"]).resolve()
ALLOWED_ASSETS = set(json.loads(os.environ["FULL_BACKEND_ALLOWED_ASSETS"]))
IP_FAMILIES = {socket.AF_INET, socket.AF_INET6}
PYTHON_KEYS = {"autocommit", "prepare_threshold", "context", "row_factory", "cursor_factory"}


def write_state() -> None:
    if EVIDENCE.is_dir():
        (EVIDENCE / f"guard-{os.getpid()}.json").write_text(
            json.dumps(STATE, indent=2) + "\n"
        )


def deny(label: str) -> None:
    STATE["outside_attempts"].append(label)
    # Metadata only: no host/arguments, source lines, locals or exception text.
    current = os.environ.get('PYTEST_CURRENT_TEST', '')
    current = current.split('[', 1)[0].split(' (', 1)[0]
    frames = []
    frame = sys._getframe(1)
    try:
        while frame is not None and len(frames) < 24:
            frames.append({'filename': frame.f_code.co_filename,
                           'lineno': frame.f_lineno,
                           'function': frame.f_code.co_name})
            frame = frame.f_back
    finally:
        del frame
    STATE.setdefault('outside_attempt_metadata', []).append({
        'event': label, 'current_native_node_without_params': current or None,
        'stack': frames,
    })
    write_state()  # persist swallowed import/test attempts immediately
    raise PermissionError("Full backend gate refused outside I/O: " + label)


def private_path(value: str | os.PathLike) -> bool:
    path = Path(value).resolve()
    return path.is_relative_to(RUNTIME)


def audit(event: str, args: tuple) -> None:
    # Audit hooks survive socket monkeypatches and cover Python children through
    # sitecustomize; the outer inherited OS sandbox also covers native children.
    if event in {"socket.connect", "socket.bind", "socket.sendto"}:
        sock = args[0]
        if sock.family in IP_FAMILIES:
            deny(event + ": AF_INET/AF_INET6")
        if sock.family == socket.AF_UNIX and len(args) > 1:
            address = args[-1]
            if isinstance(address, (str, bytes)):
                address = os.fsdecode(address)
                if not address.startswith("/") or not private_path(address):
                    deny(event + ": Unix socket outside owned runtime")
    if event in {
        "socket.getaddrinfo", "socket.gethostbyname", "socket.gethostbyaddr",
        "socket.getnameinfo",
    }:
        deny(event)
    if event == "open" and args and isinstance(args[0], (str, bytes, os.PathLike)):
        path = Path(os.fsdecode(args[0])).resolve()
        if (path.name == ".env" or path.name.startswith(".env.")) and not private_path(path):
            deny("open: dotenv")
        if path.is_relative_to(SOURCE / "backend/data"):
            deny("open: backend/data")
        research = SOURCE / "backend/evaluation/research"
        if path.is_relative_to(research):
            rel = path.relative_to(SOURCE).as_posix()
            parts = path.relative_to(research).parts
            if ("data" in parts or "baseline" in parts or "artifacts" in parts) and rel not in ALLOWED_ASSETS:
                deny("open: unlisted research asset")


def guarded(method, label: str):
    def call(sock, *args, **kwargs):
        if sock.family in IP_FAMILIES:
            deny(label)
        return method(sock, *args, **kwargs)
    return call


def arm() -> None:
    if getattr(sys, "_full_backend_guard_armed", False):
        return
    sys._full_backend_guard_stage = "stdlib_audit_and_socket_guards"
    assert RUNTIME.is_dir() and RUNTIME.stat().st_mode & 0o077 == 0
    sys._full_backend_guard_armed = True
    sys.addaudithook(audit)
    atexit.register(write_state)
    for name in ("connect", "connect_ex", "sendto", "bind"):
        setattr(socket.socket, name, guarded(getattr(socket.socket, name), "socket." + name))
    for name in ("create_connection", "getaddrinfo", "gethostbyname", "gethostbyname_ex", "getnameinfo"):
        setattr(socket, name, lambda *a, _label=name, **k: deny("socket." + _label))

    STATE["app_preimported"] = any(n == "app" or n.startswith("app.") for n in sys.modules)
    if STATE["app_preimported"]:
        deny("application imported before pytest-cov starts")
    # A relocated stdin/system Python needs only the stdlib isolation layer.
    # Optional dependency imports are guarded lazily if they actually occur.
    sys._full_backend_guard_stage = "stdlib_armed_optional_import_hook"
    from guard_optional import DeferredDrivers

    sys.meta_path.insert(0, DeferredDrivers())
    STATE["startup_stage"] = "stdlib_armed_optional_drivers_deferred"
    STATE["capability_stub"] = "lazy urllib3 import only; no dependency is required for child startup"
    if "psycopg" in sys.modules:
        install_driver_guard(sys.modules["psycopg"])
    write_state()


def install_driver_guard(psycopg) -> None:
    sys._full_backend_guard_stage = "installing_psycopg_guard"
    if STATE["driver_guard_installed"]:
        return
    from psycopg.conninfo import conninfo_to_dict, make_conninfo

    native_connect = psycopg.connect
    native_class_connect = psycopg.Connection.connect.__func__

    def check(conninfo: str, kwargs: dict) -> None:
        # Python-only driver arguments are omitted solely from libpq validation;
        # every original argument is forwarded unchanged to the native connector.
        options = {k: v for k, v in kwargs.items() if k not in PYTHON_KEYS}
        value = conninfo_to_dict(make_conninfo(conninfo, **options))
        host = value.get("host", "")
        directory = Path(host).resolve() if host.startswith("/") else None
        if (
            directory is None or not private_path(directory) or not directory.is_dir()
            or directory.stat().st_mode & 0o077 or directory.stat().st_uid != os.getuid()
            or value.get("hostaddr")
            or value.get("service") or value.get("servicefile") or value.get("password")
            or value.get("passfile") not in (None, os.environ["PGPASSFILE"])
            or value.get("sslmode") not in (None, "disable")
            or value.get("port") not in (None, "5432")
            or not value.get("user")
            or not re.fullmatch(r"[A-Za-z_][A-Za-z_0-9-]*", value.get("user", ""))
            or not re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", value.get("dbname", ""))
        ):
            deny("libpq outside owned private Unix fixture")
        STATE["allowed_pg_connections"].append({k: value.get(k) for k in ("host", "dbname", "user", "port")})

    def connect(conninfo="", **kwargs):
        check(conninfo, kwargs)
        return native_connect(conninfo, **kwargs)

    def class_connect(cls, conninfo="", **kwargs):
        check(conninfo, kwargs)
        return native_class_connect(cls, conninfo, **kwargs)

    psycopg.connect = connect
    psycopg.Connection.connect = classmethod(class_connect)
    STATE["driver_guard_installed"] = True
    write_state()
