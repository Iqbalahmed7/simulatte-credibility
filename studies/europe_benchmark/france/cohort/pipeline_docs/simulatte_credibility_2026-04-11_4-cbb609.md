# Simulatte Pipeline Note — Simulatte Credibility

**Run ID:** `pg-simulatte-credibility-20260411-1934-cbb609`  
**Generated:** 2026-04-11 19:38 UTC  
**Status:** ⚠️ Review required  

## Brief

| Field | Value |
|---|---|
| Client | Simulatte Credibility |
| Domain | france_general |
| Business Problem | Replicate Pew Spring 2024 France opinion distributions across validated survey questions covering economic conditions, democracy satisfaction, views on Russia, EU, NATO, China, Trump, religion importance, economic reform preferences, income inequality, and French party favourability (RN, Renaissance/Macron, LFI, LR, PS). Cohort must represent the French adult public: urban/rural, full political spectrum from RN to LFI, calibrated to Pew Spring 2024 toplines (N=1,002). |
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

**Wall-clock time:** 4.5 min

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
**Distinctiveness score:** 0.1572008779626611
**Grounding state:** ungrounded

## Cohort Summary


### Decision Style Distribution

| Style | Share |
|---|---|
| analytical | 2400% |
| habitual | 1300% |
| emotional | 100% |
| social | 200% |

### Trust Anchor Distribution

| Anchor | Share |
|---|---|
| self | 2400% |
| family | 1300% |
| peer | 300% |

## Persona Index (40 personas)

| ID | Name | Age | Location | Decision Style |
|---|---|---|---|---|
| `pg-fr-016` | Henri Lapointe | 62 | {'country': 'France', 'region': 'Bretagne', 'city': 'Brest', 'urban_tier': 'metro'} | analytical |
| `pg-fr-056` | Henri Lapointe | 62 | {'country': 'France', 'region': 'Bretagne', 'city': 'Brest', 'urban_tier': 'metro'} | analytical |
| `pg-fr-076` | Henri Lapointe | 62 | {'country': 'France', 'region': 'Bretagne', 'city': 'Brest', 'urban_tier': 'metro'} | analytical |
| `pg-fr-060` | Michel Gautier | 68 | {'country': 'France', 'region': 'Occitanie', 'city': 'Montpellier', 'urban_tier': 'metro'} | habitual |
| `pg-fr-035` | Isabelle Perrin | 38 | {'country': 'France', 'region': 'Occitanie', 'city': 'Toulouse', 'urban_tier': 'metro'} | analytical |
| `pg-fr-075` | Isabelle Perrin | 38 | {'country': 'France', 'region': 'Occitanie', 'city': 'Toulouse', 'urban_tier': 'metro'} | analytical |
| `pg-fr-055` | Isabelle Perrin | 38 | {'country': 'France', 'region': 'Occitanie', 'city': 'Toulouse', 'urban_tier': 'metro'} | analytical |
| `pg-fr-015` | Isabelle Perrin | 38 | {'country': 'France', 'region': 'Occitanie', 'city': 'Toulouse', 'urban_tier': 'metro'} | analytical |
| `pg-fr-013` | Claire Lefebvre | 42 | {'country': 'France', 'region': 'Île-de-France', 'city': 'Paris', 'urban_tier': 'metro'} | analytical |
| `pg-fr-033` | Claire Lefebvre | 42 | {'country': 'France', 'region': 'Île-de-France', 'city': 'Paris', 'urban_tier': 'metro'} | analytical |
| `pg-fr-073` | Claire Lefebvre | 42 | {'country': 'France', 'region': 'Île-de-France', 'city': 'Paris', 'urban_tier': 'metro'} | analytical |
| `pg-fr-040` | Michel Gautier | 68 | {'country': 'France', 'region': 'Occitanie', 'city': 'Montpellier', 'urban_tier': 'metro'} | analytical |
| `pg-fr-080` | Michel Gautier | 68 | {'country': 'France', 'region': 'Occitanie', 'city': 'Montpellier', 'urban_tier': 'metro'} | analytical |
| `pg-fr-036` | Henri Lapointe | 62 | {'country': 'France', 'region': 'Bretagne', 'city': 'Brest', 'urban_tier': 'metro'} | analytical |
| `pg-fr-022` | Martine Lebrun | 47 | {'country': 'France', 'region': 'Hauts-de-France', 'city': 'Calais', 'urban_tier': 'tier2'} | habitual |
| `pg-fr-062` | Martine Lebrun | 47 | {'country': 'France', 'region': 'Hauts-de-France', 'city': 'Calais', 'urban_tier': 'tier2'} | habitual |
| `pg-fr-042` | Martine Lebrun | 47 | {'country': 'France', 'region': 'Hauts-de-France', 'city': 'Calais', 'urban_tier': 'tier2'} | habitual |
| `pg-fr-002` | Martine Lebrun | 47 | {'country': 'France', 'region': 'Hauts-de-France', 'city': 'Calais', 'urban_tier': 'tier2'} | habitual |
| `pg-fr-058` | Rachid Boudiaf | 39 | {'country': 'France', 'region': "Provence-Alpes-Côte d'Azur", 'city': 'Marseille', 'urban_tier': 'metro'} | emotional |
| `pg-fr-001` | Jean-Pierre Durand | 54 | {'country': 'France', 'region': "Provence-Alpes-Côte d'Azur", 'city': 'Toulon', 'urban_tier': 'metro'} | habitual |
| `pg-fr-064` | Brigitte Moreau | 51 | {'country': 'France', 'region': 'Normandie', 'city': 'Rouen', 'urban_tier': 'metro'} | habitual |
| `pg-fr-024` | Brigitte Moreau | 51 | {'country': 'France', 'region': 'Normandie', 'city': 'Rouen', 'urban_tier': 'metro'} | habitual |
| `pg-fr-045` | Pascal Renard | 43 | {'country': 'France', 'region': 'Grand Est', 'city': 'Metz', 'urban_tier': 'tier2'} | habitual |
| `pg-fr-005` | Pascal Renard | 43 | {'country': 'France', 'region': 'Grand Est', 'city': 'Metz', 'urban_tier': 'tier2'} | habitual |
| `pg-fr-065` | Pascal Renard | 43 | {'country': 'France', 'region': 'Grand Est', 'city': 'Metz', 'urban_tier': 'tier2'} | analytical |
| `pg-fr-074` | Luc Mercier | 50 | {'country': 'France', 'region': 'Bretagne', 'city': 'Rennes', 'urban_tier': 'metro'} | analytical |
| `pg-fr-054` | Luc Mercier | 50 | {'country': 'France', 'region': 'Bretagne', 'city': 'Rennes', 'urban_tier': 'metro'} | analytical |
| `pg-fr-034` | Luc Mercier | 50 | {'country': 'France', 'region': 'Bretagne', 'city': 'Rennes', 'urban_tier': 'metro'} | analytical |
| `pg-fr-059` | Sophie Lacroix | 31 | {'country': 'France', 'region': 'Auvergne-Rhône-Alpes', 'city': 'Grenoble', 'urban_tier': 'metro'} | analytical |
| `pg-fr-014` | Luc Mercier | 50 | {'country': 'France', 'region': 'Bretagne', 'city': 'Rennes', 'urban_tier': 'metro'} | analytical |
| `pg-fr-017` | Valérie Morin | 55 | {'country': 'France', 'region': 'Centre-Val de Loire', 'city': 'Tours', 'urban_tier': 'tier2'} | habitual |
| `pg-fr-037` | Valérie Morin | 55 | {'country': 'France', 'region': 'Centre-Val de Loire', 'city': 'Tours', 'urban_tier': 'tier2'} | habitual |
| `pg-fr-071` | Amina Bouzid | 24 | {'country': 'France', 'region': 'Île-de-France', 'city': 'Saint-Denis', 'urban_tier': 'metro'} | social |
| `pg-fr-011` | Amina Bouzid | 24 | {'country': 'France', 'region': 'Île-de-France', 'city': 'Saint-Denis', 'urban_tier': 'metro'} | social |
| `pg-fr-051` | Amina Bouzid | 24 | {'country': 'France', 'region': 'Île-de-France', 'city': 'Saint-Denis', 'urban_tier': 'metro'} | analytical |
| `pg-fr-053` | Claire Lefebvre | 42 | {'country': 'France', 'region': 'Île-de-France', 'city': 'Paris', 'urban_tier': 'metro'} | analytical |
| `pg-fr-020` | Michel Gautier | 68 | {'country': 'France', 'region': 'Occitanie', 'city': 'Montpellier', 'urban_tier': 'metro'} | habitual |
| `pg-fr-027` | Émilie Dubois | 35 | {'country': 'France', 'region': 'Île-de-France', 'city': 'Paris', 'urban_tier': 'metro'} | analytical |
| `pg-fr-067` | Émilie Dubois | 35 | {'country': 'France', 'region': 'Île-de-France', 'city': 'Paris', 'urban_tier': 'metro'} | analytical |
| `pg-fr-007` | Émilie Dubois | 35 | {'country': 'France', 'region': 'Île-de-France', 'city': 'Paris', 'urban_tier': 'metro'} | analytical |

---

**Cohort file:** `/Users/admin/Documents/Simulatte Projects/Simulatte Credibility/studies/europe_benchmark/france/cohort/cohort-france_general-cbb609.json`

---
*Generated by Simulatte Persona Orchestrator · pg-simulatte-credibility-20260411-1934-cbb609*
