"""Money that refuses to be compared across incompatible contexts."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class Money(BaseModel):
    """An amount, its currency, and the academic year it describes.

    Two Money values from different academic years are *not* interchangeable.
    ``app.domain.costs`` refuses to net them into a clean zero and downgrades
    the result instead.
    """

    model_config = ConfigDict(extra="forbid")

    amount: float = Field(ge=0)
    currency: Annotated[str, Field(min_length=3, max_length=3)] = "USD"
    academic_year: str | None = None
    as_of: date | None = None
    is_estimate: bool = False
    range_low: float | None = Field(default=None, ge=0)
    range_high: float | None = Field(default=None, ge=0)
    source_url: str | None = None

    def __str__(self) -> str:  # pragma: no cover - display helper
        year = f" ({self.academic_year})" if self.academic_year else ""
        return f"{self.amount:,.0f} {self.currency}{year}"


class ConvertedMoney(Money):
    """A Money value restated in another currency, with the rate exposed."""

    original_amount: float
    original_currency: str
    rate: float
    rate_date: date
    rate_source: str
