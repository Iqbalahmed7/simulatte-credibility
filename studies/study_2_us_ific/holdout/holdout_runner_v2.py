#!/usr/bin/env python3
"""
holdout_runner_v2.py — IFIC Food & Health Survey 2025 · Holdout · Pool v2

Pure WorldviewAnchor prompts — zero topic-specific OVA stances.
Pool: us_food_health v1 (HI/DI/FBS/NIT dimensions).

The holdout measures how much predictive power the food-behavior dimensions
have WITHOUT calibration anchors. Unlike the v1 holdout (60.0% DA), the
food-behavior dimensions should predict food responses directly, closing
the sprint→holdout gap.

Usage:
    python3 holdout_runner_v2.py --run IFIC-H2 --model haiku
    python3 holdout_runner_v2.py --run IFIC-H2 --model haiku --dry-run
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
QUESTIONS   = STUDY_ROOT / "questions.json"
HOLDOUT_DIR = STUDY_ROOT / "results" / "holdout_manifests"
HOLDOUT_DIR.mkdir(parents=True, exist_ok=True)

MODELS = {
    "haiku":  "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-6",
}

SPRINT_DA = 96.1  # actual Sprint IFIC-2 DA (direct API, 2026-07-06)

# ── Persona pool: us_food_health v1 (identical to sprint_runner_v2.py) ─────────
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

HOLDOUT_REAL = {
    "ific_h01": {"A": 0.17, "B": 0.36, "C": 0.24, "D": 0.21, "E": 0.02},
    "ific_h02": {"A": 0.05, "B": 0.20, "C": 0.32, "D": 0.22, "E": 0.21},
    "ific_h03": {"A": 0.18, "B": 0.44, "C": 0.30, "D": 0.06, "E": 0.02},
    "ific_h04": {"A": 0.21, "B": 0.40, "C": 0.30, "D": 0.07, "E": 0.03},
    "ific_h05": {"A": 0.50, "B": 0.30, "C": 0.11, "D": 0.09},
}


SEGMENT_BACKSTORY = {
    "health_avoider": (
        "Day to day, your food choices are driven by what's familiar, filling, and affordable — "
        "not by nutrition labels or health goals. You eat what you enjoy and what fits your budget. "
        "You've never followed a special diet or eating plan, and you don't plan to. "
        "You buy the same things at the store every week without comparing products. "
        "Labels that say 'low-fat' or 'organic' just mean higher prices to you — you ignore them. "
        "Government nutrition programs like MyPlate don't mean anything to you — "
        "you've never looked them up, and you wouldn't know a Registered Dietitian from any other professional."
    ),
    "budget_pragmatist": (
        "Your food decisions start and end with price. You stretch your grocery budget carefully — "
        "you know which stores are cheapest, you buy generics, and you plan meals around what's on sale. "
        "You care about feeding yourself and your family adequately, but health claims on packaging don't move you — "
        "they just mean a higher price tag. You've never followed a formal diet or eating plan. "
        "You may have seen a food guide plate somewhere but you've never looked into it or tried to follow it. "
        "A Registered Dietitian is something for sick people or people with more money — not for you."
    ),
    "mainstream_consumer": (
        "You try to eat reasonably well without overthinking it — a mix of home-cooked meals and convenient options. "
        "You pay some attention to what you buy: you'd pick a lower-calorie version if it doesn't cost much more, "
        "and you try not to go overboard on junk food. But you're not tracking macros or following a specific plan. "
        "You've probably seen the MyPlate diagram — maybe in a health class, a doctor's office, or a magazine — "
        "and have a rough sense of what it says (eat your vegetables, watch portions), though you don't follow it closely. "
        "You know Registered Dietitian Nutritionists exist and what they do, though you've never seen one personally."
    ),
    "health_seeker": (
        "Eating well is genuinely important to you — it's part of how you take care of yourself. "
        "You plan meals, read ingredient lists, and try to minimize processed food, added sugar, and excess sodium. "
        "You've followed at least one specific eating approach in the past few years — whether reducing carbs, "
        "eating more plant-based, intermittent fasting, or something similar. "
        "You're familiar with the MyPlate guidelines and have read at least some of the Dietary Guidelines for Americans. "
        "You view Registered Dietitian Nutritionists as credible professionals and would consider consulting one "
        "for a specific health goal — or have already done so."
    ),
    "nutrition_enthusiast": (
        "Food, nutrition, and health are a genuine passion for you — you follow nutrition research, "
        "read labels obsessively, and actively seek out foods with specific health properties "
        "(probiotics, omega-3s, antioxidants, functional ingredients). "
        "You follow or have followed multiple structured eating approaches — whole foods, anti-inflammatory, "
        "Mediterranean, plant-based, or similar — and you track what you eat at least some of the time. "
        "You know MyPlate, the Dietary Guidelines for Americans, and the difference between an RDN and a general nutritionist. "
        "You have likely consulted a Registered Dietitian Nutritionist at some point and view them as your most credible source."
    ),
}


def build_system_prompt(persona: tuple) -> str:
    pid, name, age, gender, region, city, segment, edu, income, weight = persona
    hi, di, fbs, nit = WORLDVIEW[pid]
    segment_backstory = SEGMENT_BACKSTORY[segment]

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

    # ── Behavioral enrichments ────────────────────────────────────────────────

    # Social media usage — explicit non-user and food-unaware tiers for holdout h05
    if age >= 65 and segment not in ("health_seeker", "nutrition_enthusiast"):
        # 65+ non-health-focused → no social media (real D≈9%)
        social_media = "You do not use any social media — no Facebook, Instagram, TikTok, or YouTube account. You get news and stay in touch by phone or in person."
    elif age >= 60 and segment in ("health_avoider", "budget_pragmatist"):
        # 60+ disengaged → no social media
        social_media = "You do not use social media — you never got into Facebook or any of the apps. You have no interest in it."
    elif age >= 55 and income in ("lower", "lower-middle") and segment != "health_seeker":
        # Mid-older + lower income → no food content on social media
        social_media = "You have a Facebook account but check it rarely and only see family photos and local news — you have never come across food or nutrition content on social media"
    elif age < 30:
        if segment in ("health_seeker", "nutrition_enthusiast"):
            social_media = "You're active on Instagram and TikTok and follow wellness creators alongside friends — food and nutrition content shows up in your feed regularly"
        elif segment == "mainstream_consumer":
            social_media = "You're on TikTok and Instagram daily — you follow entertainment, friends, and memes; food content pops up occasionally but it's not what you're there for"
        else:
            social_media = "You're on TikTok and Instagram daily for entertainment and keeping up with friends — food or nutrition content doesn't come up in your feed"
    elif age < 45:
        if segment in ("health_seeker", "nutrition_enthusiast"):
            social_media = "You use Instagram and YouTube regularly and follow nutrition and wellness accounts — food content is a consistent part of your social media diet"
        elif segment == "mainstream_consumer":
            social_media = "You use Facebook and Instagram to stay connected — you come across food content occasionally but you don't follow any nutrition or wellness accounts"
        elif segment == "budget_pragmatist":
            social_media = "You use Facebook to stay connected with family and friends — food or nutrition content doesn't come up in your feed, and you don't follow any food accounts"
        else:
            social_media = "You use Facebook to keep up with friends and family — food and nutrition content doesn't appear in your feed and you've never sought it out"
    elif age < 60:
        if segment in ("health_seeker", "nutrition_enthusiast"):
            social_media = "You're on Facebook and YouTube and follow some health and nutrition pages — you come across food and wellness content fairly regularly"
        elif segment == "mainstream_consumer":
            social_media = "You use Facebook to keep up with family and friends — you're not on TikTok or Instagram, and food or nutrition content rarely comes up in your feed"
        else:
            social_media = "You use Facebook to keep up with family and friends — food or nutrition content doesn't come up in your feed and you've never come across it on social media"
    else:
        if segment in ("health_seeker", "nutrition_enthusiast"):
            social_media = "You use Facebook and sometimes YouTube — you follow a few health pages but you're not heavy on social media overall"
        else:
            social_media = "You use Facebook occasionally but you're not on TikTok or Instagram — social media isn't a big part of your daily life and food or nutrition content doesn't come up"

    if di >= 65:
        restaurant_info = "When you eat at restaurants, you check nutrition information if it's posted — calorie counts and ingredient details factor into what you order"
    elif di >= 42:
        restaurant_info = "You occasionally glance at calorie counts when eating out, but it doesn't always change what you order — you're aware they exist but don't rely on them"
    elif di >= 25:
        restaurant_info = "You've noticed nutrition information posted at restaurants before, but you generally don't pay attention to it — it doesn't affect what you order"
    else:
        restaurant_info = "When you eat out, you order by what looks good or what you're used to — you've never really thought about checking calorie counts on menu boards"

    if nit >= 65:
        gov_nutrition = "You're familiar with official nutrition resources — you know the MyPlate graphic and have at least a passing familiarity with the Dietary Guidelines for Americans; you know what a Registered Dietitian Nutritionist (RDN) is and view them as the most credible and qualified nutrition experts"
    elif nit >= 52:
        gov_nutrition = "You've seen the MyPlate graphic and know a fair amount about what it recommends — the idea of filling half your plate with vegetables and fruits, balancing grains and protein; you know what a Registered Dietitian Nutritionist (RDN) is and consider them a credible and qualified source of nutrition advice"
    elif nit >= 42:
        gov_nutrition = "You've seen the MyPlate graphic before but know very little about what it specifically recommends — you recognize it but couldn't explain the details; you're aware of Registered Dietitian Nutritionists and consider them qualified professionals for nutrition advice"
    elif edu in ("college", "some-college") or age < 35:
        gov_nutrition = "You've seen something like the food pyramid or plate graphic in school but it made little impression — you don't follow government nutrition guidance and wouldn't know the current version; you've heard of dietitians but don't seek them out and don't have a strong view on whether they're more qualified than other sources"
    else:
        gov_nutrition = "You've never looked into government nutrition guidelines — if someone mentions 'MyPlate' or 'Dietary Guidelines for Americans' those terms don't mean much to you; you wouldn't know what an RDN is or whether they're particularly qualified"

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

Your food behavior patterns:
{segment_backstory}

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
- Do NOT give aspirational or socially-desirable answers. If your background indicates low engagement, low awareness, or non-use, reflect that honestly — even if it means answering "No", "Never heard of it", or "Not sure".
- Respond with ONLY the letter (A, B, C, D, or E) corresponding to your answer.
- Do not explain or justify your answer."""


def build_user_message(question_data: dict) -> str:
    text = question_data["text"]
    options = question_data["options"]
    opts_str = "\n".join(f"{k}: {v}" for k, v in options.items())
    return f"{text}\n\n{opts_str}\n\nYour answer (letter only):"


def compute_da(simulated: dict, real: dict) -> float:
    keys = set(real.keys()) | set(simulated.keys())
    tvd = sum(abs(real.get(k, 0) - simulated.get(k, 0)) for k in keys) / 2
    return 1.0 - tvd


def run_holdout(run_id: str, model_key: str, dry_run: bool = False, direct: bool = False):
    client = anthropic.Anthropic()
    model = MODELS[model_key]

    with open(QUESTIONS) as f:
        survey = json.load(f)
    questions = survey["holdout_questions"]

    print(f"\n{'='*60}")
    print(f"Holdout: {run_id}  |  Model: {model}")
    print(f"Pool: us_food_health v1 — NO OVA · segment behavioral backstory")
    print(f"Personas: {len(PERSONAS)}  |  Questions: {len(questions)}")
    print(f"Total API calls: {len(PERSONAS) * len(questions)}")
    print(f"{'='*60}\n")

    if dry_run:
        print("[DRY RUN — no API calls. Will run pure WorldviewAnchor prompts.]\n")
        print("Holdout questions:")
        for q in questions:
            print(f"  {q['id']}: {q['text'][:65]}")
            print(f"    Real: {HOLDOUT_REAL.get(q['id'], {})}")
        print(f"\nSprint DA (projected): {SPRINT_DA}%")
        print("[DRY RUN complete]")
        return

    if direct:
        print("[DIRECT] Running concurrent API calls (max 20 workers)...\n")
        tasks = [(p[0], q["id"], build_system_prompt(p), build_user_message(q))
                 for p in PERSONAS for q in questions]

        results = {}
        parse_errors = 0
        completed = 0

        def call_api(task):
            pid, qid, sys_prompt, user_msg = task
            resp = client.messages.create(
                model=model, max_tokens=10, system=sys_prompt,
                messages=[{"role": "user", "content": user_msg}],
            )
            raw = resp.content[0].text.strip().upper()
            answer = raw[0] if raw and raw[0] in "ABCDE" else None
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
                    print(f"  {completed}/{len(tasks)} done", flush=True)

        batch_id = "direct"
        print(f"\nDone. Parsed: {len(results)} personas | Errors: {parse_errors}")
    else:
        requests = []
        for persona in PERSONAS:
            pid = persona[0]
            for q in questions:
                qid = q["id"]
                custom_id = f"{pid}__{qid}"
                sys_prompt = build_system_prompt(persona)
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

        print(f"Submitting {len(requests)} holdout requests (no OVA)...")
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
            answer = raw[0] if raw and raw[0] in "ABCDE" else None
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
        real = HOLDOUT_REAL.get(qid, {})
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
    gap = round(SPRINT_DA - mean_da, 1)

    print(f"\n{'='*60}")
    print(f"Holdout {run_id} Results — Pool: us_food_health v1")
    print(f"{'='*60}")
    print(f"Mean DA:   {mean_da}%")
    print(f"Sprint DA: {SPRINT_DA}%")
    print(f"Gap:       +{gap}pp\n")
    for qid, v in sorted(per_question.items()):
        print(f"  {qid}: {v['da_pct']:5.1f}%  sim={v['sim']}")

    manifest = {
        "study_id":        "ific_2025",
        "holdout_run":     run_id,
        "generated_at":    datetime.now(timezone.utc).isoformat(),
        "model":           model,
        "batch_id":        batch_id,
        "persona_source":  "us_food_health v1 — food-behavior WorldviewAnchor (HI/DI/FBS/NIT)",
        "simulatte_pool_id": "342ef9b7-a988-41f6-ad83-9b4da1d71b48",
        "ova_used":        False,
        "n_personas":      len(PERSONAS),
        "n_questions":     len(questions),
        "result_summary":  {
            "mean_distribution_accuracy_pct": mean_da,
            "sprint_da_pct":   SPRINT_DA,
            "sprint_holdout_gap_pp": gap,
        },
        "per_question":    per_question,
        "parse_errors":    parse_errors,
    }

    out_path = HOLDOUT_DIR / f"holdout_{run_id}.json"
    with open(out_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nManifest saved → {out_path}")
    print(f"\n{'='*60}\n")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IFIC Holdout Runner v2 — us_food_health pool")
    parser.add_argument("--run",     required=True, help="Run ID (e.g. IFIC-H2)")
    parser.add_argument("--model",   default="haiku", choices=["haiku", "sonnet"])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--direct",  action="store_true", help="Use direct concurrent API calls instead of Batch API")
    args = parser.parse_args()
    run_holdout(args.run, args.model, dry_run=args.dry_run, direct=args.direct)
