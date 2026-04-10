#!/usr/bin/env python3
"""
holdout_runner.py — Europe Benchmark · France holdout validation runner.

Runs only the 5 holdout questions (hd01–hd05) with ZERO topic-specific anchors.
Pure WorldviewAnchor architecture — tests generalisation outside calibration set.

Usage:
    python3 holdout_runner.py --run HD-1
    python3 holdout_runner.py --run HD-1 --dry-run

Protocol: minimum 3 independent runs. Results stable within ±2pp SD = reliable.

Holdout questions (France):
    hd01  us_view              — US favorability
    hd02  un_view              — UN favorability
    hd03  zelenskyy_confidence — Confidence in Zelenskyy
    hd04  children_future      — Optimism for children's future
    hd05  biden_confidence     — Confidence in Biden

Ground truth: Pew Research Center Global Attitudes, Spring 2024 (France N=~1,000).
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
    _env_file = Path(__file__).resolve().parent.parent / ".env"  # france/.env fallback
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
# (id, name, age, gender, region, party, eu_ref, religion, education, weight)
PERSONAS = [
    # ── RN (Rassemblement National — nationalist, anti-immigration, Leave-EU) ──
    ("fr_p01", "Jean-Pierre Lebrun",  57, "male",   "France (North / Hauts-de-France)",  "RN",           "EU-skeptic", "Catholic (non-practicing)", "BEP/vocational", 2.5),
    ("fr_p02", "Martine Dupont",      53, "female", "France (Centre-Val de Loire)",       "RN",           "EU-skeptic", "Catholic (non-practicing)", "BEP/vocational", 2.5),
    ("fr_p03", "Claude Morin",        61, "male",   "France (South West / Occitanie)",    "RN",           "EU-skeptic", "None/secular",              "BEP/vocational", 2.5),
    ("fr_p04", "Sylvie Renard",       48, "female", "France (East / Grand Est)",          "RN",           "EU-skeptic", "Catholic (non-practicing)", "Bac/BTS",        2.5),
    ("fr_p05", "Gérard Fontaine",     65, "male",   "France (Provence / PACA)",           "RN",           "EU-skeptic", "Catholic (non-practicing)", "BEP/vocational", 2.5),

    # ── Renaissance (Macron's party — centrist, pro-EU, educated) ─────────────
    ("fr_p06", "Isabelle Mercier",    44, "female", "France (Paris / Île-de-France)",     "Renaissance",  "Pro-EU",     "None/secular",              "Masters/grandes écoles", 2.0),
    ("fr_p07", "Thomas Garnier",      39, "male",   "France (Paris / Île-de-France)",     "Renaissance",  "Pro-EU",     "None/secular",              "Masters/grandes écoles", 2.0),
    ("fr_p08", "Nathalie Petit",      51, "female", "France (Lyon / Auvergne-Rhône-Alpes)", "Renaissance","Pro-EU",     "Catholic (non-practicing)", "Masters/grandes écoles", 2.0),
    ("fr_p09", "Laurent Dubois",      46, "male",   "France (Bordeaux / Nouvelle-Aquitaine)", "Renaissance","Pro-EU",   "None/secular",              "Masters/grandes écoles", 2.0),
    ("fr_p10", "Claire Beaumont",     35, "female", "France (Paris / Île-de-France)",     "Renaissance",  "Pro-EU",     "None/secular",              "Masters/grandes écoles", 2.0),
    ("fr_p11", "Marc Lefebvre",       55, "male",   "France (North / Hauts-de-France)",   "Renaissance",  "Pro-EU",     "Catholic (non-practicing)", "Bac/BTS",        2.0),
    ("fr_p12", "Véronique Simon",     42, "female", "France (Toulouse / Occitanie)",      "Renaissance",  "Pro-EU",     "None/secular",              "Masters/grandes écoles", 2.0),
    ("fr_p13", "Frédéric Bonnet",     49, "male",   "France (Strasbourg / Grand Est)",    "Renaissance",  "Pro-EU",     "Catholic (non-practicing)", "Bac/BTS",        2.0),

    # ── LFI (La France Insoumise — Mélenchon left, anti-establishment) ────────
    ("fr_p14", "Leila Benali",        31, "female", "France (Paris / Île-de-France)",     "LFI",          "EU-skeptic", "Muslim",                    "Masters/grandes écoles", 2.5),
    ("fr_p15", "Antoine Roux",        27, "male",   "France (Marseille / PACA)",          "LFI",          "EU-skeptic", "None/secular",              "Bac/BTS",        2.5),
    ("fr_p16", "Fatima Chaoui",       36, "female", "France (Paris suburb / Île-de-France)", "LFI",       "EU-skeptic", "Muslim",                    "Bac/BTS",        2.5),
    ("fr_p17", "Baptiste Girard",     33, "male",   "France (Bordeaux / Nouvelle-Aquitaine)", "LFI",      "EU-skeptic", "None/secular",              "Masters/grandes écoles", 2.0),
    ("fr_p18", "Amina Diallo",        29, "female", "France (Lyon / Auvergne-Rhône-Alpes)", "LFI",        "EU-skeptic", "Muslim",                    "Bac/BTS",        2.5),

    # ── LR (Les Républicains — Gaullist centre-right, pro-EU-lite, traditional) ─
    ("fr_p19", "Philippe Rousseau",   63, "male",   "France (Paris / Île-de-France)",     "LR",           "Pro-EU",     "Catholic (practicing)",     "Masters/grandes écoles", 2.0),
    ("fr_p20", "Catherine Moreau",    58, "female", "France (West / Bretagne)",           "LR",           "Pro-EU",     "Catholic (practicing)",     "Bac/BTS",        2.5),
    ("fr_p21", "Henri Charlot",       55, "male",   "France (East / Grand Est)",          "LR",           "Pro-EU",     "Catholic (practicing)",     "Masters/grandes écoles", 2.0),
    ("fr_p22", "Dominique Faure",     49, "female", "France (South / PACA)",              "LR",           "Pro-EU",     "Catholic (practicing)",     "Bac/BTS",        2.5),
    ("fr_p23", "Bernard Leclerc",     67, "male",   "France (Centre-Val de Loire)",       "LR",           "Pro-EU",     "Catholic (practicing)",     "BEP/vocational", 2.5),

    # ── PS (Parti Socialiste — social-democrat, pro-EU, centre-left) ──────────
    ("fr_p24", "Sandrine Vidal",      45, "female", "France (Paris / Île-de-France)",     "PS",           "Pro-EU",     "None/secular",              "Masters/grandes écoles", 2.0),
    ("fr_p25", "Éric Perrin",         52, "male",   "France (Lyon / Auvergne-Rhône-Alpes)", "PS",         "Pro-EU",     "None/secular",              "Masters/grandes écoles", 2.0),
    ("fr_p26", "Monique Aubert",      60, "female", "France (North / Hauts-de-France)",   "PS",           "Pro-EU",     "None/secular",              "Bac/BTS",        2.5),
    ("fr_p27", "Julien Marchand",     38, "male",   "France (Bordeaux / Nouvelle-Aquitaine)", "PS",       "Pro-EU",     "None/secular",              "Masters/grandes écoles", 2.0),

    # ── Non-partisan / disengaged (cross-cutting, largely periurban) ───────────
    ("fr_p28", "Michel Chevalier",    59, "male",   "France (North / Hauts-de-France)",   "Non-partisan", "EU-skeptic", "Catholic (non-practicing)", "BEP/vocational", 2.5),
    ("fr_p29", "Brigitte Lamy",       54, "female", "France (Centre-Val de Loire)",       "Non-partisan", "EU-skeptic", "None/secular",              "BEP/vocational", 2.5),
    ("fr_p30", "Rachid Ouali",        43, "male",   "France (Paris suburb / Île-de-France)", "Non-partisan","EU-skeptic","Muslim",                   "Bac/BTS",        2.5),
    ("fr_p31", "Agnès Toussaint",     47, "female", "France (South West / Occitanie)",    "Non-partisan", "EU-skeptic", "Catholic (non-practicing)", "BEP/vocational", 2.5),
    ("fr_p32", "Pierre Dufour",       64, "male",   "France (East / Grand Est)",          "Non-partisan", "EU-skeptic", "Catholic (non-practicing)", "BEP/vocational", 2.5),
    ("fr_p33", "Élise Guérin",        30, "female", "France (Paris / Île-de-France)",     "Non-partisan", "Pro-EU",     "None/secular",              "Masters/grandes écoles", 2.0),
    ("fr_p34", "Yves Bouchard",       68, "male",   "France (West / Bretagne)",           "Non-partisan", "Pro-EU",     "Catholic (practicing)",     "Bac/BTS",        2.5),
    ("fr_p35", "Nadia Bousquet",      37, "female", "France (Lyon / Auvergne-Rhône-Alpes)", "Non-partisan","Pro-EU",    "Muslim",                    "Bac/BTS",        2.5),
    ("fr_p36", "Alain Dupré",         62, "male",   "France (South / PACA)",              "Non-partisan", "EU-skeptic", "None/secular",              "BEP/vocational", 2.5),
    ("fr_p37", "Cécile Martin",       41, "female", "France (Bordeaux / Nouvelle-Aquitaine)", "Non-partisan","Pro-EU",  "None/secular",              "Masters/grandes écoles", 2.0),
    ("fr_p38", "Robert Aumont",       71, "male",   "France (Centre-Val de Loire)",       "Non-partisan", "EU-skeptic", "Catholic (non-practicing)", "BEP/vocational", 2.5),
    ("fr_p39", "Laure Tissier",       34, "female", "France (Strasbourg / Grand Est)",    "Non-partisan", "Pro-EU",     "None/secular",              "Bac/BTS",        2.0),
    ("fr_p40", "Denis Charpentier",   56, "male",   "France (North / Hauts-de-France)",   "Non-partisan", "EU-skeptic", "Catholic (non-practicing)", "BEP/vocational", 2.5),
]

# ── WorldviewAnchor values ────────────────────────────────────────────────────
WORLDVIEW = {
    # id:        (IT,  IND, CT,  MF)
    # RN — low IT, moderate IND, low CT, moderate-high MF
    "fr_p01": (30,  55,  20,  45),
    "fr_p02": (28,  52,  18,  42),
    "fr_p03": (32,  56,  22,  28),
    "fr_p04": (35,  54,  25,  44),
    "fr_p05": (27,  58,  15,  48),

    # Renaissance — high IT, moderate IND, moderate CT, low MF
    "fr_p06": (68,  62,  60,  15),
    "fr_p07": (65,  60,  58,  12),
    "fr_p08": (62,  58,  55,  28),
    "fr_p09": (60,  62,  57,  14),
    "fr_p10": (70,  58,  65,  10),
    "fr_p11": (55,  56,  50,  35),
    "fr_p12": (64,  60,  62,  12),
    "fr_p13": (58,  55,  52,  32),

    # LFI — low-moderate IT, low IND, very high CT, low MF (secular left)
    "fr_p14": (35,  25,  80,  55),
    "fr_p15": (28,  22,  82,  15),
    "fr_p16": (30,  24,  78,  60),
    "fr_p17": (32,  28,  78,  10),
    "fr_p18": (26,  22,  80,  62),

    # LR — moderate-high IT, high IND, low CT, high MF
    "fr_p19": (60,  70,  28,  58),
    "fr_p20": (58,  65,  25,  65),
    "fr_p21": (62,  68,  30,  62),
    "fr_p22": (55,  62,  28,  60),
    "fr_p23": (52,  60,  22,  65),

    # PS — moderate IT, low-moderate IND, moderate-high CT, low MF
    "fr_p24": (58,  38,  68,  14),
    "fr_p25": (55,  40,  65,  12),
    "fr_p26": (50,  38,  60,  18),
    "fr_p27": (56,  42,  68,  10),

    # Non-partisan — wide spread
    "fr_p28": (32,  50,  20,  40),
    "fr_p29": (28,  48,  22,  30),
    "fr_p30": (35,  42,  45,  65),
    "fr_p31": (30,  48,  18,  42),
    "fr_p32": (25,  50,  16,  44),
    "fr_p33": (62,  56,  72,  10),
    "fr_p34": (58,  52,  30,  62),
    "fr_p35": (50,  44,  58,  60),
    "fr_p36": (28,  55,  18,  25),
    "fr_p37": (60,  55,  65,  12),
    "fr_p38": (22,  50,  14,  48),
    "fr_p39": (56,  52,  62,  15),
    "fr_p40": (30,  50,  20,  42),
}


def build_system_prompt(persona: tuple) -> str:
    """Pure WorldviewAnchor prompt — zero topic-specific anchors."""
    pid, name, age, gender, region, party, eu_ref, religion, education, weight = persona
    it, ind, ct, mf = WORLDVIEW[pid]

    is_paris        = "Paris" in region or "Île-de-France" in region
    is_paris_suburb = "suburb" in region
    is_north        = "North" in region or "Hauts-de-France" in region
    is_south        = "PACA" in region or "Provence" in region
    is_pro_eu       = eu_ref == "Pro-EU"
    is_eu_skeptic   = eu_ref == "EU-skeptic"
    is_muslim       = religion == "Muslim"
    is_catholic_practicing = "practicing" in religion and "non" not in religion

    # ── Institutional trust descriptor ────────────────────────────────────────
    if it < 35:
        it_desc = (
            "You have very low trust in French institutions — the République, the media, "
            "Brussels. You feel the political class (PPPL — les partis politiques et les "
            "lobbies) governs for elites, not ordinary French people."
        )
    elif it < 52:
        it_desc = (
            "You have mixed trust in French institutions. You see real dysfunction and "
            "growing disillusionment, but still believe in republican values in principle."
        )
    elif it < 65:
        it_desc = (
            "You have moderate trust in French institutions. You're realistic about their "
            "imperfections but broadly believe in the Fifth Republic's stability."
        )
    else:
        it_desc = (
            "You have high trust in French institutions. The rule of law, democratic "
            "process, and European cooperation matter deeply to you."
        )

    # ── EU/Europe layer ────────────────────────────────────────────────────────
    if is_pro_eu:
        eu_layer = (
            "\nEurope: You are broadly pro-European. You see the EU as a force for "
            "stability, prosperity, and French influence in the world. "
            "The European project matters to you, even if its execution is imperfect."
        )
    else:
        eu_layer = (
            "\nEurope: You are skeptical of the EU. You feel that Brussels imposes rules "
            "that undermine French sovereignty, protect corporations over workers, and "
            "fail ordinary citizens. You are not unconditionally opposed to Europe "
            "but demand a fundamentally reformed relationship."
        )

    # ── Party political identity ───────────────────────────────────────────────
    ova_map = {
        "RN": (
            "France has been betrayed by the establishment — uncontrolled immigration, "
            "deindustrialisation, and a political class that serves globalised elites while "
            "ordinary French people struggle. Le Pen's Rassemblement National represents "
            "the France that has been left behind. You want firm border control, "
            "priorité nationale in social policy, and French sovereignty restored."
        ),
        "Renaissance": (
            "France needs bold reform — a dynamic economy, strong European partnerships, "
            "and a credible defence capacity. Macron's Renaissance represents a break from "
            "the old partisan blocs (ni droite ni gauche) that failed France. "
            "You believe in an open, modern, meritocratic France that leads in Europe."
        ),
        "LFI": (
            "The current economic system fails workers and the planet. Mélenchon's "
            "La France Insoumise represents the only credible break from neo-liberal "
            "austerity — stronger purchasing power, ecological transition, and a foreign "
            "policy free from NATO and American dominance. "
            "You are deeply anti-establishment and reject both the traditional left and right."
        ),
        "LR": (
            "France needs strong leadership grounded in Gaullist tradition — "
            "republican order, security, sovereign foreign policy, and economic competence. "
            "Les Républicains represent the responsible centre-right: lower taxes, "
            "strong institutions, firm immigration policy, and European pragmatism. "
            "You are conservative, not nationalist, and distrust both Macron and Le Pen."
        ),
        "PS": (
            "Social democracy — equality, public services, and European solidarity — "
            "remains France's best path. The Parti Socialiste stands for workers' rights, "
            "universal healthcare, progressive taxation, and a social Europe. "
            "You are pro-EU but believe it must serve people, not markets."
        ),
        "Non-partisan": (
            "no single party represents your views. You are disillusioned with the "
            "political class as a whole — la politique politicienne — and vote based "
            "on immediate concerns or not at all."
        ),
    }
    ova = ova_map.get(party, "")

    # ── Religion layer ────────────────────────────────────────────────────────
    religion_layer = ""
    if is_muslim:
        religion_layer = (
            "\nFaith and identity: Your Muslim faith is part of your identity. "
            "You experience discrimination and feel that mainstream French politics often "
            "uses Islam as a wedge issue. You believe in laïcité but reject its weaponisation "
            "against Muslim communities. France is your country too."
        )
    elif is_catholic_practicing:
        religion_layer = (
            "\nFaith and identity: You are a practising Catholic. "
            "Your faith informs your social values — family, community, and moral "
            "responsibility. You believe France's Christian heritage matters and "
            "worry about secularism becoming aggressively anti-religious."
        )

    # ── Regional layer ────────────────────────────────────────────────────────
    region_layer = ""
    if is_north:
        region_layer = (
            "\nRegional background: You are from the North (Hauts-de-France) — "
            "once the industrial heart of France, now struggling with deindustrialisation "
            "and long-term unemployment. This region votes heavily RN. "
            "You feel forgotten by Paris and Brussels alike."
        )
    elif is_paris and not is_paris_suburb:
        region_layer = (
            "\nRegional background: You live in Paris or the inner Île-de-France. "
            "You are part of France's professional and educated class. "
            "You are more cosmopolitan, pro-EU, and socially liberal than the national average."
        )
    elif is_paris_suburb:
        region_layer = (
            "\nRegional background: You live in the Paris banlieue (suburbs). "
            "This is one of the most diverse and economically unequal areas of France. "
            "You navigate identity, discrimination, and precarity daily."
        )
    elif is_south:
        region_layer = (
            "\nRegional background: You are from the South (PACA / Provence-Côte d'Azur). "
            "This region has historically swung between the left and far-right. "
            "Immigration from North Africa, regional identity, and economic precarity "
            "all shape local politics strongly."
        )

    prompt = f"""You are {name}, a {age}-year-old {gender} from {region}, France.

Education: {education}. Religion: {religion}.

Political identity: {party}. {ova}

Your worldview:
- Institutional trust ({it}/100): {it_desc}
- Economic philosophy ({ind}/100): {"You prefer market and individual solutions over state intervention — lower taxes, less regulation, personal responsibility." if ind > 65 else "You believe the state should play a significant role in the economy — public investment, redistribution, strong social services." if ind < 42 else "You hold mixed views on state vs. market solutions."}
- Change tolerance ({ct}/100): {"You welcome fundamental change and see the status quo as deeply inadequate." if ct > 70 else "You are deeply skeptical of rapid change and value stability, tradition, and continuity." if ct < 28 else "You accept gradual, carefully managed change."}
- Moral foundationalism ({mf}/100): {"Your values are grounded in traditional religious or cultural norms on social questions." if mf > 58 else "You hold secular, liberal views on social and moral questions." if mf < 25 else "You hold mixed views — traditional on some questions, liberal on others."}{eu_layer}{religion_layer}{region_layer}

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

    print(f"\nEurope Benchmark — France — Holdout {run_id}")
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
    parser = argparse.ArgumentParser(description="Europe Benchmark France holdout runner")
    parser.add_argument("--run", required=True, help="Run ID, e.g. HD-1")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run_holdout(args.run, args.dry_run)


if __name__ == "__main__":
    main()
