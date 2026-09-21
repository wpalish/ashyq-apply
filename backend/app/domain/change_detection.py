"""What changed between two readings of one page.

The cheap half of change detection already works: a conditional GET, then a
content hash, so a page that has not changed costs one request. The question
that follows is the one the phase guide calls *material* change, and nothing
answered it: a re-read page supersedes every live claim it produced and
appends the fresh ones, even when every value came back identical. A page that
merely re-rendered leaves behind a full generation of history saying exactly
what the live rows say.

Claims are paired on ``(claim_type, subject_key)`` — what makes two claims the
same statement, and the same pairing supersession itself uses — and compared on
their normalised values. Two things are deliberately *not* compared: the
excerpt, because a page may reword the sentence around an unchanged number,
and the accessed time, because re-reading a page is not a change to what it
says.

Pure domain logic: this classifies, it does not decide what to do about it.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol

from app.domain.enums import ClaimType


class Statement(Protocol):
    """The three things that make two readings comparable.

    A protocol rather than ``Claim``, because the "before" side is usually a
    persisted row read back from its payload, and demanding a fully valid
    ``Claim`` there would make a comparison fail — and, inside a re-extract's
    single transaction, take the supersession down with it. Comparing history
    must never be able to break the thing it is describing.
    """

    @property
    def claim_type(self) -> ClaimType: ...

    @property
    def subject_key(self) -> str | None: ...

    @property
    def normalized_value(self) -> Any: ...


@dataclass(frozen=True, slots=True)
class Reading:
    """One statement from one reading. Built from whatever a caller holds."""

    claim_type: ClaimType
    subject_key: str | None
    normalized_value: Any

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> Reading:
        """From a persisted claim payload, tolerating anything else in it."""
        return cls(
            claim_type=ClaimType(payload["claim_type"]),
            subject_key=payload.get("subject_key"),
            normalized_value=payload.get("normalized_value"),
        )


class ChangeKind(StrEnum):
    UNCHANGED = "unchanged"
    VALUE_CHANGED = "value_changed"
    #: The page now states something it did not state before.
    ADDED = "added"
    #: The page no longer states it. Never "the value became null": a claim
    #: that disappeared is a finding, and the one the re-extract path exists
    #: to preserve.
    REMOVED = "removed"


def _comparable(value: Any) -> str:
    """The same normalisation ``conflicts`` uses, and for the same reason:
    6.5 and 6.50 are one value, while two orderings of a list are not two."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, list):
        return "|".join(sorted(str(v) for v in value))
    if isinstance(value, dict):
        return "|".join(f"{k}={v}" for k, v in sorted(value.items()))
    return str(value).strip().lower()


@dataclass(frozen=True, slots=True)
class ClaimChange:
    kind: ChangeKind
    claim_type: ClaimType
    subject_key: str | None
    before: Any = None
    after: Any = None

    def describe(self) -> str:
        subject = f" [{self.subject_key}]" if self.subject_key else ""
        if self.kind is ChangeKind.VALUE_CHANGED:
            return f"{self.claim_type.value}{subject}: {self.before!r} -> {self.after!r}"
        if self.kind is ChangeKind.ADDED:
            return f"{self.claim_type.value}{subject}: now states {self.after!r}"
        if self.kind is ChangeKind.REMOVED:
            return f"{self.claim_type.value}{subject}: no longer stated (was {self.before!r})"
        return f"{self.claim_type.value}{subject}: unchanged"


def classify_changes(
    before: list[Statement] | list[Any], after: list[Statement] | list[Any]
) -> list[ClaimChange]:
    """Every statement that differs between two readings, and how.

    A statement appearing twice in one reading — two official pages of the
    same run, or a genuine repetition — is compared as a set of values, so a
    re-read that returns the same pair in a different order is unchanged.
    """
    old: dict[tuple[ClaimType, str | None], list[Any]] = defaultdict(list)
    new: dict[tuple[ClaimType, str | None], list[Any]] = defaultdict(list)
    for claim in before:
        old[(claim.claim_type, claim.subject_key)].append(claim)
    for claim in after:
        new[(claim.claim_type, claim.subject_key)].append(claim)

    changes: list[ClaimChange] = []
    for key in sorted(set(old) | set(new), key=lambda k: (k[0].value, k[1] or "")):
        claim_type, subject = key
        old_values = {_comparable(c.normalized_value) for c in old.get(key, ())}
        new_values = {_comparable(c.normalized_value) for c in new.get(key, ())}
        if old_values == new_values:
            changes.append(ClaimChange(ChangeKind.UNCHANGED, claim_type, subject))
        elif not old_values:
            changes.append(
                ClaimChange(
                    ChangeKind.ADDED, claim_type, subject, after=new[key][0].normalized_value
                )
            )
        elif not new_values:
            changes.append(
                ClaimChange(
                    ChangeKind.REMOVED, claim_type, subject, before=old[key][0].normalized_value
                )
            )
        else:
            changes.append(
                ClaimChange(
                    ChangeKind.VALUE_CHANGED,
                    claim_type,
                    subject,
                    before=old[key][0].normalized_value,
                    after=new[key][0].normalized_value,
                )
            )
    return changes


def is_material(changes: list[ClaimChange]) -> bool:
    """Whether anything a user could act on actually changed."""
    return any(change.kind is not ChangeKind.UNCHANGED for change in changes)


def summarise(changes: list[ClaimChange]) -> str:
    """One line for a log: what changed, or that nothing did."""
    if not is_material(changes):
        return f"no material change ({len(changes)} claim(s) re-read, all identical)"
    counts: dict[str, int] = defaultdict(int)
    for change in changes:
        counts[change.kind.value] += 1
    head = ", ".join(f"{kind}={count}" for kind, count in sorted(counts.items()))
    detail = "; ".join(
        change.describe() for change in changes if change.kind is not ChangeKind.UNCHANGED
    )
    return f"{head} — {detail}"
