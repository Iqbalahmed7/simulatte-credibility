# Research Brief — Reuters Institute Digital News Report Mirror (USA & UK)

**Project:** STU_003_reuters_digital_news_usa_uk
**Domain:** News consumption behaviour, platform trust, news avoidance
**Geography:** United States + United Kingdom
**Ground truth:** Reuters Institute Digital News Report 2024 (USA n=2,006; UK n=2,015)
**Approved by:** Morpheus (autonomous research — Stage 1 self-approval)
**Date:** 2026-04-13

---

## FACT TABLE

F01  USA overall news trust is 32% — among the lowest of 47 countries in the Reuters Institute 2024 survey.   [Reuters Institute Digital News Report 2024, USA]
F02  UK overall news trust is 36%, above USA but also below the global median of 40%.   [Reuters Institute Digital News Report 2024, UK]
F03  BBC is the most trusted news brand in the UK at 57% trust — but this has declined 8 points since 2019.   [Reuters Institute Digital News Report 2024, UK]
F04  In the USA, no single news brand exceeds 50% trust among the general public. Partisan media consumption means trust levels are strongly divided by political affiliation.   [Reuters Institute Digital News Report 2024, USA]
F05  Active news avoidance (sometimes or often avoiding news) is at 36% in the USA and 32% in the UK — both high by global standards.   [Reuters Institute Digital News Report 2024, USA/UK]
F06  Under-35s are substantially more likely to avoid news than over-55s in both countries: 46% of USA under-35s vs. 23% of over-55s report often avoiding news.   [Reuters Institute Digital News Report 2024, USA]
F07  Online sources (websites, apps) are the primary news access method for 75% of USA respondents and 79% of UK respondents — TV remains important but declining.   [Reuters Institute Digital News Report 2024, USA/UK]
F08  YouTube is used for news by 26% of USA respondents and 18% of UK respondents — more than traditional newspaper websites.   [Reuters Institute Digital News Report 2024, USA/UK]
F09  Podcasts are used as a news format by 30% of USA respondents (12% weekly) and 24% of UK respondents.   [Reuters Institute Digital News Report 2024, USA/UK]
F10  Social media news use is high but distrust is high simultaneously: 45% of USA respondents use social media for news, 63% rate it as a source they trust "not at all" or "not much".   [Reuters Institute Digital News Report 2024, USA]
F11  AI-generated news summaries: 53% of USA respondents say they would be concerned about AI writing news, though 38% say they would use AI summaries if offered.   [Reuters Institute Digital News Report 2024, USA]

G01  Whether the Persona Generator reproduces the under-35 vs. over-55 news avoidance gap (F06) from demographic inputs alone.
G02  Whether cross-country differences in trust levels (USA 32% vs. UK 36%) emerge from country-calibrated personas without explicit news trust calibration.
G03  Whether platform preference patterns (F07, F08, F09) align to the Reuters-documented distributions across demographic segments.
G04  Whether the simultaneous high-use / high-distrust pattern for social media (F10) is reproduced by personas without directly training on it.

---

## Study Objective

Test whether the Persona Generator reproduces Reuters Institute 2024 distributions for news trust, avoidance behaviour, and platform preference across USA and UK demographics. DA ≥ 91% against Reuters ground truth would establish a third independent validator for the Persona Generator — different publisher, different domain (media behaviour vs. political attitudes), existing Pew-validated geography.
