"""FastAPI application."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.adapters.fetching import PIILeakError
from app.api import routes_meta, routes_profile, routes_research, routes_results
from app.config import get_settings
from app.db import init_db
from app.pipeline.queue import queue, reconcile_orphaned_runs

settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
)
log = logging.getLogger("unimatch")


@asynccontextmanager
async def lifespan(_: FastAPI):
    import asyncio

    init_db()
    queue.bind_loop(asyncio.get_running_loop())
    recovered = reconcile_orphaned_runs()
    if recovered:
        log.warning("startup reconciliation recovered %d run(s)", len(recovered))
    log.info("UniMatch started (demo_mode=%s, robots=%s)", settings.demo_mode, settings.respect_robots)
    yield
    await queue.shutdown()


app = FastAPI(
    title="UniMatch",
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
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

for module in (routes_meta, routes_profile, routes_research, routes_results):
    app.include_router(module.router)


@app.exception_handler(PIILeakError)
async def pii_handler(_: Request, exc: PIILeakError) -> JSONResponse:
    """A privacy violation is a server error we name explicitly, never a silent pass."""
    log.error("blocked outbound request containing applicant data")
    return JSONResponse(status_code=400, content={"detail": str(exc), "code": "pii_guard"})


@app.exception_handler(ValueError)
async def value_error_handler(_: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.get("/", include_in_schema=False)
def root() -> dict:
    return {
        "name": "UniMatch",
        "docs": "/docs",
        "health": "/api/health",
        "note": "Published criteria only. This service never promises admission or funding.",
    }
