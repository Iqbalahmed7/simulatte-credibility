# ARCH-001 Addendum: Geography-Aware Worldview Architecture
## Ensuring US-only enforcement today, global extensibility tomorrow

**Status:** Proposed
**Date:** April 2026
**Parent:** ARCH-001 — Values & Ideology Layer

---

## The Core Design Question

`WorldviewAnchor` as proposed in ARCH-001 contains US-specific concepts:
`political_lean: "conservative" | "lean_conservative" | "moderate" | "lean_progressive" | "progressive"`

These categories are **meaningless outside the US**. India's political landscape is structured around caste identity, religious nationalism, regional parties, and urban/rural divides — not a left/right spectrum. The UK's around Brexit identity and class. Brazil's around evangelical conservatism vs. PT-left. Applying US political categories to non-US personas would produce worse results than having no worldview at all.

The architecture needs to answer two questions simultaneously:
1. **Enforcement today:** How do we make `WorldviewAnchor` strictly US-only until we define other geographies?
2. **Extensibility tomorrow:** How do we add India, UK, etc. later without refactoring the whole system?

---

## The Answer: A Two-Level Architecture

### Level 1 — Universal Dimensions (geography-agnostic)
A small set of continuous attributes that are meaningful everywhere, regardless of country. These go into the base `WorldviewAnchor` and are always available.

### Level 2 — Geography-Specific Profiles (country-gated)
A registry of `PoliticalProfile` objects, one per supported country. Each defines its own categorical vocabulary (political archetypes, party families, identity cleavages). The registry gates which profiles are valid for a given `location.country`.

---

## Detailed Design

### The base `WorldviewAnchor` — universal fields only

```python
# src/schema/worldview.py

class WorldviewAnchor(BaseModel):
    """Geography-agnostic worldview dimensions.

    These 4 continuous attributes are valid for any country — they describe
    a person's relationship to institutions, change, and collective identity
    in terms that translate across political systems.

    Range: 0.0–1.0
    """
    institutional_trust: float     # 0=deep distrust of all institutions, 1=high trust
    social_change_pace: float      # 0=traditional/preservationist, 1=rapid change advocate
    collectivism_score: float      # 0=strong individualist, 1=strong collectivist
    economic_security_priority: float  # 0=freedom/growth priority, 1=security/equality priority

    # The geography-specific political profile.
    # None = worldview seeded with universal dimensions only.
    # Set by demographic_sampler based on location.country.
    political_profile: PoliticalProfile | None = None
```

### The `PoliticalProfile` — geography-specific, registry-controlled

```python
class PoliticalProfile(BaseModel):
    """Geography-specific political identity anchor.

    Each supported country defines its own vocabulary here.
    The 'country' field acts as the discriminator — the registry
    validates that the archetype belongs to the declared country.
    """
    country: str                   # ISO country code or name — must match location.country
    archetype: str                 # Validated against country registry (see below)
    description: str               # Human-readable label for this archetype

    @model_validator(mode="after")
    def _validate_archetype_for_country(self) -> "PoliticalProfile":
        registry = get_political_registry()
        valid = registry.get_archetypes(self.country)
        if valid is None:
            raise ValueError(
                f"Country '{self.country}' is not yet supported in the political registry. "
                f"Supported countries: {registry.supported_countries()}. "
                f"To add support, create a new entry in src/worldview/registry/."
            )
        if self.archetype not in valid:
            raise ValueError(
                f"Archetype '{self.archetype}' is not valid for country '{self.country}'. "
                f"Valid archetypes: {valid}"
            )
        return self
```

### The `PoliticalRegistry` — the extensibility mechanism

```python
# src/worldview/registry/__init__.py

class PoliticalRegistry:
    """
    Central registry of valid political archetypes per country.

    Adding a new geography = adding one file to src/worldview/registry/
    and registering it here. Nothing else changes.
    """
    _registry: dict[str, list[str]]  # country → valid archetype strings

    def get_archetypes(self, country: str) -> list[str] | None:
        return self._registry.get(country)

    def supported_countries(self) -> list[str]:
        return list(self._registry.keys())
```

### Country registry files — one per supported geography

```
src/worldview/registry/
    __init__.py          ← PoliticalRegistry, get_political_registry()
    us.py                ← US archetypes (launches with ARCH-001)
    india.py             ← India archetypes (future sprint)
    uk.py                ← UK archetypes (future sprint)
    germany.py           ← Germany archetypes (future sprint)
```

---

## US Registry (launches with ARCH-001)

```python
# src/worldview/registry/us.py

US_POLITICAL_ARCHETYPES = {
    # Core spectrum
    "conservative":        "Aligns with Republican Party values: limited government, "
                           "traditional social values, free-market economics, strong national security.",
    "lean_conservative":   "Centre-right independent: fiscally conservative, moderately "
                           "socially tolerant, sceptical of government expansion.",
    "moderate":            "True independent: case-by-case positions, rejects strong "
                           "partisan identity, values pragmatism over ideology.",
    "lean_progressive":    "Centre-left independent: supports safety net programs, "
                           "socially liberal, open to regulated markets.",
    "progressive":         "Aligns with Democratic Party's left wing: expansive government "
                           "role, systemic equity focus, climate action, wealth redistribution.",

    # Sub-archetypes for richer simulation (optional, used for high-fidelity cohorts)
    "religious_conservative":   "Evangelical or traditional Catholic conservative; "
                                "social issues (abortion, LGBTQ) are primary political drivers.",
    "fiscal_conservative":      "Libertarian-leaning: small government, low taxes, "
                                "but socially moderate or liberal.",
    "working_class_populist":   "Obama→Trump voter profile: economically left "
                                "(pro-union, anti-trade), culturally conservative.",
    "college_educated_liberal": "Professional-class progressive: urban, postgrad-educated, "
                                "high institutional trust in science and experts.",
    "non_voter_disengaged":     "Low political efficacy, doesn't identify with either party, "
                                "unlikely to engage with political content.",
}

# Distribution targets matching Pew 2023 party identification data
# Use these proportions when building a nationally representative US cohort
US_REPRESENTATIVE_DISTRIBUTION = {
    "conservative":          0.15,
    "lean_conservative":     0.20,
    "moderate":              0.25,
    "lean_progressive":      0.22,
    "progressive":           0.18,
}
```

---

## India Registry (future sprint — structure defined now)

```python
# src/worldview/registry/india.py  — STUB, not yet implemented

INDIA_POLITICAL_ARCHETYPES = {
    # India's political cleavages are NOT left/right.
    # Primary drivers: religious identity, caste, regional identity,
    # economic aspiration vs. welfare preference.

    "hindu_nationalist":      "BJP/RSS ideological alignment; Hindutva as primary identity...",
    "secular_centrist":       "Congress-aligned or non-BJP centrist; pluralist...",
    "dalit_rights_focus":     "BSP/Ambedkarite alignment; caste justice as primary...",
    "regional_identity":      "State/regional party loyalty dominates national party...",
    "aspirational_urban":     "Economic reformer; pro-business, anti-corruption...",
    "welfare_rural":          "SP/RJD/regional left alignment; agricultural policy...",

    # NOTE: India archetypes require deep localisation per state.
    # Maharashtra != UP != Tamil Nadu. State-level registry needed.
}
```

This stub makes the point: **India's political vocabulary is entirely different** and cannot reuse any of the US archetype strings. Attempting to map "conservative/progressive" onto Indian politics would produce nonsense. The registry architecture forces each country to define its own vocabulary from scratch.

---

## How geography enforcement works in practice

### At generation time — `demographic_sampler.py`

The sampler is responsible for attaching the correct `PoliticalProfile` to a `DemographicAnchor` based on `location.country`:

```python
def sample_demographic_anchor(domain, index, seed=None):
    ...
    anchor = DemographicAnchor(...)

    # Attach worldview only for supported countries, in opinion_research mode
    if domain == "us_general":
        profile_entry = _US_GENERAL_POOL[index % len(_US_GENERAL_POOL)]
        anchor.worldview = WorldviewAnchor(
            institutional_trust=profile_entry["institutional_trust"],
            social_change_pace=profile_entry["social_change_pace"],
            collectivism_score=profile_entry["collectivism_score"],
            economic_security_priority=profile_entry["economic_security_priority"],
            political_profile=PoliticalProfile(
                country="USA",
                archetype=profile_entry["political_lean"],
                description=US_POLITICAL_ARCHETYPES[profile_entry["political_lean"]],
            )
        )
    # India, UK etc.: no WorldviewAnchor attached until their registry is built
    # cpg, saas, lofoods_fmcg: no WorldviewAnchor attached (not needed)

    return anchor
```

This means:
- US general population → `WorldviewAnchor` with `PoliticalProfile(country="USA")`
- India CPG personas → `WorldviewAnchor` is `None` (no political profile)
- SAAS personas (mixed countries) → `WorldviewAnchor` is `None`
- Any attempt to manually set `PoliticalProfile(country="India", archetype="conservative")` → **raises `ValueError` at schema validation** because India isn't in the registry yet

### At `AttributeFiller` time — country is visible

`demographic_anchor.location.country` is already passed into `AttributeFiller._demographics_to_profile()`. The filler prompt currently only includes urban_tier, not country. This should be extended to include country and worldview anchor:

```python
demogs = {
    "age": demographic_anchor.age,
    "gender": demographic_anchor.gender,
    "country": demographic_anchor.location.country,        # ADD
    "location_urban_tier": demographic_anchor.location.urban_tier,
    "income_bracket": demographic_anchor.household.income_bracket,
    "life_stage": demographic_anchor.life_stage,
    "political_archetype": (                                # ADD (if present)
        demographic_anchor.worldview.political_profile.archetype
        if demographic_anchor.worldview and demographic_anchor.worldview.political_profile
        else None
    ),
}
```

---

## Extending to a new geography — what it takes

When we're ready to add India (or UK, Germany, Brazil etc.), the work is:

| Task | Effort |
|---|---|
| Create `src/worldview/registry/india.py` with `INDIA_POLITICAL_ARCHETYPES` dict | 1–2 days research + writing |
| Register `"India"` in `PoliticalRegistry.__init__` | 5 minutes |
| Add `political_lean` field to `_CPG_POOL` / `_LOFOODS_FMCG_POOL` entries in demographic_sampler | 1 day |
| Add universal worldview dimensions (institutional_trust etc.) to Indian pool entries | 1 day |
| Validation test: generate a 10-persona Indian cohort with worldview, verify no errors | 1 hour |
| Run equivalent study (CSDS/Lokniti survey data equivalent of Pew) | Separate research task |

**Total: ~3-4 days per new geography**, mostly research into that country's political landscape. The code changes are minimal once the registry pattern is in place.

---

## What changes vs. ARCH-001 original

| ARCH-001 original | This addendum |
|---|---|
| `WorldviewAnchor` has `political_lean: Literal["conservative", ...]` directly | `WorldviewAnchor` has universal continuous fields + optional `PoliticalProfile` |
| US political categories baked into the main schema | US categories live in `src/worldview/registry/us.py` only |
| Adding a new country = modifying the Literal type | Adding a new country = adding one new file to registry/ |
| No validation that political_lean matches location.country | `PoliticalProfile._validate_archetype_for_country()` enforces this at schema level |

---

## Summary

The two-level architecture answers both questions cleanly:

**US-only enforcement today:**
The `PoliticalRegistry` only has a `"USA"` entry at launch. Any attempt to attach a `PoliticalProfile` to a non-US persona raises a `ValueError` at schema validation time — before any LLM calls are made. The demographic_sampler only attaches `WorldviewAnchor` for `us_general` domain. All existing domains (cpg, saas, lofoods_fmcg) have no worldview attached — zero impact.

**Global extensibility tomorrow:**
Adding India = one new registry file + populating the existing Indian demographic pools with worldview dimensions. The schema, the filler, the core memory assembler, and the decide loop all work unchanged. The registry pattern means country-specific political vocabulary is **isolated, not baked in**.

*This addendum supersedes the `WorldviewAnchor` schema definition in ARCH-001. Sprint A-1 should implement this two-level structure from the start.*
