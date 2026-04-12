"""Generate Greece General Population cohort via Simulatte Persona Generator."""
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
    domain="greece_general",
    business_problem=(
        "Replicate Pew Spring 2024 Greece opinion distributions across validated "
        "survey questions covering economic conditions, democracy satisfaction, "
        "views on Russia, EU, NATO, China, Trump, religion importance, and Greek "
        "party favourability (ND, SYRIZA, PASOK, KKE, Greek Solution, Spartans). "
        "Cohort must represent the Greek adult public: urban/rural, Orthodox Christian "
        "majority, full political spectrum, calibrated to Pew Spring 2024 toplines (N=1,018)."
    ),
    count=40,
    run_intent=RunIntent.DELIVER,
    auto_confirm=True,
    persona_id_prefix="gr",
    output_dir=str(Path(__file__).parent),
    emit_pipeline_doc=True,
    skip_gates=True,
)

print("Invoking Simulatte Persona Generator — Greece General Population")
result = invoke_persona_generator_sync(brief)
print(f"\n✓ Cohort saved ({result.count_delivered} personas) | {result.summary}")
