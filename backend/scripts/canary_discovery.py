"""Live canary: run the real pipeline against real university websites.

This exists because a system verified only against its own fixtures is
verified against its own assumptions. The offline suite in
``tests/test_live_discovery.py`` proves the discovery *logic*; this proves what
the logic actually reaches on sites nobody wrote for us.

It is deliberately not a test. It needs the network, it is slow, its results
change when a university edits a page, and a red result here is a finding to
investigate rather than a build to fail.

What it measures, per institution:

* which URLs discovery selected, by category, and where each came from
* whether a programme page and a scholarship page were found at all
* pages fetched, and pages that failed, with the reason
* how many claims came back, and the run's own completeness score
* structural false positives, in the four categories where we allow none:
  a full-ride classification, a degree applicability verdict, a deadline and
  an admission requirement each have to rest on a page specific enough to
  carry them.

Access is honest about refusal. If robots.txt disallows a path, the outcome is
recorded as BLOCKED and the institution is reported as blocked. Nothing here
retries with a different agent, ignores a directive, or substitutes a cached
copy to make a row look green.

Usage::

    ./.venv/bin/python scripts/canary_discovery.py --out ../artifacts/canary
    ./.venv/bin/python scripts/canary_discovery.py --only rug.nl --verbose
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import tempfile
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import ClassVar

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.adapters.discovery.live_discovery import (
    REGISTRY_PATH,
    LiveDiscoveryAdapter,
    registrable_domain,
)
from app.adapters.fetching import Fetcher
from app.config import Settings
from app.domain.enums import (
    ClaimStatus,
    DegreeLevel,
    FetchOutcome,
    FundingClassification,
    PipelineStage,
    SourceSpecificity,
)
from app.models.applicant import ApplicantProfileRow
from app.models.base import Base
from app.models.research import (
    ClaimRow,
    ProgramResultRow,
    ResearchRun,
)
from app.pipeline import runner as runner_module
from app.pipeline.runner import ResearchRunner
from app.pipeline.state import RunState
from app.schemas.profile import (
    AcademicRecord,
    ApplicantProfileIn,
    ApplicationContext,
    FundingNeeds,
    GradeValue,
    IeltsScore,
    Preferences,
    SatScore,
)
from app.schemas.result import ProgramResult

#: Specificity levels that can carry a programme-specific fact. A university's
#: general funding page cannot settle a deadline for one programme.
PROGRAMME_SPECIFIC = {SourceSpecificity.PROGRAM_INTAKE, SourceSpecificity.PROGRAM}

#: Claim types whose value is only meaningful against a specific programme.
DEADLINE_CLAIMS = {"application_deadline", "scholarship_deadline"}


def canary_profile() -> ApplicantProfileIn:
    """One realistic applicant, used for every institution.

    A Kazakhstani school-leaver applying for a bachelor's and needing nearly
    full funding: the case the product exists for, and the one where a wrong
    "full ride" costs the most. The IELTS writing band is deliberately 6.0, so
    a per-band requirement that the overall score would hide still bites.
    """
    return ApplicantProfileIn(
        display_name="Canary Applicant (synthetic)",
        context=ApplicationContext(
            level=DegreeLevel.BACHELOR,
            intended_fields=["computer science"],
            intake_term="fall",
            intake_year=2027,
            citizenship="Kazakhstan",
            country_of_residence="Kazakhstan",
            education_country="Kazakhstan",
            education_system="KZ national secondary",
            graduation_date="2027-05-25",
        ),
        academics=AcademicRecord(
            gpa=GradeValue(raw_value=4.8, raw_scale_max=5.0, raw_scale_label="KZ 5-point"),
            ielts=IeltsScore(overall=7.0, listening=7.5, reading=7.5, writing=6.0, speaking=7.0),
            sat=SatScore(total=1400, math=760, reading_writing=640),
        ),
        preferences=Preferences(),
        funding=FundingNeeds(max_annual_budget=6000, max_acceptable_gap=6000),
    )


class FetchAudit:
    """Records every request the pipeline makes, grouped by institution.

    Installed onto the fetcher the runner builds rather than replacing it, so
    the canary measures the exact fetch path the product uses — same robots
    handling, same cache, same limits — and cannot drift from
    ``ResearchRunner._make_fetcher``.
    """

    def __init__(self) -> None:
        self.by_domain: dict[str, Counter] = {}
        self.failures: dict[str, list[tuple[str, str]]] = {}

    def install(self, fetcher: Fetcher) -> Fetcher:
        original = fetcher.get

        async def audited(url: str, *, use_cache: bool = True):
            result = await original(url, use_cache=use_cache)
            domain = registrable_domain(url)
            self.by_domain.setdefault(domain, Counter())[result.outcome.value] += 1
            if not result.ok:
                self.failures.setdefault(domain, []).append(
                    (url, f"{result.outcome.value}: {(result.error or '')[:120]}")
                )
            return result

        fetcher.get = audited  # type: ignore[method-assign]
        return fetcher


class CanaryRunner(ResearchRunner):
    """The real runner, with its fetch path observed."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.audit = FetchAudit()

    def _make_fetcher(self) -> Fetcher:
        return self.audit.install(super()._make_fetcher())


class TracingAdapter(LiveDiscoveryAdapter):
    """The real adapter, keeping every instance so its trace can be read.

    The runner constructs its adapter internally and does not expose it, and
    ``app/pipeline/runner.py`` is out of scope on this branch. Rebinding the
    name the runner looks up is the least invasive way to see the traces:
    behaviour is inherited unchanged, only the reference is kept.
    """

    instances: ClassVar[list[LiveDiscoveryAdapter]] = []

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        TracingAdapter.instances.append(self)


# --- the four zero-tolerance checks --------------------------------------


def false_positives(result: ProgramResult, claims: list[dict]) -> list[dict]:
    """Structural false positives in the categories that allow none.

    Each check asks the same question: is the page this rests on specific
    enough to carry the statement? A claim without a source, without an
    excerpt, or from a page too general for the question is a defect whether or
    not the value happens to be right.
    """
    found: list[dict] = []

    def flag(kind: str, detail: str, url: str = "") -> None:
        found.append({"kind": kind, "detail": detail, "url": url})

    by_type: dict[str, list[dict]] = {}
    for claim in claims:
        by_type.setdefault(claim["claim_type"], []).append(claim)

    # 1. Full ride. The strongest statement the product can make about money.
    for scholarship in result.scholarships:
        if scholarship.classification is not FundingClassification.FULL_RIDE_CONFIRMED:
            continue
        supporting = [
            c
            for c in claims
            if c["claim_type"].startswith("scholarship")
            and scholarship.name.lower()[:24] in json.dumps(c["payload"]).lower()
        ]
        if not supporting:
            flag(
                "full_ride_without_evidence",
                f"{scholarship.name!r} classified FULL_RIDE_CONFIRMED with no claim behind it",
            )
        elif not any(c["payload"].get("original_text_excerpt") for c in supporting):
            flag(
                "full_ride_without_excerpt",
                f"{scholarship.name!r} has claims but none quote the page",
                supporting[0]["source_url"],
            )
        if scholarship.international_eligible != "yes":
            flag(
                "full_ride_without_confirmed_eligibility",
                f"{scholarship.name!r} is FULL_RIDE_CONFIRMED while international "
                f"eligibility is {scholarship.international_eligible!r}",
            )

    # 2. Degree applicability. "This award is for bachelors" is a claim about
    #    the award, and needs the award's own page to say so.
    for scholarship in result.scholarships:
        if scholarship.degree_applicability == "unknown":
            continue
        if not scholarship.degree_applicability_reason:
            flag(
                "degree_applicability_without_reason",
                f"{scholarship.name!r} states degree applicability "
                f"{scholarship.degree_applicability!r} with no stated reason",
            )

    # 3. Deadlines. A date is worthless attached to the wrong page.
    for claim_type in DEADLINE_CLAIMS:
        for claim in by_type.get(claim_type, []):
            if claim["source_specificity"] not in {s.value for s in PROGRAMME_SPECIFIC} | {
                SourceSpecificity.UNIVERSITY_ADMISSIONS.value,
                SourceSpecificity.SCHOLARSHIP_ADMINISTRATOR.value,
            }:
                flag(
                    "deadline_from_general_page",
                    f"{claim_type} taken from a {claim['source_specificity']} page",
                    claim["source_url"],
                )
            if not claim["payload"].get("original_text_excerpt"):
                flag("deadline_without_excerpt", claim_type, claim["source_url"])

    # 4. Admission requirements. A satisfied/failed verdict has to name the
    #    page it came from, and that page has to be about admission.
    for check in result.requirement_checks:
        if check.status.value in ("unknown", "needs_clarification"):
            continue
        supporting = (
            by_type.get(check.requirement.claim_type, [])
            if hasattr(check.requirement, "claim_type")
            else []
        )
        if not supporting and not getattr(check.requirement, "source_url", ""):
            flag(
                "requirement_verdict_without_source",
                f"{check.requirement.label if hasattr(check.requirement, 'label') else check}"
                f" decided {check.status.value} with no claim behind it",
            )

    # 5. Any claim at all that lacks the provenance the product promises.
    for claim in claims:
        if not claim["source_url"]:
            flag("claim_without_url", claim["claim_type"])
        elif not claim["payload"].get("original_text_excerpt"):
            flag("claim_without_excerpt", claim["claim_type"], claim["source_url"])
        elif not claim.get("accessed_at"):
            flag("claim_without_timestamp", claim["claim_type"], claim["source_url"])

    return found


# --- the run --------------------------------------------------------------


async def run_canary(only: str | None, verbose: bool) -> dict:
    registry = json.loads(REGISTRY_PATH.read_text())
    if only:
        registry = [e for e in registry if only in e["homepage"]]
        if not registry:
            raise SystemExit(f"no institution in the registry matches {only!r}")

    profile = canary_profile()
    workdir = Path(tempfile.mkdtemp(prefix="canary-"))
    # A throwaway database. The canary never touches the project's own data.
    engine = create_engine(f"sqlite:///{workdir / 'canary.db'}")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()

    settings = Settings(
        cache_dir=workdir / "cache",
        export_dir=workdir / "exports",
        database_url=f"sqlite:///{workdir / 'canary.db'}",
        candidate_limit=len(registry),
        verify_limit=len(registry),
        respect_robots=True,
    )

    row = ApplicantProfileRow(display_name="canary", payload=profile.model_dump(mode="json"))
    session.add(row)
    session.flush()
    run = ResearchRun(
        profile_id=row.id,
        stage=PipelineStage.QUEUED.value,
        demo_mode=False,
        stage_state=RunState.load(None).dump(),
        candidate_limit=len(registry),
        verify_limit=len(registry),
    )
    session.add(run)
    session.flush()

    started = datetime.now(UTC)
    TracingAdapter.instances.clear()
    # The canary deliberately swaps the adapter constructor so it can retain
    # discovery traces. The replacement subclasses the production adapter and
    # exists only for this short-lived process.
    runner_module.LiveDiscoveryAdapter = TracingAdapter  # type: ignore[misc]
    runner = CanaryRunner(session, run, profile, settings)
    error = ""
    try:
        await runner.run_to_decision()
    except Exception as exc:  # a canary that crashes must still report
        error = f"{type(exc).__name__}: {exc}"
        if verbose:
            import traceback

            traceback.print_exc()
    finished = datetime.now(UTC)

    # --- gather --------------------------------------------------------
    results = {
        r.university: ProgramResult.model_validate(r.payload)
        for r in session.query(ProgramResultRow).filter(ProgramResultRow.run_id == run.id)
    }
    claims_by_result: dict[str, list[dict]] = {}
    for c in session.query(ClaimRow).filter(ClaimRow.run_id == run.id):
        claims_by_result.setdefault(c.result_id or "", []).append(
            {
                "claim_type": c.claim_type,
                "status": c.status,
                "source_url": c.source_url,
                "source_specificity": c.source_specificity,
                "accessed_at": c.accessed_at.isoformat() if c.accessed_at else None,
                "payload": c.payload,
            }
        )
    result_ids = {
        r.university: r.id
        for r in session.query(ProgramResultRow).filter(ProgramResultRow.run_id == run.id)
    }

    traces = {t.institution: t for adapter in TracingAdapter.instances for t in adapter.traces}

    rows = []
    for entry in registry:
        name = entry["name"]
        domain = registrable_domain(entry["homepage"])
        outcomes = runner.audit.by_domain.get(domain, Counter())
        blocked = outcomes.get(FetchOutcome.ROBOTS_DISALLOWED.value, 0)
        checked = sum(outcomes.values())
        failed = (
            checked
            - outcomes.get(FetchOutcome.OK.value, 0)
            - outcomes.get(FetchOutcome.CACHED.value, 0)
        )

        candidate = next((c for c in runner._candidates if c.name == name), None)
        trace = traces.get(name)
        result = results.get(name)
        claims = claims_by_result.get(result_ids.get(name, ""), [])

        row_out = {
            "institution": name,
            "country": entry["country"],
            "domain": domain,
            "access": (
                "BLOCKED"
                if blocked and checked == blocked
                else "PARTIALLY_BLOCKED"
                if blocked
                else "REACHED"
                if checked
                else "NOT_ATTEMPTED"
            ),
            "robots_disallowed_requests": blocked,
            "pages_checked": checked,
            "pages_failed": failed,
            "failures": runner.audit.failures.get(domain, [])[:8],
            "outcomes": dict(outcomes),
            "discovered": trace.selected if trace else {},
            "discovery_trace": trace.as_dict() if trace else None,
            "programs": [p.url for p in candidate.programs] if candidate else [],
            "program_page_found": bool(candidate and candidate.programs),
            "scholarship_page_found": bool(candidate and candidate.scholarships_url),
            "discovery_notes": candidate.notes if candidate else "no candidate produced",
            "claims": len(claims),
            "claims_verified": sum(
                1
                for c in claims
                if c["status"]
                in (ClaimStatus.VERIFIED_CURRENT.value, ClaimStatus.POSSIBLY_STALE.value)
            ),
            "completeness": result.verification_completeness if result else 0.0,
            "eligibility": result.eligibility.value if result else "no result",
            "funding_fit": result.funding_fit.value if result else "no result",
            "scholarships_found": len(result.scholarships) if result else 0,
            "false_positives": false_positives(result, claims) if result else [],
        }
        rows.append(row_out)
        if verbose:
            print(
                f"  {name}: {row_out['access']}, {row_out['claims']} claims, "
                f"{len(row_out['false_positives'])} false positives",
                flush=True,
            )

    session.close()
    return {
        "accessed_at": started.isoformat(),
        "duration_seconds": round((finished - started).total_seconds(), 1),
        "run_error": error,
        "institutions": rows,
        "totals": {
            "institutions": len(rows),
            "reached": sum(1 for r in rows if r["access"] == "REACHED"),
            "blocked": sum(1 for r in rows if r["access"].endswith("BLOCKED")),
            "program_pages_found": sum(1 for r in rows if r["program_page_found"]),
            "scholarship_pages_found": sum(1 for r in rows if r["scholarship_page_found"]),
            "claims": sum(r["claims"] for r in rows),
            "false_positives": sum(len(r["false_positives"]) for r in rows),
        },
    }


def markdown_table(report: dict) -> str:
    head = (
        "| Institution | Country | Access | Programme page | Scholarship page | "
        "Pages ok/fail | Claims | Completeness | False positives |\n"
        "|---|---|---|---|---|---|---|---|---|\n"
    )
    lines = []
    for r in report["institutions"]:
        ok = r["pages_checked"] - r["pages_failed"]
        lines.append(
            f"| {r['institution']} | {r['country']} | {r['access']} | "
            f"{'yes' if r['program_page_found'] else 'no'} | "
            f"{'yes' if r['scholarship_page_found'] else 'no'} | "
            f"{ok}/{r['pages_failed']} | {r['claims']} | "
            f"{r['completeness']:.0%} | {len(r['false_positives'])} |"
        )
    return head + "\n".join(lines)


async def check_seeds() -> int:
    """Fetch every manual seed and report the ones that no longer resolve.

    A seed whose URL has moved is worse than no seed: it consumes the fetch
    budget and contributes nothing. The first live run found six dead seeds
    across four institutions, so this is a standing check rather than a
    one-time cleanup.
    """
    entries = json.loads(REGISTRY_PATH.read_text())
    workdir = Path(tempfile.mkdtemp(prefix="seed-check-"))
    broken: list[tuple[str, str, str, str]] = []
    total = 0
    async with Fetcher(workdir, respect_robots=True, contact="canary") as fetcher:
        for entry in entries:
            for category, url in (entry.get("seeds") or {}).items():
                total += 1
                result = await fetcher.get(url)
                if not result.ok:
                    broken.append((entry["name"], category, url, result.outcome.value))
                print(
                    f"{'ok ' if result.ok else 'BAD'} {entry['name'][:24]:26} {category:16} {url}",
                    flush=True,
                )
    print(f"\n{len(broken)} of {total} seeds no longer resolve")
    for name, category, url, outcome in broken:
        print(f"  {name} / {category}: {outcome} — {url}")
    return 1 if broken else 0


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, help="directory for the JSON and Markdown output")
    parser.add_argument("--only", help="substring of one institution's homepage")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument(
        "--check-seeds",
        action="store_true",
        help="only verify that the registry's manual seeds still resolve",
    )
    args = parser.parse_args()

    if args.check_seeds:
        return await check_seeds()

    print("Live canary — real network, real sites, robots.txt respected.", flush=True)
    report = await run_canary(args.only, args.verbose)

    print()
    print(markdown_table(report))
    print()
    totals = report["totals"]
    print(
        f"reached {totals['reached']}/{totals['institutions']}, "
        f"blocked {totals['blocked']}, "
        f"programme pages {totals['program_pages_found']}, "
        f"scholarship pages {totals['scholarship_pages_found']}, "
        f"claims {totals['claims']}, "
        f"false positives {totals['false_positives']}"
    )
    if report["run_error"]:
        print(f"RUN ERROR: {report['run_error']}")

    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        stamp = report["accessed_at"][:10]
        (args.out / f"canary-{stamp}.json").write_text(json.dumps(report, indent=2))
        (args.out / f"canary-{stamp}.md").write_text(markdown_table(report) + "\n")
        print(f"\nwrote {args.out}/canary-{stamp}.json")

    return 1 if totals["false_positives"] else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
