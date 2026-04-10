#!/usr/bin/env python3
"""
sprint_runner.py — Europe Benchmark · Spain calibration sprint runner.

Usage:
    python3 sprint_runner.py --sprint SP-1 --model haiku
    python3 sprint_runner.py --sprint SP-1 --model haiku --dry-run

WorldviewAnchor dimensions (0–100 scale):
    IT  — Institutional Trust
    IND — Individualism (market vs. state preference)
    CT  — Change Tolerance
    MF  — Moral Foundationalism

Key Spain calibration axes:
    1. Five-party fragmentation: PP (centre-right) / PSOE (socialist) /
       Podemos/Sumar (radical left) / Vox (nationalist far-right) /
       Junts/ERC (Catalan independence)
    2. Territorial fault line: Catalonia/Basque independence vs. Spanish unity
    3. Memory politics: Franco dictatorship shapes left-right cultural divide
    4. Religion: Catholic majority but highly secularised; South more devout
    5. Economy: Post-COVID recovery; youth unemployment; housing crisis
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
# Demographic targets (CIS barometer / Spanish Electoral Studies):
#   Parties:  PP ~20%, PSOE ~22%, Podemos/Sumar ~13%, Vox ~13%,
#             Cs (declining) ~3%, Non-partisan ~22%, Independentista ~7%
#   Region:   Madrid ~16%, Catalonia ~16%, Andalusia ~18%, Valencia ~11%,
#             Castile/other ~26%, Basque ~5%, rest ~8%
#   Religion: Catholic (inc. non-practicing) ~60%, Secular/non-religious ~34%,
#             other ~6%
#   Education: University/higher ~35%, Bachillerato/FP ~35%, Primary/ESO ~30%
#   Age range: 24–71

PERSONAS = [
    # ── PP (Partido Popular — centre-right, Madrid/Castile, business, traditional) ──
    ("sp_p01", "Carlos García Herrera",    58, "male",   "Spain (Madrid / Community of Madrid)",       "PP",             "Pro-EU",     "Catholic (non-practicing)", "University",   2.0),
    ("sp_p02", "María Fernández López",    52, "female", "Spain (Castile-La Mancha / Toledo)",         "PP",             "Pro-EU",     "Catholic (practicing)",     "Bachillerato", 2.0),
    ("sp_p03", "Antonio González Blanco",  64, "male",   "Spain (Andalusia / Seville)",                "PP",             "Pro-EU",     "Catholic (practicing)",     "University",   2.0),
    ("sp_p04", "Pilar Rodríguez Navarro",  45, "female", "Spain (Valencia / Community of Valencia)",   "PP",             "Pro-EU",     "Catholic (non-practicing)", "University",   2.0),
    ("sp_p05", "José Luis Martínez Cruz",  61, "male",   "Spain (Aragon / Zaragoza)",                  "PP",             "Pro-EU",     "Catholic (non-practicing)", "Bachillerato", 2.5),
    ("sp_p06", "Concepción Sánchez Mora",  49, "female", "Spain (Castile and León / Valladolid)",      "PP",             "Pro-EU",     "Catholic (practicing)",     "Bachillerato", 2.5),

    # ── PSOE (Partido Socialista — socialist, urban, Andalusia/Catalonia) ──────
    ("sp_p07", "Laura Pérez Giménez",      41, "female", "Spain (Andalusia / Málaga)",                 "PSOE",           "Pro-EU",     "None/secular",              "University",   2.0),
    ("sp_p08", "Miguel Ángel Gómez Ruiz",  54, "male",   "Spain (Madrid / Community of Madrid)",       "PSOE",           "Pro-EU",     "None/secular",              "University",   2.0),
    ("sp_p09", "Carmen Díaz Serrano",      48, "female", "Spain (Catalonia / Barcelona)",              "PSOE",           "Pro-EU",     "None/secular",              "University",   2.0),
    ("sp_p10", "Francisco López Ibáñez",   60, "male",   "Spain (Extremadura / Badajoz)",              "PSOE",           "Pro-EU",     "Catholic (non-practicing)", "ESO/primary",  2.5),
    ("sp_p11", "Rosa Martínez Delgado",    36, "female", "Spain (Basque Country / Bilbao)",            "PSOE",           "Pro-EU",     "None/secular",              "University",   2.0),
    ("sp_p12", "Javier Hernández Castro",  55, "male",   "Spain (Andalusia / Almería)",                "PSOE",           "Pro-EU",     "Catholic (non-practicing)", "Bachillerato", 2.5),
    ("sp_p13", "Elena Moreno Vidal",       43, "female", "Spain (Valencia / Alicante)",                "PSOE",           "Pro-EU",     "None/secular",              "University",   2.0),

    # ── Podemos/Sumar (radical left, urban, young, secular, feminist) ─────────
    ("sp_p14", "Sofía Torres Muñoz",       29, "female", "Spain (Madrid / Community of Madrid)",       "Podemos/Sumar",  "Pro-EU",     "None/secular",              "University",   2.5),
    ("sp_p15", "Adrián Jiménez Peral",     33, "male",   "Spain (Catalonia / Barcelona)",              "Podemos/Sumar",  "Pro-EU",     "None/secular",              "University",   2.5),
    ("sp_p16", "Nuria Álvarez Méndez",     27, "female", "Spain (Basque Country / San Sebastián)",     "Podemos/Sumar",  "Pro-EU",     "None/secular",              "University",   2.5),
    ("sp_p17", "Pablo Ruiz Castillo",      38, "male",   "Spain (Andalusia / Granada)",                "Podemos/Sumar",  "Pro-EU",     "None/secular",              "University",   2.5),

    # ── Vox (nationalist far-right, anti-immigration, anti-Catalan independence) ─
    ("sp_p18", "Alejandro Romero Soria",   50, "male",   "Spain (Madrid / Community of Madrid)",       "Vox",            "EU-skeptic", "Catholic (non-practicing)", "Bachillerato", 2.5),
    ("sp_p19", "Isabel Gutiérrez Pardo",   44, "female", "Spain (Andalusia / Jaén)",                   "Vox",            "EU-skeptic", "Catholic (practicing)",     "ESO/primary",  2.5),
    ("sp_p20", "Ramón Serrano Fuentes",    57, "male",   "Spain (Castile-La Mancha / Albacete)",       "Vox",            "EU-skeptic", "Catholic (practicing)",     "ESO/primary",  2.5),
    ("sp_p21", "Cristina Vargas Molina",   39, "female", "Spain (Community of Madrid / Alcalá)",       "Vox",            "EU-skeptic", "Catholic (non-practicing)", "Bachillerato", 2.5),

    # ── Cs (Ciudadanos — centrist liberal, declining; PP-adjacent) ────────────
    ("sp_p22", "Ernesto Navarro Gil",      46, "male",   "Spain (Catalonia / Tarragona)",              "Cs",             "Pro-EU",     "None/secular",              "University",   2.0),

    # ── Non-partisan / disengaged (cross-cutting) ─────────────────────────────
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

    # ── Independentista (Catalan independence — Junts/ERC) ────────────────────
    ("sp_p37", "Montserrat Puig Casals",   47, "female", "Spain (Catalonia / Girona)",                 "Independentista","Pro-EU",     "None/secular",              "University",   2.5),
    ("sp_p38", "Oriol Vila Bosch",         39, "male",   "Spain (Catalonia / Barcelona)",              "Independentista","Pro-EU",     "None/secular",              "University",   2.5),
    ("sp_p39", "Laia Mas Soler",           34, "female", "Spain (Catalonia / Lleida)",                 "Independentista","Pro-EU",     "None/secular",              "Bachillerato", 2.5),
    ("sp_p40", "Marc Ferrer Sala",         52, "male",   "Spain (Catalonia / Sabadell)",               "Independentista","Pro-EU",     "Catholic (non-practicing)", "University",   2.5),
]

# ── WorldviewAnchor values ────────────────────────────────────────────────────
WORLDVIEW = {
    # id:        (IT,  IND, CT,  MF)
    # PP — moderate-high IT, high IND, low-moderate CT, moderate-high MF
    "sp_p01": (60,  65,  32,  38),   # PP, Madrid, Pro-EU, non-practicing Catholic, university
    "sp_p02": (58,  62,  28,  62),   # PP, Castile, Pro-EU, practicing Catholic, bachillerato
    "sp_p03": (55,  63,  25,  65),   # PP, Seville, Pro-EU, practicing Catholic, university (older)
    "sp_p04": (62,  64,  35,  40),   # PP, Valencia, Pro-EU, non-practicing Catholic, university
    "sp_p05": (56,  60,  28,  44),   # PP, Aragon, Pro-EU, non-practicing Catholic, bachillerato
    "sp_p06": (54,  61,  22,  60),   # PP, Castile-León, Pro-EU, practicing Catholic, bachillerato (older)

    # PSOE — moderate IT, low-moderate IND, moderate-high CT, low MF
    "sp_p07": (55,  42,  60,  12),   # PSOE, Málaga, Pro-EU, secular, university
    "sp_p08": (58,  40,  62,  15),   # PSOE, Madrid, Pro-EU, secular, university
    "sp_p09": (52,  38,  65,  10),   # PSOE, Barcelona, Pro-EU, secular, university
    "sp_p10": (48,  36,  52,  40),   # PSOE, Extremadura, Pro-EU, non-practicing Catholic, ESO (older)
    "sp_p11": (56,  40,  68,  10),   # PSOE, Bilbao, Pro-EU, secular, university
    "sp_p12": (50,  38,  55,  35),   # PSOE, Andalusia, Pro-EU, non-practicing Catholic, bachillerato
    "sp_p13": (54,  42,  62,  14),   # PSOE, Alicante, Pro-EU, secular, university

    # Podemos/Sumar — low-moderate IT, very low IND, very high CT, very low MF
    "sp_p14": (32,  22,  82,  8),    # Podemos, Madrid, Pro-EU, secular, university (young)
    "sp_p15": (30,  20,  85,  6),    # Podemos, Barcelona, Pro-EU, secular, university (young)
    "sp_p16": (35,  24,  80,  8),    # Podemos, Basque, Pro-EU, secular, university (young)
    "sp_p17": (28,  22,  78,  10),   # Podemos, Granada, Pro-EU, secular, university

    # Vox — low-moderate IT (distrusts left establishment), moderate-high IND, low CT, high MF
    "sp_p18": (45,  62,  22,  52),   # Vox, Madrid, EU-skeptic, non-practicing Catholic, bachillerato
    "sp_p19": (42,  60,  18,  68),   # Vox, Andalusia, EU-skeptic, practicing Catholic, ESO
    "sp_p20": (40,  58,  16,  72),   # Vox, Castile, EU-skeptic, practicing Catholic, ESO (older)
    "sp_p21": (44,  62,  24,  56),   # Vox, Madrid commuter belt, EU-skeptic, non-practicing Catholic, bachillerato

    # Cs — moderate-high IT, moderate-high IND, moderate CT, low MF (centrist liberal)
    "sp_p22": (62,  66,  48,  16),   # Cs, Catalonia, Pro-EU, secular, university

    # Non-partisan — wide spread
    "sp_p23": (40,  48,  30,  48),   # NP, Córdoba, Pro-EU, non-practicing Catholic, ESO (older)
    "sp_p24": (50,  52,  48,  22),   # NP, Castellón, Pro-EU, secular, bachillerato
    "sp_p25": (44,  50,  32,  45),   # NP, Salamanca, Pro-EU, non-practicing Catholic, bachillerato
    "sp_p26": (38,  50,  22,  58),   # NP, Galicia, Pro-EU, practicing Catholic, ESO (oldest)
    "sp_p27": (58,  54,  65,  12),   # NP, Madrid, Pro-EU, secular, university (younger)
    "sp_p28": (30,  48,  28,  40),   # NP, Huelva, EU-skeptic, non-practicing Catholic, ESO
    "sp_p29": (36,  48,  20,  60),   # NP, Murcia, Pro-EU, practicing Catholic, ESO (older)
    "sp_p30": (55,  55,  58,  15),   # NP, Aragon, Pro-EU, secular, university
    "sp_p31": (52,  52,  52,  18),   # NP, Balearics, Pro-EU, secular, bachillerato
    "sp_p32": (32,  50,  20,  44),   # NP, Burgos, EU-skeptic, non-practicing Catholic, ESO
    "sp_p33": (60,  50,  70,  10),   # NP, Barcelona, Pro-EU, secular, university (youngest)
    "sp_p34": (28,  46,  18,  46),   # NP, Extremadura, EU-skeptic, non-practicing Catholic, ESO (older)
    "sp_p35": (52,  50,  55,  20),   # NP, Valencia city, Pro-EU, secular, bachillerato
    "sp_p36": (34,  48,  22,  42),   # NP, Cádiz, EU-skeptic, non-practicing Catholic, ESO

    # Independentista — IT varies (low toward Madrid, high toward Catalan institutions), high CT
    "sp_p37": (45,  42,  72,  12),   # Indy, Girona, Pro-EU, secular, university (female)
    "sp_p38": (42,  40,  75,  8),    # Indy, Barcelona, Pro-EU, secular, university
    "sp_p39": (48,  44,  68,  14),   # Indy, Lleida, Pro-EU, secular, bachillerato
    "sp_p40": (40,  46,  65,  28),   # Indy, Sabadell, Pro-EU, non-practicing Catholic, university (older)
}


def build_system_prompt(persona: tuple) -> str:
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
    is_working_class = "ESO" in education or "primary" in education

    # ── Institutional trust descriptor ────────────────────────────────────────
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

    # ── EU/Europe layer ────────────────────────────────────────────────────────
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

    # ── Party political identity ───────────────────────────────────────────────
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

    # ── Religion layer ────────────────────────────────────────────────────────
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

    # ── Regional layer ────────────────────────────────────────────────────────
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

    # ── Topic-specific option-vocabulary anchors ──────────────────────────────
    topic_anchors = []

    # sp01: Economic conditions
    # Target: A=5.4%, B=33.2%, C=33.3%, D=28.2%
    # SP-3 bugs: D too high (40.1% vs 28.2%); A=0% vs 5.4%
    # FIX (SP-4): add A for PSOE+it>=65; tighten D thresholds (eu-sk it<32, wc it<36); keep B/C
    if party == "PSOE" and it >= 65:
        topic_anchors.append('On Spain\'s economic situation: your answer is "Very good" (A) — the labour reform, minimum wage increases, EU recovery funds, and falling unemployment are real achievements. The economy is clearly improving under this government.')
    elif party in ("PSOE", "Cs"):
        topic_anchors.append('On Spain\'s economic situation: your answer is "Somewhat good" (B) — the fundamentals have improved: employment is up, wages are growing, and EU investment is arriving. Real problems remain — housing, youth precarity — but the trend is positive.')
    elif is_pro_eu and it >= 58:
        topic_anchors.append('On Spain\'s economic situation: your answer is "Somewhat good" (B) — the economic indicators are improving; employment and wages are trending positive even if housing remains a challenge.')
    elif party == "Vox" or (is_eu_skeptic and it < 32):
        topic_anchors.append('On Spain\'s economic situation: your answer is "Very bad" (D) — the government has failed ordinary Spaniards. Housing is unaffordable, youth unemployment is a scandal, and inflation destroyed household budgets while the political class cheered.')
    elif party == "Podemos/Sumar" and it < 38:
        topic_anchors.append('On Spain\'s economic situation: your answer is "Very bad" (D) — the housing crisis is a catastrophe, youth unemployment is structural, and the political class has no real answers. The economic model is broken for working people.')
    elif is_working_class and it < 36:
        topic_anchors.append('On Spain\'s economic situation: your answer is "Very bad" (D) — prices are still far too high, housing is unaffordable, and working people don\'t feel the recovery in their daily lives.')
    elif party in ("PP", "Independentista"):
        topic_anchors.append('On Spain\'s economic situation: your answer is "Somewhat bad" (C) — structural problems persist: housing costs are crushing families, youth unemployment remains high, the debt is unsustainable, and the government\'s reforms are ideologically driven rather than evidence-based.')
    elif party == "Podemos/Sumar":
        topic_anchors.append('On Spain\'s economic situation: your answer is "Somewhat bad" (C) — some macroeconomic indicators improved but housing is a disaster and youth precarity is structural. Ordinary workers don\'t feel the recovery.')
    else:
        topic_anchors.append('On Spain\'s economic situation: your answer is "Somewhat bad" (C) — prices are still high, housing is a disaster, and ordinary people don\'t feel the recovery in their daily lives.')

    # sp02: Democracy satisfaction
    # Target: A=8.5%, B=25.5%, C=35.5%, D=30.5%
    # SP-4 sim: A=0%, B=33.2%, C=45.5%, D=21.4%
    # FIX (SP-5): lower A threshold (PSOE it>=55); add Cs+pro-eu it>=65 → A; raise eu-sk D threshold to it<40
    if party == "PSOE" and it >= 55:
        topic_anchors.append('On democracy in Spain: your answer is "Very satisfied" (A) — Spanish democracy survived the far-right challenge in 2023. Pluralist coalition governance is democracy working as intended, even when messy.')
    elif (party == "Cs" or (is_pro_eu and it >= 65)) and party not in ("Podemos/Sumar", "Vox", "Independentista", "PP"):
        topic_anchors.append('On democracy in Spain: your answer is "Very satisfied" (A) — Spain\'s democratic institutions held through significant stress tests. Coalition governance and devolution are marks of democratic maturity.')
    elif party == "Podemos/Sumar":
        topic_anchors.append('On democracy in Spain: your answer is "Not too satisfied" (C) — the system needs significant reform but is functioning. The threats from the far right and the judicial right are the real dangers.')
    elif party == "Vox":
        topic_anchors.append('On democracy in Spain: your answer is "Not at all satisfied" (D) — Sánchez governs with separatists and radical left, making backroom deals that betray the constitution. Spanish democracy is broken.')
    elif party == "Independentista":
        topic_anchors.append('On democracy in Spain: your answer is "Not at all satisfied" (D) — a state that imprisons peaceful politicians and refuses to allow a legal referendum on independence is not a full democracy.')
    elif is_eu_skeptic and it < 40:
        topic_anchors.append('On democracy in Spain: your answer is "Not at all satisfied" (D) — politics is corrupt, the system serves elites, and ordinary citizens have no real voice.')
    elif party == "PSOE":
        topic_anchors.append('On democracy in Spain: your answer is "Somewhat satisfied" (B) — Spanish democracy survived the far-right threat in 2023. The coalition is messy but that\'s pluralist democracy working.')
    elif party == "PP" and it >= 58:
        topic_anchors.append('On democracy in Spain: your answer is "Somewhat satisfied" (B) — democracy is functioning even if this government\'s methods are concerning. Spain\'s institutions are resilient.')
    elif is_pro_eu and it >= 55:
        topic_anchors.append('On democracy in Spain: your answer is "Somewhat satisfied" (B) — Spain\'s democratic institutions have shown resilience; the system works even if it is far from perfect.')
    elif party in ("PP", "Cs"):
        topic_anchors.append('On democracy in Spain: your answer is "Not too satisfied" (C) — polarisation and the government\'s dependence on separatists have damaged institutional credibility and democratic norms.')
    else:
        topic_anchors.append('On democracy in Spain: your answer is "Not too satisfied" (C) — Spain\'s democracy has real structural problems: media concentration, judicial partisanship, and a political class that is disconnected from ordinary citizens.')

    # sp03: Russia view
    # Target: A=2.8%, B=5.7%, C=30.9%, D=60.6%
    # SP-4 sim: A=0%, B=0%, C=26.7%, D=73.3%
    # FIX (SP-5): Vox mf>=70 → A (extreme nationalist sympathy); Vox mf>=55 → B; all eu-sk+low-it pro-eu → C;
    #            reduce D by expanding C to pro-eu NP with it<40
    if party == "Vox" and mf >= 70:
        topic_anchors.append('On Russia: your answer is "Somewhat favorable" (A) — Russia\'s defence of Christian civilisation and national sovereignty against globalist liberal hegemony resonates with you, even if the war itself is problematic.')
    elif party == "Vox" and mf >= 55:
        topic_anchors.append('On Russia: your answer is "Somewhat unfavorable" (B) — you are deeply skeptical of NATO\'s role in provoking Russia. The Western media\'s uniformly anti-Russia framing is propaganda. A negotiated peace is needed.')
    elif party == "Podemos/Sumar":
        topic_anchors.append('On Russia: your answer is "Somewhat unfavorable" (C) — you oppose the invasion of Ukraine but also oppose NATO escalation. Neither imperialist bloc is innocent; a negotiated solution is needed.')
    elif party == "Vox":
        topic_anchors.append('On Russia: your answer is "Somewhat unfavorable" (C) — you oppose the invasion but are skeptical of NATO\'s role in provoking Russia. Sovereignty arguments resonate with you.')
    elif party in ("PP", "PSOE", "Cs"):
        topic_anchors.append('On Russia: your answer is "Very unfavorable" (D) — Russia\'s invasion of Ukraine is a war crime and an existential threat to the European security order.')
    elif party == "Independentista":
        topic_anchors.append('On Russia: your answer is "Very unfavorable" (D) — Russia\'s aggression against Ukrainian sovereignty resonates painfully with your own struggle for self-determination.')
    elif is_eu_skeptic:
        topic_anchors.append('On Russia: your answer is "Somewhat unfavorable" (C) — skeptical of NATO narratives but not supportive of the invasion.')
    elif it < 40 and is_pro_eu:
        topic_anchors.append('On Russia: your answer is "Somewhat unfavorable" (C) — you oppose the invasion but distrust the political establishment\'s narrative and are wary of military escalation.')
    else:
        topic_anchors.append('On Russia: your answer is "Very unfavorable" (D).')

    # sp04: EU view
    # Target: A=24.8%, B=41.7%, C=23.5%, D=10.0%
    # FIX (SP-3): route ALL PSOE → A; add pro-EU NP+it>=62 → A; add D for eu-sk+it<35+Vox-extreme
    if party == "PSOE":
        topic_anchors.append('On the European Union: your answer is "Very favorable" (A) — the EU has been central to Spain\'s democratic consolidation, economic development, and COVID recovery. Spain is a deeply European country and the EU is its natural home.')
    elif is_pro_eu and it >= 62:
        topic_anchors.append('On the European Union: your answer is "Very favorable" (A) — Spain has genuinely benefited enormously from EU membership: structural funds, the single market, democratic guarantees, and the COVID recovery plan.')
    elif party in ("PP", "Cs"):
        topic_anchors.append('On the European Union: your answer is "Somewhat favorable" (B) — the EU has real flaws but is fundamentally good for Spain. The structural funds, the single market, and the recovery plan have all helped.')
    elif party == "Independentista":
        topic_anchors.append('On the European Union: your answer is "Somewhat favorable" (B) — you see an independent Catalonia as a future EU member. The EU is the framework for a post-state Europe of regions.')
    elif is_pro_eu and it >= 42:
        topic_anchors.append('On the European Union: your answer is "Somewhat favorable" (B) — the EU has real benefits for Spain even if structural inequalities between north and south remain a problem.')
    elif is_eu_skeptic and it < 35:
        topic_anchors.append('On the European Union: your answer is "Very unfavorable" (D) — the EU imposed brutal austerity on Spain, serves northern European interests over southern ones, and has grown into an undemocratic technocracy that overrides national sovereignty.')
    elif party == "Vox" and it <= 38:
        topic_anchors.append('On the European Union: your answer is "Very unfavorable" (D) — Brussels imposes its progressive ideology on sovereign nations. Spain must recover control of its borders, its laws, and its destiny. The EU is a vehicle for cultural Marxism and demographic replacement.')
    elif party in ("Podemos/Sumar", "Vox"):
        topic_anchors.append('On the European Union: your answer is "Somewhat unfavorable" (C) — the EU as constituted serves capital over citizens or imposes sovereignty-eroding ideology. Fundamental reform is needed.')
    elif is_eu_skeptic and is_working_class:
        topic_anchors.append('On the European Union: your answer is "Somewhat unfavorable" (C) — austerity was imposed from Brussels; the EU serves the north, not the south.')
    else:
        topic_anchors.append('On the European Union: your answer is "Somewhat unfavorable" (C) — the EU has real benefits but also real costs for Spain\'s sovereignty and its working people.')

    # sp05: NATO view
    # Target: A=16.1%, B=39.0%, C=27.4%, D=17.5%
    # FIX (SP-2): PP→A rule was completely shadowed by PP+Cs+pro-EU→B (ordering bug).
    # All PP are Pro-EU so they all hit the B rule first — A=0% in SP-1.
    # Fix: PP+Cs → A first. Podemos → D (very unfavorable, not C). Add D for extreme EU-skeptic NP.
    if party in ("PP", "Cs"):
        topic_anchors.append('On NATO: your answer is "Very favorable" (A) — NATO is Spain\'s core security architecture. Article 5 guarantees are non-negotiable. Spain must meet its commitments and be a reliable, committed NATO member.')
    elif party == "Podemos/Sumar":
        topic_anchors.append('On NATO: your answer is "Not at all favorable" (D) — NATO is an instrument of US imperial power. Spain\'s pacifist and neutralist tradition demands we pursue real multilateral diplomacy, not military escalation. The 1986 referendum showed Spanish public ambivalence about NATO.')
    elif is_eu_skeptic and it <= 30:
        topic_anchors.append('On NATO: your answer is "Not at all favorable" (D) — NATO serves American interests, not Spanish ones. Multilateral military structures erode sovereignty and drag Spain into conflicts that are not ours.')
    elif party == "PSOE":
        topic_anchors.append('On NATO: your answer is "Somewhat favorable" (B) — NATO is a necessary security framework given Russia\'s aggression, even though Spain\'s historical relationship with it is complicated. European strategic autonomy must develop within the alliance.')
    elif party == "Vox":
        topic_anchors.append('On NATO: your answer is "Somewhat favorable" (B) — NATO defends Western civilisation against Russian aggression. You support it even if you distrust American cultural hegemony and EU federalism within the alliance.')
    elif party == "Independentista":
        topic_anchors.append('On NATO: your answer is "Somewhat unfavorable" (C) — you are deeply ambivalent about NATO\'s militarist agenda. You prefer negotiated, multilateral approaches to security and peace diplomacy over military deterrence.')
    elif is_eu_skeptic:
        topic_anchors.append('On NATO: your answer is "Somewhat unfavorable" (C) — skeptical of military alliances that ultimately serve US strategic interests rather than Spanish ones. Sovereignty concerns outweigh security arguments.')
    elif it >= 52:
        topic_anchors.append('On NATO: your answer is "Somewhat favorable" (B) — NATO is a necessity for European collective security, especially given Russia\'s aggression against Ukraine. Spain must be a reliable partner.')
    else:
        topic_anchors.append('On NATO: your answer is "Somewhat unfavorable" (C) — ambivalent: security concerns are real but so are reservations about military escalation and US leadership in the alliance.')

    # sp06: China view
    # Target: A=10.1%, B=24.2%, C=40.5%, D=25.2%
    # SP-4 sim: A=0%, B=32.1%, C=45.5%, D=22.5%
    # FIX (SP-5): eu-sk+it<40 → A (anti-establishment trade pragmatist, rejects Western anti-China bloc);
    #            PSOE → B; add pro-eu+it<45 NP → B (trade pragmatism); collapse remaining eu-sk B routes
    if is_eu_skeptic and it < 40:
        topic_anchors.append('On China: your answer is "Somewhat favorable" (A) — you reject the Western bloc\'s narrative on China. Trade relations with China are real and practically important for Spain. EU-imposed anti-China policy serves Brussels and Washington, not ordinary Spaniards.')
    elif party in ("PP", "Cs"):
        topic_anchors.append('On China: your answer is "Very unfavorable" (D) — China is a systemic rival and strategic competitor. It supports Russia\'s war against Ukraine, practises economic coercion, and represents an authoritarian model fundamentally incompatible with Spain\'s values and EU partnerships. Huawei infrastructure is a security risk.')
    elif party in ("PSOE",):
        topic_anchors.append('On China: your answer is "Somewhat favorable" (B) — China is a complex partner. Spain\'s trade relationship matters. You are cautious about unthinking alignment with US-led anti-China campaigns, though China\'s Russia support and human rights record are real concerns.')
    elif party == "Vox":
        topic_anchors.append('On China: your answer is "Somewhat unfavorable" (C) — China\'s authoritarian model and economic dumping threaten Spanish sovereignty and jobs. Its support for Russia is dangerous. You are wary but not entirely aligned with EU anti-China posture.')
    elif party == "Podemos/Sumar":
        topic_anchors.append('On China: your answer is "Somewhat unfavorable" (C) — you oppose Chinese authoritarianism and surveillance even if you also oppose US hegemony and Western double-standards. Neither imperial bloc is innocent.')
    elif party == "Independentista":
        topic_anchors.append('On China: your answer is "Somewhat unfavorable" (C) — China\'s repression of Tibetan and Uyghur ethnic identity resonates painfully with your own experience of Catalan cultural suppression.')
    elif is_pro_eu and it >= 55:
        topic_anchors.append('On China: your answer is "Very unfavorable" (D) — China is a systemic rival that supports Russia, uses economic coercion, and undermines the rules-based international order. Spain must stand with its EU and Atlantic partners.')
    elif is_pro_eu and it < 45:
        topic_anchors.append('On China: your answer is "Somewhat favorable" (B) — trade pragmatism matters; not fully aligned with the EU\'s anti-China consensus. Economic ties with China are real even if the strategic concerns are valid.')
    elif is_pro_eu and it >= 40:
        topic_anchors.append('On China: your answer is "Somewhat unfavorable" (C) — a strategic concern and systemic rival; Spain must be cautious in its dealings with China even if economic ties are real.')
    else:
        topic_anchors.append('On China: your answer is "Somewhat favorable" (B) — trade pragmatism matters; not fully aligned with the EU\'s anti-China consensus.')

    # sp07: Trump confidence
    # Target: A=6.9%, B=11.5%, C=21.0%, D=60.6%
    # SP-4 sim: A=0%, B=10.7%, C=33.7%, D=55.6%
    # FIX (SP-5): Vox mf>=65 → A; all Vox → B; eu-sk+mf>=44 → B (before Podemos C/D rule);
    #            MOVE Podemos → D BEFORE is_pro_eu+it<45 (was causing Podemos to hit C)
    if party == "Vox" and mf >= 65:
        topic_anchors.append('On Trump: your answer is "A lot of confidence" (A) — Trump\'s defence of Western Christian civilisation, his willingness to name the globalist enemy, and his America-first nationalism make him the most consequential Western leader of our era.')
    elif party == "Vox":
        topic_anchors.append('On Trump: your answer is "Some confidence" (B) — Trump\'s America-first nationalism resonates with your own political instincts. He fights the globalist elites that Spain\'s establishment serves.')
    elif is_eu_skeptic and mf >= 44:
        topic_anchors.append('On Trump: your answer is "Some confidence" (B) — Trump\'s defence of national sovereignty and his willingness to challenge the globalist consensus resonate with you, even if his style is sometimes chaotic.')
    elif party == "Podemos/Sumar":
        topic_anchors.append('On Trump: your answer is "No confidence at all" (D) — Trump represents racism, xenophobia, and American imperial arrogance. He is a danger to democracy worldwide.')
    elif party == "PP" and mf >= 55:
        topic_anchors.append('On Trump: your answer is "Not too much confidence" (C) — you share some conservative instincts but his style is chaotic and his treatment of NATO allies is strategically dangerous for Spain.')
    elif is_pro_eu and it < 45:
        topic_anchors.append('On Trump: your answer is "Not too much confidence" (C) — his behaviour is erratic and his hostility to multilateral institutions is concerning, but the strong reaction against him sometimes seems excessive.')
    elif party in ("PSOE", "Independentista", "PP", "Cs"):
        topic_anchors.append('On Trump: your answer is "No confidence at all" (D) — Trump is a threat to the democratic world order, a danger to European security, and his second term has confirmed the worst fears about his contempt for alliances and rule of law.')
    elif is_pro_eu:
        topic_anchors.append('On Trump: your answer is "No confidence at all" (D) — Trump undermines the multilateral institutions and alliances that Spain depends on for security and prosperity.')
    else:
        topic_anchors.append('On Trump: your answer is "No confidence at all" (D) — Trump\'s hostility to multilateralism and his disdain for European allies make him deeply dangerous from Spain\'s perspective.')

    # sp08: Religion importance
    # Target: A=17.4%, B=22.2%, C=25.4%, D=35.1%
    # SP-4 sim: A=17.6%, B=12.3%, C=38.5%, D=31.6%
    # FIX (SP-5): lower non-practicing→B threshold from mf>=50 to mf>=44 (adds moderate-MF NP personas to B);
    #            add Cs secular → D (fully secular liberal); reduces C over-count
    if is_catholic_practicing:
        topic_anchors.append('On religion in your life: your answer is "Very important" (A) — your Catholic faith is foundational to your values, your family, and your sense of community.')
    elif "non-practicing" in religion and mf >= 44:
        topic_anchors.append('On religion in your life: your answer is "Somewhat important" (B) — your Catholic upbringing shaped your values even if you no longer attend mass regularly. It is part of your cultural identity.')
    elif "non-practicing" in religion and party in ("PP",):
        topic_anchors.append('On religion in your life: your answer is "Somewhat important" (B) — religion is part of your cultural identity and social values even if you\'re not devout.')
    elif party == "Vox":
        topic_anchors.append('On religion in your life: your answer is "Somewhat important" (B) — Spain\'s Catholic identity is part of its civilisational heritage that must be defended.')
    elif is_secular and party in ("Cs",):
        topic_anchors.append('On religion in your life: your answer is "Not at all important" (D) — you are firmly secular and liberal; religion plays no role in your values or decisions.')
    elif party in ("Podemos/Sumar",) and is_secular:
        topic_anchors.append('On religion in your life: your answer is "Not at all important" (D) — you are firmly secular. Religion belongs in the private sphere and has no place in public policy.')
    elif party in ("PSOE", "Independentista") and is_secular:
        topic_anchors.append('On religion in your life: your answer is "Not at all important" (D) — religion plays no significant role in your life.')
    elif is_secular and ct >= 70:
        topic_anchors.append('On religion in your life: your answer is "Not at all important" (D) — you are secular; religion is irrelevant to your values and decisions.')
    elif is_secular:
        topic_anchors.append('On religion in your life: your answer is "Not too important" (C) — religion is not a significant part of your life.')
    else:
        topic_anchors.append('On religion in your life: your answer is "Not too important" (C).')

    # sp09: Economic system reform
    # Target: A=17.9%, B=60.0%, C=20.8%, D=1.3%
    # SP-4 sim: A=26.7%, B=62.6%, C=10.7%, D=0%
    # FIX (SP-5): remove eu-sk+wc+it<35 → A (too many A); narrow to it<30 only; extend PP→C to ind>=60;
    #            add explicit Vox→B; add eu-sk+ind>=58→C (Vox remaining: market-orientation = minor changes)
    if party == "Podemos/Sumar":
        topic_anchors.append('On economic reform: your answer is "Needs to be completely reformed" (A) — capitalism in its current form is incompatible with housing rights, climate justice, and generational equity.')
    elif party == "Vox" and it <= 42:
        topic_anchors.append('On economic reform: your answer is "Needs to be completely reformed" (A) — the globalist economic model has destroyed Spanish jobs, sovereignty, and family stability.')
    elif is_eu_skeptic and is_working_class and it < 30:
        topic_anchors.append('On economic reform: your answer is "Needs to be completely reformed" (A) — the current system is completely rigged against people like you; nothing short of total overhaul will fix it.')
    elif party in ("PP",) and ind >= 60:
        topic_anchors.append('On economic reform: your answer is "Needs minor changes" (C) — Spain needs deregulation and lower taxes, not more state intervention. The framework is broadly sound.')
    elif party == "Cs" and ind >= 65:
        topic_anchors.append('On economic reform: your answer is "Needs minor changes" (C) — Spain needs pro-market structural reforms, not redistribution. Liberalise the labour market and reduce red tape.')
    elif is_eu_skeptic and ind >= 58:
        topic_anchors.append('On economic reform: your answer is "Needs minor changes" (C) — the system needs adjustment, not radical overhaul. More market freedom, less state interference, and restored national sovereignty would fix the real problems.')
    elif party == "PSOE":
        topic_anchors.append('On economic reform: your answer is "Needs major changes" (B) — major redistribution, stronger workers\' rights, affordable housing, and green investment are essential.')
    elif party == "PP":
        topic_anchors.append('On economic reform: your answer is "Needs major changes" (B) — the current model needs reform but through smart, disciplined policy, not ideological experiments.')
    elif party == "Vox":
        topic_anchors.append('On economic reform: your answer is "Needs major changes" (B) — significant economic restructuring is needed to restore Spanish sovereignty, protect families, and cut the red tape that strangles enterprise.')
    elif party == "Independentista":
        topic_anchors.append('On economic reform: your answer is "Needs major changes" (B) — Catalonia\'s fiscal relationship with Spain is deeply unfair; major structural reform is needed.')
    else:
        topic_anchors.append('On economic reform: your answer is "Needs major changes" (B).')

    # sp10: Income inequality
    # Target: A=47.4%, B=33.1%, C=14.4%, D=5.2%
    # FIX (SP-2): old code had A=93.6% — almost everything went to A.
    # Fix: PP → C/D (right-wing, see inequality as smaller problem); Cs → C;
    # Vox+Indy → B; NP non-working-class → B; working-class+PSOE+Podemos → A.
    if party in ("Podemos/Sumar", "PSOE"):
        topic_anchors.append('On income inequality: your answer is "Very big problem" (A) — Spain has among the highest inequality in the EU. The housing crisis, youth precarity, and poverty wages are symptoms of a deeply unfair economic model.')
    elif is_working_class and it < 50:
        topic_anchors.append('On income inequality: your answer is "Very big problem" (A) — the gap between rich and poor is very real in your daily life. Housing is unaffordable, wages don\'t keep pace with prices, and the wealthy live in a different Spain.')
    elif party == "PP" and ind >= 65:
        topic_anchors.append('On income inequality: your answer is "Not a problem" (D) — inequality reflects different levels of effort, talent, and entrepreneurship. Redistribution punishes success, raises taxes, and destroys the dynamism that creates broad prosperity.')
    elif party in ("PP", "Cs"):
        topic_anchors.append('On income inequality: your answer is "Small problem" (C) — Spain\'s welfare state and EU convergence have significantly reduced inequality. The solution is growth and opportunity, not higher taxes and redistribution.')
    elif party == "Vox":
        topic_anchors.append('On income inequality: your answer is "Moderately big problem" (B) — the economic gap is real and growing, especially for Spanish families squeezed by immigration-driven housing costs and globalisation. But the solution is protecting Spanish workers, not socialist redistribution.')
    elif party == "Independentista":
        topic_anchors.append('On income inequality: your answer is "Moderately big problem" (B) — inequality is real across Spain, but the Catalan fiscal framework makes it worse: Catalonia funds the rest of Spain at the expense of Catalan families and public services.')
    else:
        topic_anchors.append('On income inequality: your answer is "Moderately big problem" (B) — inequality is a real concern in Spain, even if the welfare state provides some protection. The housing crisis and youth precarity are its most visible symptoms.')

    # sp11: PP view
    # Target: A=10.2%, B=23.2%, C=34.4%, D=32.2%
    # SP-3 bugs: B=4.3% (too low); A=13.9% (slightly high)
    # FIX (SP-4): raise A threshold (PP+it>=58); broaden NP B (ind>=52+it>=42); add eu-sk+it<32 NP → D
    if party == "PP" and it >= 58:
        topic_anchors.append('On the PP: your answer is "Very favorable" (A) — the PP is Spain\'s only serious party of stable governance. It stands for constitutional unity, economic responsibility, and institutional reliability.')
    elif party in ("PP", "Cs"):
        topic_anchors.append('On the PP: your answer is "Somewhat favorable" (B) — you support the PP\'s direction even if some positions need updating or some alliances are uncomfortable.')
    elif ind >= 52 and it >= 42:
        topic_anchors.append('On the PP: your answer is "Somewhat favorable" (B) — of the serious options, the PP is closest to your values on economic responsibility and institutional stability, even if their style is sometimes frustrating.')
    elif party in ("PSOE", "Podemos/Sumar"):
        topic_anchors.append('On the PP: your answer is "Very unfavorable" (D) — the PP represents austerity, the Gürtel corruption scandal, and a recentralising vision of Spain that denies pluralism and punishes working people.')
    elif is_eu_skeptic and it < 32:
        topic_anchors.append('On the PP: your answer is "Very unfavorable" (D) — the PP is the party of the privileged establishment. They don\'t represent people like you and are as corrupt and out-of-touch as the rest.')
    elif party == "Vox":
        topic_anchors.append('On the PP: your answer is "Somewhat unfavorable" (C) — the PP talks tough but always caves to separatists and the left. They lack the courage to defend Spain properly against the real threats.')
    elif party == "Independentista":
        topic_anchors.append('On the PP: your answer is "Somewhat unfavorable" (C) — the PP\'s aggressive unionism and hostility to Catalan self-determination make dialogue impossible, but they are an adversary, not an existential threat.')
    elif is_pro_eu and it >= 55:
        topic_anchors.append('On the PP: your answer is "Somewhat unfavorable" (C) — their alliance with Vox and their confrontational stance on Catalan dialogue worry you significantly.')
    else:
        topic_anchors.append('On the PP: your answer is "Somewhat unfavorable" (C) — a mainstream establishment party that doesn\'t speak to your concerns and whose governance record is mixed at best.')

    # sp12: PSOE view
    # Target: A=9.7%, B=25.5%, C=27.2%, D=37.6%
    if party == "PSOE" and it >= 56:
        topic_anchors.append('On the PSOE: your answer is "Very favorable" (A) — the PSOE has delivered real progressive change: the labour reform, minimum wage rises, and COVID recovery. Sánchez has been a strong leader.')
    elif party == "PSOE":
        topic_anchors.append('On the PSOE: your answer is "Somewhat favorable" (B) — you support the PSOE\'s direction even with frustrations about governing with Podemos and Junts.')
    elif party == "Podemos/Sumar":
        topic_anchors.append('On the PSOE: your answer is "Somewhat unfavorable" (C) — the PSOE talks progressive but always defends the system. They co-opt radical demands and water them down.')
    elif party == "Independentista":
        topic_anchors.append('On the PSOE: your answer is "Somewhat favorable" (B) — Sánchez\'s willingness to negotiate amnesty and dialogue is better than the PP\'s total intransigence, even if it\'s not enough.')
    elif party in ("PP", "Vox"):
        topic_anchors.append('On the PSOE: your answer is "Very unfavorable" (D) — Sánchez has sold Spain out to separatists and radical leftists to cling to power. The PSOE under him is unrecognisable.')
    elif party == "Cs":
        topic_anchors.append('On the PSOE: your answer is "Somewhat unfavorable" (C) — the PSOE\'s dependence on Junts and its handling of the Catalan crisis are constitutionally troubling.')
    elif is_pro_eu and it >= 55:
        topic_anchors.append('On the PSOE: your answer is "Somewhat unfavorable" (C) — the governing coalition\'s complexity concerns you even if you accept some of its policies.')
    elif is_eu_skeptic and it < 35:
        topic_anchors.append('On the PSOE: your answer is "Very unfavorable" (D).')
    else:
        topic_anchors.append('On the PSOE: your answer is "Somewhat unfavorable" (C).')

    # sp13: Podemos view
    # Target: A=6.7%, B=16.3%, C=29.9%, D=47.1%
    if party == "Podemos/Sumar" and ct >= 82:
        topic_anchors.append('On Podemos: your answer is "Very favorable" (A) — Podemos brought working class and feminist demands into mainstream politics. Their programme is the only real alternative to neo-liberal austerity.')
    elif party == "Podemos/Sumar":
        topic_anchors.append('On Podemos: your answer is "Somewhat favorable" (B) — you support their direction even if internal splits and government participation have diluted the radical message.')
    elif party == "PSOE":
        topic_anchors.append('On Podemos: your answer is "Somewhat unfavorable" (C) — you share some social goals but Podemos\'s populism, internal chaos, and anti-NATO stance alienate you.')
    elif party == "Independentista":
        topic_anchors.append('On Podemos: your answer is "Somewhat unfavorable" (C) — they share some values but their Spanish unitarian instincts conflict with your demand for Catalan self-determination.')
    elif party in ("PP", "Vox"):
        topic_anchors.append('On Podemos: your answer is "Very unfavorable" (D) — radical socialist populism, anti-democratic impulses, and a foreign policy that excuses Russia and Venezuela.')
    elif party == "Cs":
        topic_anchors.append('On Podemos: your answer is "Very unfavorable" (D) — populist, economically reckless, and a destabilising force in Spanish politics.')
    elif is_eu_skeptic and is_working_class and it < 35:
        topic_anchors.append('On Podemos: your answer is "Somewhat favorable" (B) — they at least name the problems ordinary people face.')
    else:
        topic_anchors.append('On Podemos: your answer is "Very unfavorable" (D).')

    # sp14: Vox view
    # Target: A=8.1%, B=15.1%, C=21.6%, D=55.1%
    # SP-3 bugs: C=38% (too high), D=46% (too low) — ordering bug: mf>=55+it<45 was before party D rules
    # FIX (SP-4): move party-specific D rules (PSOE/Podemos/Indy/Cs) BEFORE the mf/it NP B rule
    if party == "Vox" and it <= 50:
        topic_anchors.append('On Vox: your answer is "Very favorable" (A) — Vox is the only party that defends Spain\'s constitutional unity, its Christian heritage, and the rights of Spaniards against mass immigration, separatism, and the progressive agenda.')
    elif party == "Vox":
        topic_anchors.append('On Vox: your answer is "Somewhat favorable" (B) — you support Vox\'s defence of Spain even if some positions go further than you\'d personally take.')
    elif party in ("PSOE", "Podemos/Sumar", "Independentista", "Cs"):
        topic_anchors.append('On Vox: your answer is "Very unfavorable" (D) — Vox is a neo-fascist party that glorifies the Franco dictatorship, threatens democratic coexistence, and represents the most dangerous force in contemporary Spanish politics.')
    elif mf >= 55 and it < 45:
        topic_anchors.append('On Vox: your answer is "Somewhat favorable" (B) — Vox\'s defence of Catholic heritage and traditional values resonates with you even if their style is sometimes too confrontational.')
    elif party == "PP":
        topic_anchors.append('On Vox: your answer is "Somewhat unfavorable" (C) — you share some concerns about national unity and immigration but Vox\'s extremism damages the right\'s electoral credibility and democratic culture.')
    elif is_eu_skeptic and is_working_class and it < 35:
        topic_anchors.append('On Vox: your answer is "Somewhat unfavorable" (C) — you understand the anger they channel but their extreme positions and nostalgia for Franco aren\'t the answer.')
    elif is_pro_eu and not is_secular:
        topic_anchors.append('On Vox: your answer is "Somewhat unfavorable" (C) — their authoritarian nationalism conflicts with your support for European values and democratic pluralism, even if you share some traditional social values.')
    elif is_pro_eu and is_secular:
        topic_anchors.append('On Vox: your answer is "Very unfavorable" (D) — their authoritarian nationalism, hostility to pluralism, and nostalgia for Franco\'s dictatorship are incompatible with democratic European values.')
    else:
        topic_anchors.append('On Vox: your answer is "Very unfavorable" (D) — their extreme nationalism, anti-immigration agenda, and authoritarian tendencies threaten Spain\'s democratic coexistence and international standing.')

    # sp15: Children's future (3-option!)
    # Target: A=19.8%, B=78.9%, C=1.3%
    # NOTE: 3-option question — A/B/C only
    # SP-3 bugs: A=25.1% (too high), C=10.7% (too high), B=64.2% (too low)
    # FIX (SP-4): raise PSOE A threshold (it>=55+age<=50); remove C route entirely (→ B); default → B
    if party == "PSOE" and it >= 55 and age <= 50:
        topic_anchors.append('On children\'s financial future: your answer is "Better off" (A) — progressive policies, labour reform, the minimum wage rise, and European investment offer genuine hope for the next generation. Spain\'s trajectory is positive. (3 options only: A/B/C)')
    elif party in ("PP", "Cs") and it >= 60 and ind >= 60:
        topic_anchors.append('On children\'s financial future: your answer is "Better off" (A) — Spain\'s market dynamism, EU integration, and export competitiveness will create real opportunities for the next generation if the right policies are in place. (3 options only: A/B/C)')
    elif party == "Independentista" and ct >= 72:
        topic_anchors.append('On children\'s financial future: your answer is "Better off" (A) — an independent Catalonia within the EU would give future generations better opportunities than the current fiscal relationship with Spain allows. (3 options only: A/B/C)')
    elif is_pro_eu and it >= 65 and age <= 40:
        topic_anchors.append('On children\'s financial future: your answer is "Better off" (A) — Spain\'s EU integration and economic modernisation are creating real opportunities for young people, even if housing remains a challenge. (3 options only: A/B/C)')
    elif party in ("Vox", "Podemos/Sumar") or (is_working_class and age >= 40):
        topic_anchors.append('On children\'s financial future: your answer is "Worse off" (B) — housing prices, precarious jobs, climate change, and political dysfunction make the future look very bleak for young Spaniards. (3 options only: A/B/C)')
    elif age >= 55:
        topic_anchors.append('On children\'s financial future: your answer is "Worse off" (B) — in your experience, each generation has faced more precarity. The housing crisis is a catastrophe for young people. (3 options only: A/B/C)')
    elif party == "Independentista":
        topic_anchors.append('On children\'s financial future: your answer is "Worse off" (B) — under the current Spanish fiscal framework, Catalonia\'s young people face the same housing and unemployment crisis as everyone else. (3 options only: A/B/C)')
    else:
        topic_anchors.append('On children\'s financial future: your answer is "Worse off" (B) — Spain\'s housing crisis and youth unemployment make pessimism the rational default for most people. (3 options only: A/B/C)')

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

    print(f"\nEurope Benchmark — Spain — Sprint {sprint_id}")
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
    parser = argparse.ArgumentParser(description="Europe Benchmark Spain sprint runner")
    parser.add_argument("--sprint", required=True, help="Sprint ID, e.g. SP-1")
    parser.add_argument("--model", choices=["haiku", "sonnet"], default="haiku")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run_sprint_batch(args.sprint, args.model, args.dry_run)


if __name__ == "__main__":
    main()
