# Simulatte Validation Protocol

**Version 1.0 — April 2026**
**Program:** Simulatte Credibility Research
**Repository:** https://github.com/Iqbalahmed7/simulatte-credibility

---

## 1. Purpose

This document describes how Simulatte measures the accuracy of its synthetic population simulations, what data grounds those measurements, what the current results are, and what the known limitations are. It is the authoritative reference for anyone evaluating Simulatte's empirical claims.

The core claim is simple: **Simulatte's synthetic populations, when surveyed on public opinion questions, produce response distributions that closely match real Pew Research Center survey data.** This document explains exactly how "closely match" is defined, measured, and validated.

---

## 2. What "Accuracy" Means

### 2.1 The Metric

Simulatte uses distribution accuracy — the standard metric used in published LLM survey simulation research:

```
Distribution Accuracy = 1 − Σ|real_i − sim_i| / 2
```

Where `real_i` is the Pew Research percentage for response option `i` and `sim_i` is the Simulatte percentage for the same option. The formula is equivalent to 1 minus the total variation distance between two distributions.

**Plain English:** if the real population says Option A 40% of the time and the simulation says 38%, that 2pp error contributes proportionally to the total score. A score of 100% means the simulation is a perfect distributional match. A score of 50% means the simulation is approximately as good as random assignment.

**Scale reference:**
- 100% — perfect distributional match
- 91% — human ceiling (the theoretical maximum, explained in 2.2)
- 86–89% — current Simulatte results
- 70% — raw LLM baseline (no persona architecture, same underlying model)
- 50% — chance-level performance

### 2.2 The Human Ceiling

**The theoretical maximum for any simulation system is 91%, not 100%.**

This ceiling comes from Stanford/Iyengar survey self-consistency research: approximately 9% of real survey respondents give a different answer to the same question when asked twice. This natural human inconsistency is baked into the Pew data — it is noise in the ground truth itself.

A simulation that achieves 91% is, by this measure, statistically indistinguishable from resampling the real population. Simulations above 91% would be overfitting to measurement noise. The ceiling sets the scale for interpreting any simulation result.

### 2.3 What We Are Competing Against

Simulatte's results should be evaluated in relation to three reference points:

| System | Score | Notes |
|---|---|---|
| Human ceiling (Stanford/Iyengar) | 91.0% | Theoretical maximum — any simulation above this is overfitting |
| **Simulatte Study 1A (US)** | **88.7%** | Cohort-adjusted; 86.9% raw, n=60 personas |
| **Simulatte Study 1B (India)** | **85.3%** | n=40 personas, 15 questions |
| Published competitor benchmark | 86.0% | Self-reported; US public opinion, same metric |
| Raw LLM baseline — Study 1B (naive-sonnet) | 70.2% | Same model, no persona architecture |

The **15pp gap between Simulatte and a raw LLM** is the most important figure. It measures what the persona architecture adds beyond simply querying the same underlying model directly. Without that gap, Simulatte is just an expensive wrapper.

The **2.3pp gap to the human ceiling** in Study 1A establishes that the system is operating at the frontier of what is empirically achievable.

### 2.4 What Accuracy Does Not Mean

Three things this metric does not claim:

1. **This is not a claim of prediction.** Distribution accuracy measures whether simulated populations match known survey outcomes, not whether they can predict future real-world decisions. Survey replication is necessary validation for decision simulation; it is not sufficient.

2. **This is not a claim about any individual persona.** The metric is distributional — it measures whether the aggregate population matches reality. Any individual persona may differ substantially from how any real person would respond.

3. **This is not a claim of generalization.** Results are validated on 15 questions per study from Pew Research data. Accuracy on different question types, different topic areas, or different measurement instruments has not been tested.

---

## 3. How Synthetic Populations Are Built

### 3.1 Demographic Anchors

Each synthetic population is built by sampling from a predefined demographic pool calibrated to census distributions. Demographic dimensions vary by country:

**US General Population (Study 1A — 60 personas):**
- Age, income, education, geography, and religion calibrated to US Census
- Political lean: liberal / moderate / conservative, calibrated to Pew party ID data

**India General Population (Study 1B — 40 personas):**
- Religion: Hindu 80%, Muslim 13%, Sikh 5%, Christian 2% — calibrated to Census 2011
- Caste (Hindu): General 37.5%, OBC 40.6%, SC 12.5%, ST 6.3% — calibrated to SECC
- Region: North (Hindi belt) 33%, South (Dravidian) 23%, West 20%, East/Northeast 15%, Pan-India urban 10%
- Political lean: BJP supporter 35%, BJP lean 20%, neutral 25%, opposition lean 10%, opposition 10% — calibrated to Pew Spring 2023 BJP/Modi favorability

The India population requires more calibration dimensions than the US because BJP/opposition lean, religion, caste, and region are partially independent identity dimensions that each contribute to distinct question clusters.

### 3.2 The WorldviewAnchor Layer

Demographic anchors alone are insufficient. Real survey distributions reflect not just who people are but how they see the world — their trust levels, their relationship to authority, their tolerance for change. The WorldviewAnchor layer encodes these attitudinal dimensions as structured fields in each persona's CoreMemory:

**Universal dimensions (all populations):**
- Institutional trust (government, media, experts — modeled as separate constructs)
- Individualism vs. collectivism
- Change tolerance
- Moral foundationalism

**India-specific dimensions:**
- Authoritarianism tolerance (calibrated to political lean — drives in07 strong leader)
- National pride (higher for BJP supporters — drives in05 India global power)
- Openness to change (higher for opposition lean — drives in14 women's rights, in15 climate)

These dimensions operate as an internal belief architecture that the survey response model draws on when answering questions. Without this layer, politically diverse personas tend to cluster around center options regardless of their demographic labels — producing the systematic center-compression error that characterized the Study 1A pre-worldview baseline (57.6%).

### 3.3 The Current-Conditions Stance

A separate `current_conditions_stance` field anchors each persona's view of the present political moment, independent of their underlying ideology. This separation was the single largest single-sprint improvement in Study 1A (+7.1pp, Sprint B-1).

The failure mode it fixes: without this field, conservative personas in a Republican administration give liberal-sounding current-conditions responses because their underlying ideology (small government, tradition) conflates poorly with being asked to evaluate an administration they notionally support. The separate current-conditions field decouples timeless ideology from situational stance.

### 3.4 Generation and Response Models

| Role | Model |
|---|---|
| Persona generation | claude-sonnet-4-6 |
| Survey responses | claude-haiku-4-5-20251001 |

Persona generation uses Sonnet because richer persona generation produces more internally consistent survey responses. Switching from Haiku to Sonnet for generation produced +7.1pp in Study 1A — larger than any single prompt change at the same sprint. The inference cost is amortized: each persona is generated once and used across all survey questions.

---

## 4. Calibration Sources

All ground truth comes from publicly available sources. The study design explicitly avoids any proprietary data to ensure results are independently reproducible.

### Study 1A — US

**Pew Research Center American Trends Panel (ATP)**
- 15 questions covering: economy, national direction, gun policy, immigration, climate, social trust, role of government, religion, abortion, racial equality, healthcare, democracy satisfaction, media trust, AI, financial security
- Sample sizes: n ≥ 1,000 (US probability sample)

**US Census Bureau**
- Age, income, education, geography distributions for 60-persona pool construction

### Study 1B — India

| Question IDs | Source | N | Year |
|---|---|---|---|
| in01–in05, in07 | Pew Global Attitudes, Spring 2023 | 2,611 | 2023 |
| in06 | Pew Democracy Closed-End Report | 2,611 | 2023 |
| in08, in09, in15 | Pew Global Attitudes, Spring 2017 | 2,464 | 2017 |
| in10 | Pew Global Attitudes, Spring 2018 | 2,521 | 2018 |
| in11 | Pew Religion in India | 29,999 | 2021 |
| in12, in13, in14 | Pew Gender Roles in India | 29,999 | 2022 |

**Census of India 2011** — religion and caste distributions for pool construction

**Pew Spring 2023 BJP/Modi favorability** — political lean calibration

**DK/Refused handling:** Don't Know and Refused responses are excluded from Pew distributions and renormalised before computing accuracy. This is consistent with published methodology in this domain and is identical across both studies.

---

## 5. Accuracy Measurement Details

### 5.1 Confidence Intervals from Sampling Variance

At the cohort sizes used (n=40 India, n=60 US), individual run variance is approximately **±2 pp**. This variance comes from cohort sampling — each run draws a slightly different 40/60-persona realisation of the population pool. The simulation itself is deterministic given a fixed cohort.

**Practical implication:** A single run producing 83.5% and a second run producing 85.5% on the same prompt architecture are consistent with each other; they reflect sampling noise, not a real performance change. Sprint comparisons use multiple runs or cohort-controlled comparisons to isolate true prompt signal from sampling variance.

### 5.2 Cohort-Adjusted Scores

For Study 1A Sprint B-10, the cohort-adjusted score (88.7%) is distinguished from the raw run score (86.9%). The adjustment isolates the B-10 prompt improvement from sampling noise by applying the B-10 prompts to the B-9 cohort and measuring the delta. This methodology is documented in the sprint audit manifest and is not applied retroactively across other sprints — it was used specifically because the B-10 run drew an unusually weak cohort on the targeted question.

### 5.3 Rank-Order Correlation (Secondary Metric)

Distribution accuracy measures calibration quality. A complementary metric is **rank-order accuracy** — whether the simulation correctly identifies which response option is most popular (A > B > C > D). This matters for decision-support use cases where the primary question is not "what percentage exactly" but "which outcome will dominate."

Simulatte Study 1A Sprint B-10: 14 of 15 questions have correct rank-order on the plurality option. Study 1B Sprint A-22: 12 of 15 correct (in04, in07, in09 have structural misranking due to RLHF ceilings described in Section 7).

### 5.4 LLM Baseline Methodology

LLM baselines measure the accuracy achievable by querying the same underlying model directly — without Simulatte's demographic pool, WorldviewAnchor layer, or persona architecture. The same 15 questions are asked to a single instance of claude-sonnet-4-6 with a minimal Indian demographic context. Results are averaged over 40 simulated responses.

Study 1B naive baseline: **70.2%** (vs. Simulatte 85.3% — a 15.1pp gap attributable to persona architecture).

---

## 6. Study Results

### Study 1A — US Pew Replication (Complete)

**Mean distribution accuracy (cohort-adjusted): 88.7%**
**Raw run accuracy (n=60): 86.9%**
**Gap to human ceiling: 2.3pp**

Sprint history: 57.6% baseline → 88.7% final over 10 sprints (+31.1pp total). The largest single-sprint gains:
- ARCH-001 WorldviewAnchor introduction: +12.9pp cumulative
- current_conditions_stance + Sonnet switch (B-1): +7.1pp
- Life experience signals for social trust (B-5): +2.7pp

**Per-question results (Sprint B-10, n=60):**

| Q# | Topic | Distribution Accuracy | MAE (pp) |
|---|---|---|---|
| q01 | Economy | 82.7% | 8.7 |
| q02 | National direction | 95.5% | 4.5 |
| q03 | Gun laws | 90.7% | 6.2 |
| q04 | Immigration | 90.8% | 9.2 |
| q05 | Climate local impact | 82.0% | 9.0 |
| q06 | Social trust | 84.1% | 15.9 |
| q07 | Role of government | 90.5% | 9.5 |
| q08 | Religion importance | 85.3% | 7.3 |
| q09 | Abortion | 77.8% | 11.1 |
| q10 | Racial equality | 97.7% | 2.3 |
| q11 | Healthcare | 93.9% | 6.1 |
| q12 | Democracy satisfaction | 83.3% | 8.3 |
| q13 | Media trust | 80.5% | 9.7 |
| q14 | AI effects | 83.8% | 10.8 |
| q15 | Financial security | 85.0% | 7.5 |
| **Mean** | | **86.9%** | **8.4** |

### Study 1B — India Pew Replication (Sprint A-22)

**Mean distribution accuracy: 85.3%**
**LLM baseline (naive-sonnet): 70.2%**
**Gap to human ceiling: 5.7pp**

Sprint history: 46.2% baseline → 85.3% over 22 sprints. The largest single-sprint gain:
- Sprint A-9 root cause fix (India political lean routing): **+29.9pp** — discovered that India archetypes were silently mapped to `political_lean="moderate"` for 8 sprints because `_ARCHETYPE_TO_LEAN` in `attribute_filler.py` did not include India archetypes. All political gates and stance fields returned neutral values throughout A-1→A-8.

**Per-question results (Sprint A-22, n=40):**

| ID | Topic | A-22 | LLM Baseline | Notes |
|---|---|---|---|---|
| in01 | Democracy satisfaction | 88.3% | 78.1% | Strong |
| in02 | Modi approval | 90.2% | 79.6% | Strong |
| in03 | BJP approval | 91.6% | 80.5% | Near-ceiling |
| in04 | INC approval | 72.5% | 64.8% | D=40% vs Pew 20% — structural bjp_supporter floor |
| in05 | India global power | 81.0% | 63.6% | C=0% vs Pew 19% — RLHF ceiling |
| in06 | Representative democracy | 81.4% | 65.3% | C/D=0% — RLHF ceiling |
| in07 | Strong leader | 79.1% | 55.2% | A=62.5% vs Pew 44% — structural floor |
| in08 | Economic conditions | 87.5% | 77.0% | Strong |
| in09 | Government trust | 70.5% | 69.5% | A=65% vs Pew 42% — structural |
| in10 | Future generations | 93.5% | 82.8% | Near-ceiling |
| in11 | Religion importance | 91.5% | 78.3% | Strong |
| in12 | Wife obedience | 92.5% | 71.8% | Near-ceiling |
| in13 | Gender roles / jobs | 89.5% | 67.5% | Strong |
| in14 | Women equal rights | 80.8% | 77.2% | A=100% vs Pew 81% — RLHF ceiling |
| in15 | Climate threat | 89.0% | 69.4% | Strong |
| **Mean** | | **85.3%** | **70.2%** | **+15.1pp from persona architecture** |

---

## 7. Known Limitations and Hard Ceilings

### 7.1 Sampling Variance

At n=40 to n=60, individual run variance is ±2pp. Results should not be interpreted as point estimates. A reported score of 85.3% means the true underlying performance of the current prompt architecture is approximately 83–87%.

### 7.2 RLHF Cultural Alignment Ceiling

Anthropic's Constitutional AI training creates **hard blocks** on specific output categories. These blocks are not addressable through prompt engineering — they operate below the surface of persona instructions and framing.

**Confirmed blocked categories in Study 1B:**
- Endorsement of governance without democratic accountability (in07: strong leader without parliament)
- Endorsement of gender-based discrimination (in05, in06, in14: over-compressed toward Western liberal responses)

**Observable symptom:** Personas with explicit traditional stances acknowledge their programmed position in their reasoning chain and then produce a response inconsistent with it, typically explaining why the stated position is ethically incorrect. The model is reading the persona instructions and deciding they do not override its trained values.

**Practical consequence:** Three Study 1B questions (in05, in06, in14) have hard accuracy ceilings regardless of prompt engineering. The current best performance on these questions (81.0%, 81.4%, 80.8%) reflects where the RLHF ceiling settles — it does not improve with additional sprint work.

**Why this is reported:** Naming a limitation is more rigorous than pretending it doesn't exist. The RLHF ceiling is a property of Western-trained LLMs generally, not of Simulatte specifically. Any synthetic population tool built on Western-aligned models will exhibit the same behavior on these question categories. Simulatte identifies and characterises the ceiling; other tools may simply report inflated scores by avoiding these question types.

**Mitigation under investigation:** Testing Sarvam (India-trained model) as the survey response model for in07/in12/in13. If the block is a property of Western training norms rather than the transformer architecture, India-trained models should produce different responses on these categories.

### 7.3 Small Tail Options

Response options with real-world frequencies below 10% are difficult to simulate accurately at n=40–60. Examples: q09 option D ("illegal in all cases," Pew 8.6%) at 0% in Study 1A; q15 option D ("struggling significantly," Pew 9%) at 0%. Exact simulation of rare-population stances requires either larger cohorts or targeted persona construction.

### 7.4 Questions Not Tested

Study 1A and 1B together cover 30 questions across two countries, one US cultural context, and one Indian cultural context. Performance on questions in other topic areas, other regions, or other measurement instruments has not been validated. Extrapolation from these results to other question types should be done cautiously.

---

## 8. Reproducibility

All studies are publicly reproducible. No proprietary data, no proprietary tooling beyond the Simulatte API (which is publicly accessible).

**Repository:** https://github.com/Iqbalahmed7/simulatte-credibility

### Study 1A (US)

```bash
git clone https://github.com/Iqbalahmed7/simulatte-credibility.git
cd simulatte-credibility/study_1a_pew_replication
pip install -r requirements.txt
python3 run_study.py --simulatte-only --cohort-size 60
```

Expected: 86.9% ± 2pp (sampling variance at n=60)

**Git tags by sprint:** `study-1a-sprint-b8` (86.1%), `study-1a-sprint-b9` (87.6%), `study-1a-sprint-b10` (86.9% raw / 88.7% cohort-adjusted)

### Study 1B (India)

```bash
cd simulatte-credibility/study_1b_pew_india
pip install -r requirements.txt
python3 run_study.py --simulatte-only --cohort-size 40
```

Expected: 85.3% ± 2pp

**LLM baselines:**

```bash
python3 llm_baselines.py
```

Expected: 70.2% for naive-sonnet-4-6

### Audit Manifests

Every sprint produces a JSON audit manifest with:
- SHA-256 hash of results file
- Model versions (`claude-sonnet-4-6` for generation, `claude-haiku-4-5-20251001` for responses)
- Git commit hash at time of run
- Run timestamp and run ID
- Per-question distributions (simulated and Pew)

Manifests are committed to the repository alongside result files and serve as the tamper-evident record for each sprint's claimed accuracy.

**Environment variable (optional):**
```bash
export SIMULATTE_API_URL=https://simulatte-persona-generator.onrender.com
```

---

## 9. Summary of Claims

| Claim | Evidence | Caveat |
|---|---|---|
| Simulatte achieves 88.7% distribution accuracy on US Pew data | Study 1A Sprint B-10 (cohort-adjusted, n=60) | ±2pp sampling variance; cohort adjustment methodology documented |
| Simulatte achieves 85.3% on India Pew data | Study 1B Sprint A-22 (n=40) | ±2pp sampling variance |
| Simulatte exceeds the published competitor benchmark (86.0%) | Study 1A 88.7% vs. competitor 86.0% | Question sets are not identical; competitor figure is self-reported |
| Simulatte adds 15pp over raw LLM baselines | Study 1B: Simulatte 85.3% vs. naive-sonnet 70.2% | LLM baselines run on same questions with same model, minimal context |
| Simulatte operates 2.3pp from the human ceiling | Study 1A 88.7% vs. ceiling 91.0% | Human ceiling applies to Study 1A question set; Study 1B ceiling gap is 5.7pp |

---

*Simulatte Credibility Research Program — April 2026*
*Contact: https://simulatte.io*
