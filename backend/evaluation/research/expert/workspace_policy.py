"""Canonical V6 case workspaces and exact filesystem identity replay.

Only allocation normalizes the trusted temporary root. Persisted assignments,
receipts and selector paths must already have their canonical spelling. The
parent allocates once, hash-binds both mappings before baseline work, and checks
them before dispatch and after a selector returns. This module performs no
model, provider, content or label reads and never repairs a saved assignment.
"""

from __future__ import annotations

import os
import re
import stat
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, TypedDict


class WorkspaceReceipt(TypedDict):
    path: str
    device: int
    inode: int


def _cases(values: Sequence[str]) -> tuple[str, ...]:
    if isinstance(values, str | bytes) or not isinstance(values, Sequence):
        raise ValueError("Case IDs must be a nonempty sequence")
    cases = tuple(values)
    if not cases or any(
        type(case) is not str or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", case) is None
        for case in cases
    ):
        raise ValueError("Case IDs must be nonempty safe identifiers")
    if len(set(cases)) != len(cases):
        raise ValueError("Case IDs must be unique")
    return cases


def _declared_path(value: str | Path) -> Path:
    if not isinstance(value, Path) and type(value) is not str:
        raise ValueError("Declared paths must be absolute canonical strings or Paths")
    spelling = str(value)
    if not spelling or "\x00" in spelling:
        raise ValueError("Declared paths must be absolute canonical paths")
    path = Path(spelling)
    if not path.is_absolute() or str(path) != spelling:
        raise ValueError("Declared paths must use their exact absolute canonical spelling")
    return path


def _directory(value: str | Path) -> tuple[Path, os.stat_result]:
    path = _declared_path(value)
    descriptor: int | None = None
    try:
        before = path.lstat()
        if stat.S_ISLNK(before.st_mode):
            raise ValueError("Workspace cannot be a symlink")
        if not stat.S_ISDIR(before.st_mode):
            raise ValueError("Workspace must be a directory")
        if path.resolve(strict=True) != path:
            raise ValueError("Workspace must already use its canonical spelling")
        descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        opened = os.fstat(descriptor)
        after = path.lstat()
        if (
            not stat.S_ISDIR(opened.st_mode)
            or not stat.S_ISDIR(after.st_mode)
            or (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino)
            or (after.st_dev, after.st_ino) != (opened.st_dev, opened.st_ino)
            or path.resolve(strict=True) != path
        ):
            raise ValueError("Workspace identity changed during validation")
        return path, opened
    except (OSError, RuntimeError) as exc:
        raise ValueError("Workspace is missing, inaccessible or replaced") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)


def allocate_workspaces(
    case_ids: Sequence[str], *, temp_root: str | Path | None = None
) -> tuple[dict[str, str], dict[str, WorkspaceReceipt]]:
    """Create the entire cohort once under a canonical trusted temporary root.

    The caller owns cleanup. If allocation fails, it must stop before baseline
    or selector work; existing allocated directories are never replaced/reused.
    """
    cases = _cases(case_ids)
    try:
        root = Path(tempfile.gettempdir() if temp_root is None else temp_root).resolve(strict=True)
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        raise ValueError("Temporary root must be an existing directory") from exc
    _directory(root)
    assignments: dict[str, str] = {}
    receipts: dict[str, WorkspaceReceipt] = {}
    for case in cases:
        path, identity = _directory(
            tempfile.mkdtemp(prefix=f"unimatch-blind-{case}-", dir=str(root))
        )
        if path.parent != root:
            raise ValueError("Allocated workspace escaped its declared temporary root")
        assignments[case] = str(path)
        receipts[case] = {"path": str(path), "device": identity.st_dev, "inode": identity.st_ino}
    validate_workspaces(assignments, receipts, case_ids=cases)
    return assignments, receipts


def validate_workspaces(
    assignments: Mapping[str, Any],
    receipts: Mapping[str, Any],
    *,
    case_ids: Sequence[str] | None = None,
) -> dict[str, Path]:
    """Reject missing/foreign cases, path aliases and changed directory identities.

    Receipts are authoritative only when the parent binds their original bytes
    to its immutable trial. Rewriting both mappings cannot establish provenance.
    """
    if not isinstance(assignments, Mapping) or not isinstance(receipts, Mapping):
        raise ValueError("Assignments and receipts must be mappings")
    cases = _cases(tuple(assignments) if case_ids is None else case_ids)
    if set(assignments) != set(cases) or set(receipts) != set(cases):
        raise ValueError("Workspace assignments/receipts must contain exactly the declared cases")
    paths: dict[str, Path] = {}
    identities: set[tuple[int, int]] = set()
    for case in cases:
        spelling = assignments[case]
        receipt = receipts[case]
        if type(spelling) is not str:
            raise ValueError("Persisted workspace assignments must be canonical path strings")
        if not isinstance(receipt, Mapping) or set(receipt) != {"path", "device", "inode"}:
            raise ValueError("Workspace receipt must contain only path, device and inode")
        if (
            type(receipt["path"]) is not str
            or receipt["path"] != spelling
            or type(receipt["device"]) is not int
            or receipt["device"] < 0
            or type(receipt["inode"]) is not int
            or receipt["inode"] <= 0
        ):
            raise ValueError("Workspace receipt path/identity has invalid strict types or differs")
        path, observed = _directory(spelling)
        identity = (observed.st_dev, observed.st_ino)
        if identity != (receipt["device"], receipt["inode"]):
            raise ValueError("Workspace device/inode differs from its original receipt")
        if identity in identities or any(
            path == prior or path.is_relative_to(prior) or prior.is_relative_to(path)
            for prior in paths.values()
        ):
            raise ValueError("Workspace assignments must be unique and must not overlap")
        paths[case] = path
        identities.add(identity)
    return paths


def _expected_paths(workspace: Path, turn: int) -> tuple[Path, Path]:
    if type(turn) is not int or turn <= 0:
        raise ValueError("Selector turn must be a positive integer")
    return workspace / "decision.schema.json", workspace / f"answer-{turn:02d}.json"


def _file(path: Path, *, required: bool, fresh: bool = False) -> None:
    """Check existing leaf files without reading their bytes or following links."""
    descriptor: int | None = None
    try:
        try:
            before = path.lstat()
        except FileNotFoundError:
            if required:
                raise ValueError("Selector schema must exist before command validation") from None
            return
        if stat.S_ISLNK(before.st_mode):
            raise ValueError("Selector schema/output cannot be a symlink")
        if fresh:
            raise ValueError("Selector output must be a fresh file")
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise ValueError("Selector schema/output must be a single-link regular file")
        if path.resolve(strict=True) != path:
            raise ValueError("Selector schema/output path must already be canonical")
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        opened = os.fstat(descriptor)
        after = path.lstat()
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_nlink != 1
            or not stat.S_ISREG(after.st_mode)
            or after.st_nlink != 1
            or (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino)
            or (after.st_dev, after.st_ino) != (opened.st_dev, opened.st_ino)
            or path.resolve(strict=True) != path
        ):
            raise ValueError("Selector schema/output identity changed during validation")
    except (OSError, RuntimeError) as exc:
        raise ValueError("Selector schema/output is inaccessible or replaced") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)


def selector_paths(
    assignments: Mapping[str, Any],
    receipts: Mapping[str, Any],
    *,
    case_id: str,
    turn: int,
    fresh_output: bool = False,
) -> tuple[Path, Path]:
    """Derive exact per-turn paths, permitting a schema not yet written."""
    if type(fresh_output) is not bool:
        raise ValueError("Fresh-output mode must be boolean")
    workspaces = validate_workspaces(assignments, receipts)
    if type(case_id) is not str or case_id not in workspaces:
        raise ValueError("Selector case lacks its original workspace assignment")
    schema, output = _expected_paths(workspaces[case_id], turn)
    _file(schema, required=False)
    _file(output, required=False, fresh=fresh_output)
    validate_workspaces(assignments, receipts)
    return schema, output


def validate_selector_paths(
    assignments: Mapping[str, Any],
    receipts: Mapping[str, Any],
    *,
    case_id: str,
    turn: int,
    workspace: str | Path,
    schema: str | Path,
    output: str | Path,
    fresh_output: bool = False,
) -> None:
    """Require exact declared paths; never resolve a saved alias into acceptance.

    The schema must exist. A failed/timed-out turn may have no output; an
    existing output is allowed only for replay and must remain a regular file.
    Content hashes and isolation argv/profile validation belong to the parent.
    """
    expected_schema, expected_output = selector_paths(
        assignments, receipts, case_id=case_id, turn=turn, fresh_output=fresh_output
    )
    if (
        _declared_path(workspace) != expected_schema.parent
        or _declared_path(schema) != expected_schema
        or _declared_path(output) != expected_output
    ):
        raise ValueError(
            "Selector workspace/schema/output differs from its exact assigned turn path"
        )
    _file(expected_schema, required=True)
    _file(expected_output, required=False, fresh=fresh_output)
    validate_workspaces(assignments, receipts)
