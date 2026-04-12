# Simulatte Pipeline Note — Simulatte Credibility

**Run ID:** `pg-simulatte-credibility-20260411-1914-cccadb`  
**Generated:** 2026-04-11 19:17 UTC  
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

**Wall-clock time:** 2.7 min

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
**Distinctiveness score:** 0.11170109648734643
**Grounding state:** ungrounded

## Cohort Summary


### Decision Style Distribution

| Style | Share |
|---|---|
| analytical | 3400% |
| social | 300% |
| habitual | 200% |
| emotional | 100% |

### Trust Anchor Distribution

| Anchor | Share |
|---|---|
| family | 2900% |
| peer | 100% |
| authority | 300% |
| self | 700% |

## Persona Index (40 personas)

| ID | Name | Age | Location | Decision Style |
|---|---|---|---|---|
| `pg-uk-065` | Deepa Nair | 31 | {'country': 'India', 'region': 'Kerala', 'city': 'Kochi', 'urban_tier': 'tier2'} | analytical |
| `pg-uk-036` | Arun Nambiar | 33 | {'country': 'India', 'region': 'Kerala', 'city': 'Thiruvananthapuram', 'urban_tier': 'tier2'} | analytical |
| `pg-uk-005` | Deepa Nair | 31 | {'country': 'India', 'region': 'Kerala', 'city': 'Kochi', 'urban_tier': 'tier2'} | analytical |
| `pg-uk-048` | Arun Nambiar | 33 | {'country': 'India', 'region': 'Kerala', 'city': 'Thiruvananthapuram', 'urban_tier': 'tier2'} | analytical |
| `pg-uk-012` | Arun Nambiar | 33 | {'country': 'India', 'region': 'Kerala', 'city': 'Thiruvananthapuram', 'urban_tier': 'tier2'} | analytical |
| `pg-uk-045` | Meena Krishnan | 36 | {'country': 'India', 'region': 'Tamil Nadu', 'city': 'Chennai', 'urban_tier': 'metro'} | analytical |
| `pg-uk-009` | Meena Krishnan | 36 | {'country': 'India', 'region': 'Tamil Nadu', 'city': 'Chennai', 'urban_tier': 'metro'} | analytical |
| `pg-uk-057` | Meena Krishnan | 36 | {'country': 'India', 'region': 'Tamil Nadu', 'city': 'Chennai', 'urban_tier': 'metro'} | analytical |
| `pg-uk-033` | Meena Krishnan | 36 | {'country': 'India', 'region': 'Tamil Nadu', 'city': 'Chennai', 'urban_tier': 'metro'} | analytical |
| `pg-uk-021` | Meena Krishnan | 36 | {'country': 'India', 'region': 'Tamil Nadu', 'city': 'Chennai', 'urban_tier': 'metro'} | analytical |
| `pg-uk-069` | Meena Krishnan | 36 | {'country': 'India', 'region': 'Tamil Nadu', 'city': 'Chennai', 'urban_tier': 'metro'} | analytical |
| `pg-uk-077` | Deepa Nair | 31 | {'country': 'India', 'region': 'Kerala', 'city': 'Kochi', 'urban_tier': 'tier2'} | analytical |
| `pg-uk-029` | Deepa Nair | 31 | {'country': 'India', 'region': 'Kerala', 'city': 'Kochi', 'urban_tier': 'tier2'} | social |
| `pg-uk-017` | Deepa Nair | 31 | {'country': 'India', 'region': 'Kerala', 'city': 'Kochi', 'urban_tier': 'tier2'} | social |
| `pg-uk-041` | Deepa Nair | 31 | {'country': 'India', 'region': 'Kerala', 'city': 'Kochi', 'urban_tier': 'tier2'} | analytical |
| `pg-uk-053` | Deepa Nair | 31 | {'country': 'India', 'region': 'Kerala', 'city': 'Kochi', 'urban_tier': 'tier2'} | analytical |
| `pg-uk-024` | Arun Nambiar | 33 | {'country': 'India', 'region': 'Kerala', 'city': 'Thiruvananthapuram', 'urban_tier': 'tier2'} | analytical |
| `pg-uk-051` | Sunita Devi | 45 | {'country': 'India', 'region': 'Uttar Pradesh', 'city': 'Lucknow', 'urban_tier': 'tier2'} | analytical |
| `pg-uk-055` | Ananya Roy | 25 | {'country': 'India', 'region': 'West Bengal', 'city': 'Kolkata', 'urban_tier': 'metro'} | analytical |
| `pg-uk-019` | Ananya Roy | 25 | {'country': 'India', 'region': 'West Bengal', 'city': 'Kolkata', 'urban_tier': 'metro'} | analytical |
| `pg-uk-042` | Vikram Singh | 52 | {'country': 'India', 'region': 'Rajasthan', 'city': 'Jaipur', 'urban_tier': 'tier2'} | habitual |
| `pg-uk-063` | Sunita Devi | 45 | {'country': 'India', 'region': 'Uttar Pradesh', 'city': 'Lucknow', 'urban_tier': 'tier2'} | habitual |
| `pg-uk-003` | Sunita Devi | 45 | {'country': 'India', 'region': 'Uttar Pradesh', 'city': 'Lucknow', 'urban_tier': 'tier2'} | emotional |
| `pg-uk-066` | Vikram Singh | 52 | {'country': 'India', 'region': 'Rajasthan', 'city': 'Jaipur', 'urban_tier': 'tier2'} | analytical |
| `pg-uk-050` | Rahul Verma | 28 | {'country': 'India', 'region': 'Karnataka', 'city': 'Bengaluru', 'urban_tier': 'metro'} | analytical |
| `pg-uk-030` | Vikram Singh | 52 | {'country': 'India', 'region': 'Rajasthan', 'city': 'Jaipur', 'urban_tier': 'tier2'} | analytical |
| `pg-uk-054` | Vikram Singh | 52 | {'country': 'India', 'region': 'Rajasthan', 'city': 'Jaipur', 'urban_tier': 'tier2'} | analytical |
| `pg-uk-056` | Suresh Patel | 41 | {'country': 'India', 'region': 'Gujarat', 'city': 'Ahmedabad', 'urban_tier': 'metro'} | analytical |
| `pg-uk-008` | Suresh Patel | 41 | {'country': 'India', 'region': 'Gujarat', 'city': 'Ahmedabad', 'urban_tier': 'metro'} | analytical |
| `pg-uk-044` | Suresh Patel | 41 | {'country': 'India', 'region': 'Gujarat', 'city': 'Ahmedabad', 'urban_tier': 'metro'} | analytical |
| `pg-uk-018` | Vikram Singh | 52 | {'country': 'India', 'region': 'Rajasthan', 'city': 'Jaipur', 'urban_tier': 'tier2'} | analytical |
| `pg-uk-032` | Suresh Patel | 41 | {'country': 'India', 'region': 'Gujarat', 'city': 'Ahmedabad', 'urban_tier': 'metro'} | analytical |
| `pg-uk-016` | Amit Sharma | 38 | {'country': 'India', 'region': 'Delhi', 'city': 'Delhi', 'urban_tier': 'metro'} | analytical |
| `pg-uk-052` | Amit Sharma | 38 | {'country': 'India', 'region': 'Delhi', 'city': 'Delhi', 'urban_tier': 'metro'} | analytical |
| `pg-uk-074` | Rahul Verma | 28 | {'country': 'India', 'region': 'Karnataka', 'city': 'Bengaluru', 'urban_tier': 'metro'} | analytical |
| `pg-uk-038` | Rahul Verma | 28 | {'country': 'India', 'region': 'Karnataka', 'city': 'Bengaluru', 'urban_tier': 'metro'} | analytical |
| `pg-uk-002` | Rahul Verma | 28 | {'country': 'India', 'region': 'Karnataka', 'city': 'Bengaluru', 'urban_tier': 'metro'} | analytical |
| `pg-uk-014` | Rahul Verma | 28 | {'country': 'India', 'region': 'Karnataka', 'city': 'Bengaluru', 'urban_tier': 'metro'} | analytical |
| `pg-uk-062` | Rahul Verma | 28 | {'country': 'India', 'region': 'Karnataka', 'city': 'Bengaluru', 'urban_tier': 'metro'} | analytical |
| `pg-uk-022` | Rohit Gupta | 29 | {'country': 'India', 'region': 'Madhya Pradesh', 'city': 'Bhopal', 'urban_tier': 'tier2'} | social |

---

**Cohort file:** `/Users/admin/Documents/Simulatte Projects/Simulatte Credibility/studies/europe_benchmark/uk/cohort/cohort-uk_general-cccadb.json`

---
*Generated by Simulatte Persona Orchestrator · pg-simulatte-credibility-20260411-1914-cccadb*
