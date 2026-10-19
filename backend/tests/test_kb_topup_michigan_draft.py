"""KB top-up: Michigan's advising-article draft keeps its URL end to end.

``kb_drafts.2026-10-19/topup_programme1/programme/qs2027-051.1-department.json``
names U-M's TeamDynamix article ``ArticleDet?ID=7445`` (a URL with a query) in
the ``programme.url`` slot and its quote in ``programme.title``, beside a
dev5-style ``programme_urls`` list. Pinned here: ``verify_evidence`` emits its
programme row with that URL (the CI report row, the robots-override target and
the override's re-read row all carry it), and ``kb_build``'s programme loader
reads the ``department`` role and records the verified page under that URL.
The draft's six empty answers are "unknown" placeholder rows (``url`` None),
as for every programme-only draft. Offline: no page is read.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.adapters.fetching import FetchResult
from app.domain.enums import FetchOutcome
from evaluation.research.expert import kb_build
from scripts import verify_evidence

BACKEND = Path(__file__).resolve().parents[1]
TOPUP = (
    BACKEND / "evaluation" / "research" / "expert" / "data" / "kb_drafts.2026-10-19"
) / "topup_programme1"
ARTICLE = "https://teamdynamix.umich.edu/TDClient/154/Portal/KB/ArticleDet?ID=7445"
CASE = "qs2027-051"


def _draft() -> dict[str, Any]:
    path = TOPUP / "programme" / f"{CASE}.1-department.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_the_draft_names_the_article_in_the_programme_slot() -> None:
    draft = _draft()
    assert draft["programme"]["url"] == ARTICLE
    assert draft["programme_urls"] == [ARTICLE]
    rows = verify_evidence.items(draft)
    assert rows[0] == ("programme", "known", ARTICLE, draft["programme"]["title"])
    # The empty answers are the "unknown" placeholders every such draft has.
    assert all(status == "unknown" and url is None for _i, status, url, _q in rows[1:])


def test_the_drafts_directory_loads_it() -> None:
    drafts = [d for d in verify_evidence.load(TOPUP) if d.get("case") == CASE]
    urls = {(d.get("programme") or {}).get("url") for d in drafts}
    assert ARTICLE in urls


def test_the_ci_row_and_the_override_target_carry_the_url() -> None:
    report = json.loads((TOPUP / "evidence_check.ci-2026-10-19.json").read_text("utf-8"))
    rows = [r for r in report if r["case"] == CASE and r["item"] == "programme"]
    assert ARTICLE in {r["url"] for r in rows}
    assert (CASE, "programme", ARTICLE) in verify_evidence.robots_override_targets(report)


async def test_the_override_reread_row_carries_the_url() -> None:
    quote = _draft()["programme"]["title"]

    class _Page:
        async def get(self, url: str, **_kwargs: Any) -> FetchResult:
            return FetchResult(
                url=url,
                outcome=FetchOutcome.OK,
                status_code=200,
                text=f"<html><body><main><p>{quote}</p></main></body></html>",
                content_type="text/html",
                final_url=url,
            )

    only = {(CASE, "programme", ARTICLE)}
    rows = await verify_evidence.check_with(
        _Page(),  # type: ignore[arg-type]
        verify_evidence.load(TOPUP),
        only=only,
    )
    assert [(r["url"], r["official"], r["quote_found"]) for r in rows] == [(ARTICLE, True, True)]


def test_kb_build_records_the_department_page_under_its_url() -> None:
    pages = kb_build.load_programme_pages(TOPUP / "programme")[CASE]
    assert [role for role, _draft in pages] == ["local", "department"]
    row = {
        "case": CASE,
        "item": "programme",
        "url": ARTICLE,
        "official": True,
        "quote_found": True,
        "checked_on": "2026-10-19",
        "_verified_by": kb_build.ROBOTS_OVERRIDE,
    }
    block = kb_build.programme_block(
        CASE, pages, kb_build.Evidence([row]), default_verified="2026-10-19"
    )
    assert block["status"] == "known"
    assert block["urls"] == [ARTICLE]
    assert [e["url"] for e in block["evidence"]] == [ARTICLE]
    assert block["evidence"][0]["robots_override"] is True
