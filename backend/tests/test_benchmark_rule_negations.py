"""The harness's ``--no-<flag>`` forms for every default-on rule.

Seen-site ledger 2026-10-19, "Re-measure order for 13's protocol": every rule
flag in ``evaluation/research/live.py`` was ``store_true`` and could only switch
a rule on, so the off arm of a re-measure had no flag. Each ``--no-<stem>``
sets the rule's module constants False in the child, is forwarded by the
parent and refuses its own on-form. Offline: the child process is faked.
"""

from __future__ import annotations

import argparse
import importlib
import re
import subprocess
import sys
from pathlib import Path

import pytest

from evaluation.research import live
from evaluation.research.schema import Capture, Observation

LEDGER = Path(__file__).resolve().parents[2] / "docs/process/SEEN_SITE_LEDGER_2026-10-19.md"

#: The fifteen seen-site rules of the ledger's re-measure table.
SEEN_SITE_STEMS = [
    "local-language-queries",
    "site-identity-v2",
    "alias-aware-program-match",
    "stage-budgets",
    "question-routing",
    "coordinated-degree-scope",
    "international-round-deadline",
    "english-readers-v2",
    "fee-readers-v2",
    "intake-section-deadline",
    "parent-degree-link",
    "question-page-order",
    "award-page-evidence",
    "award-name-qualifier",
    "scholarship-index-query",
]


def _parent(monkeypatch, tmp_path: Path, *flags: str) -> list[list[str]]:
    argv = ["live", "--live", "--case", "uio", "--out", str(tmp_path), *flags]
    monkeypatch.setattr(sys, "argv", argv)
    monkeypatch.setattr(subprocess, "check_output", lambda *args, **kwargs: "synthetic-sha")
    commands: list[list[str]] = []

    def child(command, **kwargs):
        commands.append(command)
        output = Path(command[command.index("--out") + 1])
        output.write_text(Observation(case_id="uio").model_dump_json(), encoding="utf-8")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", child)
    live.main()
    return commands


def test_the_fifteen_seen_site_rules_come_first() -> None:
    assert list(live.NEGATABLE_RULES)[:15] == SEEN_SITE_STEMS


def test_every_negative_form_the_ledger_orders_exists() -> None:
    ordered = set(re.findall(r"`[^`]*?(--no-[a-z0-9-]+)", LEDGER.read_text(encoding="utf-8")))
    assert ordered, "the ledger's re-measure table names its --no- flags"
    parser = argparse.ArgumentParser()
    live.add_rule_negations(parser)
    known = {option for action in parser._actions for option in action.option_strings}
    assert ordered <= known


@pytest.mark.parametrize("stem", list(live.NEGATABLE_RULES))
def test_each_negative_form_switches_a_default_on_rule_off(stem, monkeypatch) -> None:
    targets = live.NEGATABLE_RULES[stem]
    for module, name in targets:
        # The rule is on by default today, so the off arm is the only one that
        # differs; a DEFAULT_OFF_NEGATABLE rule is off until its replay passes.
        default = stem not in live.DEFAULT_OFF_NEGATABLE
        assert getattr(importlib.import_module(module), name) is default, f"{module}.{name}"
        monkeypatch.setattr(importlib.import_module(module), name, True)
    parser = argparse.ArgumentParser()
    live.add_rule_negations(parser)
    args = parser.parse_args([f"--no-{stem}"])
    assert live.rule_negation_arguments(args) == [f"--no-{stem}"]
    live.apply_rule_negations(args)
    for module, name in targets:
        assert getattr(importlib.import_module(module), name) is False
    # Nothing else was touched.
    others = [
        (t, s not in live.DEFAULT_OFF_NEGATABLE)
        for s, ts in live.NEGATABLE_RULES.items()
        if s != stem
        for t in ts
    ]
    for (module, name), default in others:
        if (module, name) not in targets:
            assert getattr(importlib.import_module(module), name) is default


#: Every stem but IM-1's has an on-form to refuse.
ON_FORM_STEMS = [stem for stem in live.NEGATABLE_RULES if stem != "integrated-masters-level"]


@pytest.mark.parametrize("stem", ON_FORM_STEMS)
def test_each_negative_form_refuses_its_on_form(stem, monkeypatch, tmp_path, capsys) -> None:
    with pytest.raises(SystemExit):
        _parent(monkeypatch, tmp_path, f"--{stem}", f"--no-{stem}")
    assert f"--{stem} and --no-{stem} cannot be combined" in capsys.readouterr().err


def test_the_parent_forwards_the_negative_forms(tmp_path, monkeypatch) -> None:
    flags = ["--no-local-language-queries", "--no-site-identity-v2", "--no-document-rules-v2"]
    commands = _parent(monkeypatch, tmp_path, *flags, "--no-integrated-masters-level")
    for flag in [*flags, "--no-integrated-masters-level"]:
        assert flag in commands[0]
    # No on-form leaks into the child for a rule switched off.
    assert "--site-identity-v2" not in commands[0]
    capture = Capture.model_validate_json(next(tmp_path.rglob("capture.json")).read_text())
    assert capture.config["rules_off"] == [
        "--no-local-language-queries",
        "--no-site-identity-v2",
        "--no-document-rules-v2",
        "--no-integrated-masters-level",
    ]


def test_a_capture_without_negations_carries_no_rules_off(tmp_path, monkeypatch) -> None:
    commands = _parent(monkeypatch, tmp_path)
    assert not any(
        argument.startswith("--no-") and argument[5:] in live.NEGATABLE_RULES
        for argument in commands[0]
    )
    capture = Capture.model_validate_json(next(tmp_path.rglob("capture.json")).read_text())
    assert "rules_off" not in capture.config


def test_the_child_flips_the_module_constants(tmp_path, monkeypatch) -> None:
    from app.adapters.discovery import live_discovery
    from app.adapters.search import intent
    from app.catalogue import discovery

    seen: dict[str, bool] = {}

    async def fake_capture(case_id, output, max_pages, seconds, **kwargs):
        seen.update(
            local=intent.LOCAL_LANGUAGE_QUERIES,
            identity=discovery.SITE_IDENTITY_V2,
            budgets=live_discovery.STAGE_BUDGETS,
        )

    for module, name in [
        (intent, "LOCAL_LANGUAGE_QUERIES"),
        (discovery, "SITE_IDENTITY_V2"),
        (live_discovery, "STAGE_BUDGETS"),
    ]:
        monkeypatch.setattr(module, name, True)
    monkeypatch.setattr(live, "capture_one", fake_capture)
    argv = ["live", "--live", "--child", "--case", "uio", "--out", str(tmp_path / "uio.json")]
    argv += ["--no-local-language-queries", "--no-site-identity-v2"]
    monkeypatch.setattr(sys, "argv", argv)
    live.main()
    assert seen == {"local": False, "identity": False, "budgets": True}
