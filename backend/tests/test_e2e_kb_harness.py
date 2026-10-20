"""The kb-mode E2E harness wipes only its own scratch directory (security review 2026-10-22, SR2-07).

``frontend/e2e/kb-env/serve-api.sh`` starts with ``rm -rf "$E2E_KB_DIR"``. The
variable is the operator's, so ``E2E_KB_DIR=backend/data`` (or a home
directory) would have deleted the developer's database and everything beside
it before the journey ran. Only a directory named ``e2e-kb*`` is accepted.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

SERVE_API = Path(__file__).resolve().parents[2] / "frontend/e2e/kb-env/serve-api.sh"

pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="needs bash")


@pytest.mark.parametrize("name", ["data", "keep", "e2e", "kb-e2e", ".."])
def test_a_directory_that_is_not_the_journeys_scratch_is_never_wiped(
    tmp_path: Path, name: str
) -> None:
    target = tmp_path / "inner" / name if name == ".." else tmp_path / name
    (tmp_path / "inner").mkdir(exist_ok=True)
    kept = tmp_path / "inner" / "unimatch.db" if name == ".." else target / "unimatch.db"
    kept.parent.mkdir(parents=True, exist_ok=True)
    kept.write_text("keep me")
    env = {**os.environ, "E2E_KB_DIR": str(target)}
    done = subprocess.run(
        ["bash", str(SERVE_API)], env=env, capture_output=True, text=True, timeout=60
    )
    assert done.returncode == 64, done.stderr
    assert "refusing to wipe" in done.stderr
    assert kept.read_text() == "keep me"


def test_an_unset_scratch_directory_is_refused(tmp_path: Path) -> None:
    env = {k: v for k, v in os.environ.items() if k != "E2E_KB_DIR"}
    done = subprocess.run(
        ["bash", str(SERVE_API)], env=env, capture_output=True, text=True, timeout=60
    )
    assert done.returncode != 0
    assert "E2E_KB_DIR" in done.stderr
