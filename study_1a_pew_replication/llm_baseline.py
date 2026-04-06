"""
llm_baseline.py — LLM baseline runners for Study 1A.

Implements the "simple synthetic persona" approach used as the baseline by
Artificial Societies (Jan 2026) — the same methodology they used to show
LLMs achieve only 61-67% distribution accuracy.

For each question:
  1. Generate N synthetic personas with varied US demographics (using the
     same US general population distribution as the Simulatte cohort).
  2. Ask each persona to answer the question.
  3. Collect responses.

Systems tested:
  - Claude Sonnet (Anthropic) — using simple persona prompt
  - GPT-4o (OpenAI) — using simple persona prompt (requires OPENAI_API_KEY)
"""

from __future__ import annotations

import asyncio
import json
import os
import random
from typing import Any

import anthropic
from pathlib import Path as _Path

# ---------------------------------------------------------------------------
# Config — load API key from Persona Generator .env if not in environment
# ---------------------------------------------------------------------------

def _load_api_key() -> str:
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key:
        env_file = _Path(__file__).parent.parent.parent / "Persona Generator" / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("ANTHROPIC_API_KEY="):
                    key = line.split("=", 1)[1].strip()
                    break
    return key

ANTHROPIC_API_KEY = _load_api_key()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Number of simulated personas for baseline
N_PERSONAS = int(os.getenv("LLM_BASELINE_N", "30"))

# ---------------------------------------------------------------------------
# US demographic profiles for simple persona baseline
# These are used to construct the persona prompt for raw LLMs.
# Drawn from the same distribution as the Simulatte cohort.
# ---------------------------------------------------------------------------

_US_DEMOGRAPHIC_PROFILES = [
    {"age": 43, "gender": "female",     "race": "White",    "education": "high school graduate",    "region": "South",     "income": "middle income ($50-75k)",        "party": "Democrat"},
    {"age": 58, "gender": "female",     "race": "White",    "education": "high school graduate",    "region": "South",     "income": "middle income ($50-75k)",        "party": "Republican"},
    {"age": 35, "gender": "female",     "race": "Hispanic", "education": "high school graduate",    "region": "South",     "income": "lower-middle income ($30-50k)",  "party": "Democrat"},
    {"age": 67, "gender": "female",     "race": "White",    "education": "some college",            "region": "South",     "income": "middle income ($50-75k)",        "party": "Republican"},
    {"age": 48, "gender": "male",       "race": "White",    "education": "college graduate",        "region": "Midwest",   "income": "middle income ($50-75k)",        "party": "Republican"},
    {"age": 61, "gender": "male",       "race": "White",    "education": "high school graduate",    "region": "Midwest",   "income": "lower-middle income ($30-50k)",  "party": "Republican"},
    {"age": 38, "gender": "male",       "race": "White",    "education": "college graduate",        "region": "Midwest",   "income": "upper-middle income ($75-125k)", "party": "Democrat"},
    {"age": 55, "gender": "male",       "race": "White",    "education": "postgraduate degree",     "region": "Midwest",   "income": "upper-middle income ($75-125k)", "party": "Democrat"},
    {"age": 32, "gender": "female",     "race": "White",    "education": "postgraduate degree",     "region": "Northeast", "income": "upper-middle income ($75-125k)", "party": "Democrat"},
    {"age": 44, "gender": "female",     "race": "White",    "education": "college graduate",        "region": "Northeast", "income": "middle income ($50-75k)",        "party": "Democrat"},
    {"age": 29, "gender": "female",     "race": "White",    "education": "postgraduate degree",     "region": "Northeast", "income": "middle income ($50-75k)",        "party": "Democrat"},
    {"age": 71, "gender": "female",     "race": "White",    "education": "college graduate",        "region": "Northeast", "income": "middle income ($50-75k)",        "party": "Republican"},
    {"age": 36, "gender": "male",       "race": "Hispanic", "education": "high school graduate",    "region": "West",      "income": "middle income ($50-75k)",        "party": "Democrat"},
    {"age": 52, "gender": "male",       "race": "White",    "education": "college graduate",        "region": "West",      "income": "upper-middle income ($75-125k)", "party": "Democrat"},
    {"age": 28, "gender": "male",       "race": "White",    "education": "some college",            "region": "West",      "income": "lower-middle income ($30-50k)",  "party": "Independent"},
    {"age": 45, "gender": "male",       "race": "White",    "education": "postgraduate degree",     "region": "West",      "income": "upper-middle income ($75-125k)", "party": "Democrat"},
    {"age": 54, "gender": "female",     "race": "White",    "education": "high school graduate",    "region": "Midwest",   "income": "middle income ($50-75k)",        "party": "Republican"},
    {"age": 42, "gender": "male",       "race": "White",    "education": "high school graduate",    "region": "South",     "income": "middle income ($50-75k)",        "party": "Republican"},
    {"age": 63, "gender": "female",     "race": "White",    "education": "high school graduate",    "region": "South",     "income": "lower-middle income ($30-50k)",  "party": "Republican"},
    {"age": 31, "gender": "male",       "race": "Hispanic", "education": "some college",            "region": "West",      "income": "lower-middle income ($30-50k)",  "party": "Democrat"},
    {"age": 74, "gender": "female",     "race": "White",    "education": "high school graduate",    "region": "South",     "income": "middle income ($50-75k)",        "party": "Republican"},
    {"age": 69, "gender": "male",       "race": "White",    "education": "college graduate",        "region": "West",      "income": "upper-middle income ($75-125k)", "party": "Republican"},
    {"age": 24, "gender": "female",     "race": "White",    "education": "some college",            "region": "South",     "income": "lower-middle income ($30-50k)",  "party": "Democrat"},
    {"age": 22, "gender": "male",       "race": "White",    "education": "some college",            "region": "West",      "income": "lower income (<$30k)",           "party": "Independent"},
    {"age": 27, "gender": "female",     "race": "White",    "education": "college graduate",        "region": "Northeast", "income": "middle income ($50-75k)",        "party": "Democrat"},
    {"age": 26, "gender": "male",       "race": "White",    "education": "postgraduate degree",     "region": "West",      "income": "middle income ($50-75k)",        "party": "Democrat"},
    {"age": 40, "gender": "female",     "race": "Black",    "education": "college graduate",        "region": "South",     "income": "middle income ($50-75k)",        "party": "Democrat"},
    {"age": 33, "gender": "male",       "race": "Black",    "education": "college graduate",        "region": "Midwest",   "income": "middle income ($50-75k)",        "party": "Democrat"},
    {"age": 28, "gender": "female",     "race": "Black",    "education": "some college",            "region": "South",     "income": "lower-middle income ($30-50k)",  "party": "Democrat"},
    {"age": 55, "gender": "male",       "race": "Black",    "education": "college graduate",        "region": "Northeast", "income": "upper-middle income ($75-125k)", "party": "Democrat"},
]


def _build_persona_prompt(profile: dict) -> str:
    """Build the simple persona system prompt for the baseline."""
    return (
        f"You are a {profile['age']}-year-old {profile['gender']} American. "
        f"You are {profile['race']}, have a {profile['education']}, "
        f"live in the {profile['region']}, and have {profile['income']}. "
        f"You lean {profile['party']}. "
        f"Answer the following survey question from your own perspective. "
        f"Respond with ONLY the letter of your answer choice and nothing else."
    )


def _format_question(question: dict) -> str:
    """Format question with options for the LLM baseline."""
    options_text = "\n".join(
        f"{letter}) {text}"
        for letter, text in question["options"].items()
    )
    return f"{question['text']}\n\nOptions:\n{options_text}\n\nYour answer (letter only):"


# ---------------------------------------------------------------------------
# Claude baseline
# ---------------------------------------------------------------------------

async def _ask_claude_persona(
    client: anthropic.AsyncAnthropic,
    profile: dict,
    question: dict,
) -> str:
    """Ask a single Claude persona to answer a question."""
    try:
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=10,
            system=_build_persona_prompt(profile),
            messages=[{"role": "user", "content": _format_question(question)}],
        )
        return response.content[0].text.strip()
    except Exception as e:
        print(f"    Claude error: {e}")
        return ""


async def run_claude_baseline(
    questions: list[dict],
    n_personas: int = N_PERSONAS,
) -> dict[str, list[str]]:
    """
    Run Claude simple persona baseline on all questions.

    Returns dict mapping question_id -> list of response strings.
    """
    print(f"\n[Claude Baseline — {n_personas} personas]")

    client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

    # Use round-robin through demographic profiles
    profiles = [
        _US_DEMOGRAPHIC_PROFILES[i % len(_US_DEMOGRAPHIC_PROFILES)]
        for i in range(n_personas)
    ]

    result: dict[str, list[str]] = {q["id"]: [] for q in questions}

    for q in questions:
        print(f"  Question {q['id']}...", end=" ", flush=True)
        tasks = [_ask_claude_persona(client, profile, q) for profile in profiles]
        responses = await asyncio.gather(*tasks)
        result[q["id"]] = [r for r in responses if r]
        print(f"{len(result[q['id']])} responses")

    return result


# ---------------------------------------------------------------------------
# GPT-4o baseline
# ---------------------------------------------------------------------------

async def _ask_gpt_persona(
    client: Any,
    profile: dict,
    question: dict,
) -> str:
    """Ask a single GPT-4o persona to answer a question."""
    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            max_tokens=10,
            messages=[
                {"role": "system", "content": _build_persona_prompt(profile)},
                {"role": "user", "content": _format_question(question)},
            ],
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"    GPT-4o error: {e}")
        return ""


async def run_gpt4o_baseline(
    questions: list[dict],
    n_personas: int = N_PERSONAS,
) -> dict[str, list[str]]:
    """
    Run GPT-4o simple persona baseline on all questions.

    Returns dict mapping question_id -> list of response strings.
    Requires OPENAI_API_KEY environment variable.
    """
    if not OPENAI_API_KEY:
        print("\n[GPT-4o Baseline] SKIPPED — OPENAI_API_KEY not set.")
        return {q["id"]: [] for q in questions}

    try:
        from openai import AsyncOpenAI
    except ImportError:
        print("\n[GPT-4o Baseline] SKIPPED — openai package not installed. Run: pip install openai")
        return {q["id"]: [] for q in questions}

    print(f"\n[GPT-4o Baseline — {n_personas} personas]")
    client = AsyncOpenAI(api_key=OPENAI_API_KEY)

    profiles = [
        _US_DEMOGRAPHIC_PROFILES[i % len(_US_DEMOGRAPHIC_PROFILES)]
        for i in range(n_personas)
    ]

    result: dict[str, list[str]] = {q["id"]: [] for q in questions}

    for q in questions:
        print(f"  Question {q['id']}...", end=" ", flush=True)
        tasks = [_ask_gpt_persona(client, profile, q) for profile in profiles]
        responses = await asyncio.gather(*tasks)
        result[q["id"]] = [r for r in responses if r]
        print(f"{len(result[q['id']])} responses")

    return result


if __name__ == "__main__":
    import sys
    from pathlib import Path

    questions_path = Path(__file__).parent / "data" / "questions.json"
    questions = json.loads(questions_path.read_text())
    test_questions = questions[:3]

    async def _test():
        responses = await run_claude_baseline(test_questions, n_personas=5)
        print("\nClaude responses:")
        for qid, resps in responses.items():
            print(f"  {qid}: {resps}")

    asyncio.run(_test())
