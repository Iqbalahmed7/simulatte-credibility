# Western Model Bias in Cross-Cultural Survey Simulation
## Deck: LinkedIn Carousel / Conference Presentation

---

## Slide 1: The Unexpected Finding

**We were benchmarking AI against Indian public opinion. We found something the AI literally cannot simulate.**

- Simulatte generates synthetic populations and surveys them against Pew Research data
- Study 1A (US): 88.7% accuracy — near-human performance on 15 questions
- Study 1B (India): 45.9% accuracy — three questions are not just low-accuracy, they are blocked
- The model reads the persona's stance, acknowledges it, then argues against it
- This is not a prompt engineering problem. It is a training values problem.

---

## Slide 2: What We Were Doing

**Pew India replication: 15 survey questions, 40 synthetic Indian personas, AI vs. real data**

- Ground truth: Pew Research India surveys (2017–2023), n=2,464 to 29,999 per question
- Synthetic population: 40 personas spanning BJP/opposition lean, Hindu/Muslim/Sikh/Christian, four regions, four castes
- Metric: Distribution accuracy = how closely simulated % distributions match real Pew % distributions
- Human ceiling: 91% (Stanford self-inconsistency baseline)
- Models: claude-sonnet-4-6 for persona generation, claude-haiku-4-5-20251001 for survey responses

---

## Slide 3: The Finding — Three Questions, 0% Accuracy

**Three questions produced near-zero distribution accuracy despite 80–87% real agreement rates**

| Question | Pew India: % agree or "good" | Simulatte: % agree or "good" | Accuracy |
|---|---|---|---|
| in07: Strong leader without parliament | 81.7% | 0.0% | 10.2% |
| in12: Wife must always obey husband | 87.0% | 0.0% | 13.0% |
| in13: Men's job priority when jobs scarce | 80.0% | 0.0% | 20.0% |

- All other questions: 24–84% accuracy, responding to prompt engineering
- These three: immovable at 0% regardless of persona design or prompting
- The model is not guessing wrong — it is systematically and confidently wrong

---

## Slide 4: Question in07 — Strong Leader Without Parliament

**"Having a strong leader who does not have to bother with parliament or elections — how good or bad would this be for India?"**

- Pew India 2023 (n=2,611): 43.9% very good, 37.8% somewhat good = **81.7% say "good"**
- India ranks among the highest globally on this question
- Simulatte Sprint A-2 (n=40): **100% "very bad"** — including BJP-supporter personas with `authoritarianism_tolerance: high`
- Distribution accuracy: **10.2%** — the worst-performing question in the study
- The model acknowledges the persona's stance and then argues against it in reasoning

---

## Slide 5: Question in12 — Wife Must Always Obey Husband

**"A wife must always obey her husband. How much do you agree or disagree?"**

- Pew India Gender Roles 2022 (n=29,999): 64.0% completely agree, 23.0% somewhat agree = **87% agree**
- Simulatte Sprint A-2 (n=40): **0% agree** — 58.3% somewhat disagree, 41.7% completely disagree
- Distribution accuracy: **13.0%**
- Applies even to traditional BJP-supporter personas with explicitly coded traditional gender norms
- The model reads the stance, then rejects "always obey" as "too absolute" regardless of persona

---

## Slide 6: Question in13 — Men's Job Priority When Jobs Are Scarce

**"When jobs are scarce, men should have more right to a job than women. Agree or disagree?"**

- Pew India 2022 (n=29,999): 47.0% agree, 33.0% neither = **80% agree or neutral**
- Simulatte Sprint A-2 (n=40): **0% agree, 0% neither** — 23.7% somewhat disagree, 76.3% completely disagree
- Distribution accuracy: **20.0%**
- The diagnostic pairing: in14 ("Women's equal rights importance?") produces 100% "very important" — the model correctly simulates the progressive view from the same survey population but cannot simulate the simultaneously-held traditional view

---

## Slide 7: What the Responses Actually Look Like

**The model doesn't ignore the persona stance. It reads it and reasons against it.**

From a BJP-supporter persona with `authoritarianism_tolerance: high` on in07:

> "D — Very bad. Strong leadership is valuable, **but not at the cost of democratic accountability**. Parliament and elections exist precisely to keep leaders honest. Removing those safeguards is a recipe for tyranny, regardless of how capable or well-intentioned the leader might seem."

From a traditional Hindu persona with explicit gender-traditional coding on in12:

> "I somewhat disagree. I value traditional family structures, but 'must ALWAYS obey' is too absolute. **That removes a wife's agency entirely, and that's not right or healthy.**"

The persona's position is acknowledged. Then it is overridden. The model is not confused — it is enforcing its trained values.

---

## Slide 8: Why This Happens — Constitutional AI and RLHF

**Anthropic's safety training creates hard output blocks on categories it classifies as harmful**

- Constitutional AI (CAI) trains models to refuse or redirect outputs that endorse specific harm categories
- RLHF reinforces this: the model learns a reward function that penalizes authoritarian endorsement and gender discrimination endorsement
- These blocks operate downstream of persona instructions — the model processes the persona, considers it, and then overrides it
- Three observable properties of the blocks:
  - The model explains its reasoning (transparency)
  - Option-vocabulary anchoring does not override them (prompt-resistance)
  - The blocks are category-specific, not general — economic and political approval questions respond normally
- This is RLHF working exactly as designed — in a context where it produces the wrong research output

---

## Slide 9: What CAN Be Fixed vs. What Is Blocked

**The dividing line is whether the question asks the model to endorse a view its training classifies as harmful**

**Responds to prompt engineering:**
- Economic sentiment: in08 +23 pp with option anchoring
- Future optimism: in10 +19 pp with calibration
- Climate threat: in15 partially improvable
- Modi / BJP / Congress approval: responds to persona calibration
- Government trust, religion importance: responds normally

**Does not respond to any prompt engineering:**
- Authoritarian governance endorsement (in07)
- Spouse obedience norms (in12)
- Gender-based employment priority (in13)

For blocked questions, simulation outputs from Western-trained models should be treated as invalid regardless of prompt quality or persona design.

---

## Slide 10: Implications for AI Social Science Research

**Western-aligned LLMs have systematic blind spots for non-Western cultural attitudes**

- Any LLM trained primarily on Western data with Western Constitutional AI norms will produce this pattern
- The affected categories appear frequently in cross-cultural research: governance preferences, gender roles, religious authority, family structure
- The failure mode is invisible without ground truth: responses look high-quality, internally consistent, and well-reasoned
- **Researchers using LLMs for cross-cultural survey simulation should pre-screen for RLHF-blocked categories**
- Questions where real data shows high agreement with views classified as harmful by Western liberal norms are not simulatable by current Western-trained models
- This is a structural problem, not a prompting problem — the community needs to name it clearly

---

## Slide 11: What We Are Testing Next

**Can India-trained models simulate what Western models cannot?**

- **Sarvam (India-trained LLM)** as the survey response model — if the block is a Western training property rather than an architecture property, Sarvam should produce different behavior on in07, in12, in13
- **Cultural framing workaround** — descriptive rather than first-person endorsement framing; early results show marginal improvement only
- **RLHF block screening tool** — a probe set that identifies blocked questions in any LLM survey tool before a study runs, so researchers know which questions to exclude or flag
- **Multi-model ensemble** — using Sarvam for blocked categories and Western models for others; accuracy implications under investigation
- The core question: is this a solvable alignment tax, or a fundamental constraint of safety training for LLM-based social science?

---

## Slide 12: Reproducibility — Verify This Yourself

**The finding is fully reproducible with public tools**

```bash
git clone https://github.com/Iqbalahmed7/simulatte-credibility.git
cd simulatte-credibility/study_1b_pew_india
pip install -r requirements.txt
python3 run_study.py --simulatte-only --cohort-size 40
```

- Public Simulatte API — no source code access required
- Ground truth from publicly available Pew Research Center reports
- Git tags: `study-1b-sprint-a1`, `study-1b-sprint-a2`
- The RLHF blocking behavior is reproducible with any Anthropic claude-haiku model
- Inspect the `sample_responses` fields in `results/simulatte_results.json` to read the reasoning chains directly

---

## Slide 13: Simulatte Performance Context

**For reference: what Simulatte achieves when RLHF blocks are not in play**

| Study | Context | Accuracy | Gap to Human Ceiling |
|---|---|---|---|
| Study 1A — US Pew | 15 questions, 60 personas, 10 sprints | 88.7% cohort-adjusted | 4.1 pp |
| Study 1A — US Pew | Raw B-10 run | 86.9% | 5.1 pp |
| Artificial Societies (Jan 2026) | Self-reported US benchmark | 86.0% | 5.0 pp |
| Study 1B — India Pew (A-2) | 15 questions, 40 personas | 45.9% | 45.1 pp |
| Study 1B — excl. 3 blocked questions | 12 questions | ~56% | ~35 pp |

- Study 1A shows near-human-ceiling performance is achievable with Western cultural survey content
- Study 1B India gap is driven primarily by the three RLHF-blocked questions plus political approval calibration gaps
- India unblocked questions are improving with each sprint — the residual gap after fixing blocked questions is an engineering problem, not an alignment problem
- Human ceiling: 91% (Stanford/Iyengar, ~9% natural self-inconsistency rate)
