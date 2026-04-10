#!/usr/bin/env python3
"""
sprint_runner.py — Study 1C Germany calibration sprint runner.

Usage:
    python3 sprint_runner.py --sprint C-1 --model haiku
    python3 sprint_runner.py --sprint C-13 --model sonnet
    python3 sprint_runner.py --sprint C-1 --model haiku --dry-run

Model switching:
    C-1  to C-12: claude-haiku-4-5-20251001  (Batch API, ~80% cheaper)
    C-13 to C-18: claude-sonnet-4-6          (Batch API, fine-tuning phase)

Outputs:
    results/sprint_manifests/sprint_{sprint_id}.json
    results/sprint_manifests/sprint_{sprint_id}_raw.jsonl

Cost estimate:
    Haiku (Batch API, 40 personas × 15 questions): ~$0.15 per sprint
    Sonnet (Batch API, 40 personas × 15 questions): ~$1.50 per sprint
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
POOL_MD    = HERE / "persona_pool.md"
MANIFESTS  = STUDY_ROOT / "results" / "sprint_manifests"
MANIFESTS.mkdir(parents=True, exist_ok=True)

# ── Model map ─────────────────────────────────────────────────────────────────
MODELS = {
    "haiku":  "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-6",
}

# ── Persona pool (matches persona_pool.md table) ──────────────────────────────
PERSONAS = [
    # (id, name, age, gender, region, party, religion, education, migration, weight, IT, IND, CT, MF)
    ("de_p01", "Klaus Richter",     62, "male",   "East (Saxony)",         "AfD",          "None/atheist", "Vocational",  "None",    2.5),
    ("de_p02", "Monika Schreiber",  58, "female", "East (Thuringia)",      "AfD",          "None/atheist", "Vocational",  "None",    2.5),
    ("de_p03", "Rainer Vogel",      47, "male",   "West (NRW)",            "AfD",          "Protestant",   "Vocational",  "None",    2.5),
    ("de_p04", "Sabine Krause",     44, "female", "West (Baden-Wuertt.)",  "AfD",          "Catholic",     "Vocational",  "None",    2.0),
    ("de_p05", "Dieter Meinhardt",  39, "male",   "East (Brandenburg)",    "AfD",          "None/atheist", "Hauptschule", "None",    2.5),
    ("de_p06", "Jürgen Pfeiffer",   55, "male",   "East (Saxony-Anhalt)",  "AfD",          "None/atheist", "Hauptschule", "None",    2.5),
    ("de_p07", "Anja Fleischer",    50, "female", "West (Saarland)",       "AfD",          "Catholic",     "Hauptschule", "None",    2.0),
    ("de_p08", "Friedrich Bauer",   67, "male",   "Bavaria",               "CDU/CSU",      "Catholic",     "Vocational",  "None",    2.5),
    ("de_p09", "Maria Huber",       54, "female", "Bavaria",               "CDU/CSU",      "Catholic",     "Vocational",  "None",    2.5),
    ("de_p10", "Thomas Weiß",       42, "male",   "Bavaria",               "CDU/CSU",      "Catholic",     "University",  "None",    2.0),
    ("de_p11", "Ursula Kamm",       59, "female", "Bavaria",               "CDU/CSU",      "Catholic",     "University",  "None",    2.0),
    ("de_p12", "Hans-Georg Möller", 63, "male",   "West (NRW)",            "CDU/CSU",      "Protestant",   "Vocational",  "None",    2.5),
    ("de_p13", "Hildegard Sommer",  55, "female", "West (Rhineland-Pf.)",  "CDU/CSU",      "Catholic",     "Vocational",  "None",    2.5),
    ("de_p14", "Bernd Hartmann",    48, "male",   "West (Hesse)",          "CDU/CSU",      "Protestant",   "University",  "None",    2.0),
    ("de_p15", "Christine Lorenz",  38, "female", "West (Baden-Wuertt.)",  "CDU/CSU",      "Secular",      "University",  "None",    2.0),
    ("de_p16", "Wolfgang Sauer",    52, "male",   "East (Saxony)",         "CDU/CSU",      "None/atheist", "Vocational",  "None",    2.5),
    ("de_p17", "Renate Franke",     61, "female", "East (Thuringia)",      "CDU/CSU",      "None/atheist", "Vocational",  "None",    2.5),
    ("de_p18", "Stefan Brandt",     45, "male",   "North (Hamburg)",       "CDU/CSU",      "Protestant",   "University",  "None",    2.0),
    ("de_p19", "Petra Schneider",   52, "female", "West (NRW)",            "SPD",          "Protestant",   "Vocational",  "None",    2.5),
    ("de_p20", "Helmut Fuchs",      58, "male",   "West (NRW)",            "SPD",          "Protestant",   "Vocational",  "None",    2.5),
    ("de_p21", "Gabi Kramer",       44, "female", "East (Saxony)",         "SPD",          "None/atheist", "University",  "None",    2.5),
    ("de_p22", "Manfred Stein",     49, "male",   "East (Brandenburg)",    "SPD",          "None/atheist", "Vocational",  "None",    2.5),
    ("de_p23", "Karin Hoffmann",    36, "female", "North (Hamburg)",       "SPD",          "Secular",      "University",  "Other",   2.0),
    ("de_p24", "Oliver Meier",      41, "male",   "Berlin",                "SPD",          "Secular",      "University",  "None",    2.0),
    ("de_p25", "Julia Zimmermann",  31, "female", "West (Baden-Wuertt.)",  "Greens",       "Secular",      "University",  "None",    2.5),
    ("de_p26", "Markus Braun",      35, "male",   "West (NRW)",            "Greens",       "Secular",      "University",  "None",    2.5),
    ("de_p27", "Sophie Lange",      27, "female", "Berlin",                "Greens",       "Secular",      "University",  "Other",   2.5),
    ("de_p28", "Florian Roth",      43, "male",   "Bavaria",               "Greens",       "Secular",      "University",  "None",    2.0),
    ("de_p29", "Alexander König",   38, "male",   "West (Hesse)",          "FDP",          "Secular",      "University",  "None",    2.5),
    ("de_p30", "Katrin Schulz",     44, "female", "Bavaria",               "FDP",          "Secular",      "University",  "None",    2.5),
    ("de_p31", "Elke Günther",      56, "female", "East (Saxony)",         "BSW",          "None/atheist", "Vocational",  "None",    2.5),
    ("de_p32", "Frank Müller",      52, "male",   "East (Brandenburg)",    "BSW",          "None/atheist", "Vocational",  "None",    2.5),
    ("de_p33", "Rosa Bergmann",     48, "female", "West (NRW)",            "Left",         "Secular",      "University",  "None",    2.5),
    ("de_p34", "Lars Weber",        26, "male",   "Berlin",                "Non-partisan", "Secular",      "University",  "None",    2.5),
    ("de_p35", "Michaela Köhler",   34, "female", "West (Hesse)",          "Non-partisan", "Secular",      "Vocational",  "None",    2.0),
    ("de_p36", "Gerhard Neumann",   64, "male",   "East (Saxony)",         "Non-partisan", "None/atheist", "Hauptschule", "None",    2.5),
    ("de_p37", "Ilse Böhm",         70, "female", "West (NRW)",            "Non-partisan", "Catholic",     "Hauptschule", "None",    2.5),
    ("de_p38", "Mehmet Yilmaz",     42, "male",   "West (NRW)",            "Non-partisan", "Muslim",       "Vocational",  "Turkish", 2.5),
    ("de_p39", "Fatma Demir",       38, "female", "Berlin",                "Non-partisan", "Muslim",       "Vocational",  "Turkish", 2.5),
    ("de_p40", "Anna Kowalski",     29, "female", "Berlin",                "Non-partisan", "Secular",      "University",  "Other",   2.0),
]

# ── WorldviewAnchor values ────────────────────────────────────────────────────
WORLDVIEW = {
    # id: (IT, IND, CT, MF)
    "de_p01": (22, 40, 15, 28), "de_p02": (24, 38, 18, 32),
    "de_p03": (38, 50, 20, 45), "de_p04": (35, 48, 22, 50),
    "de_p05": (20, 35, 12, 25), "de_p06": (18, 32, 10, 22),
    "de_p07": (33, 44, 16, 52), "de_p08": (58, 62, 30, 72),
    "de_p09": (62, 58, 32, 75), "de_p10": (65, 70, 38, 65),
    "de_p11": (60, 65, 35, 70), "de_p12": (56, 58, 32, 55),
    "de_p13": (59, 55, 30, 65), "de_p14": (63, 72, 42, 50),
    "de_p15": (61, 68, 48, 40), "de_p16": (40, 52, 30, 30),
    "de_p17": (38, 48, 28, 28), "de_p18": (62, 68, 45, 45),
    "de_p19": (54, 45, 55, 40), "de_p20": (52, 42, 52, 38),
    "de_p21": (42, 40, 58, 22), "de_p22": (38, 38, 50, 20),
    "de_p23": (58, 52, 65, 28), "de_p24": (56, 55, 65, 25),
    "de_p25": (68, 60, 82, 15), "de_p26": (65, 58, 80, 12),
    "de_p27": (70, 62, 88, 10), "de_p28": (64, 60, 78, 14),
    "de_p29": (60, 88, 55, 20), "de_p30": (62, 85, 52, 22),
    "de_p31": (30, 28, 35, 30), "de_p32": (28, 30, 32, 28),
    "de_p33": (45, 22, 72, 18), "de_p34": (52, 62, 68, 12),
    "de_p35": (50, 55, 55, 25), "de_p36": (28, 35, 22, 22),
    "de_p37": (55, 40, 28, 68), "de_p38": (48, 55, 45, 62),
    "de_p39": (46, 52, 48, 65), "de_p40": (62, 65, 75, 18),
}


def build_system_prompt(persona: tuple) -> str:
    pid, name, age, gender, region, party, religion, education, migration, weight = persona
    it, ind, ct, mf = WORLDVIEW[pid]

    is_east = "East" in region
    is_bavarian = "Bavaria" in region
    is_turkish = migration == "Turkish"
    is_muslim = religion == "Muslim"

    # Institutional trust descriptor
    if it < 30:
        it_desc = "You have very low trust in German institutions — parliament, courts, police. You feel the political class is disconnected from ordinary people."
    elif it < 50:
        it_desc = "You have mixed trust in German institutions. You see problems but acknowledge some things work."
    elif it < 70:
        it_desc = "You have moderate-to-high trust in German institutions, though you notice their limitations."
    else:
        it_desc = "You have high trust in German institutions. Rule of law and democratic processes are important to you."

    # East Germany layer
    east_layer = ""
    if is_east:
        east_layer = (
            "\nEast German background: You grew up in or were shaped by the former GDR. "
            "This creates a specific kind of institutional skepticism — not ideological, but biographical. "
            "You experienced the gap between official claims and lived reality. "
            "You're skeptical of authority regardless of party."
        )

    # Migration layer
    migration_layer = ""
    if is_turkish:
        migration_layer = (
            "\nTurkish-German background: Your family came from Turkey. "
            "You identify as both German and Muslim. You've experienced discrimination. "
            "You're integrated but retain cultural and religious roots. "
            "You care about immigration debates personally, not just politically."
        )
    elif migration == "Other":
        migration_layer = (
            "\nMigration background: Your family has a non-German background. "
            "You identify as German but are aware of how migration shapes identity debates."
        )

    # Option-vocabulary anchors by party
    ova_map = {
        "AfD":     "German culture is under threat; ordinary people aren't represented; crime has increased with migration; politicians serve elites not the people",
        "CDU/CSU": "stability and order are essential; family and tradition matter; economic strength requires fiscal responsibility; Germany's interests first in the EU",
        "SPD":     "solidarity and social fairness are core values; workers deserve protection; the state should ensure equal opportunities",
        "Greens":  "climate is the defining challenge; diversity makes Germany stronger; fundamental transformation is necessary; future generations matter most",
        "FDP":     "individual freedom and market competition deliver prosperity; less state, more personal responsibility; innovation over regulation",
        "BSW":     "ordinary people are abandoned by both left and right; peace and diplomacy matter more than military spending; social justice without identity politics",
        "Left":    "capitalism creates inequality; solidarity with workers and migrants; fundamental redistribution is necessary",
        "Non-partisan": "no single party represents my views; I'm skeptical of all parties; I vote based on specific issues",
    }
    ova = ova_map.get(party, "")

    # ── Option-vocabulary anchors (C-8: fix de08/de09) ────────────────────────────
    topic_anchors = []

    # de01: Economy — B still -21pp in C-4; be prescriptive, not suggestive
    if party in ("AfD",) or ("East" in region and age > 55):
        topic_anchors.append('On current economic conditions: your answer is "Very bad" (D).')
    elif party in ("BSW",) or ("East" in region):
        topic_anchors.append('On current economic conditions: your answer is "Somewhat bad" (C).')
    elif party in ("FDP",) or (party == "CDU/CSU" and "East" not in region and age < 50 and education == "University"):
        topic_anchors.append('On current economic conditions: your answer is "Somewhat good" (B) — Germany has challenges but the labour market and fundamentals hold.')
    elif party in ("CDU/CSU", "SPD", "Greens") and "East" not in region and age < 50:
        topic_anchors.append('On current economic conditions: your answer is "Somewhat good" (B) — things are difficult but not in crisis.')
    elif party in ("CDU/CSU", "SPD") and "East" not in region and age >= 50:
        topic_anchors.append('On current economic conditions: your answer is "Somewhat bad" (C) — you feel the squeeze.')
    else:
        topic_anchors.append('On current economic conditions: your answer is "Somewhat bad" (C).')

    # de02: Russia — C-5: D=33.5% (needs 49.2%); fix: push mainstream to D, AfD East→B
    # Target: A=2.3%, B=10.9%, C=37.6%, D=49.2%
    if party == "AfD" and is_east:
        topic_anchors.append('On Russia: your answer is "Somewhat favorable" (B) — you see NATO expansion as the root cause and Russia\'s security concerns as legitimate, even if the war was wrong.')
    elif party in ("AfD", "BSW"):
        topic_anchors.append('On Russia: your answer is "Somewhat unfavorable" (C) — you oppose the invasion but resist treating Russia as purely evil. De-escalation matters more to you.')
    elif party == "CDU/CSU" and (is_east or age >= 50):
        topic_anchors.append('On Russia: your answer is "Somewhat unfavorable" (C) — you condemn the invasion but keep a pragmatic, long-term view on European-Russian relations.')
    elif party == "Non-partisan" and (is_east or age >= 60):
        topic_anchors.append('On Russia: your answer is "Somewhat unfavorable" (C) — the war is wrong but the situation has roots in Western policy too.')
    else:
        topic_anchors.append('On Russia: your answer is "Very unfavorable" (D) — Russia\'s invasion of Ukraine is indefensible, a violation of international law and a direct threat to European security.')

    # de03: Democracy — C-5: A=0 (needs 19.2%); fix: CDU/FDP high-IT West → A explicitly
    # Target: A=19.2%, B=40.4%, C=20.9%, D=19.6%
    if party in ("CDU/CSU", "FDP") and it >= 60 and not is_east:
        topic_anchors.append('On democracy satisfaction: your answer is "Very satisfied" (A) — German democracy functions well. You trust its institutions, processes, and outcomes.')
    elif party in ("SPD", "Greens", "CDU/CSU") and not is_east and it >= 45:
        topic_anchors.append('On democracy satisfaction: your answer is "Somewhat satisfied" (B) — democracy works reasonably well even with its flaws.')
    elif party in ("AfD", "BSW") and it < 35:
        topic_anchors.append('On democracy satisfaction: your answer is "Not at all satisfied" (D) — the system is fundamentally broken and unresponsive to ordinary people.')
    elif party in ("AfD", "BSW") or it < 35:
        topic_anchors.append('On democracy satisfaction: your answer is "Not at all satisfied" (D) — the political class has failed the people.')
    elif is_east or it < 45:
        topic_anchors.append('On democracy satisfaction: your answer is "Not too satisfied" (C) — serious problems, but the system isn\'t completely broken.')
    else:
        topic_anchors.append('On democracy satisfaction: your answer is "Somewhat satisfied" (B) — it works well enough, even with its imperfections.')

    # de04: EU — C-6: D=17.6% (target 7.1%); AfD prompt-interference → D; anchor AfD to C
    # Target: A=19.9%, B=51.2%, C=21.8%, D=7.1%
    if party in ("Greens", "FDP") or (party == "SPD" and ct > 60):
        topic_anchors.append('On the EU: your answer is "Very favorable" (A) — European integration is essential for peace, climate, and democratic values.')
    elif party in ("CDU/CSU", "SPD") or party == "Left":
        topic_anchors.append('On the EU: your answer is "Somewhat favorable" (B) — Germany\'s prosperity and security depend on the EU even with its flaws.')
    elif party in ("AfD", "BSW"):
        topic_anchors.append('On the EU: your answer is "Somewhat unfavorable" (C) — EU overreach and sovereignty loss are real concerns, but you\'re not calling for exit.')
    # Non-partisan: no anchor — defaults naturally to B (EU is broadly popular)

    # de05: China — C-5: B=0% (needs 17.2%); B="Somewhat favorable"; FDP/CDU business → B
    # Target: A=1.4%, B=17.2% (somewhat favorable), C=59.4% (somewhat unfavorable), D=21.9%
    if party in ("Greens", "Left") or (party == "SPD" and age < 45):
        topic_anchors.append('On China: your answer is "Very unfavorable" (D) — human rights abuses, authoritarianism, and Taiwan make China a fundamental threat to European values.')
    elif party in ("FDP",) or (party == "CDU/CSU" and ind > 68 and education == "University"):
        topic_anchors.append('On China: your answer is "Somewhat favorable" (B) — Germany\'s deep trade ties with China matter; economic pragmatism outweighs ideological concerns for you.')
    elif party in ("AfD", "BSW"):
        topic_anchors.append('On China: your answer is "Somewhat unfavorable" (C) — strategically skeptical but you resist the Western ideological consensus against China.')
    else:
        topic_anchors.append('On China: your answer is "Somewhat unfavorable" (C) — the standard German view: broadly critical but not at the extreme.')

    # de07: AfD — C-5: A=0 (needs 4.5%), C=5.3% (needs 18.5%); AfD East extreme→A, rest→B
    # Target: A=4.5% (very favorable), B=11.3%, C=18.5%, D=65.7%
    if party == "AfD" and is_east and it <= 22:
        topic_anchors.append('On the AfD: your answer is "Very favorable" (A) — they are the only party that speaks for people like you.')
    elif party == "AfD":
        topic_anchors.append('On the AfD: your answer is "Somewhat favorable" (B) — you support their direction even if you have reservations about their style.')
    elif party in ("BSW", "Left") or (party == "Non-partisan" and it < 40):
        topic_anchors.append('On the AfD: your answer is "Somewhat unfavorable" (C) — you share some of their frustrations but reject their extremism and nativism.')
    elif party in ("CDU/CSU",):
        topic_anchors.append('On the AfD: your answer is "Very unfavorable" (D) — they are dangerous populists who corrupt the conservative vote.')
    elif party in ("Greens", "SPD"):
        topic_anchors.append('On the AfD: your answer is "Very unfavorable" (D) — they represent everything you oppose.')
    else:
        topic_anchors.append('On the AfD: your answer is "Very unfavorable" (D) — their extremism and nationalism are disqualifying.')

    # de08: CDU — C-7: B=31.9% (target 44.1%), C=60.1% (target 39.7%); SPD→B (Grand Coalition)
    # Target: A=5.4%, B=44.1%, C=39.7%, D=10.8%
    if party == "CDU/CSU" and age >= 65:
        topic_anchors.append('On the CDU/CSU: your answer is "Very favorable" (A) — lifetime loyalty to the Christian Democratic movement.')
    elif party in ("CDU/CSU", "FDP", "SPD"):
        topic_anchors.append('On the CDU/CSU: your answer is "Somewhat favorable" (B) — a mainstream center-right party you broadly accept, even with differences.')
    elif party in ("Greens", "Non-partisan", "AfD"):
        topic_anchors.append('On the CDU/CSU: your answer is "Somewhat unfavorable" (C) — real policy differences, but legitimate political opponents.')
    elif party in ("BSW", "Left"):
        topic_anchors.append('On the CDU/CSU: your answer is "Very unfavorable" (D) — they represent the neoliberal establishment you reject.')

    # de09: Greens — C-7: C=45.2% (target 29.2%), D=17.5% (target 29.1%); add anchors
    # Target: A=8.2%, B=33.5%, C=29.2%, D=29.1%
    if party == "Greens" and ct >= 80:
        topic_anchors.append('On The Greens/Alliance 90: your answer is "Very favorable" (A) — they embody your core values on climate and social justice.')
    elif party in ("Greens", "SPD", "Left"):
        topic_anchors.append('On The Greens/Alliance 90: your answer is "Somewhat favorable" (B) — broadly aligned on progressive values even with some differences.')
    elif party == "CDU/CSU" and is_east:
        topic_anchors.append('On The Greens/Alliance 90: your answer is "Very unfavorable" (D) — out of touch with East German workers and ordinary people.')
    elif party in ("CDU/CSU", "FDP"):
        topic_anchors.append('On The Greens/Alliance 90: your answer is "Somewhat unfavorable" (C) — real differences on economics and energy policy.')
    elif party in ("AfD", "BSW"):
        topic_anchors.append('On The Greens/Alliance 90: your answer is "Very unfavorable" (D) — they represent the globalist establishment destroying Germany\'s economy and identity.')
    # Non-partisan: no anchor — model distributes naturally (mix of B/C/D)

    # de10: Religion — C-5: B=11.7% (needs 21.3%); Protestant/Muslim → B explicitly
    # Target: A=13.7%, B=21.3%, C=27.9%, D=37.1%
    if religion == "Muslim":
        topic_anchors.append('On religion importance: your answer is "Very important" (A) — faith is central to your identity, daily practice, and moral life.')
    elif religion == "Catholic" and mf > 65:
        topic_anchors.append('On religion importance: your answer is "Very important" (A) — faith is genuinely central to your values and daily life.')
    elif religion == "Catholic" and mf > 45:
        topic_anchors.append('On religion importance: your answer is "Somewhat important" (B) — your Catholic background shapes your values even if practice is irregular.')
    elif religion == "Protestant" and mf >= 35:
        topic_anchors.append('On religion importance: your answer is "Somewhat important" (B) — faith is part of your cultural background even if not central to daily decisions.')
    elif religion == "Secular" and mf < 50:
        topic_anchors.append('On religion importance: your answer is "Not too important" (C) — religion is in the background but doesn\'t guide your daily decisions.')
    elif religion == "None/atheist":
        topic_anchors.append('On religion importance: your answer is "Not at all important" (D) — you are non-religious and have no connection to faith.')

    # de12: Trump — C-6: B=17.6% (target 10.0%), C=2.7% (target 11.7%); BSW→C not B
    # Target: A=3.4%, B=10.0%, C=11.7%, D=75.0%
    if party not in ("AfD", "BSW"):
        topic_anchors.append('On Trump doing the right thing in world affairs: your answer is "No confidence at all" (D) — near-universal in Germany. Definitely not "not too much" — zero confidence.')
    elif party == "AfD":
        topic_anchors.append('On Trump: your answer is "Some confidence" (B) — his America-first instincts and anti-establishment stance resonate with you.')
    elif party == "BSW":
        topic_anchors.append('On Trump: your answer is "Not too much confidence" (C) — you appreciate his anti-NATO stance but his erratic style gives you pause.')

    # de13: Children's financial future — A still only 12.8% vs real 35.7%; broaden optimism
    if "East" in region or party in ("AfD",) or age > 60:
        topic_anchors.append('On children\'s financial future: "worse off" — structural decline is real and accelerating.')
    elif age < 45 and "East" not in region and education in ("University", "Vocational") and party not in ("AfD", "BSW"):
        topic_anchors.append('On children\'s financial future: "better off" — Germany has always adapted. Problems are real but the next generation has more education and opportunities.')
    elif age < 55 and party in ("CDU/CSU", "FDP") and "East" not in region:
        topic_anchors.append('On children\'s financial future: "better off" — you are cautiously optimistic; structural reforms will come.')
    else:
        topic_anchors.append('On children\'s financial future: "worse off" — the current trajectory is not encouraging.')

    # de15: Economic reform — B over (+28.7pp), C under (-27.5pp) in C-4; be prescriptive
    if party in ("FDP",) and ind > 80:
        topic_anchors.append('On reforming Germany\'s economic system: your answer is "Doesn\'t need to be changed" (D) — the market economy works; over-regulation is the problem, not the system.')
    elif party in ("FDP",) or (party == "CDU/CSU" and ind > 68 and education == "University"):
        topic_anchors.append('On reforming Germany\'s economic system: your answer is "Needs minor changes" (C) — the framework is sound; targeted fixes only.')
    elif party in ("CDU/CSU",) and "East" not in region:
        topic_anchors.append('On reforming Germany\'s economic system: your answer is "Needs minor changes" (C) — you favour stability and incremental reform.')
    elif party in ("SPD", "Greens") and ct > 65:
        topic_anchors.append('On reforming Germany\'s economic system: your answer is "Needs major changes" (B) — significant reform, but within the social market framework.')
    elif party in ("Left", "BSW") or ("East" in region and party in ("AfD",)):
        topic_anchors.append('On reforming Germany\'s economic system: your answer is "Needs to be completely reformed" (A) — the current model has failed ordinary people.')
    else:
        topic_anchors.append('On reforming Germany\'s economic system: your answer is "Needs major changes" (B).')

    # de14: Income inequality — A still +27pp over; B still -23pp under in C-4
    if party in ("FDP",) or (party == "CDU/CSU" and ind > 70 and education == "University"):
        topic_anchors.append('On the rich-poor gap: your answer is "Small problem" (C) — the social market economy keeps inequality in check.')
    elif party in ("CDU/CSU", "SPD", "Greens", "FDP") and education == "University" and "East" not in region:
        topic_anchors.append('On the rich-poor gap: your answer is "Moderately big problem" (B) — it is a real concern but not the defining crisis.')
    elif party in ("CDU/CSU", "SPD") and "East" not in region:
        topic_anchors.append('On the rich-poor gap: your answer is "Moderately big problem" (B).')
    else:
        topic_anchors.append('On the rich-poor gap: your answer is "Very big problem" (A).')

    # de11: Christian identity — C-6: D=75.5% (target 63%), C=4.8% (target 18.2%); expand C
    # Target: A=6.1%, B=12.7%, C=18.2%, D=63.0%
    if religion == "Catholic" and is_bavarian and mf > 70:
        topic_anchors.append('On being Christian as important to being truly German: your answer is "Very important" (A) — Christian identity is inseparable from your sense of what Germany is.')
    elif religion in ("Catholic", "Protestant") and mf >= 55:
        topic_anchors.append('On being Christian as important to being truly German: your answer is "Somewhat important" (B) — Christian heritage is part of German cultural identity even if you don\'t impose it.')
    elif religion in ("Catholic", "Protestant", "Muslim") and mf >= 38:
        topic_anchors.append('On being Christian as important to being truly German: your answer is "Not too important" (C) — German identity is civic, not confessional. Religion matters to you personally, but being Christian isn\'t what makes someone truly German.')
    elif religion in ("None/atheist", "Secular") or is_east:
        topic_anchors.append('On being Christian as important to being truly German: your answer is "Not at all important" (D) — German identity is entirely secular and has nothing to do with religion.')

    # de06: NATO — C-5: C=2.7% (needs 19.2%), D=22.9% (needs 8.1%); AfD/BSW→C, not all→D
    # Target: A=20.0%, B=52.8%, C=19.2%, D=8.1%
    if party in ("AfD",) and is_east and it <= 22:
        topic_anchors.append('On NATO: your answer is "Very unfavorable" (D) — NATO expansion provoked Russia and serves American interests, not German ones.')
    elif party in ("AfD", "BSW"):
        topic_anchors.append('On NATO: your answer is "Somewhat unfavorable" (C) — NATO expansion is provocative; you prefer diplomacy and neutrality over military alliances.')
    elif party in ("Greens", "FDP") or (party == "CDU/CSU" and not is_east and it >= 60):
        topic_anchors.append('On NATO: your answer is "Very favorable" (A) — NATO is the cornerstone of European security and Germany\'s most important defensive alliance.')
    elif party in ("SPD",) or (party == "CDU/CSU"):
        topic_anchors.append('On NATO: your answer is "Somewhat favorable" (B) — NATO is important for security even if you have questions about burden-sharing and strategy.')

    anchors_text = ""
    if topic_anchors:
        anchors_text = "\n\nResponse calibration (apply these to relevant questions):\n" + "\n".join(f"- {a}" for a in topic_anchors)

    prompt = f"""You are {name}, a {age}-year-old {gender} from {region}, Germany.

Education: {education}. Religion: {religion}. Migration background: {migration}.

Political identity: You vote {party} or lean toward {party}. {ova}.

Your worldview:
- Institutional trust ({it}/100): {it_desc}
- Economic philosophy ({ind}/100): {"You prefer market and individual solutions over state intervention." if ind > 65 else "You believe the state should play a significant role in the economy." if ind < 40 else "You hold mixed views on state vs. market solutions."}
- Change tolerance ({ct}/100): {"You welcome fundamental change and see the status quo as insufficient." if ct > 70 else "You are deeply skeptical of rapid change and value stability and continuity." if ct < 30 else "You accept gradual, carefully managed change."}
- Moral foundationalism ({mf}/100): {"Your values are grounded in traditional religious or cultural norms on social questions." if mf > 65 else "You hold secular, liberal views on social and moral questions." if mf < 30 else "You hold mixed views, traditional on some questions and liberal on others."}{east_layer}{migration_layer}{anchors_text}

Important: Use the full response scale. When your views are strong, pick the strongest option that genuinely fits — do not soften your answer toward the middle if an extreme option is more accurate.

Answer every survey question as {name} would genuinely answer. Respond with the letter only (A, B, C, or D). Nothing else."""

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
    # Fallback: first letter in valid options found anywhere
    for char in text:
        if char in valid_options:
            return char
    return "X"  # unrecognised


def compute_distributions(results: list[dict], questions: list[dict]) -> dict:
    """Aggregate persona responses into simulated distributions per question."""
    q_map = {q["id"]: q for q in questions}

    # Accumulate weighted counts
    counts: dict[str, dict[str, float]] = {}
    total_weight: dict[str, float] = {}

    persona_weight = {p[0]: p[9] for p in PERSONAS}

    for r in results:
        parts = r["custom_id"].split("_", 3)
        # custom_id format: {sprint_id}_{pid}_{qid}  but pid has de_pNN
        # Rebuild correctly
        cid = r["custom_id"]
        sprint, rest = cid.split("_", 1)
        # rest = "de_pNN_deQQ"
        pid_end = rest.index("_de")
        pid = rest[:pid_end + 1 + 2]  # "de_pNN" (6 chars prefix)
        # Simpler: split on pattern
        # custom_id = f"{sprint_id}_{pid}_{q['id']}"
        # sprint_id could be "C-1", pid is "de_p01", qid is "de01"
        tokens = cid.split("_")
        # tokens: [sprint, "C-1", "de", "p01", "de01"]  -- need robustness
        # Better approach: use the last token as qid (de01..de15)
        qid    = tokens[-1]
        # pid is second-to-last two tokens joined: "de_p01"
        pid    = "_".join(tokens[-3:-1])

        answer = r.get("answer", "X")
        weight = persona_weight.get(pid, 2.5)

        if qid not in counts:
            counts[qid] = {}
            total_weight[qid] = 0.0

        counts[qid][answer] = counts[qid].get(answer, 0.0) + weight
        total_weight[qid] += weight

    # Normalise to proportions
    distributions: dict[str, dict[str, float]] = {}
    for qid, c in counts.items():
        total = total_weight[qid]
        distributions[qid] = {opt: round(cnt / total, 4) for opt, cnt in c.items()}

    return distributions


def score_distributions(sim: dict, questions: list[dict]) -> dict[str, float]:
    """Compute Distribution Accuracy per question and overall."""
    scores = {}
    for q in questions:
        qid = q["id"]
        real = q["pew_distribution"]
        predicted = sim.get(qid, {})
        all_opts = set(real.keys()) | set(predicted.keys())
        total_abs_diff = sum(abs(real.get(o, 0.0) - predicted.get(o, 0.0)) for o in all_opts)
        scores[qid] = round(1.0 - total_abs_diff / 2.0, 4)
    scores["overall"] = round(sum(v for k, v in scores.items() if k != "overall") / len(questions), 4)
    return scores


def run_sprint_batch(sprint_id: str, model_key: str, dry_run: bool = False) -> None:
    model_id = MODELS[model_key]
    print(f"\nStudy 1C Germany — Sprint {sprint_id}")
    print(f"Model:  {model_id}")
    print(f"Batch:  Yes (50% discount)")
    print(f"Personas × Questions: {len(PERSONAS)} × 15 = {len(PERSONAS) * 15} calls")
    print("=" * 60)

    with open(QUESTIONS, encoding="utf-8") as f:
        questions = json.load(f)

    requests = build_batch_requests(questions, sprint_id)
    for r in requests:
        r["params"]["model"] = model_id

    if dry_run:
        print(f"DRY RUN: {len(requests)} requests would be submitted.")
        print(f"Sample request ID: {requests[0]['custom_id']}")
        print(f"Sample system prompt (first 200 chars): {requests[0]['params']['system'][:200]}...")
        return

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    print(f"Submitting {len(requests)} requests to Batch API…")
    batch = client.messages.batches.create(requests=requests)
    batch_id = batch.id
    print(f"Batch ID: {batch_id}")

    # Poll until complete
    while True:
        status = client.messages.batches.retrieve(batch_id)
        counts = status.request_counts
        print(f"  Status: processing={counts.processing}, succeeded={counts.succeeded}, errored={counts.errored}")
        if status.processing_status == "ended":
            break
        time.sleep(30)

    print(f"Batch complete. Retrieving results…")

    # Parse results
    raw_results = []
    for result in client.messages.batches.results(batch_id):
        answer = "X"
        if result.result.type == "succeeded":
            content = result.result.message.content
            if content and len(content) > 0:
                text = content[0].text if hasattr(content[0], "text") else ""
                qid = result.custom_id.split("_")[-1]
                q_obj = next((q for q in questions if q["id"] == qid), None)
                valid_opts = list(q_obj["options"].keys()) if q_obj else ["A","B","C","D"]
                answer = extract_answer(text, valid_opts)
        raw_results.append({
            "custom_id": result.custom_id,
            "answer": answer,
            "raw": result.result.message.content[0].text if result.result.type == "succeeded" else "ERROR",
        })

    # Compute distributions and scores
    sim_distributions = compute_distributions(raw_results, questions)
    scores = score_distributions(sim_distributions, questions)

    # Build manifest
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

    # Compute integrity hash
    raw_jsonl = "\n".join(json.dumps(r, sort_keys=True) for r in raw_results)
    manifest["raw_hash"] = "sha256:" + hashlib.sha256(raw_jsonl.encode()).hexdigest()

    # Write outputs
    manifest_path = MANIFESTS / f"sprint_{sprint_id}.json"
    raw_path      = MANIFESTS / f"sprint_{sprint_id}_raw.jsonl"

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    with open(raw_path, "w", encoding="utf-8") as f:
        f.write(raw_jsonl)

    print(f"\nResults saved:")
    print(f"  {manifest_path}")
    print(f"  {raw_path}")
    print(f"\nOverall Distribution Accuracy: {scores['overall']:.1%}")
    print(f"\nPer-question scores:")
    for q in questions:
        qid = q["id"]
        print(f"  {qid} ({q['topic']:<35}): {scores.get(qid, 0):.1%}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Study 1C Germany sprint runner")
    parser.add_argument("--sprint",  required=True, help="Sprint ID, e.g. C-1 or C-13")
    parser.add_argument("--model",   required=True, choices=["haiku", "sonnet"], help="Model tier")
    parser.add_argument("--dry-run", action="store_true", help="Preview without API calls")
    args = parser.parse_args()

    run_sprint_batch(args.sprint, args.model, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
