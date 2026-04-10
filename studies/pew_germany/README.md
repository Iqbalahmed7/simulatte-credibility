# Study 1C — Germany European Benchmark

## Overview

Study 1C benchmarks Simulatte's ability to replicate population-level opinion distributions among German adults using 15 validated questions drawn from Pew Research Center's Global Attitudes and Western Europe surveys, cross-validated against the European Social Survey (ESS) Round 11.

This is the first Simulatte benchmark in a European cultural context and the first synthetic population study to explicitly model the East/West German divide as a calibration dimension.

| Parameter | Value |
|---|---|
| **Study** | Germany — Pew Global Attitudes + Pew Western Europe Survey |
| **Questions** | 15 (Pew Global Attitudes 2023/24 + Pew Western Europe 2017) |
| **Metric** | Distribution Accuracy = 1 − (Σ\|real_i − sim_i\| / 2) |
| **Human ceiling** | 91% (Iyengar et al., Stanford) |
| **Persona pool** | 40 demographically calibrated Germany personas |
| **Status** | 🔴 In setup — data acquisition phase |

## Why Germany

Germany is the most structurally complex European benchmark target:

1. **Six-party political landscape** — CDU/CSU, SPD, AfD, Greens, FDP, BSW. Wider partisan spread than any other European country. AfD at 18–20% creates a hard-right calibration challenge equivalent to India's BJP-supporter pool.
2. **East/West divide** — 35 years of GDR history produce measurably lower institutional trust, higher economic pessimism, stronger support for authoritarian governance, and near-zero religiosity in former East Germany. No equivalent in Study 1A or 1B.
3. **Muslim minority calibration** — ~5.5M residents of Turkish origin (~6.5% of population), mostly concentrated in West German cities. Religious identity intersects with integration attitudes in a way that mirrors India's Hindu-Muslim-caste complexity.
4. **Catholic/Protestant/Secular split** — Bavaria (strongly Catholic), northern Germany (Protestant majority), East Germany (atheist majority). Three distinct moral foundationalism baselines within one country.

## Data Sources

| Source | What it provides | Access |
|---|---|---|
| Pew Global Attitudes Spring 2024 | ~50 questions incl. Germany: democracy, economy, EU views, immigration, religion | Free: pewresearch.org/datasets |
| Pew Western Europe Survey 2017 | 15 countries, deep battery: religious identity, national identity, immigration, gender | Free: pewresearch.org/datasets |
| ESS Round 11 (2023/24) | 200+ questions, Germany N≈2,400, richest demographic variables | Free: europeansocialsurvey.org/data-portal |
| German Census 2022 (Zensus 2022) | Population weights for persona calibration | Free: destatis.de |

## Persona Pool Design

40 demographically calibrated Germany personas. See `pipeline/persona_pool.md` for full specifications.

| Dimension | Distribution | Source |
|---|---|---|
| Political lean | CDU/CSU 28% · SPD 16% · AfD 18% · Greens 11% · FDP 5% · BSW/left 8% · non-partisan 14% | Bundestagswahl 2025 + ESS R11 |
| Religion | Catholic 26% · Protestant 24% · Muslim 5% · None/atheist 42% · Other 3% | German Census 2022 |
| Region | West (non-Bavaria) 45% · Bavaria 15% · East (former GDR) 20% · Berlin 10% · North 10% | Census 2022 |
| Age | 18–34: 21% · 35–54: 35% · 55+: 44% | Census 2022 |
| Education | University/Hochschule 34% · Vocational (Ausbildung) 48% · Basic (Hauptschule) 18% | Census 2022 |
| Migration background | No migration background 74% · Turkish origin 3.5% · Other migration background 22.5% | Mikrozensus 2023 |

## WorldviewAnchor Adaptations

Germany requires three Germany-specific adaptations to the WorldviewAnchor layer used in Study 1A and 1B:

| Dimension | German calibration notes |
|---|---|
| Institutional trust | **Must be East/West split, not party-driven.** East Germans average 15–20 pp lower than West Germans on Bundesverfassungsgericht, Bundeswehr, and police trust — independent of political lean. A CDU voter in Saxony has lower institutional trust than an SPD voter in Bavaria. |
| Individualism | Germany sits between US (high individualism) and collectivist cultures. East/West split again: former GDR favours state solutions; West Germans favour market solutions. AfD voters reject both — nativist collectivism. |
| Change tolerance | Widest spread of any study: Greens voters at maximum change tolerance; AfD voters at minimum. The gap is ~60 pp in ESS data — wider than US partisan spread on equivalent questions. |
| Moral foundationalism | Near-zero in secular East Germany. High in Bavarian Catholic personas. Turkish-origin Muslim personas hold moderate-to-high foundationalism on gender/family questions only — construct must be disaggregated by domain. |

## Sprint Strategy

Target: 15–18 sprints. Budget: ~$33 total (Haiku early, Sonnet late, Batch API throughout).

| Phase | Sprints | Model | Purpose |
|---|---|---|---|
| Rapid iteration | C-1 to C-12 | Claude Haiku 4.5 (Batch) | Structural calibration — archetype mapping, pool composition, construct setup |
| Refinement | C-13 to C-18 | Claude Sonnet 4.6 (Batch) | Fine-tuning — option-vocabulary anchoring, East/West trust separation |

See `pipeline/sprint_runner.py` for the calibration script.

## Files

| File | Description |
|---|---|
| `questions.json` | 15 Germany questions with ground truth distributions |
| `pipeline/persona_pool.md` | Full 40-persona pool specification |
| `pipeline/sprint_runner.py` | Calibration sprint runner (Haiku/Sonnet switchable) |
| `pipeline/score.py` | Distribution accuracy scorer |
| `pipeline/data_prep.md` | Data acquisition and ground truth computation guide |
| `audit/verify.py` | SHA-256 integrity verifier (to be generated at first sprint) |
| `results/sprint_manifests/` | Per-sprint accuracy logs (C-1 onward) |
| `results/final_scores.json` | Final Simulatte response distributions (populated after ceiling sprint) |
| `results/comparison.json` | Simulatte vs ground truth comparison (populated after ceiling sprint) |

## Ground Truth Sources

- Pew Research Center Global Attitudes Survey, Spring 2024 (Germany N≈1,000)
- Pew Research Center Western Europe Survey, 2017 (Germany N≈1,600)
- European Social Survey Round 11, 2023/24 (Germany N≈2,400) — cross-validation
- German Census 2022 (Zensus 2022) — demographic weights

## Related Studies

- [Study 1A — US Pew (88.7%)](../pew_usa/)
- [Study 1B — India Pew (85.3%)](../pew_india/)
- [LLM Comparison](../llm_comparison/)
