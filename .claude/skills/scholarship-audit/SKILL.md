---
name: scholarship-audit
description: Audit a scholarship or financial-aid award to determine what it actually covers, who is eligible, and what remains to pay. Use when classifying funding, comparing awards, computing a funding gap, or whenever a page describes an award as a "full ride" or "fully funded".
---

# Scholarship and financial aid audit

Determine what an award *pays for*, from its published coverage — not from how
it describes itself.

## The rule that matters most

**A page saying "full ride" earns nothing.** Marketing language is evidence that
you should look harder, never evidence of coverage. Classify from a
per-cost-category table drawn from official sources.

## Classification

| Class | Requires |
|---|---|
| `FULL_RIDE_CONFIRMED` | Official confirmation of **tuition + mandatory fees + housing + meals** (or an equivalent living stipend) |
| `FULL_TUITION` | Tuition confirmed covered; living costs not fully covered |
| `LARGE_GRANT` | Substantial (≥50% of cost of attendance) but a meaningful part remains |
| `PARTIAL` | Covers a limited share |
| `NEED_BASED_POSSIBLE` | Size depends on a need assessment not yet filed — it cannot be sized |
| `NOT_ELIGIBLE` | Published conditions exclude this applicant |
| `UNKNOWN` | Insufficient official information, or sources conflict |

An unknown category is **not** a covered category. Missing meal-plan information
means `FULL_TUITION`, not `FULL_RIDE_CONFIRMED`.

## Audit checklist

- Exact name, and whether it exists for **this intake**
- Amount and currency, and **which academic year** the amount is published for
- Per-category coverage: tuition, mandatory fees, housing, meals, health insurance, books, travel, personal
- Open to international students? Any citizenship restriction? (an EEA-only award excludes most applicants)
- Restricted to particular programmes or campuses?
- Automatic, separate application, or nomination-only — a nomination-only award cannot be applied for directly
- Extra essays, and their word limits
- Its own deadline, with timezone — often **earlier** than the admission deadline
- Renewable or one-time; duration; renewal conditions
- Minimum test scores gating the award
- Whether it stacks with other awards
- Number offered — **only if officially published**

## The funding gap

```
gap = cost of attendance − confirmed aid − stackable confirmed aid
```

**Refuse to compute it** — and say why — when:

- the cost and the award are published for **different academic years**
- cost components come from different years
- the currencies cannot be converted with a rate you can cite
- the award's coverage omits categories the cost table includes
- the award has no officially published amount

A zero remaining cost is the most consequential number here. Show it only when
the figures genuinely describe the same year, the same currency and comparable
categories. Otherwise report *not computable* with the reason.

**Stacking needs consent from both sides.** An award stating "may not be
combined with other scholarships" blocks stacking even when another award offers
to stack.

Always show the source currency, the academic year, the date read, the source
URL, and the FX rate with its date if you converted.

## Language

"Confirmed" describes the opportunity to apply against published criteria. It
never describes the outcome. Every award decided competitively must say so.
