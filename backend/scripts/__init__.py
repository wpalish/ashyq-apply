"""Operational scripts.

A package rather than loose files so `scripts.canary_discovery` has exactly one
module name. Without this, mypy resolved the same file as both
`canary_discovery` and `scripts.canary_discovery` — because `tests/` imports it
by the dotted path while the directory itself is on `sys.path` when a script is
run directly — and refused to check anything at all:

    error: Source file found twice under different module names

Each script stays runnable as `python scripts/<name>.py`; `__init__.py` does
not change that.
"""
