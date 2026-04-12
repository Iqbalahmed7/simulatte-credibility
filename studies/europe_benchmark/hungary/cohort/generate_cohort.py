"""Generate Hungary General Population cohort via Simulatte Persona Generator."""
from __future__ import annotations
import sys
from pathlib import Path

PERSONA_GEN_DIR = Path("/Users/admin/Documents/Simulatte Projects/Persona Generator")
if str(PERSONA_GEN_DIR) not in sys.path:
    sys.path.insert(0, str(PERSONA_GEN_DIR))

from src.orchestrator import invoke_persona_generator_sync
from src.orchestrator.brief import PersonaGenerationBrief, RunIntent

brief = PersonaGenerationBrief(
    client="Simulatte Credibility",
    domain="hungary_general",
    business_problem=(
        "Replicate Pew Spring 2024 Hungary opinion distributions across validated "
        "survey questions covering economic conditions, democracy satisfaction, "
        "views on Russia, EU, NATO, Trump, and Hungarian party favourability "
        "(Fidesz, opposition/MSZP, Jobbik/Péter Magyar, DK). "
        "Cohort must represent the Hungarian adult public: Fidesz-dominant political "
        "landscape, urban Budapest vs rural divide, calibrated to Pew Spring 2024 "
        "toplines (N=1,009)."
    ),
    count=40,
    run_intent=RunIntent.DELIVER,
    auto_confirm=True,
    persona_id_prefix="hu",
    output_dir=str(Path(__file__).parent),
    emit_pipeline_doc=True,
    skip_gates=True,
)

print("Invoking Simulatte Persona Generator — Hungary General Population")
result = invoke_persona_generator_sync(brief)
print(f"\n✓ Cohort saved ({result.count_delivered} personas) | {result.summary}")
