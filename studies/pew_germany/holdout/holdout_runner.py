#!/usr/bin/env python3
"""
holdout_runner.py — Study 1C Germany Holdout Validation

PURPOSE
-------
Validates whether Simulatte's WorldviewAnchor architecture generalises to
survey questions that were NEVER used in calibration.

The C-8 calibration sprint achieved 91.3% DA, but that was measured on the
same 15 questions used to tune the topic anchors. This is an in-sample result.

This runner uses the IDENTICAL 40 personas and WorldviewAnchor values from C-8,
but with ZERO topic-specific anchors. The persona prompt contains only:
  - Demographics (age, gender, region, religion, education, migration)
  - Party alignment + option-vocabulary description
  - WorldviewAnchor scores (IT, IND, CT, MF) and their plain-language descriptions
  - East Germany and migration background layers

No hints about what answer to give. One run. No iteration.

Usage:
    python3 holdout_runner.py

Output:
    holdout/results/holdout_results.json
    holdout/results/holdout_results_raw.jsonl
"""

import json
import time
import sys
import os
from pathlib import Path
from datetime import datetime, timezone

# Load .env from study root
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
HOLDOUT_Q  = HERE / "holdout_questions.json"
RESULTS    = HERE / "results"
RESULTS.mkdir(parents=True, exist_ok=True)

MODEL = "claude-haiku-4-5-20251001"

# ── Persona pool (identical to C-8 sprint_runner.py) ─────────────────────────
PERSONAS = [
    ("de_p01", "Klaus Richter",     62, "male",   "East (Saxony)",         "AfD",          "None/atheist", "Vocational",  "None",    2.5),
    ("de_p02", "Monika Schreiber",  58, "female", "East (Thuringia)",      "AfD",          "None/atheist", "Vocational",  "None",    2.5),
    ("de_p03", "Rainer Vogel",      47, "male",   "West (NRW)",            "AfD",          "Protestant",   "Vocational",  "None",    2.5),
    ("de_p04", "Sabine Krause",     44, "female", "West (Baden-Wuertt.)",  "AfD",          "Catholic",     "Vocational",  "None",    2.0),
    ("de_p05", "Dieter Meinhardt",  39, "male",   "East (Brandenburg)",    "AfD",          "None/atheist", "Hauptschule", "None",    2.5),
    ("de_p06", "Jürgen Pfeiffer",   55, "male",   "East (Saxony-Anhalt)",  "AfD",          "None/atheist", "Hauptschule", "None",    2.5),
    ("de_p07", "Anja Fleischer",    50, "female", "West (Saarland)",       "AfD",          "Catholic",     "Hauptschule", "None",    2.0),
    ("de_p08", "Friedrich Bauer",   67, "male",   "Bavaria",               "CDU/CSU",      "Catholic",     "Vocational",  "None",    2.5),
    ("de_p09", "Maria Huber",       54, "female", "Bavaria",               "CDU/CSU",      "Catholic",     "Vocational",  "None",    2.5),
    ("de_p10", "Thomas Weiß",       42, "male",   "Bavaria",               "CDU/CSU",      "Catholic",     "University",  "None",    2.0),
    ("de_p11", "Ursula Kamm",       59, "female", "Bavaria",               "CDU/CSU",      "Catholic",     "University",  "None",    2.0),
    ("de_p12", "Hans-Georg Möller", 63, "male",   "West (NRW)",            "CDU/CSU",      "Protestant",   "Vocational",  "None",    2.5),
    ("de_p13", "Hildegard Sommer",  55, "female", "West (Rhineland-Pf.)",  "CDU/CSU",      "Catholic",     "Vocational",  "None",    2.5),
    ("de_p14", "Bernd Hartmann",    48, "male",   "West (Hesse)",          "CDU/CSU",      "Protestant",   "University",  "None",    2.0),
    ("de_p15", "Christine Lorenz",  38, "female", "West (Baden-Wuertt.)",  "CDU/CSU",      "Secular",      "University",  "None",    2.0),
    ("de_p16", "Wolfgang Sauer",    52, "male",   "East (Saxony)",         "CDU/CSU",      "None/atheist", "Vocational",  "None",    2.5),
    ("de_p17", "Renate Franke",     61, "female", "East (Thuringia)",      "CDU/CSU",      "None/atheist", "Vocational",  "None",    2.5),
    ("de_p18", "Stefan Brandt",     45, "male",   "North (Hamburg)",       "CDU/CSU",      "Protestant",   "University",  "None",    2.0),
    ("de_p19", "Petra Schneider",   52, "female", "West (NRW)",            "SPD",          "Protestant",   "Vocational",  "None",    2.5),
    ("de_p20", "Helmut Fuchs",      58, "male",   "West (NRW)",            "SPD",          "Protestant",   "Vocational",  "None",    2.5),
    ("de_p21", "Gabi Kramer",       44, "female", "East (Saxony)",         "SPD",          "None/atheist", "University",  "None",    2.5),
    ("de_p22", "Manfred Stein",     49, "male",   "East (Brandenburg)",    "SPD",          "None/atheist", "Vocational",  "None",    2.5),
    ("de_p23", "Karin Hoffmann",    36, "female", "North (Hamburg)",       "SPD",          "Secular",      "University",  "Other",   2.0),
    ("de_p24", "Oliver Meier",      41, "male",   "Berlin",                "SPD",          "Secular",      "University",  "None",    2.0),
    ("de_p25", "Julia Zimmermann",  31, "female", "West (Baden-Wuertt.)",  "Greens",       "Secular",      "University",  "None",    2.5),
    ("de_p26", "Markus Braun",      35, "male",   "West (NRW)",            "Greens",       "Secular",      "University",  "None",    2.5),
    ("de_p27", "Sophie Lange",      27, "female", "Berlin",                "Greens",       "Secular",      "University",  "Other",   2.5),
    ("de_p28", "Florian Roth",      43, "male",   "Bavaria",               "Greens",       "Secular",      "University",  "None",    2.0),
    ("de_p29", "Alexander König",   38, "male",   "West (Hesse)",          "FDP",          "Secular",      "University",  "None",    2.5),
    ("de_p30", "Katrin Schulz",     44, "female", "Bavaria",               "FDP",          "Secular",      "University",  "None",    2.5),
    ("de_p31", "Elke Günther",      56, "female", "East (Saxony)",         "BSW",          "None/atheist", "Vocational",  "None",    2.5),
    ("de_p32", "Frank Müller",      52, "male",   "East (Brandenburg)",    "BSW",          "None/atheist", "Vocational",  "None",    2.5),
    ("de_p33", "Rosa Bergmann",     48, "female", "West (NRW)",            "Left",         "Secular",      "University",  "None",    2.5),
    ("de_p34", "Lars Weber",        26, "male",   "Berlin",                "Non-partisan", "Secular",      "University",  "None",    2.5),
    ("de_p35", "Michaela Köhler",   34, "female", "West (Hesse)",          "Non-partisan", "Secular",      "Vocational",  "None",    2.0),
    ("de_p36", "Gerhard Neumann",   64, "male",   "East (Saxony)",         "Non-partisan", "None/atheist", "Hauptschule", "None",    2.5),
    ("de_p37", "Ilse Böhm",         70, "female", "West (NRW)",            "Non-partisan", "Catholic",     "Hauptschule", "None",    2.5),
    ("de_p38", "Mehmet Yilmaz",     42, "male",   "West (NRW)",            "Non-partisan", "Muslim",       "Vocational",  "Turkish", 2.5),
    ("de_p39", "Fatma Demir",       38, "female", "Berlin",                "Non-partisan", "Muslim",       "Vocational",  "Turkish", 2.5),
    ("de_p40", "Anna Kowalski",     29, "female", "Berlin",                "Non-partisan", "Secular",      "University",  "Other",   2.0),
]

WORLDVIEW = {
    "de_p01": (22, 40, 15, 28), "de_p02": (24, 38, 18, 32),
    "de_p03": (38, 50, 20, 45), "de_p04": (35, 48, 22, 50),
    "de_p05": (20, 35, 12, 25), "de_p06": (18, 32, 10, 22),
    "de_p07": (33, 44, 16, 52), "de_p08": (58, 62, 30, 72),
    "de_p09": (62, 58, 32, 75), "de_p10": (65, 70, 38, 65),
    "de_p11": (60, 65, 35, 70), "de_p12": (56, 58, 32, 55),
    "de_p13": (59, 55, 30, 65), "de_p14": (63, 72, 42, 50),
    "de_p15": (61, 68, 48, 40), "de_p16": (40, 52, 30, 30),
    "de_p17": (38, 48, 28, 28), "de_p18": (62, 68, 45, 45),
    "de_p19": (54, 45, 55, 40), "de_p20": (52, 42, 52, 38),
    "de_p21": (42, 40, 58, 22), "de_p22": (38, 38, 50, 20),
    "de_p23": (58, 52, 65, 28), "de_p24": (56, 55, 65, 25),
    "de_p25": (68, 60, 82, 15), "de_p26": (65, 58, 80, 12),
    "de_p27": (70, 62, 88, 10), "de_p28": (64, 60, 78, 14),
    "de_p29": (60, 88, 55, 20), "de_p30": (62, 85, 52, 22),
    "de_p31": (30, 28, 35, 30), "de_p32": (28, 30, 32, 28),
    "de_p33": (45, 22, 72, 18), "de_p34": (52, 62, 68, 12),
    "de_p35": (50, 55, 55, 25), "de_p36": (28, 35, 22, 22),
    "de_p37": (55, 40, 28, 68), "de_p38": (48, 55, 45, 62),
    "de_p39": (46, 52, 48, 65), "de_p40": (62, 65, 75, 18),
}


def build_system_prompt(persona: tuple) -> str:
    """
    Pure WorldviewAnchor prompt — NO topic-specific anchors.
    This is the holdout condition. The model must derive answers
    solely from demographics, party OVA, and WorldviewAnchor scores.
    """
    pid, name, age, gender, region, party, religion, education, migration, weight = persona
    it, ind, ct, mf = WORLDVIEW[pid]

    is_east = "East" in region
    is_turkish = migration == "Turkish"

    if it < 30:
        it_desc = "You have very low trust in German institutions — parliament, courts, police. You feel the political class is disconnected from ordinary people."
    elif it < 50:
        it_desc = "You have mixed trust in German institutions. You see problems but acknowledge some things work."
    elif it < 70:
        it_desc = "You have moderate-to-high trust in German institutions, though you notice their limitations."
    else:
        it_desc = "You have high trust in German institutions. Rule of law and democratic processes are important to you."

    east_layer = ""
    if is_east:
        east_layer = (
            "\nEast German background: You grew up in or were shaped by the former GDR. "
            "This creates a specific kind of institutional skepticism — not ideological, but biographical. "
            "You experienced the gap between official claims and lived reality. "
            "You're skeptical of authority regardless of party."
        )

    migration_layer = ""
    if is_turkish:
        migration_layer = (
            "\nTurkish-German background: Your family came from Turkey. "
            "You identify as both German and Muslim. You've experienced discrimination. "
            "You're integrated but retain cultural and religious roots."
        )
    elif migration == "Other":
        migration_layer = (
            "\nMigration background: Your family has a non-German background. "
            "You identify as German but are aware of how migration shapes identity debates."
        )

    ova_map = {
        "AfD":     "German culture is under threat; ordinary people aren't represented; crime has increased with migration; politicians serve elites not the people",
        "CDU/CSU": "stability and order are essential; family and tradition matter; economic strength requires fiscal responsibility; Germany's interests first in the EU",
        "SPD":     "solidarity and social fairness are core values; workers deserve protection; the state should ensure equal opportunities",
        "Greens":  "climate is the defining challenge; diversity makes Germany stronger; fundamental transformation is necessary; future generations matter most",
        "FDP":     "individual freedom and market competition deliver prosperity; less state, more personal responsibility; innovation over regulation",
        "BSW":     "ordinary people are abandoned by both left and right; peace and diplomacy matter more than military spending; social justice without identity politics",
        "Left":    "capitalism creates inequality; solidarity with workers and migrants; fundamental redistribution is necessary",
        "Non-partisan": "no single party represents my views; I'm skeptical of all parties; I vote based on specific issues",
    }
    ova = ova_map.get(party, "")

    prompt = f"""You are {name}, a {age}-year-old {gender} from {region}, Germany.

Education: {education}. Religion: {religion}. Migration background: {migration}.

Political identity: You vote {party} or lean toward {party}. {ova}.

Your worldview:
- Institutional trust ({it}/100): {it_desc}
- Economic philosophy ({ind}/100): {"You prefer market and individual solutions over state intervention." if ind > 65 else "You believe the state should play a significant role in the economy." if ind < 40 else "You hold mixed views on state vs. market solutions."}
- Change tolerance ({ct}/100): {"You welcome fundamental change and see the status quo as insufficient." if ct > 70 else "You are deeply skeptical of rapid change and value stability and continuity." if ct < 30 else "You accept gradual, carefully managed change."}
- Moral foundationalism ({mf}/100): {"Your values are grounded in traditional religious or cultural norms on social questions." if mf > 65 else "You hold secular, liberal views on social and moral questions." if mf < 30 else "You hold mixed views, traditional on some questions and liberal on others."}{east_layer}{migration_layer}

Use the full response scale. When your views are strong, pick the strongest option that genuinely fits — do not soften your answer toward the middle if an extreme option is more accurate.

Answer every survey question as {name} would genuinely answer. Respond with the letter only (A, B, C, or D). Nothing else."""

    return prompt


def build_batch_requests(personas, questions):
    requests = []
    for persona in personas:
        pid = persona[0]
        system_prompt = build_system_prompt(persona)
        for q in questions:
            qid = q["id"]
            opts = "\n".join(f"{k}. {v}" for k, v in q["options"].items())
            user_msg = f"{q['text']}\n\n{opts}"
            requests.append({
                "custom_id": f"holdout_{pid}_{qid}",
                "params": {
                    "model": MODEL,
                    "max_tokens": 5,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": user_msg}],
                },
            })
    return requests


def compute_distributions(results, questions, personas):
    total_weight = sum(p[9] for p in personas)
    weight_map = {p[0]: p[9] for p in personas}
    q_ids = [q["id"] for q in questions]
    dists = {qid: {} for qid in q_ids}

    for custom_id, answer in results.items():
        parts = custom_id.split("_")
        # format: holdout_{pid}_{qid}  — but pid has underscores too: de_p01
        # custom_id = holdout_de_p01_hd01
        pid = "_".join(parts[1:3])   # de_p01
        qid = parts[3]               # hd01
        if pid not in weight_map or qid not in dists:
            continue
        w = weight_map[pid]
        dists[qid][answer] = dists[qid].get(answer, 0) + w

    # Normalise
    for qid in dists:
        total = sum(dists[qid].values())
        if total > 0:
            dists[qid] = {k: round(v / total, 4) for k, v in sorted(dists[qid].items())}
    return dists


def score_distributions(sim_dists, questions):
    scores = {}
    for q in questions:
        qid = q["id"]
        pew = q["pew_distribution"]
        sim = sim_dists.get(qid, {})
        pew_valid = {k: v for k, v in pew.items() if k != "DK"}
        pew_sum = sum(pew_valid.values())
        pew_norm = {k: v / pew_sum for k, v in pew_valid.items()}
        all_opts = set(pew_norm) | set(sim)
        tvd = sum(abs(pew_norm.get(o, 0) - sim.get(o, 0)) for o in all_opts)
        scores[qid] = round(1 - tvd / 2, 4)
    scores["overall"] = round(sum(v for k, v in scores.items() if k != "overall") / len(questions), 4)
    return scores


def main():
    questions = json.loads(HOLDOUT_Q.read_text())
    n_calls = len(PERSONAS) * len(questions)

    print("Study 1C Germany — Holdout Validation")
    print(f"Model:  {MODEL}")
    print(f"Batch:  Yes (50% discount)")
    print(f"Personas × Questions: {len(PERSONAS)} × {len(questions)} = {n_calls} calls")
    print(f"Topic anchors: NONE — pure WorldviewAnchor architecture")
    print("=" * 60)

    client = anthropic.Anthropic()
    requests = build_batch_requests(PERSONAS, questions)

    print(f"Submitting {n_calls} requests to Batch API…")
    batch = client.messages.batches.create(requests=requests)
    batch_id = batch.id
    print(f"Batch ID: {batch_id}")

    while True:
        status = client.messages.batches.retrieve(batch_id)
        counts = status.request_counts
        print(f"  Status: processing={counts.processing}, succeeded={counts.succeeded}, errored={counts.errored}")
        if status.processing_status == "ended":
            break
        time.sleep(30)

    print("Batch complete. Retrieving results…")
    raw_results = {}
    raw_lines = []
    for result in client.messages.batches.results(batch_id):
        cid = result.custom_id
        if result.result.type == "succeeded":
            text = result.result.message.content[0].text.strip().upper()
            answer = text[0] if text and text[0] in "ABCD" else "?"
        else:
            answer = "?"
        raw_results[cid] = answer
        raw_lines.append(json.dumps({"id": cid, "answer": answer}))

    sim_dists = compute_distributions(raw_results, questions, PERSONAS)
    scores = score_distributions(sim_dists, questions)

    out_json = RESULTS / "holdout_results.json"
    out_jsonl = RESULTS / "holdout_results_raw.jsonl"

    output = {
        "run_type": "holdout_validation",
        "model": MODEL,
        "batch_id": batch_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "n_personas": len(PERSONAS),
        "n_questions": len(questions),
        "n_calls": n_calls,
        "topic_anchors": "none",
        "note": "Pure WorldviewAnchor architecture — no topic-specific calibration anchors",
        "scores": scores,
        "sim_distributions": sim_dists,
        "pew_distributions": {q["id"]: q["pew_distribution"] for q in questions},
    }
    out_json.write_text(json.dumps(output, indent=2))
    out_jsonl.write_text("\n".join(raw_lines))

    print(f"\nResults saved:")
    print(f"  {out_json}")
    print(f"  {out_jsonl}")
    print(f"\nHoldout Distribution Accuracy (no anchors): {scores['overall']*100:.1f}%")
    print(f"Calibrated C-8 score (with anchors):        91.3%")
    print()
    print("Per-question scores:")
    for q in questions:
        qid = q["id"]
        print(f"  {qid} ({q['topic']:<30}): {scores[qid]*100:.1f}%")


if __name__ == "__main__":
    main()
