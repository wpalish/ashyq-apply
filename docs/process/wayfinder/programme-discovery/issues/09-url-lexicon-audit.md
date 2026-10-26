# URL lexicon audit against every development gold programme URL

Type: research
Status: resolved
Blocked by: —
Map: ../map.md · AFK — resolved 2026-10-18 by claude-opus-5, offline in the backend venv.

## Question

The sitemap stage keeps a URL only through `keep()` (`categorise_url` + `matches_field` + `matches_degree`,
`live_discovery.py` L2491–2520), and the navigation fallback and prefilter reuse the same predicates. Which of
the 39 development gold programme URLs would the sitemap stage keep at all, and which would it drop although
the URL names the subject or the level? What does the dormant LX-1 lexicon change?

## Answer

Script: `scratchpad/wf_tools/url_audit.py` (run with `backend/.venv/bin/python`; reads the three gold files;
request bachelor / "computer science"). Columns: category and structural score (`score_url` PROGRAM_PAGE),
field bonus (`matches_field`), degree bonus (`matches_degree`), level named, excluded, `classify_url`.

**Kept by `keep()`: 20 of 39** (all as `program_page`): groningen ×2, delft, ubc, toronto, hku, ntu ×2, ethz,
uppsala, tcd, imperial ×2, unsw, auckland (BSc page, score 15), ucph ×2 (Danish 9, English 29), puc (15),
uio (4), chula (math.sc).

**Dropped although the slug names the subject (7, six of them also the level):**

| case | gold URL | field | degree | structural | why dropped |
|---|---|---|---|---|---|
| uba | `ingresantes.exactas.uba.ar/licenciatura-en-ciencias-de-la-computacion/` | 16 | +4 | 0 | no `/programmes|bachelors|study…/` segment |
| um ×4 | `study.um.edu.my/bachelor-of-computer-science-<spec>` | 16 | +4 | 0 | root-level slug; "bachelor" inside the slug is not a path segment the signal table knows |
| vienna | `aufnahmeverfahren.univie.ac.at/en/computer-science` | 16 | 0 | 0 | admissions host, bare field slug |
| psaclay | `…/formation/licence/informatique` | 8 (LI-1 alias) | +4 (`licence`) | 0 | `formation` is not a programme signal (`_LOCALIZED_PROGRAM_SIGNALS` has `opleidingen`, `studienangebot`, … but not `formation`) |

`keep()` returns `False` the moment `categorise_url` yields `None`, *before* the field and degree bonuses are
added (L2492–2494), so 20 points of subject+level evidence are discarded on a URL whose only "flaw" is a
missing structural word. This is the decision in
[Sitemap keep rule: evidence sum or structure first](18-keep-rule-evidence-sum.md).

**Zero by construction (opaque or shape-less), 9:** kaist `content?menu=188`, kuleuven `SC_51016742.htm`,
tsinghua `Divisions1.htm`, ub `fitxaInfe.jsp?…`, auckland plan `plan?p7_code=COMP-BSc`, chula ISE
`/academics/ice`, warsaw ×3 (`programmes-all/IN/S1-INF`: `programmes-all` is not matched by the
`/programmes?/` signal, so Warsaw is found by the walker, never by the sitemap), aalto (`/en/study-options/…`:
no signal; found by seeds), iitd (`/b-tech-program/`: scores 5 as a *catalogue* because of "program", total 0
without a degree word).

**With LX-1 (`page_classifier.LEXICON_V2 = True`):** puc 15 → 23, uio 4 → 12, ucph-da 9 → 17, iitd kept (as
catalogue, 4); psaclay-fr and uba still 0 (the structural gate, not the lexicon). 21 of 39 kept.

**Other findings for the design:**

- `matches_field` scores each field *word* as a substring (`"science" in path` → +8), so
  `natural-sciences`, `mathematics-computer-science` and fee tables outrank `computing-beng` (Imperial, rank
  35/40); SR-1 (`FIELD_SLUG_SCORING`, off) fixes exactly this and was rejected for an unrelated extraction
  claim (LOOP_REPORT cycle 3f).
- `names_other_degree_level` correctly refuses none of the 39 gold URLs; `_url_excluded` excludes none.
- Nothing in the URL layer knows a catalogue entry in an admission system (`irk.uw.edu.pl/pl/offer/…/programme/S1-INF/`,
  `onderwijsaanbod.kuleuven.be/opleidingen/n/…`): both are `None`, although `opleidingen` is a localized
  signal — the signal needs a following slug word and `n/SC_…` is not one.

### Sources

- `backend/app/adapters/discovery/live_discovery.py`: `keep()` L2491–2520, `score_url` L1023–1040,
  `_URL_SIGNALS`/`_LOCALIZED_PROGRAM_SIGNALS` L440–520, `matches_field` L1117–1145, `_field_slug_bonus` L1146,
  `degree_level_named` L1233–1290, `_url_excluded` L631–640.
- Script and raw output: `scratchpad/wf_tools/url_audit.py`, `scratchpad/wf_tools/lx1_url.py`.
