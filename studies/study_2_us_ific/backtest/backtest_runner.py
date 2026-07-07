#!/usr/bin/env python3
"""
backtest_runner.py — IFIC Food & Health Survey 2025 · Blind Back-Test

Tests the us_food_health v1 persona pool against 12 IFIC 2025 items that were
NOT used in Sprint IFIC-2 calibration. Pure WorldviewAnchor prediction — no OVA.

Covers: Q1 (HI), Q2a-e (purchase drivers), Q3 (DI), Q4a-e (NIT trust),
        Q5 (DI+NIT), Q6 (FBS), Q7 (DI+HI), Q8 (DI), Q9 (HI),
        Q10 (FBS+HI), Q11 (NIT-reverse), Q12 (HI+DI)

Real distributions are estimated from IFIC 2025 published toplines.
Replace REAL_DIST values with exact marginals once the full report is in hand.

Usage:
    python3 backtest_runner.py --run BT-1 --model sonnet --direct
    python3 backtest_runner.py --run BT-1 --model sonnet --dry-run
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
    print("ERROR: anthropic package not found.")
    sys.exit(1)

HERE        = Path(__file__).resolve().parent
STUDY_ROOT  = HERE.parent
BACKTEST_DIR = STUDY_ROOT / "results" / "backtest_manifests"
BACKTEST_DIR.mkdir(parents=True, exist_ok=True)

MODELS = {
    "haiku":  "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-6",
}

SPRINT_DA = 96.1  # Sprint IFIC-2 (direct API, 2026-07-06)

# ── Persona pool: us_food_health v1 ────────────────────────────────────────
PERSONAS = [
    ("fh_p01", "Jason Miller",       24, "male",   "South (Tennessee)",     "Memphis",       "health_avoider",        "high-school",   "lower",         3.0),
    ("fh_p02", "Brandon Davis",      33, "male",   "Midwest (Ohio)",         "Columbus",      "health_avoider",        "high-school",   "lower-middle",  3.0),
    ("fh_p03", "Steve Cooper",       62, "male",   "South (Alabama)",        "Birmingham",    "health_avoider",        "high-school",   "lower",         3.0),
    ("fh_p04", "Tammy Reed",         28, "female", "South (Texas)",          "Houston",       "health_avoider",        "high-school",   "lower-middle",  3.0),
    ("fh_p05", "Gary Torres",        47, "male",   "West (Nevada)",          "Las Vegas",     "health_avoider",        "high-school",   "lower-middle",  3.0),
    ("fh_p06", "Destiny Washington", 22, "female", "South (Georgia)",        "Atlanta",       "budget_pragmatist",     "some-college",  "lower",         20/7),
    ("fh_p07", "Carlos Mendez",      35, "male",   "West (California)",      "Fresno",        "budget_pragmatist",     "high-school",   "lower-middle",  20/7),
    ("fh_p08", "Shanice Brown",      29, "female", "Midwest (Illinois)",     "Chicago",       "budget_pragmatist",     "some-college",  "lower-middle",  20/7),
    ("fh_p09", "Mike Patterson",     52, "male",   "South (Mississippi)",    "Jackson",       "budget_pragmatist",     "high-school",   "lower-middle",  20/7),
    ("fh_p10", "Rosa Flores",        38, "female", "South (Texas)",          "San Antonio",   "budget_pragmatist",     "some-college",  "lower-middle",  20/7),
    ("fh_p11", "Kevin Murphy",       44, "male",   "Northeast (Penn.)",      "Pittsburgh",    "budget_pragmatist",     "high-school",   "lower-middle",  20/7),
    ("fh_p12", "Brenda Clark",       55, "female", "South (N. Carolina)",    "Raleigh",       "budget_pragmatist",     "some-college",  "lower-middle",  20/7),
    ("fh_p13", "Lisa Thompson",      35, "female", "South (Florida)",        "Tampa",         "mainstream_consumer",   "some-college",  "middle",        30/11),
    ("fh_p14", "David Kim",          42, "male",   "West (California)",      "Sacramento",    "mainstream_consumer",   "bachelors",     "middle",        30/11),
    ("fh_p15", "Maria Ramirez",      52, "female", "South (Texas)",          "Dallas",        "mainstream_consumer",   "some-college",  "middle",        30/11),
    ("fh_p16", "James Williams",     38, "male",   "Midwest (Michigan)",     "Detroit",       "mainstream_consumer",   "some-college",  "middle",        30/11),
    ("fh_p17", "Patricia Nelson",    65, "female", "South (Georgia)",        "Savannah",      "mainstream_consumer",   "some-college",  "middle",        30/11),
    ("fh_p18", "Chris Nguyen",       29, "male",   "West (California)",      "San Jose",      "mainstream_consumer",   "some-college",  "middle",        30/11),
    ("fh_p19", "Rebecca Moore",      47, "female", "Northeast (New York)",   "Albany",        "mainstream_consumer",   "bachelors",     "middle",        30/11),
    ("fh_p20", "Frank Jackson",      55, "male",   "South (Virginia)",       "Richmond",      "mainstream_consumer",   "high-school",   "middle",        30/11),
    ("fh_p21", "Susan Harris",       31, "female", "Midwest (Minnesota)",    "Minneapolis",   "mainstream_consumer",   "bachelors",     "middle",        30/11),
    ("fh_p22", "Tony Martinez",      44, "male",   "South (Texas)",          "Austin",        "mainstream_consumer",   "some-college",  "middle",        30/11),
    ("fh_p23", "Dorothy Johnson",    70, "female", "South (Tennessee)",      "Memphis",       "mainstream_consumer",   "high-school",   "middle",        30/11),
    ("fh_p24", "Jennifer Park",      32, "female", "West (California)",      "Los Angeles",   "health_seeker",         "bachelors",     "upper-middle",  25/9),
    ("fh_p25", "Ashley Brooks",      45, "female", "South (Virginia)",       "Arlington",     "health_seeker",         "bachelors",     "upper-middle",  25/9),
    ("fh_p26", "Ryan Patel",         38, "male",   "West (California)",      "San Diego",     "health_seeker",         "bachelors",     "upper-middle",  25/9),
    ("fh_p27", "Karen Mitchell",     55, "female", "Northeast (Mass.)",      "Boston",        "health_seeker",         "bachelors",     "upper-middle",  25/9),
    ("fh_p28", "Andre Thomas",       42, "male",   "Midwest (Illinois)",     "Chicago",       "health_seeker",         "bachelors",     "upper-middle",  25/9),
    ("fh_p29", "Stephanie White",    28, "female", "South (Texas)",          "Dallas",        "health_seeker",         "bachelors",     "upper-middle",  25/9),
    ("fh_p30", "Daniel Hughes",      50, "male",   "West (Colorado)",        "Denver",        "health_seeker",         "bachelors",     "upper",         25/9),
    ("fh_p31", "Michelle Lee",       36, "female", "West (California)",      "San Francisco", "health_seeker",         "bachelors",     "upper-middle",  25/9),
    ("fh_p32", "Robert Campbell",    48, "male",   "South (Georgia)",        "Atlanta",       "health_seeker",         "some-college",  "upper-middle",  25/9),
    ("fh_p33", "Amanda Foster",      34, "female", "West (California)",      "Los Angeles",   "nutrition_enthusiast",  "postgraduate",  "upper",         2.5),
    ("fh_p34", "Sarah Chen",         42, "female", "Northeast (Mass.)",      "Cambridge",     "nutrition_enthusiast",  "postgraduate",  "upper-middle",  2.5),
    ("fh_p35", "Michael Grant",      38, "male",   "West (Oregon)",          "Portland",      "nutrition_enthusiast",  "postgraduate",  "upper",         2.5),
    ("fh_p36", "Lauren Walsh",       29, "female", "West (California)",      "San Francisco", "nutrition_enthusiast",  "postgraduate",  "upper-middle",  2.5),
]

WORLDVIEW = {
    "fh_p01": (15,  12,  82,  20),
    "fh_p02": (22,  18,  78,  28),
    "fh_p03": (18,  15,  85,  22),
    "fh_p04": (25,  20,  72,  32),
    "fh_p05": (20,  16,  80,  25),
    "fh_p06": (40,  28,  88,  42),
    "fh_p07": (35,  25,  85,  38),
    "fh_p08": (45,  32,  82,  48),
    "fh_p09": (30,  22,  80,  32),
    "fh_p10": (48,  38,  78,  52),
    "fh_p11": (32,  24,  84,  36),
    "fh_p12": (42,  30,  76,  44),
    "fh_p13": (50,  45,  52,  55),
    "fh_p14": (48,  42,  48,  52),
    "fh_p15": (55,  48,  54,  58),
    "fh_p16": (45,  40,  56,  46),
    "fh_p17": (58,  50,  58,  60),
    "fh_p18": (42,  38,  46,  45),
    "fh_p19": (60,  52,  42,  62),
    "fh_p20": (40,  35,  60,  42),
    "fh_p21": (55,  50,  44,  58),
    "fh_p22": (48,  42,  50,  50),
    "fh_p23": (52,  45,  62,  55),
    "fh_p24": (72,  65,  32,  70),
    "fh_p25": (68,  62,  38,  65),
    "fh_p26": (65,  58,  30,  68),
    "fh_p27": (75,  70,  28,  72),
    "fh_p28": (62,  55,  42,  60),
    "fh_p29": (70,  65,  35,  68),
    "fh_p30": (65,  60,  25,  62),
    "fh_p31": (72,  68,  40,  72),
    "fh_p32": (62,  55,  45,  58),
    "fh_p33": (90,  88,  15,  85),
    "fh_p34": (88,  85,  20,  90),
    "fh_p35": (82,  80,  18,  82),
    "fh_p36": (92,  90,  12,  88),
}

# ── Back-test questions (20 items; estimated real distributions) ────────────
# NOTE: Real distributions marked "estimated" — replace with exact IFIC 2025
#       topline marginals once the full report is available.
BACKTEST_QUESTIONS = [
    {
        "id": "bt_q01",
        "axis": "HI",
        "text": "How important is the healthfulness of a food or beverage to you when deciding what to purchase?",
        "options": {"A": "Very important", "B": "Somewhat important", "C": "Not too important", "D": "Not at all important"},
        "real": {"A": 0.52, "B": 0.35, "C": 0.10, "D": 0.03},  # estimated
        "real_source": "estimated",
    },
    {
        "id": "bt_q02a",
        "axis": "HI+FBS",
        "text": "When shopping for food and beverages, how much impact does TASTE have on what you purchase?",
        "options": {"A": "Major impact", "B": "Minor impact", "C": "No impact"},
        "real": {"A": 0.84, "B": 0.12, "C": 0.04},  # exact top-2-box A=84% (G12/p28); B/C estimated
        "real_source": "exact_topbox (G12/p28, 4-5 box=84%); B/C estimated",
    },
    {
        "id": "bt_q02b",
        "axis": "FBS",
        "text": "When shopping for food and beverages, how much impact does PRICE/COST have on what you purchase?",
        "options": {"A": "Major impact", "B": "Minor impact", "C": "No impact"},
        "real": {"A": 0.71, "B": 0.20, "C": 0.09},  # exact top-2-box A=71% (G12/p28); B/C estimated
        "real_source": "exact_topbox (G12/p28, 4-5 box=71%); B/C estimated",
    },
    {
        "id": "bt_q02c",
        "axis": "HI",
        "text": "When shopping for food and beverages, how much impact does HEALTHFULNESS have on what you purchase?",
        "options": {"A": "Major impact", "B": "Minor impact", "C": "No impact"},
        "real": {"A": 0.57, "B": 0.31, "C": 0.12},  # exact top-2-box A=57% (G12/p28); B/C estimated
        "real_source": "exact_topbox (G12/p28, 4-5 box=57%); B/C estimated",
    },
    {
        "id": "bt_q02d",
        "axis": "FBS",
        "text": "When shopping for food and beverages, how much impact does CONVENIENCE have on what you purchase?",
        "options": {"A": "Major impact", "B": "Minor impact", "C": "No impact"},
        "real": {"A": 0.52, "B": 0.36, "C": 0.12},  # exact top-2-box A=52% (G12/p28); B/C estimated
        "real_source": "exact_topbox (G12/p28, 4-5 box=52%); B/C estimated",
    },
    {
        "id": "bt_q02e",
        "axis": "HI",
        "text": "When shopping for food and beverages, how much impact does SUSTAINABILITY/ENVIRONMENTAL IMPACT have on what you purchase?",
        "options": {"A": "Major impact", "B": "Minor impact", "C": "No impact"},
        "real": {"A": 0.27, "B": 0.45, "C": 0.28},  # exact top-2-box A=27% (G12/p28); B/C estimated
        "real_source": "exact_topbox (G12/p28, 4-5 box=27%); B/C estimated",
    },
    {
        "id": "bt_q03",
        "axis": "DI",
        "text": "In the past year, have you followed a specific diet or eating pattern (e.g., Mediterranean, low-carb/keto, intermittent fasting, vegetarian/vegan, gluten-free)?",
        "options": {"A": "Yes", "B": "No"},
        "real": {"A": 0.57, "B": 0.43},  # exact (N3/p54: 57% yes, 43% no)
        "real_source": "exact (N3/p54)",
    },
    {
        "id": "bt_q04a",
        "axis": "NIT",
        "text": "How much do you trust a Registered Dietitian Nutritionist (RDN) as a source of information about what to eat for good health?",
        "options": {"A": "A lot", "B": "Somewhat", "C": "Not too much", "D": "Not at all"},
        "real": {"A": 0.35, "B": 0.35, "C": 0.25, "D": 0.05},  # exact (G26/p43 RDN: 5=35,4=35,3+2=24→25,1=5; 5→A,4→B,3+2→C,1→D)
        "real_source": "exact (G26/p43, 5-pt: 5→A,4→B,3+2→C,1→D)",
    },
    {
        "id": "bt_q04b",
        "axis": "NIT",
        "text": "How much do you trust a Doctor or Physician as a source of information about what to eat for good health?",
        "options": {"A": "A lot", "B": "Somewhat", "C": "Not too much", "D": "Not at all"},
        "real": {"A": 0.35, "B": 0.35, "C": 0.26, "D": 0.04},  # exact (G26/p43 Doctor: 5=35,4=35,3+2=26,1=4)
        "real_source": "exact (G26/p43, 5-pt: 5→A,4→B,3+2→C,1→D)",
    },
    {
        "id": "bt_q04c",
        "axis": "NIT",
        "text": "How much do you trust Federal Government Dietary Guidelines as a source of information about what to eat for good health?",
        "options": {"A": "A lot", "B": "Somewhat", "C": "Not too much", "D": "Not at all"},
        "real": {"A": 0.15, "B": 0.27, "C": 0.45, "D": 0.13},  # exact (G26/p43 GovtAgency: 5=15,4=27,3+2=46→45,1=13)
        "real_source": "exact (G26/p43, 5-pt: 5→A,4→B,3+2→C,1→D)",
    },
    {
        "id": "bt_q04d",
        "axis": "NIT",
        "text": "How much do you trust Friends and Family as a source of information about what to eat for good health?",
        "options": {"A": "A lot", "B": "Somewhat", "C": "Not too much", "D": "Not at all"},
        "real": {"A": 0.11, "B": 0.26, "C": 0.58, "D": 0.05},  # exact (G26/p43 FriendFamily: 5=11,4=26,3+2=57→58,1=5)
        "real_source": "exact (G26/p43, 5-pt: 5→A,4→B,3+2→C,1→D)",
    },
    {
        "id": "bt_q04e",
        "axis": "NIT_reverse",
        "text": "How much do you trust Social Media Influencers or Online Personalities as a source of information about what to eat for good health?",
        "options": {"A": "A lot", "B": "Somewhat", "C": "Not too much", "D": "Not at all"},
        "real": {"A": 0.05, "B": 0.11, "C": 0.48, "D": 0.36},  # exact (G26/p43 SocialMedia: 5=5,4=11,3+2=47→48,1=36)
        "real_source": "exact (G26/p43, 5-pt: 5→A,4→B,3+2→C,1→D)",
    },
    {
        "id": "bt_q05",
        "axis": "DI+NIT",
        "text": "When purchasing a food or beverage for the first time, how often do you read the Nutrition Facts label or ingredients list before buying?",
        "options": {"A": "Always", "B": "Usually", "C": "Sometimes", "D": "Rarely", "E": "Never"},
        "real": {"A": 0.28, "B": 0.26, "C": 0.27, "D": 0.13, "E": 0.06},  # estimated
        "real_source": "estimated",
    },
    {
        "id": "bt_q06",
        "axis": "FBS",
        "text": "In the past year, food and beverage prices have risen. How much impact has this had on what you buy?",
        "options": {"A": "Major impact — I have significantly changed what I buy", "B": "Moderate impact — I have made some changes", "C": "Minor impact — I have made only small changes", "D": "No impact — I buy the same things as before"},
        "real": {"A": 0.42, "B": 0.34, "C": 0.16, "D": 0.08},  # estimated
        "real_source": "estimated",
    },
    {
        "id": "bt_q07",
        "axis": "DI+HI",
        "text": "Compared to a year ago, how has your consumption of protein changed?",
        "options": {"A": "I am consuming more protein than a year ago", "B": "About the same as a year ago", "C": "I am consuming less protein than a year ago"},
        "real": {"A": 0.33, "B": 0.53, "C": 0.14},  # estimated
        "real_source": "estimated",
    },
    {
        "id": "bt_q08",
        "axis": "DI",
        "text": "Are you currently limiting or avoiding sugar in your diet?",
        "options": {"A": "Yes, I actively limit or avoid sugar", "B": "I somewhat limit sugar but it is not a strong priority", "C": "No, I am not limiting or avoiding sugar"},
        "real": {"A": 0.14, "B": 0.61, "C": 0.25},  # exact (SW3/p71: avoid entirely=14%, limit=61%, not limiting=25%)
        "real_source": "exact (SW3/p71)",
    },
    {
        "id": "bt_q09",
        "axis": "HI",
        "text": "Overall, how would you grade your own diet in terms of healthfulness?",
        "options": {"A": "A (Excellent)", "B": "B (Good)", "C": "C (Average)", "D": "D (Below average)", "E": "F (Failing)"},
        "real": {"A": 0.13, "B": 0.51, "C": 0.28, "D": 0.06, "E": 0.01},  # from questions.json ific10 — exact
        "real_source": "exact (ific10/G3)",
    },
    {
        "id": "bt_q10",
        "axis": "FBS+HI",
        "text": "To what extent do you agree or disagree: 'Eating a healthy diet costs more money than eating an unhealthy diet.'",
        "options": {"A": "Strongly agree", "B": "Somewhat agree", "C": "Somewhat disagree", "D": "Strongly disagree"},
        "real": {"A": 0.42, "B": 0.37, "C": 0.14, "D": 0.07},  # estimated
        "real_source": "estimated",
    },
    {
        "id": "bt_q11",
        "axis": "NIT_reverse",
        "text": "In the past year, have you changed what you eat based on information you came across on social media?",
        "options": {"A": "Yes", "B": "No"},
        "real": {"A": 0.22, "B": 0.78},  # estimated
        "real_source": "estimated",
    },
    {
        "id": "bt_q12",
        "axis": "HI+DI",
        "text": "When buying food and beverages, how actively do you seek out products with specific functional benefits (e.g., gut health/probiotics, immune support, energy boost, weight management)?",
        "options": {"A": "Yes, I actively seek out functional benefit foods", "B": "I sometimes look for functional benefit foods", "C": "No, I do not specifically seek out functional benefit foods"},
        "real": {"A": 0.32, "B": 0.42, "C": 0.26},  # estimated
        "real_source": "estimated",
    },
]


def build_system_prompt(persona: tuple) -> str:
    pid, name, age, gender, region, city, segment, edu, income, weight = persona
    hi, di, fbs, nit = WORLDVIEW[pid]

    income_desc = {
        "upper":        "upper income (financially comfortable, food costs are not a concern)",
        "upper-middle": "upper-middle income (comfortable financially)",
        "middle":       "middle income (some discretionary spending, watches food budget)",
        "lower-middle": "lower-middle income (budget is tight, food prices really matter)",
        "lower":        "lower income (stretched financially, food costs are a constant concern)",
    }.get(income, income)

    health_identity = (
        "Nutrition and health are central to who you are — you actively track what you eat and make deliberate food choices"
        if hi >= 70 else
        "You care about eating reasonably well, but health isn't something you obsess over"
        if hi >= 48 else
        "Health and nutrition aren't really your focus — you eat what you enjoy and what's affordable"
    )

    dietary_approach = (
        "You read food labels carefully, plan meals, and actively manage what goes into your body"
        if di >= 65 else
        "You pay some attention to what you eat but don't follow a strict regimen"
        if di >= 38 else
        "Food choices are driven by taste, convenience, and cost — you rarely think about nutritional details"
    )

    budget_attitude = (
        "Food prices are a major stressor — you feel every price increase and make decisions based on cost first"
        if fbs >= 70 else
        "You keep an eye on food costs but they're not your primary concern"
        if fbs >= 40 else
        "Cost isn't a factor in your food decisions — you buy what you want"
    )

    nutrition_trust = (
        "You trust established nutrition science — you follow dietary guidelines and have confidence in nutrition expert advice"
        if nit >= 65 else
        "You're somewhat skeptical about official nutrition guidance — it seems to change too often to be reliable"
        if nit >= 40 else
        "You don't put much stock in government nutrition guidelines or expert dietary advice — you go by your own experience"
    )

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

    if di >= 65:
        restaurant_info = "When you eat at restaurants, you check nutrition information if it's posted — calorie counts and ingredient details factor into what you order"
    elif di >= 42:
        restaurant_info = "You occasionally glance at calorie counts when eating out, but it doesn't always change what you order — you're aware they exist but don't rely on them"
    elif di >= 25:
        restaurant_info = "You've noticed nutrition information posted at restaurants before, but you generally don't pay attention to it — it doesn't affect what you order"
    else:
        restaurant_info = "When you eat out, you order by what looks good or what you're used to — you've never really thought about checking calorie counts on menu boards"

    if nit >= 65:
        gov_nutrition = "You're familiar with official nutrition resources — you know the MyPlate graphic and have at least a passing familiarity with the Dietary Guidelines for Americans; you know what a Registered Dietitian Nutritionist (RDN) is and view them as credible experts"
    elif nit >= 42:
        gov_nutrition = "You've vaguely heard of government food guides and have probably seen the MyPlate plate graphic somewhere, though you don't know much about what it says; you've heard the term dietitian but aren't sure exactly what their credentials mean"
    elif edu in ("college", "some-college") or age < 35:
        gov_nutrition = "You've seen something like the food pyramid or plate graphic in school but it made little impression — you don't follow government nutrition guidance and wouldn't know the current version; you've heard of dietitians but don't seek them out"
    else:
        gov_nutrition = "You've never looked into government nutrition guidelines — if someone mentions 'MyPlate' or 'Dietary Guidelines for Americans' those terms don't mean much to you; you wouldn't know what an RDN is versus a regular nutritionist"

    if di < 25 or (hi < 35 and nit < 35):
        guidance_orientation = "You don't really engage with nutrition guidance — you don't follow food rules and you don't have a strong opinion about how nutrition advice should be framed"
    elif di >= 55 and hi >= 55:
        guidance_orientation = "When you come across nutrition advice, you respond better to positive framing — hearing what's good to add to your diet rather than long lists of what to cut out or avoid"
    else:
        guidance_orientation = "You somewhat prefer hearing about what's good to eat rather than what not to eat, but you're fairly open to either framing"

    return f"""You are {name}, a {age}-year-old {gender} from {city}, {region}.

Demographic profile:
- Education: {edu}
- Financial situation: {income_desc}
- Region: {region}

Your relationship with food and health:
- Health identity: {health_identity}
- Dietary approach: {dietary_approach}
- Budget attitude: {budget_attitude}
- Nutrition information: {nutrition_trust}

Your food world:
- Social media: {social_media}
- Eating out: {restaurant_info}
- Nutrition programs: {gov_nutrition}
- Food guidance: {guidance_orientation}

Instructions:
- Answer the food and health survey question as {name}, grounded entirely in the background above.
- Do NOT give aspirational or socially-desirable answers. If your background indicates low engagement or low awareness, reflect that honestly.
- Respond with ONLY the letter corresponding to your answer.
- Do not explain or justify your answer."""


def build_user_message(question: dict) -> str:
    opts_str = "\n".join(f"{k}: {v}" for k, v in question["options"].items())
    return f"{question['text']}\n\n{opts_str}\n\nYour answer (letter only):"


def compute_da(simulated: dict, real: dict) -> float:
    keys = set(real.keys()) | set(simulated.keys())
    tvd = sum(abs(real.get(k, 0) - simulated.get(k, 0)) for k in keys) / 2
    return 1.0 - tvd


def run_backtest(run_id: str, model_key: str, dry_run: bool = False, direct: bool = False):
    client = anthropic.Anthropic()
    model = MODELS[model_key]
    questions = BACKTEST_QUESTIONS
    valid_letters = set("ABCDEF")

    total_calls = len(PERSONAS) * len(questions)
    estimated_count = sum(1 for q in questions if q["real_source"] == "estimated")

    print(f"\n{'='*65}")
    print(f"Back-Test: {run_id}  |  Model: {model}")
    print(f"Pool: us_food_health v1 (36 personas — HI/DI/FBS/NIT)")
    print(f"Questions: {len(questions)} ({estimated_count} with estimated real distributions)")
    print(f"Total API calls: {total_calls}")
    print(f"{'='*65}\n")

    if dry_run:
        print("[DRY RUN — no API calls]\n")
        for q in questions:
            n_opts = len(q["options"])
            print(f"  {q['id']} [{q['axis']}] ({n_opts}-opt): {q['text'][:60]}")
            print(f"    Real ({q['real_source']}): {q['real']}")
        print(f"\nTotal: {total_calls} calls | Sprint DA: {SPRINT_DA}%")
        print("[DRY RUN complete]")
        return

    if not direct:
        print("NOTE: Batch API has been unreliable in this workspace. Use --direct for reliable results.\n")

    if direct:
        print("[DIRECT] Running concurrent API calls (max 20 workers)...\n")
        tasks = [(p[0], q["id"], build_system_prompt(p), build_user_message(q), q["options"])
                 for p in PERSONAS for q in questions]

        results = {}
        parse_errors = 0
        completed = 0

        def call_api(task):
            pid, qid, sys_prompt, user_msg, opts = task
            valid = set(opts.keys())
            resp = client.messages.create(
                model=model, max_tokens=10, system=sys_prompt,
                messages=[{"role": "user", "content": user_msg}],
            )
            raw = resp.content[0].text.strip().upper()
            answer = raw[0] if raw and raw[0] in valid else None
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
                except Exception as e:
                    parse_errors += 1
                if completed % 72 == 0 or completed == total_calls:
                    print(f"  {completed}/{total_calls} done", flush=True)

        batch_id = "direct"
        print(f"\nDone. Parsed: {len(results)} personas | Errors: {parse_errors}")
    else:
        requests = []
        for persona in PERSONAS:
            pid = persona[0]
            for q in questions:
                qid = q["id"]
                requests.append({
                    "custom_id": f"{pid}__{qid}",
                    "params": {
                        "model": model,
                        "max_tokens": 10,
                        "system": build_system_prompt(persona),
                        "messages": [{"role": "user", "content": build_user_message(q)}],
                    },
                })

        print(f"Submitting {len(requests)} batch requests...")
        batch = client.beta.messages.batches.create(requests=requests)
        batch_id = batch.id
        print(f"Batch ID: {batch_id}\n")

        while True:
            status = client.beta.messages.batches.retrieve(batch_id)
            counts = status.request_counts
            done = counts.succeeded + counts.errored + counts.canceled + counts.expired
            total = counts.processing + done
            print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {status.processing_status} — {done}/{total} done")
            if status.processing_status == "ended":
                break
            time.sleep(30)

        results = {}
        parse_errors = 0
        for result in client.beta.messages.batches.results(batch_id):
            if result.result.type != "succeeded":
                parse_errors += 1
                continue
            raw = result.result.message.content[0].text.strip().upper()
            pid, qid = result.custom_id.split("__")
            q = next((x for x in questions if x["id"] == qid), None)
            valid = set(q["options"].keys()) if q else valid_letters
            answer = raw[0] if raw and raw[0] in valid else None
            if not answer:
                parse_errors += 1
                continue
            if pid not in results:
                results[pid] = {}
            results[pid][qid] = answer

        print(f"Parsed: {len(results)} personas | Parse errors: {parse_errors}")

    # ── Compute per-question DA ──────────────────────────────────────────────
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
        real = q["real"]
        da = compute_da(sim, real) * 100
        per_question[qid] = {
            "axis":       q["axis"],
            "question":   q["text"][:65],
            "sim":        sim,
            "real":       real,
            "real_source": q["real_source"],
            "da_pct":     round(da, 1),
            "parseable":  sum(1 for p in PERSONAS if p[0] in results and qid in results[p[0]]),
        }

    # ── Axis roll-up ────────────────────────────────────────────────────────
    axis_map = {}
    for qid, v in per_question.items():
        for ax in v["axis"].replace("+", " ").split():
            if ax not in axis_map:
                axis_map[ax] = []
            axis_map[ax].append(v["da_pct"])
    axis_means = {ax: round(sum(vals) / len(vals), 1) for ax, vals in axis_map.items()}

    da_scores = [v["da_pct"] for v in per_question.values()]
    mean_da = round(sum(da_scores) / len(da_scores), 1)
    gap = round(SPRINT_DA - mean_da, 1)
    estimated_only = [v["da_pct"] for v in per_question.values() if v["real_source"] == "estimated"]
    exact_only = [v["da_pct"] for v in per_question.values() if v["real_source"] != "estimated"]

    print(f"\n{'='*65}")
    print(f"Back-Test {run_id} Results — Pool: us_food_health v1")
    print(f"{'='*65}")
    print(f"Mean DA (all {len(da_scores)} items):        {mean_da}%")
    if exact_only:
        print(f"Mean DA (exact distributions only): {round(sum(exact_only)/len(exact_only),1)}% (n={len(exact_only)})")
    print(f"Mean DA (estimated distributions):  {round(sum(estimated_only)/len(estimated_only),1)}% (n={len(estimated_only)})")
    print(f"Sprint IFIC-2 DA:                   {SPRINT_DA}%")
    print(f"Sprint → back-test gap:             +{gap}pp\n")
    print("Per-question:")
    for qid in sorted(per_question.keys()):
        v = per_question[qid]
        flag = " *est*" if v["real_source"] == "estimated" else " [exact]"
        print(f"  {qid} [{v['axis']:12s}]: {v['da_pct']:5.1f}%  sim={v['sim']}{flag}")
    print(f"\nAxis-level mean DA:")
    for ax, mean in sorted(axis_means.items()):
        print(f"  {ax:12s}: {mean}%")

    manifest = {
        "study_id":        "ific_2025_backtest",
        "backtest_run":    run_id,
        "generated_at":    datetime.now(timezone.utc).isoformat(),
        "model":           model,
        "batch_id":        batch_id,
        "persona_source":  "us_food_health v1 — food-behavior WorldviewAnchor (HI/DI/FBS/NIT)",
        "ova_used":        False,
        "n_personas":      len(PERSONAS),
        "n_questions":     len(questions),
        "estimated_distributions_note": f"{estimated_count}/{len(questions)} real distributions are estimated — replace with IFIC 2025 exact toplines",
        "result_summary":  {
            "mean_da_all_pct":              mean_da,
            "mean_da_exact_only_pct":       round(sum(exact_only)/len(exact_only),1) if exact_only else None,
            "mean_da_estimated_only_pct":   round(sum(estimated_only)/len(estimated_only),1),
            "sprint_da_pct":                SPRINT_DA,
            "sprint_backtest_gap_pp":       gap,
        },
        "axis_means":      axis_means,
        "per_question":    per_question,
        "parse_errors":    parse_errors,
    }

    out_path = BACKTEST_DIR / f"backtest_{run_id}.json"
    with open(out_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nManifest saved → {out_path}")
    print(f"{'='*65}\n")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IFIC 2025 Back-Test Runner — us_food_health v1")
    parser.add_argument("--run",     required=True, help="Run ID (e.g. BT-1)")
    parser.add_argument("--model",   default="sonnet", choices=["haiku", "sonnet"])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--direct",  action="store_true", help="Use direct concurrent API (recommended)")
    args = parser.parse_args()
    run_backtest(args.run, args.model, dry_run=args.dry_run, direct=args.direct)
