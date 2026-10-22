# Motion contract — 22 October 2026

The original UI book remains the visual authority. This owner-requested increment adds motion to the existing UI; it does not change colours, typography, page topology, API commands or save semantics.

## Interaction matrix

| Trigger | Motion | Duration / cancellation |
| --- | --- | --- |
| Route change | Route opacity .72→1; heading rises 7px | 220 / 280ms, existing route lifecycle only; keyboard cancels CSS |
| Profile step change | Newly visible step rises 7px | 220ms, existing hidden panels stay mounted and drafts remain intact |
| Programme tab | Decorative underline slides and resizes with a transform | 240ms, retargetable CSS transition, measured on selection/font/rail resize |
| Programme content | Stable presentation surface, opacity .65→1 / translateY6→0 | 220ms WAAPI; cancel on next selection, keyboard, media change and unmount |
| Funding tab/content | Same rail and content surface | Same timing; filters and saved results remain real state |
| Button press/release | Scale .975, retargetable | 120ms; disabled buttons excluded, keyboard immediate |
| Sidebar/current section | Background/colour; current icon scale1.08 | 150–220ms, no delayed navigation |
| Profile rail / journey / language control | Background/colour feedback | 150–180ms, no animated form values |
| Main and case menu | Scale .97→1 / translateY−5→0, top-right origin | 190ms entry; native close and Escape remain immediate |
| Evidence/catalogue disclosures | Opacity / translateY7→0 | 180ms on opening; native close immediate, no height animation |
| Recovery, notice and save feedback | Finite surface entry | 180ms; never changes pending/ACK/error meaning |
| Existing modal | Backdrop opacity; surface scale .975→1 / translateY10→0 | 180 / 240ms; dismissal and focus lifecycle unchanged |
| Share switch | Native control thumb transform | 180ms, retargetable; no persistence animation pretending to be ACK |
| Result, catalogue, plan, application and shortcut cards | Hover lift2px | 220ms, only fine pointers with hover support |
| Next-action arrows | Hover shift3px | 220ms; never needed to understand or activate the action |
| Landing/auth introduction and artwork | Finite entry7–14px and slight scale | 360 / 480ms; only public introduction artwork, no continuous loop |

All movement primarily uses opacity and full transform strings. No animated width/height/top/left, global layout transitions, per-frame React state, new dependencies or indefinite decorative animations. The route itself is not translated: this avoids changing containing blocks for fixed save bars and overlays.

## Accessibility and lifecycle

- `BookMotion` tracks pointer/keyboard input in a DOM attribute without rerendering the applicant tree. StrictMode cleanup restores previous state and removes listeners.
- Keyboard-driven actions are immediate. Pointer input enables motion again. `prefers-reduced-motion: reduce` overrides both new and inherited workspace motion.
- `BookTransition` never keys or remounts its children. It uses the browser animation API only when available; missing support leaves content visible and functional.
- A rapid tab reversal cancels the previous animation. Preference changes and keyboard input cancel in-flight WAAPI transitions. No delayed exits retain an inaccessible old panel.
- The decorative tab line has no input/focus semantics. Buttons retain native keyboard activation. Resize observers disconnect on cleanup.
- No animation dispatches application commands, updates data, waits for an animation to finish before saving, or marks an operation successful.

## Verification (current increment)

- Baseline: 111 frontend files / 1049 tests passed.
- Current: 112 files / 1053 tests passed. Four new behaviour tests exercise unsent draft identity, rapid reversal/focus preservation, keyboard/reduced-motion cancellation, and indicator resize/observer cleanup.
- TypeScript and production build passed. Lint: zero errors, nine inherited warnings. Existing bundle size warning remains.
- `git diff --check` passed. No backend application or schema changes; no backend/search/provider/security/heldout runs or production deployment.
- Local preview restarted at http://127.0.0.1:18140/ using the existing synthetic database on18141. The old browser tab remained on a service error page. The browser security gate denied acquiring that page (unsupported protocol); no workaround was attempted. Owner asked to reload the tab. Current native desktop/mobile, visual timing, live OS reduced-motion and real-device performance review remain pending. Unit tests do not establish frame rate or subjective Apple fidelity.

The previous 19October native rapid-tab evidence describes the earlier implementation only and is not claimed as fresh motion verification.
