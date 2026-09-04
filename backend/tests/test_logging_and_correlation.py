"""Logs a machine can read, and a request you can find again.

Two processes each called `logging.basicConfig` with their own copy of one
format string, no line carried a correlation id, and nothing tied a log entry
to the request that produced it. When something went wrong in production the
only way to connect an error to a user's report was the clock.
"""

from __future__ import annotations

import json
import logging

import pytest

from app.logging_setup import (
    JsonFormatter,
    configure_logging,
    get_correlation_id,
    set_correlation_id,
)


@pytest.fixture(autouse=True)
def _restore_logging():
    """Leave the root logger as it was found."""
    root = logging.getLogger()
    saved, level = root.handlers[:], root.level
    yield
    root.handlers[:] = saved
    root.setLevel(level)
    set_correlation_id("-")


def record(**extra) -> logging.LogRecord:
    rec = logging.LogRecord(
        "unimatch.test", logging.INFO, __file__, 1, "hello %s", ("world",), None
    )
    for key, value in extra.items():
        setattr(rec, key, value)
    return rec


class TestTheCorrelationId:
    def test_an_unsafe_inbound_id_is_replaced_not_cleaned(self):
        """This value is echoed into a response header.

        The export filename already taught this codebase what caller-controlled
        text does when it reaches a header unchecked, so a header that does not
        match the safe shape is dropped whole rather than stripped of the parts
        that looked dangerous.
        """
        for hostile in (
            "abc\r\nX-Injected: 1",
            'abc"; x="1',
            "a" * 65,
            "",
            "id with spaces",
        ):
            assert set_correlation_id(hostile) == "-", hostile

    def test_a_reasonable_inbound_id_is_kept(self):
        for good in ("0123456789abcdef", "trace-1234_5678", "A" * 64):
            assert set_correlation_id(good) == good

    def test_the_id_reaches_a_log_record_without_the_caller_knowing(self):
        set_correlation_id("abc123")
        from app.logging_setup import CorrelationFilter

        rec = record()
        assert CorrelationFilter().filter(rec) is True
        assert rec.correlation_id == "abc123"


class TestTheJsonFormat:
    def test_one_parseable_object_per_line(self):
        set_correlation_id("req-1")
        rec = record(correlation_id="req-1")
        payload = json.loads(JsonFormatter().format(rec))
        assert payload["level"] == "INFO"
        assert payload["logger"] == "unimatch.test"
        assert payload["message"] == "hello world"
        assert payload["correlation_id"] == "req-1"

    def test_extra_fields_survive(self):
        rec = record(correlation_id="-", run_id="r1", stage="assessment")
        payload = json.loads(JsonFormatter().format(rec))
        assert payload["run_id"] == "r1"
        assert payload["stage"] == "assessment"

    def test_an_unserialisable_extra_does_not_break_the_log_call(self):
        """A logger reporting a problem must not become the problem."""
        rec = record(correlation_id="-", obj=object())
        payload = json.loads(JsonFormatter().format(rec))
        assert isinstance(payload["obj"], str)

    def test_an_exception_is_carried_whole(self):
        try:
            raise ValueError("boom")
        except ValueError:
            import sys

            rec = record(correlation_id="-")
            rec.exc_info = sys.exc_info()
        payload = json.loads(JsonFormatter().format(rec))
        assert "ValueError: boom" in payload["exception"]


class TestConfigureLogging:
    def test_calling_it_twice_does_not_double_every_line(self):
        configure_logging("INFO", "json")
        configure_logging("INFO", "json")
        assert len(logging.getLogger().handlers) == 1

    def test_uvicorn_lines_are_routed_through_our_handler(self):
        """uvicorn installs its own handlers and does not propagate."""
        uvicorn = logging.getLogger("uvicorn.access")
        uvicorn.addHandler(logging.StreamHandler())
        uvicorn.propagate = False

        configure_logging("INFO", "json")

        assert uvicorn.handlers == []
        assert uvicorn.propagate is True

    def test_the_text_format_is_the_default(self):
        configure_logging("INFO")
        formatter = logging.getLogger().handlers[0].formatter
        assert not isinstance(formatter, JsonFormatter)


def test_the_id_is_per_context_not_global():
    """Concurrent requests must not read each other's ids."""
    import asyncio

    async def one(value: str) -> str:
        set_correlation_id(value)
        await asyncio.sleep(0)
        return get_correlation_id()

    async def both() -> list[str]:
        return await asyncio.gather(*(asyncio.create_task(one(v)) for v in ("aaa", "bbb")))

    assert asyncio.run(both()) == ["aaa", "bbb"]


def test_a_job_id_is_a_usable_correlation_id():
    """The worker correlates on the job id, having no request to point at.

    If ids ever stop matching the safe shape, `set_correlation_id` replaces
    them with "-" and every worker line silently loses its correlation. This
    fails at that moment rather than at the next incident.
    """
    from app.models.base import new_id

    generated = new_id()
    assert set_correlation_id(generated) == generated

    from app.jobs.store import worker_identity

    # Not the worker identity, which is the other id in scope here: it is
    # "host:pid", and the colon fails the safe shape. Naming it keeps the two
    # apart if someone reaches for the nearer one later.
    assert set_correlation_id(worker_identity()) == "-"
