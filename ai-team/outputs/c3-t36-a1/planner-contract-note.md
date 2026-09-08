# T36 — Planner contract record (process deviation note)

- Planner invocation: NOT conducted as a separate subagent call for T36.
- Contract source: frozen verbatim by the owner-supplied master card §5-T36 (ai-team/reference/MASTER_C3_PROMPT_RU.md, «T36 — Доверенный прокси: последний hop + непубликованный API-порт»), which specified: last-hop XFF semantics (hops[-1], optional trusted_proxy_hops generalization with last-hop default), compose api ports→expose (+ commented loopback variant), verify_compose.sh no-8099-publication check, RED tests A/B/C + 2 compose tests.
- QA authoring, developer implementation, QA verification (incl. honest VERIFIED_FAIL → repair R1 → re-verify), reviewer and security reviews were all separate independent invocations (refs in acceptance-packet.json).
- Deviation recorded in ledger campaign_c3.process_deviations; integrator flagged it (non-blocking). No retro-planner assigned: the implemented contract matches the owner card exactly (no scope drift), and security review performed the adversarial analysis a planner would have contributed (multi-header XFF, internal-network threat model, trust default, exposure sweep).
