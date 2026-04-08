# LLM Comparison — India Pew Opinion Survey

## Overview

This study compares Simulatte DEEP against 10 leading large language models on the India Pew Opinion Survey (Study 1B). It establishes an independently auditable baseline showing how well naive LLMs replicate population-level Indian opinion distributions when given only demographic context.

| Parameter | Value |
|---|---|
| **Study** | India Pew Opinion Survey (Study 1B) |
| **Metric** | Distribution Accuracy = 1 − (Σ\|real_i − sim_i\| / 2) |
| **Human ceiling** | 91% (Stanford Iyengar et al.) |
| **Persona pool** | 40 demographically calibrated India personas |
| **LLMs tested** | 10 (Claude, GPT, Gemini families) |
| **Total API calls** | 5,878 (SHA-256 verified) |
| **Simulatte result** | **85.3%** (Sprint A-22) |
| **Best LLM** | GPT-4o at 75.6% |
| **Nx ratio** | **4.9x** closer to human ceiling than avg LLM |

## Results Summary

| Model | Distribution Accuracy | Gap to 91% |
|---|---|---|
| **Simulatte DEEP (A-22)** | **85.3%** | **5.7 pp** |
| GPT-4o | 75.6% | 15.4 pp |
| GPT-5 Mini | 74.3% | 16.7 pp |
| GPT-4o Mini | 73.8% | 17.2 pp |
| GPT-5 | 72.4% | 18.6 pp |
| Claude Haiku 4.5 | 71.9% | 19.1 pp |
| Claude Sonnet 4.6 | 70.2% | 20.8 pp |
| Gemini 3 Pro | 44.3% | 46.7 pp |
| Gemini 3 Flash | 43.9% | 47.1 pp |
| Gemini 2.5 Flash | 43.5% | 47.5 pp |
| *Human ceiling* | *91.0%* | *—* |

## Nx Ratio

| Comparison | Result |
|---|---|
| Simulatte error | 5.7 pp |
| Average LLM error | 27.7 pp |
| Best LLM error (GPT-4o) | 15.4 pp |
| **Nx vs. average LLM** | **4.9x closer to human ceiling** |
| Nx vs. best LLM (GPT-4o) | 2.7x closer |
| Nx vs. Gemini 2.5 Flash (AS-comparable) | 8.3x closer |

## LLM Baseline Protocol

Every LLM received the same stripped demographic description per persona — religion, caste, age, education, income, region, political lean — in a single API call with no cognitive loop, no memory, and no calibration. This is a fair, generous baseline: the same information a survey researcher would know about a respondent.

```
SYSTEM: You are {name}, a {age}-year-old {religion} {gender} living in {city}, {state}.
        Education: {education}. Employment: {employment}. Income: {income_bracket}.
        Caste: {caste}. Politically: {political_lean_description}.
        Answer the following survey question exactly as {name} would.

USER:   {question_text}
        Options: A) ... B) ... C) ... D) ...
        Respond with ONLY the single option letter (A, B, C, or D).
```

Simulatte uses a full perceive → reflect → decide cognitive loop with 22 sprints of calibration on top of the same base personas.

## Key Findings

**GPT-5 underperforms GPT-4o (72.4% vs 75.6%):** Raw model capability does not transfer to cultural calibration. GPT-5 applies heavier alignment-style balancing on politically sensitive Indian questions, flattening BJP/opposition distributions.

**Gemini clusters at 43–44%:** All three Gemini variants score within 1 pp of each other regardless of model size — a structural failure in handling Indian cultural identity, not a scale limitation.

**Hardest questions:** Government trust (in09, conflated with political approval), Congress anger calibration (in04), and the BJP-lean strong-leader paradox (in07 — India among world's highest supporters at 80%, which LLMs resist generating).

## Audit & Verification

All 5,878 API calls are logged with SHA-256 prompt and response hashes. The stripped audit file (with prompt text removed to protect the proprietary persona pool) is publicly verifiable:

```bash
python3 audit/verify.py
```

| File | Description |
|---|---|
| `audit/stripped_audit.jsonl` | All entries: timestamps, hashes, answers — no prompt text |
| `audit/audit_manifest.json` | Root hash, run IDs, entry counts |
| `audit/verify.py` | Integrity verifier — confirms file is unmodified |
| `results/llm_scores.json` | Model accuracy table with per-question breakdown |
| `questions.json` | The 15 survey questions (public Pew data) |

### Run IDs

| Run | ID | Entries | Models |
|---|---|---|---|
| Main | `llm-india-20260407-213325-677319f7` | 4,200 | 7 LLMs |
| Supplemental | `llm-india-20260407-221604-f2a991f1` | 1,678 | GPT-5, GPT-5 Mini |

Root hash (SHA-256 of stripped_audit.jsonl):
```
sha256:a76aa717a0971961220f314451fe23ac623bf01cb8ca790f39a6ad5ed273d3f0
```

## Independent Replication

Full prompt text and persona definitions are available under NDA for researchers who wish to independently replicate this benchmark. The SHA-256 hashes in the stripped audit allow verification that our published results correspond exactly to the prompts we sent — without requiring disclosure of the persona corpus.

## Related Studies

- [Pew India Study (Study 1B)](../pew_india/) — the Simulatte-only sprint progression
- [Pew USA Study (Study 1A)](../pew_usa/) — US opinion replication (88.7%)
