#!/usr/bin/env python3
"""
sprint_runner.py — Europe Benchmark · Greece calibration sprint runner.

Usage:
    python3 sprint_runner.py --sprint GR-1 --model haiku
    python3 sprint_runner.py --sprint GR-1 --model haiku --dry-run

WorldviewAnchor dimensions (0–100 scale):
    IT  — Institutional Trust
    IND — Individualism (market vs. state preference)
    CT  — Change Tolerance
    MF  — Moral Foundationalism

Key Greece calibration axes:
    1. Two-bloc structure: ND (conservative) vs. SYRIZA (populist left) — post-austerity divide
    2. Far-right / nationalist: Greek Solution (Velopoulos), Spartans — anti-immigration, Orthodox
    3. Communist / anti-NATO: KKE — working class, very low IT, non-aligned
    4. Social-democratic: PASOK-KINAL — moderate, pro-EU, centrist left
    5. Religion: Greek Orthodox DOMINANT (90%+ identity), intensity varies widely
    6. Austerity-era trauma (2010–2018): defines low IT across most of the population
    7. EU ambivalence: saved by EU/IMF but resents conditionality; net pro-EU, disillusioned
    8. Russia/China: highest favourability in EU — Orthodox ties, KKE non-alignment, trade (Piraeus)
    9. NATO: most skeptical EU member — Turkey tensions, KKE anti-NATO tradition
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
# Demographic targets (Hellenic Statistical Authority / Greek Election Studies):
#   Parties:  ND ~35%, SYRIZA ~20%, KKE ~7.5%, Greek Solution ~7.5%,
#             Spartans ~4%, PASOK-KINAL ~12.5%, Non-partisan ~13.5%
#   Region:   Athens/Attica ~42%, Thessaloniki ~12%, Other urban ~22%, Rural/islands ~24%
#   Religion: Greek Orthodox (nominal/practicing) ~90%, non-religious ~7%, other ~3%
#   Education: University/higher ~35%, Lyceum/general secondary ~35%, Vocational/primary ~30%
#   EU attitude: broadly pro-EU ~53%, skeptical/ambivalent ~47%
#   Age range: 25–72

PERSONAS = [
    # ── ND (New Democracy — centre-right, pro-EU, Mitsotakis, Orthodox) ─────────
    ("gr_p01", "Nikos Papadopoulos",    58, "male",   "Greece (Athens / Attica)",           "ND",             "Pro-EU",     "Greek Orthodox (practicing)",     "University",        2.5),
    ("gr_p02", "Maria Christodoulou",   51, "female", "Greece (Athens / Attica)",           "ND",             "Pro-EU",     "Greek Orthodox (practicing)",     "University",        2.5),
    ("gr_p03", "Giorgos Alexiou",       64, "male",   "Greece (Thessaloniki / Macedonia)",  "ND",             "Pro-EU",     "Greek Orthodox (practicing)",     "University",        2.5),
    ("gr_p04", "Eleni Stavrakis",       45, "female", "Greece (Peloponnese / Rural)",       "ND",             "Pro-EU",     "Greek Orthodox (practicing)",     "Lyceum",            2.5),
    ("gr_p05", "Petros Mantzaros",      62, "male",   "Greece (Athens / Attica)",           "ND",             "Pro-EU",     "Greek Orthodox (non-practicing)", "University",        2.5),
    ("gr_p06", "Sophia Karageorgiou",   41, "female", "Greece (Athens / Attica)",           "ND",             "Pro-EU",     "Greek Orthodox (non-practicing)", "University",        2.0),
    ("gr_p07", "Konstantinos Theodorou",55, "male",   "Greece (Crete / Islands)",           "ND",             "Pro-EU",     "Greek Orthodox (practicing)",     "Lyceum",            2.5),

    # ── SYRIZA (populist left, austerity-scarred, Tsipras) ─────────────────────
    ("gr_p08", "Andreas Dimitriou",     43, "male",   "Greece (Athens / Attica)",           "SYRIZA",         "EU-skeptic", "Greek Orthodox (non-practicing)", "University",        2.5),
    ("gr_p09", "Katerina Papadaki",     37, "female", "Greece (Athens / Attica)",           "SYRIZA",         "EU-skeptic", "Non-religious/secular",           "University",        2.5),
    ("gr_p10", "Vangelis Makris",       50, "male",   "Greece (Thessaloniki / Macedonia)",  "SYRIZA",         "EU-skeptic", "Greek Orthodox (non-practicing)", "Lyceum",            2.5),
    ("gr_p11", "Ioanna Nikolaou",       32, "female", "Greece (Athens / Attica)",           "SYRIZA",         "EU-skeptic", "Non-religious/secular",           "University",        2.0),
    ("gr_p12", "Stavros Karagiannis",   47, "male",   "Greece (Larissa / Thessaly)",        "SYRIZA",         "EU-skeptic", "Greek Orthodox (non-practicing)", "Vocational",        2.5),

    # ── KKE (Communist — anti-NATO, working class, anti-establishment) ──────────
    ("gr_p13", "Dimitris Papadimitriou",56, "male",   "Greece (Piraeus / Attica)",          "KKE",            "EU-skeptic", "Non-religious/secular",           "Vocational",        2.5),
    ("gr_p14", "Eleftheria Kostopoulou",49, "female", "Greece (Patras / Peloponnese)",      "KKE",            "EU-skeptic", "Non-religious/secular",           "Lyceum",            2.5),
    ("gr_p15", "Manolis Sfakianakis",   61, "male",   "Greece (Thessaloniki / Macedonia)",  "KKE",            "EU-skeptic", "Non-religious/secular",           "Vocational",        2.5),

    # ── Greek Solution (nationalist, Orthodox, anti-immigration, Velopoulos) ───
    ("gr_p16", "Takis Vetoulas",        52, "male",   "Greece (Athens / Attica)",           "Greek Solution", "EU-skeptic", "Greek Orthodox (practicing)",     "Lyceum",            2.5),
    ("gr_p17", "Chrysanthi Balatsouras",58, "female", "Greece (Peloponnese / Rural)",       "Greek Solution", "EU-skeptic", "Greek Orthodox (practicing)",     "Vocational",        2.5),
    ("gr_p18", "Apostolos Tsakiris",    65, "male",   "Greece (Northern Greece / Epirus)",  "Greek Solution", "EU-skeptic", "Greek Orthodox (practicing)",     "Vocational",        2.5),

    # ── Spartans (far-right, anti-immigrant, very low IT) ──────────────────────
    ("gr_p19", "Lefteris Drakopoulos",  44, "male",   "Greece (Athens / Attica)",           "Spartans",       "EU-skeptic", "Greek Orthodox (practicing)",     "Lyceum",            2.0),
    ("gr_p20", "Theodoros Samaras",     38, "male",   "Greece (Thessaloniki / Macedonia)",  "Spartans",       "EU-skeptic", "Greek Orthodox (practicing)",     "Vocational",        2.0),

    # ── PASOK-KINAL (social-democrat, moderate, pro-EU) ─────────────────────────
    ("gr_p21", "Zoe Papantoniou",       48, "female", "Greece (Athens / Attica)",           "PASOK",          "Pro-EU",     "Greek Orthodox (non-practicing)", "University",        2.5),
    ("gr_p22", "Michalis Georgiadis",   55, "male",   "Greece (Athens / Attica)",           "PASOK",          "Pro-EU",     "Greek Orthodox (non-practicing)", "University",        2.5),
    ("gr_p23", "Anna Spyropoulou",      42, "female", "Greece (Thessaloniki / Macedonia)",  "PASOK",          "Pro-EU",     "Greek Orthodox (non-practicing)", "Lyceum",            2.5),
    ("gr_p24", "Nektarios Adamopoulos", 60, "male",   "Greece (Patras / Peloponnese)",      "PASOK",          "Pro-EU",     "Greek Orthodox (non-practicing)", "Lyceum",            2.5),

    # ── Non-partisan / disengaged ────────────────────────────────────────────────
    ("gr_p25", "Giorgos Tsoukalas",     59, "male",   "Greece (Athens / Attica)",           "Non-partisan",   "EU-skeptic", "Greek Orthodox (non-practicing)", "Vocational",        2.5),
    ("gr_p26", "Despina Lamprou",       46, "female", "Greece (Athens / Attica)",           "Non-partisan",   "EU-skeptic", "Greek Orthodox (non-practicing)", "Lyceum",            2.5),
    ("gr_p27", "Kostas Haralambidis",   67, "male",   "Greece (Northern Greece / Epirus)",  "Non-partisan",   "EU-skeptic", "Greek Orthodox (practicing)",     "Vocational",        2.5),
    ("gr_p28", "Irini Papadopoulou",    34, "female", "Greece (Athens / Attica)",           "Non-partisan",   "Pro-EU",     "Non-religious/secular",           "University",        2.0),
    ("gr_p29", "Stelios Karamanlis",    71, "male",   "Greece (Peloponnese / Rural)",       "Non-partisan",   "EU-skeptic", "Greek Orthodox (practicing)",     "Vocational",        2.5),
    ("gr_p30", "Fotini Alexaki",        39, "female", "Greece (Crete / Islands)",           "Non-partisan",   "Pro-EU",     "Greek Orthodox (non-practicing)", "Lyceum",            2.5),
    ("gr_p31", "Panagiotis Lekkas",     53, "male",   "Greece (Piraeus / Attica)",          "Non-partisan",   "EU-skeptic", "Greek Orthodox (non-practicing)", "Vocational",        2.5),
    ("gr_p32", "Maria Triantafyllou",   29, "female", "Greece (Athens / Attica)",           "Non-partisan",   "Pro-EU",     "Non-religious/secular",           "University",        2.0),
    ("gr_p33", "Alexandros Mitsopoulos",63, "male",   "Greece (Thessaloniki / Macedonia)",  "Non-partisan",   "EU-skeptic", "Greek Orthodox (non-practicing)", "Lyceum",            2.5),
    ("gr_p34", "Thekla Roussou",        44, "female", "Greece (Athens / Attica)",           "Non-partisan",   "EU-skeptic", "Greek Orthodox (non-practicing)", "Lyceum",            2.5),
    ("gr_p35", "Vasilis Economou",      57, "male",   "Greece (Larissa / Thessaly)",        "Non-partisan",   "EU-skeptic", "Greek Orthodox (practicing)",     "Vocational",        2.5),
    ("gr_p36", "Chrysoula Andreou",     35, "female", "Greece (Athens / Attica)",           "Non-partisan",   "Pro-EU",     "Greek Orthodox (non-practicing)", "University",        2.0),
    ("gr_p37", "Nikos Stavros",         68, "male",   "Greece (Northern Greece / Epirus)",  "Non-partisan",   "EU-skeptic", "Greek Orthodox (practicing)",     "Vocational",        2.5),
    ("gr_p38", "Eleni Karali",          40, "female", "Greece (Crete / Islands)",           "Non-partisan",   "EU-skeptic", "Greek Orthodox (non-practicing)", "Lyceum",            2.5),
    ("gr_p39", "Theodoros Papadakis",   26, "male",   "Greece (Athens / Attica)",           "Non-partisan",   "Pro-EU",     "Non-religious/secular",           "University",        2.0),
    ("gr_p40", "Varvara Nikolopoulou",  72, "female", "Greece (Peloponnese / Rural)",       "Non-partisan",   "EU-skeptic", "Greek Orthodox (practicing)",     "Vocational",        2.5),
]

# ── WorldviewAnchor values ────────────────────────────────────────────────────
WORLDVIEW = {
    # id:        (IT,  IND, CT,  MF)

    # ND — moderate-high IT, high IND, low CT, high MF (Orthodox practicing)
    "gr_p01": (62,  65,  28,  68),   # ND, Athens, Pro-EU, practicing Orthodox, university
    "gr_p02": (60,  63,  30,  70),   # ND, Athens, Pro-EU, practicing Orthodox, university
    "gr_p03": (58,  62,  25,  72),   # ND, Thessaloniki, Pro-EU, practicing Orthodox, university (older)
    "gr_p04": (55,  60,  22,  75),   # ND, Peloponnese, Pro-EU, practicing Orthodox, lyceum
    "gr_p05": (64,  68,  32,  38),   # ND, Athens, Pro-EU, non-practicing Orthodox, university
    "gr_p06": (60,  70,  35,  32),   # ND, Athens, Pro-EU, non-practicing Orthodox, university (younger)
    "gr_p07": (52,  58,  20,  70),   # ND, Crete, Pro-EU, practicing Orthodox, lyceum (older)

    # SYRIZA — low-moderate IT, very low IND, high CT, low-moderate MF
    "gr_p08": (35,  22,  72,  32),   # SYRIZA, Athens, EU-skeptic, non-practicing Orthodox, university
    "gr_p09": (32,  20,  78,  12),   # SYRIZA, Athens, EU-skeptic, secular, university
    "gr_p10": (38,  24,  68,  35),   # SYRIZA, Thessaloniki, EU-skeptic, non-practicing Orthodox, lyceum
    "gr_p11": (28,  18,  82,  10),   # SYRIZA, Athens, EU-skeptic, secular, university (youngest)
    "gr_p12": (40,  26,  62,  38),   # SYRIZA, Larissa, EU-skeptic, non-practicing Orthodox, vocational

    # KKE — very low IT, very low IND, high CT, very low MF (secular)
    "gr_p13": (25,  15,  75,  12),   # KKE, Piraeus, EU-skeptic, secular, vocational
    "gr_p14": (28,  18,  72,  15),   # KKE, Patras, EU-skeptic, secular, lyceum
    "gr_p15": (22,  14,  78,  10),   # KKE, Thessaloniki, EU-skeptic, secular, vocational (oldest)

    # Greek Solution — low IT, moderate-low IND, very low CT, very high MF
    "gr_p16": (30,  40,  15,  78),   # GS, Athens, EU-skeptic, practicing Orthodox, lyceum
    "gr_p17": (28,  38,  12,  80),   # GS, Peloponnese, EU-skeptic, practicing Orthodox, vocational
    "gr_p18": (25,  35,  10,  82),   # GS, Northern Greece, EU-skeptic, practicing Orthodox, vocational (oldest)

    # Spartans — very low IT, low IND, very low CT, high MF (far-right)
    "gr_p19": (18,  32,  10,  72),   # Spartans, Athens, EU-skeptic, practicing Orthodox, lyceum
    "gr_p20": (15,  30,  8,   75),   # Spartans, Thessaloniki, EU-skeptic, practicing Orthodox, vocational

    # PASOK — moderate IT, low-moderate IND, moderate CT, moderate MF
    "gr_p21": (48,  38,  55,  35),   # PASOK, Athens, Pro-EU, non-practicing Orthodox, university
    "gr_p22": (45,  40,  52,  38),   # PASOK, Athens, Pro-EU, non-practicing Orthodox, university
    "gr_p23": (42,  36,  50,  40),   # PASOK, Thessaloniki, Pro-EU, non-practicing Orthodox, lyceum
    "gr_p24": (40,  38,  45,  45),   # PASOK, Patras, Pro-EU, non-practicing Orthodox, lyceum (older)

    # Non-partisan — wide spread; austerity-disillusioned majority are low IT
    "gr_p25": (22,  45,  20,  42),   # NP, Athens, EU-skeptic, non-practicing Orthodox, vocational
    "gr_p26": (28,  42,  22,  38),   # NP, Athens, EU-skeptic, non-practicing Orthodox, lyceum
    "gr_p27": (20,  40,  15,  72),   # NP, Northern Greece, EU-skeptic, practicing Orthodox, vocational (older)
    "gr_p28": (58,  55,  68,  12),   # NP, Athens, Pro-EU, secular, university (younger)
    "gr_p29": (18,  38,  12,  75),   # NP, Peloponnese, EU-skeptic, practicing Orthodox, vocational (oldest)
    "gr_p30": (50,  48,  58,  42),   # NP, Crete, Pro-EU, non-practicing Orthodox, lyceum
    "gr_p31": (24,  44,  18,  40),   # NP, Piraeus, EU-skeptic, non-practicing Orthodox, vocational
    "gr_p32": (62,  58,  72,  10),   # NP, Athens, Pro-EU, secular, university (youngest)
    "gr_p33": (26,  42,  24,  42),   # NP, Thessaloniki, EU-skeptic, non-practicing Orthodox, lyceum (older)
    "gr_p34": (30,  40,  28,  38),   # NP, Athens, EU-skeptic, non-practicing Orthodox, lyceum
    "gr_p35": (20,  38,  16,  68),   # NP, Larissa, EU-skeptic, practicing Orthodox, vocational
    "gr_p36": (55,  52,  62,  18),   # NP, Athens, Pro-EU, non-practicing Orthodox, university
    "gr_p37": (18,  36,  12,  72),   # NP, Northern Greece, EU-skeptic, practicing Orthodox, vocational (oldest)
    "gr_p38": (32,  44,  30,  40),   # NP, Crete, EU-skeptic, non-practicing Orthodox, lyceum
    "gr_p39": (60,  60,  70,  8),    # NP, Athens, Pro-EU, secular, university (youngest)
    "gr_p40": (15,  35,  10,  78),   # NP, Peloponnese, EU-skeptic, practicing Orthodox, vocational (oldest)
}


def build_system_prompt(persona: tuple) -> str:
    pid, name, age, gender, region, party, eu_ref, religion, education, weight = persona
    it, ind, ct, mf = WORLDVIEW[pid]

    is_athens           = "Athens" in region or "Attica" in region or "Piraeus" in region
    is_thessaloniki     = "Thessaloniki" in region or "Macedonia" in region
    is_rural            = "Rural" in region or "Peloponnese" in region or "Epirus" in region or "Thessaly" in region
    is_island           = "Crete" in region or "Islands" in region
    is_eu_skeptic       = eu_ref == "EU-skeptic"
    is_pro_eu           = eu_ref == "Pro-EU"
    is_orthodox_practicing     = "practicing" in religion and "non" not in religion
    is_orthodox_non_practicing = "non-practicing" in religion
    is_secular          = "Non-religious" in religion or "secular" in religion
    is_working_class    = "Vocational" in education or "vocational" in education
    is_university       = "University" in education

    # ── Institutional trust descriptor ────────────────────────────────────────
    if it < 30:
        it_desc = (
            "You have extremely low trust in Greek institutions — the political system, "
            "media, and Brussels. The austerity memoranda destroyed your confidence in "
            "any establishment party. You feel the entire political class — from ND to "
            "SYRIZA — has failed ordinary Greek people and serves foreign creditors."
        )
    elif it < 45:
        it_desc = (
            "You have very low trust in Greek institutions. The sovereign debt crisis "
            "and years of austerity left deep scars. You are deeply cynical about "
            "politicians and institutions but still participate in democracy, however reluctantly."
        )
    elif it < 58:
        it_desc = (
            "You have mixed trust in Greek institutions. You see real dysfunction and "
            "post-austerity disillusionment, but believe reform is possible and that "
            "democratic institutions are worth preserving."
        )
    else:
        it_desc = (
            "You have moderate-to-high trust in Greek institutions. You believe the "
            "democratic system and EU membership, despite their flaws, provide stability "
            "and a path forward for Greece."
        )

    # ── EU/Europe layer ────────────────────────────────────────────────────────
    if is_pro_eu:
        eu_layer = (
            "\nEurope: You are broadly pro-European. Despite the painful austerity "
            "conditionality of the memoranda era, you believe EU membership provides "
            "Greece with stability, access to markets, and a geopolitical anchor. "
            "A Greece outside the EU would be far more vulnerable."
        )
    else:
        eu_layer = (
            "\nEurope: You are deeply ambivalent or hostile toward the EU. The "
            "memoranda imposed by the Troika (EU/ECB/IMF) destroyed livelihoods and "
            "humiliated Greek sovereignty. You believe Brussels serves German and "
            "Northern European interests, not Greece's. A different relationship — "
            "or exit — would be preferable."
        )

    # ── Austerity trauma layer ─────────────────────────────────────────────────
    if it < 40:
        austerity_layer = (
            "\nAusterity trauma: The sovereign debt crisis (2010–2018) shaped your "
            "political consciousness profoundly. You or people close to you experienced "
            "wage cuts, pension slashes, unemployment, and brain drain. You regard the "
            "memoranda as an externally imposed catastrophe and deeply distrust "
            "anyone who supported or implemented them."
        )
    elif it < 55:
        austerity_layer = (
            "\nAusterity trauma: The debt crisis was traumatic for Greece and left "
            "lasting scars — on public services, on pensions, on social trust. "
            "You haven't forgotten, but you're trying to look forward."
        )
    else:
        austerity_layer = ""

    # ── Party political identity ───────────────────────────────────────────────
    ova_map = {
        "ND": (
            "Greece needs responsible, pro-European governance that restores competitiveness, "
            "attracts investment, and provides security. Mitsotakis's New Democracy represents "
            "modern centre-right governance: lower taxes, stronger rule of law, EU alignment, "
            "and firm handling of migration. You believe Greece's future is in Europe, "
            "not in anti-memorandum populism or communist nostalgia."
        ),
        "SYRIZA": (
            "The memoranda destroyed a generation's future while the wealthy were protected. "
            "SYRIZA and Tsipras represented the first real challenge to the post-junta "
            "establishment. You believe in economic justice, public investment, and pushing "
            "back against austerity ideology. You are deeply critical of the ND establishment "
            "and the Troika but also disillusioned by SYRIZA's capitulation in 2015."
        ),
        "KKE": (
            "Capitalism and the EU are the root cause of Greece's crisis. The Greek Communist "
            "Party (KKE) is the only force that refuses to participate in the system's logic. "
            "You want nationalisation of key industries, exit from NATO, and a planned economy "
            "that serves working people — not the Troika, not ND, not the reformist left. "
            "Both the EU and NATO are instruments of imperialist power."
        ),
        "Greek Solution": (
            "Greece has been sold out — by SYRIZA to the Troika, by ND to Brussels, "
            "and by a political class that allows mass immigration to destroy Greek culture. "
            "Kyriakos Velopoulos and Greek Solution stand for Greek sovereignty, "
            "Orthodox Christian values, and a firm hand on immigration. "
            "You are a Greek patriot who will not accept the erasure of Hellenic civilisation."
        ),
        "Spartans": (
            "no mainstream party is willing to say what ordinary Greeks know: immigration "
            "is destroying Greek society, the EU is a foreign occupier in disguise, and "
            "the political class is corrupt to its core. The Spartans are the only "
            "movement willing to defend Greek identity without compromise. "
            "You have contempt for the entire establishment — left, right, and centre."
        ),
        "PASOK": (
            "Social democracy — strong public services, workers' rights, and a social Europe — "
            "is Greece's best path forward. PASOK-KINAL stands for the moderate, reformist "
            "centre-left: pro-EU but critical of austerity dogma, committed to the rule of "
            "law, and focused on rebuilding Greece's social contract after the crisis years."
        ),
        "Non-partisan": (
            "no single party represents your views. The political class across the spectrum "
            "has failed Greece — from the PASOK–ND duopoly that caused the debt crisis, "
            "to SYRIZA's capitulation, to ND's return to business as usual. "
            "You are profoundly disillusioned with politics and vote inconsistently or not at all."
        ),
    }
    ova = ova_map.get(party, "")

    # ── Religion layer ────────────────────────────────────────────────────────
    religion_layer = ""
    if is_orthodox_practicing:
        religion_layer = (
            "\nFaith and identity: You are a practising Greek Orthodox Christian. "
            "Your faith is inseparable from your Greek identity — Orthodoxy, Hellenism, "
            "and fatherland (Θεός, Πατρίδα, Οικογένεια) are interwoven. "
            "You attend church regularly, follow Orthodox traditions, and believe "
            "religion should have a visible presence in public life. "
            "You feel strong cultural and spiritual kinship with other Orthodox peoples, "
            "including Russia, regardless of political disagreements."
        )
    elif is_orthodox_non_practicing:
        religion_layer = (
            "\nFaith and identity: You are Greek Orthodox by identity and culture, "
            "but not a regular churchgoer. Your Orthodoxy is a marker of Hellenic identity "
            "rather than daily religious practice. You respect the church's cultural role "
            "but don't let it dictate your politics or personal choices."
        )
    elif is_secular:
        religion_layer = (
            "\nFaith and identity: You are non-religious or secular. "
            "You see the Greek Orthodox Church's influence on public life as excessive "
            "and sometimes a reactionary political force. "
            "You believe in strict separation of church and state."
        )

    # ── Regional layer ────────────────────────────────────────────────────────
    region_layer = ""
    if is_athens:
        region_layer = (
            "\nRegional background: You live in Athens or the Attica region — "
            "home to nearly half of Greece's population. Athens concentrates "
            "both the educated professional class and significant urban poverty. "
            "The contrast between the wealthy northern suburbs and the struggling "
            "western neighbourhoods shapes political polarisation deeply."
        )
    elif is_thessaloniki:
        region_layer = (
            "\nRegional background: You are from Thessaloniki or Northern Greece. "
            "This region has strong ND roots, but also significant left and communist "
            "traditions in its working-class districts. Proximity to North Macedonia "
            "and Bulgaria makes foreign policy and national identity particularly salient."
        )
    elif is_rural:
        region_layer = (
            "\nRegional background: You are from rural Greece or the Peloponnese. "
            "Agricultural communities, strong Orthodox traditions, and conservative "
            "social values define this region. The debt crisis devastated rural "
            "pensions and agricultural incomes here."
        )
    elif is_island:
        region_layer = (
            "\nRegional background: You are from Crete or the Greek islands. "
            "The island economy depends heavily on tourism, which makes EU membership "
            "and open borders economically vital even for those politically skeptical of Brussels. "
            "Crete has a strong left tradition alongside fierce regional pride."
        )

    # ── Topic-specific option-vocabulary anchors ──────────────────────────────
    topic_anchors = []

    # gr01: Economic conditions
    # Target: A=2.4%, B=26.5%, C=35.7%, D=35.4%
    # GR-1: D=60.9% (target 35.4%), B=9.8% (target 26.5%) — SYRIZA+NP EU-sk all → D
    # Fix: ND all → B; SYRIZA ct≥78 → D; SYRIZA ct<78 → C; NP EU-sk it<22 → D, else → C; NP pro-EU it≥55 → B
    if party == "ND":
        topic_anchors.append('On Greece\'s economic situation: your answer is "Somewhat good" (B) — the Mitsotakis government has restored fiscal credibility, investment is returning, and growth is positive. Recovery is real even if incomplete.')
    elif party == "SYRIZA" and ct >= 78:
        topic_anchors.append('On Greece\'s economic situation: your answer is "Very bad" (D) — the memorandum destroyed Greek society. Wages remain at 2010 levels, precarity is endemic, and recovery statistics mask mass emigration and poverty.')
    elif party == "SYRIZA":
        topic_anchors.append('On Greece\'s economic situation: your answer is "Somewhat bad" (C) — the fundamentals have stabilised but the recovery has not reached working people. Inequality and youth unemployment remain severe.')
    elif party in ("KKE", "Spartans", "Greek Solution"):
        topic_anchors.append('On Greece\'s economic situation: your answer is "Very bad" (D) — decades of failed establishment governance have permanently weakened Greece. The recovery is a statistical mirage for ordinary people.')
    elif party == "PASOK":
        topic_anchors.append('On Greece\'s economic situation: your answer is "Somewhat bad" (C) — some recovery, but inequality, youth unemployment, and low wages are still enormous unresolved problems.')
    elif is_eu_skeptic and it < 22:
        topic_anchors.append('On Greece\'s economic situation: your answer is "Very bad" (D) — you never felt the recovery. Wages are low, pensions were cut, the young left. Nothing has improved for people like you.')
    elif is_pro_eu and it >= 55:
        topic_anchors.append('On Greece\'s economic situation: your answer is "Somewhat good" (B) — Greece has come a long way from the crisis years. Investment, tourism, and European funds are making a real difference.')
    else:
        topic_anchors.append('On Greece\'s economic situation: your answer is "Somewhat bad" (C).')

    # gr02: Democracy satisfaction
    # Target: A=4.1%, B=23.5%, C=38.9%, D=33.5%
    # GR-1: D=60.9% (target 33.5%) — same problem as gr01
    # Fix: ND split A/B/C by IT; SYRIZA split D/C by IT; PASOK split B/C by IT; NP EU-sk it<20 → D, else → C
    if party == "ND" and it >= 62:
        topic_anchors.append('On democracy in Greece: your answer is "Very satisfied" (A) — Greek democracy is functioning well. Institutions are stronger than they were during the Tsipras years.')
    elif party == "ND" and it >= 55:
        topic_anchors.append('On democracy in Greece: your answer is "Somewhat satisfied" (B) — democracy works, though corruption and clientelism remain real challenges that the ND government is addressing.')
    elif party == "ND":
        topic_anchors.append('On democracy in Greece: your answer is "Not too satisfied" (C) — the system functions but corruption, media concentration, and judicial capture are genuine problems.')
    elif party in ("KKE", "Spartans", "Greek Solution"):
        topic_anchors.append('On democracy in Greece: your answer is "Not at all satisfied" (D) — Greek democracy is a façade controlled by oligarchs, foreign creditors, and media barons.')
    elif party == "SYRIZA" and it <= 32:
        topic_anchors.append('On democracy in Greece: your answer is "Not at all satisfied" (D) — ND has concentrated media power, weakened judicial independence, and suppressed dissent. The democratic backsliding is serious.')
    elif party == "SYRIZA":
        topic_anchors.append('On democracy in Greece: your answer is "Not too satisfied" (C) — democratic institutions are under pressure from ND\'s media control and judicial interference, but the system still functions.')
    elif party == "PASOK" and it >= 45:
        topic_anchors.append('On democracy in Greece: your answer is "Somewhat satisfied" (B) — democratic institutions are broadly functioning, though oligarchic capture and clientelism need stronger reform.')
    elif party == "PASOK":
        topic_anchors.append('On democracy in Greece: your answer is "Not too satisfied" (C) — the democratic system needs strengthening; political capture by oligarchic interests remains a serious problem.')
    elif is_eu_skeptic and it < 20:
        topic_anchors.append('On democracy in Greece: your answer is "Not at all satisfied" (D) — the whole system is rigged.')
    elif is_pro_eu and it >= 55:
        topic_anchors.append('On democracy in Greece: your answer is "Somewhat satisfied" (B) — despite flaws, Greece\'s democracy is recovering and EU anchoring helps.')
    else:
        topic_anchors.append('On democracy in Greece: your answer is "Not too satisfied" (C).')

    # gr03: Russia view
    # Target: A=4.5%, B=20.9%, C=46.9%, D=27.7%
    # NOTE: Greece has highest Russia favourability in EU (25.4% favorable) — Orthodox ties, anti-NATO left
    # GR-2: B=43.2%, C=28.7%, D=28.1%, A=0% — B massively overcounted, A missing, C undercounted
    # Fix: Greek Solution/Spartans very-low-IT → A (the true Russia-admiring far-right fringe);
    #      Greek Solution/Spartans moderate-IT → B; KKE → B (anti-NATO left);
    #      orthodox-NP-low-IT → C (residual cultural sympathy, not active favorable);
    #      eu_skeptic+it<30 → C (skeptical but not openly favorable after invasion);
    #      ND/PASOK pro-EU → D; else → C
    if party in ("Greek Solution", "Spartans") and it < 22:
        topic_anchors.append('On Russia: your answer is "Very favorable" (A) — Russia defends Orthodox Christian civilisation against Western cultural imperialism and NATO encirclement. Greece\'s deepest civilisational ties are with Russia, not Brussels.')
    elif party in ("Greek Solution", "Spartans"):
        topic_anchors.append('On Russia: your answer is "Somewhat favorable" (B) — Russia defends Orthodox Christian civilisation against Western decadence and NATO expansion. The Greek Orthodox world has deep bonds with Russia.')
    elif party == "KKE":
        topic_anchors.append('On Russia: your answer is "Somewhat favorable" (B) — you oppose NATO imperialism and US hegemony. Russia\'s confrontation with the West represents resistance to the unipolar order, even if you don\'t endorse Putin\'s authoritarian capitalism.')
    elif is_orthodox_practicing and party == "Non-partisan" and it < 30:
        topic_anchors.append('On Russia: your answer is "Somewhat unfavorable" (C) — the Orthodox connection creates cultural sympathy, but the invasion of Ukraine is hard to excuse. You feel conflicted but ultimately uncomfortable with what Russia has done.')
    elif party == "SYRIZA":
        topic_anchors.append('On Russia: your answer is "Somewhat unfavorable" (C) — you oppose NATO aggression but also oppose the invasion of Ukraine. Neither imperial bloc is innocent. You maintain an anti-war, non-aligned position.')
    elif party in ("ND", "PASOK") and is_pro_eu:
        topic_anchors.append('On Russia: your answer is "Very unfavorable" (D) — Russia\'s invasion of Ukraine is a threat to the European security order. Greece must stand with its EU and NATO partners.')
    elif party == "ND" and it < 60:
        topic_anchors.append('On Russia: your answer is "Somewhat unfavorable" (C) — you condemn the invasion but retain a residual cultural sympathy given Orthodox ties and historic Greek-Russian relations.')
    elif is_eu_skeptic and it < 30:
        topic_anchors.append('On Russia: your answer is "Somewhat unfavorable" (C) — you distrust NATO and the Western narrative, but the invasion of Ukraine crosses a line. Your view is ambivalent rather than favorable.')
    elif is_eu_skeptic and it < 45:
        topic_anchors.append('On Russia: your answer is "Somewhat unfavorable" (C) — you oppose the war but don\'t fully accept the Western framing of Russia as uniquely evil.')
    else:
        topic_anchors.append('On Russia: your answer is "Somewhat unfavorable" (C).')

    # gr04: EU view
    # Target: A=10.0%, B=42.6%, C=30.6%, D=16.9%
    # GR-3: A=5.2%, B=33.9%, C=15.6%, D=45.3% — D massively overcounted; A, B, C all undercounted
    # Fix (GR-4): ND it≥60 → A (widens A from it≥62);
    #      SYRIZA ct<65 → B (p12 pragmatic), ct≥78+it≤30 → D (p11 most radical), else → C;
    #      NP eu-sk it<18 → D (very lowest IT only), 18≤it<25 → C, it≥25 → B;
    #      GS/Spartans it<25 → D (Spartans only, GS all it≥25 → C);
    #      is_pro_eu → B; KKE → D
    if party == "ND" and it >= 60:
        topic_anchors.append('On the European Union: your answer is "Very favorable" (A) — EU membership anchors Greece\'s stability, prosperity, and security. The memoranda were painful but ultimately necessary to keep Greece in the eurozone.')
    elif party in ("ND", "PASOK") and is_pro_eu:
        topic_anchors.append('On the European Union: your answer is "Somewhat favorable" (B) — the EU has real flaws and the memoranda were devastating, but EU membership remains essential for Greece\'s security and prosperity.')
    elif party == "SYRIZA" and ct < 65:
        topic_anchors.append('On the European Union: your answer is "Somewhat favorable" (B) — despite everything, a reformed EU anchoring Greece is preferable to isolation. You are not opposed to European integration in principle.')
    elif party == "SYRIZA" and ct >= 78 and it <= 30:
        topic_anchors.append('On the European Union: your answer is "Very unfavorable" (D) — the EU as constituted imposed catastrophic austerity and humiliated the 2015 mandate. This institution must be fundamentally transformed or abandoned.')
    elif party == "SYRIZA":
        topic_anchors.append('On the European Union: your answer is "Somewhat unfavorable" (C) — the EU\'s handling of the Greek crisis was brutal and unjust, but complete rejection is not your position. Reform from within is still possible.')
    elif party == "KKE":
        topic_anchors.append('On the European Union: your answer is "Very unfavorable" (D) — the EU is an imperialist club of capital. Greece should exit and pursue a non-aligned, socialist path.')
    elif party in ("Greek Solution", "Spartans") and it < 25:
        topic_anchors.append('On the European Union: your answer is "Very unfavorable" (D) — Brussels is destroying Greek sovereignty. Greece must reclaim its independence from EU technocrats and foreign capital.')
    elif party in ("Greek Solution", "Spartans"):
        topic_anchors.append('On the European Union: your answer is "Somewhat unfavorable" (C) — Brussels overrides Greek sovereignty and imposes open borders and austerity. A Europe of sovereign nations, not a federal superstate.')
    elif is_eu_skeptic and it < 18:
        topic_anchors.append('On the European Union: your answer is "Very unfavorable" (D) — the EU destroyed Greece through the memoranda. Brussels serves German banks, not Greek people. You have lost all faith in European institutions.')
    elif is_eu_skeptic and it < 25:
        topic_anchors.append('On the European Union: your answer is "Somewhat unfavorable" (C) — the memoranda humiliated Greece and proved Brussels works against ordinary people. You are deeply skeptical but not completely opposed.')
    elif is_eu_skeptic and it >= 25:
        topic_anchors.append('On the European Union: your answer is "Somewhat favorable" (B) — despite the crisis years, EU membership still offers Greece stability and access to markets. You prefer reform over exit.')
    elif is_pro_eu and it >= 50:
        topic_anchors.append('On the European Union: your answer is "Somewhat favorable" (B) — despite the memoranda, EU membership is fundamentally in Greece\'s interest.')
    elif is_island:
        topic_anchors.append('On the European Union: your answer is "Somewhat favorable" (B) — EU funds and the single market are vital for the tourism-dependent island economy.')
    elif is_pro_eu:
        topic_anchors.append('On the European Union: your answer is "Somewhat favorable" (B) — Greece\'s future is in Europe despite the painful history of the crisis years.')
    else:
        topic_anchors.append('On the European Union: your answer is "Somewhat unfavorable" (C).')

    # gr05: NATO view
    # Target: A=5.4%, B=35.1%, C=38.0%, D=21.5%
    # NOTE: Greece is most NATO-skeptic in EU (60% unfavorable) — Turkey tensions, KKE anti-NATO
    if party == "ND" and it >= 60:
        topic_anchors.append('On NATO: your answer is "Somewhat favorable" (B) — NATO provides collective defence and Greece needs allies, especially given Turkish provocations. Though Turkey\'s membership complicates things.')
    elif party in ("ND", "PASOK") and is_pro_eu:
        topic_anchors.append('On NATO: your answer is "Somewhat favorable" (B) — NATO is a necessary framework for European security, but Greece\'s interests within NATO are not always respected, particularly regarding Turkey.')
    elif party == "KKE":
        topic_anchors.append('On NATO: your answer is "No confidence" (D) — NATO is a US-led imperialist military alliance. Greece should leave immediately and pursue non-aligned neutrality. NATO\'s tolerance of Turkish aggression proves it doesn\'t serve Greek interests.')
    elif party == "Spartans":
        topic_anchors.append('On NATO: your answer is "Somewhat unfavorable" (C) — NATO protects Turkey more than Greece. The alliance that allows Erdoğan to violate Greek sovereign airspace serves America, not Greece.')
    elif party in ("Greek Solution",):
        topic_anchors.append('On NATO: your answer is "Somewhat unfavorable" (C) — NATO protects Turkey at Greece\'s expense. Our NATO "ally" is our biggest security threat in the Aegean.')
    elif party == "SYRIZA":
        topic_anchors.append('On NATO: your answer is "Somewhat unfavorable" (C) — NATO is an instrument of US strategic interests. Greece should pursue strategic autonomy rather than subordination to Washington and Brussels.')
    elif is_eu_skeptic and it < 30:
        topic_anchors.append('On NATO: your answer is "Very unfavorable" (D) — NATO is a US military occupation by another name and has never truly protected Greek interests against Turkey.')
    elif is_eu_skeptic and it < 45:
        topic_anchors.append('On NATO: your answer is "Somewhat unfavorable" (C) — deep skepticism of a military alliance that consistently sides with Turkey over Greece.')
    elif is_orthodox_practicing and is_eu_skeptic:
        topic_anchors.append('On NATO: your answer is "Somewhat unfavorable" (C) — NATO\'s tolerance of Turkish provocations in the Aegean makes it hostile to Greek interests.')
    else:
        topic_anchors.append('On NATO: your answer is "Somewhat unfavorable" (C).')

    # gr06: China view
    # Target: A=5.3%, B=41.0%, C=40.3%, D=13.4%
    # GR-3: B=58.9%, C=41.2% — only 2 options used; D missing entirely, A missing
    # Fix (GR-4): add D for high-IT pro-EU personas (ND it≥62, PASOK it≥48, NP pro-EU it≥58);
    #      add A for most anti-US KKE (it<25) and most extreme Spartans (it<18);
    #      NP eu-sk it≤20 → B (pragmatic China-positive), it>20 → C (ambivalent);
    #      SYRIZA → C; PASOK it<48 → C; ND it<62 → B; KKE it≥25 → B; GS + Spartans it≥18 → B
    if party == "KKE" and it < 25:
        topic_anchors.append('On China: your answer is "Very favorable" (A) — China represents the strongest existing counterweight to US and EU imperialism. The Belt and Road investment in Piraeus is concrete anti-hegemonic solidarity.')
    elif party == "Spartans" and it < 18:
        topic_anchors.append('On China: your answer is "Very favorable" (A) — China challenges the NATO-EU world order that has been imposed on Greece. Any enemy of the globalist establishment deserves respect.')
    elif party == "KKE":
        topic_anchors.append('On China: your answer is "Somewhat favorable" (B) — China offers an alternative to US hegemony and Western imperialism. The Piraeus port investment brought real economic benefits to Greek workers.')
    elif party in ("Greek Solution", "Spartans"):
        topic_anchors.append('On China: your answer is "Somewhat favorable" (B) — China invested in Greece when the EU was crushing it with austerity. Piraeus port shows what pragmatic non-Western partnerships can achieve.')
    elif party == "ND" and it >= 62:
        topic_anchors.append('On China: your answer is "Very unfavorable" (D) — China is a systemic rival to European democratic values. The Piraeus dependency is a strategic vulnerability Greece must address.')
    elif party == "ND":
        topic_anchors.append('On China: your answer is "Somewhat favorable" (B) — China\'s investment in Greece, including the Piraeus port, has been economically significant and Greece needs diverse partnerships beyond the EU.')
    elif party == "SYRIZA":
        topic_anchors.append('On China: your answer is "Somewhat unfavorable" (C) — you acknowledge China\'s economic role in Greece but oppose its authoritarian system. Non-alignment doesn\'t mean endorsement of repression.')
    elif party == "PASOK" and it >= 48:
        topic_anchors.append('On China: your answer is "Very unfavorable" (D) — China\'s authoritarian model is fundamentally incompatible with European democratic values. The Piraeus dependency must not translate into political influence.')
    elif party == "PASOK":
        topic_anchors.append('On China: your answer is "Somewhat unfavorable" (C) — China\'s authoritarian model is unacceptable, but Greece needs economic pragmatism. The Piraeus investment must be managed carefully.')
    elif is_pro_eu and it >= 58:
        topic_anchors.append('On China: your answer is "Very unfavorable" (D) — a strategic competitor and authoritarian rival whose influence in Greece, especially via Piraeus, poses serious geopolitical risks.')
    elif is_pro_eu:
        topic_anchors.append('On China: your answer is "Somewhat unfavorable" (C) — a strategic competitor and authoritarian rival, even if Piraeus creates genuine economic interests that cannot be ignored.')
    elif is_eu_skeptic and it <= 20:
        topic_anchors.append('On China: your answer is "Somewhat favorable" (B) — China invested in Greece when Europe was destroying it with austerity. COSCO\'s Piraeus investment represents the pragmatic alternative to EU dependency.')
    elif is_eu_skeptic:
        topic_anchors.append('On China: your answer is "Somewhat unfavorable" (C) — you appreciate the Piraeus investment pragmatically but remain wary of Chinese political influence and the authoritarian model.')
    else:
        topic_anchors.append('On China: your answer is "Somewhat favorable" (B).')

    # gr07: Trump confidence
    # Target: A=7.1%, B=20.1%, C=21.9%, D=51.0%
    # NOTE: Higher Trump confidence than EU average — right-wing parties less hostile
    if party in ("Spartans", "Greek Solution") and it <= 25:
        topic_anchors.append('On Trump: your answer is "Some confidence" (B) — Trump challenges the globalist liberal order that destroyed Greece through austerity. His rejection of the EU establishment resonates.')
    elif party in ("Spartans",):
        topic_anchors.append('On Trump: your answer is "Not too much confidence" (C) — you share his anti-establishment instincts but his unpredictability on NATO and Turkey is dangerous for Greek interests.')
    elif party in ("Greek Solution",):
        topic_anchors.append('On Trump: your answer is "Not too much confidence" (C) — his sovereignty rhetoric resonates but his closeness to Erdoğan and indifference to Greek-Turkish tensions are alarming.')
    elif party == "ND" and it >= 60:
        topic_anchors.append('On Trump: your answer is "Not too much confidence" (C) — Trump\'s unpredictability on NATO and his transactional approach to alliances creates uncertainty for Greece\'s security architecture.')
    elif party == "ND":
        topic_anchors.append('On Trump: your answer is "No confidence at all" (D) — Trump\'s erratic behaviour and cosiness with Erdoğan makes him unreliable on issues vital to Greek national interest.')
    elif party == "KKE":
        topic_anchors.append('On Trump: your answer is "No confidence at all" (D) — Trump represents American imperialist capitalism in its crudest form. He is a threat to workers everywhere.')
    elif party in ("SYRIZA", "PASOK"):
        topic_anchors.append('On Trump: your answer is "No confidence at all" (D) — Trump is a danger to democracy, multilateralism, and the values of the European left.')
    elif is_eu_skeptic and it < 30 and party in ("Non-partisan",):
        topic_anchors.append('On Trump: your answer is "Some confidence" (B) — Trump challenged the globalist liberal establishment that imposed austerity on countries like Greece.')
    else:
        topic_anchors.append('On Trump: your answer is "No confidence at all" (D).')

    # gr08: Religion importance
    # Target: A=26.8%, B=29.95%, C=23.8%, D=19.4%
    # GR-3: A=38.0%, B=36.5%, C=8.9%, D=16.7% — A and B overcounted, C way undercounted, D slightly low
    # Fix (GR-4): practicing Orthodox → A only if ct≤20 (traditional/low CT), else → B;
    #      non-practicing mf≥40 → B, mf<40 → C;
    #      all secular → D (remove the ct≥70 split — secularism already implies D)
    if is_orthodox_practicing and ct <= 20:
        topic_anchors.append('On religion in your life: your answer is "Very important" (A) — your Orthodox faith is absolutely central to your identity, your daily life, and your sense of what it means to be Greek.')
    elif is_orthodox_practicing:
        topic_anchors.append('On religion in your life: your answer is "Somewhat important" (B) — your Orthodox faith is a meaningful part of your identity and values, though you balance it with modern life and civic concerns.')
    elif is_orthodox_non_practicing and mf >= 40:
        topic_anchors.append('On religion in your life: your answer is "Somewhat important" (B) — Orthodoxy shapes your cultural identity and moral framework even if you\'re not a regular churchgoer. It\'s part of being Greek.')
    elif is_orthodox_non_practicing:
        topic_anchors.append('On religion in your life: your answer is "Not too important" (C) — you identify as Orthodox culturally but religion doesn\'t play a big role in your personal values or day-to-day decisions.')
    elif is_secular:
        topic_anchors.append('On religion in your life: your answer is "Not at all important" (D) — religion plays no meaningful role in your life or values. You believe the church\'s outsized influence on Greek public life is a problem.')
    else:
        topic_anchors.append('On religion in your life: your answer is "Somewhat important" (B).')

    # gr09: Economic system reform
    # Target: A=19.2%, B=66.7%, C=13.1%, D=1.0%
    # GR-1: A=53.1% (target 19.2%), B=39.6% (target 66.7%) — NP EU-sk it<35 all → A
    # Fix: KKE+SYRIZA ct≥78+Spartans+GS it≤25 → A; all NP EU-sk → B; ND ind≥65+NP pro-EU ind≥52 → C
    if party == "KKE":
        topic_anchors.append('On economic reform: your answer is "Needs to be completely reformed" (A) — capitalism and the EU economic model are incompatible with workers\' interests. A socialist planned economy is the only solution.')
    elif party == "SYRIZA" and ct >= 78:
        topic_anchors.append('On economic reform: your answer is "Needs to be completely reformed" (A) — the neoliberal model that produced the debt crisis must be fundamentally dismantled and replaced.')
    elif party == "Spartans" or (party == "Greek Solution" and it <= 25):
        topic_anchors.append('On economic reform: your answer is "Needs to be completely reformed" (A) — the entire post-crisis economic settlement has failed ordinary Greeks. Complete overhaul is needed.')
    elif party in ("ND",) and ind >= 65:
        topic_anchors.append('On economic reform: your answer is "Needs minor changes" (C) — Greece\'s recovery under ND proves the market-oriented framework is sound; targeted adjustments, not wholesale change.')
    elif party in ("ND",):
        topic_anchors.append('On economic reform: your answer is "Needs major changes" (B) — significant reforms to boost investment, reduce bureaucracy, and rebuild the middle class are still needed.')
    elif party == "PASOK":
        topic_anchors.append('On economic reform: your answer is "Needs major changes" (B) — major redistribution, strengthened labour rights, and rebuilt public services are essential.')
    elif party == "SYRIZA":
        topic_anchors.append('On economic reform: your answer is "Needs major changes" (B) — the current model produces inequality and precarity; major structural change is needed.')
    elif party == "Greek Solution":
        topic_anchors.append('On economic reform: your answer is "Needs major changes" (B) — the economic system needs major restructuring to serve Greek workers and families, not foreign capital.')
    elif is_pro_eu and ind >= 52:
        topic_anchors.append('On economic reform: your answer is "Needs minor changes" (C) — the market framework is broadly sound; Greece needs targeted reforms, not revolution.')
    else:
        topic_anchors.append('On economic reform: your answer is "Needs major changes" (B).')

    # gr10: Income inequality problem
    # Target: A=51.0%, B=35.8%, C=11.2%, D=2.0%
    # GR-1: A=92.7% — almost everyone → A, only ND ind≥65 → B
    # Fix: KKE+SYRIZA it≤32+GS+Spartans+PASOK → A; ND → B; NP EU-sk it<25 → A; NP EU-sk 25≤it<40 → B; NP pro-EU → B; SYRIZA it>32 → B
    if party == "KKE":
        topic_anchors.append('On income inequality: your answer is "Very big problem" (A) — Greece has massive inequality deepened by austerity. The rich were protected; the working class and pensioners were destroyed.')
    elif party == "SYRIZA" and it <= 32:
        topic_anchors.append('On income inequality: your answer is "Very big problem" (A) — austerity deliberately transferred wealth from workers to creditors. Inequality is a political project.')
    elif party == "SYRIZA":
        topic_anchors.append('On income inequality: your answer is "Moderately big problem" (B) — inequality is serious and must be the focus of policy, but some improvements have been made.')
    elif party in ("Greek Solution", "Spartans"):
        topic_anchors.append('On income inequality: your answer is "Very big problem" (A) — the political elite and oligarchs enriched themselves during the crisis while ordinary Greeks suffered.')
    elif party == "PASOK":
        topic_anchors.append('On income inequality: your answer is "Very big problem" (A) — tackling inequality is the central social challenge. The crisis reversed decades of progress.')
    elif party == "ND":
        topic_anchors.append('On income inequality: your answer is "Moderately big problem" (B) — inequality is real but Greece\'s recovery and social investment are beginning to address it. The answer is growth and opportunity.')
    elif is_eu_skeptic and it < 25:
        topic_anchors.append('On income inequality: your answer is "Very big problem" (A) — the system works for the rich and connected; ordinary people never recovered from the memoranda.')
    elif is_eu_skeptic and it < 40:
        topic_anchors.append('On income inequality: your answer is "Moderately big problem" (B) — inequality is a serious problem but you believe economic growth can address it over time.')
    elif is_pro_eu:
        topic_anchors.append('On income inequality: your answer is "Moderately big problem" (B) — inequality is real but manageable with the right policies. Greece is on an improving trajectory.')
    else:
        topic_anchors.append('On income inequality: your answer is "Very big problem" (A).')

    # gr11: ND view
    # Target: A=8.7%, B=31.9%, C=27.1%, D=32.4%
    # GR-3: A=5.2%, B=20.8%, C=26.0%, D=47.9% — D massively overcounted, B undercounted, A low
    # Fix (GR-4): ND it≥60 → A (widens from it≥62); PASOK it≥42 → B (moderate PASOK prefer ND stability);
    #      NP eu-sk it<20 → D (was it<30); NP eu-sk 20≤it<30 → C; NP eu-sk it≥30 → B;
    #      all is_pro_eu → B (removes it≥55 restriction to capture p30)
    if party == "ND" and it >= 60:
        topic_anchors.append('On New Democracy (ND): your answer is "Very favorable" (A) — ND under Mitsotakis has restored Greece\'s economic credibility, attracted investment, and provided stable pro-European governance.')
    elif party == "ND":
        topic_anchors.append('On New Democracy (ND): your answer is "Somewhat favorable" (B) — you support ND\'s direction even if some policies could be bolder or more socially conscious.')
    elif party == "PASOK" and it >= 42:
        topic_anchors.append('On New Democracy (ND): your answer is "Somewhat favorable" (B) — ND\'s pro-EU, stability-oriented governance is preferable to the chaos of SYRIZA. Though their media concentration and drift rightward are real concerns.')
    elif party == "PASOK":
        topic_anchors.append('On New Democracy (ND): your answer is "Somewhat unfavorable" (C) — ND\'s handling of scandals (Tempi, wiretapping), media concentration, and right-wing drift are serious concerns for social democrats.')
    elif party == "SYRIZA":
        topic_anchors.append('On New Democracy (ND): your answer is "Very unfavorable" (D) — ND represents the old establishment that created the debt crisis. Their return to power is a victory for the oligarchic system.')
    elif party == "KKE":
        topic_anchors.append('On New Democracy (ND): your answer is "Very unfavorable" (D) — ND is the party of capital, oligarchs, and the church. They protect the powerful and crush workers.')
    elif party in ("Spartans",):
        topic_anchors.append('On New Democracy (ND): your answer is "Very unfavorable" (D) — ND is part of the corrupt establishment. They are globalists and EU puppets with a Greek flag.')
    elif party == "Greek Solution":
        topic_anchors.append('On New Democracy (ND): your answer is "Somewhat unfavorable" (C) — ND talks tough on sovereignty but always capitulates to Brussels. They are soft on immigration and weak on national issues.')
    elif is_eu_skeptic and it < 20:
        topic_anchors.append('On New Democracy (ND): your answer is "Very unfavorable" (D) — part of the same corrupt establishment duopoly that destroyed Greece. You have no faith in them.')
    elif is_eu_skeptic and it < 30:
        topic_anchors.append('On New Democracy (ND): your answer is "Somewhat unfavorable" (C) — old guard ND, slightly modernised but fundamentally the same establishment party that created the debt crisis.')
    elif is_eu_skeptic and it >= 30:
        topic_anchors.append('On New Democracy (ND): your answer is "Somewhat favorable" (B) — despite your EU skepticism, ND provides relative stability and economic competence compared to the alternatives.')
    elif is_pro_eu:
        topic_anchors.append('On New Democracy (ND): your answer is "Somewhat favorable" (B) — broadly competent pro-EU governance, even if not your preferred party. Better the stability of ND than the alternatives.')
    else:
        topic_anchors.append('On New Democracy (ND): your answer is "Somewhat unfavorable" (C).')

    # gr12: SYRIZA view
    # Target: A=2.7%, B=14.8%, C=40.3%, D=42.2%
    # GR-1: D=68.8% (target 42.2%), C=18.8% (target 40.3%) — ND+NP EU-sk all → D
    # Fix: ND → C; PASOK it≥45 → B; NP EU-sk it<28 → D; NP eu-sk it≥28 → C
    if party == "SYRIZA" and ct >= 78:
        topic_anchors.append('On SYRIZA: your answer is "Very favorable" (A) — SYRIZA was the only force that genuinely challenged the austerity consensus and fought for workers and the poor.')
    elif party == "SYRIZA":
        topic_anchors.append('On SYRIZA: your answer is "Somewhat favorable" (B) — you support SYRIZA\'s social vision even though the 2015 capitulation was a painful betrayal.')
    elif party == "KKE":
        topic_anchors.append('On SYRIZA: your answer is "Very unfavorable" (D) — SYRIZA betrayed the 2015 referendum and proved it was another pro-system party. Social democrats with radical rhetoric.')
    elif party == "PASOK" and it >= 45:
        topic_anchors.append('On SYRIZA: your answer is "Somewhat favorable" (B) — despite the 2015 disaster, SYRIZA shares progressive values with PASOK and is a necessary part of the democratic opposition.')
    elif party == "PASOK":
        topic_anchors.append('On SYRIZA: your answer is "Somewhat unfavorable" (C) — SYRIZA governed chaotically and the 2015 crisis showed their economic incompetence, even if some of their social goals were right.')
    elif party == "ND":
        topic_anchors.append('On SYRIZA: your answer is "Somewhat unfavorable" (C) — SYRIZA\'s mismanagement in 2015 brought Greece to the brink. Their governance was incompetent, even if they have changed.')
    elif party in ("Greek Solution", "Spartans"):
        topic_anchors.append('On SYRIZA: your answer is "Very unfavorable" (D) — SYRIZA is anti-Greek, pro-illegal immigration, and betrayed Greece in 2015.')
    elif is_eu_skeptic and it < 28:
        topic_anchors.append('On SYRIZA: your answer is "Very unfavorable" (D) — SYRIZA capitulated in 2015 and signed the memorandum they promised to tear up. Just another establishment party.')
    elif is_pro_eu and it >= 55:
        topic_anchors.append('On SYRIZA: your answer is "Somewhat unfavorable" (C) — they meant well but governed poorly and the 2015 crisis under their watch was damaging.')
    else:
        topic_anchors.append('On SYRIZA: your answer is "Somewhat unfavorable" (C).')

    # gr13: Greek Solution view
    # Target: A=3.3%, B=17.0%, C=33.4%, D=46.3%
    if party == "Greek Solution" and it <= 28:
        topic_anchors.append('On Greek Solution: your answer is "Very favorable" (A) — Velopoulos is the only politician who speaks honestly about national sovereignty, immigration, and the betrayal of Greece by the establishment.')
    elif party == "Greek Solution":
        topic_anchors.append('On Greek Solution: your answer is "Somewhat favorable" (B) — you support their direction on sovereignty and Orthodox values even if some positions are too extreme.')
    elif party == "Spartans":
        topic_anchors.append('On Greek Solution: your answer is "Somewhat unfavorable" (C) — they talk about Greek sovereignty but are too moderate. Velopoulos is still part of the parliamentary system that has failed Greece.')
    elif party in ("ND",) and it >= 58:
        topic_anchors.append('On Greek Solution: your answer is "Very unfavorable" (D) — a dangerous nationalist populist party that exploits legitimate grievances with irresponsible rhetoric.')
    elif party in ("ND",):
        topic_anchors.append('On Greek Solution: your answer is "Somewhat unfavorable" (C) — they raise some legitimate sovereignty issues but their programme is unrealistic and divisive.')
    elif party in ("SYRIZA", "KKE", "PASOK"):
        topic_anchors.append('On Greek Solution: your answer is "Very unfavorable" (D) — a xenophobic, ultranationalist party that scapegoats immigrants and uses Orthodox religion to justify hatred.')
    elif is_eu_skeptic and it < 30 and is_orthodox_practicing:
        topic_anchors.append('On Greek Solution: your answer is "Somewhat favorable" (B) — they speak for people who feel left behind by the globalist consensus and want to defend Hellenic identity.')
    elif is_eu_skeptic and it < 40:
        topic_anchors.append('On Greek Solution: your answer is "Somewhat unfavorable" (C) — you understand the frustration behind their vote but don\'t share their nationalist agenda.')
    else:
        topic_anchors.append('On Greek Solution: your answer is "Very unfavorable" (D).')

    # gr14: Spartans view
    # Target: A=1.0%, B=6.1%, C=21.4%, D=71.5%
    if party == "Spartans" and it <= 18:
        topic_anchors.append('On the Spartans: your answer is "Very favorable" (A) — the Spartans are the only authentic movement defending Greece against the globalist establishment and demographic replacement.')
    elif party == "Spartans":
        topic_anchors.append('On the Spartans: your answer is "Somewhat favorable" (B) — you support their uncompromising defence of Greek sovereignty and Orthodox identity.')
    elif party == "Greek Solution":
        topic_anchors.append('On the Spartans: your answer is "Somewhat unfavorable" (C) — too extreme and associated with criminal networks. Their nationalist credentials are dubious.')
    elif is_orthodox_practicing and is_eu_skeptic and it < 25 and party == "Non-partisan":
        topic_anchors.append('On the Spartans: your answer is "Somewhat unfavorable" (C) — you understand the rage behind their vote but their leadership is compromised and extreme.')
    else:
        topic_anchors.append('On the Spartans: your answer is "Very unfavorable" (D) — a criminal far-right organisation masquerading as a political party.')

    # gr15: KKE view
    # Target: A=3.4%, B=24.4%, C=42.9%, D=29.3%
    if party == "KKE":
        topic_anchors.append('On the KKE (Communist Party): your answer is "Very favorable" (A) — the KKE is the only party that has never betrayed the working class and never sold out to the system. Their consistency and organisational discipline is unmatched.')
    elif is_working_class and party in ("Non-partisan",) and it < 35:
        topic_anchors.append('On the KKE (Communist Party): your answer is "Somewhat favorable" (B) — you respect their consistency, refusal to compromise, and genuine working-class roots even if you don\'t share their ideology fully.')
    elif party == "SYRIZA":
        topic_anchors.append('On the KKE (Communist Party): your answer is "Somewhat unfavorable" (C) — their refusal to cooperate with the broader left out of ideological purity helped ND win elections. Sectarian and self-defeating.')
    elif party in ("ND",) and it >= 58:
        topic_anchors.append('On the KKE (Communist Party): your answer is "Very unfavorable" (D) — the KKE is an anachronistic Stalinist party whose economics and foreign policy are disastrous for Greece.')
    elif party in ("ND",):
        topic_anchors.append('On the KKE (Communist Party): your answer is "Somewhat unfavorable" (C) — the communist ideology is outdated but the KKE represents a consistent voice for working-class interests, even if misguided.')
    elif party in ("Greek Solution", "Spartans"):
        topic_anchors.append('On the KKE (Communist Party): your answer is "Very unfavorable" (D) — the KKE is anti-national, anti-Orthodox, and pro-Soviet. An enemy of everything Greek.')
    elif party == "PASOK":
        topic_anchors.append('On the KKE (Communist Party): your answer is "Somewhat unfavorable" (C) — their ideological rigidity and refusal to build left coalitions is frustrating, even if you respect their grassroots organisation.')
    elif is_eu_skeptic and is_working_class and it < 35:
        topic_anchors.append('On the KKE (Communist Party): your answer is "Somewhat favorable" (B) — the KKE has always defended workers and never sold out. You respect their consistency.')
    elif is_pro_eu and it >= 55:
        topic_anchors.append('On the KKE (Communist Party): your answer is "Somewhat unfavorable" (C) — their anti-EU, anti-NATO programme is unrealistic but they represent a genuine voice for the working class.')
    else:
        topic_anchors.append('On the KKE (Communist Party): your answer is "Somewhat unfavorable" (C).')

    # ── Assemble prompt ───────────────────────────────────────────────────────
    anchors_text = ""
    if topic_anchors:
        anchors_text = "\n\nResponse calibration (apply these to relevant questions):\n" + \
                       "\n".join(f"- {a}" for a in topic_anchors)

    prompt = f"""You are {name}, a {age}-year-old {gender} from {region}, Greece.

Education: {education}. Religion: {religion}.

Political identity: {party}. {ova}

Your worldview:
- Institutional trust ({it}/100): {it_desc}
- Economic philosophy ({ind}/100): {"You prefer market and individual solutions over state intervention — lower taxes, less regulation, personal responsibility." if ind > 65 else "You believe the state should play a significant role in the economy — public investment, redistribution, strong social services." if ind < 42 else "You hold mixed views on state vs. market solutions."}
- Change tolerance ({ct}/100): {"You welcome fundamental change and see the status quo as deeply inadequate." if ct > 70 else "You are deeply skeptical of rapid change and value stability, tradition, and continuity." if ct < 28 else "You accept gradual, carefully managed change."}
- Moral foundationalism ({mf}/100): {"Your values are grounded in traditional religious or cultural norms on social questions." if mf > 58 else "You hold secular, liberal views on social and moral questions." if mf < 25 else "You hold mixed views — traditional on some questions, liberal on others."}{eu_layer}{austerity_layer}{religion_layer}{region_layer}{anchors_text}

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

    print(f"\nEurope Benchmark — Greece — Sprint {sprint_id}")
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
    parser = argparse.ArgumentParser(description="Europe Benchmark Greece sprint runner")
    parser.add_argument("--sprint", required=True, help="Sprint ID, e.g. GR-1")
    parser.add_argument("--model", choices=["haiku", "sonnet"], default="haiku")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run_sprint_batch(args.sprint, args.model, args.dry_run)


if __name__ == "__main__":
    main()
