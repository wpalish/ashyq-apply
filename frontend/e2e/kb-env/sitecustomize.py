"""The network guard of the kb-mode browser journey (E2E-KB).

Python imports ``sitecustomize`` at start-up when it is on ``PYTHONPATH``;
``serve-api.sh`` puts this directory there for the API, the worker and the
migration. Every socket connection and name lookup that is not to loopback is
logged to ``$NETGUARD_LOG`` and refused, so a kb-mode run that tried to read a
page or call a search provider fails loudly instead of quietly using the
network. The spec reads the log: one ``LOADED`` line per process, and no
``BLOCKED`` line other than the start-up probe's.

The same guard the two manual smokes used (docs/process/KB_E2E_SMOKE_2026-10-19.md).
"""

import os
import socket
import sys

_LOG = os.environ.get("NETGUARD_LOG", os.devnull)
_LOCAL = ("127.0.0.1", "::1", "localhost", "0.0.0.0")


def _ok(host):
    if isinstance(host, bytes):
        host = host.decode()
    return host is None or str(host) in _LOCAL or str(host).startswith("127.")


def _write(line):
    with open(_LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def _block(what, host):
    _write(f"BLOCKED {what} {host} pid={os.getpid()}")
    raise OSError(f"netguard: blocked {what} to {host}")


_orig_connect = socket.socket.connect
_orig_connect_ex = socket.socket.connect_ex
_orig_getaddrinfo = socket.getaddrinfo


def connect(self, address):
    if self.family in (socket.AF_INET, socket.AF_INET6) and not _ok(address[0]):
        _block("connect", address)
    return _orig_connect(self, address)


def connect_ex(self, address):
    if self.family in (socket.AF_INET, socket.AF_INET6) and not _ok(address[0]):
        _block("connect_ex", address)
    return _orig_connect_ex(self, address)


def getaddrinfo(host, *args, **kwargs):
    if not _ok(host):
        _block("getaddrinfo", host)
    return _orig_getaddrinfo(host, *args, **kwargs)


def _command_line():
    # sys.argv is still ["-m"] for `python -m app.jobs.worker` at this point.
    try:
        with open("/proc/self/cmdline", "rb") as f:
            return f.read().replace(b"\0", b" ").decode(errors="replace").strip()
    except OSError:
        return " ".join(getattr(sys, "argv", []))


socket.socket.connect = connect
socket.socket.connect_ex = connect_ex
socket.getaddrinfo = getaddrinfo
_write(f"LOADED pid={os.getpid()} cmd={_command_line()[-120:]}")
