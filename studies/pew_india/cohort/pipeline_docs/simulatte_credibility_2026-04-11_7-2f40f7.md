# Simulatte Pipeline Note — Simulatte Credibility

**Run ID:** `pg-simulatte-credibility-20260411-1637-2f40f7`  
**Generated:** 2026-04-11 16:40 UTC  
**Status:** ⚠️ Review required  

## Brief

| Field | Value |
|---|---|
| Client | Simulatte Credibility |
| Domain | india_general |
| Business Problem | Replicate Pew India 2023–2024 opinion distributions across 15 validated survey questions covering democracy satisfaction, political party approval (BJP / INC / Modi), governance preferences, economic sentiment, national pride, religious identity, gender norms, and climate threat perception. Cohort must represent the Indian adult public: urban/rural split, North/South/East/West regions, Hindu majority with Muslim minority, full BJP-to-opposition political spectrum calibrated to Pew 2023 toplines. |
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

**Wall-clock time:** 2.9 min

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
**Distinctiveness score:** 0.10821990169050182
**Grounding state:** ungrounded

## Cohort Summary


### Decision Style Distribution

| Style | Share |
|---|---|
| analytical | 1700% |
| social | 400% |
| habitual | 900% |
| emotional | 1000% |

### Trust Anchor Distribution

| Anchor | Share |
|---|---|
| family | 3600% |
| peer | 300% |
| authority | 100% |

## Persona Index (40 personas)

| ID | Name | Age | Location | Decision Style |
|---|---|---|---|---|
| `pg-in-042` | Sunita Gupta | 35 | {'country': 'India', 'region': 'Delhi', 'city': 'New Delhi', 'urban_tier': 'metro'} | analytical |
| `pg-in-002` | Sunita Gupta | 35 | {'country': 'India', 'region': 'Delhi', 'city': 'New Delhi', 'urban_tier': 'metro'} | analytical |
| `pg-in-046` | Savitri Devi | 48 | {'country': 'India', 'region': 'Bihar', 'city': 'Patna', 'urban_tier': 'tier2'} | social |
| `pg-in-006` | Savitri Devi | 48 | {'country': 'India', 'region': 'Bihar', 'city': 'Patna', 'urban_tier': 'tier2'} | habitual |
| `pg-in-048` | Poonam Verma | 40 | {'country': 'India', 'region': 'Uttar Pradesh', 'city': 'Varanasi', 'urban_tier': 'tier2'} | habitual |
| `pg-in-008` | Poonam Verma | 40 | {'country': 'India', 'region': 'Uttar Pradesh', 'city': 'Varanasi', 'urban_tier': 'tier2'} | emotional |
| `pg-in-024` | Bhavna Desai | 46 | {'country': 'India', 'region': 'Gujarat', 'city': 'Surat', 'urban_tier': 'metro'} | emotional |
| `pg-in-064` | Bhavna Desai | 46 | {'country': 'India', 'region': 'Gujarat', 'city': 'Surat', 'urban_tier': 'metro'} | emotional |
| `pg-in-074` | Harjinder Kaur | 38 | {'country': 'India', 'region': 'Punjab', 'city': 'Chandigarh', 'urban_tier': 'metro'} | analytical |
| `pg-in-034` | Harjinder Kaur | 38 | {'country': 'India', 'region': 'Punjab', 'city': 'Chandigarh', 'urban_tier': 'metro'} | analytical |
| `pg-in-018` | Geetha Rani | 42 | {'country': 'India', 'region': 'Andhra Pradesh', 'city': 'Vijayawada', 'urban_tier': 'tier2'} | habitual |
| `pg-in-029` | Prasad Mishra | 44 | {'country': 'India', 'region': 'Odisha', 'city': 'Bhubaneswar', 'urban_tier': 'metro'} | emotional |
| `pg-in-069` | Prasad Mishra | 44 | {'country': 'India', 'region': 'Odisha', 'city': 'Bhubaneswar', 'urban_tier': 'metro'} | social |
| `pg-in-058` | Geetha Rani | 42 | {'country': 'India', 'region': 'Andhra Pradesh', 'city': 'Vijayawada', 'urban_tier': 'tier2'} | habitual |
| `pg-in-019` | Thomas Mathew | 48 | {'country': 'India', 'region': 'Kerala', 'city': 'Thiruvananthapuram', 'urban_tier': 'metro'} | analytical |
| `pg-in-059` | Thomas Mathew | 48 | {'country': 'India', 'region': 'Kerala', 'city': 'Thiruvananthapuram', 'urban_tier': 'metro'} | analytical |
| `pg-in-060` | Mary George | 35 | {'country': 'India', 'region': 'Goa', 'city': 'Panaji', 'urban_tier': 'metro'} | emotional |
| `pg-in-032` | Raju Bora | 34 | {'country': 'India', 'region': 'Assam', 'city': 'Guwahati', 'urban_tier': 'metro'} | emotional |
| `pg-in-020` | Mary George | 35 | {'country': 'India', 'region': 'Goa', 'city': 'Panaji', 'urban_tier': 'metro'} | analytical |
| `pg-in-045` | Ram Prasad Yadav | 55 | {'country': 'India', 'region': 'Uttar Pradesh', 'city': 'Gorakhpur', 'urban_tier': 'tier2'} | emotional |
| `pg-in-004` | Meera Agarwal | 28 | {'country': 'India', 'region': 'Rajasthan', 'city': 'Jaipur', 'urban_tier': 'metro'} | analytical |
| `pg-in-009` | Ramesh Chamar | 38 | {'country': 'India', 'region': 'Punjab', 'city': 'Ludhiana', 'urban_tier': 'metro'} | emotional |
| `pg-in-072` | Raju Bora | 34 | {'country': 'India', 'region': 'Assam', 'city': 'Guwahati', 'urban_tier': 'metro'} | analytical |
| `pg-in-044` | Meera Agarwal | 28 | {'country': 'India', 'region': 'Rajasthan', 'city': 'Jaipur', 'urban_tier': 'metro'} | analytical |
| `pg-in-035` | Arjun Mehta | 24 | {'country': 'India', 'region': 'Delhi', 'city': 'New Delhi', 'urban_tier': 'metro'} | social |
| `pg-in-075` | Arjun Mehta | 24 | {'country': 'India', 'region': 'Delhi', 'city': 'New Delhi', 'urban_tier': 'metro'} | analytical |
| `pg-in-056` | Priya Krishnamurthy | 29 | {'country': 'India', 'region': 'Karnataka', 'city': 'Bengaluru', 'urban_tier': 'metro'} | analytical |
| `pg-in-016` | Priya Krishnamurthy | 29 | {'country': 'India', 'region': 'Karnataka', 'city': 'Bengaluru', 'urban_tier': 'metro'} | analytical |
| `pg-in-021` | Amit Patel | 40 | {'country': 'India', 'region': 'Gujarat', 'city': 'Ahmedabad', 'urban_tier': 'metro'} | analytical |
| `pg-in-061` | Amit Patel | 40 | {'country': 'India', 'region': 'Gujarat', 'city': 'Ahmedabad', 'urban_tier': 'metro'} | analytical |
| `pg-in-050` | Kamla Devi | 52 | {'country': 'India', 'region': 'Uttar Pradesh', 'city': 'Agra', 'urban_tier': 'tier2'} | habitual |
| `pg-in-010` | Kamla Devi | 52 | {'country': 'India', 'region': 'Uttar Pradesh', 'city': 'Agra', 'urban_tier': 'tier2'} | habitual |
| `pg-in-071` | Abdul Karim | 70 | {'country': 'India', 'region': 'Kerala', 'city': 'Kozhikode', 'urban_tier': 'tier2'} | habitual |
| `pg-in-077` | Kabir Hussain | 26 | {'country': 'India', 'region': 'Karnataka', 'city': 'Bengaluru', 'urban_tier': 'metro'} | analytical |
| `pg-in-037` | Kabir Hussain | 26 | {'country': 'India', 'region': 'Karnataka', 'city': 'Bengaluru', 'urban_tier': 'metro'} | social |
| `pg-in-031` | Abdul Karim | 70 | {'country': 'India', 'region': 'Kerala', 'city': 'Kozhikode', 'urban_tier': 'tier2'} | habitual |
| `pg-in-015` | Suresh Reddy | 52 | {'country': 'India', 'region': 'Telangana', 'city': 'Hyderabad', 'urban_tier': 'metro'} | analytical |
| `pg-in-057` | Murugan Pillai | 60 | {'country': 'India', 'region': 'Tamil Nadu', 'city': 'Madurai', 'urban_tier': 'tier2'} | habitual |
| `pg-in-051` | Mohammad Iqbal | 44 | {'country': 'India', 'region': 'Uttar Pradesh', 'city': 'Lucknow', 'urban_tier': 'metro'} | emotional |
| `pg-in-011` | Mohammad Iqbal | 44 | {'country': 'India', 'region': 'Uttar Pradesh', 'city': 'Lucknow', 'urban_tier': 'metro'} | emotional |

---

**Cohort file:** `/Users/admin/Documents/Simulatte Projects/Simulatte Credibility/studies/pew_india/cohort/cohort-india_general-2f40f7.json`

---
*Generated by Simulatte Persona Orchestrator · pg-simulatte-credibility-20260411-1637-2f40f7*
