# Research Brief — Edelman Trust Barometer Mirror (USA)

**Project:** STU_001_edelman_trust_usa
**Domain:** Institutional and brand trust
**Geography:** United States
**Ground truth:** Edelman Trust Barometer 2024 (USA national sample, n=1,150 per wave)
**Approved by:** Morpheus (autonomous research — Stage 1 self-approval)
**Date:** 2026-04-13

---

## FACT TABLE

F01  Edelman Trust Barometer 2024 reports USA Trust Index at 49/100 — below the global average of 57.   [Edelman Trust Barometer 2024, USA]
F02  Business is the most trusted institution in the USA (61%), ahead of NGOs (58%), government (43%), and media (42%).   [Edelman Trust Barometer 2024, USA]
F03  USA media trust (42%) is among the lowest of the 28 countries surveyed, placing it in the "distrust" zone (<50).   [Edelman Trust Barometer 2024, USA]
F04  Government trust in the USA (43%) has remained in the distrust zone for six consecutive Edelman annual reports.   [Edelman Trust Barometer 2024, USA]
F05  "Informed public" (college-educated, high income, high media consumption) trusts institutions 15–20 points higher than the "mass population" in the USA — Edelman's documented "trust inequality" gap.   [Edelman Trust Barometer 2024, USA]
F06  CEO credibility as a spokesperson has declined: only 48% of US respondents say CEOs are credible spokespeople, down from 66% in 2019.   [Edelman Trust Barometer 2024, USA]
F07  Scientists and academic experts are the most credible information sources in the USA at 68% credibility.   [Edelman Trust Barometer 2024, USA]
F08  "My employer" is the most trusted entity for 77% of US respondents — higher than government, NGOs, or media.   [Edelman Trust Barometer 2024, USA]
F09  Business is expected to lead on societal issues (climate, workforce training, inequality) by 52% of US respondents who no longer believe government is capable.   [Edelman Trust Barometer 2024, USA]
F10  Social media platforms are distrusted by 63% of US respondents as a news source.   [Edelman Trust Barometer 2024, USA]

G01  Whether Simulatte's Persona Generator can reproduce the 15–20pp informed public vs. mass population trust gap (F05) without being explicitly calibrated to Edelman data.
G02  Whether trust distributions across institutional types (business, government, NGOs, media) are reproduced accurately by synthetic personas who have not been asked about Edelman specifically.
G03  Whether the employer trust premium (F08) emerges organically in persona responses when employment and workplace scenarios are presented.
G04  Whether trust differences correlate correctly with Edelman-documented demographic predictors (income, education, political lean).

---

## Study Objective

Test whether Simulatte's Persona Generator can reproduce Edelman Trust Barometer USA 2024 distributions across institutional trust types — without being calibrated to Edelman data. If DA ≥ 91% against published Edelman ground truth, this constitutes a second independent validator for the Persona Generator beyond Pew Research, across a different topic domain (brand/institutional trust vs. political attitudes).
