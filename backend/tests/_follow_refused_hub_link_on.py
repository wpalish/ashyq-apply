"""A pytest plugin that runs a test session with rule FRH on.

``test_follow_refused_hub_link.py`` runs the budget tests (read ledger, stage
budgets, case clock) and the R2b / SP-1 tests with
``-p tests._follow_refused_hub_link_on``, so they are measured with
``FOLLOW_REFUSED_HUB_LINK`` on as well as off.
"""

from __future__ import annotations

from typing import Any


def pytest_configure(config: Any) -> None:
    from app.adapters.discovery import live_discovery

    live_discovery.FOLLOW_REFUSED_HUB_LINK = True
