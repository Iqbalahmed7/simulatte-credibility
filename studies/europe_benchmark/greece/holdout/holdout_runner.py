#!/usr/bin/env python3
"""
holdout_runner.py — Europe Benchmark · Greece holdout validation runner.

Runs only the 5 holdout questions (hd01–hd05) with ZERO topic-specific anchors.
Pure WorldviewAnchor architecture — tests generalisation outside calibration set.

Usage:
    python3 holdout_runner.py --run HD-1
    python3 holdout_runner.py --run HD-1 --dry-run

Protocol: minimum 3 independent runs. Results stable within ±2pp SD = reliable.

Holdout questions (Greece):
    hd01  us_view              — US favorability
    hd02  un_view              — UN favorability
    hd03  zelenskyy_confidence — Confidence in Zelenskyy
    hd04  macron_confidence    — Confidence in Macron
    hd05  children_future      — Optimism for children's future

Ground truth: Pew Research Center Global Attitudes, Spring 2024 (Greece N=~1,000).
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
    _env_file = Path(__file__).resolve().parent.parent / ".env"  # greece/.env fallback
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
    # ── ND (New Democracy — centre-right, pro-EU, Mitsotakis, Orthodox) ─────────
    ("gr_p01", "Nikos Papadopoulos",    58, "male",   "Greece (Athens / Attica)",           "ND",             "Pro-EU",     "Greek Orthodox (practicing)",     "University",        2.5),
    ("gr_p02", "Maria Christodoulou",   51, "female", "Greece (Athens / Attica)",           "ND",             "Pro-EU",     "Greek Orthodox (practicing)",     "University",        2.5),
    ("gr_p03", "Giorgos Alexiou",       64, "male",   "Greece (Thessaloniki / Macedonia)",  "ND",             "Pro-EU",     "Greek Orthodox (practicing)",     "University",        2.5),
    ("gr_p04", "Eleni Stavrakis",       45, "female", "Greece (Peloponnese / Rural)",       "ND",             "Pro-EU",     "Greek Orthodox (practicing)",     "Lyceum",            2.5),
    ("gr_p05", "Petros Mantzaros",      62, "male",   "Greece (Athens / Attica)",           "ND",             "Pro-EU",     "Greek Orthodox (non-practicing)", "University",        2.5),
    ("gr_p06", "Sophia Karageorgiou",   41, "female", "Greece (Athens / Attica)",           "ND",             "Pro-EU",     "Greek Orthodox (non-practicing)", "University",        2.0),
    ("gr_p07", "Konstantinos Theodorou",55, "male",   "Greece (Crete / Islands)",           "ND",             "Pro-EU",     "Greek Orthodox (practicing)",     "Lyceum",            2.5),

    # ── SYRIZA (populist left, austerity-scarred, Tsipras) ─────────────────────
    ("gr_p08", "Andreas Dimitriou",     43, "male",   "Greece (Athens / Attica)",           "SYRIZA",         "EU-skeptic", "Greek Orthodox (non-practicing)", "University",        2.5),
    ("gr_p09", "Katerina Papadaki",     37, "female", "Greece (Athens / Attica)",           "SYRIZA",         "EU-skeptic", "Non-religious/secular",           "University",        2.5),
    ("gr_p10", "Vangelis Makris",       50, "male",   "Greece (Thessaloniki / Macedonia)",  "SYRIZA",         "EU-skeptic", "Greek Orthodox (non-practicing)", "Lyceum",            2.5),
    ("gr_p11", "Ioanna Nikolaou",       32, "female", "Greece (Athens / Attica)",           "SYRIZA",         "EU-skeptic", "Non-religious/secular",           "University",        2.0),
    ("gr_p12", "Stavros Karagiannis",   47, "male",   "Greece (Larissa / Thessaly)",        "SYRIZA",         "EU-skeptic", "Greek Orthodox (non-practicing)", "Vocational",        2.5),

    # ── KKE (Communist — anti-NATO, working class, anti-establishment) ──────────
    ("gr_p13", "Dimitris Papadimitriou",56, "male",   "Greece (Piraeus / Attica)",          "KKE",            "EU-skeptic", "Non-religious/secular",           "Vocational",        2.5),
    ("gr_p14", "Eleftheria Kostopoulou",49, "female", "Greece (Patras / Peloponnese)",      "KKE",            "EU-skeptic", "Non-religious/secular",           "Lyceum",            2.5),
    ("gr_p15", "Manolis Sfakianakis",   61, "male",   "Greece (Thessaloniki / Macedonia)",  "KKE",            "EU-skeptic", "Non-religious/secular",           "Vocational",        2.5),

    # ── Greek Solution (nationalist, Orthodox, anti-immigration, Velopoulos) ───
    ("gr_p16", "Takis Vetoulas",        52, "male",   "Greece (Athens / Attica)",           "Greek Solution", "EU-skeptic", "Greek Orthodox (practicing)",     "Lyceum",            2.5),
    ("gr_p17", "Chrysanthi Balatsouras",58, "female", "Greece (Peloponnese / Rural)",       "Greek Solution", "EU-skeptic", "Greek Orthodox (practicing)",     "Vocational",        2.5),
    ("gr_p18", "Apostolos Tsakiris",    65, "male",   "Greece (Northern Greece / Epirus)",  "Greek Solution", "EU-skeptic", "Greek Orthodox (practicing)",     "Vocational",        2.5),

    # ── Spartans (far-right, anti-immigrant, very low IT) ──────────────────────
    ("gr_p19", "Lefteris Drakopoulos",  44, "male",   "Greece (Athens / Attica)",           "Spartans",       "EU-skeptic", "Greek Orthodox (practicing)",     "Lyceum",            2.0),
    ("gr_p20", "Theodoros Samaras",     38, "male",   "Greece (Thessaloniki / Macedonia)",  "Spartans",       "EU-skeptic", "Greek Orthodox (practicing)",     "Vocational",        2.0),

    # ── PASOK-KINAL (social-democrat, moderate, pro-EU) ─────────────────────────
    ("gr_p21", "Zoe Papantoniou",       48, "female", "Greece (Athens / Attica)",           "PASOK",          "Pro-EU",     "Greek Orthodox (non-practicing)", "University",        2.5),
    ("gr_p22", "Michalis Georgiadis",   55, "male",   "Greece (Athens / Attica)",           "PASOK",          "Pro-EU",     "Greek Orthodox (non-practicing)", "University",        2.5),
    ("gr_p23", "Anna Spyropoulou",      42, "female", "Greece (Thessaloniki / Macedonia)",  "PASOK",          "Pro-EU",     "Greek Orthodox (non-practicing)", "Lyceum",            2.5),
    ("gr_p24", "Nektarios Adamopoulos", 60, "male",   "Greece (Patras / Peloponnese)",      "PASOK",          "Pro-EU",     "Greek Orthodox (non-practicing)", "Lyceum",            2.5),

    # ── Non-partisan / disengaged ────────────────────────────────────────────────
    ("gr_p25", "Giorgos Tsoukalas",     59, "male",   "Greece (Athens / Attica)",           "Non-partisan",   "EU-skeptic", "Greek Orthodox (non-practicing)", "Vocational",        2.5),
    ("gr_p26", "Despina Lamprou",       46, "female", "Greece (Athens / Attica)",           "Non-partisan",   "EU-skeptic", "Greek Orthodox (non-practicing)", "Lyceum",            2.5),
    ("gr_p27", "Kostas Haralambidis",   67, "male",   "Greece (Northern Greece / Epirus)",  "Non-partisan",   "EU-skeptic", "Greek Orthodox (practicing)",     "Vocational",        2.5),
    ("gr_p28", "Irini Papadopoulou",    34, "female", "Greece (Athens / Attica)",           "Non-partisan",   "Pro-EU",     "Non-religious/secular",           "University",        2.0),
    ("gr_p29", "Stelios Karamanlis",    71, "male",   "Greece (Peloponnese / Rural)",       "Non-partisan",   "EU-skeptic", "Greek Orthodox (practicing)",     "Vocational",        2.5),
    ("gr_p30", "Fotini Alexaki",        39, "female", "Greece (Crete / Islands)",           "Non-partisan",   "Pro-EU",     "Greek Orthodox (non-practicing)", "Lyceum",            2.5),
    ("gr_p31", "Panagiotis Lekkas",     53, "male",   "Greece (Piraeus / Attica)",          "Non-partisan",   "EU-skeptic", "Greek Orthodox (non-practicing)", "Vocational",        2.5),
    ("gr_p32", "Maria Triantafyllou",   29, "female", "Greece (Athens / Attica)",           "Non-partisan",   "Pro-EU",     "Non-religious/secular",           "University",        2.0),
    ("gr_p33", "Alexandros Mitsopoulos",63, "male",   "Greece (Thessaloniki / Macedonia)",  "Non-partisan",   "EU-skeptic", "Greek Orthodox (non-practicing)", "Lyceum",            2.5),
    ("gr_p34", "Thekla Roussou",        44, "female", "Greece (Athens / Attica)",           "Non-partisan",   "EU-skeptic", "Greek Orthodox (non-practicing)", "Lyceum",            2.5),
    ("gr_p35", "Vasilis Economou",      57, "male",   "Greece (Larissa / Thessaly)",        "Non-partisan",   "EU-skeptic", "Greek Orthodox (practicing)",     "Vocational",        2.5),
    ("gr_p36", "Chrysoula Andreou",     35, "female", "Greece (Athens / Attica)",           "Non-partisan",   "Pro-EU",     "Greek Orthodox (non-practicing)", "University",        2.0),
    ("gr_p37", "Nikos Stavros",         68, "male",   "Greece (Northern Greece / Epirus)",  "Non-partisan",   "EU-skeptic", "Greek Orthodox (practicing)",     "Vocational",        2.5),
    ("gr_p38", "Eleni Karali",          40, "female", "Greece (Crete / Islands)",           "Non-partisan",   "EU-skeptic", "Greek Orthodox (non-practicing)", "Lyceum",            2.5),
    ("gr_p39", "Theodoros Papadakis",   26, "male",   "Greece (Athens / Attica)",           "Non-partisan",   "Pro-EU",     "Non-religious/secular",           "University",        2.0),
    ("gr_p40", "Varvara Nikolopoulou",  72, "female", "Greece (Peloponnese / Rural)",       "Non-partisan",   "EU-skeptic", "Greek Orthodox (practicing)",     "Vocational",        2.5),
]

# ── WorldviewAnchor values ────────────────────────────────────────────────────
WORLDVIEW = {
    # id:        (IT,  IND, CT,  MF)

    # ND — moderate-high IT, high IND, low CT, high MF (Orthodox practicing)
    "gr_p01": (62,  65,  28,  68),
    "gr_p02": (60,  63,  30,  70),
    "gr_p03": (58,  62,  25,  72),
    "gr_p04": (55,  60,  22,  75),
    "gr_p05": (64,  68,  32,  38),
    "gr_p06": (60,  70,  35,  32),
    "gr_p07": (52,  58,  20,  70),

    # SYRIZA — low-moderate IT, very low IND, high CT, low-moderate MF
    "gr_p08": (35,  22,  72,  32),
    "gr_p09": (32,  20,  78,  12),
    "gr_p10": (38,  24,  68,  35),
    "gr_p11": (28,  18,  82,  10),
    "gr_p12": (40,  26,  62,  38),

    # KKE — very low IT, very low IND, high CT, very low MF (secular)
    "gr_p13": (25,  15,  75,  12),
    "gr_p14": (28,  18,  72,  15),
    "gr_p15": (22,  14,  78,  10),

    # Greek Solution — low IT, moderate-low IND, very low CT, very high MF
    "gr_p16": (30,  40,  15,  78),
    "gr_p17": (28,  38,  12,  80),
    "gr_p18": (25,  35,  10,  82),

    # Spartans — very low IT, low IND, very low CT, high MF (far-right)
    "gr_p19": (18,  32,  10,  72),
    "gr_p20": (15,  30,  8,   75),

    # PASOK — moderate IT, low-moderate IND, moderate CT, moderate MF
    "gr_p21": (48,  38,  55,  35),
    "gr_p22": (45,  40,  52,  38),
    "gr_p23": (42,  36,  50,  40),
    "gr_p24": (40,  38,  45,  45),

    # Non-partisan — wide spread; austerity-disillusioned majority are low IT
    "gr_p25": (22,  45,  20,  42),
    "gr_p26": (28,  42,  22,  38),
    "gr_p27": (20,  40,  15,  72),
    "gr_p28": (58,  55,  68,  12),
    "gr_p29": (18,  38,  12,  75),
    "gr_p30": (50,  48,  58,  42),
    "gr_p31": (24,  44,  18,  40),
    "gr_p32": (62,  58,  72,  10),
    "gr_p33": (26,  42,  24,  42),
    "gr_p34": (30,  40,  28,  38),
    "gr_p35": (20,  38,  16,  68),
    "gr_p36": (55,  52,  62,  18),
    "gr_p37": (18,  36,  12,  72),
    "gr_p38": (32,  44,  30,  40),
    "gr_p39": (60,  60,  70,  8),
    "gr_p40": (15,  35,  10,  78),
}


def build_system_prompt(persona: tuple) -> str:
    """Pure WorldviewAnchor prompt — zero topic-specific anchors."""
    pid, name, age, gender, region, party, eu_ref, religion, education, weight = persona
    it, ind, ct, mf = WORLDVIEW[pid]

    is_athens               = "Athens" in region or "Attica" in region or "Piraeus" in region
    is_thessaloniki         = "Thessaloniki" in region or "Macedonia" in region
    is_rural                = "Rural" in region or "Peloponnese" in region or "Epirus" in region or "Thessaly" in region
    is_island               = "Crete" in region or "Islands" in region
    is_eu_skeptic           = eu_ref == "EU-skeptic"
    is_pro_eu               = eu_ref == "Pro-EU"
    is_orthodox_practicing  = "practicing" in religion and "non" not in religion
    is_orthodox_non_practicing = "non-practicing" in religion
    is_secular              = "Non-religious" in religion or "secular" in religion

    # ── Institutional trust descriptor ────────────────────────────────────────
    if it < 30:
        it_desc = (
            "You have extremely low trust in Greek institutions — the political system, "
            "media, and Brussels. The austerity memoranda destroyed your confidence in "
            "any establishment party. You feel the entire political class — from ND to "
            "SYRIZA — has failed ordinary Greek people and serves foreign creditors."
        )
    elif it < 45:
        it_desc = (
            "You have very low trust in Greek institutions. The sovereign debt crisis "
            "and years of austerity left deep scars. You are deeply cynical about "
            "politicians and institutions but still participate in democracy, however reluctantly."
        )
    elif it < 58:
        it_desc = (
            "You have mixed trust in Greek institutions. You see real dysfunction and "
            "post-austerity disillusionment, but believe reform is possible and that "
            "democratic institutions are worth preserving."
        )
    else:
        it_desc = (
            "You have moderate-to-high trust in Greek institutions. You believe the "
            "democratic system and EU membership, despite their flaws, provide stability "
            "and a path forward for Greece."
        )

    # ── EU/Europe layer ────────────────────────────────────────────────────────
    if is_pro_eu:
        eu_layer = (
            "\nEurope: You are broadly pro-European. Despite the painful austerity "
            "conditionality of the memoranda era, you believe EU membership provides "
            "Greece with stability, access to markets, and a geopolitical anchor. "
            "A Greece outside the EU would be far more vulnerable."
        )
    else:
        eu_layer = (
            "\nEurope: You are deeply ambivalent or hostile toward the EU. The "
            "memoranda imposed by the Troika (EU/ECB/IMF) destroyed livelihoods and "
            "humiliated Greek sovereignty. You believe Brussels serves German and "
            "Northern European interests, not Greece's. A different relationship — "
            "or exit — would be preferable."
        )

    # ── Austerity trauma layer ─────────────────────────────────────────────────
    if it < 40:
        austerity_layer = (
            "\nAusterity trauma: The sovereign debt crisis (2010–2018) shaped your "
            "political consciousness profoundly. You or people close to you experienced "
            "wage cuts, pension slashes, unemployment, and brain drain. You regard the "
            "memoranda as an externally imposed catastrophe and deeply distrust "
            "anyone who supported or implemented them."
        )
    elif it < 55:
        austerity_layer = (
            "\nAusterity trauma: The debt crisis was traumatic for Greece and left "
            "lasting scars — on public services, on pensions, on social trust. "
            "You haven't forgotten, but you're trying to look forward."
        )
    else:
        austerity_layer = ""

    # ── Party political identity ───────────────────────────────────────────────
    ova_map = {
        "ND": (
            "Greece needs responsible, pro-European governance that restores competitiveness, "
            "attracts investment, and provides security. Mitsotakis's New Democracy represents "
            "modern centre-right governance: lower taxes, stronger rule of law, EU alignment, "
            "and firm handling of migration. You believe Greece's future is in Europe, "
            "not in anti-memorandum populism or communist nostalgia."
        ),
        "SYRIZA": (
            "The memoranda destroyed a generation's future while the wealthy were protected. "
            "SYRIZA and Tsipras represented the first real challenge to the post-junta "
            "establishment. You believe in economic justice, public investment, and pushing "
            "back against austerity ideology. You are deeply critical of the ND establishment "
            "and the Troika but also disillusioned by SYRIZA's capitulation in 2015."
        ),
        "KKE": (
            "Capitalism and the EU are the root cause of Greece's crisis. The Greek Communist "
            "Party (KKE) is the only force that refuses to participate in the system's logic. "
            "You want nationalisation of key industries, exit from NATO, and a planned economy "
            "that serves working people — not the Troika, not ND, not the reformist left. "
            "Both the EU and NATO are instruments of imperialist power."
        ),
        "Greek Solution": (
            "Greece has been sold out — by SYRIZA to the Troika, by ND to Brussels, "
            "and by a political class that allows mass immigration to destroy Greek culture. "
            "Kyriakos Velopoulos and Greek Solution stand for Greek sovereignty, "
            "Orthodox Christian values, and a firm hand on immigration. "
            "You are a Greek patriot who will not accept the erasure of Hellenic civilisation."
        ),
        "Spartans": (
            "no mainstream party is willing to say what ordinary Greeks know: immigration "
            "is destroying Greek society, the EU is a foreign occupier in disguise, and "
            "the political class is corrupt to its core. The Spartans are the only "
            "movement willing to defend Greek identity without compromise. "
            "You have contempt for the entire establishment — left, right, and centre."
        ),
        "PASOK": (
            "Social democracy — strong public services, workers' rights, and a social Europe — "
            "is Greece's best path forward. PASOK-KINAL stands for the moderate, reformist "
            "centre-left: pro-EU but critical of austerity dogma, committed to the rule of "
            "law, and focused on rebuilding Greece's social contract after the crisis years."
        ),
        "Non-partisan": (
            "no single party represents your views. The political class across the spectrum "
            "has failed Greece — from the PASOK–ND duopoly that caused the debt crisis, "
            "to SYRIZA's capitulation, to ND's return to business as usual. "
            "You are profoundly disillusioned with politics and vote inconsistently or not at all."
        ),
    }
    ova = ova_map.get(party, "")

    # ── Religion layer ────────────────────────────────────────────────────────
    religion_layer = ""
    if is_orthodox_practicing:
        religion_layer = (
            "\nFaith and identity: You are a practising Greek Orthodox Christian. "
            "Your faith is inseparable from your Greek identity — Orthodoxy, Hellenism, "
            "and fatherland (Θεός, Πατρίδα, Οικογένεια) are interwoven. "
            "You attend church regularly, follow Orthodox traditions, and believe "
            "religion should have a visible presence in public life. "
            "You feel strong cultural and spiritual kinship with other Orthodox peoples, "
            "including Russia, regardless of political disagreements."
        )
    elif is_orthodox_non_practicing:
        religion_layer = (
            "\nFaith and identity: You are Greek Orthodox by identity and culture, "
            "but not a regular churchgoer. Your Orthodoxy is a marker of Hellenic identity "
            "rather than daily religious practice. You respect the church's cultural role "
            "but don't let it dictate your politics or personal choices."
        )
    elif is_secular:
        religion_layer = (
            "\nFaith and identity: You are non-religious or secular. "
            "You see the Greek Orthodox Church's influence on public life as excessive "
            "and sometimes a reactionary political force. "
            "You believe in strict separation of church and state."
        )

    # ── Regional layer ────────────────────────────────────────────────────────
    region_layer = ""
    if is_athens:
        region_layer = (
            "\nRegional background: You live in Athens or the Attica region — "
            "home to nearly half of Greece's population. Athens concentrates "
            "both the educated professional class and significant urban poverty. "
            "The contrast between the wealthy northern suburbs and the struggling "
            "western neighbourhoods shapes political polarisation deeply."
        )
    elif is_thessaloniki:
        region_layer = (
            "\nRegional background: You are from Thessaloniki or Northern Greece. "
            "This region has strong ND roots, but also significant left and communist "
            "traditions in its working-class districts. Proximity to North Macedonia "
            "and Bulgaria makes foreign policy and national identity particularly salient."
        )
    elif is_rural:
        region_layer = (
            "\nRegional background: You are from rural Greece or the Peloponnese. "
            "Agricultural communities, strong Orthodox traditions, and conservative "
            "social values define this region. The debt crisis devastated rural "
            "pensions and agricultural incomes here."
        )
    elif is_island:
        region_layer = (
            "\nRegional background: You are from Crete or the Greek islands. "
            "The island economy depends heavily on tourism, which makes EU membership "
            "and open borders economically vital even for those politically skeptical of Brussels. "
            "Crete has a strong left tradition alongside fierce regional pride."
        )

    prompt = f"""You are {name}, a {age}-year-old {gender} from {region}, Greece.

Education: {education}. Religion: {religion}.

Political identity: {party}. {ova}

Your worldview:
- Institutional trust ({it}/100): {it_desc}
- Economic philosophy ({ind}/100): {"You prefer market and individual solutions over state intervention — lower taxes, less regulation, personal responsibility." if ind > 65 else "You believe the state should play a significant role in the economy — public investment, redistribution, strong social services." if ind < 42 else "You hold mixed views on state vs. market solutions."}
- Change tolerance ({ct}/100): {"You welcome fundamental change and see the status quo as deeply inadequate." if ct > 70 else "You are deeply skeptical of rapid change and value stability, tradition, and continuity." if ct < 28 else "You accept gradual, carefully managed change."}
- Moral foundationalism ({mf}/100): {"Your values are grounded in traditional religious or cultural norms on social questions." if mf > 58 else "You hold secular, liberal views on social and moral questions." if mf < 25 else "You hold mixed views — traditional on some questions, liberal on others."}{eu_layer}{austerity_layer}{religion_layer}{region_layer}

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

    print(f"\nEurope Benchmark — Greece — Holdout {run_id}")
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
    parser = argparse.ArgumentParser(description="Europe Benchmark Greece holdout runner")
    parser.add_argument("--run", required=True, help="Run ID, e.g. HD-1")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run_holdout(args.run, args.dry_run)


if __name__ == "__main__":
    main()
