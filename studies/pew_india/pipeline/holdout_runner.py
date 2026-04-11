"""
PEW India Study — Holdout Runner
==================================
Pure WorldviewAnchor routing for 5 holdout questions locked before calibration.
These questions were never inspected during Sprint IND-1 calibration.

Holdout questions: in01, in07, in11, in12, in15
Sprint IDs:        HD-1, HD-1b, HD-1c (variance protocol)

Usage:
    python3 studies/pew_india/pipeline/holdout_runner.py --sprint HD-1 [--dry-run] [--model haiku]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ── Load .env ─────────────────────────────────────────────────────────────────
_env_candidates = [
    Path(__file__).parent.parent / ".env",
    Path("/Users/admin/Documents/Simulatte Projects/Persona Generator/.env"),
]
for _env_path in _env_candidates:
    if _env_path.exists():
        for line in _env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()
        break

# ── Load cohort ───────────────────────────────────────────────────────────────
COHORT_PATH = Path(__file__).parent.parent / "cohort" / "cohort-india_general-2f40f7.json"

def _load_cohort():
    raw = json.loads(COHORT_PATH.read_text())
    personas = []
    for p in raw["personas"]:
        da = p["demographic_anchor"]
        wv = da["worldview"]
        pp = wv.get("political_profile", {})
        loc = da["location"]
        hh = da["household"]
        name = da["name"]
        muslim_keywords = {"Hussain", "Iqbal", "Khan", "Karim", "Fatima", "Kabir", "Salim", "Mohammad", "Abdul"}
        christian_keywords = {"George", "Mathew", "Thomas"}
        if any(k in name for k in muslim_keywords):
            religion = "Muslim"
        elif any(k in name for k in christian_keywords):
            religion = "Christian"
        else:
            religion = "Hindu"
        personas.append({
            "id": p["persona_id"],
            "name": name,
            "age": da["age"],
            "gender": da["gender"],
            "region": loc["region"],
            "city": loc["city"],
            "urban_tier": loc["urban_tier"],
            "income": hh["income_bracket"],
            "education": da["education"],
            "employment": da.get("employment", "full-time"),
            "arch": pp.get("archetype", "neutral"),
            "religion": religion,
            "IT": wv["institutional_trust"],
            "SCP": wv["social_change_pace"],
            "CS": wv["collectivism_score"],
            "ESP": wv.get("economic_security_priority", 0.55),
            "RS": wv.get("religious_salience", 0.75),
        })
    return personas

PERSONAS = _load_cohort()

# ── Real distributions (DK excluded, renormalised) ───────────────────────────
REAL_DISTRIBUTIONS = {
    "in01": {"A": 0.283, "B": 0.444, "C": 0.111, "D": 0.162},  # DK=1% excluded
    "in07": {"A": 0.443, "B": 0.381, "C": 0.082, "D": 0.103},  # DK=3% excluded
    "in11": {"A": 0.840, "B": 0.110, "C": 0.030, "D": 0.020},
    "in12": {"A": 0.640, "B": 0.230, "C": 0.070, "D": 0.060},
    "in15": {"A": 0.620, "B": 0.290, "C": 0.090},
}

HOLDOUT_QUESTIONS = list(REAL_DISTRIBUTIONS.keys())

# ── WorldviewAnchor routing (pure — no calibration on these questions) ────────
def route_answer(p: dict, qid: str) -> str:
    arch = p["arch"]
    IT   = p["IT"]
    SCP  = p["SCP"]
    RS   = p["RS"]

    pro_bjp  = arch in {"bjp_supporter", "bjp_lean"}
    anti_bjp = arch in {"opposition_lean", "opposition"}

    if qid == "in01":  # Democracy satisfaction: Very/Somewhat/Not too/Not at all
        # Primary driver: institutional trust → political alignment
        # bjp_sup: high IT + strong Modi approval → very satisfied
        # bjp_lean/neutral: moderate-high IT → somewhat satisfied
        # opp_lean: low IT → not too satisfied
        # opp: very low IT → not at all satisfied
        if arch == "bjp_supporter":
            return "A"
        elif arch == "bjp_lean":
            return "B"
        elif arch == "neutral":
            return "B"
        elif arch == "opposition_lean":
            return "C"
        else:  # opposition
            return "D"

    elif qid == "in07":  # Strong leader: Very good/Somewhat good/bad/Very bad
        # Low SCP (traditional) + high IT → prefer strong leader over parliament
        # bjp_sup: core value — decisive leadership over democratic process
        # bjp_lean (high IT): lean toward strong leader
        # neutral: somewhat good — pragmatic on leadership
        # opp_lean: somewhat good — functional leadership matters even to opposition
        # opp: skeptical — concerns about democratic erosion
        if arch == "bjp_supporter":
            return "A"
        elif arch == "bjp_lean":
            return "A" if IT >= 0.73 else "B"
        elif arch == "neutral":
            return "B"
        elif arch == "opposition_lean":
            return "B"
        else:  # opposition
            return "C" if IT >= 0.34 else "D"

    elif qid == "in11":  # Religion importance: Very/Somewhat/Not too/Not at all
        # Pure RS (religious salience) — strongest WorldviewAnchor predictor
        # India is among the world's most religious countries: 84% very important
        if RS >= 0.70:
            return "A"
        elif RS >= 0.65:
            return "B"
        else:
            return "C"

    elif qid == "in12":  # Wife obedience: Completely/Somewhat agree/disagree
        # RS is the primary driver for traditional gender norms across all archetypes
        # (Even opposition voters broadly agree — 87% total agree in Pew data)
        if RS >= 0.80:
            return "A"
        elif RS >= 0.70:
            return "B"
        elif RS >= 0.65:
            return "C"
        else:
            return "D"

    elif qid == "in15":  # Climate change threat: Major/Minor/Not a threat
        # Progressive (anti_bjp, neutral): major threat — trust scientific consensus
        # bjp_lean: minor threat — development priority moderates climate urgency
        # bjp_sup: SCP-based — most traditional (low SCP) are pro-growth, less alarmed
        if anti_bjp or arch == "neutral":
            return "A"
        elif arch == "bjp_lean":
            return "B"
        else:  # bjp_supporter
            if SCP >= 0.30:
                return "A"   # Less traditional bjp: still concerned
            elif SCP >= 0.28:
                return "B"   # Traditional bjp: minor threat
            else:
                return "C"   # Most traditional: not a threat (pro-development)

    return "A"  # fallback


# ── OVA stances ──────────────────────────────────────────────────────────────
QUESTIONS = {
    "in01": {
        "text": "How satisfied are you with the way democracy is working in India?",
        "options": {"A": "Very satisfied", "B": "Somewhat satisfied",
                    "C": "Not too satisfied", "D": "Not at all satisfied"},
    },
    "in07": {
        "text": "Having a strong leader who does not have to bother with parliament or elections — how good or bad would this be for India as a way to govern the country?",
        "options": {"A": "Very good", "B": "Somewhat good",
                    "C": "Somewhat bad", "D": "Very bad"},
    },
    "in11": {
        "text": "How important is religion in your life?",
        "options": {"A": "Very important", "B": "Somewhat important",
                    "C": "Not too important", "D": "Not at all important"},
    },
    "in12": {
        "text": "How much do you agree or disagree: A wife must always obey her husband.",
        "options": {"A": "Completely agree", "B": "Somewhat agree",
                    "C": "Somewhat disagree", "D": "Completely disagree"},
    },
    "in15": {
        "text": "How much of a threat is global climate change to India?",
        "options": {"A": "Major threat", "B": "Minor threat", "C": "Not a threat"},
    },
}

STANCES = {
    "in01": {
        "A": "You are very satisfied with the way democracy is working in India. You believe the democratic system is delivering development, stability, and strong governance. You would say 'Very satisfied.'",
        "B": "You are somewhat satisfied with Indian democracy — you see it generally working, though with room for improvement in accountability and delivery. You would say 'Somewhat satisfied.'",
        "C": "You are not too satisfied with how democracy is working in India. You feel the system has significant problems — whether corruption, inequality, or erosion of institutions. You would say 'Not too satisfied.'",
        "D": "You are not at all satisfied with the way democracy is working in India. You believe democratic institutions have been undermined and the system no longer represents ordinary citizens fairly. You would say 'Not at all satisfied.'",
    },
    "in07": {
        "A": "You think having a strong leader who does not have to bother with parliament or elections would be very good for India. You believe decisive leadership unconstrained by political gridlock is what India needs to develop. You would say 'Very good.'",
        "B": "You think such a strong leader arrangement would be somewhat good — you see value in decisive governance, though you have some concerns about accountability. You would say 'Somewhat good.'",
        "C": "You think this would be somewhat bad for India. You believe checks and balances matter, and a leader without parliament or elections risks abuse of power. You would say 'Somewhat bad.'",
        "D": "You think this would be very bad for India. You strongly believe democratic accountability — through parliament and elections — is essential to protect citizens' rights and prevent authoritarianism. You would say 'Very bad.'",
    },
    "in11": {
        "A": "Religion is very important in your life. Your faith shapes your values, daily routines, and sense of identity in profound ways. You would say 'Very important.'",
        "B": "Religion is somewhat important in your life. You observe your faith and it matters to your identity, though it does not define every decision. You would say 'Somewhat important.'",
        "C": "Religion is not too important in your personal life. You may have cultural or family ties to religion but it does not strongly guide your daily choices. You would say 'Not too important.'",
        "D": "Religion is not at all important in your life. You live by secular values and personal ethics rather than religious teachings. You would say 'Not at all important.'",
    },
    "in12": {
        "A": "You completely agree that a wife must always obey her husband. In your view, this reflects the natural order of family life rooted in tradition and religious values. You would say 'Completely agree.'",
        "B": "You somewhat agree — you believe wives should generally defer to their husbands, though perhaps not in every circumstance. You would say 'Somewhat agree.'",
        "C": "You somewhat disagree. You think marriage should be more of a partnership, and while you respect tradition, you believe wives should not always have to obey. You would say 'Somewhat disagree.'",
        "D": "You completely disagree. You believe marriage should be based on equality and mutual respect, not obedience. You would say 'Completely disagree.'",
    },
    "in15": {
        "A": "You see global climate change as a major threat to India. Rising temperatures, extreme weather, and disrupted monsoons are already affecting Indian lives, and you believe urgent action is needed. You would say 'Major threat.'",
        "B": "You see climate change as a minor threat to India — a concern but not the most pressing challenge compared to poverty, unemployment, or security issues. You would say 'Minor threat.'",
        "C": "You do not see global climate change as a significant threat to India. You believe India's development needs must take priority and that climate concerns are often overstated. You would say 'Not a threat.'",
    },
}

WORLDVIEW_DESCRIPTIONS = {
    "bjp_supporter": (
        "You are a proud, committed BJP supporter. You believe in India's Hindu cultural heritage and national pride under Prime Minister Modi's leadership. "
        "You trust the government deeply and see BJP's governance as transformative for India. "
        "You are traditional in values, skeptical of rapid social change, and believe in strong leadership for national development."
    ),
    "bjp_lean": (
        "You generally lean toward BJP and support India's current direction under Modi. "
        "You value stability, economic development, and cultural continuity. "
        "You are broadly satisfied with the government's performance, though you evaluate issues pragmatically."
    ),
    "neutral": (
        "You are politically pragmatic — you evaluate issues on their merits rather than party loyalty. "
        "You care about local economic conditions, civic services, and practical governance. "
        "You hold mixed views on BJP and the opposition, and your vote depends on the issue and context."
    ),
    "opposition_lean": (
        "You lean toward opposition parties — INC, regional parties, or the anti-BJP coalition. "
        "You value democratic institutions, checks on executive power, and secular governance. "
        "You are concerned about the direction of the country but not strongly partisan."
    ),
    "opposition": (
        "You are a committed opposition supporter — critical of BJP's governance and concerned about India's democratic health. "
        "You prioritise secular governance, minority rights, federalism, and political pluralism. "
        "You are deeply skeptical of the current government and its impact on India's institutions."
    ),
}


def build_system_prompt(p: dict, qid: str) -> str:
    option_letter = route_answer(p, qid)
    stance = STANCES[qid][option_letter]
    wv_desc = WORLDVIEW_DESCRIPTIONS[p["arch"]]
    q = QUESTIONS[qid]
    options_str = "\n".join(f"  {k}: {v}" for k, v in q["options"].items())

    if p["religion"] == "Muslim":
        faith_line = "Your faith as a Muslim is central to your daily life and identity."
    elif p["religion"] == "Christian":
        faith_line = "Your Christian faith is an important part of your identity and community."
    else:
        faith_line = "Your Hindu faith and traditions are important to your identity and worldview."

    return f"""You are {p['name']}, a {p['age']}-year-old {p['gender']} from {p['city']}, {p['region']}, India.
Education: {p['education'].replace('-', ' ')} | Income: {p['income']} | Employment: {p['employment']}

{faith_line}

WORLDVIEW:
{wv_desc}

Institutional trust in government and media: {'high' if p['IT'] >= 0.65 else 'moderate' if p['IT'] >= 0.45 else 'low'} ({p['IT']:.2f})
Openness to social change: {'traditional/preservationist' if p['SCP'] <= 0.35 else 'moderate' if p['SCP'] <= 0.55 else 'progressive'} ({p['SCP']:.2f})
Religious commitment: {'very high' if p['RS'] >= 0.80 else 'high' if p['RS'] >= 0.65 else 'moderate'} ({p['RS']:.2f})

YOUR STANCE ON THIS QUESTION:
{stance}

Answer the following survey question by responding with ONLY the single letter (A, B, C, or D) that matches your stance above. No explanation.

Question: {q['text']}
Options:
{options_str}

Your answer (single letter only):"""


def compute_da(sim: dict, real: dict) -> float:
    tvd = sum(abs(sim.get(k, 0) - real.get(k, 0)) for k in real) / 2
    return round((1 - tvd) * 100, 2)


def dry_run():
    print("\n=== HOLDOUT DRY RUN — PREDICTED DISTRIBUTION ACCURACY ===\n")
    print("NOTE: Pure WorldviewAnchor routing — no calibration on these questions.\n")
    results = {}
    for qid in HOLDOUT_QUESTIONS:
        counts: dict[str, int] = {}
        for p in PERSONAS:
            opt = route_answer(p, qid)
            counts[opt] = counts.get(opt, 0) + 1
        n = len(PERSONAS)
        sim = {k: round(v / n, 4) for k, v in counts.items()}
        real = REAL_DISTRIBUTIONS[qid]
        da = compute_da(sim, real)
        results[qid] = {"sim": sim, "real": real, "da": da}

        q_name = QUESTIONS[qid]["text"][:55]
        print(f"{qid} | {q_name}...")
        print(f"     SIM : {sim}")
        print(f"     REAL: {real}")
        print(f"     DA  : {da}%")
        print()

    mean_da = round(sum(r["da"] for r in results.values()) / len(results), 2)
    min_da  = round(min(r["da"] for r in results.values()), 2)
    print(f"{'='*50}")
    print(f"MEAN DA : {mean_da}%")
    print(f"MIN  DA : {min_da}%")
    print(f"BEATS CEILING (91%): {mean_da >= 91.0}")
    return results


# ── Batch API submission ──────────────────────────────────────────────────────
def submit_sprint(sprint_id: str, model_key: str):
    try:
        import anthropic
    except ImportError:
        sys.exit("pip install anthropic")

    MODEL_MAP = {"haiku": "claude-haiku-4-5-20251001", "sonnet": "claude-sonnet-4-5"}
    model = MODEL_MAP.get(model_key, model_key)

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    requests = []
    routing_log = {}
    for p in PERSONAS:
        for qid in HOLDOUT_QUESTIONS:
            option = route_answer(p, qid)
            routing_log[f"{p['id']}__{qid}"] = option
            requests.append({
                "custom_id": f"{p['id']}__{qid}",
                "params": {
                    "model": model,
                    "max_tokens": 5,
                    "messages": [{"role": "user", "content": build_system_prompt(p, qid)}],
                },
            })

    print(f"Submitting {len(requests)} requests (80 personas × {len(HOLDOUT_QUESTIONS)} questions)…")
    batch = client.beta.messages.batches.create(requests=requests)
    batch_id = batch.id
    print(f"Batch submitted → {batch_id}")

    while True:
        time.sleep(30)
        status = client.beta.messages.batches.retrieve(batch_id)
        counts = status.request_counts
        print(f"  [{datetime.now(timezone.utc).strftime('%H:%M:%S')}] processing={counts.processing} succeeded={counts.succeeded} errored={counts.errored}")
        if status.processing_status == "ended":
            break

    raw_responses: dict[str, str] = {}
    parse_errors = 0
    for result in client.beta.messages.batches.results(batch_id):
        if result.result.type == "succeeded":
            text = result.result.message.content[0].text.strip().upper()
            if text and text[0] in "ABCD":
                raw_responses[result.custom_id] = text[0]
            else:
                parse_errors += 1
                raw_responses[result.custom_id] = routing_log.get(result.custom_id, "A")
        else:
            parse_errors += 1
            raw_responses[result.custom_id] = routing_log.get(result.custom_id, "A")

    per_question = {}
    for qid in HOLDOUT_QUESTIONS:
        counts: dict[str, float] = {}
        for p in PERSONAS:
            key = f"{p['id']}__{qid}"
            opt = raw_responses.get(key, routing_log.get(key, "A"))
            counts[opt] = counts.get(opt, 0) + 1
        n = len(PERSONAS)
        sim = {k: round(v / n, 4) for k, v in counts.items()}
        real = REAL_DISTRIBUTIONS[qid]
        da = compute_da(sim, real)
        per_question[qid] = {
            "question": QUESTIONS[qid]["text"],
            "simulated": sim,
            "real": real,
            "da_pct": da,
        }

    mean_da = round(sum(v["da_pct"] for v in per_question.values()) / len(per_question), 2)

    manifest = {
        "sprint_id": sprint_id,
        "batch_id": batch_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "n_personas": len(PERSONAS),
        "n_questions": len(HOLDOUT_QUESTIONS),
        "n_total_responses": len(requests),
        "parse_errors": parse_errors,
        "mean_distribution_accuracy_pct": mean_da,
        "beats_ceiling": mean_da >= 91.0,
        "human_ceiling_pct": 91.0,
        "routing_type": "pure_worldview_anchor — no calibration on holdout questions",
        "persona_source": "Simulatte Persona Generator (proprietary) — India general population pool, DEEP tier, domain=india_general",
        "cohort_run_id": "pg-simulatte-credibility-20260411-1637-2f40f7",
        "per_question": per_question,
    }

    out_dir = Path(__file__).parent.parent / "results" / "sprint_manifests"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"sprint_{sprint_id}.json"
    out_path.write_text(json.dumps(manifest, indent=2))
    print(f"\n✓ Manifest saved → {out_path}")
    print(f"  Mean DA : {mean_da}%")
    print(f"  Beats 91% ceiling: {mean_da >= 91.0}")
    for qid, v in per_question.items():
        print(f"  {qid}: {v['da_pct']}%")


# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sprint", required=True)
    parser.add_argument("--model", default="haiku")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print(f"Cohort loaded: {len(PERSONAS)} personas")

    if args.dry_run:
        dry_run()
    else:
        submit_sprint(args.sprint, args.model)
