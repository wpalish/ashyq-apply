import asyncio
import json
import sys
from contextlib import contextmanager
from dataclasses import asdict
from types import SimpleNamespace
from unittest.mock import patch

import control_support as c
from app.adapters.discovery import catalog_walker as aw
from app.pipeline.control import UniversityReadStopped


async def main():
    rows = []
    for kind, module in [("live", c.live), ("catalogue", c.catalogue)]:
        c.live.RETAIN_CONFIRMED_DISCOVERY_PARTIAL = True
        entry1 = c.entry()
        entry2 = {"name": "Second University", "country": "Example", "city": "Other",
            "homepage": "https://second.edu/", "seeds": {}}
        pages = c.catalog([(c.PREFIX + "a", "BSc Computer Science", c.programme())])
        f = c.MockFetcher(pages)
        capped = UniversityReadStopped("read_cap")
        entry_starts = []
        @contextmanager
        def scope(candidate):
            entry_starts.append({"name": candidate.name, "catalogue_id": candidate.catalogue_id,
                "gets": list(f.calls)})
            if candidate.name == "Second University":
                raise capped
            yield
        if kind == "live":
            adapter = module.LiveDiscoveryAdapter(f, research_scope=scope)
            adapter.registry = lambda: [entry1, entry2]
        else:
            adapter = module.CatalogueDiscoveryAdapter(f, session=None, university_ids=["first", "second"],
                live_limit=2, research_scope=scope)
        adapter.sitemaps.collect = c.no_sitemaps
        adapter._navigation_fallback = c.no_navigation
        adapter._add_search_results = c.no_search
        unis = [SimpleNamespace(id=key, name=e["name"], country=e["country"], city=e["city"],
            domain=e["homepage"].split('/')[2], registry_entry=e) for key,e in [("first", entry1),("second", entry2)]]
        with patch.object(aw, "CatalogWalker", c.walker.CatalogWalker), patch.object(module, "retrieve", lambda *a,**kw: unis, create=True):
            got = await adapter.discover(c.profile(),2)
        values = {"candidates": [asdict(x) for x in got], "traces": [asdict(x) for x in adapter.traces],
            "scope_starts": entry_starts, "gets": f.calls}
        okay = len(got)==2 and got[1].name=="Second University" and not got[1].programs and adapter.traces[1].institution=="Second University" and len(f.calls)==2
        if kind=="catalogue":
            okay = okay and got[1].catalogue_id=="second"
        rows.append({"case":kind+"_previous_success_then_capped_next", "status":"PASS" if okay else "RED",
            "expected":"Second university cannot inherit first name/id/domain/URL/trace; zero new get on entry refusal", **values})
    p=c.B/(sys.argv[1] if len(sys.argv)>1 else "scope-ownership.attempt1.json")
    assert not p.exists()
    p.write_text(json.dumps(rows,indent=2,default=str)+'\n')
    print(json.dumps({"PASS":sum(x['status']=='PASS' for x in rows),"RED":sum(x['status']=='RED' for x in rows)}))


if __name__=="__main__":
    asyncio.run(main())
