# Digital SAT preparation — Week 1 original learning draft

**Status: CONTENT DRAFT · REVIEW PENDING · NOT INTEGRATED.**

Draft version: `sat-week1-original-2026-10-11-v1`.

This is a small original learning pack for three skills: quadratic structure, data interpretation, and grammar/transitions. It extends the existing linear/proportion starters. The examples, passages, numbers, questions, choices and explanations were composed for this draft; no licensed or official test questions were copied. It is not an official test, a full SAT course, a validated diagnostic or evidence of score improvement. Results are formative **correct/total**, with no conversion to an official SAT score or admission probability.

All fifteen questions have one intended answer under the stated assumptions. Work is untimed; a learner may use scratch paper or a calculator for the mathematics. Exact arithmetic is sufficient. Each lesson includes learning notes, standalone worked examples and five practice questions. Instructor keys are collected at the end so the student section can be delivered without answer keys. Subscription delivery, UI/API content registration and persistence are not changed by this document.

## Five-day study plan

| Day | Work | Evidence to keep |
| --- | --- | --- |
| 1 · about 30 minutes | Read Lesson 1 and reproduce both worked examples without looking at the final steps. | Your own explanation of what factored and vertex forms reveal. |
| 2 · about 30 minutes | Complete Q1–Q5, then check the key. Read Lesson 2's notes and first example. | Mark each error as a sign, structure or arithmetic error; write a corrected line. |
| 3 · about 35 minutes | Finish Lesson 2's second example and D1–D5. | Name the statistic or inference each question actually permits. |
| 4 · about 35 minutes | Read Lesson 3, reproduce its examples and complete G1–G5. | Identify the subject, clause boundary or relationship before selecting a choice. |
| 5 · about 25 minutes | Rework missed items with the key hidden. Explain one rejected choice from each lesson aloud or in writing. | Keep the first-attempt total separate from the later review total. |

The minutes are suggestions, not a pace requirement. A useful review checkpoint is being able to justify the answer and reject a distractor; a raw total alone does not establish mastery. If a learner cannot explain a correct guess, revisit the worked example. A later attempt on these same items measures review of this pack, not performance on unseen questions.

---

## Lesson 1 — Read quadratic structure before calculating

Proposed lesson ID: `sat-quadratic-structure-1`.

### Learning goals

- Read real zeros from a factored expression.
- Read a vertex, opening direction and extreme value from vertex form.
- Rewrite a simple quadratic by completing the square.
- Recognize a repeated root without relying on trial-and-error substitution.

### What to know

A quadratic has a nonzero coefficient of the squared variable. Its form can make different information easy to see:

| Form | Information it exposes |
| --- | --- |
| `a(x − r)(x − s)` | Real zeros `r` and `s`, when this real factorization exists. A zero is an input where the output equals zero. |
| `a(x − h)² + k` | Vertex `(h, k)`. For `a > 0`, the minimum output is `k`; for `a < 0`, the maximum output is `k`. |
| `ax² + bx + c` | The output at `x = 0` is `c`. Expansion can help check whether two forms are equivalent. |

Here the domain is **all real numbers** unless a question restricts it. A real square is nonnegative, which is why a vertex-form extreme occurs when the squared expression equals zero. Notice that `x + 2` is `x − (−2)`; its vertex input is `−2`, not `2`. A negative leading coefficient changes a minimum into a maximum.

For a leading coefficient of one, complete the square by taking half the coefficient of `x`, squaring it, and balancing the added amount:

`x² + bx + c = (x + b/2)² + c − (b/2)²`.

These facts concern a mathematical function. They do not imply that a contextual input outside an allowed time, distance or count is meaningful.

### Worked example A — Two forms, two useful facts

For `f(x) = x² − 6x + 5`, find its zeros and its minimum value.

1. The numbers `−1` and `−5` multiply to `5` and add to `−6`, so `f(x) = (x − 1)(x − 5)`.
2. Either factor must equal zero for the product to be zero. The zeros are `1` and `5`.
3. Complete the square: `x² − 6x + 5 = (x − 3)² − 9 + 5 = (x − 3)² − 4`.
4. The smallest square is zero, achieved at `x = 3`. The minimum output is `−4`.
5. Check: `f(3) = 9 − 18 + 5 = −4`. The vertex lies midway between the two zeros, which agrees with `(1 + 5)/2 = 3`.

Factored form answered the zero question quickly; vertex form answered the extreme-value question quickly.

### Worked example B — A negative coefficient

For `g(x) = −3(x + 2)² + 7`, find the maximum output and the output at zero.

- Since `(x + 2)² ≥ 0`, multiplying it by `−3` produces a value no greater than zero. Therefore `g(x) ≤ 7`.
- Equality occurs at `x = −2`, so the maximum output is `7` and the vertex is `(−2, 7)`.
- At `x = 0`, `g(0) = −3(2)² + 7 = −12 + 7 = −5`.

**Common trap:** reading the vertex input as `2`, or calling `7` a minimum despite the negative coefficient.

### Practice — choose one answer for each item

**Q1 · `sat-qstruct-1-q1`**

The function `f(x) = (x − 4)² − 9` is defined for every real `x`. Which pair contains both real zeros of `f`?

- A. `−7` and `−1`
- B. `1` and `7`
- C. `3` and `9`
- D. `4` and `9`

**Q2 · `sat-qstruct-1-q2`**

For `g(x) = 2(x + 1)² + 5`, with real domain, which statement is true?

- A. The minimum output is `2`, at `x = −1`.
- B. The maximum output is `5`, at `x = −1`.
- C. The minimum output is `5`, at `x = 1`.
- D. The minimum output is `5`, at `x = −1`.

**Q3 · `sat-qstruct-1-q3`**

Which expression is equivalent to `x² + 10x + 21` for every real `x`?

- A. `(x + 5)² − 4`
- B. `(x + 5)² + 21`
- C. `(x + 10)² − 79`
- D. `(x − 5)² − 4`

**Q4 · `sat-qstruct-1-q4`**

The function `h(x) = −(x − 2)(x − 8)` is defined for every real `x`. What is its maximum output?

- A. `−9`
- B. `5`
- C. `9`
- D. `16`

**Q5 · `sat-qstruct-1-q5`**

For which value of the real constant `c` does `x² − 8x + c = 0` have exactly one distinct real solution?

- A. `8`
- B. `16`
- C. `−16`
- D. `64`

**Before checking:** Which questions require zeros, which require an extreme value, and which require equivalence? State what the form reveals before doing arithmetic.

---

## Lesson 2 — Interpret data without overstating it

Proposed lesson ID: `sat-data-interpretation-1`.

### Learning goals

- Distinguish arithmetic mean, median and range.
- Compute a combined mean using group sizes.
- Understand the effect of changing one observation on the mean.
- Separate an observed association from a causal conclusion.

### What to know

- **Arithmetic mean:** sum of all observations divided by the number of observations. Unless stated otherwise, each listed observation counts once.
- **Median:** middle observation after sorting; for an even count, average the two middle observations.
- **Range:** largest observation minus smallest observation. It is one measure of spread, not a complete description of the distribution.
- **Combined mean:** combine the group totals, then divide by the combined count. If groups have different counts, averaging their means directly is generally wrong.
- **One changed observation:** when the count remains `n` and the sum increases by `d`, the mean increases by `d/n`.
- **Association:** two recorded variables may move together. Observational data alone do not establish that changing one variable causes a change in the other; other variables or selection effects may explain the pattern.

All data below are invented for instruction. They are not learner outcomes, admissions evidence or official test results. Treat the stated observations and means as exact; no weighting, missing records or rounding is implied unless explicitly stated.

### Worked example A — The mean and median react differently

Five measurements, in units, are `10, 12, 12, 14, 22`.

1. Sum: `10 + 12 + 12 + 14 + 22 = 70`.
2. Mean: `70/5 = 14` units.
3. The list is already sorted. Its third observation is `12`, so the median is `12` units.
4. Range: `22 − 10 = 12` units.

If the `22`-unit observation is removed, the remaining sum is `48` and the remaining count is `4`. The new mean is `48/4 = 12` units. The middle observations are `12` and `12`, so the new median is still `12` units.

This particular high observation affected the mean more than the median. Do not generalize that removing an observation can never change a median; the result depends on the actual data.

### Worked example B — Combine totals, not just means

Group A has `24` observations with mean `16` units. Group B has `16` observations with mean `21` units. The groups do not overlap and contain every observation in the combined dataset.

- Group A total: `24 × 16 = 384` units.
- Group B total: `16 × 21 = 336` units.
- Combined total: `384 + 336 = 720` units.
- Combined count: `24 + 16 = 40`.
- Combined mean: `720/40 = 18` units.

The unweighted average of the two group means, `(16 + 21)/2 = 18.5`, is incorrect here because the groups are not the same size.

### Practice — choose one answer for each item

**D1 · `sat-data-1-q1`**

The five observations `6, 8, 8, 11, 17` are measured in the same units. What is the arithmetic mean minus the median?

- A. `0`
- B. `2`
- C. `3`
- D. `10`

**D2 · `sat-data-1-q2`**

A dataset contains exactly ten observations. One observation, `20`, is replaced with `50`; all other observations are unchanged. By how much does the arithmetic mean increase?

- A. `30`
- B. `5`
- C. `3`
- D. `2`

**D3 · `sat-data-1-q3`**

Group M has twelve observations with arithmetic mean `8`. Group N has eighteen observations with arithmetic mean `13`. The groups are disjoint, and their combined dataset consists of all thirty observations. What is the combined arithmetic mean?

- A. `10.5`
- B. `10`
- C. `11`
- D. `12`

**D4 · `sat-data-1-q4`**

A researcher recorded the following four observations. There was no random assignment and no controlled intervention.

| Preparation time, minutes | A separate measurement, units |
| --- | --- |
| 20 | 62 |
| 40 | 68 |
| 60 | 74 |
| 80 | 80 |

Which conclusion is supported by these observations alone?

- A. Increasing preparation time causes every person's measurement to rise.
- B. Preparation time and the recorded measurement have a positive association in these four observations.
- C. The same relationship must hold for every person outside the recorded group.
- D. Preparation time is the only variable that could affect the measurement.

**D5 · `sat-data-1-q5`**

Dataset A is `4, 6, 8, 10, 12`. Dataset B is `6, 7, 8, 9, 10`. Which statement is true?

- A. Dataset A has a larger mean and a smaller range than Dataset B.
- B. Dataset B has a larger mean and a larger range than Dataset A.
- C. The datasets have the same mean and the same range.
- D. The datasets have the same mean, and Dataset B has a smaller range.

**Before checking:** Write the count and sum for a mean question. For an inference question, distinguish what was observed from what would require a different study design.

---

## Lesson 3 — Use sentence structure and logical relationships

Proposed lesson ID: `sat-grammar-transitions-1`.

### Learning goals

- Match a verb to the head of its subject rather than to a nearby noun.
- Join two independent clauses without a comma splice.
- Choose a transition that expresses the actual relationship between ideas.
- Keep items in a series grammatically parallel.

### What to know

Use standard formal written English for these questions. The passages are short and original; only the supplied context is relevant. A transition is not correct merely because it sounds formal.

1. **Find the subject's head.** In “a collection of maps,” the head is singular “collection.” The plural noun inside the `of` phrase does not make the subject plural.
2. **Identify independent clauses.** A clause with a subject and a finite predicate that can stand as a sentence is independent. A comma alone cannot join two such clauses in standard formal writing. A semicolon can join closely related independent clauses. A period can also separate them if the next sentence begins appropriately. Other punctuation can be valid in other contexts; inspect the actual choices.
3. **Name the relationship before reading transitions.** Contrast: the second idea differs from an expectation. Result: the second idea follows from the first. Example: the second idea illustrates the first. Addition/similarity: the second supplies a compatible, related idea.
4. **Keep parallel structures.** In “how to measure, compare, and record,” a single `to` can apply to all three base-form verbs. Mixing a verb with an unrelated noun phrase or a complete clause breaks the series.

### Worked example A — Do not agree with the nearest noun

Draft: “A collection of maps **are** stored in the cabinet.”

- Subject head: `collection`, singular.
- Intervening phrase: `of maps`; it describes the collection.
- Corrected sentence: “A collection of maps **is** stored in the cabinet.”

Now compare: “The maps in the collection **are** stored in the cabinet.” The head is plural `maps`; `are` is correct. The words after the head describe it but do not control the agreement.

### Worked example B — A boundary and a relationship

Draft: “The trail is short, the ascent is steep.”

Both parts can stand independently. A comma alone creates a comma splice. One grammatical revision is: “The trail is short; the ascent is steep.” To make the contrast explicit across two sentences: “The trail is short. **However,** the ascent is steep.”

The contrast is between an apparently easy short trail and a demanding ascent. “Consequently” would claim that being short produces the steep ascent, which the supplied information does not support. The semicolon fixes the boundary; the transition explains the relationship.

### Worked example C — Parallel actions

Draft: “The guide explains how to label a sample, measuring its mass, and record its temperature.”

The series begins with `to label`. Revise all three actions into parallel base-form verbs: “The guide explains how to **label** a sample, **measure** its mass, and **record** its temperature.” The `to` is shared by the series.

### Practice — choose one answer for each item

**G1 · `sat-grammar-1-q1`**

Choose the completion that makes the sentence grammatically correct in standard formal written English.

“At the start of each session, the list of materials ___ on the workbench.”

- A. `are`
- B. `were`
- C. `is`
- D. `have been`

**G2 · `sat-grammar-1-q2`**

Choose the punctuation that correctly joins the two closely related independent clauses. Do not add or change any other words or capitalization.

“The sample was small ___ the team collected more observations before drawing a conclusion.”

- A. `,`
- B. `;`
- C. `, however,`
- D. no punctuation

**G3 · `sat-grammar-1-q3`**

“The archive's catalogue is described as a complete inventory of the collection. ___, several recently donated boxes remain unindexed.”

Which transition most logically completes the text?

- A. `For example`
- B. `However`
- C. `Consequently`
- D. `Similarly`

**G4 · `sat-grammar-1-q4`**

“The draft directions include two unnecessary turns that make the route harder to follow. ___, the editor removes those turns to make the directions simpler.”

Which transition most logically completes the text?

- A. `Consequently`
- B. `Nevertheless`
- C. `For instance`
- D. `In contrast`

**G5 · `sat-grammar-1-q5`**

Choose the completion that preserves a grammatically parallel series.

“The workshop teaches participants how to measure a sample, ___, and record the result.”

- A. `comparing its mass`
- B. `compare its mass`
- C. `its mass comparison`
- D. `the mass was compared`

**Before checking:** Underline the subject head in G1, mark both clause subjects and predicates in G2, name the relationship in G3–G4, and compare the verb forms in G5.

---

## Instructor answer key and explanations — reveal after an attempt

This section is part of the review draft, not a pre-attempt public question payload. If the pack is integrated later, keep correct choices and explanations separate from the public lesson response and reveal them through completed-attempt feedback. The identifiers above are proposed content identifiers; they are not currently registered lessons.

### Lesson 1 key

| Item | Key | Explanation and distractor check |
| --- | --- | --- |
| Q1 | **B** | Set `(x − 4)² = 9`, so `x − 4 = ±3` and `x = 1` or `7`. A reverses the shift; C and D do not make the output zero. |
| Q2 | **D** | `2(x + 1)²` is nonnegative and reaches zero at `x = −1`, giving a minimum output of `5`. A confuses the coefficient with the output; B calls the upward-opening function's minimum a maximum; C has the vertex-input sign wrong. |
| Q3 | **A** | `(x + 5)² − 4 = x² + 10x + 25 − 4 = x² + 10x + 21`. B gives constant `46`; C gives an `x` coefficient of `20`; D gives an `x` coefficient of `−10`. |
| Q4 | **C** | Expand and complete the square: `−(x − 2)(x − 8) = −x² + 10x − 16 = −(x − 5)² + 9`. The maximum output is `9`, at `x = 5`. A misses the outer negative; B is the maximizing input, not the output; D is not the vertex value. |
| Q5 | **B** | `x² − 8x + c = (x − 4)² + c − 16`. The equation is `(x − 4)² = 16 − c`. There is exactly one distinct real solution when the right side is zero, so `c = 16` and `x = 4`. For A and C the right side is positive and there are two distinct real solutions; for D it is negative and there are none. |

### Lesson 2 key

| Item | Key | Explanation and distractor check |
| --- | --- | --- |
| D1 | **B** | The sum is `50`, so the mean is `10`. The middle observation is `8`, so the median is `8`. The requested difference is `10 − 8 = 2`. D is the mean alone; A and C are not the difference. |
| D2 | **C** | The sum increases by `50 − 20 = 30` while the count remains `10`. The mean therefore increases by `30/10 = 3`. A is the change in the sum rather than in the mean; B and D use the wrong divisor or change. |
| D3 | **C** | Group totals are `12 × 8 = 96` and `18 × 13 = 234`. The combined mean is `(96 + 234)/(12 + 18) = 330/30 = 11`. A averages two unequal-sized groups without weighting; B and D do not match the combined total. |
| D4 | **B** | Across these four observations, higher preparation times appear with higher measurement values. That is a positive association in the recorded data. No random assignment or controlled intervention supports the causal claim in A, the universal generalization in C, or the exclusion of every other influence in D. |
| D5 | **D** | Both sums are `40`, so both means are `40/5 = 8`. A's range is `12 − 4 = 8`; B's range is `10 − 6 = 4`. B therefore has the smaller range. A and B wrongly claim different means; C wrongly claims equal ranges. |

### Lesson 3 key

| Item | Key | Explanation and distractor check |
| --- | --- | --- |
| G1 | **C** | The singular subject head is `list`, so `is` agrees. The plural `materials` belongs to the describing phrase `of materials`. A, B and D use plural verb forms. No choice of singular past tense is offered, so tense does not create a second valid answer. |
| G2 | **B** | Both “The sample was small” and “the team collected more observations before drawing a conclusion” are independent clauses. A semicolon joins them correctly. A is a comma splice; C is also a comma splice because `however` is not a coordinating conjunction; D is a fused sentence. The question restricts the edit to the listed choices; other properly constructed revisions could also work. |
| G3 | **B** | “Complete inventory” creates an expectation that every box is indexed, while “several … remain unindexed” contradicts that expectation. `However` signals this contrast. A suggests an illustration of completeness, C suggests a result of completeness, and D suggests similarity; none expresses the relationship supplied. |
| G4 | **A** | The unnecessary turns make the directions harder to follow; removing them is the stated response to that problem. `Consequently` connects the problem with the resulting action. B and D signal contrast, while C would introduce an example rather than the resulting edit. |
| G5 | **B** | `measure`, `compare`, and `record` are parallel base-form verbs sharing `how to`. A changes to an `-ing` form, C substitutes a noun phrase, and D substitutes a complete clause. |

## Review record and future integration boundary

- Original content draft: **prepared**. Mathematical/English peer review: **pending** at initial save; any later reviewer receipt should be linked separately without changing this into a course-launch claim.
- Pedagogical review by a qualified teacher, accessibility/content QA and learner testing: **not completed**.
- Native DTO/catalogue/version/answer validation, idempotent attempt storage, feedback release, progress/export/cascade controls and UI delivery for these new IDs: **not implemented or run by this draft task**.
- Keep original first-attempt answers and raw totals if integrated; do not overwrite official Academics scores. A repeated practice attempt, a week completed or a subscription does not establish an official score or admission eligibility.
- Any future mapping from a programme requirement to these lessons must retain exact requirement/claim scope, unknown/stale/optional/alternative states. This skill pack does not resolve those policy questions and does not supply an official requirement.
