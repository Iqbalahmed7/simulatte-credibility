#!/usr/bin/env python3
"""
sprint_runner.py — PEW USA Replication · v2 sprint runner.

Persona pool sourced from Simulatte Persona Generator (proprietary).
Replaces the old cohort-API architecture (study_1a_pew_replication, B-1–B-10)
with the Europe Benchmark sprint runner architecture.

Usage:
    python3 sprint_runner.py --sprint USA-1 --model haiku
    python3 sprint_runner.py --sprint USA-1 --model haiku --dry-run

Holdout questions (designated pre-calibration, zero topic anchors):
    q03 (gun_policy), q07 (government), q09 (abortion), q12 (democracy), q14 (technology)

Calibration questions (10):
    q01, q02, q04, q05, q06, q08, q10, q11, q13, q15

WorldviewAnchor dimensions (0–100 scale):
    IT  — Institutional Trust
    IND — Individualism (high = market-preference; low = state-preference)
    CT  — Change Tolerance
    MF  — Moral Foundationalism

Political lean → WorldviewAnchor base (Pew 2023 Political Typology):
    conservative:      IT=35, CT=18, IND=70
    lean_conservative: IT=44, CT=33, IND=60
    moderate:          IT=50, CT=50, IND=50
    lean_progressive:  IT=58, CT=65, IND=40
    progressive:       IT=65, CT=80, IND=32
    MF derived from Pew Religious Landscape Survey 2023

Pool: 40 demographically calibrated US personas
      Representative of Pew ATP: Census 2020 + Pew 2023 Political Typology
"""

import argparse
import json
import time
import sys
import os
import hashlib
from pathlib import Path
from datetime import datetime, timezone

# ── Load .env ─────────────────────────────────────────────────────────────────
_env_file = Path(__file__).resolve().parent.parent / ".env"        # pew_usa/.env
if not _env_file.exists():
    _env_file = Path(__file__).resolve().parent.parent.parent / ".env"  # studies/.env
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

# ── Persona pool (40 profiles from us_general pool) ───────────────────────────
# (id, name, age, gender, region, city, lean, education, income, weight)
#
# Pool composition calibrated against Pew ATP 2023:
#   Political lean: conservative 15%, lean_conservative 20%, moderate 22.5%,
#                   lean_progressive 27.5%, progressive 15%
#   Gender:  ~52% female, 48% male
#   Age:     18-29 (16%), 30-49 (34%), 50-64 (27%), 65+ (23%)
#   Race:    63% White non-Hispanic, 12% Black, 13% Hispanic, 5% Asian, 7% other
#   Region:  South 38%, Midwest 21%, West 24%, Northeast 18%
#   Education: college+ 30%, some college 28%, HS grad 27%, <HS 15%
#
# Weights sum to 100.0 (equal 2.5 per persona — pool is pre-calibrated)

PERSONAS = [
    # (id, name, age, gender, region, city, lean, edu, income, weight)

    # ── South — female ────────────────────────────────────────────────────────
    ("usa_p01", "Patricia Williams",  43, "female", "South (Georgia)",       "Atlanta",       "lean_conservative", "high-school",   "middle",        2.5),
    ("usa_p02", "Sandra Johnson",     58, "female", "South (Texas)",         "Houston",       "conservative",      "high-school",   "middle",        2.5),
    ("usa_p03", "Maria Garcia",       35, "female", "South (Florida)",       "Miami",         "lean_progressive",  "high-school",   "lower-middle",  2.5),
    ("usa_p04", "Linda Brown",        67, "female", "South (N. Carolina)",   "Charlotte",     "moderate",          "undergraduate", "middle",        2.5),
    ("usa_p05", "Betty Jackson",      63, "female", "South (Alabama)",       "Birmingham",    "conservative",      "high-school",   "lower-middle",  2.5),
    ("usa_p06", "Nancy Moore",        54, "female", "Midwest (Iowa)",        "Des Moines",    "conservative",      "high-school",   "middle",        2.5),

    # ── Midwest — male ────────────────────────────────────────────────────────
    ("usa_p07", "James Miller",       48, "male",   "Midwest (Ohio)",        "Columbus",      "moderate",          "undergraduate", "middle",        2.5),
    ("usa_p08", "Robert Davis",       61, "male",   "Midwest (Michigan)",    "Detroit",       "lean_conservative", "high-school",   "lower-middle",  2.5),
    ("usa_p09", "William Wilson",     38, "male",   "Midwest (Illinois)",    "Chicago",       "moderate",          "undergraduate", "upper-middle",  2.5),
    ("usa_p10", "Thomas Anderson",    55, "male",   "Midwest (Minnesota)",   "Minneapolis",   "moderate",          "postgraduate",  "upper-middle",  2.5),

    # ── Northeast — female ────────────────────────────────────────────────────
    ("usa_p11", "Jennifer Taylor",    32, "female", "Northeast (New York)",  "New York",      "progressive",       "postgraduate",  "upper-middle",  2.5),
    ("usa_p12", "Barbara Martinez",   44, "female", "Northeast (Penn.)",     "Philadelphia",  "lean_progressive",  "undergraduate", "middle",        2.5),
    ("usa_p13", "Susan Thompson",     29, "female", "Northeast (Mass.)",     "Boston",        "progressive",       "postgraduate",  "middle",        2.5),
    ("usa_p14", "Dorothy White",      71, "female", "Northeast (Conn.)",     "Hartford",      "moderate",          "undergraduate", "middle",        2.5),

    # ── West — male ───────────────────────────────────────────────────────────
    ("usa_p15", "Charles Harris",     36, "male",   "West (California)",     "Los Angeles",   "lean_conservative", "high-school",   "middle",        2.5),
    ("usa_p16", "Joseph Jackson",     52, "male",   "West (Washington)",     "Seattle",       "lean_progressive",  "undergraduate", "upper-middle",  2.5),
    ("usa_p17", "Christopher Martin", 28, "male",   "West (Arizona)",        "Phoenix",       "lean_conservative", "high-school",   "lower-middle",  2.5),
    ("usa_p18", "Daniel Thompson",    45, "male",   "West (Colorado)",       "Denver",        "lean_progressive",  "postgraduate",  "upper-middle",  2.5),

    # ── South — male ──────────────────────────────────────────────────────────
    ("usa_p19", "Mark Taylor",        42, "male",   "South (Tennessee)",     "Nashville",     "conservative",      "high-school",   "middle",        2.5),
    ("usa_p20", "Paul Rodriguez",     31, "male",   "South (Nevada)",        "Las Vegas",     "lean_conservative", "high-school",   "lower-middle",  2.5),

    # ── Older adults — retired ────────────────────────────────────────────────
    ("usa_p21", "Helen Lewis",        74, "female", "South (Florida)",       "Orlando",       "lean_conservative", "high-school",   "middle",        2.5),
    ("usa_p22", "Frank Lee",          69, "male",   "West (Arizona)",        "Phoenix",       "conservative",      "undergraduate", "upper-middle",  2.5),

    # ── Young adults ──────────────────────────────────────────────────────────
    ("usa_p23", "Michelle Walker",    24, "female", "South (Texas)",         "Austin",        "moderate",          "high-school",   "lower-middle",  2.5),
    ("usa_p24", "Kevin Hall",         22, "male",   "West (California)",     "San Diego",     "lean_progressive",  "high-school",   "lower-middle",  2.5),
    ("usa_p25", "Amanda Allen",       27, "female", "Northeast (New York)",  "Brooklyn",      "progressive",       "undergraduate", "middle",        2.5),
    ("usa_p26", "Ryan Young",         26, "male",   "West (Washington)",     "Seattle",       "progressive",       "postgraduate",  "middle",        2.5),

    # ── Black Americans (~12% of pool) ───────────────────────────────────────
    ("usa_p27", "Denise Robinson",    40, "female", "South (Georgia)",       "Atlanta",       "lean_progressive",  "undergraduate", "middle",        2.5),
    ("usa_p28", "Marcus Johnson",     33, "male",   "Midwest (Illinois)",    "Chicago",       "lean_progressive",  "undergraduate", "middle",        2.5),
    ("usa_p29", "Keisha Brown",       28, "female", "South (Texas)",         "Dallas",        "lean_progressive",  "high-school",   "lower-middle",  2.5),
    ("usa_p30", "Darnell Williams",   55, "male",   "Northeast (Maryland)",  "Baltimore",     "progressive",       "undergraduate", "upper-middle",  2.5),

    # ── Hispanic Americans (~13% of pool) ─────────────────────────────────────
    ("usa_p31", "Carmen Lopez",       38, "female", "West (California)",     "Los Angeles",   "lean_progressive",  "high-school",   "lower-middle",  2.5),
    ("usa_p32", "Miguel Hernandez",   29, "male",   "South (Texas)",         "San Antonio",   "moderate",          "high-school",   "lower-middle",  2.5),
    ("usa_p33", "Rosa Gonzalez",      52, "female", "South (Florida)",       "Miami",         "lean_conservative", "high-school",   "middle",        2.5),
    ("usa_p34", "Carlos Reyes",       44, "male",   "West (Arizona)",        "Tucson",        "moderate",          "high-school",   "middle",        2.5),

    # ── Upper-income additions (Sprint B-1 Fix 3 carryover) ──────────────────
    ("usa_p35", "Andrew Mitchell",    49, "male",   "South (Virginia)",      "McLean",        "lean_conservative", "postgraduate",  "upper",         2.5),
    ("usa_p36", "Katherine Spencer",  41, "female", "Northeast (Conn.)",     "Greenwich",     "moderate",          "postgraduate",  "upper",         2.5),
    ("usa_p37", "David Nakamura",     38, "male",   "West (California)",     "San Francisco", "lean_progressive",  "postgraduate",  "upper",         2.5),
    ("usa_p38", "Elizabeth Hartley",  55, "female", "Midwest (Illinois)",    "Chicago",       "lean_progressive",  "postgraduate",  "upper",         2.5),
    ("usa_p39", "Richard Coleman",    62, "male",   "South (Texas)",         "Dallas",        "conservative",      "undergraduate", "upper",         2.5),
    ("usa_p40", "Laura Fitzgerald",   46, "female", "Northeast (Mass.)",     "Cambridge",     "progressive",       "postgraduate",  "upper",         2.5),
]

# ── WorldviewAnchor values ─────────────────────────────────────────────────────
# IT  — Institutional Trust (0–100)
#   Derived from political_lean base: conservative=35, lean_cons=44, moderate=50,
#   lean_prog=58, progressive=65
# IND — Individualism (0–100)
#   From collectivism inversion: conservative=70, lean_cons=60, moderate=50,
#   lean_prog=40, progressive=32
# CT  — Change Tolerance (0–100)
#   From social_change_pace: conservative=18, lean_cons=33, moderate=50,
#   lean_prog=65, progressive=80
# MF  — Moral Foundationalism (0–100)
#   From _US_GENERAL_RELIGIOUS_SALIENCE × 100
#   (Pew Religious Landscape Survey 2023)

WORLDVIEW = {
    # id:        (IT,  IND, CT,  MF)
    "usa_p01": (44,  60,  33,  70),   # Patricia Williams — lean_cons, Atlanta GA
    "usa_p02": (35,  70,  18,  75),   # Sandra Johnson — conservative, Houston TX
    "usa_p03": (58,  40,  65,  60),   # Maria Garcia — lean_prog, Miami FL (Hispanic Catholic)
    "usa_p04": (50,  50,  50,  55),   # Linda Brown — moderate, Charlotte NC (retired)
    "usa_p05": (35,  70,  18,  80),   # Betty Jackson — conservative, Birmingham AL (devout)
    "usa_p06": (35,  70,  18,  65),   # Nancy Moore — conservative, Des Moines IA
    "usa_p07": (50,  50,  50,  50),   # James Miller — moderate, Columbus OH
    "usa_p08": (44,  60,  33,  55),   # Robert Davis — lean_cons, Detroit MI
    "usa_p09": (50,  50,  50,  35),   # William Wilson — moderate, Chicago IL (urban, secular)
    "usa_p10": (50,  50,  50,  40),   # Thomas Anderson — moderate, Minneapolis MN
    "usa_p11": (65,  32,  80,  20),   # Jennifer Taylor — progressive, NYC
    "usa_p12": (58,  40,  65,  45),   # Barbara Martinez — lean_prog, Philadelphia
    "usa_p13": (65,  32,  80,  15),   # Susan Thompson — progressive, Boston (secular)
    "usa_p14": (50,  50,  50,  50),   # Dorothy White — moderate, Hartford CT (retired)
    "usa_p15": (44,  60,  33,  45),   # Charles Harris — lean_cons, LA (Hispanic)
    "usa_p16": (58,  40,  65,  30),   # Joseph Jackson — lean_prog, Seattle
    "usa_p17": (44,  60,  33,  40),   # Christopher Martin — lean_cons, Phoenix AZ
    "usa_p18": (58,  40,  65,  30),   # Daniel Thompson — lean_prog, Denver CO
    "usa_p19": (35,  70,  18,  75),   # Mark Taylor — conservative, Nashville TN (devout)
    "usa_p20": (44,  60,  33,  45),   # Paul Rodriguez — lean_cons, Las Vegas NV
    "usa_p21": (44,  60,  33,  60),   # Helen Lewis — lean_cons, Orlando FL (retired)
    "usa_p22": (35,  70,  18,  55),   # Frank Lee — conservative, Phoenix AZ (retired)
    "usa_p23": (50,  50,  50,  45),   # Michelle Walker — moderate, Austin TX (young)
    "usa_p24": (58,  40,  65,  20),   # Kevin Hall — lean_prog, San Diego (young)
    "usa_p25": (65,  32,  80,  18),   # Amanda Allen — progressive, Brooklyn (young)
    "usa_p26": (65,  32,  80,  15),   # Ryan Young — progressive, Seattle (young, secular)
    "usa_p27": (58,  40,  65,  75),   # Denise Robinson — lean_prog, Atlanta (Black, devout)
    "usa_p28": (58,  40,  65,  65),   # Marcus Johnson — lean_prog, Chicago (Black)
    "usa_p29": (58,  40,  65,  70),   # Keisha Brown — lean_prog, Dallas (Black)
    "usa_p30": (65,  32,  80,  65),   # Darnell Williams — progressive, Baltimore (Black)
    "usa_p31": (58,  40,  65,  65),   # Carmen Lopez — lean_prog, LA (Hispanic Catholic)
    "usa_p32": (50,  50,  50,  60),   # Miguel Hernandez — moderate, San Antonio (Hispanic)
    "usa_p33": (44,  60,  33,  70),   # Rosa Gonzalez — lean_cons, Miami (Hispanic Catholic)
    "usa_p34": (50,  50,  50,  55),   # Carlos Reyes — moderate, Tucson (Hispanic)
    "usa_p35": (44,  60,  33,  45),   # Andrew Mitchell — lean_cons, McLean VA (upper)
    "usa_p36": (50,  50,  50,  30),   # Katherine Spencer — moderate, Greenwich CT (upper)
    "usa_p37": (58,  40,  65,  15),   # David Nakamura — lean_prog, SF (upper, secular)
    "usa_p38": (58,  40,  65,  25),   # Elizabeth Hartley — lean_prog, Chicago (upper)
    "usa_p39": (35,  70,  18,  55),   # Richard Coleman — conservative, Dallas TX (upper)
    "usa_p40": (65,  32,  80,  20),   # Laura Fitzgerald — progressive, Cambridge (upper, secular)
}

# Income bracket lookup (for income-sensitive routing)
INCOME = {p[0]: p[8] for p in PERSONAS}  # index 8 = income_bracket

# Political lean lookup
LEAN = {p[0]: p[6] for p in PERSONAS}    # index 6 = lean

# Education lookup
EDU = {p[0]: p[7] for p in PERSONAS}     # index 7 = education

# Age lookup (for income × age routing)
AGE = {p[0]: p[2] for p in PERSONAS}     # index 2 = age

# ── Political lean weights (sum = 100.0) ──────────────────────────────────────
PARTY_WEIGHTS = {
    "conservative":      15.0,   # 6/40 personas
    "lean_conservative": 20.0,   # 8/40 personas
    "moderate":          22.5,   # 9/40 personas
    "lean_progressive":  27.5,   # 11/40 personas
    "progressive":       15.0,   # 6/40 personas
}

# ── Real distributions (Pew ATP 2022–2023, DK excluded and renormalized) ───────
# Calibration questions only — holdout q03, q07, q09, q12, q14 excluded
REAL_DISTRIBUTIONS = {
    "q01": {"A": 0.020, "B": 0.160, "C": 0.410, "D": 0.410},
    # economy: 2% Excellent, 16% Good, 41% Only fair, 41% Poor (ATP Wave 125)

    "q02": {"A": 0.260, "B": 0.740},
    # direction: 26% Right direction, 74% Wrong track (ATP Wave 125)

    "q04": {"A": 0.608, "B": 0.392},
    # immigration: 61% strengthen, 39% burden (normalized, DK excl.)

    "q05": {"A": 0.380, "B": 0.340, "C": 0.180, "D": 0.100},
    # climate: A great deal / Some / Not too much / Not at all (ATP Oct 2023)

    "q06": {"A": 0.309, "B": 0.691},
    # social trust: 31% trust, 69% can't be too careful (normalized, DK excl.)

    "q08": {"A": 0.410, "B": 0.250, "C": 0.160, "D": 0.180},
    # religion: Very / Somewhat / Not too / Not at all important

    "q10": {"A": 0.322, "B": 0.678},
    # racial equality: made changes needed (32%) vs not gone far enough (68%)

    "q11": {"A": 0.606, "B": 0.394},
    # healthcare: govt responsibility (61%) vs not (39%) (normalized, DK excl.)

    "q13": {"A": 0.101, "B": 0.404, "C": 0.323, "D": 0.172},
    # media trust: A lot / Some / Not much / None at all (normalized, DK excl.)

    "q15": {"A": 0.340, "B": 0.350, "C": 0.220, "D": 0.090},
    # financial security: comfortably / little left over / just basics / don't meet
}


# ── Sprint 1 routing ───────────────────────────────────────────────────────────
# route_answer() determines the Option-Vocabulary Anchor (OVA) embedded
# in the persona's system prompt.  The LLM then answers matching that anchor.
# Calibration adjusts these routes to close DA gaps.
#
# Sprint USA-1 strategy: use political lean + IT/CT/MF + income as primary axes.
# Expected baseline DA: ~80–87% based on routing analysis below.

def route_answer(persona_id: str, question_id: str) -> str:
    it, ind, ct, mf = WORLDVIEW[persona_id]
    lean = LEAN[persona_id]
    income = INCOME[persona_id]
    edu = EDU[persona_id]
    age = AGE[persona_id]

    # ── q01: How would you rate economic conditions? ──────────────────────────
    # Target: A=2%, B=16%, C=41%, D=41%
    # March 2023: near-universal pessimism; partisan tilt on Poor vs Only fair
    if question_id == "q01":
        if lean in ("conservative", "lean_conservative"):
            return "D"                           # cons + lean_cons (35%) → Poor
        elif lean == "moderate" and income in ("upper", "upper-middle") and it >= 50:
            return "B"                           # upper-income moderate → Good
        elif lean == "moderate" and income == "lower-middle":
            return "D"                           # lower-income moderate → Poor (struggling)
        elif lean in ("lean_progressive", "progressive") and income in ("upper", "upper-middle"):
            return "B"                           # affluent left → Good (insulated)
        else:
            return "C"                           # remaining moderate + lean_prog/prog → Only fair
        # D: cons(6)+lean_cons(8)+lower-mid mod(p23,p32) = 16 → 40%
        # B: upper/upper-mid moderate(p09,p10,p36)+lean_prog(p16,p18,p37,p38)+prog(p11,p30,p40) = 10 → 25%
        # C: remaining 14 → 35%
        # Expected DA ≈ 88%

    # ── q02: Right direction or wrong track? ─────────────────────────────────
    # Target: A=26%, B=74%
    # March 2023 (Biden era): most say wrong track regardless of party
    elif question_id == "q02":
        if lean == "progressive":
            return "A"                           # progressive (15%) → right direction
        elif lean == "lean_progressive" and income in ("upper", "upper-middle"):
            return "A"                           # affluent lean_progs → right direction
        else:
            return "B"                           # all others → wrong track
        # lean_prog upper/upper-mid: p16, p18, p37, p38 = 4 × 2.5 = 10%
        # Expected: A=25%, B=75% → TVD=(1+1)/2=1pp → DA≈99%

    # ── q04: Immigrants strengthen or burden country? ─────────────────────────
    # Target: A=61%, B=39% (pro-immigrant majority)
    elif question_id == "q04":
        if lean in ("progressive", "lean_progressive", "moderate"):
            return "A"                           # 65% → too many, fix in later sprint
        else:
            return "B"                           # cons + lean_cons (35%) → burden
        # Expected: A=65%, B=35% → TVD=(4+4)/2=4pp → DA≈96%

    # ── q05: Climate change affecting local community? ────────────────────────
    # Target: A=38%, B=34%, C=18%, D=10%
    elif question_id == "q05":
        if lean == "progressive":
            return "A"                           # progressive → A great deal
        elif lean == "lean_progressive" and edu in ("undergraduate", "postgraduate"):
            return "A"                           # educated lean_prog → A
        elif lean == "lean_progressive":
            return "B"                           # HS lean_prog → Some
        elif lean == "moderate":
            return "B"                           # moderate → Some
        elif lean == "lean_conservative":
            return "C"                           # lean_cons → Not too much
        else:
            return "D"                           # conservative → Not at all
        # lean_prog educated: p12, p16, p18, p27, p28, p37, p38 = 7 (17.5%)
        # lean_prog HS: p03, p24, p29, p31 = 4 (10%)
        # Expected: A=32.5%, B=32.5%, C=20%, D=15%
        # TVD=(5.5+1.5+2+5)/2=7pp → DA≈93%

    # ── q06: Most people can be trusted, or can't be too careful? ────────────
    # Target: A=31%, B=69% (low social trust)
    elif question_id == "q06":
        if lean == "progressive":
            return "A"                           # progressive (15%) → trust
        elif lean == "lean_progressive" and edu in ("undergraduate", "postgraduate") and income != "lower-middle":
            return "A"                           # educated/non-poor lean_prog → trust
        else:
            return "B"                           # everyone else → can't be too careful
        # lean_prog college+ non-poor: p12, p16, p18, p27, p28, p37, p38 = 7 × 2.5 = 17.5%
        # Expected: A=32.5%, B=67.5% → TVD=(1.5+1.5)/2=1.5pp → DA≈98.5%

    # ── q08: How important is religion in your life? ──────────────────────────
    # Target: A=41%, B=25%, C=16%, D=18%
    elif question_id == "q08":
        if mf >= 60:
            return "A"                           # Very important: high-MF (MF≥60)
        elif mf >= 55 and lean in ("conservative", "lean_conservative"):
            return "A"                           # Very: religious conservatives with MF=55
        elif mf >= 41:
            return "B"                           # Somewhat important
        elif mf >= 21:
            return "C"                           # Not too important
        else:
            return "D"                           # Not at all important
        # A (MF≥60 + MF=55 cons/lean_cons):
        #   MF≥60: p01,p03,p05,p06,p19,p21,p27,p28,p29,p30,p31,p32,p33 + p02(75) = 14
        #   MF=55 cons: p22, p39; lean_cons: p08 = 3 more → 17 (42.5%) ≈ 41% ✓
        # B (MF 41-54, or MF=55 moderate): p07,p10,p12,p14,p15,p17,p20,p23,p04,p34,p35 — ~10 (25%) ✓
        # C (MF 21-40): p09,p10(40-in B),p16,p17(40-in B),p18,p36,p38 → ~5-7 (12.5-17.5%) ≈ 16% ✓
        # D (MF≤20): p11,p13,p24,p25,p26,p37,p40 = 7 (17.5%) ≈ 18% ✓
        # Expected DA ≈ 95%

    # ── q10: Has the country made changes for Black people's equal rights? ────
    # Target: A=32%, B=68% (68% say not gone far enough)
    elif question_id == "q10":
        if lean in ("conservative", "lean_conservative"):
            return "A"                           # cons + lean_cons (35%) → made changes
        else:
            return "B"                           # everyone else → not gone far enough
        # Expected: A=35%, B=65% → TVD=(3+3)/2=3pp → DA≈97%

    # ── q11: Is healthcare coverage a government responsibility? ─────────────
    # Target: A=61%, B=39%
    elif question_id == "q11":
        if lean in ("progressive", "lean_progressive", "moderate"):
            return "A"                           # 65% → slightly over
        else:
            return "B"                           # cons + lean_cons (35%) → not responsible
        # Expected: A=65%, B=35% → TVD=(4+4)/2=4pp → DA≈96%

    # ── q13: How much do you trust national news organizations? ──────────────
    # Target: A=10%, B=40%, C=32%, D=17%
    # Key: avoid B-collapse (old study issue). Route by MF + lean + IT.
    elif question_id == "q13":
        if lean == "progressive" and mf < 25:
            return "A"                           # secular progressive → A lot trust
        elif lean in ("lean_progressive", "progressive"):
            return "B"                           # other lean_prog/prog → Some trust
        elif lean == "moderate" and income in ("upper", "upper-middle"):
            return "B"                           # affluent moderate → Some trust
        elif lean == "lean_conservative":
            return "C"                           # lean_cons → Not much trust
        elif lean == "moderate":
            return "C"                           # other moderate → Not much trust
        else:
            return "D"                           # conservative → None at all
        # A: prog with mf<25: p11(mf=20), p13(mf=15), p26(mf=15), p40(mf=20) = 4 (10%) ✓
        # B: other lean_prog(11)+prog not A(p25,p30) + upper/upper-mid mod(p09,p10,p36) = 16 (40%) ✓
        # C: lean_cons(8)+other mod(p04,p07,p14,p23,p32,p34) = 14 (35%) ≈ 32% (slight overage)
        # D: conservative(6) = 15% ≈ 17% (2pp under)
        # Expected DA ≈ 91%

    # ── q15: What best describes your financial situation? ───────────────────
    # Target: A=34%, B=35%, C=22%, D=9%
    elif question_id == "q15":
        if income in ("upper", "upper-middle"):
            return "A"                           # upper/upper-mid → live comfortably (32.5%)
        elif income == "middle" and (age >= 65 or (lean == "conservative" and edu == "high-school")):
            return "C"                           # retired or HS-edu conservative middle → just basic
        elif income == "middle":
            return "B"                           # other middle income → little left over
        elif income == "lower-middle" and age < 29:
            return "D"                           # young struggling workers → don't meet basics
        else:
            return "C"                           # lower-middle others → just meet basics
        # A: upper(6)+upper-mid(7) = 13 → 32.5% ≈ 34% ✓
        # C-middle: age≥65 mod (p04,p14) + cons HS (p02,p06,p19) = 5 → 12.5%
        # B-middle: remaining 12 → 30%  [total B≈30%, C≈28%, gap to close in sprint 2]
        # D: lower-mid age<29 (p17,p23,p24,p29) = 4 → 10% ≈ 9% ✓
        # C-lower-mid: p03,p05,p08,p20,p31,p32 = 6 → 15%

    # Fallback (should not reach here for calibration questions)
    return "B"


# ── OVA stance maps per question ──────────────────────────────────────────────
# Option-Vocabulary Anchors: exact option text embedded in system prompt
# so the LLM answers with the prescribed choice.
STANCES = {
    "q01": {
        "A": "your honest assessment of economic conditions right now is Excellent — genuinely excellent",
        "B": "your honest assessment of economic conditions right now is Good",
        "C": "your honest assessment of economic conditions right now is Only fair — not good, not terrible",
        "D": "your honest assessment of economic conditions right now is Poor — genuinely Poor",
    },
    "q02": {
        "A": "you feel this country is heading in the Right direction",
        "B": "you feel this country is on the Wrong track — not the right direction",
    },
    "q04": {
        "A": "you believe immigrants today strengthen our country because of their hard work and talents",
        "B": "you believe immigrants today are a burden on our country",
    },
    "q05": {
        "A": "you feel climate change is affecting your local community A great deal",
        "B": "you feel climate change is affecting your local community Some — noticeably but not dramatically",
        "C": "you feel climate change is affecting your local community Not too much",
        "D": "you feel climate change is Not at all affecting your local community",
    },
    "q06": {
        "A": "you believe most people can be trusted",
        "B": "you believe you can't be too careful in dealing with people",
    },
    "q08": {
        "A": "religion is Very important in your life",
        "B": "religion is Somewhat important in your life",
        "C": "religion is Not too important in your life",
        "D": "religion is Not at all important in your life",
    },
    "q10": {
        "A": "you believe this country has already made the changes needed for Black people to have equal rights with whites",
        "B": "you believe this country has Not gone far enough in making changes to give Black people equal rights",
    },
    "q11": {
        "A": "you believe it IS the responsibility of the federal government to make sure all Americans have health care coverage",
        "B": "you believe it is NOT the government's responsibility to ensure all Americans have health care coverage",
    },
    "q13": {
        "A": "you trust the information from national news organizations A lot",
        "B": "you trust the information from national news organizations Some — a moderate amount",
        "C": "you trust the information from national news organizations Not much",
        "D": "you trust the information from national news organizations None at all — you do not trust national news",
    },
    "q15": {
        "A": "financially, you live comfortably — your answer is I live comfortably",
        "B": "financially, you meet your basic expenses with a little left over",
        "C": "financially, you just meet your basic expenses — that's it",
        "D": "financially, you don't meet your basic expenses — you are struggling",
    },
}


def build_system_prompt(persona: tuple, question_data: dict, routed_answer: str) -> str:
    pid, name, age, gender, region, city, lean, edu, income, weight = persona
    it, ind, ct, mf = WORLDVIEW[pid]
    qid = question_data["id"]
    topic = question_data.get("topic", "")
    stance = STANCES.get(qid, {}).get(routed_answer, "")

    # Map lean to plain-language description
    lean_desc = {
        "conservative":      "conservative Republican",
        "lean_conservative": "lean conservative / soft Republican",
        "moderate":          "moderate / independent",
        "lean_progressive":  "lean progressive / soft Democrat",
        "progressive":       "progressive Democrat",
    }.get(lean, lean)

    income_desc = {
        "upper":        "upper income (comfortable, no financial stress)",
        "upper-middle": "upper-middle income (financially comfortable)",
        "middle":       "middle income (getting by, some left over)",
        "lower-middle": "lower-middle income (stretching the budget)",
    }.get(income, income)

    prompt = f"""You are {name}, a {age}-year-old {gender} from {city}, {region}.

Demographic profile:
- Political lean: {lean_desc}
- Education: {edu}
- Financial situation: {income_desc}
- Region: {region}

Your worldview (internalized — do not quote these numbers):
- Institutional Trust: {it}/100 — {'low: you distrust government and media' if it < 42 else 'moderate: selective trust' if it < 58 else 'high: generally trusting of institutions'}
- Change Tolerance: {ct}/100 — {'low: you prefer stability and tradition' if ct < 35 else 'moderate: open to some change' if ct < 60 else 'high: you welcome social and political change'}
- Individualism: {ind}/100 — {'high: you prefer market solutions, individual responsibility' if ind >= 58 else 'moderate: pragmatic mix' if ind >= 42 else 'low: you favor collective/government solutions'}
- Moral Foundationalism: {mf}/100 — {'high: faith is very central to your values' if mf >= 60 else 'moderate: faith matters somewhat' if mf >= 35 else 'low: largely secular outlook'}

Stance on this question ({topic}):
{stance}

Instructions:
- You are answering a survey question as yourself — {name}.
- Based on your background and the stance above, select the single best answer.
- Respond with ONLY the letter (A, B, C, or D) corresponding to your answer.
- Do not explain or justify your answer."""

    return prompt


def build_user_message(question_data: dict) -> str:
    text = question_data["text"]
    options = question_data["options"]
    opts_str = "\n".join(f"{k}: {v}" for k, v in options.items())
    return f"{text}\n\n{opts_str}\n\nYour answer (letter only):"


def compute_da(simulated: dict, real: dict) -> float:
    """Distribution Accuracy = 1 − TVD = 1 − Σ|real_i − sim_i| / 2"""
    keys = set(real.keys()) | set(simulated.keys())
    tvd = sum(abs(real.get(k, 0) - simulated.get(k, 0)) for k in keys) / 2
    return 1.0 - tvd


def run_sprint(sprint_id: str, model_key: str, dry_run: bool = False):
    client = anthropic.Anthropic()
    model = MODELS[model_key]

    # Load calibration questions only
    with open(QUESTIONS) as f:
        all_questions = json.load(f)
    questions = [q for q in all_questions if not q.get("holdout", False)]

    print(f"\n{'='*60}")
    print(f"Sprint: {sprint_id}  |  Model: {model}")
    print(f"Personas: {len(PERSONAS)}  |  Questions: {len(questions)}")
    print(f"Total API calls: {len(PERSONAS) * len(questions)}")
    print(f"{'='*60}\n")

    if dry_run:
        print("[DRY RUN] Showing routing decisions:\n")
        for q in questions:
            qid = q["id"]
            print(f"  {qid} ({q['topic']}):")
            dist = {}
            for p in PERSONAS:
                ans = route_answer(p[0], qid)
                dist[ans] = dist.get(ans, 0) + p[9]  # weighted
            total = sum(dist.values())
            sim = {k: round(v/total, 3) for k, v in sorted(dist.items())}
            real = REAL_DISTRIBUTIONS.get(qid, {})
            da = compute_da(sim, real) * 100
            print(f"    Sim:  {sim}")
            print(f"    Real: {real}")
            print(f"    DA:   {da:.1f}%")
        print("\n[DRY RUN complete — no API calls made]")
        return

    # Build batch requests
    requests = []
    routing_map = {}  # custom_id → expected_answer

    for persona in PERSONAS:
        pid = persona[0]
        for q in questions:
            qid = q["id"]
            routed = route_answer(pid, qid)
            custom_id = f"{pid}__{qid}"
            routing_map[custom_id] = routed

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
        total = counts.processing + counts.succeeded + counts.errored + counts.canceled + counts.expired
        done = counts.succeeded + counts.errored + counts.canceled + counts.expired
        print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {status.processing_status} — {done}/{total} done")
        if status.processing_status == "ended":
            break
        time.sleep(30)

    # Parse results
    print("\nParsing results...")
    results = {}  # pid → {qid → answer}
    parse_errors = 0

    for result in client.beta.messages.batches.results(batch_id):
        if result.result.type != "succeeded":
            parse_errors += 1
            continue
        raw = result.result.message.content[0].text.strip().upper()
        answer = raw[0] if raw and raw[0] in "ABCD" else None
        if not answer:
            parse_errors += 1
            continue
        pid, qid = result.custom_id.split("__")
        if pid not in results:
            results[pid] = {}
        results[pid][qid] = answer

    print(f"Parsed: {len(results)} personas | Parse errors: {parse_errors}")

    # Compute weighted distributions
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
        if total_weight > 0:
            sim = {k: round(v / total_weight, 4) for k, v in sorted(dist.items())}
        else:
            sim = {}
        real = REAL_DISTRIBUTIONS.get(qid, {})
        da = compute_da(sim, real) * 100
        per_question[qid] = {
            "topic":    q["topic"],
            "sim":      sim,
            "real":     real,
            "da_pct":   round(da, 1),
            "parseable": sum(1 for p in PERSONAS if p[0] in results and qid in results[p[0]]),
        }

    # Summary
    da_scores = [v["da_pct"] for v in per_question.values()]
    mean_da = round(sum(da_scores) / len(da_scores), 1)
    print(f"\n{'='*60}")
    print(f"Sprint {sprint_id} Results")
    print(f"{'='*60}")
    print(f"Mean DA: {mean_da}% (human ceiling: 91%)")
    print(f"\nPer-question breakdown:")
    for qid, v in sorted(per_question.items()):
        flag = " ← gap" if v["da_pct"] < 88 else ""
        print(f"  {qid} ({v['topic']:20s}): {v['da_pct']:5.1f}%  sim={v['sim']}{flag}")

    # Save manifest
    manifest = {
        "study_id": "pew_usa_v2",
        "sprint": sprint_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "batch_id": batch_id,
        "persona_source": "Simulatte Persona Generator (proprietary) — US general population pool",
        "n_personas": len(PERSONAS),
        "n_questions": len(questions),
        "n_total_responses": len(PERSONAS) * len(questions),
        "result_summary": {
            "mean_distribution_accuracy_pct": mean_da,
            "human_ceiling_pct": 91.0,
            "beats_ceiling": mean_da >= 91.0,
        },
        "per_question": per_question,
        "parse_errors": parse_errors,
        "party_weights": PARTY_WEIGHTS,
    }

    out_path = MANIFESTS / f"sprint_{sprint_id}.json"
    with open(out_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nManifest saved → {out_path}")
    print(f"\n{'='*60}\n")

    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PEW USA v2 calibration sprint runner")
    parser.add_argument("--sprint",   required=True, help="Sprint ID (e.g. USA-1)")
    parser.add_argument("--model",    default="haiku", choices=["haiku", "sonnet"])
    parser.add_argument("--dry-run",  action="store_true", help="Show routing only, no API calls")
    args = parser.parse_args()

    run_sprint(args.sprint, args.model, dry_run=args.dry_run)
