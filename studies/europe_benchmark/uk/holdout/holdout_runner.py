#!/usr/bin/env python3
"""
holdout_runner.py — Europe Benchmark · UK holdout validation runner.

Runs only the 5 holdout questions (hd01–hd05) with ZERO topic-specific anchors.
Pure WorldviewAnchor architecture — tests generalisation outside calibration set.

Usage:
    python3 holdout_runner.py --run HD-1
    python3 holdout_runner.py --run HD-1 --dry-run

Protocol: minimum 3 independent runs. Results stable within ±2pp SD = reliable.

Holdout questions (UK):
    hd01  us_view              — US favorability
    hd02  un_view              — UN favorability
    hd03  zelenskyy_confidence — Confidence in Zelenskyy
    hd04  macron_confidence    — Confidence in Macron
    hd05  biden_confidence     — Confidence in Biden

Ground truth: Pew Research Center Global Attitudes, Spring 2024 (UK N=1,017).
"""

import argparse
import json
import time
import sys
import os
import hashlib
from pathlib import Path
from datetime import datetime, timezone

_env_file = Path(__file__).resolve().parent.parent.parent.parent.parent / ".env"
if not _env_file.exists():
    _env_file = Path(__file__).resolve().parent.parent / ".env"
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
    print("ERROR: anthropic package not found. Run: pip install anthropic")
    sys.exit(1)

HERE       = Path(__file__).resolve().parent
STUDY_ROOT = HERE.parent
QUESTIONS  = STUDY_ROOT / "questions.json"
RESULTS    = HERE / "results"
RESULTS.mkdir(parents=True, exist_ok=True)

MODEL_ID = "claude-haiku-4-5-20251001"

# ── Persona pool (identical to sprint_runner.py) ───────────────────────────────
PERSONAS = [
    ("uk_p01", "Gary Stubbs",       58, "male",   "England (Midlands)",    "Reform",       "Leave",  "None/secular",  "GCSE/vocational",  2.5),
    ("uk_p02", "Tracey Mold",       54, "female", "England (North East)",  "Reform",       "Leave",  "None/secular",  "GCSE/vocational",  2.5),
    ("uk_p03", "Brian Tanner",      64, "male",   "England (East Anglia)", "Reform",       "Leave",  "Anglican",      "GCSE/vocational",  2.5),
    ("uk_p04", "Nigel Forsythe",    67, "male",   "England (South East)",  "Conservative", "Leave",  "Anglican",      "University",       2.5),
    ("uk_p05", "Margaret Holt",     62, "female", "England (South West)",  "Conservative", "Leave",  "Anglican",      "GCSE/vocational",  2.5),
    ("uk_p06", "James Rothwell",    48, "male",   "England (South East)",  "Conservative", "Remain", "Anglican",      "University",       2.0),
    ("uk_p07", "Claire Whitmore",   52, "female", "England (Midlands)",    "Conservative", "Leave",  "Anglican",      "University",       2.0),
    ("uk_p08", "Edward Cavendish",  44, "male",   "England (South East)",  "Conservative", "Remain", "None/secular",  "University",       2.0),
    ("uk_p09", "Patricia Garner",   71, "female", "England (South West)",  "Conservative", "Leave",  "Anglican",      "GCSE/vocational",  2.5),
    ("uk_p10", "Robert Ashworth",   56, "male",   "England (North West)",  "Conservative", "Leave",  "Anglican",      "GCSE/vocational",  2.5),
    ("uk_p11", "Diana Sutton",      39, "female", "England (South East)",  "Conservative", "Remain", "None/secular",  "University",       2.0),
    ("uk_p12", "Kevin Doherty",     49, "male",   "England (North West)",  "Labour",       "Leave",  "None/secular",  "GCSE/vocational",  2.5),
    ("uk_p13", "Sharon Brennan",    45, "female", "England (North East)",  "Labour",       "Leave",  "None/secular",  "GCSE/vocational",  2.5),
    ("uk_p14", "Marcus Webb",       37, "male",   "England (London)",      "Labour",       "Remain", "None/secular",  "University",       2.5),
    ("uk_p15", "Priya Sharma",      32, "female", "England (London)",      "Labour",       "Remain", "Hindu",         "University",       2.5),
    ("uk_p16", "Ian Baxter",        53, "male",   "Wales",                 "Labour",       "Leave",  "None/secular",  "GCSE/vocational",  2.5),
    ("uk_p17", "Angela Moss",       41, "female", "England (Midlands)",    "Labour",       "Remain", "None/secular",  "University",       2.0),
    ("uk_p18", "Mohammed Rahman",   38, "male",   "England (North West)",  "Labour",       "Remain", "Muslim",        "University",       2.5),
    ("uk_p19", "Diane Okafor",      44, "female", "England (London)",      "Labour",       "Remain", "Christian",     "University",       2.0),
    ("uk_p20", "Thomas Hughes",     55, "male",   "Wales",                 "Labour",       "Leave",  "None/secular",  "GCSE/vocational",  2.5),
    ("uk_p21", "Sarah Pemberton",   43, "female", "England (South West)",  "Lib Dem",      "Remain", "None/secular",  "University",       2.5),
    ("uk_p22", "Andrew Fairclough", 47, "male",   "England (South East)",  "Lib Dem",      "Remain", "Anglican",      "University",       2.5),
    ("uk_p23", "Fiona Crawford",    35, "female", "Scotland",              "Lib Dem",      "Remain", "None/secular",  "University",       2.0),
    ("uk_p24", "Oliver Kingsley",   29, "male",   "England (London)",      "Lib Dem",      "Remain", "None/secular",  "University",       2.0),
    ("uk_p25", "Alistair MacLeod",  51, "male",   "Scotland",              "SNP",          "Remain", "None/secular",  "University",       2.5),
    ("uk_p26", "Catriona Stewart",  46, "female", "Scotland",              "SNP",          "Remain", "None/secular",  "GCSE/vocational",  2.5),
    ("uk_p27", "Dave Norris",       60, "male",   "England (Midlands)",    "Non-partisan", "Leave",  "None/secular",  "GCSE/vocational",  2.5),
    ("uk_p28", "Carol Simmons",     57, "female", "England (North East)",  "Non-partisan", "Leave",  "Anglican",      "GCSE/vocational",  2.5),
    ("uk_p29", "Nathan Cole",       33, "male",   "England (London)",      "Non-partisan", "Remain", "None/secular",  "University",       2.0),
    ("uk_p30", "Wendy Allison",     49, "female", "England (Midlands)",    "Non-partisan", "Leave",  "None/secular",  "GCSE/vocational",  2.5),
    ("uk_p31", "Reginald Firth",    68, "male",   "England (North)",       "Non-partisan", "Leave",  "Anglican",      "GCSE/vocational",  2.5),
    ("uk_p32", "Leila Hassan",      31, "female", "England (London)",      "Non-partisan", "Remain", "Muslim",        "University",       2.5),
    ("uk_p33", "George Findlay",    42, "male",   "Scotland",              "Non-partisan", "Remain", "None/secular",  "University",       2.0),
    ("uk_p34", "Joyce Williams",    63, "female", "Wales",                 "Non-partisan", "Leave",  "Anglican",      "GCSE/vocational",  2.5),
    ("uk_p35", "Zara Ahmed",        26, "female", "England (London)",      "Labour",       "Remain", "Muslim",        "University",       2.5),
    ("uk_p36", "Callum Reid",       28, "male",   "Scotland",              "SNP",          "Remain", "None/secular",  "University",       2.0),
    ("uk_p37", "Sandra Price",      72, "female", "England (South West)",  "Conservative", "Leave",  "Anglican",      "GCSE/vocational",  2.5),
    ("uk_p38", "Joseph Murphy",     50, "male",   "England (North West)",  "Labour",       "Remain", "Catholic",      "GCSE/vocational",  2.5),
    ("uk_p39", "Hannah Boateng",    36, "female", "England (Midlands)",    "Labour",       "Remain", "Christian",     "University",       2.0),
    ("uk_p40", "Derek Parkinson",   61, "male",   "England (Midlands)",    "Reform",       "Leave",  "None/secular",  "GCSE/vocational",  2.5),
]

WORLDVIEW = {
    "uk_p01": (28,  52,  15,  22),
    "uk_p02": (25,  48,  12,  20),
    "uk_p03": (30,  55,  14,  35),
    "uk_p04": (52,  72,  28,  52),
    "uk_p05": (45,  58,  20,  55),
    "uk_p06": (62,  70,  50,  40),
    "uk_p07": (48,  62,  32,  45),
    "uk_p08": (60,  75,  52,  22),
    "uk_p09": (42,  55,  18,  58),
    "uk_p10": (40,  58,  22,  42),
    "uk_p11": (65,  68,  58,  25),
    "uk_p12": (38,  38,  40,  28),
    "uk_p13": (35,  35,  38,  25),
    "uk_p14": (62,  50,  72,  15),
    "uk_p15": (65,  52,  75,  32),
    "uk_p16": (40,  40,  42,  30),
    "uk_p17": (60,  48,  68,  18),
    "uk_p18": (55,  45,  62,  65),
    "uk_p19": (62,  50,  70,  45),
    "uk_p20": (38,  38,  40,  28),
    "uk_p21": (68,  62,  78,  20),
    "uk_p22": (65,  65,  72,  35),
    "uk_p23": (64,  60,  75,  18),
    "uk_p24": (70,  58,  82,  12),
    "uk_p25": (58,  48,  70,  22),
    "uk_p26": (55,  42,  65,  28),
    "uk_p27": (30,  50,  18,  25),
    "uk_p28": (32,  48,  20,  42),
    "uk_p29": (58,  55,  70,  15),
    "uk_p30": (28,  45,  22,  28),
    "uk_p31": (25,  48,  14,  40),
    "uk_p32": (60,  50,  68,  68),
    "uk_p33": (60,  55,  72,  18),
    "uk_p34": (35,  42,  22,  45),
    "uk_p35": (62,  48,  78,  62),
    "uk_p36": (62,  52,  80,  15),
    "uk_p37": (40,  58,  16,  60),
    "uk_p38": (45,  40,  48,  55),
    "uk_p39": (63,  50,  72,  38),
    "uk_p40": (26,  52,  12,  20),
}


def build_system_prompt(persona: tuple) -> str:
    """Pure WorldviewAnchor prompt — zero topic-specific anchors."""
    pid, name, age, gender, region, party, brexit, religion, education, weight = persona
    it, ind, ct, mf = WORLDVIEW[pid]

    is_scotland = "Scotland" in region
    is_wales    = "Wales" in region
    is_leave    = brexit == "Leave"
    is_remain   = brexit == "Remain"
    is_muslim   = religion == "Muslim"

    if it < 35:
        it_desc = (
            "You have very low trust in UK institutions — Parliament, the courts, "
            "mainstream media. You feel Westminster is broken and out of touch with "
            "ordinary people like you."
        )
    elif it < 52:
        it_desc = (
            "You have mixed trust in UK institutions. You see real dysfunction and "
            "disillusionment with the political class, but acknowledge some things still work."
        )
    elif it < 65:
        it_desc = (
            "You have moderate trust in UK institutions. You're realistic about their "
            "flaws but broadly believe in parliamentary democracy."
        )
    else:
        it_desc = (
            "You have high trust in UK institutions. Rule of law, parliamentary process, "
            "and democratic norms matter deeply to you."
        )

    if is_leave:
        brexit_layer = (
            "\nBrexit: You voted Leave in 2016. For you this was about sovereignty, "
            "democratic control, and immigration — not just economics."
        )
    else:
        brexit_layer = (
            "\nBrexit: You voted Remain in 2016. You thought leaving the EU was a mistake "
            "and remain broadly positive toward European and international institutions."
        )

    scotland_layer = ""
    if is_scotland:
        if party == "SNP":
            scotland_layer = (
                "\nScottish identity: You are Scottish first, British second — or not British "
                "at all. You support independence and resent Westminster's Brexit imposition."
            )
        else:
            scotland_layer = (
                "\nScottish background: You live in Scotland and have a distinct civic "
                "identity, even if you don't support independence."
            )

    wales_layer = ""
    if is_wales:
        wales_layer = (
            "\nWelsh background: You live in Wales. Many Welsh communities felt left behind "
            "by Westminster long before Brexit — deindustrialisation, public service cuts."
        )

    minority_layer = ""
    if is_muslim:
        minority_layer = (
            "\nMuslim-British identity: Your faith is central to your identity. "
            "You care deeply about UK foreign policy in Muslim-majority countries."
        )
    elif religion == "Hindu":
        minority_layer = "\nHindu-British identity: Your family has South Asian roots."
    elif religion == "Christian" and ("Okafor" in name or "Boateng" in name):
        minority_layer = (
            "\nBlack British identity: Your family has African or Caribbean roots. "
            "You identify as British and Christian."
        )

    ova_map = {
        "Reform":       "Britain has been failed by the political establishment — immigration is out of control, public services have collapsed, and ordinary working people are ignored by an out-of-touch liberal elite. You want a radical break from the consensus.",
        "Conservative": "stability, low taxes, strong defence, and law and order are the bedrock of a well-run country. You believe in individual responsibility, earned rewards, and traditional British values.",
        "Labour":       "working people deserve a fair share of what they create. Underfunded public services, rising inequality, and corporate excess have damaged Britain. The state must actively ensure opportunity for all.",
        "Lib Dem":      "individual liberty, civil rights, and a strong role in Europe define your politics. You are pro-Remain at heart and believe in multilateral cooperation, reform of democracy, and socially liberal values.",
        "SNP":          "Scotland's interests are best served by independence. Westminster doesn't speak for Scotland. You are pro-EU, pro-public services, and believe in a progressive, outward-looking Scottish identity.",
        "Non-partisan": "no single party represents your views. You're cynical about politicians and vote based on immediate issues or not at all.",
    }
    ova = ova_map.get(party, "")

    prompt = f"""You are {name}, a {age}-year-old {gender} from {region}, United Kingdom.

Education: {education}. Religion: {religion}. Brexit vote: {brexit}.

Political identity: You support or lean toward {party}. {ova}.

Your worldview:
- Institutional trust ({it}/100): {it_desc}
- Economic philosophy ({ind}/100): {"You prefer market and individual solutions over state intervention — lower taxes, less regulation, personal responsibility." if ind > 65 else "You believe the state should play a significant role in the economy — public investment, redistribution, strong public services." if ind < 42 else "You hold mixed views on state vs. market solutions."}
- Change tolerance ({ct}/100): {"You welcome fundamental change and see the status quo as deeply inadequate." if ct > 70 else "You are deeply skeptical of rapid change and value stability, tradition, and continuity." if ct < 28 else "You accept gradual, carefully managed change."}
- Moral foundationalism ({mf}/100): {"Your values are grounded in traditional religious or cultural norms on social questions." if mf > 58 else "You hold secular, liberal views on social and moral questions." if mf < 25 else "You hold mixed views — traditional on some questions, liberal on others."}{brexit_layer}{scotland_layer}{wales_layer}{minority_layer}

Important: Use the full response scale. When your views are strong, pick the strongest option that genuinely fits — do not soften your answer toward the middle.

Answer every survey question as {name} would genuinely answer. Respond with the letter only (A, B, or C for 3-option questions; A, B, C, or D for 4-option questions). Nothing else."""

    return prompt


def build_question_messages(question: dict) -> list[dict]:
    opts = question["options"]
    options_text = "\n".join(f"{k}. {v}" for k, v in opts.items())
    return [
        {
            "role": "user",
            "content": f"{question['text']}\n\n{options_text}\n\nAnswer with the letter only."
        }
    ]


def extract_answer(text: str, valid_options: list[str]) -> str:
    text = text.strip().upper()
    for opt in valid_options:
        if text.startswith(opt):
            return opt
    for char in text:
        if char in valid_options:
            return char
    return "X"


def compute_distributions(results: list[dict]) -> dict:
    counts: dict[str, dict[str, float]] = {}
    total_weight: dict[str, float] = {}
    persona_weight = {p[0]: p[9] for p in PERSONAS}

    for r in results:
        tokens = r["custom_id"].split("_")
        qid = tokens[-1]
        pid = "_".join(tokens[-3:-1])
        answer = r.get("answer", "X")
        weight = persona_weight.get(pid, 2.5)

        if qid not in counts:
            counts[qid] = {}
            total_weight[qid] = 0.0
        counts[qid][answer] = counts[qid].get(answer, 0.0) + weight
        total_weight[qid] += weight

    distributions: dict[str, dict[str, float]] = {}
    for qid, c in counts.items():
        total = total_weight[qid]
        distributions[qid] = {opt: round(cnt / total, 4) for opt, cnt in c.items()}
    return distributions


def score_distributions(sim: dict, questions: list[dict]) -> dict[str, float]:
    scores = {}
    for q in questions:
        qid = q["id"]
        real = q["pew_distribution"]
        predicted = sim.get(qid, {})
        all_opts = set(real.keys()) | set(predicted.keys())
        total_abs_diff = sum(abs(real.get(o, 0.0) - predicted.get(o, 0.0)) for o in all_opts)
        scores[qid] = round(1.0 - total_abs_diff / 2.0, 4)
    scores["overall"] = round(sum(v for k, v in scores.items() if k != "overall") / len(questions), 4)
    return scores


def run_holdout(run_id: str, dry_run: bool = False) -> None:
    with open(QUESTIONS, encoding="utf-8") as f:
        all_questions = json.load(f)
    holdout_questions = [q for q in all_questions if q.get("holdout")]

    print(f"\nEurope Benchmark — UK — Holdout {run_id}")
    print(f"Model:  {MODEL_ID}")
    print(f"Batch:  Yes (50% discount)")
    print(f"Personas × Questions: {len(PERSONAS)} × {len(holdout_questions)} = {len(PERSONAS) * len(holdout_questions)} calls")
    print(f"Mode:   ZERO topic anchors — pure WorldviewAnchor")
    print("=" * 60)

    requests = []
    for persona in PERSONAS:
        pid = persona[0]
        system_prompt = build_system_prompt(persona)
        for q in holdout_questions:
            custom_id = f"{run_id}_{pid}_{q['id']}"
            requests.append({
                "custom_id": custom_id,
                "params": {
                    "model": MODEL_ID,
                    "max_tokens": 5,
                    "system": system_prompt,
                    "messages": build_question_messages(q),
                }
            })

    if dry_run:
        print(f"DRY RUN: {len(requests)} requests would be submitted.")
        print(f"Sample request ID: {requests[0]['custom_id']}")
        print(f"Sample system prompt (first 300 chars):\n{requests[0]['params']['system'][:300]}...")
        return

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    print(f"Submitting {len(requests)} requests to Batch API…")
    batch = client.messages.batches.create(requests=requests)
    batch_id = batch.id
    print(f"Batch ID: {batch_id}")

    while True:
        status = client.messages.batches.retrieve(batch_id)
        c = status.request_counts
        print(f"  Status: processing={c.processing}, succeeded={c.succeeded}, errored={c.errored}")
        if status.processing_status == "ended":
            break
        time.sleep(30)

    print("Batch complete. Retrieving results…")

    raw_results = []
    for result in client.messages.batches.results(batch_id):
        answer = "X"
        if result.result.type == "succeeded":
            content = result.result.message.content
            if content:
                text = content[0].text if hasattr(content[0], "text") else ""
                qid = result.custom_id.split("_")[-1]
                q_obj = next((q for q in holdout_questions if q["id"] == qid), None)
                valid_opts = list(q_obj["options"].keys()) if q_obj else ["A", "B", "C", "D"]
                answer = extract_answer(text, valid_opts)
        raw_results.append({
            "custom_id": result.custom_id,
            "answer": answer,
            "raw": result.result.message.content[0].text if result.result.type == "succeeded" else "ERROR",
        })

    sim_distributions = compute_distributions(raw_results)
    scores = score_distributions(sim_distributions, holdout_questions)

    manifest = {
        "run_id": run_id,
        "model": MODEL_ID,
        "batch_id": batch_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": "holdout — zero topic anchors",
        "n_personas": len(PERSONAS),
        "n_questions": len(holdout_questions),
        "n_calls": len(requests),
        "scores": scores,
        "sim_distributions": sim_distributions,
        "ground_truth": {q["id"]: q["pew_distribution"] for q in holdout_questions},
    }

    raw_jsonl = "\n".join(json.dumps(r, sort_keys=True) for r in raw_results)
    manifest["raw_hash"] = "sha256:" + hashlib.sha256(raw_jsonl.encode()).hexdigest()

    manifest_path = RESULTS / f"holdout_{run_id}.json"
    raw_path      = RESULTS / f"holdout_{run_id}_raw.jsonl"

    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    with open(raw_path, "w") as f:
        f.write(raw_jsonl)

    print(f"\nResults saved:")
    print(f"  {manifest_path}")
    print(f"  {raw_path}")
    print(f"\nHoldout Distribution Accuracy: {scores['overall']*100:.1f}%")
    print("\nPer-question scores:")
    for q in holdout_questions:
        qid = q["id"]
        print(f"  {qid} ({q['topic']:40s}): {scores.get(qid, 0)*100:.1f}%")


def main():
    parser = argparse.ArgumentParser(description="Europe Benchmark UK holdout runner")
    parser.add_argument("--run", required=True, help="Run ID, e.g. HD-1")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run_holdout(args.run, args.dry_run)


if __name__ == "__main__":
    main()
