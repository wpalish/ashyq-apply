"""Read-only checks for ASHYQ team configuration and evidence.

These checks do not launch models, create OS locks, authenticate agent identities,
run the claimed tests, or authorize a merge/deployment. They validate supplied
records and must be matched to real runtime logs by the primary/integrator.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
from pathlib import Path

TEAM = Path(__file__).resolve().parent
ROLES = {"ashyq-planner", "ashyq-developer", "ashyq-qa", "ashyq-reviewer"}
SHA = re.compile(r"^[0-9a-f]{40}$")


def load_plan(path: Path = TEAM / "crew.json") -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_plan(plan: dict) -> list[str]:
    errors = []
    tasks = plan.get("tasks", [])
    ids = [t.get("id") for t in tasks]
    if len(ids) != len(set(ids)):
        errors.append("Duplicate task IDs")
    if set(plan.get("required_roles", [])) != ROLES:
        errors.append("Four required independent roles must be retained")
    if plan.get("minimum_independent_roles_per_task", 0) < 4:
        errors.append("Minimum independent roles cannot be below four")
    graph = {t["id"]: t.get("dependencies", []) for t in tasks}
    for task in tasks:
        tid = task["id"]
        if not ROLES.issubset(set(task.get("required_roles", []))):
            errors.append(f"{tid}: missing required roles")
        if not task.get("allowed_paths") or not task.get("acceptance"):
            errors.append(f"{tid}: empty scope or acceptance")
        for p in task.get("allowed_paths", []):
            if p.startswith(("/", "\\")) or ".." in p.split("/"):
                errors.append(f"{tid}: unsafe scope pattern {p}")
        for dep in graph[tid]:
            if dep not in graph:
                errors.append(f"{tid}: unknown dependency {dep}")
    visiting, visited = set(), set()
    def visit(node):
        if node in visiting:
            errors.append(f"Dependency cycle at {node}")
            return
        if node in visited or node not in graph:
            return
        visiting.add(node)
        for dep in graph[node]:
            visit(dep)
        visiting.remove(node)
        visited.add(node)
    for tid in graph:
        visit(tid)
    return errors


def task_by_id(plan: dict, task_id: str) -> dict:
    for task in plan["tasks"]:
        if task["id"] == task_id:
            return task
    raise ValueError(f"Unknown task: {task_id}")


def check_scope(task: dict, repo: Path, baseline: str, head: str) -> tuple[list[str], list[str]]:
    if not SHA.fullmatch(baseline) or not SHA.fullmatch(head):
        raise ValueError("Provide full 40-character commit SHAs, not branch names")
    for ref in (baseline, head):
        subprocess.run(["git", "rev-parse", "--verify", ref + "^{commit}"], cwd=repo,
                       check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    result = subprocess.run(["git", "diff", "--name-only", "--no-renames", "-z", baseline, head, "--"],
                            cwd=repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    paths = [p.decode("utf-8") for p in result.stdout.split(b"\0") if p]
    unexpected = [p for p in paths if not any(fnmatch.fnmatchcase(p, pattern) for pattern in task["allowed_paths"])]
    return paths, unexpected


def check_packet(task: dict, packet: dict, artifact_root: Path) -> list[str]:
    errors = []
    if packet.get("task_id") != task["id"]:
        errors.append("Packet task_id mismatch")
    base, candidate = packet.get("baseline_sha", ""), packet.get("candidate_sha", "")
    if not SHA.fullmatch(base) or not SHA.fullmatch(candidate):
        errors.append("Baseline/candidate must be complete commit SHAs")
    root = artifact_root.resolve()
    def artifact(value, label):
        if not isinstance(value, str) or not value:
            errors.append(f"{label}: missing artifact path")
            return
        path = (root / value).resolve()
        if not path.is_relative_to(root):
            errors.append(f"{label}: artifact must stay under packet directory")
        elif not path.is_file() or path.stat().st_size == 0:
            errors.append(f"{label}: artifact missing/empty: {value}")
    participants = packet.get("participants", [])
    seen_roles, seen_refs = set(), set()
    for part in participants:
        role, ref = part.get("role", ""), part.get("invocation_ref", "")
        if role in seen_roles:
            errors.append(f"Duplicate final approval role: {role}")
        seen_roles.add(role)
        if not ref or "REPLACE" in ref.upper() or ref in seen_refs:
            errors.append(f"{role}: missing/placeholder/reused invocation reference")
        seen_refs.add(ref)
        expected = base if role == "ashyq-planner" else candidate
        if part.get("checked_sha") != expected:
            errors.append(f"{role}: approval targets the wrong SHA")
        if part.get("verdict") != "PASS":
            errors.append(f"{role}: verdict is not PASS")
        artifact(part.get("evidence_file"), role)
    missing = set(task["required_roles"]) - seen_roles
    if missing:
        errors.append("Missing roles: " + ", ".join(sorted(missing)))
    tests = packet.get("tests", [])
    if not tests:
        errors.append("No executed test gates recorded")
    for test in tests:
        if not test.get("command") or "REPLACE" in test.get("command", "").upper():
            errors.append("Test command missing/placeholder")
        if test.get("checked_sha") != candidate:
            errors.append("Test executed against a different SHA")
        if test.get("status") != "PASS" or test.get("exit_code") != 0:
            errors.append("A test is failed, blocked or not run")
        artifact(test.get("log_file"), "test log")
    items = packet.get("acceptance_items", [])
    required = set(task["acceptance"])
    recorded = {i.get("criterion") for i in items}
    if not required.issubset(recorded):
        errors.append("Not all task-card acceptance criteria are recorded verbatim")
    for item in items:
        if item.get("status") != "PASS":
            errors.append("Acceptance criterion is not PASS")
        artifact(item.get("evidence_file"), "acceptance")
    if packet.get("blockers"):
        errors.append("Packet still has blockers")
    if packet.get("scope_check") != "PASS":
        errors.append("Scope check not recorded as PASS; run scope command separately")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=TEAM / "crew.json")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("plan")
    scope = sub.add_parser("scope")
    scope.add_argument("--task", required=True)
    scope.add_argument("--repo", type=Path, required=True)
    scope.add_argument("--base", required=True)
    scope.add_argument("--head", required=True)
    packet = sub.add_parser("packet")
    packet.add_argument("--task", required=True)
    packet.add_argument("--file", type=Path, required=True)
    args = parser.parse_args()
    try:
        plan = load_plan(args.plan)
        errors = validate_plan(plan)
        if errors:
            raise ValueError("; ".join(errors))
        if args.command == "plan":
            print(f"PLAN OK: {len(plan['tasks'])} tasks; 4 independent roles minimum. No agents launched.")
            return 0
        task = task_by_id(plan, args.task)
        if args.command == "scope":
            changed, unexpected = check_scope(task, args.repo.resolve(), args.base, args.head)
            print(json.dumps({"changed": changed, "outside_scope": unexpected}, indent=2, ensure_ascii=False))
            return 1 if unexpected else 0
        data = json.loads(args.file.read_text(encoding="utf-8"))
        errors = check_packet(task, data, args.file.parent)
        if errors:
            print("PACKET BLOCKED:\n- " + "\n- ".join(errors))
            return 1
        print("PACKET STRUCTURE OK. Match records to actual runtime logs; not a merge/deploy approval.")
        return 0
    except (ValueError, OSError, KeyError, TypeError, subprocess.CalledProcessError) as exc:
        print(f"BLOCKED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
