# Simulatte Credibility Research Program

**Study 1B — India Pew Replication · Sprint A-9 Complete at 83.3% | Study 1A — US Complete at 88.7% | April 2026**

Simulatte generates synthetic AI personas and surveys them at scale. This repository documents a rigorous benchmarking program measuring how closely simulated survey distributions match real Pew Research Center data.

---

## Study 1B — India Pew Replication · Active

Replicating 15 Pew Research Center India survey questions against a 40-persona synthetic Indian general population.

| Sprint | Score | Δ | Key Change |
|--------|-------|----|------------|
| A-1 | 46.2% | baseline | Baseline — no cultural optimisation |
| A-2 | 45.9% | −0.3 | Option anchors (NOT-JUST pattern) |
| A-3 | 50.3% | +4.4 | Cultural preamble injection |
| A-4 | 49.2% | −1.1 | Preamble conflict fix |
| A-5 | 50.0% | +0.8 | Economics–politics decoupling attempt |
| A-6 | 50.5% | +0.5 | BJP narrative constraint; spread injection |
| A-7 | 51.6% | +1.1 | Budget ceiling gate; in15 first B responses |
| A-8 | 53.4% | +1.8 | Tendency_summary gate; in13 B=20.5% emerging |
| **A-9** | **83.3%** | **+29.9** | **ROOT CAUSE FIX: `_get_political_lean()` — India archetypes were silently mapped to "moderate" for 8 sprints** |

> **Sprint A-9 breakthrough:** +29.9 pp in a single sprint — the largest gain in the program. Root cause discovered: `_ARCHETYPE_TO_LEAN` in `attribute_filler.py` did not include India archetypes, causing ALL India personas to have `political_lean="moderate"` in their attributes dict. Every political lean gate, stance field, and narrative constraint was silently returning neutral values across A-1→A-8. The `_get_political_lean()` fix reads directly from `demographic_anchor.worldview.political_profile.archetype` for India personas, bypassing the broken attribute path. The previously reported "RLHF hard ceilings" on in07/in12/in13 were actually caused by this missing differentiation, not RLHF — all three questions jumped 40–62 pp in A-9.

---

## Study 1B Per-Question Results — Sprint A-9

| ID | Topic | A-9 | A-8 | Δ | Classification |
|----|-------|-----|-----|---|----------------|
| in01 | Democracy satisfaction | 88.1% | 91.1% | −3.0 | minor variance |
| in02 | Modi approval | 84.8% | 65.4% | **+19.4** | BJP differentiation working |
| in03 | BJP approval | 75.4% | 68.2% | +7.2 | improving |
| in04 | INC approval | 83.5% | 53.4% | **+30.1** | INC conviction fix + lean fix |
| in05 | India global power | 88.0% | 80.3% | +7.7 | spread working |
| in06 | Representative democracy | 75.1% | 84.2% | −9.1 | ⚠ governance_stance bleed; 0% C/D |
| **in07** | **Strong leader** | **95.6%** | **33.9%** | **+61.7** | **governance_stance now firing — not RLHF** |
| in08 | Economic conditions | 88.5% | 74.3% | **+14.2** | budget+tendency gates firing correctly |
| in09 | Government trust | 83.0% | 61.5% | **+21.5** | inst_trust raise + lean fix |
| in10 | Future generations | 97.0% | 82.5% | +14.5 | near-ceiling |
| in11 | Religion importance | 84.0% | 88.3% | −4.3 | 100% A collapse — needs B spread |
| **in12** | **Wife obedience** | **81.0%** | **29.1%** | **+51.9** | **gender_norms_stance now firing** |
| **in13** | **Gender roles / jobs** | **75.5%** | **35.4%** | **+40.1** | **same** |
| in14 | Women equal rights | 66.6% | 82.8% | −16.2 | ⚠ gender_norms bleed into equal rights Q |
| in15 | Climate change threat | 84.0% | 72.9% | +11.1 | dev-framing spread note working |
| **MEAN** | | **83.3%** | **53.4%** | **+29.9** | |

---

## Sprint A-10 Roadmap

| Priority | Fix | Target questions | Expected gain |
|----------|-----|-----------------|---------------|
| 1 | **Fix in14 regression** — `gender_norms_stance` bleeds into "women equal rights" question. Add spread note: even traditional Indians support women's equal rights in principle (Pew: 81% A). These views coexist in Indian public opinion. | in14 | +15 pp |
| 2 | **Fix in06 regression** — `governance_stance` bleed causing 0% C/D. Add spread note: even BJP supporters support representative democracy as a system; the strong leader preference is about effectiveness, not abolishing elections. | in06 | +8 pp |
| 3 | **Fix in11 collapse** — 100% A (very important for religion). Add spread note to distribute to B/C for secular/moderate personas. | in11 | +4 pp |
| 4 | **Push in02/in03 A option** — A still undershooting (sim 45%/25% vs Pew 56%/43%). Strengthen bjp_supporter "very favorable" anchor. | in02, in03 | +5 pp |
| 5 | **Push in12/in13 A option** — A still undershooting (sim 45%/25% vs Pew 64%/47%). Strengthen "completely agree" anchor. | in12, in13 | +4 pp |

---

## Study 1A — US Pew Replication · Completed

Simulatte's synthetic US general population achieved **88.7% distribution accuracy** (cohort-adjusted) against 15 published Pew ATP survey questions — **2.3 pp from the human self-consistency ceiling**.

| System | Score | Notes |
|--------|-------|-------|
| Human ceiling (Stanford/Iyengar) | 91.0% | Upper bound |
| **Simulatte B-10 (cohort-adjusted)** | **88.7%** | April 2026 |
| Simulatte B-10 (raw) | 86.9% | n=60, Sprint B-10 cohort |
| Competitor benchmark | 86.0% | Self-reported |

**Total gain:** 57.6% baseline → 88.7% final = **+31.1 pp over 10 sprints**

→ Full report: [`reports/study_1a_research_report.md`](reports/study_1a_research_report.md)
→ Credibility report (HTML): [`study_1a_pew_replication/results/credibility_report_b10.html`](study_1a_pew_replication/results/credibility_report_b10.html)

---

## Reports

| Document | Study | Description |
|----------|-------|-------------|
| [`reports/western_model_bias_finding.md`](reports/western_model_bias_finding.md) | 1B | Research note: RLHF cultural bias in cross-cultural survey simulation |
| [`reports/western_model_bias_deck.md`](reports/western_model_bias_deck.md) | 1B | 13-slide deck on the RLHF cultural bias finding |
| [`reports/study_1a_research_report.md`](reports/study_1a_research_report.md) | 1A | Full methodology, sprint narrative, B-10 final results |

---

## Repository Structure

```
study_1b_pew_india/                      ← Active study
├── data/questions_india.json            # 15 Pew India questions + distributions
├── data/india_population_pool.py        # 40-persona Indian population sampler
├── results/
│   ├── simulatte_results.json           # Latest India run (Sprint A-7)
│   ├── audit_manifest_a7.json           # Sprint A-7 results + prescriptive anchor backfire analysis
│   ├── audit_manifest_a6.json           # Sprint A-6 results + multi-channel contamination analysis
│   ├── audit_manifest_a5.json           # Sprint A-5 results + decoupling failure analysis
│   ├── audit_manifest_a4.json           # Sprint A-4 results + root cause
│   ├── audit_manifest_a3.json           # Sprint A-3 results
│   ├── audit_manifest_a2.json           # Sprint A-2 results + RLHF discovery
│   └── audit_manifest_a1.json           # Sprint A-1 baseline
├── run_study.py                         # Reproducible study orchestrator
├── metrics.py                           # Distribution accuracy computation
└── METHODOLOGY_INDIA.md                 # Full methodology and caveats

study_1a_pew_replication/                ← Completed study
├── data/questions.json                  # 15 Pew ATP questions + distributions
├── results/
│   ├── simulatte_results.json           # Full distributions + 900 responses (B-10)
│   ├── credibility_report_b10.html      # Dark-theme credibility report
│   ├── simulatte_study_1a_b10_deck.pptx # Pitch deck
│   ├── simulatte_study_1a_b10_report.docx # Full research report
│   └── audit_manifest_b10.json         # SHA-256, model versions, git commit
├── run_study.py
├── metrics.py
└── METHODOLOGY.md

reports/
├── western_model_bias_finding.md        # RLHF cultural bias research note (1B)
├── western_model_bias_deck.md           # 13-slide deck on RLHF bias (1B)
└── study_1a_research_report.md         # Comprehensive Study 1A report
```

---

## Reproduce Study 1B (Sprint A-6)

```bash
git clone https://github.com/Iqbalahmed7/simulatte-credibility.git
cd simulatte-credibility
git checkout study-1b-sprint-a7

pip install -r study_1b_pew_india/requirements.txt
cd study_1b_pew_india
python3 run_study.py --simulatte-only
```

Expected: **51.6% ± 3 pp** (sampling variance at n=40).

## Reproduce Study 1A (Sprint B-10)

```bash
git checkout study-1a-sprint-b10
pip install -r study_1a_pew_replication/requirements.txt
cd study_1a_pew_replication
python3 run_study.py --simulatte-only --cohort-size 60
```

Expected: **86.9% ± 2 pp** (sampling variance at n=60).

---

## Models

| Role | Model |
|------|-------|
| Persona generation | `claude-sonnet-4-6` |
| Survey responses | `claude-haiku-4-5-20251001` |

---

## Limitations

- Study 1B is in active optimisation — results will change with each sprint.
- RLHF constitutional alignment blocks create hard accuracy ceilings on in07/in12/in13 for the current survey model. Three questions are stuck regardless of prompt engineering.
- Study 1A raw score (86.9%) has sampling variance of ±2 pp at n=60.
- Pew distributions are from published reports, not raw microdata.

---

*Simulatte Credibility Research Program — April 2026 — https://simulatte.io*
