# 0136 — Owner-reviewable explosive-power slice

Status: accepted

Date: 2026-09-23

Decision version: `owner-alpha-explosive-power-slice@1.0.0`

## Decision

Prepare, but do not automatically ratify, the first complete owner-alpha explosive-power
governance chain for the existing countermovement-jump assessment:

```text
current governed jump-height estimate
→ provisional owner-only floor
→ below-floor capability need
→ explosive-power DEVELOP priority
→ reviewed plyometric-training strategy
→ exact countermovement-jump resource resolution
→ fixed starting contacts
→ exposure-sensitive progression
→ reviewed block and week
```

Use a provisional floor of 20 centimeters for the exact
`assessment_specific:countermovement_vertical_jump_height_cm` scope. The value is an explicit AGAS
engineering judgment, not an ACSM or Payne norm. The floor candidate preserves the Payne et al.
source and a separate low-applicability descriptive claim, judgment authority, authority review,
floor review, and content digest. It remains inert until a planning reviewer adopts the exact
candidate.

Add an explosive-power resource candidate using Oxfeldt et al. (2019), PMID 31136014 and DOI
10.1111/sms.13487. The scientific claim is limited to the broad direction that 4-to-12-week
lower-body plyometric training can improve jump performance in healthy recreationally active adults
or athletes. Reuse the controlled-catalog countermovement-jump exercise and require a full exact
resolution. The downstream resource envelope is 24 weekly minutes across two 12-minute sessions;
this is an engineering allocation, not a result extracted from the review.

Add a fixed-dose construction candidate for below-floor `DEVELOP` lineage only. Its starting dose is
three sets of three separately reset contacts, capped at nine initial contacts, with 120 seconds rest
and RPE 5-7. These numeric values are engineering priors. The athlete's jump-height value establishes
the assessed construct and need but is never used as dose arithmetic.

Mark the progression policy as `jumping` exposure-sensitive. Every completed repetition is recorded
as one contact, and any progression requires an explicit exposure validation. The candidate caps an
increase at both 34 percent relative and three contacts absolute over recent completed exposure.
Consequently, the ordinary automatic progression endpoint refuses this policy instead of silently
adding contacts without the exposure ledger.

Generalize prepared resource demand construction to preserve the selected exercise's loading type
instead of hard-coding bodyweight. This allows the existing ballistic jump ontology record to
resolve without changing the underlying explosive-power adaptation target.

## Reason

Decision 0135 created the fixed-repetition authority needed for measurements such as jump height,
where centimeters cannot coherently determine contacts. The product still lacked the reviewed
floor, scientific strategy, resource envelope, exercise authority, fixed contact policy, and
impact-sensitive progression needed to exercise that mechanism through a real first week.

The new chain advances the closed feedback loop without treating a descriptive population table as
athlete truth, reusing introductory assessment exposure as ordinary training, or allowing generic
repetition progression to bypass impact-exposure controls.

## Alternatives considered

- **Activate the ACSM age/sex category as the floor.** Rejected because the categories are
  descriptive, require a sex classification that the system does not infer, and are not validated
  minimum useful competencies.
- **Wait for longitudinal personal calibration before any explosive-power planning.** Deferred as
  the preferred replacement. A clearly labeled, owner-reviewed engineering floor allows the
  architecture to be exercised now without claiming external validity.
- **Reuse the six-contact introductory jump exposure.** Rejected because assessment preparation and
  ordinary capability development have different needs, effort, progression, and provenance.
- **Derive contacts from jump height.** Rejected as dimensionally invalid and falsely precise.
- **Use generic automatic repetition progression.** Rejected because impact exposure requires an
  explicit contact ledger and cap validation.
- **Represent the countermovement jump as bodyweight loading.** Rejected because the controlled
  ontology intentionally models it as ballistic; the resource resolver must preserve that meaning.

## Evidence

- Payne et al., *Canadian musculoskeletal fitness norms*, PMID 11098155, DOI 10.1139/h00-028,
  supports only the provenance and population of descriptive vertical-jump reference values.
- Oxfeldt et al., *Effects of plyometric training on jumping, sprint performance, and lower body
  muscle strength in healthy adults*, PMID 31136014, DOI 10.1111/sms.13487, supports the broad
  plyometric-training-to-jump-performance direction.
- The exact floor, resource envelope, starting contacts, RPE, rest, scheduling, and progression caps
  are explicitly labeled engineering judgment and remain owner-reviewable.

## Uncertainty

- No reviewed source validates 20 centimeters as a minimum useful competency for this athlete.
- The first personal measurement may show that the provisional floor is too low, too high, or not
  useful enough to retain.
- The Oxfeldt review includes heterogeneous healthy adult populations and interventions and does not
  establish the exact exercise or numeric policy values used here.
- Self-observed landing control and RPE do not measure ground-reaction force, asymmetry, or all
  technique faults.
- A current estimate implies an assessment-specific observation, but the session safety gate,
  environment availability, exposure history, and concerning symptoms remain separate controls.

## Consequences

- A planning reviewer can independently inspect and ratify the floor, resource, and construction
  candidates; none is silently activated by this change.
- A below-floor owner-alpha jump estimate can now travel through need, priority, resource demand,
  block, fixed dose, week, and immutable prescription provenance.
- A tested example with an 18 centimeter estimate and 20 centimeter provisional floor produces two
  3-by-3 countermovement-jump sessions while retaining that the estimate value was not used as dose
  arithmetic.
- Jump progression cannot use the simple automatic path; it requires explicit exposure-definition
  and exposure-policy identities and a validated proposed contact total.
- The next product task is to add an athlete-facing review/explanation for the new explosive-power
  candidates and then record ordinary jump-training contacts into the longitudinal response loop.
