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
    # Sprint A-15: reinforce in11 — A-14 collapsed back to 100% A (Pew: 84% A, 11% B, 3% C).
    # Root cause: pool rebalance added more religious bjp_supporters overwhelming the secular
    # urban personas. Need stronger differentiation to reach B=11% and C=3%.
    "in11": (
        "IMPORTANT: While 84% of Indians say religion is very important, 16% say otherwise. "
        "In India, urban, educated, and professionally-oriented people genuinely differ: "
        "Postgraduate-educated metro residents in Bengaluru, Mumbai, Kolkata, Kochi, Chennai "
        "who work in professional or tech industries often say religion is 'somewhat important' (B) — "
        "they respect their faith but it does not dominate their daily decisions. "
        "This is not disrespectful of religion — it is accurate for many urban professionals. "
        "Pew data confirms: 11% of Indians say 'somewhat important' (B). "
        "If you are highly educated (postgraduate), live in a metro city, work in a professional "
        "field, and your daily life is primarily driven by career and family rather than religious "
        "observance — your honest answer is likely B, not A. "
        "Do not say 'very important' (A) if religion genuinely plays a secondary role in your "
        "personal daily life. B is the accurate answer for secular urban professionals."
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
    # Sprint A-13: conviction-framing for in12. A-12: A=38% vs Pew 64%.
    # Sprint A-17: add D-floor fix — A-16 D=18% vs Pew D=6%.
    # Root cause: Muslim opposition personas (Mohammad Iqbal, Fatima Begum, Abdul Karim, Salim Khan)
    # answering D because their political opposition to BJP feels like opposition to traditional values.
    # Reality: Islamic teaching strongly supports marital hierarchy and wifely obedience —
    # Muslim voters who oppose BJP politically would often say A or B on this question.
    "in12": (
        "Think about what 'somewhat agree' actually says about a person's values. "
        "'Somewhat agree' that a wife must obey her husband means you see it as partially true — "
        "a preference, not a conviction; something you broadly accept but with reservations. "
        "In Indian households where dharma, Islamic teaching, or traditional family roles are "
        "genuinely held values — where the husband as head of household is the natural, sincere "
        "belief — 'somewhat agree' does not capture your actual position. It is an understatement. "
        "'Completely agree' (A) is the accurate answer for someone who genuinely holds "
        "traditional family values as a real conviction — Hindu OR Muslim. "
        "IMPORTANT: Traditional views on marital hierarchy are INDEPENDENT of political affiliation. "
        "Islamic teaching, Hindu dharma, and traditional Indian family values ALL support the "
        "husband's authority in the household. Opposing the BJP government does NOT mean "
        "rejecting traditional family values — many Congress and opposition voters hold these "
        "traditional beliefs strongly. Muslim voters who oppose BJP may still completely agree "
        "with this statement based on their religious values. "
        "Say A if traditional marital hierarchy is a genuine personal conviction. "
        "Say B if you broadly accept traditional roles but see room for negotiation. "
        "Say C or D only if you personally believe in fully equal marital roles in your own life."
    ),
    # Sprint A-15: add in07 spread note — A-overshoot (A=68% vs Pew A=44%, B=44%).
    # Sprint A-17/A-18: D-floor fix + simplification — A=62% B=12% in A-18.
    # Sprint A-19: target bjp_lean→B. Root cause: bjp_lean says A despite valuing democracy.
    # Key insight: "somewhat agree" means you want strong leadership IN A DEMOCRACY — not INSTEAD.
    "in07": (
        "IMPORTANT: Pew data — 44% completely agree (A), 44% somewhat agree (B), "
        "7% somewhat bad (C), 5% very bad (D). "
        "The distinction between A and B is about democratic accountability: "
        "A = 'Completely agree': You believe India genuinely would be BETTER OFF with a strong "
        "leader who bypasses elections and parliament. You see democratic accountability as "
        "an obstacle, not a feature. This is a sincere conviction that non-democratic governance "
        "would produce better outcomes for India. "
        "B = 'Somewhat agree': You value strong, decisive leadership and appreciate leaders "
        "who get things done efficiently. BUT you still believe elections and parliament "
        "serve an important purpose — they give people a voice and keep leaders accountable. "
        "You want a STRONG leader who wins elections and leads decisively from that mandate — "
        "not a leader who bypasses elections entirely. This is the honest answer for someone "
        "who admires Modi's strong governing style but still values democratic elections. "
        "If you support strong governance WITHIN democracy rather than INSTEAD of it — answer B. "
        "For those who value democracy: C is the honest answer for most principled democrats "
        "(somewhat bad). D is for absolute catastrophists only (5% of Indians)."
    ),
    # Sprint A-15: add in04 spread note — A-14 caused D-overshoot (D=42% vs Pew D=19%, C=18%).
    # Sprint A-17: rewrite — A-16 D=48% still far above Pew 19%. Narrative constraint too strong.
    # Root cause: bjp_supporter narrative says "strongly critical of Congress" → all 14 say D.
    # Fix: make C feel like an accurate self-representation for many BJP supporters by emphasising
    # the intensity difference between C and D on this specific scale.
    "in04": (
        "IMPORTANT: Views on the Indian National Congress (INC/Congress). "
        "Pew data: 24% very favorable (A), 38% somewhat favorable (B), "
        "18% somewhat unfavorable (C), 19% very unfavorable (D). "
        "Think carefully about what 'very unfavorable' actually means on this scale. "
        "'Very unfavorable' (D) = Congress makes you feel genuine anger, disgust, or alarm. "
        "It's not just that you prefer BJP — it's that the thought of Congress returning to "
        "power fills you with real dread or outrage. This is an emotional intensity, not just "
        "a political preference. "
        "'Somewhat unfavorable' (C) = You think Congress has had corruption and governance "
        "failures. You prefer BJP and wouldn't vote Congress. But you don't feel visceral "
        "hostility — it's a rational political assessment, not an emotional identity. "
        "IMPORTANT: Many committed BJP voters — even those who believe Congress failed India — "
        "honestly say C because their opposition is based on policy and performance, not rage. "
        "Only say D if your opposition to Congress goes beyond intellectual disagreement "
        "into genuine personal anger or alarm. Many BJP supporters honestly say C. "
        "INC supporters and neutrals: A or B. "
        "Prefer BJP but no deep hostility to Congress: C. "
        "Genuinely angry or alarmed at the idea of Congress: D."
    ),
    # Sprint A-16: strengthen in05 — A-15 shows A-overshoot (A=82% vs Pew 68%, C=2% vs Pew 19%).
    # Pool rebalance increased bjp_supporters pushing A; need to push C for opposition/secular.
    "in05": (
        "IMPORTANT: Indians hold genuinely varied views on India's global influence. "
        "Pew data: 68% 'getting stronger' (A), 13% 'staying about the same' (B), 19% 'getting weaker' (C). "
        "BJP supporters and nationalists: 'getting stronger' (A) — India's global power is rising. "
        "Swing/neutral voters: 'staying about the same' (B) — incremental progress, not decisive rise. "
        "Opposition supporters, secular voters, and those concerned about India's international "
        "reputation due to polarisation, democratic backsliding, or minority rights issues: "
        "'getting weaker' (C) — India's soft power and moral authority are declining. "
        "19% of Indians say C — this is a significant minority. "
        "If you are critical of the current government's impact on India's international image, "
        "or concerned about how India is perceived globally due to domestic issues, "
        "your honest answer is C — not A or B."
    ),
    # Sprint A-16: rewrite in09 — explicit persona-type mapping.
    # Sprint A-17: CATASTROPHIC bimodal collapse from trust 0.68/0.65.
    # Sprint A-18: trust fixed (0.74/0.72), simplified note — A=62%, C=25%, B=12% unchanged.
    #   Root cause: 13 opposition-leaning personas (32.5% of pool) all answering C — but Pew shows
    #   only 7% C. Opposition personas treat government trust = BJP political approval (wrong).
    # Sprint A-19: KEY FIX — distinguish INSTITUTIONAL TRUST from POLITICAL APPROVAL.
    #   Government trust = does the government function, deliver services, maintain order?
    #   Political approval = do you support BJP and Modi specifically?
    #   These are DIFFERENT questions. Even opposition voters often say "somewhat a lot" on
    #   institutional trust because Indian government DOES generally function as an institution.
    "in09": (
        "IMPORTANT: This question asks about INSTITUTIONAL TRUST in the national government — "
        "not about approval of BJP or Modi. These are different things. "
        "Institutional trust means: does the government as an institution generally function, "
        "deliver public services (roads, schools, healthcare schemes), maintain order, and "
        "implement programs? Even people who vote for opposition parties can have substantial "
        "institutional trust because they distinguish between 'the government functions' and "
        "'I approve of the BJP'. "
        "Pew India data: A=42% (a lot), B=50% (somewhat a lot), C=6% (not much), D=2% (not at all). "
        "B = 'Somewhat a lot': I trust the government as an institution — it generally delivers, "
        "schemes mostly reach people, order is maintained — but implementation is imperfect and "
        "real-world gaps exist. This is the honest answer for most Indians regardless of "
        "political affiliation. Even opposition voters can say B because they acknowledge "
        "the government functions as an institution even if they oppose its political direction. "
        "C = 'Not much': The government fails to deliver EVEN BASIC services. Schemes mostly "
        "do NOT reach people. Governance is fundamentally broken. "
        "Only say C or D if you believe the Indian government is institutionally failing — "
        "not merely that you oppose the ruling party politically."
    ),
    # Sprint A-15: rewrite in13 — pull bjp_lean toward B. Produced 92% accuracy.
    # Sprint A-17/A-18: D-framing backfired, simplified — A=62% B=12%.
    # Sprint A-19: widow/sole-earner examples caused blanket B flip: A=5%, B=70% — catastrophic.
    # Sprint A-20: return to A-15-style balanced framing without triggering examples.
    "in13": (
        "IMPORTANT: In India, 48% completely agree that men should have priority for jobs (A), "
        "and 35% somewhat agree (B). Both answers reflect traditional values. "
        "The difference is whether you hold this as an absolute principle or a general norm: "
        "'Completely agree' (A) means you see male employment priority as an absolute conviction "
        "with no exceptions — in every situation, regardless of context. "
        "'Somewhat agree' (B) means you hold the traditional view that men are generally the "
        "primary breadwinners and should have employment priority, but you acknowledge "
        "this principle needs to be applied with judgment in real-life situations. "
        "B is NOT a progressive position — it is the nuanced traditional view held by many "
        "BJP supporters, OBC community members, and traditional families across India. "
        "Choose A if your conviction is absolute and unconditional. "
        "Choose B if you hold the traditional principle but apply it with judgment. "
        "Say C or D only if you personally believe in full gender equality in employment."
    ),
    # Sprint A-15: rewrite in15 — corrected B-overshoot from old "do NOT default to A" note.
    # Sprint A-17: rewrite with visceral India climate evidence — B=65% unchanged (zero effect).
    # Sprint A-18: root cause — personas interpret "major threat" as "top development priority".
    # They choose B to avoid implying development should be deprioritised.
    # Fix: explicitly decouple "major threat" from policy priority; clarify what A means.
    "in15": (
        "IMPORTANT: Read this scale carefully. "
        "A = 'A major threat': Climate change is causing SERIOUS, SIGNIFICANT damage to India. "
        "Saying 'major threat' does NOT mean climate change is more important than development. "
        "It does NOT mean you want India to slow down economically. "
        "It does NOT mean you are critical of the current government. "
        "It simply means: the physical damage from climate change to India is serious. "
        "B = 'Somewhat of a threat': The physical damage from climate change to India is real "
        "but moderate — not severe. The risk is somewhat exaggerated. "
        "Pew finds 62% of Indians say A ('major threat'). India's own experience justifies this: "
        "record heatwaves, annual flooding in Bihar and Assam, intensifying cyclones in Odisha, "
        "monsoon disruption affecting agriculture, Himalayan glacier retreat. "
        "These are physical facts about damage, not political statements about policy. "
        "A farmer in Bihar who votes BJP and wants more development can honestly say 'major threat' "
        "because his crops are failing from monsoon disruption. That is not a contradiction. "
        "Choose A if you believe climate change is causing serious physical damage to India. "
        "Choose B only if you believe climate's physical damage to India is moderate, not severe."
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
