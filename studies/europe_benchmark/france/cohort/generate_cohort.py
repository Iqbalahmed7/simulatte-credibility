"""Generate France General Population cohort via Simulatte Persona Generator."""
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
    domain="france_general",
    business_problem=(
        "Replicate Pew Spring 2024 France opinion distributions across validated "
        "survey questions covering economic conditions, democracy satisfaction, "
        "views on Russia, EU, NATO, China, Trump, religion importance, economic "
        "reform preferences, income inequality, and French party favourability "
        "(RN, Renaissance/Macron, LFI, LR, PS). "
        "Cohort must represent the French adult public: urban/rural, full political "
        "spectrum from RN to LFI, calibrated to Pew Spring 2024 toplines (N=1,002)."
    ),
    count=40,
    run_intent=RunIntent.DELIVER,
    auto_confirm=True,
    persona_id_prefix="fr",
    output_dir=str(Path(__file__).parent),
    emit_pipeline_doc=True,
    skip_gates=True,
)

print("Invoking Simulatte Persona Generator — France General Population")
result = invoke_persona_generator_sync(brief)
print(f"\n✓ Cohort saved ({result.count_delivered} personas) | {result.summary}")
