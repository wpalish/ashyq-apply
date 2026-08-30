"""What each process writes must match what the container lets it write.

The first real container run failed here. `docker-compose.yml` gives the API
`read_only: true` with a tmpfs on `/tmp` and nothing else, while
`get_settings()` called `ensure_dirs()` at import and tried to create
`/app/data/httpcache` and `/app/data/exports`. The API container never became
healthy, and compose stopped with:

    dependency failed to start: container ...-api-1 is unhealthy

Reproduced locally without Docker by pointing those directories at a mode-500
path:

    PermissionError: [Errno 13] Permission denied: '.../httpcache'

Two facts made the eager mkdir pointless as well as fatal. `export_dir` is
never written to by any production code — exports are streamed from memory with
a Content-Disposition header — and `cache_dir` belongs to the research
pipeline, which runs in the worker. The API was crashing to create two
directories it does not use.

A static check is not enough on its own, but it is what stops this returning:
these tests fail when the declared writable paths and the compose file
disagree.
"""
from __future__ import annotations

import stat
from pathlib import Path

import pytest
import yaml

from app.config import Settings, get_settings

COMPOSE = Path(__file__).resolve().parent.parent.parent / "docker-compose.yml"


@pytest.fixture(scope="module")
def compose() -> dict:
    if not COMPOSE.exists():
        pytest.skip("no docker-compose.yml")
    return yaml.safe_load(COMPOSE.read_text())


class TestLoadingSettingsNeedsNoWritableDisk:
    def test_settings_load_on_a_read_only_filesystem(self, tmp_path: Path):
        """The exact container failure, without a container.

        An API process must be able to start with nothing writable but /tmp.
        Creating directories at import made that impossible.
        """
        readonly = tmp_path / "ro"
        readonly.mkdir()
        readonly.chmod(stat.S_IRUSR | stat.S_IXUSR)
        try:
            settings = Settings(
                cache_dir=readonly / "httpcache",
                export_dir=readonly / "exports",
                database_url="postgresql://user@host/db",
            )
            # Must not raise. Reading configuration is not writing to disk.
            assert settings.cache_dir.name == "httpcache"
        finally:
            readonly.chmod(stat.S_IRWXU)

    def test_get_settings_does_not_create_directories(self, tmp_path, monkeypatch):
        monkeypatch.setenv("UNIMATCH_CACHE_DIR", str(tmp_path / "never" / "httpcache"))
        monkeypatch.setenv("UNIMATCH_EXPORT_DIR", str(tmp_path / "never" / "exports"))
        monkeypatch.setenv("UNIMATCH_DATABASE_URL", "postgresql://user@host/db")
        get_settings.cache_clear()
        try:
            get_settings()
            assert not (tmp_path / "never").exists(), (
                "importing configuration created directories on disk"
            )
        finally:
            get_settings.cache_clear()


class TestTheWriterCreatesItsOwnDirectory:
    def test_the_http_cache_creates_its_root_when_it_is_built(self, tmp_path: Path):
        """Removing the eager mkdir is only safe because the component that
        writes creates what it needs, at the point it needs it."""
        from app.adapters.fetching import ResponseCache

        root = tmp_path / "deep" / "httpcache"
        ResponseCache(root)
        assert root.is_dir()

    def test_a_sqlite_parent_directory_is_created_before_use(self, tmp_path: Path):
        """SQLAlchemy will not create it, and a fresh checkout has no data/."""
        from app.db import ensure_database_parent

        target = tmp_path / "fresh" / "unimatch.db"
        ensure_database_parent(f"sqlite:///{target}")
        assert target.parent.is_dir()

    def test_ensuring_a_parent_is_harmless_for_postgres(self):
        from app.db import ensure_database_parent

        ensure_database_parent("postgresql://user@host/db")


class TestComposeAgreesWithWhatEachProcessWrites:
    @staticmethod
    def _writable_mounts(service: dict) -> list[str]:
        """Paths this service may write to, from tmpfs and volume mounts."""
        mounts = [str(t).split(":")[0] for t in (service.get("tmpfs") or [])]
        for volume in service.get("volumes") or []:
            text = volume if isinstance(volume, str) else volume.get("target", "")
            parts = text.split(":")
            if len(parts) >= 2 and ":ro" not in text:
                mounts.append(parts[1])
        return mounts

    @pytest.mark.parametrize("role", ["api", "worker"])
    def test_every_declared_writable_path_is_mounted(self, compose: dict, role: str):
        """The check that would have caught this before CI did.

        For a service with a read-only root filesystem, every directory the
        role writes to must fall under a tmpfs or a volume. Nothing else may.
        """
        service = compose["services"][role]
        # Not skipped when the root filesystem is writable. The check still
        # means something: a path that is written but not mounted is lost on
        # every restart, which for the worker's HTTP cache is a slow, silent
        # regression rather than a crash.
        mounts = self._writable_mounts(service)
        for path in Settings.container_writable_paths(role):
            assert any(
                path == mount or path.startswith(mount.rstrip("/") + "/")
                for mount in mounts
            ), f"{role} writes {path} but compose mounts only {mounts}"

    def test_the_api_declares_no_data_directory(self):
        """It writes neither: exports are streamed from memory and the HTTP
        cache belongs to the pipeline, which runs in the worker."""
        assert not [
            p for p in Settings.container_writable_paths("api") if p.startswith("/app/data")
        ]

    def test_the_worker_declares_its_cache(self):
        assert any(
            p.startswith("/app/data") for p in Settings.container_writable_paths("worker")
        )

    def test_the_api_root_filesystem_is_still_read_only(self, compose: dict):
        """The point of the exercise. A green test bought by deleting
        `read_only` would be worth nothing."""
        assert compose["services"]["api"]["read_only"] is True

    def test_an_unknown_role_is_refused_rather_than_silently_empty(self):
        """Returning () for a typo would make this whole check vacuous."""
        with pytest.raises(KeyError):
            Settings.container_writable_paths("aip")
