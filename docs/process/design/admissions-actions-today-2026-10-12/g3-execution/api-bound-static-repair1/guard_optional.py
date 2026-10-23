"""Lazy guards for optional dependencies; safe for stdlib-only Python children."""
from __future__ import annotations

import socket
import sys


class DeferredLoader:
    def __init__(self, loader, name: str):
        self.loader = loader
        self.name = name

    def create_module(self, spec):
        create = getattr(self.loader, 'create_module', None)
        return create(spec) if create else None

    def exec_module(self, module):
        from guard_runtime import STATE, install_driver_guard, write_state

        if self.name == 'urllib3':
            original = socket.has_ipv6
            socket.has_ipv6 = False
            try:
                self.loader.exec_module(module)
            finally:
                socket.has_ipv6 = original
                STATE['ipv6_trait_restored'] = socket.has_ipv6 is original
                write_state()
        else:
            self.loader.exec_module(module)
            install_driver_guard(module)

    def __getattr__(self, name):
        return getattr(self.loader, name)


class DeferredDrivers:
    def find_spec(self, fullname, path=None, target=None):
        if fullname not in {'psycopg', 'urllib3'}:
            return None
        for finder in sys.meta_path:
            if finder is self:
                continue
            find = getattr(finder, 'find_spec', None)
            if find is None:
                continue
            spec = find(fullname, path, target)
            if spec is not None:
                if spec.loader is not None and hasattr(spec.loader, 'exec_module'):
                    spec.loader = DeferredLoader(spec.loader, fullname)
                return spec
        return None
