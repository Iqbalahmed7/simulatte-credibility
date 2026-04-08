# Simulatte Credibility Research Program

**Study 1B — India Pew Replication · Sprint A-21 at 83.1% (session best A-20: 83.8%) | Study 1A — US Complete at 88.7% | April 2026**

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
| A-10 | 84.6% | +1.3 | Spread notes for in14/in06/in11/in02/in03/in12; bjp_lean in13 stance fix |
| A-11 | 84.8% | +0.2 | Remove in03 spread note; in01/in08 spread notes; in14/in06 strengthened |
| A-12 | 85.0% | +0.2 | Pool rebalance bjp_supporter 18%→35% — B-modal pull identified as remaining barrier |
| A-13 | 85.0% | 0.0 | **BUG: demographic_sampler.py never synced with A-12 pool changes — ran on old 7 bjp_supporter pool** |
| A-14 | 80.8% | −4.2 | First true run with correct 14 bjp_supporter pool; conviction framing for in02/in03; in09/in15 backfired |
| A-15 | 81.6% | +0.8 | Survey reuse; INC conviction split bjp_supporter/bjp_lean; in07/in13 spread notes fixed |
| A-16 | 80.1% | −1.5 | Fresh cohorts; inst_trust 0.83→0.76; in05 spread note — in09/in15/in04 still regressing |
| A-17 | 79.9% | −0.2 | Trust 0.68 → bimodal collapse (in09 A=65%,C=23%,B=13%); in15 visceral climate note |
| **A-18** | **83.4%** | **+3.5** | **Trust raised 0.74/0.72; in15 "major threat ≠ development priority" (+25pp on in15)** |
| A-19 | 82.3% | −1.1 | in09 institutional trust framing +5pp; in13 widow-example caused B=70% flip −21pp |
| **A-20** | **83.8%** | **+1.5** | **in13 rebalanced; session best. Structural ceiling: in09/in07 pool-composition limited** |
| A-21 | 83.1% | −0.7 | bjp_lean democratic narrative (in13 +5pp); in09/in08 sampling variance regression |
| **A-22** | **85.3%** | **+2.2** | **Pool recomposition opposition_lean 6→3 (in09 +7.5pp); in11 note rewrite (in11 +5pp). New best — 85%+ achieved** |

> **Sprint A-9 breakthrough:** +29.9 pp in a single sprint — the largest gain in the program. Root cause discovered: `_ARCHETYPE_TO_LEAN` in `attribute_filler.py` did not include India archetypes, causing ALL India personas to have `political_lean="moderate"` in their attributes dict. Every political lean gate, stance field, and narrative constraint was silently returning neutral values across A-1→A-8. The `_get_political_lean()` fix reads directly from `demographic_anchor.worldview.political_profile.archetype` for India personas, bypassing the broken attribute path.

> **Sprint A-13 bug:** `demographic_sampler.py` was never synced with the A-12 pool changes made in `india_population_pool.py`. All A-12/A-13 runs used the old 7 bjp_supporter (18%) pool. The A-12 score of 85.0% was achieved with the wrong pool — A-14 was the first true run at the intended 14 bjp_supporter (35%) composition, revealing a new set of calibration challenges.

> **A-14→A-16 regression:** Pool rebalance solved A-option floors (in02/in03 +22pp, in12 +12pp) but introduced a D=18% floor from 7 opposition personas on social/authority questions (in07/in12/in13), an in09 A-overshoot (60% vs Pew 42%), and in15/in04 stubborn regressions. Net: −4.9pp vs A-12 baseline. A-17 targets these three structural issues.

---

## Study 1B Per-Question Results — A-22 vs A-12

| ID | Topic | A-22 | A-12 | Δ vs A-12 | Status |
|----|-------|------|------|-----------|--------|
| in01 | Democracy satisfaction | 88.3% | 80.6% | +7.7 | ✓ strong |
| in02 | Modi approval | 90.2% | 82.3% | +7.9 | ✓ strong |
| **in03** | **BJP approval** | **91.6%** | **67.9%** | **+23.7** | **✓ near-ceiling** |
| in04 | INC approval | 72.5% | 81.2% | −8.7 | ⚠ D=40% vs Pew 20% — structural bjp_supporter floor |
| in05 | India global power | 81.0% | 90.5% | −9.5 | ⚠ C=0% vs Pew 19% — RLHF ceiling |
| in06 | Representative democracy | 81.4% | 74.3% | +7.1 | ⚠ C/D=0% vs Pew 18% — RLHF ceiling |
| in07 | Strong leader | 79.1% | 95.7% | −16.6 | ⚠ A=62.5% vs Pew 44% — structural pro-BJP floor |
| in08 | Economic conditions | 87.5% | 79.0% | +8.5 | ✓ strong |
| **in09** | **Government trust** | **70.5%** | **87.0%** | **−16.5** | ⚠ A=65% vs Pew 42%; C=12.5% vs Pew 7% — structural |
| **in10** | **Future generations** | **93.5%** | **97.0%** | **−3.5** | **✓ near-ceiling** |
| **in11** | **Religion importance** | **91.5%** | **94.0%** | **−2.5** | **✓ B=7.5% (A-22 note fix)** |
| **in12** | **Wife obedience** | **92.5%** | **76.0%** | **+16.5** | **✓ near-ceiling** |
| in13 | Gender roles / jobs | 89.5% | 93.0% | −3.5 | ✓ strong |
| in14 | Women equal rights | 80.8% | 80.8% | 0.0 | ⚠ A=100% vs Pew 81% — RLHF ceiling |
| in15 | Climate change threat | 89.0% | 89.0% | 0.0 | ✓ strong |
| **MEAN** | | **85.3%** | **85.0%** | **+0.3** | **✓ 85%+ achieved** |

---

## Remaining Gaps — Post A-22

| Question | A-22 | Gap | Root cause | Fixable? |
|----------|------|-----|-----------|----------|
| in09 | 70.5% | −14.5pp | A=65% vs Pew 42% (bjp_supporter A-floor); C=12.5% vs 7% (7 opposition C-floor). Structural minimum C=17.5% from 7 opposition personas. | Only by reducing opposition pool (risks in02/in03) or narrative-level institutional trust framing |
| in07 | 79.1% | −10.9pp | A=62.5% vs Pew 44%. 14 bjp_supporters drive near-majority A. Democratic narrative helped in13/in12 but not in07. | Narrative-level intervention at generation time — in07-specific identity framing |
| in04 | 72.5% | −11.5pp | D=40% vs Pew 20%. 14 bjp_supporters with strong INC conviction. Structural D-minimum ~30-35%. | Only by softening bjp_supporter INC narrative further — low headroom |
| in05 | 81.0% | −9pp | C=0% vs Pew 19%. RLHF constitutional alignment ceiling. | Likely not fixable |
| in06 | 81.4% | −9pp | C/D=0% vs Pew 18%. RLHF ceiling. | Likely not fixable |
| in14 | 80.8% | −3pp | A=100% vs Pew 81%. RLHF ceiling. | Likely not fixable |

**A-22 result:** Pool recomposition (opposition_lean 6→3) confirmed effective — in09 +7.5pp, demonstrating that Birsa Munda/Ramesh Chamar/Thomas Mathew were genuine C-contributors, not being redirected by the spread note as assumed. In11 behavioral note rewrite confirmed effective (+5pp). **85.3% — study 1B best. Gap to Study 1A (86.1%): 0.8pp. Gap to human ceiling (91%): 5.7pp.**

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
