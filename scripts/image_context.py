#!/usr/bin/env python3
"""Reproduce a Docker image's build context without Docker (GATE-2).

    image_context.py stage CONTEXT DEST [--link NAME=TARGET ...]

Copies into DEST exactly what ``docker build CONTEXT`` would send: the files git tracks under CONTEXT
(what CI's checkout has; pre_merge.sh has already required a clean tree), minus what
``CONTEXT/.dockerignore`` excludes, with Docker's matching rules (patterns anchored at the context root,
``*`` within one path segment, ``**`` across segments, ``!`` re-includes, the last matching rule wins, a
pattern that matches a directory excludes everything below it). Then every ``COPY`` source of
``CONTEXT/Dockerfile`` (``--from=`` stages excepted) must exist in that set, and each ``--link`` makes
``DEST/NAME`` a symlink to TARGET (node_modules: ``npm ci`` cannot run offline, the lockfile's tree is
already installed). The build command then runs in DEST, where a file the image does not get is missing.

On 2026-10-25 the web image's ``npm run build`` failed in CI because ``.dockerignore`` dropped ``e2e/``,
which two Playwright configs the build type-checks import; ``pre_merge.sh`` ran the build in
``frontend/``, where ``e2e/`` exists, and was GREEN.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Rule:
    pattern: str
    regex: re.Pattern[str]
    exclude: bool  # False for a `!pattern` exception


def _translate(pattern: str) -> str:
    """One .dockerignore pattern -> a regex over a slash-separated path relative to the context."""
    out = ["^"]
    i = 0
    while i < len(pattern):
        c = pattern[i]
        if c == "*":
            if pattern[i + 1 : i + 2] == "*":
                i += 1
                if pattern[i + 1 : i + 2] == "/":
                    i += 1
                    out.append("(?:.*/)?")
                else:
                    out.append(".*")
            else:
                out.append("[^/]*")
        elif c == "?":
            out.append("[^/]")
        elif c == "[":
            end = pattern.find("]", i + 1)
            if end == -1:
                out.append(re.escape(c))
            else:
                body = pattern[i + 1 : end].replace("\\", "\\\\")
                out.append("[" + body + "]")
                i = end
        elif c == "\\" and i + 1 < len(pattern):
            i += 1
            out.append(re.escape(pattern[i]))
        else:
            out.append(re.escape(c))
        i += 1
    out.append("$")
    return "".join(out)


def parse_dockerignore(text: str) -> list[Rule]:
    rules = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        exclude = not line.startswith("!")
        if not exclude:
            line = line[1:].strip()
        line = os.path.normpath(line).replace(os.sep, "/").lstrip("/")
        if line in ("", "."):
            continue
        rules.append(Rule(line, re.compile(_translate(line)), exclude))
    return rules


def excluded(path: str, rules: list[Rule]) -> bool:
    """Docker's MatchesOrParentMatches: a rule hits a path if it matches the path or a parent of it."""
    parts = path.split("/")
    prefixes = ["/".join(parts[: n + 1]) for n in range(len(parts))]
    result = False
    for rule in rules:
        if any(rule.regex.match(p) for p in prefixes):
            result = rule.exclude
    return result


def tracked(context: Path) -> list[str]:
    done = subprocess.run(
        ["git", "-C", str(context), "ls-files", "-z", "--", "."],
        capture_output=True,
        check=True,
    )
    return sorted(p for p in done.stdout.decode().split("\0") if p)


def instructions(dockerfile: str) -> list[tuple[str, str]]:
    """(INSTRUCTION, arguments) with continuation lines joined and comments dropped."""
    found: list[tuple[str, str]] = []
    pending = ""
    for raw in dockerfile.splitlines():
        line = raw.strip()
        if not pending and (not line or line.startswith("#")):
            continue
        if pending and line.startswith("#"):
            continue
        if line.endswith("\\"):
            pending += line[:-1].rstrip() + " "
            continue
        whole = (pending + line).strip()
        pending = ""
        if whole:
            keyword, _, rest = whole.partition(" ")
            found.append((keyword.upper(), rest.strip()))
    return found


def copy_sources(dockerfile: str) -> list[str]:
    """The context paths the Dockerfile's COPY/ADD instructions read (``--from=`` copies excepted)."""
    sources: list[str] = []
    for keyword, rest in instructions(dockerfile):
        if keyword not in ("COPY", "ADD"):
            continue
        words = list(json.loads(rest)) if rest.startswith("[") else shlex.split(rest)
        flags = [w for w in words if w.startswith("--")]
        if any(f.startswith("--from=") for f in flags):
            continue
        args = [w for w in words if not w.startswith("--")]
        sources += args[:-1]
    return sources


def run_steps(dockerfile: str) -> list[str]:
    """Every RUN instruction, one line each (backend/tests/test_pre_merge_script.py holds the list)."""
    return [
        re.sub(r"\s+", " ", rest) for keyword, rest in instructions(dockerfile) if keyword == "RUN"
    ]


def stage(context: Path, dest: Path, links: list[str]) -> int:
    ignore = context / ".dockerignore"
    rules = parse_dockerignore(ignore.read_text()) if ignore.exists() else []
    files = tracked(context)
    kept = [p for p in files if not excluded(p, rules)]
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    for rel in kept:
        src, out = context / rel, dest / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        if src.is_symlink():
            out.symlink_to(os.readlink(src))
        elif src.exists():
            shutil.copy2(src, out)
    print(
        f"staged {len(kept)} of {len(files)} tracked files of {context.name}/ into {dest}"
        f" ({len(files) - len(kept)} excluded by .dockerignore)"
    )

    missing = []
    dockerfile = (context / "Dockerfile").read_text()
    for source in copy_sources(dockerfile):
        norm = os.path.normpath(source).replace(os.sep, "/").lstrip("/")
        if norm in ("", "."):
            continue
        hit = any(
            fnmatch.fnmatchcase(p, norm) or p.startswith(norm.rstrip("/") + "/") for p in kept
        )
        if not hit:
            missing.append(source)
    for source in missing:
        why = "excluded by .dockerignore" if (context / source).exists() else "not tracked"
        print(
            f"image_context: Dockerfile COPY {source}: not in the build context ({why})",
            file=sys.stderr,
        )

    for link in links:
        name, _, target = link.partition("=")
        if not name or not target:
            print(f"image_context: --link wants NAME=TARGET, got {link!r}", file=sys.stderr)
            return 2
        (dest / name).symlink_to(Path(target).resolve())
        print(f"linked {name} -> {Path(target).resolve()}")
    return 1 if missing else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    staging = sub.add_parser("stage")
    staging.add_argument("context", type=Path)
    staging.add_argument("dest", type=Path)
    staging.add_argument("--link", action="append", default=[])
    args = parser.parse_args(argv)
    return stage(args.context.resolve(), args.dest, args.link)


if __name__ == "__main__":
    sys.exit(main())
