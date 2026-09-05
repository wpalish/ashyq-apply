#!/usr/bin/env python3
"""Print the state an agent must know before touching the repository.

Run it at the start of every session (`python scripts/handoff_check.py`) and
paste the output into the chat. It answers, from evidence rather than memory:
which branch and commit we are on, whether the previous agent left uncommitted
or unpushed work, whether the Alembic chain still has exactly one head, and
what docs/process/HANDOFF.md claims about where work stopped. A mismatch
between the tree and HANDOFF.md means the previous session was cut off — the
agent must reconcile before writing code, not guess.

Pure standard library; works on Windows, macOS and Linux; needs only `git`.
"""

from __future__ import annotations

import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HANDOFF = Path("docs/process/HANDOFF.md")
MIGRATIONS = Path("backend/migrations/versions")
STALE_AFTER_HOURS = 2
SECTIONS_TO_SHOW = ("## 1.", "## 2.", "## 3.", "## 4.", "## 5.", "## 7.", "## 10.")


def git(*args: str) -> str:
    try:
        out = subprocess.run(["git", *args], capture_output=True, text=True, check=False)
    except FileNotFoundError:
        sys.exit("git is not installed or not on PATH")
    return out.stdout.strip()


def header(title: str) -> None:
    print(f"\n=== {title} ===")


def main() -> int:
    root = git("rev-parse", "--show-toplevel")
    if not root:
        sys.exit("not inside a git repository")
    import os

    os.chdir(root)
    warnings: list[str] = []

    header("where")
    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    head = git("log", "-1", "--format=%h | %ci | %s")
    print(f"branch : {branch}")
    print(f"HEAD   : {head}")
    upstream = git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    if upstream:
        ahead_behind = git("rev-list", "--left-right", "--count", f"{upstream}...HEAD").split()
        if len(ahead_behind) == 2:
            behind, ahead = ahead_behind
            print(f"vs {upstream}: {ahead} unpushed, {behind} not pulled")
            if ahead != "0":
                warnings.append(f"{ahead} commit(s) on {branch} are NOT pushed — push before doing anything else")
            if behind != "0":
                warnings.append(f"{branch} is {behind} commit(s) behind {upstream} — `git pull --ff-only` first")
    else:
        warnings.append(f"branch {branch} has no upstream — `git push -u origin {branch}` as soon as there is a commit")

    header("last commits (who did what)")
    print(git("log", "-8", "--format=%h | %ci | %(trailers:key=Agent,valueonly,separator=%x2C) | %s"))
    subject = git("log", "-1", "--format=%s")
    if subject.lower().startswith("wip"):
        warnings.append("HEAD is a `wip:` commit — the previous agent was cut off mid-task; its message lists what is unfinished")
    last_iso = git("log", "-1", "--format=%cI")
    if last_iso:
        age_h = (datetime.now(timezone.utc) - datetime.fromisoformat(last_iso)).total_seconds() / 3600
        print(f"last commit age: {age_h:.1f} h")

    header("uncommitted work")
    dirty = git("status", "--porcelain")
    if dirty:
        lines = dirty.splitlines()
        print("\n".join(lines[:40]))
        if len(lines) > 40:
            print(f"... and {len(lines) - 40} more")
        warnings.append(f"{len(lines)} uncommitted path(s) — the previous session was probably cut off; read HANDOFF §4 and `git diff` before touching them")
    else:
        print("working tree clean")
    stash = git("stash", "list")
    if stash:
        print("stash:\n" + stash)
        warnings.append("there are stashes — decide with the owner whether they are work or junk")

    header("unpushed commits on any local branch")
    unpushed = git("log", "--branches", "--not", "--remotes", "--format=%h | %D | %s")
    print(unpushed or "none")
    if unpushed:
        warnings.append("some local branches have commits that are not on origin")

    header("alembic chain")
    revisions: dict[str, list[str]] = {}
    if MIGRATIONS.is_dir():
        rev_re = re.compile(r"^revision(?:\s*:\s*\w+)?\s*=\s*['\"]([0-9a-zA-Z_]+)['\"]", re.M)
        down_re = re.compile(r"^down_revision(?:\s*:\s*[^=\n]+)?\s*=\s*(.+)$", re.M)
        for path in sorted(MIGRATIONS.glob("*.py")):
            text = path.read_text(encoding="utf-8", errors="replace")
            rev = rev_re.search(text)
            if not rev:
                continue
            down = down_re.search(text)
            parents = re.findall(r"['\"]([0-9a-zA-Z_]+)['\"]", down.group(1)) if down else []
            revisions[rev.group(1)] = parents
        referenced = {p for parents in revisions.values() for p in parents}
        heads = sorted(r for r in revisions if r not in referenced)
        print(f"{len(revisions)} revisions, heads: {heads}")
        if len(heads) != 1:
            warnings.append(f"alembic has {len(heads)} heads — `alembic upgrade head` will fail; STOP and report, do not create migrations")
    else:
        print(f"{MIGRATIONS} not found")

    header(f"{HANDOFF} — what the previous agent said")
    if HANDOFF.exists():
        text = HANDOFF.read_text(encoding="utf-8")
        show = False
        for line in text.splitlines():
            if line.startswith("## "):
                show = line.startswith(SECTIONS_TO_SHOW)
            if show:
                print(line)
        holder = re.search(r"Holder:\s*(\S+)", text)
        if holder and holder.group(1).lower() not in {"nobody", "none", "-", "—"}:
            print(f"\nbaton holder recorded as: {holder.group(1)}")
            if last_iso and age_h > STALE_AFTER_HOURS and not dirty:
                warnings.append(f"HANDOFF says {holder.group(1)} holds the baton but nothing was committed for {age_h:.0f} h — treat that session as cut off; take the baton and say so in §1 and §11")
    else:
        warnings.append(f"{HANDOFF} is missing — create it from the template before writing code")

    header("verdict")
    if warnings:
        for w in warnings:
            print(f"! {w}")
        print("\nReconcile the points above with docs/process/HANDOFF.md, then run the gates to establish a baseline.")
    else:
        print("clean handoff: tree matches origin, one alembic head. Read HANDOFF §5 'Next step' and run the gates before changing anything.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
