"""A pytest plugin that runs a test session with rule NS-1 on.

``test_homepage_hop_reads.py`` runs the budget tests (read ledger, stage
budgets, case clock) once with ``-p tests._homepage_hop_reads_on``, so they are
measured with ``HOMEPAGE_HOP_READS`` on as well as off.
"""

from __future__ import annotations

from typing import Any


def pytest_configure(config: Any) -> None:
    from app.adapters.discovery import live_discovery

    live_discovery.HOMEPAGE_HOP_READS = True
