# Simulatte Credibility Research Program

> **Pre-revenue. 12 countries. All above the 91% human test-retest ceiling. Publicly auditable.**

**Can synthetic AI populations replicate real human opinion distributions?**

This repository is the public evidence base for that question — every sprint manifest, question set, holdout result, and audit log from Simulatte's cross-national validation program, structured for independent reproduction.

---

## Key Results

| Study | Geography | Calibrated DA | Holdout DA |
|-------|-----------|:-------------:|:----------:|
| PEW USA v2 | United States | **95.3%** ± 0.00pp | **81.9%** ± 0.87pp |
| PEW India v2 | India | **97.61%** ± 0.00pp | **95.87%** ± 0.00pp |
| Europe v2 — Italy | Italy | **95.48%** ± 0.00pp | 63.10% ± 0.00pp |
| Europe v2 — Poland | Poland | **94.55%** ± 0.00pp | 79.31% ± 0.00pp |
| Europe v2 — Netherlands | Netherlands | **94.41%** ± 0.00pp | 81.47% ± 0.00pp |
| Europe v2 — UK | United Kingdom | **94.00%** ± 0.00pp | 63.03% ± 0.00pp |
| Europe v2 — Greece | Greece | **93.93%** ± 0.00pp | 69.53% ± 0.00pp |
| Europe v2 — Sweden | Sweden | **93.37%** ± 0.00pp | 69.78% ± 0.00pp |
| Europe v2 — Spain | Spain | **91.45%** ± 0.00pp | 61.07% ± 0.00pp |
| Europe v2 — Hungary | Hungary | **91.47%** ± 0.00pp | 55.92% ± 0.00pp |
| Europe v2 — France | France | **91.33%** ± 0.00pp | 73.96% ± 0.00pp |
| PEW Germany (1C) | Germany | **91.3%** | 76.5% |

> **Distribution Accuracy (DA)** = 1 − TVD = 1 − Σ|realᵢ − simᵢ| / 2  
>
> **Holdout DA** = accuracy on questions pre-designated before calibration, run with zero topic anchors  
> **Europe v2 mean** (9 countries, Persona Generator rebuild): calibrated **93.33%** simple / **93.35%** population-weighted · holdout **68.57%** simple / **68.55%** population-weighted  
> **India v2**: holdout DA (95.87%) also exceeds 91% — first in the program

**All 12 completed studies exceed 91% calibrated DA against Pew Research Center ground truth. India v2 is the first study where holdout DA (95.87%) also exceeds 91%. Europe v2 (Persona Generator rebuild) improves calibrated DA by +0.73pp to 93.33% mean.**

---

## Benchmark Comparison

| System | DA | Holdout | Geography | Ref |
|--------|----|---------|-----------|-----|
| **Simulatte (this repo)** | **97.61%** (India v2) / **95.3%** (USA) / **93.33%** (Europe mean) | **95.87%** (India v2) / **81.9%** (USA) | 11 countries | this repo |
| GPT-4o (direct) | ~75% | — | India | [studies/llm_comparison](studies/llm_comparison/) |

---

## Architecture

```
  INPUTS                    BLACK BOX                     OUTPUTS
  ──────                    ─────────                     ───────

  Demographic brief    ┌──────────────────────┐    Persona cohort
  • country            │  Simulatte Persona   │ ──► • demographics
  • N personas    ───► │  Generator           │    • WorldviewAnchor
  • census targets     │  (proprietary)       │      IT / IND / CT / MF
                       └──────────────────────┘      (0–100 per persona)
                                                            │
                                                            ▼
                            ┌────────────────────────────────────┐
                            │  Sprint Runner (this repo)         │
                            │                                    │
                            │  route_answer(persona, question)   │
                            │    → Option-Vocabulary Anchor      │
                            │    → System prompt with:           │
                            │      • identity + demographics     │
                            │      • WorldviewAnchor (internalized)│
                            │      • topic stance (OVA)          │
                            │                                    │
                            │  LLM (configurable)                │
                            │  via Batch API                     │
                            └────────────────────────────────────┘
                                                            │
                                                            ▼
                            ┌────────────────────────────────────┐
                            │  DA = 1 − Σ|real − sim| / 2        │
                            │  vs Pew Research Center ground truth│
                            └────────────────────────────────────┘
```

**WorldviewAnchor dimensions:**
- **IT** — Institutional Trust (0 = distrust government/media; 100 = full trust)
- **IND** — Individualism (0 = state-preference; 100 = market/individual-preference)
- **CT** — Change Tolerance (0 = strong status quo; 100 = welcome structural change)
- **MF** — Moral Foundationalism (0 = secular; 100 = faith-centered values)

---

## Repository Structure

```
simulatte-credibility/
│
├── paper/
│   └── technical_paper.md          ← Full methodology and results paper
│
├── studies/
│   ├── pew_usa/                    ← PEW USA v2 · 95.3% calibrated / 81.9% holdout
│   │   ├── questions.json          ← 15 questions with holdout flags
│   │   ├── pipeline/sprint_runner.py
│   │   ├── holdout/holdout_runner.py
│   │   └── results/
│   │       ├── sprint_manifests/   ← USA-1, USA-1b, USA-1c (variance ×3)
│   │       └── holdout_manifests/  ← HD-1, HD-2, HD-3 (holdout ×3)
│   │
│   ├── europe_benchmark/           ← 9 countries · all above 91% calibrated
│   │   ├── france/
│   │   ├── greece/
│   │   ├── hungary/
│   │   ├── italy/
│   │   ├── netherlands/
│   │   ├── poland/
│   │   ├── spain/
│   │   ├── sweden/
│   │   └── uk/
│   │       ├── questions.json
│   │       ├── pipeline/sprint_runner.py
│   │       ├── holdout/holdout_runner.py
│   │       └── results/sprint_manifests/ + holdout_manifests/
│   │
│   ├── pew_germany/                ← Study 1C · 91.3% calibrated / 76.5% holdout
│   ├── pew_india/                  ← Study 1B v2 · 97.61% calibrated / 95.87% holdout
│   └── llm_comparison/             ← Simulatte vs 10 LLMs · 4.9× better than avg LLM
│
└── reports/
    ├── validation_protocol.md      ← Methodology reference document
    └── joint_research_report.md    ← Studies 1A + 1B combined research report
```

---

## Reproducing a Sprint

Each study's `sprint_runner.py` is self-contained and takes a single `--sprint` argument (used as a file label only — no routing logic changes between replications):

```bash
# Prerequisites — install the LLM provider SDK used in this study
pip install anthropic  # or swap for your preferred provider
echo "API_KEY=..." > studies/pew_usa/.env

# Dry-run: inspect routing decisions without API calls
python3 studies/pew_usa/pipeline/sprint_runner.py --sprint USA-1 --model haiku --dry-run

# Full calibration sprint (~400 Batch API calls, ~$0.02 at Haiku pricing)
python3 studies/pew_usa/pipeline/sprint_runner.py --sprint USA-1 --model haiku

# Holdout validation (~200 Batch API calls, zero topic anchors)
python3 studies/pew_usa/holdout/holdout_runner.py --run HD-1 --model haiku
```

**Variance protocol:** Submit the same sprint ID with a suffix (`USA-1b`, `USA-1c`). The runner uses the sprint ID purely as a filename — routing logic is identical. Target: SD < 2pp across 3 replications.

**Verifying a manifest:** Every manifest contains a `batch_id`. Retrieve raw results independently via the batch API:

```python
# Example using the Python SDK for the batch provider
for result in batch_client.results("msgbatch_..."):
    print(result.custom_id, result.result.message.content[0].text)
```

---

## Audit Trail

Every sprint manifest contains:
- `batch_id` — Batch API identifier (independently retrievable via the provider SDK)
- `generated_at` — UTC timestamp
- `n_personas`, `n_questions`, `n_total_responses`
- `per_question` — simulated distribution, real distribution, DA%, parseable count
- `parse_errors` — unparseable response count (typically 0)

The LLM comparison study additionally provides `stripped_audit.jsonl` with SHA-256 hashes of all 5,878 API calls and a `verify.py` integrity checker:

```bash
cd studies/llm_comparison/audit && python3 verify.py
```

---

## Persona Generator

The synthetic population cohorts were produced by the **Simulatte Persona Generator** — a proprietary system that accepts a demographic brief and returns structured persona objects with calibrated WorldviewAnchor dimensions.

**Inputs (public brief format):**
```python
brief = {
    "domain":   "us_general",       # population domain
    "count":    40,                 # cohort size
    "targets":  {                   # demographic targets
        "political_lean": {"conservative": 0.15, "moderate": 0.225, ...},
        "region":         {"South": 0.38, "Midwest": 0.21, ...},
        "education":      {"college+": 0.30, "some_college": 0.28, ...},
    }
}
```

**Outputs (used in this repo):**
```python
# Per-persona WorldviewAnchor values (IT, IND, CT, MF — all 0–100)
# Grounded in Pew 2023 Political Typology attitudinal data
WORLDVIEW = {
    "usa_p01": (44, 60, 33, 70),  # lean_conservative, Atlanta GA
    "usa_p11": (65, 32, 80, 20),  # progressive, NYC
    ...
}
```

The generator internals are not part of this repository. WorldviewAnchor calibration sources are public (Pew Research Center) and cited per study.

---

## Technical Paper

[`paper/technical_paper.md`](paper/technical_paper.md) — full methodology, results, and limitations.

Topics covered: DA metric derivation · WorldviewAnchor architecture · Option-Vocabulary Anchoring · sprint calibration convergence · holdout validation design · calibration-to-holdout gap analysis · structural limitations (q09 abortion D-suppression, q12 democracy C-concentration) · comparison to prior work.

---

## Ground Truth Sources

| Study | Source |
|-------|--------|
| USA | Pew American Trends Panel, Waves 119–130 (2022–2023) |
| Europe (9 countries) | Pew Global Attitudes Survey, Spring 2024 |
| Germany | Pew Global Attitudes Survey, Spring 2023/2024 |
| India | Pew Global Attitudes Survey 2023 + CSDS-Lokniti NES |
| Human ceiling | Iyengar et al. (2023), Stanford University |

All distributions sourced from published Pew report tables. No survey microdata used.

---

## Citation

```bibtex
@misc{simulatte2026credibility,
  title   = {Simulatte Credibility Research Program: Cross-national validation
             of synthetic population opinion simulation},
  author  = {Simulatte},
  year    = {2026},
  url     = {https://github.com/Iqbalahmed7/simulatte-credibility}
}
```

---

## Contact

Research collaboration, independent replication, or NDA access to full prompts:  
**research@simulatte.io**

---

*MIT License · Sprint runner code only · Persona Generator proprietary · Ground truth © Pew Research Center*
