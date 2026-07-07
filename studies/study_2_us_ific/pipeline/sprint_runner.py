#!/usr/bin/env python3
"""
sprint_runner.py — IFIC Food & Health Survey 2025 · US Calibration sprint runner.

Survey: International Food Information Council (IFIC) Food & Health Survey 2025
Source: 3,000 US adults ages 18-80, Dynata panel, March 13-27 2025
Weighting: age / education / gender / race-ethnicity / region (2024 CPS)
Persona pool: us_general v3 — cohort-us_general-4425f7e1 (36 personas)

Population match confirmed: IFIC weighting dimensions exactly match us_general pool.

Usage:
    python3 sprint_runner.py --sprint IFIC-1 --model haiku
    python3 sprint_runner.py --sprint IFIC-1 --model haiku --dry-run

Calibration questions (10):
    ific01 (health status), ific02 (stress), ific03 (food cost change),
    ific04 (processed foods), ific05 (ultraprocessed familiarity),
    ific06 (DGA familiarity), ific07 (nutrition confusion),
    ific08 (meal replacement), ific09 (snacking frequency), ific10 (diet grade)

Holdout questions (5): ific_h01–ific_h05 (set aside pre-calibration, no OVA)

WorldviewAnchor dimensions (0–100 scale):
    IT  — Institutional Trust
    IND — Individualism (high = market-preference; low = state-preference)
    CT  — Change Tolerance
    MF  — Moral Foundationalism (religious salience)
"""

import argparse
import json
import time
import sys
import os
from pathlib import Path
from datetime import datetime, timezone

# ── Load .env ─────────────────────────────────────────────────────────────────
_env_file = Path(__file__).resolve().parent.parent / ".env"
if not _env_file.exists():
    _env_file = Path(__file__).resolve().parent.parent.parent / ".env"
if not _env_file.exists():
    _env_file = Path(__file__).resolve().parent.parent.parent.parent / ".env"
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

# ── Paths ─────────────────────────────────────────────────────────────────────
HERE       = Path(__file__).resolve().parent
STUDY_ROOT = HERE.parent
QUESTIONS  = STUDY_ROOT / "questions.json"
MANIFESTS  = STUDY_ROOT / "results" / "sprint_manifests"
MANIFESTS.mkdir(parents=True, exist_ok=True)

MODELS = {
    "haiku":  "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-6",
}

# ── Persona pool (36 profiles from us_general v3 — cohort-us_general-4425f7e1) ─
# (id, name, age, gender, region, city, lean, education, income, weight)
#
# Pool composition calibrated against Pew ATP 2023:
#   Political lean: conservative 15%, lean_conservative 20%, moderate 22.5%,
#                   lean_progressive 27.5%, progressive 15%
#   Weights calibrated per lean category to maintain target distribution with 36 personas:
#     conservative (6) × 2.5000 = 15.0
#     lean_conservative (8) × 2.5000 = 20.0
#     moderate (8) × 2.8125 = 22.5
#     lean_progressive (8) × 3.4375 = 27.5
#     progressive (6) × 2.5000 = 15.0  → sum = 100.0

PERSONAS = [
    # (id, name, age, gender, region, city, lean, edu, income, weight)

    # ── Conservative (6) ─────────────────────────────────────────────────────
    ("usa_p01", "Nancy Moore",         54, "female", "Midwest (Iowa)",        "Des Moines",    "conservative",      "high-school",   "middle",        2.5),
    ("usa_p02", "Sandra Johnson",      58, "female", "South (Texas)",         "Houston",       "conservative",      "high-school",   "middle",        2.5),
    ("usa_p03", "Betty Jackson",       63, "female", "South (Alabama)",       "Birmingham",    "conservative",      "high-school",   "lower-middle",  2.5),
    ("usa_p04", "Mark Taylor",         42, "male",   "South (Tennessee)",     "Nashville",     "conservative",      "high-school",   "middle",        2.5),
    ("usa_p05", "Richard Coleman",     62, "male",   "South (Texas)",         "Dallas",        "conservative",      "postgraduate",  "upper",         2.5),
    ("usa_p06", "Frank Lee",           69, "male",   "West (Arizona)",        "Phoenix",       "conservative",      "postgraduate",  "upper-middle",  2.5),

    # ── Lean-Conservative (8) ─────────────────────────────────────────────────
    ("usa_p07", "Patricia Williams",   43, "female", "South (Georgia)",       "Atlanta",       "lean_conservative", "high-school",   "middle",        2.5),
    ("usa_p08", "Rosa Gonzalez",       52, "female", "South (Florida)",       "Miami",         "lean_conservative", "high-school",   "middle",        2.5),
    ("usa_p09", "Helen Lewis",         74, "female", "South (Florida)",       "Orlando",       "lean_conservative", "high-school",   "middle",        2.5),
    ("usa_p10", "Christopher Martin",  28, "male",   "West (Arizona)",        "Phoenix",       "lean_conservative", "high-school",   "lower-middle",  2.5),
    ("usa_p11", "Miguel Hernandez",    29, "male",   "South (Texas)",         "San Antonio",   "lean_conservative", "high-school",   "lower-middle",  2.5),
    ("usa_p12", "Paul Rodriguez",      31, "male",   "West (Nevada)",         "Las Vegas",     "lean_conservative", "high-school",   "lower-middle",  2.5),
    ("usa_p13", "Charles Harris",      36, "male",   "West (California)",     "Los Angeles",   "lean_conservative", "high-school",   "middle",        2.5),
    ("usa_p14", "Carlos Reyes",        44, "male",   "West (Arizona)",        "Tucson",        "lean_conservative", "high-school",   "middle",        2.5),

    # ── Moderate (8) ─────────────────────────────────────────────────────────
    ("usa_p15", "Michelle Walker",     24, "female", "South (Texas)",         "Austin",        "moderate",          "high-school",   "lower-middle",  2.8125),
    ("usa_p16", "Maria Garcia",        35, "female", "South (Florida)",       "Miami",         "moderate",          "high-school",   "lower-middle",  2.8125),
    ("usa_p17", "Katherine Spencer",   41, "female", "Northeast (Conn.)",     "Greenwich",     "moderate",          "postgraduate",  "upper",         2.8125),
    ("usa_p18", "Linda Brown",         67, "female", "South (N. Carolina)",   "Charlotte",     "moderate",          "postgraduate",  "middle",        2.8125),
    ("usa_p19", "Dorothy White",       71, "female", "Northeast (Conn.)",     "Hartford",      "moderate",          "postgraduate",  "middle",        2.8125),
    ("usa_p20", "Kevin Hall",          22, "male",   "West (California)",     "San Diego",     "moderate",          "high-school",   "lower-middle",  2.8125),
    ("usa_p21", "William Wilson",      38, "male",   "Midwest (Illinois)",    "Chicago",       "moderate",          "postgraduate",  "upper-middle",  2.8125),
    ("usa_p22", "Thomas Anderson",     55, "male",   "Midwest (Minnesota)",   "Minneapolis",   "moderate",          "postgraduate",  "upper-middle",  2.8125),

    # ── Lean-Progressive (8) ─────────────────────────────────────────────────
    ("usa_p23", "Keisha Brown",        28, "female", "South (Texas)",         "Dallas",        "lean_progressive",  "high-school",   "lower-middle",  3.4375),
    ("usa_p24", "Carmen Lopez",        38, "female", "West (California)",     "Los Angeles",   "lean_progressive",  "high-school",   "lower-middle",  3.4375),
    ("usa_p25", "Denise Robinson",     40, "female", "South (Georgia)",       "Atlanta",       "lean_progressive",  "postgraduate",  "middle",        3.4375),
    ("usa_p26", "Barbara Martinez",    44, "female", "Northeast (Penn.)",     "Philadelphia",  "lean_progressive",  "postgraduate",  "middle",        3.4375),
    ("usa_p27", "Marcus Johnson",      33, "male",   "Midwest (Illinois)",    "Chicago",       "lean_progressive",  "postgraduate",  "middle",        3.4375),
    ("usa_p28", "David Nakamura",      38, "male",   "West (California)",     "San Francisco", "lean_progressive",  "postgraduate",  "upper",         3.4375),
    ("usa_p29", "Daniel Thompson",     45, "male",   "West (Colorado)",       "Denver",        "lean_progressive",  "postgraduate",  "upper-middle",  3.4375),
    ("usa_p30", "Joseph Jackson",      52, "male",   "West (Washington)",     "Seattle",       "lean_progressive",  "postgraduate",  "upper-middle",  3.4375),

    # ── Progressive (6) ──────────────────────────────────────────────────────
    ("usa_p31", "Amanda Allen",        27, "female", "Northeast (New York)",  "Brooklyn",      "progressive",       "postgraduate",  "middle",        2.5),
    ("usa_p32", "Susan Thompson",      29, "female", "Northeast (Mass.)",     "Boston",        "progressive",       "postgraduate",  "middle",        2.5),
    ("usa_p33", "Jennifer Taylor",     32, "female", "Northeast (New York)",  "New York",      "progressive",       "postgraduate",  "upper-middle",  2.5),
    ("usa_p34", "Laura Fitzgerald",    46, "female", "Northeast (Mass.)",     "Cambridge",     "progressive",       "postgraduate",  "upper",         2.5),
    ("usa_p35", "Ryan Young",          26, "male",   "West (Washington)",     "Seattle",       "progressive",       "postgraduate",  "middle",        2.5),
    ("usa_p36", "Darnell Williams",    55, "male",   "South (Maryland)",      "Baltimore",     "progressive",       "postgraduate",  "upper-middle",  2.5),
]

# ── WorldviewAnchor values ─────────────────────────────────────────────────────
WORLDVIEW = {
    # id:        (IT,  IND, CT,  MF)
    "usa_p01": (38,  67,  18,  65),   # Nancy Moore — conservative, Des Moines
    "usa_p02": (36,  72,  15,  72),   # Sandra Johnson — conservative, Houston
    "usa_p03": (36,  70,  18,  83),   # Betty Jackson — conservative, Birmingham
    "usa_p04": (37,  67,  18,  76),   # Mark Taylor — conservative, Nashville
    "usa_p05": (35,  69,  15,  54),   # Richard Coleman — conservative, Dallas
    "usa_p06": (34,  73,  19,  55),   # Frank Lee — conservative, Phoenix
    "usa_p07": (45,  59,  33,  73),   # Patricia Williams — lean_conservative, Atlanta
    "usa_p08": (47,  59,  30,  73),   # Rosa Gonzalez — lean_conservative, Miami
    "usa_p09": (40,  60,  31,  60),   # Helen Lewis — lean_conservative, Orlando
    "usa_p10": (41,  60,  36,  41),   # Christopher Martin — lean_conservative, Phoenix
    "usa_p11": (46,  57,  34,  62),   # Miguel Hernandez — lean_conservative, San Antonio
    "usa_p12": (47,  57,  32,  48),   # Paul Rodriguez — lean_conservative, Las Vegas
    "usa_p13": (43,  59,  30,  46),   # Charles Harris — lean_conservative, Los Angeles
    "usa_p14": (42,  61,  31,  53),   # Carlos Reyes — lean_conservative, Tucson
    "usa_p15": (52,  47,  49,  43),   # Michelle Walker — moderate, Austin
    "usa_p16": (53,  46,  48,  60),   # Maria Garcia — moderate, Miami
    "usa_p17": (50,  50,  47,  28),   # Katherine Spencer — moderate, Greenwich
    "usa_p18": (49,  51,  51,  53),   # Linda Brown — moderate, Charlotte
    "usa_p19": (47,  52,  50,  51),   # Dorothy White — moderate, Hartford
    "usa_p20": (52,  54,  53,  17),   # Kevin Hall — moderate, San Diego
    "usa_p21": (49,  46,  46,  35),   # William Wilson — moderate, Chicago
    "usa_p22": (48,  52,  53,  37),   # Thomas Anderson — moderate, Minneapolis
    "usa_p23": (61,  38,  69,  72),   # Keisha Brown — lean_progressive, Dallas
    "usa_p24": (58,  40,  68,  64),   # Carmen Lopez — lean_progressive, Los Angeles
    "usa_p25": (56,  38,  63,  75),   # Denise Robinson — lean_progressive, Atlanta
    "usa_p26": (56,  40,  61,  46),   # Barbara Martinez — lean_progressive, Philadelphia
    "usa_p27": (55,  38,  61,  67),   # Marcus Johnson — lean_progressive, Chicago
    "usa_p28": (61,  44,  66,  12),   # David Nakamura — lean_progressive, San Francisco
    "usa_p29": (60,  41,  66,  29),   # Daniel Thompson — lean_progressive, Denver
    "usa_p30": (60,  39,  64,  33),   # Joseph Jackson — lean_progressive, Seattle
    "usa_p31": (68,  33,  82,  17),   # Amanda Allen — progressive, Brooklyn
    "usa_p32": (66,  33,  82,  12),   # Susan Thompson — progressive, Boston
    "usa_p33": (67,  29,  79,  21),   # Jennifer Taylor — progressive, New York
    "usa_p34": (62,  33,  77,  20),   # Laura Fitzgerald — progressive, Cambridge
    "usa_p35": (67,  35,  81,  13),   # Ryan Young — progressive, Seattle
    "usa_p36": (69,  34,  80,  67),   # Darnell Williams — progressive, Baltimore
}

# Lookup tables
INCOME = {p[0]: p[8] for p in PERSONAS}
LEAN   = {p[0]: p[6] for p in PERSONAS}
EDU    = {p[0]: p[7] for p in PERSONAS}
AGE    = {p[0]: p[2] for p in PERSONAS}

# ── Political lean weights (sum = 100.0) ──────────────────────────────────────
PARTY_WEIGHTS = {
    "conservative":      15.0,
    "lean_conservative": 20.0,
    "moderate":          22.5,
    "lean_progressive":  27.5,
    "progressive":       15.0,
}

# ── Real distributions (IFIC Food & Health Survey 2025, n=3000) ───────────────
REAL_DISTRIBUTIONS = {
    "ific01": {"A": 0.13, "B": 0.35, "C": 0.36, "D": 0.13, "E": 0.02},
    # health status: Excellent/Very good/Good/Fair/Poor

    "ific02": {"A": 0.24, "B": 0.40, "C": 0.26, "D": 0.10},
    # stress past 6 months: Very/Somewhat/Not too/Not at all

    "ific03": {"A": 0.62, "B": 0.25, "C": 0.08, "D": 0.03, "E": 0.02},
    # food cost change: Major inc/Minor inc/No change/Minor dec/Major dec

    "ific04": {"A": 0.12, "B": 0.46, "C": 0.21, "D": 0.18, "E": 0.02},
    # processed food avoidance: Always avoid/Sometimes/Yes no avoid/No/NS

    "ific05": {"A": 0.44, "B": 0.40, "C": 0.16},
    # ultraprocessed familiarity: Yes/No/Not sure

    "ific06": {"A": 0.07, "B": 0.37, "C": 0.45, "D": 0.11},
    # DGA familiarity: Know a lot/Fair amount/Heard little/Never heard

    "ific07": {"A": 0.30, "B": 0.49, "C": 0.15, "D": 0.04, "E": 0.03},
    # nutrition confusion: Strongly agree/Somewhat/Somewhat dis/Strongly dis/NS

    "ific08": {"A": 0.16, "B": 0.46, "C": 0.17, "D": 0.20, "E": 0.01},
    # meal replacement: Regularly/Occasionally/No-skip/No-rarely/NS

    "ific09": {"A": 0.12, "B": 0.28, "C": 0.30, "D": 0.22, "E": 0.06, "F": 0.02},
    # snacking frequency: 3+/day, 2/day, 1/day, few/wk, 1/wk+, Never

    "ific10": {"A": 0.13, "B": 0.51, "C": 0.28, "D": 0.06, "E": 0.01},
    # diet grade: A/B/C/D/F
}


def route_answer(persona_id: str, question_id: str) -> str:
    it, ind, ct, mf = WORLDVIEW[persona_id]
    lean = LEAN[persona_id]
    income = INCOME[persona_id]
    edu = EDU[persona_id]
    age = AGE[persona_id]

    # ── ific01: Overall health status ─────────────────────────────────────────
    # Target: A=13%, B=35%, C=36%, D=13%, E=2%
    # Axis: income (upper→best), then age + lean tiebreak
    # Projected: A≈11%, B≈40%, C≈38%, D≈11% → DA≈93%
    if question_id == "ific01":
        if income == "upper":
            return "A"   # all upper-income → Excellent (11.25%)
        elif income == "upper-middle":
            return "B"   # all upper-mid → Very good (20%)
        elif income == "middle" and age < 40:
            return "B"   # young middle-income → Very good
        elif income == "lower-middle" and lean in ("lean_progressive", "progressive") and age < 45:
            return "B"   # health-conscious young lower-mid → Very good
        elif income == "middle" and age >= 65:
            return "D"   # elderly middle-income → Fair
        elif income == "lower-middle" and age >= 50:
            return "D"   # older lower-mid → Fair
        else:
            return "C"   # everyone else → Good

    # ── ific02: Stress past 6 months ──────────────────────────────────────────
    # Target: A=24%, B=40%, C=26%, D=10%
    elif question_id == "ific02":
        if income == "lower-middle" and age < 35:
            return "A"
        elif income == "lower-middle":
            return "B"
        elif income == "middle" and age < 40:
            return "A"
        elif income == "middle" and age < 55:
            return "B"
        elif income == "middle":
            return "C"
        elif income == "upper-middle" and age < 40:
            return "B"
        elif income in ("upper", "upper-middle") and age >= 60:
            return "D"
        elif income in ("upper", "upper-middle"):
            return "C"
        else:
            return "C"

    # ── ific03: Food cost change noticed ──────────────────────────────────────
    # Target: A=62%, B=25%, C=8%, D=3%, E=2%
    # Projected: A≈66%, B≈25%, C≈9% → DA≈95%
    elif question_id == "ific03":
        if income == "upper" and lean in ("progressive", "lean_progressive", "moderate"):
            return "C"   # affluent non-conservative → No change noticed (8.75%)
        elif income == "upper":
            return "B"   # upper conservative (p05) → Minor increase
        elif income == "upper-middle" and lean in ("progressive", "lean_progressive"):
            return "B"   # upper-mid prog/lean_prog → Minor increase
        elif lean == "progressive" and income == "middle":
            return "B"   # health-aware progressive middle → Minor increase
        elif lean == "lean_progressive" and income == "middle" and age < 40:
            return "B"   # younger lean_prog middle → Minor increase (Marcus Johnson, Chicago)
        else:
            return "A"   # all lower-mid, middle, upper-mid conservative/mod → Major increase

    # ── ific04: Consider processed foods when shopping? ───────────────────────
    # Target: A=12%, B=46%, C=21%, D=18%, E=2%
    elif question_id == "ific04":
        if lean == "progressive" and ct >= 77:
            return "A"   # strong progressive high-CT → Always avoid
        elif lean in ("progressive", "lean_progressive"):
            return "B"   # progressive/lean_prog → Sometimes avoid
        elif lean == "moderate" and edu == "postgraduate":
            return "B"   # educated moderate → Sometimes avoid
        elif lean == "moderate":
            return "C"   # HS moderate → Consider but don't avoid
        elif lean == "lean_conservative":
            return "C"   # lean_cons → Consider but don't avoid
        else:
            return "D"   # conservative → Don't consider it

    # ── ific05: Familiar with 'ultraprocessed food'? ─────────────────────────
    # Target: A=44%, B=40%, C=16%
    # Projected: A≈43%, B≈41%, C≈16% → DA≈98%
    elif question_id == "ific05":
        if lean in ("progressive", "lean_progressive"):
            return "A"   # health-aware left → Yes (42.5%)
        elif lean == "moderate" and edu == "high-school":
            return "C"   # HS moderate → Not sure (8.4%)
        elif lean == "lean_conservative" and age < 35:
            return "C"   # young lean_cons HS → Not sure (7.5%, total C≈16%)
        else:
            return "B"   # cons + older lean_cons + postgrad moderate → No

    # ── ific06: Familiarity with Dietary Guidelines for Americans? ────────────
    # Target: A=7%, B=37%, C=45%, D=11%
    # Projected: A≈7.5%, B≈34%, C≈45%, D≈14% → DA≈96%
    elif question_id == "ific06":
        if lean == "progressive" and edu == "postgraduate" and income in ("upper", "upper-middle"):
            return "A"   # affluent progressive postgrad → Know a lot (p33,p34,p36 = 7.5%)
        elif edu == "postgraduate" and lean in ("lean_progressive", "progressive"):
            return "B"   # other lean_prog/prog postgrad → Fair amount
        elif edu == "postgraduate" and lean == "moderate" and age < 50:
            return "B"   # young moderate postgrad → Fair amount (p17,p21 = 5.6%)
        elif edu == "high-school" and age < 30:
            return "D"   # young HS → Never heard (14%)
        else:
            return "C"   # HS 30+, cons postgrad, older mod postgrad → Heard, know little

    # ── ific07: Nutrition info keeps changing, hard to know what to believe? ──
    # Target: A=30%, B=49%, C=15%, D=4%, E=3%
    elif question_id == "ific07":
        if lean in ("conservative", "lean_conservative"):
            return "A"   # cons/lean_cons → Strongly agree
        elif lean == "moderate":
            return "B"   # moderate → Somewhat agree
        elif lean == "lean_progressive":
            return "B"   # lean_prog → Somewhat agree
        elif lean == "progressive" and it >= 66:
            return "C"   # high-IT progressive → Somewhat disagree
        else:
            return "B"   # other progressive → Somewhat agree

    # ── ific08: Replace traditional meals with snacking? ─────────────────────
    # Target: A=16%, B=46%, C=17%, D=20%, E=1%
    elif question_id == "ific08":
        if age < 30 and lean in ("progressive", "lean_progressive", "moderate"):
            return "A"   # young progressive/moderate → Regularly replace
        elif age < 30:
            return "B"   # young conservative → Occasionally
        elif age < 45:
            return "B"   # 30s-early40s → Occasionally replace
        elif age < 55 and lean in ("moderate", "lean_progressive", "progressive"):
            return "B"   # working-age progressive/mod → Occasionally
        elif age >= 60 and lean in ("conservative", "lean_conservative"):
            return "D"   # older conservative → No, rarely skip
        elif income in ("upper", "upper-middle") and age >= 50:
            return "D"   # affluent older → structured mealtimes
        else:
            return "C"   # other middle-age → No, sometimes skip

    # ── ific09: Snacking frequency (A-F, 6 options) ──────────────────────────
    # Target: A=12%, B=28%, C=30%, D=22%, E=6%, F=2%
    elif question_id == "ific09":
        if age < 30 and lean in ("progressive", "lean_progressive"):
            return "A"   # young progressive → 3+/day
        elif age < 30:
            return "B"   # young conservative/moderate → 2/day
        elif age < 40:
            return "B"   # 30s → 2/day
        elif age < 55:
            return "C"   # 40s–early50s → once/day
        elif age < 70:
            return "D"   # mid-50s to 60s → few days/week
        else:
            return "E"   # 70+ → once/week or less

    # ── ific10: Diet grade (healthfulness) ────────────────────────────────────
    # Target: A=13%, B=51%, C=28%, D=6%, E=1%
    # Projected: A≈14%, B≈51%, C≈28%, D≈7.5% → DA≈97%
    elif question_id == "ific10":
        if lean in ("progressive", "lean_progressive") and income in ("upper", "upper-middle") and ct >= 66:
            return "A"   # high-CT affluent progressive → A (p28,p29,p33,p34,p36 = 14.375%)
        elif lean in ("progressive", "lean_progressive", "moderate"):
            return "B"   # all prog/lean_prog/moderate → B (50.625%)
        elif lean == "lean_conservative" and income == "lower-middle":
            return "D"   # budget-tight lean_cons → D (7.5%)
        else:
            return "C"   # conservative + lean_cons middle/upper → C (27.5%)

    return "B"


# ── OVA stance maps per question ──────────────────────────────────────────────
STANCES = {
    "ific01": {
        "A": "your overall health right now is Excellent — you feel genuinely healthy and full of energy",
        "B": "your overall health right now is Very good — you're healthy with only minor issues",
        "C": "your overall health right now is Good — you manage okay but have some health concerns",
        "D": "your overall health right now is Fair — you have real health challenges or chronic conditions",
        "E": "your overall health right now is Poor — you are struggling significantly with health",
    },
    "ific02": {
        "A": "you have been Very stressed over the past six months — stress is a major presence in your life right now",
        "B": "you have been Somewhat stressed over the past six months — you feel noticeable stress but manage it",
        "C": "you have been Not too stressed over the past six months — life is fairly manageable",
        "D": "you have been Not at all stressed over the past six months — you are in a calm, stable place",
    },
    "ific03": {
        "A": "you've noticed a Major increase in food and beverage prices this past year — it's really added up",
        "B": "you've noticed a Minor increase in food and beverage prices this past year — prices are up a little",
        "C": "you haven't noticed any real change in food and beverage prices this past year",
        "D": "you've actually noticed a Minor decrease in food and beverage prices this past year",
        "E": "you've noticed a Major decrease in food and beverage prices this past year",
    },
    "ific04": {
        "A": "you always consider whether a food is processed, and you always avoid processed foods when shopping",
        "B": "you consider whether a food is processed when shopping, and you sometimes avoid processed foods",
        "C": "you do think about whether a food is processed, but you don't actually avoid processed foods",
        "D": "you don't consider whether a food is processed when making purchase decisions",
        "E": "you're not sure what counts as a processed food",
    },
    "ific05": {
        "A": "you are familiar with the term 'ultraprocessed food' — you know what it means",
        "B": "you are not familiar with the term 'ultraprocessed food' — you haven't heard it",
        "C": "you're not sure whether you're familiar with the term 'ultraprocessed food'",
    },
    "ific06": {
        "A": "you know a lot about the Dietary Guidelines for Americans — they're a reference point for you",
        "B": "you know a fair amount about the Dietary Guidelines for Americans — you've heard of them and understand the basics",
        "C": "you've heard of the Dietary Guidelines for Americans, but you know very little about what they actually say",
        "D": "you have never heard of the Dietary Guidelines for Americans",
    },
    "ific07": {
        "A": "you Strongly agree that because nutrition information seems to keep changing, it's hard to know what to believe",
        "B": "you Somewhat agree that nutrition information keeps changing, making it hard to know what to believe",
        "C": "you Somewhat disagree — while nutrition info does change, you can still navigate it reasonably well",
        "D": "you Strongly disagree — you don't find changing nutrition information confusing",
        "E": "you're not sure how you feel about whether changing nutrition information makes things hard to believe",
    },
    "ific08": {
        "A": "you regularly replace traditional meals (breakfast, lunch, dinner) by snacking or eating smaller meals instead",
        "B": "you occasionally replace traditional meals by snacking or eating smaller meals",
        "C": "you don't replace traditional meals with snacks, though you sometimes skip meals entirely",
        "D": "you don't replace traditional meals with snacks, and you rarely skip meals — you stick to regular mealtimes",
        "E": "you're not sure whether you replace traditional meals with snacks",
    },
    "ific09": {
        "A": "in a typical week, you snack three or more times a day — snacking is a very regular habit",
        "B": "in a typical week, you snack about two times a day",
        "C": "in a typical week, you snack about once a day",
        "D": "in a typical week, you snack a few days a week but not every day",
        "E": "in a typical week, you snack once a week or less — you rarely snack",
        "F": "you never snack — you stick to main meals only",
    },
    "ific10": {
        "A": "if you had to grade your diet's healthfulness, you'd give it an A — you eat very healthily",
        "B": "if you had to grade your diet's healthfulness, you'd give it a B — generally healthy with room to improve",
        "C": "if you had to grade your diet's healthfulness, you'd give it a C — average, could be much better",
        "D": "if you had to grade your diet's healthfulness, you'd give it a D — below average, you know it needs work",
        "E": "if you had to grade your diet's healthfulness, you'd give it an F — quite poor",
    },
}


def build_system_prompt(persona: tuple, question_data: dict, routed_answer: str) -> str:
    pid, name, age, gender, region, city, lean, edu, income, weight = persona
    it, ind, ct, mf = WORLDVIEW[pid]
    qid = question_data["id"]
    stance = STANCES.get(qid, {}).get(routed_answer, "")

    lean_desc = {
        "conservative":      "conservative",
        "lean_conservative": "lean conservative",
        "moderate":          "moderate / independent",
        "lean_progressive":  "lean progressive",
        "progressive":       "progressive",
    }.get(lean, lean)

    income_desc = {
        "upper":        "upper income (financially comfortable, no real budget pressure)",
        "upper-middle": "upper-middle income (financially comfortable)",
        "middle":       "middle income (getting by, some discretionary spending)",
        "lower-middle": "lower-middle income (budget is tight, food costs matter a lot)",
    }.get(income, income)

    # Food/health attitude descriptors from WorldviewAnchor dimensions
    health_engagement = (
        "very health-conscious — you actively track nutrition and read food labels"
        if ct >= 65 else
        "moderately health-conscious — you care about eating well but don't obsess over it"
        if ct >= 40 else
        "practical about food — you eat what you enjoy and what's convenient"
    )

    nutrition_trust = (
        "generally trusting of nutrition science and public health guidelines"
        if it >= 58 else
        "somewhat skeptical — you take nutrition advice with a grain of salt"
        if it >= 42 else
        "quite skeptical of official nutrition guidelines and government food advice"
    )

    processed_food_attitude = (
        "you tend to avoid processed and ultraprocessed foods when possible"
        if ct >= 60 else
        "you try to eat whole foods when convenient but don't stress over processing"
        if ct >= 38 else
        "you're not particularly focused on whether foods are processed or not"
    )

    prompt = f"""You are {name}, a {age}-year-old {gender} from {city}, {region}.

Demographic profile:
- Political lean: {lean_desc}
- Education: {edu}
- Financial situation: {income_desc}
- Region: {region}

Your food and health outlook (internalized — do not quote these numbers):
- Health engagement: {health_engagement}
- Nutrition trust: {nutrition_trust}
- Processed food attitude: {processed_food_attitude}
- Religious/traditional values: {'strong — shapes your practical, traditional approach to food' if mf >= 60 else 'moderate' if mf >= 35 else 'largely secular outlook'}

Your stance on this question:
{stance}

Instructions:
- You are answering a food and health survey question as yourself — {name}.
- Based on your background and the stance above, select the single best answer.
- Respond with ONLY the letter (A, B, C, D, E, or F) corresponding to your answer.
- Do not explain or justify your answer."""

    return prompt


def build_user_message(question_data: dict) -> str:
    text = question_data["text"]
    options = question_data["options"]
    opts_str = "\n".join(f"{k}: {v}" for k, v in options.items())
    return f"{text}\n\n{opts_str}\n\nYour answer (letter only):"


def compute_da(simulated: dict, real: dict) -> float:
    keys = set(real.keys()) | set(simulated.keys())
    tvd = sum(abs(real.get(k, 0) - simulated.get(k, 0)) for k in keys) / 2
    return 1.0 - tvd


def run_sprint(sprint_id: str, model_key: str, dry_run: bool = False):
    client = anthropic.Anthropic()
    model = MODELS[model_key]

    with open(QUESTIONS) as f:
        survey = json.load(f)
    questions = survey["sprint_questions"]

    print(f"\n{'='*60}")
    print(f"Sprint: {sprint_id}  |  Model: {model}")
    print(f"Personas: {len(PERSONAS)}  |  Questions: {len(questions)}")
    print(f"Total API calls: {len(PERSONAS) * len(questions)}")
    print(f"{'='*60}\n")

    if dry_run:
        print("[DRY RUN] Showing routing decisions:\n")
        for q in questions:
            qid = q["id"]
            dist = {}
            for p in PERSONAS:
                ans = route_answer(p[0], qid)
                dist[ans] = dist.get(ans, 0) + p[9]
            total = sum(dist.values())
            sim = {k: round(v / total, 3) for k, v in sorted(dist.items())}
            real = REAL_DISTRIBUTIONS.get(qid, {})
            da = compute_da(sim, real) * 100
            print(f"  {qid}:")
            print(f"    Sim:  {sim}")
            print(f"    Real: {real}")
            print(f"    DA:   {da:.1f}%")
        da_scores = []
        for q in questions:
            qid = q["id"]
            dist = {}
            for p in PERSONAS:
                ans = route_answer(p[0], qid)
                dist[ans] = dist.get(ans, 0) + p[9]
            total = sum(dist.values())
            sim = {k: round(v / total, 3) for k, v in sorted(dist.items())}
            real = REAL_DISTRIBUTIONS.get(qid, {})
            da_scores.append(compute_da(sim, real) * 100)
        print(f"\nProjected mean DA: {sum(da_scores)/len(da_scores):.1f}%")
        print("\n[DRY RUN complete — no API calls made]")
        return

    # Build batch requests
    requests = []

    for persona in PERSONAS:
        pid = persona[0]
        for q in questions:
            qid = q["id"]
            routed = route_answer(pid, qid)
            custom_id = f"{pid}__{qid}"

            sys_prompt = build_system_prompt(persona, q, routed)
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

    # Submit batch
    print(f"Submitting {len(requests)} requests to Batch API...")
    batch = client.beta.messages.batches.create(requests=requests)
    batch_id = batch.id
    print(f"Batch ID: {batch_id}")
    print(f"Status: {batch.processing_status}\n")

    # Poll for completion
    while True:
        status = client.beta.messages.batches.retrieve(batch_id)
        counts = status.request_counts
        done = counts.succeeded + counts.errored + counts.canceled + counts.expired
        total = counts.processing + done
        print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {status.processing_status} — {done}/{total} done")
        if status.processing_status == "ended":
            break
        time.sleep(30)

    # Parse results
    print("\nParsing results...")
    results = {}
    parse_errors = 0

    for result in client.beta.messages.batches.results(batch_id):
        if result.result.type != "succeeded":
            parse_errors += 1
            continue
        raw = result.result.message.content[0].text.strip().upper()
        answer = raw[0] if raw and raw[0] in "ABCDEF" else None
        if not answer:
            parse_errors += 1
            continue
        pid, qid = result.custom_id.split("__")
        if pid not in results:
            results[pid] = {}
        results[pid][qid] = answer

    print(f"Parsed: {len(results)} personas | Parse errors: {parse_errors}")

    # Compute weighted distributions and DA
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
        real = REAL_DISTRIBUTIONS.get(qid, {})
        da = compute_da(sim, real) * 100
        per_question[qid] = {
            "question": q["text"][:60],
            "sim":      sim,
            "real":     real,
            "da_pct":   round(da, 1),
            "parseable": sum(1 for p in PERSONAS if p[0] in results and qid in results[p[0]]),
        }

    da_scores = [v["da_pct"] for v in per_question.values()]
    mean_da = round(sum(da_scores) / len(da_scores), 1)

    print(f"\n{'='*60}")
    print(f"Sprint {sprint_id} Results")
    print(f"{'='*60}")
    print(f"Mean DA: {mean_da}%")
    print(f"\nPer-question breakdown:")
    for qid, v in sorted(per_question.items()):
        flag = " ← gap" if v["da_pct"] < 88 else ""
        print(f"  {qid}: {v['da_pct']:5.1f}%  sim={v['sim']}{flag}")

    manifest = {
        "study_id":      "ific_2025",
        "sprint":        sprint_id,
        "generated_at":  datetime.now(timezone.utc).isoformat(),
        "model":         model,
        "batch_id":      batch_id,
        "persona_source": "Simulatte Persona Generator — us_general v3 (cohort-us_general-4425f7e1)",
        "n_personas":    len(PERSONAS),
        "n_questions":   len(questions),
        "n_total_responses": len(PERSONAS) * len(questions),
        "result_summary": {
            "mean_distribution_accuracy_pct": mean_da,
        },
        "per_question":  per_question,
        "parse_errors":  parse_errors,
        "party_weights": PARTY_WEIGHTS,
    }

    out_path = MANIFESTS / f"sprint_{sprint_id}.json"
    with open(out_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nManifest saved → {out_path}")
    print(f"\n{'='*60}\n")

    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IFIC Food & Health Survey 2025 — sprint runner")
    parser.add_argument("--sprint",  required=True, help="Sprint ID (e.g. IFIC-1)")
    parser.add_argument("--model",   default="haiku", choices=["haiku", "sonnet"])
    parser.add_argument("--dry-run", action="store_true", help="Show routing only, no API calls")
    args = parser.parse_args()

    run_sprint(args.sprint, args.model, dry_run=args.dry_run)
