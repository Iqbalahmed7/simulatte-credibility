#!/usr/bin/env python3
"""
holdout_runner.py — Europe Benchmark · Hungary holdout validation runner.

Runs only the 5 holdout questions (hd01–hd05) with ZERO topic-specific anchors.
Pure WorldviewAnchor architecture — tests generalisation outside calibration set.

Usage:
    python3 holdout_runner.py --run HD-1
    python3 holdout_runner.py --run HD-1 --dry-run

Protocol: minimum 3 independent runs. Results stable within ±2pp SD = reliable.

Holdout questions (Hungary):
    hd01  us_view              — US favorability
    hd02  un_view              — UN favorability
    hd03  zelenskyy_confidence — Confidence in Zelenskyy
    hd04  macron_confidence    — Confidence in Macron
    hd05  biden_confidence     — Confidence in Biden

Ground truth: Pew Research Center Global Attitudes, Spring 2024 (Hungary N=996).
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
    # ── Fidesz (nationalist-conservative, dominant since 2010) ────────────────
    ("hu_p01", "Kovács István",        58, "male",   "Hungary (Eastern / Hajdú-Bihar county)",    "Fidesz",       "EU-frustrated", "Catholic (non-practicing)", "Vocational/secondary",  2.5),
    ("hu_p02", "Tóth Erzsébet",        54, "female", "Hungary (Northern / Borsod county)",        "Fidesz",       "EU-frustrated", "Calvinist Reformed",        "Vocational/secondary",  2.5),
    ("hu_p03", "Nagy Sándor",          63, "male",   "Hungary (Rural / Szabolcs county)",         "Fidesz",       "EU-frustrated", "Catholic (practicing)",     "Vocational/secondary",  2.5),
    ("hu_p04", "Horváth Mária",        49, "female", "Hungary (Western / Győr-Moson-Sopron)",     "Fidesz",       "EU-frustrated", "Catholic (non-practicing)", "Secondary/Bac",         2.5),
    ("hu_p05", "Szabó Zoltán",         67, "male",   "Hungary (Southern / Baranya county)",       "Fidesz",       "EU-frustrated", "Catholic (practicing)",     "Vocational/secondary",  2.5),
    ("hu_p06", "Varga Katalin",        44, "female", "Hungary (Northern / Heves county)",         "Fidesz",       "EU-frustrated", "Calvinist Reformed",        "Secondary/Bac",         2.5),
    ("hu_p07", "Kiss Gábor",           51, "male",   "Hungary (Semi-urban / Miskolc)",            "Fidesz",       "EU-frustrated", "Catholic (non-practicing)", "Secondary/Bac",         2.5),
    ("hu_p08", "Molnár Ilona",         61, "female", "Hungary (Rural / Somogy county)",           "Fidesz",       "EU-frustrated", "Catholic (practicing)",     "Vocational/secondary",  2.5),
    ("hu_p09", "Németh Péter",         47, "male",   "Hungary (Eastern / Debrecen area)",         "Fidesz",       "EU-frustrated", "Calvinist Reformed",        "University/college",    2.5),

    # ── DK (Democratic Coalition — liberal opposition, pro-EU, Budapest) ──────
    ("hu_p10", "Farkas Zsuzsa",        41, "female", "Hungary (Budapest / District VII)",         "DK",           "Pro-EU",        "None/secular",              "University/college",    2.0),
    ("hu_p11", "Kovács Ádám",          36, "male",   "Hungary (Budapest / Buda side)",            "DK",           "Pro-EU",        "None/secular",              "University/college",    2.0),
    ("hu_p12", "Tóth Réka",            45, "female", "Hungary (Budapest / District XIII)",        "DK",           "Pro-EU",        "Catholic (non-practicing)", "University/college",    2.0),
    ("hu_p13", "Horváth Dániel",       52, "male",   "Hungary (Budapest / District II)",          "DK",           "Pro-EU",        "None/secular",              "University/college",    2.0),
    ("hu_p14", "Nagy Eszter",          33, "female", "Hungary (Budapest / Pest agglomeration)",   "DK",           "Pro-EU",        "None/secular",              "University/college",    2.0),

    # ── Jobbik (originally far-right, now reformed centre-right) ─────────────
    ("hu_p15", "Szabó Attila",         44, "male",   "Hungary (Northern / Miskolc area)",         "Jobbik",       "EU-skeptic",    "Catholic (non-practicing)", "Secondary/Bac",         2.5),
    ("hu_p16", "Varga Judit",          38, "female", "Hungary (Eastern / Nyíregyháza area)",      "Jobbik",       "EU-skeptic",    "Calvinist Reformed",        "Secondary/Bac",         2.5),
    ("hu_p17", "Kiss Balázs",          50, "male",   "Hungary (Rural / Bács-Kiskun county)",      "Jobbik",       "EU-skeptic",    "Catholic (non-practicing)", "Vocational/secondary",  2.5),
    ("hu_p18", "Molnár Orsolya",       42, "female", "Hungary (Semi-urban / Eger)",               "Jobbik",       "EU-skeptic",    "Catholic (practicing)",     "Secondary/Bac",         2.5),

    # ── MSZP (Socialist — older, working class, urban) ────────────────────────
    ("hu_p19", "Németh László",        64, "male",   "Hungary (Budapest / District VIII)",        "MSZP",         "Pro-EU",        "None/secular",              "Secondary/Bac",         2.5),
    ("hu_p20", "Farkas Ágnes",         59, "female", "Hungary (Semi-urban / Pécs)",               "MSZP",         "Pro-EU",        "None/secular",              "Vocational/secondary",  2.5),
    ("hu_p21", "Kovács Tibor",         68, "male",   "Hungary (Northern / Ózd area)",             "MSZP",         "Pro-EU",        "None/secular",              "Vocational/secondary",  2.5),

    # ── Mi Hazánk (far-right, extreme nationalist) ────────────────────────────
    ("hu_p22", "Tóth Norbert",         39, "male",   "Hungary (Rural / Szabolcs-Szatmár county)", "Mi Hazánk",    "EU-hostile",    "Catholic (non-practicing)", "Vocational/secondary",  2.5),
    ("hu_p23", "Horváth Béla",         55, "male",   "Hungary (Northern / Nógrád county)",        "Mi Hazánk",    "EU-hostile",    "Calvinist Reformed",        "Vocational/secondary",  2.5),

    # ── Other left/green ──────────────────────────────────────────────────────
    ("hu_p24", "Szabó Lilla",          29, "female", "Hungary (Budapest / District VI)",          "Other left",   "Pro-EU",        "None/secular",              "University/college",    2.0),
    ("hu_p25", "Varga Márton",         34, "male",   "Hungary (Budapest / District IX)",          "Other left",   "Pro-EU",        "None/secular",              "University/college",    2.0),
    ("hu_p26", "Kiss Flóra",           26, "female", "Hungary (Budapest / District XIV)",         "Other left",   "Pro-EU",        "None/secular",              "University/college",    2.0),

    # ── Non-partisan (cross-cutting: Fidesz-adjacent rural + opposition-adj.) ─
    ("hu_p27", "Molnár Ferenc",        60, "male",   "Hungary (Rural / Tolna county)",            "Non-partisan", "EU-frustrated", "Catholic (non-practicing)", "Vocational/secondary",  2.5),
    ("hu_p28", "Németh Éva",           53, "female", "Hungary (Rural / Fejér county)",            "Non-partisan", "EU-frustrated", "Catholic (non-practicing)", "Vocational/secondary",  2.5),
    ("hu_p29", "Farkas Imre",          66, "male",   "Hungary (Eastern / Hajdú-Bihar rural)",     "Non-partisan", "EU-frustrated", "Calvinist Reformed",        "Vocational/secondary",  2.5),
    ("hu_p30", "Kovács Veronika",      48, "female", "Hungary (Semi-urban / Debrecen)",           "Non-partisan", "EU-frustrated", "Catholic (non-practicing)", "Secondary/Bac",         2.5),
    ("hu_p31", "Tóth Csaba",           57, "male",   "Hungary (Northern / Miskolc)",              "Non-partisan", "EU-frustrated", "None/secular",              "Secondary/Bac",         2.5),
    ("hu_p32", "Horváth Tünde",        43, "female", "Hungary (Western / Győr)",                  "Non-partisan", "EU-frustrated", "Catholic (non-practicing)", "Secondary/Bac",         2.5),
    ("hu_p33", "Nagy Róbert",          35, "male",   "Hungary (Budapest / District IV)",          "Non-partisan", "Pro-EU",        "None/secular",              "University/college",    2.0),
    ("hu_p34", "Szabó Henrietta",      50, "female", "Hungary (Budapest / District XI)",          "Non-partisan", "Pro-EU",        "Catholic (non-practicing)", "Secondary/Bac",         2.0),
    ("hu_p35", "Varga Gergő",          31, "male",   "Hungary (Budapest / District XV)",          "Non-partisan", "Pro-EU",        "None/secular",              "University/college",    2.0),
    ("hu_p36", "Kiss Magdolna",        72, "female", "Hungary (Rural / Somogy county)",           "Non-partisan", "EU-frustrated", "Catholic (practicing)",     "Vocational/secondary",  2.5),
    ("hu_p37", "Molnár Árpád",         62, "male",   "Hungary (Southern / Pécs area)",            "Non-partisan", "EU-frustrated", "Catholic (non-practicing)", "Vocational/secondary",  2.5),
    ("hu_p38", "Németh Klára",         46, "female", "Hungary (Semi-urban / Veszprém)",           "Non-partisan", "EU-frustrated", "Calvinist Reformed",        "Secondary/Bac",         2.5),
    ("hu_p39", "Farkas Zsolt",         58, "male",   "Hungary (Eastern / Szolnok area)",          "Non-partisan", "EU-frustrated", "None/secular",              "Vocational/secondary",  2.5),
    ("hu_p40", "Kovács Annamária",     37, "female", "Hungary (Budapest / Pest county)",          "Non-partisan", "Pro-EU",        "None/secular",              "Secondary/Bac",         2.0),
]

WORLDVIEW = {
    "hu_p01": (58,  58,  22,  60),
    "hu_p02": (55,  56,  20,  65),
    "hu_p03": (62,  60,  18,  72),
    "hu_p04": (54,  58,  25,  55),
    "hu_p05": (60,  55,  16,  70),
    "hu_p06": (52,  57,  24,  63),
    "hu_p07": (56,  60,  26,  52),
    "hu_p08": (63,  54,  15,  68),
    "hu_p09": (50,  62,  30,  58),
    "hu_p10": (32,  55,  70,  12),
    "hu_p11": (30,  56,  72,  10),
    "hu_p12": (38,  52,  65,  25),
    "hu_p13": (35,  54,  68,  14),
    "hu_p14": (28,  58,  74,  10),
    "hu_p15": (42,  56,  30,  48),
    "hu_p16": (38,  55,  28,  55),
    "hu_p17": (40,  54,  25,  50),
    "hu_p18": (44,  56,  32,  58),
    "hu_p19": (48,  38,  55,  16),
    "hu_p20": (45,  36,  52,  18),
    "hu_p21": (42,  35,  50,  20),
    "hu_p22": (28,  58,  14,  65),
    "hu_p23": (25,  60,  12,  68),
    "hu_p24": (30,  32,  82,   8),
    "hu_p25": (32,  34,  80,  10),
    "hu_p26": (28,  30,  84,   8),
    "hu_p27": (50,  55,  22,  55),
    "hu_p28": (48,  54,  20,  52),
    "hu_p29": (52,  56,  18,  60),
    "hu_p30": (46,  56,  28,  48),
    "hu_p31": (44,  55,  26,  40),
    "hu_p32": (50,  57,  30,  50),
    "hu_p33": (35,  52,  65,  12),
    "hu_p34": (40,  50,  58,  28),
    "hu_p35": (32,  54,  68,  10),
    "hu_p36": (55,  50,  16,  68),
    "hu_p37": (48,  55,  24,  52),
    "hu_p38": (46,  56,  30,  58),
    "hu_p39": (44,  54,  22,  42),
    "hu_p40": (36,  52,  62,  15),
}


def build_system_prompt(persona: tuple) -> str:
    """Pure WorldviewAnchor prompt — zero topic-specific anchors."""
    pid, name, age, gender, region, party, eu_ref, religion, education, weight = persona
    it, ind, ct, mf = WORLDVIEW[pid]

    is_budapest           = "Budapest" in region
    is_rural              = "Rural" in region or "county" in region
    is_eastern            = "Eastern" in region or "Hajdú" in region or "Szabolcs" in region or "Debrecen" in region
    is_northern           = "Northern" in region or "Borsod" in region or "Miskolc" in region or "Nógrád" in region
    is_western            = "Western" in region or "Győr" in region
    is_eu_frustrated      = eu_ref == "EU-frustrated"
    is_pro_eu             = eu_ref == "Pro-EU"
    is_eu_hostile         = eu_ref == "EU-hostile"
    is_calvinist          = "Calvinist" in religion
    is_catholic_practicing = "practicing" in religion and "non" not in religion
    is_non_practicing     = "non-practicing" in religion
    is_secular            = "secular" in religion or "None" in religion

    # ── Institutional trust descriptor ────────────────────────────────────────
    if it < 35:
        it_desc = (
            "You have very low trust in Hungarian institutions — you believe Orbán has "
            "captured the courts, media, and electoral system to entrench his power. "
            "The state serves Fidesz, not Hungarian citizens."
        )
    elif it < 48:
        it_desc = (
            "You have mixed trust in Hungarian institutions. You recognise the system "
            "is skewed toward Fidesz but retain some faith in certain state functions "
            "and local administration."
        )
    elif it < 58:
        it_desc = (
            "You have moderate trust in Hungarian institutions. You broadly support "
            "the direction of the country under its current government, though you "
            "acknowledge things are not perfect."
        )
    else:
        it_desc = (
            "You have relatively high trust in Hungarian institutions — the government, "
            "police, and national media broadly reflect your values and Hungary's interests. "
            "Orbán has stabilised Hungary and stood up to Brussels."
        )

    # ── EU/Europe layer ────────────────────────────────────────────────────────
    if is_pro_eu:
        eu_layer = (
            "\nEurope: You are strongly pro-European. You see EU membership as essential "
            "for Hungary's democracy, rule of law, and economic development. "
            "You are deeply frustrated that Orbán has isolated Hungary within the EU and "
            "undermined democratic norms for which Hungarians fought in 1989."
        )
    elif is_eu_frustrated:
        eu_layer = (
            "\nEurope: You have ambivalent feelings about the EU. You accept that EU "
            "membership brings economic benefits and you are not calling for Huxit, "
            "but you resent Brussels interfering in Hungarian internal affairs, "
            "dictating on migration, and threatening to withhold funds. "
            "Orbán is right to defend Hungarian sovereignty against EU overreach."
        )
    else:  # EU-hostile
        eu_layer = (
            "\nEurope: You are deeply hostile to the EU. Brussels is an unelected "
            "bureaucracy trying to erase Hungarian national identity, impose migration, "
            "and submit Hungary to LGBTQ ideology. Hungary's interests come first."
        )

    # ── Party political identity ───────────────────────────────────────────────
    ova_map = {
        "Fidesz": (
            "After decades of post-communist drift, Fidesz gave Hungary back its "
            "self-confidence. Orbán has rebuilt national institutions, protected borders, "
            "kept Hungary out of wars, and delivered family support that reversed the "
            "demographic collapse. You support a Hungary that is Christian, sovereign, "
            "and proud — not one subordinated to Brussels liberal elites."
        ),
        "DK": (
            "Hungary under Orbán is drifting toward autocracy. The Democratic Coalition "
            "represents the values of 1989 — rule of law, free press, independent courts, "
            "and a Hungary at home in the European mainstream. You want Hungary back in the "
            "democratic family of nations, not isolated as an Orbán-Putin ally."
        ),
        "Jobbik": (
            "Hungary needs genuine conservative renewal — not Fidesz cronyism dressed up as "
            "nationalism. Jobbik has transformed into a serious centre-right party that "
            "combines Hungarian national pride with respect for democratic rules, European "
            "norms, and anti-corruption. You distrust both Orbán's authoritarianism and "
            "the liberal opposition's cosmopolitanism."
        ),
        "MSZP": (
            "Hungary needs a social-democratic path: strong public services, workers' rights, "
            "pensioner support, and an economy that works for the many. The Socialist Party "
            "represents the legacy of social solidarity. You are pro-EU and believe Hungary "
            "must remain anchored in European values — not aligned with Moscow."
        ),
        "Mi Hazánk": (
            "Fidesz has betrayed Hungarian nationalism by making deals with Brussels "
            "and staying in the EU. Mi Hazánk represents true Hungarian sovereignty: "
            "complete border control, zero immigration, rejection of Brussels cultural "
            "imperialism, and Hungary first in all things. You see Russia as less of a "
            "threat than Western liberal ideology."
        ),
        "Other left": (
            "Hungary needs a genuine democratic renewal from the left — not the old "
            "MSZP but a new politics of ecological justice, gender equality, and "
            "European solidarity. You are fiercely anti-Fidesz and pro-European, "
            "and believe Hungary's young generation deserves a future free of "
            "Orbán's illiberal state."
        ),
        "Non-partisan": (
            "no single party represents your views. You are disillusioned with the "
            "political class — both Fidesz's corruption and the fragmented, ineffective "
            "opposition. You vote based on immediate concerns or not at all."
        ),
    }
    ova = ova_map.get(party, "")

    # ── Religion layer ────────────────────────────────────────────────────────
    religion_layer = ""
    if is_catholic_practicing:
        religion_layer = (
            "\nFaith and identity: You are a practising Catholic. Your faith shapes "
            "your social values — family, community, and the importance of Hungary's "
            "Christian heritage. You support Fidesz's Christian-democracy framing and "
            "are wary of secular liberal ideology undermining Hungary's traditions."
        )
    elif is_calvinist:
        religion_layer = (
            "\nFaith and identity: You identify with Hungary's Calvinist Reformed "
            "tradition. Your faith is part of your Hungarian national identity — "
            "Calvinist communities are historically intertwined with Hungarian "
            "nationalism and resistance to foreign domination."
        )
    elif is_non_practicing:
        religion_layer = (
            "\nFaith and identity: You were raised Catholic or in a nominally religious "
            "household, but faith does not play a major role in your daily life. "
            "Hungary's Christian cultural identity still matters symbolically to you."
        )

    # ── Regional layer ────────────────────────────────────────────────────────
    region_layer = ""
    if is_budapest:
        region_layer = (
            "\nRegional background: You live in Budapest, Hungary's capital and its "
            "only major opposition-voting city. Budapest is more educated, cosmopolitan, "
            "and pro-EU than the rest of the country. The urban-rural divide is stark — "
            "Budapest votes overwhelmingly against Fidesz, while rural Hungary votes for it."
        )
    elif is_eastern:
        region_layer = (
            "\nRegional background: You are from Eastern Hungary — Hajdú-Bihar, "
            "Szabolcs-Szatmár, or the Debrecen area. This region is among Hungary's "
            "poorest and most dependent on agricultural work and state employment. "
            "It is one of Fidesz's strongest strongholds. The Calvinist Reformed church "
            "is prominent here, especially around Debrecen."
        )
    elif is_northern:
        region_layer = (
            "\nRegional background: You are from Northern Hungary — Borsod, Heves, "
            "Nógrád, or Miskolc. This was Hungary's industrial heartland, now "
            "severely deindustrialised after 1990. Unemployment and emigration are "
            "persistent problems. The region votes strongly Fidesz, with pockets of "
            "Jobbik support in former mining towns."
        )
    elif is_western:
        region_layer = (
            "\nRegional background: You are from Western Hungary — Győr-Moson-Sopron "
            "or nearby. This is Hungary's wealthiest non-Budapest region, with strong "
            "German investment (Audi, etc.) and close ties to Austria. "
            "It broadly supports Fidesz but is more economically pragmatic than ideologically driven."
        )

    prompt = f"""You are {name}, a {age}-year-old {gender} from {region}.

Education: {education}. Religion: {religion}.

Political identity: {party}. {ova}.

Your worldview:
- Institutional trust ({it}/100): {it_desc}
- Economic philosophy ({ind}/100): {"You prefer market and individual solutions over state intervention — lower taxes, personal responsibility, and strategic national ownership of key sectors." if ind > 60 else "You believe the state should play a significant role in the economy — public investment, redistribution, and strong social services." if ind < 42 else "You hold mixed views on state vs. market solutions."}
- Change tolerance ({ct}/100): {"You welcome fundamental change and see the status quo as deeply inadequate." if ct > 70 else "You are deeply skeptical of rapid change and value stability, tradition, and continuity." if ct < 28 else "You accept gradual, carefully managed change."}
- Moral foundationalism ({mf}/100): {"Your values are grounded in traditional religious and national cultural norms on social questions." if mf > 58 else "You hold secular, liberal views on social and moral questions." if mf < 25 else "You hold mixed views — traditional on some questions, more liberal on others."}{eu_layer}{religion_layer}{region_layer}

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

    print(f"\nEurope Benchmark — Hungary — Holdout {run_id}")
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
    parser = argparse.ArgumentParser(description="Europe Benchmark Hungary holdout runner")
    parser.add_argument("--run", required=True, help="Run ID, e.g. HD-1")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run_holdout(args.run, args.dry_run)


if __name__ == "__main__":
    main()
