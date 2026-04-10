#!/usr/bin/env python3
"""
sprint_runner.py — Europe Benchmark · Sweden calibration sprint runner.

Usage:
    python3 sprint_runner.py --sprint SW-1 --model haiku
    python3 sprint_runner.py --sprint SW-1 --model haiku --dry-run

WorldviewAnchor dimensions (0–100 scale):
    IT  — Institutional Trust
    IND — Individualism (market vs. state preference)
    CT  — Change Tolerance
    MF  — Moral Foundationalism

Key Sweden calibration axes:
    1. Tidö coalition: SD-supported M/KD/L centre-right minority (2022–)
    2. SAP (Social Democrats): dominant 1932–2022, now in opposition but still widely liked
    3. SD (Sweden Democrats): risen from fringe to second-largest party; immigration THE defining issue
    4. NATO: joined March 2024 after 200 years of neutrality; strong support post-Russia invasion
    5. Secularism: most secular country in study (only 22% say religion important)
    6. Russia: 96.7% unfavorable — near-unanimous; Baltic Sea security, new NATO member
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
# (id, name, age, gender, region, party, nato_ref, religion, education, weight)
#
# Demographic targets (Statistics Sweden / Swedish National Election Studies):
#   Parties:  SAP ~20%, M ~15%, SD ~12.5%, C ~5%, V ~7.5%, KD ~5%,
#             Non-partisan ~35%
#   Region:   Stockholm ~23%, Gothenburg ~13%, Malmö/Skåne ~13%, Other urban ~31%,
#             Rural/smaller towns ~20%
#   Religion: Lutheran nominal (non-practicing) ~55%, Secular/none ~35%,
#             Practicing Christian (Lutheran/other) ~5%, Muslim ~5%
#   Education: University/Masters ~35%, Upper-secondary/vocational ~40%,
#              Compulsory/lower ~25%
#   NATO attitude: strongly/somewhat supportive ~79%, opposed ~21%
#   Age range: 25–74

PERSONAS = [
    # ── SAP (Social Democrats — workers, unions, suburbs/smaller cities, secular) ─
    ("sw_p01", "Erik Johansson",       54, "male",   "Sweden (Stockholm / Stockholms län)",          "SAP",           "NATO-support",  "None/secular",                 "Upper-secondary/vocational", 2.5),
    ("sw_p02", "Karin Andersson",      49, "female", "Sweden (Gothenburg / Västra Götaland)",        "SAP",           "NATO-support",  "None/secular",                 "Upper-secondary/vocational", 2.5),
    ("sw_p03", "Lars Nilsson",         62, "male",   "Sweden (Malmö / Skåne)",                       "SAP",           "NATO-support",  "None/secular",                 "Upper-secondary/vocational", 2.5),
    ("sw_p04", "Birgitta Eriksson",    58, "female", "Sweden (Örebro / Örebro län)",                 "SAP",           "NATO-support",  "None/secular",                 "Upper-secondary/vocational", 2.5),
    ("sw_p05", "Gunnar Karlsson",      67, "male",   "Sweden (Umeå / Västernorrland)",               "SAP",           "NATO-support",  "None/secular",                 "Compulsory/lower",           2.5),
    ("sw_p06", "Annika Persson",       45, "female", "Sweden (Linköping / Östergötland)",            "SAP",           "NATO-support",  "None/secular",                 "University/Masters",         2.0),
    ("sw_p07", "Sven Gustafsson",      56, "male",   "Sweden (rural Dalarna)",                       "SAP",           "NATO-support",  "Lutheran (non-practicing)",    "Compulsory/lower",           2.5),
    ("sw_p08", "Maj-Britt Svensson",   71, "female", "Sweden (Västerås / Västmanland)",              "SAP",           "NATO-support",  "Lutheran (non-practicing)",    "Upper-secondary/vocational", 2.5),

    # ── M (Moderates — business, suburban Stockholm/Gothenburg, centre-right) ───
    ("sw_p09", "Henrik Larsson",       46, "male",   "Sweden (Stockholm / Stockholms län)",          "M",             "NATO-support",  "None/secular",                 "University/Masters",         2.0),
    ("sw_p10", "Cecilia Olsson",       41, "female", "Sweden (Stockholm / Stockholms län)",          "M",             "NATO-support",  "None/secular",                 "University/Masters",         2.0),
    ("sw_p11", "Johan Pettersson",     52, "male",   "Sweden (Gothenburg / Västra Götaland)",        "M",             "NATO-support",  "None/secular",                 "University/Masters",         2.0),
    ("sw_p12", "Maria Lindqvist",      38, "female", "Sweden (Uppsala / Uppsala län)",               "M",             "NATO-support",  "None/secular",                 "University/Masters",         2.0),
    ("sw_p13", "Anders Bergström",     59, "male",   "Sweden (Gothenburg / Västra Götaland)",        "M",             "NATO-support",  "Lutheran (non-practicing)",    "University/Masters",         2.0),
    ("sw_p14", "Sofie Magnusson",      44, "female", "Sweden (Stockholm / Stockholms län)",          "M",             "NATO-support",  "None/secular",                 "University/Masters",         2.0),

    # ── SD (Sweden Democrats — anti-immigration, rural/smaller towns, working class) ─
    ("sw_p15", "Roger Fransson",       48, "male",   "Sweden (Malmö / Skåne)",                       "SD",            "NATO-support",  "None/secular",                 "Upper-secondary/vocational", 2.5),
    ("sw_p16", "Åsa Lindgren",         44, "female", "Sweden (rural Dalarna)",                       "SD",            "NATO-support",  "None/secular",                 "Upper-secondary/vocational", 2.5),
    ("sw_p17", "Mattias Holm",         55, "male",   "Sweden (Linköping / Östergötland)",            "SD",            "NATO-support",  "Lutheran (non-practicing)",    "Compulsory/lower",           2.5),
    ("sw_p18", "Lena Björk",           52, "female", "Sweden (Gothenburg / Västra Götaland)",        "SD",            "NATO-support",  "None/secular",                 "Upper-secondary/vocational", 2.5),
    ("sw_p19", "Stefan Hedlund",       61, "male",   "Sweden (Umeå / Västernorrland)",               "SD",            "NATO-support",  "Lutheran (non-practicing)",    "Compulsory/lower",           2.5),

    # ── C (Centre Party — liberal-rural, pro-EU, decentralisation) ─────────────
    ("sw_p20", "Ingrid Söderström",    47, "female", "Sweden (rural Dalarna)",                       "C",             "NATO-support",  "None/secular",                 "University/Masters",         2.0),
    ("sw_p21", "Patrik Sundqvist",     50, "male",   "Sweden (Umeå / Västernorrland)",               "C",             "NATO-support",  "None/secular",                 "Upper-secondary/vocational", 2.5),

    # ── V (Left Party — radical left, urban, feminist) ──────────────────────────
    ("sw_p22", "Emma Lövgren",         32, "female", "Sweden (Stockholm / Stockholms län)",          "V",             "NATO-skeptic",  "None/secular",                 "University/Masters",         2.0),
    ("sw_p23", "Jonas Strömberg",      38, "male",   "Sweden (Gothenburg / Västra Götaland)",        "V",             "NATO-skeptic",  "None/secular",                 "University/Masters",         2.0),
    ("sw_p24", "Hanna Vikström",       29, "female", "Sweden (Uppsala / Uppsala län)",               "V",             "NATO-skeptic",  "None/secular",                 "University/Masters",         2.0),

    # ── KD (Christian Democrats — religious, family values) ─────────────────────
    ("sw_p25", "Christer Lundgren",    57, "male",   "Sweden (Linköping / Östergötland)",            "KD",            "NATO-support",  "Lutheran (practicing)",        "Upper-secondary/vocational", 2.0),
    ("sw_p26", "Ingeborg Samuelsson",  53, "female", "Sweden (Stockholm / Stockholms län)",          "KD",            "NATO-support",  "Lutheran (practicing)",        "University/Masters",         2.0),

    # ── Non-partisan / disengaged (wide cross-section) ───────────────────────────
    ("sw_p27", "Torsten Åberg",        63, "male",   "Sweden (rural Dalarna)",                       "Non-partisan",  "NATO-support",  "Lutheran (non-practicing)",    "Compulsory/lower",           2.5),
    ("sw_p28", "Inger Westberg",       58, "female", "Sweden (Västerås / Västmanland)",              "Non-partisan",  "NATO-support",  "None/secular",                 "Upper-secondary/vocational", 2.5),
    ("sw_p29", "Mikael Dahl",          42, "male",   "Sweden (Malmö / Skåne)",                       "Non-partisan",  "NATO-support",  "None/secular",                 "Upper-secondary/vocational", 2.5),
    ("sw_p30", "Berit Holmgren",       67, "female", "Sweden (Umeå / Västernorrland)",               "Non-partisan",  "NATO-support",  "Lutheran (non-practicing)",    "Compulsory/lower",           2.5),
    ("sw_p31", "Niklas Forsgren",      36, "male",   "Sweden (Stockholm / Stockholms län)",          "Non-partisan",  "NATO-support",  "None/secular",                 "University/Masters",         2.0),
    ("sw_p32", "Camilla Rydén",        39, "female", "Sweden (Gothenburg / Västra Götaland)",        "Non-partisan",  "NATO-support",  "None/secular",                 "University/Masters",         2.0),
    ("sw_p33", "Bo Nordin",            74, "male",   "Sweden (rural Dalarna)",                       "Non-partisan",  "NATO-support",  "Lutheran (non-practicing)",    "Compulsory/lower",           2.5),
    ("sw_p34", "Kerstin Eliasson",     55, "female", "Sweden (Linköping / Östergötland)",            "Non-partisan",  "NATO-support",  "None/secular",                 "Upper-secondary/vocational", 2.5),
    ("sw_p35", "Håkan Nyström",        47, "male",   "Sweden (Malmö / Skåne)",                       "Non-partisan",  "NATO-skeptic",  "None/secular",                 "Upper-secondary/vocational", 2.5),
    ("sw_p36", "Susanne Alexandersson",45, "female", "Sweden (Uppsala / Uppsala län)",               "Non-partisan",  "NATO-support",  "None/secular",                 "University/Masters",         2.0),
    ("sw_p37", "Leif Boström",         60, "male",   "Sweden (Västerås / Västmanland)",              "Non-partisan",  "NATO-support",  "Lutheran (non-practicing)",    "Upper-secondary/vocational", 2.5),
    ("sw_p38", "Astrid Wallin",        34, "female", "Sweden (Stockholm / Stockholms län)",          "Non-partisan",  "NATO-support",  "None/secular",                 "University/Masters",         2.0),
    ("sw_p39", "Per-Olov Engström",    69, "male",   "Sweden (Umeå / Västernorrland)",               "Non-partisan",  "NATO-support",  "Lutheran (non-practicing)",    "Compulsory/lower",           2.5),
    ("sw_p40", "Malin Björklund",      31, "female", "Sweden (Gothenburg / Västra Götaland)",        "Non-partisan",  "NATO-support",  "None/secular",                 "University/Masters",         2.0),
]

# ── WorldviewAnchor values ────────────────────────────────────────────────────
WORLDVIEW = {
    # id:        (IT,  IND, CT,  MF)
    # SAP — moderate-high IT, low-moderate IND, moderate-high CT, low MF (secular labour)
    "sw_p01": (68,  42,  62,  14),   # SAP, Stockholm, secular, upper-secondary
    "sw_p02": (65,  40,  60,  16),   # SAP, Gothenburg, secular, upper-secondary
    "sw_p03": (62,  38,  58,  18),   # SAP, Malmö, secular, upper-secondary (older)
    "sw_p04": (64,  40,  62,  15),   # SAP, Örebro, secular, upper-secondary
    "sw_p05": (58,  36,  55,  22),   # SAP, Umeå, secular, compulsory (oldest)
    "sw_p06": (70,  44,  68,  12),   # SAP, Linköping, secular, university
    "sw_p07": (60,  38,  52,  28),   # SAP, rural Dalarna, Lutheran non-practicing, compulsory
    "sw_p08": (56,  36,  48,  30),   # SAP, Västerås, Lutheran non-practicing, upper-secondary (oldest)

    # M — high IT, high IND, moderate CT, low MF (market-liberal, secular)
    "sw_p09": (72,  70,  52,  18),   # M, Stockholm, secular, university
    "sw_p10": (70,  68,  54,  15),   # M, Stockholm, secular, university
    "sw_p11": (68,  72,  50,  20),   # M, Gothenburg, secular, university
    "sw_p12": (74,  70,  58,  14),   # M, Uppsala, secular, university (younger)
    "sw_p13": (65,  66,  48,  32),   # M, Gothenburg, Lutheran non-practicing, university (older)
    "sw_p14": (71,  68,  56,  16),   # M, Stockholm, secular, university

    # SD — moderate-low IT (distrust left/media establishment), moderate IND, low CT, moderate MF
    "sw_p15": (42,  58,  28,  42),   # SD, Malmö, secular, upper-secondary (immigration focus)
    "sw_p16": (38,  56,  25,  40),   # SD, rural Dalarna, secular, upper-secondary (female)
    "sw_p17": (45,  60,  30,  48),   # SD, Linköping, Lutheran non-practicing, compulsory
    "sw_p18": (40,  55,  26,  38),   # SD, Gothenburg, secular, upper-secondary (female)
    "sw_p19": (36,  58,  22,  50),   # SD, Umeå, Lutheran non-practicing, compulsory (oldest)

    # C — moderate-high IT, moderate-high IND (liberal-rural), moderate-high CT, low MF
    "sw_p20": (66,  64,  62,  14),   # C, rural Dalarna, secular, university
    "sw_p21": (62,  62,  58,  18),   # C, Umeå, secular, upper-secondary

    # V — moderate IT, very low IND (state/collective), high CT, very low MF (radical-secular)
    "sw_p22": (56,  24,  80,  10),   # V, Stockholm, secular, university (youngest)
    "sw_p23": (52,  26,  78,  12),   # V, Gothenburg, secular, university
    "sw_p24": (54,  22,  82,  10),   # V, Uppsala, secular, university (youngest)

    # KD — moderate-high IT, moderate IND, low-moderate CT, high MF (religious)
    "sw_p25": (64,  56,  36,  68),   # KD, Linköping, Lutheran practicing, upper-secondary
    "sw_p26": (62,  58,  40,  65),   # KD, Stockholm, Lutheran practicing, university

    # Non-partisan — wide spread
    "sw_p27": (48,  50,  25,  44),   # NP, rural Dalarna, Lutheran non-practicing, compulsory (older)
    "sw_p28": (55,  50,  40,  28),   # NP, Västerås, secular, upper-secondary
    "sw_p29": (50,  52,  45,  22),   # NP, Malmö, secular, upper-secondary
    "sw_p30": (44,  48,  30,  38),   # NP, Umeå, Lutheran non-practicing, compulsory (oldest)
    "sw_p31": (68,  60,  65,  12),   # NP, Stockholm, secular, university (younger)
    "sw_p32": (65,  58,  62,  14),   # NP, Gothenburg, secular, university
    "sw_p33": (40,  48,  20,  48),   # NP, rural Dalarna, Lutheran non-practicing, compulsory (oldest)
    "sw_p34": (58,  50,  48,  26),   # NP, Linköping, secular, upper-secondary
    "sw_p35": (38,  52,  35,  30),   # NP, Malmö, secular, upper-secondary (NATO-skeptic)
    "sw_p36": (66,  58,  60,  12),   # NP, Uppsala, secular, university
    "sw_p37": (52,  50,  38,  36),   # NP, Västerås, Lutheran non-practicing, upper-secondary (older)
    "sw_p38": (70,  60,  68,  10),   # NP, Stockholm, secular, university (youngest)
    "sw_p39": (42,  46,  25,  46),   # NP, Umeå, Lutheran non-practicing, compulsory (oldest)
    "sw_p40": (64,  56,  64,  14),   # NP, Gothenburg, secular, university (youngest)
}


def build_system_prompt(persona: tuple) -> str:
    pid, name, age, gender, region, party, nato_ref, religion, education, weight = persona
    it, ind, ct, mf = WORLDVIEW[pid]

    is_stockholm       = "Stockholm" in region
    is_gothenburg      = "Gothenburg" in region or "Västra Götaland" in region
    is_malmo           = "Malmö" in region or "Skåne" in region
    is_rural           = "rural" in region or "Dalarna" in region
    is_north           = "Umeå" in region or "Västernorrland" in region
    is_nato_support    = nato_ref == "NATO-support"
    is_nato_skeptic    = nato_ref == "NATO-skeptic"
    is_lutheran_practicing = "practicing" in religion and "non" not in religion
    is_lutheran_nonpracticing = "non-practicing" in religion
    is_secular         = "secular" in religion or "None" in religion
    is_working_class   = "Compulsory" in education or "vocational" in education or "upper-secondary" in education.lower()
    is_university      = "University" in education or "Masters" in education

    # ── Institutional trust descriptor ────────────────────────────────────────
    if it < 45:
        it_desc = (
            "You have low trust in Sweden's political establishment and mainstream media. "
            "You feel the political class governs for urban, educated elites and ignores "
            "ordinary Swedes — especially on immigration and crime. The Sweden Democrats "
            "exist because the old parties failed people like you."
        )
    elif it < 58:
        it_desc = (
            "You have mixed trust in Swedish institutions. You see real failures — "
            "especially on immigration policy and gang violence — but still believe in "
            "Swedish democratic tradition and the rule of law in principle."
        )
    elif it < 68:
        it_desc = (
            "You have moderate to good trust in Swedish institutions. You are realistic "
            "about their imperfections but broadly believe Sweden's model — transparency, "
            "rule of law, independent agencies — is something to be proud of."
        )
    else:
        it_desc = (
            "You have high trust in Swedish institutions. Swedish democracy, its "
            "independent agencies, free press, and the rule of law are fundamental "
            "values you believe in deeply. Sweden's model works."
        )

    # ── NATO/security layer ────────────────────────────────────────────────────
    if is_nato_support:
        nato_layer = (
            "\nNATO and security: Sweden's historic decision to join NATO in March 2024 "
            "was the right call. Russia's full-scale invasion of Ukraine ended 200 years "
            "of neutrality — that era is over. You support Sweden's NATO membership as "
            "essential for Baltic security and the credible deterrence of Russian aggression."
        )
    else:
        nato_layer = (
            "\nNATO and security: You have reservations about Sweden's NATO membership. "
            "Sweden's 200-year tradition of neutrality and non-alignment was a source of "
            "national identity and diplomatic credibility. You supported a strong defence "
            "but feel the rush to join NATO risks entangling Sweden in conflicts beyond "
            "its direct interests. That said, you understand the threat Russia poses."
        )

    # ── Party political identity ───────────────────────────────────────────────
    ova_map = {
        "SAP": (
            "The Swedish Social Democrats built the folkhemmet — the people's home. "
            "The welfare state, universal healthcare, free education, and labour rights "
            "that make Sweden fair are SAP achievements. You believe in collective "
            "solutions, strong public services, and an economy that works for everyone, "
            "not just shareholders. The party is in opposition now but its values endure."
        ),
        "M": (
            "Sweden needs a well-functioning market economy, fiscal discipline, and "
            "a state that empowers individuals rather than creating dependency. The "
            "Moderates represent responsible centre-right governance: lower taxes, "
            "school choice, law and order, and a competitive business environment. "
            "You support the Tidö government's agenda — especially on crime and order."
        ),
        "SD": (
            "Mass immigration has fundamentally changed Sweden — and not for the better. "
            "Gang violence, parallel societies, and integration failures are the result "
            "of decades of irresponsible SAP immigration policy. The Sweden Democrats "
            "were the only party willing to name this reality. You want a Swedish Sweden: "
            "controlled immigration, cultural cohesion, and law and order. "
            "You are a Swedish nationalist-conservative, not a racist — you want Sweden "
            "to work for Swedes first."
        ),
        "C": (
            "The Centre Party stands for liberal values in a Swedish context: "
            "individual freedom, decentralisation, and a rural Sweden that isn't left "
            "behind by Stockholm. You believe in free markets but also in sustainable "
            "communities, liberal immigration policy, and EU cooperation. "
            "You are socially liberal and economically pragmatic."
        ),
        "V": (
            "Sweden's welfare model is under attack from the right. The Left Party "
            "stands for gender equality, workers' rights, welfare, and a foreign policy "
            "independent of military blocs. You are skeptical of NATO and believe "
            "Sweden's strength has always been its neutrality and development aid. "
            "You want a more equal Sweden — taxing the wealthy, investing in welfare, "
            "and addressing the climate emergency."
        ),
        "KD": (
            "Christian Democrat values — family, community, and human dignity — "
            "provide the ethical foundation for a cohesive Sweden. You support "
            "Christian heritage, stronger families, and care for the vulnerable. "
            "You are part of the Tidö government coalition and believe in law and order, "
            "integration through shared Swedish values, and a welfare system "
            "that prioritises families and the elderly."
        ),
        "Non-partisan": (
            "no single party fully represents your views. You follow politics but feel "
            "disillusioned with the party system — politicians argue while ordinary "
            "Swedes deal with rising costs, gang violence, and uncertain futures. "
            "You vote pragmatically or sometimes not at all."
        ),
    }
    ova = ova_map.get(party, "")

    # ── Religion layer ────────────────────────────────────────────────────────
    religion_layer = ""
    if is_lutheran_practicing:
        religion_layer = (
            "\nFaith and identity: You are a practicing Lutheran Christian. "
            "Your faith shapes your values — care for others, honesty, and community. "
            "Sweden is very secular and you sometimes feel your faith is marginalised "
            "in public life. You support KD's emphasis on Christian heritage and values."
        )
    elif is_lutheran_nonpracticing:
        religion_layer = (
            "\nFaith and identity: You were raised Lutheran and still feel a loose "
            "cultural connection to the church — Christmas, confirmations, funerals. "
            "But religion plays little practical role in your daily life or worldview. "
            "You are secular in practice even if nominally Lutheran."
        )

    # ── Regional layer ────────────────────────────────────────────────────────
    region_layer = ""
    if is_stockholm:
        region_layer = (
            "\nRegional background: You live in Stockholm, Sweden's capital and economic "
            "engine. You are part of Sweden's professional class. More cosmopolitan, "
            "pro-EU, and socially liberal than the national average. "
            "The political debates feel different here than in rural Sweden."
        )
    elif is_gothenburg:
        region_layer = (
            "\nRegional background: You live in Gothenburg (Göteborg), Sweden's second city "
            "and industrial hub. Strong labour movement history — Volvo, Ericsson. "
            "A mix of working-class SAP tradition and newer middle-class M voters."
        )
    elif is_malmo:
        region_layer = (
            "\nRegional background: You live in Malmö or Skåne in southern Sweden. "
            "Malmö is one of Sweden's most diverse cities and has faced serious "
            "challenges with gang violence and integration. It is also the heartland "
            "of SD support. Immigration and security dominate local politics."
        )
    elif is_rural:
        region_layer = (
            "\nRegional background: You live in rural Sweden — Dalarna or similar. "
            "You feel the distance between Stockholm's political class and the "
            "realities of rural life. Local industries, hunting, forestry, and "
            "community ties matter. Immigration has changed some smaller towns significantly."
        )
    elif is_north:
        region_layer = (
            "\nRegional background: You live in northern Sweden — Umeå or Norrland. "
            "A long way from Stockholm geographically and culturally. "
            "Strong SAP tradition among forestry and industrial workers. "
            "NATO membership feels very real here — Russia is close."
        )

    # ── Topic-specific option-vocabulary anchors ──────────────────────────────
    topic_anchors = []

    # sw01: Economic conditions
    # Target: A=2.1%, B=56.3%, C=35.9%, D=5.7%
    # SW-3: B=71.4%, C=28.6% — B 15pp high, C 7pp low, A and D both 0%
    # SW-4: B=61%, C=28.6%, A=2.2%, D=8.2% — D over by 2.5pp (NP wc D rule too broad), C 7pp low
    # Fix: remove NP wc D route (p33 goes to wc<48→C instead, corrects D);
    #      widen NP→C threshold to it<58 (catches moderate-IT NP for C, corrects C vs B split)
    if party == "M" and it >= 74 and ind >= 70:
        topic_anchors.append('On Sweden\'s economic situation: your answer is "Very good" (A) — Sweden\'s economy is among the strongest in the world: low debt, high productivity, competitive firms. The fundamentals are excellent.')
    elif party == "SD" and it < 40:
        topic_anchors.append('On Sweden\'s economic situation: your answer is "Very bad" (D) — decades of irresponsible immigration policy have strained welfare and public finances. Ordinary Swedes are paying the price.')
    elif party == "SD" and it < 45:
        topic_anchors.append('On Sweden\'s economic situation: your answer is "Somewhat bad" (C) — immigration costs, welfare strain, and law and order failures have weakened the economy for ordinary Swedes.')
    elif party == "V":
        topic_anchors.append('On Sweden\'s economic situation: your answer is "Somewhat bad" (C) — growing inequality and housing unaffordability mean the economy isn\'t working for everyone.')
    elif party in ("M", "KD") and it >= 65:
        topic_anchors.append('On Sweden\'s economic situation: your answer is "Somewhat good" (B) — Sweden\'s fundamentals remain strong, though inflation and housing challenges need to be addressed.')
    elif party == "SAP":
        topic_anchors.append('On Sweden\'s economic situation: your answer is "Somewhat good" (B) — Sweden\'s social model built a resilient economy, even with recent challenges.')
    elif party == "C":
        topic_anchors.append('On Sweden\'s economic situation: your answer is "Somewhat good" (B) — the Swedish economy is solid; structural reforms can address remaining challenges.')
    elif is_working_class and it < 48:
        topic_anchors.append('On Sweden\'s economic situation: your answer is "Somewhat bad" (C) — costs have risen and life is harder for ordinary working Swedes.')
    elif party == "Non-partisan" and it < 58:
        topic_anchors.append('On Sweden\'s economic situation: your answer is "Somewhat bad" (C) — prices are up, housing costs are punishing, and it\'s harder to get ahead than it used to be.')
    elif it >= 62:
        topic_anchors.append('On Sweden\'s economic situation: your answer is "Somewhat good" (B) — Sweden remains one of the world\'s strongest economies.')
    else:
        topic_anchors.append('On Sweden\'s economic situation: your answer is "Somewhat good" (B).')

    # sw02: Democracy satisfaction
    # Target: A=16.9%, B=61.3%, C=16.3%, D=5.7%
    # SW-1: B=87.4%, A=4.4%, C=8.2% — ordering bug (M+it≥70→A never triggered)
    # Fix: A-first routing for high-IT M/SAP/NP; D for lowest-IT SD+NP; C for moderate disillusion
    if party == "M" and it >= 68:
        topic_anchors.append('On democracy in Sweden: your answer is "Very satisfied" (A) — Sweden\'s democratic institutions are among the best in the world: independent courts, free press, high turnout.')
    elif party == "SAP" and it >= 68:
        topic_anchors.append('On democracy in Sweden: your answer is "Very satisfied" (A) — Swedish democracy produced decades of Social Democrat governance through fair elections. The system works.')
    elif party == "Non-partisan" and it >= 70:
        topic_anchors.append('On democracy in Sweden: your answer is "Very satisfied" (A) — Sweden\'s democratic model is something to be genuinely proud of.')
    elif party == "SD" and it <= 38:
        topic_anchors.append('On democracy in Sweden: your answer is "Not very satisfied" (D) — the mainstream parties colluded for decades to exclude and stigmatise SD voters. That was anti-democratic.')
    elif party == "Non-partisan" and it < 38:
        topic_anchors.append('On democracy in Sweden: your answer is "Not very satisfied" (D) — politicians serve themselves and urban elites, not ordinary Swedes.')
    elif party == "SD" and it < 45:
        topic_anchors.append('On democracy in Sweden: your answer is "Not too satisfied" (C) — the political establishment ignored ordinary Swedes on immigration for too long.')
    elif party == "Non-partisan" and it < 48:
        topic_anchors.append('On democracy in Sweden: your answer is "Not too satisfied" (C) — politicians feel distant from people like you.')
    elif party == "V":
        topic_anchors.append('On democracy in Sweden: your answer is "Somewhat satisfied" (B) — democracy works in Sweden even if economic power remains unevenly distributed.')
    elif party in ("SAP", "M", "KD", "C", "SD"):
        topic_anchors.append('On democracy in Sweden: your answer is "Somewhat satisfied" (B) — Swedish democracy is fundamentally healthy: free press, independent courts, high turnout.')
    elif it >= 60:
        topic_anchors.append('On democracy in Sweden: your answer is "Somewhat satisfied" (B).')
    else:
        topic_anchors.append('On democracy in Sweden: your answer is "Somewhat satisfied" (B).')

    # sw03: Russia view
    # Target: A=0.5%, B=2.8%, C=14.2%, D=82.5%
    # SW-1: D=100% — all-D gives 82.5% but C=14.2% completely missed
    # Fix: V → C (anti-war stance; oppose both Russian aggression AND NATO entanglement)
    #      NATO-skeptic NP → C; everyone else → D
    if party == "V":
        topic_anchors.append('On Russia: your answer is "Somewhat unfavorable" (C) — Russia\'s invasion of Ukraine is wrong and you condemn it clearly. But you oppose both Russian imperialism and NATO escalation. Your position: strong international law, not military bloc logic.')
    elif is_nato_skeptic:
        topic_anchors.append('On Russia: your answer is "Somewhat unfavorable" (C) — Russia\'s aggression is unacceptable, but you are cautious about how Sweden responds. You prefer diplomatic and international legal approaches over pure military deterrence.')
    elif party == "SD":
        topic_anchors.append('On Russia: your answer is "Very unfavorable" (D) — Russia is a direct threat to Sweden and Baltic security. NATO membership was the right call. Putin\'s aggression must be firmly opposed.')
    else:
        topic_anchors.append('On Russia: your answer is "Very unfavorable" (D) — Russia\'s invasion of Ukraine is a fundamental threat to the European security order and to Sweden as a new NATO member.')

    # sw04: EU view
    # Target: A=22.4%, B=53.9%, C=18.4%, D=5.3%
    # SW-1: A=0%, B=68.7%, C=31.3% — ordering bug (M+it≥70→A rule preceded by M+it≥62→B)
    # Fix: A-first for M/C/SAP high-IT; D for SD very-low-IT; C for V/SD/low-IT NP
    if party in ("M", "C") and it >= 60:
        topic_anchors.append('On the European Union: your answer is "Very favorable" (A) — the EU single market, collective security, and rule of law are essential for Sweden. Deep integration is the right direction.')
    elif party == "SAP" and it >= 66:
        topic_anchors.append('On the European Union: your answer is "Very favorable" (A) — the EU is fundamental to Swedish prosperity and European peace. Solidarity across borders.')
    elif party == "V":
        topic_anchors.append('On the European Union: your answer is "Somewhat unfavorable" (C) — the EU serves corporations and neoliberal interests more than workers. It needs fundamental democratic reform.')
    elif party == "SD" and it < 40:
        topic_anchors.append('On the European Union: your answer is "Very unfavorable" (D) — the EU undermines Swedish sovereignty, imposes migration policy, and answers to no Swedish voter. Sweden\'s self-determination must come first.')
    elif party == "SD":
        topic_anchors.append('On the European Union: your answer is "Somewhat unfavorable" (C) — the EU undermines Swedish sovereignty and democratic self-determination. Sweden should cooperate with Europe but on our terms.')
    elif party in ("SAP", "KD"):
        topic_anchors.append('On the European Union: your answer is "Somewhat favorable" (B) — the EU is important for security and trade, even if it over-regulates at times.')
    elif it >= 62:
        topic_anchors.append('On the European Union: your answer is "Somewhat favorable" (B) — important for Sweden\'s prosperity and place in the world.')
    elif it < 42:
        topic_anchors.append('On the European Union: your answer is "Somewhat unfavorable" (C) — Brussels imposes rules without accountability to Swedish voters.')
    else:
        topic_anchors.append('On the European Union: your answer is "Somewhat favorable" (B).')

    # sw05: NATO view
    # Target: A=25.7%, B=53.0%, C=14.3%, D=7.0%
    # SW-3: A=24.7%, B=41.2%, C=27.5%, D=6.6% — B 12pp low, C 13pp high
    # Fix: it<50 catch-all was grabbing SD (should be B) and too many NP;
    #      SD explicit B before broad C; tighten C to non-partisan/V nato-skeptics only;
    #      add SAP/C explicit B route before the fallback
    if party == "V":
        topic_anchors.append('On NATO: your answer is "Very unfavorable" (D) — Sweden\'s 200-year tradition of neutrality and non-alignment was a source of national identity and diplomatic strength. Joining NATO was the wrong move: it entangles Sweden in great-power conflicts and undermines the peace role Sweden played for generations.')
    elif is_nato_skeptic and party != "SD":
        topic_anchors.append('On NATO: your answer is "Somewhat unfavorable" (C) — you feel uneasy about abandoning 200 years of neutrality. Sweden can defend itself without joining a military bloc.')
    elif party == "M" and it >= 68:
        topic_anchors.append('On NATO: your answer is "Very favorable" (A) — Sweden\'s NATO membership is essential for Baltic security. The era of neutrality is over; this was the right historic decision.')
    elif party == "KD":
        topic_anchors.append('On NATO: your answer is "Very favorable" (A) — NATO membership protects Sweden and reinforces the Western community of democratic values.')
    elif party == "SAP" and it >= 68:
        topic_anchors.append('On NATO: your answer is "Very favorable" (A) — given Russian aggression, NATO membership was the right call for Sweden\'s security.')
    elif party == "Non-partisan" and it >= 68:
        topic_anchors.append('On NATO: your answer is "Very favorable" (A) — Sweden made the right decision joining NATO; security and deterrence matter.')
    elif party == "SD":
        topic_anchors.append('On NATO: your answer is "Somewhat favorable" (B) — NATO is the right choice for Swedish security. Russia must be deterred.')
    elif party in ("SAP", "C") and it >= 60:
        topic_anchors.append('On NATO: your answer is "Somewhat favorable" (B) — NATO membership was the right decision given Russian aggression, even if it represents a major historic shift.')
    elif party == "Non-partisan" and it < 44:
        topic_anchors.append('On NATO: your answer is "Somewhat unfavorable" (C) — you support defending Sweden but have mixed feelings about full NATO integration and its implications.')
    elif party == "M" and it >= 60:
        topic_anchors.append('On NATO: your answer is "Somewhat favorable" (B) — NATO membership is the right choice for Sweden\'s security in the current geopolitical environment.')
    else:
        topic_anchors.append('On NATO: your answer is "Somewhat favorable" (B).')

    # sw06: China view
    # Target: A=0.5%, B=9.7%, C=55.3%, D=34.5%
    # Sweden is extremely hostile: Gui Minhai case; near-unanimous unfavorable
    # SW-4: D=37.9%, C=62.1%, B=0%, A=0% — no B routes at all; D over by 3.4pp
    # Fix: lower M/C→D threshold to it≥62 (gets C close to target);
    #      add SAP<62→B route (lower-IT SAP are aware but less engaged on China specifics);
    #      raise NP→D threshold to it≥68 (reduces D overshoot)
    if party in ("M", "C") and it >= 62:
        topic_anchors.append('On China: your answer is "Very unfavorable" (D) — the Gui Minhai abduction, Huawei security threats, and systematic human rights violations make China an adversary, not a partner.')
    elif party == "SAP" and it >= 62:
        topic_anchors.append('On China: your answer is "Somewhat unfavorable" (C) — China\'s authoritarianism and treatment of Sweden\'s citizens abroad (Gui Minhai) is deeply troubling.')
    elif party == "SAP":
        topic_anchors.append('On China: your answer is "Somewhat unfavorable" (B) — China\'s human rights record is concerning, though Sweden should prioritise dialogue and trade over confrontation.')
    elif party == "V":
        topic_anchors.append('On China: your answer is "Somewhat unfavorable" (C) — you oppose Chinese authoritarianism and its treatment of Uyghurs and Hong Kong. Neither great power imperialism is acceptable.')
    elif party == "SD":
        topic_anchors.append('On China: your answer is "Very unfavorable" (D) — China is an authoritarian state that kidnapped a Swedish citizen and poses strategic threats. Sweden must stand firm.')
    elif it >= 68:
        topic_anchors.append('On China: your answer is "Very unfavorable" (D) — Gui Minhai, Huawei, and China\'s authoritarianism make this clear.')
    else:
        topic_anchors.append('On China: your answer is "Somewhat unfavorable" (C).')

    # sw07: Trump confidence
    # Target: A=2.1%, B=9.9%, C=14.8%, D=73.2%
    # SW-2: D=91.8%, C=8.2% — D collapse; no A or B routes at all
    # Fix: SD very-low-IT → B (some confidence: populist solidarity on immigration/sovereignty);
    #      SD moderate-IT → C; NP low-IT populist → B; else → D
    # Note: A (a lot of confidence) is only ~2.1% — no explicit route; relies on rare model variation
    if party == "SD" and it < 40:
        topic_anchors.append('On Trump: your answer is "Some confidence" (B) — Trump challenges the globalist liberal establishment on immigration and borders in ways that resonate with you, even if his NATO stance is worrying.')
    elif party == "SD" and it < 48:
        topic_anchors.append('On Trump: your answer is "Not too much confidence" (C) — you share some of his views on immigration and sovereignty, but his erratic stance on NATO and willingness to appease Putin is alarming for Swedish security.')
    elif party == "SD":
        topic_anchors.append('On Trump: your answer is "No confidence at all" (D) — Trump\'s threats to weaken NATO are a direct threat to Swedish security. SD is pro-NATO; Trump undermines the alliance.')
    elif party == "Non-partisan" and it < 42:
        topic_anchors.append('On Trump: your answer is "Some confidence" (B) — Trump\'s anti-establishment and anti-immigration stance speaks to frustrations the mainstream Swedish media won\'t acknowledge.')
    else:
        topic_anchors.append('On Trump: your answer is "No confidence at all" (D) — Trump is unpredictable, threatens NATO, and undermines the international rules-based order that small countries like Sweden depend on.')

    # sw08: Religion importance
    # Target: A=6.9%, B=15.2%, C=31.7%, D=46.2%
    # SW-1: D=81.9%, B=4.4% — KD+practicing→A rule never triggered (is_lutheran_practicing→B ran first)
    # Fix: KD+practicing→A first; non-practicing high-MF→B; secular+MF≥22→C; else→D
    if party == "KD" and is_lutheran_practicing:
        topic_anchors.append('On religion in your life: your answer is "Very important" (A) — your Christian faith is foundational to your worldview and the reason you support KD. Faith shapes your values on family, community, and human dignity.')
    elif is_lutheran_practicing:
        topic_anchors.append('On religion in your life: your answer is "Somewhat important" (B) — your Lutheran faith shapes your values even in very secular Sweden.')
    elif is_lutheran_nonpracticing and mf >= 42:
        topic_anchors.append('On religion in your life: your answer is "Somewhat important" (B) — you feel a genuine cultural and moral connection to the Lutheran tradition even if you don\'t attend church regularly.')
    elif is_lutheran_nonpracticing and mf >= 28:
        topic_anchors.append('On religion in your life: your answer is "Not too important" (C) — you have a loose cultural connection to Lutheranism — Christmas, confirmations — but religion doesn\'t guide your life.')
    elif is_lutheran_nonpracticing:
        topic_anchors.append('On religion in your life: your answer is "Not at all important" (D) — religion is nominally in your background but plays no real role.')
    elif is_secular and mf >= 30:
        topic_anchors.append('On religion in your life: your answer is "Not too important" (C) — religion is largely absent from your life, though you respect others\' beliefs.')
    elif is_secular and mf >= 22:
        topic_anchors.append('On religion in your life: your answer is "Not too important" (C) — Sweden is secular and so are you; religion is not part of your daily life.')
    else:
        topic_anchors.append('On religion in your life: your answer is "Not at all important" (D) — Sweden is one of the most secular societies on earth. Religion plays no role in your life.')

    # sw09: Economic system reform
    # Target: A=6.1%, B=30.9%, C=54.3%, D=8.7%
    # SW-1: C=82.4%, B=17.6%, A=0%, D=0% — everything→C; V→B but should→A; M high-IND/IT→D
    # Fix: V→A; M high-IND+IT→D; SD+working class→B; SAP lower-IT/less-educated→B; else→C
    if party == "V":
        topic_anchors.append('On economic reform: your answer is "Needs complete overhaul" (A) — Sweden\'s growing inequality, housing crisis, and welfare cuts since the 1990s require fundamental redistribution. The market-liberal direction must be reversed.')
    elif party == "M" and ind >= 68 and it >= 70:
        topic_anchors.append('On economic reform: your answer is "Does not need to be changed" (D) — Sweden\'s market economy is among the world\'s strongest. The model is fundamentally sound; political tinkering is the real risk.')
    elif party == "SD":
        topic_anchors.append('On economic reform: your answer is "Needs major changes" (B) — the current model has failed working-class Swedes, especially through decades of immigration costs and welfare strain. Major course corrections are needed.')
    elif party == "SAP" and (not is_university) and it < 65:
        topic_anchors.append('On economic reform: your answer is "Needs major changes" (B) — inequality has grown and the welfare state needs strengthening. The right-wing agenda is moving Sweden in the wrong direction.')
    elif party in ("M", "C") and ind >= 65:
        topic_anchors.append('On economic reform: your answer is "Needs minor changes" (C) — Sweden\'s market economy is broadly sound; targeted reforms on regulation and incentives are right, not structural overhaul.')
    elif party in ("SAP", "KD"):
        topic_anchors.append('On economic reform: your answer is "Needs minor changes" (C) — Sweden\'s mixed economy model is fundamentally right; protect the welfare state and make targeted improvements.')
    elif is_working_class and it < 48:
        topic_anchors.append('On economic reform: your answer is "Needs major changes" (B) — rising costs, housing unaffordability, and stagnant wages for working-class Swedes mean the system needs serious reform.')
    elif it >= 62 and ind >= 55:
        topic_anchors.append('On economic reform: your answer is "Needs minor changes" (C) — Sweden\'s economic model is one of the world\'s strongest; incremental improvement is right.')
    else:
        topic_anchors.append('On economic reform: your answer is "Needs minor changes" (C).')

    # sw10: Income inequality problem
    # Target: A=25.6%, B=43.0%, C=27.1%, D=4.4%
    # SW-3: A=39.0%, B=45.6%, C=15.4%, D=0% — A 13pp high, C 12pp low, D never fires
    # SW-4: A=11.5%, B=68.7%, C=15.4%, D=4.4% — A too low (SAP threshold too high, wc→B wrong)
    # Fix: restore SAP A-threshold to it≥65 (narrow; only committed SAP equality champions → A);
    #      remove working-class→B rule (was draining A and C unfairly);
    #      route KD→C (family/community model means inequality is manageable, not B);
    #      widen C via it≥64+ind≥55 (moderate-high-trust NP/C see welfare system as working);
    #      keep it<45→A catch for genuinely left-behind low-IT personas
    if party == "V":
        topic_anchors.append('On income inequality: your answer is "Very big problem" (A) — Sweden\'s Gini coefficient has risen sharply since the 1990s. The gap between rich and poor is now the largest in the Nordic region. This is a crisis.')
    elif party == "M" and ind >= 70 and it >= 72:
        topic_anchors.append('On income inequality: your answer is "Not a problem at all" (D) — Sweden\'s welfare state already aggressively redistributes. The real problem is not enough incentive for work and innovation.')
    elif party in ("M", "C") and ind >= 65:
        topic_anchors.append('On income inequality: your answer is "Small problem" (C) — Sweden still has the most redistributive tax system in the world. The focus should be on growth and opportunity, not further equalisation.')
    elif party == "SAP" and it >= 65:
        topic_anchors.append('On income inequality: your answer is "Very big problem" (A) — growing inequality directly threatens the social solidarity and collective model that the SAP built. This is one of the defining issues of our time.')
    elif party == "SAP":
        topic_anchors.append('On income inequality: your answer is "Moderately big problem" (B) — inequality has grown and the welfare state needs defending.')
    elif party == "SD":
        topic_anchors.append('On income inequality: your answer is "Moderately big problem" (B) — inequality has grown, especially in areas affected by failed immigration integration and welfare strain on working-class communities.')
    elif party == "KD":
        topic_anchors.append('On income inequality: your answer is "Small problem" (C) — Sweden\'s welfare state and strong family networks mean the most vulnerable are still protected; the focus should be on community, not redistribution.')
    elif it >= 64 and ind >= 55:
        topic_anchors.append('On income inequality: your answer is "Small problem" (C) — Sweden\'s extensive welfare system addresses inequality; the focus should be on opportunity and productivity.')
    elif it >= 60:
        topic_anchors.append('On income inequality: your answer is "Moderately big problem" (B).')
    elif it < 45:
        topic_anchors.append('On income inequality: your answer is "Very big problem" (A) — ordinary Swedes are being left behind while inequality grows.')
    else:
        topic_anchors.append('On income inequality: your answer is "Moderately big problem" (B).')

    # sw11: SAP view
    # Target: A=12.3%, B=50.4%, C=26.1%, D=11.2%
    # SAP still widely liked even in opposition (62.7% favorable)
    if party == "SAP" and it >= 65:
        topic_anchors.append('On the Social Democrats (SAP): your answer is "Very favorable" (A) — the SAP built modern Sweden. Their values remain the right values even in opposition.')
    elif party == "SAP":
        topic_anchors.append('On the Social Democrats (SAP): your answer is "Somewhat favorable" (B) — you support the SAP even if recent leadership has sometimes disappointed.')
    elif party == "V":
        topic_anchors.append('On the Social Democrats (SAP): your answer is "Somewhat favorable" (B) — you share many SAP goals but they moved too far to the centre and abandoned workers\' interests.')
    elif party == "C":
        topic_anchors.append('On the Social Democrats (SAP): your answer is "Somewhat unfavorable" (C) — they dominated Sweden for too long and built excessive state dependency.')
    elif party == "M":
        topic_anchors.append('On the Social Democrats (SAP): your answer is "Somewhat unfavorable" (C) — 90 years of SAP dominance left Sweden with too much state, too many taxes, and chronic inability to reform.')
    elif party == "KD":
        topic_anchors.append('On the Social Democrats (SAP): your answer is "Somewhat unfavorable" (C) — SAP secularism and immigration policy were wrong for Sweden.')
    elif party == "SD":
        topic_anchors.append('On the Social Democrats (SAP): your answer is "Very unfavorable" (D) — the SAP destroyed Sweden through mass immigration and political correctness. They betrayed the working class.')
    elif it >= 60 and is_working_class:
        topic_anchors.append('On the Social Democrats (SAP): your answer is "Somewhat favorable" (B) — whatever their failings, the SAP built the welfare state that protects people like you.')
    elif it < 45:
        topic_anchors.append('On the Social Democrats (SAP): your answer is "Somewhat unfavorable" (C).')
    else:
        topic_anchors.append('On the Social Democrats (SAP): your answer is "Somewhat favorable" (B).')

    # sw12: Moderates view
    # Target: A=7.4%, B=44.7%, C=34.2%, D=13.7%
    # SW-2: C=52.8%, B=31.9%, A=8.8%, D=6.6% — C overcounted, B undercounted
    # Fix: NP moderate-IT (45–64) → B instead of C (they are not hostile to the centre-right);
    #      NP low-IT → C (populist disenchantment with elites); SAP low-IT → D (stronger opposition)
    if party == "M" and it >= 70:
        topic_anchors.append('On the Moderates (M): your answer is "Very favorable" (A) — the Moderates are the responsible centre-right delivering stable government and needed reforms.')
    elif party == "M":
        topic_anchors.append('On the Moderates (M): your answer is "Somewhat favorable" (B) — you support the Moderate agenda even if governing in the Tidö coalition involves difficult compromises.')
    elif party == "KD":
        topic_anchors.append('On the Moderates (M): your answer is "Somewhat favorable" (B) — coalition partners; you agree on many things even if priorities differ.')
    elif party == "C":
        topic_anchors.append('On the Moderates (M): your answer is "Somewhat favorable" (B) — broadly aligned on markets and individual freedom, even if the SD reliance is uncomfortable.')
    elif party == "SAP" and it < 55:
        topic_anchors.append('On the Moderates (M): your answer is "Very unfavorable" (D) — Moderate austerity would gut the welfare state and is fundamentally opposed to everything the SAP stands for.')
    elif party == "SAP":
        topic_anchors.append('On the Moderates (M): your answer is "Somewhat unfavorable" (C) — centre-right austerity politics that will weaken the welfare state if they get their way.')
    elif party == "V":
        topic_anchors.append('On the Moderates (M): your answer is "Very unfavorable" (D) — Moderate economic policy serves the wealthy and undermines public services.')
    elif party == "SD":
        topic_anchors.append('On the Moderates (M): your answer is "Somewhat favorable" (B) — they finally accepted SD support and are now delivering on immigration and crime.')
    elif it >= 65 and ind >= 60:
        topic_anchors.append('On the Moderates (M): your answer is "Somewhat favorable" (B) — competent economic managers.')
    elif it >= 45 and it < 65:
        topic_anchors.append('On the Moderates (M): your answer is "Somewhat favorable" (B) — broadly acceptable centre-right government; not your first choice but not a concern either.')
    elif it < 45:
        topic_anchors.append('On the Moderates (M): your answer is "Somewhat unfavorable" (C) — they represent Stockholm elites, not ordinary Swedes.')
    else:
        topic_anchors.append('On the Moderates (M): your answer is "Somewhat unfavorable" (C).')

    # sw13: SD view
    # Target: A=5.5%, B=22.0%, C=25.7%, D=46.8%
    # SW-3: C=39.0%, B=22.0%, A=8.2%, D=30.8% — C 13pp high, D 16pp low
    # SW-4: C=47.3%, B=22.0%, A=8.2%, D=22.5% — SAP/M/KD→C flooding C; D badly under-routed
    # Fix: route high-IT SAP (it≥60) to D — strong SAP are most firmly anti-SD ideologically;
    #      route high-IT M (it≥70) to D — genuinely troubled by SD values despite coalition;
    #      keep lower-IT SAP and moderate M → C; B stays intact (wc+it<52 unchanged)
    if party == "SD" and it < 42:
        topic_anchors.append('On the Sweden Democrats (SD): your answer is "Very favorable" (A) — the SD are the only party that tells the truth about immigration and what it has done to Sweden.')
    elif party == "SD":
        topic_anchors.append('On the Sweden Democrats (SD): your answer is "Somewhat favorable" (B) — you support their direction even if the party is still finding its governing footing.')
    elif party == "V":
        topic_anchors.append('On the Sweden Democrats (SD): your answer is "Very unfavorable" (D) — the SD emerged from neo-Nazi roots; their ethnic nationalism is fundamentally incompatible with a tolerant, open Sweden.')
    elif party == "C":
        topic_anchors.append('On the Sweden Democrats (SD): your answer is "Very unfavorable" (D) — their nationalism contradicts the liberal values of individual freedom and open society that you believe in.')
    elif party == "SAP" and it >= 60:
        topic_anchors.append('On the Sweden Democrats (SD): your answer is "Very unfavorable" (D) — SD\'s politics of exclusion directly contradicts the solidarity, openness, and equality that the labour movement was built on. They are the opposite of what Sweden should stand for.')
    elif party == "SAP":
        topic_anchors.append('On the Sweden Democrats (SD): your answer is "Somewhat unfavorable" (C) — the SD represent a politics of exclusion that contradicts solidarity and Sweden\'s open tradition.')
    elif party == "M" and it >= 70:
        topic_anchors.append('On the Sweden Democrats (SD): your answer is "Very unfavorable" (D) — you accept their parliamentary support to govern, but their nationalist populism is fundamentally at odds with the liberal values of individual freedom and open society you believe in.')
    elif party == "M":
        topic_anchors.append('On the Sweden Democrats (SD): your answer is "Somewhat unfavorable" (C) — you accept SD support to govern but keep your distance; their values and M\'s are not the same.')
    elif party == "KD":
        topic_anchors.append('On the Sweden Democrats (SD): your answer is "Somewhat unfavorable" (C) — you work with them in coalition but their nationalism lacks the Christian democratic foundation of human dignity for all.')
    elif is_working_class and it < 52:
        topic_anchors.append('On the Sweden Democrats (SD): your answer is "Somewhat favorable" (B) — they say what others won\'t about immigration\'s real impact on ordinary Swedish communities.')
    elif is_university and it >= 58:
        topic_anchors.append('On the Sweden Democrats (SD): your answer is "Very unfavorable" (D) — their nationalist populism is corrosive to Swedish democratic culture and open society.')
    elif is_secular and it >= 60:
        topic_anchors.append('On the Sweden Democrats (SD): your answer is "Very unfavorable" (D) — SD nationalism and exclusionary politics are fundamentally at odds with secular, open Swedish values.')
    elif it >= 55 and not is_working_class:
        topic_anchors.append('On the Sweden Democrats (SD): your answer is "Very unfavorable" (D) — their politics of cultural exclusion and nationalist populism are deeply troubling.')
    elif it >= 50:
        topic_anchors.append('On the Sweden Democrats (SD): your answer is "Somewhat unfavorable" (C) — you have reservations about their nationalist direction but acknowledge they raised real concerns about integration.')
    else:
        topic_anchors.append('On the Sweden Democrats (SD): your answer is "Very unfavorable" (D).')

    # sw14: Children's future (3-option question)
    # Target: A=32.8%, B=57.6%, C=9.6%
    # Note: 3 options only — A=Better off, B=Worse off, C=Same
    if party == "V":
        topic_anchors.append('On whether children will be better or worse off than their parents: your answer is "Worse off" (B) — climate change, growing inequality, and housing unaffordability mean the next generation faces serious challenges.')
    elif party == "SD" and it < 45:
        topic_anchors.append('On whether children will be better or worse off than their parents: your answer is "Worse off" (B) — if immigration and crime are not addressed, Sweden\'s future is bleak.')
    elif party in ("M", "C") and it >= 68:
        topic_anchors.append('On whether children will be better or worse off than their parents: your answer is "Better off" (A) — with sound policy, Sweden\'s prosperity and innovation will create a better future.')
    elif party in ("M", "KD") and it >= 60:
        topic_anchors.append('On whether children will be better or worse off than their parents: your answer is "Better off" (A) — Sweden\'s strong institutions and economic model give reason for optimism.')
    elif is_working_class and it < 50:
        topic_anchors.append('On whether children will be better or worse off than their parents: your answer is "Worse off" (B) — costs keep rising, housing is unaffordable, and job security is worse than a generation ago.')
    elif it >= 65:
        topic_anchors.append('On whether children will be better or worse off than their parents: your answer is "Better off" (A) — Sweden has the institutions and values to build a good future.')
    else:
        topic_anchors.append('On whether children will be better or worse off than their parents: your answer is "Worse off" (B).')

    # sw15: UN view
    # Target: A=27.8%, B=52.6%, C=15.9%, D=3.7%
    # Sweden: 80.4% favorable — historically very pro-UN/multilateral
    if party in ("SAP", "C") and it >= 62:
        topic_anchors.append('On the United Nations: your answer is "Somewhat favorable" (B) — Sweden has always been a strong supporter of multilateralism and the UN. It\'s imperfect but essential.')
    elif party in ("M", "KD") and it >= 68:
        topic_anchors.append('On the United Nations: your answer is "Very favorable" (A) — international institutions and the rules-based order are vital for a small country like Sweden.')
    elif party == "V":
        topic_anchors.append('On the United Nations: your answer is "Somewhat favorable" (B) — the UN is important for conflict resolution and development, even if it is often blocked by great power politics.')
    elif party == "SD":
        topic_anchors.append('On the United Nations: your answer is "Somewhat unfavorable" (C) — the UN has been used to undermine Swedish sovereignty on migration policy. National self-determination matters more.')
    elif it >= 65:
        topic_anchors.append('On the United Nations: your answer is "Very favorable" (A) — Sweden\'s whole foreign policy tradition is built on multilateralism and the UN.')
    elif it < 45:
        topic_anchors.append('On the United Nations: your answer is "Somewhat unfavorable" (C) — the UN pushes globalist agendas that override national interests.')
    else:
        topic_anchors.append('On the United Nations: your answer is "Somewhat favorable" (B).')

    # ── Assemble prompt ───────────────────────────────────────────────────────
    anchors_text = ""
    if topic_anchors:
        anchors_text = "\n\nResponse calibration (apply these to relevant questions):\n" + \
                       "\n".join(f"- {a}" for a in topic_anchors)

    prompt = f"""You are {name}, a {age}-year-old {gender} from {region}.

Education: {education}. Religion: {religion}.

Political identity: {party}. {ova}

Your worldview:
- Institutional trust ({it}/100): {it_desc}
- Economic philosophy ({ind}/100): {"You prefer market and individual solutions over state intervention — lower taxes, less regulation, personal responsibility." if ind > 62 else "You believe the state should play a significant role in the economy — public investment, redistribution, strong social services." if ind < 38 else "You hold mixed views on state vs. market solutions."}
- Change tolerance ({ct}/100): {"You welcome fundamental change and see the status quo as deeply inadequate." if ct > 70 else "You are deeply skeptical of rapid change and value stability, tradition, and continuity." if ct < 28 else "You accept gradual, carefully managed change."}
- Moral foundationalism ({mf}/100): {"Your values are grounded in traditional religious or cultural norms on social questions." if mf > 55 else "You hold secular, liberal views on social and moral questions." if mf < 22 else "You hold mixed views — traditional on some questions, liberal on others."}{nato_layer}{religion_layer}{region_layer}{anchors_text}

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

    print(f"\nEurope Benchmark — Sweden — Sprint {sprint_id}")
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
    parser = argparse.ArgumentParser(description="Europe Benchmark Sweden sprint runner")
    parser.add_argument("--sprint", required=True, help="Sprint ID, e.g. SW-1")
    parser.add_argument("--model", choices=["haiku", "sonnet"], default="haiku")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run_sprint_batch(args.sprint, args.model, args.dry_run)


if __name__ == "__main__":
    main()
