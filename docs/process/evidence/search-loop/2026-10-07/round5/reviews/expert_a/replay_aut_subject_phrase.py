# ruff: noqa: E402
"""Offline AUT reader replay using immutable saved body+metadata copies.

The production WebRequirementsAdapter executes. Fetcher.get is replaced only
by a two-page saved-byte lookup; provider factory, DNS and socket I/O are denied.
This does not test Fetcher transport or production read/time budget enforcement.
"""

import ast
import asyncio
import dataclasses
import hashlib
import importlib.util
import json
import socket
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("expert_a_external_loader", ROOT / "conftest.py")
loader = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
spec.loader.exec_module(loader)

from app.adapters.base import (
    Candidate,
    CandidateProgram,
)
from app.adapters.discovery import (
    live_discovery as discovery,
)
from app.adapters.extraction import (
    readable_text,
)
from app.adapters.fetching import (
    Fetcher,
    FetchResult,
    _content_hash,
)
from app.adapters.html_parse import (
    parse_html,
)
from app.adapters.page_classifier import (
    classify_page,
)
from app.adapters.requirements import (
    web_requirements as requirements,
)
from app.domain.enums import (
    ClaimType,
    DegreeLevel,
    FetchOutcome,
)

MANIFEST = json.loads((ROOT / "review-start.manifest.json").read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


original_path = ROOT / "source-original/backend/app/adapters/discovery/live_discovery.py"
original_text = original_path.read_text()
node = next(
    n
    for n in ast.parse(original_text).body
    if isinstance(n, ast.FunctionDef) and n.name == "matches_field_text"
)
namespace = dict(vars(discovery))
exec(ast.get_source_segment(original_text, node), namespace)
legacy_matcher = namespace["matches_field_text"]
new_matcher = discovery.matches_field_text


def denied(*args, **kwargs):
    raise AssertionError("Offline replay attempted network/provider access")


class SavedPages:
    def __init__(self, pages):
        self.pages = pages
        self.requested = []

    async def get(self, url, **kwargs):
        self.requested.append(url)
        saved = self.pages.get(url)
        if saved is None:
            return FetchResult(
                url=url,
                outcome=FetchOutcome.HTTP_ERROR,
                status_code=404,
                final_url=url,
                error="Offline: no original saved bytes for URL",
            )
        body, meta = saved
        return FetchResult(
            url=url,
            outcome=FetchOutcome.CACHED,
            status_code=meta.get("status_code", 200),
            content=body,
            text=body.decode(meta.get("encoding", "utf-8"), errors="replace"),
            content_type=meta.get("content_type", "text/html"),
            fetched_at=datetime.fromisoformat(meta["fetched_at"]),
            from_cache=True,
            final_url=meta.get("final_url", url),
            content_hash=meta.get("content_hash", ""),
            etag=meta.get("etag", ""),
            last_modified=meta.get("last_modified", ""),
        )


async def main():
    pages = {}
    evidence = []
    for item in MANIFEST["pages"]:
        body_path = Path(item["body_copy"])
        meta_path = Path(item["metadata_copy"])
        assert sha(body_path) == sha(Path(item["body_original"])) == item["body_sha256"]
        assert sha(meta_path) == sha(Path(item["metadata_original"])) == item["metadata_sha256"]
        body = body_path.read_bytes()
        meta = json.loads(meta_path.read_text())
        html = body.decode(meta.get("encoding", "utf-8"), errors="replace")
        calculated_hash = _content_hash(html)
        assert calculated_hash == meta["content_hash"]
        page = classify_page(url=item["url"], html=html, text=readable_text(html))
        soup = parse_html(html)
        pages[item["url"]] = (body, meta)
        evidence.append(
            dict(
                item,
                h1=[h.get_text(" ", strip=True) for h in soup.find_all("h1")],
                page_classification=dataclasses.asdict(page),
                calculated_content_hash=calculated_hash,
                content_hash_formula="fetching._content_hash(raw decoded HTML): NFKC normalized whitespace-collapsed html_to_text; distinct from raw body SHA256",
            )
        )
    rows = []
    for phase, enabled in [
        ("original", False),
        ("off1", False),
        ("on1", True),
        ("on2", True),
        ("off2", False),
    ]:
        matcher = legacy_matcher if phase == "original" else new_matcher
        with tempfile.TemporaryDirectory(prefix="offline-reader-", dir=ROOT) as temp:  # noqa: SIM117
            with (
                patch.object(socket, "getaddrinfo", denied),
                patch.object(socket, "create_connection", denied),
                patch.object(socket.socket, "connect", denied),
                patch("app.adapters.search.get_search_provider", denied),
            ):
                async with Fetcher(Path(temp) / "cache", offline=True) as fetcher:
                    saved = SavedPages(pages)
                    fetcher.get = saved.get
                    adapter = requirements.WebRequirementsAdapter(fetcher, "2027/28")
                    adapter._find_topic_pages = AsyncMock(return_value=[])
                    with (
                        patch.object(discovery, "SUBJECT_PHRASE_MATCH", enabled),
                        patch.object(discovery, "matches_field_text", matcher),
                        patch.object(requirements, "matches_field_text", matcher),
                    ):
                        for url, (body, meta) in pages.items():
                            name = discovery._program_name_from_url(
                                url, ["computer science"], DegreeLevel.BACHELOR
                            )
                            candidate = Candidate(
                                name="Auckland University of Technology",
                                country="New Zealand",
                                city="Auckland",
                                domain="aut.ac.nz",
                            )
                            program = CandidateProgram(
                                name=name,
                                field="computer science",
                                degree=DegreeLevel.BACHELOR,
                                url=url,
                            )
                            before = len(saved.requested)
                            observed = await adapter.verify(candidate, program, "fall2027")
                            claims = [c.model_dump(mode="json") for c in observed.claims]
                            rows.append(
                                {
                                    "phase": phase,
                                    "effective_subject_phrase_match": enabled,
                                    "source_url": url,
                                    "raw_body_sha256": hashlib.sha256(body).hexdigest(),
                                    "source_content_hash": meta["content_hash"],
                                    "requested_programme_name": name,
                                    "requested_field": "computer science",
                                    "requested_intake": "fall2027",
                                    "requested_academic_year": "2027/28",
                                    "claims": claims,
                                    "errors": list(observed.errors),
                                    "pages_checked": observed.pages_checked,
                                    "pages_failed": observed.pages_failed,
                                    "page_types": list(observed.page_types),
                                    "page_outcomes": [
                                        dataclasses.asdict(x) for x in observed.page_outcomes
                                    ],
                                    "saved_byte_lookup_calls": saved.requested[before:],
                                    "exists_count": sum(
                                        c["claim_type"] == ClaimType.PROGRAM_EXISTS.value
                                        for c in claims
                                    ),
                                    "intake_open_count": sum(
                                        c["claim_type"] == ClaimType.INTAKE_OPEN.value
                                        and c["normalized_value"] is True
                                        for c in claims
                                    ),
                                }
                            )

    def snapshot(row):
        return {
            k: v for k, v in row.items() if k not in ("phase", "effective_subject_phrase_match")
        }

    differences = []
    for url in pages:
        by_phase = {r["phase"]: r for r in rows if r["source_url"] == url}
        assert (
            snapshot(by_phase["original"])
            == snapshot(by_phase["off1"])
            == snapshot(by_phase["off2"])
        )
        assert snapshot(by_phase["on1"]) == snapshot(by_phase["on2"])
        is_cs = "/computer-science-major-" in url
        assert [by_phase[x]["exists_count"] for x in ("off1", "on1", "on2", "off2")] == (
            [1, 1, 1, 1] if is_cs else [1, 0, 0, 1]
        )
        old = by_phase["off1"]
        new = by_phase["on1"]
        old_claims = [c for c in old["claims"] if c["claim_type"] != ClaimType.PROGRAM_EXISTS.value]
        new_claims = [c for c in new["claims"] if c["claim_type"] != ClaimType.PROGRAM_EXISTS.value]
        assert old_claims == new_claims
        assert all(
            "intake status is unknown, not open" in " ".join(by_phase[x]["errors"])
            for x in by_phase
        )
        assert all(by_phase[x]["intake_open_count"] == 0 for x in by_phase)
        differences.append(
            {
                "source_url": url,
                "exists_off": old["exists_count"],
                "exists_on": new["exists_count"],
                "changed_snapshot_keys": [
                    k for k in snapshot(old) if snapshot(old)[k] != snapshot(new)[k]
                ],
                "other_claims_unchanged": True,
                "intake_remains_unknown": True,
                "programme_exists_excerpts_off": [
                    c["original_text_excerpt"]
                    for c in old["claims"]
                    if c["claim_type"] == ClaimType.PROGRAM_EXISTS.value
                ],
                "programme_exists_excerpts_on": [
                    c["original_text_excerpt"]
                    for c in new["claims"]
                    if c["claim_type"] == ClaimType.PROGRAM_EXISTS.value
                ],
            }
        )
    result = {
        "created_at_utc": datetime.now(UTC).isoformat(),
        "network_actions": 0,
        "real_provider_actions": 0,
        "real_model_actions": 0,
        "source_edited": False,
        "subject_phrase_default": False,
        "replay_script_sha256": sha(Path(__file__)),
        "source_original_sha256": MANIFEST["source_original_sha256"],
        "proposed_matcher_module_sha256": sha(
            ROOT / "proposed/backend/app/adapters/discovery/live_discovery.py"
        ),
        "phases": ["original", "off1", "on1", "on2", "off2"],
        "evidence": evidence,
        "rows": rows,
        "combined_snapshot_diffs": differences,
        "scope": "Actual WebRequirementsAdapter.verify over exact two retained AUT pages with saved-byte get; classifier/claim extraction production code. No discovery/selection/model/live run and no 2027 intake proof.",
    }
    (ROOT / "aut-subject-phrase.reader-replay.offline.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps(differences, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
