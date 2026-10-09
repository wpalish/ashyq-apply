# DRAFT — security documentation reconciliation proposal

Written before proposed document edits on 2026-10-09. Parent is the only repository/Git writer.

Scope: externally propose at most SECURITY.md, docs/legal/RELEASE_READINESS.md and docs/legal/PRIVACY_POLICY_RU.md. Preserve historical content, public policy version, DRAFT status and operator placeholders. Read exact current applied source, operator metadata and saved acceptance receipts only. Source checkpoint c7b41fcf42c2fb84e877a8cb8b1349eedb79941f includes the authorized-case recovery accepted from B748c/A509f; current recovery core/full/browser remain pending at proposal preparation. No claim of public security, production, legal or quality readiness.

The predecessor c976074b had SECURITY.md but no RELEASE_READINESS.md; the latter is new legal preparation, not an overwritten predecessor policy. The first security full on a0fc was reported FAILED 12/13 due to same-owner recovery; retain it as historical evidence rather than a current successful gate. Parent will add actual current closure independently.

Method: pin current documents/source and immutable STOP; inspect source control boundaries; make minimal document copies and a unified diff; validate source/current/STOP unchanged and local proposed links. No tests, application/evaluation imports, subprocess application execution, database, ports, browser, provider, model, network, labels, scoring, Git writes or operational changes. Reports distinguish applied source controls from focused proof and pending full/browser/deployment.

No publication is authorized by this proposal. All three documents remain DRAFT. Root applies exact reviewed bytes only after its native/UI closure.
