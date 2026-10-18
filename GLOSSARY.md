# ASHYQ Apply — research pipeline

The part of the product that finds a university's official pages for one applicant request and reads
published requirements from them. This glossary holds the terms the discovery and evaluation code already
fixes; terms still being decided (see `docs/process/wayfinder/programme-discovery/`) are not in it.

## Language

### Discovery

**Programme page**:
The official page that names one degree programme at the requested level in the requested field, read and
accepted by the classifier. A page that was not read is never a programme page.
_Avoid_: course page, degree page, program URL

**Lead**:
A URL discovery holds as a possible programme page before it has been read. A lead that cannot be read is
reported as unresolved, never as found.
_Avoid_: candidate URL, hit

**Confirmation**:
The act of reading a lead and accepting it as the programme page by the shared predicate (page type, degree
level, subject, campus). The same predicate decides for every stage.
_Avoid_: validation, verification (reserved for claims)

**Programme twin**:
A page the programme page itself declares as its alternate in another language. The twin is the same
programme, not a second one.
_Avoid_: translation, mirror

**Opaque URL**:
A programme URL whose path says nothing about level or subject (an identifier, a query parameter, a numeric
node), so only link text and the page's own identity can lead to it.

**Discovery stage**:
One ordered step of discovery for one institution — seeds, sitemaps, navigation, confirm, walker, search,
identity recovery — each charged to the institution's single discovery budget.

**Stage budget**:
The discovery clock and read allowance for one institution, shared by all its stages and reported per stage;
spent means the evidence stages begin with what was confirmed.

**Query family**:
One of the fixed shapes a discovery query takes (field and degree, natural language, programmes, courses,
undergraduate, admissions). A family carries only the public request words, never an applicant attribute.

**Identity recovery**:
Reading the provider's results through the Fetcher and classifying each, so that search contributes pages it
has read rather than titles it was shown.

**Site identity**:
Proof that a probed host is the university's official site, established before any discovery on an
institution outside the registry.

### Institutions and evaluation

**Registry institution**:
One of the nineteen universities with human-verified seed pages. A seed says where to look; it is not evidence.

**Unseen university**:
A university outside the registry, reached through its catalogue row with no seeds. The product's general
case.

**Development split**:
The universities on which rules may be tuned: the cohort, dev2, dev3 (and dev4 when signed). Every rule is
measured on all of them.

**Heldout split**:
The nine universities whose gold, captures and per-case results are never opened while designing or tuning a
rule; they are run only to check that a rule set generalises.

**Readable site**:
An official site whose pages the measurement network can fetch under robots.txt. A site that refuses is
reported as unavailable and counted outside the programme-page denominator.
_Avoid_: reachable (an HTTP fact, not a policy one)
