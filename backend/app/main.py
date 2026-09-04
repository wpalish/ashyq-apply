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

from app import metrics
from app.adapters.fetching import PIILeakError
from app.api import (
    routes_account,
    routes_admin,
    routes_auth,
    routes_cases,
    routes_meta,
    routes_metrics,
    routes_profile,
    routes_research,
    routes_results,
    routes_social,
)
from app.config import get_settings
from app.db import init_db
from app.jobs.worker import reconcile_startup
from app.logging_setup import configure_logging, new_correlation_id, set_correlation_id

settings = get_settings()
configure_logging(settings.log_level, settings.log_format)
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
    routes_account,
    routes_admin,
    routes_auth,
    routes_cases,
    routes_meta,
    routes_metrics,
    routes_profile,
    routes_research,
    routes_results,
    routes_social,
):
    app.include_router(module.router)


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
        self._collect(cutoff)
        return True

    #: Every distinct caller left an empty deque behind for the life of the
    #: process. One address per login attempt is a slow leak in a long-running
    #: API, so the map is swept occasionally rather than never.
    _SWEEP_EVERY = 500

    def _collect(self, cutoff: float) -> None:
        self._since_sweep = getattr(self, "_since_sweep", 0) + 1
        if self._since_sweep < self._SWEEP_EVERY:
            return
        self._since_sweep = 0
        for key, bucket in list(self.hits.items()):
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if not bucket:
                del self.hits[key]


_limiter = FixedWindowLimiter()


def client_address(request: Request) -> str:
    """The address a limit should be charged to.

    Behind a reverse proxy every request arrives from the proxy, so keying on
    the socket peer makes one limit for the whole world: a single script would
    lock every user out of login. The first hop of X-Forwarded-For is the
    caller, but only when we put the proxy there ourselves — hence the setting.
    """
    if settings.trust_proxy_headers:
        forwarded = request.headers.get("x-forwarded-for", "")
        first_hop = forwarded.split(",")[0].strip()
        if first_hop:
            return first_hop
    return request.client.host if request.client else "unknown"


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
    elif unsafe and path.startswith("/api/social/"):
        limit = settings.social_rate_limit_per_minute
        group = "social"
    else:
        limit = 0
        group = ""
    if limit:
        peer = client_address(request)
        if not _limiter.allow(f"{group}:{peer}", limit, time.monotonic()):
            metrics.count_rate_limited(group)
            return _secure(
                JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests. Try again in a minute."},
                    headers={"Retry-After": "60"},
                )
            )

    return _secure(await call_next(request))


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Time every request, including the ones refused before they reach a route.

    Declared after the security middleware so it wraps it: a 429 the limiter
    returned is a served request as far as an operator is concerned, and the
    latency of a refusal is worth seeing. Declared before the correlation
    middleware so that one stays outermost, as its own docstring requires.
    """
    started = time.perf_counter()
    response = await call_next(request)
    if request.url.path != "/metrics":
        # The route template, never the URL. `scope["route"]` is set during
        # routing, so it is present by the time the response comes back; a
        # request that matched nothing has no template and is grouped as such.
        route = request.scope.get("route")
        template = getattr(route, "path", None) or "unmatched"
        metrics.observe_request(
            request.method, template, response.status_code, time.perf_counter() - started
        )
    return response


@app.middleware("http")
async def correlation_middleware(request: Request, call_next):
    """Give every request an id, and hand it back.

    Registered last on purpose. Starlette inserts each `add_middleware` at the
    front of the stack, so the last one declared is the outermost — which is
    what a correlation id has to be, or the middleware that runs before it
    logs without one.

    An inbound `X-Request-ID` is honoured so a proxy's id survives into these
    logs, but only if it is a safe shape: it goes straight back out in a
    response header, and this codebase has already shipped one header it did
    not check.
    """
    incoming = request.headers.get("x-request-id", "")
    request_id = set_correlation_id(incoming)
    if request_id == "-":
        request_id = set_correlation_id(new_correlation_id())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(PIILeakError)
async def pii_handler(_: Request, exc: PIILeakError) -> JSONResponse:
    """A privacy violation is a server error we name explicitly, never a silent pass."""
    log.error("blocked outbound request containing applicant data")
    return JSONResponse(status_code=400, content={"detail": str(exc), "code": "pii_guard"})


# There is deliberately no global ValueError handler. One used to turn every
# ValueError raised anywhere - including ordinary bugs and UnsupportedCurrency
# from deep inside the domain - into a 400 carrying its raw text. That masked
# real 500s as client errors and handed internal detail to the caller. Routes
# where a ValueError is genuinely the user's mistake convert it themselves.


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
