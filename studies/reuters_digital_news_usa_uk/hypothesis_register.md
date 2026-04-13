# Hypothesis Register — Reuters Digital News Report Mirror (USA & UK)

**Project:** STU_003_reuters_digital_news_usa_uk
**Generated:** 2026-04-13
**Status:** DRAFT — awaiting researcher approval

---

## Approved Hypotheses

H01  USA personas will report substantially lower overall news trust than UK personas — reflecting the documented 4pp country gap (USA 32%, UK 36%) — with both countries landing in the "low trust" zone.
     Category: B   Citations: F01, F02   breadth_claim: true
     Strongest challenge: A 4pp gap is within normal persona-level variance; the study may confirm directional ordering but fail DA if the specific margin is not reproduced accurately [F01, F02].

H02  Calibrated DA for news trust distributions against Reuters 2024 ground truth will exceed 91% in both USA and UK, replicating the performance level achieved against Pew in the existing study program.
     Category: C   Citations: F01, F02, G02   breadth_claim: false
     Strongest challenge: News trust is a more volatile and emotionally salient domain than political attitudes; persona calibration anchored on political and demographic WorldviewAnchor dimensions may underperform on media-specific sentiment [G02].

H03  Under-35 personas will show meaningfully higher news avoidance rates than over-55 personas in both countries, consistent with the documented 23pp gap in the USA (46% vs. 23% — F06).
     Category: B   Citations: F05, F06   breadth_claim: true
     Strongest challenge: Age-based news avoidance may be a proxy for a different underlying dimension (distrust vs. irrelevance vs. anxiety avoidance) that demographic age alone does not fully capture in persona calibration [F06].

H04  YouTube will rank above traditional newspaper websites as a news access platform for under-35 personas, consistent with F08's documented usage levels — without being explicitly instructed to prefer digital-native formats.
     Category: B   Citations: F07, F08   breadth_claim: false
     Strongest challenge: Platform preference requires recency-sensitive data to model accurately; persona calibration based on 2024 Reuters data may not reproduce fine-grained platform hierarchies if the WorldviewAnchor dimensions do not encode platform-specific media habits [F08].

H05  Personas will simultaneously report using social media for news AND distrusting it as a source — reproducing the use/distrust paradox in F10 — rather than resolving it in one direction.
     Category: C   Citations: F10, G04   breadth_claim: true
     Strongest challenge: Holding simultaneous high use and low trust is a complex cognitive state; personas may flatten this paradox, reporting either consistent use-without-trust or consistent distrust-with-avoidance [F10, G04].

H06  BBC will be identified as the most trusted news brand among UK personas, with trust ratings consistent with the Edelman-scale (F03 — 57%), but declining relative to an older reference point.
     Category: A   Citations: F03   breadth_claim: false
     Strongest challenge: BBC trust is politically differentiated in UK data — it is disproportionately trusted by older, more centrist voters and distrusted by right-leaning and younger audiences; aggregate DA may mask segment-level errors [F03].

H07  Podcast news consumption will be reported at higher rates by under-45 personas than by over-55 personas, consistent with the format's documented demographic skew in F09.
     Category: B   Citations: F09   breadth_claim: false
     Strongest challenge: Podcast usage is a behavioural pattern requiring specific lifestyle and commute context to be salient; personas without an explicitly activated media-consumption routine may underreport podcast use across all age groups [F09].

H08  USA personas will be more evenly split on AI news summaries (concern vs. willingness-to-use) than their stated scepticism implies — reproducing the F11 paradox (53% concerned, 38% would still use) rather than resolving it toward pure rejection.
     Category: C   Citations: F11, G04   breadth_claim: false
     Strongest challenge: AI attitudes are a rapidly evolving domain where persona calibration may reflect training data skew rather than the nuanced public ambivalence documented in F11's split distribution [F11].

---

## Rejected Hypotheses

H_REJ01  Personas will voluntarily reference Reuters Institute by name or cite its findings in responses.
          REJECTED — LLM assumption: tests meta-awareness of the survey instrument rather than authentic simulated belief.

H_REJ02  Conservative-leaning USA personas will show lower trust in mainstream media brands than liberal-leaning personas.
          REJECTED — LLM assumption: no partisan trust disaggregation cited in the fact table. Requires adding a fact entry with partisan-disaggregated Reuters data before this can be tested.

---

## Uncovered Gaps

G01 (age-based avoidance gap) is covered by H03.
G02 (cross-country trust difference) covered by H01.
G03 (platform preference distribution) covered by H04.
G04 (simultaneous use/distrust paradox) covered by H05 and H08.
No gaps uncovered.

---

## Strongest Challenges Summary (Morpheus-only)

H01  4pp gap may be within variance noise — directional but not precise [F01, F02]
H02  Media trust may be under-served by political WorldviewAnchor calibration [G02]
H03  Age-avoidance relationship may proxy a non-demographic dimension [F06]
H04  Platform hierarchies require recent behavioural data; WorldviewAnchor may not encode them [F08]
H05  Use/distrust paradox likely to collapse in synthetic responses [F10]
H06  BBC trust is politically segmented; aggregate DA may hide within-segment errors [F03]
H07  Podcast use requires activated media-routine context [F09]
H08  AI ambivalence is data-volatile; LLM training skew risk is high [F11]
