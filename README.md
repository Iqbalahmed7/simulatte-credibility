# Simulatte Credibility Research Program

**April 2026 — Study 1A complete (88.7%) | Study 1B complete (85.3%) | Study 1C complete (91.3%) | LLM comparison: 4.9x | Europe Benchmark: 9 countries in progress**

Simulatte generates synthetic AI personas and surveys them at scale. This repository documents a rigorous, independently auditable benchmarking program measuring how closely simulated survey distributions match real Pew Research Center data.

---

## Studies

### [Study 1A — Pew USA Opinion Replication](studies/pew_usa/)
15 Pew American Trends Panel questions · 60 US personas · **88.7% accuracy** (Sprint B-10) · 2.3 pp below human ceiling

### [Study 1B — Pew India Opinion Replication](studies/pew_india/)
15 Pew India questions · 40 India personas · **85.3% accuracy** (Sprint A-22) · 5.7 pp below human ceiling · 22 sprints from 46.2% baseline

### [Study 1C — Pew Germany Opinion Replication](studies/pew_germany/)
15 Pew Global Attitudes questions · 40 German personas · **91.3% calibrated accuracy** (Sprint C-8) · 8 sprints from 83.2% baseline · Holdout validation: **82.2% cold** on 4 structural questions (7-question holdout overall: 70.3%)

### [LLM Comparison — India Pew](studies/llm_comparison/)
Simulatte vs. 10 LLMs on the India Pew study · **4.9x closer to human ceiling than the average LLM** · 5,878 SHA-256 verified API calls · GPT-5 underperforms GPT-4o · Gemini clusters at 43–44%

### [Europe Benchmark](studies/europe_benchmark/) *(in progress)*
9 European countries · France, Greece, Hungary, Italy, Netherlands, Poland, Spain, Sweden, UK · 15 Pew questions per country · 40 personas per country · Holdout sets designated before calibration · Ground truth: Pew Global Attitudes Spring 2024 (all N≈1,000)

---

## Headline Numbers

| Study | Calibrated (in-sample) | Cold holdout | Human Ceiling |
|---|---|---|---|
| Pew USA (Study 1A) | **88.7%** | — | 91% |
| Pew India (Study 1B) | **85.3%** | — | 91% |
| Pew Germany (Study 1C) | **91.3%** | **82.2%** structural · 70.3% all | 91% |

**LLM Comparison (Study 1B):** Simulatte 4.9× closer to human ceiling than average LLM (calibrated vs. single-pass uncalibrated).

**Holdout methodology note:** Study 1C includes a blind holdout validation — 7 questions never seen during calibration, run once with zero topic anchors. Party and institutional questions score 82.2% cold, confirming the WorldviewAnchor architecture has genuine predictive power independent of calibration. Leader-specific confidence questions (Biden, Macron) score 54.4% cold, identifying the architecture's boundary condition.

---

## Audit & Reproducibility

Every Simulatte sprint is logged in a structured audit manifest (JSON) with per-question accuracy, simulated distributions, and ground truth targets. The LLM comparison study additionally provides:

- `stripped_audit.jsonl` — SHA-256 hashes of all 5,878 LLM API calls (no prompt text)
- `audit_manifest.json` — root hash for tamper detection
- `verify.py` — one-command integrity check

```bash
cd studies/llm_comparison/audit && python3 verify.py
```

Full prompts and persona pool definitions are proprietary and available under NDA for independent replication.

---

## Ground Truth

All benchmark questions are drawn from publicly available Pew Research Center surveys:
- [Pew Global Attitudes Survey — Spring 2024](https://www.pewresearch.org/global/datasets/) (Germany, Study 1C)
- [Pew Global Attitudes Survey — Spring 2023](https://www.pewresearch.org/global/) (India, Study 1B)
- [Pew American Trends Panel](https://www.pewresearch.org/american-trends-panel-datasets/) (USA, Study 1A)
- [Pew Religion in India 2021](https://www.pewresearch.org/religion/2021/06/29/religion-in-india-tolerance-and-segregation/)
- CSDS-Lokniti National Election Studies

Human replication ceiling: **91%** (Stanford Iyengar et al., 2023 — human panel-to-panel replication benchmark)
