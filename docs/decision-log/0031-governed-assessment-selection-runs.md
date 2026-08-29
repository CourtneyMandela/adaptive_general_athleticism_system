# Decision 0031: Governed assessment-selection runs

- Status: accepted provisionally
- Date: 2026-08-27
- Decision version: `governed-assessment-selection-run@1.0.0`

## Decision

Represent athlete-level permission to enter assessment selection as an immutable,
predecessor-linked `AssessmentEligibilityReview`. The review records a bounded outcome of
`SELECTION_ALLOWED`, `SELECTION_BLOCKED`, or `REVIEW_REQUIRED`; the direct observations reviewed;
the screening-process reference; reviewer, rationale, uncertainty, validity interval; and rule
version. It is an authority record, not a diagnosis or medical clearance.

Only the current, unexpired `SELECTION_ALLOWED` review may authorize a new persisted assessment
selection. Each new selection names both that eligibility review and the exact current approved
protocol review. Legacy nullable references remain readable, while new repository writes fail
closed without both authorities.

An authenticated athlete may create an immutable `AssessmentSelectionRun` from one owned
environment and explicit non-medical self-report: body mass when known, domain training history,
exercise-skill tags, and recent-exposure tags. The application derives equipment categories from
effective-dated availability instead of accepting them from the browser. It stores the submitted
context as a direct observation, evaluates only currently approved self-administered definitions,
persists all decisions atomically, and groups them in one run with ordered selection IDs.

Eligibility review is initially available only through a narrow local operator CLI. The ordinary
athlete API cannot create or alter it and accepts no health, injury, or symptom classifications.

## Reason

The reviewed protocol catalog establishes that a test definition is operationally approved; it
does not establish that the test is currently appropriate for a particular athlete. Conversely,
an athlete-level review cannot approve an unreviewed protocol. Both decisions must remain explicit
and traceable.

Persisting the browser's non-medical context as an observation preserves what was actually
reported. Deriving equipment from environment history prevents the athlete request from claiming
equipment that the authoritative environment record does not contain. The run container creates a
stable boundary for later guided execution and result recording without pretending an in-progress
workflow is mutable athlete state.

## Alternatives considered

- Accept `health_screening_completed = true` from the browser. Rejected because a checkbox is not
  a governed screening decision.
- Store raw symptom, injury, or health classifications in this endpoint. Rejected until controlled
  taxonomies, privacy obligations, and escalation ownership are resolved.
- Let an eligibility review approve specific protocols. Rejected because athlete applicability and
  protocol scientific approval are separate authorities.
- Accept equipment categories directly. Rejected because equipment availability is already an
  effective-dated environmental record.
- Create selections without a run container. Rejected because later results need an inspectable
  snapshot of the context and ordered decisions evaluated together.
- Generate capability estimates in the same transaction. Deferred because a result must first be
  performed and stored as a direct observation under a reviewed estimation policy.

## Assumptions and provisional choices

- The initial eligibility outcome is coarse and contains no medical taxonomy. Any constraint means
  the operator uses `SELECTION_BLOCKED` or `REVIEW_REQUIRED`; finer reviewed constraint routing is
  future work.
- Every eligibility review has an explicit positive validity window. No default screening period
  is embedded in software.
- Skill and recent-exposure tags are exact, user-reported strings. Missing tags conservatively
  defer protocols that require them.
- The athlete endpoint evaluates only reviews marked `self_administered`; professionally
  administered protocols remain visible in the global catalog but cannot enter this run type.
- Body mass, training history, skill, and exposure reports are not capability estimates.
- `reviewed_by` is inspectable operator text, not yet a verified professional credential.

## Evidence and uncertainty

This is a safety-authority, provenance, and transaction-boundary decision. It approves no
screening instrument, protocol, medical taxonomy, reassessment interval, or capability formula.
Those remain subject to evidence policy and qualified review.

Production reviewer authorization, credential verification, consent, sensitive-data handling,
controlled taxonomies, escalation ownership, protocol seed review, and jurisdiction-specific
screening requirements remain unresolved.

## Consequences

- Onboarding can progress to an auditable assessment-selection run without browser-controlled
  screening or equipment authority.
- Missing, blocked, review-required, future, or expired eligibility fails before athlete context or
  selection history is written.
- Every run can explain which observations, environment state, athlete review, and protocol review
  produced each decision.
- No real run is available until at least one evidence-reviewed self-administered protocol exists.
- Guided performance recording and conservative estimate creation remain subsequent milestones.
