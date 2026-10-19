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

From an agent sandbox whose only way out is an HTTPS proxy, add
``--trust-env-proxy``: the same fetcher (user agent, robots.txt, extraction)
then sends through ``HTTPS_PROXY`` and verifies TLS against the environment's
CA bundle. To re-check only the rows a CI report did not pass (robots.txt
refusals stay as they are), give the reports instead of a drafts directory::

    python scripts/verify_evidence.py --trust-env-proxy \\
        --recheck <batch>/evidence_check.ci-<date>.json [...]

Each writes ``evidence_check.recheck-<today>.json`` beside its report, in the
same row shape plus ``"origin": "sandbox-proxy"``.

A host's robots.txt Crawl-delay is waited out up to ``MAX_CRAWL_DELAY_WAIT``
seconds; a longer one is still not read (outcome ``robots_crawl_delay``).

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
from datetime import UTC, datetime
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
    # dev5 (2026-10-19): country proxies for the heldout set.
    "upol": ("upol.cz",),
    "zcu": ("zcu.cz",),
    "tud": ("tu-dresden.de",),
    "lmu": ("lmu.de",),
}

#: The verified knowledge base's top-100 list (owner, 2026-10-19): each row's
#: ``official_domain`` and the host of its ``official_site`` (``www.`` aside)
#: are that university's official domains, with any ``extra_domains`` (an
#: institution's second official host, e.g. ``illinois.edu``), under its
#: ``seed_id`` and, for a
#: row imported from a development corpus, its ``existing_case`` too.
KB_LIST = Path(__file__).resolve().parents[1] / "evaluation/research/data/kb_top100_list.json"


def _host(url: str | None) -> str:
    return (urlsplit(url or "").hostname or "").lower().removeprefix("www.")


def load_kb_domains(path: Path = KB_LIST) -> dict[str, tuple[str, ...]]:
    """seed_id (and existing case) -> official domains from the KB list; {} without the file."""
    try:
        rows = json.loads(path.read_text(encoding="utf-8")).get("rows") or []
    except (OSError, ValueError, AttributeError):
        return {}
    out: dict[str, tuple[str, ...]] = {}
    for row in rows:
        if not isinstance(row, dict) or not row.get("seed_id"):
            continue
        hosts = [str(row.get("official_domain") or "").lower().removeprefix("www.")]
        hosts.append(_host(row.get("official_site")))
        hosts += [str(d).lower().removeprefix("www.") for d in row.get("extra_domains") or []]
        domains = tuple(dict.fromkeys(h for h in hosts if h))
        if not domains:
            continue
        for key in (str(row["seed_id"]), str(row.get("existing_case") or "")):
            if key:
                out[key] = tuple(dict.fromkeys((*out.get(key, ()), *domains)))
    return out


KB_DOMAINS: dict[str, tuple[str, ...]] = load_kb_domains()


def official_domains(case: str, seed_id: str | None = None) -> tuple[str, ...]:
    """The case's curated domains plus the KB list's for its case id or ``seed_id``."""
    found = (*OFFICIAL_DOMAINS.get(case, ()), *KB_DOMAINS.get(case, ()))
    if seed_id:
        found = (*found, *KB_DOMAINS.get(seed_id, ()))
    return tuple(dict.fromkeys(found))


#: The longest Crawl-delay the check waits out per request to a host. The
#: product's fetcher waits at most 10 s (a run has a clock); a one-off check
#: has none, so a slower host is read, politely, instead of skipped.
MAX_CRAWL_DELAY_WAIT = 30.0
#: ``origin`` of a recheck report's rows.
RECHECK_ORIGIN = "sandbox-proxy"

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


def is_official(url: str, case: str, seed_id: str | None = None) -> bool:
    host = (urlsplit(url).hostname or "").lower()
    return any(host == d or host.endswith("." + d) for d in official_domains(case, seed_id))


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


Target = tuple[str, str, str]

_TSV = (
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


def passed(row: dict[str, Any]) -> bool:
    return row.get("official") is True and row.get("quote_found") is True


def recheck_targets(report: list[dict[str, Any]]) -> set[Target]:
    """(case, item, url) of a report's rows worth checking again.

    A row with a URL that did not pass (not official, or quote not found) is
    rechecked, unless robots.txt refused it: that refusal is final. A
    (case, item, url) that also has a passing row in the report is not.
    """
    rows = [r for r in report if isinstance(r, dict) and r.get("url")]
    done = {(str(r.get("case")), str(r.get("item")), str(r["url"])) for r in rows if passed(r)}
    out: set[Target] = set()
    for row in rows:
        if passed(row) or row.get("outcome") == "robots_disallowed":
            continue
        key = (str(row.get("case")), str(row.get("item")), str(row["url"]))
        if key not in done:
            out.add(key)
    return out


async def check(
    drafts: list[dict[str, Any]],
    timeout: float,
    *,
    trust_env_proxy: bool = False,
    only: set[Target] | None = None,
) -> list[dict[str, Any]]:
    """One row per draft item; ``only`` limits the rows to those (case, item, url)."""
    with tempfile.TemporaryDirectory() as cache:
        fetcher = Fetcher(
            Path(cache),
            timeout=timeout,
            max_crawl_delay=MAX_CRAWL_DELAY_WAIT,
            trust_env_proxy=trust_env_proxy,
        )
        async with fetcher:
            return await check_with(fetcher, drafts, only=only)


async def check_with(
    fetcher: Fetcher, drafts: list[dict[str, Any]], *, only: set[Target] | None = None
) -> list[dict[str, Any]]:
    """``check`` with an open fetcher."""
    rows: list[dict[str, Any]] = []
    pages: dict[str, tuple[str, int | None, str, str]] = {}
    checked_on = datetime.now(UTC).date().isoformat()
    for draft in drafts:
        case = str(draft.get("case") or "")
        seed_id = str(draft.get("seed_id") or "") or None
        for item, status, url, quote in items(draft):
            if only is not None and (case, item, str(url)) not in only:
                continue
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
                "checked_on": checked_on,
            }
            if seed_id:
                row["seed_id"] = seed_id
            if not url or not quote:
                row["note"] = "no url or quote in the draft" if status != "unknown" else ""
                rows.append(row)
                continue
            row["official"] = is_official(url, case, seed_id)
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
            print("\t".join(str(row[k]) for k in _TSV), flush=True)
    return rows


def load(path: Path) -> list[dict[str, Any]]:
    """Expert drafts: JSON objects with a ``case``; earlier reports beside them are skipped.

    A directory is read recursively, so a KB batch (``batchN/programme`` and
    ``batchN/core``) is checked in one run.
    """
    files = sorted(path.rglob("*.json")) if path.is_dir() else [path]
    drafts = [json.loads(f.read_text(encoding="utf-8")) for f in files]
    return [d for d in drafts if isinstance(d, dict) and d.get("case")]


def recheck_path(report: Path, day: str) -> Path:
    return report.parent / f"evidence_check.recheck-{day}.json"


async def recheck(
    report: Path, timeout: float, *, trust_env_proxy: bool = False
) -> list[dict[str, Any]]:
    """The failed rows of one report, checked again against the drafts beside it."""
    targets = recheck_targets(json.loads(report.read_text(encoding="utf-8")))
    if not targets:
        return []
    rows = await check(load(report.parent), timeout, trust_env_proxy=trust_env_proxy, only=targets)
    return [{**row, "origin": RECHECK_ORIGIN} for row in rows]


def _summary(rows: list[dict[str, Any]]) -> str:
    verified = [r for r in rows if passed(r)]
    counts = Counter(r["outcome"] for r in rows if r["url"])
    return f"checked={sum(1 for r in rows if r['url'])}  verified={len(verified)}  " + "  ".join(
        f"{k}={v}" for k, v in sorted(counts.items())
    )


def _write(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("drafts", type=Path, nargs="?", help="directory of expert JSON files")
    parser.add_argument("--out", type=Path, help="write all rows as JSON here")
    parser.add_argument("--timeout", type=float, default=25.0)
    parser.add_argument(
        "--trust-env-proxy",
        action="store_true",
        help="send through HTTPS_PROXY and verify TLS with the environment's CA bundle",
    )
    parser.add_argument(
        "--recheck",
        type=Path,
        nargs="+",
        metavar="REPORT",
        help="re-check the failed rows of these CI reports (drafts: each report's directory)",
    )
    args = parser.parse_args(argv)
    if args.recheck:
        if args.drafts or args.out:
            parser.error("--recheck takes neither a drafts directory nor --out")
        day = datetime.now(UTC).date().isoformat()
        for report in args.recheck:
            rows = asyncio.run(recheck(report, args.timeout, trust_env_proxy=args.trust_env_proxy))
            out = recheck_path(report, day)
            _write(out, rows)
            print(f"\n{report.parent.name}: {_summary(rows)} -> {out}")
        return
    if args.drafts is None:
        parser.error("give a drafts directory, or --recheck REPORT [...]")
    rows = asyncio.run(check(load(args.drafts), args.timeout, trust_env_proxy=args.trust_env_proxy))
    print("\n" + _summary(rows))
    if args.out:
        _write(args.out, rows)


if __name__ == "__main__":
    main()
