"""Runtime configuration. No secrets are required to run the product."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parent.parent

#: A webhook secret shorter than this is not a secret. ApiPay issues long
#: ones; a short value is a placeholder somebody meant to replace.
MIN_WEBHOOK_SECRET_CHARS = 16


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

    #: 2 ranks with the non-compensatory geometric mean and the portfolio
    #: buckets; 1 restores the v1 additive score, byte for byte, so a bad
    #: release can be rolled back without a migration.
    ranking_version: int = 2
    #: How hard an unverified row is discounted: sort_key = fit * coverage**y.
    ranking_gamma: float = 0.5

    #: Worker
    worker_concurrency: int = 2
    worker_poll_seconds: float = 1.0
    job_lease_seconds: int = 120

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    log_level: str = "INFO"
    #: "text" for a person reading a terminal, "json" for anything that parses
    #: logs. Production wants json; the default stays readable so development
    #: does not pay for a machine that is not there.
    log_format: str = "text"

    #: Authentication is deliberately opt-in for the zero-friction local demo,
    #: and mandatory in a production environment.  Sessions are opaque,
    #: server-side records; no applicant data is placed in a browser token.
    auth_enabled: bool = False
    auth_registration_enabled: bool = True
    session_cookie_name: str = "unimatch_session"
    session_ttl_hours: int = 24 * 7
    cookie_secure: bool = False
    #: A person has a laptop, a phone and a work machine; twenty covers that
    #: with room to spare. Past it the oldest session is revoked rather than
    #: letting them accumulate for years.
    max_sessions_per_user: int = 20
    #: scrypt cost as a power of two. 17 is ~1s of CPU per hash, which is the
    #: production value; the test suite lowers it because hashing a hundred
    #: throwaway passwords at full cost buys nothing.
    password_scrypt_log2: int = 17
    #: Public origin of the frontend, used to build links a person clicks from
    #: their email. HTTPS in production, where startup refuses anything else.
    public_base_url: str = "http://127.0.0.1:5173"
    #: Password reset. The link is single-use and short-lived on purpose.
    password_reset_ttl_minutes: int = 60
    #: Where reset links are sent. "console" logs them (development and the
    #: demo); "smtp" uses the settings below. There is no third option, and
    #: production refuses to start on "console".
    email_sender: str = "console"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    #: SecretStr like every other credential here: a plain str renders itself
    #: in any settings dump, repr or traceback frame that carries the object.
    smtp_password: SecretStr = SecretStr("")
    smtp_from: str = "no-reply@ashyq.example"
    #: Recorded on the user, never enforced while this is false: there is no
    #: verification flow yet, and pretending otherwise would be theatre.
    auth_require_verified_email: bool = False
    auth_rate_limit_per_minute: int = 10
    run_rate_limit_per_minute: int = 20
    #: Parsing a transcript is the most expensive thing an authenticated caller
    #: can ask for: ten megabytes of PDF through pypdf, on a worker thread.
    #: Nobody uploads their transcript six times a minute by hand.
    upload_rate_limit_per_minute: int = 6
    #: Posting writes content other people read, so it gets its own bound.
    #: Generous enough for a real conversation, narrow enough that a script
    #: cannot fill the feed.
    social_rate_limit_per_minute: int = 30
    #: Whether X-Forwarded-For may be believed. True only when something we
    #: control terminates the connection and rewrites the header (nginx in the
    #: compose stack, Fly's edge). Believing it on a directly exposed port
    #: would let any client invent an address and walk around the limiter.
    trust_proxy_headers: bool = False

    #: Who may read the moderation queue and act on it, as a comma-separated
    #: list of account emails.
    #:
    #: Deliberately not a role in the database. A workspace owner is the admin
    #: of their own tenant, and the community is not theirs — it spans every
    #: workspace — so tenant roles cannot grant this. A setting the deployment
    #: operator edits is crude, but it puts the decision where it belongs and
    #: needs no table, no grant flow and no way for one applicant to make
    #: themselves a moderator. A real deployment with more than a handful of
    #: moderators should replace it.
    moderator_emails: str = ""

    #: `/metrics` for a Prometheus scraper. It carries no applicant data, only
    #: aggregates, but traffic and queue depth are still not public facts:
    #: production must either set a token or switch the endpoint off.
    metrics_enabled: bool = True
    metrics_token: str = ""

    #: Payments are off until a merchant account exists. With this false the
    #: product behaves exactly as it did before payments were written: no
    #: paywall, no truncation, every case fully open.
    payments_enabled: bool = False
    #: "fake" drives the tests and local development; "apipay" talks to Kaspi.
    payments_provider: str = "fake"
    apipay_base_url: str = "https://api.apipay.kz/api/v1"
    apipay_api_key: SecretStr = SecretStr("")
    apipay_webhook_secret: SecretStr = SecretStr("")
    apipay_timeout_seconds: float = 20.0
    #: Whole tenge. The server is the only authority on what a case costs.
    case_unlock_price_kzt: int = 4990
    #: What an unpaid case is allowed to spend, and to show.
    free_candidate_limit: int = 5
    free_shortlist_rows: int = 5

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in ("production", "prod")

    @property
    def is_postgres(self) -> bool:
        return self.database_url.startswith(("postgresql", "postgres"))

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def moderator_email_list(self) -> list[str]:
        return [e.strip().casefold() for e in self.moderator_emails.split(",") if e.strip()]

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
        if self.is_production and self.email_sender == "console":
            raise RuntimeError(
                "UNIMATCH_EMAIL_SENDER=console only logs reset links. Configure SMTP before "
                "running in production, or password reset silently does nothing."
            )
        if self.email_sender == "smtp" and not self.smtp_host:
            raise RuntimeError("UNIMATCH_SMTP_HOST is required when the sender is smtp.")
        if self.is_production and not self.public_base_url.startswith("https://"):
            raise RuntimeError("UNIMATCH_PUBLIC_BASE_URL must be an HTTPS origin in production.")
        if self.is_production and self.password_scrypt_log2 < 17:
            raise RuntimeError("Production password hashing must use at least scrypt 2**17.")
        if self.is_production and self.metrics_enabled and not self.metrics_token:
            raise RuntimeError(
                "UNIMATCH_METRICS_TOKEN must be set in production, or set "
                "UNIMATCH_METRICS_ENABLED=false. An open /metrics publishes traffic volumes "
                "and queue depth to anyone who asks."
            )
        if self.payments_enabled:
            self._validate_payments()

    def _validate_payments(self) -> None:
        """Refuse to take money through a provider that cannot verify a callback.

        The webhook is the only unauthenticated write endpoint in the service
        and the only thing that unlocks a paid case, so its signature is the
        whole boundary. Two ways it used to be no boundary at all:

        * ``payments_provider`` still on its default ``fake`` in production —
          the test double, which invents invoices nobody paid for;
        * ``apipay_webhook_secret`` unset — verification against an empty key,
          which anybody can reproduce.

        Both now stop the process at startup rather than at the first forged
        callback.
        """
        secret = self.apipay_webhook_secret.get_secret_value()
        if self.payments_provider not in ("apipay", "fake"):
            raise RuntimeError(
                f"UNIMATCH_PAYMENTS_PROVIDER={self.payments_provider!r} is not a payment "
                "provider this build knows. Use 'apipay', or 'fake' outside production."
            )
        if self.is_production and self.payments_provider != "apipay":
            raise RuntimeError(
                "UNIMATCH_PAYMENTS_PROVIDER must be 'apipay' when payments are enabled in "
                "production. The 'fake' provider is a test double: it issues invoices nobody "
                "paid and would unlock every case."
            )
        if not secret:
            raise RuntimeError(
                "UNIMATCH_APIPAY_WEBHOOK_SECRET must be set when payments are enabled. "
                "Without it the payment callback cannot be verified, and anyone who can "
                "reach /webhooks/apipay can mark an order paid."
            )
        if self.is_production and len(secret) < MIN_WEBHOOK_SECRET_CHARS:
            raise RuntimeError(
                "UNIMATCH_APIPAY_WEBHOOK_SECRET must be at least "
                f"{MIN_WEBHOOK_SECRET_CHARS} characters. It is the only thing standing "
                "between a stranger and a free unlock."
            )
        if self.is_production and not self.apipay_api_key.get_secret_value():
            raise RuntimeError(
                "UNIMATCH_APIPAY_API_KEY must be set when payments are enabled in production."
            )


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.ensure_dirs()
    return s
