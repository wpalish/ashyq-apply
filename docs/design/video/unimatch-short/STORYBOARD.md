---
format: 1080x1920
duration: 30s
message: "Know what is left to pay — before you apply"
arc: Hook → Product intro → Demo cycle (routes → pass → money → answers → decide → plan) → CTA
audience: students applying abroad (first users in Kazakhstan), and their parents
mode: autonomous
music: original synthesized bed, 120 BPM, A minor (Am–F–C–G), one chord per 2 s bar
captions: skipped (no narration)
---

# Unimatch — 30-second vertical short

Repurposed from a 30 s horizontal SaaS promo (ClimbX). Kept: the core idea — a nagging question
answered by the product in fast, confident beats — and the pacing: a new beat every 2–4 s on a
120 BPM grid, a dark "why it matters" beat two-thirds in, an end card with what you get and one
button. Original: every visual (Unimatch's night globe, passes in country colours, the money line
by line, the three separate answers, tickets), the script (no line of the source's copy) and the
structure (tabs → one pass, a route map, a money sheet, a swipe, a dated plan — none of these
beats exist in the source).

## Video direction

- **Palette** (`frame.md`): two registers. **Night** — ground `ink-black` #101014, text `cream`
  #F3F2EF, muted `cream-muted` #A9A9B6, accent `fire-orange` (= ochre tint #D2BE8C) for kickers and
  one emphasised word. **Paper** — ground `paper` #F3F2EF, text `ink` #111114, muted 55 % ink.
  Passes wear their country: Groningen `pass-1` slate, Leuven `pass-2` plum, Tokyo `pass-3`
  oxblood, Vienna `pass-8`; route strokes in the matching `tint-N`. Product sheets are white with
  the app's tone chips (pending amber, stronger / competitive blue). Night and paper alternate:
  N P N P P N P P P.
- **Type**: Inter only. Display is lowercase 800, tight (−0.04 em), one display moment per frame,
  left-anchored at `pad-x`. Kickers are Inter 700 uppercase 0.16 em in the accent (night) or 55 %
  ink (paper). Figures are tabular.
- **Motion grammar**: everything lands on the 0.5 s beat grid of the music. Entrances are
  `fromTo` with long-tail eases (`power3.out` default, `expo.out` for slams, `back.out(1.4)` only
  for the logo tile's pop). Words reveal by line with a short y-rise + blur-in; cards travel with
  overlap and settle; numbers never count up or down — a figure appears whole, as the page states it.
  A slow camera drift (scale 1.00 → 1.04) runs under every frame so held reads stay alive.
- **Rhythm / holds**: frames 1–4 accelerate; frame 5 ends on a 1 s held read of "1,848"; frame 6 is
  the breakdown (music drops its kick, motion slows, the three answers stamp one per bar); frames
  7–8 snap back; frame 9 holds its final 2 s still.
- **Keep-out**: all content above y = 1600 (bottom 17 % kept clear — the platform's own UI sits
  there on Shorts / Reels / TikTok).
- **Negative list**: no orange, no stock imagery, no fake logos, users, reviews, ratings or URL;
  no percentage, chance or probability anywhere; no count-up on money; no glow blobs or
  purple-blue "AI" gradients; no elastic bounce except the logo pop; no slideshow (front-load then
  freeze) and no screensaver (everything floating on its own).

## Frame 1 — The question

- scene: Night. "where can i study" types in; browser tabs pile up above it until they crowd the frame; "— and what will it cost?" slams in
- duration: 3s
- poster: 2.6s
- transition_in: cut
- type: hook
- status: animated
- src: compositions/frames/01-hook.html
- voiceover: (none — on the beat)
- blueprint: compose
- focal: the two-line question
- roles: tab strip = supporting (the problem made visible) · question = focal
- sfx: keyboard ticks, riser into 3.0 s

Scene 1 (0.0–1.0s): night ground; kicker "STUDY ABROAD" at top-left; display line 1 "where can i study" types in letter by letter (two beats) at ~0.42 h, a caret blinking on the beat.
Scene 2 (1.0–2.0s): browser tabs drop in from above one per half-beat and pile into a tilted stack across the top half — titles "Tuition fees 2027/28 (PDF)", "Scholarships — who can apply", "Admission requirements", "Cost of living", "Application deadlines", "Recognition of foreign diplomas", "Fees for non-EU students", "Grant FAQ" — each new tab nudges the stack; the stack crowds toward the question.
Scene 3 (2.0–3.0s): line 2 "— and what will it cost?" slams in under line 1 (expo), "cost?" in the accent; the tab pile tightens (scale 1.0 → 0.96) as if about to be swallowed. Hold the last half-beat.

## Frame 2 — One place

- scene: Paper. Every tab is pulled into one point — the dot of the i — and the unimatch wordmark opens out of it; "official pages, read for you."
- duration: 2s
- poster: 1.4s
- transition_in: cut
- type: product_intro
- status: animated
- src: compositions/frames/02-logo.html
- voiceover: (none)
- blueprint: compose
- focal: the unimatch wordmark (the owner's logo, assets/images/unimatch-logo.svg)
- roles: tab ghosts = supporting · wordmark = focal
- sfx: whoosh-in, impact-soft at 0.5 s

Scene 1 (0.0–0.5s): paper ground; eight small tab ghosts (the same titles, as pale bars) rush from the edges into the centre and vanish into a point at ~0.42 h.
Scene 2 (0.5–1.2s): that point is the dot of the i: it pops, then the whole wordmark opens out of it (a circular reveal centred on the dot) with a slight settle — centred, ~80 % of frame width.
Scene 3 (1.2–2.0s): the tagline "official pages, read for you." rises under the lockup in 55 % ink; a hairline rule draws under it. Hold.

## Frame 3 — From Astana

- scene: Night. The globe rises; routes draw from Astana to Groningen, Leuven, Vienna, Tokyo and Singapore, one per beat; "from astana / to 15 countries."
- duration: 4s
- poster: 3.4s
- transition_in: cut
- type: feature_showcase
- status: animated
- src: compositions/frames/03-routes.html
- voiceover: (none)
- blueprint: compose
- focal: the globe with its routes
- roles: globe-night.svg = focal (lower 60 %) · route strokes (inlined from routes.json) = focal detail · headline = supporting
- asset_candidates: capture/assets/images/globe-night.svg
- sfx: low swell, five soft plucks on the route ends

Scene 1 (0.0–1.0s): night ground; the globe plate rises from below into the lower ~65 % of the frame (centre near 0.66 h, wider than the frame), Astana's white dot lands with one pulse ring; kicker "FROM YOUR CITY" + display line "from astana" at the top-left.
Scene 2 (1.0–3.0s): five routes draw out of Astana one per beat in their country tints (Groningen, Leuven, Vienna, Tokyo, Singapore), each ending in a dot and a small city label that pops on arrival; the camera pushes in slightly (scale 1.0 → 1.05) toward the routes.
Scene 3 (3.0–4.0s): display line 2 "to 15 countries." lands under line 1; a small tag beneath it, "demo run · 20 programmes", in muted. Hold the map still for the last beat.

## Frame 4 — A pass each

- scene: Paper. Three passes fly up and stack — Tokyo (oxblood), Leuven (plum), Groningen (slate) on top; "one pass / per programme."
- duration: 2s
- poster: 1.6s
- transition_in: cut
- type: feature_showcase
- status: animated
- src: compositions/frames/04-passes.html
- voiceover: (none)
- blueprint: compose
- focal: the pass stack
- roles: passes = focal · headline = supporting
- sfx: three card flicks

Scene 1 (0.0–1.2s): paper ground; three passes fly in from below one per beat with a slight spin and settle in a fanned stack in the lower-middle (Tokyo 1,986 · Leuven 7,554 · Groningen 32,663 "USD a year, price"), each carrying country, city, university · programme.
Scene 2 (1.2–2.0s): headline "one pass / per programme." rises at the top-left; the "Example · demo data" tag lands on the top pass. Hold.

## Frame 5 — What is left

- scene: Paper. The Groningen pass opens into the money sheet line by line: price 32,663, Talent Grant − 30,815 if awarded, left to pay 1,848; "what's left / to pay."
- duration: 4s
- poster: 3.6s
- transition_in: cut
- type: benefit_highlight
- status: animated
- src: compositions/frames/05-money.html
- voiceover: (none)
- blueprint: compose
- focal: the "left to pay" figure
- roles: Groningen pass = supporting (top) · money sheet = focal · headline = supporting
- sfx: three ticks (one per line), a low hit on 1,848

Scene 1 (0.0–1.0s): paper ground; headline "what's left / to pay." at the top-left; the Groningen pass (slate) sits under it with "32,663 USD a year, price".
Scene 2 (1.0–2.5s): a white sheet slides out from under the pass; its rows appear one per beat — "Price a year · tuition, housing, living, fees · 32,663", then "Groningen Talent Grant · competitive · if awarded · − 30,815" (minus in green).
Scene 3 (2.5–3.0s): the total row lands — "Left to pay a year · if the grant is awarded · 1,848" — big; the pass's price swaps from 32,663 to "1,848 USD a year left, if awarded" (a swap, never a count).
Scene 4 (3.0–4.0s): an "if awarded" stamp lands beside the total in the accent hue; source line "rug.nl · demo fixture · read Oct 05" fades in under the sheet. Hold still.

## Frame 6 — Answers, not odds

- scene: Night. Three answers stamp in one per bar — requirements · pending, your profile · stronger, money · competitive; then "answers, / not odds."
- duration: 4s
- poster: 3.6s
- transition_in: cut
- type: benefit_highlight
- status: animated
- src: compositions/frames/06-answers.html
- voiceover: (none)
- blueprint: compose
- focal: the three answer rows
- roles: answer rows = focal · closing line = supporting
- sfx: three stamps (music breakdown, no kick)

Scene 1 (0.0–1.0s): night ground; kicker "REQUIREMENTS · PROFILE · MONEY"; row 1 lands: "requirements" (display, cream) + an amber chip "Pending" + muted note "waiting on minimum GPA".
Scene 2 (1.0–2.0s): row 2 lands under it: "your profile" + blue chip "Stronger" + "above the minimums".
Scene 3 (2.0–3.0s): row 3: "money" + blue chip "Competitive" + "Talent Grant, if awarded"; hairlines draw between the rows.
Scene 4 (3.0–4.0s): the closing line "answers, / not odds." rises at the bottom of the block, "not odds." in the accent; a muted note "three separate answers — never one score". Slow settle.

## Frame 7 — One at a time

- scene: Paper. A fanned deck; "keep" is pressed and the top pass slides onto a kept pile; the next pass comes up; "decide / one at a time."
- duration: 3s
- poster: 2.6s
- transition_in: cut
- type: feature_showcase
- status: animated
- src: compositions/frames/07-decide.html
- voiceover: (none)
- blueprint: compose
- focal: the deck
- roles: deck = focal · three buttons = supporting · headline = supporting
- sfx: tap, swish

Scene 1 (0.0–1.0s): paper ground; headline "decide / one at a time." top-left; the deck of three passes (Groningen on top, Leuven and Tokyo fanned behind) settles mid-frame; three pill buttons under it — "Not for me", "Maybe", "Keep" (Keep in ink).
Scene 2 (1.0–2.0s): "Keep" presses (scale dip on the beat); the Groningen pass slides up-right onto a small "Kept · 1" pile and the deck re-fans with Leuven on top.
Scene 3 (2.0–3.0s): "Maybe" presses; Leuven slides onto a "Maybe · 1" pile; Tokyo comes up. Hold the last half-beat.

## Frame 8 — A dated plan

- scene: Paper. Deadline tickets slide in with country stubs — 1 Feb Talent Grant, 1 Mar KU Leuven, 1 May Groningen; a black card "start first: reference letter"; "your plan, / dated."
- duration: 3s
- poster: 2.6s
- transition_in: cut
- type: feature_showcase
- status: animated
- src: compositions/frames/08-plan.html
- voiceover: (none)
- blueprint: compose
- focal: the ticket list
- roles: tickets = focal · this-week card = supporting · headline = supporting
- sfx: three ticket slides

Scene 1 (0.0–0.8s): paper ground; headline "your plan, / dated." top-left; the black "This week" card drops in under it: "Start first: reference letter — it depends on someone else".
Scene 2 (0.8–2.4s): three tickets slide in from the right one per beat, each with a country-colour stub and a perforation: "1 Feb 2027 · Groningen Talent Grant · grant", "1 Mar 2027 · KU Leuven · BSc Informatics", "1 May 2027 · University of Groningen · BSc Computing Science".
Scene 3 (2.4–3.0s): a small "demo data" tag lands under the list. Hold.

## Frame 9 — Start with your profile

- scene: Paper end card. The wordmark; "know what's left to pay / — before you apply."; three honest promises; the button "start with your profile →"
- duration: 5s
- poster: 4.2s
- transition_in: cut
- type: cta
- status: animated
- src: compositions/frames/09-end.html
- voiceover: (none)
- blueprint: compose
- focal: the headline + button
- roles: logo = supporting · promises = supporting · button = focal
- sfx: final hit at 3.0 s

Scene 1 (0.0–1.0s): paper ground; the unimatch wordmark wipes in at the top; the display headline "know what's left to pay" rises line by line, "— before you apply." in 55 % ink.
Scene 2 (1.0–2.5s): three promise rows tick in one per beat with a hairline above each — "a source and a date on every fact", "three answers, never a score", "free to start".
Scene 3 (2.5–3.5s): the ink pill button "start with your profile →" pops in (scale 0.9 → 1); a soft press on the downbeat at 3.0 s.
Scene 4 (3.5–5.0s): fine print fades in under the button — "example figures from demo data · none of this predicts an admission decision". Hold still to the end; a gentle fade to paper in the last 0.4 s (final frame).
