# Owned synthetic journey browser checks

The before snapshot is863a9c64/6cf5c04b; initial core snapshot d6a727aa/f14eb5f8; integrated12path snapshot45bcc99a/4148fb4f. The latter contains all route/filter/choice changes and Documents ordering; Compare2 was applied afterward and requires its separate final-source UI check. Private competitor/account data and SQLite files are excluded. API/worker/Vite operated only on cloned owned synthetic demo data with provider none/auth false/browser tier false. Original source manifests, process receipts, app logs and screenshots are retained.

Observed routes and outcomes:

- Documents with20fixture results/no checklist exposes24 recorded dates/ICS. Initial new core screen still placed Choose after24calendar rows (08desktop/09mobile390x844); corrected integrated view shows working Choose first (10desktop/11mobile).
- Mobile Choose enters Find. Search Groningen + Netherlands filters remain visible outside closed Filters (12); removing Country leaves Search. Normal Save yields Saved; Plan labels Considering(1) with explicit applicant-choice disclaimer (13).
- Successful demo collect enters Documents, shows pending research, then returns5saved fixture checklist items ordered by role/lead time. Academic-reference tick persists across reload (14,DOM); this verifies this browser convenience only, not cloud sync/admission readiness.
- Home after collection offers Open documents and explains checklist is not an application-ready assessment. Plan after reload retains Considering(1), source-supported unknowns and Open collected checklists (15,DOM).
- Saved-tab/card toggle removes the saved programme from the filtered list; Clear all restores20results with Save available. Normal Save restored Considering before final preview clone.

One CUA selector expected exact Plan after Save; desktop button actually carries count Plan1. Fresh DOM established that label and the corrected control succeeded. This is a browser automation selector correction, not a failed application flow. The first reload snapshot caught Connecting securely; explicit heading wait verified hydration before accepting persistence.

Failure/stale/partial/wrong-result-ID states are covered by native targeted tests and independent static review, not injected into this runtime. API collection refusal was not triggered in browser; its true/false navigation contract is covered by store/screen controls. Signed-in production, another device, semantic keyboard walkthrough, WCAG compliance, actual university facts and comparative user completion times remain unmeasured. Before screenshots05/06 with the Explore overlay and competitor screenshot02 intro are not treated as accepted normal journey screens.
