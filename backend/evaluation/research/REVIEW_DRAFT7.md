# Draft7: the owner's first human review of the corpus

Source annotations accessed 2026-09-23. **0/10 human verified** — see "What is
still missing" below, because this draft is the first one where that number is
misleading if read alone.

**62/220 known/total labels**, **10/10 programme identities**. Two cases change:
Aalto and HKU. Everything else is untouched, as are all frozen datasets, the
capture and the production tree.

## What the owner found

The owner reviewed draft6 and returned two corrections and an approval of the
other eight cases. Both corrections were checked against the primary sources
and both are right. This is the first time the corpus has been changed by a
human reading rather than by AI annotation.

### Aalto: the wrong programme, not a wrong fact

Draft6 recorded the Finnish-language [tietotekniikka programme](https://www.aalto.fi/fi/koulutustarjonta/tietotekniikka-tekniikan-kandidaatti-ja-diplomi-insinoori)
with `teaching_language.primary = "Finnish"`. That page is real and that fact is
true of it. It is still the wrong answer, because the requested scope is an
international bachelor applicant and that route is not available to one in
English.

The English-taught route is the [Aalto Bachelor's Programme in Science and
Technology, Computer Engineering major](https://www.aalto.fi/en/study-options/computer-engineering-bachelor-of-science-and-master-of-science-technology),
heading "Computer Engineering, Bachelor of Science and Master of Science
(Technology)". Aalto states it is the only bachelor route in science and
technology taught entirely in English. Identity and teaching language move
there; the Finnish programme stays the separate thing it is.

**This draft does not claim that Computer Engineering is the requested computer
science.** Aalto describes the major as combining information technology and
electrical engineering, and draft2 already refused exactly this equivalence move
for Data Science. What is recorded is that an English-taught bachelor route
exists. Whether it satisfies a computer-science request is an open question in
the worksheet, and a reviewer may legitimately send this case back to `unknown`.

Also read on that page but **not** recorded: €12 000 per year for non-EU/EEA
students and an application period of 7–22 January 2027. Neither is scoped to
the requested fall 2027 intake by the page itself, so both stay UNKNOWN under
the rule every draft since draft2 has followed.

### HKU: a missing faculty and an approximate title

The owner supplied "School of Computing and Data Science", and the admissions
page confirms it. The page also shows the degree is titled **Bachelor of
Engineering in Computer Science**, not a bare "Computer Science" programme, and
that the same school offers two other degrees — Artificial Intelligence and Data
Science, and Applied Artificial Intelligence — which are not this one.

New label `programme.faculty`; the recorded programme title is tightened.

## Replay

```sh
# From backend
python -m evaluation.research --dataset evaluation/research/data/ground_truth.draft7.json --capture evaluation/research/baseline/capture.json --out evaluation/research/baseline/metrics.draft7.json --allow-drafts
```

Programme precision **1/9** and recall **1/10** are unchanged: moving Aalto's
ground-truth URL neither gained nor lost a match against the frozen capture.
Claim recall moves 0/61 to 0/62 for the one new label. Everything else is
identical to draft6. As always this is an annotation change, not a pipeline run.

## What is still missing

`review.status` is `draft` for all ten cases and the strict scorer still refuses
the corpus. That is **not** because the owner has not reviewed it — they have.
It is because `schema.py` requires a reviewer name and a date before a case may
be `human_verified`, and no AI may invent either. Supply a name and a date and
eight cases can be marked immediately; Aalto needs the Computer Engineering
question answered first, and HKU's new labels want a second look since they were
authored from the review itself.

Remaining source gaps are unchanged: the Kazakhstan fall-2027 intake, fees, and
the general SAT/IELTS policy for the cases still holding them UNKNOWN.
