# Simulatte Pipeline Note — Simulatte Credibility

**Run ID:** `pg-simulatte-credibility-20260411-1930-e0a7c3`  
**Generated:** 2026-04-11 19:32 UTC  
**Status:** ⚠️ Review required  

## Brief

| Field | Value |
|---|---|
| Client | Simulatte Credibility |
| Domain | uk_general |
| Business Problem | Replicate Pew Spring 2024 UK opinion distributions across validated survey questions covering economic conditions, democracy satisfaction, views on Russia, EU, NATO, China, Trump, religion importance, economic reform preferences, income inequality, and UK party favourability (Conservative, Labour, Lib Dems, Reform UK). Cohort must represent the British adult public: England/Scotland/Wales, urban/rural split, full political spectrum from Reform UK to Labour/SNP, calibrated to Pew Spring 2024 toplines (N=1,017). |
| Count | 40 |
| Run Intent | deliver |
| Mode | deep |
| Sarvam Enabled | False |

## Tier & Model Routing

| Stage | Model |
|---|---|
| Tier Used | DEEP |
| Generation (all tiers) | claude-sonnet-4-6 |
| Perceive | claude-haiku-4-5-20251001 |
| Reflect | claude-sonnet-4-6 |
| Decide | claude-sonnet-4-6 |

## Cost Breakdown

| Phase | Estimated | Actual |
|---|---|---|
| Pre-generation | $0.00 | $0.00 |
| Generation | $4.62 | $4.62 |
| Simulation | $0.00 | $0.00 |
| **Total** | **$4.62** | **$4.62** |
| Per Persona | $0.116 | $0.116 |

**Wall-clock time:** 2.6 min

## Quality Gates

| Gate | Result |
|---|---|
| G11-CalibrationState | ✅ Passed |
| G1-AttributeCoherence | ✅ Passed |
| G2-NarrativeConsistency | ✅ Passed |
| G3-MemoryValidity | ✅ Passed |
| G6-Diversity | ❌ Failed |
| G7-Distinctiveness | ❌ Failed |

**Personas quarantined:** 0
**Personas regenerated:** 0
**Distinctiveness score:** 0.1777053427226302
**Grounding state:** ungrounded

## Cohort Summary


### Decision Style Distribution

| Style | Share |
|---|---|
| analytical | 2300% |
| habitual | 1200% |
| social | 400% |
| emotional | 100% |

### Trust Anchor Distribution

| Anchor | Share |
|---|---|
| peer | 2300% |
| self | 1100% |
| family | 600% |

## Persona Index (40 personas)

| ID | Name | Age | Location | Decision Style |
|---|---|---|---|---|
| `pg-uk-011` | James Patel | 38 | {'country': 'United Kingdom', 'region': 'England', 'city': 'Birmingham', 'urban_tier': 'metro'} | analytical |
| `pg-uk-031` | James Patel | 38 | {'country': 'United Kingdom', 'region': 'England', 'city': 'Birmingham', 'urban_tier': 'metro'} | analytical |
| `pg-uk-071` | James Patel | 38 | {'country': 'United Kingdom', 'region': 'England', 'city': 'Birmingham', 'urban_tier': 'metro'} | analytical |
| `pg-uk-051` | James Patel | 38 | {'country': 'United Kingdom', 'region': 'England', 'city': 'Birmingham', 'urban_tier': 'metro'} | analytical |
| `pg-uk-013` | Marcus Thompson | 46 | {'country': 'United Kingdom', 'region': 'England', 'city': 'Leeds', 'urban_tier': 'metro'} | habitual |
| `pg-uk-033` | Marcus Thompson | 46 | {'country': 'United Kingdom', 'region': 'England', 'city': 'Leeds', 'urban_tier': 'metro'} | analytical |
| `pg-uk-070` | Rebecca Hughes | 41 | {'country': 'United Kingdom', 'region': 'Wales', 'city': 'Cardiff', 'urban_tier': 'metro'} | habitual |
| `pg-uk-030` | Rebecca Hughes | 41 | {'country': 'United Kingdom', 'region': 'Wales', 'city': 'Cardiff', 'urban_tier': 'metro'} | analytical |
| `pg-uk-050` | Rebecca Hughes | 41 | {'country': 'United Kingdom', 'region': 'Wales', 'city': 'Cardiff', 'urban_tier': 'metro'} | social |
| `pg-uk-010` | Rebecca Hughes | 41 | {'country': 'United Kingdom', 'region': 'Wales', 'city': 'Cardiff', 'urban_tier': 'metro'} | analytical |
| `pg-uk-073` | Marcus Thompson | 46 | {'country': 'United Kingdom', 'region': 'England', 'city': 'Leeds', 'urban_tier': 'metro'} | habitual |
| `pg-uk-053` | Marcus Thompson | 46 | {'country': 'United Kingdom', 'region': 'England', 'city': 'Leeds', 'urban_tier': 'metro'} | emotional |
| `pg-uk-079` | Peter Grant | 50 | {'country': 'United Kingdom', 'region': 'England', 'city': 'Norwich', 'urban_tier': 'tier2'} | analytical |
| `pg-uk-009` | Daniel Okafor | 29 | {'country': 'United Kingdom', 'region': 'England', 'city': 'London', 'urban_tier': 'metro'} | analytical |
| `pg-uk-069` | Daniel Okafor | 29 | {'country': 'United Kingdom', 'region': 'England', 'city': 'London', 'urban_tier': 'metro'} | analytical |
| `pg-uk-049` | Daniel Okafor | 29 | {'country': 'United Kingdom', 'region': 'England', 'city': 'London', 'urban_tier': 'metro'} | analytical |
| `pg-uk-057` | Callum MacLeod | 36 | {'country': 'United Kingdom', 'region': 'Scotland', 'city': 'Glasgow', 'urban_tier': 'metro'} | analytical |
| `pg-uk-040` | Helen Foster | 59 | {'country': 'United Kingdom', 'region': 'England', 'city': 'Liverpool', 'urban_tier': 'metro'} | habitual |
| `pg-uk-032` | Aisha Rahman | 26 | {'country': 'United Kingdom', 'region': 'England', 'city': 'Bradford', 'urban_tier': 'metro'} | social |
| `pg-uk-012` | Aisha Rahman | 26 | {'country': 'United Kingdom', 'region': 'England', 'city': 'Bradford', 'urban_tier': 'metro'} | social |
| `pg-uk-058` | Sioned Williams | 28 | {'country': 'United Kingdom', 'region': 'Wales', 'city': 'Swansea', 'urban_tier': 'tier2'} | analytical |
| `pg-uk-018` | Sioned Williams | 28 | {'country': 'United Kingdom', 'region': 'Wales', 'city': 'Swansea', 'urban_tier': 'tier2'} | analytical |
| `pg-uk-038` | Sioned Williams | 28 | {'country': 'United Kingdom', 'region': 'Wales', 'city': 'Swansea', 'urban_tier': 'tier2'} | analytical |
| `pg-uk-020` | Helen Foster | 59 | {'country': 'United Kingdom', 'region': 'England', 'city': 'Liverpool', 'urban_tier': 'metro'} | habitual |
| `pg-uk-060` | Helen Foster | 59 | {'country': 'United Kingdom', 'region': 'England', 'city': 'Liverpool', 'urban_tier': 'metro'} | habitual |
| `pg-uk-080` | Helen Foster | 59 | {'country': 'United Kingdom', 'region': 'England', 'city': 'Liverpool', 'urban_tier': 'metro'} | habitual |
| `pg-uk-039` | Peter Grant | 50 | {'country': 'United Kingdom', 'region': 'England', 'city': 'Norwich', 'urban_tier': 'tier2'} | analytical |
| `pg-uk-019` | Peter Grant | 50 | {'country': 'United Kingdom', 'region': 'England', 'city': 'Norwich', 'urban_tier': 'tier2'} | analytical |
| `pg-uk-059` | Peter Grant | 50 | {'country': 'United Kingdom', 'region': 'England', 'city': 'Norwich', 'urban_tier': 'tier2'} | habitual |
| `pg-uk-075` | Charlotte Webb | 33 | {'country': 'United Kingdom', 'region': 'England', 'city': 'Bristol', 'urban_tier': 'metro'} | analytical |
| `pg-uk-055` | Charlotte Webb | 33 | {'country': 'United Kingdom', 'region': 'England', 'city': 'Bristol', 'urban_tier': 'metro'} | analytical |
| `pg-uk-015` | Charlotte Webb | 33 | {'country': 'United Kingdom', 'region': 'England', 'city': 'Bristol', 'urban_tier': 'metro'} | analytical |
| `pg-uk-042` | Sandra Briggs | 44 | {'country': 'United Kingdom', 'region': 'England', 'city': 'Grimsby', 'urban_tier': 'tier2'} | habitual |
| `pg-uk-062` | Sandra Briggs | 44 | {'country': 'United Kingdom', 'region': 'England', 'city': 'Grimsby', 'urban_tier': 'tier2'} | social |
| `pg-uk-022` | Sandra Briggs | 44 | {'country': 'United Kingdom', 'region': 'England', 'city': 'Grimsby', 'urban_tier': 'tier2'} | habitual |
| `pg-uk-065` | Robert Simmons | 55 | {'country': 'United Kingdom', 'region': 'England', 'city': 'Maidstone', 'urban_tier': 'tier2'} | analytical |
| `pg-uk-045` | Robert Simmons | 55 | {'country': 'United Kingdom', 'region': 'England', 'city': 'Maidstone', 'urban_tier': 'tier2'} | analytical |
| `pg-uk-005` | Robert Simmons | 55 | {'country': 'United Kingdom', 'region': 'England', 'city': 'Maidstone', 'urban_tier': 'tier2'} | analytical |
| `pg-uk-026` | Patricia Dawson | 63 | {'country': 'United Kingdom', 'region': 'England', 'city': 'York', 'urban_tier': 'tier2'} | habitual |
| `pg-uk-066` | Patricia Dawson | 63 | {'country': 'United Kingdom', 'region': 'England', 'city': 'York', 'urban_tier': 'tier2'} | habitual |

---

**Cohort file:** `/Users/admin/Documents/Simulatte Projects/Simulatte Credibility/studies/europe_benchmark/uk/cohort/cohort-uk_general-e0a7c3.json`

---
*Generated by Simulatte Persona Orchestrator · pg-simulatte-credibility-20260411-1930-e0a7c3*
