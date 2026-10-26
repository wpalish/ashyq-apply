"""The demo and auth E2E harness wipes only its own scratch directory (E2E-DB-1).

``frontend/e2e/demo-env/serve-api.sh`` starts with ``rm -rf "$E2E_SCRATCH_DIR"``
so that ``npm run e2e`` and ``npm run e2e:auth`` start from an empty database,
as CI does. The variable is the operator's, so only a directory named
``e2e-demo*`` or ``e2e-auth*`` directly under ``backend/data`` is accepted —
the rule ``test_e2e_kb_harness.py`` holds for the kb script.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SERVE_API = ROOT / "frontend/e2e/demo-env/serve-api.sh"

pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="needs bash")


def _run(env_dir: str | None) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k != "E2E_SCRATCH_DIR"}
    if env_dir is not None:
        env["E2E_SCRATCH_DIR"] = env_dir
    return subprocess.run(
        ["bash", str(SERVE_API)], env=env, capture_output=True, text=True, timeout=60
    )


def test_the_script_parses() -> None:
    done = subprocess.run(["bash", "-n", str(SERVE_API)], capture_output=True, text=True)
    assert done.returncode == 0, done.stderr


@pytest.mark.parametrize(
    "name", ["data", "keep", "e2e", "e2e-kb", "demo-e2e", "e2e-demo", "e2e-auth", ".."]
)
def test_a_directory_that_is_not_a_suites_scratch_is_never_wiped(tmp_path: Path, name: str) -> None:
    # e2e-demo / e2e-auth are refused here too: right name, wrong parent (not backend/data).
    (tmp_path / "inner").mkdir()
    target = tmp_path / "inner" / name if name == ".." else tmp_path / name
    kept = tmp_path / "inner" / "unimatch.db" if name == ".." else target / "unimatch.db"
    kept.parent.mkdir(parents=True, exist_ok=True)
    kept.write_text("keep me")
    done = _run(str(target))
    assert done.returncode == 64, done.stderr
    assert "refusing to wipe" in done.stderr
    assert kept.read_text() == "keep me"


def test_backend_data_itself_is_never_wiped() -> None:
    done = _run(str(ROOT / "backend/data"))
    assert done.returncode == 64, done.stderr
    assert "refusing to wipe" in done.stderr


def test_an_unset_scratch_directory_is_refused() -> None:
    done = _run(None)
    assert done.returncode != 0
    assert "E2E_SCRATCH_DIR" in done.stderr


def test_the_database_cache_and_exports_live_in_the_scratch_directory() -> None:
    script = SERVE_API.read_text()
    for line in (
        'export UNIMATCH_DATABASE_URL="sqlite:///$SCRATCH/unimatch.db"',
        'export UNIMATCH_CACHE_DIR="$SCRATCH/httpcache"',
        'export UNIMATCH_EXPORT_DIR="$SCRATCH/exports"',
    ):
        assert line in script
    # The name and parent checks come before the wipe.
    assert script.index("e2e-demo* | e2e-auth*)") < script.index('rm -rf -- "$SCRATCH"')
    assert script.index('[ "$PARENT" =') < script.index('rm -rf -- "$SCRATCH"')
