"""Currency conversion that always shows its work.

Rates are static, dated snapshots shipped with the app. That is a deliberate
limitation: a wrong-but-dated rate the user can see beats a live rate they
cannot audit. Every conversion returns the rate and the rate's date.
"""

from __future__ import annotations

from datetime import date

from app.schemas.money import ConvertedMoney, Money

RATE_SOURCE = "Static snapshot bundled with UniMatch (see app/domain/currency.py)"
RATE_DATE = date(2026, 8, 1)

#: Units of the currency per 1 USD, as of RATE_DATE.
_PER_USD: dict[str, float] = {
    "USD": 1.0,
    "EUR": 0.92,
    "GBP": 0.78,
    "CAD": 1.36,
    "AUD": 1.50,
    "CHF": 0.88,
    "SEK": 10.60,
    "NOK": 10.70,
    "DKK": 6.85,
    "PLN": 3.95,
    "CZK": 23.10,
    "HUF": 355.0,
    "TRY": 34.0,
    "AED": 3.67,
    "SGD": 1.34,
    "HKD": 7.82,
    "JPY": 152.0,
    "KRW": 1340.0,
    "CNY": 7.16,
    "KZT": 480.0,
    "RUB": 92.0,
    "INR": 83.5,
    "MYR": 4.55,
    "NZD": 1.63,
    "ZAR": 18.4,
    "BRL": 5.35,
    "MXN": 18.0,
    "ILS": 3.70,
    "SAR": 3.75,
    "QAR": 3.64,
}


class UnsupportedCurrency(ValueError):
    """Raised instead of guessing a rate."""


def supported_currencies() -> list[str]:
    return sorted(_PER_USD)


def rate(from_currency: str, to_currency: str) -> float:
    src, dst = from_currency.upper(), to_currency.upper()
    for code in (src, dst):
        if code not in _PER_USD:
            raise UnsupportedCurrency(
                f"No bundled rate for {code}. Add one to app/domain/currency.py "
                f"or keep the amount in its original currency."
            )
    return _PER_USD[dst] / _PER_USD[src]


def convert(money: Money, to_currency: str) -> ConvertedMoney | Money:
    """Convert, preserving the original amount, the rate and the rate date.

    Returns the input untouched when the currency already matches, so callers
    never see a spurious ``rate=1.0`` conversion record.
    """
    dst = to_currency.upper()
    if money.currency.upper() == dst:
        return money
    r = rate(money.currency, dst)
    return ConvertedMoney(
        amount=round(money.amount * r, 2),
        currency=dst,
        academic_year=money.academic_year,
        as_of=money.as_of,
        is_estimate=money.is_estimate,
        range_low=round(money.range_low * r, 2) if money.range_low is not None else None,
        range_high=round(money.range_high * r, 2) if money.range_high is not None else None,
        source_url=money.source_url,
        original_amount=money.amount,
        original_currency=money.currency.upper(),
        rate=r,
        rate_date=RATE_DATE,
        rate_source=RATE_SOURCE,
    )
