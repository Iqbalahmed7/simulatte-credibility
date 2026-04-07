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
    # Sprint A-11 Fix 1: in01 B-overshoot fix.
    # A-10 result: B=62% (sim) vs Pew 44%. BJP personas are collapsing to B (somewhat satisfied)
    # instead of the correct A (very satisfied). Pew: 28% A, 44% B, 11% C, 16% D.
    # Root cause: current_conditions_stance anchor for bjp_supporter says "VERY satisfied" but
    # B-option is winning out. Add spread note to push bjp_supporter/lean back to A.
    # Sprint A-13: conviction-framing for in01.
    # A-12: B=60% vs Pew 44%. bjp_supporters collapsing to B (somewhat satisfied).
    "in01": (
        "Think about what 'somewhat satisfied' actually says about a person. "
        "'Somewhat satisfied' with democracy means you see it working — but with significant "
        "reservations, with doubts about whether it's truly functioning well. "
        "If you believe that India's democracy under the current government is genuinely working — "
        "elections happen freely, the people's mandate is respected, institutions are functioning — "
        "then 'somewhat satisfied' understates your view. "
        "'Very satisfied' (A) is the accurate answer for someone who genuinely has no major "
        "complaints about how Indian democracy is currently working. "
        "Say B if you're broadly satisfied but have real specific concerns. "
        "Say C or D if you are genuinely dissatisfied with how democracy is functioning. "
        "Choose the answer that honestly reflects your actual level of satisfaction."
    ),
    # Sprint A-11 Fix 2: in08 A-undershoot fix.
    # A-10 result: A=15% (sim) vs Pew 32%. BJP personas not producing "very good" economic answers.
    # The A anchor in current_conditions_stance says "VERY good" but only 15% reach it.
    # Add spread note to reinforce for bjp_supporter/lean that India's economy is genuinely "very good".
    # Sprint A-13: conviction-framing rewrite for in08.
    # A-12: A=18% vs Pew 32%. Same B-modal pull as in02/in03.
    "in08": (
        "Think carefully about what 'somewhat good' actually means about a person's view. "
        "'Somewhat good' describes cautious optimism — someone who sees improvement but has "
        "real doubts, who acknowledges problems as large as the gains. "
        "If you believe India's economy has fundamentally transformed under Modi — fastest-growing "
        "major economy, infrastructure revolution, digital payments, manufacturing growth — then "
        "'somewhat good' does not accurately describe your view. It is an understatement. "
        "'Very good' (A) is the accurate answer for someone who genuinely believes India's "
        "economic trajectory is strong and that Modi's policies have delivered real results. "
        "Say B if you see genuine growth but have significant concerns about inequality or "
        "job creation that temper your assessment. "
        "Say C or D if you believe economic conditions are actually poor. "
        "Choose the option that honestly reflects your real assessment."
    ),
    # Sprint A-10 Fix 1: in14 regression fix.
    # A-9 root cause: gender_norms_stance ("wife must obey", "men have job priority") bleeds
    # into this question about women's equal rights, pushing personas toward B instead of A.
    # Reality: traditional marital hierarchy views and belief in women's equal rights as citizens
    # COEXIST in Indian public opinion — 81% of Indians support women's equal rights even while
    # 87% say wives should obey husbands (Pew Religion Survey 2021). These are separate domains.
    # Fix: inject this distinction at question time so personas don't apply marital-role stance here.
    "in14": (
        # Sprint A-11 update: add B spread to fix 100% A collapse.
        # A-10 result: 100% A (sim) vs Pew 81% A / 14% B. The civic/marital distinction
        # fixed the regression but overcorrected — now ALL personas answer A.
        # Reality: urban, highly educated, younger Indians who are skeptical of full equality
        # in practice (vs principle) say B ('somewhat agree'). Add this nuance.
        "IMPORTANT: This question is about women having the same rights as men in society — "
        "voting, education, employment, and legal rights. This is completely separate from "
        "questions about marital roles, family hierarchy, or household structure. "
        "In India, holding traditional family values and believing women deserve equal rights "
        "as citizens are NOT contradictory — they coexist. Pew Research finds 81% of Indians "
        "strongly agree women should have equal rights. "
        "Most Indians say A — strongly agree. "
        "However, ~14% say B — somewhat agree — typically those who believe full equality "
        "exists in law but see practical barriers, or who have reservations about specific "
        "domains like inheritance or religious personal law. "
        "If you strongly believe in complete equal rights without reservation: answer A. "
        "If you agree in principle but see important qualifications: answer B."
    ),
    # Sprint A-10 Fix 2: in06 regression fix.
    # A-9 root cause: governance_stance ("parliamentary gridlock is bad, strong leader is good")
    # is bleeding into THIS question about representative democracy as a system — causing 0% C/D
    # and pushing all personas to B (somewhat good) instead of the real A=37%, C=8%, D=10%.
    # Fix: clarify the distinction between preferring strong leadership (in07) and evaluating
    # representative democracy as a system (in06). Add explicit C/D acknowledgement.
    "in06": (
        # Sprint A-11 update: strengthen C/D path.
        # A-10 result: 0% C/D (sim) vs 18% (Pew). Spread note mentions C but personas ignore it.
        # Root cause: current framing says "if you strongly value centralised governance... may be C"
        # — too hedged. Strengthen with explicit persona types who answer C/D.
        "IMPORTANT: This question asks whether having a representative democratic political system "
        "is good or bad — a separate question from whether you prefer strong decisive leadership. "
        "In India: 37% say very good (A), 44% somewhat good (B), 8% somewhat bad (C), 10% very bad (D). "
        "Most Indians value democracy. But 18% genuinely view it negatively: "
        "C — somewhat bad: voters who believe parliamentary democracy in India has produced "
        "corruption, inefficiency, and caste-based politics; who believe elected representatives "
        "serve themselves not voters; who think the democratic system enables dynastic parties. "
        "D — very bad: those who believe elections in India are fundamentally rigged by money "
        "and caste power, and that democracy has failed the poor entirely. "
        "If you are cynical about whether elections produce real accountability in India, "
        "your honest answer may be C or D — not A or B."
    ),
    # Sprint A-10 Fix 3: in11 collapse fix.
    # A-9 root cause: all 40 personas answered A (very important) — 100% collapse.
    # Reality: Pew says 84% A, 11% B, 3% C, 2% D. Urban/educated/secular personas should answer B/C.
    # Fix: spread note directing secular, urban, professional personas toward B.
    "in11": (
        "IMPORTANT: While religion is very important to most Indians, genuine variation exists. "
        "Urban, educated, and professionally-oriented Indians often say religion is 'somewhat "
        "important' (B) rather than 'very important' (A) in their personal daily lives. "
        "Secular or non-religious Indians may say 'not too important' (C). "
        "If you are urban, highly educated, or hold secular values, your honest answer may be "
        "B — somewhat important — not A. Do not default to A if religion plays a smaller role "
        "in your daily life than in India's general population."
    ),
    # Sprint A-10 Fix 4: in02/in03 A-option push.
    # A-9: in02 A=45% vs Pew 56%; in03 A=25% vs Pew 43%. Too many bjp_lean/bjp_supporter
    # landing on B (somewhat favorable) instead of A (very favorable).
    # Sprint A-13: conviction-framing rewrite for in02.
    # A-12 diagnosis: B-modal pull — even bjp_supporters defaulting to "somewhat favorable".
    # "Somewhat favorable" is the answer of a reluctant or ambivalent voter — not a committed one.
    # New strategy: make choosing B feel like an inaccurate self-representation.
    "in02": (
        "Think carefully about what 'somewhat favorable' actually means about a person. "
        "'Somewhat favorable' describes someone who has reservations — who sees both positives "
        "and negatives, who is not fully committed, who hedges. "
        "If you genuinely believe Modi has transformed India, stands for Hindu values, and has "
        "delivered real development — then 'somewhat favorable' does NOT describe your view. "
        "It would be inaccurate. You are not lukewarm about him. "
        "'Very favorable' (A) means you strongly support him — this is the accurate answer for "
        "a committed BJP supporter. "
        "Say B only if you genuinely have significant reservations about Modi specifically. "
        "Say C or D if you are critical. "
        "Do not pick 'somewhat' just because it feels safer — pick the one that accurately "
        "represents your actual view."
    ),
    # Sprint A-13: add in03 conviction-framing spread note.
    # A-11 removal backfired: removing the note kept B at 60%. Reinstating with conviction framing
    # instead of prescriptive framing ("your answer is A" was the problem, not the note itself).
    "in03": (
        "Think carefully about what 'somewhat favorable' actually means about a person. "
        "'Somewhat favorable' toward the BJP describes someone with reservations — who sees "
        "value in the party but has significant doubts about its direction or leadership. "
        "If you believe the BJP represents your values, your community, and India's future — "
        "if BJP is your political home — then 'somewhat favorable' understates your actual view "
        "and does not accurately represent you. "
        "'Very favorable' (A) is the accurate answer for someone whose political identity "
        "is genuinely aligned with the BJP. "
        "Say B if you broadly support BJP but have real reservations about specific policies "
        "or leadership decisions. "
        "Say C or D if you are skeptical or opposed. "
        "Choose the option that accurately represents your real political conviction."
    ),
    # Sprint A-10 Fix 5: in12 A-option push.
    # A-9: A=45% vs Pew 64%. bjp_lean personas are going B instead of A.
    # Both bjp_supporter AND bjp_lean should answer A (completely agree) for in12.
    # Sprint A-13: conviction-framing for in12.
    # A-12: A=38% vs Pew 64%. B-modal pull — "somewhat agree" is overrepresented.
    "in12": (
        "Think about what 'somewhat agree' actually says about a person's values. "
        "'Somewhat agree' that a wife must obey her husband means you see it as partially true — "
        "a preference, not a conviction; something you broadly accept but with reservations. "
        "In Indian households where dharma and traditional family roles are genuinely held values — "
        "where the husband as head of household is the natural, sincere belief — "
        "'somewhat agree' does not capture your actual position. It is an understatement. "
        "'Completely agree' (A) is the accurate answer for someone who genuinely holds "
        "traditional Indian family values as a real conviction, not just a preference. "
        "Say B if you broadly accept traditional roles but see room for partnership and negotiation. "
        "Say C or D if you believe in more equal marital roles. "
        "Choose the option that honestly represents your actual beliefs about family."
    ),
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
