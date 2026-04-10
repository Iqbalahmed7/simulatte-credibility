# Study 1C — Data Acquisition and Ground Truth Guide

This document describes how to download the source survey data and compute ground truth distributions for the 15 questions in `questions.json`.

## Sources Required

| Source | File to download | Germany N | Free? |
|---|---|---|---|
| Pew Global Attitudes Spring 2024 | `Spring_2024_Global_Attitudes_Dataset.sav` | ~1,000 | Yes — pewresearch.org/datasets |
| Pew Western Europe Survey 2017 | `Pew-Research-Center-Western-Europe-Survey-Dataset.sav` | ~1,600 | Yes — pewresearch.org/datasets |
| ESS Round 11 (2023/24) | `ESS11.sav` | ~2,400 | Yes — europeansocialsurvey.org/data-portal |
| German Census 2022 | Zensus 2022 summary tables | — | Yes — destatis.de |

---

## Step 1 — Pew Global Attitudes Spring 2024

### Download

1. Go to: https://www.pewresearch.org/global/datasets/
2. Find "Spring 2024 Global Attitudes Survey"
3. Register (free academic account) and download the SPSS `.sav` file
4. Place at: `data/raw/pew_global_2024.sav`

### Extract Germany rows

```python
import pandas as pd

df = pd.read_spss("data/raw/pew_global_2024.sav")

# Filter to Germany respondents only
de = df[df["COUNTRY"] == "Germany"]   # or equivalent ISO code — check codebook
print(f"Germany N: {len(de)}")
```

### Questions from this source

| Question ID | Pew variable name | Notes |
|---|---|---|
| de01 | `ECON_SIT` or `ECONOMY_*` | Economic conditions |
| de02 | `SCHOLZ_FAV` or `LEADER_FAV` | Chancellor approval |
| de03 | `DEMSAT` | Democracy satisfaction |
| de04 | `EU_FAV` | EU favorability |
| de05 | `CHINA_FAV` | China favorability |
| de10 | `CLIMATE_THREAT` | Climate seriousness |
| de13 | `CHILDREN_FINANCES` or `FUTURE_GEN` | Future generations |
| de14 | `CONF_PARL` or `CONF_BUNDESTAG` | Bundestag confidence |

> **Note:** Exact variable names must be verified against the codebook (included in the download). Pew renames variables between survey years.

### Compute ground truth distribution

```python
def compute_distribution(series, value_labels=None):
    """Compute proportions excluding DK/Refused."""
    counts = series.value_counts(dropna=False)
    # Identify DK/Refused codes (typically 8, 9, 98, 99)
    dk_codes = [c for c in counts.index if str(c) in ["8","9","98","99","DK","Refused"]]
    valid = counts.drop(index=dk_codes, errors="ignore")
    total_valid = valid.sum()
    total_all   = counts.sum()
    dk_pct = 1.0 - total_valid / total_all
    dist = (valid / total_valid).round(4).to_dict()
    dist["DK"] = round(dk_pct, 4)
    return dist

# Example for de01 (economic conditions)
dist_de01 = compute_distribution(de["ECON_SIT"])
print(dist_de01)  # Should match: {"A":0.03,"B":0.13,"C":0.43,"D":0.40,"DK":0.01}
```

---

## Step 2 — Pew Western Europe Survey 2017

### Download

1. Go to: https://www.pewresearch.org/global/datasets/
2. Find "Western Europe Survey 2017"
3. Download the SPSS `.sav` file
4. Place at: `data/raw/pew_western_europe_2017.sav`

### Extract Germany rows

```python
df_we = pd.read_spss("data/raw/pew_western_europe_2017.sav")
de_we = df_we[df_we["COUNTRY"] == "Germany"]   # check codebook for exact country code
print(f"Germany N (WE 2017): {len(de_we)}")
```

### Questions from this source

| Question ID | Pew variable name (approximate) | Notes |
|---|---|---|
| de06 | `IMMIG_ECON` or `IMMIG_JOBS` | Immigration impact on jobs |
| de07 | `IMMIG_CRIME` | Immigration impact on crime |
| de08 | `STRONG_LEADER` | Strong leader question |
| de09 | `RELIG_IMP` | Religion importance |
| de11 | `NATIONAL_PRIDE` | National pride |
| de12 | `WOMEN_RIGHTS` | Women equal rights |
| de15 | `IMMIG_DISTINCT` | Immigration cultural identity |

### Cross-validate with ESS Round 11

For each question, compare Pew 2017 distribution against ESS Round 11 (2023/24) equivalent. If drift > 5pp, use the ESS number as ground truth and note the discrepancy.

---

## Step 3 — ESS Round 11 (Cross-validation)

### Download

1. Go to: https://www.europeansocialsurvey.org/data-portal
2. Select "ESS Round 11 - 2023/24"
3. Select country: Germany
4. Download SPSS or CSV
5. Place at: `data/raw/ess_round11_germany.sav`

### Key variables for cross-validation

| ESS variable | Maps to | Notes |
|---|---|---|
| `stfdem` | de03 (democracy satisfaction) | Scale 0–10, binarise: 0-4=dissatisfied, 7-10=satisfied |
| `trstprl` | de14 (Bundestag confidence) | Scale 0–10 |
| `imbgeco` | de06 (immigration economy) | Scale 0–10, 0=bad, 10=good |
| `imwbcnt` | de15 (immigration cultural) | Scale 0–10 |
| `rlgdgr` | de09 (religion importance) | Scale 0–10 |
| `ipcrtiv` | Future orientation proxy | — |

### Compute East/West splits

```python
# ESS includes region variable — use to compute East vs West distributions
# East Germany: former GDR states (Sachsen, Thüringen, Brandenburg, Sachsen-Anhalt, Mecklenburg-Vorpommern, East Berlin)

east_states = ["Sachsen", "Thüringen", "Brandenburg", "Sachsen-Anhalt", "Mecklenburg-Vorpommern"]
de_east = ess[ess["region"].isin(east_states)]
de_west = ess[~ess["region"].isin(east_states)]

# Compute institutional trust gap
trust_east = de_east["trstprl"].mean()
trust_west = de_west["trstprl"].mean()
print(f"Trust gap (West - East): {trust_west - trust_east:.1f} points")
# Target: 1.5–2.0 points on 0–10 scale (~15–20pp in DA terms)
```

---

## Step 4 — Update questions.json with Verified Distributions

After downloading and processing, compare computed distributions to the pre-filled values in `questions.json`.

```python
import json

with open("../questions.json") as f:
    questions = json.load(f)

# Example verification for de03 (democracy satisfaction)
q = next(q for q in questions if q["id"] == "de03")
pre_filled = q["pew_distribution"]
computed   = compute_distribution(de_pew["DEMSAT"])

# Check for large discrepancies
for opt in pre_filled:
    diff = abs(pre_filled.get(opt, 0) - computed.get(opt, 0))
    if diff > 0.05:
        print(f"  de03 option {opt}: pre-filled={pre_filled[opt]:.0%}, computed={computed[opt]:.0%}, diff={diff:.0%} ⚠")
```

If discrepancies > 5pp are found, update `questions.json` with the computed values and add a note.

---

## Step 5 — Save Processed Data

```bash
mkdir -p data/processed

# Save clean Germany dataframes
python3 -c "
import pandas as pd
df = pd.read_spss('data/raw/pew_global_2024.sav')
de = df[df['COUNTRY'] == 'Germany']
de.to_csv('data/processed/pew_global_2024_germany.csv', index=False)
print(f'Saved {len(de)} Germany rows')
"
```

---

## Data Directory Structure

```
studies/pew_germany/
└── data/
    ├── raw/                        # Downloaded source files (not committed to git — see .gitignore)
    │   ├── pew_global_2024.sav
    │   ├── pew_western_europe_2017.sav
    │   └── ess_round11_germany.sav
    └── processed/                  # Derived clean files (committed)
        ├── pew_global_2024_germany.csv
        ├── pew_western_europe_2017_germany.csv
        ├── ess_round11_germany.csv
        └── ground_truth_verified.json  # Final verified distributions
```

> **Git note:** Raw `.sav` files should be listed in `.gitignore` (large binaries). Processed CSVs and verified JSON are committed.

---

## Verification Checklist

Before starting Sprint C-1:

- [ ] Germany N ≥ 900 for Pew Global Attitudes 2024
- [ ] Germany N ≥ 1,400 for Pew Western Europe 2017
- [ ] Germany N ≥ 2,000 for ESS Round 11
- [ ] All 15 questions have computed distributions
- [ ] ESS cross-validation complete — any drift > 5pp documented in question notes
- [ ] East/West institutional trust gap confirmed in ESS data (~15–20pp)
- [ ] `ground_truth_verified.json` written and matches `questions.json` distributions
- [ ] SHA-256 hash of `ground_truth_verified.json` recorded in `audit/audit_manifest.json`
