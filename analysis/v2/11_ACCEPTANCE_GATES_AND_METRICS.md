# ACCEPTANCE GATES AND METRICS

These are target product-quality gates. They do not replace repository CI.

Thresholds must be revisited after benchmark maturity, but they must never be weakened merely to declare success.

# Repository engineering gates

Always preserve:
- Ruff;
- format check;
- mypy;
- backend tests;
- coverage floor (do not reduce existing floor);
- PostgreSQL tests where relevant;
- frontend typecheck/lint/unit/build;
- required E2E;
- security/dependency checks;
- one Alembic head.

Use exact current commands from `AGENTS.md`/CI, not copied stale commands.

# Discovery gates

Aspirational production target on held-out validation:

```text
exact programme-page recall       >= 95%
exact programme-page precision    >= 99%
```

Also report:
- recall@5;
- recall@10;
- recall@20;
- no-result rate.

Do not obscure subgroup failures behind aggregate average.

Break down by:
- country;
- site type;
- language;
- JS/static;
- PDF-heavy;
- faculty subdomain.

# Claim gates

For decision-grade fields:

```text
claim precision               >= 99%
unsupported claim rate        < 0.5%
wrong-scope claim rate        < 1%
```

Claim recall/coverage must be reported separately.

Critical evidence with no source/excerpt:
`0 tolerated`.

# Scholarship gates

```text
applicability precision       >= 98%
coverage precision            >= 98%
```

Recall must also be reported. High precision with nearly all UNKNOWN is not enough.

# Freshness gates

- expired/stale evidence is visibly marked;
- critical stale evidence does not silently support a current hard decision;
- change history preserved;
- recheck scheduler functioning.

# Privacy gates

- no unnecessary applicant PII in public search queries;
- external provider payloads comply with data-class policy;
- secrets absent from repository/logs;
- provider usage auditable.

# Latency/cost gates

Track at least:

```text
P50 first useful result
P95 first useful result
P50 complete result
P95 complete result

cost per university researched
cost per verified programme
browser fallback rate
cache hit rate
human review rate
```

Do not choose an AI component only on quality if latency/cost makes it impractical.

# AI/Jev promotion gates

Every component requires:
- baseline;
- labelled dev set;
- held-out set;
- error analysis;
- threshold;
- cost;
- latency;
- fallback;
- versioning.

Promotion is prohibited if:
- false-positive consequence is higher and precision falls;
- benchmark is provider-produced only;
- there is no held-out ASHYQ dataset;
- provider outage causes incorrect acceptance instead of graceful fallback.

# Beta readiness

A private/counselor beta may launch before all aspirational production thresholds if:

- limitation is explicit;
- no unsupported decision-grade claim reaches users;
- review coverage is sufficient;
- evidence can be inspected;
- exact programme discovery is already meaningfully reliable for the supported subset.

Use a supported-university/country scope if necessary rather than pretending global reliability.

# Global-production readiness

Do not label the product globally reliable until:
- 100+ university validation exists;
- multiple countries/site architectures are covered;
- quality gates are stable over repeated live recrawls;
- freshness/change operations work;
- security/privacy review is complete;
- operational observability exists;
- human-review load is economically manageable.
