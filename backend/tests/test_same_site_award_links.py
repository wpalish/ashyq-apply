"""SH-1: a funding index's award links on a sibling host of its own site.

REACH_ROWS_2026-10-20, shape S5 (sibling-host half): ES-1 counted award-shaped
links the index walk dropped because they sat on another host, and on two
development sets some of those hosts were under the index's own registrable
domain. With ``web_scholarships.SAME_SITE_AWARD_LINKS`` on, such a link is kept
like a same-host one, inside the one award budget; a link to another
registrable domain stays dropped. Off: nothing changes. Synthetic pages only.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from app.adapters.scholarship import web_scholarships as ws
from evaluation.research import live, stage_summary
from tests.test_award_page_evidence import _find
from tests.test_scholarship_index_walk import _AWARD, _INDEX

INDEX = "https://www.zqsite.edu/funding/scholarships"
SAME_HOST = "https://www.zqsite.edu/funding/scholarships/merit-scholarship"
SIBLING = "https://awards.zqsite.edu/scholarships/global-excellence-scholarship"
OTHER_SITE = "https://grants.zqfoundation.org/scholarships/zq-scholarship"
MAILER = "https://massmailer.zqsite.edu/scholarships/newsletter-scholarship"


def _links_page(*hrefs: str) -> str:
    items = "".join(
        f'<li><a href="{href}">Scholarship {i}</a></li>' for i, href in enumerate(hrefs)
    )
    return _INDEX.format(title="Scholarships", items=items)


def _award(name: str) -> str:
    return _AWARD.format(name=name)


# --- the link filter -------------------------------------------------------------


@pytest.mark.parametrize("on", [False, True])
def test_a_sibling_host_link_is_kept_only_with_the_rule(monkeypatch, on):
    monkeypatch.setattr(ws, "SAME_SITE_AWARD_LINKS", on)
    html = _links_page(SAME_HOST, SIBLING, OTHER_SITE, MAILER)
    links, dropped = ws._award_links_counted(html, INDEX)
    assert links == ws._award_links(html, INDEX)
    assert links == ([SAME_HOST, SIBLING] if on else [SAME_HOST])
    # Another registrable domain and a mail redirector stay dropped either way.
    assert dropped == ([OTHER_SITE, MAILER] if on else [SIBLING, OTHER_SITE, MAILER])


@pytest.mark.parametrize(
    ("index", "href", "kept"),
    [
        # A multi-part public suffix: the registrable domain is uni.ac.uk.
        ("https://www.zquni.ac.uk/funding", "https://awards.zquni.ac.uk/scholarships/a", True),
        ("https://www.zquni.ac.uk/funding", "https://zqother.ac.uk/scholarships/a", False),
        # The bare registrable domain is a sibling of its www host.
        ("https://www.zqsite.edu/funding", "https://zqsite.edu/scholarships/a", True),
        # A private public suffix: two tenants are two sites.
        ("https://zqsite.github.io/funding", "https://zqother.github.io/scholarships/a", False),
        # A look-alike host that only contains the name is another site.
        ("https://www.zqsite.edu/funding", "https://zqsite.edu.evil.example/scholarships/a", False),
    ],
)
def test_same_site_is_the_public_suffix_aware_registrable_domain(monkeypatch, index, href, kept):
    monkeypatch.setattr(ws, "SAME_SITE_AWARD_LINKS", True)
    links, dropped = ws._award_links_counted(_links_page(href), index)
    assert (links == [href]) is kept
    assert (dropped == [href]) is (not kept)


def test_the_rule_is_off_by_default():
    assert ws.SAME_SITE_AWARD_LINKS is False


@pytest.mark.parametrize("on", [False, True])
def test_a_sibling_host_link_is_never_filed_beneath_the_page(monkeypatch, on):
    monkeypatch.setattr(ws, "SAME_SITE_AWARD_LINKS", on)
    below = [f"https://awards.zqsite.edu/funding/scholarships/award-{i}" for i in range(3)]
    html = _links_page(*below)
    assert ws._lists_awards_below(html, INDEX) is False
    summary = ws._award_link_summary(html, INDEX)
    assert summary.startswith(f"{3 if on else 0} award links, 0 below it")


# --- the diagnostics lines -------------------------------------------------------


@pytest.mark.parametrize("on", [False, True])
def test_the_diagnostics_line_counts_follow_the_rule(monkeypatch, on):
    monkeypatch.setattr(ws, "SAME_SITE_AWARD_LINKS", on)
    links, dropped = ws._award_links_counted(_links_page(SAME_HOST, SIBLING, OTHER_SITE), INDEX)
    rows = stage_summary.evidence_categories(ws._off_host_line(INDEX, dropped))
    assert rows == [
        ("award_links_dropped_off_host", 1 if on else 2),
        ("award_links_dropped_off_host_same_site", 0 if on else 1),
    ]
    sibling = sum(1 for link in links if not ws._on_page_host(link, INDEX))
    assert sibling == (1 if on else 0)
    assert stage_summary.evidence_categories(ws._sibling_host_line(INDEX, 1)) == [
        ("award_links_kept_same_site", 1)
    ]


# --- the funding walk ------------------------------------------------------------


def _pages(*award_urls: str) -> dict[str, str]:
    pages = {INDEX: _links_page(*award_urls)}
    for i, url in enumerate(award_urls):
        pages[url] = _award(f"Zq Award {i} Scholarship")
    return pages


@pytest.mark.asyncio
@pytest.mark.parametrize("on", [False, True])
async def test_the_walk_reads_a_sibling_host_award_only_with_the_rule(tmp_path, monkeypatch, on):
    monkeypatch.setattr(ws, "SAME_SITE_AWARD_LINKS", on)
    awards, result, site = await _find(
        tmp_path,
        monkeypatch,
        _pages(SAME_HOST, SIBLING, OTHER_SITE),
        on=True,
        domain="zqsite.edu",
        scholarships_url=INDEX,
    )
    assert SAME_HOST in site.requested
    assert (SIBLING in site.requested) is on
    assert OTHER_SITE not in site.requested
    names = {a.name for a in awards}
    assert ("Zq Award 1 Scholarship" in names) is on
    assert "Zq Award 2 Scholarship" not in names
    off_host = [line for line in result.errors if "on another host not followed" in line]
    assert off_host == [ws._off_host_line(INDEX, [OTHER_SITE] if on else [SIBLING, OTHER_SITE])]
    kept = [line for line in result.errors if "on a sibling host of the same site kept" in line]
    assert kept == ([ws._sibling_host_line(INDEX, 1)] if on else [])


@pytest.mark.asyncio
async def test_the_walk_keeps_sibling_links_inside_the_award_budget(tmp_path, monkeypatch):
    monkeypatch.setattr(ws, "SAME_SITE_AWARD_LINKS", True)
    monkeypatch.setattr(ws, "_MAX_AWARD_PAGES", 2)
    siblings = [f"https://awards.zqsite.edu/scholarships/award-{i}-scholarship" for i in range(4)]
    _, result, site = await _find(
        tmp_path,
        monkeypatch,
        _pages(SAME_HOST, *siblings),
        on=True,
        domain="zqsite.edu",
        scholarships_url=INDEX,
    )
    read = [url for url in site.requested if url != INDEX]
    assert len(read) == 2, site.requested
    detail = next(o.detail for o in result.page_outcomes if o.url == INDEX)
    assert detail.startswith("read as a funding index; 5 award links, 2 queued within the award")


@pytest.mark.asyncio
async def test_off_the_walk_is_unchanged_for_same_host_links(tmp_path, monkeypatch):
    # Off and on read the same pages when every award link is on the index's host.
    requested = []
    for on in (False, True):
        monkeypatch.setattr(ws, "SAME_SITE_AWARD_LINKS", on)
        _, result, site = await _find(
            tmp_path / str(on),
            monkeypatch,
            _pages(SAME_HOST),
            on=True,
            domain="zqsite.edu",
            scholarships_url=INDEX,
        )
        requested.append((site.requested, result.errors))
    assert requested[0] == requested[1]


# --- the harness flag ------------------------------------------------------------


def test_the_flag_is_a_default_off_negatable_rule(tmp_path, monkeypatch) -> None:
    from tests.test_benchmark_rule_negations import _parent

    result = subprocess.run(
        [sys.executable, "-m", "evaluation.research.live", "--help"],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "--same-site-award-links" in result.stdout
    assert "--no-same-site-award-links" in result.stdout
    assert live.NEGATABLE_RULES["same-site-award-links"] == (
        ("app.adapters.scholarship.web_scholarships", "SAME_SITE_AWARD_LINKS"),
    )
    assert "same-site-award-links" in live.DEFAULT_OFF_NEGATABLE
    commands = _parent(monkeypatch, tmp_path, "--same-site-award-links")
    assert "--same-site-award-links" in commands[0]


def test_the_child_switches_the_rule_on(tmp_path, monkeypatch) -> None:
    seen: dict[str, bool] = {}

    async def fake_capture(case_id, output, max_pages, seconds, **kwargs):
        seen["on"] = ws.SAME_SITE_AWARD_LINKS

    monkeypatch.setattr(ws, "SAME_SITE_AWARD_LINKS", False)
    monkeypatch.setattr(live, "capture_one", fake_capture)
    argv = ["live", "--live", "--child", "--case", "uio", "--out", str(tmp_path / "uio.json")]
    monkeypatch.setattr(sys, "argv", [*argv, "--same-site-award-links"])
    live.main()
    assert seen == {"on": True}
