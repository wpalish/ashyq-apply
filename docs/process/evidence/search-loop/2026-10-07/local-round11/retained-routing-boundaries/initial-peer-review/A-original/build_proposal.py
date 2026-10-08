from pathlib import Path
import hashlib,json,difflib
B=Path(__file__).resolve().parent;BASE=B.parents[1];REPO=BASE/'ashyq-apply/backend';plan=json.loads((B/'PLAN.json').read_text())
files=['app/adapters/discovery/catalog_walker.py','app/adapters/discovery/live_discovery.py','app/catalogue/discovery.py']
for rel in files:
 data=(REPO/rel).read_bytes();assert hashlib.sha256(data).hexdigest()==plan['current_source_sha256'][rel]
 p=B/'original'/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
# Source proof helper: unchanged scoped academic proof, local own-degree and strict field identity.
old=(BASE/'local-round10/a-strict-walker-preparation/catalog_walker.proposed.py').read_text()
start=old.index('def _route_normalize(');end=old.index('\n@dataclass(frozen=True)\nclass WalkerLink:')
helper='''"""Strict in-memory routing proof; never Claim/applicant/intake coverage."""
from __future__ import annotations
import re, unicodedata
from urllib.parse import urlparse
from bs4 import Tag
from app.adapters import page_classifier as _route_pc
from app.adapters.page_classifier import PageClassification,PageType
from app.adapters.fetching import FetchResult
from app.adapters.html_parse import parse_html
from app.adapters.search.ontology import canonical_field

'''+old[start:end]
# Retention cannot treat an explicit non-degree purpose as an offered full degree.
needle='''    # Reuse existing scoped academic-purpose proof without a whole-page fallback.
'''
helper=helper.replace(needle,'''    own_text = root.get_text(" ", strip=True)
    if re.search(
        r"\\bnon[- ]degree\\b|\\b(?:does?|do) not (?:offer|award)\\b[^.]{0,60}\\bdegree\\b"
        r"|\\bno degree\\b[^.]{0,40}\\b(?:awarded|offered)\\b",
        own_text, re.I,
    ):
        return None
'''+needle)
helper=helper.replace('def _own_field_route(','def own_field_route(')
p=B/'proposed/app/adapters/discovery/confirmed_routing.py';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(helper)
# Walker: normal acceptance callback only; no catch, no cut and no return-shape change.
rel=files[0];s=(B/'original'/rel).read_text()
s=s.replace('''        page_recorder: Callable[..., object] | None = None,
    ) -> None:
        self.fetcher = fetcher''','''        page_recorder: Callable[..., object] | None = None,
        confirmation_callback: Callable[..., None] | None = None,
    ) -> None:
        self.confirmation_callback = confirmation_callback
        self.fetcher = fetcher''',1)
s=s.replace('''        walk.outcomes.append((link.url, page.page_type.value))

    async def _read_catalogue(''','''        walk.outcomes.append((link.url, page.page_type.value))
        if self.confirmation_callback is not None:
            self.confirmation_callback(link.url, result, page, walk.confirmed)

    async def _read_catalogue(''',1)
p=B/'proposed'/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s)
# Live: normal confirmation publication; typed read_cap wrapper retains snapshot only.
rel=files[1];s=(B/'original'/rel).read_text();s=s.replace('from contextlib import AbstractContextManager, nullcontext\n','from contextlib import AbstractContextManager, nullcontext\nfrom copy import deepcopy\n',1)
s=s.replace('from app.adapters.base import Candidate, CandidateProgram, PageOutcome\n','from app.adapters.base import Candidate, CandidateProgram, PageOutcome\nfrom app.adapters.discovery.confirmed_routing import own_field_route\n',1)
marker='\n\n@dataclass\nclass DiscoveryTrace:'
new='''
# External lifecycle experiment. Native read_cap only; no deadline/cancellation conversion.
RETAIN_CONFIRMED_DISCOVERY_PARTIAL = False


def retained_partial(publication, stopped: UniversityReadStopped):
    """Only accounting/diagnostics merge on unwind; never _apply or source I/O."""
    candidate, trace, current_trace = publication
    candidate, trace = deepcopy(candidate), deepcopy(trace)
    latest = max(candidate.search_queries_used, trace.search_queries_sent, current_trace.search_queries_sent)
    candidate.search_queries_used = trace.search_queries_sent = latest
    trace.search_failures = list(dict.fromkeys([*trace.search_failures, *current_trace.search_failures]))
    trace.search_limitations = list(dict.fromkeys([*trace.search_limitations, *current_trace.search_limitations]))
    trace.search_limitations.append(
        f"Partial discovery: previously read strict programme routing retained; remaining research unknown ({stopped.reason}). Applicant/intake/campus/population applicability remains unknown."
    )
    candidate.notes = f"Partial discovery ({stopped.reason}); retained routing is not verified programme facts. Remaining research and applicability unknown."
    return candidate, trace
'''
assert s.count(marker)==1;s=s.replace(marker,new+marker)
old='''                    candidate, trace = await self._discover_one(entry, profile)
            except UniversityReadStopped as stopped:
                if stopped.reason == "checkpoint_busy":
                    raise
                candidate = seed
                trace = DiscoveryTrace(institution=seed.name, domain="")'''
new='''                    if RETAIN_CONFIRMED_DISCOVERY_PARTIAL:
                        publication = []
                        candidate, trace = await self._discover_one(
                            entry, profile, confirmation_publisher=lambda *value: publication.append(value)
                        )
                    else:
                        candidate, trace = await self._discover_one(entry, profile)
            except UniversityReadStopped as stopped:
                if stopped.reason == "checkpoint_busy" or (RETAIN_CONFIRMED_DISCOVERY_PARTIAL and stopped.reason != "read_cap"):
                    raise
                if RETAIN_CONFIRMED_DISCOVERY_PARTIAL and publication:
                    candidate, trace = retained_partial(publication[-1], stopped)
                else:
                    candidate = seed
                    trace = DiscoveryTrace(institution=seed.name, domain="")'''
assert s.count(old)==1;s=s.replace(old,new)
s=s.replace('''        self, entry: dict, profile: ApplicantProfileIn, *, search_queries_used: int = 0
''','''        self, entry: dict, profile: ApplicantProfileIn, *, search_queries_used: int = 0,
        confirmation_publisher: Callable[..., None] | None = None,
''',1)
# local published subset uses actual native prefix/cap; normal candidate+trace remain untouched.
marker='''        try:
            await self.sitemaps.collect(entry["homepage"], domain, trace, keep)'''
callback='''        strict_sources = {}

        def on_confirmation(url, result, page, native_prefix):
            field_key = own_field_route(result, page, degree)
            if field_key is None or not any(
                canonical_field(field_name) == field_key for field_name in fields
            ):
                return
            strict_sources[url] = (page.subject or "", result.final_url or url)
            native_cap = list(dict.fromkeys(native_prefix))[:MAX_PAGES_PER_CATEGORY]
            strict_cap = [value for value in native_cap if value in strict_sources]
            if not strict_cap or confirmation_publisher is None:
                return
            snapshot_selected = deepcopy(selected)
            snapshot_selected[PageCategory.PROGRAM_PAGE] = strict_cap
            snapshot_trace = deepcopy(trace)
            snapshot_trace.field_sources = {
                key: value for key, value in snapshot_trace.field_sources.items()
                if key in {canonical_url(value) for value in strict_cap}
            }
            if len(_distinct_fields(list(profile.context.intended_fields))) > 1:
                for value in strict_cap:
                    subject, source_url = strict_sources[value]
                    _remember_field_source(snapshot_trace, url=value, subject=subject, fields=fields,
                                           basis="classified_programme_page", source_url=source_url)
            snapshot_trace.selected = {key: list(value) for key,value in snapshot_selected.items() if value}
            provisional = deepcopy(candidate)
            # Normal successful confirmation point; never called by an exception/finally handler.
            self._apply(provisional, snapshot_selected, profile, snapshot_trace)
            provisional.notes = "Provisional strict-confirmed source routing; applicant/intake/campus/population applicability unknown."
            confirmation_publisher(provisional, snapshot_trace, trace)

'''
assert s.count(marker)==1;s=s.replace(marker,callback+marker)
# canonical_field currently ld importswith_strong_aliases in search intent? use separate normal import.
s=s.replace('from app.adapters.discovery.confirmed_routing import own_field_route\n','from app.adapters.discovery.confirmed_routing import own_field_route\nfrom app.adapters.search.ontology import canonical_field\n',1)
old='''        await self._confirm_programs(selected, ranked, trace, profile)
        await self._walk_catalogs(entry, selected, trace, profile)'''
new='''        if RETAIN_CONFIRMED_DISCOVERY_PARTIAL and confirmation_publisher is not None:
            await self._confirm_programs(selected, ranked, trace, profile, confirmation_callback=on_confirmation)
            await self._walk_catalogs(entry, selected, trace, profile, confirmation_callback=on_confirmation)
        else:
            await self._confirm_programs(selected, ranked, trace, profile)
            await self._walk_catalogs(entry, selected, trace, profile)'''
assert s.count(old)==1;s=s.replace(old,new)
# add optional kwargs only to two native methods.
old='''        trace: DiscoveryTrace,
        profile: ApplicantProfileIn,
    ) -> None:
        """Keep only programme pages'''
new='''        trace: DiscoveryTrace,
        profile: ApplicantProfileIn,
        *, confirmation_callback: Callable[..., None] | None = None,
    ) -> None:
        """Keep only programme pages'''
assert s.count(old)==1;s=s.replace(old,new)
old='''        if confirmed or selected[PageCategory.PROGRAM_PAGE]:'''
new='''            if confirmation_callback is not None:
                confirmation_callback(url, result, page, confirmed)

        if confirmed or selected[PageCategory.PROGRAM_PAGE]:'''
assert s.count(old)==1;s=s.replace(old,new)
old='''        profile: ApplicantProfileIn,
    ) -> None:
        """Read the catalogue itself'''
new='''        profile: ApplicantProfileIn,
        *, confirmation_callback: Callable[..., None] | None = None,
    ) -> None:
        """Read the catalogue itself'''
assert s.count(old)==1;s=s.replace(old,new)
old='''            page_recorder=self.page_recorder,
        )
        try:
            walks = await walker.walk'''
new='''            page_recorder=self.page_recorder,
            **({"confirmation_callback": lambda url, result, page, native: confirmation_callback(
                url, result, page, [*selected[PageCategory.PROGRAM_PAGE], *native]
            )} if confirmation_callback is not None else {}),
        )
        try:
            walks = await walker.walk'''
assert s.count(old)==1;s=s.replace(old,new)
p=B/'proposed'/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s)
# Catalogue owning wrapper and decoration.
rel=files[2];s=(B/'original'/rel).read_text()
s=s.replace('from app.adapters.discovery.live_discovery import DiscoveryTrace, LiveDiscoveryAdapter\n','from app.adapters.discovery import live_discovery as live_module\nfrom app.adapters.discovery.live_discovery import DiscoveryTrace, LiveDiscoveryAdapter, retained_partial\n',1)
old='''                        candidate, trace = await asyncio.wait_for(
                            self._enrich(uni, profile, candidate, trace), timeout=300
                        )
                except UniversityReadStopped as stopped:
                    if stopped.reason == "checkpoint_busy":
                        raise'''
new='''                        if live_module.RETAIN_CONFIRMED_DISCOVERY_PARTIAL:
                            publication = []
                            candidate, trace = await asyncio.wait_for(
                                self._enrich(uni, profile, candidate, trace,
                                             confirmation_publisher=lambda *value: publication.append(value)), timeout=300
                            )
                        else:
                            candidate, trace = await asyncio.wait_for(
                                self._enrich(uni, profile, candidate, trace), timeout=300
                            )
                except UniversityReadStopped as stopped:
                    if stopped.reason == "checkpoint_busy" or (live_module.RETAIN_CONFIRMED_DISCOVERY_PARTIAL and stopped.reason != "read_cap"):
                        raise
                    if live_module.RETAIN_CONFIRMED_DISCOVERY_PARTIAL and publication:
                        candidate, trace = retained_partial(publication[-1], stopped)'''
assert s.count(old)==1;s=s.replace(old,new)
s=s.replace('''        trace: DiscoveryTrace,
    ) -> tuple[Candidate, DiscoveryTrace]:
        trace.search_queries_sent''','''        trace: DiscoveryTrace,
        *, confirmation_publisher=None,
    ) -> tuple[Candidate, DiscoveryTrace]:
        trace.search_queries_sent''',1)
old='''        enriched, discovered = await self._discover_one(
            entry, profile, search_queries_used=trace.search_queries_sent
        )'''
new='''        if live_module.RETAIN_CONFIRMED_DISCOVERY_PARTIAL and confirmation_publisher is not None:
            def publish(provisional, snapshot_trace, current_trace):
                provisional.catalogue_id = uni.id
                provisional.discovery_source = f"local-catalogue:{uni.id}; {provisional.discovery_source}"
                snapshot_trace.search_failures[:0] = trace.search_failures
                snapshot_trace.search_limitations[:0] = trace.search_limitations
                confirmation_publisher(provisional, snapshot_trace, current_trace)
            enriched, discovered = await self._discover_one(
                entry, profile, search_queries_used=trace.search_queries_sent,
                confirmation_publisher=publish,
            )
        else:
            enriched, discovered = await self._discover_one(
                entry, profile, search_queries_used=trace.search_queries_sent
            )'''
assert s.count(old)==1;s=s.replace(old,new)
p=B/'proposed'/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s)
patch=[]
for rel in [*files,'app/adapters/discovery/confirmed_routing.py']:
 old=(B/'original'/rel).read_text() if (B/'original'/rel).exists() else ''
 new=(B/'proposed'/rel).read_text();compile(new,rel,'exec')
 patch.append(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/backend/'+rel if old else '/dev/null',tofile='b/backend/'+rel)))
(B/'retained-discovery.patch').write_text(''.join(patch))
print('prepared4files')
