"""FUSE-1: two recorded-search stores combined offline per request key (TRACK_B_2026-10-26 §3).

Offline only: synthetic stores, and the committed Exa r1 and Serper base3 stores
re-fused in memory. Nothing is sent to any provider.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import pytest

from app.adapters.search.recorded import RecordedSearchStore, RecordedStoreError, request_key
from evaluation.research import live, recorded_search
from evaluation.research.recorded_search import fuse_documents

DATA = Path(live.__file__).resolve().parent / "data"
FUSED = DATA / "recorded_search.fused1.json"


def _v1(*entries: dict[str, Any]) -> dict[str, Any]:
    return {"schema": "recorded-search/1", "provenance": {"sources": []}, "entries": list(entries)}


def _v2(*entries: dict[str, Any]) -> dict[str, Any]:
    return {"schema": "recorded-search/2", "provenance": {"sources": []}, "entries": list(entries)}


def _entry(query: str, urls: list[str], **extra: Any) -> dict[str, Any]:
    return {
        "set": "cohort",
        "case": "groningen",
        "family": "field_and_degree",
        "query": query,
        "domains": ["uni.edu"],
        "hl": None,
        "gl": None,
        "urls": urls,
        **extra,
    }


def _wide(query: str, urls: list[str]) -> dict[str, Any]:
    return _entry(
        query,
        urls,
        results=[
            {"url": u, "title": f"T{n}", "snippet": f"S{n}", "rank": n}
            for n, u in enumerate(urls, start=1)
        ],
        page={"requested": 25, "returned": len(urls), "consumed": min(10, len(urls))},
        provider="exa",
    )


U = [f"https://www.uni.edu/p{n}" for n in range(1, 7)]


def test_interleave_lists_rank_by_rank_each_url_once_and_keeps_both_texts() -> None:
    primary = _v2(_wide("q", [U[0], U[1], U[2]]))
    secondary = _v1(_entry("Q", [U[3], U[1] + "/", U[4]]))
    document = fuse_documents(primary, secondary)
    (entry,) = document["entries"]
    assert entry["urls"] == [U[0], U[3], U[1], U[2], U[4]]
    assert [r["rank"] for r in entry["results"]] == [1, 2, 3, 4, 5]
    assert [(r["title"], r["snippet"]) for r in entry["results"]] == [
        ("T1", "S1"),
        ("", ""),
        ("T2", "S2"),
        ("T3", "S3"),
        ("", ""),
    ]
    assert "page" not in entry  # the paid page's counts were the primary's alone
    assert entry["fused"] == {"primary": 3, "secondary_added": 2}
    store = RecordedSearchStore.from_document(document)
    assert store.entries[request_key("q", ["uni.edu"])] == tuple(entry["urls"])


def test_append_keeps_the_primary_whole_then_the_secondary_novel() -> None:
    primary = _v2(_wide("q", [U[0], U[1]]))
    secondary = _v1(_entry("q", [U[1], U[2]]))
    (entry,) = fuse_documents(primary, secondary, order="append")["entries"]
    assert entry["urls"] == [U[0], U[1], U[2]]


def test_a_key_in_one_store_only_is_copied_and_the_page_kept_when_nothing_is_added() -> None:
    primary = _v2(_wide("only primary", [U[0]]), _wide("both", [U[1], U[2]]))
    secondary = _v1(_entry("only secondary", [U[3]]), _entry("both", [U[2]]))
    document = fuse_documents(primary, secondary)
    by_query = {e["query"]: e for e in document["entries"]}
    assert by_query["only primary"] == primary["entries"][0]
    assert by_query["only secondary"]["urls"] == [U[3]]
    assert by_query["only secondary"]["fused"] == {"primary": 0, "secondary_added": 1}
    assert by_query["both"]["urls"] == [U[1], U[2]]
    assert by_query["both"]["page"] == primary["entries"][1]["page"]
    assert document["provenance"]["fused"]["entries"] == {
        "both": 1,
        "primary_only": 1,
        "secondary_only": 1,
    }


def test_a_malformed_input_or_order_is_refused() -> None:
    with pytest.raises(RecordedStoreError):
        fuse_documents(_v2(_entry("q", ["ftp://x"])), _v1())
    with pytest.raises(ValueError, match="order"):
        fuse_documents(_v2(_wide("q", U[:1])), _v1(_entry("q", U[1:2])), order="zip")


def test_the_cli_fuses_two_files_and_takes_nothing_else(tmp_path: Path, capsys) -> None:
    a, b, out = tmp_path / "a.json", tmp_path / "b.json", tmp_path / "out.json"
    a.write_text(json.dumps(_v2(_wide("q", U[:2]))))
    b.write_text(json.dumps(_v1(_entry("q", U[2:3]))))
    assert recorded_search.main(["--fuse", str(a), str(b), "--out", str(out)]) == 0
    assert json.loads(out.read_text())["entries"][0]["urls"] == [U[0], U[2], U[1]]
    assert "cohort: 1 cases, 1 requests" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        recorded_search.main(["--fuse", str(a), str(b), "--cases", "groningen", "--out", str(out)])


def test_the_committed_fused_store_is_r1_and_base3_fused_and_development_only() -> None:
    document = json.loads(FUSED.read_text(encoding="utf-8"))
    rebuilt = fuse_documents(
        json.loads((DATA / "recorded_search.r1.json").read_text(encoding="utf-8")),
        json.loads((DATA / "recorded_search.base3.json").read_text(encoding="utf-8")),
    )
    assert document == rebuilt
    assert document["provenance"]["provider_recorded"] == "exa + serper"
    store = RecordedSearchStore.from_document(document)
    assert len(store) == len(document["entries"])
    for entry in document["entries"]:
        assert entry["case"] in recorded_search.DEV_SETS[entry["set"]]
        assert entry["case"] not in recorded_search.FORBIDDEN_CASES
    forbidden = {*live.HELDOUT.values(), *live.DEV5_DOMAINS.values()}
    hosts = {urlsplit(u).hostname or "" for e in document["entries"] for u in e["urls"]}
    assert not {h for h in hosts for d in forbidden if h == d or h.endswith("." + d)}
