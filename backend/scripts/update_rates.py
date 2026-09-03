"""Refresh the bundled exchange-rate snapshot — by hand, on purpose.

    python scripts/update_rates.py                 # show the diff
    python scripts/update_rates.py --print-block   # emit the block to paste

The rates in app/domain/currency.py are static and dated because a wrong rate
the user can see beats a live rate they cannot audit (see the module docstring).
This script does not write the file: it fetches, prints the difference, and
prints a ready block for a human to paste, so the source and the date land in
the pull request alongside the numbers.

Source: the European Central Bank's daily reference rates, published openly and
without a key. EUR-based, so everything is rebased onto USD here.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

try:  # A hostile feed could otherwise expand into a billion-laughs bomb.
    from defusedxml import ElementTree as ET
except ModuleNotFoundError:  # pragma: no cover - optional developer extra
    import xml.etree.ElementTree as ET

    print(
        "note: defusedxml is not installed, parsing with the stdlib instead.\n"
        "      pip install defusedxml if you want the hardened parser.",
        file=sys.stderr,
    )

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.domain.currency import _PER_USD, RATE_DATE

ECB_DAILY = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
NAMESPACES = {
    "gesmes": "http://www.gesmes.org/xml/2002-08-01",
    "ecb": "http://www.ecb.int/vocabulary/2002-08-01/eurofxref",
}


def fetch_ecb_rates() -> tuple[date, dict[str, float]]:
    """Rates per 1 EUR, plus the date the ECB published them."""
    response = httpx.get(ECB_DAILY, timeout=30.0, follow_redirects=True)
    response.raise_for_status()
    root = ET.fromstring(response.text)
    cube = root.find(".//ecb:Cube/ecb:Cube", NAMESPACES)
    if cube is None:
        raise SystemExit("The ECB feed did not contain a dated Cube element.")
    published = date.fromisoformat(cube.attrib["time"])
    per_eur = {"EUR": 1.0}
    for entry in cube.findall("ecb:Cube", NAMESPACES):
        per_eur[entry.attrib["currency"]] = float(entry.attrib["rate"])
    return published, per_eur


def rebase_to_usd(per_eur: dict[str, float]) -> dict[str, float]:
    if "USD" not in per_eur:
        raise SystemExit("The ECB feed carried no USD rate; cannot rebase.")
    usd_per_eur = per_eur["USD"]
    return {code: value / usd_per_eur for code, value in per_eur.items()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--print-block", action="store_true", help="emit the _PER_USD block")
    args = parser.parse_args()

    published, per_eur = fetch_ecb_rates()
    fresh = rebase_to_usd(per_eur)

    missing = sorted(set(_PER_USD) - set(fresh) - {"USD"})
    print(f"bundled snapshot: {RATE_DATE}   ECB feed: {published}")
    print(
        f"currencies in the bundle: {len(_PER_USD)}   present in the feed: "
        f"{len(set(_PER_USD) & set(fresh))}"
    )
    if missing:
        print(f"NOT in the ECB feed, keep the bundled value: {', '.join(missing)}")

    print("\ncode    bundled        fresh     change")
    for code in sorted(_PER_USD):
        if code not in fresh:
            continue
        old, new = _PER_USD[code], fresh[code]
        drift = (new - old) / old * 100 if old else 0.0
        flag = "  <-- >5%" if abs(drift) > 5 else ""
        print(f"{code:<6} {old:>10.4f} {new:>12.4f} {drift:>+8.1f}%{flag}")

    if args.print_block:
        print(
            f"\n#: Units of the currency per 1 USD, as of RATE_DATE.\nRATE_DATE = date({published.year}, {published.month}, {published.day})"
        )
        print("_PER_USD: dict[str, float] = {")
        for code in sorted(_PER_USD):
            value = fresh.get(code, _PER_USD[code])
            source = "" if code in fresh else "  # kept: not in the ECB feed"
            print(f'    "{code}": {round(value, 4)},{source}')
        print("}")
        print(f"\n# Source: ECB daily reference rates, {published.isoformat()}, {ECB_DAILY}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
