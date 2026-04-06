"""
simulatte_runner.py — Run Pew survey questions through the Simulatte API.

Flow:
  1. Generate a US general population cohort via POST /generate
     (using 'saas' domain as a US-biased proxy until a us_general domain
      is added to the persona generator's demographic_sampler.py)
  2. Format each Pew question with explicit categorical options
  3. POST /survey with the formatted questions
  4. Parse the free-text 'decision' fields back to option letters
  5. Return raw responses dict: {question_id: [response_str, ...]}

Demographic composition:
  Uses the 'us_general' domain pool — 34 profiles approximating the
  Pew Research Center American Trends Panel (ATP) composition:
  nationally representative US adults across age, gender, race,
  education, region, and income.

  Pool source: /Persona Generator/src/generation/demographic_sampler.py
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

import httpx

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SIMULATTE_API_URL = os.getenv(
    "SIMULATTE_API_URL",
    "https://simulatte-persona-generator.onrender.com"
)

# US general population domain — matches Pew ATP sample composition.
# Pool added to /Persona Generator/src/generation/demographic_sampler.py
DOMAIN = "us_general"

# Number of personas per cohort. More = better statistics, higher cost + time.
# Recommended: 50 for proof of concept, 200+ for publication.
COHORT_SIZE = int(os.getenv("SIMULATTE_COHORT_SIZE", "30"))

# Claude model for survey responses
SURVEY_MODEL = os.getenv("SIMULATTE_SURVEY_MODEL", "claude-haiku-4-5-20251001")

_TIMEOUT = httpx.Timeout(300.0, connect=30.0)  # Long timeout — Render cold starts

# ---------------------------------------------------------------------------
# Question formatting
# ---------------------------------------------------------------------------

def format_question_for_survey(question: dict) -> str:
    """
    Format a Pew question with explicit categorical options for the Simulatte
    survey endpoint.

    Forces the persona to respond with a single option letter. This is critical
    because the survey modality returns free-text decisions — we need structured
    output to compute distribution accuracy.
    """
    options_text = "\n".join(
        f"  {letter}) {text}"
        for letter, text in question["options"].items()
    )
    return (
        f"{question['text']}\n\n"
        f"Please respond with ONLY the letter of your answer (e.g. 'A' or 'B').\n"
        f"Do not write anything else — just the single letter.\n\n"
        f"Options:\n{options_text}"
    )


# ---------------------------------------------------------------------------
# API calls
# ---------------------------------------------------------------------------

def health_check() -> bool:
    """Check if the Simulatte API is reachable."""
    try:
        with httpx.Client(timeout=httpx.Timeout(15.0)) as client:
            resp = client.get(f"{SIMULATTE_API_URL}/health")
            resp.raise_for_status()
            data = resp.json()
            print(f"  Simulatte API: {data}")
            return data.get("status") == "ok"
    except Exception as e:
        print(f"  ERROR: Simulatte API unreachable — {e}")
        return False


def generate_cohort(cohort_size: int = COHORT_SIZE, domain: str = DOMAIN) -> str:
    """
    Generate a new cohort via POST /generate.

    Returns the cohort_id for use in subsequent survey calls.
    Retries up to 3 times on 5xx errors (Render cold-start flakiness).
    """
    print(f"  Generating cohort: {cohort_size} personas, domain={domain}...")
    payload = {
        "count": cohort_size,
        "domain": domain,
        "mode": "quick",
        "anchor_overrides": {},
        "persona_id_prefix": "pew",
        "sarvam_enabled": False,
        "skip_gates": True,  # Skip quality gates for speed in research context
    }

    max_retries = 5
    for attempt in range(1, max_retries + 1):
        try:
            with httpx.Client(timeout=_TIMEOUT) as client:
                resp = client.post(f"{SIMULATTE_API_URL}/generate", json=payload)
                resp.raise_for_status()
                data = resp.json()
                cohort_id = data["cohort_id"]
                persona_count = data["persona_count"]
                print(f"  Generated cohort: {cohort_id} ({persona_count} personas)")
                return cohort_id
        except httpx.HTTPStatusError as e:
            if e.response.status_code >= 500 and attempt < max_retries:
                wait = min(attempt * 20, 90)  # 20s, 40s, 60s, 80s — Render cold starts need time
                print(f"  Server error (attempt {attempt}/{max_retries}), retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise
        except httpx.TimeoutException:
            if attempt < max_retries:
                wait = min(attempt * 20, 90)
                print(f"  Timeout (attempt {attempt}/{max_retries}), retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise

    raise RuntimeError("generate_cohort failed after all retries")


def _survey_single_question(
    cohort_id: str,
    question: dict,
    q_index: int,
    model: str,
) -> list[str]:
    """Run a single question against all personas in a cohort.

    Sends a /survey call with exactly one question. This keeps each request
    fast enough (~30-60s) to avoid Render's 502 gateway timeout that occurs
    with large batches (50 personas × 15 questions in one call).

    Returns a list of raw decision strings (one per persona).
    """
    formatted = format_question_for_survey(question)
    payload = {
        "cohort_id": cohort_id,
        "questions": [formatted],
        "model": model,
    }

    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            with httpx.Client(timeout=_TIMEOUT) as client:
                resp = client.post(f"{SIMULATTE_API_URL}/survey", json=payload)
                resp.raise_for_status()
                data = resp.json()

            # Parse — the single question maps to internal id "q1"
            raw = data.get("responses", {})
            if isinstance(raw, dict):
                responses_list = raw.get("responses", [])
            elif isinstance(raw, list):
                responses_list = raw
            else:
                return []

            return [
                str(r.get("decision", ""))
                for r in responses_list
                if r.get("decision")
            ]

        except httpx.HTTPStatusError as e:
            if e.response.status_code in (502, 503, 504) and attempt < max_retries:
                wait = attempt * 20
                print(f"    [{question['id']}] Gateway {e.response.status_code} (attempt {attempt}/{max_retries}), retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise
        except httpx.TimeoutException:
            if attempt < max_retries:
                wait = attempt * 20
                print(f"    [{question['id']}] Timeout (attempt {attempt}/{max_retries}), retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise

    return []


def run_survey_batch(
    cohort_id: str,
    questions: list[dict],
    model: str = SURVEY_MODEL,
) -> dict[str, list[str]]:
    """
    Run all Pew questions against a cohort, one question at a time.

    Sends one /survey request per question to avoid Render's 502 gateway
    timeout that occurs when all 50 personas × 15 questions are sent in
    a single synchronous HTTP call.

    Returns:
        Dict mapping question_id -> list of decision strings (one per persona).
    """
    print(f"  Running survey: {len(questions)} questions × cohort {cohort_id} (one at a time)...")
    print(f"  Model: {model}")

    result: dict[str, list[str]] = {q["id"]: [] for q in questions}

    for i, question in enumerate(questions):
        print(f"    [{i+1:02d}/{len(questions)}] {question['id']} — {question['topic']}...", end=" ", flush=True)
        decisions = _survey_single_question(cohort_id, question, i, model)
        result[question["id"]] = decisions
        print(f"{len(decisions)} responses")

    return result


def _parse_survey_response(
    api_response: dict,
    questions: list[dict],
) -> dict[str, list[str]]:
    """
    Parse the SurveyResponse from the API into {question_id: [decisions]}.

    The API returns:
    {
      "cohort_id": "...",
      "responses": {
        "survey_id": "...",
        "questions": [...],
        "responses": [
          {
            "persona_id": "...",
            "persona_name": "...",
            "question_id": "q1",   # "q1", "q2", etc. (1-indexed by _run_survey)
            "decision": "A",
            "confidence": 8,
            "key_drivers": [...],
            "reasoning_trace": "...",
            "objections": [...]
          },
          ...
        ],
        "modality": "one_time_survey"
      }
    }

    Note: The survey runner assigns IDs as q1, q2, ... (1-indexed), which
    map to our question IDs q01, q02, ... positionally.
    """
    raw = api_response.get("responses", {})

    # Handle both direct responses list and nested structure
    if isinstance(raw, dict):
        responses_list = raw.get("responses", [])
    elif isinstance(raw, list):
        responses_list = raw
    else:
        print(f"  WARNING: Unexpected response format: {type(raw)}")
        return {q["id"]: [] for q in questions}

    # Build positional mapping: the survey runner uses q1, q2, ... (1-indexed)
    # Map these back to our question IDs (q01, q02, ...)
    internal_id_to_question_id = {
        f"q{i+1}": q["id"]
        for i, q in enumerate(questions)
    }

    result: dict[str, list[str]] = {q["id"]: [] for q in questions}

    for persona_resp in responses_list:
        internal_qid = persona_resp.get("question_id", "")
        decision = persona_resp.get("decision", "")

        question_id = internal_id_to_question_id.get(internal_qid)
        if question_id and decision:
            result[question_id].append(str(decision))

    # Log parse stats
    for q in questions:
        n = len(result[q["id"]])
        print(f"    {q['id']}: {n} responses collected")

    return result


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def run_simulatte_study(
    questions: list[dict],
    cohort_size: int = COHORT_SIZE,
    domain: str = DOMAIN,
    existing_cohort_id: str | None = None,
    existing_cohort_ids: list[str] | None = None,
) -> tuple[str, dict[str, list[str]]]:
    """
    Full Simulatte study runner.

    Generates in batches of MAX_BATCH_SIZE (20) to avoid Render's 300s
    generation timeout for large cohorts. Merges responses across batches.

    Args:
        questions: List of question dicts from questions.json.
        cohort_size: Total number of personas to generate.
        domain: Domain for persona generation.
        existing_cohort_id: If provided, skip generation and use single cohort.
        existing_cohort_ids: If provided, skip generation and survey all listed cohorts.

    Returns:
        Tuple of (primary_cohort_id, merged_raw_responses_dict).
    """
    MAX_BATCH_SIZE = 20  # Render times out beyond ~20 personas per /generate call

    print("\n[Simulatte Runner]")

    if not health_check():
        raise RuntimeError("Simulatte API is not reachable. Check SIMULATTE_API_URL.")

    # Determine cohort IDs to survey
    if existing_cohort_ids:
        cohort_ids = existing_cohort_ids
        print(f"  Using {len(cohort_ids)} pre-generated cohorts: {', '.join(cohort_ids)}")
    elif existing_cohort_id:
        cohort_ids = [existing_cohort_id]
        print(f"  Using existing cohort: {existing_cohort_id}")
    else:
        # Split into batches of MAX_BATCH_SIZE
        n_batches = (cohort_size + MAX_BATCH_SIZE - 1) // MAX_BATCH_SIZE
        batch_sizes = []
        remaining = cohort_size
        for _ in range(n_batches):
            b = min(remaining, MAX_BATCH_SIZE)
            batch_sizes.append(b)
            remaining -= b

        print(f"  Generating {cohort_size} personas in {n_batches} batch(es) of ≤{MAX_BATCH_SIZE}...")
        cohort_ids = []
        for i, bsize in enumerate(batch_sizes):
            print(f"  Batch {i+1}/{n_batches}: {bsize} personas...")
            cid = generate_cohort(cohort_size=bsize, domain=domain)
            cohort_ids.append(cid)

    # Merge responses across all cohorts
    merged: dict[str, list[str]] = {q["id"]: [] for q in questions}
    primary_cohort_id = cohort_ids[0]

    for i, cohort_id in enumerate(cohort_ids):
        if len(cohort_ids) > 1:
            print(f"\n  Surveying cohort {i+1}/{len(cohort_ids)}: {cohort_id}")
        batch_responses = run_survey_batch(cohort_id, questions)
        for qid, decisions in batch_responses.items():
            merged[qid].extend(decisions)

    n_total = sum(len(v) for v in merged.values())
    print(f"  Total responses collected: {n_total}")

    return primary_cohort_id, merged


if __name__ == "__main__":
    import sys
    from pathlib import Path

    questions_path = Path(__file__).parent / "data" / "questions.json"
    questions = json.loads(questions_path.read_text())

    # Use first 3 questions for a quick test
    test_questions = questions[:3]

    cohort_id, responses = run_simulatte_study(
        questions=test_questions,
        cohort_size=5,
    )

    print("\nRaw responses:")
    for qid, resps in responses.items():
        print(f"  {qid}: {resps}")
