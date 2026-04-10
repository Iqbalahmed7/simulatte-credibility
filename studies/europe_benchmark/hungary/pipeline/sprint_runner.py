#!/usr/bin/env python3
"""
sprint_runner.py — Europe Benchmark · Hungary calibration sprint runner.

Usage:
    python3 sprint_runner.py --sprint HU-1 --model haiku
    python3 sprint_runner.py --sprint HU-1 --model haiku --dry-run

WorldviewAnchor dimensions (0–100 scale):
    IT  — Institutional Trust
    IND — Individualism (market vs. state preference)
    CT  — Change Tolerance
    MF  — Moral Foundationalism

Key Hungary calibration axes:
    1. Dominant axis: Fidesz (Orbán ruling party) vs. opposition coalition
    2. Orbán effect: state media controls narrative; Fidesz voters show elevated IT
    3. Urban/rural split: Budapest opposition (DK/liberal) vs. rural Fidesz stronghold
    4. Russia: Hungary has softest Russia stance in EU — Orbán's pro-Russia/Paks ties
    5. Trump: 38% confidence — highest in EU; Orbán-Trump ideological alignment
    6. China: 37.9% favorable — highest in EU; Orbán's China-friendly Fudan/BYD policy
    7. Religion: Catholic (50%), Calvinist Reformed (16%), non-practicing majority
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
# Demographic targets (Pew / Hungarian Election Studies):
#   Parties:  Fidesz ~22.5%, DK ~12.5%, Jobbik ~10%, MSZP ~7.5%,
#             Non-partisan ~35%, Mi Hazánk ~5%, Other left/green ~7.5%
#   Region:   Budapest ~17%, Other urban ~38%, Rural/small town ~45%
#   Religion: Catholic (inc. non-practicing) ~50%, Calvinist Reformed ~16%,
#             Secular/non-practicing majority ~60%+
#   Education: University/college ~25%, Secondary/vocational ~45%, Primary/no qual ~30%
#   EU attitude: broadly favorable ~61%, unfavorable ~38%
#   Age range: 26–72

PERSONAS = [
    # ── Fidesz (nationalist-conservative, dominant since 2010) ────────────────
    ("hu_p01", "Kovács István",        58, "male",   "Hungary (Eastern / Hajdú-Bihar county)",    "Fidesz",       "EU-frustrated", "Catholic (non-practicing)", "Vocational/secondary",  2.5),
    ("hu_p02", "Tóth Erzsébet",        54, "female", "Hungary (Northern / Borsod county)",        "Fidesz",       "EU-frustrated", "Calvinist Reformed",        "Vocational/secondary",  2.5),
    ("hu_p03", "Nagy Sándor",          63, "male",   "Hungary (Rural / Szabolcs county)",         "Fidesz",       "EU-frustrated", "Catholic (practicing)",     "Vocational/secondary",  2.5),
    ("hu_p04", "Horváth Mária",        49, "female", "Hungary (Western / Győr-Moson-Sopron)",     "Fidesz",       "EU-frustrated", "Catholic (non-practicing)", "Secondary/Bac",         2.5),
    ("hu_p05", "Szabó Zoltán",         67, "male",   "Hungary (Southern / Baranya county)",       "Fidesz",       "EU-frustrated", "Catholic (practicing)",     "Vocational/secondary",  2.5),
    ("hu_p06", "Varga Katalin",        44, "female", "Hungary (Northern / Heves county)",         "Fidesz",       "EU-frustrated", "Calvinist Reformed",        "Secondary/Bac",         2.5),
    ("hu_p07", "Kiss Gábor",           51, "male",   "Hungary (Semi-urban / Miskolc)",            "Fidesz",       "EU-frustrated", "Catholic (non-practicing)", "Secondary/Bac",         2.5),
    ("hu_p08", "Molnár Ilona",         61, "female", "Hungary (Rural / Somogy county)",           "Fidesz",       "EU-frustrated", "Catholic (practicing)",     "Vocational/secondary",  2.5),
    ("hu_p09", "Németh Péter",         47, "male",   "Hungary (Eastern / Debrecen area)",         "Fidesz",       "EU-frustrated", "Calvinist Reformed",        "University/college",    2.5),

    # ── DK (Democratic Coalition — liberal opposition, pro-EU, Budapest) ──────
    ("hu_p10", "Farkas Zsuzsa",        41, "female", "Hungary (Budapest / District VII)",         "DK",           "Pro-EU",        "None/secular",              "University/college",    2.0),
    ("hu_p11", "Kovács Ádám",          36, "male",   "Hungary (Budapest / Buda side)",            "DK",           "Pro-EU",        "None/secular",              "University/college",    2.0),
    ("hu_p12", "Tóth Réka",            45, "female", "Hungary (Budapest / District XIII)",        "DK",           "Pro-EU",        "Catholic (non-practicing)", "University/college",    2.0),
    ("hu_p13", "Horváth Dániel",       52, "male",   "Hungary (Budapest / District II)",          "DK",           "Pro-EU",        "None/secular",              "University/college",    2.0),
    ("hu_p14", "Nagy Eszter",          33, "female", "Hungary (Budapest / Pest agglomeration)",   "DK",           "Pro-EU",        "None/secular",              "University/college",    2.0),

    # ── Jobbik (originally far-right, now reformed centre-right) ─────────────
    ("hu_p15", "Szabó Attila",         44, "male",   "Hungary (Northern / Miskolc area)",         "Jobbik",       "EU-skeptic",    "Catholic (non-practicing)", "Secondary/Bac",         2.5),
    ("hu_p16", "Varga Judit",          38, "female", "Hungary (Eastern / Nyíregyháza area)",      "Jobbik",       "EU-skeptic",    "Calvinist Reformed",        "Secondary/Bac",         2.5),
    ("hu_p17", "Kiss Balázs",          50, "male",   "Hungary (Rural / Bács-Kiskun county)",      "Jobbik",       "EU-skeptic",    "Catholic (non-practicing)", "Vocational/secondary",  2.5),
    ("hu_p18", "Molnár Orsolya",       42, "female", "Hungary (Semi-urban / Eger)",               "Jobbik",       "EU-skeptic",    "Catholic (practicing)",     "Secondary/Bac",         2.5),

    # ── MSZP (Socialist — older, working class, urban) ────────────────────────
    ("hu_p19", "Németh László",        64, "male",   "Hungary (Budapest / District VIII)",        "MSZP",         "Pro-EU",        "None/secular",              "Secondary/Bac",         2.5),
    ("hu_p20", "Farkas Ágnes",         59, "female", "Hungary (Semi-urban / Pécs)",               "MSZP",         "Pro-EU",        "None/secular",              "Vocational/secondary",  2.5),
    ("hu_p21", "Kovács Tibor",         68, "male",   "Hungary (Northern / Ózd area)",             "MSZP",         "Pro-EU",        "None/secular",              "Vocational/secondary",  2.5),

    # ── Mi Hazánk (far-right, extreme nationalist) ────────────────────────────
    ("hu_p22", "Tóth Norbert",         39, "male",   "Hungary (Rural / Szabolcs-Szatmár county)", "Mi Hazánk",    "EU-hostile",    "Catholic (non-practicing)", "Vocational/secondary",  2.5),
    ("hu_p23", "Horváth Béla",         55, "male",   "Hungary (Northern / Nógrád county)",        "Mi Hazánk",    "EU-hostile",    "Calvinist Reformed",        "Vocational/secondary",  2.5),

    # ── Other left/green ──────────────────────────────────────────────────────
    ("hu_p24", "Szabó Lilla",          29, "female", "Hungary (Budapest / District VI)",          "Other left",   "Pro-EU",        "None/secular",              "University/college",    2.0),
    ("hu_p25", "Varga Márton",         34, "male",   "Hungary (Budapest / District IX)",          "Other left",   "Pro-EU",        "None/secular",              "University/college",    2.0),
    ("hu_p26", "Kiss Flóra",           26, "female", "Hungary (Budapest / District XIV)",         "Other left",   "Pro-EU",        "None/secular",              "University/college",    2.0),

    # ── Non-partisan (cross-cutting: Fidesz-adjacent rural + opposition-adj.) ─
    ("hu_p27", "Molnár Ferenc",        60, "male",   "Hungary (Rural / Tolna county)",            "Non-partisan", "EU-frustrated", "Catholic (non-practicing)", "Vocational/secondary",  2.5),
    ("hu_p28", "Németh Éva",           53, "female", "Hungary (Rural / Fejér county)",            "Non-partisan", "EU-frustrated", "Catholic (non-practicing)", "Vocational/secondary",  2.5),
    ("hu_p29", "Farkas Imre",          66, "male",   "Hungary (Eastern / Hajdú-Bihar rural)",     "Non-partisan", "EU-frustrated", "Calvinist Reformed",        "Vocational/secondary",  2.5),
    ("hu_p30", "Kovács Veronika",      48, "female", "Hungary (Semi-urban / Debrecen)",           "Non-partisan", "EU-frustrated", "Catholic (non-practicing)", "Secondary/Bac",         2.5),
    ("hu_p31", "Tóth Csaba",           57, "male",   "Hungary (Northern / Miskolc)",              "Non-partisan", "EU-frustrated", "None/secular",              "Secondary/Bac",         2.5),
    ("hu_p32", "Horváth Tünde",        43, "female", "Hungary (Western / Győr)",                  "Non-partisan", "EU-frustrated", "Catholic (non-practicing)", "Secondary/Bac",         2.5),
    ("hu_p33", "Nagy Róbert",          35, "male",   "Hungary (Budapest / District IV)",          "Non-partisan", "Pro-EU",        "None/secular",              "University/college",    2.0),
    ("hu_p34", "Szabó Henrietta",      50, "female", "Hungary (Budapest / District XI)",          "Non-partisan", "Pro-EU",        "Catholic (non-practicing)", "Secondary/Bac",         2.0),
    ("hu_p35", "Varga Gergő",          31, "male",   "Hungary (Budapest / District XV)",          "Non-partisan", "Pro-EU",        "None/secular",              "University/college",    2.0),
    ("hu_p36", "Kiss Magdolna",        72, "female", "Hungary (Rural / Somogy county)",           "Non-partisan", "EU-frustrated", "Catholic (practicing)",     "Vocational/secondary",  2.5),
    ("hu_p37", "Molnár Árpád",         62, "male",   "Hungary (Southern / Pécs area)",            "Non-partisan", "EU-frustrated", "Catholic (non-practicing)", "Vocational/secondary",  2.5),
    ("hu_p38", "Németh Klára",         46, "female", "Hungary (Semi-urban / Veszprém)",           "Non-partisan", "EU-frustrated", "Calvinist Reformed",        "Secondary/Bac",         2.5),
    ("hu_p39", "Farkas Zsolt",         58, "male",   "Hungary (Eastern / Szolnok area)",          "Non-partisan", "EU-frustrated", "None/secular",              "Vocational/secondary",  2.5),
    ("hu_p40", "Kovács Annamária",     37, "female", "Hungary (Budapest / Pest county)",          "Non-partisan", "Pro-EU",        "None/secular",              "Secondary/Bac",         2.0),
]

# ── WorldviewAnchor values ────────────────────────────────────────────────────
WORLDVIEW = {
    # id:        (IT,  IND, CT,  MF)
    # Fidesz — elevated IT (trust Orbán's institutions), moderate IND, low CT, moderate-high MF
    "hu_p01": (58,  58,  22,  60),   # Fidesz, Eastern rural, Calvinist/Catholic, vocational (male)
    "hu_p02": (55,  56,  20,  65),   # Fidesz, Northern, Calvinist Reformed, vocational (female)
    "hu_p03": (62,  60,  18,  72),   # Fidesz, rural Szabolcs, practicing Catholic, vocational (older)
    "hu_p04": (54,  58,  25,  55),   # Fidesz, Western Győr, non-practicing Catholic, Bac
    "hu_p05": (60,  55,  16,  70),   # Fidesz, Southern, practicing Catholic, vocational (oldest)
    "hu_p06": (52,  57,  24,  63),   # Fidesz, Northern, Calvinist Reformed, Bac (female)
    "hu_p07": (56,  60,  26,  52),   # Fidesz, Miskolc semi-urban, non-practicing, Bac
    "hu_p08": (63,  54,  15,  68),   # Fidesz, rural Somogy, practicing Catholic, vocational (older female)
    "hu_p09": (50,  62,  30,  58),   # Fidesz, Debrecen, Calvinist, university (younger, pragmatic)

    # DK — low IT (distrust Orbán's captured institutions), moderate IND, high CT, low MF
    "hu_p10": (32,  55,  70,  12),   # DK, Budapest VII, secular, university (female)
    "hu_p11": (30,  56,  72,  10),   # DK, Budapest Buda, secular, university
    "hu_p12": (38,  52,  65,  25),   # DK, Budapest XIII, non-practicing Catholic, university
    "hu_p13": (35,  54,  68,  14),   # DK, Budapest II, secular, university (older male)
    "hu_p14": (28,  58,  74,  10),   # DK, Budapest Pest agglo, secular, university (youngest)

    # Jobbik — low-moderate IT, moderate IND, moderate-low CT, moderate MF
    "hu_p15": (42,  56,  30,  48),   # Jobbik, Miskolc, non-practicing Catholic, Bac
    "hu_p16": (38,  55,  28,  55),   # Jobbik, Nyíregyháza, Calvinist, Bac
    "hu_p17": (40,  54,  25,  50),   # Jobbik, rural, non-practicing Catholic, vocational
    "hu_p18": (44,  56,  32,  58),   # Jobbik, Eger, practicing Catholic, Bac

    # MSZP — moderate IT, low IND, moderate CT, low MF
    "hu_p19": (48,  38,  55,  16),   # MSZP, Budapest VIII, secular, Bac (older male)
    "hu_p20": (45,  36,  52,  18),   # MSZP, Pécs, secular, vocational (female)
    "hu_p21": (42,  35,  50,  20),   # MSZP, Ózd, secular, vocational (oldest male)

    # Mi Hazánk — very low IT (anti-Brussels), moderate IND, very low CT, high MF
    "hu_p22": (28,  58,  14,  65),   # Mi Hazánk, rural Szabolcs, non-practicing Catholic, vocational
    "hu_p23": (25,  60,  12,  68),   # Mi Hazánk, rural Nógrád, Calvinist, vocational (older)

    # Other left/green — low IT, low IND, very high CT, very low MF
    "hu_p24": (30,  32,  82,  8),    # Other left, Budapest VI, secular, university (youngest female)
    "hu_p25": (32,  34,  80,  10),   # Other left, Budapest IX, secular, university
    "hu_p26": (28,  30,  84,  8),    # Other left, Budapest XIV, secular, university (youngest)

    # Non-partisan Fidesz-adjacent (rural/semi-urban, EU-frustrated)
    "hu_p27": (50,  55,  22,  55),   # NP, rural Tolna, non-practicing Catholic, vocational (male)
    "hu_p28": (48,  54,  20,  52),   # NP, rural Fejér, non-practicing Catholic, vocational (female)
    "hu_p29": (52,  56,  18,  60),   # NP, Eastern rural, Calvinist, vocational (oldest male)
    "hu_p30": (46,  56,  28,  48),   # NP, Debrecen semi-urban, non-practicing Catholic, Bac
    "hu_p31": (44,  55,  26,  40),   # NP, Miskolc, secular, Bac
    "hu_p32": (50,  57,  30,  50),   # NP, Western Győr, non-practicing Catholic, Bac

    # Non-partisan Budapest opposition-adjacent (urban, Pro-EU)
    "hu_p33": (35,  52,  65,  12),   # NP, Budapest IV, secular, university
    "hu_p34": (40,  50,  58,  28),   # NP, Budapest XI, non-practicing Catholic, Bac
    "hu_p35": (32,  54,  68,  10),   # NP, Budapest XV, secular, university (younger)
    "hu_p36": (55,  50,  16,  68),   # NP, rural Somogy, practicing Catholic, vocational (oldest)
    "hu_p37": (48,  55,  24,  52),   # NP, Pécs area, non-practicing Catholic, vocational
    "hu_p38": (46,  56,  30,  58),   # NP, Veszprém, Calvinist, Bac
    "hu_p39": (44,  54,  22,  42),   # NP, Eastern Szolnok, secular, vocational
    "hu_p40": (36,  52,  62,  15),   # NP, Budapest Pest county, secular, Bac (younger female)
}


def build_system_prompt(persona: tuple) -> str:
    pid, name, age, gender, region, party, eu_ref, religion, education, weight = persona
    it, ind, ct, mf = WORLDVIEW[pid]

    is_budapest         = "Budapest" in region
    is_rural            = "Rural" in region or "county" in region
    is_eastern          = "Eastern" in region or "Hajdú" in region or "Szabolcs" in region or "Debrecen" in region
    is_northern         = "Northern" in region or "Borsod" in region or "Miskolc" in region or "Nógrád" in region
    is_western          = "Western" in region or "Győr" in region
    is_eu_frustrated    = eu_ref == "EU-frustrated"
    is_pro_eu           = eu_ref == "Pro-EU"
    is_eu_hostile       = eu_ref == "EU-hostile"
    is_calvinist        = "Calvinist" in religion
    is_catholic_practicing = "practicing" in religion and "non" not in religion
    is_non_practicing   = "non-practicing" in religion
    is_secular          = "secular" in religion or "None" in religion
    is_working_class    = "Vocational" in education or "vocational" in education
    is_fidesz           = party == "Fidesz"
    is_dk               = party == "DK"
    is_opposition       = party in ("DK", "MSZP", "Jobbik", "Other left")
    is_mi_hazank        = party == "Mi Hazánk"

    # ── Institutional trust descriptor ────────────────────────────────────────
    if it < 35:
        it_desc = (
            "You have very low trust in Hungarian institutions — you believe Orbán has "
            "captured the courts, media, and electoral system to entrench his power. "
            "The state serves Fidesz, not Hungarian citizens."
        )
    elif it < 48:
        it_desc = (
            "You have mixed trust in Hungarian institutions. You recognise the system "
            "is skewed toward Fidesz but retain some faith in certain state functions "
            "and local administration."
        )
    elif it < 58:
        it_desc = (
            "You have moderate trust in Hungarian institutions. You broadly support "
            "the direction of the country under its current government, though you "
            "acknowledge things are not perfect."
        )
    else:
        it_desc = (
            "You have relatively high trust in Hungarian institutions — the government, "
            "police, and national media broadly reflect your values and Hungary's interests. "
            "Orbán has stabilised Hungary and stood up to Brussels."
        )

    # ── EU/Europe layer ────────────────────────────────────────────────────────
    if is_pro_eu:
        eu_layer = (
            "\nEurope: You are strongly pro-European. You see EU membership as essential "
            "for Hungary's democracy, rule of law, and economic development. "
            "You are deeply frustrated that Orbán has isolated Hungary within the EU and "
            "undermined democratic norms for which Hungarians fought in 1989."
        )
    elif is_eu_frustrated:
        eu_layer = (
            "\nEurope: You have ambivalent feelings about the EU. You accept that EU "
            "membership brings economic benefits and you are not calling for Huxit, "
            "but you resent Brussels interfering in Hungarian internal affairs, "
            "dictating on migration, and threatening to withhold funds. "
            "Orbán is right to defend Hungarian sovereignty against EU overreach."
        )
    else:  # EU-hostile
        eu_layer = (
            "\nEurope: You are deeply hostile to the EU. Brussels is an unelected "
            "bureaucracy trying to erase Hungarian national identity, impose migration, "
            "and submit Hungary to LGBTQ ideology. Hungary's interests come first."
        )

    # ── Party political identity ───────────────────────────────────────────────
    ova_map = {
        "Fidesz": (
            "After decades of post-communist drift, Fidesz gave Hungary back its "
            "self-confidence. Orbán has rebuilt national institutions, protected borders, "
            "kept Hungary out of wars, and delivered family support that reversed the "
            "demographic collapse. You support a Hungary that is Christian, sovereign, "
            "and proud — not one subordinated to Brussels liberal elites."
        ),
        "DK": (
            "Hungary under Orbán is drifting toward autocracy. The Democratic Coalition "
            "represents the values of 1989 — rule of law, free press, independent courts, "
            "and a Hungary at home in the European mainstream. You want Hungary back in the "
            "democratic family of nations, not isolated as an Orbán-Putin ally."
        ),
        "Jobbik": (
            "Hungary needs genuine conservative renewal — not Fidesz cronyism dressed up as "
            "nationalism. Jobbik has transformed into a serious centre-right party that "
            "combines Hungarian national pride with respect for democratic rules, European "
            "norms, and anti-corruption. You distrust both Orbán's authoritarianism and "
            "the liberal opposition's cosmopolitanism."
        ),
        "MSZP": (
            "Hungary needs a social-democratic path: strong public services, workers' rights, "
            "pensioner support, and an economy that works for the many. The Socialist Party "
            "represents the legacy of social solidarity. You are pro-EU and believe Hungary "
            "must remain anchored in European values — not aligned with Moscow."
        ),
        "Mi Hazánk": (
            "Fidesz has betrayed Hungarian nationalism by making deals with Brussels "
            "and staying in the EU. Mi Hazánk represents true Hungarian sovereignty: "
            "complete border control, zero immigration, rejection of Brussels cultural "
            "imperialism, and Hungary first in all things. You see Russia as less of a "
            "threat than Western liberal ideology."
        ),
        "Other left": (
            "Hungary needs a genuine democratic renewal from the left — not the old "
            "MSZP but a new politics of ecological justice, gender equality, and "
            "European solidarity. You are fiercely anti-Fidesz and pro-European, "
            "and believe Hungary's young generation deserves a future free of "
            "Orbán's illiberal state."
        ),
        "Non-partisan": (
            "no single party represents your views. You are disillusioned with the "
            "political class — both Fidesz's corruption and the fragmented, ineffective "
            "opposition. You vote based on immediate concerns or not at all."
        ),
    }
    ova = ova_map.get(party, "")

    # ── Religion layer ────────────────────────────────────────────────────────
    religion_layer = ""
    if is_catholic_practicing:
        religion_layer = (
            "\nFaith and identity: You are a practising Catholic. Your faith shapes "
            "your social values — family, community, and the importance of Hungary's "
            "Christian heritage. You support Fidesz's Christian-democracy framing and "
            "are wary of secular liberal ideology undermining Hungary's traditions."
        )
    elif is_calvinist:
        religion_layer = (
            "\nFaith and identity: You identify with Hungary's Calvinist Reformed "
            "tradition. Your faith is part of your Hungarian national identity — "
            "Calvinist communities are historically intertwined with Hungarian "
            "nationalism and resistance to foreign domination."
        )
    elif is_non_practicing:
        religion_layer = (
            "\nFaith and identity: You were raised Catholic or in a nominally religious "
            "household, but faith does not play a major role in your daily life. "
            "Hungary's Christian cultural identity still matters symbolically to you."
        )

    # ── Regional layer ────────────────────────────────────────────────────────
    region_layer = ""
    if is_budapest:
        region_layer = (
            "\nRegional background: You live in Budapest, Hungary's capital and its "
            "only major opposition-voting city. Budapest is more educated, cosmopolitan, "
            "and pro-EU than the rest of the country. The urban-rural divide is stark — "
            "Budapest votes overwhelmingly against Fidesz, while rural Hungary votes for it."
        )
    elif is_eastern:
        region_layer = (
            "\nRegional background: You are from Eastern Hungary — Hajdú-Bihar, "
            "Szabolcs-Szatmár, or the Debrecen area. This region is among Hungary's "
            "poorest and most dependent on agricultural work and state employment. "
            "It is one of Fidesz's strongest strongholds. The Calvinist Reformed church "
            "is prominent here, especially around Debrecen."
        )
    elif is_northern:
        region_layer = (
            "\nRegional background: You are from Northern Hungary — Borsod, Heves, "
            "Nógrád, or Miskolc. This was Hungary's industrial heartland, now "
            "severely deindustrialised after 1990. Unemployment and emigration are "
            "persistent problems. The region votes strongly Fidesz, with pockets of "
            "Jobbik support in former mining towns."
        )
    elif is_western:
        region_layer = (
            "\nRegional background: You are from Western Hungary — Győr-Moson-Sopron "
            "or nearby. This is Hungary's wealthiest non-Budapest region, with strong "
            "German investment (Audi, etc.) and close ties to Austria. "
            "It broadly supports Fidesz but is more economically pragmatic than ideologically driven."
        )

    # ── Topic-specific option-vocabulary anchors ──────────────────────────────
    topic_anchors = []

    # hu01: Economic conditions
    # Target: A=3.9%, B=37.7%, C=43.1%, D=15.3%
    # HU-1: B=10.6%, C=89.4% — only Fidesz high-IT → B, everything else → C
    # Fix: Fidesz all → B; NP Fidesz-adj → B; DK/MSZP/Other left → C or D; Jobbik/Mi Hazánk → C
    if is_fidesz and it >= 58:
        topic_anchors.append('On Hungary\'s economic situation: your answer is "Somewhat good" (B) — the government has delivered jobs, family benefits, and stability. Despite inflation challenges, the economic fundamentals are solid.')
    elif is_fidesz:
        topic_anchors.append('On Hungary\'s economic situation: your answer is "Somewhat good" (B) — you trust the government\'s economic direction. Inflation is a challenge but employment is high and family support programmes are real.')
    elif is_dk and it <= 32:
        topic_anchors.append('On Hungary\'s economic situation: your answer is "Very bad" (D) — Orbán\'s crony capitalism has destroyed institutional capacity. Wages are among the lowest in the EU and EU funds are stolen.')
    elif is_dk:
        topic_anchors.append('On Hungary\'s economic situation: your answer is "Somewhat bad" (C) — GDP figures mask structural dysfunction: low wages, brain drain, and lost EU funds due to rule-of-law disputes.')
    elif party == "MSZP":
        topic_anchors.append('On Hungary\'s economic situation: your answer is "Somewhat bad" (C) — workers are falling behind. Real wages eroded by inflation, and investment benefits oligarchs, not ordinary Hungarians.')
    elif party == "Other left":
        topic_anchors.append('On Hungary\'s economic situation: your answer is "Very bad" (D) — Hungary is experiencing managed decline. EU funds lost, brain drain accelerating, real wages stagnant.')
    elif is_mi_hazank:
        topic_anchors.append('On Hungary\'s economic situation: your answer is "Somewhat bad" (C) — too dependent on foreign capital, EU transfers, and cheap Russian energy. Not a sovereign economy.')
    elif party == "Jobbik":
        topic_anchors.append('On Hungary\'s economic situation: your answer is "Somewhat bad" (C) — structural problems: low wages, regional inequality, and the economy\'s dependence on Fidesz-connected oligarchs.')
    elif is_eu_frustrated and it >= 48:
        topic_anchors.append('On Hungary\'s economic situation: your answer is "Somewhat good" (B) — employment is high, family benefits exist, but you feel squeezed by inflation and rising prices.')
    elif is_eu_frustrated:
        topic_anchors.append('On Hungary\'s economic situation: your answer is "Somewhat bad" (C) — inflation has eroded your living standards even if employment is technically high.')
    elif is_pro_eu and it <= 40:
        topic_anchors.append('On Hungary\'s economic situation: your answer is "Very bad" (D) — lost EU funds, structural corruption, and brain drain are destroying Hungary\'s long-term economic future.')
    else:
        topic_anchors.append('On Hungary\'s economic situation: your answer is "Somewhat bad" (C).')

    # hu02: Democracy satisfaction
    # Target: A=5.5%, B=43.4%, C=33.2%, D=18.0%
    # NOTE: 48.8% satisfied — Fidesz voters say satisfied, opposition voters say not
    if is_fidesz and it >= 58:
        topic_anchors.append('On democracy in Hungary: your answer is "Somewhat satisfied" (B) — Hungary has free elections and a strong government that follows its mandate. Western critics distort the reality of Hungarian democracy.')
    elif is_fidesz:
        topic_anchors.append('On democracy in Hungary: your answer is "Somewhat satisfied" (B) — the system works; you can vote, protest, and live freely.')
    elif is_mi_hazank:
        topic_anchors.append('On democracy in Hungary: your answer is "Not too satisfied" (C) — even under Fidesz, the system still serves elites and EU dependencies rather than real Hungarian sovereignty.')
    elif is_dk and it <= 32:
        topic_anchors.append('On democracy in Hungary: your answer is "Not at all satisfied" (D) — Orbán has systematically dismantled democratic institutions: courts, media, electoral rules. Hungary is no longer a full democracy.')
    elif is_dk:
        topic_anchors.append('On democracy in Hungary: your answer is "Not at all satisfied" (D) — the democratic backsliding since 2010 has been severe and deliberate.')
    elif party == "MSZP":
        topic_anchors.append('On democracy in Hungary: your answer is "Not too satisfied" (C) — the playing field is deeply uneven: state media, gerrymandering, and captured courts.')
    elif party == "Jobbik":
        topic_anchors.append('On democracy in Hungary: your answer is "Not too satisfied" (C) — the system favours Fidesz structurally; genuine democratic competition is constrained.')
    elif party == "Other left":
        topic_anchors.append('On democracy in Hungary: your answer is "Not at all satisfied" (D) — Hungary under Orbán is an electoral autocracy, not a democracy.')
    elif is_eu_frustrated and it >= 48:
        topic_anchors.append('On democracy in Hungary: your answer is "Somewhat satisfied" (B) — things work well enough in day-to-day life.')
    elif is_pro_eu and is_budapest:
        topic_anchors.append('On democracy in Hungary: your answer is "Not at all satisfied" (D) — democratic norms have been gutted.')
    else:
        topic_anchors.append('On democracy in Hungary: your answer is "Not too satisfied" (C).')

    # hu03: Russia view
    # Target: A=2.7%, B=21.0%, C=40.8%, D=35.5%
    # NOTE: 23.7% favorable — highest in CEE due to Orbán-Putin framing
    if is_fidesz and it >= 58:
        topic_anchors.append('On Russia: your answer is "Somewhat favorable" (B) — Russia is a neighbour Hungary must deal with pragmatically. The Paks nuclear plant provides energy security. Orbán\'s peace approach is more sensible than those pushing escalation.')
    elif is_fidesz:
        topic_anchors.append('On Russia: your answer is "Somewhat unfavorable" (C) — you understand the pragmatic case for engagement but are uneasy about the invasion of Ukraine.')
    elif is_mi_hazank:
        topic_anchors.append('On Russia: your answer is "Somewhat favorable" (B) — Russia represents a counterweight to American and Brussels liberal hegemony. Hungary has more in common with Russia\'s conservative values than with Soros\'s open society agenda.')
    elif is_dk or party == "Other left":
        topic_anchors.append('On Russia: your answer is "Very unfavorable" (D) — Russia is an aggressive imperialist power threatening all of Europe, including Hungary. Orbán\'s pro-Russia stance endangers Hungarian security.')
    elif party == "MSZP":
        topic_anchors.append('On Russia: your answer is "Very unfavorable" (D) — the invasion of Ukraine was an unprovoked war crime. Hungary must stand with its NATO and EU partners.')
    elif party == "Jobbik":
        topic_anchors.append('On Russia: your answer is "Somewhat unfavorable" (C) — you understand energy dependency pressures but cannot approve of Russian aggression.')
    elif is_eu_frustrated and is_working_class:
        topic_anchors.append('On Russia: your answer is "Somewhat unfavorable" (C) — you are not pro-Russian but also not convinced the war has nothing to do with NATO expansion.')
    elif is_pro_eu:
        topic_anchors.append('On Russia: your answer is "Very unfavorable" (D).')
    else:
        topic_anchors.append('On Russia: your answer is "Somewhat unfavorable" (C).')

    # hu04: EU view
    # Target: A=12.1%, B=49.4%, C=28.9%, D=9.6%
    # HU-3: B=62.2%, C=23.9%, D=5.3%, A=8.5% — B over, A slightly under
    # Fix (HU-4): DK low-IT → A to push A to target; DK higher-IT stays B;
    #   pro-EU Budapest NP → A; other paths unchanged.
    if is_dk and it <= 32:
        topic_anchors.append('On the European Union: your answer is "Very favorable" (A) — the EU is Hungary\'s only real guarantee of democratic accountability, rule of law, and economic development. Orbán\'s war against Brussels is a war against Hungarian democracy itself.')
    elif is_dk:
        topic_anchors.append('On the European Union: your answer is "Somewhat favorable" (B) — EU membership is Hungary\'s essential lifeline for democratic accountability. Orbán\'s euroscepticism damages Hungary\'s future, but the answer is deeper engagement, not exit.')
    elif party in ("MSZP", "Other left"):
        topic_anchors.append('On the European Union: your answer is "Somewhat favorable" (B) — the EU is vital for Hungary\'s democratic institutions and economic development. You are firmly pro-EU even as you push for deeper reform.')
    elif party == "Jobbik":
        topic_anchors.append('On the European Union: your answer is "Somewhat favorable" (B) — EU membership is important for Hungary\'s economy and security, even if Brussels sometimes overreaches on issues of national sovereignty.')
    elif is_fidesz and it >= 58:
        topic_anchors.append('On the European Union: your answer is "Somewhat favorable" (B) — EU funds help Hungary develop, but Brussels must respect Hungarian sovereignty and not dictate on migration or family policy.')
    elif is_fidesz:
        topic_anchors.append('On the European Union: your answer is "Somewhat unfavorable" (C) — Brussels has become a political weapon used against Hungary for not following its liberal agenda. Hungary\'s sovereignty must be defended.')
    elif is_mi_hazank:
        topic_anchors.append('On the European Union: your answer is "Very unfavorable" (D) — the EU is a superstate project designed to erase Hungarian sovereignty and national identity. Hungary should renegotiate its membership on sovereign terms.')
    elif is_eu_frustrated and it >= 48:
        topic_anchors.append('On the European Union: your answer is "Somewhat favorable" (B) — the funds matter and Huxit would be catastrophic. But Brussels overreaches on politics and must respect Hungarian sovereignty.')
    elif is_eu_frustrated:
        topic_anchors.append('On the European Union: your answer is "Somewhat unfavorable" (C) — Brussels interferes too much in Hungary\'s internal affairs and withholds funds as political punishment.')
    elif is_pro_eu and is_budapest:
        topic_anchors.append('On the European Union: your answer is "Very favorable" (A) — the EU is Hungary\'s guarantee of democratic values, prosperity, and a future free from Orbán\'s illiberal isolation of Hungary within Europe.')
    else:
        topic_anchors.append('On the European Union: your answer is "Somewhat favorable" (B).')

    # hu05: NATO view
    # Target: A=12.2%, B=53.7%, C=27.7%, D=6.5%
    # HU-3: B=50.5%, C=45.2%, D=4.3% — no A; C massively over because all eu_frustrated → C
    # Fix (HU-4): DK → A (very favorable, NATO = only bulwark against Russia); MSZP/Other left → B;
    #   Fidesz high-IT → B; Fidesz lower → C; Mi Hazánk → D; Jobbik → B;
    #   NP eu_frustrated high-IT (≥48) → B (accept NATO as security shield, not actively hostile);
    #   NP eu_frustrated low-IT → C; pro-EU NP Budapest → A or B
    if is_dk:
        topic_anchors.append('On NATO: your answer is "Very favorable" (A) — NATO is Hungary\'s only real security guarantee against Russian aggression. Orbán\'s obstruction of Ukraine aid and cozying up to Putin is a betrayal of Hungary\'s NATO commitments and endangers the whole alliance.')
    elif party == "MSZP":
        topic_anchors.append('On NATO: your answer is "Somewhat favorable" (B) — NATO membership is Hungary\'s essential security guarantee. Collective defence has kept the peace in Europe for 75 years.')
    elif party == "Other left":
        topic_anchors.append('On NATO: your answer is "Somewhat favorable" (B) — collective defence is necessary given Russian aggression, though NATO must also invest more in diplomacy and conflict prevention.')
    elif is_fidesz and it >= 58:
        topic_anchors.append('On NATO: your answer is "Somewhat favorable" (B) — NATO membership provides collective security, but Hungary should not be dragged into escalation. Orbán is right to pursue peace negotiations rather than sending weapons.')
    elif is_fidesz:
        topic_anchors.append('On NATO: your answer is "Somewhat unfavorable" (C) — NATO\'s current direction under American pressure conflicts with Hungarian national interests. Hungary needs peace and neutrality, not to become a frontline state.')
    elif is_mi_hazank:
        topic_anchors.append('On NATO: your answer is "Very unfavorable" (D) — NATO is an instrument of American imperialism that drags Hungary into wars that serve Washington, not Hungarians. True sovereignty means neutrality.')
    elif party == "Jobbik":
        topic_anchors.append('On NATO: your answer is "Somewhat favorable" (B) — collective defence is important given Russia\'s aggression. Hungary must honour its NATO commitments and not undermine the alliance.')
    elif is_eu_frustrated and it >= 48:
        topic_anchors.append('On NATO: your answer is "Somewhat favorable" (B) — NATO has kept Hungary safe since 1999. You have reservations about escalation but fundamentally accept collective defence as a necessary shield.')
    elif is_eu_frustrated:
        topic_anchors.append('On NATO: your answer is "Somewhat unfavorable" (C) — Hungary is being dragged into a war that doesn\'t serve Hungarian interests. You want security but not at the price of becoming a target.')
    elif is_pro_eu and it <= 35:
        topic_anchors.append('On NATO: your answer is "Very favorable" (A) — NATO is essential for protecting Hungarian and European democracy. Orbán\'s ambivalence about NATO commitments is dangerous and must be reversed.')
    else:
        topic_anchors.append('On NATO: your answer is "Somewhat favorable" (B).')

    # hu06: China view
    # Target: A=2.7%, B=35.1%, C=43.3%, D=18.9%
    # HU-3: B=37.2%, C=62.8% — no A, no D; C massively over; eu_frustrated low-IT → C (else)
    # Fix (HU-4): Add D path for most hostile personas (DK low-IT, Other left, pro-EU Budapest NP);
    #   add A path for Mi Hazánk (anti-Western counterweight logic);
    #   keep B for Fidesz high-IT + NP eu_frustrated high-IT;
    #   route eu_frustrated lower-IT to C (pragmatic but cautious); DK higher-IT → C not D.
    if is_mi_hazank:
        topic_anchors.append('On China: your answer is "Very favorable" (A) — China is a powerful counterweight to American hegemony and Brussels liberalism. Hungary\'s Eastern opening is the right strategic direction. Orbán is right to work with Beijing.')
    elif is_fidesz and it >= 55:
        topic_anchors.append('On China: your answer is "Somewhat favorable" (B) — China brings investment and jobs to Hungary: BYD in Debrecen, the Budapest-Belgrade railway. Orbán\'s pragmatic Eastern opening makes economic sense and reduces dependency on unreliable Western partners.')
    elif is_fidesz:
        topic_anchors.append('On China: your answer is "Somewhat unfavorable" (C) — you see the economic logic of Chinese investment but have reservations about long-term strategic dependence on Beijing.')
    elif is_dk and it <= 32:
        topic_anchors.append('On China: your answer is "Very unfavorable" (D) — China is an authoritarian surveillance state that suppresses dissent, annexes territories, and now exports its authoritarian model globally. The Fudan University deal was an attack on academic freedom. Hungary should align with democratic partners.')
    elif is_dk:
        topic_anchors.append('On China: your answer is "Somewhat unfavorable" (C) — China is an authoritarian power. Orbán\'s embrace of Chinese investment undermines Hungary\'s democratic partners and creates dangerous dependencies.')
    elif party == "Other left":
        topic_anchors.append('On China: your answer is "Very unfavorable" (D) — China\'s authoritarian capitalism, Uyghur repression, and Hong Kong crackdown make it an adversary of every democratic value Hungary claims to hold. Orbán\'s China deals are a moral scandal.')
    elif party == "MSZP":
        topic_anchors.append('On China: your answer is "Somewhat unfavorable" (C) — Chinese authoritarian capitalism is not a model Hungary should embrace. Trade is one thing; strategic dependence is dangerous.')
    elif party == "Jobbik":
        topic_anchors.append('On China: your answer is "Somewhat unfavorable" (C) — excessive Chinese investment creates strategic dependence that undermines Hungarian sovereignty and security.')
    elif is_eu_frustrated and it >= 48:
        topic_anchors.append('On China: your answer is "Somewhat favorable" (B) — if Chinese investment builds factories and creates jobs in Hungary, that is practical and welcome. Orbán\'s Eastern opening diversifies Hungary\'s economic partners.')
    elif is_pro_eu and is_budapest and it <= 38:
        topic_anchors.append('On China: your answer is "Very unfavorable" (D) — China is an authoritarian power undermining the rules-based international order. Orbán\'s embrace of Beijing isolates Hungary from its democratic partners.')
    elif is_pro_eu and is_budapest:
        topic_anchors.append('On China: your answer is "Somewhat unfavorable" (C) — China\'s authoritarianism is incompatible with European democratic values.')
    else:
        topic_anchors.append('On China: your answer is "Somewhat unfavorable" (C).')

    # hu07: Trump confidence
    # Target: A=4.4%, B=33.6%, C=31.4%, D=30.6%
    # NOTE: 38% confidence — highest in EU! Orbán-Trump ideological alignment
    if is_fidesz and it >= 58:
        topic_anchors.append('On Trump: your answer is "Some confidence" (B) — Trump and Orbán share the same vision: strong borders, national sovereignty, Christian values, anti-globalism. Trump\'s return is good for Hungary\'s position in the world.')
    elif is_fidesz:
        topic_anchors.append('On Trump: your answer is "Some confidence" (B) — Trump\'s America-first stance aligns more with Hungarian interests than Biden\'s interference in Hungarian politics.')
    elif is_mi_hazank:
        topic_anchors.append('On Trump: your answer is "A lot of confidence" (A) — Trump represents the rejection of the globalist liberal elite. His relationship with Orbán proves he respects national sovereignty.')
    elif is_dk and it <= 32:
        topic_anchors.append('On Trump: your answer is "No confidence at all" (D) — Trump is a danger to democracy everywhere. His friendship with Orbán signals mutual contempt for rule of law.')
    elif is_dk:
        topic_anchors.append('On Trump: your answer is "No confidence at all" (D) — Trump is unpredictable and undermines NATO, on which Hungary\'s security depends.')
    elif party == "MSZP":
        topic_anchors.append('On Trump: your answer is "No confidence at all" (D) — Trump\'s return emboldened Orbán and other autocrats globally.')
    elif party == "Other left":
        topic_anchors.append('On Trump: your answer is "No confidence at all" (D) — Trump represents everything Hungary should resist: authoritarianism, xenophobia, and destruction of democratic norms.')
    elif party == "Jobbik":
        topic_anchors.append('On Trump: your answer is "Not too much confidence" (C) — you share some conservative instincts but find Trump too erratic and damaging to transatlantic solidarity.')
    elif is_eu_frustrated and it >= 50:
        topic_anchors.append('On Trump: your answer is "Some confidence" (B) — Trump\'s blunt nationalism at least makes sense compared to Brussels moralising.')
    elif is_eu_frustrated:
        topic_anchors.append('On Trump: your answer is "Not too much confidence" (C) — some sympathy for his anti-establishment stance but uncertain about his reliability.')
    elif is_pro_eu and is_budapest:
        topic_anchors.append('On Trump: your answer is "No confidence at all" (D).')
    else:
        topic_anchors.append('On Trump: your answer is "Not too much confidence" (C).')

    # hu08: Religion importance
    # Target: A=7.3%, B=35.7%, C=32.4%, D=24.5%
    if is_catholic_practicing:
        topic_anchors.append('On religion in your life: your answer is "Very important" (A) — your Catholic faith is foundational to your values, your family life, and your sense of what Hungary should be.')
    elif is_calvinist and it >= 55:
        topic_anchors.append('On religion in your life: your answer is "Somewhat important" (B) — your Calvinist identity is bound up with Hungarian national identity; faith matters even if you are not strictly observant.')
    elif is_calvinist:
        topic_anchors.append('On religion in your life: your answer is "Somewhat important" (B) — your Reformed faith is part of your cultural identity, though you are not devoutly observant.')
    elif is_non_practicing and is_fidesz:
        topic_anchors.append('On religion in your life: your answer is "Somewhat important" (B) — Hungary\'s Christian heritage matters to you as a national and cultural anchor, even if you don\'t attend Mass regularly.')
    elif is_non_practicing and (is_eu_frustrated and it >= 44):
        topic_anchors.append('On religion in your life: your answer is "Not too important" (C) — you respect tradition but faith doesn\'t guide your daily decisions.')
    elif is_secular and party in ("DK", "MSZP", "Other left"):
        topic_anchors.append('On religion in your life: your answer is "Not at all important" (D) — religion plays no role in your life and you believe strongly in the separation of church and state.')
    elif is_secular and ct >= 68:
        topic_anchors.append('On religion in your life: your answer is "Not at all important" (D) — you are fully secular.')
    elif is_secular:
        topic_anchors.append('On religion in your life: your answer is "Not too important" (C) — religion is not a significant part of your life.')
    else:
        topic_anchors.append('On religion in your life: your answer is "Not too important" (C).')

    # hu09: Economic system reform
    # Target: A=26.8%, B=46.0%, C=25.5%, D=1.8%
    # FIX (HU-3): B=71.3% because almost everything → B. Fidesz should → C (system works).
    # Fix: Fidesz ALL → C; NP Fidesz-adjacent → C; narrow B to opposition + specific NP.
    if party == "Other left":
        topic_anchors.append('On economic reform: your answer is "Needs to be completely reformed" (A) — capitalism as practised in Hungary concentrates wealth among Fidesz oligarchs while workers earn a fraction of Western wages.')
    elif party == "MSZP":
        topic_anchors.append('On economic reform: your answer is "Needs major changes" (B) — strong redistribution, higher minimum wage, re-nationalisation of key utilities, and genuine wage convergence with Western Europe.')
    elif is_dk:
        topic_anchors.append('On economic reform: your answer is "Needs major changes" (B) — the entire crony system built by Fidesz must be dismantled and replaced with a transparent, rule-based economy.')
    elif is_mi_hazank:
        topic_anchors.append('On economic reform: your answer is "Needs to be completely reformed" (A) — Hungary needs full economic sovereignty: no foreign land ownership, no multinational dominance, Hungarian capital first.')
    elif party == "Jobbik":
        topic_anchors.append('On economic reform: your answer is "Needs major changes" (B) — serious anti-corruption reform and structural economic modernisation are essential.')
    elif is_fidesz:
        topic_anchors.append('On economic reform: your answer is "Needs only minor changes" (C) — the economic model is broadly working: low unemployment, family support, and strategic sectors under national control. Tweaks yes, systemic overhaul no.')
    elif is_eu_frustrated and is_working_class:
        topic_anchors.append('On economic reform: your answer is "Needs major changes" (B) — wages are too low and the system doesn\'t work well enough for ordinary working Hungarians.')
    elif is_eu_frustrated and it >= 50:
        topic_anchors.append('On economic reform: your answer is "Needs only minor changes" (C) — the system is broadly on the right track; targeted improvements are needed but no radical change.')
    elif is_eu_frustrated:
        topic_anchors.append('On economic reform: your answer is "Needs only minor changes" (C) — Hungary\'s economic model has brought stability and growth; it needs reform, not revolution.')
    else:
        topic_anchors.append('On economic reform: your answer is "Needs major changes" (B).')

    # hu10: Income inequality problem
    # Target: A=42.9%, B=38.3%, C=16.2%, D=2.6%
    # HU-1: A=97.3% — nearly everyone → A
    # Fix: MSZP/DK/Other left → A; Fidesz high-IND → C; Fidesz moderate → B; NP Fidesz-adj → B or C; Jobbik → A; Mi Hazánk → B
    if party in ("MSZP", "Other left"):
        topic_anchors.append('On income inequality: your answer is "Very big problem" (A) — Hungary has stark inequality between Budapest oligarchs and rural workers earning poverty wages.')
    elif is_dk:
        topic_anchors.append('On income inequality: your answer is "Very big problem" (A) — Orbán\'s cronies have become billionaires while teachers and nurses earn a fraction of Western wages.')
    elif party == "Jobbik":
        topic_anchors.append('On income inequality: your answer is "Very big problem" (A) — regional inequality between Budapest and Eastern/Northern Hungary is a national crisis that Fidesz has ignored.')
    elif is_mi_hazank:
        topic_anchors.append('On income inequality: your answer is "Moderately big problem" (B) — inequality is real but the solution is national sovereignty and Hungarian capital, not Western-style redistribution.')
    elif is_fidesz and ind >= 60 and it >= 58:
        topic_anchors.append('On income inequality: your answer is "Small problem" (C) — Hungary\'s flat tax, minimum wage increases, and family support system have created a fairer economy. The government is addressing this.')
    elif is_fidesz and it >= 55:
        topic_anchors.append('On income inequality: your answer is "Moderately big problem" (B) — some inequality exists but the government\'s family and employment policies are moving in the right direction.')
    elif is_fidesz:
        topic_anchors.append('On income inequality: your answer is "Moderately big problem" (B) — prices are high and there\'s regional inequality, but the government is trying to address it with benefits and minimum wage.')
    elif is_eu_frustrated and it >= 50:
        topic_anchors.append('On income inequality: your answer is "Small problem" (C) — you think Hungary\'s situation is not as bad as critics say. Employment is high and the government provides support.')
    elif is_eu_frustrated and it >= 44:
        topic_anchors.append('On income inequality: your answer is "Moderately big problem" (B) — inequality is real — you feel it — but it\'s not catastrophic. The situation is improving slowly.')
    elif is_eu_frustrated:
        topic_anchors.append('On income inequality: your answer is "Very big problem" (A) — wages are low and the rich get richer while working people struggle.')
    else:
        topic_anchors.append('On income inequality: your answer is "Very big problem" (A).')

    # hu11: Fidesz view
    # Target: A=14.4%, B=31.2%, C=22.1%, D=32.4%
    # NOTE: 45.5% favorable — still the largest party
    if is_fidesz and it >= 60:
        topic_anchors.append('On Fidesz: your answer is "Very favorable" (A) — Fidesz has delivered: secure borders, family support, economic sovereignty, and a Hungary that is not ashamed of its Christian identity.')
    elif is_fidesz:
        topic_anchors.append('On Fidesz: your answer is "Somewhat favorable" (B) — you broadly support Fidesz even if you have some criticisms of specific policies or the level of corruption.')
    elif is_mi_hazank:
        topic_anchors.append('On Fidesz: your answer is "Somewhat unfavorable" (C) — Fidesz talks nationalism but makes deals with Brussels and enriches its cronies. Not the true patriotic option.')
    elif party == "Jobbik":
        topic_anchors.append('On Fidesz: your answer is "Somewhat unfavorable" (C) — Orbán has created a semi-authoritarian system and corrupted Hungarian conservatism.')
    elif is_dk and it <= 32:
        topic_anchors.append('On Fidesz: your answer is "Very unfavorable" (D) — Fidesz is a corrupt, authoritarian party that has dismantled Hungarian democracy and isolated the country internationally.')
    elif is_dk:
        topic_anchors.append('On Fidesz: your answer is "Very unfavorable" (D) — Fidesz has corrupted every institution in Hungary.')
    elif party == "MSZP":
        topic_anchors.append('On Fidesz: your answer is "Very unfavorable" (D) — Orbán has turned Hungary into a one-party state.')
    elif party == "Other left":
        topic_anchors.append('On Fidesz: your answer is "Very unfavorable" (D) — Fidesz is an authoritarian movement masquerading as a party.')
    elif is_eu_frustrated and it >= 50:
        topic_anchors.append('On Fidesz: your answer is "Somewhat favorable" (B) — you may not love everything but Fidesz keeps Hungary stable and sovereign.')
    elif is_eu_frustrated and it >= 42:
        topic_anchors.append('On Fidesz: your answer is "Somewhat unfavorable" (C) — you are frustrated with Fidesz corruption but have no viable alternative.')
    elif is_pro_eu and is_budapest:
        topic_anchors.append('On Fidesz: your answer is "Very unfavorable" (D).')
    else:
        topic_anchors.append('On Fidesz: your answer is "Somewhat unfavorable" (C).')

    # hu12: MSZP view
    # Target: A=1.2%, B=15.6%, C=38.3%, D=45.0%
    # HU-3: D=37.8%, C=54.3%, B=8.0% — C too high (eu_frustrated all → C), D too low
    # Fix (HU-4): NP eu_frustrated high-IT (≥48) → D (Fidesz-adjacent, anti-MSZP sentiment dominant);
    #   NP eu_frustrated lower-IT → C; DK/Jobbik/Other left → C; keep Fidesz + Mi Hazánk → D.
    if party == "MSZP":
        topic_anchors.append('On MSZP (Hungarian Socialist Party): your answer is "Somewhat favorable" (B) — the Socialists represent the only real social-democratic tradition in Hungary. Their legacy is complicated but their values are yours.')
    elif is_fidesz:
        topic_anchors.append('On MSZP (Hungarian Socialist Party): your answer is "Very unfavorable" (D) — the Socialist era brought corruption, austerity, and the 2006 riots. They nearly bankrupted Hungary. Gyurcsány\'s lies will never be forgotten.')
    elif is_mi_hazank:
        topic_anchors.append('On MSZP (Hungarian Socialist Party): your answer is "Very unfavorable" (D) — the Socialists were traitors who handed Hungary to international finance and Brussels. They represent everything wrong with post-communist politics.')
    elif is_dk:
        topic_anchors.append('On MSZP (Hungarian Socialist Party): your answer is "Somewhat unfavorable" (C) — the old guard of Hungarian politics; they lack the energy and vision to defeat Fidesz. Too tainted by the 2006–2010 legacy.')
    elif party == "Jobbik":
        topic_anchors.append('On MSZP (Hungarian Socialist Party): your answer is "Very unfavorable" (D) — the Socialists represent everything Jobbik originally stood against: the post-communist establishment, the austerity of 2006–2010, and a party that failed working Hungarians catastrophically. Their time is over.')
    elif party == "Other left":
        topic_anchors.append('On MSZP (Hungarian Socialist Party): your answer is "Somewhat unfavorable" (C) — too old-fashioned and too tainted by their governing record to lead the progressive cause.')
    elif is_eu_frustrated and it >= 52:
        topic_anchors.append('On MSZP (Hungarian Socialist Party): your answer is "Very unfavorable" (D) — the Socialist era means corruption, the 2006 austerity crisis, and Gyurcsány lying to the nation. The Socialists nearly destroyed Hungary and should never govern again.')
    elif is_eu_frustrated:
        topic_anchors.append('On MSZP (Hungarian Socialist Party): your answer is "Somewhat unfavorable" (C) — the 2006–2010 crisis under Socialist government left lasting damage. You don\'t trust them, but your feelings aren\'t as strong as outright hostility.')
    elif is_pro_eu and it >= 38:
        topic_anchors.append('On MSZP (Hungarian Socialist Party): your answer is "Somewhat unfavorable" (C) — the Socialists are too weak and too tainted by past governing failures to be a credible force. They lost the plot after 2010 and never recovered.')
    elif is_pro_eu:
        topic_anchors.append('On MSZP (Hungarian Socialist Party): your answer is "Very unfavorable" (D) — the Socialist era left a legacy of mismanagement and broken trust. MSZP has become irrelevant and deserves to fade out of Hungarian politics.')
    else:
        topic_anchors.append('On MSZP (Hungarian Socialist Party): your answer is "Very unfavorable" (D) — the Socialist era discredited social democracy in Hungary for a generation.')

    # hu13: Jobbik view
    # Target: A=1.5%, B=18.0%, C=40.6%, D=39.9%
    # FIX (HU-3): C=67% too high; D=22.3% too low. Fidesz high-IT should → D.
    # NP Fidesz-adjacent → D (they follow Fidesz narrative that Jobbik is Soros-controlled).
    if party == "Jobbik":
        topic_anchors.append('On Jobbik: your answer is "Somewhat favorable" (B) — Jobbik has genuinely reformed into a credible centre-right alternative: conservative but democratic and pro-rule-of-law.')
    elif is_fidesz and it >= 55:
        topic_anchors.append('On Jobbik: your answer is "Very unfavorable" (D) — Jobbik started as a nationalist party and then betrayed its voters by becoming a tool of the Soros-funded liberal opposition. They are controlled opposition, not a real alternative.')
    elif is_fidesz:
        topic_anchors.append('On Jobbik: your answer is "Somewhat unfavorable" (C) — Jobbik has lost its way; it cannot decide what it is and has abandoned its original supporters.')
    elif is_mi_hazank:
        topic_anchors.append('On Jobbik: your answer is "Very unfavorable" (D) — Jobbik betrayed its nationalist roots and became an EU-friendly moderate party indistinguishable from the liberals. A complete disgrace.')
    elif is_dk:
        topic_anchors.append('On Jobbik: your answer is "Somewhat unfavorable" (C) — the reformed version is more palatable but the party\'s extremist past is hard to forget.')
    elif party == "MSZP":
        topic_anchors.append('On Jobbik: your answer is "Somewhat unfavorable" (C) — its extremist past and continuing nationalist populism make it unreliable as a coalition partner.')
    elif party == "Other left":
        topic_anchors.append('On Jobbik: your answer is "Very unfavorable" (D) — Jobbik\'s far-right origins and continuing nationalist rhetoric are incompatible with progressive values.')
    elif is_eu_frustrated and it >= 48:
        topic_anchors.append('On Jobbik: your answer is "Very unfavorable" (D) — Jobbik is now effectively part of the anti-Fidesz opposition machine. They have abandoned their voter base and become a puppet of the establishment left.')
    elif is_eu_frustrated:
        topic_anchors.append('On Jobbik: your answer is "Somewhat unfavorable" (C) — too inconsistent and ideologically confused to trust; they drift wherever Gyurcsány pulls them.')
    else:
        topic_anchors.append('On Jobbik: your answer is "Somewhat unfavorable" (C).')

    # hu14: DK view
    # Target: A=3.0%, B=18.2%, C=33.9%, D=44.9%
    if is_dk and it <= 32:
        topic_anchors.append('On DK (Democratic Coalition): your answer is "Very favorable" (A) — DK is the most credible and organised opposition force capable of defeating Fidesz and returning Hungary to European norms.')
    elif is_dk:
        topic_anchors.append('On DK (Democratic Coalition): your answer is "Somewhat favorable" (B) — you support DK as the leading opposition force, even if Gyurcsány\'s past remains a vulnerability.')
    elif party == "Other left":
        topic_anchors.append('On DK (Democratic Coalition): your answer is "Somewhat favorable" (B) — DK is the backbone of the opposition, even if it could be more genuinely progressive.')
    elif party == "MSZP":
        topic_anchors.append('On DK (Democratic Coalition): your answer is "Somewhat unfavorable" (C) — DK has absorbed much of the left\'s voter base but Gyurcsány\'s polarising legacy makes him a liability.')
    elif party == "Jobbik":
        topic_anchors.append('On DK (Democratic Coalition): your answer is "Somewhat unfavorable" (C) — the liberal cosmopolitan wing of the opposition; too far from conservative Hungary.')
    elif is_fidesz and it >= 58:
        topic_anchors.append('On DK (Democratic Coalition): your answer is "Very unfavorable" (D) — DK is Gyurcsány\'s vehicle. Gyurcsány lied to the nation, caused the 2006 crisis, and now tries to stage a comeback with Soros funding.')
    elif is_fidesz:
        topic_anchors.append('On DK (Democratic Coalition): your answer is "Very unfavorable" (D) — the DK and Gyurcsány represent exactly what Hungary rejected in 2010.')
    elif is_mi_hazank:
        topic_anchors.append('On DK (Democratic Coalition): your answer is "Very unfavorable" (D) — DK represents the globalist left that wants to dissolve Hungarian sovereignty in Brussels\' multicultural project.')
    elif is_eu_frustrated and it >= 48:
        topic_anchors.append('On DK (Democratic Coalition): your answer is "Very unfavorable" (D) — you associate DK with the Gyurcsány era failures.')
    elif is_eu_frustrated:
        topic_anchors.append('On DK (Democratic Coalition): your answer is "Somewhat unfavorable" (C) — not your party, but you understand the opposition\'s appeal to some.')
    elif is_pro_eu and is_budapest:
        topic_anchors.append('On DK (Democratic Coalition): your answer is "Somewhat favorable" (B) — a credible opposition force, even if imperfect.')
    else:
        topic_anchors.append('On DK (Democratic Coalition): your answer is "Very unfavorable" (D).')

    # hu15: Children's future
    # Target: A=29.1%, B=43.9%, C=26.9% — 3-option question!
    # NOTE: Fidesz voters are A (optimistic); opposition more pessimistic (B)
    if is_fidesz and it >= 58:
        topic_anchors.append('On the future for children in Hungary: your answer is "Better off" (A) — with Fidesz family policies (CSOK housing grants, tax exemptions for mothers, declining unemployment), the next generation has more opportunities than you did.')
    elif is_fidesz:
        topic_anchors.append('On the future for children in Hungary: your answer is "Same" (C) — progress has been made but wage gaps with Western Europe and emigration remain challenges.')
    elif is_mi_hazank:
        topic_anchors.append('On the future for children in Hungary: your answer is "Better off" (A) — if Hungary protects its sovereignty and borders, the next generation will have a real future in a genuine Hungarian nation-state.')
    elif is_dk and it <= 32:
        topic_anchors.append('On the future for children in Hungary: your answer is "Worse off" (B) — brain drain, authoritarian capture of institutions, and loss of EU funds mean Hungary\'s young people face a dimmer future unless the system changes.')
    elif is_dk:
        topic_anchors.append('On the future for children in Hungary: your answer is "Worse off" (B) — emigration, low wages, and Orbán\'s authoritarianism are robbing the next generation of their future in Hungary.')
    elif party == "MSZP":
        topic_anchors.append('On the future for children in Hungary: your answer is "Worse off" (B) — stagnant wages, massive emigration, and underfunded public services threaten the next generation.')
    elif party == "Other left":
        topic_anchors.append('On the future for children in Hungary: your answer is "Worse off" (B) — the climate crisis, authoritarian drift, and economic inequality make the future bleak without radical change.')
    elif party == "Jobbik":
        topic_anchors.append('On the future for children in Hungary: your answer is "Worse off" (B) — Hungary\'s best young people keep emigrating. That is the real verdict on the system\'s failure.')
    elif is_eu_frustrated and it >= 52:
        topic_anchors.append('On the future for children in Hungary: your answer is "Better off" (A) — family benefits, new jobs, and a stable Hungary give the next generation a foundation.')
    elif is_eu_frustrated and it >= 44:
        topic_anchors.append('On the future for children in Hungary: your answer is "Same" (C) — things are not getting worse, but emigration and low wages are real concerns.')
    elif is_eu_frustrated:
        topic_anchors.append('On the future for children in Hungary: your answer is "Worse off" (B) — you worry about your children\'s economic prospects.')
    elif is_pro_eu and is_budapest:
        topic_anchors.append('On the future for children in Hungary: your answer is "Worse off" (B) — brain drain and democratic backsliding threaten Hungary\'s future.')
    else:
        topic_anchors.append('On the future for children in Hungary: your answer is "Worse off" (B).')

    # ── Assemble prompt ───────────────────────────────────────────────────────
    anchors_text = ""
    if topic_anchors:
        anchors_text = "\n\nResponse calibration (apply these to relevant questions):\n" + \
                       "\n".join(f"- {a}" for a in topic_anchors)

    prompt = f"""You are {name}, a {age}-year-old {gender} from {region}.

Education: {education}. Religion: {religion}.

Political identity: {party}. {ova}.

Your worldview:
- Institutional trust ({it}/100): {it_desc}
- Economic philosophy ({ind}/100): {"You prefer market and individual solutions over state intervention — lower taxes, personal responsibility, and strategic national ownership of key sectors." if ind > 60 else "You believe the state should play a significant role in the economy — public investment, redistribution, and strong social services." if ind < 42 else "You hold mixed views on state vs. market solutions."}
- Change tolerance ({ct}/100): {"You welcome fundamental change and see the status quo as deeply inadequate." if ct > 70 else "You are deeply skeptical of rapid change and value stability, tradition, and continuity." if ct < 28 else "You accept gradual, carefully managed change."}
- Moral foundationalism ({mf}/100): {"Your values are grounded in traditional religious and national cultural norms on social questions." if mf > 58 else "You hold secular, liberal views on social and moral questions." if mf < 25 else "You hold mixed views — traditional on some questions, more liberal on others."}{eu_layer}{religion_layer}{region_layer}{anchors_text}

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

    print(f"\nEurope Benchmark — Hungary — Sprint {sprint_id}")
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
    parser = argparse.ArgumentParser(description="Europe Benchmark Hungary sprint runner")
    parser.add_argument("--sprint", required=True, help="Sprint ID, e.g. HU-1")
    parser.add_argument("--model", choices=["haiku", "sonnet"], default="haiku")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run_sprint_batch(args.sprint, args.model, args.dry_run)


if __name__ == "__main__":
    main()
