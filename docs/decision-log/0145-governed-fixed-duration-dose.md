# 0145 — Governed fixed-duration dose authority

## Decision

Add `FixedDurationDosePolicy` as a first-class, immutable planning authority for capability paths
whose initial prescription is expressed as time rather than repetitions or load. A policy is scoped
to one adaptation, assessment estimate scope, and `DEVELOP` or `MAINTAIN` priority state. It stores
the exact set count, seconds per set, maximum initial total seconds, effort range, technique
constraints, session envelope, progression reference, authority kind, rationale, uncertainty, and
version.

The matching capability estimate remains lineage and applicability input. Its numeric value is not
converted into training seconds. Training-construction ratification, first-block authority checks,
prepared-week projection, weekly prescription construction, persistence, and the owner review UI
all recognize the new typed authority. No aerobic assessment, floor, dose value, or operational
candidate is approved by this decision.

## Reason

AGAS cannot construct an aerobic capability slice honestly with a repetition-only dose model. A
field-test distance and a training duration are different quantities, and deriving one from the
other without a reviewed rule would collapse an observation into an ungoverned prescription.

A typed duration authority preserves the required chain:

`observation -> estimate -> need -> priority -> adaptation -> reviewed duration policy -> prescription`

It also lets the existing execution boundary record actual duration without pretending that the
assessment result itself supplied the starting dose.

## Alternatives considered

- Store duration in an exercise metadata blob. Rejected because this would hide material planning
  authority outside the ratified dose and prescription lineage.
- Reuse `RepetitionDosePolicy` and reinterpret repetitions as minutes. Rejected because units and
  progression semantics would be false.
- Convert field-test distance directly into seconds. Rejected because no reviewed scientific or
  engineering rule authorizes that arithmetic.
- Add an aerobic candidate and hard-code its duration in prepared-week code. Rejected because it
  would bypass governance and make the runtime the concealed training authority.
- Wait until a complete aerobic evidence package is selected. Rejected because the missing typed
  primitive is independently useful, replaceable, and testable without approving content.

## Evidence

- `AGENTS.md` requires observations, derived estimates, planning decisions, and prescriptions to
  remain distinct and requires material rules to be versioned.
- `docs/MASTER_BLUEPRINT.md` requires planning to determine a stimulus before exercise and dose,
  and requires progression dimensions to remain explicit rather than assuming load progression.
- The existing `SessionPrescription` and execution models already distinguish repetitions from
  duration, so the new authority completes rather than replaces that typed boundary.
- Unit and integration regressions demonstrate estimate-value invariance, priority/need/scope and
  staleness checks, immutable persistence, digest-locked ratification, and duration-based first-week
  construction.

## Uncertainty

This decision establishes software authority semantics only. It does not determine which aerobic
field assessment is appropriate for the owner, what competency floor is meaningful, which modality
is feasible in the owner's environment, what starting duration is suitable, or how duration should
progress. Those require a separate evidence/applicability review and explicit owner ratification.

The current automatic post-session endpoint still admits only its already governed automatic
dimensions. A future aerobic release must either provide and test a safe duration-progression
contract or deliberately hold duration constant until block review.

## Consequences

- Duration policies are queryable and immutable in PostgreSQL, with ordered evidence lineage and
  an explicit engineering/professional/scientific numeric origin.
- A configured dose must fit both its maximum-initial-duration cap and its planned session envelope.
- Training-construction releases must contain exactly one dose authority; fixed duration is now one
  valid option.
- Prepared first-week candidates expose exactly one of repetitions or seconds per set, and weekly
  prescriptions carry `duration_seconds` rather than fabricated repetitions.
- Existing repetition, fixed-contact, and introductory-exposure paths remain unchanged.
- The next source task is to prepare a reviewable aerobic assessment/evidence/floor/resource/
  construction slice, including a deliberately scoped duration-progression or hold policy. It must
  remain unavailable to planning until the owner ratifies each exact candidate.

## Version/date

- Decision version: `governed-fixed-duration-dose@1.0.0`
- Date: 2026-09-25
