from __future__ import annotations

import hashlib
import importlib.util
import json
import socket
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

B = Path(__file__).resolve().parent
BASE = Path("/Users/wpalish/Documents/Codex/2026-10-07/x20/work")
REPO = BASE / "ashyq-apply/backend"
sys.path.insert(0, str(REPO))


def deny(*args, **kwargs):
    raise AssertionError("Offline lifecycle controls prohibit external calls")


socket.getaddrinfo = deny
socket.create_connection = deny
socket.socket.connect = deny
import httpx

httpx.Client.send = deny
httpx.AsyncClient.send = deny

from app.adapters.discovery import live_discovery as actual_live
from app.adapters.discovery import catalog_walker as actual_walker
from app.catalogue import discovery as actual_catalogue
from app.adapters.fetching import FetchResult
from app.domain.enums import FetchOutcome
from app.schemas.profile import ApplicantProfileIn

plan = json.loads((B / "PLAN.json").read_text())
for rel, want in plan["current_source_sha256"].items():
    assert hashlib.sha256((REPO / rel).read_bytes()).hexdigest() == want, rel


def load(name, rel):
    spec = importlib.util.spec_from_file_location(name, B / "proposed" / rel)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


helper = load("app.adapters.discovery.confirmed_routing", "app/adapters/discovery/confirmed_routing.py")
live = load("external_retention_live", "app/adapters/discovery/live_discovery.py")
live.REGISTRY_PATH = actual_live.REGISTRY_PATH
walker = load("external_retention_walker", "app/adapters/discovery/catalog_walker.py")
# The prototype catalogue's dependency must be this explicit external class seam.
with patch.dict(sys.modules, {"app.adapters.discovery.live_discovery": live}), patch(
    "app.adapters.discovery.live_discovery", live
):
    catalogue = load("external_retention_catalogue", "app/catalogue/discovery.py")
assert catalogue.LiveDiscoveryAdapter is live.LiveDiscoveryAdapter
assert catalogue.live_module is live
assert live.RETAIN_CONFIRMED_DISCOVERY_PARTIAL is False
assert actual_live.SUBJECT_PHRASE_MATCH is False

rows = json.loads((BASE / "local-round9/b-confirmed-coverage-plan/retained-receipt.json").read_text())["pages"]
retained = {}
for row in rows:
    raw = Path(row["body_owned"]).read_bytes()
    meta = json.loads(Path(row["meta_owned"]).read_text())
    assert hashlib.sha256(raw).hexdigest() == row["body_sha256"]
    retained[row["url"]] = (raw, meta)

CAT = "https://example.edu/bachelors/catalog"
PREFIX = "https://example.edu/bachelors/"
GRCS = "https://www.rug.nl/bachelors/computing-science"
GRCAT = "https://www.rug.nl/bachelors/alphabet"


def profile(fields=None):
    return ApplicantProfileIn.model_validate({
        "context": {"level": "bachelor", "intended_fields": fields if fields is not None else ["computer science"],
            "intake_term": "fall", "intake_year": 2027, "citizenship": "Kazakhstan",
            "country_of_residence": "Kazakhstan", "education_country": "Kazakhstan",
            "education_system": "KZ national secondary", "graduation_date": "2027-05-25"},
        "academics": {"gpa": {"raw_value": 4.8, "raw_scale_max": 5.0, "raw_scale_label": "KZ 5-point"},
            "ielts": {"overall": 7.0, "listening": 7.5, "reading": 7.5, "writing": 6.0, "speaking": 7.0},
            "sat": {"total": 1400, "math": 760, "reading_writing": 640}},
        "funding": {"max_annual_budget": 6000, "max_acceptable_gap": 6000}})


def programme(name="BSc Computer Science", extra=""):
    return f'<html><head><title>{name} | Example University</title></head><body><main><h1>{name}</h1><p>This degree programme provides practical and theoretical education.</p><section><h2>Curriculum</h2><p>Year 1 modules include programming, algorithms and mathematical foundations. Year 2 modules include software systems, databases and research projects, with 120 credits.</p></section>{extra}</main></body></html>'


def catalog(entries, cat=CAT):
    return {cat: '<html><head><title>Bachelor programmes</title></head><main><h1>Bachelor programmes</h1>' + ''.join(
        f'<a href="{url}">{label}</a>' for url, label, body in entries) + '</main></html>',
        **{url: body for url, label, body in entries}}


def result(url, item):
    if isinstance(item, FetchResult):
        return item
    if isinstance(item, tuple):
        raw, meta = item
        return FetchResult(url=url, final_url=meta["final_url"], outcome=FetchOutcome.OK,
            status_code=meta["status_code"], content=raw, text=raw.decode(meta["encoding"]),
            content_type=meta["content_type"], content_hash=meta["content_hash"],
            fetched_at=datetime.fromisoformat(meta["fetched_at"]))
    return FetchResult(url=url, final_url=url, outcome=FetchOutcome.OK, status_code=200,
        text=item, content=item.encode())


class MockFetcher:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    async def get(self, url, **kwargs):
        self.calls.append(url)
        item = self.pages[url]
        if isinstance(item, BaseException):
            raise item
        return result(url, item)


def entry(cat=CAT, programmes=None):
    seeds = {actual_live.PageCategory.PROGRAM_CATALOG: cat}
    if programmes:
        seeds[actual_live.PageCategory.PROGRAM_PAGE] = programmes[0]
    return {"name": "Example University", "country": "Netherlands", "city": "City",
        "homepage": "https://" + cat.split('/')[2] + "/", "seeds": seeds}


async def no_sitemaps(*args, **kwargs):
    return None


async def no_navigation(*args, **kwargs):
    return None


async def no_search(*args, **kwargs):
    return None


def error(exc):
    return {"type": type(exc).__name__, "reason": getattr(exc, "reason", None), "message": str(exc)}
