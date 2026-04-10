# Simulatte Europe Benchmark

**Status: In progress — calibration not yet run**

9 European countries · 15 questions per country · 40 personas per country · Pew Spring 2024 ground truth

Part of the [Simulatte Credibility Research Program](../../README.md). Ground truth, persona pools, and holdout questions established before any calibration run. All sprint results will be committed to this repository as they complete, maintaining continuous audit trail.

---

## Countries

| Country | N (Pew 2024) | Status | Calibrated DA | Holdout DA |
|---------|-------------|--------|---------------|------------|
| France | 1,018 | Pending | — | — |
| Greece | 1,015 | Pending | — | — |
| Hungary | 996 | Pending | — | — |
| Italy | 1,120 | Pending | — | — |
| Netherlands | 1,010 | Pending | — | — |
| Poland | 1,031 | Pending | — | — |
| Spain | 1,013 | Pending | — | — |
| Sweden | 1,017 | Pending | — | — |
| UK | 1,017 | Pending | — | — |

---

## Design

### Questions (15 calibration + holdout per country)

**10 shared calibration questions** (identical across all 9 countries — enables direct cross-country comparison):

| # | Variable | Topic |
|---|----------|-------|
| 1 | `econ_sit` | Economic conditions |
| 2 | `satisfied_democracy` | Democracy satisfaction |
| 3 | `fav_russia` | Russia view |
| 4 | `fav_eu` | EU view |
| 5 | `fav_nato` | NATO view |
| 6 | `fav_china` | China view |
| 7 | `confid_trump` | Trump confidence |
| 8 | `religion_import` | Religion importance |
| 9 | `econsys_reform` | Economic system reform |
| 10 | `prob_rich_poor` | Income inequality |

**5 country-specific calibration questions** (party favorability + domestic leader where applicable):

| Country | Country-specific questions |
|---------|--------------------------|
| France | RN, Renaissance (En Marche), LFI, Les Républicains, Macron confidence |
| Greece | New Democracy, SYRIZA, Greek Solution, Spartans, KKE |
| Hungary | Fidesz, MSZP, Jobbik, DK, children's future |
| Italy | Fratelli d'Italia, PD, Five Star, Lega, Forza Italia |
| Netherlands | VVD, PVV, D66, Labour (PvdA), NSC |
| Poland | PiS, PO, SLD, children's future, UN view |
| Spain | PP, PSOE, Podemos, Vox, children's future |
| Sweden | SAP, Moderate Party, Sweden Democrats, children's future, UN view |
| UK | Conservative, Labour, Lib Dems, Reform UK, children's future |

**Holdout questions** (designated before calibration — never shown to the calibration process):

| Country | Holdout questions (N) |
|---------|----------------------|
| France | US view, UN view, Zelenskyy confidence, children's future, Biden confidence (5) |
| Greece | US view, UN view, Zelenskyy confidence, Macron confidence, children's future (5) |
| Hungary | US view, UN view, Zelenskyy confidence, Macron confidence, Biden confidence (5) |
| Italy | US view, UN view, Zelenskyy confidence, Macron confidence, children's future (5) |
| Netherlands | US view, UN view, Zelenskyy confidence, Macron confidence, children's future (5) |
| Poland | US view, Zelenskyy confidence, Macron confidence, Biden confidence (4) |
| Spain | US view, UN view, Zelenskyy confidence, Macron confidence, Biden confidence (5) |
| Sweden | US view, Zelenskyy confidence, Macron confidence, Biden confidence (4) |
| UK | US view, UN view, Zelenskyy confidence, Macron confidence, Biden confidence (5) |

Poland and Sweden have 4 holdout questions (UN view used as calibration fill for these countries' smaller party question sets).

### Personas (40 per country)

Each country uses 40 demographically calibrated personas with hardcoded WorldviewAnchor dimensions:

- **IT** — Institutional Trust (0–100)
- **IND** — Individualism (0–100)
- **CT** — Change Tolerance (0–100)
- **MF** — Moral Foundationalism (0–100)

Key calibration axes by country:

| Country | Primary axis | Secondary axis |
|---------|-------------|----------------|
| France | Macron bloc / Le Pen RN / Mélenchon LFI | Paris vs. provinces |
| Greece | ND vs. SYRIZA | Austerity-era institutional distrust |
| Hungary | Fidesz loyalty vs. opposition | Urban/rural + Orbán media effect |
| Italy | FdI coalition vs. centre-left | North/South (Mezzogiorno) |
| Netherlands | VVD/D66 liberal vs. PVV nationalist | Randstad vs. periphery |
| Poland | PiS vs. PO cultural divide | Catholic/secular + East/West |
| Spain | PP/Vox vs. PSOE/Podemos | Catalan/Basque regional identity |
| Sweden | SAP social-democratic vs. SD nationalist | Urban/rural + immigration |
| UK | Labour/Remain vs. Conservative/Leave | England/Scotland/Wales |

---

## Methodology

**Distribution Accuracy (DA)** = `1 − (Σ|real_i − sim_i| / 2)` — same formula as Studies 1A, 1B, 1C.

**Human ceiling**: 91% (Iyengar et al., Stanford 2023 — human panel-to-panel replication benchmark).

**Calibration approach**: Iterative sprint calibration using the WorldviewAnchor architecture with option-vocabulary anchors. Each sprint is logged as a structured JSON manifest with per-question accuracy, simulated distributions, and SHA-256 hash of raw API responses.

**Holdout validation**: Questions designated before any calibration run. Holdout runner uses pure WorldviewAnchor architecture — zero topic-specific calibration anchors. Run minimum 3 times for variance estimate.

**Variance protocol**: Minimum 3 independent re-runs of ceiling sprint and holdout (following Study 1C methodology). Results stable within ±2pp SD are considered reliable.

---

## Ground Truth

All benchmark questions drawn from publicly available data:

- **Pew Research Center Global Attitudes Survey — Spring 2024** (`country` codes 3–12 in dataset)
- Dataset: [pewresearch.org/global/datasets](https://www.pewresearch.org/global/datasets/)
- All distributions verified from raw CSV (`Pew Research Center Global Attitudes Spring 2024 Dataset CSV.csv`)
- Germany ground truth (Study 1C) is `country=4` in the same dataset — same source, continuous audit trail

Raw data file location: `studies/pew_germany/data/raw/` (shared with Study 1C — no duplication).

---

## Cross-Country Comparisons (shared questions)

The 10 shared calibration questions enable direct cross-country comparison. See `shared_questions.json` for all distributions.

Notable cross-country variation in the ground truth data:

**Russia view (% very/somewhat unfavorable):**
Poland: 99.1% · Sweden: 96.7% · Netherlands: 93.9% · UK: 88.9% · France: 85.0% · Italy: 85.0% · Germany: 86.8% · Spain: 91.5% · Hungary: 76.3% · Greece: 74.6%

**Democracy satisfaction (% very/somewhat satisfied):**
Sweden: 78.1% · Netherlands: 63.5% · Poland: 58.4% · Germany: 59.5% · Hungary: 48.8% · UK: 41.4% · Spain: 34.0% · France: 38.3% · Italy: 35.6% · Greece: 27.6%

**Religion importance (% very/somewhat important):**
Poland: 71.4% · Hungary: 64.9% · Italy: 55.5% · Spain: 47.7% · UK: 41.6% · Greece: 51.8% · France: 35.1% · Germany: 35.0% · Netherlands: 37.9% · Sweden: 26.3%

---

## Repository Structure

```
studies/europe_benchmark/
├── README.md                        (this file)
├── shared_questions.json            (10 common questions, all 10 country distributions)
│
├── france/
│   ├── questions.json               (15 calibration + 5 holdout)
│   ├── pipeline/
│   │   ├── sprint_runner.py         (40 personas, WorldviewAnchor, Batch API)
│   │   └── persona_pool.md          (persona specifications)
│   ├── holdout/
│   │   ├── holdout_runner.py
│   │   └── results/
│   └── results/
│       └── sprint_manifests/
│
├── greece/ [same structure]
├── hungary/ [same structure]
├── italy/ [same structure]
├── netherlands/ [same structure]
├── poland/ [same structure]
├── spain/ [same structure]
├── sweden/ [same structure]
└── uk/ [same structure]
```

---

## Audit & Reproducibility

Every sprint is logged with:
- Per-question DA scores
- Simulated vs. ground truth distributions
- SHA-256 hash of raw API responses
- Batch ID for Anthropic API verification

Full prompts and persona pool definitions are proprietary and available under NDA for independent replication.
