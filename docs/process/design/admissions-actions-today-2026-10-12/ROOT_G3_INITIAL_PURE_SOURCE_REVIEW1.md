# Root G3 first immutable source review

2026-10-12 · SOURCE_ONLY / NOT_ACCEPTED / NOT_APPLIED / NOT_IMPORTED / NOT_RUN

## Evidence boundary

Root read the complete sealed schema (1151 lines), domain (714), tests (646), README, preimages and native read pins. All9 SEAL members, all8 accepted frozen contract pins, root ninth implementation disposition, and all17 declared native source pins match exact current bytes. All3 new-file diffs reconcile to exact source postimages; their new file headers use b/path. The seal is 41a34f0226609b0710a83135b815f0b35ef873096296b2bfd50478731544b1e1. All3 granted application paths remain ABSENT in primary and isolated lab. No application import, collection, execution, lint/typecheck or runtime result is claimed.

## Confirmed source blockers

1. **Canonical native UUID compatibility.** schema85–92 accepts lowercase hex only. tests125–132 affirm rejection of an uppercase A–F UUID. Native backend/app/schemas/shared_route.py54–63 accepts [a-fA-F] and canonicalizes to UUID; independent frozen oracle P05 requires equal canonical typed intent. Repair the parser to preserve native equivalence, replace the erroneous rejection case with a genuine malformed spelling and add independent equal-digest/replay controls. Do not broaden beyond exact hyphenated form or coerce revisions.
2. **Embedded decoded token-key link form.** schema1145–1148 blocks a token key only at segment start or after ;/&. prefix-token=PRIVATE remains actionable although frozen FINITE§3 requires embedded decoded key=value token forms to be blocked. Repair only this new lexical policy, preserving raw authority order, one decoding pass, original proof identity, fixed safe output, no global SourceLink or network behavior.
3. **Correction of an already corrected planning declaration.** domain271–276 requires prior.applied_delta.declaration non-null for every correction. A valid accepted correct_declaration→planning legitimately has no submission/withdrawal body but has the exact own application mutation and correction ref. The command/schema explicitly allow correct_declaration and owner disposition permits any prior own same-application declaration. Validate the complete own prior receipt/event/kind/affected application and allow this permitted correction chain; preserve originals and append one event, never replace old history.
4. **Wrong own application relationship classification.** The same condition returns record_not_found404 for a valid fully checked own prior declaration associated with a different existing own application. The accepted pure oracle P20 requires invalid_transition422 for an own wrong relationship, missing/foreign record404, corrupted saved receipt503. Separate those cases without revealing foreign data or bypassing ownership.

Independent reviewer confirms all4 by source inspection; sealed full independent receipt is pending. Any further reviewer blocker must receive explicit root disposition before a repair is accepted. The first authored source/controls stay immutable; a finite second packet must preserve preimages and all original controls except the demonstrated erroneous uppercase rejection.

## Supported architecture versus deferred proof

Closed12 commands; three-field EventRef; full actor identity; current/head/affected metadata; original replay; durable task/old report preservation; separate own-state/source/plan/access reads and supplied Today behavior are explicit in the proposal. This source review is not a PASS result, proof of raw/native parsing, migration, storage race, API privacy, export/delete implementation or browser recovery. Caller-supplied observations do not establish ownership/access. Model/API/migration/frontend/actual Today endpoint remain outside this initial grant. The independent42-group oracle is planned coverage, not42 executed tests; producer42 source test functions/97 literal cases are NOT_COLLECTED.

## Limits and next step

Save the immutable first packet and this report, then receive and read the complete sealed independent source review. Issue a separate finite repair grant for the confirmed blockers only, preserve all previous bytes, verify sealed replacement source/controls, then qualify source before root-only application and bounded isolated local static/focused gates. No main/deploy/live/provider/closed protocol work. All prior STOPs remain unchanged.
