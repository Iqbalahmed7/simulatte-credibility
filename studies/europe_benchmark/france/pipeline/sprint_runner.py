#!/usr/bin/env python3
"""
sprint_runner.py — Europe Benchmark · France calibration sprint runner.

Usage:
    python3 sprint_runner.py --sprint FR-1 --model haiku
    python3 sprint_runner.py --sprint FR-1 --model haiku --dry-run

WorldviewAnchor dimensions (0–100 scale):
    IT  — Institutional Trust
    IND — Individualism (market vs. state preference)
    CT  — Change Tolerance
    MF  — Moral Foundationalism

Key France calibration axes:
    1. Three-bloc structure: Macron Renaissance / Le Pen RN / Mélenchon LFI
    2. Traditional right (LR / Gaulliste): sovereign, conservative, pro-EU-lite
    3. Paris vs. provinces: metropolitan educated vs. rural/periurban working class
    4. Religion: Muslim practicing (8–10%), practising Catholic, secular (laïcité dominant)
    5. Age: younger LFI/Renaissance urban vs. older RN rural
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
    _env_file = Path(__file__).resolve().parent.parent / ".env"  # france/.env fallback
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
# Demographic targets (INSEE / French Election Studies):
#   Parties:  RN ~12.5%, Renaissance ~20%, LFI ~12.5%, LR ~12.5%,
#             PS (social-dem) ~10%, Non-partisan ~32.5%
#   Region:   Paris/ÎdF ~18%, Other urban ~42%, Periurban/rural ~40%
#   Religion: Catholic (inc. non-practicing) 55%, Muslim 9%, Secular 36%
#   Education: Grandes écoles/Masters 30%, Bac/BTS/IUT 35%, BEP/vocational/CAP 35%
#   EU attitude: broadly pro-EU ~55%, skeptical 45%
#   Age range: 25–72

PERSONAS = [
    # ── RN (Rassemblement National — nationalist, anti-immigration, Leave-EU) ──
    ("fr_p01", "Jean-Pierre Lebrun",  57, "male",   "France (North / Hauts-de-France)",  "RN",           "EU-skeptic", "Catholic (non-practicing)", "BEP/vocational", 2.5),
    ("fr_p02", "Martine Dupont",      53, "female", "France (Centre-Val de Loire)",       "RN",           "EU-skeptic", "Catholic (non-practicing)", "BEP/vocational", 2.5),
    ("fr_p03", "Claude Morin",        61, "male",   "France (South West / Occitanie)",    "RN",           "EU-skeptic", "None/secular",              "BEP/vocational", 2.5),
    ("fr_p04", "Sylvie Renard",       48, "female", "France (East / Grand Est)",          "RN",           "EU-skeptic", "Catholic (non-practicing)", "Bac/BTS",        2.5),
    ("fr_p05", "Gérard Fontaine",     65, "male",   "France (Provence / PACA)",           "RN",           "EU-skeptic", "Catholic (non-practicing)", "BEP/vocational", 2.5),

    # ── Renaissance (Macron's party — centrist, pro-EU, educated) ─────────────
    ("fr_p06", "Isabelle Mercier",    44, "female", "France (Paris / Île-de-France)",     "Renaissance",  "Pro-EU",     "None/secular",              "Masters/grandes écoles", 2.0),
    ("fr_p07", "Thomas Garnier",      39, "male",   "France (Paris / Île-de-France)",     "Renaissance",  "Pro-EU",     "None/secular",              "Masters/grandes écoles", 2.0),
    ("fr_p08", "Nathalie Petit",      51, "female", "France (Lyon / Auvergne-Rhône-Alpes)", "Renaissance","Pro-EU",     "Catholic (non-practicing)", "Masters/grandes écoles", 2.0),
    ("fr_p09", "Laurent Dubois",      46, "male",   "France (Bordeaux / Nouvelle-Aquitaine)", "Renaissance","Pro-EU",   "None/secular",              "Masters/grandes écoles", 2.0),
    ("fr_p10", "Claire Beaumont",     35, "female", "France (Paris / Île-de-France)",     "Renaissance",  "Pro-EU",     "None/secular",              "Masters/grandes écoles", 2.0),
    ("fr_p11", "Marc Lefebvre",       55, "male",   "France (North / Hauts-de-France)",   "Renaissance",  "Pro-EU",     "Catholic (non-practicing)", "Bac/BTS",        2.0),
    ("fr_p12", "Véronique Simon",     42, "female", "France (Toulouse / Occitanie)",      "Renaissance",  "Pro-EU",     "None/secular",              "Masters/grandes écoles", 2.0),
    ("fr_p13", "Frédéric Bonnet",     49, "male",   "France (Strasbourg / Grand Est)",    "Renaissance",  "Pro-EU",     "Catholic (non-practicing)", "Bac/BTS",        2.0),

    # ── LFI (La France Insoumise — Mélenchon left, anti-establishment) ────────
    ("fr_p14", "Leila Benali",        31, "female", "France (Paris / Île-de-France)",     "LFI",          "EU-skeptic", "Muslim",                    "Masters/grandes écoles", 2.5),
    ("fr_p15", "Antoine Roux",        27, "male",   "France (Marseille / PACA)",          "LFI",          "EU-skeptic", "None/secular",              "Bac/BTS",        2.5),
    ("fr_p16", "Fatima Chaoui",       36, "female", "France (Paris suburb / Île-de-France)", "LFI",       "EU-skeptic", "Muslim",                    "Bac/BTS",        2.5),
    ("fr_p17", "Baptiste Girard",     33, "male",   "France (Bordeaux / Nouvelle-Aquitaine)", "LFI",      "EU-skeptic", "None/secular",              "Masters/grandes écoles", 2.0),
    ("fr_p18", "Amina Diallo",        29, "female", "France (Lyon / Auvergne-Rhône-Alpes)", "LFI",        "EU-skeptic", "Muslim",                    "Bac/BTS",        2.5),

    # ── LR (Les Républicains — Gaullist centre-right, pro-EU-lite, traditional) ─
    ("fr_p19", "Philippe Rousseau",   63, "male",   "France (Paris / Île-de-France)",     "LR",           "Pro-EU",     "Catholic (practicing)",     "Masters/grandes écoles", 2.0),
    ("fr_p20", "Catherine Moreau",    58, "female", "France (West / Bretagne)",           "LR",           "Pro-EU",     "Catholic (practicing)",     "Bac/BTS",        2.5),
    ("fr_p21", "Henri Charlot",       55, "male",   "France (East / Grand Est)",          "LR",           "Pro-EU",     "Catholic (practicing)",     "Masters/grandes écoles", 2.0),
    ("fr_p22", "Dominique Faure",     49, "female", "France (South / PACA)",              "LR",           "Pro-EU",     "Catholic (practicing)",     "Bac/BTS",        2.5),
    ("fr_p23", "Bernard Leclerc",     67, "male",   "France (Centre-Val de Loire)",       "LR",           "Pro-EU",     "Catholic (practicing)",     "BEP/vocational", 2.5),

    # ── PS (Parti Socialiste — social-democrat, pro-EU, centre-left) ──────────
    ("fr_p24", "Sandrine Vidal",      45, "female", "France (Paris / Île-de-France)",     "PS",           "Pro-EU",     "None/secular",              "Masters/grandes écoles", 2.0),
    ("fr_p25", "Éric Perrin",         52, "male",   "France (Lyon / Auvergne-Rhône-Alpes)", "PS",         "Pro-EU",     "None/secular",              "Masters/grandes écoles", 2.0),
    ("fr_p26", "Monique Aubert",      60, "female", "France (North / Hauts-de-France)",   "PS",           "Pro-EU",     "None/secular",              "Bac/BTS",        2.5),
    ("fr_p27", "Julien Marchand",     38, "male",   "France (Bordeaux / Nouvelle-Aquitaine)", "PS",       "Pro-EU",     "None/secular",              "Masters/grandes écoles", 2.0),

    # ── Non-partisan / disengaged (cross-cutting, largely periurban) ───────────
    ("fr_p28", "Michel Chevalier",    59, "male",   "France (North / Hauts-de-France)",   "Non-partisan", "EU-skeptic", "Catholic (non-practicing)", "BEP/vocational", 2.5),
    ("fr_p29", "Brigitte Lamy",       54, "female", "France (Centre-Val de Loire)",       "Non-partisan", "EU-skeptic", "None/secular",              "BEP/vocational", 2.5),
    ("fr_p30", "Rachid Ouali",        43, "male",   "France (Paris suburb / Île-de-France)", "Non-partisan","EU-skeptic","Muslim",                   "Bac/BTS",        2.5),
    ("fr_p31", "Agnès Toussaint",     47, "female", "France (South West / Occitanie)",    "Non-partisan", "EU-skeptic", "Catholic (non-practicing)", "BEP/vocational", 2.5),
    ("fr_p32", "Pierre Dufour",       64, "male",   "France (East / Grand Est)",          "Non-partisan", "EU-skeptic", "Catholic (non-practicing)", "BEP/vocational", 2.5),
    ("fr_p33", "Élise Guérin",        30, "female", "France (Paris / Île-de-France)",     "Non-partisan", "Pro-EU",     "None/secular",              "Masters/grandes écoles", 2.0),
    ("fr_p34", "Yves Bouchard",       68, "male",   "France (West / Bretagne)",           "Non-partisan", "Pro-EU",     "Catholic (practicing)",     "Bac/BTS",        2.5),
    ("fr_p35", "Nadia Bousquet",      37, "female", "France (Lyon / Auvergne-Rhône-Alpes)", "Non-partisan","Pro-EU",    "Muslim",                    "Bac/BTS",        2.5),
    ("fr_p36", "Alain Dupré",         62, "male",   "France (South / PACA)",              "Non-partisan", "EU-skeptic", "None/secular",              "BEP/vocational", 2.5),
    ("fr_p37", "Cécile Martin",       41, "female", "France (Bordeaux / Nouvelle-Aquitaine)", "Non-partisan","Pro-EU",  "None/secular",              "Masters/grandes écoles", 2.0),
    ("fr_p38", "Robert Aumont",       71, "male",   "France (Centre-Val de Loire)",       "Non-partisan", "EU-skeptic", "Catholic (non-practicing)", "BEP/vocational", 2.5),
    ("fr_p39", "Laure Tissier",       34, "female", "France (Strasbourg / Grand Est)",    "Non-partisan", "Pro-EU",     "None/secular",              "Bac/BTS",        2.0),
    ("fr_p40", "Denis Charpentier",   56, "male",   "France (North / Hauts-de-France)",   "Non-partisan", "EU-skeptic", "Catholic (non-practicing)", "BEP/vocational", 2.5),
]

# ── WorldviewAnchor values ────────────────────────────────────────────────────
WORLDVIEW = {
    # id:        (IT,  IND, CT,  MF)
    # RN — low IT, moderate IND, low CT, moderate-high MF
    "fr_p01": (30,  55,  20,  45),   # RN, North, EU-skeptic, non-practicing Catholic, vocational
    "fr_p02": (28,  52,  18,  42),   # RN, Centre, EU-skeptic, non-practicing Catholic, vocational
    "fr_p03": (32,  56,  22,  28),   # RN, SW, EU-skeptic, secular, vocational
    "fr_p04": (35,  54,  25,  44),   # RN, East, EU-skeptic, non-practicing Catholic, Bac
    "fr_p05": (27,  58,  15,  48),   # RN, PACA, EU-skeptic, non-practicing Catholic, vocational (older)

    # Renaissance — high IT, moderate IND, moderate CT, low MF
    "fr_p06": (68,  62,  60,  15),   # Ren, Paris, Pro-EU, secular, grandes écoles
    "fr_p07": (65,  60,  58,  12),   # Ren, Paris, Pro-EU, secular, grandes écoles
    "fr_p08": (62,  58,  55,  28),   # Ren, Lyon, Pro-EU, non-practicing Catholic, grandes écoles
    "fr_p09": (60,  62,  57,  14),   # Ren, Bordeaux, Pro-EU, secular, grandes écoles
    "fr_p10": (70,  58,  65,  10),   # Ren, Paris, Pro-EU, secular, grandes écoles (younger)
    "fr_p11": (55,  56,  50,  35),   # Ren, North, Pro-EU, non-practicing Catholic, Bac
    "fr_p12": (64,  60,  62,  12),   # Ren, Toulouse, Pro-EU, secular, grandes écoles
    "fr_p13": (58,  55,  52,  32),   # Ren, Strasbourg, Pro-EU, non-practicing Catholic, Bac

    # LFI — low-moderate IT, low IND, very high CT, low MF (secular left)
    "fr_p14": (35,  25,  80,  55),   # LFI, Paris, EU-skeptic, Muslim, grandes écoles
    "fr_p15": (28,  22,  82,  15),   # LFI, Marseille, EU-skeptic, secular, Bac
    "fr_p16": (30,  24,  78,  60),   # LFI, Paris suburb, EU-skeptic, Muslim, Bac
    "fr_p17": (32,  28,  78,  10),   # LFI, Bordeaux, EU-skeptic, secular, grandes écoles
    "fr_p18": (26,  22,  80,  62),   # LFI, Lyon, EU-skeptic, Muslim, Bac

    # LR — moderate-high IT, high IND, low CT, high MF
    "fr_p19": (60,  70,  28,  58),   # LR, Paris, Pro-EU, practicing Catholic, grandes écoles
    "fr_p20": (58,  65,  25,  65),   # LR, Bretagne, Pro-EU, practicing Catholic, Bac
    "fr_p21": (62,  68,  30,  62),   # LR, East, Pro-EU, practicing Catholic, grandes écoles
    "fr_p22": (55,  62,  28,  60),   # LR, PACA, Pro-EU, practicing Catholic, Bac
    "fr_p23": (52,  60,  22,  65),   # LR, Centre, Pro-EU, practicing Catholic, vocational (older)

    # PS — moderate IT, low-moderate IND, moderate-high CT, low MF
    "fr_p24": (58,  38,  68,  14),   # PS, Paris, Pro-EU, secular, grandes écoles
    "fr_p25": (55,  40,  65,  12),   # PS, Lyon, Pro-EU, secular, grandes écoles
    "fr_p26": (50,  38,  60,  18),   # PS, North, Pro-EU, secular, Bac
    "fr_p27": (56,  42,  68,  10),   # PS, Bordeaux, Pro-EU, secular, grandes écoles

    # Non-partisan — wide spread
    "fr_p28": (32,  50,  20,  40),   # NP, North, EU-skeptic, non-practicing Catholic, vocational
    "fr_p29": (28,  48,  22,  30),   # NP, Centre, EU-skeptic, secular, vocational
    "fr_p30": (35,  42,  45,  65),   # NP, Paris suburb, EU-skeptic, Muslim, Bac
    "fr_p31": (30,  48,  18,  42),   # NP, SW, EU-skeptic, non-practicing Catholic, vocational
    "fr_p32": (25,  50,  16,  44),   # NP, East, EU-skeptic, non-practicing Catholic, vocational (older)
    "fr_p33": (62,  56,  72,  10),   # NP, Paris, Pro-EU, secular, grandes écoles (younger)
    "fr_p34": (58,  52,  30,  62),   # NP, Bretagne, Pro-EU, practicing Catholic, Bac (older)
    "fr_p35": (50,  44,  58,  60),   # NP, Lyon, Pro-EU, Muslim, Bac
    "fr_p36": (28,  55,  18,  25),   # NP, PACA, EU-skeptic, secular, vocational
    "fr_p37": (60,  55,  65,  12),   # NP, Bordeaux, Pro-EU, secular, grandes écoles
    "fr_p38": (22,  50,  14,  48),   # NP, Centre, EU-skeptic, non-practicing Catholic, vocational (oldest)
    "fr_p39": (56,  52,  62,  15),   # NP, Strasbourg, Pro-EU, secular, Bac
    "fr_p40": (30,  50,  20,  42),   # NP, North, EU-skeptic, non-practicing Catholic, vocational
}


def build_system_prompt(persona: tuple) -> str:
    pid, name, age, gender, region, party, eu_ref, religion, education, weight = persona
    it, ind, ct, mf = WORLDVIEW[pid]

    is_paris       = "Paris" in region or "Île-de-France" in region
    is_paris_suburb = "suburb" in region
    is_north       = "North" in region or "Hauts-de-France" in region
    is_south       = "PACA" in region or "Provence" in region
    is_east        = "Grand Est" in region or "Strasbourg" in region or "East" in region
    is_eu_skeptic  = eu_ref == "EU-skeptic"
    is_pro_eu      = eu_ref == "Pro-EU"
    is_muslim      = religion == "Muslim"
    is_catholic_practicing = "practicing" in religion and "non" not in religion
    is_secular     = "secular" in religion or "None" in religion
    is_working_class = "BEP" in education or "vocational" in education or "CAP" in education

    # ── Institutional trust descriptor ────────────────────────────────────────
    if it < 35:
        it_desc = (
            "You have very low trust in French institutions — the République, the media, "
            "Brussels. You feel the political class (PPPL — les partis politiques et les "
            "lobbies) governs for elites, not ordinary French people."
        )
    elif it < 52:
        it_desc = (
            "You have mixed trust in French institutions. You see real dysfunction and "
            "growing disillusionment, but still believe in republican values in principle."
        )
    elif it < 65:
        it_desc = (
            "You have moderate trust in French institutions. You're realistic about their "
            "imperfections but broadly believe in the Fifth Republic's stability."
        )
    else:
        it_desc = (
            "You have high trust in French institutions. The rule of law, democratic "
            "process, and European cooperation matter deeply to you."
        )

    # ── EU/Europe layer ────────────────────────────────────────────────────────
    if is_pro_eu:
        eu_layer = (
            "\nEurope: You are broadly pro-European. You see the EU as a force for "
            "stability, prosperity, and French influence in the world. "
            "The European project matters to you, even if its execution is imperfect."
        )
    else:
        eu_layer = (
            "\nEurope: You are skeptical of the EU. You feel that Brussels imposes rules "
            "that undermine French sovereignty, protect corporations over workers, and "
            "fail ordinary citizens. You are not unconditionally opposed to Europe "
            "but demand a fundamentally reformed relationship."
        )

    # ── Party political identity ───────────────────────────────────────────────
    ova_map = {
        "RN": (
            "France has been betrayed by the establishment — uncontrolled immigration, "
            "deindustrialisation, and a political class that serves globalised elites while "
            "ordinary French people struggle. Le Pen's Rassemblement National represents "
            "the France that has been left behind. You want firm border control, "
            "priorité nationale in social policy, and French sovereignty restored."
        ),
        "Renaissance": (
            "France needs bold reform — a dynamic economy, strong European partnerships, "
            "and a credible defence capacity. Macron's Renaissance represents a break from "
            "the old partisan blocs (ni droite ni gauche) that failed France. "
            "You believe in an open, modern, meritocratic France that leads in Europe."
        ),
        "LFI": (
            "The current economic system fails workers and the planet. Mélenchon's "
            "La France Insoumise represents the only credible break from neo-liberal "
            "austerity — stronger purchasing power, ecological transition, and a foreign "
            "policy free from NATO and American dominance. "
            "You are deeply anti-establishment and reject both the traditional left and right."
        ),
        "LR": (
            "France needs strong leadership grounded in Gaullist tradition — "
            "republican order, security, sovereign foreign policy, and economic competence. "
            "Les Républicains represent the responsible centre-right: lower taxes, "
            "strong institutions, firm immigration policy, and European pragmatism. "
            "You are conservative, not nationalist, and distrust both Macron and Le Pen."
        ),
        "PS": (
            "Social democracy — equality, public services, and European solidarity — "
            "remains France's best path. The Parti Socialiste stands for workers' rights, "
            "universal healthcare, progressive taxation, and a social Europe. "
            "You are pro-EU but believe it must serve people, not markets."
        ),
        "Non-partisan": (
            "no single party represents your views. You are disillusioned with the "
            "political class as a whole — la politique politicienne — and vote based "
            "on immediate concerns or not at all."
        ),
    }
    ova = ova_map.get(party, "")

    # ── Religion layer ────────────────────────────────────────────────────────
    religion_layer = ""
    if is_muslim:
        religion_layer = (
            "\nFaith and identity: Your Muslim faith is part of your identity. "
            "You experience discrimination and feel that mainstream French politics often "
            "uses Islam as a wedge issue. You believe in laïcité but reject its weaponisation "
            "against Muslim communities. France is your country too."
        )
    elif is_catholic_practicing:
        religion_layer = (
            "\nFaith and identity: You are a practising Catholic. "
            "Your faith informs your social values — family, community, and moral "
            "responsibility. You believe France's Christian heritage matters and "
            "worry about secularism becoming aggressively anti-religious."
        )

    # ── Regional layer ────────────────────────────────────────────────────────
    region_layer = ""
    if is_north:
        region_layer = (
            "\nRegional background: You are from the North (Hauts-de-France) — "
            "once the industrial heart of France, now struggling with deindustrialisation "
            "and long-term unemployment. This region votes heavily RN. "
            "You feel forgotten by Paris and Brussels alike."
        )
    elif is_paris and not is_paris_suburb:
        region_layer = (
            "\nRegional background: You live in Paris or the inner Île-de-France. "
            "You are part of France's professional and educated class. "
            "You are more cosmopolitan, pro-EU, and socially liberal than the national average."
        )
    elif is_paris_suburb:
        region_layer = (
            "\nRegional background: You live in the Paris banlieue (suburbs). "
            "This is one of the most diverse and economically unequal areas of France. "
            "You navigate identity, discrimination, and precarity daily."
        )
    elif is_south:
        region_layer = (
            "\nRegional background: You are from the South (PACA / Provence-Côte d'Azur). "
            "This region has historically swung between the left and far-right. "
            "Immigration from North Africa, regional identity, and economic precarity "
            "all shape local politics strongly."
        )

    # ── Topic-specific option-vocabulary anchors ──────────────────────────────
    topic_anchors = []

    # fr01: Economic conditions
    # Target: A=1.2%, B=27.4%, C=43.8%, D=27.5%
    # FR-2: D=45.9% — RN all + LFI + NP EU-skeptic WC all routing to D
    # Fix: RN split by IT (≤30→D, >30→C); NP EU-sk WC split by IT (it<27→D, else→C)
    #      Renaissance all→B; NP pro-EU it≥55→B
    if party == "RN" and it <= 30:
        topic_anchors.append('On France\'s economic situation: your answer is "Very bad" (D) — Macron\'s neo-liberal policies have crushed working families and destroyed French industry.')
    elif party == "RN":
        topic_anchors.append('On France\'s economic situation: your answer is "Somewhat bad" (C) — the economy is not working for ordinary people, though you stop short of total despair.')
    elif party == "LFI":
        topic_anchors.append('On France\'s economic situation: your answer is "Very bad" (D) — neo-liberal policies have impoverished workers and entrenched inequality.')
    elif party == "Renaissance":
        topic_anchors.append('On France\'s economic situation: your answer is "Somewhat good" (B) — Macron\'s structural reforms have improved employment and investment, even if inequality persists.')
    elif party == "LR":
        topic_anchors.append('On France\'s economic situation: your answer is "Somewhat bad" (C) — overspending, over-regulation, and structural paralysis have weakened France.')
    elif party == "PS":
        topic_anchors.append('On France\'s economic situation: your answer is "Somewhat bad" (C) — inequality is worsening and austerity has failed workers, but some gains remain.')
    elif is_eu_skeptic and is_working_class and it < 27:
        topic_anchors.append('On France\'s economic situation: your answer is "Very bad" (D) — the system is broken for working people like you. Nothing has improved.')
    elif is_eu_skeptic and is_working_class:
        topic_anchors.append('On France\'s economic situation: your answer is "Somewhat bad" (C) — the economy is not working for people like you, but you acknowledge some regional variation.')
    elif is_pro_eu and it >= 55:
        topic_anchors.append('On France\'s economic situation: your answer is "Somewhat good" (B) — France\'s position in the European economy has genuine strengths even if challenges remain.')
    else:
        topic_anchors.append('On France\'s economic situation: your answer is "Somewhat bad" (C).')

    # fr02: Democracy satisfaction
    # FR-1: D=45.9% (target 31.9%), B=13.7% (target 33.7%) — D over, B under
    # Fix: NP EU-skeptic moderate IT (32-45) → C not D; pro-EU NP → B; split RN on IT
    # Target: A=4.6%, B=33.7%, C=29.8%, D=31.9%
    if party == "RN" and it <= 30:
        topic_anchors.append('On democracy in France: your answer is "Not at all satisfied" (D) — the political system is rigged against the French people and the true opposition.')
    elif party == "RN":
        topic_anchors.append('On democracy in France: your answer is "Not too satisfied" (C) — you want a real break with the establishment\'s hold on politics, even if you stop short of total rejection.')
    elif party == "LFI" and ct >= 80:
        topic_anchors.append('On democracy in France: your answer is "Not at all satisfied" (D) — the République is captured by financial elites and media power.')
    elif party == "LFI":
        topic_anchors.append('On democracy in France: your answer is "Not too satisfied" (C) — real democracy requires structural change that current institutions block.')
    elif party == "Renaissance" and it >= 65:
        topic_anchors.append('On democracy in France: your answer is "Somewhat satisfied" (B) — French democracy is resilient; Macron\'s reforms are strengthening institutions even if the process is messy.')
    elif party == "Renaissance":
        topic_anchors.append('On democracy in France: your answer is "Somewhat satisfied" (B) — the system is imperfect but functional.')
    elif party == "LR":
        topic_anchors.append('On democracy in France: your answer is "Not too satisfied" (C) — too much executive power, too little parliamentary control.')
    elif party == "PS":
        topic_anchors.append('On democracy in France: your answer is "Somewhat satisfied" (B) — French democracy has real flaws but is worth defending and reforming.')
    elif is_eu_skeptic and it < 32:
        topic_anchors.append('On democracy in France: your answer is "Not at all satisfied" (D).')
    elif is_eu_skeptic and it < 45:
        topic_anchors.append('On democracy in France: your answer is "Not too satisfied" (C) — the system doesn\'t work for ordinary people.')
    elif is_pro_eu and it >= 55:
        topic_anchors.append('On democracy in France: your answer is "Somewhat satisfied" (B).')
    else:
        topic_anchors.append('On democracy in France: your answer is "Not too satisfied" (C).')

    # fr03: Russia view
    # Target: A=2.8%, B=12.2%, C=32.5%, D=52.5%
    if party == "RN" and it <= 30:
        topic_anchors.append('On Russia: your answer is "Somewhat favorable" (B) — Russia is a sovereign nation defending its interests against NATO expansion. The war is complicated.')
    elif party == "RN":
        topic_anchors.append('On Russia: your answer is "Somewhat unfavorable" (C) — you have some sympathy for Russian sovereignty arguments but condemn the invasion of Ukraine.')
    elif party == "LFI":
        topic_anchors.append('On Russia: your answer is "Somewhat unfavorable" (C) — you oppose the invasion but also oppose NATO escalation. Neither bloc is innocent.')
    elif party in ("Renaissance", "LR", "PS"):
        topic_anchors.append('On Russia: your answer is "Very unfavorable" (D) — the invasion of Ukraine is a war crime and a threat to the European order.')
    elif is_eu_skeptic and it < 35:
        topic_anchors.append('On Russia: your answer is "Somewhat unfavorable" (C) — you are skeptical of NATO narratives but do not support the invasion.')
    else:
        topic_anchors.append('On Russia: your answer is "Very unfavorable" (D).')

    # fr04: EU view
    # Target: A=10.0%, B=44.8%, C=27.1%, D=18.2%
    if party == "Renaissance" and it >= 65:
        topic_anchors.append('On the European Union: your answer is "Very favorable" (A) — the EU is central to France\'s prosperity, security, and global influence.')
    elif party in ("Renaissance", "LR", "PS") and is_pro_eu:
        topic_anchors.append('On the European Union: your answer is "Somewhat favorable" (B) — the EU has real flaws but is fundamentally a positive force for France.')
    elif party == "LFI":
        topic_anchors.append('On the European Union: your answer is "Somewhat unfavorable" (C) — the EU as currently constituted serves capital over citizens. You want a fundamentally different Europe, not this one.')
    elif party == "RN" and it <= 30:
        topic_anchors.append('On the European Union: your answer is "Very unfavorable" (D) — Brussels bureaucrats steal French sovereignty and impose liberal migration policies against the will of the French people.')
    elif party == "RN":
        topic_anchors.append('On the European Union: your answer is "Somewhat unfavorable" (C) — you want a fundamentally reformed EU that respects national sovereignty.')
    elif is_eu_skeptic and is_working_class:
        topic_anchors.append('On the European Union: your answer is "Somewhat unfavorable" (C) — the EU has brought cheap labour competition and loss of French jobs.')
    elif is_pro_eu and is_secular:
        topic_anchors.append('On the European Union: your answer is "Somewhat favorable" (B).')
    elif is_eu_skeptic:
        topic_anchors.append('On the European Union: your answer is "Somewhat unfavorable" (C).')
    else:
        topic_anchors.append('On the European Union: your answer is "Somewhat favorable" (B).')

    # fr05: NATO view
    # FR-1: C=45.9% (target 24.2%) — C massively over; need D bucket and differentiate RN/LFI
    # Target: A=8.9%, B=53.5%, C=24.2%, D=13.5%
    if party == "Renaissance" and it >= 65:
        topic_anchors.append('On NATO: your answer is "Very favorable" (A) — NATO is essential for European security and France must remain a committed, active member.')
    elif party in ("Renaissance", "LR") and is_pro_eu:
        topic_anchors.append('On NATO: your answer is "Somewhat favorable" (B) — NATO provides essential collective defence, even if Macron rightly pushes for greater European strategic autonomy.')
    elif party == "LFI" and it <= 30:
        topic_anchors.append('On NATO: your answer is "No confidence — very unfavorable" — actually: your answer is "Very unfavorable (D)" — NATO is an imperialist military alliance and France should withdraw entirely like de Gaulle from the integrated command.')
    elif party == "LFI":
        topic_anchors.append('On NATO: your answer is "Somewhat unfavorable" (C) — NATO is an instrument of US imperial policy. France should pursue true strategic independence.')
    elif party == "RN" and it <= 28:
        topic_anchors.append('On NATO: your answer is "Very unfavorable" (D) — NATO drags France into American wars and undermines our sovereign defence. De Gaulle was right and we should finish the job.')
    elif party == "RN":
        topic_anchors.append('On NATO: your answer is "Somewhat unfavorable" (C) — France\'s security interests don\'t always align with NATO\'s agenda.')
    elif party == "PS":
        topic_anchors.append('On NATO: your answer is "Somewhat favorable" (B) — NATO is a necessary framework for now, with European defence autonomy as the goal.')
    elif is_eu_skeptic and it < 28:
        topic_anchors.append('On NATO: your answer is "Very unfavorable" (D) — sceptical of all military alliances that serve American interests over French ones.')
    elif is_eu_skeptic and it < 40:
        topic_anchors.append('On NATO: your answer is "Somewhat unfavorable" (C) — sceptical of military alliances that serve American interests.')
    else:
        topic_anchors.append('On NATO: your answer is "Somewhat favorable" (B).')

    # fr06: China view
    # FR-3: C=59.6%, B=24.0%, D=16.4% — D underweight (target 30.8%), missing A (target 2.4%)
    # Fix: LR + Renaissance high-IT → D; add A bucket for LFI Muslim high-CT; expand D with PS;
    #      NP EU-skeptic it≥35 → C (not B); NP pro-EU it≥60 → D
    # Target: A=2.4%, B=20.4%, C=46.5%, D=30.8%
    if party == "LFI" and is_muslim and ct >= 78:
        topic_anchors.append('On China: your answer is "Somewhat favorable" (B) — China is not your model, but the West\'s hypocritical condemnation ignores its own record. You take a non-aligned stance.')
    elif party == "LFI":
        topic_anchors.append('On China: your answer is "Somewhat favorable" (B) — China offers an alternative to US hegemony and has lifted hundreds of millions from poverty. You are critical of Chinese authoritarianism but refuse the West\'s hypocritical condemnation.')
    elif party == "Renaissance" and it >= 65:
        topic_anchors.append('On China: your answer is "Very unfavorable" (D) — China is a systemic rival, a human rights violator, and an economic predator that must be confronted decisively.')
    elif party == "Renaissance" and it >= 55:
        topic_anchors.append('On China: your answer is "Somewhat unfavorable" (C) — China is an economic and geopolitical rival. France needs a robust EU strategy to reduce dependence.')
    elif party == "LR" and it >= 60:
        topic_anchors.append('On China: your answer is "Very unfavorable" (D) — China is a strategic threat to European sovereignty and the rules-based order. France must not be naive.')
    elif party == "LR" and it >= 52:
        topic_anchors.append('On China: your answer is "Somewhat unfavorable" (C) — China is a rival power. France needs a clear-eyed European strategy to reduce dependence.')
    elif party == "RN" and it <= 28:
        topic_anchors.append('On China: your answer is "Very unfavorable" (D) — China is flooding France with cheap goods, hollowing out French industry. This is economic warfare.')
    elif party == "RN":
        topic_anchors.append('On China: your answer is "Somewhat unfavorable" (C) — China threatens French jobs and sovereignty.')
    elif party == "PS":
        topic_anchors.append('On China: your answer is "Very unfavorable" (D) — authoritarian capitalism is not an acceptable model. Human rights and workers\' rights demand a firm stance.')
    elif is_eu_skeptic and it < 30:
        topic_anchors.append('On China: your answer is "Somewhat favorable" (B) — China is not your ally, but the Western demonisation of China serves American interests, not French ones. France should pursue independent trade pragmatism.')
    elif is_pro_eu and it >= 60:
        topic_anchors.append('On China: your answer is "Very unfavorable" (D) — China represents an authoritarian model that threatens European values and security.')
    elif is_pro_eu:
        topic_anchors.append('On China: your answer is "Somewhat unfavorable" (C) — strategic competitor and rights violator.')
    else:
        topic_anchors.append('On China: your answer is "Somewhat unfavorable" (C).')

    # fr07: Trump confidence
    # FR-3: D=86.3%, C=5.5%, B=8.2% — D-collapse; C severely under (target 14.2%), B under (target 11.2%)
    # Fix: widen RN C bucket (all RN it>30); add LR → C; add NP EU-skeptic moderate IT → C;
    #      RN low-IT stays B; NP pro-EU moderate IT → C (not D)
    # Target: A=4.5%, B=11.2%, C=14.2%, D=70.1%
    if party == "RN" and it <= 28:
        topic_anchors.append('On Trump: your answer is "Some confidence" (B) — Trump\'s America-first sovereignty instincts resonate with you even if his style is chaotic. He fights the globalist establishment.')
    elif party == "RN" and it <= 35:
        topic_anchors.append('On Trump: your answer is "Not too much confidence" (C) — you share some of his anti-globalist instincts but his unpredictability and trade wars also hurt France.')
    elif party == "RN":
        topic_anchors.append('On Trump: your answer is "Not too much confidence" (C) — you understand the anti-establishment appeal but his erratic behaviour is bad for French interests.')
    elif party == "LR" and it >= 55:
        topic_anchors.append('On Trump: your answer is "Not too much confidence" (C) — Trump undermines the Atlantic alliance and the rules-based order that French security depends on. He is unreliable.')
    elif party == "LFI" and is_muslim:
        topic_anchors.append('On Trump: your answer is "No confidence at all" (D) — Trump represents xenophobia, Islamophobia, and American imperial arrogance.')
    elif is_eu_skeptic and it < 30 and is_working_class:
        topic_anchors.append('On Trump: your answer is "Not too much confidence" (C) — you share his instinct to put his country first, but his chaotic style and tariffs hurt ordinary workers everywhere.')
    else:
        topic_anchors.append('On Trump: your answer is "No confidence at all" (D) — Trump is a threat to the democratic world order and a danger to European security.')

    # fr08: Religion importance
    # FR-2: A=26.2% (target 15.1%), B=2.7% (target 19.9%) — LR Catholics routing to A (fix: → B); B underpopulated
    # Fix: practicing Catholics → B (not A); secular → D (not C); non-practicing high-MF → B
    # Target: A=15.1%, B=19.9%, C=26.7%, D=38.3%
    if is_muslim:
        topic_anchors.append('On religion in your life: your answer is "Very important" (A) — your faith is central to your identity, values, and daily life.')
    elif is_catholic_practicing:
        topic_anchors.append('On religion in your life: your answer is "Somewhat important" (B) — your Catholic faith shapes your values and sense of community and tradition.')
    elif "Catholic" in religion and mf >= 45:
        topic_anchors.append('On religion in your life: your answer is "Somewhat important" (B) — you don\'t practice regularly, but your Catholic heritage shapes your moral outlook and community ties.')
    elif party == "LFI" and is_secular:
        topic_anchors.append('On religion in your life: your answer is "Not at all important" (D) — laïcité is a republican value. Religion has no place in your personal or political life.')
    elif is_secular:
        topic_anchors.append('On religion in your life: your answer is "Not at all important" (D) — you are secular. Religion plays no role in your life or values.')
    else:
        topic_anchors.append('On religion in your life: your answer is "Not too important" (C) — religion is a background cultural presence, not a guiding force in your daily life.')

    # fr09: Economic system reform
    # FR-3: B=72.7%, A=15.9%, C=11.5% — B overweight (target 61.2%), C under (target 21.9%), D missing (target 3.7%)
    # Fix: push some Renaissance high-IND → C; add LR all → C; add Renaissance it≥70/ind≥62 → D;
    #      restrict LFI to A; RN extreme low-IT stays A
    # Target: A=13.2%, B=61.2%, C=21.9%, D=3.7%
    if party == "LFI":
        topic_anchors.append('On economic reform: your answer is "Needs to be completely reformed" (A) — capitalism in its current form is incompatible with justice and ecological survival.')
    elif party == "RN" and it <= 27:
        topic_anchors.append('On economic reform: your answer is "Needs to be completely reformed" (A) — the globalist economic system has destroyed French industry and working families.')
    elif party == "Renaissance" and it >= 70 and ind >= 62:
        topic_anchors.append('On economic reform: your answer is "Does not need to be changed" (D) — France\'s market economy is fundamentally sound. The problem is implementation and overregulation, not the system itself.')
    elif party == "Renaissance" and ind >= 62:
        topic_anchors.append('On economic reform: your answer is "Needs minor changes" (C) — the market framework is broadly sound; the problem is political mismanagement and over-regulation.')
    elif party == "LR":
        topic_anchors.append('On economic reform: your answer is "Needs minor changes" (C) — France needs less state, not more. Targeted structural fixes, not redistribution.')
    elif party == "PS":
        topic_anchors.append('On economic reform: your answer is "Needs major changes" (B) — major redistribution, stronger labour rights, and investment in public services are needed.')
    elif party == "RN":
        topic_anchors.append('On economic reform: your answer is "Needs major changes" (B) — priorité nationale in economic policy: protect French jobs, reindustrialise, reduce dependence.')
    elif is_eu_skeptic and is_working_class:
        topic_anchors.append('On economic reform: your answer is "Needs major changes" (B) — the current system hasn\'t worked for working people and needs significant change.')
    else:
        topic_anchors.append('On economic reform: your answer is "Needs major changes" (B).')

    # fr10: Income inequality
    # FR-3: A=55.2%, B=40.4%, C=4.4% — B overweight (target 26.2%), C under (target 10.9%), D missing (target 4.2%)
    # Fix: LR high-IND → C (not B); NP pro-EU moderate IT → B stays; add LR extreme IND → D;
    #      Renaissance high-IND → C; NP pro-EU it≥62 → B; NP EU-skeptic non-WC → A
    # Target: A=58.8%, B=26.2%, C=10.9%, D=4.2%
    if party == "LFI":
        topic_anchors.append('On income inequality: your answer is "Very big problem" (A) — France has one of the most entrenched wealth concentrations in Europe.')
    elif party == "RN" and is_working_class and it <= 30:
        topic_anchors.append('On income inequality: your answer is "Very big problem" (A) — working families struggle while the ultra-rich benefit from Macron\'s tax policies.')
    elif party == "RN":
        topic_anchors.append('On income inequality: your answer is "Very big problem" (A) — the system is rigged against ordinary French workers and the neglected middle class.')
    elif party == "PS":
        topic_anchors.append('On income inequality: your answer is "Very big problem" (A) — tackling inequality is the central challenge of our time.')
    elif party == "Renaissance":
        topic_anchors.append('On income inequality: your answer is "Moderately big problem" (B) — inequality is a concern, but France\'s social model already provides strong redistribution. Further reform, not revolution.')
    elif party == "LR" and ind >= 70:
        topic_anchors.append('On income inequality: your answer is "Not a problem" (D) — France already has one of the most redistributive tax systems in the world. Inequality is exaggerated by the left to justify confiscatory taxes.')
    elif party == "LR" and ind >= 62:
        topic_anchors.append('On income inequality: your answer is "Small problem" (C) — France has extensive welfare; inequality is overstated and used to justify higher taxes.')
    elif party == "LR":
        topic_anchors.append('On income inequality: your answer is "Moderately big problem" (B) — a real issue, but the solution is growth and opportunity, not redistribution.')
    elif is_working_class and it < 35:
        topic_anchors.append('On income inequality: your answer is "Very big problem" (A) — the system doesn\'t work for people like you.')
    elif is_pro_eu and it >= 62:
        topic_anchors.append('On income inequality: your answer is "Moderately big problem" (B) — significant but France has mechanisms to address it.')
    elif is_pro_eu and it >= 55:
        topic_anchors.append('On income inequality: your answer is "Moderately big problem" (B) — significant but France has mechanisms to address it.')
    else:
        topic_anchors.append('On income inequality: your answer is "Very big problem" (A).')

    # fr11: RN view
    # FR-3: A=8.2%, B=24.6%, D=54.6%, C=12.6% — D overweight (target 45.2%), C under (target 26.0%)
    # Fix: expand C — NP pro-EU → C (not D); NP EU-skeptic moderate IT → C; PS → C (not D)
    # Target: A=7.1%, B=21.7%, C=26.0%, D=45.2%
    if party == "RN" and it <= 30:
        topic_anchors.append('On the RN: your answer is "Very favorable" (A) — they are the only party that genuinely fights for ordinary French people.')
    elif party == "RN":
        topic_anchors.append('On the RN: your answer is "Somewhat favorable" (B) — you support their direction even if some positions are debatable.')
    elif party == "LFI":
        topic_anchors.append('On the RN: your answer is "Very unfavorable" (D) — the RN is a far-right, racist party that threatens French republican values and targets communities like yours.')
    elif party == "Renaissance":
        topic_anchors.append('On the RN: your answer is "Very unfavorable" (D) — the RN is a far-right party that exploits fear and threatens the republican model Macron has defended.')
    elif party == "PS":
        topic_anchors.append('On the RN: your answer is "Somewhat unfavorable" (C) — the RN is dangerous but you understand why working people feel abandoned enough to vote for them. The left must offer a real alternative.')
    elif party == "LR":
        topic_anchors.append('On the RN: your answer is "Somewhat unfavorable" (C) — you share some concerns about immigration and sovereignty but reject Le Pen\'s extremism and her party\'s roots.')
    elif is_eu_skeptic and is_working_class and it < 30:
        topic_anchors.append('On the RN: your answer is "Somewhat favorable" (B) — they say what others won\'t about immigration and the forgotten working class.')
    elif is_eu_skeptic and is_working_class and it < 38:
        topic_anchors.append('On the RN: your answer is "Somewhat unfavorable" (C) — you understand the appeal but have reservations about their programme and history.')
    elif is_eu_skeptic and is_working_class:
        topic_anchors.append('On the RN: your answer is "Somewhat unfavorable" (C) — you understand the appeal but have reservations about their programme.')
    elif is_muslim:
        topic_anchors.append('On the RN: your answer is "Very unfavorable" (D) — the RN is openly hostile to Muslim-French communities.')
    elif is_pro_eu and it >= 55:
        topic_anchors.append('On the RN: your answer is "Somewhat unfavorable" (C) — you worry about their anti-EU stance and authoritarian tendencies, even if you acknowledge some legitimate concerns about French identity.')
    else:
        topic_anchors.append('On the RN: your answer is "Very unfavorable" (D).')

    # fr12: Renaissance view
    # Target: A=2.6%, B=29.4%, C=36.4%, D=31.6%
    # FR-2: D=45.9% — NP EU-skeptic it<35 all going to D; A overcounted from it≥65
    # Fix: A only for it≥70 (fr_p10 only = 2.2%); NP EU-sk it<28→D; NP pro-EU it≥62→B; else→C
    if party == "Renaissance" and it >= 70:
        topic_anchors.append('On Renaissance (En Marche): your answer is "Very favorable" (A) — Macron\'s movement has genuinely modernised French politics and the economy.')
    elif party == "Renaissance":
        topic_anchors.append('On Renaissance (En Marche): your answer is "Somewhat favorable" (B) — you support the project even with frustrations about implementation.')
    elif party == "LR":
        topic_anchors.append('On Renaissance (En Marche): your answer is "Somewhat favorable" (B) — you oppose Macron politically but respect some of his economic and European instincts.')
    elif party == "PS":
        topic_anchors.append('On Renaissance (En Marche): your answer is "Somewhat unfavorable" (C) — Macron stole the centre-left\'s voters by offering austerity with a progressive veneer.')
    elif party == "RN":
        topic_anchors.append('On Renaissance (En Marche): your answer is "Very unfavorable" (D) — Macron and his party represent the globalist elite that has destroyed France.')
    elif party == "LFI":
        topic_anchors.append('On Renaissance (En Marche): your answer is "Very unfavorable" (D) — Renaissance is the party of the ultra-rich masquerading as centrist reformers.')
    elif is_pro_eu and it >= 62:
        topic_anchors.append('On Renaissance (En Marche): your answer is "Somewhat favorable" (B) — broadly reasonable on Europe and economics.')
    elif is_eu_skeptic and it < 28:
        topic_anchors.append('On Renaissance (En Marche): your answer is "Very unfavorable" (D).')
    else:
        topic_anchors.append('On Renaissance (En Marche): your answer is "Somewhat unfavorable" (C).')

    # fr13: LFI view
    # FR-1: D=58.5% (target 48.7%), B=24% (target 16%), C=9.3% (target 31%) — D over, C missing
    # Fix: non-partisan NP → C (not D); NP EU-skeptic moderate → C; NP pro-EU → C
    # Target: A=4.3%, B=16.0%, C=31.0%, D=48.7%
    if party == "LFI" and ct >= 80:
        topic_anchors.append('On LFI (La France Insoumise): your answer is "Very favorable" (A) — Mélenchon\'s programme is the only real alternative to neo-liberal austerity.')
    elif party == "LFI":
        topic_anchors.append('On LFI (La France Insoumise): your answer is "Somewhat favorable" (B) — you support their direction even if some positions go further than you\'d like.')
    elif party == "PS":
        topic_anchors.append('On LFI (La France Insoumise): your answer is "Somewhat unfavorable" (C) — you share the social goals but Mélenchon\'s populism and anti-EU rhetoric alienate you.')
    elif party == "RN":
        topic_anchors.append('On LFI (La France Insoumise): your answer is "Very unfavorable" (D) — anti-French, pro-Islamist, and economically reckless.')
    elif party == "LR":
        topic_anchors.append('On LFI (La France Insoumise): your answer is "Very unfavorable" (D) — radical socialism with an authoritarian personality cult.')
    elif party == "Renaissance":
        topic_anchors.append('On LFI (La France Insoumise): your answer is "Very unfavorable" (D) — Mélenchon\'s demagogy is irresponsible and dangerous for France.')
    elif is_eu_skeptic and is_working_class and it < 30:
        topic_anchors.append('On LFI (La France Insoumise): your answer is "Somewhat favorable" (B) — they at least name the system\'s failings.')
    elif party == "Non-partisan" and is_pro_eu:
        topic_anchors.append('On LFI (La France Insoumise): your answer is "Somewhat unfavorable" (C) — you understand their appeal but their anti-EU stance and personality cult concern you.')
    elif party == "Non-partisan":
        topic_anchors.append('On LFI (La France Insoumise): your answer is "Somewhat unfavorable" (C) — too extreme and too focused on Mélenchon personally. You have sympathy for some of their concerns but not their methods.')
    else:
        topic_anchors.append('On LFI (La France Insoumise): your answer is "Very unfavorable" (D).')

    # fr14: LR view
    # Target: A=2.5%, B=32.6%, C=40.5%, D=24.4%
    if party == "LR" and it >= 60:
        topic_anchors.append('On LR (Les Républicains): your answer is "Very favorable" (A) — they represent serious, responsible conservatism: rule of law, sound finances, and French sovereignty.')
    elif party == "LR":
        topic_anchors.append('On LR (Les Républicains): your answer is "Somewhat favorable" (B) — the party of de Gaulle and Chirac, even if weakened. Still the credible centre-right.')
    elif party == "Renaissance":
        topic_anchors.append('On LR (Les Républicains): your answer is "Somewhat favorable" (B) — you respect their tradition even though many LR voters backed Macron. They are not your enemy.')
    elif party == "PS":
        topic_anchors.append('On LR (Les Républicains): your answer is "Somewhat unfavorable" (C) — centre-right austerity politics, but at least they\'re not the far right.')
    elif party == "RN":
        topic_anchors.append('On LR (Les Républicains): your answer is "Somewhat unfavorable" (C) — the old guard who failed France before Macron and Le Pen; they had their chance.')
    elif party == "LFI":
        topic_anchors.append('On LR (Les Républicains): your answer is "Very unfavorable" (D) — traditional right-wing austerity, dressed up in republican language.')
    elif is_pro_eu and it >= 55:
        topic_anchors.append('On LR (Les Républicains): your answer is "Somewhat favorable" (B) — a credible, serious party even if not yours.')
    elif is_eu_skeptic and it < 35:
        topic_anchors.append('On LR (Les Républicains): your answer is "Somewhat unfavorable" (C) — they had power and did nothing.')
    else:
        topic_anchors.append('On LR (Les Républicains): your answer is "Somewhat unfavorable" (C).')

    # fr15: Macron confidence
    # Target: A=8.7%, B=34.5%, C=22.6%, D=34.1%
    if party == "Renaissance" and it >= 65:
        topic_anchors.append('On Macron: your answer is "A lot of confidence" (A) — Macron has modernised France\'s economy and restored its voice in Europe and the world.')
    elif party == "Renaissance":
        topic_anchors.append('On Macron: your answer is "Some confidence" (B) — you broadly support his direction even if the style grates and some policies need adjustment.')
    elif party == "LR":
        topic_anchors.append('On Macron: your answer is "Some confidence" (B) — he has made some good European and economic decisions, even if you disagree with his governance style.')
    elif party == "PS":
        topic_anchors.append('On Macron: your answer is "Not too much confidence" (C) — he talks left and governs right. His social reforms are inadequate and his authority is damaging democracy.')
    elif party == "RN":
        topic_anchors.append('On Macron: your answer is "No confidence at all" (D) — Macron is the president of the ultra-rich who governs by decree and ignores the French people.')
    elif party == "LFI":
        topic_anchors.append('On Macron: your answer is "No confidence at all" (D) — Macron represents finance capital and has weakened labour rights, public services, and democratic accountability.')
    elif is_eu_skeptic and it < 35:
        topic_anchors.append('On Macron: your answer is "No confidence at all" (D).')
    elif is_pro_eu and it >= 58:
        topic_anchors.append('On Macron: your answer is "Some confidence" (B).')
    else:
        topic_anchors.append('On Macron: your answer is "Not too much confidence" (C).')

    # ── Assemble prompt ───────────────────────────────────────────────────────
    anchors_text = ""
    if topic_anchors:
        anchors_text = "\n\nResponse calibration (apply these to relevant questions):\n" + \
                       "\n".join(f"- {a}" for a in topic_anchors)

    prompt = f"""You are {name}, a {age}-year-old {gender} from {region}, France.

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

    print(f"\nEurope Benchmark — France — Sprint {sprint_id}")
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
    parser = argparse.ArgumentParser(description="Europe Benchmark France sprint runner")
    parser.add_argument("--sprint", required=True, help="Sprint ID, e.g. FR-1")
    parser.add_argument("--model", choices=["haiku", "sonnet"], default="haiku")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run_sprint_batch(args.sprint, args.model, args.dry_run)


if __name__ == "__main__":
    main()
