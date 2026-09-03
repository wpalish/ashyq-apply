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
    #: Optional built frontend. Set by the single-image deployment; local Vite
    #: development leaves it unset.
    frontend_dir: Path | None = None

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

    #: Authentication is deliberately opt-in for the zero-friction local demo,
    #: and mandatory in a production environment.  Sessions are opaque,
    #: server-side records; no applicant data is placed in a browser token.
    auth_enabled: bool = False
    auth_registration_enabled: bool = True
    session_cookie_name: str = "unimatch_session"
    session_ttl_hours: int = 24 * 7
    cookie_secure: bool = False
    auth_rate_limit_per_minute: int = 10
    run_rate_limit_per_minute: int = 20
    #: Whether X-Forwarded-For may be believed. True only when something we
    #: control terminates the connection and rewrites the header (nginx in the
    #: compose stack, Fly's edge). Believing it on a directly exposed port
    #: would let any client invent an address and walk around the limiter.
    trust_proxy_headers: bool = False

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
        directories = [self.cache_dir, self.export_dir]
        if self.database_url.startswith("sqlite:///"):
            directories.append(Path(self.database_url.removeprefix("sqlite:///")).parent)
        for d in directories:
            d.mkdir(parents=True, exist_ok=True)

    def validate_runtime(self) -> None:
        """Reject configurations that would expose applicant data unsafely."""
        if self.is_production and not self.auth_enabled:
            raise RuntimeError(
                "UNIMATCH_AUTH_ENABLED must be true in production; refusing to expose "
                "applicant profiles without authentication."
            )
        if self.is_production and not self.cookie_secure:
            raise RuntimeError(
                "UNIMATCH_COOKIE_SECURE must be true in production; refusing to send a session "
                "cookie over a connection the browser may treat as insecure."
            )
        if self.is_production and not self.is_postgres:
            raise RuntimeError(
                "Production requires PostgreSQL for durable multi-process jobs and tenant data."
            )
        if self.is_production and (
            not self.cors_origin_list
            or "*" in self.cors_origin_list
            or any(not origin.startswith("https://") for origin in self.cors_origin_list)
        ):
            raise RuntimeError(
                "Production CORS origins must be an explicit, non-empty list of HTTPS origins."
            )
        if self.session_ttl_hours < 1 or self.session_ttl_hours > 24 * 30:
            raise RuntimeError("UNIMATCH_SESSION_TTL_HOURS must be between 1 and 720.")


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.ensure_dirs()
    return s
