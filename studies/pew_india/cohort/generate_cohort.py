"""
Generate India General Population cohort via Simulatte Persona Generator.

Invokes invoke_persona_generator_sync() with domain="india_general",
sarvam_enabled=True, 40 personas at DELIVER tier.

Output: india_general_cohort.json saved to this directory.

Usage:
    python3 studies/pew_india/cohort/generate_cohort.py

Run from the Simulatte Credibility repo root (or any directory —
the script inserts the Persona Generator path automatically).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# ── Resolve Persona Generator source path ────────────────────────────────────
PERSONA_GEN_DIR = Path("/Users/admin/Documents/Simulatte Projects/Persona Generator")
if str(PERSONA_GEN_DIR) not in sys.path:
    sys.path.insert(0, str(PERSONA_GEN_DIR))

from src.orchestrator import invoke_persona_generator_sync          # noqa: E402
from src.orchestrator.brief import PersonaGenerationBrief, RunIntent  # noqa: E402

# ── Brief ─────────────────────────────────────────────────────────────────────
brief = PersonaGenerationBrief(
    client="Simulatte Credibility",
    domain="india_general",
    business_problem=(
        "Replicate Pew India 2023–2024 opinion distributions across 15 validated "
        "survey questions covering democracy satisfaction, political party approval "
        "(BJP / INC / Modi), governance preferences, economic sentiment, national "
        "pride, religious identity, gender norms, and climate threat perception. "
        "Cohort must represent the Indian adult public: urban/rural split, "
        "North/South/East/West regions, Hindu majority with Muslim minority, "
        "full BJP-to-opposition political spectrum calibrated to Pew 2023 toplines."
    ),
    count=40,
    run_intent=RunIntent.DELIVER,
    sarvam_enabled=False,   # Sarvam enrichment disabled — LLM client bug in pipeline.py
    auto_confirm=True,
    persona_id_prefix="in",
    output_dir=str(Path(__file__).parent),
    emit_pipeline_doc=True,
    # Commercial cohort diversity gates (G6-G8: age bracket %, pairwise cosine distance,
    # archetype type count) are designed for customer persona deliverables, not for
    # population opinion survey replication. Distribution quality is validated externally
    # against Pew Research Center ground truth via DA = 1 − TVD.
    skip_gates=True,
)

# ── Run ───────────────────────────────────────────────────────────────────────
print("Invoking Simulatte Persona Generator — India General Population")
print(f"  domain       : {brief.domain}")
print(f"  count        : {brief.count}")
print(f"  run_intent   : {brief.run_intent}")
print(f"  sarvam       : {brief.sarvam_enabled}")
print(f"  output_dir   : {brief.output_dir}")
print()

result = invoke_persona_generator_sync(brief)

# ── Save cohort JSON ──────────────────────────────────────────────────────────
out_path = Path(__file__).parent / "india_general_cohort.json"

cohort_data = {
    "run_id": result.run_id,
    "cohort_id": result.cohort_id,
    "generated_at": result.generated_at,
    "domain": result.domain,
    "tier_used": result.tier_used,
    "count_delivered": result.count_delivered,
    "quality_report": result.quality_report.model_dump() if hasattr(result.quality_report, "model_dump") else result.quality_report,
    "summary": result.summary,
    "personas": [],
}

for p in result.personas:
    wv = p.worldview
    da = p.demographic_anchor
    loc = da.location if da else None
    hh = da.household if da else None

    persona_entry = {
        "persona_id": p.persona_id,
        "name": p.narrative.display_name if p.narrative else p.persona_id,
        "age": da.age if da else None,
        "gender": da.gender if da else None,
        "country": loc.country if loc else "India",
        "region": loc.region if loc else None,
        "city": loc.city if loc else None,
        "urban_tier": loc.urban_tier if loc else None,
        "income_bracket": hh.income_bracket if hh else None,
        "education": da.education if da else None,
        "employment": da.employment if da else None,
        "political_archetype": (
            wv.political_profile.archetype if wv and wv.political_profile else None
        ),
        "worldview": {
            "institutional_trust": wv.institutional_trust if wv else None,
            "social_change_pace": wv.social_change_pace if wv else None,
            "collectivism_score": wv.collectivism_score if wv else None,
            "economic_security_priority": wv.economic_security_priority if wv else None,
            "religious_salience": wv.religious_salience if wv else None,
        },
        "narrative_first_person": (
            p.narrative.first_person if p.narrative else None
        ),
    }
    cohort_data["personas"].append(persona_entry)

out_path.write_text(json.dumps(cohort_data, indent=2, ensure_ascii=False))
print(f"\n✓ Cohort saved → {out_path}")
print(f"  Personas delivered : {result.count_delivered}")
print(f"  Summary            : {result.summary}")
