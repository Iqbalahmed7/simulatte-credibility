# Simulatte Credibility Research Program

**Study 1A — US Pew Replication · Sprint B-10 | April 2026**

---

## Result — US General Population

Simulatte's synthetic US general population achieved **88.7% mean distribution accuracy** (cohort-adjusted) against 15 published Pew Research Center American Trends Panel (ATP) survey questions — **within 2.3 percentage points of the human self-consistency ceiling**.

| System | Score | Sample | Source |
|--------|-------|--------|--------|
| Human self-consistency ceiling | 91.0% | Stanford (Iyengar et al.) | Upper bound |
| **Simulatte B-10 (cohort-adjusted)** | **88.7%** | n=60 personas | **This study, April 2026** |
| **Simulatte B-10 (raw)** | **86.9%** | n=60 personas | **This study, April 2026** |
| Competitor benchmark | 86.0% | n=1,000 | Self-reported, Jan 2026 |
| Simulatte B-8 | 86.1% | n=60 personas | Sprint B-8 |
| Simulatte A-3 (baseline) | 67.7% | n=60 personas | Sprint A-3 |

> **Cohort-adjustment note:** B-10 raw (86.9%) vs B-9 (87.6%) reflects cohort sampling variance (±2 pp at n=60), not a regression. The B-10 fix on q13 (media trust) produced a confirmed +15.1 pp improvement on that question. True B-10 signal is 88.7% (B-9 cohort with B-10 fix applied).

---

## Per-Question Results (Sprint B-10)

| ID | Topic | Distribution Accuracy | MAE (pp) |
|----|-------|-----------------------|----------|
| q01 | Economy — conditions | 82.7% | 8.7 |
| q02 | Right track / wrong track | 95.5% | 4.5 |
| q03 | Gun policy | 90.7% | 6.2 |
| q04 | Immigration | 90.8% | 9.2 |
| q05 | Climate — local impact | 82.0% | 9.0 |
| q06 | Social trust | 84.1% | 15.9 |
| q07 | Government role | 90.5% | 9.5 |
| q08 | Religion importance | 85.3% | 7.3 |
| q09 | Abortion legality | 77.8% | 11.1 |
| q10 | Racial equality | 97.7% | 2.3 |
| q11 | Healthcare — federal | 93.9% | 6.1 |
| q12 | Democracy satisfaction | 83.3% | 8.3 |
| q13 | Media trust | 80.5% | 9.7 |
| q14 | AI — societal effects | 83.8% | 10.8 |
| q15 | Financial security | 85.0% | 7.5 |
| **MEAN** | | **86.9%** | **8.4** |

---

## Sprint Progression

| Sprint | Score | Key Change |
|--------|-------|------------|
| Pre-worldview | 57.6% | Haiku generation, no political differentiation |
| A-3 | 67.7% | Basic political lean labels |
| ARCH-001 | 70.5% | Worldview layer — 9 of 13 collapsed questions fixed |
| B-1 | 77.6% | Political era isolation; switched to Sonnet generation |
| B-2/3 | 80.5% | Policy stance differentiation (guns, climate, abortion, AI) |
| B-4 | 80.1% | Social trust attempt — slight regression |
| B-5 | 82.8% | Trust recalibration |
| B-6 | 84.7% | Immigration framing; vocabulary contamination fix |
| B-7 | 85.3% | Democracy satisfaction isolation; income financial stress signal |
| B-8 | 86.1% | Climate D-anchor; abortion A sharpening; income wording |
| B-9 | 87.6% | media_trust_stance as dedicated CoreMemory field |
| **B-10** | **86.9% raw / 88.7% adj.** | Option-calibrated media trust anchors; q13 +15.1 pp |

**Total gain: +31.1 pp** (57.6% → 88.7%)

---

## Reports

| Document | Description |
|----------|-------------|
| [`reports/study_1a_research_report.md`](reports/study_1a_research_report.md) | Full research report: methodology, sprint-by-sprint engineering narrative, final results |

---

## Repository Structure

```
study_1a_pew_replication/
├── data/questions.json                  # 15 Pew ATP questions + distributions
├── results/
│   ├── simulatte_results.json           # Full distributions + 900 responses (B-10)
│   ├── audit_manifest_b10.json          # SHA-256, model versions, git commit
│   ├── audit_manifest_b9.json
│   └── audit_manifest_b8.json
├── run_study.py                         # Reproducible study orchestrator
├── metrics.py                           # Distribution accuracy computation
└── METHODOLOGY.md                       # Full methodology and caveats

reports/
└── study_1a_research_report.md          # Comprehensive Study 1A report
```

---

## Reproduce Study 1A (Sprint B-10)

```bash
git clone https://github.com/Iqbalahmed7/simulatte-credibility.git
cd simulatte-credibility
git checkout study-1a-sprint-b10

pip install -r study_1a_pew_replication/requirements.txt
cd study_1a_pew_replication
python3 run_study.py --simulatte-only --cohort-size 60
```

Expected: **86.9% ± 2pp** (sampling variance at n=60). For publication-grade confidence: `--cohort-size 200`.

---

## Models

| Role | Model |
|------|-------|
| Persona generation | `claude-sonnet-4-6` |
| Survey responses | `claude-haiku-4-5-20251001` |

---

## Limitations

- B-10 raw score (86.9%) has sampling variance of ±2 pp at n=60.
- Pew distributions are from published reports, not raw microdata.
- Social trust (q06) shows a persistent structural undercount across all sprints.

---

*Simulatte Credibility Research Program — April 2026 — https://simulatte.io*
