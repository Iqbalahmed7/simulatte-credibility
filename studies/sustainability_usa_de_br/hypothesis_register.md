# Hypothesis Register — Consumer Sustainability Attitudes (USA, Germany, Brazil)

**Project:** STU_004_sustainability_usa_de_br
**Generated:** 2026-04-13
**Status:** DRAFT — awaiting researcher approval

---

## Approved Hypotheses

H01  Simulatte personas will reproduce the documented rank ordering of sustainability concern across the three countries: Germany (78%) > Brazil (72%) > USA (61%) — without explicit sustainability-specific calibration.
     Category: B   Citations: F02, G01   breadth_claim: true
     Strongest challenge: Country rank ordering in sustainability may emerge from general LLM geo-cultural priors rather than from calibrated WorldviewAnchor dimensions, making it a training artefact rather than persona-level accuracy [F02].

H02  Calibrated DA for sustainability attitude distributions will exceed 91% against GlobeScan 2024 ground truth across all three countries, consistent with performance in the political attitudes study program.
     Category: C   Citations: F01, F02, F03, G01   breadth_claim: false
     Strongest challenge: GlobeScan uses proprietary question framing and scale anchors that differ from Pew methodology; the 91% threshold that is meaningful for Pew-calibrated studies may not transfer directly to a different survey instrument [G01].

H03  Brazilian personas will show the largest gap between stated environmental concern and premium payment willingness — reproducing the F03 divergence (72% concern, 28% premium behaviour) as the widest attitude-behaviour gap of the three countries.
     Category: B   Citations: F03, F04, G01   breadth_claim: false
     Strongest challenge: Brazil's gap may be driven by income constraint rather than values divergence; personas calibrated by demographic and worldview dimensions may conflate poverty-driven non-purchase with values-driven non-commitment [F03, G01].

H04  USA personas will show higher stated environmental concern than their purchase behaviour suggests — reproducing the F04 documented attitude-behaviour gap (61% concern, 34% action) rather than resolving it toward either pure concern or pure indifference.
     Category: B   Citations: F04, G01   breadth_claim: false
     Strongest challenge: The USA attitude-behaviour gap requires the persona to simultaneously hold genuine concern and economically rational inaction; this is a cognitively complex state that synthetic personas may collapse toward one pole [F04].

H05  German personas will report both the highest premium willingness (F03 — 41%) and the highest personal sacrifice acceptance (F09 — 49%) of the three countries — reproducing Germany's unique "committed sustainability" profile without explicit geo-specific calibration.
     Category: B   Citations: F02, F03, F09   breadth_claim: false
     Strongest challenge: Germany's sustainability profile is a culturally specific construct (Green politics heritage, Energiewende, consumer movement history) that may require narrative context to activate in personas rather than emerging from WorldviewAnchor dimensions alone [F09].

H06  Personas across all three countries will rate third-party eco-certification as more credible than brand-only environmental claims — reflecting the 22pp certification premium documented in F06.
     Category: A   Citations: F05, F06, G04   breadth_claim: true
     Strongest challenge: The certification premium requires greenwashing scepticism (F05) and brand distrust to be co-activated; personas that hold high brand trust may show a smaller certification premium, fragmenting the aggregate effect [F06, G04].

H07  Greenwashing scepticism distributions (F05: 57% USA, 63% Germany, 49% Brazil) will be reproduced accurately by country-calibrated personas, with Germany showing the highest scepticism of the three markets.
     Category: B   Citations: F05, G03   breadth_claim: true
     Strongest challenge: Greenwashing scepticism is a relatively recent and media-driven attitude; its distribution may be captured by general LLM knowledge rather than by WorldviewAnchor calibration, making it hard to attribute accuracy to the persona architecture specifically [F05].

H08  Younger personas (18–34) will show higher sustainability concern than older personas in all three countries, but similar or lower willingness to pay a premium — reproducing the age-decoupled attitude-behaviour gap documented in F07.
     Category: B   Citations: F07, G01   breadth_claim: true
     Strongest challenge: The age-decoupled gap is subtle and could be masked by income effects; young-persona demographic calibration may produce lower income levels that depress premium willingness for economic rather than values-based reasons [F07].

H09  Brazilian personas will respond more strongly to Amazon/deforestation framing than to generic climate change framing — reproducing the 18pp concern amplification documented in F10.
     Category: C   Citations: F10   breadth_claim: false
     Strongest challenge: Topic framing sensitivity is highly stimulus-dependent and may not emerge from WorldviewAnchor calibration; it may require specific narrative activation that the default persona architecture does not provide [F10].

---

## Rejected Hypotheses

H_REJ01  Personas will cite specific GlobeScan data in their responses.
          REJECTED — LLM assumption: tests meta-awareness, not authentic belief.

H_REJ02  German personas will be more politically engaged on sustainability issues than USA or Brazilian personas.
          REJECTED — LLM assumption: no political engagement disaggregation by country cited in fact table. The fact table addresses consumer attitudes and purchase behaviour, not political engagement.

---

## Uncovered Gaps

G02 (Germany premium advantage emerging from WorldviewAnchor alone): covered by H05.
G03 (greenwashing scepticism across markets): covered by H07.
G04 (certification premium across ESP values): covered by H06.
All G-codes covered.

---

## Strongest Challenges Summary (Morpheus-only)

H01  Country rank ordering likely a training artefact, not calibration signal [F02]
H02  GlobeScan scale anchors may not map to the same DA threshold as Pew [G01]
H03  Brazil gap may be income-driven, not values-driven — conflation risk [F03]
H04  USA attitude-behaviour gap requires holding cognitive tension; collapse risk [F04]
H05  Germany's profile requires cultural activation, not just WorldviewAnchor [F09]
H06  Certification premium requires greenwashing scepticism co-activation [F06]
H07  Greenwashing scepticism may be LLM training data artefact [F05]
H08  Age-income conflation may mask age-specific attitude pattern [F07]
H09  Framing sensitivity is highly stimulus-dependent; may not emerge without specific activation [F10]
