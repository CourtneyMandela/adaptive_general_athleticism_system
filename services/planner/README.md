# Planner service boundary

Contains deterministic adaptive-assessment selection, assessment-result recording, conservative
capability estimation, evidence-linked competency-floor detection, configurable priority scoring,
four-state adaptation assignment, and revisionable long-range strategy generation.

The service also constructs stimulus requirements, derives effective-dated environment snapshots,
and resolves exercises with explicit full, partial, or infeasible outcomes.

Milestone 5A adds four-to-six-week block planning, minimum/target weekly resource allocation,
explicit session-prescription contracts, and deterministic scheduling into dated availability
windows. The allocator does not invent demand values. The scheduler does not invent sets, reps,
intensity, rest, or progression rules; it only validates and places supplied prescriptions.
Milestone 5B adds safety-authorized set-level execution recording and descriptive adherence. Actual
performance is stored as a direct workout-result observation; adherence is a separate derived
record with explicit sources, method, and rule version. The recorder refuses blocked decisions and
requires exact acknowledgement of configured modifications. Progression execution, exposure
ledgers, and response-driven replanning remained out of scope for that milestone.

Milestone 5C adds immutable progression decisions and exposure-ledger validation. Explicit,
evidence-linked policies control completion, adherence, effort, technique, adjustment, and
exposure caps. The engine records a decision but does not mutate the prescription.

Milestone 5D applies supported repetitions, sets, or duration progression as a new immutable
prescription linked to both the completed prescription and the authorizing decision. Unsupported
dimensions fail explicitly.

Milestone 6A derives an immutable delivered-dose training response from compatible reassessment
estimates and the exact prescription/execution/adherence chain. A deterministic, evidence-linked
policy reviews the original block hypothesis against explicit meaningful-change targets. Low
delivery or low confidence is inconclusive. The engine does not update capability estimates or
generate the next block.

The session-container correction keeps each `SessionPrescription` item independently versioned
while an explicit `SessionTemplate` groups ordered items into one real workout. The scheduler uses
one availability window per template occurrence, the safety decision applies to the whole session,
and execution/adherence/progression preserve item identity. Typed intensity targets now support
auditable absolute and relative load progression; template generation and scientific dose rules
remain deferred.
