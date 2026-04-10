#!/usr/bin/env python3
"""
sprint_runner.py — Europe Benchmark · Netherlands calibration sprint runner.

Usage:
    python3 sprint_runner.py --sprint NL-1 --model haiku
    python3 sprint_runner.py --sprint NL-1 --model haiku --dry-run

WorldviewAnchor dimensions (0–100 scale):
    IT  — Institutional Trust
    IND — Individualism (market vs. state preference)
    CT  — Change Tolerance
    MF  — Moral Foundationalism

Key Netherlands calibration axes:
    1. Party structure: PVV (Wilders, nationalist-populist), VVD (liberal-conservative),
       D66 (progressive-liberal, pro-EU), PvdA/GroenLinks (social-dem + green),
       NSC (Omtzigt centrist), CDA (Christian-democratic)
    2. Randstad (Amsterdam/Rotterdam/Den Haag — cosmopolitan, D66/Labour) vs.
       periphery (PVV stronghold)
    3. MH17: Malaysia Airlines MH17 shot down over Ukraine 2014; 196 Dutch killed —
       defining emotional event; drives extreme Russia hostility across all parties
    4. Religion: highly secular (~25% religious); Bible Belt exception (Reformed Protestant)
    5. Economy: strong, export-oriented; most content with economic system in the study
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
MANIFESTS  = STUDY_ROOT / "results" / "sprint_manifests"
MANIFESTS.mkdir(parents=True, exist_ok=True)

MODELS = {
    "haiku":  "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-6",
}

# ── Persona pool ──────────────────────────────────────────────────────────────
# (id, name, age, gender, region, party, eu_ref, religion, education, weight)
#
# Demographic targets (CBS / Dutch Election Studies):
#   Parties:  PVV ~12.5%, VVD ~12.5%, D66 ~12.5%, PvdA/GL ~12.5%,
#             NSC ~10%, CDA ~7.5%, Non-partisan ~32.5%
#   Region:   Randstad (Amsterdam/Rotterdam/Den Haag/Utrecht) ~45%,
#             Other urban ~30%, Peripheral/rural ~25%
#   Religion: Non-religious ~75%, Protestant ~10%, Catholic ~10%, Muslim ~5%
#   Education: University/HBO ~40%, MBO ~35%, VMBO/lower ~25%
#   Age range: 26–70

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

# ── WorldviewAnchor values ────────────────────────────────────────────────────
WORLDVIEW = {
    # id:        (IT,  IND, CT,  MF)
    # VVD — high IT, high IND, moderate CT, low-moderate MF
    "nl_p01": (68,  76,  48,  16),   # VVD, Amsterdam, Pro-EU, secular, university
    "nl_p02": (65,  74,  46,  14),   # VVD, Rotterdam, Pro-EU, secular, university
    "nl_p03": (70,  78,  44,  18),   # VVD, Den Haag, Pro-EU, secular, university (older)
    "nl_p04": (64,  72,  50,  12),   # VVD, Utrecht, Pro-EU, secular, university
    "nl_p05": (62,  70,  42,  30),   # VVD, Noord-Brabant, Pro-EU, non-practicing Catholic, university

    # PVV — low IT, moderate IND, low CT, moderate MF
    "nl_p06": (30,  62,  22,  40),   # PVV, Almere, EU-skeptic, secular, MBO
    "nl_p07": (28,  58,  18,  38),   # PVV, Spijkenisse, EU-skeptic, secular, VMBO
    "nl_p08": (32,  60,  20,  46),   # PVV, Limburg, EU-skeptic, non-practicing Catholic, MBO
    "nl_p09": (35,  64,  24,  36),   # PVV, Dordrecht, EU-skeptic, secular, MBO
    "nl_p10": (26,  58,  16,  50),   # PVV, Noord-Brabant, EU-skeptic, non-practicing Catholic, VMBO (oldest)

    # D66 — high IT, moderate IND, high CT, very low MF
    "nl_p11": (68,  64,  80,  10),   # D66, Amsterdam, Pro-EU, secular, university (younger)
    "nl_p12": (65,  62,  76,  12),   # D66, Rotterdam, Pro-EU, secular, university
    "nl_p13": (70,  64,  82,   8),   # D66, Amsterdam, Pro-EU, secular, university (youngest)
    "nl_p14": (62,  66,  72,  14),   # D66, Utrecht, Pro-EU, secular, university
    "nl_p15": (64,  62,  74,  10),   # D66, Den Haag, Pro-EU, secular, university

    # PvdA/GL — moderate-high IT, low IND, high CT, low MF
    "nl_p16": (60,  32,  76,  48),   # PvdA/GL, Amsterdam, Pro-EU, Muslim, university
    "nl_p17": (58,  35,  72,  14),   # PvdA/GL, Rotterdam, Pro-EU, secular, university
    "nl_p18": (55,  30,  70,  12),   # PvdA/GL, Groningen, Pro-EU, secular, university
    "nl_p19": (62,  38,  78,  10),   # PvdA/GL, Nijmegen, Pro-EU, secular, university (younger)
    "nl_p20": (60,  34,  74,  12),   # PvdA/GL, Amsterdam, Pro-EU, secular, university

    # NSC — moderate IT, moderate IND, moderate CT, moderate MF
    "nl_p21": (52,  55,  40,  45),   # NSC, Overijssel, Pro-EU, non-practicing Protestant, MBO
    "nl_p22": (54,  52,  42,  35),   # NSC, Overijssel, Pro-EU, secular, MBO
    "nl_p23": (56,  58,  44,  42),   # NSC, Overijssel, Pro-EU, non-practicing Protestant, university
    "nl_p24": (50,  50,  38,  32),   # NSC, Utrecht, Pro-EU, secular, MBO

    # CDA/Bible Belt — moderate IT, moderate IND, low CT, high MF
    "nl_p25": (58,  52,  26,  72),   # CDA, Staphorst Bible Belt, Pro-EU, practicing Protestant, MBO
    "nl_p26": (55,  50,  24,  76),   # CDA, Zeeland Bible Belt, Pro-EU, practicing Protestant, VMBO
    "nl_p27": (60,  54,  28,  66),   # CDA, Noord-Brabant, Pro-EU, practicing Catholic, MBO

    # Non-partisan — wide spread
    "nl_p28": (34,  56,  28,  32),   # NP, Almere, EU-skeptic, secular, MBO
    "nl_p29": (30,  52,  24,  28),   # NP, Rotterdam, EU-skeptic, secular, VMBO
    "nl_p30": (48,  44,  52,  54),   # NP, Amsterdam, Pro-EU, Muslim, MBO
    "nl_p31": (35,  50,  22,  44),   # NP, Noord-Brabant, EU-skeptic, non-practicing Catholic, VMBO
    "nl_p32": (32,  54,  20,  30),   # NP, Noord-Brabant, EU-skeptic, secular, MBO
    "nl_p33": (65,  58,  78,  10),   # NP, Amsterdam, Pro-EU, secular, university (youngest)
    "nl_p34": (56,  48,  22,  68),   # NP, Zeeland Bible Belt, Pro-EU, practicing Protestant, MBO (oldest)
    "nl_p35": (52,  46,  58,  52),   # NP, Rotterdam, Pro-EU, Muslim, MBO
    "nl_p36": (28,  52,  20,  26),   # NP, Groningen, EU-skeptic, secular, MBO
    "nl_p37": (62,  58,  68,  12),   # NP, Utrecht, Pro-EU, secular, university
    "nl_p38": (30,  50,  18,  46),   # NP, Limburg, EU-skeptic, non-practicing Catholic, VMBO (oldest)
    "nl_p39": (60,  56,  66,  14),   # NP, Eindhoven, Pro-EU, secular, university
    "nl_p40": (26,  52,  16,  34),   # NP, Almere, EU-skeptic, secular, VMBO (older)
}


def build_system_prompt(persona: tuple) -> str:
    pid, name, age, gender, region, party, eu_ref, religion, education, weight = persona
    it, ind, ct, mf = WORLDVIEW[pid]

    is_randstad         = any(x in region for x in ("Amsterdam", "Rotterdam", "The Hague", "Den Haag", "Utrecht"))
    is_periphery        = any(x in region for x in ("Almere", "Flevoland", "Limburg", "Venlo", "Tilburg", "Groningen", "Spijkenisse"))
    is_bible_belt       = "Bible Belt" in region or "Staphorst" in region or "Zeeland" in region
    is_eu_skeptic       = eu_ref == "EU-skeptic"
    is_pro_eu           = eu_ref == "Pro-EU"
    is_muslim           = religion == "Muslim"
    is_protestant_pract = "Protestant (practicing)" in religion
    is_catholic_pract   = "Catholic (practicing)" in religion
    is_religious_pract  = is_protestant_pract or is_catholic_pract
    is_secular          = "secular" in religion or "None" in religion
    is_working_class    = "VMBO" in education or "MBO" in education

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
    if is_pro_eu:
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

    # ── Topic-specific option-vocabulary anchors ──────────────────────────────
    topic_anchors = []

    # nl01: Economic conditions
    # Target: A=11.6%, B=59.7%, C=20.5%, D=8.1%
    # FIX (NL-4): NL-3 had A=6.6% (only D66+it>=65→A), D=0% (no D branch).
    # Fix: add VVD+it>=68→A; add NP eu-sk+wc+it<=30→D (most economically pessimistic).
    if party == "D66" and it >= 65:
        topic_anchors.append('On the Dutch economy: your answer is "Very good" (A) — the Netherlands has one of the strongest economies in the EU: low unemployment, fiscal surplus, and strong exports.')
    elif party == "VVD" and it >= 68:
        topic_anchors.append('On the Dutch economy: your answer is "Very good" (A) — the Dutch economy is performing excellently: record employment, fiscal surplus, and world-class export industries. The VVD economic model delivers.')
    elif party in ("VVD", "D66"):
        topic_anchors.append('On the Dutch economy: your answer is "Somewhat good" (B) — the fundamentals are strong; housing and cost of living are challenges but the broader economy is healthy.')
    elif party == "PvdA/GL":
        topic_anchors.append('On the Dutch economy: your answer is "Somewhat good" (B) — the macro figures look good but housing unaffordability and inequality mean ordinary people don\'t always feel it.')
    elif party == "NSC":
        topic_anchors.append('On the Dutch economy: your answer is "Somewhat good" (B) — strong overall, but the government has failed to translate this into affordable housing and public services.')
    elif party == "CDA":
        topic_anchors.append('On the Dutch economy: your answer is "Somewhat good" (B) — the Netherlands is prosperous but needs to invest more in community and social cohesion.')
    elif party == "PVV" and is_working_class:
        topic_anchors.append('On the Dutch economy: your answer is "Somewhat bad" (C) — the statistics look fine for the elites but ordinary Dutch people face housing costs they can\'t afford and wages that don\'t keep up.')
    elif party == "PVV":
        topic_anchors.append('On the Dutch economy: your answer is "Somewhat good" (B) — the economy is broadly okay but immigration costs and mismanagement hold it back.')
    elif is_eu_skeptic and is_working_class and it <= 30:
        topic_anchors.append('On the Dutch economy: your answer is "Very bad" (D) — the economy is failing ordinary Dutch people: housing is unaffordable, wages don\'t keep up, and the elites take all the gains while working families struggle.')
    elif is_eu_skeptic and is_working_class:
        topic_anchors.append('On the Dutch economy: your answer is "Somewhat bad" (C) — the benefits of the strong economy don\'t reach everyone equally.')
    else:
        topic_anchors.append('On the Dutch economy: your answer is "Somewhat good" (B).')

    # nl02: Democracy satisfaction
    # Target: A=16.5%, B=47.0%, C=23.8%, D=12.7%
    # FIX (NL-4): NL-3 had A=0% (no A branch), D=24.7% (is_eu_sk+it<35 too broad).
    # Fix: VVD/D66+it>=65→A; PVV+it<=30→D; NP eu-sk+it<=28→D; tighten remaining C/D.
    if party == "PVV" and it <= 30:
        topic_anchors.append('On democracy in the Netherlands: your answer is "Not at all satisfied" (D) — the system has been rigged by elites for decades; the establishment ignored the people on immigration, and when Wilders finally won they tried to block him anyway.')
    elif is_eu_skeptic and it <= 28:
        topic_anchors.append('On democracy in the Netherlands: your answer is "Not at all satisfied" (D) — the whole system is rotten; elections change nothing while ordinary people lose faith in politics entirely.')
    elif party == "PVV":
        topic_anchors.append('On democracy in the Netherlands: your answer is "Not too satisfied" (C) — democracy works in principle but the political class has ignored ordinary voters for too long.')
    elif party in ("VVD", "D66") and it >= 65:
        topic_anchors.append('On democracy in the Netherlands: your answer is "Very satisfied" (A) — Dutch democracy is one of the world\'s strongest: pluralist, rule-of-law grounded, with a free press and independent judiciary. You are proud of the system even when you disagree with outcomes.')
    elif party in ("VVD", "D66"):
        topic_anchors.append('On democracy in the Netherlands: your answer is "Somewhat satisfied" (B) — the system functions well, even if the PVV entering government raises concerns about rule-of-law norms.')
    elif party == "PvdA/GL":
        topic_anchors.append('On democracy in the Netherlands: your answer is "Somewhat satisfied" (B) — broadly healthy but the rise of PVV and the toeslagen failure show serious vulnerabilities.')
    elif party == "NSC":
        topic_anchors.append('On democracy in the Netherlands: your answer is "Not too satisfied" (C) — institutions have failed citizens repeatedly; restoring trust requires genuine reform.')
    elif party == "CDA":
        topic_anchors.append('On democracy in the Netherlands: your answer is "Somewhat satisfied" (B) — the system works; polarisation is a risk but Dutch consensus culture is durable.')
    elif is_eu_skeptic and it < 35:
        topic_anchors.append('On democracy in the Netherlands: your answer is "Not too satisfied" (C) — the political class has failed ordinary voters; real change never comes through elections.')
    elif is_pro_eu and it >= 58:
        topic_anchors.append('On democracy in the Netherlands: your answer is "Somewhat satisfied" (B).')
    else:
        topic_anchors.append('On democracy in the Netherlands: your answer is "Somewhat satisfied" (B).')

    # nl03: Russia view
    # Target: A=1.0%, B=5.1%, C=19.9%, D=74.0%
    # FIX (NL-3): old code had D=91.8% because only PVV+it<=30 → C, everything else → D.
    # Fix: ALL PVV → C (Wilders voters have a "both sides" / MH17-but-NATO-provocation view);
    # NP eu-sk very-low-IT → B (extreme anti-NATO/anti-Western narrative); else → D.
    if party == "PVV":
        topic_anchors.append('On Russia: your answer is "Somewhat unfavorable" (C) — MH17 killed 196 Dutch people and Russia is responsible. That is unforgivable. But you also reject the simple NATO-vs-Russia narrative; NATO expansion and Western meddling in Ukraine played a role. You refuse to be told what to think by the same establishment that failed ordinary Dutch people.')
    elif is_eu_skeptic and it < 30:
        topic_anchors.append('On Russia: your answer is "Somewhat favorable" (B) — you don\'t trust the Western narrative on Russia. The media and political class that botched MH17\'s investigation for years now demand you accept their version of events. You are skeptical of both sides.')
    else:
        topic_anchors.append('On Russia: your answer is "Very unfavorable" (D) — MH17 killed 196 Dutch people. Putin\'s Russia shot down a civilian airliner, invaded Ukraine, and now threatens all of Europe. There is nothing to be "favorable" about.')

    # nl04: EU view
    # Target: A=22.6%, B=50.4%, C=16.7%, D=10.3%
    # FIX (NL-3): A=4.4% because only D66+it>=68 → A. Fix: D66 all → A; PvdA/GL+high-IT → A.
    if party == "D66":
        topic_anchors.append('On the European Union: your answer is "Very favorable" (A) — the EU is central to Dutch prosperity, security, and our shared future. The single market, freedom of movement, joint climate action, and the rule of law are all vital. D66 is the most unambiguously pro-European party.')
    elif party == "PvdA/GL" and it >= 60:
        topic_anchors.append('On the European Union: your answer is "Very favorable" (A) — European solidarity, social rights, and climate action can only be achieved together. The EU is essential for a fair and sustainable Netherlands.')
    elif party in ("VVD", "PvdA/GL", "NSC", "CDA"):
        topic_anchors.append('On the European Union: your answer is "Somewhat favorable" (B) — the EU has real flaws and needs reform, but it is fundamentally good for the Netherlands and for European stability.')
    elif party == "PVV" and it <= 30:
        topic_anchors.append('On the European Union: your answer is "Very unfavorable" (D) — Brussels imposes open borders and regulations that the Dutch people never voted for. Nexit should be on the table.')
    elif party == "PVV":
        topic_anchors.append('On the European Union: your answer is "Somewhat unfavorable" (C) — the EU has gone too far in taking powers away from national governments. It needs to be fundamentally reformed or we should reconsider membership.')
    elif is_eu_skeptic and is_working_class:
        topic_anchors.append('On the European Union: your answer is "Somewhat unfavorable" (C) — open borders have driven down wages and the EU serves multinationals, not Dutch workers.')
    elif is_pro_eu:
        topic_anchors.append('On the European Union: your answer is "Somewhat favorable" (B).')
    elif is_eu_skeptic:
        topic_anchors.append('On the European Union: your answer is "Somewhat unfavorable" (C).')
    else:
        topic_anchors.append('On the European Union: your answer is "Somewhat favorable" (B).')

    # nl05: NATO view
    # Target: A=29.5%, B=52.6%, C=10.7%, D=7.2%
    # NL-1: A=13.2%, B=75.8%, C=11.0% — CDA→A rule shadowed by VVD/D66/NSC/CDA→B
    # Fix: A-first for VVD/D66+it≥62 + CDA all; D for very-low-IT EU-skeptic
    if party in ("VVD", "D66") and it >= 62:
        topic_anchors.append('On NATO: your answer is "Very favorable" (A) — NATO is the cornerstone of Dutch security. After MH17 and Ukraine, collective defence is not optional. The Netherlands must honour its F-35 commitment and be a fully committed NATO member.')
    elif party == "CDA":
        topic_anchors.append('On NATO: your answer is "Very favorable" (A) — transatlantic solidarity and European defence cooperation are essential. The Netherlands must honour its NATO commitments fully.')
    elif is_eu_skeptic and it <= 28:
        topic_anchors.append('On NATO: your answer is "Very unfavorable" (D) — NATO is dominated by American interests that don\'t always align with the Netherlands. The billions in defence spending could be better spent at home.')
    elif is_eu_skeptic and it < 36:
        topic_anchors.append('On NATO: your answer is "Somewhat unfavorable" (C) — you support Dutch defence but have mixed feelings about NATO\'s direction under American leadership.')
    elif party in ("VVD", "D66", "NSC"):
        topic_anchors.append('On NATO: your answer is "Somewhat favorable" (B) — NATO is essential for Dutch security after MH17 and Ukraine; the Netherlands must maintain its commitments.')
    elif party == "PvdA/GL":
        topic_anchors.append('On NATO: your answer is "Somewhat favorable" (B) — NATO provides necessary collective security; you want stronger European coordination within the alliance.')
    elif party == "PVV":
        topic_anchors.append('On NATO: your answer is "Somewhat favorable" (B) — you support NATO for Dutch security. Wilders is not anti-NATO; after MH17 the Netherlands must be protected.')
    else:
        topic_anchors.append('On NATO: your answer is "Somewhat favorable" (B).')

    # nl06: China view
    # Target: A=1.6%, B=18.4%, C=45.6%, D=34.3%
    # NL-1: D=17.6%, C=82.4%, B=0% — ordering bug (VVD/D66+it≥64→D shadowed); B completely missed
    # Fix: VVD+D66+PvdA/GL all → D; NP EU-skeptic working-class low-IT → B; rest → C
    if party in ("VVD", "D66"):
        topic_anchors.append('On China: your answer is "Very unfavorable" (D) — China is a strategic threat: it steals ASML technology, persecutes Uyghurs, kidnaps people like Gui Minhai, and uses economic coercion. The Netherlands must be clear-eyed and firm.')
    elif party == "PvdA/GL":
        topic_anchors.append('On China: your answer is "Very unfavorable" (D) — China\'s persecution of Uyghurs, crushing of Hong Kong democracy, and authoritarian capitalism make it a systemic adversary. Human rights cannot be traded away.')
    elif is_eu_skeptic and is_working_class and it < 36:
        topic_anchors.append('On China: your answer is "Somewhat favorable" (B) — China is a big country that gets things done and doesn\'t lecture us about values. The West has its own problems. Trade matters for ordinary Dutch workers.')
    elif party in ("NSC", "CDA"):
        topic_anchors.append('On China: your answer is "Somewhat unfavorable" (C) — China\'s human rights record and economic aggression are deeply concerning; ASML restrictions are justified.')
    elif party == "PVV":
        topic_anchors.append('On China: your answer is "Somewhat unfavorable" (C) — China is a threat to Dutch industry and technology. ASML restrictions are correct. But unlike the left, you see all authoritarian threats clearly.')
    elif is_pro_eu and it >= 55:
        topic_anchors.append('On China: your answer is "Somewhat unfavorable" (C) — a systemic rival that does not respect the rules-based order or human rights.')
    elif is_eu_skeptic:
        topic_anchors.append('On China: your answer is "Somewhat unfavorable" (C) — a threat to Dutch manufacturing and jobs.')
    else:
        topic_anchors.append('On China: your answer is "Somewhat unfavorable" (C).')

    # nl07: Trump confidence
    # Target: A=4.3%, B=12.9%, C=13.8%, D=69.1%
    # FIX (NL-4): NL-3 had D=86.3% (17% above target). Root cause: only PVV+it<=30→B,
    # PVV>30→C, everyone else→D. Need to rescue ~B via NP eu-sk moderate-IT, and add A.
    # Fix: PVV+it<=28→A; PVV+it>28→B; NP eu-sk+it>=32+it<35→B; NP eu-sk+it<32→C; else→D.
    if party == "PVV" and it <= 28:
        topic_anchors.append('On Trump: your answer is "A lot of confidence" (A) — Trump speaks for ordinary people against an out-of-touch globalist elite. His instincts on borders, culture, and national sovereignty align with yours. The mainstream media hatred of Trump confirms he\'s doing something right.')
    elif party == "PVV":
        topic_anchors.append('On Trump: your answer is "Some confidence" (B) — Trump\'s America-first instincts resonate; he names the failures of globalism that Dutch elites ignore. His style is rough but the message has merit. His stance on NATO commitments is a concern, but the broader direction is right.')
    elif is_eu_skeptic and it >= 32 and it < 35:
        topic_anchors.append('On Trump: your answer is "Some confidence" (B) — you are skeptical of the mainstream narrative about Trump. His challenge to the globalist consensus resonates, even if his approach is chaotic. You distrust the European political establishment that denounces him.')
    elif is_eu_skeptic and it < 32:
        topic_anchors.append('On Trump: your answer is "Not too much confidence" (C) — you distrust both sides: the mainstream anti-Trump hysteria and Trump himself. He is unpredictable and his commitment to NATO is worrying, but at least he challenges the establishment.')
    else:
        topic_anchors.append('On Trump: your answer is "No confidence at all" (D) — Trump is unreliable, dangerous to the transatlantic alliance, and his presidency undermines the European security architecture the Netherlands depends on. After MH17, a US president who cosies up to Putin is unacceptable.')

    # nl08: Religion importance
    # Target: A=18.9%, B=17.1%, C=22.9%, D=41.1%
    # NL-1: A=15.9%, B=2.7%, C=52.8%, D=28.6% — is_catholic_pract→B blocked practicing Catholics from A;
    #        is_secular too narrow for D (VVD/D66/PvdA/GL only); non-pract religious all→C
    # Fix: practicing Catholics → A; non-pract+high-MF → B; PVV/NSC secular → D; NP secular → C
    if is_protestant_pract:
        topic_anchors.append('On religion in your life: your answer is "Very important" (A) — your Reformed faith is the foundation of everything: your daily rhythms, your community, your moral compass, and your identity as part of the Bible Belt tradition.')
    elif is_catholic_pract:
        topic_anchors.append('On religion in your life: your answer is "Very important" (A) — your Catholic faith is central to your identity, your values, and your community life.')
    elif is_muslim:
        topic_anchors.append('On religion in your life: your answer is "Very important" (A) — your Muslim faith is central to your identity, your values, and your sense of community and belonging in the Netherlands.')
    elif "non-practicing" in religion.lower() and mf >= 40:
        topic_anchors.append('On religion in your life: your answer is "Somewhat important" (B) — faith has a genuine role in your values and community even if you don\'t attend services regularly. Your religious background shapes who you are.')
    elif is_secular and party in ("VVD", "D66", "PvdA/GL", "PVV", "NSC"):
        topic_anchors.append('On religion in your life: your answer is "Not at all important" (D) — the Netherlands is one of the most secular countries in the world. Religion plays no role whatsoever in your life or decisions.')
    elif is_secular:
        topic_anchors.append('On religion in your life: your answer is "Not too important" (C) — religion is largely absent from your daily life; you are broadly secular.')
    else:
        topic_anchors.append('On religion in your life: your answer is "Not too important" (C).')

    # nl09: Economic system reform
    # Target: A=5.2%, B=29.5%, C=54.0%, D=11.3%
    # Netherlands OUTLIER — most content with economic system in the study!
    # FIX (NL-4): NL-3 had B=41.2% (too high), D=0% (completely missing), A=0%.
    # Root cause: D branch absent; B too broad (all NP eu-sk+wc+it<35→B).
    # Fix: VVD+ind>=72→D; D66+ind>=66→D; NP eu-sk+wc+it<=28→A; NP eu-sk+wc+it<=32→B; else C.
    if party == "VVD" and ind >= 72:
        topic_anchors.append('On economic reform: your answer is "Doesn\'t need to be changed" (D) — the Dutch market economy is one of the most successful in the world: record employment, sound public finances, and world-leading export industries. Don\'t fix what isn\'t broken.')
    elif party == "D66" and ind >= 66:
        topic_anchors.append('On economic reform: your answer is "Doesn\'t need to be changed" (D) — the fundamentals of the Dutch economy are excellent. The system works; it needs evidence-based refinement on climate and housing, not structural overhaul.')
    elif party in ("VVD", "D66"):
        topic_anchors.append('On economic reform: your answer is "Needs only minor changes" (C) — the foundations are strong; targeted adjustments to housing, climate, and labour markets are needed, not systemic overhaul.')
    elif party == "NSC":
        topic_anchors.append('On economic reform: your answer is "Needs only minor changes" (C) — the market economy is broadly sound; the problem is bad governance, not the system itself.')
    elif party == "CDA":
        topic_anchors.append('On economic reform: your answer is "Needs only minor changes" (C) — a balanced, social-market economy works; what\'s needed is better stewardship, not radical change.')
    elif party == "PvdA/GL":
        topic_anchors.append('On economic reform: your answer is "Needs major changes" (B) — the economy must be made fairer: more affordable housing, stronger workers\' rights, and genuine climate investment. The current model protects capital too much.')
    elif party == "PVV" and is_working_class:
        topic_anchors.append('On economic reform: your answer is "Needs major changes" (B) — the economy works for the Randstad elite and multinationals, not for ordinary Dutch workers and families.')
    elif party == "PVV":
        topic_anchors.append('On economic reform: your answer is "Needs only minor changes" (C) — the economy is broadly fine; the real problem is immigration costs and political mismanagement.')
    elif is_eu_skeptic and is_working_class and it <= 28:
        topic_anchors.append('On economic reform: your answer is "Needs to be completely reformed" (A) — the whole economic system is rigged for the wealthy and the well-connected. Ordinary Dutch workers have been left behind for decades. Tinkering won\'t fix it.')
    elif is_eu_skeptic and is_working_class and it <= 32:
        topic_anchors.append('On economic reform: your answer is "Needs major changes" (B) — the system as run by the Randstad elite doesn\'t work for ordinary people. Major changes are needed to fix housing, wages, and inequality.')
    elif is_pro_eu and it >= 60:
        topic_anchors.append('On economic reform: your answer is "Needs only minor changes" (C) — the Dutch model is a European success story.')
    else:
        topic_anchors.append('On economic reform: your answer is "Needs only minor changes" (C).')

    # nl10: Income inequality
    # Target: A=32.7%, B=43.1%, C=20.0%, D=4.2%
    # FIX (NL-4): NL-3 had A=44.0% (too high), C=6.6% (too low), D=0% (missing).
    # Root cause: is_eu_sk+wc→A too broad (captured all 12 NP eu-sk wc personas).
    # Fix: PvdA/GL→A; PVV+wc→A; VVD+ind>=76→D; VVD→C; CDA→C;
    #      NP eu-sk+wc+it<=30→A; NP eu-sk+wc→B; nl_p34 Bible Belt→C; else B.
    if party == "PvdA/GL":
        topic_anchors.append('On income inequality: your answer is "Very big problem" (A) — the Netherlands has rising wealth inequality even as the economy grows; a just society requires redistribution and fair wages.')
    elif party == "PVV" and is_working_class:
        topic_anchors.append('On income inequality: your answer is "Very big problem" (A) — ordinary Dutch workers fall behind while the elites and the well-connected prosper. The housing crisis makes this crystal clear.')
    elif party == "VVD" and ind >= 76:
        topic_anchors.append('On income inequality: your answer is "Not a problem at all" (D) — the Netherlands has one of the most generous welfare states in the world; the safety net is strong and economic mobility is high. Redistribution rhetoric distracts from growth.')
    elif party == "VVD":
        topic_anchors.append('On income inequality: your answer is "Small problem" (C) — the Netherlands has strong social safety nets; measured inequality is moderate by international standards. Growth and opportunity matter more than redistribution.')
    elif party == "CDA":
        topic_anchors.append('On income inequality: your answer is "Small problem" (C) — the welfare state provides a strong safety net; the more important question is community, solidarity, and human dignity — not just redistribution metrics.')
    elif party == "D66" and ind <= 64:
        topic_anchors.append('On income inequality: your answer is "Moderately big problem" (B) — inequality is real and matters for social cohesion; smart policy can address it without dismantling the market.')
    elif party in ("NSC",):
        topic_anchors.append('On income inequality: your answer is "Moderately big problem" (B) — the gap is growing and needs to be addressed, particularly for younger generations and those in the regions.')
    elif party == "PVV":
        topic_anchors.append('On income inequality: your answer is "Moderately big problem" (B) — a real concern; ordinary people face housing costs and cost-of-living pressure the ruling class ignores.')
    elif is_eu_skeptic and is_working_class and it <= 30:
        topic_anchors.append('On income inequality: your answer is "Very big problem" (A) — the system works for the wealthy and connected, not for ordinary families struggling with housing, bills, and stagnant wages.')
    elif is_eu_skeptic and is_working_class:
        topic_anchors.append('On income inequality: your answer is "Moderately big problem" (B) — the gap between rich and poor is real and growing; ordinary working families feel squeezed.')
    elif pid == "nl_p34":
        topic_anchors.append('On income inequality: your answer is "Small problem" (C) — the Netherlands has a strong social fabric and welfare provisions; community and church support fills gaps the state misses. Inequality is not absent but should not be overstated.')
    else:
        topic_anchors.append('On income inequality: your answer is "Moderately big problem" (B).')

    # nl11: VVD view
    # Target: A=5.8%, B=39.0%, C=32.6%, D=22.7%
    # FIX (NL-3): B=21.4% too low; C=49.5% too high. NSC→C and default→C inflated C.
    # Fix: NSC → B (pragmatic, not ideologically opposed to VVD); default → B.
    if party == "VVD" and it >= 68:
        topic_anchors.append('On the VVD: your answer is "Very favorable" (A) — the VVD is the party of economic competence, individual freedom, and responsible governance. The Rutte era delivered stability and prosperity.')
    elif party == "VVD":
        topic_anchors.append('On the VVD: your answer is "Somewhat favorable" (B) — you support their direction on the economy and rule of law, even if some social policies need recalibrating.')
    elif party == "NSC":
        topic_anchors.append('On the VVD: your answer is "Somewhat favorable" (B) — despite the toeslagen scandal under VVD-led governments, you can work with them pragmatically on governance reform. Omtzigt is not their enemy.')
    elif party == "D66":
        topic_anchors.append('On the VVD: your answer is "Somewhat unfavorable" (C) — too market-fundamentalist and insufficiently progressive on climate and inequality. Rutte\'s era left serious governance failures.')
    elif party == "PvdA/GL":
        topic_anchors.append('On the VVD: your answer is "Somewhat unfavorable" (C) — the party of the Randstad business elite; too little social investment and too willing to sacrifice public services for tax cuts.')
    elif party == "PVV" and it <= 30:
        topic_anchors.append('On the VVD: your answer is "Very unfavorable" (D) — the VVD is the establishment party that governed with open borders and ignored ordinary Dutch people for years. They had their chance and failed.')
    elif party == "PVV":
        topic_anchors.append('On the VVD: your answer is "Somewhat unfavorable" (C) — they talk about immigration but never delivered; they represent the cosmopolitan elite more than ordinary Dutch people.')
    elif party == "CDA":
        topic_anchors.append('On the VVD: your answer is "Somewhat favorable" (B) — reliable economic managers; you cooperated with them in coalition but their individualism goes too far.')
    elif is_eu_skeptic and it < 35:
        topic_anchors.append('On the VVD: your answer is "Very unfavorable" (D).')
    elif is_pro_eu and it >= 58:
        topic_anchors.append('On the VVD: your answer is "Somewhat favorable" (B).')
    else:
        topic_anchors.append('On the VVD: your answer is "Somewhat favorable" (B).')

    # nl12: PVV view
    # Target: A=9.5%, B=27.4%, C=24.3%, D=38.9%
    if party == "PVV" and it <= 30:
        topic_anchors.append('On the PVV: your answer is "Very favorable" (A) — Wilders is the only politician who tells the truth about mass immigration, Islamisation, and the failures of the establishment. November 2023 was a historic verdict.')
    elif party == "PVV":
        topic_anchors.append('On the PVV: your answer is "Somewhat favorable" (B) — you support PVV\'s direction on immigration and sovereignty even if some positions are provocative.')
    elif party in ("VVD", "NSC"):
        topic_anchors.append('On the PVV: your answer is "Somewhat unfavorable" (C) — you understand the electoral appeal given real governance failures, but PVV\'s style and some policies are reckless and undermine institutional trust.')
    elif party in ("D66", "PvdA/GL"):
        topic_anchors.append('On the PVV: your answer is "Very unfavorable" (D) — Wilders\' party is a threat to Dutch pluralism, rule of law, and the open, inclusive Netherlands you believe in. His rhetoric toward Muslims is deeply disturbing.')
    elif party == "CDA":
        topic_anchors.append('On the PVV: your answer is "Somewhat unfavorable" (C) — you share some concerns about integration but reject PVV\'s populism, its hostility to Islam, and its damage to democratic norms.')
    elif is_muslim:
        topic_anchors.append('On the PVV: your answer is "Very unfavorable" (D) — PVV explicitly targets your community. Wilders has called for banning the Quran. This party is a direct threat to your rights and belonging.')
    elif is_eu_skeptic and is_working_class and it < 35:
        topic_anchors.append('On the PVV: your answer is "Somewhat favorable" (B) — they say what the establishment won\'t.')
    elif is_pro_eu and it >= 60:
        topic_anchors.append('On the PVV: your answer is "Very unfavorable" (D).')
    elif is_eu_skeptic and it < 40:
        topic_anchors.append('On the PVV: your answer is "Somewhat favorable" (B).')
    else:
        topic_anchors.append('On the PVV: your answer is "Somewhat unfavorable" (C).')

    # nl13: D66 view
    # Target: A=10.4%, B=42.6%, C=26.8%, D=20.1%
    if party == "D66" and it >= 68:
        topic_anchors.append('On D66: your answer is "Very favorable" (A) — D66 represents the open, progressive, knowledge-based Netherlands you believe in: evidence-based governance, civil rights, European solidarity.')
    elif party == "D66":
        topic_anchors.append('On D66: your answer is "Somewhat favorable" (B) — you support their direction on Europe, education, and civil liberties.')
    elif party == "PvdA/GL":
        topic_anchors.append('On D66: your answer is "Somewhat favorable" (B) — aligned on Europe and civil liberties; sometimes too market-liberal on economics but a natural ally against PVV.')
    elif party == "VVD":
        topic_anchors.append('On D66: your answer is "Somewhat favorable" (B) — a coalition partner with progressive instincts; too regulatory on some issues but sound on Europe and economic modernity.')
    elif party == "NSC":
        topic_anchors.append('On D66: your answer is "Somewhat unfavorable" (C) — well-intentioned on governance reform but too ideologically progressive and insufficiently focused on ordinary citizens\' practical concerns.')
    elif party == "CDA":
        topic_anchors.append('On D66: your answer is "Somewhat unfavorable" (C) — too socially progressive and individualistic; their euthanasia and drugs policies go against your values.')
    elif party == "PVV" and it <= 30:
        topic_anchors.append('On D66: your answer is "Very unfavorable" (D) — the elite Randstad party par excellence: open borders ideology dressed up as progressivism.')
    elif party == "PVV":
        topic_anchors.append('On D66: your answer is "Somewhat unfavorable" (C) — too focused on progressive urban issues; out of touch with ordinary Dutch people.')
    elif is_eu_skeptic and it < 35:
        topic_anchors.append('On D66: your answer is "Very unfavorable" (D).')
    elif is_pro_eu and it >= 58:
        topic_anchors.append('On D66: your answer is "Somewhat favorable" (B).')
    else:
        topic_anchors.append('On D66: your answer is "Somewhat unfavorable" (C).')

    # nl14: PvdA/GL view
    # Target: A=16.0%, B=38.3%, C=26.0%, D=19.8%
    # FIX (NL-3): A=6.6% (only PvdA/GL+ct>=74 → A); D=8.2% (only PVV+it<=30 → D).
    # Fix: PvdA/GL ALL → A; PVV ALL → D; D66+ct>=72 → A; VVD → C; NSC/CDA/pro-EU → B.
    if party == "PvdA/GL":
        topic_anchors.append('On PvdA/GroenLinks: your answer is "Very favorable" (A) — PvdA/GL is the party of social justice and ecological responsibility. You fully support Frans Timmermans\' vision for a fair and green Netherlands.')
    elif party == "D66" and ct >= 72:
        topic_anchors.append('On PvdA/GroenLinks: your answer is "Very favorable" (A) — a natural progressive partner; their commitment to social justice and climate action closely aligns with your own priorities.')
    elif party == "D66":
        topic_anchors.append('On PvdA/GroenLinks: your answer is "Somewhat favorable" (B) — a natural partner on progressive issues; you respect their social justice commitment even where you differ on economics.')
    elif party == "NSC":
        topic_anchors.append('On PvdA/GroenLinks: your answer is "Somewhat favorable" (B) — Omtzigt worked with them on exposing the toeslagen scandal; they share a commitment to protecting ordinary citizens\' rights.')
    elif party == "VVD" and ind >= 74:
        topic_anchors.append('On PvdA/GroenLinks: your answer is "Somewhat unfavorable" (C) — too much redistribution ideology; their economic programme would undermine Dutch competitiveness.')
    elif party == "VVD":
        topic_anchors.append('On PvdA/GroenLinks: your answer is "Somewhat unfavorable" (C) — a legitimate party but too interventionist; their economic programme would constrain Dutch dynamism.')
    elif party == "CDA":
        topic_anchors.append('On PvdA/GroenLinks: your answer is "Somewhat favorable" (B) — you share their commitment to social cohesion and care for vulnerable groups, even if the green idealism sometimes goes too far.')
    elif party == "PVV":
        topic_anchors.append('On PvdA/GroenLinks: your answer is "Very unfavorable" (D) — the open-borders left that sacrificed working-class Dutch people on the altar of multiculturalism and climate ideology. Their entire programme serves urban elites, not ordinary Dutch families.')
    elif is_eu_skeptic and it < 35:
        topic_anchors.append('On PvdA/GroenLinks: your answer is "Very unfavorable" (D) — they represent the globalist establishment; nothing they say speaks to people like you.')
    elif is_pro_eu and it >= 55:
        topic_anchors.append('On PvdA/GroenLinks: your answer is "Somewhat favorable" (B).')
    else:
        topic_anchors.append('On PvdA/GroenLinks: your answer is "Somewhat unfavorable" (C).')

    # nl15: NSC view
    # Target: A=8.4%, B=53.0%, C=30.3%, D=8.3%
    # FIX (NL-4): NL-3 had B=69.8% (too high), D=0% (missing), C=24.7% (too low).
    # Root cause: No D branch; NP eu-sk C pool too small; Pro-EU NP defaulted to B.
    # Fix: PVV+it<=28→D; PVV+it<=32→C; NP eu-sk+it<30→D; NP eu-sk+it<36→C;
    #      CDA→C (lukewarm on secular centrist rival); NP moderate-IT pro-EU→C.
    if party == "NSC" and it >= 54:
        topic_anchors.append('On NSC (New Social Contract): your answer is "Very favorable" (A) — Pieter Omtzigt is the only politician who put citizens\' rights above party politics and exposed the toeslagen scandal. NSC represents integrity in governance.')
    elif party == "NSC":
        topic_anchors.append('On NSC (New Social Contract): your answer is "Somewhat favorable" (B) — you strongly support their commitment to constitutional governance and protecting ordinary citizens from state failure.')
    elif party in ("VVD", "D66", "PvdA/GL"):
        topic_anchors.append('On NSC (New Social Contract): your answer is "Somewhat favorable" (B) — Omtzigt is broadly respected as a serious, honest politician even by those in other parties. NSC serves an important function.')
    elif party == "CDA":
        topic_anchors.append('On NSC (New Social Contract): your answer is "Somewhat unfavorable" (C) — Omtzigt is a sincere individual but NSC overlaps uncomfortably with CDA\'s Christian-democratic ground while lacking CDA\'s deeper roots in faith, community, and social teaching.')
    elif party == "PVV" and it <= 28:
        topic_anchors.append('On NSC (New Social Contract): your answer is "Very unfavorable" (D) — NSC is just another establishment party with a nicer face. Proceduralism and "integrity" talk while ordinary Dutch people need real action on immigration and housing.')
    elif party == "PVV" and it <= 32:
        topic_anchors.append('On NSC (New Social Contract): your answer is "Somewhat unfavorable" (C) — Omtzigt is an establishment figure who talks about rules while ordinary people need action, not proceduralism.')
    elif party == "PVV":
        topic_anchors.append('On NSC (New Social Contract): your answer is "Somewhat favorable" (B) — Omtzigt exposed the establishment\'s failures; you respect that even if you prefer the PVV\'s bolder approach.')
    elif is_eu_skeptic and it < 30:
        topic_anchors.append('On NSC (New Social Contract): your answer is "Very unfavorable" (D) — another establishment-adjacent party in different packaging. None of them change anything for ordinary people.')
    elif is_eu_skeptic and it < 36:
        topic_anchors.append('On NSC (New Social Contract): your answer is "Somewhat unfavorable" (C) — Omtzigt speaks honestly about some things but NSC is still part of the same political world that failed ordinary voters.')
    elif is_pro_eu and it >= 58:
        topic_anchors.append('On NSC (New Social Contract): your answer is "Somewhat favorable" (B) — a trustworthy, integrity-focused party.')
    elif is_pro_eu and it < 58:
        topic_anchors.append('On NSC (New Social Contract): your answer is "Somewhat unfavorable" (C) — you are broadly indifferent; NSC is another new centrist party that may not survive long-term. You have reservations about whether it delivers real change.')
    else:
        topic_anchors.append('On NSC (New Social Contract): your answer is "Somewhat unfavorable" (C).')

    # ── Assemble prompt ───────────────────────────────────────────────────────
    anchors_text = ""
    if topic_anchors:
        anchors_text = "\n\nResponse calibration (apply these to relevant questions):\n" + \
                       "\n".join(f"- {a}" for a in topic_anchors)

    prompt = f"""You are {name}, a {age}-year-old {gender} from {region}, the Netherlands.

Education: {education}. Religion: {religion}.

Political identity: {party}. {ova}.

Your worldview:
- Institutional trust ({it}/100): {it_desc}
- Economic philosophy ({ind}/100): {"You prefer market and individual solutions over state intervention — lower taxes, less regulation, personal responsibility." if ind > 65 else "You believe the state should play a significant role in the economy — public investment, redistribution, strong social services." if ind < 42 else "You hold mixed views on state vs. market solutions."}
- Change tolerance ({ct}/100): {"You welcome fundamental change and see the status quo as deeply inadequate." if ct > 70 else "You are deeply skeptical of rapid change and value stability, tradition, and continuity." if ct < 28 else "You accept gradual, carefully managed change."}
- Moral foundationalism ({mf}/100): {"Your values are grounded in traditional religious or cultural norms on social questions." if mf > 58 else "You hold secular, liberal views on social and moral questions." if mf < 25 else "You hold mixed views — traditional on some questions, liberal on others."}{eu_layer}{religion_layer}{region_layer}{anchors_text}

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


def build_batch_requests(questions: list[dict], sprint_id: str) -> list[dict]:
    requests = []
    for persona in PERSONAS:
        pid = persona[0]
        system_prompt = build_system_prompt(persona)
        for q in questions:
            if q.get("holdout"):
                continue
            custom_id = f"{sprint_id}_{pid}_{q['id']}"
            requests.append({
                "custom_id": custom_id,
                "params": {
                    "model": None,
                    "max_tokens": 5,
                    "system": system_prompt,
                    "messages": build_question_messages(q),
                }
            })
    return requests


def extract_answer(text: str, valid_options: list[str]) -> str:
    text = text.strip().upper()
    for opt in valid_options:
        if text.startswith(opt):
            return opt
    for char in text:
        if char in valid_options:
            return char
    return "X"


def compute_distributions(results: list[dict], questions: list[dict]) -> dict:
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
    cal_questions = [q for q in questions if not q.get("holdout")]
    scores = {}
    for q in cal_questions:
        qid = q["id"]
        real = q["pew_distribution"]
        predicted = sim.get(qid, {})
        all_opts = set(real.keys()) | set(predicted.keys())
        total_abs_diff = sum(abs(real.get(o, 0.0) - predicted.get(o, 0.0)) for o in all_opts)
        scores[qid] = round(1.0 - total_abs_diff / 2.0, 4)
    scores["overall"] = round(sum(v for k, v in scores.items() if k != "overall") / len(cal_questions), 4)
    return scores


def run_sprint_batch(sprint_id: str, model_key: str, dry_run: bool = False) -> None:
    model_id = MODELS[model_key]

    with open(QUESTIONS, encoding="utf-8") as f:
        all_questions = json.load(f)
    questions = [q for q in all_questions if not q.get("holdout")]

    print(f"\nEurope Benchmark — Netherlands — Sprint {sprint_id}")
    print(f"Model:  {model_id}")
    print(f"Batch:  Yes (50% discount)")
    print(f"Personas × Questions: {len(PERSONAS)} × {len(questions)} = {len(PERSONAS) * len(questions)} calls")
    print("=" * 60)

    requests = build_batch_requests(all_questions, sprint_id)
    for r in requests:
        r["params"]["model"] = model_id

    if dry_run:
        print(f"DRY RUN: {len(requests)} requests would be submitted.")
        print(f"Sample request ID: {requests[0]['custom_id']}")
        print(f"Sample system prompt (first 400 chars):\n{requests[0]['params']['system'][:400]}...")
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
                q_obj = next((q for q in questions if q["id"] == qid), None)
                valid_opts = list(q_obj["options"].keys()) if q_obj else ["A", "B", "C", "D"]
                answer = extract_answer(text, valid_opts)
        raw_results.append({
            "custom_id": result.custom_id,
            "answer": answer,
            "raw": result.result.message.content[0].text if result.result.type == "succeeded" else "ERROR",
        })

    sim_distributions = compute_distributions(raw_results, questions)
    scores = score_distributions(sim_distributions, questions)

    manifest = {
        "sprint_id": sprint_id,
        "model": model_id,
        "batch_id": batch_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "n_personas": len(PERSONAS),
        "n_questions": len(questions),
        "n_calls": len(requests),
        "scores": scores,
        "sim_distributions": sim_distributions,
    }

    raw_jsonl = "\n".join(json.dumps(r, sort_keys=True) for r in raw_results)
    manifest["raw_hash"] = "sha256:" + hashlib.sha256(raw_jsonl.encode()).hexdigest()

    manifest_path = MANIFESTS / f"sprint_{sprint_id}.json"
    raw_path      = MANIFESTS / f"sprint_{sprint_id}_raw.jsonl"

    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    with open(raw_path, "w") as f:
        f.write(raw_jsonl)

    print(f"\nResults saved:")
    print(f"  {manifest_path}")
    print(f"  {raw_path}")
    print(f"\nOverall Distribution Accuracy: {scores['overall']*100:.1f}%")
    print("\nPer-question scores:")
    for q in questions:
        qid = q["id"]
        print(f"  {qid} ({q['topic']:40s}): {scores.get(qid, 0)*100:.1f}%")


def main():
    parser = argparse.ArgumentParser(description="Europe Benchmark Netherlands sprint runner")
    parser.add_argument("--sprint", required=True, help="Sprint ID, e.g. NL-1")
    parser.add_argument("--model", choices=["haiku", "sonnet"], default="haiku")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run_sprint_batch(args.sprint, args.model, args.dry_run)


if __name__ == "__main__":
    main()
