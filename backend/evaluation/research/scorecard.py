"""One table for one paired run: what changed, against the signed corpus.

``python -m evaluation.research.scorecard RUN_DIR`` reads the layout the
``expert_paired`` workflow uploads (``<case>-<arm>/<stamp>/capture.json``),
scores every arm and repetition with the official scorer, and adds what the
scorer's totals hide:

* the outcome of every known label (hit, missed, wrong value, wrong scope,
  unsupported), so a miss can be traced to a cause;
* every wrong claim and every unlabelled answer, which the scorer only counts;
* the six core questions an applicant asks first, answered or not;
* the cost of each case against the per-university budget.

A label counts as gained or lost only when every repetition of one arm agrees
and every repetition of the other arm disagrees; anything else is reported as
unstable rather than as a result.

Plan approved by the owner on 2026-10-05 ("Начинай выполнение по плану");
the targets below are its Definition of Done.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .metrics import adjudicate, score
from .schema import Capture, Dataset, Prediction

#: Definition of Done, metric targets (docs/process/SEARCH_DEFINITION_OF_DONE.md).
TARGETS: dict[str, tuple[str, float]] = {
    "claim_precision": (">=", 0.95),
    "wrong_scope_claim_rate": ("<=", 0.03),
}
#: Definition of Done, per-university budget.
BUDGET: dict[str, float] = {"search_calls": 6, "http_fetches": 60, "latency_seconds": 120.0}

#: The six questions an applicant asks first (app.pipeline.runner.CORE_QUESTIONS),
#: as the prediction keys that answer each. A key outside the corpus mapping is
#: written ``unmapped.<claim type>`` by map_claims, and still answers a question.
CORE_QUESTIONS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "english",
        re.compile(
            r"^(ielts\.overall|english_evidence\.[a-z0-9_]+\.minimum"
            r"|unmapped\.(ielts_min_overall|toefl_min_total|duolingo_min))$"
        ),
    ),
    ("gpa", re.compile(r"^(gpa|min_gpa|unmapped\.min_gpa)$")),
    ("deadline", re.compile(r"^(deadline|unmapped\.admission_deadline)$")),
    ("cost", re.compile(r"^(tuition|unmapped\.(tuition|total_cost_of_attendance))$")),
    ("scholarship", re.compile(r"^(scholarships\.[^.]+\.exists|unmapped\.scholarship_exists)$")),
    (
        "scholarship_international",
        re.compile(
            r"^(scholarships\.[^.]+\.applicability\.(international|nationality)"
            r"|unmapped\.scholarship_(international_eligible|citizenship_restriction))$"
        ),
    ),
)

#: The repetition directories the workflow writes, oldest first.
_ARM_DIR = re.compile(r"^(?P<case>[a-z0-9_]+)-(?P<arm>off|on)$")


@dataclass
class Arm:
    """One arm of a paired run: its captures, one list per repetition."""

    name: str
    repetitions: list[Capture] = field(default_factory=list)
    #: case id -> (access, pages checked, pages failed) from the raw trace.
    access: dict[str, tuple[str, int, int]] = field(default_factory=dict)


def _answered(predictions: list[Prediction]) -> list[Prediction]:
    """The predictions the scorer counts: a value, and one copy of each."""
    unique: dict[str, Prediction] = {}
    for p in predictions:
        if p.value is not None and p.value != "UNKNOWN":
            unique[p.model_dump_json()] = p
    return list(unique.values())


def label_outcomes(dataset: Dataset, capture: Capture) -> dict[str, Any]:
    """Every known label's outcome, every wrong claim, every unlabelled answer."""
    observed = {o.case_id: o for o in capture.observations}
    labels_out: list[dict[str, Any]] = []
    wrong: list[dict[str, Any]] = []
    unlabelled: list[dict[str, Any]] = []
    for case in dataset.cases:
        observation = observed.get(case.id)
        predictions = _answered(observation.predictions) if observation else []
        labels = {label.key: label for label in case.labels}
        by_key: dict[str, list[Prediction]] = defaultdict(list)
        for p in predictions:
            label = labels.get(p.key)
            verdict = adjudicate(p, label)
            by_key[p.key].append(p)
            if not verdict.labelled:
                unlabelled.append(
                    {
                        "case": case.id,
                        "key": p.key,
                        "value": p.value,
                        "url": str(p.evidence.url) if p.evidence else None,
                        "label_status": label.status if label else None,
                    }
                )
            elif not verdict.correct:
                wrong.append(
                    {
                        "case": case.id,
                        "key": p.key,
                        "value": p.value,
                        "expected": label.value if label else None,
                        "why": _why(verdict),
                        "url": str(p.evidence.url) if p.evidence else None,
                    }
                )
        for label in case.labels:
            if label.status != "known":
                continue
            ours = by_key.get(label.key, [])
            verdicts = [adjudicate(p, label) for p in ours]
            if any(v.correct for v in verdicts):
                outcome = "hit"
            elif not verdicts:
                outcome = "missed"
            elif any(v.value_matches and v.valid_scope for v in verdicts):
                outcome = "unsupported"
            elif any(v.value_matches for v in verdicts):
                outcome = "wrong_scope"
            else:
                outcome = "wrong_value"
            labels_out.append(
                {
                    "case": case.id,
                    "key": label.key,
                    "outcome": outcome,
                    "expected": label.value,
                    "ours": [p.value for p in ours],
                }
            )
    return {"labels": labels_out, "wrong_claims": wrong, "unlabelled": unlabelled}


def _why(verdict: Any) -> str:
    if not verdict.value_matches:
        return "wrong_value"
    if not verdict.valid_scope:
        return "wrong_scope"
    return "unsupported"


def core_coverage(capture: Capture) -> dict[str, list[str]]:
    """Case id -> the core questions any prediction answers."""
    out: dict[str, list[str]] = {}
    for o in capture.observations:
        keys = {p.key for p in _answered(o.predictions)}
        out[o.case_id] = [
            name for name, pattern in CORE_QUESTIONS if any(pattern.match(k) for k in keys)
        ]
    return out


def cost(capture: Capture) -> dict[str, dict[str, float | None]]:
    """Case id -> queries, reads and seconds, with the budget's verdict."""
    out: dict[str, dict[str, float | None]] = {}
    for o in capture.observations:
        t = o.telemetry
        row: dict[str, float | None] = {
            "search_calls": t.search_calls,
            "http_fetches": t.http_fetches,
            "latency_seconds": round(t.latency_seconds, 1) if t.latency_seconds else None,
        }
        over = [k for k, limit in BUDGET.items() if (row.get(k) or 0) > limit]
        row["over_budget"] = len(over)
        out[o.case_id] = row
    return out


def load_run(run_dir: Path) -> dict[str, Arm]:
    """Arms of a paired run, each with its captures merged per repetition."""
    per_arm: dict[str, dict[str, list[Path]]] = defaultdict(lambda: defaultdict(list))
    for capture_path in sorted(run_dir.glob("*/*/capture.json")):
        match = _ARM_DIR.match(capture_path.parent.parent.name)
        if match:
            per_arm[match["arm"]][match["case"]].append(capture_path)
    if not per_arm:
        single = run_dir / "capture.json" if run_dir.is_dir() else run_dir
        arm = Arm(name="run", repetitions=[_read(single)])
        return {"run": arm}
    arms: dict[str, Arm] = {}
    for name, cases in sorted(per_arm.items()):
        arm = Arm(name=name)
        depth = max(len(paths) for paths in cases.values())
        for index in range(depth):
            parts = [_read(paths[index]) for paths in cases.values() if index < len(paths)]
            merged = parts[0].model_copy(
                update={"observations": [o for part in parts for o in part.observations]}
            )
            arm.repetitions.append(merged)
        for case_id, paths in cases.items():
            raw = next(paths[0].parent.glob("*.raw.json"), None)
            if raw is not None:
                arm.access[case_id] = _access(raw)
        arms[name] = arm
    return arms


def _read(path: Path) -> Capture:
    return Capture.model_validate_json(path.read_text(encoding="utf-8"))


def _access(raw_path: Path) -> tuple[str, int, int]:
    try:
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
        inst = (raw["canary"]["institutions"] or [{}])[0]
        return (
            str(inst.get("access") or "unknown"),
            int(inst.get("pages_checked") or 0),
            int(inst.get("pages_failed") or 0),
        )
    except (OSError, ValueError, KeyError, IndexError, TypeError):
        return ("unknown", 0, 0)


def build(dataset: Dataset, arms: dict[str, Arm], *, allow_drafts: bool = False) -> dict[str, Any]:
    """The scorecard as data: metrics, label outcomes, changes, core, cost."""
    card: dict[str, Any] = {"dataset_version": dataset.version, "arms": {}}
    for name, arm in arms.items():
        reps = []
        for capture in arm.repetitions:
            report = score(dataset, capture, allow_drafts=allow_drafts)
            reps.append(
                {
                    "pipeline_sha": capture.pipeline_sha,
                    "metrics": report["metrics"],
                    "outcomes": label_outcomes(dataset, capture),
                    "core": core_coverage(capture),
                    "cost": cost(capture),
                }
            )
        card["arms"][name] = {"repetitions": reps, "access": arm.access}
    if {"off", "on"} <= set(arms):
        card["changes"] = stable_changes(card["arms"]["off"], card["arms"]["on"])
    card["targets"] = check_targets(card)
    return card


def stable_changes(off: dict[str, Any], on: dict[str, Any]) -> dict[str, list[str]]:
    """Labels every ``on`` repetition hits and every ``off`` one misses, or the reverse."""

    def hits(arm: dict[str, Any]) -> list[set[str]]:
        return [
            {f"{x['case']}:{x['key']}" for x in rep["outcomes"]["labels"] if x["outcome"] == "hit"}
            for rep in arm["repetitions"]
        ]

    off_hits, on_hits = hits(off), hits(on)
    always_on = set.intersection(*on_hits) if on_hits else set()
    never_on = set.union(*on_hits) if on_hits else set()
    always_off = set.intersection(*off_hits) if off_hits else set()
    never_off = set.union(*off_hits) if off_hits else set()
    everything = never_on | never_off
    gained = sorted(always_on - never_off)
    lost = sorted(always_off - never_on)
    unstable = sorted(everything - always_on - always_off - set(gained) - set(lost))
    return {"gained": gained, "lost": lost, "unstable": unstable}


def check_targets(card: dict[str, Any]) -> list[dict[str, Any]]:
    """Each Definition-of-Done target, judged on the worst repetition of each arm."""
    rows = []
    for name, arm in card["arms"].items():
        for metric, (op, target) in TARGETS.items():
            values = [rep["metrics"][metric]["value"] for rep in arm["repetitions"]]
            known = [v for v in values if v is not None]
            if not known:
                continue
            worst = min(known) if op == ">=" else max(known)
            met = worst >= target if op == ">=" else worst <= target
            rows.append(
                {
                    "arm": name,
                    "metric": metric,
                    "worst": worst,
                    "target": f"{op} {target}",
                    "met": met,
                }
            )
        over = sum(
            1 for rep in arm["repetitions"] for row in rep["cost"].values() if row["over_budget"]
        )
        rows.append(
            {
                "arm": name,
                "metric": "cases_over_budget",
                "worst": over,
                "target": "== 0",
                "met": over == 0,
            }
        )
    return rows


_SHOWN = (
    "programme_page_recall",
    "claim_precision",
    "claim_recall",
    "wrong_scope_claim_rate",
    "critical_field_coverage",
    "unsupported_claim_rate",
)


def render(card: dict[str, Any]) -> str:
    """The scorecard as Markdown, short enough to read in a PR."""
    lines = [f"# Scorecard — corpus {card['dataset_version']}", ""]
    columns = [
        (name, i, rep)
        for name, arm in card["arms"].items()
        for i, rep in enumerate(arm["repetitions"], 1)
    ]
    lines.append("| metric | " + " | ".join(f"{n}#{i}" for n, i, _ in columns) + " |")
    lines.append("|---|" + "---|" * len(columns))
    for metric in _SHOWN:
        cells = [
            f"{rep['metrics'][metric]['numerator']}/{rep['metrics'][metric]['denominator']}"
            for _, _, rep in columns
        ]
        lines.append(f"| {metric} | " + " | ".join(cells) + " |")
    core = [sum(len(v) for v in rep["core"].values()) for _, _, rep in columns]
    cases = [len(rep["core"]) * len(CORE_QUESTIONS) for _, _, rep in columns]
    lines.append(
        "| core questions answered | "
        + " | ".join(f"{a}/{b}" for a, b in zip(core, cases, strict=True))
        + " |"
    )
    reads = [sum(r["http_fetches"] or 0 for r in rep["cost"].values()) for _, _, rep in columns]
    lines.append("| reads (all cases) | " + " | ".join(str(r) for r in reads) + " |")
    if "changes" in card:
        ch = card["changes"]
        lines += [
            "",
            f"**Stable gains** ({len(ch['gained'])}): " + (", ".join(ch["gained"]) or "none"),
        ]
        lines.append(f"**Stable losses** ({len(ch['lost'])}): " + (", ".join(ch["lost"]) or "none"))
        lines.append(f"Unstable ({len(ch['unstable'])}): " + (", ".join(ch["unstable"]) or "none"))
    lines += [
        "",
        "## Targets (worst repetition)",
        "",
        "| arm | metric | worst | target | met |",
        "|---|---|---|---|---|",
    ]
    for row in card["targets"]:
        worst = row["worst"]
        shown = f"{worst:.3f}" if isinstance(worst, float) else str(worst)
        lines.append(
            f"| {row['arm']} | {row['metric']} | {shown} | {row['target']} | {'yes' if row['met'] else 'NO'} |"
        )
    last_arm = list(card["arms"])[-1]
    rep = card["arms"][last_arm]["repetitions"][0]
    lines += ["", f"## Wrong claims ({last_arm}, every repetition)", ""]
    # The same fact quoted from several pages, or in several repetitions, is
    # one finding, counted. A wrong value in any repetition is a finding.
    seen: dict[tuple[str, str, str, str, str], int] = defaultdict(int)
    for each in card["arms"][last_arm]["repetitions"]:
        for w in each["outcomes"]["wrong_claims"]:
            ours, expected = json.dumps(w["value"])[:80], json.dumps(w["expected"])[:80]
            seen[(w["case"], w["key"], ours, expected, w["why"])] += 1
    for (case_id, key, ours, expected, why), n in seen.items():
        times = f" ×{n}" if n > 1 else ""
        lines.append(f"- {case_id} `{key}`: ours {ours} vs {expected} ({why}){times}")
    if not seen:
        lines.append("- none")
    counts: dict[str, int] = defaultdict(int)
    for x in rep["outcomes"]["labels"]:
        counts[x["outcome"]] += 1
    lines += ["", f"## Known labels by outcome ({last_arm}#1)", ""]
    lines.append(", ".join(f"{k}: {v}" for k, v in sorted(counts.items())))
    lines += [
        "",
        f"## Per case ({last_arm}#1)",
        "",
        "| case | access | hits | core | queries | reads | s |",
        "|---|---|---|---|---|---|---|",
    ]
    access = card["arms"][last_arm]["access"]
    for case_id, row in rep["cost"].items():
        hits = sum(
            1 for x in rep["outcomes"]["labels"] if x["case"] == case_id and x["outcome"] == "hit"
        )
        known = sum(1 for x in rep["outcomes"]["labels"] if x["case"] == case_id)
        acc = access.get(case_id, ("unknown", 0, 0))
        lines.append(
            f"| {case_id} | {acc[0]} ({acc[2]}/{acc[1]} failed) | {hits}/{known} | "
            f"{len(rep['core'].get(case_id, []))}/6 | {row['search_calls']} | {row['http_fetches']} | {row['latency_seconds']} |"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "run_dir", type=Path, help="unpacked paired-run artifact, or one capture.json"
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path(__file__).parent / "data" / "ground_truth.reviewed.json",
    )
    parser.add_argument("--allow-drafts", action="store_true")
    parser.add_argument("--out", type=Path, help="write the full scorecard as JSON here")
    args = parser.parse_args(argv)
    dataset = Dataset.model_validate_json(args.dataset.read_text(encoding="utf-8"))
    card = build(dataset, load_run(args.run_dir), allow_drafts=args.allow_drafts)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(card, ensure_ascii=False, indent=1, default=str), encoding="utf-8"
        )
    print(render(card), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
