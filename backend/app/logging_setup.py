"""Logging, configured in one place for both processes.

The API and the worker each called `logging.basicConfig` with their own copy of
the same format string, so a change to one silently diverged from the other.
They share this module now.

Two things travel with every line: a correlation id, and a format the receiving
system can actually parse. In production the logs are read by a machine, so
`UNIMATCH_LOG_FORMAT=json` emits one JSON object per line; the default stays
human-readable, because the person reading them in development is a person.
"""

from __future__ import annotations

import json
import logging
import re
from contextvars import ContextVar

#: The id of the request being served on this task, or the job being run.
#: A ContextVar rather than a thread local: the API is async, and several
#: requests share a thread while never sharing a context.
_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="-")

#: What an inbound correlation header may contain. Anything else is replaced
#: rather than cleaned: this value is echoed back in a response header, and the
#: export filename taught this codebase what happens when caller-controlled
#: text reaches a header unchecked. Hyphens and underscores cover the shapes
#: real proxies send (uuid, ULID, `trace-span`); the cap stops a log line being
#: used as a payload.
_SAFE_ID = re.compile(r"\A[A-Za-z0-9_-]{1,64}\Z")


def set_correlation_id(value: str) -> str:
    """Adopt `value` if it is safe, otherwise keep the caller honest."""
    _correlation_id.set(value if _SAFE_ID.match(value or "") else "-")
    return _correlation_id.get()


def get_correlation_id() -> str:
    return _correlation_id.get()


def new_correlation_id() -> str:
    from uuid import uuid4

    return uuid4().hex


class CorrelationFilter(logging.Filter):
    """Puts the current correlation id on every record.

    A filter rather than an adapter, so third-party loggers — uvicorn's
    included — carry the id without any of their call sites knowing about it.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = _correlation_id.get()
        return True


#: Attributes LogRecord always carries. Anything outside this set was attached
#: by a caller via `extra=` and belongs in the JSON output.
_STANDARD = frozenset(logging.LogRecord("", 0, "", 0, "", None, None).__dict__) | {
    "asctime",
    "message",
    "correlation_id",
    "taskName",
}


class JsonFormatter(logging.Formatter):
    """One JSON object per line, hand-written to avoid a dependency.

    `python-json-logger` would do this too; it is not worth a new package on
    the production image for thirty lines.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", "-"),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        for key, value in record.__dict__.items():
            if key not in _STANDARD and not key.startswith("_"):
                payload[key] = value
        # default=str so an un-serialisable `extra=` degrades to its repr
        # rather than throwing inside the logging call that was reporting a
        # problem in the first place.
        return json.dumps(payload, default=str, ensure_ascii=False)


TEXT_FORMAT = "%(asctime)s %(levelname)-7s [%(correlation_id)s] %(name)s: %(message)s"


def configure_logging(level: str = "INFO", fmt: str = "text") -> None:
    """Install the handler both processes use. Safe to call twice."""
    handler = logging.StreamHandler()
    handler.setFormatter(
        JsonFormatter() if fmt.lower() == "json" else logging.Formatter(TEXT_FORMAT)
    )
    handler.addFilter(CorrelationFilter())

    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    # Replace rather than append: called twice (tests, or a reload), appending
    # would print every line once per call.
    for existing in root.handlers[:]:
        root.removeHandler(existing)
    root.addHandler(handler)

    # uvicorn installs its own handlers and does not propagate, so its access
    # and error lines would keep the old format and carry no correlation id.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True
