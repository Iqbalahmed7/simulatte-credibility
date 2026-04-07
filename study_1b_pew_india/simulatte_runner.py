"""
simulatte_runner.py — Run Pew India survey questions through the Simulatte API.

Flow:
  1. Generate an India general population cohort via POST /generate
     (using 'india_general' domain — 40 profiles covering religion, caste,
      region, urban tier, and BJP/opposition political lean)
  2. Format each Pew question with explicit categorical options
  3. POST /survey with the formatted questions (one question at a time)
  4. Parse the free-text 'decision' fields back to option letters
  5. Return raw responses dict: {question_id: [response_str, ...]}

Demographic composition:
  Uses the 'india_general' domain pool — 40 profiles approximating the
  Pew Research Center India survey composition:
  nationally representative Indian adults across religion, region, urban tier,
  income, education, and political lean (BJP/opposition spectrum).

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

# India general population domain — matches Pew India sample composition.
DOMAIN = "india_general"

# Number of personas per cohort.
COHORT_SIZE = int(os.getenv("SIMULATTE_COHORT_SIZE", "40"))

# Claude model for survey responses
SURVEY_MODEL = os.getenv("SIMULATTE_SURVEY_MODEL", "claude-haiku-4-5-20251001")

_TIMEOUT = httpx.Timeout(300.0, connect=30.0)  # Long timeout — Render cold starts

# ---------------------------------------------------------------------------
# Question formatting
# ---------------------------------------------------------------------------


# Sprint A-6 Fix 2: per-question spread notes for questions stuck at 100% single option.
# Root cause: in05/in09/in15 showed 100% A or 100% B across all 5 sprints despite
# spread anchors in policy stance fields. Stance-field approach is insufficiently salient
# at response time — the model answers from a "universal Indian" frame.
# Fix: inject the spread instruction directly into the survey question prompt so it
# appears at the exact moment of decision, not buried in the persona's background.
_SPREAD_QUESTION_NOTES: dict[str, str] = {
    "in05": (
        "IMPORTANT: Indians hold genuinely varied views on this depending on political lean. "
        "BJP supporters and nationalists see India's global influence as clearly 'getting stronger'. "
        "Opposition supporters and skeptics see it as 'staying about the same'. "
        "Strong critics see it 'getting weaker' due to polarisation. "
        "Answer based on YOUR specific political perspective — do NOT default to the majority view."
    ),
    "in09": (
        "IMPORTANT: Trust in government reflects genuine political conviction, not a moderate default. "
        "People who deeply support the current government naturally express HIGH trust — a lot. "
        "That is what genuine support looks like in survey data. "
        "People who voted for this government and believe in its direction trust it a lot, not just somewhat. "
        "People who are truly neutral say somewhat. "
        "People who oppose the government say not much or not at all. "
        "Answer from your actual political position — do not drift toward the middle if you genuinely support or oppose this government."
    ),
    "in13": (
        "IMPORTANT: This question is about gender roles in employment. "
        "Answer based on your own cultural values — do NOT assume a universal view. "
        "In India, opinions genuinely vary: traditional voters and rural communities "
        "believe men should have priority for jobs when jobs are scarce (option A). "
        "Others disagree to varying degrees. "
        "Answer honestly based on YOUR cultural background and values. "
        "YOU MUST RESPOND WITH ONLY THE SINGLE LETTER A, B, C OR D. "
        "Nothing else. Not a word. Not a sentence. Just the one letter."
    ),
    "in15": (
        # Sprint A-9 Fix: reframe away from party identity entirely.
        # A-8 root cause: framing 'BJP supporters answer B' triggered explicit meta-aware
        # resistance — personas said 'I'm a political moderate who rejects BJP identity,
        # so I won't follow that instruction.' The party-identity anchor backfired for
        # ~50% of the pool (moderate/opposition_lean/neutral personas).
        # Fix: replace party-based framing with development-priority framing that moderate
        # personas can accept without feeling it conflicts with their self-identity.
        "IMPORTANT: Indians vary significantly on how severe a threat climate change is. "
        "Development-focused voters who prioritise economic growth and jobs typically answer B — "
        "somewhat of a threat — real, but not the most urgent issue when millions need "
        "electricity, roads, and employment. "
        "If you believe India's development and economic growth should not be sacrificed for "
        "climate targets, your answer is B — somewhat of a threat, not the most urgent issue. "
        "Voters who have personally experienced floods, droughts, or extreme heat as a "
        "life-defining disruption typically answer A — a major threat. "
        "Answer B if you prioritise development over climate action. "
        "Answer A only if climate disruption has directly and severely affected your own life. "
        "Do NOT default to A."
    ),
}


def format_question_for_survey(question: dict) -> str:
    """
    Format a Pew India question with explicit categorical options.

    Forces the persona to respond with a single option letter.

    Sprint A-6 Fix 2: injects per-question spread notes for in05/in09/in15
    which have been stuck at 100% single option across all 5 sprints.
    """
    options_text = "\n".join(
        f"  {letter}) {text}"
        for letter, text in question["options"].items()
    )
    question_id = question.get("id", "")
    spread_note = _SPREAD_QUESTION_NOTES.get(question_id, "")
    spread_block = f"{spread_note}\n\n" if spread_note else ""

    return (
        f"{question['text']}\n\n"
        f"{spread_block}"
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
    Retries up to 5 times on 5xx errors (Render cold-start flakiness).
    """
    print(f"  Generating cohort: {cohort_size} personas, domain={domain}...")
    payload = {
        "count": cohort_size,
        "domain": domain,
        "mode": "quick",
        "anchor_overrides": {},
        "persona_id_prefix": "pew_in",
        "sarvam_enabled": False,
        "skip_gates": True,
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
                wait = min(attempt * 20, 90)
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
    fast enough to avoid Render's 502 gateway timeout.

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
    Run all India Pew questions against a cohort, one question at a time.

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
    Full Simulatte India study runner.

    Generates in batches of MAX_BATCH_SIZE (20) to avoid Render's 300s
    generation timeout. Merges responses across batches.

    Returns:
        Tuple of (primary_cohort_id, merged_raw_responses_dict).
    """
    MAX_BATCH_SIZE = 20

    print("\n[Simulatte Runner — India]")

    if not health_check():
        raise RuntimeError("Simulatte API is not reachable. Check SIMULATTE_API_URL.")

    if existing_cohort_ids:
        cohort_ids = existing_cohort_ids
        print(f"  Using {len(cohort_ids)} pre-generated cohorts: {', '.join(cohort_ids)}")
    elif existing_cohort_id:
        cohort_ids = [existing_cohort_id]
        print(f"  Using existing cohort: {existing_cohort_id}")
    else:
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

    questions_path = Path(__file__).parent / "data" / "questions_india.json"
    questions = json.loads(questions_path.read_text())

    # Quick test — first 3 questions, 5 personas
    test_questions = questions[:3]

    cohort_id, responses = run_simulatte_study(
        questions=test_questions,
        cohort_size=5,
    )

    print("\nRaw responses:")
    for qid, resps in responses.items():
        print(f"  {qid}: {resps}")
