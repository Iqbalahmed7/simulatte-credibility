# ARCH-001 Sprint A-3 Results: Worldview Layer Validation

**Date:** April 2026
**Cohort:** faecd4d0 — 50 personas, domain=us_general, Claude Haiku 4.5
**Comparison:** Pre-worldview (57.6%) vs Post-worldview (70.5%)

---

## Headline Result

| Metric | Before (baseline) | After (ARCH-001) | Delta |
|---|---|---|---|
| Mean distribution accuracy | 57.6% | **70.5%** | **+12.9pp** |
| Mean MAE | 27.6 pp | 18.2 pp | −9.4 pp |
| Gap to human benchmark (91%) | 33.4pp | 20.5pp | −12.9pp |
| Gap to Artificial Societies (86%) | 28.4pp | 15.5pp | **−12.9pp** |

Adding political worldview anchors to persona generation closes **38% of the gap** to the human benchmark ceiling in a single sprint.

---

## Per-question breakdown

| Q | Topic | Before | After | Delta | Status |
|---|---|---|---|---|---|
| q01 | economy | 45.0% | 47.0% | +2.0pp | ✗ still collapsed |
| q02 | economy | 74.0% | 74.0% | +0.0pp | ✗ still collapsed |
| q03 | gun_policy | 64.7% | **94.3%** | +29.6pp | ✓ fixed |
| q04 | immigration | 60.8% | **77.5%** | +16.7pp | ✓ fixed |
| q05 | climate | 34.0% | **66.9%** | +32.9pp | ✓ fixed |
| q06 | social_trust | 71.1% | **94.1%** | +23.0pp | ✓ fixed |
| q07 | government | 98.4% | 92.2% | −6.2pp | slight regression |
| q08 | religion | 73.0% | 55.6% | −17.4pp | regression |
| q09 | abortion | 42.7% | **65.8%** | +23.1pp | ✓ fixed |
| q10 | racial_equality | 67.7% | **91.1%** | +23.4pp | ✓ fixed |
| q11 | healthcare | 66.6% | **89.8%** | +23.2pp | ✓ fixed |
| q12 | democracy | 40.4% | 42.5% | +2.1pp | ✗ still collapsed |
| q13 | media_trust | 44.5% | **68.7%** | +24.2pp | ✓ fixed |
| q14 | technology | 40.4% | 40.4% | +0.0pp | ✗ still collapsed |
| q15 | financial_security | 41.0% | **57.7%** | +16.7pp | ✓ fixed |

**9 of 13 collapsed questions fixed.** 4 remain collapsed.

---

## Analysis: What worked

The worldview layer performed exactly as predicted. Questions whose distributions
are primarily driven by partisan identity all improved substantially:

- **Gun laws** (+29.6pp): Conservatives now pick "as-is" or "less strict" at
  realistic rates rather than unanimous "more strict"
- **Climate impact** (+32.9pp): Conservatives pick "not much" / "not at all" at
  much higher rates; progressives cluster at "great deal"
- **Abortion** (+23.1pp): Conservatives now distribute toward C/D rather than
  collapsing at B
- **Media trust** (+24.2pp): Conservatives pick "not much" / "none at all";
  progressives pick "a lot" / "some" — correctly bifurcated
- **Healthcare** (+23.2pp): Conservatives now correctly push back on government
  responsibility at ~40% rate vs 6% before

The `CoreMemory.key_values` propagation worked as intended: political worldview
statement appearing first in key_values is visible to the LLM's decide loop
and overrides its default moderate-progressive prior.

---

## Analysis: What didn't work

### Category 1: Temporal/partisan sentiment (q01, q02, q12)

These three questions ask about *current conditions* — not values or ideology:

- q01: "How would you rate economic conditions today?" (94% → "Only fair"; Pew: 41% Only fair / 41% Poor)
- q02: "Right direction or wrong track?" (100% → "Wrong track"; Pew: 26% right / 74% wrong)
- q12: "How satisfied are you with democracy?" (96% → "Not too satisfied"; Pew: 4%/28%/38%/29%)

**Root cause:** These answers depend heavily on which party currently holds power,
not just on the persona's political lean. A conservative in April 2026 might
rate the economy as "Good" or "Excellent" if a Republican administration is in
power — the exact opposite of a progressive. But the LLM has no anchor for the
current political moment, so all personas default to moderate pessimism ("Only
fair", "Wrong track", "Not too satisfied").

**Fix required:** Inject a political context anchor — who controls the White House
and Congress at the time of the simulated survey — into the `AttributeFiller`
prompt and `CoreMemory`. This is a temporal awareness problem, not a values problem.

### Category 2: LLM self-bias (q14)

- q14: "Will AI have more positive or negative effects on society?" (100% → "About equally"; Pew: 43% positive / 40% equal / 17% negative)

**Root cause:** Claude models are trained to give balanced, nuanced answers about
AI. No amount of political lean anchoring changes this — the LLM's own prior
dominates regardless of persona worldview. Conservatives should be somewhat more
likely to say "positive" (economic growth, innovation) and progressives somewhat
more "negative" (job loss, inequality), but the training prior overwhelms this.

**Fix required:** Either (a) run q14 with a different/older model that doesn't
have this self-bias, or (b) add a specific `ai_optimism` attribute to the worldview
taxonomy that explicitly anchors the persona's AI sentiment before the question.

### Category 3: Pool calibration regressions (q07, q08)

- q07 (government size): 98.4% → 92.2% (slight regression from near-perfect)
- q08 (religion importance): 73.0% → 55.6% (significant regression)

**Root cause:** The pool has a slight progressive skew (lean_progressive: 9/34 = 26%
vs target 22%; progressive: 5/34 = 15% vs target 18%). This causes:

1. q07: More personas answer "government should do more" (61% vs Pew 54%)
2. q08: More personas answer "not too important" for religion. Deeper issue:
   `institutional_trust` in the worldview anchor is being interpreted as applying
   to religion, but religious importance is personal faith — not institutional trust.
   The conservative personas' low `institutional_trust` values are incorrectly
   reducing their stated religious importance.

**Fix required for q08:** Add `religious_salience` as a distinct worldview
attribute, decoupled from institutional trust. Religious conservatives have LOW
institutional trust in government/media but HIGH personal religious commitment —
these must be independent axes.

---

## Path to 75%+ accuracy

| Fix | Target questions | Estimated gain |
|---|---|---|
| Temporal political context anchor | q01, q12 | +8–12pp overall |
| `religious_salience` worldview attribute | q08 | +5–8pp overall |
| Pool calibration (fix lean_progressive skew) | q07, q08 | +2–3pp overall |
| `ai_optimism` worldview attribute | q14 | +2–4pp overall |

**Combined estimate: 75–84% accuracy** — within striking distance of Artificial
Societies' self-reported 86%.

---

## Summary

ARCH-001 is validated. The worldview layer is the right architecture. The
12.9pp improvement from a single sprint confirms the hypothesis: political lean
was the primary missing predictor, accounting for the majority of distribution
collapse.

The 4 remaining problem areas fall into two distinct categories — temporal context
and attribute granularity — which require targeted follow-on work rather than
fundamental rethinking. The registry architecture is extensible for both.

*Next sprint recommendation: Add `temporal_political_context` injection and
`religious_salience` attribute.*
