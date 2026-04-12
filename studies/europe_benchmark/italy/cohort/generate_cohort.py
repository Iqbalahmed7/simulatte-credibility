"""Generate Italy General Population cohort via Simulatte Persona Generator."""
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
    domain="italy_general",
    business_problem=(
        "Replicate Pew Spring 2024 Italy opinion distributions across validated "
        "survey questions covering economic conditions, democracy satisfaction, "
        "views on Russia, EU, NATO, China, Trump, religion importance, and Italian "
        "party favourability (FdI/Meloni, PD, M5S, Lega, Forza Italia). "
        "Cohort must represent the Italian adult public: North/South divide, "
        "urban/rural, cultural Catholic majority, calibrated to Pew Spring 2024 "
        "toplines (N=1,120)."
    ),
    count=40,
    run_intent=RunIntent.DELIVER,
    auto_confirm=True,
    persona_id_prefix="it",
    output_dir=str(Path(__file__).parent),
    emit_pipeline_doc=True,
    skip_gates=True,
)

print("Invoking Simulatte Persona Generator — Italy General Population")
result = invoke_persona_generator_sync(brief)
print(f"\n✓ Cohort saved ({result.count_delivered} personas) | {result.summary}")
