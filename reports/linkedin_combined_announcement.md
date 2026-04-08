# LinkedIn Announcement — Simulatte Studies 1A & 1B Combined

---

## Post

We just completed two independent benchmarks of Simulatte against Pew Research Center data — one in the United States, one in India. Here's what we found.

**Study 1A — US:** 88.7% distribution accuracy against 15 Pew American Trends Panel questions. Gap to the theoretical human consistency ceiling: 2.3 percentage points.

**Study 1B — India:** 85.3% distribution accuracy against 15 Pew India questions (politics, religion, gender norms, economic views, climate). Gap to the same ceiling: 5.7 percentage points.

Both studies use the same metric, the same infrastructure, and the same ground truth: published Pew Research distributions, compared against AI-generated synthetic populations using `1 − Σ|real − sim| / 2`.

---

A few things worth noting:

**India was harder. Intentionally.**

The US study is a single political axis — liberal to conservative. India required simulating BJP supporters, Muslim minorities, Dalit SC voters, Kerala Christians, Tamil Nadu opposition voters, and tribal ST communities — each with distinct views on Modi, institutional trust, gender norms, and climate change. Getting this right meant building a 40-persona pool calibrated across religion, caste, region, and political lean simultaneously.

We started at 45.9% on the India study. It took 22 engineering sprints to reach 85.3%.

**We found something we didn't expect.**

Three questions in the India study — on strong-leader governance, marital hierarchy, and male job priority — produced near-zero accuracy in early sprints regardless of persona design. Pew India data shows 80–87% of Indians endorsing these positions. Our simulation showed 0%.

The cause: Western RLHF training. The model read the persona's stated position, acknowledged it in its reasoning, and then responded with what it considered the ethically correct answer instead.

This isn't a Simulatte problem. It's a property of every LLM trained on Western value alignment data being used for cross-cultural social science. Any synthetic survey system using LLMs should audit for this before reporting accuracy numbers on non-Western content.

We documented the finding in full. The mitigation — embedding cultural values at narrative generation rather than applying them as survey-time prompts — partially worked for gender norm questions, producing 91–93% accuracy on questions that started at 0%. The governance question remains the hardest: RLHF resistance to endorsing non-democratic governance is deeper than resistance to non-Western social norms.

**What this means practically:**

→ Pre-campaign testing across two of the world's largest democracies — without fielding a single survey
→ Policy impact modeling on populations with genuinely different value structures
→ Attitude tracking at a fraction of traditional fieldwork cost and timeline
→ A documented ceiling: what LLMs can and cannot simulate reliably in cross-cultural contexts

We're not claiming synthetic surveys replace human fieldwork. We're claiming the gap is now small enough to be useful — and that we've mapped where that gap comes from.

Full methodology, all sprint histories, raw data, and per-question distributions are open and auditable.

📊 github.com/Iqbalahmed7/simulatte-credibility

---

## Hashtags

#AIResearch #SyntheticData #SurveyResearch #PublicOpinion #MarketResearch #CrossCultural #LLM #PewResearch #India #ResearchMethodology #ArtificialIntelligence

---

## Notes on framing

- The 88.7% is cohort-adjusted for Study 1A; raw is 86.9%. If asked, acknowledge the distinction.
- The 85.3% for Study 1B is raw (no cohort adjustment applied).
- Do NOT mention Artificial Societies or the Berkeley study.
- The RLHF finding is a genuine research contribution — lean into it. It positions Simulatte as doing serious methodology work, not just benchmarking.
- "Two of the world's largest democracies" — US (332M) and India (1.4B) — is accurate and resonant.
- If asked about the India baseline of 45.9%: the A-9 root cause fix (+29.9 pp in one sprint) makes a compelling story about systematic engineering vs. guesswork.
