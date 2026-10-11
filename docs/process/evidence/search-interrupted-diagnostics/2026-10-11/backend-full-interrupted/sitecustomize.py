"""Inherited guard for native Python children; fail closed on startup failure."""
import json
import os
from pathlib import Path

if os.environ.get("FULL_BACKEND_ARM_GUARD") == "1":
    try:
        from guard_runtime import arm

        arm()
    except BaseException as exc:
        # CPython normally swallows sitecustomize errors. Refuse to execute user
        # code when the guard could not arm; do not print environment/payloads.
        try:
            evidence = Path(os.environ["FULL_BACKEND_EVIDENCE"])
            (evidence / f"guard-startup-failed-{os.getpid()}.json").write_text(
                json.dumps({"guard_startup_failed": True, "pid": os.getpid(),
                            "exception_type": type(exc).__name__,
                            "missing_module": getattr(exc, "name", None),
                            "stage": getattr(__import__('sys'), '_full_backend_guard_stage', 'stdlib_or_lazy_guard_startup')}) + "\n"
            )
        finally:
            os._exit(2)
