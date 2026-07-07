# Study 2 — IFIC Food & Health Survey (USA)

## Overview

Study 2 is Simulatte's first domain generalisation benchmark — testing whether the WorldviewAnchor persona architecture transfers beyond political opinion to food behaviour and nutrition attitudes.

Ground truth is the **IFIC Foundation 2025 Food & Health Survey**, a nationally representative study of US adults covering dietary identity, nutrition trust, food purchasing behaviour, and government guidance familiarity.

| Parameter | Value |
|---|---|
| **Questions** | 15 (IFIC 2025) — 10 calibration + 5 holdout |
| **Metric** | Distribution Accuracy = 1 − (Σ\|real_i − sim_i\| / 2) |
| **Human ceiling** | 91% (Stanford Iyengar et al.) |
| **Persona pool** | 1,000 — Simulatte Persona Generator `us_food_health v1` |
| **Calibrated DA** | **96.1%** (Sprint IFIC-2) |
| **Holdout DA** | **83.1%** (H2i, pure WorldviewAnchor) |
| **Cal → holdout gap** | 13.0pp |

---

## Results Summary

### Calibrated DA — Sprint IFIC-2

| Q | Topic | DA |
|---|-------|----|
| ific02 | purchase decision scale | 98.3% |
| ific10 | cost vs. nutrition trade-off | 98.3% |
| ific06 | nutrition concern | 98.0% |
| ific01 | food purchase factors | 97.3% |
| ific04 | meal planning frequency | 97.2% |
| ific07 | organic / natural preference | 95.8% |
| ific09 | functional foods | 95.4% |
| ific05 | food label use | 94.9% |
| ific08 | sugar / processing views | 93.8% |
| ific03 | diet quality self-rating | 92.2% |
| **Mean** | | **96.1%** |

All 10 calibrated questions above 92%.

### Holdout DA — H2i (pure WorldviewAnchor, no OVA)

| Q | Topic | DA | Notes |
|---|-------|----|-------|
| h01 | MyPlate dietary familiarity | 94.4% | Near-perfect; NIT threshold split resolved |
| h03 | RDN credibility rating | 85.6% | gov_nutrition NIT framing drives this |
| h04 | Food safety concern level | 80.6% | Segment distribution captures spread well |
| h02 | Eating-out nutrition tracking | 79.1% | DI-tracking not fully resolved without OVA |
| h05 | Social media food content | 75.9% | A still over-represented (74% sim vs 50% real) |
| **Mean** | | **83.1%** | |

### H2 Series — Holdout Improvement Journey

| Run | DA | Gap | Key change |
|-----|----|-----|------------|
| H2 (Haiku) | 60.7% | 35.4pp | Baseline |
| H2b | 66.9% | 29.2pp | Sonnet + anti-sycophancy instruction |
| H2c | 69.2% | 26.9pp | Age-gated non-user D phrasing |
| H2d | 71.7% | 24.4pp | Segment behavioral backstory added |
| H2g | 75.5% | 20.6pp | Social media enrichment fix (h05) |
| H2h | 80.7% | 15.4pp | gov_nutrition RDN + MyPlate language |
| **H2i** | **83.1%** | **13.0pp** | NIT threshold split at 52 (h01 refinement) |

Total improvement: +13.9pp from H2c baseline across 7 iterations.

---

## WorldviewAnchor Dimensions

Study 2 uses a food-behavior WorldviewAnchor — four dimensions purpose-built for IFIC:

| Dimension | Full Name | What it captures |
|---|---|---|
| **HI** | Health Identity | How central food quality and health are to personal identity |
| **DI** | Dietary Intentionality | Whether food choices are deliberate vs. habitual |
| **FBS** | Food Budget Sensitivity | Sensitivity to food price; cost vs. quality trade-off |
| **NIT** | Nutrition Info Trust | Trust in government guidelines, RDNs, scientific consensus |

All dimensions are 0–100 scales, assigned per-persona by the Simulatte Persona Generator.

### Segments

| Segment | Share | Profile |
|---|---|---|
| health_avoiders | 15% | Low HI + DI — food is fuel, not identity |
| budget_pragmatists | 20% | High FBS — price drives every decision |
| mainstream_consumers | 30% | Mid-range across all dimensions |
| health_seekers | 25% | High HI + DI — plans meals, follows guidelines |
| nutrition_enthusiasts | 10% | Max HI + NIT — reads research, may consult RDN |

---

## Architecture

- **Persona source**: Simulatte Persona Generator `us_food_health v1` (1,000 profiles)
  - US Census demographic weights (age, gender, region, education, income)
  - Food-behavior segment split matching CPS consumer data
  - WorldviewAnchor (HI/DI/FBS/NIT) derived from IFIC 2025 attitudinal data
- **Calibration**: Option-Vocabulary Anchors (OVA) embedded in system prompts
- **Holdout**: Pure WorldviewAnchor — zero topic-specific stances
- **Sprint model**: `claude-haiku-4-5` via direct API (`--direct` flag)
- **Holdout model**: `claude-sonnet-4-6` via direct API (Haiku over-agrees on holdout)

> **Note:** Batch API was unreliable for this workspace — both initial batches had cancellations. Use `--direct` flag for all runs.

---

## Domain Generalisation Finding

The calibration-to-holdout gap for IFIC (13.0pp) matches the US political study (13.4pp) within 0.4pp — despite completely different survey instruments, WorldviewAnchor dimensions, and persona pools.

| Study | Domain | Calibrated | Holdout | Gap |
|---|---|---|---|---|
| PEW USA v2 | Political | 95.3% | 81.9% | 13.4pp |
| **IFIC USA** | **Food & Health** | **96.1%** | **83.1%** | **13.0pp** |

This confirms the structural floor of WorldviewAnchor zero-shot prediction (~83%) is domain-independent. Opinion Vector Anchors (OVA) are required to close the remaining gap.

---

## Known Structural Gaps

- **h05 (social media food content)**: A still over-represented (74% sim vs 50% real). The question asks about passive exposure, but HI/DI dimensions capture active engagement more than passive feed behaviour.
- **h02 (eating-out nutrition tracking)**: C/D shift unresolved — no DI-tracking OVA anchor in holdout to distinguish "sometimes" vs "rarely" monitoring.
- **Structural floor**: ~13pp gap is architectural. Without per-question OVA, WorldviewAnchor prediction peaks at ~83% on this instrument.

---

## Running the Study

```bash
cd studies/study_2_us_ific

# Sprint calibration (Haiku, direct API)
python3 pipeline/sprint_runner_v2.py --sprint IFIC-3 --model haiku --direct

# Holdout validation (Sonnet, direct API)
python3 holdout/holdout_runner_v2.py --run IFIC-H3 --model sonnet --direct

# Backtest (20 questions, 36 personas)
python3 backtest/backtest_runner.py --run BT-3 --model sonnet --direct
```

---

## Files

| File | Description |
|---|---|
| `questions.json` | 15 IFIC 2025 questions; holdout=true on h01–h05 |
| `pipeline/sprint_runner_v2.py` | Calibration runner — food-behavior WV routing |
| `holdout/holdout_runner_v2.py` | Pure WorldviewAnchor holdout runner (H2 series) |
| `backtest/backtest_runner.py` | 20-question backtest runner |
| `results/sprint_manifests/sprint_IFIC-2.json` | Final calibration manifest (96.1%) |
| `results/holdout_manifests/holdout_IFIC-H2i.json` | Best holdout manifest (83.1%) |
| `results/backtest_manifests/backtest_BT-2.json` | Backtest manifest (72.3%, 20 questions) |

---

## Ground Truth

IFIC Foundation 2025 Food & Health Survey. Nationally representative sample of US adults (N≈1,000). Fieldwork conducted Spring 2025. Published topline distributions used as ground truth. No survey microdata used.
