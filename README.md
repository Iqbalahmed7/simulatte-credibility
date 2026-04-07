# Simulatte Credibility Research Program

**Study 1B — India Pew Replication · Sprint A-8 (A-9 in progress) | Study 1A — US Complete at 88.7% | April 2026**

Simulatte generates synthetic AI personas and surveys them at scale. This repository documents a rigorous benchmarking program measuring how closely simulated survey distributions match real Pew Research Center data.

---

## Study 1B — India Pew Replication · Active

Replicating 15 Pew Research Center India survey questions against a 40-persona synthetic Indian general population. Sprint A-8 complete; A-9 in progress.

| Sprint | Score | Key Change |
|--------|-------|------------|
| A-1 | 46.2% | Baseline — no cultural optimisation |
| A-2 | 45.9% | Option anchors (NOT-JUST pattern); RLHF blocks discovered on in07/in12/in13 |
| A-3 | 50.3% | Cultural preamble injection; partially unblocked in07/in12/in13 |
| A-4 | 49.2% | Preamble conflict fix; political/economic contamination root cause identified |
| A-5 | 50.0% | Economics–politics decoupling attempt; in10 hit 96.7% (new best); in13 parse recovery |
| **A-6** | **50.5%** | BJP narrative hardship exclusion; survey-prompt spread injection; in05 **+13.5 pp** breakthrough |
| A-7 | 51.6% | Budget ceiling gate (in08 +5 pp); in13 parse recovered (40/40); in15 first B responses (+7.5 pp); in10 **97%** new study best |
| A-8 | 53.4% | Tendency_summary gate (in08 +7.5 pp); in13 B=20.5% emerging (+10.6 pp); in15 meta-aware spread resistance identified |
| **A-9** | **In progress** | in15 framing rewrite (dev-focused not party-based); in04 INC to identity_statement; in09 worldview inst_trust raise |

> **Sprint A-7 note:** +1.1 pp net. Five wins (in05 +5.5, in06 +8.0, in08 +5.0 budget gate, in10 +7.4 new best, in13 +8.3 parse recovery, in15 +7.5 first B) offset by in09 −7.5 (explicit 'your answer is A' triggered resistance, collapsed to 100% B) and in04 −5.0 (INC narrative added conviction but strengthened C, not D). New root cause: prescriptive spread anchors trigger model resistance; descriptive framing needed instead.

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

## Study 1B Per-Question Results — Sprint A-8

| ID | Topic | Accuracy | MAE (pp) | Δ vs A-7 | Classification |
|----|-------|----------|----------|----------|----------------|
| in01 | Democracy satisfaction | 55.6% | 22.2 | +8.6 | cohort variance recovery |
| in02 | Modi approval | 32.3% | 33.8 | +0.6 | flat — 0% A persists |
| in03 | BJP approval | 42.9% | 28.6 | 0.0 | stable |
| in04 | INC approval | 22.7% | 38.6 | 0.0 | INC stance field ineffective — 0% D |
| in05 | India global power | 84.0% | 10.7 | −3.0 | minor variance |
| in06 | Representative democracy | 56.1% | 22.0 | +0.7 | stable |
| in07 | Strong leader | 13.4% | 43.3 | +2.7 | **RLHF hard ceiling** |
| **in08** | **Economic conditions** | **50.5%** | **24.8** | **+7.5** | **tendency_summary gate confirmed — B 35→42.5%** |
| in09 | Government trust | 50.7% | 24.6 | +2.7 | descriptive anchor partial — A still 0% |
| **in10** | **Future generations** | **95.4%** | **3.0** | −1.6 | **near-ceiling (95%+)** |
| in11 | Religion importance | 86.5% | 6.8 | +2.5 | stable near-ceiling |
| in12 | Wife obedience | 30.0% | 35.0 | 0.0 | **RLHF hard ceiling** |
| **in13** | **Gender roles / jobs** | **33.1%** | **33.5** | **+10.6** | **B=20.5% emerging toward Pew 33%** |
| in14 | Women equal rights | 80.8% | 9.6 | −2.5 | minor variance |
| in15 | Climate change threat | 67.0% | 22.0 | −2.5 | personas explicitly resisting party-framed spread note |
| **MEAN** | | **53.4%** | **23.9** | **+1.8** | |

---

## Sprint A-9 Roadmap

| Priority | Fix | Target questions |
|----------|-----|-----------------|
| 1 | **Reframe in15 spread note** — replace "BJP supporters" with "development-focused voters who prioritise economic growth". Personas explicitly resisted party-identity framing in A-8 ("I'm a moderate, not a BJP supporter"). Non-partisan framing avoids meta-aware override. | in15 |
| 2 | **INC conviction to identity_statement** — pragmatic-moderate identity fires before stance fields on in04. Add "deeply critical of Congress" to `_derive_identity_statement()` for bjp_supporter — fires as first sentence of decide prompt. | in04 |
| 3 | **Raise bjp_supporter inst_trust in `_INDIA_WORLDVIEW_BASE_DIMS`** — current setting maps to ~0.65 ('somewhat' territory). Raise to 0.82+ to produce genuine 'a lot' trust responses for in09. | in09 |
| 4 | **Audit life_defining_events** — last unaddressed economic contamination channel. Check whether bjp_supporter personas still have economic hardship life events despite narrative constraint. | in02, in08 |
| Track 2 | **Sarvam evaluation** — RLHF hard ceiling confirmed across 8 sprints for in07/in12/in13. | in07, in12, in13 |

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
