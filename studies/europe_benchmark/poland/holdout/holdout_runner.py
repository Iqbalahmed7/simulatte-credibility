#!/usr/bin/env python3
"""
holdout_runner.py — Europe Benchmark · Poland holdout validation runner.

Runs only the 4 holdout questions (hd01–hd04) with ZERO topic-specific anchors.
Pure WorldviewAnchor architecture — tests generalisation outside calibration set.

Usage:
    python3 holdout_runner.py --run HD-1
    python3 holdout_runner.py --run HD-1 --dry-run

Protocol: minimum 3 independent runs. Results stable within ±2pp SD = reliable.

Holdout questions (Poland):
    hd01  us_view              — US favorability
    hd02  zelenskyy_confidence — Confidence in Zelenskyy
    hd03  macron_confidence    — Confidence in Macron
    hd04  biden_confidence     — Confidence in Biden

Ground truth: Pew Research Center Global Attitudes, Spring 2024 (Poland N=1,031).
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
    # ── PiS (Law and Justice — conservative-Catholic, nationalist, rural/eastern) ─
    ("pl_p01", "Zygmunt Kamiński",      62, "male",   "Poland (Rzeszów / Podkarpacie)",       "PiS",           "EU-skeptic", "Catholic (practicing)",     "Secondary/lyceum",     2.5),
    ("pl_p02", "Krystyna Wójcik",       58, "female", "Poland (Lublin / Lubelskie)",          "PiS",           "EU-skeptic", "Catholic (practicing)",     "Vocational",           2.5),
    ("pl_p03", "Tadeusz Kowalski",      67, "male",   "Poland (Rzeszów / Podkarpacie)",       "PiS",           "EU-skeptic", "Catholic (practicing)",     "Vocational",           2.5),
    ("pl_p04", "Halina Szymańska",      55, "female", "Poland (Łódź / Łódź Province)",        "PiS",           "EU-skeptic", "Catholic (practicing)",     "Secondary/lyceum",     2.5),
    ("pl_p05", "Ryszard Dąbrowski",     60, "male",   "Poland (Katowice / Silesia)",          "PiS",           "EU-skeptic", "Catholic (practicing)",     "Vocational",           2.5),
    ("pl_p06", "Bożena Woźniak",        52, "female", "Poland (Lublin / Lubelskie)",          "PiS",           "EU-skeptic", "Catholic (practicing)",     "Secondary/lyceum",     2.0),
    ("pl_p07", "Mirosław Kowalczyk",    64, "male",   "Poland (Rzeszów / Podkarpacie)",       "PiS",           "EU-skeptic", "Catholic (practicing)",     "Vocational",           2.5),

    # ── PO/KO (Civic Coalition — pro-EU, urban, educated, liberal) ───────────
    ("pl_p08", "Agnieszka Wiśniewska",  41, "female", "Poland (Warsaw / Mazowsze)",           "PO/KO",         "Pro-EU",     "Catholic (non-practicing)", "University",           2.0),
    ("pl_p09", "Piotr Lewandowski",     38, "male",   "Poland (Warsaw / Mazowsze)",           "PO/KO",         "Pro-EU",     "Secular/none",              "University",           2.0),
    ("pl_p10", "Monika Zielińska",      45, "female", "Poland (Kraków / Małopolska)",         "PO/KO",         "Pro-EU",     "Catholic (non-practicing)", "University",           2.0),
    ("pl_p11", "Marcin Wiśniewski",     35, "male",   "Poland (Gdańsk / Pomerania)",          "PO/KO",         "Pro-EU",     "Secular/none",              "University",           2.0),
    ("pl_p12", "Joanna Kamińska",       48, "female", "Poland (Wrocław / Lower Silesia)",     "PO/KO",         "Pro-EU",     "Catholic (non-practicing)", "University",           2.0),
    ("pl_p13", "Tomasz Dąbrowski",      52, "male",   "Poland (Poznań / Wielkopolska)",       "PO/KO",         "Pro-EU",     "Catholic (non-practicing)", "University",           2.0),
    ("pl_p14", "Katarzyna Lewandowska", 33, "female", "Poland (Warsaw / Mazowsze)",           "PO/KO",         "Pro-EU",     "Secular/none",              "University",           2.0),
    ("pl_p15", "Wojciech Szymański",    44, "male",   "Poland (Kraków / Małopolska)",         "PO/KO",         "Pro-EU",     "Catholic (non-practicing)", "Secondary/lyceum",     2.0),

    # ── Lewica (Left / SLD — secular, urban, younger, social-democratic) ─────
    ("pl_p16", "Natalia Kowalska",      29, "female", "Poland (Warsaw / Mazowsze)",           "Lewica",        "Pro-EU",     "Secular/none",              "University",           2.5),
    ("pl_p17", "Damian Woźniak",        34, "male",   "Poland (Wrocław / Lower Silesia)",     "Lewica",        "Pro-EU",     "Secular/none",              "University",           2.5),
    ("pl_p18", "Ewa Zielińska",         38, "female", "Poland (Warsaw / Mazowsze)",           "Lewica",        "Pro-EU",     "Secular/none",              "Secondary/lyceum",     2.0),
    ("pl_p19", "Jakub Kowalczyk",       27, "male",   "Poland (Poznań / Wielkopolska)",       "Lewica",        "Pro-EU",     "Secular/none",              "University",           2.5),

    # ── TD (Third Way / Trzecia Droga — agrarian-centrist, rural, moderate) ──
    ("pl_p20", "Stanisław Kamiński",    54, "male",   "Poland (Lublin / Lubelskie)",          "TD",            "Pro-EU",     "Catholic (practicing)",     "Secondary/lyceum",     2.5),
    ("pl_p21", "Grażyna Wójcik",        49, "female", "Poland (Rzeszów / Podkarpacie)",       "TD",            "Pro-EU",     "Catholic (practicing)",     "Secondary/lyceum",     2.5),
    ("pl_p22", "Henryk Kowalski",       57, "male",   "Poland (Łódź / Łódź Province)",        "TD",            "Pro-EU",     "Catholic (practicing)",     "Vocational",           2.5),

    # ── Konfederacja (nationalist-libertarian, anti-EU, anti-establishment) ──
    ("pl_p23", "Bartosz Wiśniewski",    28, "male",   "Poland (Warsaw / Mazowsze)",           "Konfederacja",  "EU-skeptic", "Catholic (non-practicing)", "University",           2.5),
    ("pl_p24", "Krzysztof Dąbrowski",   32, "male",   "Poland (Kraków / Małopolska)",         "Konfederacja",  "EU-skeptic", "Secular/none",              "University",           2.5),
    ("pl_p25", "Radosław Szymański",    36, "male",   "Poland (Gdańsk / Pomerania)",          "Konfederacja",  "EU-skeptic", "Secular/none",              "Secondary/lyceum",     2.0),

    # ── Non-partisan / disengaged (cross-cutting, rural/semi-urban, Catholic) ─
    ("pl_p26", "Józef Kowalczyk",       61, "male",   "Poland (Rzeszów / Podkarpacie)",       "Non-partisan",  "EU-skeptic", "Catholic (practicing)",     "Vocational",           2.5),
    ("pl_p27", "Teresa Lewandowska",    55, "female", "Poland (Lublin / Lubelskie)",          "Non-partisan",  "EU-skeptic", "Catholic (practicing)",     "Vocational",           2.5),
    ("pl_p28", "Andrzej Kamiński",      48, "male",   "Poland (Katowice / Silesia)",          "Non-partisan",  "EU-skeptic", "Catholic (non-practicing)", "Secondary/lyceum",     2.5),
    ("pl_p29", "Maria Woźniak",         63, "female", "Poland (Łódź / Łódź Province)",        "Non-partisan",  "EU-skeptic", "Catholic (practicing)",     "Vocational",           2.5),
    ("pl_p30", "Sławomir Wiśniewski",   43, "male",   "Poland (Katowice / Silesia)",          "Non-partisan",  "EU-skeptic", "Catholic (non-practicing)", "Secondary/lyceum",     2.5),
    ("pl_p31", "Irena Dąbrowska",       59, "female", "Poland (Kraków / Małopolska)",         "Non-partisan",  "Pro-EU",     "Catholic (practicing)",     "Secondary/lyceum",     2.5),
    ("pl_p32", "Władysław Kowalski",    71, "male",   "Poland (Rzeszów / Podkarpacie)",       "Non-partisan",  "EU-skeptic", "Catholic (practicing)",     "Vocational",           2.5),
    ("pl_p33", "Elżbieta Szymańska",    46, "female", "Poland (Gdańsk / Pomerania)",          "Non-partisan",  "Pro-EU",     "Catholic (non-practicing)", "Secondary/lyceum",     2.0),
    ("pl_p34", "Leszek Wójcik",         53, "male",   "Poland (Wrocław / Lower Silesia)",     "Non-partisan",  "Pro-EU",     "Catholic (non-practicing)", "Secondary/lyceum",     2.0),
    ("pl_p35", "Alicja Lewandowska",    37, "female", "Poland (Warsaw / Mazowsze)",           "Non-partisan",  "Pro-EU",     "Secular/none",              "University",           2.0),
    ("pl_p36", "Czesław Kowalczyk",     66, "male",   "Poland (Lublin / Lubelskie)",          "Non-partisan",  "EU-skeptic", "Catholic (practicing)",     "Vocational",           2.5),
    ("pl_p37", "Dorota Kamińska",       42, "female", "Poland (Poznań / Wielkopolska)",       "Non-partisan",  "Pro-EU",     "Catholic (non-practicing)", "Secondary/lyceum",     2.0),
    ("pl_p38", "Roman Wiśniewski",      69, "male",   "Poland (Łódź / Łódź Province)",        "Non-partisan",  "EU-skeptic", "Catholic (practicing)",     "Vocational",           2.5),
    ("pl_p39", "Beata Dąbrowska",       31, "female", "Poland (Warsaw / Mazowsze)",           "Non-partisan",  "Pro-EU",     "Secular/none",              "University",           2.0),
    ("pl_p40", "Grzegorz Szymański",    57, "male",   "Poland (Katowice / Silesia)",          "Non-partisan",  "EU-skeptic", "Catholic (non-practicing)", "Secondary/lyceum",     2.5),
]

WORLDVIEW = {
    # id:        (IT,  IND, CT,  MF)
    "pl_p01": (58,  58,  20,  78),
    "pl_p02": (55,  55,  18,  80),
    "pl_p03": (52,  56,  15,  82),
    "pl_p04": (56,  57,  22,  75),
    "pl_p05": (54,  58,  20,  72),
    "pl_p06": (60,  60,  25,  70),
    "pl_p07": (53,  55,  18,  80),
    "pl_p08": (68,  58,  60,  30),
    "pl_p09": (65,  62,  65,  15),
    "pl_p10": (62,  60,  58,  32),
    "pl_p11": (66,  63,  62,  14),
    "pl_p12": (64,  60,  60,  28),
    "pl_p13": (60,  58,  55,  35),
    "pl_p14": (70,  62,  68,  10),
    "pl_p15": (58,  56,  55,  38),
    "pl_p16": (55,  30,  78,  12),
    "pl_p17": (52,  32,  75,  10),
    "pl_p18": (50,  35,  72,  14),
    "pl_p19": (54,  28,  80,  10),
    "pl_p20": (55,  52,  42,  68),
    "pl_p21": (52,  50,  40,  70),
    "pl_p22": (50,  52,  38,  65),
    "pl_p23": (28,  80,  38,  42),
    "pl_p24": (25,  78,  40,  32),
    "pl_p25": (30,  75,  42,  28),
    "pl_p26": (45,  52,  22,  75),
    "pl_p27": (42,  50,  20,  78),
    "pl_p28": (48,  55,  28,  58),
    "pl_p29": (40,  48,  18,  80),
    "pl_p30": (45,  54,  30,  55),
    "pl_p31": (55,  52,  45,  70),
    "pl_p32": (38,  50,  16,  82),
    "pl_p33": (58,  55,  52,  42),
    "pl_p34": (56,  55,  50,  40),
    "pl_p35": (62,  58,  65,  12),
    "pl_p36": (38,  50,  18,  80),
    "pl_p37": (58,  56,  55,  38),
    "pl_p38": (35,  48,  16,  82),
    "pl_p39": (62,  58,  68,  12),
    "pl_p40": (44,  54,  28,  55),
}


def build_system_prompt(persona: tuple) -> str:
    """Pure WorldviewAnchor prompt — zero topic-specific anchors."""
    pid, name, age, gender, region, party, eu_ref, religion, education, weight = persona
    it, ind, ct, mf = WORLDVIEW[pid]

    is_warsaw        = "Warsaw" in region or "Mazowsze" in region
    is_krakow        = "Kraków" in region or "Małopolska" in region
    is_gdansk        = "Gdańsk" in region or "Pomerania" in region
    is_east          = "Podkarpacie" in region or "Lublin" in region or "Lubelskie" in region
    is_silesia       = "Silesia" in region or "Katowice" in region
    is_eu_skeptic    = eu_ref == "EU-skeptic"
    is_practicing    = "practicing" in religion and "non" not in religion
    is_nonpracticing = "non-practicing" in religion
    is_secular       = "Secular" in religion or "none" in religion

    # ── Institutional trust descriptor ────────────────────────────────────────
    if it < 35:
        it_desc = (
            "You have very low trust in Polish institutions — the state, the courts, "
            "the media. You feel the political class governs for party interests and "
            "EU bureaucrats, not for ordinary Polish people."
        )
    elif it < 52:
        it_desc = (
            "You have mixed trust in Polish institutions. You see deep polarisation and "
            "dysfunction — years of PiS rule eroded checks and balances, and the new "
            "coalition is still proving itself. You're cautiously watchful."
        )
    elif it < 65:
        it_desc = (
            "You have moderate trust in Polish institutions. You broadly believe in "
            "democratic norms and the rule of law, even if the system has been "
            "strained by political conflict in recent years."
        )
    else:
        it_desc = (
            "You have high trust in Polish institutions — the rule of law, independent "
            "courts, free media, and European integration matter deeply to you. "
            "The Tusk-led coalition restoration of democratic standards is important to you."
        )

    # ── EU/Europe layer ────────────────────────────────────────────────────────
    if not is_eu_skeptic:
        eu_layer = (
            "\nEurope: You are broadly pro-European. After years of PiS conflicts with "
            "Brussels over rule-of-law, you are relieved that Poland is back in good "
            "standing with the EU. EU funds, freedom of movement, and collective security "
            "matter enormously to you. You see EU membership as a guarantee of Poland's "
            "democratic future and protection against Russian pressure."
        )
    else:
        eu_layer = (
            "\nEurope: You are skeptical of the EU. You feel Brussels imposes regulations "
            "that undermine Polish sovereignty and Christian values. You believe Poland "
            "should benefit from EU funds while pushing back on ideological impositions "
            "around gender, migration quotas, or judicial oversight. "
            "Sovereignty comes first."
        )

    # ── Party political identity ───────────────────────────────────────────────
    ova_map = {
        "PiS": (
            "Poland was strongest under PiS — 500+ child benefit, coal miners protected, "
            "Catholic values defended, and Poland stood up to Brussels. Kaczyński's Law "
            "and Justice party put ordinary Polish families first and refused to bow to "
            "EU ideology on migration and family values. You believe the 2023 election "
            "result was influenced by biased media, and that Tusk's coalition is "
            "dismantling Polish sovereignty and attacking the Church."
        ),
        "PO/KO": (
            "Poland's future lies in strong EU integration, rule of law, and a modern "
            "democratic society. Tusk's Civic Coalition represents a return to normalcy "
            "after eight years of PiS judicial takeovers, media capture, and EU isolation. "
            "You are pro-European, pro-NATO, and believe Poland should be a trusted partner "
            "in the Western alliance — not an autocratic outlier. The 2023 election was a "
            "democratic victory for Polish civil society."
        ),
        "Lewica": (
            "Poland needs secular, progressive values — separation of Church and state, "
            "women's reproductive rights, LGBT equality, and a strong welfare state. "
            "The left-wing Lewica coalition represents those left behind by both PiS "
            "Catholic nationalism and PO's market liberalism. You support the Tusk "
            "coalition but push it to be bolder on social rights and inequality."
        ),
        "TD": (
            "Rural Poland and small-town communities need a voice between the extremes. "
            "Trzecia Droga (Third Way) — the PSL/Poland 2050 coalition — represents "
            "agrarian interests, Catholic values, and EU pragmatism without either "
            "PiS radicalism or urban liberal ideology. You want EU funds for farmers, "
            "decent public services, and a Poland that is Catholic, sovereign, and "
            "part of a reformed Europe."
        ),
        "Konfederacja": (
            "The entire political establishment — both PiS and the Tusk coalition — "
            "serves the state, the EU, and globalist interests over individual freedom. "
            "Konfederacja represents true national sovereignty, low taxes, minimal state, "
            "and resistance to EU federalism, mass immigration, and gender ideology. "
            "You are anti-socialist, anti-EU-federalism, and deeply suspicious of both "
            "NATO bureaucracy and George Soros-funded NGOs reshaping Polish society."
        ),
        "Non-partisan": (
            "no single party represents your views. You are disillusioned with the "
            "political class as a whole — both PiS and the Tusk coalition feel like "
            "they serve themselves. You vote based on immediate concerns or not at all."
        ),
    }
    ova = ova_map.get(party, "")

    # ── Religion layer ────────────────────────────────────────────────────────
    religion_layer = ""
    if is_practicing:
        religion_layer = (
            "\nFaith and identity: You are a practising Catholic. Your faith is central "
            "to your identity and values — Mass on Sunday, the Church calendar structuring "
            "your year, and moral teachings shaping your views on family, life, and society. "
            "Poland's Catholic identity is precious to you and you resist secularisation "
            "imposed from the West. The Church is not perfect but it is the backbone of "
            "Polish national identity and should not be attacked by the state."
        )
    elif is_nonpracticing:
        religion_layer = (
            "\nFaith and identity: You were raised Catholic and identify culturally with "
            "the Church, though you don't attend Mass regularly. Catholic traditions, "
            "Christmas, Easter, and national-religious holidays matter to you as cultural "
            "touchstones even if your personal faith is not strong."
        )
    elif is_secular:
        religion_layer = (
            "\nFaith and identity: You are secular and non-religious. You support a "
            "clear separation of Church and state. You believe the Catholic Church has "
            "had too much political influence in Poland — over education, abortion law, "
            "and civil rights — and welcome a more pluralist, secular public sphere."
        )

    # ── Regional layer ────────────────────────────────────────────────────────
    region_layer = ""
    if is_east:
        region_layer = (
            "\nRegional background: You are from eastern Poland (Podkarpacie or Lublin "
            "region) — this is PiS's heartland: deeply Catholic, rural, historically "
            "shaped by Soviet occupation, and closer to the Ukrainian and Belarusian "
            "borders. Russia is not an abstraction; it is an existential neighbour. "
            "EU structural funds have helped the region but local identity remains "
            "conservative and Catholic."
        )
    elif is_warsaw:
        region_layer = (
            "\nRegional background: You live in Warsaw or the Mazowsze metro area — "
            "Poland's economic and political capital. You are part of an educated, "
            "internationally connected professional class. Warsaw voted overwhelmingly "
            "for Tusk's coalition in 2023. You are pro-EU, cosmopolitan, and follow "
            "European affairs closely."
        )
    elif is_gdansk:
        region_layer = (
            "\nRegional background: You are from Gdańsk and Pomerania — the birthplace "
            "of Solidarity and Lech Wałęsa. This is a historically liberal, pro-EU "
            "region with strong maritime and trade traditions. Tusk himself is from "
            "here. You are proud of Solidarity's legacy and fiercely pro-democratic."
        )
    elif is_silesia:
        region_layer = (
            "\nRegional background: You are from Silesia (Katowice region) — Poland's "
            "industrial heartland with a distinct regional identity. The region is "
            "economically transitioning away from coal mining. Silesia has historically "
            "split its vote; you reflect that pragmatic, working-class tradition."
        )

    prompt = f"""You are {name}, a {age}-year-old {gender} from {region}, Poland.

Education: {education}. Religion: {religion}.

Political identity: {party}. {ova}.

Your worldview:
- Institutional trust ({it}/100): {it_desc}
- Economic philosophy ({ind}/100): {"You prefer market and individual solutions over state intervention — lower taxes, less regulation, personal responsibility." if ind > 65 else "You believe the state should play a significant role in the economy — social transfers, redistribution, and strong public services." if ind < 42 else "You hold mixed views on state vs. market solutions."}
- Change tolerance ({ct}/100): {"You welcome fundamental change and see the status quo as deeply inadequate." if ct > 70 else "You are deeply skeptical of rapid change and value stability, tradition, and continuity." if ct < 28 else "You accept gradual, carefully managed change."}
- Moral foundationalism ({mf}/100): {"Your values are strongly grounded in Catholic moral teaching and Polish Christian tradition on social questions." if mf > 58 else "You hold secular, liberal views on social and moral questions — Church should stay out of politics." if mf < 25 else "You hold mixed views — traditional on some questions, more liberal on others."}{eu_layer}{religion_layer}{region_layer}

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

    print(f"\nEurope Benchmark — Poland — Holdout {run_id}")
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
        "batch_id": batch_id,
        "model": MODEL_ID,
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
    parser = argparse.ArgumentParser(description="Europe Benchmark Poland holdout runner")
    parser.add_argument("--run", required=True, help="Run ID, e.g. HD-1")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run_holdout(args.run, args.dry_run)


if __name__ == "__main__":
    main()
