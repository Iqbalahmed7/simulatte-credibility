#!/usr/bin/env python3
"""
holdout_runner.py — Europe Benchmark · Netherlands holdout validation runner.

Runs only the 5 holdout questions (hd01–hd05) with ZERO topic-specific anchors.
Pure WorldviewAnchor architecture — tests generalisation outside calibration set.

Usage:
    python3 holdout_runner.py --run HD-1
    python3 holdout_runner.py --run HD-1 --dry-run

Protocol: minimum 3 independent runs. Results stable within ±2pp SD = reliable.

Holdout questions (Netherlands):
    hd01  us_view              — US favorability
    hd02  un_view              — UN favorability
    hd03  zelenskyy_confidence — Confidence in Zelenskyy
    hd04  macron_confidence    — Confidence in Macron
    hd05  children_future      — Children better/worse off financially

Ground truth: Pew Research Center Global Attitudes, Spring 2024 (Netherlands N=1,010).
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
    # ── VVD (liberal-conservative, Randstad business, pro-market) ─────────────
    ("nl_p01", "Pieter van den Berg",   52, "male",   "Netherlands (Amsterdam / Noord-Holland)",    "VVD",         "Pro-EU",     "None/secular",               "University/HBO", 2.0),
    ("nl_p02", "Mariëlle de Vries",     45, "female", "Netherlands (Rotterdam / Zuid-Holland)",     "VVD",         "Pro-EU",     "None/secular",               "University/HBO", 2.0),
    ("nl_p03", "Frank Jansen",          58, "male",   "Netherlands (The Hague / Den Haag)",         "VVD",         "Pro-EU",     "None/secular",               "University/HBO", 2.0),
    ("nl_p04", "Annemiek Bakker",       41, "female", "Netherlands (Utrecht)",                      "VVD",         "Pro-EU",     "None/secular",               "University/HBO", 2.0),
    ("nl_p05", "Willem Visser",         63, "male",   "Netherlands (Eindhoven / Noord-Brabant)",    "VVD",         "Pro-EU",     "Catholic (non-practicing)",   "University/HBO", 2.0),

    # ── PVV (Wilders voters, periphery, anti-immigration) ────────────────────
    ("nl_p06", "Ronald Smit",           54, "male",   "Netherlands (Almere / Flevoland)",           "PVV",         "EU-skeptic", "None/secular",               "MBO",            2.5),
    ("nl_p07", "Gerda Mulder",          49, "female", "Netherlands (Spijkenisse / Zuid-Holland)",   "PVV",         "EU-skeptic", "None/secular",               "VMBO/lower",     2.5),
    ("nl_p08", "Henk de Boer",          61, "male",   "Netherlands (Venlo / Limburg)",              "PVV",         "EU-skeptic", "Catholic (non-practicing)",   "MBO",            2.5),
    ("nl_p09", "Yvonne Meijer",         44, "female", "Netherlands (Dordrecht / Zuid-Holland)",     "PVV",         "EU-skeptic", "None/secular",               "MBO",            2.5),
    ("nl_p10", "Cor van der Berg",      67, "male",   "Netherlands (Tilburg / Noord-Brabant)",      "PVV",         "EU-skeptic", "Catholic (non-practicing)",   "VMBO/lower",     2.5),

    # ── D66 (progressive-liberal, Amsterdam/Rotterdam, highly educated, pro-EU) ─
    ("nl_p11", "Sophie de Vries",       34, "female", "Netherlands (Amsterdam / Noord-Holland)",    "D66",         "Pro-EU",     "None/secular",               "University/HBO", 2.0),
    ("nl_p12", "Joris Bakker",          38, "male",   "Netherlands (Rotterdam / Zuid-Holland)",     "D66",         "Pro-EU",     "None/secular",               "University/HBO", 2.0),
    ("nl_p13", "Lisa van den Berg",     29, "female", "Netherlands (Amsterdam / Noord-Holland)",    "D66",         "Pro-EU",     "None/secular",               "University/HBO", 2.0),
    ("nl_p14", "Niels Jansen",          46, "male",   "Netherlands (Utrecht)",                      "D66",         "Pro-EU",     "None/secular",               "University/HBO", 2.0),
    ("nl_p15", "Floor Visser",          42, "female", "Netherlands (The Hague / Den Haag)",         "D66",         "Pro-EU",     "None/secular",               "University/HBO", 2.0),

    # ── PvdA/GroenLinks (social-democrat + green, urban, educated) ────────────
    ("nl_p16", "Fatima el-Amrani",      33, "female", "Netherlands (Amsterdam / Noord-Holland)",    "PvdA/GL",     "Pro-EU",     "Muslim",                     "University/HBO", 2.0),
    ("nl_p17", "Sander de Boer",        47, "male",   "Netherlands (Rotterdam / Zuid-Holland)",     "PvdA/GL",     "Pro-EU",     "None/secular",               "University/HBO", 2.0),
    ("nl_p18", "Ingrid Mulder",         55, "female", "Netherlands (Groningen)",                    "PvdA/GL",     "Pro-EU",     "None/secular",               "University/HBO", 2.0),
    ("nl_p19", "Tom Smit",              31, "male",   "Netherlands (Nijmegen / Gelderland)",        "PvdA/GL",     "Pro-EU",     "None/secular",               "University/HBO", 2.0),
    ("nl_p20", "Roos van den Berg",     40, "female", "Netherlands (Amsterdam / Noord-Holland)",    "PvdA/GL",     "Pro-EU",     "None/secular",               "University/HBO", 2.0),

    # ── NSC (New Social Contract — Omtzigt centrist, disaffected from old parties) ─
    ("nl_p21", "Hans Bakker",           53, "male",   "Netherlands (Enschede / Overijssel)",        "NSC",         "Pro-EU",     "Protestant (non-practicing)", "MBO",            2.5),
    ("nl_p22", "Marlies Visser",        48, "female", "Netherlands (Deventer / Overijssel)",        "NSC",         "Pro-EU",     "None/secular",               "MBO",            2.5),
    ("nl_p23", "Erik Jansen",           44, "male",   "Netherlands (Zwolle / Overijssel)",          "NSC",         "Pro-EU",     "Protestant (non-practicing)", "University/HBO", 2.5),
    ("nl_p24", "Wilma de Vries",        59, "female", "Netherlands (Amersfoort / Utrecht)",         "NSC",         "Pro-EU",     "None/secular",               "MBO",            2.5),

    # ── CDA (Christian-democratic — Bible Belt, Reformed Protestant or Catholic) ─
    ("nl_p25", "Gerrit van der Berg",   64, "male",   "Netherlands (Staphorst / Overijssel — Bible Belt)", "CDA", "Pro-EU",     "Protestant (practicing)",    "MBO",            2.5),
    ("nl_p26", "Rietje Mulder",         58, "female", "Netherlands (Zeeland — Bible Belt)",         "CDA",         "Pro-EU",     "Protestant (practicing)",    "VMBO/lower",     2.5),
    ("nl_p27", "Hendrikus Smit",        62, "male",   "Netherlands (rural Noord-Brabant)",          "CDA",         "Pro-EU",     "Catholic (practicing)",      "MBO",            2.5),

    # ── Non-partisan / disengaged (cross-cutting) ─────────────────────────────
    ("nl_p28", "Kevin Bakker",          36, "male",   "Netherlands (Almere / Flevoland)",           "Non-partisan", "EU-skeptic", "None/secular",              "MBO",            2.5),
    ("nl_p29", "Chantal de Vries",      43, "female", "Netherlands (Rotterdam / Zuid-Holland)",     "Non-partisan", "EU-skeptic", "None/secular",              "VMBO/lower",     2.5),
    ("nl_p30", "Mohamed el-Bakali",     38, "male",   "Netherlands (Amsterdam / Noord-Holland)",    "Non-partisan", "Pro-EU",     "Muslim",                    "MBO",            2.5),
    ("nl_p31", "Greet Jansen",          61, "female", "Netherlands (rural Noord-Brabant)",          "Non-partisan", "EU-skeptic", "Catholic (non-practicing)",  "VMBO/lower",     2.5),
    ("nl_p32", "Theo Visser",           55, "male",   "Netherlands (Tilburg / Noord-Brabant)",      "Non-partisan", "EU-skeptic", "None/secular",              "MBO",            2.5),
    ("nl_p33", "Amber van den Berg",    27, "female", "Netherlands (Amsterdam / Noord-Holland)",    "Non-partisan", "Pro-EU",     "None/secular",              "University/HBO", 2.0),
    ("nl_p34", "Jaap Smit",             69, "male",   "Netherlands (Zeeland — Bible Belt)",         "Non-partisan", "Pro-EU",     "Protestant (practicing)",   "MBO",            2.5),
    ("nl_p35", "Naima Bouazza",         32, "female", "Netherlands (Rotterdam / Zuid-Holland)",     "Non-partisan", "Pro-EU",     "Muslim",                    "MBO",            2.5),
    ("nl_p36", "Kees Mulder",           57, "male",   "Netherlands (Groningen)",                    "Non-partisan", "EU-skeptic", "None/secular",              "MBO",            2.5),
    ("nl_p37", "Tineke de Boer",        46, "female", "Netherlands (Utrecht)",                      "Non-partisan", "Pro-EU",     "None/secular",              "University/HBO", 2.0),
    ("nl_p38", "Ad Jansen",             70, "male",   "Netherlands (Venlo / Limburg)",              "Non-partisan", "EU-skeptic", "Catholic (non-practicing)",  "VMBO/lower",     2.5),
    ("nl_p39", "Lotte Bakker",          35, "female", "Netherlands (Eindhoven / Noord-Brabant)",    "Non-partisan", "Pro-EU",     "None/secular",              "University/HBO", 2.0),
    ("nl_p40", "Bert van der Berg",     60, "male",   "Netherlands (Almere / Flevoland)",           "Non-partisan", "EU-skeptic", "None/secular",              "VMBO/lower",     2.5),
]

WORLDVIEW = {
    # id:        (IT,  IND, CT,  MF)
    "nl_p01": (68,  76,  48,  16),
    "nl_p02": (65,  74,  46,  14),
    "nl_p03": (70,  78,  44,  18),
    "nl_p04": (64,  72,  50,  12),
    "nl_p05": (62,  70,  42,  30),
    "nl_p06": (30,  62,  22,  40),
    "nl_p07": (28,  58,  18,  38),
    "nl_p08": (32,  60,  20,  46),
    "nl_p09": (35,  64,  24,  36),
    "nl_p10": (26,  58,  16,  50),
    "nl_p11": (68,  64,  80,  10),
    "nl_p12": (65,  62,  76,  12),
    "nl_p13": (70,  64,  82,   8),
    "nl_p14": (62,  66,  72,  14),
    "nl_p15": (64,  62,  74,  10),
    "nl_p16": (60,  32,  76,  48),
    "nl_p17": (58,  35,  72,  14),
    "nl_p18": (55,  30,  70,  12),
    "nl_p19": (62,  38,  78,  10),
    "nl_p20": (60,  34,  74,  12),
    "nl_p21": (52,  55,  40,  45),
    "nl_p22": (54,  52,  42,  35),
    "nl_p23": (56,  58,  44,  42),
    "nl_p24": (50,  50,  38,  32),
    "nl_p25": (58,  52,  26,  72),
    "nl_p26": (55,  50,  24,  76),
    "nl_p27": (60,  54,  28,  66),
    "nl_p28": (34,  56,  28,  32),
    "nl_p29": (30,  52,  24,  28),
    "nl_p30": (48,  44,  52,  54),
    "nl_p31": (35,  50,  22,  44),
    "nl_p32": (32,  54,  20,  30),
    "nl_p33": (65,  58,  78,  10),
    "nl_p34": (56,  48,  22,  68),
    "nl_p35": (52,  46,  58,  52),
    "nl_p36": (28,  52,  20,  26),
    "nl_p37": (62,  58,  68,  12),
    "nl_p38": (30,  50,  18,  46),
    "nl_p39": (60,  56,  66,  14),
    "nl_p40": (26,  52,  16,  34),
}


def build_system_prompt(persona: tuple) -> str:
    """Pure WorldviewAnchor prompt — zero topic-specific anchors."""
    pid, name, age, gender, region, party, eu_ref, religion, education, weight = persona
    it, ind, ct, mf = WORLDVIEW[pid]

    is_randstad         = any(x in region for x in ("Amsterdam", "Rotterdam", "The Hague", "Den Haag", "Utrecht"))
    is_periphery        = any(x in region for x in ("Almere", "Flevoland", "Limburg", "Venlo", "Tilburg", "Groningen", "Spijkenisse"))
    is_bible_belt       = "Bible Belt" in region or "Staphorst" in region or "Zeeland" in region
    is_eu_skeptic       = eu_ref == "EU-skeptic"
    is_muslim           = religion == "Muslim"
    is_protestant_pract = "Protestant (practicing)" in religion
    is_catholic_pract   = "Catholic (practicing)" in religion

    # ── Institutional trust descriptor ────────────────────────────────────────
    if it < 38:
        it_desc = (
            "You have very low trust in Dutch institutions — the Tweede Kamer, the media, "
            "the EU technocrats in Brussels. You feel the political establishment "
            "(Den Haag) governs for a cosmopolitan elite while ordinary Dutch people "
            "are ignored, particularly on immigration and safety."
        )
    elif it < 52:
        it_desc = (
            "You have mixed trust in Dutch institutions. You see real dysfunction — "
            "housing crisis, nitrogen crisis, benefit-affairs scandal — and growing "
            "disillusionment, but you still believe in the principles of Dutch "
            "consensus democracy (polderen) in theory."
        )
    elif it < 63:
        it_desc = (
            "You have moderate trust in Dutch institutions. You are realistic about "
            "their imperfections — the toeslagen scandal, housing crisis — but broadly "
            "believe in the Netherlands' democratic and rule-of-law traditions."
        )
    else:
        it_desc = (
            "You have high trust in Dutch institutions. The rule of law, the independent "
            "judiciary, a free press, and European cooperation all matter deeply to you. "
            "The Netherlands' democratic culture is something to be proud of and defended."
        )

    # ── EU/Europe layer ────────────────────────────────────────────────────────
    if not is_eu_skeptic:
        eu_layer = (
            "\nEurope: You are broadly pro-European. The Netherlands has benefited "
            "enormously from the EU single market and free movement. You see European "
            "cooperation as essential for Dutch prosperity, security, and climate policy. "
            "Nexit talk from the PVV strikes you as economically reckless."
        )
    else:
        eu_layer = (
            "\nEurope: You are skeptical of the EU. Brussels imposes costly regulations — "
            "nitrogen rules, migration policy — that the Dutch public never agreed to. "
            "You want a Netherlands that puts its own citizens first and has sovereignty "
            "over its own borders and laws. You are not against trade, but against "
            "political integration driven by unelected bureaucrats."
        )

    # ── Party political identity ───────────────────────────────────────────────
    ova_map = {
        "VVD": (
            "The Netherlands works best when individuals and businesses are free to "
            "innovate and compete. The VVD stands for a strong economy, low taxes, "
            "sound finances, and firm but fair rule of law. You believe in personal "
            "responsibility and a government that enables rather than directs. "
            "The Rutte years delivered economic stability; Wilders' populism risks undoing that."
        ),
        "PVV": (
            "The Netherlands has been transformed by mass immigration without the consent "
            "of ordinary Dutch people. Geert Wilders and the PVV are the only ones "
            "who name this honestly. You want the Netherlands to be Dutch again — "
            "firm immigration control, protection of Dutch culture and identity, "
            "and a government that serves ordinary citizens, not elites, asylum seekers, "
            "or Brussels bureaucrats. The establishment ignored voters for decades; "
            "November 2023 was the reckoning."
        ),
        "D66": (
            "A progressive, open, and knowledge-based Netherlands is the country's "
            "best future. D66 represents evidence-based governance, civil liberties, "
            "European integration, and investment in education and climate. "
            "You believe in an inclusive Netherlands that is confident in the world — "
            "rejecting both PVV nationalism and old-left statism. "
            "Wilders' governing majority alarms you deeply."
        ),
        "PvdA/GL": (
            "The Netherlands cannot just be a market economy. It must also be a "
            "just society — strong public services, a liveable climate, affordable "
            "housing, and genuine equality of opportunity. PvdA/GroenLinks represents "
            "the combination of social justice and ecological responsibility. "
            "You want a Netherlands where nobody is left behind and the planet is "
            "not sacrificed for short-term profit."
        ),
        "NSC": (
            "The political system has failed Dutch citizens — from the toeslagen "
            "affair to the nitrogen crisis — because established parties put "
            "coalition politics above honest governance. Pieter Omtzigt and NSC "
            "stand for integrity: follow the law, protect citizens' rights, and "
            "restore trust in government by actually doing what parliament decides. "
            "You are centre — not ideologically rigid — but deeply committed to "
            "constitutional norms and governmental accountability."
        ),
        "CDA": (
            "Society needs more than the state and the market — it needs community, "
            "faith, and shared responsibility. The CDA's Christian-democratic tradition "
            "grounds social values in care for one another, family, and human dignity. "
            "You believe the Netherlands' Christian heritage matters, that subsidarity "
            "and civil society are vital, and that both unbridled individualism and "
            "heavy-handed state control are wrong."
        ),
        "Non-partisan": (
            "no single party speaks for you. You vote based on specific issues "
            "or not at all. You are disillusioned with how established parties "
            "have run the country — housing crisis, failed asylum policy, toeslagen "
            "scandal — but also uncertain whether PVV or the old parties offer "
            "real solutions."
        ),
    }
    ova = ova_map.get(party, "")

    # ── Religion layer ────────────────────────────────────────────────────────
    religion_layer = ""
    if is_muslim:
        religion_layer = (
            "\nFaith and identity: Your Muslim faith is part of your identity. "
            "You experience discrimination in Dutch society and feel that PVV "
            "rhetoric explicitly targets your community. You are Dutch — this "
            "is your country — and you reject the framing that Islam and Dutch "
            "identity are incompatible. You believe in the separation of church "
            "and state but object to Islam being singled out in political discourse."
        )
    elif is_protestant_pract:
        religion_layer = (
            "\nFaith and identity: You are a practising Reformed Protestant "
            "(Gereformeerd). Your faith is foundational to your daily life, "
            "your community, and your values. You live in or identify with "
            "the Bible Belt (Bijbelgordel) — a tight-knit community where "
            "Sunday observance, biblical ethics, and church life remain central. "
            "The rapid secularisation of the Netherlands concerns you deeply."
        )
    elif is_catholic_pract:
        religion_layer = (
            "\nFaith and identity: You are a practising Catholic, rooted in "
            "the Catholic south (Noord-Brabant or Limburg). Your faith shapes "
            "your social values — care for the community, human dignity, "
            "and social responsibility. You worry that a purely secular, "
            "market-driven society loses its moral compass."
        )

    # ── Regional layer ────────────────────────────────────────────────────────
    region_layer = ""
    if is_randstad:
        region_layer = (
            "\nRegional background: You live in the Randstad — Amsterdam, "
            "Rotterdam, The Hague, or Utrecht. This is the economic and "
            "cultural engine of the Netherlands: highly educated, cosmopolitan, "
            "diverse, and internationally connected. The gap between Randstad "
            "and the rest of the country (the 'regio') is real and growing."
        )
    elif is_periphery:
        region_layer = (
            "\nRegional background: You live outside the Randstad — in a "
            "smaller city or town in a peripheral province. You feel that "
            "national politics is dominated by the Randstad bubble — Den Haag "
            "and Amsterdam decide everything while your region is overlooked "
            "on housing, public transport, and services. This resentment "
            "drives strong PVV support in many peripheral areas."
        )
    elif is_bible_belt:
        region_layer = (
            "\nRegional background: You are from the Bible Belt (Bijbelgordel) — "
            "Zeeland, Staphorst, or the Veluwe. This is the most religious "
            "part of the Netherlands: a strip of Reformed Protestant communities "
            "where faith still structures everyday life. Your community values "
            "are different from the secular urban Netherlands most politicians "
            "seem to have in mind."
        )

    prompt = f"""You are {name}, a {age}-year-old {gender} from {region}, Netherlands.

Education: {education}. Religion: {religion}. EU position: {eu_ref}.

Political identity: You support or lean toward {party}. {ova}.

Your worldview:
- Institutional trust ({it}/100): {it_desc}
- Economic philosophy ({ind}/100): {"You prefer market and individual solutions over state intervention — lower taxes, less regulation, personal responsibility." if ind > 65 else "You believe the state should play a significant role in the economy — public investment, redistribution, strong public services." if ind < 42 else "You hold mixed views on state vs. market solutions."}
- Change tolerance ({ct}/100): {"You welcome fundamental change and see the status quo as deeply inadequate." if ct > 70 else "You are deeply skeptical of rapid change and value stability, tradition, and continuity." if ct < 28 else "You accept gradual, carefully managed change."}
- Moral foundationalism ({mf}/100): {"Your values are grounded in traditional religious or cultural norms on social questions." if mf > 58 else "You hold secular, liberal views on social and moral questions." if mf < 25 else "You hold mixed views — traditional on some questions, liberal on others."}{eu_layer}{region_layer}{religion_layer}

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

    print(f"\nEurope Benchmark — Netherlands — Holdout {run_id}")
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
    parser = argparse.ArgumentParser(description="Europe Benchmark Netherlands holdout runner")
    parser.add_argument("--run", required=True, help="Run ID, e.g. HD-1")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run_holdout(args.run, args.dry_run)


if __name__ == "__main__":
    main()
