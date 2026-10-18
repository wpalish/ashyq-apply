"""FS-2: a topic-search page that is another programme's own page claims nothing.

UM, dev3 runs of 2026-10-18: the English-requirements query returned the
"Bachelor of English Language and Linguistics" page and its conditional IELTS 6
was claimed for Computer Science, whose own page states 5.5.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.adapters.requirements import web_requirements
from tests.test_topic_faculty_scope import PROGRAMME, _ielts, _run

OTHER = """<html><head>
<title>Bachelor of English Language and Linguistics | University of Groningen</title></head>
<body><h1>Bachelor of English Language and Linguistics</h1>
<p>Bachelor's degree programme English Language and Linguistics, 3 years.</p>
<h2>Entry requirements</h2>
<p>International applicants: IELTS Academic overall score 6.0.</p>
</body></html>"""

SAME = OTHER.replace("English Language and Linguistics", "Computing Science")


def _site(tmp_path: Path, topic_html: str) -> Path:
    root = tmp_path / "site"
    (root / "rug" / "bachelors").mkdir(parents=True)
    (root / "rug" / "bachelors" / "computing-science.html").write_text(PROGRAMME, encoding="utf-8")
    (root / "rug" / "topic.html").write_text(topic_html, encoding="utf-8")
    return root


@pytest.fixture(params=[False, True], ids=["off", "on"])
def scoped(request, monkeypatch) -> bool:
    monkeypatch.setattr(web_requirements, "TOPIC_PROGRAMME_SCOPE", request.param)
    return request.param


def test_off_by_default():
    assert web_requirements.TOPIC_PROGRAMME_SCOPE is False


@pytest.mark.asyncio
async def test_another_programmes_page_claims_nothing_when_on(
    settings, tmp_path, monkeypatch, scoped
):
    result = await _run(settings, _site(tmp_path, OTHER), monkeypatch, "topic.html")
    got = _ielts(result, "fixture://rug/topic.html")
    assert got == ([] if scoped else [6.0])
    if scoped:
        [why] = [o for o in result.page_outcomes if o.url == "fixture://rug/topic.html"]
        assert why.category == "no-pattern-match"
        assert why.detail.startswith("FS-2:")


@pytest.mark.asyncio
async def test_the_requested_programmes_page_is_kept(settings, tmp_path, monkeypatch, scoped):
    result = await _run(settings, _site(tmp_path, SAME), monkeypatch, "topic.html")
    assert _ielts(result, "fixture://rug/topic.html") == [6.0]
