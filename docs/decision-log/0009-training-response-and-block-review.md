# 0009: Training response and block review

- Status: accepted provisionally
- Date: 2026-08-19
- Decision version: `training-response-review@1.0.0`

## Decision

Milestone 6A adds two immutable derived layers without updating athlete state:

```text
compatible baseline/follow-up CapabilityEstimates
+ block prescriptions/executions/adherence
-> TrainingResponse

BlockPlan hypothesis + TrainingResponses + safety history
+ versioned BlockReviewPolicy and explicit evaluation thresholds
-> BlockReview
```

`TrainingResponse` retains the intended adaptation, intervention summary, prescribed and actual
dose, adherence, baseline/follow-up estimates, observed numeric change, measurement uncertainty,
context, confidence, observations, and rule version. It is empirical history, not a genetic claim.

Each block-review evaluation stores its response, comparison direction, minimum meaningful change,
and whether the threshold was met. Insufficient delivery or confidence is `INCONCLUSIVE`; all
targets met is `SUPPORTED`, some is `PARTIALLY_SUPPORTED`, and none is `NOT_SUPPORTED`. Thresholds
and minimum delivery rules are explicit, evidence-linked inputs rather than scientific defaults.
Safety history is preserved as context and never reinterpreted medically.

## Reason

The closed loop must compare the original hypothesis with what was actually delivered and measured
before changing capability state or planning another block.

## Alternatives considered

- Update capability estimates during review: deferred to keep observation, response, and state
  transitions independently auditable.
- Infer response from workout performance alone: rejected; reassessment and uncertainty matter.
- Label low-adherence blocks ineffective: rejected because the intervention was not adequately
  tested.
- Use one hidden universal change threshold: rejected because metrics and measurement error differ.

## Evidence, assumptions, and uncertainty

This implements blueprint sections 45–48 and 74 as product architecture. No operational response
threshold is seeded. V1 requires numeric, scope-compatible estimates and one dose unit per response.
Context remains explicit and does not imply causality. Applying review results to athlete state and
creating the next block remain later milestones.

## Consequences

- Block outcomes can distinguish lack of delivery, uncertain measurement, and observed response.
- Personal history remains descriptive and cannot become a genetic ceiling claim.
- Later state updates can cite an immutable review rather than recomputing history silently.
