"""A pytest plugin that runs a test session with ticket PC-1's rule on.

``test_puc_clock.py`` runs the budget tests (read ledger, stage budgets, case
clock) and the NS-1 tests once with ``-p tests._sitemap_stage_cap_on``, so they
are measured with ``SITEMAP_STAGE_CAP`` on as well as off.
"""

from __future__ import annotations

from typing import Any


def pytest_configure(config: Any) -> None:
    from app.adapters.discovery import live_discovery

    live_discovery.SITEMAP_STAGE_CAP = True
