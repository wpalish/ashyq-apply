# Release evidence

Every measured value below is generated from `artifacts/release-evidence.json`
by `backend/scripts/render_release_docs.py`. Nothing inside the generated block
is typed by hand, because hand-typed numbers drift, and the ways they drift are
not obvious: a `sed` with an empty variable once turned six
`**PASS** — 1858 passed` rows into `**PASS** —  passed`, and the consistency
test did not notice, because its rule was "if a number is here it must match"
and a blank is not a number.

To refresh it:

```bash
cd backend
.venv/bin/python scripts/release_evidence.py --canary DIR --container-check-run FILE
.venv/bin/python scripts/render_release_docs.py
```

## What this document is, and is not

It is a snapshot, produced on a developer machine, of the commit named in the
generated block. It is **not** proof about the commit it is checked in at: a
file in a repository can only ever describe a commit before itself, since the
commit that records a count is itself a commit.

The authority for a given commit is the CI attestation, written by the
`container-runtime` job and uploaded with the diagnostics. On a `pull_request`
event the commit CI checks out is a *synthetic merge* of the branch head onto
the base — not the branch head — so the attestation records `tested_sha`,
`head_sha`, `base_sha` and both trees separately. An earlier version of this
document called the merge SHA the branch SHA, which is how an artifact named
for `ba15bbb` came to be built from merge commit `6a95c5bd`.

## Environment

| | |
|---|---|
| Machine | macOS (darwin 25.5.0), Apple Silicon |
| Python | 3.12.13 in `backend/.venv` |
| Node | 22 |
| PostgreSQL | 16.2, provisioned in-process by `pgserver` via `scripts/pg.py` |
| Container runtime | none installed locally; the gate is measured by CI |

## Gates

<!-- generated:gates:begin -->
<!-- generated:gates:end -->

## Accepted programme pages

Every page the live canary accepted is listed in
`artifacts/accepted-pages.json` with its institution, the programme name and
level the classifier assigned, the run it came from and a reviewer verdict.
Counts quoted anywhere must resolve from that file rather than from prose: this
document has previously said 12, 14 and 20 in different places.

## What this document must not be read as

- It does not say the product is ready. The verdict in the generated block is
  computed from the gates *and* the product thresholds, and the thresholds
  alone can hold it at NOT READY however green the technical gates are.
- A passing container gate means CI ran the smoke test at the named commit. It
  does not mean anything was deployed; nothing has been.
- No number here is a prediction of admission or of funding.
