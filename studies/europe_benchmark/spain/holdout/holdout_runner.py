#!/usr/bin/env python3
"""
holdout_runner.py — Europe Benchmark · Spain holdout validation runner.

Runs only the 5 holdout questions (hd01–hd05) with ZERO topic-specific anchors.
Pure WorldviewAnchor architecture — tests generalisation outside calibration set.

Usage:
    python3 holdout_runner.py --run HD-1
    python3 holdout_runner.py --run HD-1 --dry-run

Protocol: minimum 3 independent runs. Results stable within ±2pp SD = reliable.

Holdout questions (Spain):
    hd01  us_view              — US favorability
    hd02  un_view              — UN favorability
    hd03  zelenskyy_confidence — Confidence in Zelenskyy
    hd04  macron_confidence    — Confidence in Macron
    hd05  biden_confidence     — Confidence in Biden

Ground truth: Pew Research Center Global Attitudes, Spring 2024 (Spain N=1,013).
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
    ("sp_p01", "Carlos García Herrera",    58, "male",   "Spain (Madrid / Community of Madrid)",       "PP",             "Pro-EU",     "Catholic (non-practicing)", "University",   2.0),
    ("sp_p02", "María Fernández López",    52, "female", "Spain (Castile-La Mancha / Toledo)",         "PP",             "Pro-EU",     "Catholic (practicing)",     "Bachillerato", 2.0),
    ("sp_p03", "Antonio González Blanco",  64, "male",   "Spain (Andalusia / Seville)",                "PP",             "Pro-EU",     "Catholic (practicing)",     "University",   2.0),
    ("sp_p04", "Pilar Rodríguez Navarro",  45, "female", "Spain (Valencia / Community of Valencia)",   "PP",             "Pro-EU",     "Catholic (non-practicing)", "University",   2.0),
    ("sp_p05", "José Luis Martínez Cruz",  61, "male",   "Spain (Aragon / Zaragoza)",                  "PP",             "Pro-EU",     "Catholic (non-practicing)", "Bachillerato", 2.5),
    ("sp_p06", "Concepción Sánchez Mora",  49, "female", "Spain (Castile and León / Valladolid)",      "PP",             "Pro-EU",     "Catholic (practicing)",     "Bachillerato", 2.5),
    ("sp_p07", "Laura Pérez Giménez",      41, "female", "Spain (Andalusia / Málaga)",                 "PSOE",           "Pro-EU",     "None/secular",              "University",   2.0),
    ("sp_p08", "Miguel Ángel Gómez Ruiz",  54, "male",   "Spain (Madrid / Community of Madrid)",       "PSOE",           "Pro-EU",     "None/secular",              "University",   2.0),
    ("sp_p09", "Carmen Díaz Serrano",      48, "female", "Spain (Catalonia / Barcelona)",              "PSOE",           "Pro-EU",     "None/secular",              "University",   2.0),
    ("sp_p10", "Francisco López Ibáñez",   60, "male",   "Spain (Extremadura / Badajoz)",              "PSOE",           "Pro-EU",     "Catholic (non-practicing)", "ESO/primary",  2.5),
    ("sp_p11", "Rosa Martínez Delgado",    36, "female", "Spain (Basque Country / Bilbao)",            "PSOE",           "Pro-EU",     "None/secular",              "University",   2.0),
    ("sp_p12", "Javier Hernández Castro",  55, "male",   "Spain (Andalusia / Almería)",                "PSOE",           "Pro-EU",     "Catholic (non-practicing)", "Bachillerato", 2.5),
    ("sp_p13", "Elena Moreno Vidal",       43, "female", "Spain (Valencia / Alicante)",                "PSOE",           "Pro-EU",     "None/secular",              "University",   2.0),
    ("sp_p14", "Sofía Torres Muñoz",       29, "female", "Spain (Madrid / Community of Madrid)",       "Podemos/Sumar",  "Pro-EU",     "None/secular",              "University",   2.5),
    ("sp_p15", "Adrián Jiménez Peral",     33, "male",   "Spain (Catalonia / Barcelona)",              "Podemos/Sumar",  "Pro-EU",     "None/secular",              "University",   2.5),
    ("sp_p16", "Nuria Álvarez Méndez",     27, "female", "Spain (Basque Country / San Sebastián)",     "Podemos/Sumar",  "Pro-EU",     "None/secular",              "University",   2.5),
    ("sp_p17", "Pablo Ruiz Castillo",      38, "male",   "Spain (Andalusia / Granada)",                "Podemos/Sumar",  "Pro-EU",     "None/secular",              "University",   2.5),
    ("sp_p18", "Alejandro Romero Soria",   50, "male",   "Spain (Madrid / Community of Madrid)",       "Vox",            "EU-skeptic", "Catholic (non-practicing)", "Bachillerato", 2.5),
    ("sp_p19", "Isabel Gutiérrez Pardo",   44, "female", "Spain (Andalusia / Jaén)",                   "Vox",            "EU-skeptic", "Catholic (practicing)",     "ESO/primary",  2.5),
    ("sp_p20", "Ramón Serrano Fuentes",    57, "male",   "Spain (Castile-La Mancha / Albacete)",       "Vox",            "EU-skeptic", "Catholic (practicing)",     "ESO/primary",  2.5),
    ("sp_p21", "Cristina Vargas Molina",   39, "female", "Spain (Community of Madrid / Alcalá)",       "Vox",            "EU-skeptic", "Catholic (non-practicing)", "Bachillerato", 2.5),
    ("sp_p22", "Ernesto Navarro Gil",      46, "male",   "Spain (Catalonia / Tarragona)",              "Cs",             "Pro-EU",     "None/secular",              "University",   2.0),
    ("sp_p23", "Mercedes Ortega Blanco",   63, "female", "Spain (Andalusia / Córdoba)",                "Non-partisan",   "Pro-EU",     "Catholic (non-practicing)", "ESO/primary",  2.5),
    ("sp_p24", "Víctor Castro Llorente",   42, "male",   "Spain (Valencia / Castellón)",               "Non-partisan",   "Pro-EU",     "None/secular",              "Bachillerato", 2.5),
    ("sp_p25", "Amparo Delgado Nieto",     56, "female", "Spain (Castile and León / Salamanca)",       "Non-partisan",   "Pro-EU",     "Catholic (non-practicing)", "Bachillerato", 2.5),
    ("sp_p26", "Manuel Ramos Iglesias",    71, "male",   "Spain (Galicia / A Coruña)",                 "Non-partisan",   "Pro-EU",     "Catholic (practicing)",     "ESO/primary",  2.5),
    ("sp_p27", "Beatriz Santos Morales",   31, "female", "Spain (Madrid / Community of Madrid)",       "Non-partisan",   "Pro-EU",     "None/secular",              "University",   2.0),
    ("sp_p28", "Jorge Medina Cano",        48, "male",   "Spain (Andalusia / Huelva)",                 "Non-partisan",   "EU-skeptic", "Catholic (non-practicing)", "ESO/primary",  2.5),
    ("sp_p29", "Dolores Aguilar Torres",   67, "female", "Spain (Murcia / Cartagena)",                 "Non-partisan",   "Pro-EU",     "Catholic (practicing)",     "ESO/primary",  2.5),
    ("sp_p30", "Raúl Herrero Pascual",     35, "male",   "Spain (Aragon / Zaragoza)",                  "Non-partisan",   "Pro-EU",     "None/secular",              "University",   2.0),
    ("sp_p31", "Inés Cabrera Santana",     53, "female", "Spain (Balearic Islands / Palma)",           "Non-partisan",   "Pro-EU",     "None/secular",              "Bachillerato", 2.5),
    ("sp_p32", "Eduardo Vega Prieto",      44, "male",   "Spain (Castile and León / Burgos)",          "Non-partisan",   "EU-skeptic", "Catholic (non-practicing)", "ESO/primary",  2.5),
    ("sp_p33", "Lucía Blanco Salas",       24, "female", "Spain (Catalonia / Barcelona)",              "Non-partisan",   "Pro-EU",     "None/secular",              "University",   2.0),
    ("sp_p34", "Andrés Molina Reyes",      59, "male",   "Spain (Extremadura / Cáceres)",              "Non-partisan",   "EU-skeptic", "Catholic (non-practicing)", "ESO/primary",  2.5),
    ("sp_p35", "Patricia Guerrero Rubio",  37, "female", "Spain (Valencia / Valencia city)",           "Non-partisan",   "Pro-EU",     "None/secular",              "Bachillerato", 2.5),
    ("sp_p36", "Fernando Iglesias Moya",   62, "male",   "Spain (Andalusia / Cádiz)",                  "Non-partisan",   "EU-skeptic", "Catholic (non-practicing)", "ESO/primary",  2.5),
    ("sp_p37", "Montserrat Puig Casals",   47, "female", "Spain (Catalonia / Girona)",                 "Independentista","Pro-EU",     "None/secular",              "University",   2.5),
    ("sp_p38", "Oriol Vila Bosch",         39, "male",   "Spain (Catalonia / Barcelona)",              "Independentista","Pro-EU",     "None/secular",              "University",   2.5),
    ("sp_p39", "Laia Mas Soler",           34, "female", "Spain (Catalonia / Lleida)",                 "Independentista","Pro-EU",     "None/secular",              "Bachillerato", 2.5),
    ("sp_p40", "Marc Ferrer Sala",         52, "male",   "Spain (Catalonia / Sabadell)",               "Independentista","Pro-EU",     "Catholic (non-practicing)", "University",   2.5),
]

WORLDVIEW = {
    "sp_p01": (60,  65,  32,  38),
    "sp_p02": (58,  62,  28,  62),
    "sp_p03": (55,  63,  25,  65),
    "sp_p04": (62,  64,  35,  40),
    "sp_p05": (56,  60,  28,  44),
    "sp_p06": (54,  61,  22,  60),
    "sp_p07": (55,  42,  60,  12),
    "sp_p08": (58,  40,  62,  15),
    "sp_p09": (52,  38,  65,  10),
    "sp_p10": (48,  36,  52,  40),
    "sp_p11": (56,  40,  68,  10),
    "sp_p12": (50,  38,  55,  35),
    "sp_p13": (54,  42,  62,  14),
    "sp_p14": (32,  22,  82,  8),
    "sp_p15": (30,  20,  85,  6),
    "sp_p16": (35,  24,  80,  8),
    "sp_p17": (28,  22,  78,  10),
    "sp_p18": (45,  62,  22,  52),
    "sp_p19": (42,  60,  18,  68),
    "sp_p20": (40,  58,  16,  72),
    "sp_p21": (44,  62,  24,  56),
    "sp_p22": (62,  66,  48,  16),
    "sp_p23": (40,  48,  30,  48),
    "sp_p24": (50,  52,  48,  22),
    "sp_p25": (44,  50,  32,  45),
    "sp_p26": (38,  50,  22,  58),
    "sp_p27": (58,  54,  65,  12),
    "sp_p28": (30,  48,  28,  40),
    "sp_p29": (36,  48,  20,  60),
    "sp_p30": (55,  55,  58,  15),
    "sp_p31": (52,  52,  52,  18),
    "sp_p32": (32,  50,  20,  44),
    "sp_p33": (60,  50,  70,  10),
    "sp_p34": (28,  46,  18,  46),
    "sp_p35": (52,  50,  55,  20),
    "sp_p36": (34,  48,  22,  42),
    "sp_p37": (45,  42,  72,  12),
    "sp_p38": (42,  40,  75,  8),
    "sp_p39": (48,  44,  68,  14),
    "sp_p40": (40,  46,  65,  28),
}


def build_system_prompt(persona: tuple) -> str:
    """Pure WorldviewAnchor prompt — zero topic-specific anchors."""
    pid, name, age, gender, region, party, eu_ref, religion, education, weight = persona
    it, ind, ct, mf = WORLDVIEW[pid]

    is_madrid        = "Madrid" in region
    is_catalonia     = "Catalonia" in region
    is_andalusia     = "Andalusia" in region
    is_basque        = "Basque" in region
    is_castile       = "Castile" in region
    is_eu_skeptic    = eu_ref == "EU-skeptic"
    is_pro_eu        = eu_ref == "Pro-EU"
    is_catholic_practicing = "practicing" in religion and "non" not in religion
    is_secular       = "secular" in religion or "None" in religion

    if it < 35:
        it_desc = (
            "You have very low trust in Spanish institutions — the government, the media, "
            "the political parties. You feel the political class (la casta) governs for "
            "elites, not ordinary Spaniards. Corruption scandals and political gridlock "
            "have destroyed your confidence in the system."
        )
    elif it < 52:
        it_desc = (
            "You have mixed trust in Spanish institutions. You see real dysfunction, "
            "political fragmentation, and entrenched corruption, but you still believe "
            "in democratic values in principle. The system disappoints more often than not."
        )
    elif it < 65:
        it_desc = (
            "You have moderate trust in Spanish institutions. You are realistic about "
            "their imperfections — the Catalonia crisis, the fragmented parliament — "
            "but broadly believe Spanish democracy can work when politicians act responsibly."
        )
    else:
        it_desc = (
            "You have relatively high trust in Spanish institutions. The rule of law, "
            "democratic process, and European cooperation matter deeply to you. "
            "You believe Spain's democratic transition was a success worth defending."
        )

    if is_pro_eu:
        eu_layer = (
            "\nEurope: You are broadly pro-European. Spain has been a major beneficiary "
            "of EU structural funds and the single market. You see the EU as a force for "
            "stability, prosperity, and Spanish influence. European solidarity matters to you, "
            "especially after the COVID recovery fund."
        )
    else:
        eu_layer = (
            "\nEurope: You are skeptical of the EU. You feel that Brussels imposes rules "
            "that serve the Franco-German core at the expense of southern European workers. "
            "Austerity was imposed from outside. You are not opposed to European cooperation "
            "in principle but want a fundamentally more sovereign relationship."
        )

    ova_map = {
        "PP": (
            "Spain needs stable, responsible centre-right government. The Partido Popular "
            "represents order, economic competence, and Spanish national unity against "
            "the separatist threat in Catalonia and the Basque Country. You are deeply "
            "concerned by Sánchez's coalition with Sumar and his negotiations with Junts. "
            "You want lower taxes, pro-business policy, and a firm hand on public order."
        ),
        "PSOE": (
            "Social democracy — equality, public services, women's rights, and European "
            "solidarity — remains Spain's best path. The PSOE under Sánchez has delivered "
            "minimum wage increases, the labour reform, and European recovery funds. "
            "You believe in a plurinational Spain that can accommodate regional diversity "
            "within a democratic framework. The right and far-right are the real threat."
        ),
        "Podemos/Sumar": (
            "The current economic system fails workers, women, and the planet. "
            "Podemos/Sumar represents the only real break from neo-liberal austerity — "
            "stronger labour rights, feminist policies, ecological transition, and a "
            "foreign policy free from NATO militarism and US dominance. You are deeply "
            "anti-establishment and distrust both the traditional left and right. "
            "You see housing and youth unemployment as a generational emergency."
        ),
        "Vox": (
            "Spain is being destroyed from within — by Catalan and Basque separatists "
            "who want to break up the nation, by a government that negotiates with "
            "those who want to destroy Spain, by mass immigration, and by a woke ideology "
            "that attacks traditional Spanish values and the family. Vox defends Spain, "
            "its unity, its history, and its Christian cultural identity. "
            "Sánchez is the greatest threat to Spanish democracy since Franco's death."
        ),
        "Cs": (
            "Spain needs a credible centrist option — pro-European, liberal, reformist, "
            "and firmly constitutionalist. You oppose both the nationalist right (PP/Vox) "
            "and the radical left. Ciudadanos stood for rule of law, free markets, "
            "and a pluralist Spain that rejects both separatism and populism. "
            "You are disappointed by the party's collapse but still hold these values."
        ),
        "Non-partisan": (
            "no single party represents your views. You are deeply disillusioned with "
            "Spanish politics — the polarisation, the corruption scandals, the endless "
            "negotiations over Catalonia. You vote based on immediate concerns or abstain."
        ),
        "Independentista": (
            "Catalonia has the democratic right to self-determination. The Spanish state "
            "has repeatedly failed to recognise Catalan identity, language, and fiscal "
            "grievances. The 2017 referendum, the imprisonment of independence leaders, "
            "and Madrid's intransigence have convinced you that independence is the only "
            "path to genuine self-governance. You support Junts or ERC and see the EU "
            "as a future framework for an independent Catalonia."
        ),
    }
    ova = ova_map.get(party, "")

    religion_layer = ""
    if is_catholic_practicing:
        religion_layer = (
            "\nFaith and identity: You are a practising Catholic. "
            "Your faith informs your social values — family, community, and respect for "
            "life. You are concerned about aggressive secularism in public life and believe "
            "Spain's Catholic heritage deserves respect, not erasure. You support Church "
            "presence in education."
        )
    elif "non-practicing" in religion:
        religion_layer = (
            "\nFaith and identity: You were raised Catholic but are no longer practicing. "
            "Religion is a private cultural background, not a guide for politics. "
            "You support separation of Church and state."
        )

    region_layer = ""
    if is_catalonia:
        region_layer = (
            "\nRegional background: You are from Catalonia. The question of Catalan "
            "identity, language, and self-governance is never far from political "
            "conversation. Whether you support independence or not, you feel that "
            "Madrid often fails to understand Catalonia's distinct culture and interests."
        )
    elif is_basque:
        region_layer = (
            "\nRegional background: You are from the Basque Country. "
            "The Basque Country has its own strong cultural and linguistic identity "
            "and a degree of fiscal autonomy (concierto económico) that sets it apart. "
            "You follow both Spanish and Basque politics closely."
        )
    elif is_andalusia:
        region_layer = (
            "\nRegional background: You are from Andalusia — Spain's most populous "
            "region, historically marked by high unemployment, rural poverty, and "
            "agricultural dependence. Andalusia has been a PSOE stronghold for decades "
            "but shifted right under the PP. Economic anxiety is a daily reality here."
        )
    elif is_madrid:
        region_layer = (
            "\nRegional background: You live in the Madrid metropolitan area — "
            "Spain's political and financial capital. Madrid is wealthier than the "
            "national average, more cosmopolitan, and the centre of both government "
            "and the business elite. The PP has governed the Community of Madrid for "
            "two decades. The city concentrates Spain's cultural and economic power."
        )
    elif is_castile:
        region_layer = (
            "\nRegional background: You are from Castile — the historical heartland "
            "of Spain, a region associated with Spanish national identity, the Catholic "
            "Church, and conservative rural values. Castile has seen significant rural "
            "depopulation and feels left behind by urban Spain."
        )

    prompt = f"""You are {name}, a {age}-year-old {gender} from {region}.

Education: {education}. Religion: {religion}.

Political identity: {party}. {ova}.

Your worldview:
- Institutional trust ({it}/100): {it_desc}
- Economic philosophy ({ind}/100): {"You prefer market and individual solutions over state intervention — lower taxes, less regulation, personal responsibility." if ind > 65 else "You believe the state should play a significant role in the economy — public investment, redistribution, strong social services." if ind < 42 else "You hold mixed views on state vs. market solutions."}
- Change tolerance ({ct}/100): {"You welcome fundamental change and see the status quo as deeply inadequate." if ct > 70 else "You are deeply skeptical of rapid change and value stability, tradition, and continuity." if ct < 28 else "You accept gradual, carefully managed change."}
- Moral foundationalism ({mf}/100): {"Your values are grounded in traditional religious or cultural norms on social questions." if mf > 58 else "You hold secular, liberal views on social and moral questions." if mf < 25 else "You hold mixed views — traditional on some questions, liberal on others."}{eu_layer}{religion_layer}{region_layer}

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

    print(f"\nEurope Benchmark — Spain — Holdout {run_id}")
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
    parser = argparse.ArgumentParser(description="Europe Benchmark Spain holdout runner")
    parser.add_argument("--run", required=True, help="Run ID, e.g. HD-1")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run_holdout(args.run, args.dry_run)


if __name__ == "__main__":
    main()
