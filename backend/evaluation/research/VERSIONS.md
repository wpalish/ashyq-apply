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

- Draft1 freezes the initial source annotation and captured pipeline outputs.
- Draft2 adds official-source annotations, resolves Toronto/KAIST programme identity
  and corrects Aalto subject and Groningen fee-year assumptions. It changes which
  returned URLs and claims can be adjudicated.
- Draft3 splits seven document records into thirteen fields without introducing
  new source facts. The [projection manifest](data/document_projection.draft3.json)
  permits reconstruction of every original value, including conditions and JSON types.

Claim adjudication stays 5/13 and support adjudication stays 0/13 in all seven
reports. No unsupported-claim rate can be inferred from an empty support denominator.
All ten cases remain drafts in every version; strict scoring refuses them without
the explicit provisional-results flag. A human review worksheet is not a signature.

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
