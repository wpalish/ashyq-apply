# Bounded model as programme-page picker

Type: grilling
Status: open
Blocked by: 01
Map: ../map.md · HITL — a scope decision with a cost dimension (brief D5, D9).

## Question

Brief D5 makes the AI a *researcher*: it may find pages and extract quoted claims, never a number in the
ranking. A bounded model that reads the sitemap's kept URLs, the catalogue's link texts or the provider's
result titles and *proposes* the programme URL — which the classifier then reads and accepts or refuses
exactly as today — is allowed by D5 and would sidestep every lexicon problem the research found (local
titles, opaque URLs, subject-title shapes). It is also a paid call per university in production, D9 requires
a zero-retention provider and `UNIMATCH_LLM_DATA_POLICY_ACK`, and only public institution/field/degree text
may be sent (I3). Is it inside this design?

❓ **Q1** - **Out of this map, for now.** Rules first: the research tickets name five mechanical defects and
gaps (search skipped, keep() gate, lexicon, identity gate, twin not recorded) that cost nothing per call and
can be measured in the loop within days. A model picker is a separate, priced experiment (`app/adapters/
decisions`, typesafe provider) after those land, and it would be measured against the same gold.

➡️ Yes — out for now; revisit when the rule set plateaus on dev4, with a cost per university and a paired run.

---

❓ **Q2** - If **in**, the only acceptable shape is a *proposer*, never an accepter: the model ranks
candidates it is shown (public URLs and link texts only), the classifier confirms, and a model proposal that
the classifier refuses is reported as `unresolved`, never as the programme page.

➡️ Yes — this is the only shape that keeps "never a guess".
