# H-E: university-name aliasing — the production identity gate on the thirteen dev5 homepages, native names, award bindings

Type: research
Status: open
Blocked by: —
Map: ../map.md · AFK, offline (homepages hand-fetched as ticket 12 of the programme-discovery map did; `python3 -I`); no run.

## Question

Three places read a university's name: production's identity gate (`_identify_site`: homepage title/h1 must contain
the English seed name or an acronym equal to the host label — failed 8 of 15 development homepages, ticket 12), the
confirm step's "names another institution" check (R6), and the scorer's `university` dimension (patched twice on
development: KIT, UNSW). The nine never exercised the gate (registry path), so **the product's first wall for an unseen
university in these countries is unmeasured**; the second look's gate arm (01-Q4) will measure it on the nine once —
this ticket predicts it on dev5 first. Award bindings are the fourth name problem: a claim on an award page with no
binding stays `unmapped.*` (2–7 per column on the nine; dev3 36–38).

## Test

1. **Gate offline** on the 13 dev5 homepages (and the 9 dev4 ones for comparison): fetch `https://{host}/`, record
   final host, `<title>`, `h1`s, `<html lang>`, hreflang `en` alternate; run `scratchpad/wf_tools/identity_gate.py`'s
   rule with the seed row (`unimatch_top500_seed.json`) or, for an off-seed case, the name 02 gives. Verdict per case:
   PASS / FAIL conclusive (native or short name) / FAIL inconclusive (shell, challenge). Then the three signals the
   design of ticket 05 (programme-discovery) added — redirect to `official_site`, native name by `<html lang>`, English
   alternate — applied to the same pages: how many would pass.
2. **Native-name table**: seed-row English name, the homepage's own name in the page language, the acronym the site
   uses, whether `metrics._name_parts` / `_acronym_names` would match them (scorer), whether R6's
   `_names_other_institution` would call a faculty page "another institution" (confirm). dev4 + dev5 rows.
3. **Bindings coverage** (`evaluation.research.expressibility` on dev4 draft3 and dev5 draft2 as 04 lands): how many
   known award labels have a binding; how many claim keys the pipeline can emit for them. For dev5 before 04: the
   count of named awards on the drafts' award pages that would need a binding.

## Deliverable

`docs/process/IDENTITY_GATE_DEV5_2026-10-19.md`: the gate table (pass / fail / reason) for dev4 + dev5, the native-name
table, the bindings coverage, and a verdict: **H-E confirmed for the product path** if ≥ 4 of 13 dev5 homepages fail
the gate conclusively (then the gate arm of the second look must be pre-registered as *expected* to lose cases at the
gate, and the design signals of ticket 05 are the rule to build — flag proposal `IDENTITY_GATE_NATIVE_NAME`,
`--identity-gate-native-name`, loop id **IG-1**, files `catalogue/discovery.py` `_probe_site` only); **refuted for
the scorer** if every dev4/dev5 label scope name is matched by `dimension_matches` on the recorded name.

## Files the worker holds

`scratchpad/g11/*`, the new doc. No code change in this ticket.

## Evidence

- programme-discovery [12](../../programme-discovery/issues/12-identity-gate-offline.md) (method, 8/15 failures,
  the three signals), [05](../../programme-discovery/issues/05-identity-gate-in-design.md); `catalogue/discovery.py`
  L101–190, L277–294; `metrics.py` L64–143; `identities.py`; `expressibility.py` docstring;
  `HELDOUT_STAGE_SUMMARY_2026-10-19.md` `by_type:unmapped.scholarship_exists 2–7`, `identity gate not exercised`.

## Done when

The doc is committed; the Answer gives pass/fail counts, the native-name table size and the bindings coverage; 15
reads the gate prediction. Loop id: **G-11**.
