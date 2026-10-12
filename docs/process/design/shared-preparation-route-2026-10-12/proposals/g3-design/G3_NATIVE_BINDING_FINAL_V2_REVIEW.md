# G3 native binding final-v2 peer close-out

2026-10-12 · **READ ONLY / DESIGN ONLY / NOT APPLIED / NOT RUN**

Reviewed sealed `G3_NATIVE_BINDING_ADDENDUM_FINAL_V2.md` SHA-256 `0c15b69b2cdb9347a1f30501822aeff4cf913f3e12d08635bdd1d30a7b525474` and receipt SHA-256 `3fca6f1c32799611ca4bef624b0fa7a18eebc117c5542f2846790f28fab840f4` against the original addendum `d38e1fa08697f866a22ebf59a20046608eddc79865286874851f79542840a72c` and independent review `5c53608b06923f528af469d977e2b6f127aa1d2c9da98935c44b8ec672ec6605`. The exact diff changes only the title, explanatory delta, proof/reference field list and matching future control.

**Disposition: clarification closed in design.** Native `DocumentItem.source_url` now participates in proof/reference identity with absent/present and exact recorded-value distinction, while remaining outside item semantics. Thus URL-only changes map to `proof_changed_item_same` without a source fetch, portal verification or applicability claim. This matches accepted G3 V2 §4 and the native field. The selector, 20 G3 + 20 G2 reference bounds, role-specific reads, exact Today navigation and prior privacy/owner contracts are unchanged. Original sealed files remain intact. This is no G3 implementation or runtime acceptance.
