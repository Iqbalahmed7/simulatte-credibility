#!/usr/bin/env python3
"""
holdout_runner.py — PEW USA v2 · Holdout validation runner.

Holdout questions (designated pre-calibration, zero topic anchors):
    q03 — gun_policy
    q07 — government role
    q09 — abortion
    q12 — democracy satisfaction
    q14 — AI/technology

Architecture:
    - Pure WorldviewAnchor system prompts (NO topic-specific OVA stances)
    - Same 40 personas + WORLDVIEW values as sprint_runner.py
    - 40 personas × 5 questions = 200 calls per run
    - Persona pool sourced from Simulatte Persona Generator (proprietary)

Usage:
    python3 holdout_runner.py --run HD-1 --model haiku
    python3 holdout_runner.py --run HD-1 --model haiku --dry-run
"""

import argparse
import json
import time
import sys
import os
from pathlib import Path
from datetime import datetime, timezone

# ── Load .env ─────────────────────────────────────────────────────────────────
_env_file = Path(__file__).resolve().parent.parent / ".env"        # pew_usa/.env
if not _env_file.exists():
    _env_file = Path(__file__).resolve().parent.parent.parent / ".env"
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

HERE       = Path(__file__).resolve().parent
STUDY_ROOT = HERE.parent
QUESTIONS  = STUDY_ROOT / "questions.json"
HOLDOUT_DIR = STUDY_ROOT / "results" / "holdout_manifests"
HOLDOUT_DIR.mkdir(parents=True, exist_ok=True)

MODELS = {
    "haiku":  "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-6",
}

# ── Persona pool (identical to sprint_runner.py) ───────────────────────────────
PERSONAS = [
    ("usa_p01", "Patricia Williams",  43, "female", "South (Georgia)",       "Atlanta",       "lean_conservative", "high-school",   "middle",        2.5),
    ("usa_p02", "Sandra Johnson",     58, "female", "South (Texas)",         "Houston",       "conservative",      "high-school",   "middle",        2.5),
    ("usa_p03", "Maria Garcia",       35, "female", "South (Florida)",       "Miami",         "lean_progressive",  "high-school",   "lower-middle",  2.5),
    ("usa_p04", "Linda Brown",        67, "female", "South (N. Carolina)",   "Charlotte",     "moderate",          "undergraduate", "middle",        2.5),
    ("usa_p05", "Betty Jackson",      63, "female", "South (Alabama)",       "Birmingham",    "conservative",      "high-school",   "lower-middle",  2.5),
    ("usa_p06", "Nancy Moore",        54, "female", "Midwest (Iowa)",        "Des Moines",    "conservative",      "high-school",   "middle",        2.5),
    ("usa_p07", "James Miller",       48, "male",   "Midwest (Ohio)",        "Columbus",      "moderate",          "undergraduate", "middle",        2.5),
    ("usa_p08", "Robert Davis",       61, "male",   "Midwest (Michigan)",    "Detroit",       "lean_conservative", "high-school",   "lower-middle",  2.5),
    ("usa_p09", "William Wilson",     38, "male",   "Midwest (Illinois)",    "Chicago",       "moderate",          "undergraduate", "upper-middle",  2.5),
    ("usa_p10", "Thomas Anderson",    55, "male",   "Midwest (Minnesota)",   "Minneapolis",   "moderate",          "postgraduate",  "upper-middle",  2.5),
    ("usa_p11", "Jennifer Taylor",    32, "female", "Northeast (New York)",  "New York",      "progressive",       "postgraduate",  "upper-middle",  2.5),
    ("usa_p12", "Barbara Martinez",   44, "female", "Northeast (Penn.)",     "Philadelphia",  "lean_progressive",  "undergraduate", "middle",        2.5),
    ("usa_p13", "Susan Thompson",     29, "female", "Northeast (Mass.)",     "Boston",        "progressive",       "postgraduate",  "middle",        2.5),
    ("usa_p14", "Dorothy White",      71, "female", "Northeast (Conn.)",     "Hartford",      "moderate",          "undergraduate", "middle",        2.5),
    ("usa_p15", "Charles Harris",     36, "male",   "West (California)",     "Los Angeles",   "lean_conservative", "high-school",   "middle",        2.5),
    ("usa_p16", "Joseph Jackson",     52, "male",   "West (Washington)",     "Seattle",       "lean_progressive",  "undergraduate", "upper-middle",  2.5),
    ("usa_p17", "Christopher Martin", 28, "male",   "West (Arizona)",        "Phoenix",       "lean_conservative", "high-school",   "lower-middle",  2.5),
    ("usa_p18", "Daniel Thompson",    45, "male",   "West (Colorado)",       "Denver",        "lean_progressive",  "postgraduate",  "upper-middle",  2.5),
    ("usa_p19", "Mark Taylor",        42, "male",   "South (Tennessee)",     "Nashville",     "conservative",      "high-school",   "middle",        2.5),
    ("usa_p20", "Paul Rodriguez",     31, "male",   "South (Nevada)",        "Las Vegas",     "lean_conservative", "high-school",   "lower-middle",  2.5),
    ("usa_p21", "Helen Lewis",        74, "female", "South (Florida)",       "Orlando",       "lean_conservative", "high-school",   "middle",        2.5),
    ("usa_p22", "Frank Lee",          69, "male",   "West (Arizona)",        "Phoenix",       "conservative",      "undergraduate", "upper-middle",  2.5),
    ("usa_p23", "Michelle Walker",    24, "female", "South (Texas)",         "Austin",        "moderate",          "high-school",   "lower-middle",  2.5),
    ("usa_p24", "Kevin Hall",         22, "male",   "West (California)",     "San Diego",     "lean_progressive",  "high-school",   "lower-middle",  2.5),
    ("usa_p25", "Amanda Allen",       27, "female", "Northeast (New York)",  "Brooklyn",      "progressive",       "undergraduate", "middle",        2.5),
    ("usa_p26", "Ryan Young",         26, "male",   "West (Washington)",     "Seattle",       "progressive",       "postgraduate",  "middle",        2.5),
    ("usa_p27", "Denise Robinson",    40, "female", "South (Georgia)",       "Atlanta",       "lean_progressive",  "undergraduate", "middle",        2.5),
    ("usa_p28", "Marcus Johnson",     33, "male",   "Midwest (Illinois)",    "Chicago",       "lean_progressive",  "undergraduate", "middle",        2.5),
    ("usa_p29", "Keisha Brown",       28, "female", "South (Texas)",         "Dallas",        "lean_progressive",  "high-school",   "lower-middle",  2.5),
    ("usa_p30", "Darnell Williams",   55, "male",   "Northeast (Maryland)",  "Baltimore",     "progressive",       "undergraduate", "upper-middle",  2.5),
    ("usa_p31", "Carmen Lopez",       38, "female", "West (California)",     "Los Angeles",   "lean_progressive",  "high-school",   "lower-middle",  2.5),
    ("usa_p32", "Miguel Hernandez",   29, "male",   "South (Texas)",         "San Antonio",   "moderate",          "high-school",   "lower-middle",  2.5),
    ("usa_p33", "Rosa Gonzalez",      52, "female", "South (Florida)",       "Miami",         "lean_conservative", "high-school",   "middle",        2.5),
    ("usa_p34", "Carlos Reyes",       44, "male",   "West (Arizona)",        "Tucson",        "moderate",          "high-school",   "middle",        2.5),
    ("usa_p35", "Andrew Mitchell",    49, "male",   "South (Virginia)",      "McLean",        "lean_conservative", "postgraduate",  "upper",         2.5),
    ("usa_p36", "Katherine Spencer",  41, "female", "Northeast (Conn.)",     "Greenwich",     "moderate",          "postgraduate",  "upper",         2.5),
    ("usa_p37", "David Nakamura",     38, "male",   "West (California)",     "San Francisco", "lean_progressive",  "postgraduate",  "upper",         2.5),
    ("usa_p38", "Elizabeth Hartley",  55, "female", "Midwest (Illinois)",    "Chicago",       "lean_progressive",  "postgraduate",  "upper",         2.5),
    ("usa_p39", "Richard Coleman",    62, "male",   "South (Texas)",         "Dallas",        "conservative",      "undergraduate", "upper",         2.5),
    ("usa_p40", "Laura Fitzgerald",   46, "female", "Northeast (Mass.)",     "Cambridge",     "progressive",       "postgraduate",  "upper",         2.5),
]

WORLDVIEW = {
    "usa_p01": (44, 60, 33, 70), "usa_p02": (35, 70, 18, 75), "usa_p03": (58, 40, 65, 60),
    "usa_p04": (50, 50, 50, 55), "usa_p05": (35, 70, 18, 80), "usa_p06": (35, 70, 18, 65),
    "usa_p07": (50, 50, 50, 50), "usa_p08": (44, 60, 33, 55), "usa_p09": (50, 50, 50, 35),
    "usa_p10": (50, 50, 50, 40), "usa_p11": (65, 32, 80, 20), "usa_p12": (58, 40, 65, 45),
    "usa_p13": (65, 32, 80, 15), "usa_p14": (50, 50, 50, 50), "usa_p15": (44, 60, 33, 45),
    "usa_p16": (58, 40, 65, 30), "usa_p17": (44, 60, 33, 40), "usa_p18": (58, 40, 65, 30),
    "usa_p19": (35, 70, 18, 75), "usa_p20": (44, 60, 33, 45), "usa_p21": (44, 60, 33, 60),
    "usa_p22": (35, 70, 18, 55), "usa_p23": (50, 50, 50, 45), "usa_p24": (58, 40, 65, 20),
    "usa_p25": (65, 32, 80, 18), "usa_p26": (65, 32, 80, 15), "usa_p27": (58, 40, 65, 75),
    "usa_p28": (58, 40, 65, 65), "usa_p29": (58, 40, 65, 70), "usa_p30": (65, 32, 80, 65),
    "usa_p31": (58, 40, 65, 65), "usa_p32": (50, 50, 50, 60), "usa_p33": (44, 60, 33, 70),
    "usa_p34": (50, 50, 50, 55), "usa_p35": (44, 60, 33, 45), "usa_p36": (50, 50, 50, 30),
    "usa_p37": (58, 40, 65, 15), "usa_p38": (58, 40, 65, 25), "usa_p39": (35, 70, 18, 55),
    "usa_p40": (65, 32, 80, 20),
}

# Holdout real distributions (Pew ATP 2022–2023, DK excluded)
HOLDOUT_REAL = {
    "q03": {"A": 0.592, "B": 0.265, "C": 0.143},
    # gun laws: More strict 59%, Kept as is 27%, Less strict 14%

    "q07": {"A": 0.531, "B": 0.469},
    # government: should do more (53%) vs too many things (47%) [normalized DK excl]

    "q09": {"A": 0.260, "B": 0.376, "C": 0.251, "D": 0.082},
    # abortion: Legal all / Legal most / Illegal most / Illegal all [DK excl renorm]

    "q12": {"A": 0.041, "B": 0.286, "C": 0.388, "D": 0.296},
    # democracy satisfaction: Very / Somewhat / Not too / Not at all [DK excl renorm]

    "q14": {"A": 0.422, "B": 0.400, "C": 0.167},
    # AI effects: Mostly positive / About equal / Mostly negative [DK excl renorm]
}


def build_holdout_system_prompt(persona: tuple) -> str:
    """Pure WorldviewAnchor prompt — zero topic-specific stances."""
    pid, name, age, gender, region, city, lean, edu, income, weight = persona
    it, ind, ct, mf = WORLDVIEW[pid]

    lean_desc = {
        "conservative":      "conservative Republican",
        "lean_conservative": "lean conservative / soft Republican",
        "moderate":          "moderate / independent",
        "lean_progressive":  "lean progressive / soft Democrat",
        "progressive":       "progressive Democrat",
    }.get(lean, lean)

    income_desc = {
        "upper":        "upper income",
        "upper-middle": "upper-middle income",
        "middle":       "middle income",
        "lower-middle": "lower-middle income",
    }.get(income, income)

    return f"""You are {name}, a {age}-year-old {gender} from {city}, {region}.

Demographic profile:
- Political lean: {lean_desc}
- Education: {edu}
- Financial situation: {income_desc}

Your worldview (internalized — do not quote these numbers):
- Institutional Trust: {it}/100 — {'low: you distrust government, media, and institutions' if it < 42 else 'moderate: selective trust in institutions' if it < 58 else 'high: generally trusting of institutions'}
- Change Tolerance: {ct}/100 — {'low: you prefer stability, tradition, and the status quo' if ct < 35 else 'moderate: open to some change, pragmatic' if ct < 60 else 'high: you welcome social, cultural, and political change'}
- Individualism: {ind}/100 — {'high: strong preference for individual responsibility, limited government, free markets' if ind >= 58 else 'moderate: pragmatic mix of individual and collective approaches' if ind >= 42 else 'low: strong preference for collective/government solutions'}
- Moral Foundationalism: {mf}/100 — {'high: traditional moral values and faith are very central to your worldview' if mf >= 60 else 'moderate: faith and tradition matter but are not overriding' if mf >= 35 else 'low: largely secular, post-traditional moral outlook'}

Instructions:
- You are answering a survey question as yourself — {name}.
- Answer based entirely on your own background, values, and worldview as described above.
- Select the single best answer option.
- Respond with ONLY the letter (A, B, C, or D) corresponding to your answer.
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
        all_questions = json.load(f)
    questions = [q for q in all_questions if q.get("holdout", False)]

    print(f"\n{'='*60}")
    print(f"Holdout Run: {run_id}  |  Model: {model}")
    print(f"Personas: {len(PERSONAS)}  |  Holdout questions: {len(questions)}")
    print(f"Total API calls: {len(PERSONAS) * len(questions)}")
    print(f"Architecture: PURE WorldviewAnchor — zero topic anchors")
    print(f"{'='*60}\n")

    if dry_run:
        print("[DRY RUN] Holdout questions:")
        for q in questions:
            print(f"  {q['id']} ({q['topic']}): {q['text'][:60]}...")
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
        total = counts.processing + counts.succeeded + counts.errored + counts.canceled + counts.expired
        done = counts.succeeded + counts.errored + counts.canceled + counts.expired
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
        answer = raw[0] if raw and raw[0] in "ABCD" else None
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
            "topic":     q["topic"],
            "sim":       sim,
            "real":      real,
            "da_pct":    round(da, 1),
            "parseable": sum(1 for p in PERSONAS if p[0] in results and qid in results[p[0]]),
        }

    da_scores = [v["da_pct"] for v in per_question.values()]
    mean_da = round(sum(da_scores) / len(da_scores), 1)

    print(f"\n{'='*60}")
    print(f"Holdout Run {run_id} Results")
    print(f"{'='*60}")
    print(f"Mean Holdout DA: {mean_da}%")
    print(f"\nPer-question breakdown:")
    for qid, v in sorted(per_question.items()):
        flag = " ← gap" if v["da_pct"] < 75 else ""
        print(f"  {qid} ({v['topic']:20s}): {v['da_pct']:5.1f}%  sim={v['sim']}{flag}")

    manifest = {
        "study_id":       "pew_usa_v2",
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
            "calibrated_da_pct":   95.3,
            "gap_pp":              round(95.3 - mean_da, 1),
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
    parser = argparse.ArgumentParser(description="PEW USA v2 holdout validation runner")
    parser.add_argument("--run",     required=True, help="Run ID (e.g. HD-1)")
    parser.add_argument("--model",   default="haiku", choices=["haiku", "sonnet"])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run_holdout(args.run, args.model, dry_run=args.dry_run)
