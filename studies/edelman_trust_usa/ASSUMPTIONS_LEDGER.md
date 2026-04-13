# Assumptions Ledger — Edelman Trust Barometer Mirror (USA)

**Project:** STU_001_edelman_trust_usa
**Generated:** 2026-04-13
**Critical assumptions:** 4 | **Other:** 6

---

### A01 — Edelman question framing is sufficiently similar to Pew framing for DA comparison
**Source:** H02 (Lens: Citation Adequacy)
**If wrong:** The stimulus design would need to use Edelman's exact question wording as measurement anchors rather than general institutional trust prompts — otherwise DA will measure stimulus-to-stimulus variance rather than population-level accuracy.
**Decision change:** Would redesign stimuli to mirror Edelman survey instrument exactly, rather than using open-ended trust questions that allow persona-native framing.

---

### A02 — WorldviewAnchor IT (Institutional Trust) dimension captures cross-institutional trust variation
**Source:** H03 (Lens: Population Assumption)
**If wrong:** The trust inequality gap (H03) would not emerge from IT dimension alone — would need institution-specific sub-dimensions (government trust, media trust, business trust as separate coordinates) rather than a single IT score.
**Decision change:** Would architect personas with four separate institutional trust coordinates rather than relying on aggregate IT to differentiate informed public vs. mass population responses by institution type.

---

### A03 — Employer trust (F08) can be activated by employment-frame stimuli without direct prompting
**Source:** H04 (Lens: Context Assumption)
**If wrong:** H04 would need to be redesigned as a direct question ("How much do you trust your employer?") rather than an indirect activation — invalidating the test of whether employer trust emerges organically in relevant scenarios.
**Decision change:** Would add an explicit employer-trust direct question stimulus rather than relying on scenario-based emergence, and flag H04 as a direct measurement hypothesis rather than an emergence test.

---

### A04 — The 91% DA threshold derived from Pew methodology applies to Edelman survey data
**Source:** H02 (Lens: Causal Assumption)
**If wrong:** The entire success criterion for the study would need to be recalibrated — Edelman's sampling methodology, panel composition, and question format may produce different test-retest noise floors that shift the meaningful threshold up or down from 91%.
**Decision change:** Would establish an Edelman-specific noise floor empirically before publishing results, rather than applying the Pew-derived 91% threshold directly.

---

<details>
<summary>6 other assumptions (methodological + low-impact)</summary>

| ID  | Assumption | Source | Lens | Severity |
|-----|---|---|---|---|
| A05 | CEO credibility findings are not sector-dependent in the aggregate Edelman USA figure | H07 | Context | METHODOLOGICAL |
| A06 | Edelman "informed public" / "mass population" segmentation maps cleanly to income + education demographic anchors | H03 | Population | METHODOLOGICAL |
| A07 | Political lean does not need to be an explicit WorldviewAnchor input to reproduce trust inequality gap | H03 | Causal | METHODOLOGICAL |
| A08 | The 2024 Edelman Trust Barometer USA data is the most recent available at time of study execution | H01 | Context | LOW_IMPACT |
| A09 | Social media use/distrust paradox (F10) is stable enough to be captured by a single-wave ground truth comparison | H06 | Context | LOW_IMPACT |
| A10 | Scientists/experts can be modelled as a distinct credibility category without sector specification | H05 | Population | LOW_IMPACT |

</details>
