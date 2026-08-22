# 0017: Transactional weekly-plan use case

- Status: accepted provisionally
- Date: 2026-08-22
- Decision version: `transactional-weekly-plan-use-case@1.0.0`

## Decision

Add `POST /v1/blocks/{block_id}/weekly-plans` as the transactional application boundary from a
persisted feasible block to one dated weekly plan.

The caller supplies explicit prescription drafts keyed by resource-allocation ID, explicit session
container drafts whose items use those same allocation IDs, dated availability windows, a
persisted weekly-scheduling policy ID, and one preparation timestamp. Prescription drafts contain
the complete dose, intensity targets, rest, fatigue classification, progression-rule reference,
provenance, rationale, and rule version. Session drafts contain explicit composition, order,
frequency, duration, fatigue, provenance, and version.

The service derives athlete, block, adaptation, exercise-resolution, selected-exercise, and newly
generated prescription identities from persisted state. It constructs availability and session
containers, delegates scheduling to the deterministic `WeeklyScheduler`, and appends all
prescriptions, templates, availability, and the weekly plan in one transaction. Both feasible and
explicitly infeasible scheduling results may be persisted.

## Reason

The deterministic scheduler and persistence mappings already existed, but callers had to assemble
and persist the whole chain manually. That allowed partial writes and made it easy to mismatch a
prescription with an allocation or exercise. The application service makes the legal sequence the
only exposed write path while retaining the separation between block allocation, dose,
within-session composition, and calendar scheduling.

## Alternatives considered

- Generate sets, repetitions, intensity, or session composition from adaptation names: rejected
  because the repository has no reviewed scientific policy authorizing those choices.
- Accept complete `SessionPrescription` objects from the client: rejected because athlete,
  adaptation, selected exercise, resolution, and block identities are derivable and must not be
  forgeable transport inputs.
- Automatically create one session per allocation: rejected because that silently decides
  session composition and prevents explicit multi-item containers.
- Persist only feasible weeks: rejected because an infeasible schedule with explicit issues is a
  valuable planning result and must not disappear.
- Split prescriptions, templates, availability, and scheduling into raw CRUD endpoints: rejected
  because failures could leave an incomplete authoritative chain.

## Evidence and uncertainty

This is an application consistency decision implementing blueprint sections 33–37, 54, 60,
64–65, 73–74, and 89. It introduces no scientific dose or recovery claim. Every material dose and
scheduling-policy value remains an explicit versioned input requiring upstream governance.

## Assumptions and unresolved questions

- One preparation timestamp is provisionally used for prescriptions, session containers,
  availability recording, and plan generation.
- Session-template drafts refer to allocation IDs because prescription IDs are generated inside the
  transaction.
- V1 uses the block allocation's existing resolution; environment-driven re-resolution remains a
  separate governed operation.
- Empty-training weeks, plan idempotency, current-plan selection, rescheduling, and approval states
  remain unresolved rather than being guessed.

## Consequences

- A block can now produce a persisted, dated week without raw planning CRUD.
- Prescription exercise identity cannot diverge from the persisted block resolution.
- Session composition and dose remain explicit instead of becoming hidden generator defaults.
- Scheduling infeasibility remains inspectable through structured issues.
- A late persistence failure rolls back the entire prescription-to-week chain.
