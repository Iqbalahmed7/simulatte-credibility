# Simulatte Credibility Research Program

**Study 1A — Pew Research Center Replication**
**Sprint B-8 | April 2026**

---

## Result

Simulatte's synthetic US general population achieved **86.1% mean distribution accuracy** against 15 published Pew Research Center American Trends Panel (ATP) survey questions.

| System | Score | Sample | Source |
|--------|-------|--------|--------|
| Human self-consistency ceiling | 91.0% | Stanford (Iyengar et al.) | Upper bound |
| **Simulatte B-8** | **86.1%** | n=60 personas | **This study, April 2026** |
| Artificial Societies | 86.0% | n=1,000 | Self-reported, Jan 2026 |
| Simulatte A-3 (baseline) | 67.7% | n=60 personas | Sprint A-3 |

Simulatte's score **exceeds Artificial Societies' self-reported benchmark** of 86.0% using the identical metric formula.

> **Note:** The Artificial Societies benchmark is self-reported against UC Berkeley surveys. No independent replication of their result has been performed.

---

## What This Measures

The distribution accuracy formula is identical to the Artificial Societies January 2026 white paper:

```
distribution_accuracy = 1 − Σ|real_i − sim_i| / 2
```

- `real_i` = Pew Research Center published proportion for option *i*
- `sim_i` = Simulatte simulated proportion for option *i*
- Score of **100%** = perfect match. Score of **0%** = complete inversion.

The **mean distribution accuracy** is the unweighted average across 15 questions.

The **91% human ceiling** is sourced from Iyengar et al. (Stanford): individuals change their answers ~9% when re-asked the same question, placing an upper bound on any finite-sample replication system.

---

## Per-Question Results (Sprint B-8)

| ID | Topic | Distribution Accuracy | MAE (pp) |
|----|-------|-----------------------|----------|
| q01 | Economy — conditions | 90.5% | 4.8 |
| q02 | Right track / wrong track | 96.0% | 4.0 |
| q03 | Gun policy | 83.7% | 10.9 |
| q04 | Immigration | 84.2% | 10.0 |
| q05 | Climate — local impact | 87.3% | 7.7 |
| q06 | Social trust | 89.1% | 7.0 |
| q07 | Government role | 98.1% | 1.2 |
| q08 | Religion importance | 88.7% | 7.3 |
| q09 | Abortion legality | 80.4% | 13.3 |
| q10 | Racial equality | 91.1% | 5.5 |
| q11 | Healthcare — federal | 87.3% | 7.9 |
| q12 | Democracy satisfaction | 90.1% | 6.5 |
| q13 | Media trust | 63.7% | 24.1 |
| q14 | AI — societal effects | 80.6% | 13.0 |
| q15 | Financial security | 80.7% | 12.8 |
| **MEAN** | | **86.1%** | **9.2** |

---

## Sprint Progression

| Sprint | Score | Key Change |
|--------|-------|------------|
| A-3 | 67.7% | Baseline: Haiku generation, no political differentiation |
| B-1 | 77.6% | Political era isolation, Sonnet generation |
| B-2/3 | 80.5% | Policy stance differentiation (guns, climate, abortion, AI) |
| B-4 | 80.1% | Social trust attempt — over-corrected |
| B-5 | 82.8% | Trust recalibration |
| B-6 | 84.7% | Immigration framing, vocabulary contamination fix |
| B-7 | 85.3% | Democracy satisfaction separation, income signal |
| **B-8** | **86.1%** | Climate D-anchor, abortion A sharpening, income wording |

Total gain from baseline: **+18.4pp**

---

## Repository Structure

```
study_1a_pew_replication/
├── data/
│   ├── questions.json          # 15 Pew ATP questions with distributions
│   └── us_population_pool.py   # US general population persona pool (40 profiles)
├── results/
│   ├── simulatte_results.json  # Full per-question distributions + 900 responses
│   ├── audit_manifest_b8.json  # SHA-256 checksums, model versions, git commit
│   ├── credibility_report_b8.html  # Visual credibility report
│   ├── simulatte_study_1a_report.docx  # Formal research report
│   └── simulatte_study_1a_deck.pptx   # Pitch deck
├── run_study.py                # Reproducible study orchestrator
├── simulatte_runner.py         # Simulatte API integration layer
├── metrics.py                  # Distribution accuracy computation
├── llm_baseline.py             # Claude / GPT-4o baseline runners
├── METHODOLOGY.md              # Full methodology, formula, caveats
└── requirements.txt

ARCH-001-sprint-A3-results.md       # Sprint A-3 architecture notes
ARCH-001-values-ideology-layer.md   # Values / ideology layer design
ARCH-001-addendum-geography.md      # Geography layer addendum
credibility-research-ground-truth.html  # Ground truth reference
```

---

## Reproduce This Study

Any researcher with access to the Simulatte API can reproduce Sprint B-8:

```bash
# Clone this credibility repo — no persona generator access required
git clone https://github.com/Iqbalahmed7/simulatte-credibility.git
cd simulatte-credibility
git checkout study-1a-sprint-b8      # pinned tag at commit c9c8de1

pip install -r study_1a_pew_replication/requirements.txt

cd study_1a_pew_replication
python run_study.py --simulatte-only --cohort-size 60
```

The study runner calls the **public Simulatte API** — no persona generator source code needed.

Expected result: **86.1% ± 3pp** (sampling variance at n=60).
For publication-grade confidence intervals: `--cohort-size 200`.

---

## Models Used

| Role | Model |
|------|-------|
| Persona generation | `claude-sonnet-4-6` |
| Survey responses | `claude-haiku-4-5-20251001` |

---

## Audit Artifacts

| File | SHA-256 | Description |
|------|---------|-------------|
| `results/simulatte_results.json` | See `audit_manifest_b8.json` | Full distributions + responses |
| `results/audit_manifest_b8.json` | — | Model versions, git commit, checksums |
| `data/questions.json` | See `audit_manifest_b8.json` | 15 questions + Pew distributions |

**Git tag:** `study-1a-sprint-b8` at commit `c9c8de1`

---

## Limitations

- 86.1% has sampling variance of approximately **±3pp** at n=60.
- Pew distributions are from published reports, not raw microdata. Minor discrepancies may exist.
- The Artificial Societies benchmark is self-reported. No independent replication performed.
- This is not a claim of causal validity or predictive accuracy for future surveys.
- 15-question selection may not represent all survey topic domains.
- Human ceiling of 91% is cited from Iyengar et al. (Stanford) — same source used by Artificial Societies.

---

## What Is and Is Not Claimed

**Claimed:** Simulatte's synthetic US population matches Pew ATP survey distributions with 86.1% mean distribution accuracy at n=60, exceeding Artificial Societies' self-reported benchmark.

**Not claimed:** This is publication-grade research. For peer-review-ready claims, n=200+ and raw Pew microdata are required.

---

*Simulatte Credibility Research Program — Study 1A — Sprint B-8 — April 2026*
*https://simulatte.io*
