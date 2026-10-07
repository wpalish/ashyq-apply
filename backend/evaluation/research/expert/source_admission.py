"""Opt-in, evaluation-only admission shared by persistent local workers.

Admission linearizes under one process-safe lock immediately before a stock
source action. It is not proof the action actually executed. Never hold this
lock across a tool await. Case clocks/counters remain owned by the caller.
The caller rechecks its immutable deadline after receipt persistence, then
flips execution/counters and invokes the tool without an intervening await.

First cause is exclusive and durable before another admission can observe
STOP. Already admitted tails remain real charged attempts. There is no source
retry, replacement provider, reset, or additional case time in this module.
"""

from __future__ import annotations

import asyncio
import fcntl
import hashlib
import json
import math
import os
import re
import stat
import time
import uuid
from collections.abc import AsyncIterator, Callable, Iterator, Mapping
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

CONTRACT = "source_admission_v1"
PUBLICATION_LOCK_SECONDS = 1.0
Tool = Literal["fetcher", "search_provider"]
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,199}\Z")
_HEX = re.compile(r"[a-f0-9]{64}\Z")
_ADMISSION_PATH = re.compile(r"admissions/[a-f0-9]{64}\.json\Z")
_REASONS = frozenset(
    {
        "timeout",
        "transport error",
        "network policy",
        "MCP RPC error",
        "MCP tool error",
        "malformed response",
        "response too large",
        "unsupported protocol",
        "unexpected HTTP status",
    }
)
_INTEGRITY_REASONS = frozenset(
    {
        "source_integrity_failure",
        "source_resume_invalid",
        "source_record_invalid",
        "source_hash_mismatch",
        "source_policy_mismatch",
        "provider_identity_mismatch",
        "conflicting_provider_http_status",
        "duplicate_source_action",
        "worker_receipt_invalid",
    }
)
_BASE_FIELDS = {"schema_version", "contract", "run_id", "provider"}
_ADMISSION_FIELDS = _BASE_FIELDS | {"case_id", "action_id", "tool", "admission_id", "admitted_at"}
_STOP_FIELDS = _BASE_FIELDS | {
    "case_id",
    "action_id",
    "tool",
    "status",
    "stop_scope",
    "stop_kind",
    "terminal_reason",
    "observed_at",
    "http_status",
    "failure_reason",
    "origin_admission",
    "origin_external",
}
_MODEL_KINDS = frozenset(
    {"model_usage_limit", "model_authentication_refusal", "model_transport_failure"}
)
_MODEL_FIELDS = {
    "kind",
    "selector_error_kind",
    "event_line",
    "event_type",
    "stream_sha256",
    "case_id",
    "turn",
    "model_finished_at",
}


class SourceAdmissionIntegrityError(RuntimeError):
    """Fixed diagnostic only; the caller must stop on unauditable admission."""

    def __init__(self, reason: str = "source_record_invalid") -> None:
        super().__init__(reason)
        self.reason = reason


class SourceAdmissionDeadline(TimeoutError):
    """Case-local expiry while waiting for final admission; no source attempt."""


class SourceAdmissionPublicationError(RuntimeError):
    """No new calls are permitted if durable publication cannot be proved."""


class SourceAdmissionRefused(RuntimeError):
    """A verified original batch cause refused this new source action."""

    def __init__(self, stop_record: dict[str, Any]) -> None:
        super().__init__("batch_stopped")
        self.reason = "batch_stopped"
        self.stop_record = stop_record


@dataclass(frozen=True)
class StoredReceipt:
    receipt_path: str
    receipt_sha256: str
    record: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            **self.record,
            "receipt_path": self.receipt_path,
            "receipt_sha256": self.receipt_sha256,
        }


def _id(value: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise SourceAdmissionIntegrityError()
    return value


def _utc(value: datetime) -> str:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise SourceAdmissionIntegrityError()
    return value.astimezone(UTC).isoformat()


def _timestamp(value: Any) -> None:
    if not isinstance(value, str):
        raise SourceAdmissionIntegrityError()
    try:
        stamp = datetime.fromisoformat(value)
    except ValueError as exc:
        raise SourceAdmissionIntegrityError() from exc
    if _utc(stamp) != value:
        raise SourceAdmissionIntegrityError()


def _guard(remaining: Callable[[], float]) -> None:
    try:
        value = remaining()
    except TimeoutError as exc:
        raise SourceAdmissionDeadline("case_deadline_exhausted") from exc
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
        raise SourceAdmissionIntegrityError()
    if value <= 0:
        raise SourceAdmissionDeadline("case_deadline_exhausted")


def _read(path: Path) -> bytes:
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_size > 64 * 1024:
                raise SourceAdmissionIntegrityError()
            with os.fdopen(fd, "rb", closefd=False) as stream:
                return stream.read(64 * 1024 + 1)
        finally:
            os.close(fd)
    except OSError as exc:
        raise SourceAdmissionIntegrityError() from exc


def _decode(data: bytes) -> dict[str, Any]:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise SourceAdmissionIntegrityError()
            result[key] = value
        return result

    try:
        value = json.loads(data, object_pairs_hook=unique)
    except ValueError as exc:
        raise SourceAdmissionIntegrityError() from exc
    if not isinstance(value, dict):
        raise SourceAdmissionIntegrityError()
    return value


def _record(
    value: dict[str, Any], *, run_id: str, provider: str, kind: Literal["admission", "stop"]
) -> None:
    if (
        set(value) != (_ADMISSION_FIELDS if kind == "admission" else _STOP_FIELDS)
        or value.get("schema_version") != "1"
        or value.get("contract") != CONTRACT
        or value.get("run_id") != run_id
        or value.get("provider") != provider
    ):
        raise SourceAdmissionIntegrityError()
    _id(value["case_id"])
    _id(value["action_id"])
    if value["tool"] not in (
        {"fetcher", "search_provider", "model"}
        if kind == "stop"
        else {"fetcher", "search_provider"}
    ):
        raise SourceAdmissionIntegrityError()
    if kind == "admission":
        try:
            if str(uuid.UUID(value["admission_id"])) != value["admission_id"]:
                raise SourceAdmissionIntegrityError()
        except (ValueError, TypeError, AttributeError) as exc:
            raise SourceAdmissionIntegrityError() from exc
        _timestamp(value["admitted_at"])
    else:
        _timestamp(value["observed_at"])
        if value["status"] != "stopped" or value["stop_scope"] != "batch":
            raise SourceAdmissionIntegrityError()
        status = value["http_status"]
        if status is not None and (type(status) is not int or not 100 <= status <= 599):
            raise SourceAdmissionIntegrityError()
        if value["stop_kind"] == "provider_failure":
            if value["tool"] != "search_provider" or value["failure_reason"] not in _REASONS | {
                None
            }:
                raise SourceAdmissionIntegrityError()
            expected = f"provider_http_{status}" if status is not None else "provider_unavailable"
            if value["terminal_reason"] != expected:
                raise SourceAdmissionIntegrityError()
        elif value["stop_kind"] == "integrity_failure":
            if status is not None or value["terminal_reason"] not in _INTEGRITY_REASONS:
                raise SourceAdmissionIntegrityError()
            if value["failure_reason"] is not None:
                raise SourceAdmissionIntegrityError()
        elif value["stop_kind"] == "model_failure":
            if (
                value["tool"] != "model"
                or value["terminal_reason"] not in _MODEL_KINDS
                or status is not None
                or value["failure_reason"] is not None
                or value["origin_admission"] is not None
            ):
                raise SourceAdmissionIntegrityError()
        else:
            raise SourceAdmissionIntegrityError()
        if value["stop_kind"] != "model_failure" and value["origin_external"] is not None:
            raise SourceAdmissionIntegrityError()


def validate_receipt(
    proof: Mapping[str, Any],
    *,
    root: Path,
    run_id: str,
    provider: str,
    kind: Literal["admission", "stop"],
) -> dict[str, Any]:
    """Validate independently stored bytes/hash/path/schema; no source or model I/O."""
    root = root.resolve()
    relative, digest = proof.get("receipt_path"), proof.get("receipt_sha256")
    if (
        not isinstance(relative, str)
        or not isinstance(digest, str)
        or not _HEX.fullmatch(digest)
        or (relative != "stop.json" if kind == "stop" else not _ADMISSION_PATH.fullmatch(relative))
    ):
        raise SourceAdmissionIntegrityError()
    path = root / relative
    if (
        path.parent.is_symlink()
        or path.resolve().parent != (root / Path(relative).parent).resolve()
    ):
        raise SourceAdmissionIntegrityError()
    data = _read(path)
    if hashlib.sha256(data).hexdigest() != digest:
        raise SourceAdmissionIntegrityError("source_hash_mismatch")
    value = _decode(data)
    _record(value, run_id=run_id, provider=provider, kind=kind)
    if dict(proof) != {**value, "receipt_path": relative, "receipt_sha256": digest}:
        raise SourceAdmissionIntegrityError()
    if kind == "stop" and value["origin_admission"] is not None:
        origin = value["origin_admission"]
        if not isinstance(origin, dict):
            raise SourceAdmissionIntegrityError()
        admitted = validate_receipt(
            origin, root=root, run_id=run_id, provider=provider, kind="admission"
        )
        if any(admitted[key] != value[key] for key in ("case_id", "action_id", "tool")):
            raise SourceAdmissionIntegrityError()
    if kind == "stop" and value["stop_kind"] == "model_failure":
        external = value["origin_external"]
        if not isinstance(external, dict) or set(external) != {
            "receipt_path",
            "receipt_sha256",
            "kind",
        }:
            raise SourceAdmissionIntegrityError()
        path = root.parent / "model-batch-stop.json"
        if external["receipt_path"] != str(path) or not isinstance(external["receipt_sha256"], str):
            raise SourceAdmissionIntegrityError()
        data = _read(path)
        if hashlib.sha256(data).hexdigest() != external["receipt_sha256"]:
            raise SourceAdmissionIntegrityError("source_hash_mismatch")
        model = _model_record(_decode(data))
        if (
            model["kind"] != external["kind"]
            or model["kind"] != value["terminal_reason"]
            or model["case_id"] != value["case_id"]
        ):
            raise SourceAdmissionIntegrityError()
    return value


def _model_record(value: dict[str, Any]) -> dict[str, Any]:
    if set(value) != _MODEL_FIELDS or value["kind"] not in _MODEL_KINDS:
        raise SourceAdmissionIntegrityError()
    _id(value["case_id"])
    _timestamp(value["model_finished_at"])
    if (
        type(value["turn"]) is not int
        or value["turn"] < 1
        or not isinstance(value["stream_sha256"], str)
        or not _HEX.fullmatch(value["stream_sha256"])
    ):
        raise SourceAdmissionIntegrityError()
    if value["event_line"] is not None and (
        type(value["event_line"]) is not int or value["event_line"] < 1
    ):
        raise SourceAdmissionIntegrityError()
    if value["event_type"] not in {None, "error", "turn.failed"}:
        raise SourceAdmissionIntegrityError()
    if value["selector_error_kind"] not in {
        None,
        "selector_process_failed",
        "selector_process_unavailable",
        "selector_output_rejected",
        "selector_timeout",
    }:
        raise SourceAdmissionIntegrityError()
    return value


class SourceAdmission:
    """One root/run/provider identity shared across arms and worker processes."""

    def __init__(
        self,
        root: Path,
        *,
        run_id: str,
        provider: str,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.run_id = _id(run_id)
        if provider not in {"exa", "exa_mcp"}:
            raise SourceAdmissionIntegrityError("provider_identity_mismatch")
        self.provider, self.now = provider, now
        if root.is_symlink():
            raise SourceAdmissionIntegrityError()
        root.mkdir(parents=True, exist_ok=True)
        self.root = root.resolve()
        self._base = {
            "schema_version": "1",
            "contract": CONTRACT,
            "run_id": self.run_id,
            "provider": self.provider,
        }
        with self._locked():
            identity = self.root / "identity.json"
            if not identity.exists() and not identity.is_symlink():
                if (self.root / "stop.json").exists() or (self.root / "admissions").exists():
                    raise SourceAdmissionIntegrityError()
                self._write("identity.json", self._base)
            self._identity()
            admissions = self.root / "admissions"
            if admissions.is_symlink():
                raise SourceAdmissionIntegrityError()
            admissions.mkdir(exist_ok=True)

    def policy(self) -> dict[str, Any]:
        return {
            "contract": CONTRACT,
            "run_id": self.run_id,
            "provider": self.provider,
            "root": str(self.root),
            "identity_path": "identity.json",
            "identity_sha256": hashlib.sha256(self._identity()).hexdigest(),
        }

    def _identity(self) -> bytes:
        data = _read(self.root / "identity.json")
        if _decode(data) != self._base:
            raise SourceAdmissionIntegrityError("source_policy_mismatch")
        return data

    def _lock_fd(self) -> int:
        try:
            fd = os.open(self.root / ".lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        except OSError as exc:
            raise SourceAdmissionIntegrityError() from exc
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            os.close(fd)
            raise SourceAdmissionIntegrityError()
        return fd

    @contextmanager
    def _locked(self) -> Iterator[None]:
        fd = self._lock_fd()
        until = time.monotonic() + PUBLICATION_LOCK_SECONDS
        try:
            while True:
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= until:
                        raise SourceAdmissionPublicationError(
                            "admission_publication_lock_unavailable"
                        ) from None
                    time.sleep(0)  # Scheduler yield only; not a source retry or time allowance.
            yield
        finally:
            os.close(fd)

    @asynccontextmanager
    async def _admission_lock(self, remaining: Callable[[], float]) -> AsyncIterator[None]:
        fd = self._lock_fd()
        try:
            while True:
                _guard(remaining)
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    await asyncio.sleep(0)  # Cancellable and bounded by the same case clock.
            _guard(remaining)
            yield
        finally:
            os.close(fd)

    def _write(self, relative: str, value: dict[str, Any]) -> StoredReceipt:
        final = self.root / relative
        data = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n"
        temporary = final.parent / (".pending-" + uuid.uuid4().hex)
        try:
            with temporary.open("xb") as output:
                output.write(data)
                output.flush()
                os.fsync(output.fileno())
            os.link(
                temporary, final, follow_symlinks=False
            )  # Exclusive: never replace first cause.
            temporary.unlink()
            directory = os.open(final.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            temporary.unlink(missing_ok=True)
        return StoredReceipt(relative, hashlib.sha256(data).hexdigest(), value)

    def _stop(self) -> StoredReceipt | None:
        path = self.root / "stop.json"
        if not path.exists() and not path.is_symlink():
            return None
        data = _read(path)
        receipt = StoredReceipt("stop.json", hashlib.sha256(data).hexdigest(), _decode(data))
        validate_receipt(
            receipt.as_dict(),
            root=self.root,
            run_id=self.run_id,
            provider=self.provider,
            kind="stop",
        )
        return receipt

    def stop_snapshot(self) -> dict[str, Any] | None:
        with self._locked():
            self._identity()
            stop = self._stop() or self._external_model_stop()
            return stop.as_dict() if stop else None

    async def admit(
        self,
        *,
        case_id: str,
        tool: Tool,
        action_id: str,
        remaining: Callable[[], float],
    ) -> StoredReceipt:
        _id(case_id)
        _id(action_id)
        if tool not in {"fetcher", "search_provider"}:
            raise SourceAdmissionIntegrityError()
        async with self._admission_lock(remaining):
            self._identity()
            stop = self._stop() or self._external_model_stop()
            if stop:
                raise SourceAdmissionRefused(stop.as_dict())
            relative = (
                "admissions/"
                + hashlib.sha256(f"{case_id}\n{action_id}".encode()).hexdigest()
                + ".json"
            )
            if (self.root / relative).exists() or (self.root / relative).is_symlink():
                self._publish(
                    case_id=case_id,
                    action_id=action_id,
                    tool=tool,
                    stop_kind="integrity_failure",
                    terminal_reason="duplicate_source_action",
                )
                raise SourceAdmissionIntegrityError("duplicate_source_action")
            admitted_at = _utc(self.now())
            _guard(remaining)
            return self._write(
                relative,
                {
                    **self._base,
                    "case_id": case_id,
                    "tool": tool,
                    "action_id": action_id,
                    "admission_id": str(uuid.uuid4()),
                    "admitted_at": admitted_at,
                },
            )

    def _publish(
        self,
        *,
        case_id: str,
        action_id: str,
        tool: str,
        stop_kind: str,
        terminal_reason: str,
        http_status: int | None = None,
        failure_reason: str | None = None,
        origin_admission: StoredReceipt | None = None,
        origin_external: dict[str, Any] | None = None,
    ) -> StoredReceipt:
        self._identity()
        original = self._stop()
        if original is None and stop_kind != "model_failure":
            original = self._external_model_stop()
        if original:
            return original
        value = {
            **self._base,
            "case_id": _id(case_id),
            "action_id": _id(action_id),
            "tool": tool,
            "status": "stopped",
            "stop_scope": "batch",
            "stop_kind": stop_kind,
            "terminal_reason": terminal_reason,
            "observed_at": _utc(self.now()),
            "http_status": http_status,
            "failure_reason": failure_reason,
            "origin_admission": origin_admission.as_dict() if origin_admission else None,
            "origin_external": origin_external,
        }
        _record(value, run_id=self.run_id, provider=self.provider, kind="stop")
        if origin_admission:
            admitted = validate_receipt(
                origin_admission.as_dict(),
                root=self.root,
                run_id=self.run_id,
                provider=self.provider,
                kind="admission",
            )
            if any(admitted[key] != value[key] for key in ("case_id", "action_id", "tool")):
                raise SourceAdmissionIntegrityError()
        return self._write("stop.json", value)

    def _external_model_stop(self) -> StoredReceipt | None:
        path = self.root.parent / "model-batch-stop.json"
        if not path.exists() and not path.is_symlink():
            return None
        data = _read(path)
        model = _model_record(_decode(data))
        return self._publish(
            case_id=model["case_id"],
            action_id=f"model.turn.{model['turn']}",
            tool="model",
            stop_kind="model_failure",
            terminal_reason=model["kind"],
            origin_external={
                "receipt_path": str(path),
                "receipt_sha256": hashlib.sha256(data).hexdigest(),
                "kind": model["kind"],
            },
        )

    def publish_model_failure(
        self,
        *,
        case_id: str,
        action_id: str,
        origin_receipt_path: Path,
        origin_receipt_sha256: str,
    ) -> StoredReceipt:
        path = self.root.parent / "model-batch-stop.json"
        if origin_receipt_path != path:
            raise SourceAdmissionIntegrityError()
        with self._locked():
            data = _read(path)
            if hashlib.sha256(data).hexdigest() != origin_receipt_sha256:
                raise SourceAdmissionIntegrityError("source_hash_mismatch")
            model = _model_record(_decode(data))
            if model["case_id"] != case_id:
                raise SourceAdmissionIntegrityError()
            return self._publish(
                case_id=case_id,
                action_id=action_id,
                tool="model",
                stop_kind="model_failure",
                terminal_reason=model["kind"],
                origin_external={
                    "receipt_path": str(path),
                    "receipt_sha256": origin_receipt_sha256,
                    "kind": model["kind"],
                },
            )

    def publish_provider_failure(
        self,
        *,
        case_id: str,
        action_id: str,
        http_status: int | None,
        failure_reason: str | None = None,
        origin_admission: StoredReceipt | None = None,
    ) -> StoredReceipt:
        with self._locked():
            return self._publish(
                case_id=case_id,
                action_id=action_id,
                tool="search_provider",
                stop_kind="provider_failure",
                http_status=http_status,
                failure_reason=failure_reason,
                terminal_reason=f"provider_http_{http_status}"
                if http_status is not None
                else "provider_unavailable",
                origin_admission=origin_admission,
            )

    def publish_integrity_failure(
        self,
        *,
        case_id: str,
        action_id: str,
        tool: Tool = "fetcher",
        reason: str = "source_integrity_failure",
        origin_admission: StoredReceipt | None = None,
    ) -> StoredReceipt:
        with self._locked():
            return self._publish(
                case_id=case_id,
                action_id=action_id,
                tool=tool,
                stop_kind="integrity_failure",
                terminal_reason=reason,
                origin_admission=origin_admission,
            )
