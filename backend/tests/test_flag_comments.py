"""A module-level flag's comment must not call it off while its value is True (review P9)."""

from __future__ import annotations

import re
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "app"
#: Phrases that state the *current* default as off. "off until a paired run
#: passes" is a rule's history, not its default, and is not matched.
_SAYS_OFF = re.compile(r"\boff by default\b|\bfalse \(the default\)", re.IGNORECASE)
_FLAG = re.compile(r"^([A-Z][A-Z0-9_]+)\s*(?::[^=]*)?=\s*\(?\s*$|^([A-Z][A-Z0-9_]+)\s*=\s*(\w+)")


def _flags_documented_off() -> list[str]:
    drift: list[str] = []
    for path in sorted(APP.rglob("*.py")):
        lines = path.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            match = _FLAG.match(line)
            if not match:
                continue
            name = match[1] or match[2]
            value = match[3] if match[2] else (lines[i + 1].strip() if i + 1 < len(lines) else "")
            if not value.startswith("True"):
                continue
            start = i
            while start > 0 and lines[start - 1].lstrip().startswith("#"):
                start -= 1
            comment = " ".join(line.lstrip("#: ").strip() for line in lines[start:i])
            if _SAYS_OFF.search(comment):
                drift.append(f"{path.relative_to(APP)}:{i + 1} {name}")
    return drift


def test_no_flag_that_is_on_is_documented_as_off_by_default() -> None:
    assert _flags_documented_off() == []
