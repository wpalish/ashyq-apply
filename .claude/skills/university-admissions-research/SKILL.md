---
name: university-admissions-research
description: Research and verify university admission requirements for an international applicant, with a source and a date behind every value. Use when checking entry requirements, deadlines, test policies, credential recognition or document lists for a specific programme and intake — and whenever a requirement must be trusted enough to act on.
---

# University admissions research

Establish what a programme *actually requires*, for a *specific intake*, from a
source you can point at. The failure mode this skill exists to prevent is a
confident answer drawn from an aggregator, a previous cycle, or a general page
that the programme overrides.

## Source hierarchy

Use the most specific source available. Never let a lower tier settle a
question a higher tier answers.

1. The programme page for **this intake**
2. The programme page (cycle unstated)
3. The university's international admissions page
4. The official application portal's instructions
5. The scholarship administrator's own page
6. Government or immigration sources (visas, post-study work)
7. A written reply from the admissions office

**Aggregators and rankings are discovery only.** They may tell you a university
exists. They may never tell you its requirements, deadlines, fees or
eligibility. If an aggregator is your only source for one of those, the answer
is "not verified", not the aggregator's number.

## Checklist per programme

Ask each of these, and record the source for each:

**Academic**
- Educational prerequisites and the recognised equivalent of the applicant's qualification
- Minimum GPA **and the scale it is published on**
- Required school subjects
- Whether a credential evaluation (WES, ECE, NARIC) is required

**Tests**
- SAT/ACT policy — required, optional, or blind. Test-optional is not the same as test-blind.
- Any published minimum score
- Superscoring policy
- English: overall minimum **and per-section minimums**, which are separate requirements
- Which test *variants* are accepted (IELTS Academic vs General Training vs UKVI)
- Validity window (usually two years) measured against the intake date

**Process**
- Portfolio, interview, audition or entrance examination
- Application fee and whether a waiver exists
- The deadline **with its timezone**, for this intake
- Whether the intake is open at all

## Rules

**Never convert a grade silently.** Record the original value, its scale, and
the scale the programme publishes. If they differ, that is
`NEEDS_OFFICIAL_CLARIFICATION` until a documented conversion is applied — and
the method and its source travel with the converted number.

**Per-section minimums are independent of the overall score.** An applicant with
IELTS 7.0 overall and 6.0 writing fails a 6.5 per-band requirement. Checking
only the overall band is the single most common error in this work.

**Absent data never eliminates a candidate.** A requirement you could not read
is a question. Only a *confirmed* published requirement that the applicant
*confirms* they miss is a barrier.

**When two official pages disagree, report both.** Prefer the more specific one,
say that you are preferring it, and draft the question for the admissions
office. Do not pick a winner quietly.

## Output shape

For every value, record: the value, the URL, a short excerpt proving it, the
programme and intake it applies to, and when you read it. A value without those
is a rumour.

State conclusions as: *formal requirements are met* / *the profile looks
competitive against published data* / *there is a confirmed opportunity to
apply* / *the decision depends on competitive selection* / *there is not enough
official data to say*. Never as a probability, and never as a promise.
