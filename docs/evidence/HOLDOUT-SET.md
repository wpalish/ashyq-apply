# Holdout set — fixed 2026-08-29, before any classifier or crawler change

Six universities, six countries, six content-management systems, none of them
in the main canary registry and none of them looked at before this file was
committed. Two do not publish in English as their primary language.

| Institution | Country | Domain | Why it is here |
|---|---|---|---|
| Trinity College Dublin | Ireland | `tcd.ie` | `ac`-less Irish domain, long-lived bespoke CMS |
| Uppsala University | Sweden | `uu.se` | Swedish-primary site with an `/en/` tree |
| University of Auckland | New Zealand | `auckland.ac.nz` | `.ac.nz` multi-part suffix, `.html` page extensions |
| University of Cape Town | South Africa | `uct.ac.za` | `.ac.za` multi-part suffix, faculty-devolved site |
| Tecnológico de Monterrey | Mexico | `tec.mx` | Spanish-primary, private university, marketing-led CMS |
| University of Tokyo | Japan | `u-tokyo.ac.jp` | `.ac.jp` multi-part suffix, Japanese-primary |

## The rule this file exists to enforce

This list is **frozen**. If a site here turns out to be hard, it stays. It is
not replaced with an easier one, and the denominator stays at six. A holdout
chosen after seeing the result measures nothing.

Selected before: any change to `page_classifier.py`, `live_discovery.py`, or
the crawler. Committed in the same commit as the file itself.
