# Study 1B — Pew India Opinion Replication

## Overview

Study 1B benchmarks Simulatte's ability to replicate population-level social, political, religious, and economic opinion distributions among Indian adults using 15 validated questions from Pew Research Center's Global Attitudes and Religion in India surveys.

| Parameter | Value |
|---|---|
| **Questions** | 15 (Pew Global Attitudes 2017–2024 + Pew Religion 2021 + CSDS-Lokniti) |
| **Metric** | Distribution Accuracy = 1 − (Σ\|real_i − sim_i\| / 2) |
| **Human ceiling** | 91% (Stanford Iyengar et al.) |
| **Persona pool** | 40 demographically calibrated India personas |
| **Final result** | **85.3%** (Sprint A-22 — locked as ceiling) |
| **Baseline** | 46.2% (Sprint A-1) |
| **Total gain** | +39.1 pp across 22 sprints |

## Result

Simulatte DEEP (Sprint A-22) achieves **85.3% distribution accuracy** — 5.7 percentage points below the 91% human replication ceiling. Sprint A-22 is the locked ceiling for this study.

## Sprint Progression

| Sprint | Accuracy | Key Change |
|---|---|---|
| A-1 | 46.2% | Baseline |
| A-9 | 76.1% | +29.9 pp — India archetypes mapped to political lean |
| A-17 | 81.4% | Institutional trust separated from political approval |
| A-21 | 83.1% | BJP-lean democratic accountability narrative |
| A-22 | **85.3%** | Opposition pool rebalancing — locked as ceiling |

Full sprint-by-sprint audit manifests (A-1 through A-22) are in `results/sprint_manifests/`.

## Pool Composition

| Dimension | Distribution |
|---|---|
| Religion | Hindu 80%, Muslim 13%, Sikh/Christian 7% |
| Politics | BJP-supporter 35%, BJP-lean 20%, Neutral 10%, Opposition-lean 8%, INC-supporter 10% |
| Caste | General 37%, OBC 41%, SC 13%, ST 6% (Hindu only) |
| Region | North/Hindi belt 33%, South 23%, West 20%, East/NE 15%, Pan-India 10% |

## Files

| File | Description |
|---|---|
| `questions.json` | 15 Pew India questions with ground truth distributions |
| `results/sprint_manifests/` | Per-sprint accuracy logs (A-1 through A-22) |
| `results/final_scores.json` | Final Simulatte response distributions (A-22) |
| `results/comparison.json` | Simulatte vs ground truth comparison |

## Ground Truth Sources

- Pew Research Center Global Attitudes Survey 2023/2024 (N=2,611 India)
- Pew Research Center Global Attitudes Survey 2017/2018 (N=2,464 India)
- Pew Research Center Religion in India 2021 (N=29,999)
- CSDS-Lokniti National Election Studies

All survey data publicly available at pewresearch.org.

## Persona Pool

The 40-persona India population pool is proprietary. It reflects SECC 2011, Census 2011, and Lokniti demographic weights. Available under NDA for independent replication.

## LLM Comparison

See [../llm_comparison/](../llm_comparison/) for the benchmark comparing Simulatte against 10 leading LLMs on this same study.
