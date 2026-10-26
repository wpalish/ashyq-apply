# Query-shape probe (v3-M5, ticket 07)

Provider: serper · requests sent: 30 of a 300 limit · 2026-10-18T12:13:47.247575+00:00

Rule: a shape with the gold (or a canonical variant / gold twin) in the top 10 on >= 4 of 6 cases joins the first pass; programmes -> reserve, admissions dropped.

Cell: rank of the first gold page (or variant / twin) in the top 10; — not in the top 10; err / n/a not answered; · not sent.

| case | a_today | b_alias_or | c_local | d_local_hl_gl | e_local_natural |
|---|---|---|---|---|---|
| uba | — | — | 2 | 2 | 6 |
| puc | — | — | 1 | 1 | 1 |
| uio | — | — | 1 | 1 | 1 |
| kuleuven | — | — | — | — | — |
| psaclay | — | — | — | 1 | — |
| ucph | 1 | 1 | 1 | 1 | 1 |
| **hits** | **1** | **1** | **4** ✓ | **5** ✓ | **4** ✓ |

Shapes joining the first pass: c_local, d_local_hl_gl, e_local_natural. Local-language shapes joining: c_local, d_local_hl_gl, e_local_natural. R5 exists: yes.

## Queries

| case | shape | query | hl/gl |
|---|---|---|---|
| uba | a_today | `site:uba.ar "computer science" "bachelor"` |  |
| uba | b_alias_or | `site:uba.ar ("computer science" OR "computing science" OR computing OR informatics) "bachelor"` |  |
| uba | c_local | `site:uba.ar "ciencias de la computación" licenciatura` |  |
| uba | d_local_hl_gl | `site:uba.ar "ciencias de la computación" licenciatura` | es/ar |
| uba | e_local_natural | `Universidad de Buenos Aires licenciatura ciencias de la computación` |  |
| puc | a_today | `site:uc.cl "computer science" "bachelor"` |  |
| puc | b_alias_or | `site:uc.cl ("computer science" OR "computing science" OR computing OR informatics) "bachelor"` |  |
| puc | c_local | `site:uc.cl "ciencia de la computación" licenciatura` |  |
| puc | d_local_hl_gl | `site:uc.cl "ciencia de la computación" licenciatura` | es/cl |
| puc | e_local_natural | `Pontificia Universidad Católica de Chile licenciatura ciencia de la computación` |  |
| uio | a_today | `site:uio.no "computer science" "bachelor"` |  |
| uio | b_alias_or | `site:uio.no ("computer science" OR "computing science" OR computing OR informatics) "bachelor"` |  |
| uio | c_local | `site:uio.no informatikk bachelor` |  |
| uio | d_local_hl_gl | `site:uio.no informatikk bachelor` | no/no |
| uio | e_local_natural | `Universitetet i Oslo bachelor informatikk` |  |
| kuleuven | a_today | `site:kuleuven.be "computer science" "bachelor"` |  |
| kuleuven | b_alias_or | `site:kuleuven.be ("computer science" OR "computing science" OR computing OR informatics) "bachelor"` |  |
| kuleuven | c_local | `site:kuleuven.be informatica bachelor` |  |
| kuleuven | d_local_hl_gl | `site:kuleuven.be informatica bachelor` | nl/be |
| kuleuven | e_local_natural | `KU Leuven bachelor informatica` |  |
| psaclay | a_today | `site:universite-paris-saclay.fr "computer science" "bachelor"` |  |
| psaclay | b_alias_or | `site:universite-paris-saclay.fr ("computer science" OR "computing science" OR computing OR informatics) "bachelor"` |  |
| psaclay | c_local | `site:universite-paris-saclay.fr informatique licence` |  |
| psaclay | d_local_hl_gl | `site:universite-paris-saclay.fr informatique licence` | fr/fr |
| psaclay | e_local_natural | `Université Paris-Saclay licence informatique` |  |
| ucph | a_today | `site:ku.dk "computer science" "bachelor"` |  |
| ucph | b_alias_or | `site:ku.dk ("computer science" OR "computing science" OR computing OR informatics) "bachelor"` |  |
| ucph | c_local | `site:ku.dk datalogi bachelor` |  |
| ucph | d_local_hl_gl | `site:ku.dk datalogi bachelor` | da/dk |
| ucph | e_local_natural | `Københavns Universitet bachelor datalogi` |  |
