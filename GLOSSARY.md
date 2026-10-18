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

**Section link**:
A link on the homepage or a section page whose label, in a language of the institution's country, names the
study or programme-catalogue section ("Studier", "Carreras de pregrado"). It is a lead by its label, whatever
its URL says.
_Avoid_: menu link, nav item

**Catalogue host**:
A host of the institution's own domain that publishes its programme catalogue apart from the main site (an
admissions or study-offer subdomain), reached from a page discovery has read. A host on another domain is not
a catalogue host.
_Avoid_: microsite, subdomain (says nothing about the catalogue)

**Discovery stage**:
One ordered step of discovery for one institution — seeds, sitemaps, navigation, confirm, walker, search,
identity recovery — each charged to the institution's single discovery budget.

**Stage budget**:
The discovery clock and read allowance for one institution, shared by all its stages and reported per stage;
spent means the evidence stages begin with what was confirmed.

**Query family**:
One of the fixed shapes a discovery query takes (field and degree, natural language, programmes, courses,
undergraduate, admissions). A family carries only the public request words, never an applicant attribute.

**Query pass**:
One of the two rounds in which an institution's query families are sent: the first pass of three families, then
the reserve of three only when nothing has been confirmed. A pass that is never reached sends nothing.
_Avoid_: batch, round

**Identity recovery**:
Reading the provider's results through the Fetcher and classifying each, so that search contributes pages it
has read rather than titles it was shown.

**Site identity**:
Proof that a probed host is the university's official site, established before any discovery on an
institution outside the registry.

### Programme identity

**Programme identity**:
Whether a page is the requested programme: the institution's degree at the requested level in the requested
field. The page's own text decides it, never its address.
_Avoid_: URL match, page match

**Programme title**:
The name a programme page publishes for its programme, as written: degree words, subject, and any subtitle,
place or form word around them.
_Avoid_: page title (the browser tab), course name

**Subject head**:
The part of a programme title that names the subject: what stands before a subtitle introduced by a colon or
dash, without degree words or filler words. Only the subject head says whether the title names the field.
_Avoid_: main subject, keyword

**Filler word**:
A word in a programme title that names no subject: a place in the institution's country, an honours or form
word ("Hons", "programme", "Studieprogramma"). A foreign campus is never filler.
_Avoid_: stop word

**Related field**:
A subject beside the requested field that is not it: business, engineering, economics, mathematics, or a field
the ontology marks as related but not equivalent. In a subject head it makes the programme related, not the
requested one.
_Avoid_: adjacent field, similar subject

**Canonical variant**:
The programme page under another spelling of its address: with or without an intake-year segment, a trailing
slash, `index.html` or a `.htm` / `.html` extension, or with a language parameter that the page's own
declared language confirms. A
variant is the same page; any other query parameter makes another page.
_Avoid_: duplicate URL, alias (reserved for the ontology's names)

**Related programme**:
A programme of the same institution that answers the applicant's field without being the requested
programme: a sibling specialisation, a major within the degree, the field's bachelor in another faculty, or a
title whose subject head joins the field to a related field. It is reported as related — neither found nor
wrong.
_Avoid_: near miss, partial hit, sibling (one kind of it)

**Wrong page**:
A page reported as the programme page that is not the programme page, its twin, a canonical variant of
either, or a related programme. Wrong pages are what programme-page precision counts against.
_Avoid_: false positive (reserved for claims), mismatch

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

**Gold**:
The expert-labelled, owner-signed value a case is scored against — a programme URL (with its declared twin) or a
core answer with its quote. A draft label is not gold until it is signed.
_Avoid_: ground truth, expected value

**Paired run**:
The loop's measurement of one rule: the same cases run with the rule off and on, two repetitions each, read for
stable gains and stable losses only. A rule is judged by its paired run, never by a single capture.
_Avoid_: A/B test, experiment

**Readable site**:
An official site whose pages the measurement network can fetch under robots.txt. A site that refuses is
reported as unavailable and counted outside the programme-page denominator.
_Avoid_: reachable (an HTTP fact, not a policy one)
