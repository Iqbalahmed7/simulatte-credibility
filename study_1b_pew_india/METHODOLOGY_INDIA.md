# Study 1B: Pew India Replication — Methodology

## Overview

Study 1B replicates the Simulatte credibility framework (established in Study 1A on US Pew data) against Indian public opinion surveys. The goal is to establish whether Simulatte's persona generation generalises from a Western liberal-democratic survey context to a large, religiously and linguistically diverse democracy.

**Benchmark target:** Match or exceed Study 1A result of 86.1% mean distribution accuracy.

---

## Ground Truth Sources

All distributions sourced from publicly available Pew Research Center reports:

| Question IDs | Source | N | Year |
|---|---|---|---|
| in01–in05, in07 | Pew Global Attitudes, Spring 2023 | 2,611 | 2023 |
| in06 | Pew Democracy Closed-End Report | 2,611 | 2023 |
| in08, in09, in15 | Pew Global Attitudes, Spring 2017 | 2,464 | 2017 |
| in10 | Pew Global Attitudes, Spring 2018 | 2,521 | 2018 |
| in11 | Pew Religion in India | 29,999 | 2021 |
| in12, in13, in14 | Pew Gender Roles in India | 29,999 | 2022 |

**DK/Refused handling:** Don't Know responses are excluded and distributions renormalised before computing accuracy. This matches Study 1A methodology.

---

## Question Set (15 questions)

| ID | Topic | Source Year |
|---|---|---|
| in01 | Democracy satisfaction | 2023 |
| in02 | Modi approval | 2023 |
| in03 | BJP approval | 2023 |
| in04 | INC/Congress approval | 2023 |
| in05 | India global power trajectory | 2023 |
| in06 | Representative democracy | 2023 |
| in07 | Strong leader without parliament | 2023 |
| in08 | Current economic conditions | 2017 |
| in09 | Trust in national government | 2017 |
| in10 | Future generations financial outlook | 2018 |
| in11 | Importance of religion | 2021 |
| in12 | Wife must obey husband | 2022 |
| in13 | Men's job priority when jobs scarce | 2022 |
| in14 | Women's equal rights importance | 2022 |
| in15 | Climate change threat | 2017 |

---

## Persona Pool

**Domain:** `india_general`
**Pool size:** 40 profiles
**Source:** `/Persona Generator/src/generation/demographic_sampler.py`

### Demographic composition

**Religion** (N=40):
- Hindu: 32 (80%) — Census 2011: 79.8%
- Muslim: 5 (13%) — Census 2011: 14.2%
- Sikh: 2 (5%) — slightly oversampled for signal
- Christian: 2 (5%) — slightly oversampled for signal

**Caste** (Hindu only):
- General: 12 (37.5%)
- OBC: 13 (40.6%) — SECC: ~41%
- SC: 4 (12.5%) — Census: ~16%
- ST: 2 (6.3%) — Census: ~9%

**Region** (N=40):
- North (Hindi belt, BJP stronghold): 13 (33%)
- South (Dravidian/regional parties): 9 (23%)
- West (Maharashtra/Gujarat): 8 (20%)
- East/Northeast: 6 (15%)
- Pan-India (young urban): 4 (10%)

**Political lean** (calibrated against Spring 2023 BJP/Modi favorability):
- bjp_supporter: 7 (18%) — BJP very favorable 42%
- bjp_lean: 8 (20%) — BJP somewhat favorable 31%
- neutral: 10 (25%) — pragmatic, issue-by-issue
- opposition_lean: 8 (20%) — INC somewhat favorable 37%
- opposition: 7 (18%) — BJP very unfavorable + strong INC

---

## Persona Generation

Each India persona is generated with:

1. **WorldviewAnchor** — four dimensions calibrated by political lean:
   - Authoritarianism tolerance (higher for BJP supporters → in07 strong leader)
   - Collectivism (higher for traditional/rural personas → in12/in13 gender norms)
   - National pride (higher for BJP supporters → in05 India global power)
   - Openness to change (higher for opposition → gender equality, climate)

2. **Political era:** "BJP government in power (Modi, 2014– second term from 2024)"

3. **Political lean statements** (system prompt injection):
   - `bjp_supporter`: Strong BJP support, Hindu cultural identity, centralized leadership
   - `bjp_lean`: BJP-positive, development focus, traditional values
   - `neutral`: Pragmatic, local issues, mixed views
   - `opposition_lean`: Democratic institutions, gender equality, regional party
   - `opposition`: Secular, minority rights, strong democracy

4. **Current conditions stance** (injected separately per Sprint B-1 fix):
   - BJP supporters: positive on economy, optimistic on India's trajectory
   - Opposition: skeptical of government claims, concerned about inequality

---

## Accuracy Metric

Identical to Study 1A (Artificial Societies Jan 2026 methodology):

```
Distribution Accuracy = 1 − Σ|real_i − sim_i| / 2
```

- Scale: 0–100%, higher is better
- Human benchmark ceiling: 91% (Stanford self-inconsistency baseline)
- Study 1A reference: 86.1% (US Pew, Sprint B-8, 60 personas, 15 questions)

---

## Reproduction Instructions

```bash
git clone https://github.com/Iqbalahmed7/simulatte-credibility.git
cd simulatte-credibility
pip install -r study_1b_pew_india/requirements.txt
cd study_1b_pew_india
python3 run_study.py --simulatte-only --cohort-size 40
```

The study calls the public Simulatte API — no access to the persona generator source code is required to reproduce.

**Environment variable (optional):**
```bash
export SIMULATTE_API_URL=https://simulatte-persona-generator.onrender.com
```

---

## Key Design Choices

**India vs. US differences:**
- US pool uses a single liberal/conservative axis; India requires BJP/opposition lean + religion + caste as distinct identity dimensions
- Religion is the strongest driver of in11 (religion importance) and interacts with in12/in13 (gender norms) and in02/in03 (political approval)
- Caste (SC/ST) drives economic anxiety and opposition lean, separate from religious identity
- Region (North vs. South) captures BJP stronghold vs. Dravidian resistance — North personas are more BJP-leaning, South more neutral/opposition

**Question selection rationale:**
- in02/in03 (Modi/BJP approval): highest diagnostic signal — 79% favorable vs. 21% unfavorable produces extreme skew that tests whether personas are politically differentiated
- in12 (wife obedience, 87% agree): tests whether personas can hold traditional gender norms even when educated — a real feature of Indian public opinion
- in14 (women equal rights, 94% important) paired with in12: tests the Indian paradox — respondents simultaneously endorse wife obedience and women's equal rights. Simulatte personas should replicate this tension.
- in07 (strong leader, 80% good): India is among the highest globally on this metric — tests whether personas are culturally calibrated vs. defaulting to Western liberal values
