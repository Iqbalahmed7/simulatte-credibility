#!/usr/bin/env python3
"""
holdout_runner.py — Europe Benchmark · Italy holdout validation runner.

Runs only the 5 holdout questions (hd01–hd05) with ZERO topic-specific anchors.
Pure WorldviewAnchor architecture — tests generalisation outside calibration set.

Usage:
    python3 holdout_runner.py --run HD-1
    python3 holdout_runner.py --run HD-1 --dry-run

Protocol: minimum 3 independent runs. Results stable within ±2pp SD = reliable.

Holdout questions (Italy):
    hd01  us_view              — US favorability
    hd02  un_view              — UN favorability
    hd03  zelenskyy_confidence — Confidence in Zelenskyy
    hd04  macron_confidence    — Confidence in Macron
    hd05  children_future      — Financial future of children vs. parents

Ground truth: Pew Research Center Global Attitudes, Spring 2024 (Italy N=1,120).
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
RESULTS    = HERE / "results"
RESULTS.mkdir(parents=True, exist_ok=True)

MODEL_ID = "claude-haiku-4-5-20251001"

# ── Persona pool (identical to sprint_runner.py) ───────────────────────────────
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

WORLDVIEW = {
    "it_p01": (52,  60,  22,  68),
    "it_p02": (50,  62,  28,  62),
    "it_p03": (47,  58,  20,  72),
    "it_p04": (55,  64,  32,  55),
    "it_p05": (48,  60,  25,  58),
    "it_p06": (58,  65,  30,  50),
    "it_p07": (48,  68,  22,  52),
    "it_p08": (45,  65,  20,  55),
    "it_p09": (40,  70,  18,  32),
    "it_p10": (52,  64,  28,  48),
    "it_p11": (62,  72,  30,  42),
    "it_p12": (60,  68,  28,  55),
    "it_p13": (65,  70,  32,  40),
    "it_p14": (58,  65,  25,  58),
    "it_p15": (65,  42,  68,  14),
    "it_p16": (62,  40,  65,  12),
    "it_p17": (68,  45,  62,  15),
    "it_p18": (60,  38,  70,  12),
    "it_p19": (66,  40,  72,  10),
    "it_p20": (55,  48,  58,  28),
    "it_p21": (63,  42,  65,  14),
    "it_p22": (28,  38,  60,  35),
    "it_p23": (32,  42,  58,  38),
    "it_p24": (25,  35,  55,  42),
    "it_p25": (38,  45,  65,  18),
    "it_p26": (35,  40,  62,  22),
    "it_p27": (30,  38,  22,  68),
    "it_p28": (28,  48,  18,  48),
    "it_p29": (60,  55,  65,  12),
    "it_p30": (25,  40,  20,  65),
    "it_p31": (32,  42,  25,  62),
    "it_p32": (55,  50,  38,  28),
    "it_p33": (22,  38,  15,  72),
    "it_p34": (62,  58,  70,  10),
    "it_p35": (42,  55,  25,  48),
    "it_p36": (35,  52,  22,  30),
    "it_p37": (58,  52,  60,  15),
    "it_p38": (20,  40,  14,  70),
    "it_p39": (56,  50,  62,  16),
    "it_p40": (30,  48,  22,  52),
}


def build_system_prompt(persona: tuple) -> str:
    """Pure WorldviewAnchor prompt — zero topic-specific anchors."""
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

    prompt = f"""You are {name}, a {age}-year-old {gender} from {region}, Italy.

Education: {education}. Religion: {religion}.

Political identity: {party}. {ova}

Your worldview:
- Institutional trust ({it}/100): {it_desc}
- Economic philosophy ({ind}/100): {"You prefer market and individual solutions over state intervention — lower taxes, less regulation, personal responsibility." if ind > 65 else "You believe the state should play a significant role in the economy — public investment, redistribution, strong social services." if ind < 42 else "You hold mixed views on state vs. market solutions."}
- Change tolerance ({ct}/100): {"You welcome fundamental change and see the status quo as deeply inadequate." if ct > 70 else "You are deeply skeptical of rapid change and value stability, tradition, and continuity." if ct < 28 else "You accept gradual, carefully managed change."}
- Moral foundationalism ({mf}/100): {"Your values are grounded in traditional religious or cultural norms on social questions." if mf > 58 else "You hold secular, liberal views on social and moral questions." if mf < 25 else "You hold mixed views — traditional on some questions, liberal on others."}{eu_layer}{religion_layer}{region_layer}{northern_autonomy_layer}

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


def extract_answer(text: str, valid_options: list[str]) -> str:
    text = text.strip().upper()
    for opt in valid_options:
        if text.startswith(opt):
            return opt
    for char in text:
        if char in valid_options:
            return char
    return "X"


def compute_distributions(results: list[dict]) -> dict:
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


def run_holdout(run_id: str, dry_run: bool = False) -> None:
    with open(QUESTIONS, encoding="utf-8") as f:
        all_questions = json.load(f)
    holdout_questions = [q for q in all_questions if q.get("holdout")]

    print(f"\nEurope Benchmark — Italy — Holdout {run_id}")
    print(f"Model:  {MODEL_ID}")
    print(f"Batch:  Yes (50% discount)")
    print(f"Personas × Questions: {len(PERSONAS)} × {len(holdout_questions)} = {len(PERSONAS) * len(holdout_questions)} calls")
    print(f"Mode:   ZERO topic anchors — pure WorldviewAnchor")
    print("=" * 60)

    requests = []
    for persona in PERSONAS:
        pid = persona[0]
        system_prompt = build_system_prompt(persona)
        for q in holdout_questions:
            custom_id = f"{run_id}_{pid}_{q['id']}"
            requests.append({
                "custom_id": custom_id,
                "params": {
                    "model": MODEL_ID,
                    "max_tokens": 5,
                    "system": system_prompt,
                    "messages": build_question_messages(q),
                }
            })

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
                q_obj = next((q for q in holdout_questions if q["id"] == qid), None)
                valid_opts = list(q_obj["options"].keys()) if q_obj else ["A", "B", "C", "D"]
                answer = extract_answer(text, valid_opts)
        raw_results.append({
            "custom_id": result.custom_id,
            "answer": answer,
            "raw": result.result.message.content[0].text if result.result.type == "succeeded" else "ERROR",
        })

    sim_distributions = compute_distributions(raw_results)
    scores = score_distributions(sim_distributions, holdout_questions)

    manifest = {
        "run_id": run_id,
        "model": MODEL_ID,
        "batch_id": batch_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": "holdout — zero topic anchors",
        "n_personas": len(PERSONAS),
        "n_questions": len(holdout_questions),
        "n_calls": len(requests),
        "scores": scores,
        "sim_distributions": sim_distributions,
        "ground_truth": {q["id"]: q["pew_distribution"] for q in holdout_questions},
    }

    raw_jsonl = "\n".join(json.dumps(r, sort_keys=True) for r in raw_results)
    manifest["raw_hash"] = "sha256:" + hashlib.sha256(raw_jsonl.encode()).hexdigest()

    manifest_path = RESULTS / f"holdout_{run_id}.json"
    raw_path      = RESULTS / f"holdout_{run_id}_raw.jsonl"

    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    with open(raw_path, "w") as f:
        f.write(raw_jsonl)

    print(f"\nResults saved:")
    print(f"  {manifest_path}")
    print(f"  {raw_path}")
    print(f"\nHoldout Distribution Accuracy: {scores['overall']*100:.1f}%")
    print("\nPer-question scores:")
    for q in holdout_questions:
        qid = q["id"]
        print(f"  {qid} ({q['topic']:40s}): {scores.get(qid, 0)*100:.1f}%")


def main():
    parser = argparse.ArgumentParser(description="Europe Benchmark Italy holdout runner")
    parser.add_argument("--run", required=True, help="Run ID, e.g. HD-1")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run_holdout(args.run, args.dry_run)


if __name__ == "__main__":
    main()
