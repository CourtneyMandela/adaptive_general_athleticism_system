# 0065: Authenticated first-week preparation

- Status: accepted provisionally
- Date: 2026-08-29
- Supersedes: the first-week CLI-only transport boundary in Decision 0044
- Decision version: `authenticated-first-week-preparation@1.0.0`

## Decision

Expose the existing atomic first-week planning service through a `planning_reviewer`-protected HTTP
boundary. The request supplies exact prescriptions, session composition, dated availability, the
exact scheduling policy and current approved review, preparation time, applicability rationale,
and uncertainty. Reviewer identity and the current role assignment are server-owned. The service
revalidates that assignment and records it in the immutable decision lineage.

Add a purpose-specific preparation projection for one block. It returns each allocation with its
resource demand, adaptation, stimulus, resolution, and selected exercise; athlete environments;
every scheduling policy with its current review; existing first-week plans; and the observations
and evidence claims referenced by those chains. It does not mark a policy selected or derive any
dose, session grouping, frequency, availability window, or calendar placement.

Add a provisional `/review/weeks` PWA preparation screen and typed browser client. The screen is
read-only at this increment: it makes required lineage and readiness visible, while the client
contract can submit a complete externally constructed request. A field-by-field authoring form is
deferred until it can represent all supported intensity targets and arbitrary session composition
without narrowing the domain model or supplying hidden defaults.

## Reason

The block workflow now produces real allocation decisions, but Week 1 remained accessible only by
local JSON and CLI. Authentication and role history now provide the authority foundation that
Decision 0044 required. Reusing the existing atomic service retains deterministic scheduling and
prevents partially persisted authoritative prescriptions.

The preparation projection gives a reviewer the information needed to make decisions without
pretending allocated minutes determine sets, repetitions, intensity, rest, grouping, or calendar.

## Alternatives considered

- Generate prescriptions from allocation minutes. Rejected because resource allocation does not
  establish a scientifically or individually valid exercise dose.
- Add a simplified form supporting one intensity type and one all-exercises session. Rejected
  because it would silently narrow prescription semantics and invent session grouping.
- Persist editable prescription and session drafts. Deferred because draft supersession,
  author/approver separation, and partial-authority semantics are not yet defined.
- Continue with only the local CLI. Rejected because the authenticated reviewer role can now bind
  authority safely and the PWA needs an inspectable path toward the first usable week.
- Automatically choose the only approved policy. Rejected because cardinality is not
  applicability and selection must remain explicit.

## Evidence

This is an authorization, provenance, and workflow decision implementing blueprint sections
16, 33–36, 52, 60, 64, 73, 77, and 89. It introduces no training dose, scheduling, progression, or
exercise-equivalence claim.

## Assumptions and uncertainty

- One active planning reviewer may provisionally author and approve Week 1 inputs.
- Existing local CLI commands remain supported and intentionally lack account-role lineage.
- The projection includes only observations and evidence already cited by the block/demand/stimulus
  and current scheduling-policy review chains; it does not expose unrelated athlete history.
- Multiple first-week plans remain visible and ambiguous; no current-plan rule is invented.
- Production credential verification, reviewer qualifications, author/approver separation, and a
  governed draft model remain unresolved.

## Consequences

- Reviewer-authenticated Week 1 writes are server-attributed and atomically auditable.
- A withdrawn, mismatched, future-dated, or superseded scheduling-policy review still fails closed.
- The PWA can inspect the exact block-to-prescription boundary without generating a workout.
- The next increment is a complete structured authoring form, followed by pre-session safety and
  execution of the resulting feasible week.
