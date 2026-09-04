"""The 402 the frontend keys off.

``HTTPException`` would give us a bare ``detail``. The frontend needs to know
which case to sell and for how much, so this carries both — in the shape
``api/client.ts`` already parses: a string ``detail`` and a top-level ``code``.
"""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse


class PaymentRequired(Exception):
    """Raised by the paywall guard. Rendered as 402 by the handler below."""

    def __init__(self, profile_id: str, price_kzt: int) -> None:
        super().__init__("This case has not been unlocked.")
        self.profile_id = profile_id
        self.price_kzt = price_kzt


async def payment_required_handler(_request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, PaymentRequired)
    return JSONResponse(
        status_code=402,
        content={
            "detail": "Unlock this case to see the full report.",
            "code": "payment_required",
            "profile_id": exc.profile_id,
            "price_kzt": exc.price_kzt,
        },
    )
