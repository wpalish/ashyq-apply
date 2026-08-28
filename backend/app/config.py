"""Runtime configuration. No secrets are required to run the product."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="UNIMATCH_", env_file=".env", extra="ignore")

    #: Demo mode uses the bundled synthetic corpus and never touches the network.
    demo_mode: bool = True
    #: Environment. Production refuses several unsafe defaults outright.
    environment: str = "development"
    #: Applying migrations on startup is off by default. Two processes starting
    #: together would otherwise both try to migrate — which on SQLite deadlocks
    #: and on PostgreSQL races. Migrating is a deliberate step: `run.sh` and the
    #: compose stack do it once, before anything else starts.
    auto_migrate: bool = False
    database_url: str = f"sqlite:///{BACKEND_ROOT / 'data' / 'unimatch.db'}"
    cache_dir: Path = BACKEND_ROOT / "data" / "httpcache"
    export_dir: Path = BACKEND_ROOT / "data" / "exports"
    corpus_dir: Path = BACKEND_ROOT / "app" / "corpus" / "pages"

    #: Politeness. Lower these only with a good reason.
    fetch_delay_seconds: float = 1.5
    respect_robots: bool = True
    fetch_timeout_seconds: float = 20.0
    cache_ttl_seconds: int = 86_400
    #: Sent in the User-Agent so site operators can reach a human.
    fetch_contact: str = ""

    enable_browser_tier: bool = True
    candidate_limit: int = 40
    verify_limit: int = 20
    academic_year: str = "2026/27"
    target_currency: str = "USD"

    #: Worker
    worker_concurrency: int = 2
    worker_poll_seconds: float = 1.0
    job_lease_seconds: int = 120

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    log_level: str = "INFO"

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in ("production", "prod")

    @property
    def is_postgres(self) -> bool:
        return self.database_url.startswith(("postgresql", "postgres"))

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def ensure_dirs(self) -> None:
        for d in (self.cache_dir, self.export_dir, Path(self.database_url.replace("sqlite:///", "")).parent):
            d.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.ensure_dirs()
    return s
