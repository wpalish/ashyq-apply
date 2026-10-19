"""Invariants of the imported development KB (app/knowledge/kb_imported_dev.json).

Reads only the KB file and the public top-100 list; never a heldout corpus.
"""

import json
import re
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
KB = BACKEND / "app" / "knowledge" / "kb_imported_dev.json"
LIST = BACKEND / "evaluation" / "research" / "data" / "kb_top100_list.json"

HELDOUT_TOKENS = {
    "nu",
    "metu",
    "sabanci",
    "charles",
    "masaryk",
    "tum",
    "tartu",
    "polimi",
    "vilnius",
}
QUESTIONS = {
    "english",
    "gpa",
    "deadline",
    "tuition",
    "scholarship_exists",
    "scholarship_international",
}


def _kb():
    return json.loads(KB.read_text(encoding="utf-8"))


def _facts(kb):
    for seed_id, entry in kb["entries"].items():
        for question, facts in entry["facts"].items():
            for fact in facts:
                yield seed_id, question, fact


def test_entries_are_exactly_the_import_existing_rows():
    kb = _kb()
    rows = json.loads(LIST.read_text(encoding="utf-8"))["rows"]
    expected = {r["seed_id"]: r["existing_case"] for r in rows if r["status"] == "import_existing"}
    assert kb["format"] == "kb-imported-dev/1"
    assert {k: e["source_case"] for k, e in kb["entries"].items()} == expected
    for seed_id, entry in kb["entries"].items():
        assert entry["seed_id"] == seed_id
        assert set(entry["facts"]) == QUESTIONS
        assert entry["known_fact_count"] == sum(len(v) for v in entry["facts"].values())


def test_every_known_fact_has_a_url_a_quote_and_dates():
    kb = _kb()
    facts = list(_facts(kb))
    assert facts
    for _, _, fact in facts:
        assert fact["source_url"].startswith(("http://", "https://"))
        assert fact["quote"].strip()
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", fact["accessed_on"])
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", fact["verified_on"])
        assert isinstance(fact["stale"], bool)
        for extra in fact.get("more_sources", []):
            assert extra["url"].startswith(("http://", "https://")) and extra["quote"].strip()


def test_programme_pages_carry_evidence():
    for entry in _kb()["entries"].values():
        programme = entry["programme"]
        assert isinstance(programme["related_programme_urls"], list)
        if programme["status"] == "known":
            assert programme["urls"]
            assert programme["evidence"]
        for ev in programme["evidence"]:
            assert ev["url"].startswith(("http://", "https://")) and ev["quote"].strip()


def test_stale_list_matches_flags():
    kb = _kb()
    flagged = {(s, f["key"]) for s, _, f in _facts(kb) if f["stale"]}
    assert flagged == {(s["seed_id"], s["key"]) for s in kb["stale_facts"]}


def test_no_heldout_case_and_no_model_identifier():
    kb = _kb()
    rows = json.loads(LIST.read_text(encoding="utf-8"))["rows"]
    excluded = {r["seed_id"] for r in rows if r["status"] == "excluded_heldout"}
    assert not excluded & set(kb["entries"])
    for entry in kb["entries"].values():
        assert entry["source_case"] not in HELDOUT_TOKENS
        assert "heldout" not in entry["source_corpus"]
    text = KB.read_text(encoding="utf-8")
    assert "heldout" not in text.lower()
    assert not re.search(r"(?i)\b(gpt|claude|codex|opus|sonnet|haiku|fable)-[\w.]", text)
