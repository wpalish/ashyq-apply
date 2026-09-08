"""The paywall surface scan: every material-returning route, checked as free.

T33 A1 frozen contract §2. Three things are pinned here at once:

1. Discovery. ``app.routes`` is walked for routes under ``^/api/runs/{run_id}``
   and ``^/api/profiles/{profile_id}`` (proper prefixes) answering GET, POST,
   PATCH or PUT with a body — enqueue/no-content statuses 202 and 204 are out.
2. Inventory. The discovered set must equal a frozen 17-route list. A route
   added to either surface without a decision here fails the suite, because a
   new route is how a paywall quietly stops being one.
3. Execution. Each route is served once to a free organization (payments on,
   no entitlement) and the response is walked recursively for the material
   dictionary: non-empty arrays under claims/conflicts/scholarships/
   requirement_checks/missing_prerequisites/hard_filter_failures/unresolved/
   source_urls/eligibility_checks; non-empty funding_gap/checklist;
   verification_completeness != 0; non-empty career_notes/post_study_work/
   work_during_study; admission_deadline_raw; any dict carrying claim_type.
   Counts arrays in the summary, ranking coverage scalars, route metadata and
   paid_content_withheld are not material.

On the unfixed baseline this file fails on exactly three parameters — the
decision route, the notes route and the profile export. The failing-parameter
list IS the leak inventory; any fourth failure is a new finding, not noise.
"""

from __future__ import annotations

import asyncio
import re

import pytest

from tests.test_paywall import _seed_paid_material_into_first_row, drain

#: Proper prefixes: the surface behind a run id or a profile id, not the
#: id-bearing routes themselves (a run view or a profile view carries none of
#: the fetched evidence this scan guards).
RUN_SURFACE = re.compile(r"^/api/runs/\{run_id\}/")
PROFILE_SURFACE = re.compile(r"^/api/profiles/\{profile_id\}/")
METHODS = {"GET", "POST", "PATCH", "PUT"}
#: Routes that enqueue work or return no body never carry material.
NO_BODY_STATUS = {202, 204}

#: The frozen inventory. Change only as a deliberate, reviewed decision.
FROZEN_INVENTORY = {
    ("POST", "/api/runs/{run_id}/cancel"),
    ("GET", "/api/runs/{run_id}/claims"),
    ("GET", "/api/runs/{run_id}/conflicts"),
    ("GET", "/api/runs/{run_id}/deadlines"),
    ("GET", "/api/runs/{run_id}/deadlines.ics"),
    ("GET", "/api/runs/{run_id}/export.{fmt}"),
    ("GET", "/api/runs/{run_id}/questions"),
    ("POST", "/api/runs/{run_id}/rerank"),
    ("GET", "/api/runs/{run_id}/results"),
    ("GET", "/api/runs/{run_id}/results/{result_id}"),
    ("POST", "/api/runs/{run_id}/results/{result_id}/decision"),
    ("PATCH", "/api/runs/{run_id}/results/{result_id}/notes"),
    ("POST", "/api/runs/{run_id}/retry"),
    ("GET", "/api/runs/{run_id}/shortlist"),
    ("GET", "/api/runs/{run_id}/summary"),
    ("GET", "/api/profiles/{profile_id}/export"),
    ("GET", "/api/profiles/{profile_id}/validation"),
}

#: Request bodies for the surface's write routes. Everything else is served
#: with no body at all.
REQUEST_BODIES = {
    ("POST", "/api/runs/{run_id}/results/{result_id}/decision"): {
        "decision": "maybe",
        "reason": "surface scan",
        "notes": "surface scan",
    },
    ("PATCH", "/api/runs/{run_id}/results/{result_id}/notes"): {"notes": "surface scan"},
    ("POST", "/api/runs/{run_id}/rerank"): {
        "priorities": None,
        "preferences": None,
        "funding": None,
    },
}

MATERIAL_ARRAY_KEYS = {
    "claims",
    "conflicts",
    "scholarships",
    "requirement_checks",
    "missing_prerequisites",
    "hard_filter_failures",
    "unresolved",
    "source_urls",
    "eligibility_checks",
}
MATERIAL_VALUE_KEYS = {"funding_gap", "checklist"}
MATERIAL_TEXT_KEYS = {"career_notes", "post_study_work", "work_during_study"}


def _material_hits(node: object, where: str = "response") -> list[str]:
    """Paths into ``node`` where the material dictionary is present."""
    hits: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            spot = f"{where}.{key}"
            if (
                (key in MATERIAL_ARRAY_KEYS and isinstance(value, list) and bool(value))
                or (key in MATERIAL_VALUE_KEYS and value not in (None, {}, [], ""))
                or (
                    key == "verification_completeness"
                    and value != 0
                    and isinstance(value, int | float)
                )
                or (key in MATERIAL_TEXT_KEYS and isinstance(value, str) and bool(value.strip()))
                or (key == "admission_deadline_raw" and value not in (None, ""))
            ):
                hits.append(spot)
            if isinstance(value, dict) and "claim_type" in value:
                hits.append(f"{spot}.claim_type")
            hits.extend(_material_hits(value, spot))
    elif isinstance(node, list):
        for index, item in enumerate(node):
            hits.extend(_material_hits(item, f"{where}[{index}]"))
    return hits


def _discovered_surface_routes() -> set[tuple[str, str]]:
    """(method, path) pairs the app actually serves on the two surfaces."""
    from app.main import app

    found: set[tuple[str, str]] = set()
    for top in app.routes:
        context = getattr(top, "include_context", None)
        if context is not None and hasattr(top, "original_router"):
            # FastAPI >= 0.141 wraps each include_router in an _IncludedRouter.
            prefix = getattr(context, "prefix", "") or ""
            routes = list(top.original_router.routes)
        elif hasattr(top, "methods"):
            prefix, routes = "", [top]
        elif hasattr(top, "routes"):
            prefix = getattr(top, "path_prefix", "") or ""
            routes = list(top.routes)
        else:
            continue
        for route in routes:
            path = prefix + str(getattr(route, "path", ""))
            methods = {m for m in (getattr(route, "methods", None) or ()) if m in METHODS}
            status = getattr(route, "status_code", None)
            status = 200 if status is None else status
            if not methods or status in NO_BODY_STATUS:
                continue
            if RUN_SURFACE.match(path) or PROFILE_SURFACE.match(path):
                found.update((method, path) for method in methods)
    return found


def test_the_paywall_surface_inventory_matches_the_frozen_list() -> None:
    """A route added to or removed from the surface is a decision, not a drift."""
    discovered = _discovered_surface_routes()
    vanished = FROZEN_INVENTORY - discovered
    appeared = discovered - FROZEN_INVENTORY
    assert not vanished, f"routes left the run/profile surface: {sorted(vanished)}"
    assert not appeared, (
        "A new route appeared on the run/profile surface. Decide whether it "
        "returns paid material: if it does, require_full_access or project it "
        "through free_view, then add it to FROZEN_INVENTORY in this file. "
        f"Unlisted route(s): {sorted(appeared)}"
    )


@pytest.fixture
def surface_run(paid_client, case_id) -> dict[str, str]:
    """A finished free demo run whose first row provably carries material."""
    run = paid_client.post("/api/runs", json={"profile_id": case_id, "demo_mode": True}).json()
    asyncio.run(drain())
    return {
        "run_id": run["id"],
        "profile_id": case_id,
        "result_id": _seed_paid_material_into_first_row(run["id"]),
    }


@pytest.mark.parametrize(("method", "path"), sorted(FROZEN_INVENTORY))
def test_a_free_org_receives_no_paid_material_from(
    method: str, path: str, paid_client, surface_run
) -> None:
    url = path.format(
        run_id=surface_run["run_id"],
        result_id=surface_run["result_id"],
        profile_id=surface_run["profile_id"],
        fmt="json",
    )
    response = paid_client.request(method, url, json=REQUEST_BODIES.get((method, path)))
    assert response.status_code < 500, f"{method} {url} crashed: {response.text[:400]}"
    try:
        body = response.json()
    except ValueError:
        return  # a non-JSON body (a file download) carries no walkable material
    hits = _material_hits(body)
    assert not hits, (
        f"{method} {path} handed paid material to a free organization at: {hits}. "
        "Project the answer through free_view or require_full_access."
    )
