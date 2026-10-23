from pathlib import Path
import hashlib,difflib,json
B=Path(__file__).resolve().parent;REPO=B.parents[1]/'ashyq-apply/backend'
rel='app/adapters/discovery/catalog_walker.py';s=(REPO/rel).read_text()
plan=json.loads((B/'PLAN.json').read_text());assert hashlib.sha256(s.encode()).hexdigest()==plan['current_source_sha256'][rel]
(B/'catalog_walker.original.py').write_text(s)
s=s.replace('import re\n','import re\nimport unicodedata\n',1)
s=s.replace('from app.adapters.fetching import Fetcher, FetchResult, same_source_site\n','from app.adapters.fetching import Fetcher, FetchResult, same_source_site\nfrom app.adapters.search.ontology import canonical_field\n',1)
helpers='''
# External ordering experiment. No stop/cut or new confirmation permission.
WALKER_ORDER_EXACT_FIELD_LEADS = False


def _requested_order_routes(fields: list[str]) -> frozenset[str] | None:
    if not fields or any(not value.strip() for value in fields):
        return None
    keys: set[str] = set()
    for value in fields:
        key = canonical_field(value)
        if key is None:
            return None
        keys.add(key)
    return frozenset(keys)


def _exact_label_route(label: str) -> str | None:
    primary = re.split(r"\\s+[-–—]\\s+|\\|", label, maxsplit=1)[0].strip()
    text = unicodedata.normalize("NFKC", primary).casefold().replace("&", " and ")
    words = re.findall(r"[^\\W_]+", text)
    while words and words[-1] in {"major", "honours", "honors", "hons", "degree", "programme", "program"}:
        words.pop()
    degree_prefix = {
        "bachelor", "bachelors", "undergraduate", "bsc", "bs", "beng", "ba",
        "master", "masters", "postgraduate", "msc", "ms", "meng", "ma",
        "phd", "doctoral", "doctorate", "foundation",
    }
    wrappers = degree_prefix | {"of", "in", "science", "engineering", "arts", "degree", "programme", "program"}
    for start in range(len(words)):
        if start and (words[0] not in degree_prefix or not set(words[:start]) <= wrappers):
            break
        term = " ".join(words[start:])
        if term in {"computing", "informatics"}:
            continue  # broad one-word aliases do not earn new priority
        key = canonical_field(term)
        if key is not None:
            return key
    return None

'''
s=s.replace('\n\n@dataclass(frozen=True)\nclass WalkerLink:',helpers+'\n@dataclass(frozen=True)\nclass WalkerLink:',1)
old='''        for link in budget:
            await self._read_lead(link, walk)
        return walk
'''
new='''        ordered = False
        original_order = {link.url: i for i, link in enumerate(budget)}
        required = _requested_order_routes(self.fields) if WALKER_ORDER_EXACT_FIELD_LEADS else None
        if required is not None:
            hints = {link.url: _exact_label_route(link.label) for link in budget}
            if required <= {hint for hint in hints.values() if hint is not None}:
                # Labels guide read priority only, after all original admission cuts.
                budget = sorted(budget, key=lambda link: hints[link.url] not in required)
                ordered = True
        for link in budget:
            await self._read_lead(link, walk)
        if ordered:
            # Preserve legacy caller caps/selection; the trace keeps actual read chronology.
            walk.confirmed.sort(key=lambda url: original_order[url])
            walk.confirmed_subjects = {url: walk.confirmed_subjects[url] for url in walk.confirmed}
        return walk
'''
assert s.count(old)==1;s=s.replace(old,new)
(B/'catalog_walker.proposed.py').write_text(s)
(B/'stable-read-order.patch').write_text(''.join(difflib.unified_diff((B/'catalog_walker.original.py').read_text().splitlines(True),s.splitlines(True),fromfile='a/backend/'+rel,tofile='b/backend/'+rel)))
print(hashlib.sha256(s.encode()).hexdigest())
