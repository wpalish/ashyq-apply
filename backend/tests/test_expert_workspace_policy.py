"""V6 workspace identity checks use real temporary aliases, never model I/O."""

from __future__ import annotations

import copy
import json
import os
import tempfile
from pathlib import Path
from typing import Any

import pytest

from evaluation.research.expert.turn_policy import AstraLowEffortIsolation, command_proof
from evaluation.research.expert.workspace_policy import (
    WorkspaceReceipt,
    allocate_workspaces,
    selector_paths,
    validate_selector_paths,
    validate_workspaces,
)

WorkspaceMaps = tuple[dict[str, str], dict[str, WorkspaceReceipt]]


def receipt(path: Path) -> WorkspaceReceipt:
    observed = path.stat()
    return {"path": str(path), "device": observed.st_dev, "inode": observed.st_ino}


@pytest.fixture
def allocated(tmp_path: Path) -> WorkspaceMaps:
    return allocate_workspaces(("u", "v"), temp_root=tmp_path)


def test_entire_ten_case_allocation_is_canonical_even_through_a_real_root_alias(
    tmp_path: Path,
) -> None:
    physical = tmp_path / "physical"
    physical.mkdir()
    logical = tmp_path / "logical"
    logical.symlink_to(physical, target_is_directory=True)
    cases = tuple(f"case{index}" for index in range(10))
    assignments, receipts = allocate_workspaces(cases, temp_root=logical)
    assert set(assignments) == set(receipts) == set(cases)
    assert len(set(assignments.values())) == 10
    assert len({(item["device"], item["inode"]) for item in receipts.values()}) == 10
    for case in cases:
        path = Path(assignments[case])
        assert path == path.resolve(strict=True) and path.parent == physical.resolve(strict=True)
        assert receipts[case] == receipt(path)
    assert validate_workspaces(assignments, receipts, case_ids=cases) == {
        case: Path(assignments[case]) for case in cases
    }


def test_default_temp_root_is_canonicalized_before_any_case_allocation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    physical = tmp_path / "physical"
    physical.mkdir()
    logical = tmp_path / "logical"
    logical.symlink_to(physical, target_is_directory=True)
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(logical))
    assignments, _ = allocate_workspaces(("u",))
    assert Path(assignments["u"]).parent == physical.resolve(strict=True)


@pytest.mark.parametrize(
    "cases", [[], ["u", "u"], [""], [" u"], ["../u"], ["u/v"], ["u\\v"], [True], "u"]
)
def test_invalid_case_sets_fail_before_creating_any_directory(tmp_path: Path, cases: Any) -> None:
    with pytest.raises(ValueError, match="Case IDs"):
        allocate_workspaces(cases, temp_root=tmp_path)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("kind", ["missing", "file"])
def test_allocation_requires_an_existing_directory_root(tmp_path: Path, kind: str) -> None:
    root = tmp_path / "root"
    if kind == "file":
        root.write_text("synthetic")
    with pytest.raises(ValueError):
        allocate_workspaces(("u",), temp_root=root)


def test_v5_logical_assignment_is_rejected_even_when_it_resolves_to_the_proved_directory(
    tmp_path: Path,
) -> None:
    physical = tmp_path / "physical"
    physical.mkdir()
    logical = tmp_path / "logical"
    logical.symlink_to(physical, target_is_directory=True)
    legacy = Path(tempfile.mkdtemp(prefix="legacy-", dir=logical))
    canonical = legacy.resolve(strict=True)
    assert legacy != canonical and legacy.stat().st_ino == canonical.stat().st_ino
    with pytest.raises(ValueError, match="canonical"):
        validate_workspaces({"u": str(legacy)}, {"u": receipt(legacy)})


def test_v5_partial_command_normalization_is_rejected_before_any_execution(
    tmp_path: Path,
) -> None:
    physical = tmp_path / "physical"
    physical.mkdir()
    logical = tmp_path / "logical"
    logical.symlink_to(physical, target_is_directory=True)
    assignments, receipts = allocate_workspaces(("u",), temp_root=logical)
    schema, output = selector_paths(assignments, receipts, case_id="u", turn=1)
    schema.write_text("{}")
    alias_workspace = logical / schema.parent.name
    assert alias_workspace.resolve(strict=True) == schema.parent
    with pytest.raises(ValueError, match="exact assigned turn path"):
        validate_selector_paths(
            assignments,
            receipts,
            case_id="u",
            turn=1,
            workspace=schema.parent,
            schema=alias_workspace / schema.name,
            output=alias_workspace / output.name,
        )
    isolation = AstraLowEffortIsolation(
        schema.parent, (tmp_path / "sealed",), "/mock/sandbox", "/mock/codex"
    )
    argv = isolation.command(schema, output=output, model="gpt-6-astra")
    assert {
        key: argv[argv.index(key) + 1] for key in ("-C", "--output-schema", "--output-last-message")
    } == {
        "-C": assignments["u"],
        "--output-schema": str(schema),
        "--output-last-message": str(output),
    }
    assert command_proof(argv)["model_reasoning_effort"] == "low"
    validate_selector_paths(
        assignments,
        receipts,
        case_id="u",
        turn=1,
        workspace=schema.parent,
        schema=schema,
        output=output,
        fresh_output=True,
    )


def test_json_round_trip_retains_the_original_canonical_directory_identities(
    allocated: WorkspaceMaps,
) -> None:
    assignments, receipts = allocated
    restored = json.loads(json.dumps({"assignments": assignments, "receipts": receipts}))
    assert validate_workspaces(
        restored["assignments"], restored["receipts"], case_ids=("u", "v")
    ) == {case: Path(path) for case, path in assignments.items()}


@pytest.mark.parametrize(
    "change",
    [
        "missing_case",
        "foreign_case",
        "missing_receipt",
        "foreign_receipt",
        "receipt_path",
        "extra_field",
        "device_bool",
        "device_negative",
        "device_float",
        "inode_bool",
        "inode_zero",
        "inode_negative",
        "inode_string",
        "path_object",
        "relative",
        "trailing_slash",
        "dot_spelling",
        "device_changed",
        "inode_changed",
    ],
)
def test_persisted_mapping_tampering_is_rejected_without_repair(
    allocated: WorkspaceMaps, change: str
) -> None:
    original_assignments, original_receipts = allocated
    assignments: dict[str, Any] = copy.deepcopy(original_assignments)
    receipts: dict[str, Any] = copy.deepcopy(original_receipts)
    if change == "missing_case":
        assignments.pop("v")
    elif change == "foreign_case":
        assignments["foreign"] = assignments["v"]
    elif change == "missing_receipt":
        receipts.pop("v")
    elif change == "foreign_receipt":
        receipts["foreign"] = receipts["v"]
    elif change == "receipt_path":
        receipts["u"]["path"] = assignments["v"]
    elif change == "extra_field":
        receipts["u"]["unused"] = False
    elif change.startswith("device_"):
        receipts["u"]["device"] = {
            "device_bool": True,
            "device_negative": -1,
            "device_float": 1.0,
            "device_changed": receipts["u"]["device"] + 1,
        }[change]
    elif change.startswith("inode_"):
        receipts["u"]["inode"] = {
            "inode_bool": True,
            "inode_zero": 0,
            "inode_negative": -1,
            "inode_string": "1",
            "inode_changed": receipts["u"]["inode"] + 1,
        }[change]
    elif change == "path_object":
        assignments["u"] = Path(assignments["u"])
    else:
        assignments["u"] = {
            "relative": "workspace",
            "trailing_slash": assignments["u"] + "/",
            "dot_spelling": str(Path(assignments["u"]).parent)
            + "/./"
            + Path(assignments["u"]).name,
        }[change]
        receipts["u"]["path"] = assignments["u"]
    changed = copy.deepcopy((assignments, receipts))
    with pytest.raises(ValueError):
        validate_workspaces(assignments, receipts, case_ids=("u", "v"))
    assert (assignments, receipts) == changed
    assert validate_workspaces(original_assignments, original_receipts, case_ids=("u", "v"))


@pytest.mark.parametrize("kind", ["identical", "alias", "nested"])
def test_case_workspaces_cannot_share_or_overlap_directories(
    allocated: WorkspaceMaps, tmp_path: Path, kind: str
) -> None:
    assignments, receipts = copy.deepcopy(allocated)
    first = Path(assignments["u"])
    if kind == "identical":
        second = first
    elif kind == "alias":
        second = tmp_path / "case_alias"
        second.symlink_to(first, target_is_directory=True)
    else:
        second = first / "nested"
        second.mkdir()
    assignments["v"] = str(second)
    receipts["v"] = receipt(second)
    with pytest.raises(ValueError, match="unique|overlap|symlink|canonical"):
        validate_workspaces(assignments, receipts)


@pytest.mark.parametrize(
    "kind", ["missing", "replaced", "same_inode_symlink", "foreign_symlink", "dangling_symlink"]
)
def test_workspace_replacement_is_not_accepted_from_its_unchanged_path(
    allocated: WorkspaceMaps, tmp_path: Path, kind: str
) -> None:
    assignments, receipts = allocated
    workspace = Path(assignments["u"])
    moved = tmp_path / "original"
    workspace.rename(moved)
    if kind == "replaced":
        workspace.mkdir()
    elif kind == "same_inode_symlink":
        workspace.symlink_to(moved, target_is_directory=True)
    elif kind in ("foreign_symlink", "dangling_symlink"):
        foreign = tmp_path / "foreign"
        if kind == "foreign_symlink":
            foreign.mkdir()
        workspace.symlink_to(foreign, target_is_directory=True)
    with pytest.raises(ValueError):
        validate_workspaces(assignments, receipts)


def test_retargeted_ancestor_is_rejected_despite_retaining_the_leaf_inode(tmp_path: Path) -> None:
    base = tmp_path / "base"
    base.mkdir()
    assignments, receipts = allocate_workspaces(("u",), temp_root=base)
    moved = tmp_path / "original_base"
    base.rename(moved)
    base.symlink_to(moved, target_is_directory=True)
    assert Path(assignments["u"]).stat().st_ino == receipts["u"]["inode"]
    with pytest.raises(ValueError, match="canonical"):
        validate_workspaces(assignments, receipts)


def test_opened_workspace_must_still_have_the_same_named_identity(
    allocated: WorkspaceMaps, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assignments, receipts = allocated
    workspace = Path(assignments["u"])
    original_open = os.open
    changed = False

    def replacing_open(path: Any, flags: int, *args: Any, **kwargs: Any) -> int:
        nonlocal changed
        descriptor = original_open(path, flags, *args, **kwargs)
        if Path(path) == workspace and not changed:
            changed = True
            workspace.rename(tmp_path / "moved")
            workspace.mkdir()
        return descriptor

    monkeypatch.setattr(os, "open", replacing_open)
    with pytest.raises(ValueError, match="identity changed"):
        validate_workspaces(assignments, receipts)


def test_directory_contents_do_not_change_its_original_identity(allocated: WorkspaceMaps) -> None:
    assignments, receipts = allocated
    (Path(assignments["u"]) / "public.json").write_text('{"synthetic":true}')
    assert validate_workspaces(assignments, receipts)


def test_planning_launch_and_replay_share_exact_per_turn_paths(allocated: WorkspaceMaps) -> None:
    assignments, receipts = allocated
    schema, output = selector_paths(assignments, receipts, case_id="u", turn=3, fresh_output=True)
    assert schema.name == "decision.schema.json" and output.name == "answer-03.json"
    schema.write_text("{}")
    validate_selector_paths(
        assignments,
        receipts,
        case_id="u",
        turn=3,
        workspace=schema.parent,
        schema=schema,
        output=output,
        fresh_output=True,
    )
    output.write_text('{"synthetic":true}')
    validate_selector_paths(
        assignments,
        receipts,
        case_id="u",
        turn=3,
        workspace=schema.parent,
        schema=schema,
        output=output,
    )
    with pytest.raises(ValueError, match="fresh"):
        selector_paths(assignments, receipts, case_id="u", turn=3, fresh_output=True)
    second_schema, second_output = selector_paths(
        assignments, receipts, case_id="u", turn=4, fresh_output=True
    )
    assert second_schema == schema and second_output.name == "answer-04.json"


@pytest.mark.parametrize("turn", [0, -1, True, 1.0, "1"])
def test_selector_turn_requires_a_strict_positive_integer(
    allocated: WorkspaceMaps, turn: Any
) -> None:
    assignments, receipts = allocated
    with pytest.raises(ValueError, match="positive integer"):
        selector_paths(assignments, receipts, case_id="u", turn=turn)


@pytest.mark.parametrize(
    "change", ["case", "workspace", "schema", "output", "relative", "fresh_mode"]
)
def test_foreign_or_wrong_turn_selector_paths_fail_exact_comparison(
    allocated: WorkspaceMaps, change: str
) -> None:
    assignments, receipts = allocated
    schema, output = selector_paths(assignments, receipts, case_id="u", turn=2)
    schema.write_text("{}")
    kwargs: dict[str, Any] = {
        "case_id": "u",
        "turn": 2,
        "workspace": schema.parent,
        "schema": schema,
        "output": output,
    }
    if change == "case":
        kwargs["case_id"] = "foreign"
    elif change == "workspace":
        kwargs["workspace"] = assignments["v"]
    elif change == "schema":
        kwargs["schema"] = schema.parent / "other.schema.json"
    elif change == "output":
        kwargs["output"] = schema.parent / "answer-01.json"
    elif change == "relative":
        kwargs["output"] = "answer-02.json"
    else:
        kwargs["fresh_output"] = 1
    with pytest.raises(ValueError):
        validate_selector_paths(assignments, receipts, **kwargs)


def test_schema_is_required_for_command_validation_but_not_path_planning(
    allocated: WorkspaceMaps,
) -> None:
    assignments, receipts = allocated
    schema, output = selector_paths(assignments, receipts, case_id="u", turn=1)
    with pytest.raises(ValueError, match="schema must exist"):
        validate_selector_paths(
            assignments,
            receipts,
            case_id="u",
            turn=1,
            workspace=schema.parent,
            schema=schema,
            output=output,
        )


@pytest.mark.parametrize("leaf", ["schema", "output"])
@pytest.mark.parametrize(
    "kind", ["symlink_inside", "symlink_foreign", "dangling", "directory", "fifo", "hardlink"]
)
def test_selector_files_cannot_redirect_or_share_external_content(
    allocated: WorkspaceMaps, tmp_path: Path, leaf: str, kind: str
) -> None:
    assignments, receipts = allocated
    schema, output = selector_paths(assignments, receipts, case_id="u", turn=1)
    selected = schema if leaf == "schema" else output
    if selected != schema:
        schema.write_text("{}")
    foreign = tmp_path / "foreign.json"
    inside = schema.parent / "inside.json"
    if kind == "directory":
        selected.mkdir()
    elif kind == "fifo":
        os.mkfifo(selected)
    elif kind == "dangling":
        selected.symlink_to(foreign)
    elif kind == "symlink_inside":
        inside.write_text("{}")
        selected.symlink_to(inside)
    else:
        foreign.write_text("{}")
        if kind == "hardlink":
            os.link(foreign, selected)
        else:
            selected.symlink_to(foreign)
    with pytest.raises(ValueError, match="symlink|regular file"):
        validate_selector_paths(
            assignments,
            receipts,
            case_id="u",
            turn=1,
            workspace=schema.parent,
            schema=schema,
            output=output,
        )


def test_replaced_schema_during_open_is_rejected_before_any_content_read(
    allocated: WorkspaceMaps, monkeypatch: pytest.MonkeyPatch
) -> None:
    assignments, receipts = allocated
    schema, output = selector_paths(assignments, receipts, case_id="u", turn=1)
    schema.write_text("{}")
    original_open = os.open
    changed = False

    def replacing_open(path: Any, flags: int, *args: Any, **kwargs: Any) -> int:
        nonlocal changed
        descriptor = original_open(path, flags, *args, **kwargs)
        if Path(path) == schema and not changed:
            changed = True
            schema.rename(schema.parent / "original.schema.json")
            schema.write_text("{}")
        return descriptor

    monkeypatch.setattr(os, "open", replacing_open)
    with pytest.raises(ValueError, match="identity changed"):
        validate_selector_paths(
            assignments,
            receipts,
            case_id="u",
            turn=1,
            workspace=schema.parent,
            schema=schema,
            output=output,
        )
