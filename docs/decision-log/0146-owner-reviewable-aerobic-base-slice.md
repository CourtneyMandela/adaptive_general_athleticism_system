# 0146 — Owner-reviewable aerobic-base slice

## Decision

Prepare, but do not automatically ratify, a complete owner-alpha aerobic-capacity candidate chain:

- a high-effort 12-minute walk/run assessment that stores direct distance in meters;
- a low-confidence, 28-day, assessment-specific estimate with no VO2 conversion;
- an owner-only provisional 1200-meter competency floor;
- an aerobic-base resource authority that resolves the existing treadmill walk/run exercise only
  when the exact equipment and environment are feasible;
- a 24-minute weekly scheduling envelope across two 12-minute slots;
- a fixed 600-second starting duration at RPE 4-6, independent of assessment distance;
- deterministic 60-second progression after complete, technique-compliant work at session RPE 5
  or below, with an absolute 720-second per-set ceiling;
- a separately governed 80-percent adherence review boundary and provisional 50-meter meaningful-
  change rule.

Every exact threshold, duration, frequency, effort, progression, ceiling, adherence, and response
value is labeled `engineering_judgment`. The scientific claims authorize only the field-test
validity and broad individualized aerobic-training direction described in their exact records.

## Reason

Aerobic capacity is a major general-athleticism domain that still lacked an operational owner path.
Decision 0145 supplied the missing duration-dose type but deliberately did not select an assessment
or prescription. This decision connects the next complete vertical slice without collapsing test
distance into training time or treating a population association as an athlete-specific norm.

The path preserves:

`distance observation -> assessment-specific estimate -> reviewed floor comparison -> aerobic need -> DEVELOP priority -> required cyclic stimulus -> feasible treadmill means -> reviewed duration dose -> performance -> reassessment`

Walking is always permitted. Running is not introduced by either the assessment or training
candidate; it is allowed only when already familiar and currently appropriate.

## Alternatives considered

- Convert 12-minute distance to predicted VO2 and plan from that number. Rejected because the
  field result is not a direct laboratory measurement and prediction error would create false
  precision.
- Use a direct maximal treadmill VO2 threshold from the existing research-proposal inventory.
  Rejected for the owner self-service alpha because it requires specialized maximal testing and a
  materially different clinical and equipment boundary.
- Use a six-minute walk test. Deferred because the selected systematic reviews provide a clearer
  validity basis for the 12-minute walk/run test in healthy adults, while walking can still be used
  throughout the chosen protocol.
- Adopt a published age/sex fitness category as the floor. Rejected because descriptive categories
  are not minimum useful competencies and the product does not need to infer or operationalize sex
  to identify a deliberately low owner-only sentinel.
- Start at the full 12-minute dose and keep adding time automatically. Rejected because assessment
  duration is not a training prescription and unbounded automatic duration progression is unsafe
  architecture.
- Treat cycling or rowing as automatically equivalent when a treadmill is absent. Rejected. The
  current narrow candidate reports infeasibility rather than silently changing the required
  locomotion stimulus; later modality-specific candidates may preserve the aerobic goal with honest
  partial or full matching.

## Evidence

- Mayorga-Vega et al. (2016), PMID 26987118, DOI 10.1371/journal.pone.0151671: systematic review
  and meta-analysis of distance- and time-based walk/run field tests. The pooled 12-minute
  walk/run validity correlation was 0.78 (95% CI 0.72 to 0.83). This supports the field measure,
  not a VO2 conversion, floor, reassessment interval, or dose.
- Garber et al. (2011), PMID 21694556, DOI 10.1249/MSS.0b013e318213fefb: ACSM position stand
  supporting regular individualized aerobic exercise for apparently healthy adults and noting that
  volumes below the full public-health target may still be beneficial. It does not establish the
  candidate's exact modality, minutes, effort, increment, ceiling, or response threshold.
- The original Cooper 12-minute report, PMID 5694044, was reviewed as historical protocol context
  but was not used as the sole applicability basis because its narrow 1968 U.S. Air Force male
  sample does not match the owner-alpha population.
- Tests preserve exact source/claim identity across assessment and floor candidates, keep direct
  distance distinct from dose, require explicit review for every authority, generate a real
  duration prescription, and hold deterministic progression at the reviewed ceiling.

## Uncertainty

The 1200-meter floor is a deliberately low owner-only sentinel, not a validated health or athletic
minimum. The 600-second start, two-session frequency, RPE range, 60-second increment, 720-second
ceiling, 80-percent adherence cutoff, and 50-meter response threshold have not been calibrated
against this athlete's repeated observations.

Pacing, route or treadmill accuracy, surface, weather, footwear, recent fatigue, motivation, and
walking or running familiarity can materially affect the assessment. Perceived exertion cannot
establish medical safety or directly measure physiology. Independent domain-expert review is still
absent.

## Consequences

- The owner can inspect and separately ratify the exact assessment, floor, resource, and
  construction candidates through the existing governance surfaces.
- No candidate affects planning until its required owner review is persisted; deployment alone
  creates no authority.
- The 12-minute observation remains meters, the training prescription remains seconds, and no
  conversion joins the two.
- Missing treadmill availability remains visible as infeasibility. Equipment limitations do not
  rewrite the aerobic adaptation goal or claim an inadequate substitute is equivalent.
- Duration progression now has a typed, persisted ceiling and the session-envelope validator is a
  second hard bound.
- Existing chair, push-up, jump-exposure, explosive-power DEVELOP, and explosive-power MAINTAIN
  candidate identities and behavior remain unchanged.
- The next product task is an owner-facing guided aerobic review/activation flow and a persisted
  below-floor acceptance regression covering candidate ratification through first week and
  repeated 10-to-11-to-12-minute progression/hold behavior.

## Version/date

- Decision version: `owner-reviewable-aerobic-base-slice@1.0.0`
- Date: 2026-09-25
