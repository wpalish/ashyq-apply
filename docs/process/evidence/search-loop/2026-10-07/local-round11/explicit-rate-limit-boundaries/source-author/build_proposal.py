from pathlib import Path
import difflib
import hashlib
import json
B=Path(__file__).resolve().parent
P=json.loads((B/'PLAN.json').read_text())
manifest={}
for rel in P['source_files']:
    old=(B/'original'/rel).read_text()
    assert hashlib.sha256(old.encode()).hexdigest()==P['source_sha256'][rel]
    new=old
    if rel.endswith('search/__init__.py'):
        new=new.replace('    SearchError,\n','    SearchError,\n    SearchFailureReason,\n',1)
        new=new.replace('#: How long a provider that answered HTTP 429 is left alone, in seconds. The', '#: How long a provider that reported a rate limit is left alone, in seconds. The')
        new=new.replace('_THROTTLED_UNTIL: dict[str, float] = {}\n', '''_THROTTLED_UNTIL: dict[str, float] = {}
#: Deadline-stamped typed provenance. The existing float map remains compatible
#: with deliberately injected legacy HTTP-429 state; a stale record is ignored.
_THROTTLED_ORIGIN: dict[str, tuple[float, int | None, SearchFailureReason | None]] = {}


def _is_explicit_rate_limit(exc: SearchUnavailable) -> bool:
    """Only an HTTP 429 or the fixed typed reason proves a rate limit."""
    return exc.http_status == 429 or exc.reason is SearchFailureReason.RATE_LIMITED
''')
        new=new.replace('"""Forget every recorded 429. Tests and a deliberate operator retry only."""\n    _THROTTLED_UNTIL.clear()', '"""Forget recorded rate limits. Tests and a deliberate operator retry only."""\n    _THROTTLED_UNTIL.clear()\n    _THROTTLED_ORIGIN.clear()')
        new=new.replace('''    """A provider that stops asking once its endpoint has said HTTP 429.

    No retry and no backoff loop: after one refusal every caller in this
    process gets the same refusal locally, without a request, until the
    cool-down passes. The caller sees an ordinary :class:`SearchUnavailable`
    with ``http_status=429``, so every existing quota-stop path still applies.
    """''','''    """Stop later callers after an explicit rate-limit failure escapes.

    The inner provider keeps its existing retry behavior. Once it raises,
    later callers receive a local :class:`SearchUnavailable` until cooldown,
    preserving the original HTTP status and fixed typed reason.
    """''')
        new=new.replace('''        if time.monotonic() < _THROTTLED_UNTIL.get(self.name, 0.0):
            raise SearchUnavailable(
                f"{self.name} refused an earlier request with HTTP 429; this request was not sent",
                http_status=429,
            )''','''        until = _THROTTLED_UNTIL.get(self.name, 0.0)
        if time.monotonic() < until:
            origin = _THROTTLED_ORIGIN.get(self.name)
            # A float-only entry is the pre-existing HTTP-429 state contract.
            # It does not establish an HTTP status for a recorded typed failure.
            status, reason = (origin[1], origin[2]) if origin and origin[0] == until else (429, None)
            message = (
                f"{self.name} refused an earlier request with HTTP 429; this request was not sent"
                if status == 429
                else f"{self.name} reported an earlier rate limit; this request was not sent"
            )
            raise SearchUnavailable(message, http_status=status, reason=reason)''')
        new=new.replace('''            if exc.http_status == 429:
                _THROTTLED_UNTIL[self.name] = time.monotonic() + THROTTLE_COOLDOWN_SECONDS''','''            if _is_explicit_rate_limit(exc):
                until = time.monotonic() + THROTTLE_COOLDOWN_SECONDS
                _THROTTLED_UNTIL[self.name] = until
                reason = exc.reason if isinstance(exc.reason, SearchFailureReason) else None
                _THROTTLED_ORIGIN[self.name] = (until, exc.http_status, reason)''')
    elif rel.endswith('search/retrieval.py'):
        new=new.replace('from app.adapters.search.base import (','from app.adapters.search import _is_explicit_rate_limit\nfrom app.adapters.search.base import (',1)
        new=new.replace('A provider failure on one query does not abort the run: the other queries','A non-rate-limit provider failure does not abort the run: the other queries')
        new=new.replace('#: A 429 stops the loop; unattempted planned families remain uncharged.', '#: An explicit rate limit stops the loop; unattempted families stay uncharged.')
        new=new.replace('if exc.http_status == 429:', 'if _is_explicit_rate_limit(exc):',1)
    else:
        new=new.replace('f"Search at {entry[\'name\']} stopped: {report.provider} answered "\n                "HTTP 429, so', 'f"Search at {entry[\'name\']} stopped: {report.provider} reported "\n                "a rate limit, so',1)
        new=new.replace('# Counted before a throttle stop: the queries sent before the 429', '# Counted before a throttle stop: queries attempted before the rate limit')
        new=new.replace('f"Search at {entry[\'name\']} stopped: {provider.name} answered "\n                    "HTTP 429, so', 'f"Search at {entry[\'name\']} stopped: {provider.name} reported "\n                    "a rate limit, so',1)
    assert old!=new
    out=B/'proposed'/rel
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(new)
    manifest[rel]={'original_sha256':hashlib.sha256(old.encode()).hexdigest(),'proposed_sha256':hashlib.sha256(new.encode()).hexdigest()}
patch=''.join(''.join(difflib.unified_diff((B/'original'/r).read_text().splitlines(keepends=True),(B/'proposed'/r).read_text().splitlines(keepends=True),fromfile='a/backend/'+r,tofile='b/backend/'+r)) for r in P['source_files'])
(B/'explicit-rate-limit.patch').write_text(patch)
(B/'source-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
