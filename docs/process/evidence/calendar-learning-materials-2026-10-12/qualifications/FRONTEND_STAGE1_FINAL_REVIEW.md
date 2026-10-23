# Frontend Stage 1 final read-only review

Source checkout: `/Users/wpalish/Documents/Codex/2026-09-28/files-mentioned-by-the-user-2026/work/unimatch-calendar-materials`.
Parent-supplied source ref: `914ee9e0` (Git state not queried in this review).
Review date: 2026-10-12.

## Findings disposition

1. **Stale calendar target buttons after a failed fresh read: closed in source.** In `frontend/src/screens/LearningSchedulePanel.tsx:45-57`, reloading clears preview and marks `readReady=false`. At lines 114-117, both exact lesson/attempt targets and receipt review buttons require `readReady` and the sidecar revision to match the parent revision. The preview button uses the same revision fence at line 129. If a sidecar GET returns a newer shared revision, lines 53-55 ask the parent to reload before targets become enabled. The focused test at `frontend/src/screens/LearningSchedulePanel.test.tsx:114-136` covers failed refresh and a newer shared revision. I found no remaining defect in this correction.

2. **“Outside recent twenty” fixture: closed.** `frontend/src/screens/PreparationScreen.learningPath.test.tsx:389-403` now creates twenty distinct attempt UUIDs, excludes the pinned UUID, sets `attempt_count=21`, opens the pinned review through its direct owned UUID, and confirms the visible twenty review controls do not contain that UUID. I found no remaining defect in this correction.

## File fingerprints

| File in source checkout | SHA-256 |
| --- | --- |
| `frontend/src/screens/LearningSchedulePanel.tsx` | `f61dbb1b548e983970ac6cb0d41269e01d806183897274699ecd752ccb633936` |
| `frontend/src/screens/LearningSchedulePanel.test.tsx` | `61616d52a03305eecbaf6b20c6c657b5b863b479142027207c7566b6b59ba07d` |
| `frontend/src/screens/PreparationScreen.learningPath.test.tsx` | `511043447c827e3b7b557ecd3409f941b6b13891057d768508af662a0612cb62` |

No new defects found in the reviewed corrections. This is source inspection only; the root's active runtime check has not been used as evidence here. No source file, Git state, test run, browser, provider or collector was changed or invoked by this review.
