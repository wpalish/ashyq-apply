# Expert-500 V4 representation proposal

Date: 2026-10-04. Status: prospective design only, for an owner decision after the complete V3 seal and report. This note makes no V3 result or score claim. Every institution, programme, qualification, date and value in the examples below is invented.

## Public contracts reviewed

The review used the public `TASK` and `selector_packet` in `/tmp/unimatch-expert500-journal-pilot.py`, plus:

- [Journal instructions and acceptance](../../backend/evaluation/research/expert/journal.py).
- [Compact facts, scopes, values and expansion](../../backend/evaluation/research/expert/compact.py).
- [Question scope obligations](../../backend/evaluation/research/expert/models.py).
- [Every-fact citation validation](../../backend/evaluation/research/expert/citations.py).
- [Public key mapping](../../backend/evaluation/research/mapping.py), [evaluation types](../../backend/evaluation/research/schema.py), and [scope comparison](../../backend/evaluation/research/metrics.py).

The proposal concerns public representation and closure. Its examples contain no reviewed answers, private subject bindings, university routes or earlier trial output.

## 1. Give the selector the same representation contract the validator uses

V3 already instructs source-only scope, explicit nulls, typed boolean programme existence, correct intake/year, and immutable sparse findings. Its provider schema is stricter about transport shape than about a fact's meaning:

| Contract boundary | Current gap | Prospective guidance |
| --- | --- | --- |
| University | Instructions demand a source-supported university string; a settled finding also compares it literally with the public request's university. A site's branding can differ from that canonical name. | Explain institution attribution separately from applicant/programme/time applicability. Publish the public case's canonical institution string and the exact proof requirement for using it. |
| Programme | Q0 requires the submitted programme string to occur in the exact evidence location. Degree words or an expanded title added by the selector can break that requirement. | Copy the actual title visible at the cited location into `scope.programme`. Keep canonical degree and field in their separate fields, only when established by that source. |
| Intake | An older intake may be correctly quoted yet fail when assigned to the requested Q3. | Keep a historical fact under `OTHER` with its actual published intake. A settled Q3 requires evidence for the requested intake. |
| Typed value | `value_json` is a string containing any valid JSON; the public key dictionaries name keys but do not define a complete value schema for each one. | Publish a short, versioned key/value card generated from public types and mapper interfaces. Explain inner JSON types and aliases explicitly. |
| Closure | A hash-only commit still receives source views, ontology and a packet. It can spend the remaining selector time regenerating a large answer. | Use a dedicated small commit contract, or a declared mechanical budget closure, after the latest observed source has been explicitly checkpointed. |

These explanations should be present before navigation begins. Validation errors remain a final guard rather than the only way a selector can learn the contract.

## 2. University identity: canonical attribution with an explicit proof boundary

Use the current public case identity as an attribution anchor. It supplies a name and official domain, not an admissions rule. Do not treat the applicant request as evidence of any scope dimension.

A minimal V4 instruction could say:

> For institution attribution, use the exact public case university string only after the recorded official source is verified as belonging to that institution. Preserve the source's literal institution wording in its quotation. A different institution or an ambiguous alias requires an unresolved identity; do not silently rename it. Programme, degree, field, population, qualification, intake and academic year still come solely from source evidence, with unstated dimensions null.

This is a deliberate clarification to the broad V3 phrase “never fill scope from the request.” It must be accompanied by a source-attribution check. An official domain alone cannot override a passage explicitly describing a different institution, consortium member or partner.

If the existing validator cannot preserve both canonical attribution and literal wording, use a versioned V4 representation with separate `entity_ref` and `source_scope` fields. The parent supplies the current `case_id`; the selector supplies source wording. An optional identity assertion must cite an exact recorded quotation/location demonstrating equivalence. Project to the canonical evaluation university only after that assertion and official-source provenance validate; otherwise retain literal source scope and leave the finding unresolved. Any projection rule must be frozen before V4 and leave the original source scope in the seal.

Synthetic example: public identity “Example University”; source explicitly says “Example University, also branded University of Example.” Canonical attribution is justified by that recorded equivalence. A source saying only “University of Elsewhere” must not be relabelled as “Example University.” No case-specific alias table should be learned from reviewed data or prior failures.

## 3. Programme labels: preserve the title, separate the category

The evidence location, rather than the applicant's preferred title, determines the programme string. If a location says:

> Example University offers Computer Science as a bachelor's degree.

the source title is `Computer Science`; `Bachelor of Science in Computer Science` would add words absent from that location. A source that actually prints a longer title should retain that exact longer title. A title from a different page needs its own recorded quotation/location and an explicit relationship; it must not be transplanted into the cited block.

Suggested rules:

- `programme.exists` has an inner JSON boolean. A programme-name object does not replace it.
- `scope.programme` is the literal programme identity supported at the cited location.
- `scope.degree="bachelor"` is allowed when the source establishes that degree; `scope.field="computer science"` is allowed when the source establishes that field. Neither comes from the request.
- A different or combined programme remains distinct unless a predeclared public identity rule establishes equivalence. An uncertain identity remains unresolved.

The existing scorer's programme identity comparison does not relax the earlier citation requirement that the declared title be present at its evidence location. Keep both checks and document their separate purposes.

## 4. Typed values and question assignment

Retain the V3 `value_json` transport initially. Add a compact card explaining that the outer field is a string while its decoded contents preserve the value's type. For example, outer `"value_json":"false"` decodes to boolean false; outer `"value_json":"\"false\""` decodes to a string and is a different value.

| Public key | Synthetic inner JSON example | Rule |
| --- | --- | --- |
| `programme.exists` | `true` or `false` | Boolean only; absence of search results proves neither value. |
| `ielts.overall` | `6.0` | A numeric minimum stays numeric; preserve any stated conditions separately in an approved lossless shape. |
| `ielts.subscores` | `{"listening":5.5,"reading":5.5,"speaking":5.5,"writing":5.5}` | Expand a common floor to all bands only when the source explicitly states it for all bands. Do not fill omitted bands. |
| `deadline` | `"2030-03-15"` | ISO date string only when the source supplies the complete date. The application's intake is distinct from the deadline date. Do not invent a missing year or extrapolate annually. |
| `subjects.<public-subject>.required` | `true` | Preserve boolean versus conditional policy; the subject must be source-established and publicly declared. |
| Money, credential, document and award policies | A declared lossless numeric/string/object variant | Publish the exact public value alternatives before launch. Do not invent a universal money shape, drop currency/period/conditions, reduce a policy to a number, or infer a private award ID. |

A key card must distinguish mapper input aliases from canonical output keys. For instance, `admission_deadline` maps to `deadline`; canonical keys should pass through unchanged. Structured mapper input has exact fields, while an already canonical output key has its declared scalar or object value. The card must not contain expected university answers. Unsupported shapes should produce a precise key/type error, preserving the previously accepted journal atomically.

For money and complex policy keys, the public `JsonValue` type alone does not settle a narrower schema. Define any new tagged alternatives and the lossless adapter prospectively; verify them against synthetic values. A V4 adapter must not change V3 scoring or silently coerce old submissions.

### Historical intake example

Synthetic request: international bachelor entry in fall 2031. Recorded source:

> Example University: international bachelor's Computer Science applicants for Fall 2030 must apply by 15 March 2030.

A source-faithful retained fact fragment is:

```json
{
  "id": "historical_deadline",
  "question": "OTHER",
  "claim_key": "deadline",
  "value_json": "\"2030-03-15\"",
  "source_step": 3,
  "quotation": "Example University: international bachelor's Computer Science applicants for Fall 2030 must apply by 15 March 2030.",
  "location": {"kind": "text", "block_id": null, "section_path": [], "page": null},
  "scope": {
    "university": "Example University",
    "programme": "Computer Science",
    "degree": "bachelor",
    "field": "computer science",
    "intake": "fall 2030",
    "population": "international",
    "qualification": null,
    "academic_year": null
  }
}
```

This fragment requires an actual successful recorded step 3 and every existing citation check. `OTHER` changes question assignment, not validation. Q3 for fall 2031 remains unresolved. Older intake evidence does not prove `not_published`, and its date must not be shifted to 2031. The source URL and access date continue to derive from the recorded action; they are not selector fields.

## 5. Closure with small output and clear status

Keep normal evidence decisions incremental. Accepted facts/quotes remain in the parent journal; the selector sends only a new delta and its prior hash. Keep the hard delta limits and source checks. Prefer a small useful delta and short observation over reproducing all seven questions, while retaining every source-supported value that is actually submitted.

Introduce an explicit `observed_through_step` receipt, or an equivalent frozen coverage marker, for completed evidence decisions. It acknowledges which already recorded source views were considered; it creates no fact and settles no question. Validate monotonicity and the completed action prefix, hash it into the journal event, and seal it. An empty receipt must be permitted without fabricating a finding. It is a processing declaration, not proof that every relevant fact was discovered.

After the latest observed source has such a receipt and there is no pending action:

- **Small explicit commit:** a dedicated schema such as `{"kind":"commit","journal_sha256":"<exact-current-hash>"}`. Its prompt contains the current hash, the commit instruction and remaining budget; no recent source bodies, ontology or full packet are necessary. The parent mechanically constructs the final submission from retained facts. Require a completed tool-free selector, exact raw-answer replay, matching hash, and all existing final trace/citation validation. All selector/parse/hash/finalization time remains charged.
- **Mechanical closure:** freeze this policy before the trial and close the accepted journal without another model turn at the declared navigation/budget boundary. Record `completion_kind="budget_checkpoint"`; do not represent it as an explicit model commit. Omitted questions remain mechanically unresolved. The same trace/citation validation, clock, seal and eligibility checks still apply.

When the latest source has not been acknowledged, a hash-only prompt cannot replace its evidence-processing turn. Preserve the accepted checkpoint and record the coverage gap. Any partial selector output, timeout, failed turn, rejected delta or overrun keeps the existing incomplete/protocol-ineligible distinction; mechanical closure must not erase it. Closing reserve and any smaller dedicated commit timeout must be declared before V4, fit within the same total budget, and provide no fresh allowance.

## 6. Freeze and offline acceptance conditions

Before any owner-approved V4 run:

1. Freeze the public guidance, schema, key/value card, identity projection rules and closure policy. Preserve V3 artifacts and results under their original protocol version.
2. Verify synthetic canonical/alias/foreign institution cases; exact versus invented programme titles; requested, historical and unknown intakes; correct versus missing fee years; boolean/numeric/string distinctions; conditional values and null scopes.
3. Verify every quotation, structural block/section or exact PDF page, official-source attribution, body hash and raw-log policy. Include `OTHER` and unreferenced facts. Reject the entire invalid delta without changing accepted state.
4. Verify receipt replay and hash-only/mechanical closure with exact clocks, timeout retention, sticky failures, source-counter resume floors and immutable seals. No closure path may manufacture positive findings or publication absence.
5. Verify prompt blinding using synthetic sentinel fields: current public identity/request/caps and own observed sources only; baseline outputs, prior cases, private bindings and reviewed facts remain outside selectors.

Retain 120,000 active milliseconds, 60 Fetcher calls, six queries, the V3 95,000ms source deadline and 3,000ms closing reserve unless a separate owner decision changes a future protocol. Keep official-domain policy, no provider retries after 429, every-fact proof, explicit null scope, typed false, atomic append-only acceptance, truthful completion status, and sealing before reviewed-data access.

**Owner decision requested after V3 reporting:** choose prompt-only representation clarification first, or a versioned identity/receipt/closure schema. A new pilot requires its own frozen protocol and authorization; this note is not that authorization.
