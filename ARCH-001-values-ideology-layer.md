# ARCH-001: Values & Ideology Layer
## Architectural Design for Opinion Research Validity

**Status:** Proposed
**Author:** Simulatte Credibility Research
**Date:** April 2026
**Triggered by:** Study 1A Pew Replication — distribution collapse finding

---

## 1. The Problem

Study 1A produced a critical diagnostic. On 13 of 15 Pew survey questions, Simulatte's 50-persona cohort collapsed to near-unanimous consensus on a single answer option. Example:

| Question | Simulatte | Real humans (Pew) |
|---|---|---|
| Economy rating | 96% "Only fair" | 41% Only fair / 41% Poor |
| Gun laws | 94% "More strict" | 59% more strict / 27% as-is / 14% less strict |
| Climate impact | 100% "Some" | 38% great deal / 34% some / 18% not much / 10% not at all |
| Democracy satisfaction | 98% "Not too satisfied" | 4% / 28% / 38% / 29% across 4 options |

**The one exception:** Q07 (government size) achieved 98.4% accuracy. This question is not driven by partisan identity — it is driven by general philosophical disposition, which the existing attribute set does capture reasonably.

**Root cause:** The persona generation pipeline is built for *consumer behaviour* diversity. It captures income, lifestyle, family structure, and purchasing psychology extremely well. But opinion survey responses are primarily driven by:

1. **Political lean** — the single biggest predictor of response variation on most Pew questions (~30-40% of variance explained by party ID alone)
2. **Values orientation** — individualism vs. collectivism, traditional vs. progressive worldview
3. **Institutional trust** — trust in government, media, science, religion (already partially in taxonomy but not prominent enough)

None of these are currently first-class dimensions in the persona generation pipeline.

---

## 2. What the Current Architecture Has

The base taxonomy has 191 attributes across 6 categories. The relevant existing attributes are:

**Relevant — but not sufficient:**
- `authority_trust` (social) — trust in institutions, default 0.5
- `civic_participation` (social) — engagement, default 0.4
- `primary_value_driver` (values, anchor) — price/quality/brand/convenience/relationships/status — **entirely consumer-oriented**
- `tension_seed` (identity, anchor) — aspiration_vs_constraint etc. — **entirely consumer-oriented**
- `tradition_vs_novelty` (values) — exists! But at default 0.5, not anchored

**What's missing entirely:**
- `political_lean` — no equivalent anywhere in the taxonomy
- `worldview_orientation` — individualist/collectivist/communitarian
- `institutional_trust_government` — distinct from authority_trust
- `institutional_trust_media` — distinct from authority_trust
- `institutional_trust_science` — distinct from authority_trust
- `economic_optimism` — general economic outlook
- `social_change_orientation` — pace of acceptable social change

**The core memory problem:**
`CoreMemory.key_values` is assembled from consumer-oriented value drivers. When `decide.py` builds its system prompt, the persona's identity statement and key_values contain nothing about political worldview or social values. So the LLM falls back to its own "average American" priors — which skew educated, moderate, and progressive (the training data bias). All 50 personas end up sounding like the same thoughtful moderate.

---

## 3. Proposed Architecture

### Layer 1: New `WorldviewAnchor` schema object

Add a `WorldviewAnchor` to `DemographicAnchor` (optional, defaults to None). This is a lightweight, schema-validated object that seeds the LLM's identity construction with values and political orientation.

```python
class WorldviewAnchor(BaseModel):
    political_lean: Literal["conservative", "lean_conservative", "moderate",
                             "lean_progressive", "progressive"]
    economic_philosophy: Literal["free_market", "mixed", "interventionist"]
    social_change_orientation: Literal["traditional", "moderate", "progressive"]
    institutional_trust_level: Literal["low", "medium", "high"]  # government/media/science
    primary_identity_salience: Literal["national", "religious", "ethnic",
                                        "class", "local", "none"]
```

This object sits alongside the existing `DemographicAnchor` and is passed into `AttributeFiller.fill()` as additional context. It does **not** replace existing attributes — it anchors them.

### Layer 2: Taxonomy additions to `base_taxonomy.py`

Add a `worldview` category (6 new attributes, all anchored):

| Attribute | Type | Description |
|---|---|---|
| `political_lean` | categorical | conservative / lean_conservative / moderate / lean_progressive / progressive |
| `economic_philosophy` | categorical | free_market / mixed / interventionist |
| `social_change_pace` | continuous | 0=traditional, 1=rapid change advocate |
| `institutional_trust_government` | continuous | trust in government specifically |
| `institutional_trust_media` | continuous | trust in news media specifically |
| `institutional_trust_science` | continuous | trust in scientific/expert consensus |

These 6 attributes are **anchor attributes** — filled first, before all others, because they have the highest downstream correlation effect on opinion survey responses.

**Correlation additions:**
- `political_lean=conservative` → `institutional_trust_government` low if current party not in power, `social_change_pace` low, `tradition_vs_novelty` low
- `political_lean=progressive` → `institutional_trust_science` high, `social_change_pace` high, `environmental_consciousness` high
- `institutional_trust_media=low` → `authority_trust` low, `online_community_trust` varies

### Layer 3: `CoreMemory` key_values propagation

Modify `assemble_core_memory()` to include worldview attributes in `key_values` when present:

- `political_lean` → "Holds [conservative/progressive] political values"
- `institutional_trust_government` < 0.3 → "Deep skepticism of government institutions"
- `institutional_trust_media` < 0.3 → "Mistrusts mainstream media"
- `social_change_pace` extremes → "Committed to preserving traditional values" or "Strongly advocates social change"

These propagate directly into the `decide.py` system prompt via `CoreMemory.key_values`, giving the LLM the worldview context it needs to respond differently to politically-charged questions.

### Layer 4: `demographic_sampler.py` — `us_general` pool update

The `us_general` pool should encode `political_lean` distributions matching real US demographics:

- ~35% conservative + lean_conservative
- ~25% moderate
- ~40% progressive + lean_progressive

(Matching Pew's 2023 party identification data: 28% Republican, 27% Democrat, 43% Independent — with independents split ~55% lean-R, 45% lean-D overall)

The 34-persona pool gets `political_lean` as an explicit field per persona, matching the above distribution.

### Layer 5: `us_general` ICP spec mode

Add a new `mode` value: `"opinion_research"` — a variant of `"quick"` that:
1. Requires `WorldviewAnchor` to be present in the demographic spec
2. Skips consumer-oriented domain taxonomy (CPG/SaaS attributes not relevant)
3. Weights worldview attributes as top-priority anchors
4. Seeds life stories with politically-relevant formative experiences

---

## 4. What This Does NOT Change

- Existing domains (cpg, saas, lofoods_fmcg etc.) are **unaffected** — `WorldviewAnchor` is optional and defaults to None
- Existing persona schema validation is **backward compatible** — new fields are Optional
- The `decide.py` cognitive loop is **unchanged** — worldview flows in via CoreMemory, not by modifying the reasoning chain
- LittleJoys, LoFoods, and all existing pilots **continue to work as before**

---

## 5. Implementation Plan

### Sprint A-1 (Schema + Taxonomy) — ~2 days
- [ ] Add `WorldviewAnchor` to `src/schema/persona.py`
- [ ] Add `worldview` category (6 attrs) to `src/taxonomy/base_taxonomy.py`
- [ ] Add correlations for worldview attributes to `KNOWN_CORRELATIONS`
- [ ] Update `DemographicAnchor` to include `worldview: WorldviewAnchor | None = None`

### Sprint A-2 (Generation + Memory) — ~2 days
- [ ] Update `AttributeFiller.fill()` to inject worldview as additional anchor context
- [ ] Update `assemble_core_memory()` to propagate worldview into `key_values`
- [ ] Update `demographic_sampler.py` `us_general` pool with `political_lean` per persona
- [ ] Add `"opinion_research"` mode to CLI + API

### Sprint A-3 (Validation + Study Rerun) — ~1 day
- [ ] Update Study 1A `run_study.py` to use `mode="opinion_research"`
- [ ] Generate new 50-persona `us_general` cohort with worldview anchors
- [ ] Rerun all 15 Pew questions
- [ ] Compare distribution accuracy before/after

### Expected outcome
Distribution accuracy should move from ~58% (current) to 75-85% range, based on the fact that adding party ID alone explains ~30-40% of variance on most Pew political/social questions. The remaining gap to Artificial Societies' 86% will come from further refinement of the worldview attribute correlations.

---

## 6. Longer-term Implications

Once this architecture is in place, Simulatte gains a capability that no competitor has published:

**Worldview-stratified simulation** — the ability to specify exact ideological composition of a synthetic population and test how a message/policy/product lands differently across the political spectrum. This is what comms teams, policy researchers, and strategists actually need.

Artificial Societies claims 86% accuracy but publishes no mechanism for controlling ideological composition. Simulatte's architecture makes this explicit and configurable.

---

## 7. Files to Modify

| File | Change |
|---|---|
| `src/schema/persona.py` | Add `WorldviewAnchor` class, add to `DemographicAnchor` |
| `src/taxonomy/base_taxonomy.py` | Add `worldview` category (6 attrs), add correlations |
| `src/generation/attribute_filler.py` | Inject worldview context into fill prompt |
| `src/memory/core_memory.py` | Propagate worldview into `key_values` |
| `src/generation/demographic_sampler.py` | Add `political_lean` to `us_general` pool entries |
| `src/cli.py` | Add `opinion_research` mode |
| `src/api/models.py` | Add `worldview_anchor` field to `GenerateRequest` |

**New files:**
| File | Purpose |
|---|---|
| `src/schema/worldview.py` | `WorldviewAnchor` schema (or inline in persona.py) |
| `src/taxonomy/domain_templates/opinion_research.py` | Empty domain template for opinion_research mode |

---

*This document is the canonical reference for ARCH-001. Implementation begins in Sprint A-1.*
