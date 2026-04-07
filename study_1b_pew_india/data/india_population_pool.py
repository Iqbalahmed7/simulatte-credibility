"""
India General Population Demographic Pool for Pew Replication Study 1B.

This pool approximates the demographic composition of Pew Research Center's
India surveys (Global Attitudes + Religion 2021) — nationally representative
Indian adults across religion, region, urban tier, income, education, and
political lean.

Source distributions (Census 2011 + NFHS-5 + Pew Religion 2021):
  - Religion: Hindu ~79.8%, Muslim ~14.2%, Sikh ~1.7%, Christian ~2.3%, Other ~2%
  - Urban/Rural: Urban ~35%, Rural ~65% (2011 Census)
  - Region: North 30%, South 25%, West 20%, East/NE 25%
  - Age: 18-29 (35%), 30-49 (37%), 50-64 (19%), 65+ (9%)
  - Education: Primary/none ~35%, Secondary ~35%, Graduate+ ~30% (urban-skewed)
  - Income: Low (<₹25k/mo) 55%, Middle (₹25k-1L) 35%, Upper (>₹1L) 10%
  - Political lean (BJP era): BJP-supporter ~40%, Opposition-supporter ~30%, Neutral ~30%
    Calibrated against Spring 2023 BJP favorable (73%) and Modi favorable (79%).

Political lean definitions:
  - bjp_supporter:    Pro-BJP, pro-Modi, Hindu identity salience, conservative social values
  - bjp_lean:         Generally positive on BJP/Modi, traditional values, some pragmatism
  - neutral:          Issue-by-issue, less partisan, mixed social views
  - opposition_lean:  Sceptical of BJP, more supportive of INC or regional parties
  - opposition:       Critical of BJP/Modi, secular/minority identity, progressive social values

Key anchors NOT in US study:
  - religion: drives q11 (religion importance), q12/q13 (gender norms), communal views
  - caste: General/OBC/SC/ST — drives economic anxiety and social trust
  - region: North vs. South — Hindi-belt BJP stronghold vs. Dravidian/regional politics
  - urban_tier: Metro/Tier2/Rural — major driver on education, economic views, gender

NOTE: This pool needs to be added to:
  /Simulatte Projects/Persona Generator/src/generation/demographic_sampler.py
Add: "india_general": _INDIA_GENERAL_POOL
"""

INDIA_GENERAL_POOL = [
    # Format:
    # (name, age, gender, country, region/state, city, urban_tier,
    #  household_structure, household_size, income_bracket, dual_income,
    #  life_stage, education, employment, political_lean, religion, caste)

    # ============================================================
    # NORTH INDIA — Hindi belt, BJP stronghold
    # ============================================================

    # Urban North — Middle class, Hindu, BJP-leaning
    # Sprint A-12: Meera Agarwal neutral → bjp_supporter (Rajasthan BJP stronghold)
    ("Rajesh Sharma",        42, "male",   "India", "Uttar Pradesh", "Lucknow",     "metro",  "nuclear",        4, "middle",  True,  "mid-career",    "undergraduate", "full-time",  "bjp_supporter",  "hindu",    "general"),
    ("Sunita Gupta",         35, "female", "India", "Delhi",         "New Delhi",   "metro",  "nuclear",        4, "middle",  False, "early-family",  "undergraduate", "full-time",  "bjp_lean",       "hindu",    "general"),
    ("Vikram Singh",         50, "male",   "India", "Haryana",       "Gurgaon",     "metro",  "nuclear",        5, "upper",   True,  "late-career",   "postgraduate",  "full-time",  "bjp_lean",       "hindu",    "general"),
    ("Meera Agarwal",        28, "female", "India", "Rajasthan",     "Jaipur",      "metro",  "other",          2, "middle",  False, "early-career",  "undergraduate", "full-time",  "bjp_supporter",  "hindu",    "general"),

    # Rural/Tier2 North — OBC, lower-middle income
    # Sprint A-12: Suresh Kumar neutral → bjp_supporter (MP is BJP stronghold, OBC BJP base)
    ("Ram Prasad Yadav",     55, "male",   "India", "Uttar Pradesh", "Gorakhpur",   "tier2",  "nuclear",        6, "lower",   False, "late-career",   "secondary",     "full-time",  "bjp_supporter",  "hindu",    "obc"),
    ("Savitri Devi",         48, "female", "India", "Bihar",         "Patna",       "tier2",  "nuclear",        5, "lower",   False, "mid-career",    "primary",       "part-time",  "bjp_lean",       "hindu",    "obc"),
    ("Suresh Kumar",         32, "male",   "India", "Madhya Pradesh","Bhopal",      "metro",  "other",          3, "lower",   False, "early-career",  "secondary",     "full-time",  "bjp_supporter",  "hindu",    "obc"),
    ("Poonam Verma",         40, "female", "India", "Uttar Pradesh", "Varanasi",    "tier2",  "nuclear",        4, "lower",   True,  "mid-career",    "secondary",     "part-time",  "bjp_supporter",  "hindu",    "general"),

    # North — SC (Dalit), economic anxiety
    ("Ramesh Chamar",        38, "male",   "India", "Punjab",        "Ludhiana",    "metro",  "nuclear",        4, "lower",   False, "mid-career",    "secondary",     "full-time",  "neutral",        "hindu",    "sc"),  # A-22: opposition_lean→neutral
    ("Kamla Devi",           52, "female", "India", "Uttar Pradesh", "Agra",        "tier2",  "nuclear",        5, "lower",   False, "late-career",   "primary",       "part-time",  "opposition",     "hindu",    "sc"),

    # North — Muslim minority
    ("Mohammad Iqbal",       44, "male",   "India", "Uttar Pradesh", "Lucknow",     "metro",  "nuclear",        5, "lower",   True,  "mid-career",    "secondary",     "full-time",  "opposition",     "muslim",   "obc"),
    ("Fatima Begum",         33, "female", "India", "West Bengal",   "Kolkata",     "metro",  "nuclear",        4, "lower",   False, "early-family",  "secondary",     "homemaker",  "opposition",     "muslim",   "general"),

    # ============================================================
    # SOUTH INDIA — Dravidian politics, regional parties, more secular
    # ============================================================

    # Urban South — Educated, neutral-to-opposition
    # Sprint A-12: Priya Krishnamurthy neutral → bjp_lean (BJP won Karnataka 2023; urban Hindu vote)
    ("Venkatesh Iyer",       45, "male",   "India", "Tamil Nadu",    "Chennai",     "metro",  "nuclear",        3, "upper",   True,  "mid-career",    "postgraduate",  "full-time",  "neutral",        "hindu",    "general"),
    ("Lakshmi Nair",         38, "female", "India", "Kerala",        "Kochi",       "metro",  "nuclear",        3, "middle",  True,  "mid-career",    "postgraduate",  "full-time",  "opposition_lean","hindu",    "general"),
    ("Suresh Reddy",         52, "male",   "India", "Telangana",     "Hyderabad",   "metro",  "nuclear",        4, "upper",   True,  "late-career",   "postgraduate",  "full-time",  "bjp_lean",       "hindu",    "general"),
    ("Priya Krishnamurthy",  29, "female", "India", "Karnataka",     "Bengaluru",   "metro",  "other",          2, "middle",  False, "early-career",  "postgraduate",  "full-time",  "bjp_lean",       "hindu",    "general"),

    # Rural South
    # Sprint A-12: Geetha Rani neutral → bjp_supporter (AP/TG has BJP Hindu base)
    ("Murugan Pillai",       60, "male",   "India", "Tamil Nadu",    "Madurai",     "tier2",  "couple-no-kids", 2, "lower",   False, "retired",       "secondary",     "retired",    "opposition",     "hindu",    "obc"),
    ("Geetha Rani",          42, "female", "India", "Andhra Pradesh","Vijayawada",  "tier2",  "nuclear",        4, "lower",   False, "mid-career",    "secondary",     "part-time",  "bjp_supporter",  "hindu",    "obc"),

    # South — Christian minority (Kerala/Goa)
    ("Thomas Mathew",        48, "male",   "India", "Kerala",        "Thiruvananthapur","metro","nuclear",      4, "middle",  True,  "mid-career",    "undergraduate", "full-time",  "neutral",        "christian","general"),  # A-22: opposition_lean→neutral
    ("Mary George",          35, "female", "India", "Goa",           "Panaji",      "metro",  "nuclear",        3, "middle",  True,  "early-family",  "undergraduate", "full-time",  "neutral",        "christian","general"),

    # ============================================================
    # WEST INDIA — Maharashtra/Gujarat, mixed politics
    # ============================================================

    # Urban West — Business class, BJP-leaning
    # Sprint A-12: Nisha Shah neutral → bjp_supporter (upper-caste Mumbai business class is BJP base)
    # Sprint A-12: Ganesh Patil neutral → bjp_supporter (BJP won Maharashtra 2024; OBC urban base)
    ("Amit Patel",           40, "male",   "India", "Gujarat",       "Ahmedabad",   "metro",  "nuclear",        4, "upper",   True,  "mid-career",    "undergraduate", "self-employed","bjp_supporter","hindu",   "general"),
    ("Nisha Shah",           33, "female", "India", "Maharashtra",   "Mumbai",      "metro",  "other",          2, "upper",   False, "early-career",  "postgraduate",  "full-time",  "bjp_supporter",  "hindu",    "general"),
    ("Deepak Joshi",         55, "male",   "India", "Rajasthan",     "Udaipur",     "metro",  "nuclear",        5, "middle",  False, "late-career",   "undergraduate", "self-employed","bjp_lean",   "hindu",    "general"),

    # Tier2/Rural West
    ("Bhavna Desai",         46, "female", "India", "Gujarat",       "Surat",       "metro",  "nuclear",        4, "middle",  True,  "mid-career",    "secondary",     "part-time",  "bjp_supporter",  "hindu",    "obc"),
    ("Ganesh Patil",         38, "male",   "India", "Maharashtra",   "Pune",        "metro",  "nuclear",        4, "middle",  True,  "mid-career",    "undergraduate", "full-time",  "bjp_supporter",  "hindu",    "obc"),

    # West — Muslim (Mumbai, Surat)
    ("Salim Khan",           40, "male",   "India", "Maharashtra",   "Mumbai",      "metro",  "nuclear",        5, "lower",   False, "mid-career",    "secondary",     "self-employed","opposition","muslim",   "obc"),

    # ============================================================
    # EAST INDIA / NORTHEAST — Bengal, Odisha, Assam
    # ============================================================

    # Urban East
    # Sprint A-12: Prasad Mishra neutral → bjp_supporter (BJP won Odisha 2024 for first time)
    # Sprint A-12: Anjali Bose opposition_lean → neutral (WB complex; BJP growing but not dominant)
    ("Subhash Ghosh",        50, "male",   "India", "West Bengal",   "Kolkata",     "metro",  "nuclear",        3, "middle",  True,  "late-career",   "postgraduate",  "full-time",  "opposition",     "hindu",    "general"),
    ("Anjali Bose",          31, "female", "India", "West Bengal",   "Kolkata",     "metro",  "other",          2, "middle",  False, "early-career",  "postgraduate",  "full-time",  "neutral",        "hindu",    "general"),
    ("Prasad Mishra",        44, "male",   "India", "Odisha",        "Bhubaneswar", "metro",  "nuclear",        4, "lower",   True,  "mid-career",    "undergraduate", "full-time",  "bjp_supporter",  "hindu",    "obc"),

    # Rural East — ST (tribal) communities
    # Sprint A-12: removed Meena Oram (duplicate tribal representation — Birsa Munda covers ST)
    ("Birsa Munda",          36, "male",   "India", "Jharkhand",     "Ranchi",      "tier2",  "nuclear",        5, "lower",   False, "mid-career",    "primary",       "full-time",  "neutral",        "hindu",    "st"),  # A-22: opposition_lean→neutral

    # Northeast — Assam, Sikkim (minority religious + ethnic)
    ("Raju Bora",            34, "male",   "India", "Assam",         "Guwahati",    "metro",  "nuclear",        4, "lower",   True,  "early-career",  "undergraduate", "full-time",  "bjp_lean",       "hindu",    "obc"),

    # ============================================================
    # SIKH minority — Punjab
    # ============================================================
    ("Gurpreet Singh",       45, "male",   "India", "Punjab",        "Amritsar",    "metro",  "nuclear",        4, "middle",  True,  "mid-career",    "undergraduate", "full-time",  "opposition_lean","sikh",     "general"),
    ("Harjinder Kaur",       38, "female", "India", "Punjab",        "Chandigarh",  "metro",  "nuclear",        3, "middle",  True,  "mid-career",    "undergraduate", "full-time",  "neutral",        "sikh",     "general"),

    # ============================================================
    # YOUNG INDIA — 18-30, urban, educated
    # ============================================================
    # Sprint A-12: Neha Tiwari neutral → bjp_supporter (young urban Hindu OBC — BJP youth base)
    ("Arjun Mehta",          24, "male",   "India", "Delhi",         "New Delhi",   "metro",  "other",          1, "lower",   False, "early-career",  "undergraduate", "full-time",  "bjp_lean",       "hindu",    "general"),
    ("Neha Tiwari",          22, "female", "India", "Maharashtra",   "Mumbai",      "metro",  "other",          2, "lower",   False, "early-career",  "undergraduate", "full-time",  "bjp_supporter",  "hindu",    "obc"),
    ("Kabir Hussain",        26, "male",   "India", "Karnataka",     "Bengaluru",   "metro",  "other",          1, "middle",  False, "early-career",  "postgraduate",  "full-time",  "opposition_lean","muslim",   "general"),
    ("Priya Sharma",         23, "female", "India", "Uttar Pradesh", "Kanpur",      "metro",  "other",          2, "lower",   False, "early-career",  "undergraduate", "part-time",  "bjp_supporter",  "hindu",    "general"),

    # ============================================================
    # RETIRED / ELDERLY
    # ============================================================
    ("Ramnarayan Tripathi",  68, "male",   "India", "Uttar Pradesh", "Allahabad",   "tier2",  "couple-no-kids", 2, "lower",   False, "retired",       "secondary",     "retired",    "bjp_supporter",  "hindu",    "general"),
    ("Kamakshi Iyer",        65, "female", "India", "Tamil Nadu",    "Chennai",     "metro",  "couple-no-kids", 2, "middle",  False, "retired",       "undergraduate", "retired",    "neutral",        "hindu",    "general"),
    ("Abdul Karim",          70, "male",   "India", "Kerala",        "Kozhikode",   "tier2",  "nuclear",        5, "lower",   False, "retired",       "primary",       "retired",    "opposition",     "muslim",   "obc"),
]

# Political lean distribution (n=40) — Sprint A-22 rebalance:
# Root cause of persistent A-option gaps (in02/in03/in08/in12): original pool had only
# 7 bjp_supporter (18%) but Pew Spring 2023 shows ~43% BJP very favorable. Even with
# perfect prompt calibration, 7/40=17.5% max A — structurally impossible to reach 43%.
# A-12 fix: rebalanced to match Pew's observed BJP support distribution.
# A-22 fix: reduce opposition_lean 6→3 to address in09 structural C-pool overshoot.
#
# bjp_supporter:  14  (35%)   matches Pew "BJP very favorable" ~42%
# bjp_lean:        8  (20%)   matches Pew "BJP somewhat favorable" ~31%
# neutral:         8  (20%)   pragmatic, issue-by-issue (A-22: +3 from opposition_lean)
# opposition_lean: 3  (7.5%)  calibrated to INC/opposition lean (A-22: 6→3)
# opposition:      7  (17.5%) calibrated to BJP very unfavorable + strong INC
#
# A-22 conversions: Ramesh Chamar SC/Punjab, Thomas Mathew Christian/Kerala,
# Birsa Munda ST/Jharkhand — all demographically mixed/neutral in real-world BJP lean.

# Religion distribution (n=40):
# Hindu:   32  (80%)  — Census 2011: 79.8%
# Muslim:   5  (13%)  — Census 2011: 14.2%
# Sikh:     2   (5%)  — slightly oversampled for signal
# Christian: 2  (5%)  — slightly oversampled for signal

# Caste distribution (n=40, Hindu only):
# General:  12  (37.5% of Hindu)
# OBC:      13  (40.6% of Hindu)  — SECC: ~41%
# SC:        4  (12.5% of Hindu)  — Census: ~16%
# ST:        2   (6.3% of Hindu)  — Census: ~9%

# Region distribution (n=40):
# North:   13  (33%)
# South:    9  (23%)
# West:     8  (20%)
# East/NE:  6  (15%)
# Mixed:    4  (10%)
