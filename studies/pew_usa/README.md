# Study 1A — Pew US Opinion Replication (v2)

## Overview

Study 1A benchmarks Simulatte's ability to replicate population-level opinion distributions among US adults using 15 validated questions from Pew Research Center's American Trends Panel (ATP).

**v2** (April 2026) rebuilds on the Simulatte Persona Generator `us_general` pool — replacing the hand-crafted B-series cohort with a demographically-anchored synthetic panel. Achieved 91%+ ceiling on Sprint 1.

| Parameter | Value |
|---|---|
| **Questions** | 15 (Pew ATP 2022–2023) — 10 calibration + 5 holdout |
| **Metric** | Distribution Accuracy = 1 − (Σ\|real_i − sim_i\| / 2) |
| **Human ceiling** | 91% (Stanford Iyengar et al.) |
| **Persona pool** | 40 — Simulatte Persona Generator `us_general` (Census 2020 + Pew ATP) |
| **Calibrated DA** | **95.3% ± 0.00pp** (Sprint USA-1, variance certified) |
| **Holdout DA** | **81.9% ± 0.87pp** (HD-1/2/3, pure WorldviewAnchor) |
| **Calibration-to-holdout gap** | 13.4pp |

## Results Summary

### Calibrated DA (10 questions, Sprint USA-1)

| Q | Topic | DA |
|---|-------|----|
| q02 | direction (economy) | 99.0% |
| q06 | social_trust | 98.4% |
| q08 | religion | 97.0% |
| q10 | racial_equality | 97.2% |
| q04 | immigration | 95.8% |
| q11 | healthcare | 95.6% |
| q13 | media_trust | 94.9% |
| q05 | climate | 93.0% |
| q01 | economy | 91.0% |
| q15 | financial_security | 91.0% |
| **Mean** | | **95.3%** |

### Holdout DA (5 questions, pure WorldviewAnchor — mean of HD-1/2/3)

| Q | Topic | DA | Notes |
|---|-------|----|-------|
| q07 | government | 98.5% | Near-perfect zero-anchor transfer |
| q14 | technology (AI) | 84.2% | B-option slightly over-weighted |
| q03 | gun_policy | 83.5% | A over-routed (45% vs 59%) |
| q09 | abortion | 76.8% | D=0% structural gap (hard-right option) |
| q12 | democracy satisfaction | 66.6% | C over-concentrated; multi-bucket pessimism |
| **Mean** | | **81.9%** | |

### Variance Protocol

| Run | Calibrated DA |
|-----|--------------|
| USA-1 | 95.3% |
| USA-1b | 95.3% |
| USA-1c | 95.3% |
| **Mean ± SD** | **95.3% ± 0.00pp** ✅ |

SD = 0.00pp — OVA architecture is fully deterministic.

## vs. Previous Study (B-series)

| Version | DA | Method |
|---------|----|--------|
| B-1 (baseline) | 57.6% | Handcrafted cohort, no worldview |
| B-10 (final) | 88.7% | Handcrafted cohort, WorldviewAnchor + OVA |
| **v2 USA-1** | **95.3%** | Persona Generator `us_general`, WorldviewAnchor + OVA |

**+6.6pp improvement** over B-10 by switching to generator-sourced personas.

## Architecture

- **Persona source**: Simulatte Persona Generator `us_general` pool (40 profiles)
  - Census 2020 demographic weights (gender, age, race, region, education)
  - Political lean from Pew 2023 Party ID data
  - WorldviewAnchor (IT/IND/CT/MF) derived from Pew 2023 Political Typology attitudinal data
  - Religious salience from Pew Religious Landscape Survey 2023
- **Calibration**: Option-Vocabulary Anchors (OVA) embedded in system prompts
- **Holdout**: Pure WorldviewAnchor prompts — zero topic-specific stances
- **Model**: `claude-haiku-4-5-20251001` via Anthropic Batch API

## Known Structural Gaps

- **q12 (democracy satisfaction)**: C over-concentrated (72% vs 39% real). Multi-bucket pessimism question where the IT/CT axes don't fully differentiate the A=4%/B=29%/C=39%/D=30% distribution. Needs party × age routing in future sprint.
- **q09 (abortion)**: D=0% vs 8.2% real. Hard-right option ("illegal in all cases") not expressed even by conservative personas — possible LLM value alignment suppression.

## Files

| File | Description |
|---|---|
| `questions.json` | 15 Pew ATP questions; holdout=true on q03/q07/q09/q12/q14 |
| `pipeline/sprint_runner.py` | v2 calibration runner — Persona Generator pool |
| `holdout/holdout_runner.py` | Pure WorldviewAnchor holdout runner |
| `results/sprint_manifests/sprint_USA-1.json` | Final calibration manifest |
| `results/sprint_manifests/sprint_USA-1b.json` | Variance rep 2 |
| `results/sprint_manifests/sprint_USA-1c.json` | Variance rep 3 |
| `results/holdout_manifests/holdout_HD-1.json` | Holdout rep 1 |
| `results/holdout_manifests/holdout_HD-2.json` | Holdout rep 2 |
| `results/holdout_manifests/holdout_HD-3.json` | Holdout rep 3 |

## Ground Truth Sources

Questions drawn from Pew Research Center American Trends Panel surveys (publicly available at pewresearch.org). Survey distributions represent weighted national samples of US adults.

## Persona Pool

40-persona `us_general` synthetic panel. Composition:
- US Census 2020 demographic weights
- Political lean: conservative 15%, lean-conservative 20%, moderate 22.5%, lean-progressive 27.5%, progressive 15%
- Covers race (White 63%, Black 12%, Hispanic 13%, Asian/other 12%), region (South/Midwest/West/Northeast), income, education, religious salience
- Pool defined in Simulatte Persona Generator `src/generation/demographic_sampler.py`
- Available for independent inspection (no NDA required for pool spec)
