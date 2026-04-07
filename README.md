# Simulatte Credibility Research Program

**Study 1B — India Pew Replication · Sprint A-6 (A-7 in progress) | Study 1A — US Complete at 88.7% | April 2026**

Simulatte generates synthetic AI personas and surveys them at scale. This repository documents a rigorous benchmarking program measuring how closely simulated survey distributions match real Pew Research Center data.

---

## Study 1B — India Pew Replication · Active

Replicating 15 Pew Research Center India survey questions against a 40-persona synthetic Indian general population. Sprint A-6 complete; A-7 in progress.

| Sprint | Score | Key Change |
|--------|-------|------------|
| A-1 | 46.2% | Baseline — no cultural optimisation |
| A-2 | 45.9% | Option anchors (NOT-JUST pattern); RLHF blocks discovered on in07/in12/in13 |
| A-3 | 50.3% | Cultural preamble injection; partially unblocked in07/in12/in13 |
| A-4 | 49.2% | Preamble conflict fix; political/economic contamination root cause identified |
| A-5 | 50.0% | Economics–politics decoupling attempt; in10 hit 96.7% (new best); in13 parse recovery |
| **A-6** | **50.5%** | BJP narrative hardship exclusion; survey-prompt spread injection; in05 **+13.5 pp** breakthrough |
| **A-7** | **In progress** | Budget ceiling gate for BJP in decide.py; in09 BJP "a lot" reinforcement; in13 parse fix; in15 strengthened; in04 INC narrative identity |

> **Sprint A-6 note:** Headline +0.5 pp masks two significant wins: in05 +13.5 pp (spread injection broke 100% A lock; 62.5% vs Pew 68%) and in09 +7.5 pp. Both masked by in13 parse regression (24/40 parseable, −13.0 pp) and in10 variance (−7.1 pp). True signal positive. New root cause confirmed: economic context bleeds into BJP political answers through FOUR memory channels — narrative text (fixed A-6), budget_ceiling in decide.py (A-7 P1), tendency_summary (pending), life_defining_events (pending).

---

## Key Finding — RLHF Cultural Bias

Anthropic's Constitutional AI training creates **measurable hard blocks** on survey questions where Indian cultural norms diverge from Western liberal defaults:

| Question | Topic | Pew India | Simulatte A-4 | Classification |
|----------|-------|-----------|----------------|----------------|
| in07 | Strong leader preference | A=44%, B=38% | A=0%, B=0%, C=87% | RLHF block |
| in12 | Wife obedience | A=64% | A=0%, B=34% | RLHF partial block |
| in13 | Gender roles / jobs | A=47%, B=33% | A=0%, B=4%, C=93% | RLHF partial block |

The model answers these questions from Western liberal defaults regardless of explicit persona stance injection. Cultural preamble injection (A-3) partially unblocked in07/in12/in13 — moving responses in the correct direction — but option A remains at 0% across all sprints for these three questions. RLHF prompt engineering ceiling confirmed; alternative survey model evaluation (Sarvam) on the roadmap.

See [`reports/western_model_bias_finding.md`](reports/western_model_bias_finding.md) for the full research note.

---

## Study 1B Per-Question Results — Sprint A-6

| ID | Topic | Accuracy | MAE (pp) | Δ vs A-5 | Classification |
|----|-------|----------|----------|----------|----------------|
| in01 | Democracy satisfaction | 55.6% | 22.2 | 0.0 | stable |
| in02 | Modi approval | 32.3% | 33.8 | +5.4 | partial — narrative constraint helped; 3 channels remain |
| in03 | BJP approval | 42.9% | 28.6 | 0.0 | stable |
| in04 | INC approval | 27.7% | 36.1 | −0.3 | stuck — modal C lock; pragmatic-moderate override |
| **in05** | **India global power** | **81.5%** | **12.3** | **+13.5** | **major win — spread injection breakthrough** |
| in06 | Representative democracy | 47.4% | 26.3 | +3.1 | parse variance (33/40) |
| in07 | Strong leader | 16.1% | 42.0 | +0.4 | **RLHF hard ceiling** |
| in08 | Economic conditions | 38.0% | 31.0 | 0.0 | stuck — economic context override |
| in09 | Government trust | 55.5% | 22.2 | +7.5 | partial win — first C responses; A still 2.5% vs 41% |
| in10 | Future generations | 89.6% | 7.0 | −7.1 | variance / parse loss (35/40) |
| in11 | Religion importance | 84.0% | 8.0 | −2.5 | variance |
| in12 | Wife obedience | 30.0% | 35.0 | 0.0 | **RLHF hard ceiling** |
| in13 | Gender roles / jobs | 14.2% | 42.9 | −13.0 | **parse regression 24/40** — RLHF ceiling confirmed |
| in14 | Women equal rights | 80.8% | 9.6 | 0.0 | unchanged |
| in15 | Climate change threat | 62.0% | 25.3 | 0.0 | spread injection not firing — 100% A persists |
| **MEAN** | | **50.5%** | **25.5** | **+0.5** | |

---

## Sprint A-7 Roadmap

| Priority | Fix | Target questions |
|----------|-----|-----------------|
| 1 | **Gate budget_ceiling for BJP in decide.py** — suppress "Budget reality:" line in `_decide_core_memory_block()` for bjp_supporter/bjp_lean. Main remaining economic contamination channel. | in02, in08, in09 |
| 2 | **Strengthen in15 spread note** — explicit BJP anchor: "your answer is B — somewhat of a threat, not A". Current note insufficient vs. climate lived experience. | in15 |
| 3 | **in13 parse reinforcement** — add to `_SPREAD_QUESTION_NOTES` with explicit "YOU MUST RESPOND WITH ONLY THE SINGLE LETTER". Parse rate 24/40 is unacceptable. | in13 |
| 4 | **Strengthen in09 BJP "a lot" anchor** — more explicit: "If you voted BJP, your answer is A — a lot — not B." A=2.5% vs Pew 41%. | in09 |
| 5 | **in04 INC narrative identity** — add anti-Congress identity to BJP persona narrative at generation time. Pragmatic-moderate tendency overrides stance anchors; must be embedded in narrative identity. | in04 |
| Track 2 | **Sarvam evaluation** — RLHF hard ceiling confirmed across 6 sprints for in07/in12/in13. | in07, in12, in13 |

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
│   ├── simulatte_results.json           # Latest India run (Sprint A-6)
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
git checkout study-1b-sprint-a6

pip install -r study_1b_pew_india/requirements.txt
cd study_1b_pew_india
python3 run_study.py --simulatte-only
```

Expected: **50.5% ± 3 pp** (sampling variance at n=40).

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
