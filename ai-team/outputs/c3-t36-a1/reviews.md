# T36 A1 (+repair R1) — Reviews (both on frozen candidate f9c90bf90f057d35c6ef72fcf70bdd14afc8bd80)

## Reviewer (agent_307cd666-ba71-45dc-af5f-634d39dfacd9) — VERDICT: PASS

ACCEPTANCE_MAP: все пункты PROVEN (RED реальный «assert 401 == 429»; hops[-1] main.py:162-167 — единственная точка XFF-обработки в app/, все группы лимитеров делегируют; nginx append подтверждён nginx.conf:34; compose expose-only, awk gate дважды офлайн-валидирован; API_PORT — 0 ссылок; существующие 24 security-теста побайтово стабильны, все XFF-использования single-hop). Полный suite/cov — NOT_RUN (пакет ограничил gates a-e) → интегратору.

REPAIR_HISTORY_ASSESSMENT: честно и минимально — A1 VERIFIED_FAIL записан (L45 двойной /api/api), R1 ровно +1/−1, полная повторная верификация; 6-probe инвентарь независимо подтверждён против реальных префиксов роутеров; «QA верифицирует свой фикс» утечек нет.

SCRIPT_GATE_RULING: область awk корректна (api-блок, post-interpolation); строжесть к loopback ПРИНЯТА (fail-closed release gate, закомментированный вариант = ad-hoc debug); URI-семантика проб корректна (proxy_pass без URI-части); fail-on-503 корректен.

Nonblocking: awk слеп к host-remap (защищено статическим QA-тестом для закоммиченного файла); nginx.conf append-семантика load-bearing — предложить статический guard; uvicorn --forwarded-allow-ips=* (Dockerfile:56, fly.toml) — передано security (F1).

## Security (agent_b90a566c-2543-4459-99cc-19eb7e654a97) — VERDICT: PASS

SPOOF_POST_FIX: nginx.conf:34 ровно $proxy_add_x_forwarded_for (append socket peer в КОНЕЦ, emit ровно ONE header) → через опубликованный путь hops[-1] всегда реальный клиент; multi-header/folded XFF нормализуются nginx — инъекция возможна только ЛЕВЕЕ appended peer. Fallback peer fail-safe.

INTERNAL_NETWORK_THREAT_MODEL: compose-сеть = доверенная зена (однотенантный оператор; peers уже держат DB-credentials) — ACCEPTED-RESIDUAL Low; лимитер — abuse-щит, не authz; SSRF-пивота нет (Fetcher блокирует внутренние адреса).

TRUST_DEFAULT_RULING: default False (config.py:110) — безопасный дефолт; compose явно true и теперь когерентен с expose-only. НО: F1 — shipped Dockerfile CMD (--proxy-headers --forwarded-allow-ips "*") на уровне uvicorn перезаписывает scope["client"] на FIRST hop: латентно для deploy образа напрямую с trust=False (request.client consumer один — fallback; TestClient не гоняет uvicorn middleware).

EXPOSURE_POST_FIX: единственная внешняя публикация web 8080; /docs /openapi /redoc НЕ под /api/ → nginx отдаёт SPA (docs не публичны); /metrics root 404 + bearer; ${API_PORT} 0 ссылок; override-file same-port ловится gate; host-remap и network_mode:host — слепые зоны (F2, P3, требуют незакоммиченных правок).

NEW_FINDINGS: F1 P2 pre-existing (uvicorn forwarded-allow-ips="*" в Dockerfile:56 + fly.toml:34 — отдельная задача с Dockerfile в scope); F2 P3 awk-tightening (fail на ЛЮБОЙ published в api-блоке + запрет network_mode); F3 P3 (совпадает с T33-F4: retry/recheck/collect-documents не гейтяся — backlog); F4 Low internal-XFF/two-proxy (принято карточкой).

Required extra tests (QA, synthetic): real-nginx spoof matrix; duplicate XFF lines; первый живой docker-прогон verify_compose.sh (владелец); F1-репро; awk негативные фикстуры. Guards not weakened: TestAbuseLimits нетронуты, пороги неизменны, nginx.conf нетронут.
