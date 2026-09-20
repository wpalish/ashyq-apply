# Corpus versions over one frozen capture

All rows use `baseline/capture.json`. None is human-certified. This table compares
label inventories, not changes to the production pipeline or retrieval quality.

| Dataset | Known / total fields | Known programme URLs | Programme precision / recall | Claim precision / recall | Critical coverage |
|---|---:|---:|---|---|---|
| [draft1](data/ground_truth.json) | 12/160 | 6/10 | 1/7 / 1/6 | 0/5 / 0/12 | 0/150 |
| [draft2](data/ground_truth.draft2.json) | 46/206 | 8/10 | 1/8 / 1/8 | 0/5 / 0/46 | 0/197 |
| [draft3](data/ground_truth.draft3.json) | 52/212 | 8/10 | 1/8 / 1/8 | 0/5 / 0/52 | 0/203 |

- Draft1 freezes the initial source annotation and captured pipeline outputs.
- Draft2 adds official-source annotations, resolves Toronto/KAIST programme identity
  and corrects Aalto subject and Groningen fee-year assumptions. It changes which
  returned URLs and claims can be adjudicated.
- Draft3 splits seven document records into thirteen fields without introducing
  new source facts. The [projection manifest](data/document_projection.draft3.json)
  permits reconstruction of every original value, including conditions and JSON types.

Claim adjudication stays 5/13 and support adjudication stays 0/13 in all three
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
