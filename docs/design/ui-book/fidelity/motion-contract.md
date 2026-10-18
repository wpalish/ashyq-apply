# Motion contract —19October2026

| Trigger | Motion | Fallback / cleanup |
| --- | --- | --- |
| Programme tab selection | One keyed presentation panel, opacity0→1 andy4→0,180ms; wrapper ease[.16,1,.3,1] | useReducedMotion:duration0,y0. Last selection wins; no API mutation. Store/form identity outside panel. |
| Button hover/press |120ms colour/background/border feedback | Immediate focus; reduced CSS removes transforms. |
| Share disclosure switch | Local thumb/colour feedback | CSSprefers-reduced-motion removes transition. Render snapshot/case changes cancel stale PNG download. |
| Menu/detail disclosure | Native open/closed | Escape returns focus to summary; no persistence coupling. |
| Globe | Static raster/labels, no continuous motion | No canvas/WebGL/RAF/observer or renderer lifecycle. Forms do not wait for the artwork. |
| Local PDF | Finite lazy PDF.js page render | Abort/destroy on generation change/unmount; local-open fallback; no outbound document URL. |

Native rapid tab sequence Requirements→Costs→Requirements→Sources→Overview ends with exactly one Overview panel; leaving removes that panel, with0canvas. Real keyboard/recovery focus and pending/retry states were tested separately. StrictMode remains enabled. DOManimation timeline, recording,OSreducedmotion,200%browserzoom and GPU/CPUprofiles are unavailable in the current permitted browser API; they were not simulated or claimed. Static code/unit checks do not replace those native gates.
