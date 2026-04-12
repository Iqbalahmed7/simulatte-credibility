"""
Generate Europe Benchmark v2 cohorts locally — no Anthropic API calls.

Uses demographic_sampler.sample_demographic_anchor() directly to build
WorldviewAnchor data from local pool definitions. Skips expensive LLM
narrative generation (not needed for sprint runner calibration).

Generates cohorts for all 9 European countries and saves them in the
same JSON format that sprint_runner.py expects.

Usage:
    python3 studies/europe_benchmark/generate_cohorts_local.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PERSONA_GEN_DIR = Path("/Users/admin/Documents/Simulatte Projects/Persona Generator")
if str(PERSONA_GEN_DIR) not in sys.path:
    sys.path.insert(0, str(PERSONA_GEN_DIR))

from src.generation.demographic_sampler import sample_demographic_anchor  # noqa: E402

# Countries to generate (domain → output path)
COUNTRIES = {
    "greece_general":      Path(__file__).parent / "greece/cohort",
    "hungary_general":     Path(__file__).parent / "hungary/cohort",
    "italy_general":       Path(__file__).parent / "italy/cohort",
    "netherlands_general": Path(__file__).parent / "netherlands/cohort",
    "poland_general":      Path(__file__).parent / "poland/cohort",
    "spain_general":       Path(__file__).parent / "spain/cohort",
    "sweden_general":      Path(__file__).parent / "sweden/cohort",
}

COHORT_SIZE = 40


def build_cohort(domain: str, output_dir: Path) -> Path:
    """Build a cohort from the local demographic pool and save to JSON."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Derive a short hash from domain for file naming consistency
    domain_hash = format(abs(hash(domain)) % 0xFFFFFF, "06x")
    cohort_id = f"cohort-{domain}-{domain_hash}"

    personas = []
    for i in range(COHORT_SIZE):
        da = sample_demographic_anchor(domain=domain, index=i, seed=42 + i)

        # Extract location
        loc = da.location
        hh = da.household
        wv = da.worldview

        # Build worldview dict
        wv_dict = None
        if wv is not None:
            pp = wv.political_profile
            wv_dict = {
                "institutional_trust": wv.institutional_trust,
                "social_change_pace": wv.social_change_pace,
                "collectivism_score": wv.collectivism_score,
                "economic_security_priority": wv.economic_security_priority,
                "religious_salience": wv.religious_salience,
                "political_profile": {
                    "country": pp.country if pp else None,
                    "archetype": pp.archetype if pp else None,
                    "description": pp.description if pp and hasattr(pp, "description") else None,
                } if pp else None,
                "political_era": wv.political_era if hasattr(wv, "political_era") else None,
            }

        persona_id = f"pg-{domain[:2]}-{i + 1:03d}"

        personas.append({
            "persona_id": persona_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "generator_version": "local-pool-v2",
            "domain": domain,
            "mode": "DELIVER",
            "demographic_anchor": {
                "name": da.name,
                "age": da.age,
                "gender": da.gender,
                "education": da.education,
                "employment": da.employment,
                "life_stage": da.life_stage,
                "location": {
                    "country": loc.country if loc else None,
                    "region": loc.region if loc else None,
                    "city": loc.city if loc else None,
                    "urban_tier": loc.urban_tier if loc else None,
                },
                "household": {
                    "structure": hh.structure if hh else None,
                    "size": hh.size if hh else None,
                    "income_bracket": hh.income_bracket if hh else None,
                    "dual_income": hh.dual_income if hh else None,
                },
                "worldview": wv_dict,
            },
            "attributes": {},
            "narrative": {
                "display_name": da.name,
                "first_person": f"I am {da.name}, a {da.age}-year-old from {loc.city if loc else 'unknown'}.",
            },
        })

    cohort_data = {
        "cohort_id": cohort_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "domain": domain,
        "client": "Simulatte Credibility",
        "mode": "DELIVER",
        "count_delivered": len(personas),
        "cohort_summary": f"Local pool generation — {len(personas)} personas for {domain}",
        "personas": personas,
    }

    out_path = output_dir / f"{cohort_id}.json"
    out_path.write_text(json.dumps(cohort_data, indent=2, ensure_ascii=False))
    return out_path


if __name__ == "__main__":
    for domain, output_dir in COUNTRIES.items():
        print(f"Generating {domain}...", end=" ", flush=True)
        out_path = build_cohort(domain, output_dir)
        print(f"✓ → {out_path.name}")

    print("\nAll 7 cohorts generated locally.")
