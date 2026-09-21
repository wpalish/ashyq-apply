# PHASE 1 — DISCOVERY ENGINE v2

## Goal

Increase exact programme-page recall without weakening precision or privacy.

Current design already has:
- institution registry;
- manual seeds;
- sitemap-first discovery;
- navigation fallback;
- page classifier;
- catalogue walker;
- browser tier;
- passive JSON/XHR catalogue capture.

Preserve those useful parts. Add missing retrieval layers.

# Discovery principle

Use multiple candidate generators:

```text
CACHE / KNOWLEDGE GRAPH
REGISTRY
SITEMAP
WEB SEARCH
UNIVERSITY INTERNAL SEARCH
CATALOGUE WALKER
KNOWN UNIVERSITY APIs
```

Then fuse and rank candidates.

No one source should be treated as universally complete.

# 1. Search provider abstraction

Define a provider-neutral interface similar to:

```python
class SearchProvider(Protocol):
    async def search(
        self,
        *,
        query: str,
        domains: Sequence[str] = (),
        max_results: int = 10,
    ) -> SearchResponse: ...
```

Response must include:
- URL;
- title;
- snippet/excerpt if provider supplies it;
- provider name;
- rank;
- retrieval timestamp.

Adapters may later support:
- Brave;
- Exa;
- Parallel;
- Tavily;
- other owner-approved provider.

Do not leak provider-specific objects into domain logic.

Implement fake provider for tests.

# 2. Privacy-safe query generation

Search query generation must accept **discovery intent**, not the full applicant profile.

Allowed ordinary discovery dimensions:
- institution;
- degree;
- field;
- intake/year only when useful;
- generic `international` or `Kazakhstan` only when searching a country-specific public requirement page.

Do not insert:
- applicant name;
- exact scores;
- exact GPA;
- budget;
- family contribution;
- email/phone;
- transcript content.

Log a redacted query audit record.

# 3. Field and degree ontology

Create canonical concepts and aliases.

Example:

```yaml
computer_science:
  strong_aliases:
    - computer science
    - computing science
    - computing
    - informatics
  related_not_equivalent:
    - software engineering
    - data science
    - artificial intelligence
    - computer engineering
```

Important: related programmes are **retrieval candidates**, not automatically equivalent matches.

Degree:

```yaml
bachelor:
  aliases:
    - bachelor
    - bachelor's
    - bsc
    - bs
    - beng
    - undergraduate
```

Ontology must support multilingual aliases over time.

Keep version information.

# 4. Candidate generation

Example search families:

```text
site:<domain> "<field alias>" "<degree alias>"
site:<domain> programmes "<field>"
site:<domain> courses "<field>"
site:<domain> undergraduate "<field>"
site:<domain> admissions <degree>
site:<domain> scholarships international undergraduate
site:<domain> Kazakhstan admission requirements
```

Do not explode all aliases into unlimited queries.

Use bounded query budgets and telemetry.

# 5. Cheap deterministic prefilter

Before embeddings/models:
- canonicalize URL;
- reject unsupported scheme;
- apply same-institution policy where appropriate;
- reject obvious news/events/jobs/media;
- detect PDF;
- detect degree mismatch in URL;
- use existing path signals;
- deduplicate.

This stage should be very cheap.

# 6. Retrieval stack

Recommended comparison:

```text
deterministic score
BM25
multilingual embeddings
cross-encoder reranker
experimental Jev
cheap LLM
```

Do not automatically deploy all of them.

Use Phase-0 benchmark.

For very large URL sets:

```text
100,000 URLs
→ deterministic filter
→ lexical/embedding retrieval
→ ~100 candidates
→ expensive reranker/model
→ fetch top K
```

Never send tens of thousands of options directly to Jev.

# 7. University internal search

Create a detection layer for public site search/catalogue mechanisms.

Potential types:
- plain HTML form;
- JSON endpoint;
- WordPress REST;
- Drupal JSON/views;
- Algolia;
- Elastic/OpenSearch;
- Solr;
- GraphQL;
- custom catalogue JSON.

Rules:
- use only publicly accessible endpoints used by the site;
- no bypass of authentication/access controls;
- preserve Fetcher network/PII/SSRF rules;
- record endpoint provenance;
- cap response/body sizes;
- bound pagination.

Prefer passive discovery from browser network logs before active endpoint inference.

# 8. Subdomains

The university entity must support known related hosts:

```text
canonical domain
admissions host
faculty hosts
programme catalogue host
international host
application host
```

Do not blindly treat every sibling subdomain as trusted if the registrable-domain rules are ambiguous.

Use official links/search evidence to attach additional hosts.

# 9. PDFs

PDF can be:
- a direct programme handbook;
- country credential table;
- tuition schedule;
- scholarship regulation.

Discovery should classify PDF candidates separately.

Text parser first.
OCR only when:
- text layer is absent;
- legal/privacy constraints allow it;
- OCR provider policy is approved or local OCR is available.

A PDF being official does not imply every rule applies to the target programme.

# 10. Programme identity verification

Do not collapse identity into one fuzzy score.

Verify separately:

```text
page establishes a programme exists?
correct university?
correct degree level?
field semantically matches?
active/current programme?
requested intake supported?
```

Recommended outcome per dimension:

```text
YES
NO
UNKNOWN
```

A candidate becomes exact programme match only when required identity dimensions meet the rule defined by domain code.

# 11. Discovery provenance

For every candidate keep:

```text
candidate_url
discovered_by:
  registry_seed | sitemap | web_search | site_search | catalogue | browser_payload
provider
query_or_parent_url
rank
retrieved_at
```

This is discovery provenance, not claim evidence.

# 12. Success criteria

A discovery change is good only if benchmark improves.

Primary:
- programme recall;
- programme precision;
- recall@K.

Secondary:
- fetch count;
- browser rate;
- cost;
- latency.

Do not accept:
- higher recall caused by exploding fetch budget without cost limits;
- higher recall with material false positives;
- hard-coded university-specific fixes that do not generalize unless explicitly stored as verified registry metadata.
