"""The scrape endpoint.

Outside `/api` on purpose: it is not part of the product's API, it is not
versioned with it, and a reverse proxy should be able to refuse `/metrics` from
the public internet with one rule.
"""

from __future__ import annotations

import hmac

from fastapi import APIRouter, HTTPException, Request, Response

from app import metrics
from app.config import get_settings

router = APIRouter(tags=["ops"], include_in_schema=False)


@router.get("/metrics")
def scrape(request: Request) -> Response:
    """Prometheus text for this process.

    Off or token-protected rather than open by default in production: the
    numbers name no applicant, but they do describe traffic and queue depth,
    which is not something to hand to anyone who asks.
    """
    settings = get_settings()
    if not settings.metrics_enabled:
        # 404, not 403. A disabled endpoint should not advertise that it exists.
        raise HTTPException(status_code=404, detail="Not found.")

    if settings.metrics_token:
        offered = request.headers.get("authorization", "")
        scheme, _, value = offered.partition(" ")
        # Constant time: the token is a shared secret, and a scraper retries
        # forever, which is exactly the budget a timing attack needs.
        if scheme.lower() != "bearer" or not hmac.compare_digest(value, settings.metrics_token):
            raise HTTPException(status_code=401, detail="Metrics require a bearer token.")

    return Response(content=metrics.render(), media_type=metrics.CONTENT_TYPE)
