#!/usr/bin/env python3
"""
sprint_runner.py — Europe Benchmark · Italy calibration sprint runner.

Usage:
    python3 sprint_runner.py --sprint IT-1 --model haiku
    python3 sprint_runner.py --sprint IT-1 --model haiku --dry-run

WorldviewAnchor dimensions (0–100 scale):
    IT  — Institutional Trust
    IND — Individualism (market vs. state preference)
    CT  — Change Tolerance
    MF  — Moral Foundationalism

Key Italy calibration axes:
    1. Coalition: FdI (Meloni, nationalist-conservative) + Lega + Forza Italia vs PD + M5S
    2. North/South (Mezzogiorno) divide: Lega Northern autonomy; Southern disengagement
    3. Post-fascist legacy of FdI; Berlusconi heritage in Forza Italia
    4. Religion: Catholic dominant but declining; South more devout; secular North
    5. EU: 65% favorable despite Eurosceptic government — population ≠ elites
    6. Russia: 15% favorable — elevated vs. Western Europe; Berlusconi–Putin ties; M5S ambivalence
    7. Economic stagnation, high debt, COVID aftermath shape economic pessimism
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
# Demographic targets (Istituto Cattaneo / Pew / Italian Election Studies):
#   Parties:  FdI ~15%, Lega ~10%, Forza Italia ~10%,
#             PD ~17.5%, M5S ~12.5%, Non-partisan ~35%
#   Region:   Milan/Lombardia ~16%, Rome/Lazio ~10%, Naples/Campania ~9%,
#             Turin/Piemonte ~7%, Bologna/Emilia-Romagna ~5%, Venice/Veneto ~5%,
#             Florence/Toscana ~5%, Palermo/Sicily ~8%, Other ~35%
#   Religion: Catholic (inc. non-practicing) ~68%, Secular ~28%, Other ~4%
#   Education: Laurea/Masters ~20%, Diploma liceo/tecnico ~45%, Vocational/scuola media ~35%
#   EU attitude: broadly pro-EU ~65%, skeptical ~35%
#   Age range: 26–72

PERSONAS = [
    # ── FdI (Fratelli d'Italia — nationalist-conservative, Meloni coalition) ────
    ("it_p01", "Salvatore Esposito",   54, "male",   "Italy (Naples / Campania)",             "FdI",          "EU-skeptic", "Catholic (practicing)",     "Diploma tecnico",   2.5),
    ("it_p02", "Rosaria Ferrara",      49, "female", "Italy (Rome / Lazio)",                  "FdI",          "EU-skeptic", "Catholic (practicing)",     "Diploma liceo",     2.5),
    ("it_p03", "Antonio Greco",        61, "male",   "Italy (Palermo / Sicily)",              "FdI",          "EU-skeptic", "Catholic (practicing)",     "Vocational/media",  2.5),
    ("it_p04", "Giovanna Ricci",       47, "female", "Italy (Rome / Lazio)",                  "FdI",          "EU-skeptic", "Catholic (non-practicing)", "Diploma tecnico",   2.5),
    ("it_p05", "Marco Conti",          58, "male",   "Italy (Naples / Campania)",             "FdI",          "EU-skeptic", "Catholic (non-practicing)", "Vocational/media",  2.5),
    ("it_p06", "Lucia Lombardi",       42, "female", "Italy (Florence / Toscana)",            "FdI",          "EU-skeptic", "Catholic (non-practicing)", "Diploma liceo",     2.5),

    # ── Lega (Northern League — Padanian autonomy, anti-immigration) ─────────
    ("it_p07", "Roberto Fontana",      55, "male",   "Italy (Milan / Lombardia)",             "Lega",         "EU-skeptic", "Catholic (non-practicing)", "Diploma tecnico",   2.5),
    ("it_p08", "Claudia Bianchi",      48, "female", "Italy (Venice / Veneto)",               "Lega",         "EU-skeptic", "Catholic (non-practicing)", "Diploma tecnico",   2.5),
    ("it_p09", "Giorgio Sala",         62, "male",   "Italy (Turin / Piemonte)",              "Lega",         "EU-skeptic", "None/secular",              "Vocational/media",  2.5),
    ("it_p10", "Federica Colombo",     44, "female", "Italy (Milan / Lombardia)",             "Lega",         "EU-skeptic", "Catholic (non-practicing)", "Diploma liceo",     2.5),

    # ── Forza Italia (Berlusconi centre-right, business class) ───────────────
    ("it_p11", "Giancarlo Mancini",    66, "male",   "Italy (Milan / Lombardia)",             "ForzaItalia",  "Pro-EU",     "Catholic (non-practicing)", "Laurea/Masters",    2.0),
    ("it_p12", "Silvana De Luca",      61, "female", "Italy (Rome / Lazio)",                  "ForzaItalia",  "Pro-EU",     "Catholic (practicing)",     "Diploma liceo",     2.5),
    ("it_p13", "Enrico Ferretti",      58, "male",   "Italy (Turin / Piemonte)",              "ForzaItalia",  "Pro-EU",     "Catholic (non-practicing)", "Laurea/Masters",    2.0),
    ("it_p14", "Margherita Vitale",    53, "female", "Italy (Naples / Campania)",             "ForzaItalia",  "Pro-EU",     "Catholic (practicing)",     "Diploma tecnico",   2.5),

    # ── PD (Partito Democratico — centre-left, urban, educated, pro-EU) ──────
    ("it_p15", "Francesca Moretti",    38, "female", "Italy (Bologna / Emilia-Romagna)",      "PD",           "Pro-EU",     "None/secular",              "Laurea/Masters",    2.0),
    ("it_p16", "Alessandro Caruso",    45, "male",   "Italy (Milan / Lombardia)",             "PD",           "Pro-EU",     "None/secular",              "Laurea/Masters",    2.0),
    ("it_p17", "Elena Santoro",        52, "female", "Italy (Florence / Toscana)",            "PD",           "Pro-EU",     "None/secular",              "Laurea/Masters",    2.0),
    ("it_p18", "Daniele Ruggiero",     41, "male",   "Italy (Rome / Lazio)",                  "PD",           "Pro-EU",     "None/secular",              "Laurea/Masters",    2.0),
    ("it_p19", "Chiara Ferraro",       34, "female", "Italy (Bologna / Emilia-Romagna)",      "PD",           "Pro-EU",     "None/secular",              "Laurea/Masters",    2.0),
    ("it_p20", "Matteo Bernardi",      57, "male",   "Italy (Florence / Toscana)",            "PD",           "Pro-EU",     "Catholic (non-practicing)", "Diploma liceo",     2.0),
    ("it_p21", "Silvia Amato",         47, "female", "Italy (Turin / Piemonte)",              "PD",           "Pro-EU",     "None/secular",              "Laurea/Masters",    2.0),

    # ── M5S (Movimento 5 Stelle — populist, anti-establishment, cross-cutting)
    ("it_p22", "Giuseppe Marino",      43, "male",   "Italy (Naples / Campania)",             "M5S",          "EU-skeptic", "None/secular",              "Diploma tecnico",   2.5),
    ("it_p23", "Valentina Palumbo",    36, "female", "Italy (Rome / Lazio)",                  "M5S",          "EU-skeptic", "Catholic (non-practicing)", "Diploma liceo",     2.5),
    ("it_p24", "Carmelo Russo",        50, "male",   "Italy (Palermo / Sicily)",              "M5S",          "EU-skeptic", "Catholic (non-practicing)", "Vocational/media",  2.5),
    ("it_p25", "Sara Monti",           31, "female", "Italy (Milan / Lombardia)",             "M5S",          "EU-skeptic", "None/secular",              "Laurea/Masters",    2.0),
    ("it_p26", "Luca De Santis",       39, "male",   "Italy (Rome / Lazio)",                  "M5S",          "EU-skeptic", "None/secular",              "Diploma liceo",     2.5),

    # ── Non-partisan / disengaged (mix of North/South, ages, backgrounds) ────
    ("it_p27", "Carmela Sorrentino",   59, "female", "Italy (Naples / Campania)",             "Non-partisan", "EU-skeptic", "Catholic (practicing)",     "Vocational/media",  2.5),
    ("it_p28", "Bruno Marchetti",      64, "male",   "Italy (Rome / Lazio)",                  "Non-partisan", "EU-skeptic", "Catholic (non-practicing)", "Vocational/media",  2.5),
    ("it_p29", "Annalisa Galli",       37, "female", "Italy (Milan / Lombardia)",             "Non-partisan", "Pro-EU",     "None/secular",              "Laurea/Masters",    2.0),
    ("it_p30", "Francesco Caputo",     52, "male",   "Italy (Palermo / Sicily)",              "Non-partisan", "EU-skeptic", "Catholic (practicing)",     "Vocational/media",  2.5),
    ("it_p31", "Patrizia Longo",       46, "female", "Italy (Naples / Campania)",             "Non-partisan", "EU-skeptic", "Catholic (practicing)",     "Diploma tecnico",   2.5),
    ("it_p32", "Stefano Martini",      68, "male",   "Italy (Bologna / Emilia-Romagna)",      "Non-partisan", "Pro-EU",     "Catholic (non-practicing)", "Diploma liceo",     2.5),
    ("it_p33", "Maria Grazia Coppola", 72, "female", "Italy (Palermo / Sicily)",              "Non-partisan", "EU-skeptic", "Catholic (practicing)",     "Vocational/media",  2.5),
    ("it_p34", "Davide Barbieri",      29, "male",   "Italy (Milan / Lombardia)",             "Non-partisan", "Pro-EU",     "None/secular",              "Laurea/Masters",    2.0),
    ("it_p35", "Teresa Rizzo",         55, "female", "Italy (Venice / Veneto)",               "Non-partisan", "EU-skeptic", "Catholic (non-practicing)", "Diploma tecnico",   2.5),
    ("it_p36", "Angelo Parisi",        48, "male",   "Italy (Turin / Piemonte)",              "Non-partisan", "EU-skeptic", "None/secular",              "Vocational/media",  2.5),
    ("it_p37", "Nadia Fabbri",         41, "female", "Italy (Florence / Toscana)",            "Non-partisan", "Pro-EU",     "None/secular",              "Diploma liceo",     2.0),
    ("it_p38", "Vincenzo Aiello",      63, "male",   "Italy (Palermo / Sicily)",              "Non-partisan", "EU-skeptic", "Catholic (practicing)",     "Vocational/media",  2.5),
    ("it_p39", "Laura Gentile",        33, "female", "Italy (Rome / Lazio)",                  "Non-partisan", "Pro-EU",     "None/secular",              "Diploma liceo",     2.0),
    ("it_p40", "Massimo Pellegrini",   57, "male",   "Italy (Naples / Campania)",             "Non-partisan", "EU-skeptic", "Catholic (non-practicing)", "Vocational/media",  2.5),
]

# ── WorldviewAnchor values ────────────────────────────────────────────────────
WORLDVIEW = {
    # id:        (IT,  IND, CT,  MF)
    # FdI — moderate IT (trust Meloni govt), high-moderate IND, low CT, high MF (Catholic-nationalist)
    "it_p01": (52,  60,  22,  68),   # FdI, Naples, practicing Catholic, vocational, Southern
    "it_p02": (50,  62,  28,  62),   # FdI, Rome, practicing Catholic, liceo
    "it_p03": (47,  58,  20,  72),   # FdI, Sicily, practicing Catholic, vocational, oldest/most devout
    "it_p04": (55,  64,  32,  55),   # FdI, Rome, non-practicing Catholic, tecnico
    "it_p05": (48,  60,  25,  58),   # FdI, Naples, non-practicing Catholic, vocational
    "it_p06": (58,  65,  30,  50),   # FdI, Florence, non-practicing Catholic, liceo (more urban)

    # Lega — moderate IT, high IND (market/Northern autonomy), low CT, moderate MF
    "it_p07": (48,  68,  22,  52),   # Lega, Milan, non-practicing Catholic, Northern entrepreneur
    "it_p08": (45,  65,  20,  55),   # Lega, Venice, non-practicing Catholic, Padanian identity
    "it_p09": (40,  70,  18,  32),   # Lega, Turin, secular, older industrial worker (Padania resentment)
    "it_p10": (52,  64,  28,  48),   # Lega, Milan, non-practicing Catholic, working professional

    # Forza Italia — moderate-high IT, high IND, low-moderate CT, moderate MF (Berlusconi heritage)
    "it_p11": (62,  72,  30,  42),   # FI, Milan, non-practicing Catholic, business class, oldest
    "it_p12": (60,  68,  28,  55),   # FI, Rome, practicing Catholic, Berlusconi loyalist
    "it_p13": (65,  70,  32,  40),   # FI, Turin, non-practicing Catholic, industrial/business
    "it_p14": (58,  65,  25,  58),   # FI, Naples, practicing Catholic, Southern moderate-right

    # PD — high IT, low-moderate IND, high CT, low MF (pro-EU, progressive, secular)
    "it_p15": (65,  42,  68,  14),   # PD, Bologna, secular, young female academic
    "it_p16": (62,  40,  65,  12),   # PD, Milan, secular, urban professional
    "it_p17": (68,  45,  62,  15),   # PD, Florence, secular, older female (Tuscany left tradition)
    "it_p18": (60,  38,  70,  12),   # PD, Rome, secular, younger male
    "it_p19": (66,  40,  72,  10),   # PD, Bologna, secular, youngest female
    "it_p20": (55,  48,  58,  28),   # PD, Florence, non-practicing Catholic, older male (ex-PCI tradition)
    "it_p21": (63,  42,  65,  14),   # PD, Turin, secular, female professional

    # M5S — low IT, low-moderate IND, moderate-high CT, low-moderate MF (anti-establishment, populist)
    "it_p22": (28,  38,  60,  35),   # M5S, Naples, secular, Southern disillusionment
    "it_p23": (32,  42,  58,  38),   # M5S, Rome, non-practicing Catholic, young woman
    "it_p24": (25,  35,  55,  42),   # M5S, Sicily, non-practicing Catholic, older, most anti-establishment
    "it_p25": (38,  45,  65,  18),   # M5S, Milan, secular, young female (more progressive M5S)
    "it_p26": (35,  40,  62,  22),   # M5S, Rome, secular, younger male

    # Non-partisan — wide spread, skewed toward South/older/lower IT
    "it_p27": (30,  38,  22,  68),   # NP, Naples, practicing Catholic, Southern matriarch (most devout NP)
    "it_p28": (28,  48,  18,  48),   # NP, Rome, non-practicing Catholic, older disengaged
    "it_p29": (60,  55,  65,  12),   # NP, Milan, secular, young female professional (Northern pro-EU)
    "it_p30": (25,  40,  20,  65),   # NP, Sicily, practicing Catholic, older Southern (most disengaged)
    "it_p31": (32,  42,  25,  62),   # NP, Naples, practicing Catholic, Southern householder
    "it_p32": (55,  50,  38,  28),   # NP, Bologna, non-practicing Catholic, older moderate (Red Belt)
    "it_p33": (22,  38,  15,  72),   # NP, Sicily, practicing Catholic, oldest persona (most traditional)
    "it_p34": (62,  58,  70,  10),   # NP, Milan, secular, young male (Northern, educated, pro-EU)
    "it_p35": (42,  55,  25,  48),   # NP, Venice, non-practicing Catholic, small-business owner
    "it_p36": (35,  52,  22,  30),   # NP, Turin, secular, industrial worker
    "it_p37": (58,  52,  60,  15),   # NP, Florence, secular, female professional (Tuscan left tradition)
    "it_p38": (20,  40,  14,  70),   # NP, Sicily, practicing Catholic, oldest male (most disengaged)
    "it_p39": (56,  50,  62,  16),   # NP, Rome, secular, young female professional
    "it_p40": (30,  48,  22,  52),   # NP, Naples, non-practicing Catholic, middle-aged worker
}


def build_system_prompt(persona: tuple) -> str:
    pid, name, age, gender, region, party, eu_ref, religion, education, weight = persona
    it, ind, ct, mf = WORLDVIEW[pid]

    is_milan       = "Milan" in region or "Lombardia" in region
    is_rome        = "Rome" in region or "Lazio" in region
    is_naples      = "Naples" in region or "Campania" in region
    is_sicily      = "Palermo" in region or "Sicily" in region
    is_north       = is_milan or "Turin" in region or "Piemonte" in region or "Venice" in region or "Veneto" in region or "Bologna" in region or "Emilia" in region
    is_south       = is_naples or is_sicily
    is_tuscany     = "Florence" in region or "Toscana" in region
    is_eu_skeptic  = eu_ref == "EU-skeptic"
    is_pro_eu      = eu_ref == "Pro-EU"
    is_catholic_practicing = "practicing" in religion and "non" not in religion
    is_secular     = "secular" in religion or "None" in religion
    is_working_class = "Vocational" in education or "media" in education
    is_business    = party == "ForzaItalia" and ind >= 68

    # ── Institutional trust descriptor ────────────────────────────────────────
    if it < 35:
        it_desc = (
            "You have very low trust in Italian institutions — the parties, the parliament, "
            "the media. The political class (la casta) has governed for itself, not for "
            "ordinary Italians. Corruption, clientelism, and decay feel endemic."
        )
    elif it < 52:
        it_desc = (
            "You have mixed trust in Italian institutions. You see real dysfunction and "
            "systemic problems, but still believe Italy can be reformed from within — "
            "even if progress is agonisingly slow."
        )
    elif it < 65:
        it_desc = (
            "You have moderate trust in Italian institutions. You are realistic about "
            "Italy's chronic governance problems but broadly believe in its constitutional "
            "order and, for now, the direction of the Meloni government."
        )
    else:
        it_desc = (
            "You have relatively high trust in Italian institutions. The rule of law, "
            "democratic process, and European cooperation matter deeply to you. "
            "You see Italy's problems as manageable within a functioning democratic system."
        )

    # ── EU/Europe layer ────────────────────────────────────────────────────────
    if is_pro_eu:
        eu_layer = (
            "\nEurope: You are broadly pro-European. You see the EU as essential for Italy's "
            "prosperity, stability, and credibility. Italy's future lies in deeper European "
            "integration, not in the nationalist fantasies of sovereigntists. "
            "The EU's recovery funds (PNRR) show what cooperation can achieve."
        )
    else:
        eu_layer = (
            "\nEurope: You are skeptical of the EU. Brussels imposes austerity, takes away "
            "sovereignty, and protects northern European interests over Italian ones. "
            "The EU's response to Italy's debt and immigration pressures has been deeply "
            "unfair. You want Italy's national interests defended first."
        )

    # ── Party political identity ───────────────────────────────────────────────
    ova_map = {
        "FdI": (
            "Italy needs to be governed with pride and backbone. Giorgia Meloni's "
            "Fratelli d'Italia represents a patriotic Italy — strong borders, Italian "
            "families first, cultural identity protected, and a government that actually "
            "governs. The left has dominated Italian culture for too long. "
            "You believe in Italy's sovereignty, Catholic roots, and national dignity. "
            "Post-fascist accusations don't define you — patriotism does."
        ),
        "Lega": (
            "The North produces, the South consumes, and Rome wastes. Salvini's Lega "
            "represents Northern Italy — hard-working, productive, resentful of fiscal "
            "transfers and Roman bureaucracy. You want less taxation, stricter immigration "
            "control, and federalist autonomy for Lombardia and Padania. "
            "The South's problems are not yours to solve."
        ),
        "ForzaItalia": (
            "Berlusconi built modern Italian centre-right politics — market economics, "
            "lower taxes, anti-communism, and pro-Americanism. Forza Italia represents "
            "the business class, the professional middle class, and moderate conservatives "
            "who want a functional, stable Italy integrated in Europe. "
            "You respect Berlusconi's legacy and distrust both the far-right and the left."
        ),
        "PD": (
            "Italy's future lies in progressive politics, European solidarity, and "
            "investment in education, culture, and social rights. The Partito Democratico "
            "stands for workers, women's rights, civil liberties, and a social Europe. "
            "Meloni's government represents a dangerous slide toward authoritarianism. "
            "You are deeply pro-EU and believe Italy must be at the heart of European "
            "integration, not sabotaging it."
        ),
        "M5S": (
            "The entire political class has failed Italians — left and right. "
            "The Movimento 5 Stelle was born from the rage of citizens against la casta, "
            "corruption, and a system that serves elites while citizens struggle. "
            "You are anti-establishment, suspicious of both NATO narratives and EU austerity, "
            "and believe in direct democracy and citizens' income. "
            "The system must be disrupted, not tinkered with."
        ),
        "Non-partisan": (
            "no single party represents your views. You are disillusioned with Italian "
            "politics — le solite facce, le solite promesse. You vote out of habit or "
            "not at all. Politicians are all the same: corrupt, self-interested, "
            "and disconnected from the lives of ordinary Italians."
        ),
    }
    ova = ova_map.get(party, "")

    # ── Religion layer ────────────────────────────────────────────────────────
    religion_layer = ""
    if is_catholic_practicing:
        if is_south:
            religion_layer = (
                "\nFaith and identity: You are a devout Catholic and your faith is central "
                "to your daily life — Mass, family, the saints, the Madonna. "
                "In the South, faith is woven into culture, community, and identity. "
                "You believe Italy must protect its Catholic heritage. "
                "You worry about secularism and the erosion of traditional family values."
            )
        else:
            religion_layer = (
                "\nFaith and identity: You are a practising Catholic. "
                "Your faith informs your social values — family, community, moral responsibility. "
                "You believe Italy's Christian roots matter and that the Church still plays "
                "an important role in public life."
            )
    elif is_secular:
        religion_layer = (
            "\nFaith and identity: You are secular and religion plays little or no role "
            "in your life. You are broadly liberal on social questions and wary of "
            "the Catholic Church's influence on Italian politics and policy."
        )

    # ── Regional layer ────────────────────────────────────────────────────────
    region_layer = ""
    if is_milan:
        region_layer = (
            "\nRegional background: You are from Milan or Lombardia — the economic engine "
            "of Italy. Milan is cosmopolitan, internationally connected, and proud of "
            "its productivity. You resent Rome's bureaucracy and the fiscal drain southward. "
            "You identify more with European business culture than with traditional Italian politics."
        )
    elif is_north and not is_milan and not is_tuscany:
        region_layer = (
            "\nRegional background: You are from Northern Italy — "
            "Piemonte, Veneto, or Emilia-Romagna. The North has historically driven "
            "Italy's economic success and has strong regional identities. "
            "There is real resentment of fiscal centralisation and Roman waste."
        )
    elif is_tuscany:
        region_layer = (
            "\nRegional background: You are from Tuscany — historically part of the "
            "'Red Belt' of left-wing Italy, though this has weakened. Florence is "
            "culturally sophisticated and more progressive than the national average. "
            "The Tuscan tradition of civic republicanism shapes your political identity."
        )
    elif is_naples:
        region_layer = (
            "\nRegional background: You are from Naples or Campania — a region of "
            "extraordinary culture but also chronic unemployment, organised crime (Camorra), "
            "and dependence on state transfers. You navigate daily life in a system "
            "that does not work well. Disillusionment with politics is near-universal. "
            "Faith, family, and local community are what actually hold things together."
        )
    elif is_sicily:
        region_layer = (
            "\nRegional background: You are from Sicily — the most extreme expression "
            "of Italy's North-South divide. Chronic underdevelopment, Mafia presence, "
            "emigration of young people, and a sense that Rome and Brussels have forgotten "
            "you. Family and Catholic faith provide the social fabric where the state fails."
        )

    # ── Lega-specific Northern autonomy layer ────────────────────────────────
    northern_autonomy_layer = ""
    if party == "Lega":
        northern_autonomy_layer = (
            "\nNorthern identity: You have a strong Padanian or Northern Italian identity. "
            "The North subsidises the South and Rome wastes the money. "
            "You want fiscal federalism — Northern taxes for Northern services. "
            "Immigration into Northern Italian cities is a tangible daily concern "
            "that the political class in Rome refuses to address seriously."
        )

    # ── Topic-specific option-vocabulary anchors ──────────────────────────────
    topic_anchors = []

    # it01: Economic conditions
    # Target: A=0.8%, B=24.6%, C=51.8%, D=22.7%
    # FIX (IT-3): B=0% — no B routes existed. PD, ForzaItalia, Lega moderate should → B.
    # FIX (IT-4): D=34.4% too high (target 22.7%); C=31.7% too low (target 51.8%).
    #   South+working_class route was sending ALL Southern NP workers to D; tighten to it<35.
    #   Add NP EU-skeptic working-class default to C, not D.
    if party == "M5S" or (is_working_class and it < 28):
        topic_anchors.append('On Italy\'s economic situation: your answer is "Very bad" (D) — Italy has been in stagnation for decades. The PNRR money disappears into bureaucracy. The economic system does not work for ordinary people.')
    elif is_south and is_working_class and it < 35:
        topic_anchors.append('On Italy\'s economic situation: your answer is "Very bad" (D) — in the Mezzogiorno, there is no recovery. Youth emigrate north or abroad. The South has been structurally abandoned for generations.')
    elif party == "PD":
        topic_anchors.append('On Italy\'s economic situation: your answer is "Somewhat good" (B) — the PNRR, minimum wage debate, and post-COVID recovery show real progress. Italy\'s labour market is improving and EU funds are arriving.')
    elif party == "ForzaItalia":
        topic_anchors.append('On Italy\'s economic situation: your answer is "Somewhat good" (B) — Italian business has recovered well post-COVID. The fundamentals are stronger than the pessimists claim; what\'s needed is deregulation and tax cuts.')
    elif party == "Lega" and it >= 50:
        topic_anchors.append('On Italy\'s economic situation: your answer is "Somewhat good" (B) — Northern Italian manufacturing and exports are doing well; the challenge is making this recovery reach the centre-south.')
    elif party in ("FdI", "Lega"):
        topic_anchors.append('On Italy\'s economic situation: your answer is "Somewhat bad" (C) — years of misgovernance and EU fiscal constraints have damaged Italy\'s potential. The Meloni government is trying, but structural problems remain.')
    elif is_pro_eu and it >= 58:
        topic_anchors.append('On Italy\'s economic situation: your answer is "Somewhat good" (B) — the PNRR and EU recovery funds offer a real path forward; Italy\'s trajectory is cautiously positive for the first time in years.')
    elif is_south and is_working_class:
        topic_anchors.append('On Italy\'s economic situation: your answer is "Somewhat bad" (C) — the South is still struggling: few jobs, precarious contracts, young people leaving. The recovery has not reached us.')
    else:
        topic_anchors.append('On Italy\'s economic situation: your answer is "Somewhat bad" (C) — structural problems persist: housing costs, youth unemployment, North-South divide. The recovery is uneven.')

    # it02: Democracy satisfaction
    # Target: A=4.3%, B=31.3%, C=39.8%, D=24.5%
    if party == "M5S" and it < 35:
        topic_anchors.append('On democracy in Italy: your answer is "Not at all satisfied" (D) — Italian democracy is captured by la casta, lobbyists, and the same corrupt faces recycled for decades.')
    elif party == "M5S":
        topic_anchors.append('On democracy in Italy: your answer is "Not too satisfied" (C) — the democratic system is dysfunctional and needs radical citizen-led reform.')
    elif party == "FdI" and it >= 55:
        topic_anchors.append('On democracy in Italy: your answer is "Somewhat satisfied" (B) — for the first time in years, Italy has a stable government with a genuine popular mandate.')
    elif party == "FdI":
        topic_anchors.append('On democracy in Italy: your answer is "Not too satisfied" (C) — the previous decades of instability and technocratic government were a democratic failure.')
    elif party == "Lega" and it <= 45:
        topic_anchors.append('On democracy in Italy: your answer is "Not too satisfied" (C) — the political system has failed Northern Italy. Real federalism and popular sovereignty are suppressed.')
    elif party == "Lega":
        topic_anchors.append('On democracy in Italy: your answer is "Somewhat satisfied" (B) — the coalition is moving things in the right direction.')
    elif party == "PD" and it >= 65:
        topic_anchors.append('On democracy in Italy: your answer is "Not too satisfied" (C) — Meloni\'s government is eroding democratic norms and attacking independent institutions.')
    elif party == "PD":
        topic_anchors.append('On democracy in Italy: your answer is "Not too satisfied" (C) — Italian democracy has been weakened by decades of Berlusconi and now by FdI\'s nationalist turn.')
    elif party == "ForzaItalia":
        topic_anchors.append('On democracy in Italy: your answer is "Somewhat satisfied" (B) — Italy has a functioning democracy; the current coalition reflects the popular will.')
    elif is_working_class and it < 35:
        topic_anchors.append('On democracy in Italy: your answer is "Not at all satisfied" (D).')
    elif is_pro_eu and it >= 58:
        topic_anchors.append('On democracy in Italy: your answer is "Somewhat satisfied" (B).')
    else:
        topic_anchors.append('On democracy in Italy: your answer is "Not too satisfied" (C).')

    # it03: Russia view
    # Target: A=3.6%, B=11.4%, C=32.8%, D=52.2%
    # NOTE: 15% favorable — elevated vs Western Europe; Berlusconi-Putin ties; M5S ambivalence
    if party == "ForzaItalia" and it >= 58:
        topic_anchors.append('On Russia: your answer is "Somewhat unfavorable" (C) — the invasion was wrong, but Italy has deep historical and economic ties with Russia that must eventually be rebuilt. Berlusconi understood this.')
    elif party == "ForzaItalia":
        topic_anchors.append('On Russia: your answer is "Somewhat favorable" (B) — Berlusconi maintained that dialogue with Russia was always the right approach. The war is a tragedy that diplomacy should have prevented.')
    elif party == "M5S" and it <= 32:
        topic_anchors.append('On Russia: your answer is "Somewhat favorable" (B) — you oppose the invasion but also oppose NATO escalation. Russia has legitimate security concerns. Neither side is innocent.')
    elif party == "M5S":
        topic_anchors.append('On Russia: your answer is "Somewhat unfavorable" (C) — the invasion is wrong, but Italy should not be dragged into an American-led proxy war. Negotiation, not weapons.')
    elif party in ("FdI", "Lega") and it <= 48:
        topic_anchors.append('On Russia: your answer is "Somewhat unfavorable" (C) — you condemn the invasion but believe dialogue must eventually resume. Italian-Russian energy ties were real.')
    elif party in ("FdI", "Lega"):
        topic_anchors.append('On Russia: your answer is "Very unfavorable" (D) — the invasion of Ukraine is a war crime. Italy must stand with NATO and its European partners.')
    elif party == "PD":
        topic_anchors.append('On Russia: your answer is "Very unfavorable" (D) — Putin\'s Russia is an aggressor state and a threat to European democracy. Italy must stand firm with Ukraine.')
    elif is_working_class and is_south and it < 32:
        topic_anchors.append('On Russia: your answer is "Somewhat unfavorable" (C) — you distrust both sides. NATO and Russia are big powers playing games while ordinary people suffer.')
    else:
        topic_anchors.append('On Russia: your answer is "Very unfavorable" (D).')

    # it04: EU view
    # Target: A=19.6%, B=45.5%, C=22.9%, D=12.1%
    # FIX (IT-3): B=23.1% too low; C=34.4% too high. FdI+it>=55 → C was wrong; should → B.
    if party == "PD" and it >= 65:
        topic_anchors.append('On the European Union: your answer is "Very favorable" (A) — the EU is essential for Italy\'s future: PNRR, the euro, the single market. Italy thrives in Europe and must be at the EU\'s core.')
    elif party == "PD":
        topic_anchors.append('On the European Union: your answer is "Very favorable" (A) — Italy belongs at the heart of Europe. EU membership has brought Italy peace, prosperity, and democratic stability.')
    elif party == "ForzaItalia":
        topic_anchors.append('On the European Union: your answer is "Somewhat favorable" (B) — Italy\'s place is in Europe. The single market and euro zone are essential for Italian business and stability. Forza Italia has always been a pro-European party.')
    elif party == "Lega" and it <= 45:
        topic_anchors.append('On the European Union: your answer is "Somewhat unfavorable" (C) — Brussels\' austerity has strangled Northern Italian business. Fiscal rules serve Germany, not Italy.')
    elif party == "Lega":
        topic_anchors.append('On the European Union: your answer is "Somewhat favorable" (B) — despite frustrations with Brussels, Italy needs the single market and the euro. Salvini has moderated his position; pragmatism beats Europhobia.')
    elif party == "FdI":
        topic_anchors.append('On the European Union: your answer is "Somewhat favorable" (B) — Italy is a founding EU member and must remain at the table. Meloni has proven she can work constructively with Brussels even while defending Italian interests.')
    elif party == "M5S" and it <= 30:
        topic_anchors.append('On the European Union: your answer is "Very unfavorable" (D) — the EU imposed austerity that destroyed Italian public services and created a lost generation of young Italians.')
    elif party == "M5S":
        topic_anchors.append('On the European Union: your answer is "Somewhat unfavorable" (C) — the EU in its current form serves banks and elites more than Italian citizens. Major reform is needed.')
    elif is_pro_eu and it >= 55:
        topic_anchors.append('On the European Union: your answer is "Very favorable" (A) — Italy\'s prosperity and democratic security depend on the EU.')
    elif is_pro_eu:
        topic_anchors.append('On the European Union: your answer is "Somewhat favorable" (B) — the EU has real benefits for Italy even with its flaws.')
    elif is_eu_skeptic and it <= 30:
        topic_anchors.append('On the European Union: your answer is "Somewhat unfavorable" (C) — Brussels has imposed constraints on Italy that serve creditor nations, not Italian workers.')
    else:
        topic_anchors.append('On the European Union: your answer is "Somewhat favorable" (B) — even with reservations, the EU matters for Italy\'s economic future.')

    # it05: NATO view
    # Target: A=13.9%, B=48.8%, C=23.8%, D=13.5%
    # FIX (IT-3): D=0% — no D routes; C=45.2% too high; A=6.5% too low.
    # Fix: PD ALL → A; M5S → D for low-IT; FdI/Lega+low-IT → C only.
    if party == "PD":
        topic_anchors.append('On NATO: your answer is "Very favorable" (A) — NATO is essential for Europe\'s security. Italy must be a committed and active member. The transatlantic alliance is the foundation of Italian security policy.')
    elif party == "M5S" and it <= 32:
        topic_anchors.append('On NATO: your answer is "Not at all favorable" (D) — NATO is a tool of American foreign policy that drags Italy into wars that serve Washington, not Italian interests. Italy should pursue real strategic neutrality.')
    elif party == "M5S":
        topic_anchors.append('On NATO: your answer is "Somewhat unfavorable" (C) — deeply sceptical of military escalation. Italy should be a voice for peace and diplomacy, not more weapons and military spending.')
    elif party == "ForzaItalia" and is_pro_eu:
        topic_anchors.append('On NATO: your answer is "Somewhat favorable" (B) — NATO provides collective defence that Italy cannot afford alone. The alliance is imperfect but necessary for Western security.')
    elif party in ("FdI", "Lega") and it >= 52:
        topic_anchors.append('On NATO: your answer is "Somewhat favorable" (B) — Italy must honour its alliance commitments; NATO is the foundation of European security. But Italian strategic interests must be respected within the alliance.')
    elif party in ("FdI", "Lega"):
        topic_anchors.append('On NATO: your answer is "Somewhat unfavorable" (C) — NATO serves American interests more than Italian ones. Italy needs greater strategic independence and should not be dragged into every US-led conflict.')
    elif is_working_class and it < 32:
        topic_anchors.append('On NATO: your answer is "Not at all favorable" (D) — military alliances bring wars, not security, for ordinary Italians. The money spent on defence should go to schools and hospitals.')
    else:
        topic_anchors.append('On NATO: your answer is "Somewhat favorable" (B).')

    # it06: China view
    # Target: A=3.9%, B=28.8%, C=43.5%, D=23.8%
    # FIX (IT-3): B=12.4% too low; C=70.4% too high. ForzaItalia → B (all); PD → D (all).
    # FIX (IT-4): C=63.4% still too high (target 43.5%); B=15.1% still too low (target 28.8%); A=0% (target 3.9%).
    #   Root cause: FdI, Lega, M5S default, NP catch-all all go C. Need B routes for more personas.
    #   FdI moderate (it>=52): soften to B (Italy exited BRI but trade pragmatism remains).
    #   M5S standard: → B (anti-Western-hegemony, pragmatic engagement angle).
    #   NP pro-EU moderate-IT: → C (already there). NP EU-skeptic high-IND: → B.
    #   Add A route: ForzaItalia business class (it>=62, ind>=70) — Italy's luxury/fashion exports depend on China.
    if party == "PD" and it >= 62:
        topic_anchors.append('On China: your answer is "Very unfavorable" (D) — China\'s authoritarianism, Xinjiang persecution, and Belt and Road debt traps are fundamental violations of the values Italy shares with its European partners. Italy was right to exit the BRI.')
    elif party == "PD":
        topic_anchors.append('On China: your answer is "Very unfavorable" (D) — China\'s human rights record, intellectual property theft, and authoritarian model make it a strategic adversary, not a partner. EU solidarity on China policy is essential.')
    elif party == "ForzaItalia" and it >= 62 and ind >= 70:
        topic_anchors.append('On China: your answer is "Very favorable" (A) — China is Italy\'s most important non-EU export destination for luxury, fashion, and machinery. Pragmatic engagement, not Cold War confrontation, serves Italian business.')
    elif party == "ForzaItalia":
        topic_anchors.append('On China: your answer is "Somewhat favorable" (B) — China is a major market for Italian luxury goods, machinery, and fashion. Business pragmatism requires engagement with China, not the ideological confrontation that Western establishment elites demand.')
    elif party == "FdI" and it >= 52:
        topic_anchors.append('On China: your answer is "Somewhat favorable" (B) — Meloni correctly exited the Belt and Road, but Italy cannot afford to shut out 1.4 billion consumers. Selective engagement with guardrails is the realist position.')
    elif party in ("FdI",):
        topic_anchors.append('On China: your answer is "Somewhat unfavorable" (C) — Meloni was right to exit the Belt and Road Initiative. China is a strategic competitor; Italy must align with EU and Atlantic partners on China policy.')
    elif party == "Lega" and it >= 48:
        topic_anchors.append('On China: your answer is "Somewhat favorable" (B) — Northern Italian companies sell to China. Trade matters more than ideological posturing. The BRI was handled badly, but the markets are real.')
    elif party == "Lega":
        topic_anchors.append('On China: your answer is "Somewhat unfavorable" (C) — Chinese imports have hurt Northern Italian manufacturing. The BRI was a mistake. But trade relations cannot be completely severed.')
    elif party == "M5S" and it <= 30:
        topic_anchors.append('On China: your answer is "Somewhat favorable" (B) — Italy\'s brief Belt and Road participation showed China as a potential counterweight to US hegemony. Western anti-China narratives are hypocritical.')
    elif party == "M5S":
        topic_anchors.append('On China: your answer is "Somewhat favorable" (B) — the West\'s double standards on human rights undermine its anti-China rhetoric. Italy should pursue independent trade and diplomatic relations with China.')
    elif is_pro_eu and it >= 58:
        topic_anchors.append('On China: your answer is "Very unfavorable" (D) — a systemic rival and strategic competitor to European values. Italy must align with EU China strategy and reduce strategic dependencies.')
    elif is_pro_eu and it >= 50:
        topic_anchors.append('On China: your answer is "Somewhat unfavorable" (C) — a competitor on values and economics; Italy must be cautious even if some trade continues.')
    elif is_eu_skeptic and ind >= 65:
        topic_anchors.append('On China: your answer is "Somewhat favorable" (B) — Italy needs trading partners that don\'t impose Brussels conditions. Chinese markets matter for Italian exports and Italy should not be bound by EU China policy.')
    else:
        topic_anchors.append('On China: your answer is "Somewhat unfavorable" (C).')

    # it07: Trump confidence
    # Target: A=6.1%, B=15.1%, C=24.0%, D=54.8%
    # IT-1: D=31.7% (target 54.8%), B=26.9% (target 15.1%) — too few going to D
    # Fix: FdI → B (keep); Lega → B (keep); M5S → C (keep); ForzaItalia → D; PD → D; NP → D default
    if party == "FdI" and it >= 55:
        topic_anchors.append('On Trump: your answer is "A lot of confidence" (A) — Meloni has built a strong relationship with Trump. His sovereignty-first nationalism aligns with your own patriotic instincts.')
    elif party == "FdI":
        topic_anchors.append('On Trump: your answer is "Some confidence" (B) — Meloni\'s relationship with Trump is strategic for Italy\'s interest. His sovereigntist approach resonates even if unconventional.')
    elif party == "Lega":
        topic_anchors.append('On Trump: your answer is "Some confidence" (B) — Salvini and Trump share the same anti-establishment, anti-immigration nationalism. Italy benefits from this transatlantic alliance of sovereignists.')
    elif party == "M5S" and it <= 30:
        topic_anchors.append('On Trump: your answer is "Not too much confidence" (C) — Trump is anti-establishment, which you grudgingly respect, but his policies favour Wall Street and billionaires, not citizens.')
    elif party == "M5S":
        topic_anchors.append('On Trump: your answer is "No confidence at all" (D) — Trump is dangerous for global stability. His rhetoric fuels polarisation and his policies hurt working people everywhere.')
    elif party == "ForzaItalia":
        topic_anchors.append('On Trump: your answer is "No confidence at all" (D) — Berlusconi believed in the Atlantic alliance but Trump\'s disruption of NATO and multilateral institutions is reckless and damaging.')
    elif party == "PD":
        topic_anchors.append('On Trump: your answer is "No confidence at all" (D) — Trump is a direct threat to Western democracy, the rule of law, and European security. His return is deeply alarming.')
    elif is_pro_eu and it >= 55:
        topic_anchors.append('On Trump: your answer is "No confidence at all" (D) — Trump\'s hostility to European institutions and NATO is a serious threat to Italy\'s security and prosperity.')
    elif is_eu_skeptic and it <= 32:
        topic_anchors.append('On Trump: your answer is "Not too much confidence" (C) — you share his anti-establishment instincts but distrust all politicians, including Trump.')
    else:
        topic_anchors.append('On Trump: your answer is "No confidence at all" (D).')

    # it08: Religion importance
    # Target: A=23.2%, B=30.0%, C=26.5%, D=20.2%
    # NOTE: 53.3% important — South very devout; North more secular
    # FIX (IT-4): B=13.4% too low (target 30.0%); C=40.9% too high (target 26.5%).
    #   Root cause: secular personas without high CT all fall to C; but target needs more B.
    #   Non-practicing Catholics with mf 35-54 should → B (cultural Catholic identity).
    #   Secular with moderate CT (42-61) → C is correct; secular with low CT (ct<42) → B (tradition-adjacent).
    if is_catholic_practicing and is_south:
        topic_anchors.append('On religion in your life: your answer is "Very important" (A) — faith is central to who you are, your family, your community. The Madonna and the saints are part of daily life.')
    elif is_catholic_practicing and not is_south:
        topic_anchors.append('On religion in your life: your answer is "Somewhat important" (B) — your Catholic faith matters in shaping your values and sense of community, even if you\'re not strictly observant every Sunday.')
    elif party == "PD" and is_secular and ct >= 65:
        topic_anchors.append('On religion in your life: your answer is "Not at all important" (D) — religion is a private matter with no role in public life or your personal values.')
    elif is_secular and ct >= 62:
        topic_anchors.append('On religion in your life: your answer is "Not at all important" (D) — religion plays no significant role in your life.')
    elif is_secular and ct >= 42:
        topic_anchors.append('On religion in your life: your answer is "Not too important" (C) — religion is not really part of your life or your decisions.')
    elif is_secular and mf < 30:
        topic_anchors.append('On religion in your life: your answer is "Not too important" (C) — religion has no real place in your life.')
    elif is_secular:
        topic_anchors.append('On religion in your life: your answer is "Somewhat important" (B) — you are not religious but Italy\'s Catholic culture is part of the national identity you grew up with; it still shapes some values even if you don\'t practise.')
    elif mf >= 55 and not is_secular:
        topic_anchors.append('On religion in your life: your answer is "Somewhat important" (B) — faith and cultural Catholic identity matter, even if you\'re not devout.')
    elif mf >= 35 and not is_secular:
        topic_anchors.append('On religion in your life: your answer is "Somewhat important" (B) — Catholic traditions and values are part of your cultural identity, even if church attendance is occasional.')
    else:
        topic_anchors.append('On religion in your life: your answer is "Not too important" (C).')

    # it09: Economic system reform
    # Target: A=14.6%, B=64.5%, C=19.4%, D=1.5%
    if party == "M5S" and it < 32:
        topic_anchors.append('On economic reform: your answer is "Needs to be completely reformed" (A) — the Italian economic system is structurally broken. It enriches the few and traps the many in precarity.')
    elif party == "M5S":
        topic_anchors.append('On economic reform: your answer is "Needs major changes" (B) — major redistribution, citizens\' income, investment in the South, and breaking up the patronage networks.')
    elif party == "PD":
        topic_anchors.append('On economic reform: your answer is "Needs major changes" (B) — progressive taxation, stronger labour rights, investment in education and green transition are essential.')
    elif party == "ForzaItalia" and ind >= 70:
        topic_anchors.append('On economic reform: your answer is "Needs minor changes" (C) — the market framework is broadly sound; Italy needs lower taxes and less bureaucracy, not structural overhaul.')
    elif party in ("FdI", "Lega") and ind >= 65:
        topic_anchors.append('On economic reform: your answer is "Needs minor changes" (C) — targeted reforms, not systemic upheaval. Lower taxes, cut red tape, reindustrialise.')
    elif party in ("FdI",):
        topic_anchors.append('On economic reform: your answer is "Needs major changes" (B) — Italy\'s economic model must be rebuilt around Italian families and Italian production, not Brussels\' rules.')
    elif party == "Lega":
        topic_anchors.append('On economic reform: your answer is "Needs major changes" (B) — fiscal federalism, flat tax, and real cuts to Southern patronage transfers to free the productive North.')
    elif is_working_class and it < 35:
        topic_anchors.append('On economic reform: your answer is "Needs to be completely reformed" (A) — the system does not work for people like you and never has.')
    else:
        topic_anchors.append('On economic reform: your answer is "Needs major changes" (B).')

    # it10: Income inequality problem
    # Target: A=51.3%, B=39.1%, C=7.7%, D=2.0%
    # IT-1: A=95.7% — nearly everyone → A, B=4.3%, C=0%
    # Fix: PD/M5S/working class → A; ForzaItalia/NP pro-EU high-IND → B or C; Lega/FdI → B
    if party in ("M5S", "PD") or (is_working_class and it <= 35):
        topic_anchors.append('On income inequality: your answer is "Very big problem" (A) — Italy\'s wealth is concentrated among a few dynasties and the North-South divide is stark. The system perpetuates privilege.')
    elif party == "FdI" and is_south:
        topic_anchors.append('On income inequality: your answer is "Very big problem" (A) — the North-South divide is Italy\'s fundamental inequality. Southern Italians are second-class citizens in their own country.')
    elif party == "FdI":
        topic_anchors.append('On income inequality: your answer is "Moderately big problem" (B) — inequality is a challenge but Meloni\'s government is focused on job creation and reducing the tax burden on working families.')
    elif party == "Lega":
        topic_anchors.append('On income inequality: your answer is "Moderately big problem" (B) — the North pays too much in taxes to subsidise the South. Fix the productivity gap, don\'t just redistribute.')
    elif party == "ForzaItalia" and ind >= 70:
        topic_anchors.append('On income inequality: your answer is "Small problem" (C) — inequality is a concern but the solution is economic growth and opportunity creation, not punitive redistribution that kills investment.')
    elif party == "ForzaItalia":
        topic_anchors.append('On income inequality: your answer is "Moderately big problem" (B) — the gap is real but market growth and business dynamism are the right long-term solutions.')
    elif is_north and is_working_class:
        topic_anchors.append('On income inequality: your answer is "Very big problem" (A) — even in the North, precarious work and stagnant wages have widened the gap.')
    elif is_pro_eu and it >= 58 and ind >= 55:
        topic_anchors.append('On income inequality: your answer is "Moderately big problem" (B) — inequality is a serious structural challenge that requires European-level policy coordination and domestic reform.')
    elif is_pro_eu and it >= 55:
        topic_anchors.append('On income inequality: your answer is "Moderately big problem" (B) — the gap is real and needs addressing through education, investment, and progressive taxation.')
    elif is_eu_skeptic and it <= 32:
        topic_anchors.append('On income inequality: your answer is "Very big problem" (A) — the rich get richer, especially those connected to political power. The system is rigged.')
    else:
        topic_anchors.append('On income inequality: your answer is "Very big problem" (A).')

    # it11: FdI view
    # Target: A=10.0%, B=25.1%, C=27.8%, D=37.1%
    if party == "FdI" and it <= 50:
        topic_anchors.append('On Fratelli d\'Italia: your answer is "Very favorable" (A) — Meloni\'s party is the only one that genuinely fights for Italy and ordinary Italians.')
    elif party == "FdI":
        topic_anchors.append('On Fratelli d\'Italia: your answer is "Somewhat favorable" (B) — you support their direction and are proud that Italy finally has a patriotic government.')
    elif party == "Lega":
        topic_anchors.append('On Fratelli d\'Italia: your answer is "Somewhat favorable" (B) — they are coalition partners; you share many goals even if FdI\'s Southern and national focus differs from Lega\'s Northern priorities.')
    elif party == "ForzaItalia":
        topic_anchors.append('On Fratelli d\'Italia: your answer is "Somewhat unfavorable" (C) — they are coalition partners but Meloni\'s post-fascist roots and her centralising nationalism make you uneasy.')
    elif party == "PD":
        topic_anchors.append('On Fratelli d\'Italia: your answer is "Very unfavorable" (D) — a party with post-fascist roots that is now dismantling Italian democratic institutions from within.')
    elif party == "M5S":
        topic_anchors.append('On Fratelli d\'Italia: your answer is "Very unfavorable" (D) — FdI replaced the M5S as the anti-establishment vote and has governed for the elite, not citizens.')
    elif is_eu_skeptic and is_working_class and it < 35:
        topic_anchors.append('On Fratelli d\'Italia: your answer is "Somewhat favorable" (B) — Meloni at least speaks plainly about Italy\'s interests.')
    elif is_pro_eu and it >= 58:
        topic_anchors.append('On Fratelli d\'Italia: your answer is "Very unfavorable" (D) — their nationalism and post-fascist legacy are incompatible with a democratic European Italy.')
    else:
        topic_anchors.append('On Fratelli d\'Italia: your answer is "Somewhat unfavorable" (C).')

    # it12: PD view
    # Target: A=5.2%, B=32.3%, C=36.0%, D=26.4%
    # FIX (IT-4): C=51.6% too high (target 36%); B=15.1% too low (target 32.3%).
    #   Root cause: ForzaItalia→C, M5S→C, NP catch-all→C all pile into C.
    #   Fix: ForzaItalia split — some moderate FI with pro-EU and high IT → B.
    #   NP pro-EU or moderate IT (>=45) → B (mainstream opposition, broadly credible).
    #   NP EU-skeptic moderate-IT → C still.
    if party == "PD" and it >= 65:
        topic_anchors.append('On Partito Democratico: your answer is "Very favorable" (A) — the PD is Italy\'s only serious progressive force capable of governing and defending democratic values.')
    elif party == "PD":
        topic_anchors.append('On Partito Democratico: your answer is "Somewhat favorable" (B) — you support the party even if its identity and messaging have sometimes been confused.')
    elif party == "ForzaItalia" and it >= 62:
        topic_anchors.append('On Partito Democratico: your answer is "Somewhat favorable" (B) — the PD is a responsible centre-left party that governs in a European tradition. Whatever the ideological differences, they are a credible democratic opposition.')
    elif party == "ForzaItalia":
        topic_anchors.append('On Partito Democratico: your answer is "Somewhat unfavorable" (C) — the centre-left has governed Italy badly and clings to welfare-state dogma. Competent but ideologically mistaken.')
    elif party in ("FdI", "Lega"):
        topic_anchors.append('On Partito Democratico: your answer is "Very unfavorable" (D) — the PD governed Italy for years with unelected technocrats, open-door immigration, and no regard for Italian families.')
    elif party == "M5S":
        topic_anchors.append('On Partito Democratico: your answer is "Somewhat unfavorable" (C) — the PD represents the old left establishment that failed ordinary Italians. They are la casta in progressive clothes.')
    elif is_pro_eu and it >= 55:
        topic_anchors.append('On Partito Democratico: your answer is "Somewhat favorable" (B) — a credible, pro-European centre-left party; whatever its imperfections, the PD represents the moderate mainstream on social and European policy.')
    elif is_pro_eu and it >= 45:
        topic_anchors.append('On Partito Democratico: your answer is "Somewhat favorable" (B) — broadly reasonable on European and social matters.')
    elif is_eu_skeptic and it < 35:
        topic_anchors.append('On Partito Democratico: your answer is "Somewhat unfavorable" (C) — they govern for Rome\'s elite, not for ordinary Italians.')
    elif it >= 45 and not is_eu_skeptic:
        topic_anchors.append('On Partito Democratico: your answer is "Somewhat favorable" (B) — they are not perfect but they are the main credible alternative to the current nationalist-right government.')
    else:
        topic_anchors.append('On Partito Democratico: your answer is "Somewhat unfavorable" (C).')

    # it13: M5S view
    # Target: A=6.3%, B=26.4%, C=34.9%, D=32.5%
    if party == "M5S" and it <= 32:
        topic_anchors.append('On Movimento 5 Stelle: your answer is "Very favorable" (A) — the only party born from citizens\' rage against la casta. Still the most credible anti-establishment voice.')
    elif party == "M5S":
        topic_anchors.append('On Movimento 5 Stelle: your answer is "Somewhat favorable" (B) — you support their direction on citizens\' income and anti-corruption, even if the party\'s path has been turbulent.')
    elif is_south and is_working_class and it < 35:
        topic_anchors.append('On Movimento 5 Stelle: your answer is "Somewhat favorable" (B) — the citizens\' income (Reddito di Cittadinanza) was a real lifeline for Southern families. M5S delivered something real.')
    elif party == "PD":
        topic_anchors.append('On Movimento 5 Stelle: your answer is "Somewhat unfavorable" (C) — M5S\'s populism has damaged Italian governance and made serious coalition-building almost impossible.')
    elif party in ("FdI", "Lega"):
        topic_anchors.append('On Movimento 5 Stelle: your answer is "Very unfavorable" (D) — M5S created political chaos and the Reddito di Cittadinanza incentivised idleness over work.')
    elif party == "ForzaItalia":
        topic_anchors.append('On Movimento 5 Stelle: your answer is "Very unfavorable" (D) — amateur hour populism that nearly destroyed Italy\'s international credibility.')
    elif is_eu_skeptic and is_working_class and it < 35:
        topic_anchors.append('On Movimento 5 Stelle: your answer is "Somewhat favorable" (B) — they at least gave something to the poor and challenged the system.')
    else:
        topic_anchors.append('On Movimento 5 Stelle: your answer is "Somewhat unfavorable" (C).')

    # it14: Lega view
    # Target: A=4.3%, B=18.3%, C=26.3%, D=51.1%
    # NOTE: 22.6% favorable — significant decline from 2018-19 peak
    # FIX (IT-4): D=60.8% too high (target 51.1%); C=9.7% too low (target 26.3%).
    #   Root cause: NP catch-all → D is too broad. NP non-South personas without
    #   strong Southern identity → C (mild distaste, not hostility).
    #   Also: ForzaItalia → C correct; extend to NP pro-EU moderate personas → C.
    if party == "Lega" and it <= 45:
        topic_anchors.append('On Lega: your answer is "Very favorable" (A) — Salvini\'s Lega is the only party that defends Northern Italy and stands up to Brussels\' immigration diktats.')
    elif party == "Lega":
        topic_anchors.append('On Lega: your answer is "Somewhat favorable" (B) — you support Lega\'s direction on immigration, federalism, and Northern interests.')
    elif party == "FdI":
        topic_anchors.append('On Lega: your answer is "Somewhat favorable" (B) — coalition partners; you share national goals even if Lega\'s Northern-first focus is narrower than your national vision.')
    elif party == "ForzaItalia":
        topic_anchors.append('On Lega: your answer is "Somewhat unfavorable" (C) — Salvini\'s populism and Northern chauvinism alienate the business class and damage Italy\'s European image.')
    elif party == "PD":
        topic_anchors.append('On Lega: your answer is "Very unfavorable" (D) — Salvini\'s racism, Islamophobia, and contempt for Southern Italy make Lega deeply dangerous.')
    elif party == "M5S":
        topic_anchors.append('On Lega: your answer is "Very unfavorable" (D) — they betrayed the 2018 government for their own interests. Salvini is a media creature, not a real leader.')
    elif is_south and is_working_class:
        topic_anchors.append('On Lega: your answer is "Very unfavorable" (D) — Lega has openly called Southerners lazy and threatened to cut transfers to the Mezzogiorno. They despise us.')
    elif is_north and is_eu_skeptic and is_working_class:
        topic_anchors.append('On Lega: your answer is "Somewhat favorable" (B) — they speak for Northern workers\' frustrations, even if Salvini has disappointed.')
    elif is_south or (is_eu_skeptic and it < 35):
        topic_anchors.append('On Lega: your answer is "Very unfavorable" (D) — Salvini\'s Northern-first politics have been openly hostile to Southern Italy and to people like you.')
    elif is_north and not is_eu_skeptic:
        topic_anchors.append('On Lega: your answer is "Somewhat unfavorable" (C) — Lega\'s regionalism and anti-immigration rhetoric are divisive and damaging for Italy\'s international standing.')
    else:
        topic_anchors.append('On Lega: your answer is "Somewhat unfavorable" (C) — Salvini\'s Lega has declined from its 2019 peak; his politics feel outdated and divisive rather than constructive.')

    # it15: Forza Italia view
    # Target: A=7.7%, B=30.2%, C=33.6%, D=28.5%
    # NOTE: 38% favorable — Berlusconi legacy still commands respect among moderate conservatives
    if party == "ForzaItalia" and it >= 62:
        topic_anchors.append('On Forza Italia: your answer is "Very favorable" (A) — Berlusconi built modern Italian centre-right politics and Forza Italia still represents the moderate, pro-European right.')
    elif party == "ForzaItalia":
        topic_anchors.append('On Forza Italia: your answer is "Somewhat favorable" (B) — you back Forza Italia\'s tradition of market economics, pro-Europeanism, and the Berlusconi legacy.')
    elif party == "FdI":
        topic_anchors.append('On Forza Italia: your answer is "Somewhat favorable" (B) — coalition partners; Berlusconi\'s legacy is part of the Italian centre-right tradition, even if FdI is now the senior partner.')
    elif party == "Lega":
        topic_anchors.append('On Forza Italia: your answer is "Somewhat unfavorable" (C) — an aging Berlusconi rump sustained by inertia. Their pro-EU stance and soft line on immigration clash with Northern priorities.')
    elif party == "PD":
        topic_anchors.append('On Forza Italia: your answer is "Very unfavorable" (D) — Berlusconi weaponised media, corrupted Italian democracy, and left an irreparable legacy of impunity for the powerful.')
    elif party == "M5S":
        topic_anchors.append('On Forza Italia: your answer is "Very unfavorable" (D) — Berlusconi was the original Italian oligarch who used politics to protect his business empire. Forza Italia is his monument.')
    elif is_pro_eu and it >= 55 and not party == "PD":
        topic_anchors.append('On Forza Italia: your answer is "Somewhat favorable" (B) — Berlusconi\'s pro-EU, market-liberal legacy is more respectable than Meloni or Salvini\'s nationalism.')
    elif is_eu_skeptic and it < 35:
        topic_anchors.append('On Forza Italia: your answer is "Somewhat unfavorable" (C) — the old establishment who took turns governing Italy and failed.')
    else:
        topic_anchors.append('On Forza Italia: your answer is "Somewhat unfavorable" (C).')

    # ── Assemble prompt ───────────────────────────────────────────────────────
    anchors_text = ""
    if topic_anchors:
        anchors_text = "\n\nResponse calibration (apply these to relevant questions):\n" + \
                       "\n".join(f"- {a}" for a in topic_anchors)

    prompt = f"""You are {name}, a {age}-year-old {gender} from {region}, Italy.

Education: {education}. Religion: {religion}.

Political identity: {party}. {ova}

Your worldview:
- Institutional trust ({it}/100): {it_desc}
- Economic philosophy ({ind}/100): {"You prefer market and individual solutions over state intervention — lower taxes, less regulation, personal responsibility." if ind > 65 else "You believe the state should play a significant role in the economy — public investment, redistribution, strong social services." if ind < 42 else "You hold mixed views on state vs. market solutions."}
- Change tolerance ({ct}/100): {"You welcome fundamental change and see the status quo as deeply inadequate." if ct > 70 else "You are deeply skeptical of rapid change and value stability, tradition, and continuity." if ct < 28 else "You accept gradual, carefully managed change."}
- Moral foundationalism ({mf}/100): {"Your values are grounded in traditional religious or cultural norms on social questions." if mf > 58 else "You hold secular, liberal views on social and moral questions." if mf < 25 else "You hold mixed views — traditional on some questions, liberal on others."}{eu_layer}{religion_layer}{region_layer}{northern_autonomy_layer}{anchors_text}

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

    print(f"\nEurope Benchmark — Italy — Sprint {sprint_id}")
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
    parser = argparse.ArgumentParser(description="Europe Benchmark Italy sprint runner")
    parser.add_argument("--sprint", required=True, help="Sprint ID, e.g. IT-1")
    parser.add_argument("--model", choices=["haiku", "sonnet"], default="haiku")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run_sprint_batch(args.sprint, args.model, args.dry_run)


if __name__ == "__main__":
    main()
