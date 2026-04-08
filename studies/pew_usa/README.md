# Study 1A — Pew US Opinion Replication

## Overview

Study 1A benchmarks Simulatte's ability to replicate population-level opinion distributions among US adults using 15 validated questions from Pew Research Center's American Trends Panel (ATP).

| Parameter | Value |
|---|---|
| **Questions** | 15 (Pew ATP 2022–2023) |
| **Metric** | Distribution Accuracy = 1 − (Σ\|real_i − sim_i\| / 2) |
| **Human ceiling** | 91% (Stanford Iyengar et al.) |
| **Persona pool** | 60 demographically calibrated US personas |
| **Final result** | **88.7%** (cohort-adjusted, Sprint B-10) |
| **Baseline** | 57.6% (Sprint B-1) |
| **Total gain** | +31.1 pp across 10 sprints |

## Result

Simulatte DEEP (Sprint B-10) achieves **88.7% distribution accuracy** — just 2.3 percentage points below the 91% human replication ceiling.

## Sprint Progression

| Sprint | Accuracy | Key Change |
|---|---|---|
| B-1 | 57.6% | Baseline |
| B-8 | 85.2% | Worldview layer added |
| B-9 | 87.1% | Trust calibration |
| B-10 | **88.7%** | Final — cohort adjustment |

Full sprint-by-sprint audit manifests are in `results/sprint_manifests/`.

## Files

| File | Description |
|---|---|
| `questions.json` | 15 Pew ATP questions with ground truth distributions |
| `results/sprint_manifests/` | Per-sprint accuracy logs (B-8, B-9, B-10) |
| `results/final_scores.json` | Final Simulatte response distributions |
| `results/comparison.json` | Simulatte vs ground truth comparison |

## Ground Truth Sources

Questions drawn from Pew Research Center American Trends Panel surveys (publicly available at pewresearch.org). Survey distributions represent weighted national samples of US adults.

## Persona Pool

The 60-persona US population pool is proprietary. Pool composition:
- Reflects 2020 US Census demographic weights
- Covers political lean (Democrat / Republican / Independent), religion, age, education, income, region
- Available under NDA for independent replication
