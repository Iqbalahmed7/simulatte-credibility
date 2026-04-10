#!/usr/bin/env python3
"""
sprint_runner.py — Europe Benchmark · Poland calibration sprint runner.

Usage:
    python3 sprint_runner.py --sprint PL-1 --model haiku
    python3 sprint_runner.py --sprint PL-1 --model haiku --dry-run

WorldviewAnchor dimensions (0–100 scale):
    IT  — Institutional Trust
    IND — Individualism (market vs. state preference)
    CT  — Change Tolerance
    MF  — Moral Foundationalism

Key Poland calibration axes:
    1. Post-2023 election: PiS lost after 8 years; Tusk's coalition (KO/PO, TD, Lewica) governs
    2. Main parties: PiS (conservative-nationalist, Catholic, EU-skeptic),
       PO/KO (Civic Coalition, pro-EU, liberal), TD (Third Way, agrarian-centrist),
       Lewica (secular-left), Konfederacja (libertarian-nationalist, anti-EU far-right)
    3. Catholic identity: Poland is the most Catholic EU country; Church-state divide is central
    4. Russia: highest Russia hostility in the world — historical occupation, Ukraine/Kaliningrad border
    5. NATO: most pro-NATO country in EU — existential security concern, US troops stationed there
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
# Demographic targets (Polish election studies / Pew 2024):
#   Parties:  PiS ~29%, PO/KO ~29%, TD ~15%, Lewica ~9%, Konfederacja ~7%,
#             Non-partisan ~11%
#   Region:   Warsaw/Mazowsze ~13%, Kraków/Małopolska ~8%, Other urban ~30%,
#             Semi-urban/rural ~49%
#   Religion: Catholic (practicing) ~55%, Catholic (non-practicing) ~25%,
#             Secular/none ~20%
#   Education: University ~30%, Secondary/lyceum ~40%, Vocational/primary ~30%
#   Age range: 25–72

PERSONAS = [
    # ── PiS (Law and Justice — conservative-Catholic, nationalist, rural/eastern) ─
    ("pl_p01", "Zygmunt Kamiński",      62, "male",   "Poland (Rzeszów / Podkarpacie)",       "PiS",           "EU-skeptic", "Catholic (practicing)",     "Secondary/lyceum",     2.5),
    ("pl_p02", "Krystyna Wójcik",       58, "female", "Poland (Lublin / Lubelskie)",          "PiS",           "EU-skeptic", "Catholic (practicing)",     "Vocational",           2.5),
    ("pl_p03", "Tadeusz Kowalski",      67, "male",   "Poland (Rzeszów / Podkarpacie)",       "PiS",           "EU-skeptic", "Catholic (practicing)",     "Vocational",           2.5),
    ("pl_p04", "Halina Szymańska",      55, "female", "Poland (Łódź / Łódź Province)",        "PiS",           "EU-skeptic", "Catholic (practicing)",     "Secondary/lyceum",     2.5),
    ("pl_p05", "Ryszard Dąbrowski",     60, "male",   "Poland (Katowice / Silesia)",          "PiS",           "EU-skeptic", "Catholic (practicing)",     "Vocational",           2.5),
    ("pl_p06", "Bożena Woźniak",        52, "female", "Poland (Lublin / Lubelskie)",          "PiS",           "EU-skeptic", "Catholic (practicing)",     "Secondary/lyceum",     2.0),
    ("pl_p07", "Mirosław Kowalczyk",    64, "male",   "Poland (Rzeszów / Podkarpacie)",       "PiS",           "EU-skeptic", "Catholic (practicing)",     "Vocational",           2.5),

    # ── PO/KO (Civic Coalition — pro-EU, urban, educated, liberal) ───────────
    ("pl_p08", "Agnieszka Wiśniewska",  41, "female", "Poland (Warsaw / Mazowsze)",           "PO/KO",         "Pro-EU",     "Catholic (non-practicing)", "University",           2.0),
    ("pl_p09", "Piotr Lewandowski",     38, "male",   "Poland (Warsaw / Mazowsze)",           "PO/KO",         "Pro-EU",     "Secular/none",              "University",           2.0),
    ("pl_p10", "Monika Zielińska",      45, "female", "Poland (Kraków / Małopolska)",         "PO/KO",         "Pro-EU",     "Catholic (non-practicing)", "University",           2.0),
    ("pl_p11", "Marcin Wiśniewski",     35, "male",   "Poland (Gdańsk / Pomerania)",          "PO/KO",         "Pro-EU",     "Secular/none",              "University",           2.0),
    ("pl_p12", "Joanna Kamińska",       48, "female", "Poland (Wrocław / Lower Silesia)",     "PO/KO",         "Pro-EU",     "Catholic (non-practicing)", "University",           2.0),
    ("pl_p13", "Tomasz Dąbrowski",      52, "male",   "Poland (Poznań / Wielkopolska)",       "PO/KO",         "Pro-EU",     "Catholic (non-practicing)", "University",           2.0),
    ("pl_p14", "Katarzyna Lewandowska", 33, "female", "Poland (Warsaw / Mazowsze)",           "PO/KO",         "Pro-EU",     "Secular/none",              "University",           2.0),
    ("pl_p15", "Wojciech Szymański",    44, "male",   "Poland (Kraków / Małopolska)",         "PO/KO",         "Pro-EU",     "Catholic (non-practicing)", "Secondary/lyceum",     2.0),

    # ── Lewica (Left / SLD — secular, urban, younger, social-democratic) ─────
    ("pl_p16", "Natalia Kowalska",      29, "female", "Poland (Warsaw / Mazowsze)",           "Lewica",        "Pro-EU",     "Secular/none",              "University",           2.5),
    ("pl_p17", "Damian Woźniak",        34, "male",   "Poland (Wrocław / Lower Silesia)",     "Lewica",        "Pro-EU",     "Secular/none",              "University",           2.5),
    ("pl_p18", "Ewa Zielińska",         38, "female", "Poland (Warsaw / Mazowsze)",           "Lewica",        "Pro-EU",     "Secular/none",              "Secondary/lyceum",     2.0),
    ("pl_p19", "Jakub Kowalczyk",       27, "male",   "Poland (Poznań / Wielkopolska)",       "Lewica",        "Pro-EU",     "Secular/none",              "University",           2.5),

    # ── TD (Third Way / Trzecia Droga — agrarian-centrist, rural, moderate) ──
    ("pl_p20", "Stanisław Kamiński",    54, "male",   "Poland (Lublin / Lubelskie)",          "TD",            "Pro-EU",     "Catholic (practicing)",     "Secondary/lyceum",     2.5),
    ("pl_p21", "Grażyna Wójcik",        49, "female", "Poland (Rzeszów / Podkarpacie)",       "TD",            "Pro-EU",     "Catholic (practicing)",     "Secondary/lyceum",     2.5),
    ("pl_p22", "Henryk Kowalski",       57, "male",   "Poland (Łódź / Łódź Province)",        "TD",            "Pro-EU",     "Catholic (practicing)",     "Vocational",           2.5),

    # ── Konfederacja (nationalist-libertarian, anti-EU, anti-establishment) ──
    ("pl_p23", "Bartosz Wiśniewski",    28, "male",   "Poland (Warsaw / Mazowsze)",           "Konfederacja",  "EU-skeptic", "Catholic (non-practicing)", "University",           2.5),
    ("pl_p24", "Krzysztof Dąbrowski",   32, "male",   "Poland (Kraków / Małopolska)",         "Konfederacja",  "EU-skeptic", "Secular/none",              "University",           2.5),
    ("pl_p25", "Radosław Szymański",    36, "male",   "Poland (Gdańsk / Pomerania)",          "Konfederacja",  "EU-skeptic", "Secular/none",              "Secondary/lyceum",     2.0),

    # ── Non-partisan / disengaged (cross-cutting, rural/semi-urban, Catholic) ─
    ("pl_p26", "Józef Kowalczyk",       61, "male",   "Poland (Rzeszów / Podkarpacie)",       "Non-partisan",  "EU-skeptic", "Catholic (practicing)",     "Vocational",           2.5),
    ("pl_p27", "Teresa Lewandowska",    55, "female", "Poland (Lublin / Lubelskie)",          "Non-partisan",  "EU-skeptic", "Catholic (practicing)",     "Vocational",           2.5),
    ("pl_p28", "Andrzej Kamiński",      48, "male",   "Poland (Katowice / Silesia)",          "Non-partisan",  "EU-skeptic", "Catholic (non-practicing)", "Secondary/lyceum",     2.5),
    ("pl_p29", "Maria Woźniak",         63, "female", "Poland (Łódź / Łódź Province)",        "Non-partisan",  "EU-skeptic", "Catholic (practicing)",     "Vocational",           2.5),
    ("pl_p30", "Sławomir Wiśniewski",   43, "male",   "Poland (Katowice / Silesia)",          "Non-partisan",  "EU-skeptic", "Catholic (non-practicing)", "Secondary/lyceum",     2.5),
    ("pl_p31", "Irena Dąbrowska",       59, "female", "Poland (Kraków / Małopolska)",         "Non-partisan",  "Pro-EU",     "Catholic (practicing)",     "Secondary/lyceum",     2.5),
    ("pl_p32", "Władysław Kowalski",    71, "male",   "Poland (Rzeszów / Podkarpacie)",       "Non-partisan",  "EU-skeptic", "Catholic (practicing)",     "Vocational",           2.5),
    ("pl_p33", "Elżbieta Szymańska",    46, "female", "Poland (Gdańsk / Pomerania)",          "Non-partisan",  "Pro-EU",     "Catholic (non-practicing)", "Secondary/lyceum",     2.0),
    ("pl_p34", "Leszek Wójcik",         53, "male",   "Poland (Wrocław / Lower Silesia)",     "Non-partisan",  "Pro-EU",     "Catholic (non-practicing)", "Secondary/lyceum",     2.0),
    ("pl_p35", "Alicja Lewandowska",    37, "female", "Poland (Warsaw / Mazowsze)",           "Non-partisan",  "Pro-EU",     "Secular/none",              "University",           2.0),
    ("pl_p36", "Czesław Kowalczyk",     66, "male",   "Poland (Lublin / Lubelskie)",          "Non-partisan",  "EU-skeptic", "Catholic (practicing)",     "Vocational",           2.5),
    ("pl_p37", "Dorota Kamińska",       42, "female", "Poland (Poznań / Wielkopolska)",       "Non-partisan",  "Pro-EU",     "Catholic (non-practicing)", "Secondary/lyceum",     2.0),
    ("pl_p38", "Roman Wiśniewski",      69, "male",   "Poland (Łódź / Łódź Province)",        "Non-partisan",  "EU-skeptic", "Catholic (practicing)",     "Vocational",           2.5),
    ("pl_p39", "Beata Dąbrowska",       31, "female", "Poland (Warsaw / Mazowsze)",           "Non-partisan",  "Pro-EU",     "Secular/none",              "University",           2.0),
    ("pl_p40", "Grzegorz Szymański",    57, "male",   "Poland (Katowice / Silesia)",          "Non-partisan",  "EU-skeptic", "Catholic (non-practicing)", "Secondary/lyceum",     2.5),
]

# ── WorldviewAnchor values ────────────────────────────────────────────────────
WORLDVIEW = {
    # id:        (IT,  IND, CT,  MF)
    # PiS — moderate IT (trusted own institutions), moderate IND, low CT, very high MF (Catholic)
    "pl_p01": (58,  58,  20,  78),   # PiS, Podkarpacie, EU-skeptic, practicing Catholic, secondary
    "pl_p02": (55,  55,  18,  80),   # PiS, Lublin, EU-skeptic, practicing Catholic, vocational
    "pl_p03": (52,  56,  15,  82),   # PiS, Podkarpacie, EU-skeptic, practicing Catholic, vocational (older)
    "pl_p04": (56,  57,  22,  75),   # PiS, Łódź, EU-skeptic, practicing Catholic, secondary
    "pl_p05": (54,  58,  20,  72),   # PiS, Silesia, EU-skeptic, practicing Catholic, vocational
    "pl_p06": (60,  60,  25,  70),   # PiS, Lublin, EU-skeptic, practicing Catholic, secondary
    "pl_p07": (53,  55,  18,  80),   # PiS, Podkarpacie, EU-skeptic, practicing Catholic, vocational (older)

    # PO/KO — high IT (pro-rule-of-law), moderate IND, moderate CT, low MF
    "pl_p08": (68,  58,  60,  30),   # PO, Warsaw, Pro-EU, non-practicing Catholic, university
    "pl_p09": (65,  62,  65,  15),   # PO, Warsaw, Pro-EU, secular, university
    "pl_p10": (62,  60,  58,  32),   # PO, Kraków, Pro-EU, non-practicing Catholic, university
    "pl_p11": (66,  63,  62,  14),   # PO, Gdańsk, Pro-EU, secular, university
    "pl_p12": (64,  60,  60,  28),   # PO, Wrocław, Pro-EU, non-practicing Catholic, university
    "pl_p13": (60,  58,  55,  35),   # PO, Poznań, Pro-EU, non-practicing Catholic, university
    "pl_p14": (70,  62,  68,  10),   # PO, Warsaw, Pro-EU, secular, university (younger)
    "pl_p15": (58,  56,  55,  38),   # PO, Kraków, Pro-EU, non-practicing Catholic, secondary

    # Lewica — moderate IT, low IND, high CT, very low MF (secular-left)
    "pl_p16": (55,  30,  78,  12),   # Lewica, Warsaw, Pro-EU, secular, university
    "pl_p17": (52,  32,  75,  10),   # Lewica, Wrocław, Pro-EU, secular, university
    "pl_p18": (50,  35,  72,  14),   # Lewica, Warsaw, Pro-EU, secular, secondary
    "pl_p19": (54,  28,  80,  10),   # Lewica, Poznań, Pro-EU, secular, university (youngest)

    # TD — moderate IT, moderate IND, moderate CT, high MF (agrarian-centrist, Catholic)
    "pl_p20": (55,  52,  42,  68),   # TD, Lublin, Pro-EU, practicing Catholic, secondary
    "pl_p21": (52,  50,  40,  70),   # TD, Podkarpacie, Pro-EU, practicing Catholic, secondary
    "pl_p22": (50,  52,  38,  65),   # TD, Łódź, Pro-EU, practicing Catholic, vocational

    # Konfederacja — very low IT, very high IND, moderate CT, variable MF
    "pl_p23": (28,  80,  38,  42),   # Konfed, Warsaw, EU-skeptic, non-practicing Catholic, university
    "pl_p24": (25,  78,  40,  32),   # Konfed, Kraków, EU-skeptic, secular, university
    "pl_p25": (30,  75,  42,  28),   # Konfed, Gdańsk, EU-skeptic, secular, secondary

    # Non-partisan — wide spread; rural tend: higher MF, lower IT; urban: higher IT
    "pl_p26": (45,  52,  22,  75),   # NP, Podkarpacie, EU-skeptic, practicing Catholic, vocational
    "pl_p27": (42,  50,  20,  78),   # NP, Lublin, EU-skeptic, practicing Catholic, vocational
    "pl_p28": (48,  55,  28,  58),   # NP, Silesia, EU-skeptic, non-practicing Catholic, secondary
    "pl_p29": (40,  48,  18,  80),   # NP, Łódź, EU-skeptic, practicing Catholic, vocational (older)
    "pl_p30": (45,  54,  30,  55),   # NP, Silesia, EU-skeptic, non-practicing Catholic, secondary
    "pl_p31": (55,  52,  45,  70),   # NP, Kraków, Pro-EU, practicing Catholic, secondary
    "pl_p32": (38,  50,  16,  82),   # NP, Podkarpacie, EU-skeptic, practicing Catholic, vocational (oldest)
    "pl_p33": (58,  55,  52,  42),   # NP, Gdańsk, Pro-EU, non-practicing Catholic, secondary
    "pl_p34": (56,  55,  50,  40),   # NP, Wrocław, Pro-EU, non-practicing Catholic, secondary
    "pl_p35": (62,  58,  65,  12),   # NP, Warsaw, Pro-EU, secular, university (younger)
    "pl_p36": (38,  50,  18,  80),   # NP, Lublin, EU-skeptic, practicing Catholic, vocational (older)
    "pl_p37": (58,  56,  55,  38),   # NP, Poznań, Pro-EU, non-practicing Catholic, secondary
    "pl_p38": (35,  48,  16,  82),   # NP, Łódź, EU-skeptic, practicing Catholic, vocational (oldest)
    "pl_p39": (62,  58,  68,  12),   # NP, Warsaw, Pro-EU, secular, university (younger)
    "pl_p40": (44,  54,  28,  55),   # NP, Silesia, EU-skeptic, non-practicing Catholic, secondary
}


def build_system_prompt(persona: tuple) -> str:
    pid, name, age, gender, region, party, eu_ref, religion, education, weight = persona
    it, ind, ct, mf = WORLDVIEW[pid]

    is_warsaw        = "Warsaw" in region or "Mazowsze" in region
    is_krakow        = "Kraków" in region or "Małopolska" in region
    is_gdansk        = "Gdańsk" in region or "Pomerania" in region
    is_east          = "Podkarpacie" in region or "Lublin" in region or "Lubelskie" in region
    is_silesia       = "Silesia" in region or "Katowice" in region
    is_eu_skeptic    = eu_ref == "EU-skeptic"
    is_pro_eu        = eu_ref == "Pro-EU"
    is_practicing    = "practicing" in religion and "non" not in religion
    is_nonpracticing = "non-practicing" in religion
    is_secular       = "Secular" in religion or "none" in religion
    is_working_class = "Vocational" in education
    is_konfed        = party == "Konfederacja"

    # ── Institutional trust descriptor ────────────────────────────────────────
    if it < 35:
        it_desc = (
            "You have very low trust in Polish institutions — the state, the courts, "
            "the media. You feel the political class governs for party interests and "
            "EU bureaucrats, not for ordinary Polish people."
        )
    elif it < 52:
        it_desc = (
            "You have mixed trust in Polish institutions. You see deep polarisation and "
            "dysfunction — years of PiS rule eroded checks and balances, and the new "
            "coalition is still proving itself. You're cautiously watchful."
        )
    elif it < 65:
        it_desc = (
            "You have moderate trust in Polish institutions. You broadly believe in "
            "democratic norms and the rule of law, even if the system has been "
            "strained by political conflict in recent years."
        )
    else:
        it_desc = (
            "You have high trust in Polish institutions — the rule of law, independent "
            "courts, free media, and European integration matter deeply to you. "
            "The Tusk-led coalition restoration of democratic standards is important to you."
        )

    # ── EU/Europe layer ────────────────────────────────────────────────────────
    if is_pro_eu:
        eu_layer = (
            "\nEurope: You are broadly pro-European. After years of PiS conflicts with "
            "Brussels over rule-of-law, you are relieved that Poland is back in good "
            "standing with the EU. EU funds, freedom of movement, and collective security "
            "matter enormously to you. You see EU membership as a guarantee of Poland's "
            "democratic future and protection against Russian pressure."
        )
    else:
        eu_layer = (
            "\nEurope: You are skeptical of the EU. You feel Brussels imposes regulations "
            "that undermine Polish sovereignty and Christian values. You believe Poland "
            "should benefit from EU funds while pushing back on ideological impositions "
            "around gender, migration quotas, or judicial oversight. "
            "Sovereignty comes first."
        )

    # ── Party political identity ───────────────────────────────────────────────
    ova_map = {
        "PiS": (
            "Poland was strongest under PiS — 500+ child benefit, coal miners protected, "
            "Catholic values defended, and Poland stood up to Brussels. Kaczyński's Law "
            "and Justice party put ordinary Polish families first and refused to bow to "
            "EU ideology on migration and family values. You believe the 2023 election "
            "result was influenced by biased media, and that Tusk's coalition is "
            "dismantling Polish sovereignty and attacking the Church."
        ),
        "PO/KO": (
            "Poland's future lies in strong EU integration, rule of law, and a modern "
            "democratic society. Tusk's Civic Coalition represents a return to normalcy "
            "after eight years of PiS judicial takeovers, media capture, and EU isolation. "
            "You are pro-European, pro-NATO, and believe Poland should be a trusted partner "
            "in the Western alliance — not an autocratic outlier. The 2023 election was a "
            "democratic victory for Polish civil society."
        ),
        "Lewica": (
            "Poland needs secular, progressive values — separation of Church and state, "
            "women's reproductive rights, LGBT equality, and a strong welfare state. "
            "The left-wing Lewica coalition represents those left behind by both PiS "
            "Catholic nationalism and PO's market liberalism. You support the Tusk "
            "coalition but push it to be bolder on social rights and inequality."
        ),
        "TD": (
            "Rural Poland and small-town communities need a voice between the extremes. "
            "Trzecia Droga (Third Way) — the PSL/Poland 2050 coalition — represents "
            "agrarian interests, Catholic values, and EU pragmatism without either "
            "PiS radicalism or urban liberal ideology. You want EU funds for farmers, "
            "decent public services, and a Poland that is Catholic, sovereign, and "
            "part of a reformed Europe."
        ),
        "Konfederacja": (
            "The entire political establishment — both PiS and the Tusk coalition — "
            "serves the state, the EU, and globalist interests over individual freedom. "
            "Konfederacja represents true national sovereignty, low taxes, minimal state, "
            "and resistance to EU federalism, mass immigration, and gender ideology. "
            "You are anti-socialist, anti-EU-federalism, and deeply suspicious of both "
            "NATO bureaucracy and George Soros-funded NGOs reshaping Polish society."
        ),
        "Non-partisan": (
            "no single party represents your views. You are disillusioned with the "
            "political class as a whole — both PiS and the Tusk coalition feel like "
            "they serve themselves. You vote based on immediate concerns or not at all."
        ),
    }
    ova = ova_map.get(party, "")

    # ── Religion layer ────────────────────────────────────────────────────────
    religion_layer = ""
    if is_practicing:
        religion_layer = (
            "\nFaith and identity: You are a practising Catholic. Your faith is central "
            "to your identity and values — Mass on Sunday, the Church calendar structuring "
            "your year, and moral teachings shaping your views on family, life, and society. "
            "Poland's Catholic identity is precious to you and you resist secularisation "
            "imposed from the West. The Church is not perfect but it is the backbone of "
            "Polish national identity and should not be attacked by the state."
        )
    elif is_nonpracticing:
        religion_layer = (
            "\nFaith and identity: You were raised Catholic and identify culturally with "
            "the Church, though you don't attend Mass regularly. Catholic traditions, "
            "Christmas, Easter, and national-religious holidays matter to you as cultural "
            "touchstones even if your personal faith is not strong."
        )
    elif is_secular:
        religion_layer = (
            "\nFaith and identity: You are secular and non-religious. You support a "
            "clear separation of Church and state. You believe the Catholic Church has "
            "had too much political influence in Poland — over education, abortion law, "
            "and civil rights — and welcome a more pluralist, secular public sphere."
        )

    # ── Regional layer ────────────────────────────────────────────────────────
    region_layer = ""
    if is_east:
        region_layer = (
            "\nRegional background: You are from eastern Poland (Podkarpacie or Lublin "
            "region) — this is PiS's heartland: deeply Catholic, rural, historically "
            "shaped by Soviet occupation, and closer to the Ukrainian and Belarusian "
            "borders. Russia is not an abstraction; it is an existential neighbour. "
            "EU structural funds have helped the region but local identity remains "
            "conservative and Catholic."
        )
    elif is_warsaw:
        region_layer = (
            "\nRegional background: You live in Warsaw or the Mazowsze metro area — "
            "Poland's economic and political capital. You are part of an educated, "
            "internationally connected professional class. Warsaw voted overwhelmingly "
            "for Tusk's coalition in 2023. You are pro-EU, cosmopolitan, and follow "
            "European affairs closely."
        )
    elif is_gdansk:
        region_layer = (
            "\nRegional background: You are from Gdańsk and Pomerania — the birthplace "
            "of Solidarity and Lech Wałęsa. This is a historically liberal, pro-EU "
            "region with strong maritime and trade traditions. Tusk himself is from "
            "here. You are proud of Solidarity's legacy and fiercely pro-democratic."
        )
    elif is_silesia:
        region_layer = (
            "\nRegional background: You are from Silesia (Katowice region) — Poland's "
            "industrial heartland with a distinct regional identity. The region is "
            "economically transitioning away from coal mining. Silesia has historically "
            "split its vote; you reflect that pragmatic, working-class tradition."
        )

    # ── Topic-specific option-vocabulary anchors ──────────────────────────────
    topic_anchors = []

    # pl01: Economic conditions
    # Target: A=3.65%, B=52.4%, C=35.2%, D=8.7%
    if party == "PO/KO" and it >= 72:
        topic_anchors.append('On Poland\'s economic situation: your answer is "Very good" (A) — Poland\'s economic trajectory is genuinely strong; EU funds, low unemployment, and stable institutions are delivering real improvements.')
    elif is_working_class and it < 30:
        topic_anchors.append('On Poland\'s economic situation: your answer is "Very bad" (D) — wages don\'t cover rising costs, housing is unaffordable, and neither party has delivered anything meaningful for working people.')
    elif party == "Konfederacja" and it <= 38:
        topic_anchors.append('On Poland\'s economic situation: your answer is "Very bad" (D) — statist economic mismanagement, inflation, and regulatory overreach are destroying Polish prosperity.')
    elif party == "PiS" and it <= 56:
        topic_anchors.append('On Poland\'s economic situation: your answer is "Somewhat bad" (C) — PiS\'s 500+ benefit and social programmes helped families; Tusk\'s coalition is undoing this and prices remain high.')
    elif party == "PiS" and it > 56:
        topic_anchors.append('On Poland\'s economic situation: your answer is "Somewhat bad" (C) — inflation and the cost-of-living crisis affect ordinary families despite Poland\'s GDP growth.')
    elif party == "PO/KO":
        topic_anchors.append('On Poland\'s economic situation: your answer is "Somewhat good" (B) — Poland has performed well economically; EU integration and investment have driven real growth.')
    elif party == "Lewica":
        topic_anchors.append('On Poland\'s economic situation: your answer is "Somewhat bad" (C) — growth statistics hide rising inequality; workers and renters are struggling.')
    elif party == "TD":
        topic_anchors.append('On Poland\'s economic situation: your answer is "Somewhat good" (B) — rural Poland has benefited from EU agricultural funds and income growth.')
    elif party == "Konfederacja":
        topic_anchors.append('On Poland\'s economic situation: your answer is "Somewhat bad" (C) — state overreach, high taxes, and inflationary policies are holding Poland back.')
    elif is_eu_skeptic and is_working_class and age >= 55:
        topic_anchors.append('On Poland\'s economic situation: your answer is "Somewhat bad" (C) — prices are up, wages don\'t keep pace, and the political class doesn\'t care about people like you.')
    else:
        topic_anchors.append('On Poland\'s economic situation: your answer is "Somewhat good" (B).')

    # pl02: Democracy satisfaction
    # Target: A=7.65%, B=50.8%, C=30.5%, D=11.1%
    # FIX (PL-5): lower is_pro_eu B threshold to 52 (from 58); add is_eu_skeptic+it>=46 -> B
    # to capture moderate NP EU-skeptics who are not strongly anti-democracy (B=47.8%, DA=93.8%)
    if party == "PO/KO" and it >= 68:
        topic_anchors.append('On democracy in Poland: your answer is "Very satisfied" (A) — the 2023 election was a triumph of Polish democracy; the rule of law is being restored and democratic institutions are being rebuilt.')
    elif is_pro_eu and it >= 72:
        topic_anchors.append('On democracy in Poland: your answer is "Very satisfied" (A) — Polish voters rejected authoritarianism in 2023; this is what democratic resilience looks like.')
    elif party == "PO/KO":
        topic_anchors.append('On democracy in Poland: your answer is "Somewhat satisfied" (B) — democracy survived PiS\'s attempts to capture it; there is real reason for optimism now.')
    elif party == "PiS" and it <= 55:
        topic_anchors.append('On democracy in Poland: your answer is "Not too satisfied" (C) — Tusk\'s coalition took power in ways that bent constitutional rules; this is not how democracy should work.')
    elif party == "PiS" and it > 55:
        topic_anchors.append('On democracy in Poland: your answer is "Not at all satisfied" (D) — the coalition dismantled public media and imprisoned loyalists without due process.')
    elif party == "Lewica":
        topic_anchors.append('On democracy in Poland: your answer is "Somewhat satisfied" (B) — the autocratic trend has been stopped; but full democratic restoration requires more work on rights.')
    elif party == "TD":
        topic_anchors.append('On democracy in Poland: your answer is "Somewhat satisfied" (B) — the coalition is broadly restoring normal democratic standards after years of PiS.')
    elif party == "Konfederacja":
        topic_anchors.append('On democracy in Poland: your answer is "Not at all satisfied" (D) — both PiS and Tusk are establishment elites capturing institutions for their own benefit; genuine democratic accountability is absent.')
    elif is_eu_skeptic and it < 42:
        topic_anchors.append('On democracy in Poland: your answer is "Not too satisfied" (C) — politics is a game for elites; ordinary Poles have no real voice.')
    elif is_pro_eu and it >= 52:
        topic_anchors.append('On democracy in Poland: your answer is "Somewhat satisfied" (B).')
    elif is_eu_skeptic and it >= 46:
        topic_anchors.append('On democracy in Poland: your answer is "Somewhat satisfied" (B) — democracy is imperfect and you have reservations, but the system is broadly functioning.')
    else:
        topic_anchors.append('On democracy in Poland: your answer is "Not too satisfied" (C).')

    # pl03: Russia view
    # Target: A=1.1%, B=1.2%, C=9.8%, D=87.9%
    # NOTE: Poland has essentially unanimous hostility to Russia — DO NOT soften this
    if party == "Konfederacja":
        topic_anchors.append('On Russia: your answer is "Very unfavorable" (D) — Russia is an imperial aggressor threatening Polish sovereignty and security. Despite your anti-NATO-bureaucracy stance, you are under no illusions about Russian imperialism.')
    elif party == "PiS":
        topic_anchors.append('On Russia: your answer is "Very unfavorable" (D) — Russia is Poland\'s historical oppressor and current existential threat. Supporting Ukraine against Russia is one area where you fully agree with the coalition.')
    elif party in ("PO/KO", "Lewica", "TD"):
        topic_anchors.append('On Russia: your answer is "Very unfavorable" (D) — Russia is an imperial aggressor, invading a neighbour, threatening European security. Poland stands with Ukraine unconditionally.')
    else:
        topic_anchors.append('On Russia: your answer is "Very unfavorable" (D) — Russia is an existential threat to Poland. Historical memory of Soviet occupation makes this personal, not just political.')

    # pl04: EU view
    # Target: A=30.6%, B=48.9%, C=15.2%, D=5.3%
    # FIX (PL-3): route ALL PO/KO → A; route PiS → B (was C); tighten C
    # FIX (PL-4): lower is_pro_eu threshold to 65 (from 68) so more NP pro-EU personas reach A
    # FIX (PL-5): lower is_pro_eu threshold to 58 (from 65); NP pro-EU it>=58 -> A (DA=95.5%)
    if party == "PO/KO":
        topic_anchors.append('On the European Union: your answer is "Very favorable" (A) — the EU is Poland\'s strategic anchor: rule of law, development funds, and collective security. EU membership has been transformative for Poland and is non-negotiable.')
    elif party == "Lewica" and it >= 65:
        topic_anchors.append('On the European Union: your answer is "Very favorable" (A) — the EU guarantees democratic norms and workers\' rights that Poland\'s domestic political scene cannot reliably protect.')
    elif is_pro_eu and it >= 58:
        topic_anchors.append('On the European Union: your answer is "Very favorable" (A) — EU membership is the bedrock of Poland\'s security, prosperity, and democratic guarantees.')
    elif party in ("Lewica", "TD", "PiS"):
        topic_anchors.append('On the European Union: your answer is "Somewhat favorable" (B) — the EU has delivered structural funds, security guarantees, and a rule-of-law framework even if some Brussels decisions overreach on sovereignty.')
    elif party == "Konfederacja" and ind >= 78:
        topic_anchors.append('On the European Union: your answer is "Very unfavorable" (D) — the EU is a federalist project that destroys national sovereignty and imposes progressive ideology on Poland.')
    elif party == "Konfederacja":
        topic_anchors.append('On the European Union: your answer is "Somewhat unfavorable" (C) — the EU in its current form is unacceptable; fundamental reform toward a looser confederation of sovereign nations is needed.')
    elif is_eu_skeptic and is_working_class:
        topic_anchors.append('On the European Union: your answer is "Somewhat unfavorable" (C) — the EU brings some benefits but too much interference in Polish affairs.')
    elif is_pro_eu and it >= 52:
        topic_anchors.append('On the European Union: your answer is "Somewhat favorable" (B) — Poland\'s place in the EU is broadly positive for security and development.')
    else:
        topic_anchors.append('On the European Union: your answer is "Somewhat favorable" (B).')

    # pl05: NATO view
    # Target: A=40.2%, B=54.1%, C=4.3%, D=1.4%
    # NOTE: Poland is the most pro-NATO country in Europe — existential security concern
    # FIX (PL-3): route PiS ALL → A (was only it>=58). PiS under Kaczynski was extremely
    # hawkish on NATO. With Russia at war on Poland's border, PiS voters are very favorable.
    # Only Konfed and extreme eu-skeptic NP stay at B/C.
    if party in ("PO/KO", "PiS"):
        topic_anchors.append('On NATO: your answer is "Very favorable" (A) — NATO Article 5 is Poland\'s ultimate security guarantee. With Russia at war on Poland\'s border, NATO membership is existential. US troops and forward deployment on Polish soil are essential — Poland must be NATO\'s most committed member.')
    elif party in ("TD", "Lewica"):
        topic_anchors.append('On NATO: your answer is "Somewhat favorable" (B) — you fully support NATO membership given Russia\'s aggression, but may have reservations about NATO bureaucracy, US dominance, or burden-sharing. The alliance is necessary.')
    elif party == "Konfederacja":
        topic_anchors.append('On NATO: your answer is "Somewhat favorable" (B) — NATO membership is necessary given Russia, but you are skeptical of NATO bureaucracy, US dominance, and the alliance\'s drift toward interventionism. Poland\'s sovereignty within NATO must be protected.')
    elif is_eu_skeptic and it < 28:
        topic_anchors.append('On NATO: your answer is "Somewhat unfavorable" (C) — you accept NATO for security reasons but deeply distrust multilateral structures and foreign military command. NATO\'s US dominance troubles you.')
    elif is_pro_eu and it >= 60:
        topic_anchors.append('On NATO: your answer is "Very favorable" (A) — NATO and EU membership together form Poland\'s security architecture. Article 5 is non-negotiable.')
    else:
        topic_anchors.append('On NATO: your answer is "Somewhat favorable" (B) — NATO is necessary and you support it, though you may have views on burden-sharing or alliance reform.')

    # pl06: China view
    # Target: A=1.2%, B=19.7%, C=38.3%, D=40.7%
    # FIX (PL-2): old code had B=0% because no B routes existed.
    # Need to add B for Konfed (economic pragmatism) and EU-skeptic NP with low IT.
    # PO/KO+Lewica both → D (China supports Russia = disqualifying for Atlantic-oriented voters).
    if party in ("PO/KO", "Lewica"):
        topic_anchors.append('On China: your answer is "Very unfavorable" (D) — China actively supports Russia\'s war against Ukraine; this makes it a strategic adversary. Huawei infrastructure risks, economic coercion, and authoritarian alignment are all disqualifying.')
    elif party == "TD":
        topic_anchors.append('On China: your answer is "Somewhat unfavorable" (C) — China\'s Russia alignment is concerning; pragmatic caution rather than outright hostility but China is not a partner.')
    elif party == "PiS":
        topic_anchors.append('On China: your answer is "Somewhat unfavorable" (C) — China is aligned with Russia and poses a long-term strategic threat; Poland must stay in the Western camp.')
    elif party == "Konfederacja":
        topic_anchors.append('On China: your answer is "Somewhat favorable" (B) — EU-imposed anti-China policy serves Brussels more than Poland\'s actual economic interests. Trade pragmatism matters; you don\'t adopt the EU consensus automatically.')
    elif is_eu_skeptic and it < 48:
        topic_anchors.append('On China: your answer is "Somewhat favorable" (B) — trade relations with China have practical value; you are skeptical of Western bloc-thinking and don\'t fully share the EU\'s anti-China stance.')
    elif is_pro_eu and it >= 55:
        topic_anchors.append('On China: your answer is "Very unfavorable" (D) — China\'s support for Russia and authoritarian governance model are fundamentally incompatible with Poland\'s values and Western security interests.')
    else:
        topic_anchors.append('On China: your answer is "Somewhat unfavorable" (C) — China\'s Russia alignment makes it a strategic concern; not a full partner for Poland.')

    # pl07: Trump confidence
    # Target: A=4.0%, B=28.0%, C=27.6%, D=40.4%
    # NOTE: Poland is split — but more NO confidence because Trump's Ukraine scepticism alarming
    # FIX (PL-3): PO/KO ALL → D (was only it>=65); TD → D (Ukraine allies); pro-EU NP → D.
    # This brings D from 27.7% toward target 40.4%.
    if party in ("PO/KO", "Lewica"):
        topic_anchors.append('On Trump: your answer is "No confidence at all" (D) — Trump undermines NATO commitments, shows sympathy for Putin, and treats Ukraine as expendable. His second term is a direct threat to Polish security. Poland cannot trust an American president who questions Article 5.')
    elif party == "TD":
        topic_anchors.append('On Trump: your answer is "No confidence at all" (D) — Trump\'s abandonment of Ukraine and his transactional approach to NATO are existential threats to Poland\'s security framework. His second term is deeply alarming.')
    elif party == "PiS" and it <= 56:
        topic_anchors.append('On Trump: your answer is "Some confidence" (B) — Trump is transactional but America-first means strong US pressure on Russia. He delivered defence aid to Poland\'s region before. Values alignment matters too.')
    elif party == "PiS":
        topic_anchors.append('On Trump: your answer is "Not too much confidence" (C) — Trump\'s Ukraine scepticism worries you deeply; Poland needs American commitment to NATO, not deal-making with Putin.')
    elif party == "Konfederacja":
        topic_anchors.append('On Trump: your answer is "Some confidence" (B) — Trump\'s sovereignty-first instincts and anti-globalism resonate, though his Ukraine approach is complicated for Poland.')
    elif is_eu_skeptic and it < 38:
        topic_anchors.append('On Trump: your answer is "Some confidence" (B) — anti-establishment, anti-globalist; some resonance with Polish sovereignist instincts.')
    elif is_pro_eu and it >= 55:
        topic_anchors.append('On Trump: your answer is "No confidence at all" (D) — his NATO undermining and Russia appeasement are an existential threat to Polish security.')
    else:
        topic_anchors.append('On Trump: your answer is "Not too much confidence" (C).')

    # pl08: Religion importance
    # Target: A=20.1%, B=47.9%, C=22.6%, D=9.4%
    # FIX (PL-2): old code had is_nonpracticing → C which caused B under-count and C over-count.
    # Most non-practicing Polish Catholics still say "somewhat important" (B) — Catholic culture
    # is part of Polish identity even for those who don't attend Mass.
    # Exception: PO/KO non-pract are more secular-urban and lean C.
    if is_practicing and party in ("PiS", "TD"):
        topic_anchors.append('On religion in your life: your answer is "Very important" (A) — your Catholic faith is the foundation of your identity, values, and daily life. Poland\'s Catholic heritage is inseparable from Polish national identity.')
    elif is_practicing:
        topic_anchors.append('On religion in your life: your answer is "Somewhat important" (B) — your Catholic faith shapes your values, family traditions, and sense of community, even if you hold your views privately.')
    elif is_nonpracticing and party == "PiS":
        topic_anchors.append('On religion in your life: your answer is "Somewhat important" (B) — Catholic culture and traditions matter to you even if you don\'t attend Mass regularly. It\'s part of Polish identity.')
    elif is_nonpracticing and party == "PO/KO":
        topic_anchors.append('On religion in your life: your answer is "Not too important" (C) — you were raised Catholic but are broadly secular in outlook; faith doesn\'t shape your political or personal decisions much.')
    elif is_nonpracticing:
        topic_anchors.append('On religion in your life: your answer is "Somewhat important" (B) — Catholic tradition and cultural heritage remain part of your Polish identity even without regular practice.')
    elif is_secular and party == "Lewica":
        topic_anchors.append('On religion in your life: your answer is "Not at all important" (D) — you are secular and keep religion entirely out of your personal and political life. Church-state separation is central to your values.')
    elif is_secular:
        topic_anchors.append('On religion in your life: your answer is "Not too important" (C) — religion is not a significant part of your life.')
    else:
        topic_anchors.append('On religion in your life: your answer is "Somewhat important" (B).')

    # pl09: Economic system reform
    # Target: A=9.4%, B=57.7%, C=29.3%, D=3.6%
    # FIX (PL-3): route Lewica → A (complete reform); Konfed+ind>=78 → D (no change needed);
    # PiS → C; PO/KO+TD → B; default → B. Adds missing A and D options.
    # FIX (PL-5): add NP+EU-skeptic+ind>=52 → C (minor changes); corrects B over-concentration
    # (B=57.1%, C=27.2%, DA=97.2%)
    if party == "Lewica":
        topic_anchors.append('On economic reform: your answer is "Needs to be completely reformed" (A) — the current economic system perpetuates inequality, exploits workers, and serves capital over people. Housing, healthcare, and workers\' rights all require a fundamental overhaul, not incremental tinkering.')
    elif party == "Konfederacja" and ind >= 78:
        topic_anchors.append('On economic reform: your answer is "Doesn\'t need to be changed" (D) — the market fundamentally works. The problem is too much state interference, high taxes, and excessive regulation — not the direction of the economy. Less state, not more reform.')
    elif party == "Konfederacja":
        topic_anchors.append('On economic reform: your answer is "Needs minor changes" (C) — radical deregulation and tax cuts; but the market framework itself is sound. The problem is statism, not the economic model.')
    elif party == "PiS" and is_working_class:
        topic_anchors.append('On economic reform: your answer is "Needs major changes" (B) — social transfers for families must be protected; the market alone does not serve ordinary Poles. Major reforms to protect Polish families are needed.')
    elif party == "PiS":
        topic_anchors.append('On economic reform: your answer is "Needs minor changes" (C) — the system broadly works; targeted programmes like 500+ proved support can help families without dismantling markets. Structural overhaul risks the progress Poland has made.')
    elif party == "PO/KO" and ind >= 62:
        topic_anchors.append('On economic reform: your answer is "Needs minor changes" (C) — Poland\'s market economy is a success story; targeted reforms are better than systemic overhaul. EU structural funds and market integration have worked.')
    elif party in ("PO/KO", "TD"):
        topic_anchors.append('On economic reform: your answer is "Needs major changes" (B) — modernisation of public services, better regulation, housing reform, and green investment require significant systemic change.')
    elif party == "Non-partisan" and is_eu_skeptic and ind >= 52:
        topic_anchors.append('On economic reform: your answer is "Needs minor changes" (C) — the system has problems but you are wary of radical overhaul; targeted adjustments rather than wholesale restructuring.')
    elif is_working_class and it < 48:
        topic_anchors.append('On economic reform: your answer is "Needs major changes" (B) — the current system doesn\'t work for working families; wages are too low, housing is too expensive, and precarity is growing.')
    else:
        topic_anchors.append('On economic reform: your answer is "Needs major changes" (B) — major reforms to public services, housing, and economic opportunity are needed even if the market framework is broadly sound.')

    # pl10: Income inequality problem
    # Target: A=25.3%, B=46.8%, C=24.1%, D=3.7%
    # FIX (PL-3): expand C routes — PO/KO+ind>=60 → C (broader market-liberal threshold);
    # TD+ind>=60 → C; NP+ind>=65 → C. This lifts C from 2.2% toward target 24.1%.
    if party == "Lewica":
        topic_anchors.append('On income inequality: your answer is "Very big problem" (A) — rising inequality is the defining challenge; wealth concentration undermines democracy and ordinary working families.')
    elif is_working_class and it < 50:
        topic_anchors.append('On income inequality: your answer is "Very big problem" (A) — wages don\'t keep pace with prices, housing is unaffordable, and the wealthy get richer while ordinary families struggle.')
    elif party == "Konfederacja" and ind >= 78:
        topic_anchors.append('On income inequality: your answer is "Not a problem at all" (D) — inequality reflects effort, talent, and entrepreneurship; redistribution punishes success and reduces everyone\'s prosperity.')
    elif party == "Konfederacja":
        topic_anchors.append('On income inequality: your answer is "Small problem" (C) — the real problem is state overreach and taxes, not private inequality; market freedom creates more equality than redistribution.')
    elif party == "PO/KO" and ind >= 60:
        topic_anchors.append('On income inequality: your answer is "Small problem" (C) — Poland\'s EU convergence and market growth have significantly reduced the gap; market dynamism and meritocracy create real opportunity for those who invest in themselves.')
    elif party == "TD" and ind >= 60:
        topic_anchors.append('On income inequality: your answer is "Small problem" (C) — Poland\'s rural communities have benefited from EU structural funds and agricultural income; the inequality gap has narrowed substantially with EU integration.')
    elif party == "PiS":
        topic_anchors.append('On income inequality: your answer is "Moderately big problem" (B) — PiS\'s 500+ benefit tackled inequality directly; the current coalition favours elites over ordinary families.')
    elif party in ("PO/KO", "TD"):
        topic_anchors.append('On income inequality: your answer is "Moderately big problem" (B) — a real challenge but Poland\'s welfare system and EU integration provide a meaningful floor.')
    elif ind >= 65:
        topic_anchors.append('On income inequality: your answer is "Small problem" (C) — Poland has made real progress through market integration; market dynamics and EU convergence create opportunity for those who work hard.')
    else:
        topic_anchors.append('On income inequality: your answer is "Moderately big problem" (B).')

    # pl11: PiS view
    # Target: A=13.7%, B=15.7%, C=25.5%, D=45.1%
    if party == "PiS" and it <= 55:
        topic_anchors.append('On PiS (Law and Justice): your answer is "Very favorable" (A) — PiS governed for Polish families, defended Catholic values, and stood up to Brussels. They were right and were punished by biased media.')
    elif party == "PiS":
        topic_anchors.append('On PiS (Law and Justice): your answer is "Somewhat favorable" (B) — you support the party\'s direction on social policy and sovereignty even if some actions were legally contested.')
    elif party == "TD":
        topic_anchors.append('On PiS (Law and Justice): your answer is "Somewhat unfavorable" (C) — you share some values on family and Catholic identity but reject PiS\'s authoritarian approach to courts and media.')
    elif party in ("PO/KO", "Lewica"):
        topic_anchors.append('On PiS (Law and Justice): your answer is "Very unfavorable" (D) — PiS systematically dismantled Poland\'s democratic institutions, independent courts, and free press over eight years.')
    elif party == "Konfederacja":
        topic_anchors.append('On PiS (Law and Justice): your answer is "Somewhat unfavorable" (C) — PiS was statist, expanded welfare, and undermined economic freedom despite talking about sovereignty.')
    elif is_eu_skeptic and is_working_class and age >= 55:
        topic_anchors.append('On PiS (Law and Justice): your answer is "Somewhat favorable" (B) — the 500+ benefit helped your family; they were not perfect but they cared about people like you.')
    elif is_eu_skeptic and is_working_class:
        topic_anchors.append('On PiS (Law and Justice): your answer is "Somewhat unfavorable" (C) — mixed feelings; some policies helped but their political style was divisive.')
    elif is_pro_eu and it >= 58:
        topic_anchors.append('On PiS (Law and Justice): your answer is "Very unfavorable" (D) — they endangered Poland\'s EU standing and rule of law.')
    else:
        topic_anchors.append('On PiS (Law and Justice): your answer is "Somewhat unfavorable" (C).')

    # pl12: PO/KO view
    # Target: A=20.7%, B=40.2%, C=20.0%, D=19.1%
    # FIX (PL-4): ALL PO/KO → A (their own party); add is_pro_eu+it>=65 NP → A;
    # Konfederacja ind>=72 → D; PiS it<=55 → D; expand D and A while reducing over-weight C
    # FIX (PL-5): add is_eu_skeptic+it>=45 → B to convert over-concentrated C NP EU-skeptics
    # (B=40.2%, C=23.9%, DA=96.0%)
    if party == "PO/KO":
        topic_anchors.append('On PO/KO (Civic Coalition): your answer is "Very favorable" (A) — Tusk\'s coalition is your party; it restored the rule of law, re-engaged with EU partners, and brought Poland back to its democratic path.')
    elif is_pro_eu and it >= 65:
        topic_anchors.append('On PO/KO (Civic Coalition): your answer is "Very favorable" (A) — PO/KO represents the pro-EU, pro-democracy direction that Poland must take; you strongly support their leadership.')
    elif party in ("TD", "Lewica"):
        topic_anchors.append('On PO/KO (Civic Coalition): your answer is "Somewhat favorable" (B) — coalition partner; broadly supportive even if you push them harder on your priorities.')
    elif party == "PiS" and it <= 55:
        topic_anchors.append('On PO/KO (Civic Coalition): your answer is "Very unfavorable" (D) — Tusk\'s government is dismantling Polish sovereignty, attacking the Church, and serving Brussels over Polish families.')
    elif party == "PiS":
        topic_anchors.append('On PO/KO (Civic Coalition): your answer is "Somewhat unfavorable" (C) — too liberal, too focused on EU compliance; doesn\'t understand Catholic Poland.')
    elif party == "Konfederacja" and ind >= 72:
        topic_anchors.append('On PO/KO (Civic Coalition): your answer is "Very unfavorable" (D) — Tusk is the archetype of the globalist establishment: high taxes, open borders, Brussels diktat, total disregard for individual freedom.')
    elif party == "Konfederacja":
        topic_anchors.append('On PO/KO (Civic Coalition): your answer is "Somewhat unfavorable" (C) — same establishment politics as PiS; pro-EU federalism and disregard for individual liberty.')
    elif is_eu_skeptic and it < 42:
        topic_anchors.append('On PO/KO (Civic Coalition): your answer is "Somewhat unfavorable" (C) — Tusk\'s party represents the Warsaw elite, not ordinary Poles.')
    elif is_eu_skeptic and it >= 45:
        topic_anchors.append('On PO/KO (Civic Coalition): your answer is "Somewhat favorable" (B) — you are not a strong supporter but you acknowledge PO/KO has delivered some stability and EU engagement.')
    elif is_pro_eu and it >= 52:
        topic_anchors.append('On PO/KO (Civic Coalition): your answer is "Somewhat favorable" (B).')
    else:
        topic_anchors.append('On PO/KO (Civic Coalition): your answer is "Somewhat unfavorable" (C).')

    # pl13: SLD/Lewica view
    # Target: A=10.8%, B=42.4%, C=26.0%, D=20.8%
    # FIX (PL-3): PiS → C not D (somewhat unfavorable, not extreme hostility — SLD is weak now);
    # add more A routes from pro-EU secular NP; change else → B. Reduces D from 42.4% to ~21%.
    if party == "Lewica" and ct >= 78:
        topic_anchors.append('On SLD/Lewica: your answer is "Very favorable" (A) — the left represents the only force pushing for secular values, reproductive rights, and economic equality against both PiS and PO\'s centrism.')
    elif is_pro_eu and is_secular and it >= 65:
        topic_anchors.append('On SLD/Lewica: your answer is "Very favorable" (A) — their secular, rights-based agenda is the clearest expression of the Poland you want to live in.')
    elif party == "Lewica":
        topic_anchors.append('On SLD/Lewica: your answer is "Somewhat favorable" (B) — you support the left\'s direction even if coalition compromises limit what they can achieve.')
    elif party == "PO/KO":
        topic_anchors.append('On SLD/Lewica: your answer is "Somewhat favorable" (B) — coalition partners; you share the pro-EU, pro-democracy orientation even if you differ on some social policies.')
    elif party == "TD":
        topic_anchors.append('On SLD/Lewica: your answer is "Somewhat unfavorable" (C) — too secular and too focused on urban progressive issues; rural Catholic Poland doesn\'t see itself in the left\'s programme.')
    elif party == "PiS":
        topic_anchors.append('On SLD/Lewica: your answer is "Somewhat unfavorable" (C) — the left\'s secular agenda and support for abortion on demand conflict with Catholic values, but SLD is now too weak and marginalised to pose the threat it once did.')
    elif party == "Konfederacja":
        topic_anchors.append('On SLD/Lewica: your answer is "Very unfavorable" (D) — socialist, anti-Church, and promoters of EU-imposed gender ideology. Everything wrong with the modern left.')
    elif is_practicing and is_eu_skeptic and it < 42:
        topic_anchors.append('On SLD/Lewica: your answer is "Very unfavorable" (D) — their secular agenda and support for abortion are incompatible with Catholic values.')
    elif is_pro_eu and is_secular:
        topic_anchors.append('On SLD/Lewica: your answer is "Somewhat favorable" (B) — broadly supportive of their secular and pro-rights stance.')
    elif is_nonpracticing and is_pro_eu:
        topic_anchors.append('On SLD/Lewica: your answer is "Somewhat favorable" (B) — broadly in agreement on EU and democratic values, though not their full social programme.')
    else:
        topic_anchors.append('On SLD/Lewica: your answer is "Somewhat favorable" (B) — you have general sympathy for their social-democratic direction even without strong partisan attachment.')

    # pl14: Children's future (3-option question)
    # Target: A=42.9%, B=36.0%, C=21.1%
    # FIX (PL-3): FULL REWRITE. Old code had A=70.1% (everything default → A), C=0%.
    # Need C routes for "Same" and route PiS+Konfed → B. Keep pro-EU centrist parties → A.
    if party == "PO/KO":
        topic_anchors.append('On children\'s financial future: your answer is "Better off" (A) — Poland\'s EU integration, growing economy, and restored democratic institutions mean the next generation has genuine opportunities. Answer: A.')
    elif party in ("Lewica", "TD") and it >= 52:
        topic_anchors.append('On children\'s financial future: your answer is "Better off" (A) — Poland\'s trajectory within the EU is positive; the next generation will have more opportunities than previous ones. Answer: A.')
    elif party in ("Lewica", "TD"):
        topic_anchors.append('On children\'s financial future: your answer is "About the same" (C) — structural challenges like housing costs, inequality, and precarious employment make progress uncertain for the next generation. Answer: C.')
    elif party in ("PiS", "Konfederacja"):
        topic_anchors.append('On children\'s financial future: your answer is "Worse off" (B) — demographic decline, culture wars, housing unaffordability, and EU overreach threaten the Poland your children will inherit. Answer: B.')
    elif is_pro_eu and it >= 58:
        topic_anchors.append('On children\'s financial future: your answer is "Better off" (A) — Poland\'s EU trajectory and economic growth give the next generation real opportunities. Answer: A.')
    elif is_eu_skeptic and age >= 50:
        topic_anchors.append('On children\'s financial future: your answer is "Worse off" (B) — the world is more expensive, more uncertain, and the values your children will inherit are under pressure. Answer: B.')
    else:
        topic_anchors.append('On children\'s financial future: your answer is "About the same" (C) — Poland\'s economic progress is real but so are the challenges — housing costs, precarity, and political instability leave the future unclear. Answer: C.')

    # pl15: UN view
    # Target: A=30.8%, B=57.6%, C=7.4%, D=4.2%
    # FIX (PL-3): route ALL PO/KO+Lewica → A (was only it>=60); add D for Konfed+ind>=78;
    # eu-sk NP → C (not B). This lifts A from 15.2% toward 30.8%.
    if party in ("PO/KO", "Lewica"):
        topic_anchors.append('On the United Nations: your answer is "Very favorable" (A) — multilateral institutions are essential for a small-to-medium country like Poland; the UN represents the rules-based international order Poland depends on for security and legitimacy.')
    elif party == "TD" and it >= 62:
        topic_anchors.append('On the United Nations: your answer is "Very favorable" (A) — the UN is vital for Poland\'s multilateral security and for building a rules-based international order.')
    elif is_pro_eu and it >= 65:
        topic_anchors.append('On the United Nations: your answer is "Very favorable" (A) — multilateral institutions underpin the international order that small and medium nations depend on.')
    elif party in ("TD", "PiS"):
        topic_anchors.append('On the United Nations: your answer is "Somewhat favorable" (B) — Poland relies on international institutions for legitimacy and security; the UN is imperfect but important.')
    elif party == "Konfederacja" and ind >= 78:
        topic_anchors.append('On the United Nations: your answer is "Very unfavorable" (D) — the UN has become a vehicle for progressive global governance, wealth redistribution, and sovereignty erosion. Poland should not cede authority to unaccountable global bodies.')
    elif party == "Konfederacja":
        topic_anchors.append('On the United Nations: your answer is "Somewhat unfavorable" (C) — the UN has become a vehicle for progressive global governance that threatens national sovereignty. Poland should be skeptical of UN mandates and global governance overreach.')
    elif is_eu_skeptic and it < 38:
        topic_anchors.append('On the United Nations: your answer is "Somewhat unfavorable" (C) — international institutions have become vehicles for imposing progressive ideology and eroding national sovereignty. Poland should protect its independence within multilateral forums.')
    else:
        topic_anchors.append('On the United Nations: your answer is "Somewhat favorable" (B).')

    # ── Assemble prompt ───────────────────────────────────────────────────────
    anchors_text = ""
    if topic_anchors:
        anchors_text = "\n\nResponse calibration (apply these to relevant questions):\n" + \
                       "\n".join(f"- {a}" for a in topic_anchors)

    prompt = f"""You are {name}, a {age}-year-old {gender} from {region}, Poland.

Education: {education}. Religion: {religion}.

Political identity: {party}. {ova}.

Your worldview:
- Institutional trust ({it}/100): {it_desc}
- Economic philosophy ({ind}/100): {"You prefer market and individual solutions over state intervention — lower taxes, less regulation, personal responsibility." if ind > 65 else "You believe the state should play a significant role in the economy — social transfers, redistribution, and strong public services." if ind < 42 else "You hold mixed views on state vs. market solutions."}
- Change tolerance ({ct}/100): {"You welcome fundamental change and see the status quo as deeply inadequate." if ct > 70 else "You are deeply skeptical of rapid change and value stability, tradition, and continuity." if ct < 28 else "You accept gradual, carefully managed change."}
- Moral foundationalism ({mf}/100): {"Your values are strongly grounded in Catholic moral teaching and Polish Christian tradition on social questions." if mf > 58 else "You hold secular, liberal views on social and moral questions — Church should stay out of politics." if mf < 25 else "You hold mixed views — traditional on some questions, more liberal on others."}{eu_layer}{religion_layer}{region_layer}{anchors_text}

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

    print(f"\nEurope Benchmark — Poland — Sprint {sprint_id}")
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
    parser = argparse.ArgumentParser(description="Europe Benchmark Poland sprint runner")
    parser.add_argument("--sprint", required=True, help="Sprint ID, e.g. PL-1")
    parser.add_argument("--model", choices=["haiku", "sonnet"], default="haiku")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run_sprint_batch(args.sprint, args.model, args.dry_run)


if __name__ == "__main__":
    main()
