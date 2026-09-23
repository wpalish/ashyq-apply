# Corpus versions over one frozen capture

All rows use `baseline/capture.json`. None is human-certified. This table compares
label inventories, not changes to the production pipeline or retrieval quality.

| Dataset | Known / total fields | Known programme URLs | Programme precision / recall | Claim precision / recall | Critical coverage |
|---|---:|---:|---|---|---|
| [draft1](data/ground_truth.json) | 12/160 | 6/10 | 1/7 / 1/6 | 0/5 / 0/12 | 0/150 |
| [draft2](data/ground_truth.draft2.json) | 46/206 | 8/10 | 1/8 / 1/8 | 0/5 / 0/46 | 0/197 |
| [draft3](data/ground_truth.draft3.json) | 52/212 | 8/10 | 1/8 / 1/8 | 0/5 / 0/52 | 0/203 |
| [draft4](data/ground_truth.draft4.json) | 56/215 | 9/10 | 1/8 / 1/9 | 0/5 / 0/56 | 0/206 |
| [draft5](data/ground_truth.draft5.json) | 61/219 | 9/10 | 1/8 / 1/9 | 0/5 / 0/61 | 0/210 |
| [draft6](data/ground_truth.draft6.json) | 61/219 | 10/10 | 1/9 / 1/10 | 0/5 / 0/61 | 0/210 |
| [draft7](data/ground_truth.draft7.json) | 62/220 | 10/10 | 1/9 / 1/10 | 0/5 / 0/62 | 0/210 |
| **[reviewed](data/ground_truth.reviewed.json)** | 62/220 | 10/10 | 1/9 / 1/10 | 0/5 / 0/62 | 0/210 |

**Scorer definition changed 2026-09-22, and every row's `wrong_scope_claim_rate` moved with it:
5/5 → 4/5, in all eight versions.** The owner settled that the scorer compares programme *identity*
rather than programme strings, so NTU's "Bachelor of Computing (Hons) in Computer Science" now answers
a label reading "Computer Science". The pipeline did not change and the capture did not change: the
published metrics were regenerated from the same frozen `capture.json` and the same datasets, and the
diff is two lines per file — numerator 5 → 4, value 1.0 → 0.8 — with every other field byte-identical.
A number computed under the old definition is not comparable to one computed under the new; that is
why this note exists rather than a silent edit.

- Draft1 freezes the initial source annotation and captured pipeline outputs.
- Draft2 adds official-source annotations, resolves Toronto/KAIST programme identity
  and corrects Aalto subject and Groningen fee-year assumptions. It changes which
  returned URLs and claims can be adjudicated.
- Draft3 splits seven document records into thirteen fields without introducing
  new source facts. The [projection manifest](data/document_projection.draft3.json)
  permits reconstruction of every original value, including conditions and JSON types.

Claim adjudication stays 5/13 and support adjudication stays 0/13 in all seven
reports. No unsupported-claim rate can be inferred from an empty support denominator.
Every **draft** version refuses strict scoring without the explicit provisional-results flag; a review
worksheet is not a signature. The `reviewed` row is the exception and the point of the exercise: it is
signed by Диас on 2026-09-21 and scores strictly, with `provisional: false`. Its metrics are identical
to draft7's — certification changes who vouches for the corpus, never a measured value. See
[the acceptance record](ACCEPTANCE.md).

Between draft2 and draft3, the only changed aggregate metrics are the denominators
of claim recall and critical-field coverage. All operational measurements are
identical: 520 HTTP attempts, two PDFs, three wall-clock timeouts and two page-budget
failures. See [capture provenance](baseline/README.md) for budgets and limitations.

Compare future pipeline runs on the same accepted dataset version, capture budget,
scope and mapping conventions. Do not compare percentages across these versions as
an improvement or regression. Generic unresolved family placeholders remain; the
applicable field inventory still requires review.

Draft4 adds exact Aalto identity/language and qualification-scoped Groningen facts.
See [source decisions](REVIEW_DRAFT4.md) and [draft4 worksheet](REVIEW_WORKSHEET_DRAFT4.md).

Draft5 adds NTU qualification/conditional English-evidence facts and the Toronto
Kazakhstan credential. See [source notes](REVIEW_DRAFT5.md) and
[draft5 worksheet](REVIEW_WORKSHEET_DRAFT5.md).

Draft6 resolves the Delft programme identity from the official tudelft.nl page,
completing 10/10 identities and changing no label. Its two programme numbers fall
because both denominators grow against the same frozen capture; that is the
arithmetic of a tenth answerable case, not a retrieval regression. See
[source notes](REVIEW_DRAFT6.md) and [draft6 worksheet](REVIEW_WORKSHEET_DRAFT6.md).

Draft7 is the first version changed by a human reading rather than by AI
annotation. The owner reviewed draft6 and corrected two cases: Aalto's identity
moves from the Finnish tietotekniikka programme to the English-taught Computer
Engineering major, because the requested scope is an international applicant;
and HKU gains its offering school and its exact degree title. Whether Computer
Engineering satisfies a computer-science request is left open for the reviewer,
not asserted. See [source notes](REVIEW_DRAFT7.md) and
[current worksheet](REVIEW_WORKSHEET_DRAFT7.md).

**Mapping, 2026-09-23 — one IELTS floor is written as the four bands it governs.** A prediction of
`ielts_min_subscore` with a single number ("no part less than 6.0") is mapped to
`{"listening": 6.0, "reading": 6.0, "speaking": 6.0, "writing": 6.0}`, the certified corpus' own
shape for the same statement. Before this, the scorer's exact comparison could never match the one to
the other. This is a change of representation, not an equivalence. No stored capture carries a
single-number subscore, so no published metric moves (the replay guard passes unchanged).

**Scorer definition, 2026-09-23 — which way a quote supports (owner decision).** A prediction's quote
supports a label's when ours lies inside the reviewer's (the original rule), **or** the reviewer's lies
inside ours and ours is at most `SUPPORTING_QUOTE_MAX` = 300 characters; whitespace is compared
collapsed on both sides (`metrics.quote_supports`). Reviewers quote the least that proves a fact and
the pipeline a sentence, so the one-way rule made every correct claim unsupported (run 13: 0 of 6
value-correct claims supported, 2 under the reverse). **No published number moved:** all eight files
replay byte-identically against the frozen capture, whose excerpts are fragments like "The Bachelor"
that neither contain nor sit inside a reviewer's quote. Live captures are where it shows.

**Live mapping, 2026-09-23 — the approved identity bindings (owner decision).** Live captures now map
with `normalize_subject_claims` and `data/identity_bindings.reviewed.json` (the three draft1 bindings,
approved by the owner; draft1 stays frozen). An NTU Nanyang Global or KAIST Scholarship claim, or
Groningen's transcript, lands on its certified key instead of `unmapped.*`. The live claim_recall
ceiling moves from 14 to 28 of 62 (`expressibility`). The frozen capture and the eight published
baselines are unaffected: they are scored from stored predictions, not re-mapped.

**Corpus amendment, 2026-09-23 — one key for teaching language (owner decision).** Aalto's
`programme.teaching_language.primary` is renamed `programme.language` in `ground_truth.reviewed.json`
(now `2026-09-23.reviewed`; see the amendment in [ACCEPTANCE.md](ACCEPTANCE.md)). The mapping now
emits `programme.language` from the teaching language a programme page states on its `program_exists`
claim, capitalised as the corpus writes it. `metrics.reviewed.json` was regenerated: every top-level
metric is identical, and only the per-field row moves (`programme.language` 2 → 3). Drafts stay frozen.
The live ceiling becomes 31 of 62.

**Scorer definition, 2026-09-23 — scope compares case-blind outside the programme.** The pipeline writes
an intake as "Fall 2027" and the corpus as "fall 2027"; compared literally, no intake read from a page
could ever match. Every non-programme dimension now compares `casefold()`-equal (programme still
compares identity). All eight published files replay byte-identically. Alongside it (owner decision,
same day): a programme's own stated start in September–November is read as that fall intake, in page
text ("programme starts 1 September 2027") and in a deadline table's start column ("Deadline | Start
course"). A bare date is still never an intake.

**Live harness, 2026-09-23 — the page budget counts network reads only.** `--max-pages` bounded every
`Fetcher.get` call, cache hits included, so a page two stages both read (admission, tuition) was paid
for twice. Run 20 ended Delft, Vienna and UBC in the funding stage with several of their 60 calls
being cache hits. The budget now counts reads that reach a server; the capture's `config` says so
(`page_budget_counts`). Live runs before this commit are not directly comparable on budget-bound
cases. Scoring and every published file are unaffected.

**Scorer definition, 2026-09-23 — a sibling official page supports (owner decision).** A right-valued,
right-scoped claim whose quote comes from another page on the same registrable domain as a page the
reviewer cited now counts as supported. Universities publish one deadline or fee on several pages; run 23
had 9 value-correct claims and 8 of them were quoted from such a sibling page, all scored unsupported.
Another site still does not support. `verbatim_evidence_rate` keeps the same-page reading, and the strict
recall is published beside the new one as **`claim_recall_same_page`**. All eight published files were
regenerated from the frozen capture: every existing metric is identical; only the new key is added.
