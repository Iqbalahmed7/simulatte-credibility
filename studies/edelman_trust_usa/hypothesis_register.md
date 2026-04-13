# Hypothesis Register — Edelman Trust Barometer Mirror (USA)

**Project:** STU_001_edelman_trust_usa
**Generated:** 2026-04-13
**Status:** DRAFT — awaiting researcher approval

---

## Approved Hypotheses

H01  Simulatte personas will distribute institutional trust across business, government, NGOs, and media in proportions consistent with Edelman 2024 USA published distributions (business most trusted, media and government in distrust zone).
     Category: B   Citations: F02, F04   breadth_claim: false
     Strongest challenge: The trust ordering may emerge from general LLM training data rather than from calibrated persona architecture, making it a knowledge artefact rather than a genuine population simulation [F02, F04].

H02  The calibrated DA for institutional trust distributions will exceed 91% against Edelman 2024 USA ground truth, consistent with performance against Pew ground truth in the existing study program.
     Category: C   Citations: F02, F03, F04, G02   breadth_claim: false
     Strongest challenge: Edelman's trust questions use proprietary framing and scale anchors that differ from Pew methodology; stimulus phrasing differences may systematically deflate DA in ways unrelated to persona accuracy [G02].

H03  Personas calibrated to "informed public" demographic profiles (college-educated, high income) will score institutional trust 12–20pp higher than "mass population" personas — reproducing the Edelman trust inequality gap without explicit calibration to it.
     Category: C   Citations: F05, G01   breadth_claim: true
     Strongest challenge: The trust inequality gap may be confounded by political lean in the Edelman data, which demographic calibration alone may not capture without explicit political orientation anchoring [F05, G01].

H04  Employer trust will emerge as the highest-trust entity in responses from personas whose employment context is active and stable — reproducing F08's finding without directly prompting on "my employer" as a category.
     Category: C   Citations: F08, G03   breadth_claim: false
     Strongest challenge: Employer trust as the highest-trust entity is a context-dependent finding that only emerges when employment framing is salient; personas may not volunteer employer trust unless the stimulus specifically activates that frame [F08, G03].

H05  Scientists and academic experts will be rated as the most credible information sources by a majority of personas across demographic groups, consistent with F07's 68% figure.
     Category: B   Citations: F07   breadth_claim: true
     Strongest challenge: Expert credibility is subject to political lean effects documented across multiple Pew and Gallup studies; without political calibration, personas may over-index on expert trust or produce undifferentiated responses [F07].

H06  Social media will be simultaneously highly used and highly distrusted as a news/information source — with personas showing the paradox documented in F10 (high use, low trust) rather than resolving it in one direction.
     Category: B   Citations: F10, G02   breadth_claim: true
     Strongest challenge: The simultaneous use/distrust pattern is cognitively complex; synthetic personas may resolve the tension in one direction (either high trust reflecting use, or low trust reflecting stated attitudes) rather than holding both [F10].

H07  CEO credibility will be rated as lower than scientist/expert credibility across all persona archetypes, consistent with the gap between F07 (68% expert credibility) and F06 (48% CEO credibility).
     Category: B   Citations: F06, F07   breadth_claim: true
     Strongest challenge: CEO credibility ratings may vary substantially by sector (e.g. tech vs. pharmaceutical), which the Edelman aggregate figure obscures; personas without sector-specific context may produce regression-to-mean responses [F06].

---

## Rejected Hypotheses

H_REJ01  Personas will spontaneously reference Edelman Trust Barometer data or framing in their responses, indicating alignment with the survey instrument.
          REJECTED — LLM assumption: assumes personas have meta-awareness of survey instruments rather than holding authentic simulated beliefs. This tests the wrong thing.

H_REJ02  Trust in government will be higher among personas in the 55+ age bracket than among 18–35 personas.
          REJECTED — LLM assumption: no Edelman USA age-disaggregated government trust data cited in fact table. Cannot validate this without adding it as a fact entry.

---

## Uncovered Gaps

G04 (demographic predictors of trust) is partially covered by H03 but not fully addressed. H03 covers income/education. Political lean as a trust predictor has no dedicated hypothesis. Recommend adding or accepting as a known gap.

---

## Strongest Challenges Summary (Morpheus-only)

H01  Trust ordering plausibly emerges from LLM training data, not persona calibration [F02, F04]
H02  Edelman scale anchors differ from Pew methodology — DA metric may not be directly comparable [G02]
H03  Political lean confounds the trust inequality gap; demographic calibration may not be sufficient [F05]
H04  Employer trust requires employment-frame activation in stimulus; may not emerge organically [F08]
H05  Expert credibility is politically differentiated; archetypes without political anchoring may blur this [F07]
H06  Use/distrust paradox may resolve artificially in one direction in synthetic responses [F10]
H07  CEO credibility is sector-dependent; aggregate Edelman figure may not map to uncontextualised personas [F06]
