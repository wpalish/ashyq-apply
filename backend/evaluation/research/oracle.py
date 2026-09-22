"""Fetch the certified source of each fact directly, and ask whether we can read it.

`claim_recall` has reported 0/62 for four runs and has never said which of two
very different things is wrong: the pipeline never reaches the page, or it
reaches it and cannot read it. Every fix so far has been aimed at a guess.

The certified corpus is the oracle. Seventy-three of its labels carry an exact
source URL and a human-reviewed verbatim excerpt. This module fetches those URLs
**directly, with no discovery at all**, runs the real classifier and the real
extractors, and files one verdict per fact. Removing discovery from the question
by construction is the whole point: what is left is readability.

Evaluation only. Production never reads ground truth, and this module is never
imported from ``app``. Live by explicit opt-in, as the search probe is; the
offline tests drive it through ``fixture://`` pages.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

from .mapping import normalize_claim
from .schema import Dataset

#: What happened to one certified fact when we read its own source page.
RECOVERED = "recovered"
VALUE_MISSING = "value_missing"
TEXT_MISSING = "text_missing"
FETCH_FAILED = "fetch_failed"

#: Words carry the meaning; punctuation and casing differ between a reviewer's
#: excerpt and the page's own rendering, and a table's cells may be joined with
#: different whitespace. Comparing word sequences is strict enough to prove the
#: text is present and loose enough not to fail on a non-breaking space.
_WORD = re.compile(r"\w+", re.UNICODE)


@dataclass(frozen=True, slots=True)
class Target:
    """One certified fact, and the page its reviewer read it from."""

    case_id: str
    key: str
    value: object
    url: str
    excerpt: str


@dataclass(frozen=True, slots=True)
class Finding:
    case_id: str
    key: str
    url: str
    verdict: str
    detail: str = ""

    def line(self) -> str:
        return f"{self.case_id:11} {self.key:28} {self.verdict:14} {self.detail}"


def targets(dataset: Dataset) -> list[Target]:
    """Every certified fact that names the page it was read from."""
    found: list[Target] = []
    for case in dataset.cases:
        for label in case.labels:
            for evidence in label.evidence or []:
                url = str(evidence.url)
                if not url.startswith(("http://", "https://", "fixture://")):
                    continue
                found.append(
                    Target(
                        case_id=case.id,
                        key=label.key,
                        value=label.value,
                        url=url,
                        excerpt=evidence.excerpt or "",
                    )
                )
    return found


def _words(text: str) -> list[str]:
    return [w.casefold() for w in _WORD.findall(text or "")]


def excerpt_is_present(excerpt: str, text: str) -> bool:
    """Whether the reviewer's quoted words still appear, in order, in our text.

    Not a substring test: the reviewer joined table cells with spaces, and a
    page renders non-breaking spaces and soft hyphens we do not reproduce
    character for character. The word sequence is the honest comparison.
    """
    needle = _words(excerpt)
    if not needle:
        return False
    haystack = _words(text)
    if len(needle) > len(haystack):
        return False
    first = needle[0]
    for start in (i for i, word in enumerate(haystack) if word == first):
        if haystack[start : start + len(needle)] == needle:
            return True
    return False


def _claims_on(url: str, html: str, fetched_at) -> list[tuple[str, object]]:
    """The real extraction path, on one page, normalised to the scorer's keys."""
    from app.adapters.extraction import ClaimBuilder, html_title, readable_text
    from app.adapters.page_classifier import classify_page
    from app.adapters.requirements.web_requirements import extract_requirements

    text = readable_text(html)
    title = html_title(html)
    page = classify_page(url=url, html=html)
    builder = ClaimBuilder(
        source_url=url,
        page_title=title,
        official_domain=True,
        extraction_method="html_rule",
        accessed_at=fetched_at,
    )
    if page.accepts("requirements"):
        extract_requirements(text, builder)
    out: list[tuple[str, object]] = []
    for claim in builder.claims:
        payload = claim.model_dump(mode="json")
        key, value, _programme, _degree = normalize_claim(payload["claim_type"], payload)
        out.append((key, value))
    return out


def _matches(expected: object, produced: object) -> bool:
    if expected is None:
        return False
    if isinstance(expected, int | float) and isinstance(produced, int | float):
        return abs(float(expected) - float(produced)) < 1e-9
    return str(expected).casefold() == str(produced).casefold()


async def probe(target: Target, fetcher) -> Finding:
    """Read one certified source page and say what happened to its fact."""
    page = await fetcher.get(target.url)
    if not page.ok:
        return Finding(
            target.case_id,
            target.key,
            target.url,
            FETCH_FAILED,
            f"{page.outcome.value} — {page.error}"[:160],
        )

    from app.adapters.extraction import readable_text

    text = readable_text(page.text)
    produced = _claims_on(target.url, page.text, page.fetched_at)
    for key, value in produced:
        if key == target.key and _matches(target.value, value):
            return Finding(target.case_id, target.key, target.url, RECOVERED)

    if excerpt_is_present(target.excerpt, text):
        return Finding(
            target.case_id,
            target.key,
            target.url,
            VALUE_MISSING,
            f"the quoted words are in our text; {len(produced)} claims came out, none this one",
        )
    return Finding(
        target.case_id,
        target.key,
        target.url,
        TEXT_MISSING,
        f"the quoted words are not in our text at all ({len(text)} chars read)",
    )


def summarise(findings: list[Finding]) -> str:
    """The table, then the reading. The counts are the point."""
    by_verdict = Counter(f.verdict for f in findings)
    lines = [f.line() for f in findings]
    lines.append("")
    lines.append(f"{len(findings)} certified facts read from their own source pages")
    for verdict in (RECOVERED, VALUE_MISSING, TEXT_MISSING, FETCH_FAILED):
        lines.append(f"  {verdict:14} {by_verdict.get(verdict, 0)}")
    lines.append("")
    lines.append(
        "value_missing means the patterns; text_missing means the page's content never "
        "reached us; recovered with a still-zero live claim_recall would mean navigation."
    )
    return "\n".join(lines)


async def run(dataset: Dataset, *, live: bool, cache: Path, corpus: Path | None) -> list[Finding]:
    from app.adapters.fetching import Fetcher

    async with Fetcher(cache, offline=not live, corpus_dir=corpus) as fetcher:
        return [await probe(t, fetcher) for t in targets(dataset)]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--cache", type=Path, default=Path(".cache/oracle"))
    parser.add_argument("--json", type=Path, help="also write the findings as JSON")
    parser.add_argument(
        "--live",
        action="store_true",
        help="fetch the certified source pages for real; off by default, as the search probe is",
    )
    args = parser.parse_args()

    dataset = Dataset.model_validate_json(args.dataset.read_text(encoding="utf-8"))
    findings = asyncio.run(run(dataset, live=args.live, cache=args.cache, corpus=None))
    print(summarise(findings))
    if args.json:
        args.json.write_text(json.dumps([asdict(f) for f in findings], indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
