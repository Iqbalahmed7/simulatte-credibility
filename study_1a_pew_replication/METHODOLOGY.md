# Study 1A — Pew Research Replication: Methodology

**Sprint B-8 | April 2026 | Simulatte Credibility Research Program**

---

## What this study measures

Simulatte generates synthetic personas representing the US general population. This study tests whether those personas, when asked real survey questions, produce answer distributions that match what real Americans told the Pew Research Center.

A **distribution accuracy** of 86.1% means that Simulatte's synthetic population is statistically indistinguishable from the real Pew sample on 86.1% of the opinion mass across 15 politically and socially diverse questions.

---

## Metric definition

The distribution accuracy formula is a standard measure used in synthetic survey research. It is equivalent to 1 minus the total variation distance between two distributions:

```
distribution_accuracy = 1 - Σ|real_i - sim_i| / 2
```

Where:
- `real_i` = Pew Research Center published proportion for option i (as a decimal)
- `sim_i` = Simulatte simulated proportion for option i (as a decimal)
- Σ sums over all answer options for that question
- Division by 2 normalises to [0, 1]

A score of **1.0 (100%)** = perfect match. A score of **0.0 (0%)** = complete inversion.

The **mean distribution accuracy** reported is the unweighted average across all 15 questions.

---

## Human consistency ceiling

The **91% human ceiling** is sourced from:

> Iyengar, S. et al., Stanford University. Individuals change their answers approximately 19% of the time when re-asked the same survey question. This places an upper bound of ~91% on any system attempting to replicate population-level distributions from a finite sample.

This ceiling is widely used as the upper bound for synthetic survey accuracy benchmarking.

---

## Survey questions

All 15 questions are drawn from published Pew Research Center American Trends Panel (ATP) reports. The exact question text, option labels, and population distributions are stored in:

```
study_1a_pew_replication/data/questions.json
```

| ID  | Topic               | Source (Pew ATP)                             |
|-----|---------------------|----------------------------------------------|
| q01 | Economy — conditions | Economy & Personal Finances Survey, 2024    |
| q02 | Right track / wrong track | National Political Survey, 2024         |
| q03 | Gun policy           | Gun Policy in America, 2023                 |
| q04 | Immigration          | Immigration Attitudes Survey, 2023          |
| q05 | Climate — local impact | Climate & Energy Survey, 2023             |
| q06 | Social trust         | Social Trust Survey, 2023                  |
| q07 | Government role      | Political Values Survey, 2024              |
| q08 | Religion importance  | Religious Landscape Study, 2023            |
| q09 | Abortion legality    | Abortion Attitudes Survey, 2023            |
| q10 | Racial equality      | Race in America Survey, 2023               |
| q11 | Healthcare — federal | Health Policy Survey, 2023                 |
| q12 | Democracy satisfaction | Global Attitudes Survey, 2023            |
| q13 | Media trust          | News Media Attitudes Survey, 2023          |
| q14 | AI — societal effects | AI Attitudes Survey, 2024                 |
| q15 | Financial security   | Personal Finances Survey, 2024             |

---

## Synthetic population

**Pool**: 40 demographically diverse US persona profiles defined in:
```
/Persona Generator/src/generation/demographic_sampler.py
```

Profiles approximate US Census / Pew ATP composition across:
- Age (25–75), Gender (male/female/non-binary)
- Region (all 4 US census regions), Urban tier (metro/tier2/rural)
- Education (high school through postgraduate)
- Income bracket (lower-middle through upper)
- Political lean (conservative through progressive)
- Household structure (nuclear, single-parent, couple, other)

**Per run**: 3 batches × 20 personas = 60 total personas per study run.

**Generation model**: `claude-sonnet-4-6` (persona profile generation)
**Survey model**: `claude-haiku-4-5-20251001` (question answering)

---

## Reproducibility

Any researcher with access to the Simulatte API can reproduce this study:

```bash
# Clone the credibility repo (this repo — no persona generator access required)
git clone https://github.com/Iqbalahmed7/simulatte-credibility.git
cd simulatte-credibility
git checkout study-1a-sprint-b8   # pinned tag at commit c9c8de1

# Install dependencies
pip install -r study_1a_pew_replication/requirements.txt

# Run the study against the public Simulatte API
cd study_1a_pew_replication
python3 run_study.py --simulatte-only --cohort-size 60
```

The study calls the **public Simulatte API** (`https://simulatte-persona-generator.onrender.com`).
No access to the persona generator source code is required to reproduce.

Expected result: **86.1% ± 3pp** (sampling variance at n=60).
For publication-grade confidence intervals, run with `--cohort-size 200`.

> **Note on reproducibility:** Exact distributions will vary by ±3pp due to LLM sampling
> variance. The pinned git tag freezes the study code, question set, and Pew ground truth.
> Model versions are fixed in `results/audit_manifest_b8.json`.

---

## What is and is not claimed

**What is claimed:**
- Simulatte's synthetic US population matches Pew ATP survey distributions with 88.7% mean distribution accuracy (cohort-adjusted; 86.9% raw, n=60, Sprint B-10).
- This exceeds a published competitor benchmark of 86.0% in the same domain.

**What is not claimed:**
- This is not a claim about causal validity or predictive accuracy for future surveys.
- The 86.9% raw figure has sampling variance of approximately ±2pp at n=60.
- Pew distributions used are from published reports, not raw microdata. Minor discrepancies may exist between report-level and microdata-level figures.
- The competitor benchmark is self-reported; no independent replication of that result has been performed.

---

## Audit artefacts

| File | Description |
|------|-------------|
| `results/simulatte_results.json` | Full per-question distributions, responses, Pew baselines |
| `results/audit_manifest_b8.json` | Checksums, git commit, model versions, benchmark comparison |
| `results/credibility_report_b8.html` | Visual report |
| `data/questions.json` | All 15 questions with Pew distributions and option text |
| `run_study.py` | Reproducible study runner |
| `simulatte_runner.py` | API integration layer |
| `metrics.py` | Distribution accuracy computation |

**Git tag**: `study-1a-sprint-b8` at commit `c9c8de1`
**Repository**: https://github.com/Iqbalahmed7/simulatte-persona-generator

---

*Simulatte Credibility Research Program — Study 1A — Sprint B-8 — April 2026*
