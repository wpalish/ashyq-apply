"""HP-AUDIT D3: the two LI-1 rows a heldout page picked, behind one flag.

``docs/process/HELDOUT_PROVENANCE_AUDIT_2026-10-20.md`` re-sourced every LI-1
row to a dictionary or a degree law, but two were *selected* because a heldout
page needed them: the German path word "studienangebot" (row A6) and the
Italian slug compound ``laurea-magistrale`` (row A17). ``HELDOUT_PICKED_ROWS``
(on by default, behaviour unchanged) lets a removal replay leave both out with
``--no-heldout-picked-rows``. Generic invented hosts only; offline.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import pytest

from app.adapters.discovery import live_discovery
from app.adapters.discovery.live_discovery import PageCategory, degree_level_named, score_url
from app.adapters.search.retrieval import _local_catalogue_path
from evaluation.research import live

BACKEND = Path(__file__).resolve().parents[1]

GERMAN_PATH = "https://www.uni.de/studium/studienangebot/informatik-bachelor"
GERMAN_OTHER_WORD = "https://www.uni.de/studium/studiengaenge/informatik-bachelor"
ITALIAN_MASTER = "https://www.uni.it/corsi/laurea-magistrale/informatica"


@pytest.fixture(autouse=True)
def _li1_on(monkeypatch):
    monkeypatch.setattr(live_discovery, "LOCALIZED_IDENTITY", True)


def test_on_by_default() -> None:
    assert live_discovery.HELDOUT_PICKED_ROWS is True
    assert live_discovery.localized_program_signals() is live_discovery._LOCALIZED_PROGRAM_SIGNALS
    assert (
        live_discovery._localized_degree_compounds() is live_discovery._LOCALIZED_DEGREE_COMPOUNDS
    )


def test_on_the_studienangebot_path_scores_as_a_programme_page() -> None:
    assert score_url(GERMAN_PATH, PageCategory.PROGRAM_PAGE) == score_url(
        GERMAN_OTHER_WORD, PageCategory.PROGRAM_PAGE
    )
    assert score_url(GERMAN_PATH, PageCategory.PROGRAM_PAGE) >= 3
    assert _local_catalogue_path(GERMAN_PATH)


def test_off_the_studienangebot_word_alone_is_left_out(monkeypatch) -> None:
    on = score_url(GERMAN_PATH, PageCategory.PROGRAM_PAGE)
    other_on = score_url(GERMAN_OTHER_WORD, PageCategory.PROGRAM_PAGE)
    monkeypatch.setattr(live_discovery, "HELDOUT_PICKED_ROWS", False)
    assert score_url(GERMAN_PATH, PageCategory.PROGRAM_PAGE) == on - 3
    # Every other LI-1 path word is untouched.
    assert score_url(GERMAN_OTHER_WORD, PageCategory.PROGRAM_PAGE) == other_on
    assert _local_catalogue_path(GERMAN_OTHER_WORD)


def test_on_the_laurea_magistrale_compound_names_a_master() -> None:
    assert degree_level_named(ITALIAN_MASTER) == "master"


def test_off_the_compound_is_gone_and_laurea_reads_bachelor(monkeypatch) -> None:
    monkeypatch.setattr(live_discovery, "HELDOUT_PICKED_ROWS", False)
    # As if the row had never been written: ``laurea`` (bachelor) answers.
    assert degree_level_named(ITALIAN_MASTER) == "bachelor"
    # The other compounds stay.
    assert degree_level_named("https://u.edu.tr/yuksek-lisans/bilgisayar") == "master"
    assert degree_level_named("https://u.it/corsi/laurea-triennale/informatica") == "bachelor"


def test_flag_does_nothing_while_li1_is_off(monkeypatch) -> None:
    monkeypatch.setattr(live_discovery, "LOCALIZED_IDENTITY", False)
    for value in (True, False):
        monkeypatch.setattr(live_discovery, "HELDOUT_PICKED_ROWS", value)
        assert degree_level_named(ITALIAN_MASTER) is None
        assert score_url(GERMAN_PATH, PageCategory.PROGRAM_PAGE) == score_url(
            GERMAN_PATH.replace("studienangebot", "xyz"), PageCategory.PROGRAM_PAGE
        )


def test_harness_negation_is_registered_default_on() -> None:
    assert live.NEGATABLE_RULES["heldout-picked-rows"] == (
        ("app.adapters.discovery.live_discovery", "HELDOUT_PICKED_ROWS"),
    )
    assert "heldout-picked-rows" not in live.DEFAULT_OFF_NEGATABLE


def test_harness_negation_switches_the_flag_off(monkeypatch) -> None:
    monkeypatch.setattr(live_discovery, "HELDOUT_PICKED_ROWS", True)
    parser = argparse.ArgumentParser()
    live.add_rule_negations(parser)
    args = parser.parse_args(["--no-heldout-picked-rows"])
    assert live.rule_negation_arguments(args) == ["--no-heldout-picked-rows"]
    live.apply_rule_negations(args)
    assert live_discovery.HELDOUT_PICKED_ROWS is False
    assert degree_level_named(ITALIAN_MASTER) == "bachelor"


def test_harness_exposes_forwards_and_negates_the_flag() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "evaluation.research.live", "--help"],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "--heldout-picked-rows" in result.stdout
    assert "--no-heldout-picked-rows" in result.stdout
    source = (BACKEND / "evaluation" / "research" / "live.py").read_text(encoding="utf-8")
    assert "hp_module.HELDOUT_PICKED_ROWS = True" in source
    assert '["--heldout-picked-rows"] if args.heldout_picked_rows' in source
