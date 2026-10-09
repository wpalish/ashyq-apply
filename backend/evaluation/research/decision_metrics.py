"""Decision-grade evaluation, separate from the historical claim scorer.

Only captures of answers actually displayed/used belong here: an evidence
inventory is not a decision capture. Independent review sidecars establish
conditions, currentness and conflict resolution; production confidence flags
are not a substitute. Unknown gold stays unadjudicated, never silently correct.
"""

from __future__ import annotations

import hashlib
import json
import random
import re
from collections import Counter, defaultdict
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlsplit, urlunsplit

from app.adapters.search.ontology import titles_name_same_programme
from app.domain.programme_identity import Verdict

from .schema import Capture, Dataset, Label, Prediction, Scope

GROUPS = frozenset(
    {
        "english",
        "academic",
        "deadline",
        "tuition",
        "scholarship_exists",
        "scholarship_applicability",
    }
)
QuestionState = Literal[
    "published_answer",
    "explicit_not_applicable",
    "explicit_not_published_yet",
    "unresolved_conflict",
    "access_blocked",
    "review_incomplete",
]
QUESTION_STATES = frozenset(
    {
        "published_answer",
        "explicit_not_applicable",
        "explicit_not_published_yet",
        "unresolved_conflict",
        "access_blocked",
        "review_incomplete",
    }
)


def canonical_url(url: object) -> str:
    parts = urlsplit(str(url))
    return urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), parts.query, "")
    )


def ratio(numerator: int, denominator: int) -> dict[str, Any]:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": numerator / denominator if denominator else None,
    }


def scope_matches(expected: Scope, actual: Scope) -> bool:
    """No descriptive-population wildcard or silent applicant scope inheritance."""
    for dimension, expected_value in expected.model_dump().items():
        if expected_value is None:
            continue
        actual_value = getattr(actual, dimension)
        if actual_value is None:
            return False
        if dimension == "programme":
            if titles_name_same_programme(expected_value, actual_value) is not Verdict.YES:
                return False
        elif dimension == "academic_year":

            def normalized_year(value: str) -> str:
                found = re.search(r"(\d{4})\s*[-/–]\s*(\d{2,4})", value)
                return f"{found[1]}/{found[2][-2:]}" if found else value.strip().casefold()

            if normalized_year(expected_value) != normalized_year(actual_value):
                return False
        elif (
            " ".join(expected_value.split()).casefold() != " ".join(actual_value.split()).casefold()
        ):
            return False
    return True


@dataclass(frozen=True)
class DecisionReview:
    """Independent source review, keyed by ``prediction_id``.

    ``evidence_entails`` permits a different official quotation only alongside
    explicit supported=True and a lexical value check. Never derive this
    review from the candidate model's own confidence or expected-value match.
    """

    reviewer: str
    current: bool
    conditions_correct: bool
    conflict_resolved: bool
    evidence_entails: bool = False

    def __post_init__(self) -> None:
        if not self.reviewer.strip():
            raise ValueError("Independent review requires reviewer identity")


def prediction_id(case_id: str, prediction: Prediction) -> str:
    payload = json.dumps(
        [case_id, prediction.model_dump(mode="json")], sort_keys=True, ensure_ascii=False
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _same_value(left: Any, right: Any) -> bool:
    return json.dumps(left, sort_keys=True) == json.dumps(right, sort_keys=True)


def _contains_span(ours: str, certified: str) -> bool:
    """The whole independently certified span must occur, not its substring."""
    ours_flat, certified_flat = " ".join(ours.split()), " ".join(certified.split())
    return bool(certified_flat and certified_flat in ours_flat)


def _value_in_quote(value: Any, quote: str) -> bool:
    # Boolean/structured policies need exact gold evidence; lexical coincidence
    # cannot establish negation, exceptions, currency, units or list completeness.
    if isinstance(value, bool) or value is None or isinstance(value, list | dict):
        return False
    text = f"{value:g}" if isinstance(value, int | float) else str(value)
    return bool(text and re.search(r"(?<!\w)" + re.escape(text) + r"(?!\w)", quote, re.IGNORECASE))


def _verdict(
    p: Prediction,
    label: Label | None,
    request: Scope,
    review: DecisionReview | None,
    conflicting: bool,
) -> list[str]:
    reasons = []
    if label is None or label.status != "known":
        reasons.append("unadjudicated_gold")
    elif not _same_value(p.value, label.value):
        reasons.append("wrong_value")
    e = p.evidence
    if e is None or e.source_type not in {"official", "government"} or e.excerpt_truncated:
        reasons.append("missing_primary_complete_evidence")
    else:
        if not scope_matches(request, e.scope):
            reasons.append("request_scope_unestablished")
        if label is not None and label.status == "known":
            if not any(scope_matches(g.scope, e.scope) for g in label.evidence):
                reasons.append("gold_scope_mismatch")
            exact = any(
                canonical_url(g.url) == canonical_url(e.url)
                and _contains_span(e.excerpt, g.excerpt)
                for g in label.evidence
            )
            alternative = bool(
                p.supported is True
                and review
                and review.evidence_entails
                and _value_in_quote(p.value, e.excerpt)
            )
            if p.supported is False or not (exact or alternative):
                reasons.append("evidence_not_independently_supported")
    if review is None:
        reasons.append("missing_independent_review")
    else:
        if not review.current:
            reasons.append("not_current")
        if not review.conditions_correct:
            reasons.append("conditions_incorrect")
        if not review.conflict_resolved:
            reasons.append("unresolved_conflict")
    if conflicting:
        reasons.append("contradictory_displayed_values")
    return reasons


def _cluster_interval(
    rows: list[dict[str, Any]], name: str, samples: int, seed: int
) -> dict[str, Any]:
    clustered: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for row in rows:
        n, d = row[name]
        clustered[row["university"]][0] += n
        clustered[row["university"]][1] += d
    values = [v for v in clustered.values() if v[1]]
    result: dict[str, Any] = {
        "method": "university_cluster_percentile_bootstrap",
        "confidence": 0.95,
        "clusters": len(values),
        "samples": samples,
        "seed": seed,
        "lower": None,
        "upper": None,
    }
    if len(values) < 2:
        result["limitation"] = "fewer_than_two_informative_university_clusters"
        return result
    if len({n / d for n, d in values}) == 1:
        result["limitation"] = (
            "no_between_cluster_variation_bootstrap_cannot_estimate_tail_uncertainty"
        )
        return result
    rng = random.Random(seed)
    draws = []
    for _ in range(samples):
        chosen = rng.choices(values, k=len(values))
        draws.append(sum(v[0] for v in chosen) / sum(v[1] for v in chosen))
    draws.sort()
    result.update(lower=draws[int((samples - 1) * 0.025)], upper=draws[int((samples - 1) * 0.975)])
    return result


def score_decisions(
    dataset: Dataset,
    capture: Capture,
    *,
    contracts: Mapping[str, Mapping[str, list[str]]],
    reviews: Mapping[str, DecisionReview] | None = None,
    question_states: Mapping[str, Mapping[str, QuestionState]] | None = None,
    identity_keys: Mapping[str, list[str]] | None = None,
    allow_drafts: bool = False,
    bootstrap_samples: int = 2000,
    bootstrap_seed: int = 90,
) -> dict[str, Any]:
    """Score frozen six-group contracts, retaining every requested case.

    Contracts list *all* required keys per group; any missing/wrong/contradictory
    component fails that answer. An empty contract is review-incomplete unless
    independently classified otherwise in question_states. An access-blocked
    group with known gold remains source-answerable and in recall. No budgets
    or exclusions are inferred from a run's success/failure.
    """
    if bootstrap_samples < 100:
        raise ValueError("At least 100 bootstrap samples required")
    if not allow_drafts and any(c.review.status != "human_verified" for c in dataset.cases):
        raise ValueError("Dataset contains cases without human verification")
    ids = {c.id for c in dataset.cases}
    if set(contracts) != ids or any(set(groups) != GROUPS for groups in contracts.values()):
        raise ValueError("Every requested dataset case needs exactly the six decision groups")
    observed = {o.case_id: o for o in capture.observations}
    if len(observed) != len(capture.observations) or set(observed) - ids:
        raise ValueError("Duplicate or foreign observation case IDs")
    if question_states is not None and (
        set(question_states) - ids
        or any(
            set(v) - GROUPS or any(s not in QUESTION_STATES for s in v.values())
            for v in question_states.values()
        )
    ):
        raise ValueError("Foreign question state or case")
    if identity_keys is not None and set(identity_keys) - ids:
        raise ValueError("Foreign identity contract case")
    reviews = reviews or {}
    rows, errors = [], Counter()
    statuses, states = Counter(), Counter()
    missing_cases, access_failed_cases = [], []
    for case in dataset.cases:
        observation = observed.get(case.id)
        if observation is None:
            missing_cases.append(case.id)
        if observation and (
            observation.error
            or any(p.category in {"fetch-failed", "unreadable"} for p in observation.page_outcomes)
        ):
            access_failed_cases.append(case.id)
        predictions = (
            {
                p.model_dump_json(): p
                for p in observation.predictions
                if p.value is not None and p.value != "UNKNOWN"
            }
            if observation
            else {}
        )
        labels = {label.key: label for label in case.labels}
        statuses.update(label.status for label in case.labels)
        by_key: dict[str, list[Prediction]] = defaultdict(list)
        for p in predictions.values():
            by_key[p.key].append(p)
        correct_keys, incorrect_keys = set(), set()
        correct_predictions = unadjudicated = 0
        for p in predictions.values():
            conflicting = len({json.dumps(x.value, sort_keys=True) for x in by_key[p.key]}) > 1
            reasons = _verdict(
                p,
                labels.get(p.key),
                case.request,
                reviews.get(prediction_id(case.id, p)),
                conflicting,
            )
            errors.update(reasons)
            unadjudicated += int("unadjudicated_gold" in reasons)
            if reasons:
                incorrect_keys.add(p.key)
            else:
                correct_predictions += 1
                correct_keys.add(p.key)
        correct_keys -= incorrect_keys
        # Programme identity and reviewed teaching language are separate gates.
        requested_identity = (identity_keys or {}).get(case.id, ["programme.language"])
        identity_established = bool(
            observation
            and case.programme_status == "known"
            and set(map(canonical_url, case.programme_urls))
            & set(map(canonical_url, observation.programme_urls))
            and requested_identity
            and set(requested_identity) <= correct_keys
        )
        successes = answerable = 0
        group_rows = {}
        for group, keys in contracts[case.id].items():
            if len(keys) != len(set(keys)) or any(k not in labels for k in keys):
                raise ValueError("Question contracts require unique gold label keys")
            known = bool(keys and all(labels[k].status == "known" for k in keys))
            declared = (question_states or {}).get(case.id, {}).get(group)
            if declared in {"explicit_not_applicable", "explicit_not_published_yet"} and known:
                raise ValueError("Published gold cannot be excluded by an absence state")
            if declared == "published_answer" and not known:
                raise ValueError("Published question needs complete known gold")
            state = declared or (
                "published_answer"
                if known
                else "explicit_not_applicable"
                if keys and all(labels[k].status == "not_applicable" for k in keys)
                else "review_incomplete"
            )
            states[state] += 1
            success = bool(known and identity_established and set(keys) <= correct_keys)
            successes += int(success)
            answerable += int(known)
            group_rows[group] = {
                "state": state,
                "source_answerable": known,
                "correct": success,
                "required_keys": list(keys),
            }
        rows.append(
            {
                "case_id": case.id,
                "university": case.domain.casefold(),
                "subject": case.request.field or "unassigned",
                "identity_established": identity_established,
                "groups": group_rows,
                "recall": [successes, answerable],
                "precision": [correct_predictions, len(predictions)],
                "usable_coverage": [successes, len(GROUPS)],
                "unadjudicated_predictions": unadjudicated,
            }
        )

    def aggregate(selected: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            name: {
                **ratio(sum(r[name][0] for r in selected), sum(r[name][1] for r in selected)),
                "interval": _cluster_interval(selected, name, bootstrap_samples, bootstrap_seed),
            }
            for name in ("recall", "precision", "usable_coverage")
        }

    overall = aggregate(rows)
    subjects = {
        s: aggregate([r for r in rows if r["subject"] == s])
        for s in sorted({r["subject"] for r in rows})
    }
    complete = "review_incomplete" not in states
    review_digest = hashlib.sha256(
        json.dumps({k: asdict(v) for k, v in sorted(reviews.items())}, sort_keys=True).encode()
    ).hexdigest()
    contract_digest = hashlib.sha256(
        json.dumps(
            {
                "contracts": contracts,
                "question_states": question_states,
                "identity_keys": identity_keys,
            },
            sort_keys=True,
        ).encode()
    ).hexdigest()
    return {
        "scorer_version": "decision-v1",
        "dataset_version": dataset.version,
        "dataset_sha256": hashlib.sha256(dataset.model_dump_json().encode()).hexdigest(),
        "contracts_sha256": contract_digest,
        "reviews_sha256": review_digest,
        "pipeline_sha": capture.pipeline_sha,
        "mode": capture.mode,
        "provisional": any(c.review.status != "human_verified" for c in dataset.cases),
        "metrics": overall,
        "subjects": subjects,
        "cases": rows,
        "label_statuses": dict(statuses),
        "question_states": dict(states),
        "missing_cases": missing_cases,
        "access_failed_cases": access_failed_cases,
        "prediction_failures": dict(errors),
        "gold_complete": complete,
        "point_thresholds_met": complete
        and all(
            v["recall"]["value"] is not None
            and v["recall"]["value"] >= 0.90
            and v["precision"]["value"] is not None
            and v["precision"]["value"] >= 0.95
            for v in [overall, *subjects.values()]
        ),
        # This module does not verify a sealed experiment's sampling manifest,
        # budgets or minimum size; a high-scoring one-case capture cannot release.
        "release_eligible": False,
        "release_review_required": True,
        "notes": [
            "Precision is a conservative verified-correct/all-emitted-decision-answers fraction; unadjudicated answers remain in denominator, not labelled false.",
            "Usable coverage counts verified published answers over all six requested groups; explicit absence/NA is reported separately, not silently credited.",
            "Point thresholds are experimental gates, not population guarantees. Cluster intervals cannot establish uncertainty at constant cluster outcomes.",
            "Capture must contain displayed/used decision answers, not the internal evidence inventory. No production self-confidence substitutes for independent review.",
            "Live validation thresholds alone do not certify sealed sampling, minimum cohort size or budget compliance; audit these in the preregistered experiment protocol.",
        ],
    }


def main() -> None:
    """Replay without provider calls; preserve the historical capture unchanged.

    --contracts JSON: {contracts: {case_id: {group: [label_key]}},
    question_states?: {...}, identity_keys?: {case_id: [label_key]}}
    --reviews JSON: {prediction_id: {reviewer,current,conditions_correct,
    conflict_resolved,evidence_entails?}}. Missing reviews produce failures.
    """
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--contracts", type=Path, required=True)
    parser.add_argument("--reviews", type=Path)
    parser.add_argument("--allow-drafts", action="store_true")
    parser.add_argument("--bootstrap-samples", type=int, default=2000)
    parser.add_argument("--bootstrap-seed", type=int, default=90)
    args = parser.parse_args()
    dataset = Dataset.model_validate_json(args.dataset.read_text(encoding="utf-8"))
    capture = Capture.model_validate_json(args.capture.read_text(encoding="utf-8"))
    contracts = json.loads(args.contracts.read_text(encoding="utf-8"))
    reviews = json.loads(args.reviews.read_text(encoding="utf-8")) if args.reviews else {}
    report = score_decisions(
        dataset,
        capture,
        contracts=contracts["contracts"],
        question_states=contracts.get("question_states"),
        identity_keys=contracts.get("identity_keys"),
        reviews={k: DecisionReview(**v) for k, v in reviews.items()},
        allow_drafts=args.allow_drafts,
        bootstrap_samples=args.bootstrap_samples,
        bootstrap_seed=args.bootstrap_seed,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
