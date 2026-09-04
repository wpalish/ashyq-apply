"""Process metrics in the Prometheus text format.

Deliberately hand-written rather than pulled from `prometheus_client`. What is
needed here is four numbers and a histogram; the dependency would bring a
registry, a multiprocess mode and a WSGI app to avoid writing forty lines.

Two honest limitations, both of which an operator has to know to read the
numbers correctly:

* **Counters are per process.** Two API processes answer with their own totals,
  and a restart resets them. That is normal for Prometheus counters — `rate()`
  handles both — but it means these are not billing figures.
* **The gauges are read at scrape time** from the database, so they describe
  the queue right now rather than a moving average.

Nothing here is scoped to a tenant, and nothing carries applicant data: the
labels are HTTP methods, route templates, statuses and job states. That is the
property that lets the endpoint be exposed to a monitoring system at all, and
`tests/test_metrics.py` asserts it.
"""

from __future__ import annotations

import logging
import threading
from collections import Counter

log = logging.getLogger("unimatch.metrics")

CONTENT_TYPE = "text/plain; version=0.0.4; charset=utf-8"

#: Seconds. The tail matters more than the middle here — a run enqueue that
#: takes ten seconds is the interesting event, not the difference between 5ms
#: and 7ms on a health check.
BUCKETS: tuple[float, ...] = (0.005, 0.025, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)

# ponytail: one lock around counter updates. Contention is a dict update per
# request, which is nothing next to the work the request itself does; per-metric
# locks or atomics would only matter at a request rate this product will not see.
_lock = threading.Lock()

_requests: Counter[tuple[str, str, int]] = Counter()
_rate_limited: Counter[str] = Counter()
_bucket_counts: list[int] = [0] * (len(BUCKETS) + 1)
_latency_sum: float = 0.0
_database_errors: int = 0


def reset() -> None:
    """Empty the registry. For tests, which must not read each other's numbers."""
    global _latency_sum, _database_errors
    with _lock:
        _requests.clear()
        _rate_limited.clear()
        for i in range(len(_bucket_counts)):
            _bucket_counts[i] = 0
        _latency_sum = 0.0
        _database_errors = 0


def observe_request(method: str, route: str, status: int, seconds: float) -> None:
    """Record one finished HTTP request.

    `route` must be the route *template* (`/api/runs/{run_id}`), never the URL
    that was requested. A run id in a label is a new time series for every run,
    which is how a metrics endpoint becomes a memory leak in the scraper.
    """
    global _latency_sum
    index = len(BUCKETS)
    for i, bound in enumerate(BUCKETS):
        if seconds <= bound:
            index = i
            break
    with _lock:
        _requests[(method, route, status)] += 1
        _bucket_counts[index] += 1
        _latency_sum += seconds


def count_rate_limited(group: str) -> None:
    """Record a request the limiter turned away.

    Refusals used to leave no trace at all: no log line and no number, so a
    limit set too low was invisible until a user complained.
    """
    with _lock:
        _rate_limited[group] += 1


def _escape(value: str) -> str:
    return value.replace("\\", r"\\").replace('"', r"\"").replace("\n", r"\n")


def _labels(pairs: dict[str, str]) -> str:
    if not pairs:
        return ""
    inner = ",".join(f'{k}="{_escape(v)}"' for k, v in pairs.items())
    return "{" + inner + "}"


def _database_gauges() -> list[str]:
    """Queue and pipeline state, counted in the database at scrape time."""
    global _database_errors
    lines: list[str] = []
    try:
        from sqlalchemy import func, select

        import app.db as db_module
        from app.jobs.store import JobStore
        from app.models import ResearchRun

        # Resolved at call time: the session factory is swapped by the test
        # suite, and replaced by anything that reconnects after a failure.
        session = db_module.SessionLocal()
        try:
            jobs = JobStore(session).counts()
            # A grouped count, not a row per run: this endpoint is scraped every
            # few seconds and has to stay cheap on a large table.
            stages = session.execute(
                select(ResearchRun.stage, func.count()).group_by(ResearchRun.stage)
            ).all()
        finally:
            session.close()
    except Exception as exc:  # a blind operator is worse than an incomplete scrape
        with _lock:
            _database_errors += 1
        log.warning("metrics could not read the database: %s", exc)
        return lines

    lines.append("# HELP ashyq_jobs Jobs in the durable queue, by status.")
    lines.append("# TYPE ashyq_jobs gauge")
    for status, count in sorted(jobs.items()):
        lines.append(f"ashyq_jobs{_labels({'status': str(status)})} {count}")

    lines.append("# HELP ashyq_runs Research runs, by pipeline stage.")
    lines.append("# TYPE ashyq_runs gauge")
    for stage, count in sorted(stages, key=lambda row: str(row[0])):
        lines.append(f"ashyq_runs{_labels({'stage': str(stage)})} {count}")
    return lines


def render() -> str:
    """The whole registry, in the format a Prometheus scraper parses."""
    with _lock:
        requests = dict(_requests)
        refusals = dict(_rate_limited)
        buckets = list(_bucket_counts)
        latency_sum = _latency_sum

    lines: list[str] = []

    lines.append("# HELP ashyq_http_requests_total HTTP requests served, by route and status.")
    lines.append("# TYPE ashyq_http_requests_total counter")
    for (method, route, status), count in sorted(requests.items()):
        labels = _labels({"method": method, "route": route, "status": str(status)})
        lines.append(f"ashyq_http_requests_total{labels} {count}")

    total = sum(buckets)
    lines.append("# HELP ashyq_http_request_duration_seconds Time to serve a request, in seconds.")
    lines.append("# TYPE ashyq_http_request_duration_seconds histogram")
    cumulative = 0
    for bound, count in zip(BUCKETS, buckets, strict=False):
        cumulative += count
        lines.append(
            f"ashyq_http_request_duration_seconds_bucket{_labels({'le': _number(bound)})} "
            f"{cumulative}"
        )
    lines.append(f"ashyq_http_request_duration_seconds_bucket{_labels({'le': '+Inf'})} {total}")
    lines.append(f"ashyq_http_request_duration_seconds_sum {latency_sum:.6f}")
    lines.append(f"ashyq_http_request_duration_seconds_count {total}")

    lines.append("# HELP ashyq_rate_limited_total Requests the abuse limiter refused.")
    lines.append("# TYPE ashyq_rate_limited_total counter")
    for group, count in sorted(refusals.items()):
        lines.append(f"ashyq_rate_limited_total{_labels({'group': group})} {count}")

    lines.extend(_database_gauges())

    lines.append(
        "# HELP ashyq_metrics_database_errors_total Scrapes that could not read the database."
    )
    lines.append("# TYPE ashyq_metrics_database_errors_total counter")
    lines.append(f"ashyq_metrics_database_errors_total {_database_errors}")

    return "\n".join(lines) + "\n"


def _number(value: float) -> str:
    """`0.005`, not `0.005000000001`; Prometheus compares bucket bounds as text."""
    return f"{value:g}"
