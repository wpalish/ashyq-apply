# Backend learning-pack proposal

**READY FOR INDEPENDENT REVIEW / NOT APPLIED.** 2026-10-11. Root is the source/Git writer. Apply only the five repo-relative files listed in source-pins.json after checking their preimages; this is an external proposal, not a native full-gate/deployment receipt.

## Scope

- Two existing files: schemas/preparation.py and api/routes_preparation.py.
- Three new files: preparation/learning_pack.py, tests/test_learning_pack_domain.py, tests/test_learning_pack_api.py.
- Original catalogue.py, all three starter lessons/9items, existing tests, models/migrations, payments, Academics, research and deadline calendar stay unchanged.
- Explicit pack catalogue/progress opt-in; default catalogue serializes identically. Exact per-lesson versions; choice DTO/digest/grader preserved. New short types and stored feedback are distinct shapes, with no null defaults inserted into choice answers.
- Nine lessons:3 starters+6 original reviewed drafts/30new practice items. Full student teaching/examples/passages/instructions are literal Markdown introductions. Private teacher keys are never initial public fields. Matching headings/features remain choice questions; completion is genuine short answer.
- Saved-UUID review reads original stored receipt and exact immutable lesson after expiry; unknown/retired pair returns null lesson. No entitlement bypass for unseen lessons, regrading or substitution.
- New pack stores first submitted answer order/raw short text; grading alone normalizes. Identical reordered UUID retries replay the first receipt. Legacy starter canonical ordering remains exact.

## Actual bounded verification

External isolated ordinary app copy, inherited native Python, own staging only. The pure test launcher installs a durable Python audit hook denying IP bind/connect/send and DNS before imports; IPv6 capability is temporarily false for harmless import probes and restored afterward. It does not launch DBs, servers, providers or native full runner.

- Final pure domain: **54 PASS**,0failure/error/skip,0.10s; focused-junit.xml and focused-guard.json, outside_attempts=[] and IPv6 restored.
- Five-file native-context Ruff check, Ruff format check and mypy: **PASS** (evidence/*-ready.log).
- API test collection: **56 cases**,28 SQLite+28 PostgreSQL, no fixture/HTTP/database execution. **API RUNTIME NOT_RUN; FULL BACKEND/PG/FRONTEND/E2E NOT_RUN BY AUTHOR.** Root must execute its unchanged full gates on integrated bytes.

Preserved errors: system Python authoring extractor lacked zip(strict); initial pure run50PASS2FAIL used an overly broad prose substring assertion for the private JSON key explanation (teaching can legitimately contain that word); corrected assertions check actual JSON key syntax, not arbitrary prose. Initial mypy found feedback variable/SQLAlchemy Row annotations; both repaired without weakening runtime assertions. Initial formatting/import diagnostics and raw logs remain retained. The final raw-text receipt check covers the inherited whitespace-trim seam before seal.

## Original inputs and qualifications

- SAT_WEEK1.md SHA0445e9070186d577a4b5b8f549562821e7801c4a34b21695e7196438fe1fd802.
- IELTS_READING_WEEK1_v2.md SHAe4414505cdc5c3e807de315487685e024cbba583d53f9c872ffff4ea7806cddb. V1 remains historical; use corrected v2 forms.
- Student material is copied from the reviewed drafts; keys/explanations from their teacher tables. One obsolete editor-only metadata sentence describing short answer as unimplemented is excluded from runtime material. No teaching/passage/question/key is rewritten by that exclusion.
- Originality is author-attested. Saved static item review is distinct from qualified-teacher pedagogy, learner trials, calibrated difficulty, full course, score improvement, IELTS band/SAT score or admission readiness. All of those remain unclaimed.
- A repeated quiz is familiar-item review. Practice submission/progress never becomes a prerequisite attainment, calendar completion or official baseline.

Authoring scripts and isolated/ are non-application artifacts; final files/ plus the sealed patch are authoritative. Do not rerun the earlier authoring composers to overwrite final edits. Immutable source/inputs/outputs and evidence hashes are recorded in source-pins.json and MANIFEST.json. Review must bind their final exact bytes.
