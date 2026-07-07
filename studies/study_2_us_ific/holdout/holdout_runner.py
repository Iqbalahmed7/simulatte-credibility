#!/usr/bin/env python3
"""
holdout_runner.py — IFIC Food & Health Survey 2025 · Holdout validation runner.

Holdout questions (designated pre-calibration, zero topic anchors):
    ific_h01 — MyPlate familiarity
    ific_h02 — Nutrition info at restaurants
    ific_h03 — RDN expertise trust
    ific_h04 — Interest in what TO eat
    ific_h05 — Social media food content

Architecture:
    - Pure WorldviewAnchor system prompts (NO topic-specific OVA stances)
    - Same 36 personas + WORLDVIEW values as sprint_runner.py
    - 36 personas × 5 questions = 180 calls per run

Usage:
    python3 holdout_runner.py --run IFIC-H1 --model haiku
    python3 holdout_runner.py --run IFIC-H1 --model haiku --dry-run
"""

import argparse
import json
import time
import sys
import os
from pathlib import Path
from datetime import datetime, timezone

# ── Load .env ─────────────────────────────────────────────────────────────────
_env_file = Path(__file__).resolve().parent.parent / ".env"
if not _env_file.exists():
    _env_file = Path(__file__).resolve().parent.parent.parent / ".env"
if not _env_file.exists():
    _env_file = Path(__file__).resolve().parent.parent.parent.parent / ".env"
if _env_file.exists():
    with open(_env_file) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ[_k.strip()] = _v.strip()

try:
    import anthropic
except ImportError:
    print("ERROR: anthropic package not found.")
    sys.exit(1)

HERE        = Path(__file__).resolve().parent
STUDY_ROOT  = HERE.parent
QUESTIONS   = STUDY_ROOT / "questions.json"
HOLDOUT_DIR = STUDY_ROOT / "results" / "holdout_manifests"
HOLDOUT_DIR.mkdir(parents=True, exist_ok=True)

MODELS = {
    "haiku":  "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-6",
}

# ── Persona pool (identical to sprint_runner.py — us_general v3) ──────────────
PERSONAS = [
    # (id, name, age, gender, region, city, lean, edu, income, weight)

    # ── Conservative (6) ─────────────────────────────────────────────────────
    ("usa_p01", "Nancy Moore",         54, "female", "Midwest (Iowa)",        "Des Moines",    "conservative",      "high-school",   "middle",        2.5),
    ("usa_p02", "Sandra Johnson",      58, "female", "South (Texas)",         "Houston",       "conservative",      "high-school",   "middle",        2.5),
    ("usa_p03", "Betty Jackson",       63, "female", "South (Alabama)",       "Birmingham",    "conservative",      "high-school",   "lower-middle",  2.5),
    ("usa_p04", "Mark Taylor",         42, "male",   "South (Tennessee)",     "Nashville",     "conservative",      "high-school",   "middle",        2.5),
    ("usa_p05", "Richard Coleman",     62, "male",   "South (Texas)",         "Dallas",        "conservative",      "postgraduate",  "upper",         2.5),
    ("usa_p06", "Frank Lee",           69, "male",   "West (Arizona)",        "Phoenix",       "conservative",      "postgraduate",  "upper-middle",  2.5),

    # ── Lean-Conservative (8) ─────────────────────────────────────────────────
    ("usa_p07", "Patricia Williams",   43, "female", "South (Georgia)",       "Atlanta",       "lean_conservative", "high-school",   "middle",        2.5),
    ("usa_p08", "Rosa Gonzalez",       52, "female", "South (Florida)",       "Miami",         "lean_conservative", "high-school",   "middle",        2.5),
    ("usa_p09", "Helen Lewis",         74, "female", "South (Florida)",       "Orlando",       "lean_conservative", "high-school",   "middle",        2.5),
    ("usa_p10", "Christopher Martin",  28, "male",   "West (Arizona)",        "Phoenix",       "lean_conservative", "high-school",   "lower-middle",  2.5),
    ("usa_p11", "Miguel Hernandez",    29, "male",   "South (Texas)",         "San Antonio",   "lean_conservative", "high-school",   "lower-middle",  2.5),
    ("usa_p12", "Paul Rodriguez",      31, "male",   "West (Nevada)",         "Las Vegas",     "lean_conservative", "high-school",   "lower-middle",  2.5),
    ("usa_p13", "Charles Harris",      36, "male",   "West (California)",     "Los Angeles",   "lean_conservative", "high-school",   "middle",        2.5),
    ("usa_p14", "Carlos Reyes",        44, "male",   "West (Arizona)",        "Tucson",        "lean_conservative", "high-school",   "middle",        2.5),

    # ── Moderate (8) ─────────────────────────────────────────────────────────
    ("usa_p15", "Michelle Walker",     24, "female", "South (Texas)",         "Austin",        "moderate",          "high-school",   "lower-middle",  2.8125),
    ("usa_p16", "Maria Garcia",        35, "female", "South (Florida)",       "Miami",         "moderate",          "high-school",   "lower-middle",  2.8125),
    ("usa_p17", "Katherine Spencer",   41, "female", "Northeast (Conn.)",     "Greenwich",     "moderate",          "postgraduate",  "upper",         2.8125),
    ("usa_p18", "Linda Brown",         67, "female", "South (N. Carolina)",   "Charlotte",     "moderate",          "postgraduate",  "middle",        2.8125),
    ("usa_p19", "Dorothy White",       71, "female", "Northeast (Conn.)",     "Hartford",      "moderate",          "postgraduate",  "middle",        2.8125),
    ("usa_p20", "Kevin Hall",          22, "male",   "West (California)",     "San Diego",     "moderate",          "high-school",   "lower-middle",  2.8125),
    ("usa_p21", "William Wilson",      38, "male",   "Midwest (Illinois)",    "Chicago",       "moderate",          "postgraduate",  "upper-middle",  2.8125),
    ("usa_p22", "Thomas Anderson",     55, "male",   "Midwest (Minnesota)",   "Minneapolis",   "moderate",          "postgraduate",  "upper-middle",  2.8125),

    # ── Lean-Progressive (8) ─────────────────────────────────────────────────
    ("usa_p23", "Keisha Brown",        28, "female", "South (Texas)",         "Dallas",        "lean_progressive",  "high-school",   "lower-middle",  3.4375),
    ("usa_p24", "Carmen Lopez",        38, "female", "West (California)",     "Los Angeles",   "lean_progressive",  "high-school",   "lower-middle",  3.4375),
    ("usa_p25", "Denise Robinson",     40, "female", "South (Georgia)",       "Atlanta",       "lean_progressive",  "postgraduate",  "middle",        3.4375),
    ("usa_p26", "Barbara Martinez",    44, "female", "Northeast (Penn.)",     "Philadelphia",  "lean_progressive",  "postgraduate",  "middle",        3.4375),
    ("usa_p27", "Marcus Johnson",      33, "male",   "Midwest (Illinois)",    "Chicago",       "lean_progressive",  "postgraduate",  "middle",        3.4375),
    ("usa_p28", "David Nakamura",      38, "male",   "West (California)",     "San Francisco", "lean_progressive",  "postgraduate",  "upper",         3.4375),
    ("usa_p29", "Daniel Thompson",     45, "male",   "West (Colorado)",       "Denver",        "lean_progressive",  "postgraduate",  "upper-middle",  3.4375),
    ("usa_p30", "Joseph Jackson",      52, "male",   "West (Washington)",     "Seattle",       "lean_progressive",  "postgraduate",  "upper-middle",  3.4375),

    # ── Progressive (6) ──────────────────────────────────────────────────────
    ("usa_p31", "Amanda Allen",        27, "female", "Northeast (New York)",  "Brooklyn",      "progressive",       "postgraduate",  "middle",        2.5),
    ("usa_p32", "Susan Thompson",      29, "female", "Northeast (Mass.)",     "Boston",        "progressive",       "postgraduate",  "middle",        2.5),
    ("usa_p33", "Jennifer Taylor",     32, "female", "Northeast (New York)",  "New York",      "progressive",       "postgraduate",  "upper-middle",  2.5),
    ("usa_p34", "Laura Fitzgerald",    46, "female", "Northeast (Mass.)",     "Cambridge",     "progressive",       "postgraduate",  "upper",         2.5),
    ("usa_p35", "Ryan Young",          26, "male",   "West (Washington)",     "Seattle",       "progressive",       "postgraduate",  "middle",        2.5),
    ("usa_p36", "Darnell Williams",    55, "male",   "South (Maryland)",      "Baltimore",     "progressive",       "postgraduate",  "upper-middle",  2.5),
]

WORLDVIEW = {
    # id:        (IT,  IND, CT,  MF)
    "usa_p01": (38,  67,  18,  65),
    "usa_p02": (36,  72,  15,  72),
    "usa_p03": (36,  70,  18,  83),
    "usa_p04": (37,  67,  18,  76),
    "usa_p05": (35,  69,  15,  54),
    "usa_p06": (34,  73,  19,  55),
    "usa_p07": (45,  59,  33,  73),
    "usa_p08": (47,  59,  30,  73),
    "usa_p09": (40,  60,  31,  60),
    "usa_p10": (41,  60,  36,  41),
    "usa_p11": (46,  57,  34,  62),
    "usa_p12": (47,  57,  32,  48),
    "usa_p13": (43,  59,  30,  46),
    "usa_p14": (42,  61,  31,  53),
    "usa_p15": (52,  47,  49,  43),
    "usa_p16": (53,  46,  48,  60),
    "usa_p17": (50,  50,  47,  28),
    "usa_p18": (49,  51,  51,  53),
    "usa_p19": (47,  52,  50,  51),
    "usa_p20": (52,  54,  53,  17),
    "usa_p21": (49,  46,  46,  35),
    "usa_p22": (48,  52,  53,  37),
    "usa_p23": (61,  38,  69,  72),
    "usa_p24": (58,  40,  68,  64),
    "usa_p25": (56,  38,  63,  75),
    "usa_p26": (56,  40,  61,  46),
    "usa_p27": (55,  38,  61,  67),
    "usa_p28": (61,  44,  66,  12),
    "usa_p29": (60,  41,  66,  29),
    "usa_p30": (60,  39,  64,  33),
    "usa_p31": (68,  33,  82,  17),
    "usa_p32": (66,  33,  82,  12),
    "usa_p33": (67,  29,  79,  21),
    "usa_p34": (62,  33,  77,  20),
    "usa_p35": (67,  35,  81,  13),
    "usa_p36": (69,  34,  80,  67),
}

# ── Holdout real distributions (IFIC 2025, n=3000) ───────────────────────────
HOLDOUT_REAL = {
    "ific_h01": {"A": 0.17, "B": 0.36, "C": 0.24, "D": 0.21, "E": 0.02},
    # MyPlate familiarity: Know a lot / Fair amount / Seen+little / Never seen / NS

    "ific_h02": {"A": 0.05, "B": 0.20, "C": 0.32, "D": 0.22, "E": 0.21},
    # Nutrition info at restaurants: Won't eat without / Regularly / Sometimes / Noticed not used / Not noticed

    "ific_h03": {"A": 0.18, "B": 0.44, "C": 0.30, "D": 0.06, "E": 0.02},
    # RDN expertise: Strongly agree / Somewhat / Neither / Somewhat dis / Strongly dis

    "ific_h04": {"A": 0.21, "B": 0.40, "C": 0.30, "D": 0.07, "E": 0.03},
    # What TO eat interest: Strongly agree / Somewhat / Neither / Somewhat dis / Strongly dis

    "ific_h05": {"A": 0.50, "B": 0.30, "C": 0.11, "D": 0.09},
    # Social media food content: Yes / No / Not sure / Don't use SM
}

# Calibrated sprint DA for reference (Sprint IFIC-1)
SPRINT_DA = 93.4


def build_holdout_system_prompt(persona: tuple) -> str:
    """Pure WorldviewAnchor prompt — zero topic-specific OVA stances."""
    pid, name, age, gender, region, city, lean, edu, income, weight = persona
    it, ind, ct, mf = WORLDVIEW[pid]

    lean_desc = {
        "conservative":      "conservative",
        "lean_conservative": "lean conservative",
        "moderate":          "moderate / independent",
        "lean_progressive":  "lean progressive",
        "progressive":       "progressive",
    }.get(lean, lean)

    income_desc = {
        "upper":        "upper income",
        "upper-middle": "upper-middle income",
        "middle":       "middle income",
        "lower-middle": "lower-middle income",
    }.get(income, income)

    health_engagement = (
        "very health-conscious — you actively follow nutrition news and read food labels"
        if ct >= 65 else
        "moderately health-conscious — you care about eating well but don't obsess over it"
        if ct >= 40 else
        "practical about food — you eat what you enjoy and what's convenient"
    )

    nutrition_trust = (
        "generally trusting of nutrition science, public health agencies, and dietitian advice"
        if it >= 58 else
        "somewhat skeptical — you take nutrition advice with a grain of salt"
        if it >= 42 else
        "quite skeptical of official nutrition guidelines and government food advice"
    )

    return f"""You are {name}, a {age}-year-old {gender} from {city}, {region}.

Demographic profile:
- Political lean: {lean_desc}
- Education: {edu}
- Financial situation: {income_desc}
- Region: {region}

Your food and health outlook (internalized — do not quote these numbers):
- Health engagement: {health_engagement}
- Nutrition trust: {nutrition_trust}
- Attitude toward change: {'you embrace new approaches to food and health' if ct >= 60 else 'you are practical and open to change' if ct >= 38 else 'you prefer familiar, traditional approaches to food'}
- Religious/traditional values: {'strong' if mf >= 60 else 'moderate' if mf >= 35 else 'largely secular'}

Instructions:
- You are answering a food and health survey question as yourself — {name}.
- Answer based entirely on your own background, values, and outlook as described above.
- Select the single best answer option.
- Respond with ONLY the letter (A, B, C, D, or E) corresponding to your answer.
- Do not explain or justify your answer."""


def build_user_message(question_data: dict) -> str:
    text = question_data["text"]
    options = question_data["options"]
    opts_str = "\n".join(f"{k}: {v}" for k, v in options.items())
    return f"{text}\n\n{opts_str}\n\nYour answer (letter only):"


def compute_da(simulated: dict, real: dict) -> float:
    keys = set(real.keys()) | set(simulated.keys())
    tvd = sum(abs(real.get(k, 0) - simulated.get(k, 0)) for k in keys) / 2
    return 1.0 - tvd


def run_holdout(run_id: str, model_key: str, dry_run: bool = False):
    client = anthropic.Anthropic()
    model = MODELS[model_key]

    with open(QUESTIONS) as f:
        survey = json.load(f)
    questions = survey["holdout_questions"]

    print(f"\n{'='*60}")
    print(f"Holdout Run: {run_id}  |  Model: {model}")
    print(f"Personas: {len(PERSONAS)}  |  Holdout questions: {len(questions)}")
    print(f"Total API calls: {len(PERSONAS) * len(questions)}")
    print(f"Architecture: PURE WorldviewAnchor — zero topic anchors")
    print(f"{'='*60}\n")

    if dry_run:
        print("[DRY RUN] Holdout questions:")
        for q in questions:
            print(f"  {q['id']}: {q['text'][:70]}...")
        print("\n[DRY RUN complete — no API calls made]")
        return

    requests = []
    for persona in PERSONAS:
        pid = persona[0]
        for q in questions:
            qid = q["id"]
            custom_id = f"{pid}__{qid}"
            sys_prompt = build_holdout_system_prompt(persona)
            user_msg = build_user_message(q)
            requests.append({
                "custom_id": custom_id,
                "params": {
                    "model": model,
                    "max_tokens": 10,
                    "system": sys_prompt,
                    "messages": [{"role": "user", "content": user_msg}],
                },
            })

    print(f"Submitting {len(requests)} requests to Batch API...")
    batch = client.beta.messages.batches.create(requests=requests)
    batch_id = batch.id
    print(f"Batch ID: {batch_id}")
    print(f"Status: {batch.processing_status}\n")

    while True:
        status = client.beta.messages.batches.retrieve(batch_id)
        counts = status.request_counts
        done = counts.succeeded + counts.errored + counts.canceled + counts.expired
        total = counts.processing + done
        print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {status.processing_status} — {done}/{total} done")
        if status.processing_status == "ended":
            break
        time.sleep(30)

    print("\nParsing results...")
    results = {}
    parse_errors = 0

    for result in client.beta.messages.batches.results(batch_id):
        if result.result.type != "succeeded":
            parse_errors += 1
            continue
        raw = result.result.message.content[0].text.strip().upper()
        answer = raw[0] if raw and raw[0] in "ABCDE" else None
        if not answer:
            parse_errors += 1
            continue
        pid, qid = result.custom_id.split("__")
        if pid not in results:
            results[pid] = {}
        results[pid][qid] = answer

    print(f"Parsed: {len(results)} personas | Parse errors: {parse_errors}")

    per_question = {}
    for q in questions:
        qid = q["id"]
        dist = {}
        total_weight = 0.0
        for persona in PERSONAS:
            pid = persona[0]
            weight = persona[9]
            ans = results.get(pid, {}).get(qid)
            if ans:
                dist[ans] = dist.get(ans, 0) + weight
                total_weight += weight
        sim = {k: round(v / total_weight, 4) for k, v in sorted(dist.items())} if total_weight > 0 else {}
        real = HOLDOUT_REAL.get(qid, {})
        da = compute_da(sim, real) * 100
        per_question[qid] = {
            "question": q["text"][:60],
            "sim":      sim,
            "real":     real,
            "da_pct":   round(da, 1),
            "parseable": sum(1 for p in PERSONAS if p[0] in results and qid in results[p[0]]),
        }

    da_scores = [v["da_pct"] for v in per_question.values()]
    mean_da = round(sum(da_scores) / len(da_scores), 1)
    gap = round(SPRINT_DA - mean_da, 1)

    print(f"\n{'='*60}")
    print(f"Holdout Run {run_id} Results")
    print(f"{'='*60}")
    print(f"Mean Holdout DA: {mean_da}%")
    print(f"Sprint DA (IFIC-1): {SPRINT_DA}%  |  Gap: {gap:+.1f}pp")
    print(f"\nPer-question breakdown:")
    for qid, v in sorted(per_question.items()):
        flag = " ←" if v["da_pct"] < 75 else ""
        print(f"  {qid}: {v['da_pct']:5.1f}%  sim={v['sim']}{flag}")

    manifest = {
        "study_id":       "ific_2025",
        "run_id":         run_id,
        "type":           "holdout_validation",
        "generated_at":   datetime.now(timezone.utc).isoformat(),
        "model":          model,
        "batch_id":       batch_id,
        "architecture":   "pure_worldview_anchor — zero topic anchors",
        "n_personas":     len(PERSONAS),
        "n_questions":    len(questions),
        "n_total_responses": len(PERSONAS) * len(questions),
        "result_summary": {
            "mean_holdout_da_pct": mean_da,
            "sprint_da_pct":       SPRINT_DA,
            "gap_pp":              gap,
        },
        "per_question":  per_question,
        "parse_errors":  parse_errors,
    }

    out_path = HOLDOUT_DIR / f"holdout_{run_id}.json"
    with open(out_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nManifest saved → {out_path}")
    print(f"{'='*60}\n")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IFIC Food & Health Survey 2025 — holdout validation runner")
    parser.add_argument("--run",     required=True, help="Run ID (e.g. IFIC-H1)")
    parser.add_argument("--model",   default="haiku", choices=["haiku", "sonnet"])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run_holdout(args.run, args.model, dry_run=args.dry_run)
