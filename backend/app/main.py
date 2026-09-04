"""FastAPI application."""

from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.adapters.fetching import PIILeakError
from app.api import (
    routes_auth,
    routes_billing,
    routes_cases,
    routes_meta,
    routes_profile,
    routes_research,
    routes_results,
)
from app.config import get_settings
from app.db import init_db
from app.jobs.worker import reconcile_startup
from app.payments.http import PaymentRequired, payment_required_handler

settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
)
log = logging.getLogger("unimatch")


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Prepare the database and reconcile anything a crash left behind.

    The API does not run jobs. It enqueues them and reports on them; a separate
    worker process consumes the queue, so restarting the API cannot lose work
    and deploying the two is independent.
    """
    settings.validate_runtime()
    init_db()
    summary = reconcile_startup()
    if any(summary.values()):
        log.warning("startup reconciliation: %s", summary)
    log.info(
        "ASHYQ Apply API started (env=%s, demo_mode=%s, robots=%s, db=%s)",
        settings.environment,
        settings.demo_mode,
        settings.respect_robots,
        "postgresql" if settings.is_postgres else "sqlite",
    )
    yield


app = FastAPI(
    title="ASHYQ Apply",
    version="0.1.0",
    summary="University and scholarship matching for international applicants, with a source for every claim.",
    description=(
        "Every material value in a result traces to a claim carrying its URL, excerpt and the "
        "date it was read. The service reports published criteria only; it does not predict "
        "admission or funding outcomes."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

for module in (
    routes_auth,
    routes_billing,
    routes_cases,
    routes_meta,
    routes_profile,
    routes_research,
    routes_results,
):
    app.include_router(module.router)

# A gated route raises PaymentRequired; this renders it as the 402 the frontend
# recognises, carrying which case to sell and for how much.
app.add_exception_handler(PaymentRequired, payment_required_handler)


class FixedWindowLimiter:
    """A small per-process shield for login and expensive enqueue endpoints.

    It is intentionally not sold as billing-grade distributed quota. Every API
    process still enforces the bound, while the database remains the authority
    for job idempotency and concurrency.
    """

    def __init__(self) -> None:
        self.hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, limit: int, now: float) -> bool:
        bucket = self.hits[key]
        cutoff = now - 60.0
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
        if len(bucket) >= limit:
            return False
        bucket.append(now)
        return True


_limiter = FixedWindowLimiter()


def _secure(response: Response) -> Response:
    """Apply the browser security policy to every response, including early refusals."""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; base-uri 'none'; frame-ancestors 'none'; object-src 'none'; "
        "img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; "
        "connect-src 'self'"
    )
    if settings.is_production and settings.cookie_secure:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    """Headers, same-site request checks and narrow abuse limits."""
    unsafe = request.method in {"POST", "PUT", "PATCH", "DELETE"}
    if settings.auth_enabled and unsafe:
        # SameSite=Strict is the primary CSRF control. These headers add a
        # second browser-level barrier without breaking CLI clients.
        if request.headers.get("sec-fetch-site", "").lower() == "cross-site":
            return _secure(
                JSONResponse(status_code=403, content={"detail": "Cross-site request refused."})
            )
        origin = request.headers.get("origin")
        if origin and origin not in settings.cors_origin_list:
            return _secure(
                JSONResponse(status_code=403, content={"detail": "Untrusted request origin."})
            )

    path = request.url.path
    if request.method == "POST" and path in {"/api/auth/login", "/api/auth/register"}:
        limit = settings.auth_rate_limit_per_minute
        group = "auth"
    elif request.method == "POST" and path == "/api/runs":
        limit = settings.run_rate_limit_per_minute
        group = "research"
    else:
        limit = 0
        group = ""
    if limit:
        peer = request.client.host if request.client else "unknown"
        if not _limiter.allow(f"{group}:{peer}", limit, time.monotonic()):
            return _secure(
                JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests. Try again in a minute."},
                    headers={"Retry-After": "60"},
                )
            )

    return _secure(await call_next(request))


@app.exception_handler(PIILeakError)
async def pii_handler(_: Request, exc: PIILeakError) -> JSONResponse:
    """A privacy violation is a server error we name explicitly, never a silent pass."""
    log.error("blocked outbound request containing applicant data")
    return JSONResponse(status_code=400, content={"detail": str(exc), "code": "pii_guard"})


@app.exception_handler(ValueError)
async def value_error_handler(_: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


if settings.frontend_dir and settings.frontend_dir.is_dir():
    app.mount("/", StaticFiles(directory=settings.frontend_dir, html=True), name="frontend")
else:

    @app.get("/", include_in_schema=False)
    def root() -> dict:
        return {
            "name": "ASHYQ Apply",
            "docs": "/docs",
            "health": "/api/health",
            "note": "Published criteria only. This service never promises admission or funding.",
        }
