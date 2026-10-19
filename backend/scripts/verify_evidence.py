"""Evidence check for expert-drafted labels: does production read the quote?

Finish plan v2, track A (docs/process/SEARCH_FINISH_PLAN_V2.md): experts
draft the six core answers per university with a URL and a verbatim quote.
Before the owner signs anything, every quote is checked by the production
``Fetcher`` itself: the host is an official domain of that university, the
page opens under our own user agent with robots.txt honoured, and the quote is
present in the readable text word for word (whitespace and quote marks
normalised, nothing else). A row that fails stays ``unknown``; it is not
offered for signature.

Run it where the fetcher has ordinary internet access (GitHub Actions,
``verify-evidence.yml``), from ``backend``::

    python scripts/verify_evidence.py <drafts_dir> --out <report.json>

One TSV row per checked item goes to stdout: case, item, draft status, HTTP
outcome, status code, official, quote found, readable characters, URL, note.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import tempfile
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from app.adapters.extraction import pdf_to_text, readable_text
from app.adapters.fetching import Fetcher

#: Official domains per case, as given to the experts. A host is official when
#: it equals one of these or ends with ``.`` + one of these.
OFFICIAL_DOMAINS: dict[str, tuple[str, ...]] = {
    "groningen": ("rug.nl",),
    "delft": ("tudelft.nl",),
    "aalto": ("aalto.fi",),
    "vienna": ("univie.ac.at",),
    "warsaw": ("uw.edu.pl", "mimuw.edu.pl"),
    "ubc": ("ubc.ca",),
    "toronto": ("utoronto.ca",),
    "hku": ("hku.hk",),
    "ntu": ("ntu.edu.sg",),
    "kaist": ("kaist.ac.kr",),
    "nu": ("nu.edu.kz",),
    "metu": ("metu.edu.tr",),
    "sabanci": ("sabanciuniv.edu",),
    "charles": ("cuni.cz",),
    "masaryk": ("muni.cz",),
    "tum": ("tum.de",),
    "tartu": ("ut.ee",),
    "polimi": ("polimi.it",),
    "vilnius": ("vu.lt",),
    # dev2 (finish plan v2, loop 2): no curated registry entry.
    "ethz": ("ethz.ch",),
    "psaclay": ("universite-paris-saclay.fr",),
    "uppsala": ("uu.se",),
    "tcd": ("tcd.ie",),
    # Tsinghua's international undergraduate admissions run on their own host.
    "tsinghua": ("tsinghua.edu.cn", "join-tsinghua.edu.cn"),
    "tec": ("tec.mx",),
    "uba": ("uba.ar",),
    "kaznu": ("kaznu.kz",),
    "uct": ("uct.ac.za",),
    "khalifa": ("ku.ac.ae",),
    "imperial": ("imperial.ac.uk",),
    "unsw": ("unsw.edu.au",),
    "utokyo": ("u-tokyo.ac.jp",),
    "ntutw": ("ntu.edu.tw",),
    "um": ("um.edu.my",),
    "kuleuven": ("kuleuven.be",),
    "auckland": ("auckland.ac.nz",),
    "ucph": ("ku.dk",),
    "msu": ("msu.ru",),
    "iitd": ("iitd.ac.in",),
    "puc": ("uc.cl",),
    "uio": ("uio.no",),
    # USP's admissions exam is run by FUVEST, linked from USP's own pages.
    "usp": ("usp.br", "fuvest.br"),
    "ub": ("ub.edu",),
    "chula": ("chula.ac.th",),
    # dev4 (wayfinder ticket 15): country proxies for the heldout nine.
    "ctu": ("cvut.cz",),
    "vut": ("vut.cz",),
    "rwth": ("rwth-aachen.de",),
    "kit": ("kit.edu",),
    "unibo": ("unibo.it",),
    "taltech": ("taltech.ee",),
    "ktu": ("ktu.edu",),
    "boun": ("bogazici.edu.tr",),
    "itu": ("itu.edu.tr",),
    # dev5: Kazakhstan country proxy (expert drafts 2026-10-19).
    "kbtu": ("kbtu.edu.kz",),
    "satbayev": ("satbayev.university",),
    "aitu": ("astanait.edu.kz",),
    # dev5: further country proxies for the heldout nine (Italy, Lithuania).
    "unipd": ("unipd.it",),
    "sapienza": ("uniroma1.it",),
    "vilniustech": ("vilniustech.lt",),
    # dev5: Turkish country proxies for the heldout set.
    "hacettepe": ("hacettepe.edu.tr",),
    "bilkent": ("bilkent.edu.tr",),
    "ytu": ("yildiz.edu.tr",),
}

ITEMS = (
    "english",
    "gpa",
    "deadline",
    "tuition",
    "scholarship_exists",
    "scholarship_international",
)

_QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', " ": " "})


def normalise(text: str) -> str:
    """Whitespace runs to one space, typographic quotes to ASCII, NFKC."""
    text = unicodedata.normalize("NFKC", text).translate(_QUOTES)
    return re.sub(r"\s+", " ", text).strip()


_WORD = re.compile(r"[^\W_]+(?:[.,'][^\W_]+)*", re.UNICODE)


def words(text: str) -> list[str]:
    """Lower-cased word tokens; separators ("|", "•", "*", dashes, brackets) drop out.

    Experts join table cells with " | " or bullets; the page's readable text
    joins the same cells with newlines. Words and their order still have to
    match exactly, so a paraphrase or a changed figure is never accepted.
    """
    return [w.lower() for w in _WORD.findall(normalise(text))]


def quote_in(quote: str, page: str) -> bool:
    """True when the quote's words occur in the page as one contiguous run."""
    q, p = words(quote), words(page)
    if not q or len(q) > len(p):
        return False
    first = q[0]
    return any(p[i] == first and p[i : i + len(q)] == q for i in range(len(p) - len(q) + 1))


#: Words that carry no identity in a programme title.
_TITLE_STOP = frozenset(
    "a an and the of in for with to on at by from or programme program course degree "
    "bachelor bachelors bachelor's undergraduate bsc ba beng bs hons honours mod "
    "de des du la le les en et y del el los las da do di der die und im".split()
)


def title_in(title: str, page: str) -> bool:
    """Programme item only: every identity word of the expert's title is on the page.

    Experts write titles in their own words ("Licence mention Informatique
    (entry year: L1 …)"), so the title is not a verbatim quote. A bracketed
    aside is dropped, filler words are ignored, and at least two identity
    words must remain and all appear somewhere in the readable text.
    """
    core = re.sub(r"\([^)]*\)", " ", title)
    wanted = {w for w in words(core) if w not in _TITLE_STOP and len(w) > 1}
    if len(wanted) < 1:
        return False
    have = set(words(page))
    return wanted <= have


def is_official(url: str, case: str) -> bool:
    host = (urlsplit(url).hostname or "").lower()
    return any(host == d or host.endswith("." + d) for d in OFFICIAL_DOMAINS.get(case, ()))


def items(draft: dict[str, Any]) -> list[tuple[str, str, str | None, str | None]]:
    """(item, draft status, url, quote) for the programme page and six answers."""
    out: list[tuple[str, str, str | None, str | None]] = []
    programme = draft.get("programme") or {}
    if programme.get("url"):
        out.append(("programme", "known", programme.get("url"), programme.get("title")))
    answers = draft.get("answers") or {}
    for item in ITEMS:
        answer = answers.get(item) or {}
        status = str(answer.get("status") or "unknown")
        if status == "unknown":
            out.append((item, status, None, None))
            continue
        out.append((item, status, answer.get("url"), answer.get("quote")))
    return out


async def check(drafts: list[dict[str, Any]], timeout: float) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    pages: dict[str, tuple[str, int | None, str, str]] = {}
    with tempfile.TemporaryDirectory() as cache:
        async with Fetcher(Path(cache), timeout=timeout) as fetcher:
            for draft in drafts:
                case = str(draft.get("case") or "")
                for item, status, url, quote in items(draft):
                    row: dict[str, Any] = {
                        "case": case,
                        "item": item,
                        "draft_status": status,
                        "url": url,
                        "outcome": "-",
                        "status_code": None,
                        "official": None,
                        "quote_found": None,
                        "chars": 0,
                        "note": "",
                    }
                    if not url or not quote:
                        row["note"] = "no url or quote in the draft" if status != "unknown" else ""
                        rows.append(row)
                        continue
                    row["official"] = is_official(url, case)
                    if url not in pages:
                        result = await fetcher.get(url, use_cache=False)
                        if result.is_pdf and result.content:
                            text = pdf_to_text(result.content)
                        else:
                            text = readable_text(result.text) if result.text else ""
                        pages[url] = (
                            result.outcome.value,
                            result.status_code,
                            normalise(text),
                            result.error or "",
                        )
                    outcome, code, text, error = pages[url]
                    row["outcome"], row["status_code"], row["chars"] = outcome, code, len(text)
                    row["quote_found"] = bool(text) and (
                        quote_in(quote, text) or (item == "programme" and title_in(quote, text))
                    )
                    row["note"] = error[:120]
                    rows.append(row)
                    print(
                        "\t".join(
                            str(row[k])
                            for k in (
                                "case",
                                "item",
                                "draft_status",
                                "outcome",
                                "status_code",
                                "official",
                                "quote_found",
                                "chars",
                                "url",
                                "note",
                            )
                        ),
                        flush=True,
                    )
    return rows


def load(path: Path) -> list[dict[str, Any]]:
    """Expert drafts: JSON objects with a ``case``; earlier reports beside them are skipped."""
    files = sorted(path.glob("*.json")) if path.is_dir() else [path]
    drafts = [json.loads(f.read_text(encoding="utf-8")) for f in files]
    return [d for d in drafts if isinstance(d, dict) and d.get("case")]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("drafts", type=Path, help="directory of expert JSON files, or one file")
    parser.add_argument("--out", type=Path, help="write all rows as JSON here")
    parser.add_argument("--timeout", type=float, default=25.0)
    args = parser.parse_args()
    rows = asyncio.run(check(load(args.drafts), args.timeout))
    verified = [r for r in rows if r["official"] and r["quote_found"]]
    counts = Counter(r["outcome"] for r in rows if r["url"])
    print(
        f"\nchecked={sum(1 for r in rows if r['url'])}  verified={len(verified)}  "
        + "  ".join(f"{k}={v}" for k, v in sorted(counts.items()))
    )
    if args.out:
        args.out.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
