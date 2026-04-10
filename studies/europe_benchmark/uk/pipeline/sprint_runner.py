#!/usr/bin/env python3
"""
sprint_runner.py — Europe Benchmark · UK calibration sprint runner.

Usage:
    python3 sprint_runner.py --sprint UK-1 --model haiku
    python3 sprint_runner.py --sprint UK-5 --model sonnet
    python3 sprint_runner.py --sprint UK-1 --model haiku --dry-run

Model switching:
    UK-1 to UK-12: claude-haiku-4-5-20251001  (Batch API, ~80% cheaper)
    UK-13+:        claude-sonnet-4-6           (fine-tuning phase)

Outputs:
    results/sprint_manifests/sprint_{sprint_id}.json
    results/sprint_manifests/sprint_{sprint_id}_raw.jsonl

Cost estimate:
    Haiku (Batch API, 40 personas × 15 questions): ~$0.15 per sprint
    Sonnet (Batch API, 40 personas × 15 questions): ~$1.50 per sprint

WorldviewAnchor dimensions (0–100 scale):
    IT  — Institutional Trust
    IND — Individualism (market vs. state preference)
    CT  — Change Tolerance
    MF  — Moral Foundationalism

Key UK calibration axes:
    1. Brexit vote (Leave/Remain) — primary IT and CT signal
    2. Party (Conservative / Labour / Lib Dem / Reform / SNP / Non-partisan)
    3. Nation (England / Scotland / Wales / N.Ireland)
    4. Class/education (working class vocational vs. university educated)
    5. Age (under-40 Remainers vs. over-55 Leave voters)
"""

import argparse
import json
import time
import sys
import os
import hashlib
from pathlib import Path
from datetime import datetime, timezone

# Load .env from study root if present
_env_file = Path(__file__).resolve().parent.parent.parent.parent / ".env"
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

# ── Paths ─────────────────────────────────────────────────────────────────────
HERE       = Path(__file__).resolve().parent
STUDY_ROOT = HERE.parent
QUESTIONS  = STUDY_ROOT / "questions.json"
MANIFESTS  = STUDY_ROOT / "results" / "sprint_manifests"
MANIFESTS.mkdir(parents=True, exist_ok=True)

# ── Model map ─────────────────────────────────────────────────────────────────
MODELS = {
    "haiku":  "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-6",
}

# ── Persona pool ──────────────────────────────────────────────────────────────
# (id, name, age, gender, nation, region, party, brexit, religion, education, weight)
#
# Demographic targets (ONS / British Election Study):
#   Nation:    England 84%, Scotland 9%, Wales 5%, N.Ireland 3%
#   Party:     Conservative 28%, Labour 35%, Lib Dem 12%, Reform 8%, SNP 4%, Non-partisan 13%
#   Brexit:    Leave ~52%, Remain ~48% (2016 vote; Remain higher in younger cohort)
#   Religion:  Christian (Anglican/Catholic) 46%, None 37%, Muslim 6%, Other 11%
#   Education: University 44%, A-level/equivalent 26%, GCSE/vocational 30%
#   Age range: 26–72 (working-age + older cohort)
#
# 40 personas, weights sum to 100%

PERSONAS = [
    # (id, name, age, gender, nation/region, party, brexit, religion, education, weight)
    # ── Reform UK / ex-Brexit Party (populist nationalist, Leave) ───────────
    ("uk_p01", "Gary Stubbs",       58, "male",   "England (Midlands)",    "Reform",       "Leave",  "None/secular",  "GCSE/vocational",  2.5),
    ("uk_p02", "Tracey Mold",       54, "female", "England (North East)",  "Reform",       "Leave",  "None/secular",  "GCSE/vocational",  2.5),
    ("uk_p03", "Brian Tanner",      64, "male",   "England (East Anglia)", "Reform",       "Leave",  "Anglican",      "GCSE/vocational",  2.5),

    # ── Conservative (centre-right, mix of Leave/Remain) ─────────────────────
    ("uk_p04", "Nigel Forsythe",    67, "male",   "England (South East)",  "Conservative", "Leave",  "Anglican",      "University",       2.5),
    ("uk_p05", "Margaret Holt",     62, "female", "England (South West)",  "Conservative", "Leave",  "Anglican",      "GCSE/vocational",  2.5),
    ("uk_p06", "James Rothwell",    48, "male",   "England (South East)",  "Conservative", "Remain", "Anglican",      "University",       2.0),
    ("uk_p07", "Claire Whitmore",   52, "female", "England (Midlands)",    "Conservative", "Leave",  "Anglican",      "University",       2.0),
    ("uk_p08", "Edward Cavendish",  44, "male",   "England (South East)",  "Conservative", "Remain", "None/secular",  "University",       2.0),
    ("uk_p09", "Patricia Garner",   71, "female", "England (South West)",  "Conservative", "Leave",  "Anglican",      "GCSE/vocational",  2.5),
    ("uk_p10", "Robert Ashworth",   56, "male",   "England (North West)",  "Conservative", "Leave",  "Anglican",      "GCSE/vocational",  2.5),
    ("uk_p11", "Diana Sutton",      39, "female", "England (South East)",  "Conservative", "Remain", "None/secular",  "University",       2.0),

    # ── Labour (centre-left, predominantly Remain) ────────────────────────────
    ("uk_p12", "Kevin Doherty",     49, "male",   "England (North West)",  "Labour",       "Leave",  "None/secular",  "GCSE/vocational",  2.5),
    ("uk_p13", "Sharon Brennan",    45, "female", "England (North East)",  "Labour",       "Leave",  "None/secular",  "GCSE/vocational",  2.5),
    ("uk_p14", "Marcus Webb",       37, "male",   "England (London)",      "Labour",       "Remain", "None/secular",  "University",       2.5),
    ("uk_p15", "Priya Sharma",      32, "female", "England (London)",      "Labour",       "Remain", "Hindu",         "University",       2.5),
    ("uk_p16", "Ian Baxter",        53, "male",   "Wales",                 "Labour",       "Leave",  "None/secular",  "GCSE/vocational",  2.5),
    ("uk_p17", "Angela Moss",       41, "female", "England (Midlands)",    "Labour",       "Remain", "None/secular",  "University",       2.0),
    ("uk_p18", "Mohammed Rahman",   38, "male",   "England (North West)",  "Labour",       "Remain", "Muslim",        "University",       2.5),
    ("uk_p19", "Diane Okafor",      44, "female", "England (London)",      "Labour",       "Remain", "Christian",     "University",       2.0),
    ("uk_p20", "Thomas Hughes",     55, "male",   "Wales",                 "Labour",       "Leave",  "None/secular",  "GCSE/vocational",  2.5),

    # ── Liberal Democrats (pro-Remain, educated, suburban/Scotland) ───────────
    ("uk_p21", "Sarah Pemberton",   43, "female", "England (South West)",  "Lib Dem",      "Remain", "None/secular",  "University",       2.5),
    ("uk_p22", "Andrew Fairclough", 47, "male",   "England (South East)",  "Lib Dem",      "Remain", "Anglican",      "University",       2.5),
    ("uk_p23", "Fiona Crawford",    35, "female", "Scotland",              "Lib Dem",      "Remain", "None/secular",  "University",       2.0),
    ("uk_p24", "Oliver Kingsley",   29, "male",   "England (London)",      "Lib Dem",      "Remain", "None/secular",  "University",       2.0),

    # ── SNP (Scottish independence, Remain) ───────────────────────────────────
    ("uk_p25", "Alistair MacLeod",  51, "male",   "Scotland",              "SNP",          "Remain", "None/secular",  "University",       2.5),
    ("uk_p26", "Catriona Stewart",  46, "female", "Scotland",              "SNP",          "Remain", "None/secular",  "GCSE/vocational",  2.5),

    # ── Non-partisan / disengaged (cross-cutting, high Leave) ─────────────────
    ("uk_p27", "Dave Norris",       60, "male",   "England (Midlands)",    "Non-partisan", "Leave",  "None/secular",  "GCSE/vocational",  2.5),
    ("uk_p28", "Carol Simmons",     57, "female", "England (North East)",  "Non-partisan", "Leave",  "Anglican",      "GCSE/vocational",  2.5),
    ("uk_p29", "Nathan Cole",       33, "male",   "England (London)",      "Non-partisan", "Remain", "None/secular",  "University",       2.0),
    ("uk_p30", "Wendy Allison",     49, "female", "England (Midlands)",    "Non-partisan", "Leave",  "None/secular",  "GCSE/vocational",  2.5),
    ("uk_p31", "Reginald Firth",    68, "male",   "England (North)",       "Non-partisan", "Leave",  "Anglican",      "GCSE/vocational",  2.5),
    ("uk_p32", "Leila Hassan",      31, "female", "England (London)",      "Non-partisan", "Remain", "Muslim",        "University",       2.5),
    ("uk_p33", "George Findlay",    42, "male",   "Scotland",              "Non-partisan", "Remain", "None/secular",  "University",       2.0),
    ("uk_p34", "Joyce Williams",    63, "female", "Wales",                 "Non-partisan", "Leave",  "Anglican",      "GCSE/vocational",  2.5),

    # ── Diversity fill: younger, ethnic minority, urban Labour-adjacent ────────
    ("uk_p35", "Zara Ahmed",        26, "female", "England (London)",      "Labour",       "Remain", "Muslim",        "University",       2.5),
    ("uk_p36", "Callum Reid",       28, "male",   "Scotland",              "SNP",          "Remain", "None/secular",  "University",       2.0),
    ("uk_p37", "Sandra Price",      72, "female", "England (South West)",  "Conservative", "Leave",  "Anglican",      "GCSE/vocational",  2.5),
    ("uk_p38", "Joseph Murphy",     50, "male",   "England (North West)",  "Labour",       "Remain", "Catholic",      "GCSE/vocational",  2.5),
    ("uk_p39", "Hannah Boateng",    36, "female", "England (Midlands)",    "Labour",       "Remain", "Christian",     "University",       2.0),
    ("uk_p40", "Derek Parkinson",   61, "male",   "England (Midlands)",    "Reform",       "Leave",  "None/secular",  "GCSE/vocational",  2.5),
]

# ── WorldviewAnchor values ────────────────────────────────────────────────────
# IT  — Institutional Trust (0–100)
#   Key: Leave voters: 25–45; Remain mainstream: 52–70; SNP pro-EU: 55–68
#   England working class Leave: 22–38; London educated Remain: 60–72
#
# IND — Individualism (0–100)
#   Conservative/Reform: 55–78; Labour: 28–48; Lib Dem: 55–68
#
# CT  — Change Tolerance (0–100)
#   Remain/SNP/young Labour: 60–85; Leave/Reform/older Tory: 12–32
#
# MF  — Moral Foundationalism (0–100)
#   Muslim/devout Anglican: 55–75; secular/urban: 10–25; average: 30–50

WORLDVIEW = {
    # id:        (IT,  IND, CT,  MF)
    "uk_p01": (28,  52,  15,  22),   # Reform, Midlands, Leave, secular, vocational
    "uk_p02": (25,  48,  12,  20),   # Reform, NE, Leave, secular, vocational
    "uk_p03": (30,  55,  14,  35),   # Reform, East Anglia, Leave, Anglican, vocational
    "uk_p04": (52,  72,  28,  52),   # Tory, SE, Leave, Anglican, university
    "uk_p05": (45,  58,  20,  55),   # Tory, SW, Leave, Anglican, vocational
    "uk_p06": (62,  70,  50,  40),   # Tory, SE, Remain, Anglican, university
    "uk_p07": (48,  62,  32,  45),   # Tory, Midlands, Leave, Anglican, university
    "uk_p08": (60,  75,  52,  22),   # Tory, SE, Remain, secular, university
    "uk_p09": (42,  55,  18,  58),   # Tory, SW, Leave, Anglican, vocational — older
    "uk_p10": (40,  58,  22,  42),   # Tory, NW, Leave, Anglican, vocational
    "uk_p11": (65,  68,  58,  25),   # Tory, SE, Remain, secular, university — younger
    "uk_p12": (38,  38,  40,  28),   # Labour, NW, Leave, secular, vocational
    "uk_p13": (35,  35,  38,  25),   # Labour, NE, Leave, secular, vocational
    "uk_p14": (62,  50,  72,  15),   # Labour, London, Remain, secular, university
    "uk_p15": (65,  52,  75,  32),   # Labour, London, Remain, Hindu, university
    "uk_p16": (40,  40,  42,  30),   # Labour, Wales, Leave, secular, vocational
    "uk_p17": (60,  48,  68,  18),   # Labour, Midlands, Remain, secular, university
    "uk_p18": (55,  45,  62,  65),   # Labour, NW, Remain, Muslim, university
    "uk_p19": (62,  50,  70,  45),   # Labour, London, Remain, Christian, university
    "uk_p20": (38,  38,  40,  28),   # Labour, Wales, Leave, secular, vocational
    "uk_p21": (68,  62,  78,  20),   # Lib Dem, SW, Remain, secular, university
    "uk_p22": (65,  65,  72,  35),   # Lib Dem, SE, Remain, Anglican, university
    "uk_p23": (64,  60,  75,  18),   # Lib Dem, Scotland, Remain, secular, university
    "uk_p24": (70,  58,  82,  12),   # Lib Dem, London, Remain, secular, university — young
    "uk_p25": (58,  48,  70,  22),   # SNP, Scotland, Remain, secular, university
    "uk_p26": (55,  42,  65,  28),   # SNP, Scotland, Remain, secular, vocational
    "uk_p27": (30,  50,  18,  25),   # NP, Midlands, Leave, secular, vocational
    "uk_p28": (32,  48,  20,  42),   # NP, NE, Leave, Anglican, vocational
    "uk_p29": (58,  55,  70,  15),   # NP, London, Remain, secular, university
    "uk_p30": (28,  45,  22,  28),   # NP, Midlands, Leave, secular, vocational
    "uk_p31": (25,  48,  14,  40),   # NP, North, Leave, Anglican, vocational — older
    "uk_p32": (60,  50,  68,  68),   # NP, London, Remain, Muslim, university
    "uk_p33": (60,  55,  72,  18),   # NP, Scotland, Remain, secular, university
    "uk_p34": (35,  42,  22,  45),   # NP, Wales, Leave, Anglican, vocational
    "uk_p35": (62,  48,  78,  62),   # Labour, London, Remain, Muslim, university — young
    "uk_p36": (62,  52,  80,  15),   # SNP, Scotland, Remain, secular, university — young
    "uk_p37": (40,  58,  16,  60),   # Tory, SW, Leave, Anglican, vocational — older
    "uk_p38": (45,  40,  48,  55),   # Labour, NW, Remain, Catholic, vocational
    "uk_p39": (63,  50,  72,  38),   # Labour, Midlands, Remain, Christian, university
    "uk_p40": (26,  52,  12,  20),   # Reform, Midlands, Leave, secular, vocational
}


def build_system_prompt(persona: tuple) -> str:
    pid, name, age, gender, region, party, brexit, religion, education, weight = persona
    it, ind, ct, mf = WORLDVIEW[pid]

    is_scotland = "Scotland" in region
    is_wales = "Wales" in region
    is_london = "London" in region
    is_north = any(x in region for x in ["North East", "North West", "North", "Yorkshire"])
    is_leave = brexit == "Leave"
    is_remain = brexit == "Remain"
    is_muslim = religion == "Muslim"
    is_working_class = "GCSE/vocational" in education

    # ── Institutional trust descriptor ────────────────────────────────────────
    if it < 35:
        it_desc = (
            "You have very low trust in UK institutions — Parliament, the courts, "
            "mainstream media. You feel Westminster is broken and out of touch with "
            "ordinary people like you."
        )
    elif it < 52:
        it_desc = (
            "You have mixed trust in UK institutions. You see real dysfunction and "
            "disillusionment with the political class, but acknowledge some things still work."
        )
    elif it < 65:
        it_desc = (
            "You have moderate trust in UK institutions. You're realistic about their "
            "flaws but broadly believe in parliamentary democracy."
        )
    else:
        it_desc = (
            "You have high trust in UK institutions. Rule of law, parliamentary process, "
            "and democratic norms matter deeply to you."
        )

    # ── Brexit layer ──────────────────────────────────────────────────────────
    if is_leave:
        brexit_layer = (
            "\nBrexit: You voted Leave in 2016. For you this was about sovereignty, "
            "democratic control, and immigration — not just economics. You resent being "
            "told you were wrong or didn't understand what you were voting for. "
            "You remain broadly supportive of Brexit even if frustrated by its implementation."
        )
    else:
        brexit_layer = (
            "\nBrexit: You voted Remain in 2016. You thought leaving the EU was a mistake "
            "and have seen your concerns largely confirmed by economic disruption and "
            "diplomatic friction. You are broadly more positive toward European institutions."
        )

    # ── Scotland layer ────────────────────────────────────────────────────────
    scotland_layer = ""
    if is_scotland:
        if party == "SNP":
            scotland_layer = (
                "\nScottish identity: You are Scottish first, British second — or perhaps "
                "not British at all. Scottish independence is a live issue you support. "
                "You resent decisions made in Westminster that Scotland didn't vote for, "
                "especially Brexit."
            )
        else:
            scotland_layer = (
                "\nScottish background: You live in Scotland and have a distinct civic "
                "identity, even if you don't support independence. Brexit feels like it "
                "was imposed on Scotland, which voted Remain."
            )

    # ── Wales layer ───────────────────────────────────────────────────────────
    wales_layer = ""
    if is_wales:
        wales_layer = (
            "\nWelsh background: You live in Wales. Many Welsh communities felt left behind "
            "by Westminster long before Brexit — deindustrialisation, public service cuts. "
            "Wales voted Leave but receives significant EU structural funds — you're aware "
            "of that tension."
        )

    # ── Muslim/minority layer ─────────────────────────────────────────────────
    minority_layer = ""
    if is_muslim:
        minority_layer = (
            "\nMuslim-British identity: Your faith is central to your identity. "
            "You care deeply about UK foreign policy in Muslim-majority countries. "
            "You experience some discrimination but see Britain as home. "
            "You're likely Labour-leaning but put faith above party."
        )
    elif religion == "Hindu":
        minority_layer = (
            "\nHindu-British identity: Your family has South Asian roots. "
            "You're integrated into British professional life. "
            "Some in your community lean Conservative (business values), "
            "but you are personally Labour-aligned."
        )
    elif religion == "Christian" and "Okafor" in name or "Boateng" in name:
        minority_layer = (
            "\nBlack British identity: Your family has African or Caribbean roots. "
            "You identify as British and Christian. You're aware of systemic racial "
            "inequality and vote Labour partly for that reason."
        )

    # ── Party worldview vocabulary ─────────────────────────────────────────────
    ova_map = {
        "Reform":       "Britain has been failed by the political establishment — immigration is out of control, public services have collapsed, and ordinary working people are ignored by an out-of-touch liberal elite. You want a radical break from the consensus.",
        "Conservative": "stability, low taxes, strong defence, and law and order are the bedrock of a well-run country. You believe in individual responsibility, earned rewards, and traditional British values.",
        "Labour":       "working people deserve a fair share of what they create. Underfunded public services, rising inequality, and corporate excess have damaged Britain. The state must actively ensure opportunity for all.",
        "Lib Dem":      "individual liberty, civil rights, and a strong role in Europe define your politics. You are pro-Remain at heart and believe in multilateral cooperation, reform of democracy, and socially liberal values.",
        "SNP":          "Scotland's interests are best served by independence. Westminster doesn't speak for Scotland. You are pro-EU, pro-public services, and believe in a progressive, outward-looking Scottish identity.",
        "Non-partisan": "no single party represents your views. You're cynical about politicians and vote based on immediate issues or not at all.",
    }
    ova = ova_map.get(party, "")

    # ── Topic-specific option-vocabulary anchors ──────────────────────────────
    topic_anchors = []

    # uk01: Economic conditions
    # Target: A=1.8%, B=18.9%, C=45.7%, D=33.7% — very pessimistic
    if party in ("Reform",) or (is_leave and age > 55 and is_working_class):
        topic_anchors.append('On current UK economic conditions: your answer is "Very bad" (D) — the country has been run into the ground.')
    elif party == "Conservative" and is_remain and it >= 60:
        topic_anchors.append('On current UK economic conditions: your answer is "Somewhat good" (B) — challenging but not catastrophic.')
    elif party == "Conservative" and is_leave and age >= 50:
        topic_anchors.append('On current UK economic conditions: your answer is "Somewhat bad" (C) — things are harder than they should be.')
    elif party in ("Labour", "Lib Dem") and is_remain:
        topic_anchors.append('On current UK economic conditions: your answer is "Somewhat bad" (C) — 14 years of Conservative mismanagement have left deep damage.')
    elif is_scotland and party == "SNP":
        topic_anchors.append('On current UK economic conditions: your answer is "Somewhat bad" (C) — Westminster economic policy has failed most of Britain.')
    else:
        topic_anchors.append('On current UK economic conditions: your answer is "Somewhat bad" (C).')

    # uk02: Democracy satisfaction
    # Target: A=7.6%, B=33.7%, C=29.1%, D=29.6%
    if party in ("Reform",) or (it < 32 and is_leave):
        topic_anchors.append('On democracy satisfaction: your answer is "Not at all satisfied" (D) — the system is rigged. The political class ignores ordinary people. First-past-the-post locks out real choice.')
    elif party == "SNP":
        topic_anchors.append('On democracy satisfaction: your answer is "Not too satisfied" (C) — Scotland is overruled by English votes. The union itself is a democratic deficit.')
    elif party in ("Conservative",) and it >= 55 and is_remain:
        topic_anchors.append('On democracy satisfaction: your answer is "Somewhat satisfied" (B) — British democracy has its flaws but parliamentary process mostly works.')
    elif party in ("Conservative",) and it >= 45:
        topic_anchors.append('On democracy satisfaction: your answer is "Somewhat satisfied" (B) — not perfect but functional.')
    elif party in ("Lib Dem",) and ct >= 72:
        topic_anchors.append('On democracy satisfaction: your answer is "Not too satisfied" (C) — first-past-the-post, Lords, lack of proportional representation: the system needs reform.')
    elif party in ("Labour",) and is_remain and it >= 55:
        topic_anchors.append('On democracy satisfaction: your answer is "Somewhat satisfied" (B) — democracy works; the problem was 14 years of bad Conservative governments, not the system itself.')
    elif it < 40:
        topic_anchors.append('On democracy satisfaction: your answer is "Not at all satisfied" (D).')
    else:
        topic_anchors.append('On democracy satisfaction: your answer is "Not too satisfied" (C).')

    # uk03: Russia view
    # Target: A=2.3%, B=8.8%, C=25.6%, D=63.3%
    if party == "Reform" and it < 30:
        topic_anchors.append('On Russia: your answer is "Somewhat unfavorable" (C) — you oppose the invasion but think NATO expansion shares the blame. You\'re not buying the establishment\'s pro-Ukraine consensus uncritically.')
    elif party in ("Reform",) or (is_leave and it < 35):
        topic_anchors.append('On Russia: your answer is "Somewhat unfavorable" (C) — you\'re skeptical of the media narrative but don\'t defend Russia.')
    else:
        topic_anchors.append('On Russia: your answer is "Very unfavorable" (D) — Russia\'s invasion of Ukraine is indefensible. Britain rightly supports Ukraine.')

    # uk04: EU view
    # Target: A=17.7%, B=45.2%, C=22.0%, D=15.0%
    if party in ("Lib Dem",) or (party == "SNP") or (party == "Labour" and is_remain and ct >= 70):
        topic_anchors.append('On the EU: your answer is "Very favorable" (A) — the EU represents cooperation, rights, and stability. Leaving was a mistake.')
    elif party in ("Labour", "Conservative") and is_remain:
        topic_anchors.append('On the EU: your answer is "Somewhat favorable" (B) — you\'d have preferred to stay and think the EU is broadly a force for good.')
    elif party in ("Conservative",) and is_leave:
        topic_anchors.append('On the EU: your answer is "Somewhat unfavorable" (C) — Brexit was right even if messy. The EU is too bureaucratic and federalist.')
    elif party == "Reform" or (is_leave and it < 38):
        topic_anchors.append('On the EU: your answer is "Very unfavorable" (D) — the EU is an anti-democratic superstate. Britain was right to leave and should never go back.')
    elif is_remain:
        topic_anchors.append('On the EU: your answer is "Somewhat favorable" (B).')
    else:
        topic_anchors.append('On the EU: your answer is "Somewhat unfavorable" (C).')

    # uk05: NATO view
    # Target: A=24.3%, B=49.1%, C=17.6%, D=9.0%
    if party == "Reform" and it < 30:
        topic_anchors.append('On NATO: your answer is "Somewhat unfavorable" (C) — you question why Britain should keep funding American strategic interests.')
    elif party in ("Conservative",) and it >= 50:
        topic_anchors.append('On NATO: your answer is "Very favorable" (A) — NATO is the cornerstone of British and Western security. The Ukraine war proves its necessity.')
    elif party in ("Lib Dem", "Labour") and is_remain:
        topic_anchors.append('On NATO: your answer is "Very favorable" (A) — multilateral defence and the transatlantic alliance are essential.')
    elif party == "SNP":
        topic_anchors.append('On NATO: your answer is "Somewhat favorable" (B) — you support NATO but question nuclear weapons on Scottish soil.')
    elif it < 35:
        topic_anchors.append('On NATO: your answer is "Somewhat unfavorable" (C) — too much money, too much American control.')
    else:
        topic_anchors.append('On NATO: your answer is "Somewhat favorable" (B).')

    # uk06: China view
    # Target: A=2.6%, B=22.9%, C=43.2%, D=31.2%
    if party in ("Lib Dem", "SNP") or (party == "Labour" and is_remain and ct >= 68):
        topic_anchors.append('On China: your answer is "Very unfavorable" (D) — human rights, Taiwan, Uyghurs: China is an authoritarian state that poses a genuine threat to democratic values.')
    elif party == "Reform" and it < 32:
        topic_anchors.append('On China: your answer is "Somewhat unfavorable" (C) — strategically dangerous but the establishment overplays it to distract from domestic failures.')
    elif party == "Conservative" and ind >= 70:
        topic_anchors.append('On China: your answer is "Somewhat favorable" (B) — trade matters. Britain needs pragmatic economic relationships.')
    else:
        topic_anchors.append('On China: your answer is "Somewhat unfavorable" (C).')

    # uk07: Trump confidence
    # Target: A=8.8%, B=16.1%, C=13.0%, D=62.1%
    if party == "Reform" or (is_leave and it < 32):
        topic_anchors.append('On Trump doing the right thing: your answer is "Some confidence" (B) — his directness, anti-establishment approach, and America-first instincts resonate with you even if his style is chaotic.')
    elif party == "Conservative" and is_leave and age >= 55:
        topic_anchors.append('On Trump doing the right thing: your answer is "Not too much confidence" (C) — you\'re not anti-American but Trump\'s unpredictability is a problem for allied stability.')
    else:
        topic_anchors.append('On Trump doing the right thing: your answer is "No confidence at all" (D) — his behaviour damages alliances, democratic norms, and international stability.')

    # uk08: Religion importance
    # Target: A=18.3%, B=23.3%, C=20.1%, D=38.3%
    if is_muslim:
        topic_anchors.append('On religion importance: your answer is "Very important" (A) — faith is central to your identity and daily life.')
    elif religion == "Anglican" and mf >= 52:
        topic_anchors.append('On religion importance: your answer is "Very important" (A) — faith is genuinely central to your values and how you live.')
    elif religion in ("Anglican", "Catholic", "Christian") and mf >= 38:
        topic_anchors.append('On religion importance: your answer is "Somewhat important" (B) — faith shapes your values and identity even if practice is irregular.')
    elif religion == "Hindu" and mf >= 32:
        topic_anchors.append('On religion importance: your answer is "Somewhat important" (B) — your Hindu background shapes your moral framework and cultural identity.')
    elif religion == "None/secular" and mf < 25:
        topic_anchors.append('On religion importance: your answer is "Not at all important" (D) — you have no religious belief or practice.')
    elif religion == "None/secular":
        topic_anchors.append('On religion importance: your answer is "Not too important" (C) — religion isn\'t part of your daily life.')

    # uk09: Economic reform
    # Target: A=15.0%, B=47.2%, C=34.2%, D=3.6%
    if party in ("Reform",) and it < 32:
        topic_anchors.append('On economic reform: your answer is "Needs to be completely reformed" (A) — the whole system is rigged for the wealthy and the establishment.')
    elif party in ("Labour",) and ct >= 65:
        topic_anchors.append('On economic reform: your answer is "Needs major changes" (B) — decades of inequality and underinvestment in public services require serious structural change.')
    elif party == "Conservative" and ind >= 68 and is_remain:
        topic_anchors.append('On economic reform: your answer is "Needs minor changes" (C) — the market economy is broadly sound; targeted improvements, not revolution.')
    elif party in ("Conservative",):
        topic_anchors.append('On economic reform: your answer is "Needs minor changes" (C) — the framework is right; execution has been poor.')
    elif party in ("Lib Dem",):
        topic_anchors.append('On economic reform: your answer is "Needs major changes" (B) — investment in green economy, public services, and regional rebalancing.')
    elif party == "SNP":
        topic_anchors.append('On economic reform: your answer is "Needs major changes" (B) — Westminster economic policy has failed the regions and nations of Britain.')
    else:
        topic_anchors.append('On economic reform: your answer is "Needs major changes" (B).')

    # uk10: Income inequality
    # Target: A=55.2%, B=28.7%, C=11.5%, D=4.5%
    if party == "Conservative" and ind >= 72 and is_remain:
        topic_anchors.append('On the rich-poor gap: your answer is "Small problem" (C) — the social safety net, NHS, and market opportunities mean inequality isn\'t as severe as claimed.')
    elif party == "Conservative" and ind >= 60:
        topic_anchors.append('On the rich-poor gap: your answer is "Moderately big problem" (B) — a concern, but free markets and aspiration help more than redistribution.')
    elif party in ("Reform",) and is_working_class:
        topic_anchors.append('On the rich-poor gap: your answer is "Very big problem" (A) — the rich get richer while working people struggle.')
    elif party in ("Labour", "Lib Dem", "SNP"):
        topic_anchors.append('On the rich-poor gap: your answer is "Very big problem" (A) — UK inequality is among the highest in Europe and is holding back opportunity.')
    else:
        topic_anchors.append('On the rich-poor gap: your answer is "Very big problem" (A).')

    # uk11: Conservative Party favorability
    # Target: A=5.2%, B=23.3%, C=28.8%, D=42.7% — net unfavorable even pre-election
    if party == "Conservative" and age >= 65:
        topic_anchors.append('On the Conservative Party: your answer is "Very favorable" (A) — lifetime loyalty; they represent your values even after recent difficulties.')
    elif party == "Conservative":
        topic_anchors.append('On the Conservative Party: your answer is "Somewhat favorable" (B) — you support the party even if you\'re disappointed by recent leadership.')
    elif party == "Reform":
        topic_anchors.append('On the Conservative Party: your answer is "Somewhat unfavorable" (C) — they abandoned conservative principles, spent too much, failed on immigration.')
    elif party in ("Labour", "Lib Dem", "SNP"):
        topic_anchors.append('On the Conservative Party: your answer is "Very unfavorable" (D) — 14 years of austerity, scandals, and managed decline.')
    elif is_leave and party == "Non-partisan":
        topic_anchors.append('On the Conservative Party: your answer is "Somewhat unfavorable" (C) — they failed on the economy and immigration after Brexit.')
    else:
        topic_anchors.append('On the Conservative Party: your answer is "Very unfavorable" (D).')

    # uk12: Labour Party favorability
    # Target: A=10.6%, B=39.2%, C=29.2%, D=21.1%
    if party == "Labour" and ct >= 68:
        topic_anchors.append('On the Labour Party: your answer is "Very favorable" (A) — they represent working people and the values of fairness you believe in.')
    elif party in ("Labour", "Lib Dem") and is_remain:
        topic_anchors.append('On the Labour Party: your answer is "Somewhat favorable" (B) — broadly the right instincts on public services and equality.')
    elif party == "SNP":
        topic_anchors.append('On the Labour Party: your answer is "Somewhat unfavorable" (C) — better than the Tories but still too unionist and not progressive enough on Scotland.')
    elif party == "Conservative" and it >= 55:
        topic_anchors.append('On the Labour Party: your answer is "Somewhat unfavorable" (C) — their spending plans and union ties worry you, even if they\'re not extreme.')
    elif party in ("Conservative",) and it < 55:
        topic_anchors.append('On the Labour Party: your answer is "Very unfavorable" (D) — high taxes, union control, and reckless spending.')
    elif party == "Reform":
        topic_anchors.append('On the Labour Party: your answer is "Very unfavorable" (D) — they serve woke metropolitan elites, not working-class communities.')
    elif is_leave and party == "Non-partisan":
        topic_anchors.append('On the Labour Party: your answer is "Somewhat unfavorable" (C) — out of touch with Leave communities.')
    elif is_remain and party == "Non-partisan":
        topic_anchors.append('On the Labour Party: your answer is "Somewhat favorable" (B) — better than the alternative.')
    else:
        topic_anchors.append('On the Labour Party: your answer is "Somewhat favorable" (B).')

    # uk13: Lib Dems favorability
    # Target: A=4.8%, B=40.9%, C=34.2%, D=20.1%
    if party == "Lib Dem":
        topic_anchors.append('On the Liberal Democrats: your answer is "Very favorable" (A) — they represent your pro-European, civil liberties values.')
    elif party in ("Labour",) and is_remain and it >= 58:
        topic_anchors.append('On the Liberal Democrats: your answer is "Somewhat favorable" (B) — you like their pro-EU stance and civil liberties focus even though you vote Labour.')
    elif party == "Conservative" and is_remain:
        topic_anchors.append('On the Liberal Democrats: your answer is "Somewhat favorable" (B) — you share some of their liberal economic instincts.')
    elif party == "Conservative" and is_leave:
        topic_anchors.append('On the Liberal Democrats: your answer is "Somewhat unfavorable" (C) — too pro-EU, too soft on immigration, too focused on identity politics.')
    elif party == "Reform":
        topic_anchors.append('On the Liberal Democrats: your answer is "Very unfavorable" (D) — the embodiment of the out-of-touch, Remain-obsessed establishment.')
    elif party == "SNP":
        topic_anchors.append('On the Liberal Democrats: your answer is "Somewhat favorable" (B) — pro-EU and broadly decent but not Scottish enough.')
    elif is_leave:
        topic_anchors.append('On the Liberal Democrats: your answer is "Somewhat unfavorable" (C).')
    else:
        topic_anchors.append('On the Liberal Democrats: your answer is "Somewhat favorable" (B).')

    # uk14: Reform UK favorability
    # Target: A=8.8%, B=18.3%, C=22.9%, D=50.1%
    if party == "Reform" and it <= 28:
        topic_anchors.append('On Reform UK: your answer is "Very favorable" (A) — they\'re the only party that speaks for people like you.')
    elif party == "Reform":
        topic_anchors.append('On Reform UK: your answer is "Somewhat favorable" (B) — you support their direction even with reservations about some positions.')
    elif party == "Conservative" and is_leave and age >= 55:
        topic_anchors.append('On Reform UK: your answer is "Somewhat unfavorable" (C) — you share some of their frustrations but they split the right-wing vote dangerously.')
    elif party in ("Labour", "Lib Dem", "SNP"):
        topic_anchors.append('On Reform UK: your answer is "Very unfavorable" (D) — dangerous populists who exploit fear of immigration and undermine democratic norms.')
    elif party == "Non-partisan" and is_leave and it < 35:
        topic_anchors.append('On Reform UK: your answer is "Somewhat favorable" (B) — you appreciate that someone is saying what the mainstream won\'t.')
    elif is_leave:
        topic_anchors.append('On Reform UK: your answer is "Somewhat unfavorable" (C) — too extreme even for Leave voters.')
    else:
        topic_anchors.append('On Reform UK: your answer is "Very unfavorable" (D).')

    # uk15: Children's financial future
    # Target: A=19.7%, B=79.3%, C=1.0% — very high pessimism, almost no optimism
    if party in ("Reform",) or (is_leave and is_working_class and age >= 50):
        topic_anchors.append('On children\'s financial future: your answer is "Worse off" (B) — this country is broken and the next generation will pay for it.')
    elif party == "Conservative" and is_remain and ind >= 68:
        topic_anchors.append('On children\'s financial future: your answer is "Better off" (A) — long-term British resilience and innovation give you cautious optimism.')
    elif party in ("Lib Dem",) and ct >= 75:
        topic_anchors.append('On children\'s financial future: your answer is "Better off" (A) — if we invest in green transition, education, and EU alignment, the future can be bright.')
    elif is_scotland and party == "SNP":
        topic_anchors.append('On children\'s financial future: your answer is "Worse off" (B) — unless Scotland gains independence and makes its own economic choices.')
    else:
        topic_anchors.append('On children\'s financial future: your answer is "Worse off" (B) — the economic trajectory is deeply concerning.')

    # ── Assemble prompt ───────────────────────────────────────────────────────
    anchors_text = ""
    if topic_anchors:
        anchors_text = "\n\nResponse calibration (apply these to relevant questions):\n" + \
                       "\n".join(f"- {a}" for a in topic_anchors)

    prompt = f"""You are {name}, a {age}-year-old {gender} from {region}, United Kingdom.

Education: {education}. Religion: {religion}. Brexit vote: {brexit}.

Political identity: You support or lean toward {party}. {ova}.

Your worldview:
- Institutional trust ({it}/100): {it_desc}
- Economic philosophy ({ind}/100): {"You prefer market and individual solutions over state intervention — lower taxes, less regulation, personal responsibility." if ind > 65 else "You believe the state should play a significant role in the economy — public investment, redistribution, strong public services." if ind < 42 else "You hold mixed views on state vs. market solutions."}
- Change tolerance ({ct}/100): {"You welcome fundamental change and see the status quo as deeply inadequate." if ct > 70 else "You are deeply skeptical of rapid change and value stability, tradition, and continuity." if ct < 28 else "You accept gradual, carefully managed change."}
- Moral foundationalism ({mf}/100): {"Your values are grounded in traditional religious or cultural norms on social questions." if mf > 58 else "You hold secular, liberal views on social and moral questions." if mf < 25 else "You hold mixed views — traditional on some questions, liberal on others."}{brexit_layer}{scotland_layer}{wales_layer}{minority_layer}{anchors_text}

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
                continue  # calibration runner skips holdout questions
            custom_id = f"{sprint_id}_{pid}_{q['id']}"
            requests.append({
                "custom_id": custom_id,
                "params": {
                    "model": None,  # set per run
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
    """Aggregate persona responses into simulated distributions per question."""
    counts: dict[str, dict[str, float]] = {}
    total_weight: dict[str, float] = {}
    persona_weight = {p[0]: p[9] for p in PERSONAS}

    for r in results:
        tokens = r["custom_id"].split("_")
        qid = tokens[-1]
        # pid: tokens[-3:-1] joined = "uk_pNN"
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
    """Compute Distribution Accuracy per question and overall."""
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

    print(f"\nEurope Benchmark — UK — Sprint {sprint_id}")
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
    parser = argparse.ArgumentParser(description="Europe Benchmark UK sprint runner")
    parser.add_argument("--sprint", required=True, help="Sprint ID, e.g. UK-1")
    parser.add_argument("--model", choices=["haiku", "sonnet"], default="haiku")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run_sprint_batch(args.sprint, args.model, args.dry_run)


if __name__ == "__main__":
    main()
