"""
US General Population Demographic Pool for Pew Replication Study.

This pool is designed to approximate the demographic composition of Pew Research
Center's American Trends Panel (ATP) — a probability-based, nationally
representative sample of US adults.

Source distributions:
  - Gender: ~52% female, 48% male (US Census 2020)
  - Age: 18-29 (16%), 30-49 (34%), 50-64 (27%), 65+ (23%)
  - Race/Ethnicity: 63% White non-Hispanic, 12% Black, 13% Hispanic, 5% Asian, 7% other
  - Education: ~30% college grad+, ~28% some college, ~27% HS grad, ~15% <HS
  - Region: South (38%), Midwest (21%), West (24%), Northeast (18%)
  - Urban: Metro (54%), Suburban (27%), Rural (19%)

NOTE: This pool needs to be added to:
  /Simulatte Projects/Persona Generator/src/generation/demographic_sampler.py

Add the following to _DOMAIN_POOLS:
  "us_general": _US_GENERAL_POOL

And register it in sample_demographic_anchor().
"""

US_GENERAL_POOL = [
    # (name, age, gender, country, region, city, urban_tier,
    #  structure, size, income_bracket, dual_income,
    #  life_stage, education, employment)

    # --- South, Female, 35-50, Middle income ---
    ("Patricia Williams",  43, "female", "USA", "Georgia",        "Atlanta",       "metro",    "nuclear",        4, "middle",        True,  "mid-career",    "high-school",   "full-time"),
    ("Sandra Johnson",     58, "female", "USA", "Texas",          "Houston",       "metro",    "nuclear",        3, "middle",        False, "late-career",   "high-school",   "part-time"),
    ("Maria Garcia",       35, "female", "USA", "Florida",        "Miami",         "metro",    "nuclear",        4, "lower-middle",  True,  "early-family",  "high-school",   "full-time"),
    ("Linda Brown",        67, "female", "USA", "North Carolina", "Charlotte",     "metro",    "couple-no-kids", 2, "middle",        False, "retired",       "undergraduate", "retired"),

    # --- Midwest, Male, 30-55, varied income ---
    ("James Miller",       48, "male",   "USA", "Ohio",           "Columbus",      "metro",    "nuclear",        4, "middle",        True,  "mid-career",    "undergraduate", "full-time"),
    ("Robert Davis",       61, "male",   "USA", "Michigan",       "Detroit",       "metro",    "nuclear",        3, "lower-middle",  False, "late-career",   "high-school",   "full-time"),
    ("William Wilson",     38, "male",   "USA", "Illinois",       "Chicago",       "metro",    "nuclear",        4, "upper-middle",  True,  "mid-career",    "undergraduate", "full-time"),
    ("Thomas Anderson",    55, "male",   "USA", "Minnesota",      "Minneapolis",   "metro",    "nuclear",        3, "upper-middle",  True,  "late-career",   "postgraduate",  "full-time"),

    # --- Northeast, Female, 25-45, higher education ---
    ("Jennifer Taylor",    32, "female", "USA", "New York",       "New York",      "metro",    "other",          1, "upper-middle",  False, "early-career",  "postgraduate",  "full-time"),
    ("Barbara Martinez",   44, "female", "USA", "Pennsylvania",   "Philadelphia",  "metro",    "nuclear",        3, "middle",        True,  "mid-career",    "undergraduate", "full-time"),
    ("Susan Thompson",     29, "female", "USA", "Massachusetts",  "Boston",        "metro",    "other",          2, "middle",        False, "early-career",  "postgraduate",  "full-time"),
    ("Dorothy White",      71, "female", "USA", "Connecticut",    "Hartford",      "metro",    "couple-no-kids", 2, "middle",        False, "retired",       "undergraduate", "retired"),

    # --- West, Male, 28-50, varied income ---
    ("Charles Harris",     36, "male",   "USA", "California",     "Los Angeles",   "metro",    "nuclear",        4, "middle",        True,  "early-family",  "high-school",   "full-time"),
    ("Joseph Jackson",     52, "male",   "USA", "Washington",     "Seattle",       "metro",    "nuclear",        3, "upper-middle",  True,  "late-career",   "undergraduate", "full-time"),
    ("Christopher Martin", 28, "male",   "USA", "Arizona",        "Phoenix",       "metro",    "other",          1, "lower-middle",  False, "early-career",  "high-school",  "full-time"),
    ("Daniel Thompson",    45, "male",   "USA", "Colorado",       "Denver",        "metro",    "nuclear",        4, "upper-middle",  True,  "mid-career",    "postgraduate",  "full-time"),

    # --- Rural / Suburban, both genders, varied ages ---
    ("Nancy Moore",        54, "female", "USA", "Iowa",           "Des Moines",    "tier2",    "nuclear",        4, "middle",        True,  "late-career",   "high-school",   "full-time"),
    ("Mark Taylor",        42, "male",   "USA", "Tennessee",      "Nashville",     "metro",    "nuclear",        4, "middle",        True,  "mid-career",    "high-school",   "full-time"),
    ("Betty Jackson",      63, "female", "USA", "Alabama",        "Birmingham",    "tier2",    "nuclear",        3, "lower-middle",  False, "late-career",   "high-school",   "part-time"),
    ("Paul Rodriguez",     31, "male",   "USA", "Nevada",         "Las Vegas",     "metro",    "other",          2, "lower-middle",  False, "early-career",  "high-school",  "full-time"),

    # --- Older adults, retired ---
    ("Helen Lewis",        74, "female", "USA", "Florida",        "Orlando",       "metro",    "couple-no-kids", 2, "middle",        False, "retired",       "high-school",   "retired"),
    ("Frank Lee",          69, "male",   "USA", "Arizona",        "Phoenix",       "metro",    "couple-no-kids", 2, "upper-middle",  False, "retired",       "undergraduate", "retired"),

    # --- Younger adults, diverse ---
    ("Michelle Walker",    24, "female", "USA", "Texas",          "Austin",        "metro",    "other",          1, "lower-middle",  False, "early-career",  "high-school",  "full-time"),
    ("Kevin Hall",         22, "male",   "USA", "California",     "San Diego",     "metro",    "other",          1, "lower-middle",  False, "early-career",  "high-school",  "part-time"),
    ("Amanda Allen",       27, "female", "USA", "New York",       "Brooklyn",      "metro",    "other",          2, "middle",        False, "early-career",  "undergraduate", "full-time"),
    ("Ryan Young",         26, "male",   "USA", "Washington",     "Seattle",       "metro",    "other",          1, "middle",        False, "early-career",  "postgraduate",  "full-time"),

    # --- Black Americans ---
    ("Denise Robinson",    40, "female", "USA", "Georgia",        "Atlanta",       "metro",    "nuclear",        3, "middle",        True,  "mid-career",    "undergraduate", "full-time"),
    ("Marcus Johnson",     33, "male",   "USA", "Illinois",       "Chicago",       "metro",    "other",          1, "middle",        False, "early-career",  "undergraduate", "full-time"),
    ("Keisha Brown",       28, "female", "USA", "Texas",          "Dallas",        "metro",    "other",          1, "lower-middle",  False, "early-career",  "high-school",  "full-time"),
    ("Darnell Williams",   55, "male",   "USA", "Maryland",       "Baltimore",     "metro",    "nuclear",        4, "upper-middle",  True,  "late-career",   "undergraduate", "full-time"),

    # --- Hispanic Americans ---
    ("Carmen Lopez",       38, "female", "USA", "California",     "Los Angeles",   "metro",    "nuclear",        5, "lower-middle",  True,  "early-family",  "high-school",   "full-time"),
    ("Miguel Hernandez",   29, "male",   "USA", "Texas",          "San Antonio",   "metro",    "nuclear",        4, "lower-middle",  True,  "early-career",  "high-school",  "full-time"),
    ("Rosa Gonzalez",      52, "female", "USA", "Florida",        "Miami",         "metro",    "nuclear",        4, "middle",        False, "late-career",   "high-school",   "full-time"),
    ("Carlos Reyes",       44, "male",   "USA", "Arizona",        "Tucson",        "tier2",    "nuclear",        4, "middle",        True,  "mid-career",    "high-school",   "self-employed"),
]


def get_us_general_pool():
    """Return the US general population demographic pool."""
    return US_GENERAL_POOL
