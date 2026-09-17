# 0119 - Judgment-backed owner push-up floor

Date: 2026-09-15

Status: accepted

Decision version: `owner-alpha-standard-pushup-floor@1.0.0`

## Decision

Extend the data-loaded competency-floor release format so one exact candidate may include an
immutable `CompetencyFloorAuthority` and its prepared review content in addition to supporting
scientific evidence. Ratification must persist the evidence review, judgment authority, authority
review, floor, floor review, and decision record atomically. The floor review cites both bases.

Add `engineering_judgment` as a distinct authority kind. `professional_judgment` remains available
for a named human expert acting within an explicitly described qualification context, while
`personal_calibration` remains reserved for longitudinal athlete-specific inference. This release
uses `engineering_judgment` so neither the data nor the UI implies that Courtney authored the value
or that Codex holds a professional credential.

Prepare an owner-only, age-30-to-39 standard-push-up floor of 10 valid consecutive repetitions
under the governed assessment protocol. The ACSM source supports the protocol and narrow
upper-body muscular-endurance construct only. The number 10 is explicitly an AGAS engineering
judgment, not an ACSM norm, not athlete-authored professional advice, and not a credential claim.
The release is unusable until a planning reviewer adopts the exact content-addressed judgment.

Use a floor-specific supporting evidence claim and review identity even though the assessment and
floor share the same immutable ACSM source snapshot. This lets either candidate be ratified first
without creating competing review histories for one claim.

Bump the prepared initial-planning context to `@1.1.0`. It now selects an exact governed standard-
push-up estimate and matching floor before considering the chair-stand path. The chair-stand path
remains a historical fallback so existing state is not discarded, but it is no longer the preferred
owner-alpha input.

## Reason

The professional-judgment domain model added in decision 0116 was not yet reachable through the
ordinary candidate-ratification path. Leaving that seam open would either block owner-relevant
floors or encourage unsupported numbers to be disguised as scientific findings. The standard
push-up assessment is practical and relevant enough to exercise the honest authority path.

Ten repetitions is deliberately conservative. It distinguishes inability to sustain a short
valid series from a result suitable for maintenance review without importing the source's
non-comparable male standard-push-up and female modified-push-up categories. It may be too low for
this athlete; that is visible uncertainty, not a reason to invent a stronger evidence claim.

## Alternatives considered

- **Use the ACSM male age-30-to-39 Good-category boundary of 17.** Rejected because athlete sex has
  not been explicitly reported and the source uses a different movement protocol in its female
  row. The category is also descriptive, not a validated AGAS minimum.
- **Use the lower of the two sex-specific numbers.** Rejected because it would silently compare
  standard and modified movements and repeat the chair-stand content failure under a new label.
- **Attribute the threshold to Courtney's professional judgment.** Rejected because Courtney asked
  AGAS engineering to author and research the product. Owner ratification is adoption of an exact
  product judgment, not authorship or a professional credential attestation.
- **Wait for several personal observations before creating any floor.** Deferred as the desired
  replacement path. A floor is needed to exercise planning now; longitudinal calibration cannot
  exist before the governed assessment is performed.
- **Reuse the assessment claim-review identity.** Rejected because dynamic ratification metadata
  would make the two independent releases conflict depending on approval order.

## Assumptions and unresolved questions

- The owner remains within the floor's inclusive age bounds when the comparison is made.
- Ten repetitions has no population-validity claim and may yield `MAINTAIN` immediately.
- Meeting the floor does not mean upper-body endurance should disappear from training. The current
  deficit-only strategy and chair-stand-specific construction path still need an owner-relevant
  maintenance/development bridge.
- Personal baseline, repeatability, recovery, and response history should drive a replacement
  `personal_calibration` authority after enough observations exist.

## Consequences

- The existing competency-floor review UI can show the number's scientific and judgment origins
  separately and can ratify both authority chains in one transaction.
- Supporting protocol evidence remains available to downstream planning records, while the numeric
  decision remains traceable to its distinct judgment authority.
- This release does not create a plan, exercise selection, dose, session, medical clearance, or
  permission to perform the assessment.
- The planning-context handoff now accepts the ratified standard-push-up estimate without losing
  the `MAINTAIN` case. The next milestone is to replace the chair-stand-specific construction and
  dose path with owner-relevant push-up authorities.
