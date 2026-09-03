"""Post-study work rules from a government source."""

from __future__ import annotations

from app.adapters.base import AdapterResult
from app.adapters.extraction import ClaimBuilder, html_title, html_to_text
from app.adapters.fetching import Fetcher
from app.domain.enums import ClaimType, SourceSpecificity


class WebGovernmentAdapter:
    name = "web-government"

    def __init__(self, fetcher: Fetcher, url_for_country=None) -> None:
        self.fetcher = fetcher
        self._url_for_country = url_for_country or (
            lambda c: f"fixture://government/{c.lower().replace(' ', '-')}.html"
        )

    async def post_study_work(self, country: str) -> AdapterResult:
        out = AdapterResult()
        url = self._url_for_country(country)
        if not url:
            out.errors.append(f"No government source is configured for {country}.")
            return out
        res = await self.fetcher.get(url)
        out.pages_checked += 1
        if not res.ok:
            out.pages_failed += 1
            out.errors.append(
                f"{url}: {res.outcome.value} — post-study work rules unverified for {country}."
            )
            return out

        text = html_to_text(res.text)
        builder = ClaimBuilder(
            source_url=url,
            page_title=html_title(res.text),
            specificity=SourceSpecificity.GOVERNMENT,
            official_domain=True,
            extraction_method="fixture" if url.startswith("fixture://") else "html_rule",
            accessed_at=res.fetched_at,
        )
        body = " ".join(
            ln.strip()
            for ln in text.splitlines()
            if ln.strip() and "FIXTURE" not in ln and not ln.startswith("Home")
        )
        builder.add(ClaimType.POST_STUDY_WORK, body[:400], body[:400], confidence=0.85)
        out.claims.extend(builder.claims)
        return out
