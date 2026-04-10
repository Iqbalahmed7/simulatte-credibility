#!/usr/bin/env python3
"""
holdout_runner.py — Europe Benchmark · Sweden holdout validation runner.

Runs only the 4 holdout questions (hd01–hd04) with ZERO topic-specific anchors.
Pure WorldviewAnchor architecture — tests generalisation outside calibration set.

Usage:
    python3 holdout_runner.py --run HD-1
    python3 holdout_runner.py --run HD-1 --dry-run

Protocol: minimum 3 independent runs. Results stable within ±2pp SD = reliable.

Holdout questions (Sweden):
    hd01  us_view              — US favorability
    hd02  zelenskyy_confidence — Confidence in Zelenskyy
    hd03  macron_confidence    — Confidence in Macron
    hd04  biden_confidence     — Confidence in Biden

Ground truth: Pew Research Center Global Attitudes, Spring 2024 (Sweden N=1,017).
"""

import argparse
import json
import time
import sys
import os
import hashlib
from pathlib import Path
from datetime import datetime, timezone

_env_file = Path(__file__).resolve().parent.parent.parent / ".env"  # europe_benchmark/.env
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
    ("sw_p01", "Erik Johansson",        54, "male",   "Sweden (Stockholm / Stockholms län)",          "SAP",           "NATO-support",  "None/secular",                 "Upper-secondary/vocational", 2.5),
    ("sw_p02", "Karin Andersson",       49, "female", "Sweden (Gothenburg / Västra Götaland)",        "SAP",           "NATO-support",  "None/secular",                 "Upper-secondary/vocational", 2.5),
    ("sw_p03", "Lars Nilsson",          62, "male",   "Sweden (Malmö / Skåne)",                       "SAP",           "NATO-support",  "None/secular",                 "Upper-secondary/vocational", 2.5),
    ("sw_p04", "Birgitta Eriksson",     58, "female", "Sweden (Örebro / Örebro län)",                 "SAP",           "NATO-support",  "None/secular",                 "Upper-secondary/vocational", 2.5),
    ("sw_p05", "Gunnar Karlsson",       67, "male",   "Sweden (Umeå / Västernorrland)",               "SAP",           "NATO-support",  "None/secular",                 "Compulsory/lower",           2.5),
    ("sw_p06", "Annika Persson",        45, "female", "Sweden (Linköping / Östergötland)",            "SAP",           "NATO-support",  "None/secular",                 "University/Masters",         2.0),
    ("sw_p07", "Sven Gustafsson",       56, "male",   "Sweden (rural Dalarna)",                       "SAP",           "NATO-support",  "Lutheran (non-practicing)",    "Compulsory/lower",           2.5),
    ("sw_p08", "Maj-Britt Svensson",    71, "female", "Sweden (Västerås / Västmanland)",              "SAP",           "NATO-support",  "Lutheran (non-practicing)",    "Upper-secondary/vocational", 2.5),
    ("sw_p09", "Henrik Larsson",        46, "male",   "Sweden (Stockholm / Stockholms län)",          "M",             "NATO-support",  "None/secular",                 "University/Masters",         2.0),
    ("sw_p10", "Cecilia Olsson",        41, "female", "Sweden (Stockholm / Stockholms län)",          "M",             "NATO-support",  "None/secular",                 "University/Masters",         2.0),
    ("sw_p11", "Johan Pettersson",      52, "male",   "Sweden (Gothenburg / Västra Götaland)",        "M",             "NATO-support",  "None/secular",                 "University/Masters",         2.0),
    ("sw_p12", "Maria Lindqvist",       38, "female", "Sweden (Uppsala / Uppsala län)",               "M",             "NATO-support",  "None/secular",                 "University/Masters",         2.0),
    ("sw_p13", "Anders Bergström",      59, "male",   "Sweden (Gothenburg / Västra Götaland)",        "M",             "NATO-support",  "Lutheran (non-practicing)",    "University/Masters",         2.0),
    ("sw_p14", "Sofie Magnusson",       44, "female", "Sweden (Stockholm / Stockholms län)",          "M",             "NATO-support",  "None/secular",                 "University/Masters",         2.0),
    ("sw_p15", "Roger Fransson",        48, "male",   "Sweden (Malmö / Skåne)",                       "SD",            "NATO-support",  "None/secular",                 "Upper-secondary/vocational", 2.5),
    ("sw_p16", "Åsa Lindgren",          44, "female", "Sweden (rural Dalarna)",                       "SD",            "NATO-support",  "None/secular",                 "Upper-secondary/vocational", 2.5),
    ("sw_p17", "Mattias Holm",          55, "male",   "Sweden (Linköping / Östergötland)",            "SD",            "NATO-support",  "Lutheran (non-practicing)",    "Compulsory/lower",           2.5),
    ("sw_p18", "Lena Björk",            52, "female", "Sweden (Gothenburg / Västra Götaland)",        "SD",            "NATO-support",  "None/secular",                 "Upper-secondary/vocational", 2.5),
    ("sw_p19", "Stefan Hedlund",        61, "male",   "Sweden (Umeå / Västernorrland)",               "SD",            "NATO-support",  "Lutheran (non-practicing)",    "Compulsory/lower",           2.5),
    ("sw_p20", "Ingrid Söderström",     47, "female", "Sweden (rural Dalarna)",                       "C",             "NATO-support",  "None/secular",                 "University/Masters",         2.0),
    ("sw_p21", "Patrik Sundqvist",      50, "male",   "Sweden (Umeå / Västernorrland)",               "C",             "NATO-support",  "None/secular",                 "Upper-secondary/vocational", 2.5),
    ("sw_p22", "Emma Lövgren",          32, "female", "Sweden (Stockholm / Stockholms län)",          "V",             "NATO-skeptic",  "None/secular",                 "University/Masters",         2.0),
    ("sw_p23", "Jonas Strömberg",       38, "male",   "Sweden (Gothenburg / Västra Götaland)",        "V",             "NATO-skeptic",  "None/secular",                 "University/Masters",         2.0),
    ("sw_p24", "Hanna Vikström",        29, "female", "Sweden (Uppsala / Uppsala län)",               "V",             "NATO-skeptic",  "None/secular",                 "University/Masters",         2.0),
    ("sw_p25", "Christer Lundgren",     57, "male",   "Sweden (Linköping / Östergötland)",            "KD",            "NATO-support",  "Lutheran (practicing)",        "Upper-secondary/vocational", 2.0),
    ("sw_p26", "Ingeborg Samuelsson",   53, "female", "Sweden (Stockholm / Stockholms län)",          "KD",            "NATO-support",  "Lutheran (practicing)",        "University/Masters",         2.0),
    ("sw_p27", "Torsten Åberg",         63, "male",   "Sweden (rural Dalarna)",                       "Non-partisan",  "NATO-support",  "Lutheran (non-practicing)",    "Compulsory/lower",           2.5),
    ("sw_p28", "Inger Westberg",        58, "female", "Sweden (Västerås / Västmanland)",              "Non-partisan",  "NATO-support",  "None/secular",                 "Upper-secondary/vocational", 2.5),
    ("sw_p29", "Mikael Dahl",           42, "male",   "Sweden (Malmö / Skåne)",                       "Non-partisan",  "NATO-support",  "None/secular",                 "Upper-secondary/vocational", 2.5),
    ("sw_p30", "Berit Holmgren",        67, "female", "Sweden (Umeå / Västernorrland)",               "Non-partisan",  "NATO-support",  "Lutheran (non-practicing)",    "Compulsory/lower",           2.5),
    ("sw_p31", "Niklas Forsgren",       36, "male",   "Sweden (Stockholm / Stockholms län)",          "Non-partisan",  "NATO-support",  "None/secular",                 "University/Masters",         2.0),
    ("sw_p32", "Camilla Rydén",         39, "female", "Sweden (Gothenburg / Västra Götaland)",        "Non-partisan",  "NATO-support",  "None/secular",                 "University/Masters",         2.0),
    ("sw_p33", "Bo Nordin",             74, "male",   "Sweden (rural Dalarna)",                       "Non-partisan",  "NATO-support",  "Lutheran (non-practicing)",    "Compulsory/lower",           2.5),
    ("sw_p34", "Kerstin Eliasson",      55, "female", "Sweden (Linköping / Östergötland)",            "Non-partisan",  "NATO-support",  "None/secular",                 "Upper-secondary/vocational", 2.5),
    ("sw_p35", "Håkan Nyström",         47, "male",   "Sweden (Malmö / Skåne)",                       "Non-partisan",  "NATO-skeptic",  "None/secular",                 "Upper-secondary/vocational", 2.5),
    ("sw_p36", "Susanne Alexandersson", 45, "female", "Sweden (Uppsala / Uppsala län)",               "Non-partisan",  "NATO-support",  "None/secular",                 "University/Masters",         2.0),
    ("sw_p37", "Leif Boström",          60, "male",   "Sweden (Västerås / Västmanland)",              "Non-partisan",  "NATO-support",  "Lutheran (non-practicing)",    "Upper-secondary/vocational", 2.5),
    ("sw_p38", "Astrid Wallin",         34, "female", "Sweden (Stockholm / Stockholms län)",          "Non-partisan",  "NATO-support",  "None/secular",                 "University/Masters",         2.0),
    ("sw_p39", "Per-Olov Engström",     69, "male",   "Sweden (Umeå / Västernorrland)",               "Non-partisan",  "NATO-support",  "Lutheran (non-practicing)",    "Compulsory/lower",           2.5),
    ("sw_p40", "Malin Björklund",       31, "female", "Sweden (Gothenburg / Västra Götaland)",        "Non-partisan",  "NATO-support",  "None/secular",                 "University/Masters",         2.0),
]

WORLDVIEW = {
    "sw_p01": (68,  42,  62,  14),
    "sw_p02": (65,  40,  60,  16),
    "sw_p03": (62,  38,  58,  18),
    "sw_p04": (64,  40,  62,  15),
    "sw_p05": (58,  36,  55,  22),
    "sw_p06": (70,  44,  68,  12),
    "sw_p07": (60,  38,  52,  28),
    "sw_p08": (56,  36,  48,  30),
    "sw_p09": (72,  70,  52,  18),
    "sw_p10": (70,  68,  54,  15),
    "sw_p11": (68,  72,  50,  20),
    "sw_p12": (74,  70,  58,  14),
    "sw_p13": (65,  66,  48,  32),
    "sw_p14": (71,  68,  56,  16),
    "sw_p15": (42,  58,  28,  42),
    "sw_p16": (38,  56,  25,  40),
    "sw_p17": (45,  60,  30,  48),
    "sw_p18": (40,  55,  26,  38),
    "sw_p19": (36,  58,  22,  50),
    "sw_p20": (66,  64,  62,  14),
    "sw_p21": (62,  62,  58,  18),
    "sw_p22": (56,  24,  80,  10),
    "sw_p23": (52,  26,  78,  12),
    "sw_p24": (54,  22,  82,  10),
    "sw_p25": (64,  56,  36,  68),
    "sw_p26": (62,  58,  40,  65),
    "sw_p27": (48,  50,  25,  44),
    "sw_p28": (55,  50,  40,  28),
    "sw_p29": (50,  52,  45,  22),
    "sw_p30": (44,  48,  30,  38),
    "sw_p31": (68,  60,  65,  12),
    "sw_p32": (65,  58,  62,  14),
    "sw_p33": (40,  48,  20,  48),
    "sw_p34": (58,  50,  48,  26),
    "sw_p35": (38,  52,  35,  30),
    "sw_p36": (66,  58,  60,  12),
    "sw_p37": (52,  50,  38,  36),
    "sw_p38": (70,  60,  68,  10),
    "sw_p39": (42,  46,  25,  46),
    "sw_p40": (64,  56,  64,  14),
}


def build_system_prompt(persona: tuple) -> str:
    """Pure WorldviewAnchor prompt — zero topic-specific anchors."""
    pid, name, age, gender, region, party, nato_ref, religion, education, weight = persona
    it, ind, ct, mf = WORLDVIEW[pid]

    is_stockholm              = "Stockholm" in region
    is_gothenburg             = "Gothenburg" in region or "Västra Götaland" in region
    is_malmo                  = "Malmö" in region or "Skåne" in region
    is_rural                  = "rural" in region or "Dalarna" in region
    is_north                  = "Umeå" in region or "Västernorrland" in region
    is_nato_support           = nato_ref == "NATO-support"
    is_nato_skeptic           = nato_ref == "NATO-skeptic"
    is_lutheran_practicing    = "practicing" in religion and "non" not in religion
    is_lutheran_nonpracticing = "non-practicing" in religion
    is_secular                = "secular" in religion or "None" in religion

    if it < 45:
        it_desc = (
            "You have low trust in Sweden's political establishment and mainstream media. "
            "You feel the political class governs for urban, educated elites and ignores "
            "ordinary Swedes — especially on immigration and crime. The Sweden Democrats "
            "exist because the old parties failed people like you."
        )
    elif it < 58:
        it_desc = (
            "You have mixed trust in Swedish institutions. You see real failures — "
            "especially on immigration policy and gang violence — but still believe in "
            "Swedish democratic tradition and the rule of law in principle."
        )
    elif it < 68:
        it_desc = (
            "You have moderate to good trust in Swedish institutions. You are realistic "
            "about their imperfections but broadly believe Sweden's model — transparency, "
            "rule of law, independent agencies — is something to be proud of."
        )
    else:
        it_desc = (
            "You have high trust in Swedish institutions. Swedish democracy, its "
            "independent agencies, free press, and the rule of law are fundamental "
            "values you believe in deeply. Sweden's model works."
        )

    if is_nato_support:
        nato_layer = (
            "\nNATO and security: Sweden's historic decision to join NATO in March 2024 "
            "was the right call. Russia's full-scale invasion of Ukraine ended 200 years "
            "of neutrality — that era is over. You support Sweden's NATO membership as "
            "essential for Baltic security and the credible deterrence of Russian aggression."
        )
    else:
        nato_layer = (
            "\nNATO and security: You have reservations about Sweden's NATO membership. "
            "Sweden's 200-year tradition of neutrality and non-alignment was a source of "
            "national identity and diplomatic credibility. You supported a strong defence "
            "but feel the rush to join NATO risks entangling Sweden in conflicts beyond "
            "its direct interests. That said, you understand the threat Russia poses."
        )

    ova_map = {
        "SAP": (
            "The Swedish Social Democrats built the folkhemmet — the people's home. "
            "The welfare state, universal healthcare, free education, and labour rights "
            "that make Sweden fair are SAP achievements. You believe in collective "
            "solutions, strong public services, and an economy that works for everyone, "
            "not just shareholders. The party is in opposition now but its values endure."
        ),
        "M": (
            "Sweden needs a well-functioning market economy, fiscal discipline, and "
            "a state that empowers individuals rather than creating dependency. The "
            "Moderates represent responsible centre-right governance: lower taxes, "
            "school choice, law and order, and a competitive business environment. "
            "You support the Tidö government's agenda — especially on crime and order."
        ),
        "SD": (
            "Mass immigration has fundamentally changed Sweden — and not for the better. "
            "Gang violence, parallel societies, and integration failures are the result "
            "of decades of irresponsible SAP immigration policy. The Sweden Democrats "
            "were the only party willing to name this reality. You want a Swedish Sweden: "
            "controlled immigration, cultural cohesion, and law and order. "
            "You are a Swedish nationalist-conservative, not a racist — you want Sweden "
            "to work for Swedes first."
        ),
        "C": (
            "The Centre Party stands for liberal values in a Swedish context: "
            "individual freedom, decentralisation, and a rural Sweden that isn't left "
            "behind by Stockholm. You believe in free markets but also in sustainable "
            "communities, liberal immigration policy, and EU cooperation. "
            "You are socially liberal and economically pragmatic."
        ),
        "V": (
            "Sweden's welfare model is under attack from the right. The Left Party "
            "stands for gender equality, workers' rights, welfare, and a foreign policy "
            "independent of military blocs. You are skeptical of NATO and believe "
            "Sweden's strength has always been its neutrality and development aid. "
            "You want a more equal Sweden — taxing the wealthy, investing in welfare, "
            "and addressing the climate emergency."
        ),
        "KD": (
            "Christian Democrat values — family, community, and human dignity — "
            "provide the ethical foundation for a cohesive Sweden. You support "
            "Christian heritage, stronger families, and care for the vulnerable. "
            "You are part of the Tidö government coalition and believe in law and order, "
            "integration through shared Swedish values, and a welfare system "
            "that prioritises families and the elderly."
        ),
        "Non-partisan": (
            "no single party fully represents your views. You follow politics but feel "
            "disillusioned with the party system — politicians argue while ordinary "
            "Swedes deal with rising costs, gang violence, and uncertain futures. "
            "You vote pragmatically or sometimes not at all."
        ),
    }
    ova = ova_map.get(party, "")

    religion_layer = ""
    if is_lutheran_practicing:
        religion_layer = (
            "\nFaith and identity: You are a practicing Lutheran Christian. "
            "Your faith shapes your values — care for others, honesty, and community. "
            "Sweden is very secular and you sometimes feel your faith is marginalised "
            "in public life. You support KD's emphasis on Christian heritage and values."
        )
    elif is_lutheran_nonpracticing:
        religion_layer = (
            "\nFaith and identity: You were raised Lutheran and still feel a loose "
            "cultural connection to the church — Christmas, confirmations, funerals. "
            "But religion plays little practical role in your daily life or worldview. "
            "You are secular in practice even if nominally Lutheran."
        )

    region_layer = ""
    if is_stockholm:
        region_layer = (
            "\nRegional background: You live in Stockholm, Sweden's capital and economic "
            "engine. You are part of Sweden's professional class. More cosmopolitan, "
            "pro-EU, and socially liberal than the national average. "
            "The political debates feel different here than in rural Sweden."
        )
    elif is_gothenburg:
        region_layer = (
            "\nRegional background: You live in Gothenburg (Göteborg), Sweden's second city "
            "and industrial hub. Strong labour movement history — Volvo, Ericsson. "
            "A mix of working-class SAP tradition and newer middle-class M voters."
        )
    elif is_malmo:
        region_layer = (
            "\nRegional background: You live in Malmö or Skåne in southern Sweden. "
            "Malmö is one of Sweden's most diverse cities and has faced serious "
            "challenges with gang violence and integration. It is also the heartland "
            "of SD support. Immigration and security dominate local politics."
        )
    elif is_rural:
        region_layer = (
            "\nRegional background: You live in rural Sweden — Dalarna or similar. "
            "You feel the distance between Stockholm's political class and the "
            "realities of rural life. Local industries, hunting, forestry, and "
            "community ties matter. Immigration has changed some smaller towns significantly."
        )
    elif is_north:
        region_layer = (
            "\nRegional background: You live in northern Sweden — Umeå or Norrland. "
            "A long way from Stockholm geographically and culturally. "
            "Strong SAP tradition among forestry and industrial workers. "
            "NATO membership feels very real here — Russia is close."
        )

    prompt = f"""You are {name}, a {age}-year-old {gender} from {region}.

Education: {education}. Religion: {religion}.

Political identity: {party}. {ova}

Your worldview:
- Institutional trust ({it}/100): {it_desc}
- Economic philosophy ({ind}/100): {"You prefer market and individual solutions over state intervention — lower taxes, less regulation, personal responsibility." if ind > 62 else "You believe the state should play a significant role in the economy — public investment, redistribution, strong social services." if ind < 38 else "You hold mixed views on state vs. market solutions."}
- Change tolerance ({ct}/100): {"You welcome fundamental change and see the status quo as deeply inadequate." if ct > 70 else "You are deeply skeptical of rapid change and value stability, tradition, and continuity." if ct < 28 else "You accept gradual, carefully managed change."}
- Moral foundationalism ({mf}/100): {"Your values are grounded in traditional religious or cultural norms on social questions." if mf > 55 else "You hold secular, liberal views on social and moral questions." if mf < 22 else "You hold mixed views — traditional on some questions, liberal on others."}{nato_layer}{religion_layer}{region_layer}

Important: Use the full response scale. When your views are strong, pick the strongest option that genuinely fits — do not soften your answer toward the middle if a more extreme option is accurate.

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

    print(f"\nEurope Benchmark — Sweden — Holdout {run_id}")
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
    parser = argparse.ArgumentParser(description="Europe Benchmark Sweden holdout runner")
    parser.add_argument("--run", required=True, help="Run ID, e.g. HD-1")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run_holdout(args.run, args.dry_run)


if __name__ == "__main__":
    main()
