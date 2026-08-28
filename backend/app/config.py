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

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    log_level: str = "INFO"

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
