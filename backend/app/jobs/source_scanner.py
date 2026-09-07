"""Freshness 2.0: scanning tracked pages for change, and re-reading them.

Two job kinds live here:

- ``source_scan`` (run-less): one institution at a time, ask each tracked
  page whether it moved — sitemap ``lastmod`` where available, a content-hash
  conditional GET otherwise — and enqueue a ``reextract_page`` per affected
  (page, result) when the body actually changed. The job reschedules itself
  for the next UTC midnight (staggered per institution) on success, and
  ``reconcile_startup`` bootstraps it per institution with the same
  date-keyed idempotency, so a double bootstrap costs nothing.
- ``reextract_page`` (run-bound): re-read one page for one result through the
  pipeline's own extraction path, supersede the old live claims, and append
  the fresh ones — in the one transaction the job completes in, so a fenced
  or crashed attempt writes neither side.

Every network byte goes through ``Fetcher``: robots, rate limits and the PII
guard stay inside it, and a ROBOTS_DISALLOWED outcome here means "skip, and
record nothing".

Retention (C4) rides along: ``purge_source_pages`` bulk-deletes the rows the
T28 ``is_purgeable`` predicate calls purgeable. It is scheduled once a day
under the dedicated key ``source_scan:__purge__:{date}`` — the job store's
existing idempotency is the only mechanism it needs.
"""

from __future__ import annotations

import hashlib
import logging
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.adapters.base import Candidate, CandidateProgram
from app.adapters.fetching import Fetcher, FetchOutcome, FetchResult
from app.adapters.requirements.web_requirements import WebRequirementsAdapter
from app.config import Settings
from app.domain.enums import ClaimStatus, DegreeLevel
from app.domain.freshness import apply_freshness
from app.jobs.store import BACKOFF_SECONDS, JobStore
from app.models import (
    TERMINAL_STATUSES,
    ClaimRow,
    Job,
    JobStatus,
    ResearchRun,
    SourcePage,
)
from app.models.base import ensure_utc
from app.models.source_page import is_purgeable
from app.schemas.profile import ApplicantProfileIn

log = logging.getLogger("unimatch.sources")

#: Key prefix of the once-a-day retention purge. The date in the key IS the
#: generation: every completing scan enqueues it, the store deduplicates.
PURGE_KEY_PREFIX = "source_scan:__purge__:"
SCAN_KIND = "source_scan"
REEXTRACT_KIND = "reextract_page"


# --- scheduling slots --------------------------------------------------------


def next_scan_slot(institution: str) -> tuple[datetime, str]:
    """Tomorrow's UTC midnight, staggered per institution, and its key.

    The stagger is a digest, not ``hash()``: it must be stable across
    processes and restarts. The date inside the key is the scan's generation —
    one scan per institution per UTC day, whichever path enqueues it first.
    """
    tomorrow = (datetime.now(UTC) + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    digest = hashlib.sha256(institution.encode("utf-8")).hexdigest()
    stagger = int(digest, 16) % 3600
    return (
        tomorrow + timedelta(seconds=stagger),
        f"{SCAN_KIND}:{institution}:{tomorrow.date().isoformat()}",
    )


def bootstrap_source_scans(session: Session, settings: Settings) -> int:
    """Queue today's scan for every institution that has tracked pages.

    Called from ``reconcile_startup``. An institution with a queued or running
    scan for today's or tomorrow's key is left alone, so a worker restarting
    ten times enqueues exactly one scan per institution.
    """
    institutions = [
        row[0]
        for row in session.query(SourcePage.institution_key)
        .filter(SourcePage.institution_key.isnot(None))
        .distinct()
        .all()
    ]
    store = JobStore(session, lease_seconds=settings.job_lease_seconds)
    today = datetime.now(UTC).date().isoformat()
    enqueued = 0
    for institution in sorted(institutions):
        available_at, key = next_scan_slot(institution)
        live = (
            session.query(Job)
            .filter(
                Job.kind == SCAN_KIND,
                Job.idempotency_key.in_([f"{SCAN_KIND}:{institution}:{today}", key]),
                Job.status.in_([JobStatus.QUEUED.value, JobStatus.RUNNING.value]),
            )
            .first()
        )
        if live is not None:
            continue
        store.enqueue(
            SCAN_KIND,
            payload={"institution_key": institution},
            idempotency_key=key,
            available_at=available_at,
            priority=-10,  # housekeeping, never ahead of work a person waits for
        )
        enqueued += 1
    return enqueued


# --- reextract_page ----------------------------------------------------------


def enqueue_reextract(
    session: Session,
    *,
    source_page_id: str,
    url: str,
    reason: str,
    run_id: str,
    result_id: str,
    available_at: datetime | None = None,
) -> str:
    """Enqueue one page re-read for one result, under a generation key.

    The generation is the count of terminal jobs sharing the key's
    ``reextract:{page}:{result}:`` prefix — never a date — so a re-run after a
    completed reextract gets a fresh key, while two racing producers converge
    on the same key and the store's dedupe collapses them into one job.
    """
    prefix = f"reextract:{source_page_id}:{result_id}:"
    generation = (
        session.query(Job)
        .filter(
            Job.idempotency_key.like(f"{prefix}%"),
            Job.status.in_([status.value for status in TERMINAL_STATUSES]),
        )
        .count()
    )
    return (
        JobStore(session)
        .enqueue(
            REEXTRACT_KIND,
            run_id=run_id,
            available_at=available_at or datetime.now(UTC),
            payload={
                "source_page_id": source_page_id,
                "url": url,
                "reason": reason,
                "run_id": run_id,
                "result_id": result_id,
            },
            idempotency_key=f"{prefix}{generation}",
        )
        .job_id
    )


def _fetcher_for(settings: Settings, *, demo: bool) -> Fetcher:
    """The same Fetcher the runner builds — all traffic stays inside it."""
    return Fetcher(
        settings.cache_dir,
        delay_seconds=settings.fetch_delay_seconds,
        respect_robots=settings.respect_robots,
        offline=demo,
        cache_ttl_seconds=settings.cache_ttl_seconds,
        timeout=settings.fetch_timeout_seconds,
        contact=settings.fetch_contact,
        corpus_dir=settings.corpus_dir if demo else None,
    )


async def reextract_page(
    session: Session,
    job: Job,
    run: ResearchRun,
    profile: ApplicantProfileIn,
    settings: Settings,
) -> None:
    """Re-read one page through the pipeline's own extraction path.

    The fetch and the claim extraction are the runner's own (the requirements
    adapter classifies the page and runs the same html-rule extractors); what
    surrounds them is supersession: in the job's one transaction, every live
    claim of this run over this URL flips to SUPERSEDED (column and embedded
    payload — GET /claims reads the payload), keeps its value and gains the
    source-page link, and the fresh claims are appended next to them. A page
    that now yields nothing supersedes anyway: history is what the page no
    longer says, and keeping a VERIFIED_CURRENT row the page contradicts is
    the one thing this must never do.

    Anything raised here rolls the whole attempt back and lets the queue's
    backoff retry it — a half-applied supersession is worse than a late one.
    """
    payload: dict[str, Any] = job.payload or {}
    source_page_id = str(payload.get("source_page_id", ""))
    url = str(payload.get("url", ""))
    result_id = str(payload.get("result_id", ""))

    page = session.get(SourcePage, source_page_id)
    if page is None:
        raise LookupError(f"source page {source_page_id} is gone (purged?)")

    fetcher = _fetcher_for(settings, demo=run.demo_mode)
    async with fetcher:
        res = await fetcher.get(url)
        if not res.ok or res.status_code == 304:
            raise RuntimeError(f"reextract of {url}: the page could not be re-read ({res.error})")
        # The runner's own path for one page: classify, then extract. The
        # adapter's fetch lands on the just-filled cache, so the page is read
        # from the origin exactly once. The programme context comes from the
        # evidence being replaced (a result_id groups claims; it is not a
        # program_results primary key), and a mismatch there costs a
        # program_exists claim, never a false positive.
        program = CandidateProgram(
            name=_program_of(session, run.id, url), field="", degree=_DEFAULT_DEGREE, url=url
        )
        candidate = Candidate(
            name="",
            country="",
            city="",
            domain=page.registrable_domain,
            programs=[program],
        )
        adapter = WebRequirementsAdapter(fetcher, settings.academic_year)
        extracted = await adapter.verify(candidate, program, _intake_of(profile))

    if any(outcome.category == "fetch-failed" for outcome in extracted.page_outcomes):
        # A fetch that never produced the page is not evidence of anything.
        # Retry later; the live claims stand until the page is actually read.
        raise RuntimeError(f"reextract of {url}: the page could not be re-read")

    # Supersession scope: the destination result's run, per source_url.
    superseded = (
        session.query(ClaimRow)
        .filter(
            ClaimRow.run_id == run.id,
            ClaimRow.source_url == url,
            ClaimRow.status != ClaimStatus.SUPERSEDED.value,
        )
        .all()
    )
    for row in superseded:
        row.status = ClaimStatus.SUPERSEDED.value
        new_payload = dict(row.payload)
        new_payload["status"] = ClaimStatus.SUPERSEDED.value
        row.payload = new_payload
        row.source_page_id = page.id

    fresh = [
        claim.model_copy(
            update={"status": apply_freshness(claim.status, claim.claim_type, claim.accessed_at)}
        )
        for claim in extracted.claims
    ]
    for claim in fresh:
        session.add(
            ClaimRow(
                run_id=run.id,
                result_id=result_id,
                claim_type=claim.claim_type.value,
                status=claim.status.value,
                source_url=claim.source_url,
                source_specificity=claim.source_specificity.value,
                accessed_at=claim.accessed_at,
                payload=claim.model_dump(mode="json"),
                source_page_id=page.id,
            )
        )
    run.claims_recorded = (run.claims_recorded or 0) + len(fresh)

    _record_page(session, page, res, lastmod=None)
    log.info(
        "reextract of %s for result %s: %d claim(s) superseded, %d appended",
        url[:80],
        result_id[:8],
        len(superseded),
        len(fresh),
    )


def _intake_of(profile: ApplicantProfileIn) -> str:
    return f"{profile.context.intake_term} {profile.context.intake_year}"


#: Degree level for the re-read's programme context, when the replaced
#: evidence does not state one. Only used to match the page's programme
#: identity; a mismatch costs a program_exists claim, never a false positive.
_DEFAULT_DEGREE = DegreeLevel.MASTER


def _program_of(session: Session, run_id: str, url: str) -> str:
    """The programme name the live evidence for this page was read under."""
    row = (
        session.query(ClaimRow.payload)
        .filter(
            ClaimRow.run_id == run_id,
            ClaimRow.source_url == url,
            ClaimRow.status != ClaimStatus.SUPERSEDED.value,
        )
        .first()
    )
    if row is None:
        return ""
    program = (row[0] or {}).get("program")
    return str(program) if program else ""


def _record_page(
    session: Session, page: SourcePage, res: FetchResult, *, lastmod: datetime | None
) -> SourcePage:
    """Persist one fetch's metadata onto the page row, then advance lastmod.

    ``record`` coalesces ``lastmod_seen`` (an existing value wins over None),
    so the new value is set directly on the returned instance — the one way,
    per the T28 contract, that lastmod actually advances.
    """
    recorded = SourcePage.record(
        session,
        url=page.url,
        registrable_domain=page.registrable_domain,
        etag=res.etag or None,
        last_modified_header=res.last_modified or None,
        content_hash=res.content_hash or None,
        http_status=res.status_code,
        page_type=page.page_type,
        institution_key=page.institution_key,
        fetched_at=res.fetched_at,
    )
    seen = lastmod or (res.fetched_at if res.last_modified else None)
    if seen is not None:
        recorded.lastmod_seen = seen
    session.add(recorded)
    return recorded


# --- source_scan -------------------------------------------------------------


async def run_source_scan(
    session: Session,
    job: Job,
    settings: Settings,
) -> None:
    """Scan one institution's tracked pages, then reschedule for tomorrow.

    Run-less by design: the job carries an institution key, not a run. The
    lease is renewed by the worker's own heartbeat task, never from inside
    this transaction — a heartbeat here would hold an uncommitted jobs-row
    lock across a page fetch, and a lease takeover racing that fetch would
    deadlock against it. The reschedule is enqueued in the same transaction
    as the scan's own completion, so a scan leaves both or neither.
    """
    scan_payload: dict[str, Any] = job.payload or {}
    institution = str(scan_payload.get("institution_key") or "")
    if not institution:
        raise ValueError("source_scan payload carries no institution_key")

    pages = session.query(SourcePage).filter(SourcePage.institution_key == institution).all()
    fetcher = _fetcher_for(settings, demo=settings.demo_mode)
    async with fetcher:
        if pages:
            await _scan_institution(session, fetcher, pages)

    store = JobStore(session, lease_seconds=settings.job_lease_seconds)
    available_at, key = next_scan_slot(institution)
    store.enqueue(
        SCAN_KIND,
        payload={"institution_key": institution},
        idempotency_key=key,
        available_at=available_at,
        priority=-10,
    )
    _schedule_daily_purge(store)


async def _scan_institution(
    session: Session,
    fetcher: Fetcher,
    pages: list[SourcePage],
) -> None:
    domains: dict[str, list[SourcePage]] = defaultdict(list)
    for page in pages:
        domains[page.registrable_domain].append(page)

    for domain, domain_pages in sorted(domains.items()):
        sitemap = await fetcher.get(f"https://{domain}/sitemap.xml", use_cache=False)
        if sitemap.outcome == FetchOutcome.ROBOTS_DISALLOWED:
            # The host has closed itself to us. Nothing is recorded, so the
            # next scan starts as if this one never looked.
            log.info("scan of %s: robots disallows the sitemap; skipping", domain)
            continue
        lastmod_map = _parse_sitemap(sitemap.text) if sitemap.ok and sitemap.text else {}
        checked: set[str] = set()
        for page in sorted(domain_pages, key=lambda p: p.url):
            lastmod = lastmod_map.get(page.url)
            seen = ensure_utc(page.lastmod_seen)
            if lastmod is not None and seen is not None and lastmod <= seen:
                continue  # fresh by the sitemap's own account
            if lastmod is not None or page.lastmod_seen is None:
                checked.add(page.url)
                await _check_page(
                    session,
                    fetcher,
                    page,
                    reason="sitemap_lastmod",
                    lastmod=lastmod,
                )
        if not lastmod_map:
            # No lastmod to lean on (or none for these pages): sweep the
            # claim-bearing pages by content hash instead. Pages without live
            # claims stay metadata-only.
            for page in sorted(domain_pages, key=lambda p: p.url):
                if page.url in checked or page.active_claims <= 0:
                    continue
                await _check_page(
                    session,
                    fetcher,
                    page,
                    reason="content_hash",
                    lastmod=None,
                )


async def _check_page(
    session: Session,
    fetcher: Fetcher,
    page: SourcePage,
    *,
    reason: str,
    lastmod: datetime | None,
) -> None:
    """One conditional GET, and whatever it honestly implies.

    304: the copy is current — touch fetched_at and nothing else. 200 with a
    moved content hash: enqueue one reextract per affected (page, result),
    then persist the new validators and advance lastmod. Unchanged, or a
    fetch we cannot act on: metadata only, or nothing at all.
    """
    res = await fetcher.get(
        page.url, use_cache=False, etag=page.etag, if_modified_since=page.last_modified_header
    )
    if res.status_code == 304:
        page.fetched_at = datetime.now(UTC)
        session.add(page)
        return
    if res.outcome == FetchOutcome.ROBOTS_DISALLOWED:
        return
    if not res.ok:
        # Transient: leave the row exactly as it was for the next scan.
        return

    if (res.content_hash or "") != (page.content_hash or ""):
        affected = (
            session.query(ClaimRow.run_id, ClaimRow.result_id)
            .filter(
                ClaimRow.source_url == page.url,
                ClaimRow.status != ClaimStatus.SUPERSEDED.value,
                ClaimRow.result_id.isnot(None),
            )
            .distinct()
            .all()
        )
        for run_id, result_id in sorted(affected):
            enqueue_reextract(
                session,
                source_page_id=page.id,
                url=page.url,
                reason=reason,
                run_id=str(run_id),
                result_id=str(result_id),
                # A scan that is still mid-flight must not hand the queue work
                # it would then execute inside the same tick: the re-read
                # rides the next poll, on the queue's own short-step cadence.
                available_at=datetime.now(UTC) + timedelta(seconds=BACKOFF_SECONDS[0]),
            )
    _record_page(session, page, res, lastmod=lastmod)


def _schedule_daily_purge(store: JobStore) -> None:
    """Queue today's retention purge, once, under a dedicated dated key."""
    today = datetime.now(UTC).date().isoformat()
    tomorrow = (datetime.now(UTC) + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    store.enqueue(
        SCAN_KIND,
        payload={"purge": True},
        idempotency_key=f"{PURGE_KEY_PREFIX}{today}",
        available_at=tomorrow,
        priority=-10,
    )


def purge_source_pages(session: Session, now: datetime) -> int:
    """Bulk-delete the page rows the retention policy calls purgeable.

    The T28 predicate is the policy; this is only its execution. The
    claims.source_page_id FK is ON DELETE SET NULL, so purging a page whose
    only referencers are SUPERSEDED keeps the history rows intact; pages with
    live claims are never purgeable in the first place. Returns the count.
    """
    rows = session.query(SourcePage).all()
    doomed = [
        row for row in rows if is_purgeable(row.fetched_at, row.created_at, row.active_claims, now)
    ]
    if not doomed:
        return 0
    # Detach the doomed instances before the bulk delete: the bulk DELETE says
    # nothing to the identity map, and a stale instance here would come back
    # to haunt its next ``session.get`` as ObjectDeletedError.
    for row in doomed:
        session.expunge(row)
    session.query(SourcePage).filter(SourcePage.id.in_([row.id for row in doomed])).delete(
        synchronize_session=False
    )
    session.flush()
    log.info("purged %d source page row(s) past retention", len(doomed))
    return len(doomed)


# --- sitemap -----------------------------------------------------------------


def _parse_sitemap(body: str) -> dict[str, datetime]:
    """The <loc> -> <lastmod> pairs of a sitemap.xml, if it has any."""
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        return {}
    out: dict[str, datetime] = {}
    for element in root.iter():
        if element.tag.rpartition("}")[2] != "url":
            continue
        loc = ""
        lastmod = ""
        for child in element:
            name = child.tag.rpartition("}")[2]
            if name == "loc":
                loc = (child.text or "").strip()
            elif name == "lastmod":
                lastmod = (child.text or "").strip()
        if loc and lastmod:
            parsed = _parse_timestamp(lastmod)
            if parsed is not None:
                out[loc] = parsed
    return out


def _parse_timestamp(raw: str) -> datetime | None:
    """A sitemap W3C datetime, naive values read as UTC."""
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
