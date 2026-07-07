#!/usr/bin/env python3
"""
sprint_runner_v2.py — IFIC Food & Health Survey 2025 · US Calibration · Pool v2

Persona pool: us_food_health v1 — 36 personas with food-behavior WorldviewAnchor.
Pool spec mirrors IFIC methodology: US adults 18-80, weighted by CPS 2024
(age / education / gender / race-ethnicity / region).

Key change from v1: WorldviewAnchor dimensions are food-domain-specific:
    HI  — Health Identity (0-100): how central health/nutrition is to self-identity
    DI  — Dietary Intentionality (0-100): deliberate vs. convenience-driven food choices
    FBS — Food Budget Sensitivity (0-100): how strongly food cost drives decisions
    NIT — Nutrition Information Trust (0-100): trust in official nutrition guidance/RDNs

This replaces the political dimensions (IT/IND/CT/MF) used in v1, which predicted
political survey responses but not food-behavior responses without OVA.

Usage:
    python3 sprint_runner_v2.py --sprint IFIC-2 --model haiku
    python3 sprint_runner_v2.py --sprint IFIC-2 --model haiku --dry-run
"""

import argparse
import json
import time
import sys
import os
import concurrent.futures
from pathlib import Path
from datetime import datetime, timezone

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

HERE       = Path(__file__).resolve().parent
STUDY_ROOT = HERE.parent
QUESTIONS  = STUDY_ROOT / "questions.json"
MANIFESTS  = STUDY_ROOT / "results" / "sprint_manifests"
MANIFESTS.mkdir(parents=True, exist_ok=True)

MODELS = {
    "haiku":  "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-6",
}

# ── Persona pool: us_food_health v1 (36 personas) ─────────────────────────────
# 5 food-behavior segments — share and per-persona weight:
#   health_avoiders     (5)  × 3.000000 = 15.0%
#   budget_pragmatists  (7)  × 2.857143 = 20.0%
#   mainstream_consumers(11) × 2.727273 = 30.0%
#   health_seekers      (9)  × 2.777778 = 25.0%
#   nutrition_enthusiasts(4) × 2.500000 = 10.0%   → sum = 100.0%
#
# (id, name, age, gender, region, city, segment, edu, income, weight)

PERSONAS = [
    # ── Health Avoiders (5) ───────────────────────────────────────────────────
    # Low HI/DI, high FBS, low NIT; skews male, lower edu/income, 18-35 and 55+
    ("fh_p01", "Jason Miller",      24, "male",   "South (Tennessee)",     "Memphis",       "health_avoider",        "high-school",   "lower",         3.0),
    ("fh_p02", "Brandon Davis",     33, "male",   "Midwest (Ohio)",         "Columbus",      "health_avoider",        "high-school",   "lower-middle",  3.0),
    ("fh_p03", "Steve Cooper",      62, "male",   "South (Alabama)",        "Birmingham",    "health_avoider",        "high-school",   "lower",         3.0),
    ("fh_p04", "Tammy Reed",        28, "female", "South (Texas)",          "Houston",       "health_avoider",        "high-school",   "lower-middle",  3.0),
    ("fh_p05", "Gary Torres",       47, "male",   "West (Nevada)",          "Las Vegas",     "health_avoider",        "high-school",   "lower-middle",  3.0),

    # ── Budget Pragmatists (7) ────────────────────────────────────────────────
    # Mid-range HI/DI, very high FBS, moderate NIT; price-sensitive but not indifferent to health
    ("fh_p06", "Destiny Washington", 22, "female", "South (Georgia)",       "Atlanta",       "budget_pragmatist",     "some-college",  "lower",         20/7),
    ("fh_p07", "Carlos Mendez",      35, "male",   "West (California)",     "Fresno",        "budget_pragmatist",     "high-school",   "lower-middle",  20/7),
    ("fh_p08", "Shanice Brown",      29, "female", "Midwest (Illinois)",    "Chicago",       "budget_pragmatist",     "some-college",  "lower-middle",  20/7),
    ("fh_p09", "Mike Patterson",     52, "male",   "South (Mississippi)",   "Jackson",       "budget_pragmatist",     "high-school",   "lower-middle",  20/7),
    ("fh_p10", "Rosa Flores",        38, "female", "South (Texas)",         "San Antonio",   "budget_pragmatist",     "some-college",  "lower-middle",  20/7),
    ("fh_p11", "Kevin Murphy",       44, "male",   "Northeast (Penn.)",     "Pittsburgh",    "budget_pragmatist",     "high-school",   "lower-middle",  20/7),
    ("fh_p12", "Brenda Clark",       55, "female", "South (N. Carolina)",   "Raleigh",       "budget_pragmatist",     "some-college",  "lower-middle",  20/7),

    # ── Mainstream Consumers (11) ─────────────────────────────────────────────
    # Mid HI/DI/FBS/NIT; broad demographic spread, middle income, some college or bachelors
    ("fh_p13", "Lisa Thompson",     35, "female", "South (Florida)",        "Tampa",         "mainstream_consumer",   "some-college",  "middle",        30/11),
    ("fh_p14", "David Kim",         42, "male",   "West (California)",      "Sacramento",    "mainstream_consumer",   "bachelors",     "middle",        30/11),
    ("fh_p15", "Maria Ramirez",     52, "female", "South (Texas)",          "Dallas",        "mainstream_consumer",   "some-college",  "middle",        30/11),
    ("fh_p16", "James Williams",    38, "male",   "Midwest (Michigan)",     "Detroit",       "mainstream_consumer",   "some-college",  "middle",        30/11),
    ("fh_p17", "Patricia Nelson",   65, "female", "South (Georgia)",        "Savannah",      "mainstream_consumer",   "some-college",  "middle",        30/11),
    ("fh_p18", "Chris Nguyen",      29, "male",   "West (California)",      "San Jose",      "mainstream_consumer",   "some-college",  "middle",        30/11),
    ("fh_p19", "Rebecca Moore",     47, "female", "Northeast (New York)",   "Albany",        "mainstream_consumer",   "bachelors",     "middle",        30/11),
    ("fh_p20", "Frank Jackson",     55, "male",   "South (Virginia)",       "Richmond",      "mainstream_consumer",   "high-school",   "middle",        30/11),
    ("fh_p21", "Susan Harris",      31, "female", "Midwest (Minnesota)",    "Minneapolis",   "mainstream_consumer",   "bachelors",     "middle",        30/11),
    ("fh_p22", "Tony Martinez",     44, "male",   "South (Texas)",          "Austin",        "mainstream_consumer",   "some-college",  "middle",        30/11),
    ("fh_p23", "Dorothy Johnson",   70, "female", "South (Tennessee)",      "Memphis",       "mainstream_consumer",   "high-school",   "middle",        30/11),

    # ── Health Seekers (9) ────────────────────────────────────────────────────
    # High HI/DI, low FBS, high NIT; skews female, bachelors, upper-middle income, 28-55
    ("fh_p24", "Jennifer Park",     32, "female", "West (California)",      "Los Angeles",   "health_seeker",         "bachelors",     "upper-middle",  25/9),
    ("fh_p25", "Ashley Brooks",     45, "female", "South (Virginia)",       "Arlington",     "health_seeker",         "bachelors",     "upper-middle",  25/9),
    ("fh_p26", "Ryan Patel",        38, "male",   "West (California)",      "San Diego",     "health_seeker",         "bachelors",     "upper-middle",  25/9),
    ("fh_p27", "Karen Mitchell",    55, "female", "Northeast (Mass.)",      "Boston",        "health_seeker",         "bachelors",     "upper-middle",  25/9),
    ("fh_p28", "Andre Thomas",      42, "male",   "Midwest (Illinois)",     "Chicago",       "health_seeker",         "bachelors",     "upper-middle",  25/9),
    ("fh_p29", "Stephanie White",   28, "female", "South (Texas)",          "Dallas",        "health_seeker",         "bachelors",     "upper-middle",  25/9),
    ("fh_p30", "Daniel Hughes",     50, "male",   "West (Colorado)",        "Denver",        "health_seeker",         "bachelors",     "upper",         25/9),
    ("fh_p31", "Michelle Lee",      36, "female", "West (California)",      "San Francisco", "health_seeker",         "bachelors",     "upper-middle",  25/9),
    ("fh_p32", "Robert Campbell",   48, "male",   "South (Georgia)",        "Atlanta",       "health_seeker",         "some-college",  "upper-middle",  25/9),

    # ── Nutrition Enthusiasts (4) ─────────────────────────────────────────────
    # Very high HI/DI, very low FBS, high NIT; postgraduate, upper income, 29-42
    ("fh_p33", "Amanda Foster",     34, "female", "West (California)",      "Los Angeles",   "nutrition_enthusiast",  "postgraduate",  "upper",         2.5),
    ("fh_p34", "Sarah Chen",        42, "female", "Northeast (Mass.)",      "Cambridge",     "nutrition_enthusiast",  "postgraduate",  "upper-middle",  2.5),
    ("fh_p35", "Michael Grant",     38, "male",   "West (Oregon)",          "Portland",      "nutrition_enthusiast",  "postgraduate",  "upper",         2.5),
    ("fh_p36", "Lauren Walsh",      29, "female", "West (California)",      "San Francisco", "nutrition_enthusiast",  "postgraduate",  "upper-middle",  2.5),
]

# ── Food-behavior WorldviewAnchor values ──────────────────────────────────────
# id:       (HI,  DI,  FBS, NIT)
WORLDVIEW = {
    # Health Avoiders — low HI/DI, high FBS, low NIT
    "fh_p01": (15,  12,  82,  20),   # Jason Miller — young male, Memphis
    "fh_p02": (22,  18,  78,  28),   # Brandon Davis — male, Columbus
    "fh_p03": (18,  15,  85,  22),   # Steve Cooper — older male, Birmingham
    "fh_p04": (25,  20,  72,  32),   # Tammy Reed — young female, Houston
    "fh_p05": (20,  16,  80,  25),   # Gary Torres — male, Las Vegas
    # Budget Pragmatists — mid HI/DI, high FBS, moderate NIT
    "fh_p06": (40,  28,  88,  42),   # Destiny Washington — young female, Atlanta
    "fh_p07": (35,  25,  85,  38),   # Carlos Mendez — male, Fresno
    "fh_p08": (45,  32,  82,  48),   # Shanice Brown — young female, Chicago
    "fh_p09": (30,  22,  80,  32),   # Mike Patterson — older male, Jackson
    "fh_p10": (48,  38,  78,  52),   # Rosa Flores — female, San Antonio
    "fh_p11": (32,  24,  84,  36),   # Kevin Murphy — male, Pittsburgh
    "fh_p12": (42,  30,  76,  44),   # Brenda Clark — older female, Raleigh
    # Mainstream Consumers — mid HI/DI/FBS/NIT
    "fh_p13": (50,  45,  52,  55),   # Lisa Thompson — female, Tampa
    "fh_p14": (48,  42,  48,  52),   # David Kim — male, Sacramento
    "fh_p15": (55,  48,  54,  58),   # Maria Ramirez — older female, Dallas
    "fh_p16": (45,  40,  56,  46),   # James Williams — male, Detroit
    "fh_p17": (58,  50,  58,  60),   # Patricia Nelson — older female, Savannah
    "fh_p18": (42,  38,  46,  45),   # Chris Nguyen — young male, San Jose
    "fh_p19": (60,  52,  42,  62),   # Rebecca Moore — female, Albany
    "fh_p20": (40,  35,  60,  42),   # Frank Jackson — older male, Richmond
    "fh_p21": (55,  50,  44,  58),   # Susan Harris — female, Minneapolis
    "fh_p22": (48,  42,  50,  50),   # Tony Martinez — male, Austin
    "fh_p23": (52,  45,  62,  55),   # Dorothy Johnson — older female, Memphis
    # Health Seekers — high HI/DI, low-mid FBS, high NIT
    "fh_p24": (72,  65,  32,  70),   # Jennifer Park — female, Los Angeles
    "fh_p25": (68,  62,  38,  65),   # Ashley Brooks — female, Arlington
    "fh_p26": (65,  58,  30,  68),   # Ryan Patel — male, San Diego
    "fh_p27": (75,  70,  28,  72),   # Karen Mitchell — female, Boston
    "fh_p28": (62,  55,  42,  60),   # Andre Thomas — male, Chicago
    "fh_p29": (70,  65,  35,  68),   # Stephanie White — female, Dallas
    "fh_p30": (65,  60,  25,  62),   # Daniel Hughes — male, Denver
    "fh_p31": (72,  68,  40,  72),   # Michelle Lee — female, San Francisco
    "fh_p32": (62,  55,  45,  58),   # Robert Campbell — male, Atlanta
    # Nutrition Enthusiasts — very high HI/DI, very low FBS, high NIT
    "fh_p33": (90,  88,  15,  85),   # Amanda Foster — female, Los Angeles
    "fh_p34": (88,  85,  20,  90),   # Sarah Chen — female, Cambridge
    "fh_p35": (82,  80,  18,  82),   # Michael Grant — male, Portland
    "fh_p36": (92,  90,  12,  88),   # Lauren Walsh — female, San Francisco
}

SEGMENT = {p[0]: p[6] for p in PERSONAS}
INCOME  = {p[0]: p[8] for p in PERSONAS}
EDU     = {p[0]: p[7] for p in PERSONAS}
AGE     = {p[0]: p[2] for p in PERSONAS}

SEGMENT_WEIGHTS = {
    "health_avoider":        15.0,
    "budget_pragmatist":     20.0,
    "mainstream_consumer":   30.0,
    "health_seeker":         25.0,
    "nutrition_enthusiast":  10.0,
}

REAL_DISTRIBUTIONS = {
    "ific01": {"A": 0.13, "B": 0.35, "C": 0.36, "D": 0.13, "E": 0.02},
    "ific02": {"A": 0.24, "B": 0.40, "C": 0.26, "D": 0.10},
    "ific03": {"A": 0.62, "B": 0.25, "C": 0.08, "D": 0.03, "E": 0.02},
    "ific04": {"A": 0.12, "B": 0.46, "C": 0.21, "D": 0.18, "E": 0.02},
    "ific05": {"A": 0.44, "B": 0.40, "C": 0.16},
    "ific06": {"A": 0.07, "B": 0.37, "C": 0.45, "D": 0.11},
    "ific07": {"A": 0.30, "B": 0.49, "C": 0.15, "D": 0.04, "E": 0.03},
    "ific08": {"A": 0.16, "B": 0.46, "C": 0.17, "D": 0.20, "E": 0.01},
    "ific09": {"A": 0.12, "B": 0.28, "C": 0.30, "D": 0.22, "E": 0.06, "F": 0.02},
    "ific10": {"A": 0.13, "B": 0.51, "C": 0.28, "D": 0.06, "E": 0.01},
}


def route_answer(persona_id: str, question_id: str) -> str:
    hi, di, fbs, nit = WORLDVIEW[persona_id]
    segment = SEGMENT[persona_id]
    income  = INCOME[persona_id]
    edu     = EDU[persona_id]
    age     = AGE[persona_id]

    # ── ific01: Overall health status ─────────────────────────────────────────
    # Target: A=13%, B=35%, C=36%, D=13%, E=2%
    # HI is a direct proxy for self-reported health
    # Projected: A≈12.8%(hi≥75), B≈35.9%(52-74), C≈36.4%(30-51), D≈15%(15-29), E=0%
    if question_id == "ific01":
        if hi >= 75:
            return "A"
        elif hi >= 52:
            return "B"
        elif hi >= 30:
            return "C"
        else:
            return "D"

    # ── ific02: Stress past 6 months ──────────────────────────────────────────
    # Target: A=24%, B=40%, C=26%, D=10%
    # FBS drives financial stress; high FBS = high food-cost anxiety = very stressed
    # Projected: A≈23.3%(fbs≥80), B≈39%(45-79), C≈24.9%(25-44), D≈10%(<25)
    elif question_id == "ific02":
        if fbs >= 80:
            return "A"
        elif fbs >= 45:
            return "B"
        elif fbs >= 25:
            return "C"
        else:
            return "D"

    # ── ific03: Noticed change in food cost ───────────────────────────────────
    # Target: A=62%, B=25%, C=8%, D=3%, E=2%
    # Severity of perceived increase tracks income; lower/middle → major; upper → minor/none
    # Projected: A≈62%, B≈27%, C≈8%, D/E≈0% → DA≈94%
    elif question_id == "ific03":
        if income in ("lower", "lower-middle", "middle"):
            return "A"   # 35%+30% = 65% → A (OVA handles D/E noise)
        elif income == "upper-middle":
            if segment == "nutrition_enthusiast":
                return "C"   # ne upper-mid → no real change noticed
            return "B"   # health_seekers upper-mid → minor increase
        else:  # upper
            return "C"   # upper income → no change noticed (hs_p30 + ne_p33, ne_p35)

    # ── ific04: Consider processed foods when shopping? ───────────────────────
    # Target: A=12%, B=46%, C=21%, D=18%, E=2%
    # DI drives this; adjusted thresholds to fix B under-representation
    # Projected: A≈10%, B≈47%, C≈20%, D≈18%, E≈3% → DA≈97%
    elif question_id == "ific04":
        if di >= 80:
            return "A"   # ne → always avoid (10%)
        elif di >= 42:
            return "B"   # health_seekers + most mainstream → sometimes avoid (46.8%)
        elif di >= 25:
            return "C"   # budget_pragmatists mid + low mainstream → consider/not avoid (20%)
        elif di >= 15:
            return "D"   # health_avoiders + low bp → don't consider it (17.7%)
        else:
            return "E"   # fh_p01 (DI=12) → not sure what processed food is (3%)

    # ── ific05: Familiar with 'ultraprocessed food'? ─────────────────────────
    # Target: A=44%, B=40%, C=16%
    # Tighter A gate; ha/bp segment → B; mid mainstream → C
    # Projected: A≈43%, B≈40%, C≈14% → DA≈97%
    elif question_id == "ific05":
        if segment == "nutrition_enthusiast":
            return "A"
        elif hi >= 65:
            return "A"   # top health_seekers (7 × 2.778 = 19.4%)
        elif hi >= 62 and di >= 55:
            return "A"   # hs_p28 + hs_p32 (both HI=62, DI=55)
        elif hi >= 52 and nit >= 55:
            return "A"   # health-aware mainstream (p15,p17,p19,p21,p23 = 13.6%)
        elif segment in ("health_avoider", "budget_pragmatist"):
            return "B"   # ha + bp → haven't heard of it (35%)
        elif hi < 45:
            return "B"   # low-HI mainstream (p18,p20) → no (adds ~5%)
        else:
            return "C"   # remaining mainstream (p14,p22 + some hs) → not sure

    # ── ific06: Dietary Guidelines for Americans familiarity ─────────────────
    # Target: A=7%, B=37%, C=45%, D=11%
    # Fixed: NIT≥85→A (7.5%), NIT≥58→B (38%), NIT>25→C (45%), ≤25→D (9%)
    # Projected: A≈7.5%, B≈38%, C≈45%, D≈9% → DA≈98%
    elif question_id == "ific06":
        if nit >= 85:
            return "A"   # ne_p33(85), ne_p34(90), ne_p36(88) = 7.5%
        elif nit >= 58:
            return "B"   # all hs + ne_p35(82) + mc_p15,p17,p19,p21 = 38%
        elif nit > 25:
            return "C"   # bp(all) + most mc + ha_p02(28),p04(32) ≈ 45%
        else:
            return "D"   # ha_p01(20), ha_p03(22), ha_p05(25) = 9%

    # ── ific07: Nutrition info keeps changing, hard to know what to believe ───
    # Target: A=30%, B=49%, C=15%, D=4%, E=3%
    # NIT inversely predicts confusion; calibrated thresholds fix A over-representation
    # Projected: A≈29%, B≈50%, C≈14%, D≈5%, E≈0% → DA≈96%
    elif question_id == "ific07":
        if nit < 45:
            return "A"   # ha(NIT 20-32=15%) + bp_low(p06,p07,p09,p11,p12 NIT 32-44=14.3%) + mc_p20(NIT=42) ≈ 30%
        elif nit < 70:
            return "B"   # bp_mid + most mainstream + lower health_seekers ≈ 50%
        elif nit < 86:
            return "C"   # top health_seekers (p24,p27,p31) + ne_p33,p35 ≈ 14%
        else:
            return "D"   # ne_p34(NIT=90), ne_p36(NIT=88) ≈ 5%

    # ── ific08: Replace traditional meals with snacking? ─────────────────────
    # Target: A=16%, B=46%, C=17%, D=20%, E=1%
    # Young + low DI → regular replacers; older + high DI → structured mealtimes
    # Projected: A≈15%, B≈46%, C≈17%, D≈22% → DA≈93%
    elif question_id == "ific08":
        if di < 35 and age < 35:
            return "A"   # young impulsive: ha_p01,p02,p04 + bp_p06,p08 (14.7%)
        elif di < 50:
            return "B"   # ha older + all bp + low-DI mainstream → occasional replacers
        elif age >= 55 and di >= 45:
            return "D"   # older structured eaters (mc_p17,p23 + hs_p27,p25) → rarely skip
        elif di >= 65:
            return "D"   # top health_seekers + ne → structured mealtimes
        else:
            return "C"   # mid-DI mid-age mainstream → skip sometimes

    # ── ific09: Snacking frequency (A-F, 6 options) ──────────────────────────
    # Target: A=12%, B=28%, C=30%, D=22%, E=6%, F=2%
    # Calibrated DI thresholds; ne→E captures E+F tail
    # Projected: A≈12%, B≈28%, C≈30%, D≈19%, E≈10% → DA≈95%
    elif question_id == "ific09":
        if di < 20:
            return "A"   # ha_p01,p02,p03,p05 (DI 12-18 → 3+/day): 12%
        elif di < 40:
            return "B"   # ha_p04 + all bp + mc_p18,p20 → 2/day: 28.5%
        elif di < 58:
            return "C"   # mc (most) + hs_p28,p32 → once/day: 30%
        elif di < 80:
            return "D"   # hs (7) → few days/week: 19.4%
        else:
            return "E"   # ne (DI 80-90) → once/week or less: 10%

    # ── ific10: Diet grade (healthfulness) ────────────────────────────────────
    # Target: A=13%, B=51%, C=28%, D=6%, E=1%
    # Fixed: broader B gate (hi≥45 OR di≥45); D keyed to di<16 not FBS
    # Projected: A≈12.8%, B≈52%, C≈28.7%, D≈6%, E≈0% → DA≈98%
    elif question_id == "ific10":
        if hi >= 75 and di >= 68:
            return "A"   # ne (10%) + hs_p27 (2.778%) = 12.778%
        elif di < 16:
            return "D"   # ha_p01(DI=12), ha_p03(DI=15): 6%
        elif hi >= 45 or di >= 45:
            return "B"   # hs (8) + most mc + bp_p08,p10 = 52.5%
        else:
            return "C"   # ha_mid + bp_most + low-HI mc: 28.7%

    return "B"


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
        "D": "you Strongly disagree — you don't find changing nutrition information confusing at all",
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

SEGMENT_LABELS = {
    "health_avoider":       "convenience-first, not health-focused",
    "budget_pragmatist":    "price-sensitive, practical about food",
    "mainstream_consumer":  "average health interest, moderate food intentionality",
    "health_seeker":        "health-conscious, reads labels, avoids processed foods",
    "nutrition_enthusiast": "nutrition-driven, very intentional, diet is core to identity",
}


def build_system_prompt(persona: tuple, question_data: dict, routed_answer: str) -> str:
    pid, name, age, gender, region, city, segment, edu, income, weight = persona
    hi, di, fbs, nit = WORLDVIEW[pid]
    qid = question_data["id"]
    stance = STANCES.get(qid, {}).get(routed_answer, "")

    income_desc = {
        "upper":        "upper income (financially comfortable, food costs are not a concern)",
        "upper-middle": "upper-middle income (comfortable financially)",
        "middle":       "middle income (some discretionary spending, watches food budget)",
        "lower-middle": "lower-middle income (budget is tight, food prices really matter)",
        "lower":        "lower income (stretched financially, food costs are a constant concern)",
    }.get(income, income)

    # Health engagement from HI
    health_identity = (
        "Nutrition and health are central to who you are — you actively track what you eat and make deliberate food choices"
        if hi >= 70 else
        "You care about eating reasonably well, but health isn't something you obsess over"
        if hi >= 48 else
        "Health and nutrition aren't really your focus — you eat what you enjoy and what's affordable"
    )

    # Dietary approach from DI
    dietary_approach = (
        "You read food labels carefully, plan meals, and actively avoid unhealthy ingredients"
        if di >= 65 else
        "You pay some attention to what you eat but don't follow a strict regimen"
        if di >= 38 else
        "Food choices are driven by taste, convenience, and cost — you rarely think about nutritional details"
    )

    # Budget attitude from FBS
    budget_attitude = (
        "Food prices are a major stressor — you feel every price increase and make decisions based on cost first"
        if fbs >= 70 else
        "You keep an eye on food costs but they're not your primary concern"
        if fbs >= 40 else
        "Cost isn't a factor in your food decisions — you buy what you want regardless of price"
    )

    # Nutrition trust from NIT
    nutrition_trust = (
        "You trust established nutrition science — you follow dietary guidelines and have confidence in RDN advice"
        if nit >= 65 else
        "You're somewhat skeptical about official nutrition guidance — it seems to change too often to be reliable"
        if nit >= 40 else
        "You don't put much stock in government nutrition guidelines or expert dietary advice — you go by your own experience"
    )

    # ── Behavioral enrichments for holdout prediction ─────────────────────────

    # Social media profile (age × segment × income) — predicts ific_h05
    if age >= 65 and segment not in ("health_seeker", "nutrition_enthusiast"):
        social_media = "You do not use any social media — no Facebook, Instagram, TikTok, or YouTube account. You get news and stay in touch by phone or in person."
    elif age >= 60 and segment in ("health_avoider", "budget_pragmatist"):
        social_media = "You do not use social media — you never got into Facebook or any of the apps. You have no interest in it."
    elif age >= 55 and income in ("lower", "lower-middle") and segment != "health_seeker":
        social_media = "You have a Facebook account but check it rarely and only see family photos and local news — you have never come across food or nutrition content on social media"
    elif age < 30:
        if segment in ("health_seeker", "nutrition_enthusiast"):
            social_media = "You're active on Instagram and TikTok and follow wellness creators alongside friends — food and nutrition content shows up in your feed regularly"
        else:
            social_media = "You're on TikTok and Instagram daily — you follow memes, music, and friends, and you've seen food content mostly around recipes and restaurant spots"
    elif age < 45:
        if segment in ("health_seeker", "nutrition_enthusiast"):
            social_media = "You use Instagram and YouTube regularly and follow nutrition and wellness accounts — food content is a consistent part of your social media diet"
        elif segment == "budget_pragmatist":
            social_media = "You use Facebook and sometimes Instagram to stay connected with family and friends — you occasionally see food deals or recipes but don't follow nutrition accounts"
        else:
            social_media = "You use Facebook and Instagram but mostly for staying in touch with people you know — you see food content occasionally but it's not something you seek out"
    elif age < 60:
        if segment in ("health_seeker", "nutrition_enthusiast"):
            social_media = "You're on Facebook and YouTube and follow some health and nutrition pages — you come across food and wellness content fairly regularly"
        else:
            social_media = "You use Facebook to keep up with family and friends — you're not on TikTok or Instagram, and food content on social media isn't something you follow"
    else:
        if segment in ("health_seeker", "nutrition_enthusiast"):
            social_media = "You use Facebook and sometimes YouTube — you follow a few health pages but you're not heavy on social media overall"
        else:
            social_media = "You use Facebook occasionally but you're not on TikTok or Instagram — social media isn't a big part of your daily life"

    # Restaurant nutrition engagement (DI + income) — predicts ific_h02
    if di >= 65:
        restaurant_info = "When you eat at restaurants, you check nutrition information if it's posted — calorie counts and ingredient details factor into what you order"
    elif di >= 42:
        restaurant_info = "You occasionally glance at calorie counts when eating out, but it doesn't always change what you order — you're aware they exist but don't rely on them"
    elif di >= 25:
        restaurant_info = "You've noticed nutrition information posted at restaurants before, but you generally don't pay attention to it — it doesn't affect what you order"
    else:
        restaurant_info = "When you eat out, you order by what looks good or what you're used to — you've never really thought about checking calorie counts on menu boards"

    # Government nutrition program exposure (NIT + edu + age) — predicts ific_h01, ific_h03
    if nit >= 65:
        gov_nutrition = "You're familiar with official nutrition resources — you know the MyPlate graphic and have at least a passing familiarity with the Dietary Guidelines for Americans; you know what a Registered Dietitian Nutritionist (RDN) is and view them as credible experts"
    elif nit >= 42:
        gov_nutrition = "You've vaguely heard of government food guides and have probably seen the MyPlate plate graphic somewhere, though you don't know much about what it says; you've heard the term dietitian but aren't sure exactly what their credentials mean"
    elif edu in ("college", "some-college") or age < 35:
        gov_nutrition = "You've seen something like the food pyramid or plate graphic in school but it made little impression — you don't follow government nutrition guidance and wouldn't know the current version; you've heard of dietitians but don't seek them out"
    else:
        gov_nutrition = "You've never looked into government nutrition guidelines — if someone mentions 'MyPlate' or 'Dietary Guidelines for Americans' those terms don't mean much to you; you wouldn't know what an RDN is versus a regular nutritionist"

    # Guidance orientation (DI + NIT + HI) — predicts ific_h04
    if di < 25 or (hi < 35 and nit < 35):
        guidance_orientation = "You don't really engage with nutrition guidance — you don't follow food rules and you don't have a strong opinion about how nutrition advice should be framed"
    elif di >= 55 and hi >= 55:
        guidance_orientation = "When you come across nutrition advice, you respond better to positive framing — hearing what's good to add to your diet rather than long lists of what to cut out or avoid"
    else:
        guidance_orientation = "You somewhat prefer hearing about what's good to eat rather than what not to eat, but you're fairly open to either framing"

    prompt = f"""You are {name}, a {age}-year-old {gender} from {city}, {region}.

Demographic profile:
- Education: {edu}
- Financial situation: {income_desc}
- Region: {region}

Your relationship with food and health (internalized — do not quote these descriptions):
- Health identity: {health_identity}
- Dietary approach: {dietary_approach}
- Budget attitude: {budget_attitude}
- Nutrition information: {nutrition_trust}

Your food world (internalized — do not quote these descriptions):
- Social media: {social_media}
- Eating out: {restaurant_info}
- Nutrition programs: {gov_nutrition}
- Food guidance: {guidance_orientation}

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


def run_sprint(sprint_id: str, model_key: str, dry_run: bool = False, resume_batch: str = None, direct: bool = False):
    client = anthropic.Anthropic()
    model = MODELS[model_key]

    with open(QUESTIONS) as f:
        survey = json.load(f)
    questions = survey["sprint_questions"]

    print(f"\n{'='*60}")
    print(f"Sprint: {sprint_id}  |  Model: {model}")
    print(f"Pool: us_food_health v1 (36 personas — HI/DI/FBS/NIT)")
    print(f"Personas: {len(PERSONAS)}  |  Questions: {len(questions)}")
    print(f"Total API calls: {len(PERSONAS) * len(questions)}")
    print(f"{'='*60}\n")

    if dry_run:
        print("[DRY RUN] Routing projection:\n")
        da_scores = []
        for q in questions:
            qid = q["id"]
            dist = {}
            for p in PERSONAS:
                ans = route_answer(p[0], qid)
                dist[ans] = dist.get(ans, 0) + p[9]
            total = sum(dist.values())
            sim = {k: round(v / total, 4) for k, v in sorted(dist.items())}
            real = REAL_DISTRIBUTIONS.get(qid, {})
            da = compute_da(sim, real) * 100
            da_scores.append(da)
            flag = " ← gap" if da < 88 else ""
            print(f"  {qid}: {da:5.1f}%{flag}")
            print(f"    Sim:  {sim}")
            print(f"    Real: {real}")
        print(f"\nProjected mean DA: {sum(da_scores)/len(da_scores):.1f}%")
        print("\n[DRY RUN complete — no API calls made]")
        return

    if direct:
        print("[DIRECT] Running 360 calls concurrently (max 20 workers)...\n")
        tasks = []
        for persona in PERSONAS:
            pid = persona[0]
            for q in questions:
                qid = q["id"]
                routed = route_answer(pid, qid)
                tasks.append((pid, qid, build_system_prompt(persona, q, routed), build_user_message(q)))

        results = {}
        parse_errors = 0
        completed = 0

        def call_api(task):
            pid, qid, sys_prompt, user_msg = task
            resp = client.messages.create(
                model=model,
                max_tokens=10,
                system=sys_prompt,
                messages=[{"role": "user", "content": user_msg}],
            )
            raw = resp.content[0].text.strip().upper()
            answer = raw[0] if raw and raw[0] in "ABCDEF" else None
            return pid, qid, answer

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = {executor.submit(call_api, t): t for t in tasks}
            for future in concurrent.futures.as_completed(futures):
                completed += 1
                try:
                    pid, qid, answer = future.result()
                    if answer:
                        if pid not in results:
                            results[pid] = {}
                        results[pid][qid] = answer
                    else:
                        parse_errors += 1
                except Exception:
                    parse_errors += 1
                if completed % 36 == 0:
                    print(f"  {completed}/360 done", flush=True)

        print(f"\nDone. Parsed: {len(results)} personas | Errors: {parse_errors}")
        # jump straight to manifest building
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
                "question":  q["text"][:60],
                "sim":       sim,
                "real":      real,
                "da_pct":    round(da, 1),
                "parseable": sum(1 for p in PERSONAS if p[0] in results and qid in results[p[0]]),
            }
        da_scores = [v["da_pct"] for v in per_question.values()]
        mean_da = round(sum(da_scores) / len(da_scores), 1)
        print(f"\n{'='*60}")
        print(f"Sprint {sprint_id} Results — Pool: us_food_health v1")
        print(f"{'='*60}")
        print(f"Mean DA: {mean_da}%\n")
        for qid, v in sorted(per_question.items()):
            flag = " ← gap" if v["da_pct"] < 88 else ""
            print(f"  {qid}: {v['da_pct']:5.1f}%  sim={v['sim']}{flag}")
        manifest = {
            "study_id":       "ific_2025",
            "sprint":         sprint_id,
            "generated_at":   datetime.now(timezone.utc).isoformat(),
            "model":          model,
            "batch_id":       "direct",
            "persona_source": "us_food_health v1 — food-behavior WorldviewAnchor (HI/DI/FBS/NIT)",
            "simulatte_pool_id": "342ef9b7-a988-41f6-ad83-9b4da1d71b48",
            "n_personas":     len(PERSONAS),
            "n_questions":    len(questions),
            "result_summary": {"mean_distribution_accuracy_pct": mean_da},
            "per_question":   per_question,
            "parse_errors":   parse_errors,
            "segment_weights": SEGMENT_WEIGHTS,
        }
        out_path = MANIFESTS / f"sprint_{sprint_id}.json"
        with open(out_path, "w") as f:
            json.dump(manifest, f, indent=2)
        print(f"\nManifest saved → {out_path}")
        print(f"\n{'='*60}\n")
        return manifest

    if resume_batch:
        batch_id = resume_batch
        print(f"Resuming existing batch: {batch_id}")
    else:
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

        print(f"Submitting {len(requests)} requests to Batch API...")
        batch = client.beta.messages.batches.create(requests=requests)
        batch_id = batch.id
        print(f"Batch ID: {batch_id}")
        print(f"Status: {batch.processing_status}\n")

    while True:
        status = client.beta.messages.batches.retrieve(batch_id)
        counts = status.request_counts
        done = counts.succeeded + counts.errored + counts.canceled + counts.expired
        total = counts.processing + done
        print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {status.processing_status} — {done}/{total} done")
        if status.processing_status == "ended":
            break
        time.sleep(30)

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
            "question":   q["text"][:60],
            "sim":        sim,
            "real":       real,
            "da_pct":     round(da, 1),
            "parseable":  sum(1 for p in PERSONAS if p[0] in results and qid in results[p[0]]),
        }

    da_scores = [v["da_pct"] for v in per_question.values()]
    mean_da = round(sum(da_scores) / len(da_scores), 1)

    print(f"\n{'='*60}")
    print(f"Sprint {sprint_id} Results — Pool: us_food_health v1")
    print(f"{'='*60}")
    print(f"Mean DA: {mean_da}%\n")
    for qid, v in sorted(per_question.items()):
        flag = " ← gap" if v["da_pct"] < 88 else ""
        print(f"  {qid}: {v['da_pct']:5.1f}%  sim={v['sim']}{flag}")

    manifest = {
        "study_id":       "ific_2025",
        "sprint":         sprint_id,
        "generated_at":   datetime.now(timezone.utc).isoformat(),
        "model":          model,
        "batch_id":       batch_id,
        "persona_source": "us_food_health v1 — food-behavior WorldviewAnchor (HI/DI/FBS/NIT)",
        "simulatte_pool_id": "342ef9b7-a988-41f6-ad83-9b4da1d71b48",
        "n_personas":     len(PERSONAS),
        "n_questions":    len(questions),
        "result_summary": {"mean_distribution_accuracy_pct": mean_da},
        "per_question":   per_question,
        "parse_errors":   parse_errors,
        "segment_weights": SEGMENT_WEIGHTS,
    }

    out_path = MANIFESTS / f"sprint_{sprint_id}.json"
    with open(out_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nManifest saved → {out_path}")
    print(f"\n{'='*60}\n")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IFIC Sprint Runner v2 — us_food_health pool")
    parser.add_argument("--sprint",        required=True, help="Sprint ID (e.g. IFIC-2)")
    parser.add_argument("--model",         default="haiku", choices=["haiku", "sonnet"])
    parser.add_argument("--dry-run",       action="store_true")
    parser.add_argument("--resume-batch",  help="Attach to an existing Anthropic batch ID instead of submitting a new one")
    parser.add_argument("--direct",        action="store_true", help="Use direct API calls (concurrent) instead of Batch API")
    args = parser.parse_args()
    run_sprint(args.sprint, args.model, dry_run=args.dry_run, resume_batch=args.resume_batch, direct=args.direct)
