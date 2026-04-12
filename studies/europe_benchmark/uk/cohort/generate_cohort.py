"""
Generate UK General Population cohort via Simulatte Persona Generator.
Output is saved by the streaming writer to: cohort-uk_general-{hash}.json

Usage:
    python3 studies/europe_benchmark/uk/cohort/generate_cohort.py
"""

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
    domain="uk_general",
    business_problem=(
        "Replicate Pew Spring 2024 UK opinion distributions across validated "
        "survey questions covering economic conditions, democracy satisfaction, "
        "views on Russia, EU, NATO, China, Trump, religion importance, economic "
        "reform preferences, income inequality, and UK party favourability "
        "(Conservative, Labour, Lib Dems, Reform UK). "
        "Cohort must represent the British adult public: England/Scotland/Wales, "
        "urban/rural split, full political spectrum from Reform UK to Labour/SNP, "
        "calibrated to Pew Spring 2024 toplines (N=1,017)."
    ),
    count=40,
    run_intent=RunIntent.DELIVER,
    auto_confirm=True,
    persona_id_prefix="uk",
    output_dir=str(Path(__file__).parent),
    emit_pipeline_doc=True,
    skip_gates=True,
)

print("Invoking Simulatte Persona Generator — UK General Population")
result = invoke_persona_generator_sync(brief)
print(f"\n✓ Cohort saved by streaming writer ({result.count_delivered} personas)")
print(f"  Summary: {result.summary}")
