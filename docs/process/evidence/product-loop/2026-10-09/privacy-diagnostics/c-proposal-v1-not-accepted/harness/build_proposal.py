"""Apply explicit finite edits to the owned ON copy only; preserve OFF bytes."""
from pathlib import Path
import difflib
import json
import hashlib

packet = Path(__file__).resolve().parents[1]
base = packet / "runtime/on/backend/app"
changed = []

def edit(rel, pairs):
    f = base / rel
    before = f.read_text()
    after = before
    for old, new in pairs:
        assert old in after, (rel, old)
        after = after.replace(old, new)
    assert after != before
    f.write_text(after)
    target = packet / "proposed/backend/app" / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(after)
    changed.append(("backend/app/" + rel, before, after))

edit("adapters/fetching.py", [
    ('def assert_no_pii(url: str, extra: str = "") -> None:', '''def privacy_safe_url(url: str) -> str:
    """Diagnostic identity only; never a retry target or proof of a read.

    Ordinary public URLs remain exact. For an already rejected URL retain
    only a structurally safe origin, never userinfo/path/query/fragment. This
    does not extend PII detection or verify the origin through DNS.
    """
    if find_pii(url) is None:
        return url
    try:
        parsed = urlparse(url)
        host = parsed.hostname or ""
        if parsed.scheme not in ("http", "https") or not host:
            return "[privacy-refused URL]"
        host = f"[{host}]" if ":" in host else host
        port = f":{parsed.port}" if parsed.port is not None else ""
        origin = f"{parsed.scheme}://{host}{port}/"
        return origin if find_pii(origin) is None else "[privacy-refused URL]"
    except ValueError:
        return "[privacy-refused URL]"


def fetch_diagnostic_url(requested_url: str, result: FetchResult) -> str:
    """Use safe identity for a refused input; keep an ordinary source exact."""
    return (
        privacy_safe_url(requested_url)
        if result.outcome == FetchOutcome.REFUSED_PRIVACY
        else requested_url
    )


def fetch_retry_url(requested_url: str, result: FetchResult) -> str | None:
    """A privacy refusal must not turn an origin placeholder into a retry."""
    return None if result.outcome == FetchOutcome.REFUSED_PRIVACY else requested_url


def assert_no_pii(url: str, extra: str = "") -> None:'''),
    ('log.warning("refusing %s: looks like %s", current[:120], leak)',
     'log.warning("refusing %s: looks like %s", privacy_safe_url(url), leak)'),
    ('error=f"Refused: the URL contains what looks like a {leak}. It was not fetched.",\n                    final_url=current,',
     'error=f"Refused: the URL contains what looks like a {leak}. It was not fetched.",\n                    final_url=privacy_safe_url(url),'),
    ('log.warning("refusing %s: looks like %s", url[:120], leak)',
     'log.warning("refusing %s: looks like %s", privacy_safe_url(url), leak)'),
    ('url=url,\n                outcome=FetchOutcome.REFUSED_PRIVACY,',
     'url=privacy_safe_url(url),\n                outcome=FetchOutcome.REFUSED_PRIVACY,'),
])

edit("adapters/search/intent.py", [
    ('    """Raised when a value carries something a provider must never be told."""', '''    """Typed safe refusal: the rejected value is never retained as diagnostics."""

    def __init__(self, *, field: str, reason: str) -> None:
        self.field = field if field in {
            "institution", "domain", "field", "population_marker"
        } else "discovery field"
        descriptions = {
            "email": "contains an email address; contact details are never part of a discovery query",
            "currency": "contains a currency amount; budget and family contribution never leave this service",
            "grade": "looks like a grade; a search engine is never told how well the applicant did",
            "long-number": "contains a long number (score or phone); use intake_year for a year",
            "population-not-allowed": "is not one of the allowed public population markers",
        }
        self.reason = reason if reason in descriptions else "privacy-refused"
        super().__init__(f"{self.field}: {descriptions.get(self.reason, 'discovery value refused for privacy')}.")'''),
    ('''        raise QueryPrivacyError(
            f"{field}={value!r} contains an email address. Contact details are never "
            "part of a discovery query."
        )''', '        raise QueryPrivacyError(field=field, reason="email")'),
    ('''        raise QueryPrivacyError(
            f"{field}={value!r} contains a currency amount. Budget and family "
            "contribution never leave this service."
        )''', '        raise QueryPrivacyError(field=field, reason="currency")'),
    ('''        raise QueryPrivacyError(
            f"{field}={value!r} looks like a grade. A search engine is asked where a "
            "programme is, never how well the applicant did."
        )''', '        raise QueryPrivacyError(field=field, reason="grade")'),
    ('''        raise QueryPrivacyError(
            f"{field}={value!r} contains a long number, which is how a test score or a "
            "phone number gets into a query. Use intake_year for a year."
        )''', '        raise QueryPrivacyError(field=field, reason="long-number")'),
    ('''            raise QueryPrivacyError(
                f"population_marker={self.population_marker!r} is not one of "
                f"{sorted(ALLOWED_POPULATION_MARKERS)}. A narrower audience describes this "
                "applicant rather than a published policy."
            )''', '''            raise QueryPrivacyError(field="population_marker", reason="population-not-allowed")'''),
])

for rel, old, new in [
    ("pipeline/runner.py", '            log.exception("run %s failed", self.run.id)', '''            if isinstance(exc, QueryPrivacyError):
                # Exception context can carry the rejected value even when
                # str(exc) is safe. Keep the typed reason without a traceback.
                log.error("run %s failed: %s: %s", self.run.id, type(exc).__name__, exc)
            else:
                log.exception("run %s failed", self.run.id)'''),
    ("jobs/worker.py", '            log.exception("job %s failed", job_id[:8])', '''            if isinstance(exc, QueryPrivacyError):
                # Do not serialize a chained rejected input through exc_info.
                log.error("job %s failed: %s: %s", job_id[:8], type(exc).__name__, exc)
            else:
                log.exception("job %s failed", job_id[:8])'''),
]:
    edit(rel, [("from app.config import", "from app.adapters.search.intent import QueryPrivacyError\nfrom app.config import"), (old, new)])

edit("adapters/cost/web_costs.py", [
    ('from app.adapters.fetching import Fetcher', 'from app.adapters.fetching import Fetcher, fetch_diagnostic_url, fetch_retry_url'),
    ('            out.errors.append(f"{candidate.costs_url}: {res.outcome.value} — {res.error}")',
     '            failed_url = fetch_diagnostic_url(candidate.costs_url, res)\n            out.errors.append(f"{failed_url}: {res.outcome.value} — {res.error}")'),
    ('                    url=candidate.costs_url,\n                    category="fetch-failed",', '                    url=failed_url,\n                    category="fetch-failed",'),
    ('            out.retry_urls.append(candidate.costs_url)', '            retry_url = fetch_retry_url(candidate.costs_url, res)\n            if retry_url is not None:\n                out.retry_urls.append(retry_url)'),
])

# Other live consumers share the same result-to-diagnostic contract. Their
# successful extraction, classifier and ordinary retry behavior stay intact.
rel = "adapters/requirements/web_requirements.py"
f = base / rel
imports = next(line for line in f.read_text().splitlines() if line.startswith("from app.adapters.fetching import "))
assert "(" not in imports
edit(rel, [(imports, imports + ", fetch_diagnostic_url"),
    ('                out.errors.append(f"{target.url}: {res.outcome.value} — {res.error}")',
     '                failed_url = fetch_diagnostic_url(target.url, res)\n                out.errors.append(f"{failed_url}: {res.outcome.value} — {res.error}")'),
    ('                        url=target.url,\n                        category="fetch-failed",', '                        url=failed_url,\n                        category="fetch-failed",')])

edit("adapters/documents/web_documents.py", [
    ('from app.adapters.fetching import Fetcher', 'from app.adapters.fetching import Fetcher, fetch_diagnostic_url, fetch_retry_url'),
    ('            out.errors.append(f"{url}: {res.outcome.value} — {res.error}")\n            out.retry_urls.append(url)\n            out.page_outcomes.append(PageOutcome(url, "fetch-failed"))',
     '''            failed_url = fetch_diagnostic_url(url, res)
            out.errors.append(f"{failed_url}: {res.outcome.value} — {res.error}")
            retry_url = fetch_retry_url(url, res)
            if retry_url is not None:
                out.retry_urls.append(retry_url)
            out.page_outcomes.append(
                PageOutcome(failed_url, "fetch-failed", detail=f"{res.outcome.value} — {res.error}")
            )'''),
])

edit("adapters/government/web_government.py", [
    ('from app.adapters.fetching import Fetcher', 'from app.adapters.fetching import Fetcher, fetch_diagnostic_url'),
    ('            out.pages_failed += 1\n            out.errors.append(', '            out.pages_failed += 1\n            failed_url = fetch_diagnostic_url(url, res)\n            out.errors.append('),
    ('f"{url}: {res.outcome.value} — post-study work rules unverified for {country}."', 'f"{failed_url}: {res.outcome.value} — post-study work rules unverified for {country}."'),
    ('url=url, category="fetch-failed",', 'url=failed_url, category="fetch-failed",'),
])

edit("adapters/scholarship/web_scholarships.py", [
    ('from app.adapters.fetching import Fetcher, FetchResult', 'from app.adapters.fetching import Fetcher, FetchResult, fetch_diagnostic_url, fetch_retry_url'),
    ('                out.errors.append(f"{url}: {page.outcome.value} — {page.error}")\n                out.retry_urls.append(url)',
     '''                failed_url = fetch_diagnostic_url(url, page)
                out.errors.append(f"{failed_url}: {page.outcome.value} — {page.error}")
                retry_url = fetch_retry_url(url, page)
                if retry_url is not None:
                    out.retry_urls.append(retry_url)'''),
    ('                        url=url,\n                        category="fetch-failed",', '                        url=failed_url,\n                        category="fetch-failed",'),
])

rel = "adapters/discovery/live_discovery.py"
imports = next(line for line in (base / rel).read_text().splitlines() if line.startswith("from app.adapters.fetching import "))
edit(rel, [(imports, imports + ", fetch_diagnostic_url"),
    ('f"{url}: {result.outcome.value} — {result.error}"[:300]', 'f"{fetch_diagnostic_url(url, result)}: {result.outcome.value} — {result.error}"[:300]'),
    ('trace.reject(url, f"could not be read ({result.outcome.value})")', 'trace.reject(fetch_diagnostic_url(url, result), f"could not be read ({result.outcome.value})")'),
    ('                pending.append(found.url)\n                trace.reject(found.url, f"search lead unresolved ({result.outcome.value})")',
     '''                if result.outcome != FetchOutcome.REFUSED_PRIVACY:
                    pending.append(found.url)
                trace.reject(fetch_diagnostic_url(found.url, result), f"search lead unresolved ({result.outcome.value})")'''),
    ('f"navigation fallback: {start} unreachable ({result.outcome.value})"', 'f"navigation fallback: {fetch_diagnostic_url(start, result)} unreachable ({result.outcome.value})"'),
    ('# QueryPrivacyError embeds the raw value. Never log it here.', '# Rejected fields are not public source identity. Do not echo them here.'),
])

rel = "adapters/discovery/catalog_walker.py"
imports = next(line for line in (base / rel).read_text().splitlines() if line.startswith("from app.adapters.fetching import "))
edit(rel, [(imports, imports + ", fetch_diagnostic_url, privacy_safe_url"),
    ("from app.pipeline.control import", "from app.domain.enums import FetchOutcome\nfrom app.pipeline.control import"),
    ("from dataclasses import dataclass, field", "from dataclasses import dataclass, field, replace"),
    ('            walk.outcomes.append((catalogue_url, catalogue_outcome))', '''            diagnostic_url = (
                privacy_safe_url(catalogue_url)
                if catalogue_outcome == FetchOutcome.REFUSED_PRIVACY.value
                else catalogue_url
            )
            walk.outcomes.append((diagnostic_url, catalogue_outcome))
            if catalogue_outcome == FetchOutcome.REFUSED_PRIVACY.value:
                walk.catalogue_url = diagnostic_url
                return walk'''),
    ('            walk.outcomes.append((link.url, result.outcome.value))', '''            diagnostic_url = fetch_diagnostic_url(link.url, result)
            if result.outcome == FetchOutcome.REFUSED_PRIVACY:
                # Candidate trace is a diagnostic record, not another source
                # read. Keep the evaluated lead count without its rejected URL.
                walk.candidates = [
                    replace(candidate, url=diagnostic_url) if candidate.url == link.url else candidate
                    for candidate in walk.candidates
                ]
            walk.outcomes.append((diagnostic_url, result.outcome.value))'''),
])

diff = "".join("".join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
    fromfile="a/"+rel, tofile="b/"+rel)) for rel,before,after in changed)
(packet / "proposal.diff").write_text(diff)
(packet / "proposal-source-manifest.json").write_text(json.dumps({rel: {
    "before_sha256": hashlib.sha256(before.encode()).hexdigest(),
    "proposed_sha256": hashlib.sha256(after.encode()).hexdigest(),
    "bytes": len(after.encode())} for rel,before,after in changed}, indent=2)+"\n")
print("proposed source files", len(changed))
