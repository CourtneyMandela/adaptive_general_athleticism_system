# 0092 — Prepared priority-policy candidate

Date: 2026-09-09

Status: accepted as a prepared owner-alpha candidate; not ratified by this change

Decision version: `planning-governance-candidate@1.0.0`

## Decision

Add one server-owned, immutable candidate for a conservative initial-planning priority policy. The
owner-facing review page presents the policy's narrow scope, exact operational choices, evidence,
and unresolved limitations. Ratification submits only the candidate version, SHA-256 content
digest, and a true attestation. The server binds the authenticated `planning_reviewer` account and
exact active role assignment, then atomically stores the evidence source snapshot, extracted
claim, evidence review, policy, policy review, and decision record.

The candidate makes capability deficit the strongest benefit input, discounts low-confidence
state, gives unknown confidence no adjusted benefit, charges explicit fatigue/time/interference
cost, and permits no more than two simultaneous `DEVELOP` assignments. These numbers are a
versioned engineering prior, not estimates taken from research. Changed values require a new
candidate and review.

Ratification does not create a competency floor, athlete-specific candidate context, strategy,
block, exercise, dose, session, or workout. Those remain separately governed steps.

## Reason

The existing planning engine and audit trail are functional, but initial planning still requires a
reviewed priority policy. Requiring the owner to author weights or paste administrative JSON
misassigns engineering and evidence-synthesis work and encourages uninspectable arbitrary values.
A prepared candidate lets engineering do that work while preserving explicit owner oversight and
the product's fail-closed boundary.

## Evidence

The bundled claim is extracted from the 2026 American College of Sports Medicine position stand,
PMID 41843416. It reports that progressive resistance training improved multiple muscle-function
and physical-performance outcomes across 137 systematic reviews representing more than 30,000
healthy adults.

That source supports the broad usefulness of resistance training. It does **not** validate the
candidate's priority weights, thresholds, maximum-development count, an athlete-specific priority,
or a workout. The stored claim, review, presentation, and policy all state that boundary.

## Alternatives considered

- **Ask the owner to author the policy.** Rejected because the owner is supervising the product,
  not supplying scientific or algorithmic values.
- **Install hidden runtime defaults.** Rejected because material planning rules must be versioned,
  reviewable, and reproducible.
- **Ratify automatically during deployment.** Rejected because deployment is not approval and the
  exact candidate should remain visible before authority is granted.
- **Bundle a competency floor and first strategy immediately.** Deferred because a useful chair-
  stand floor needs a separately defensible applicability rule; one broad training source cannot
  establish it.
- **Wait for scientifically optimized ranking weights.** Rejected as an unrealistic standard. The
  replaceable heuristic is transparent, bounded, tested, and clearly distinguished from evidence.

## Assumptions and provisional choices

- The owner-alpha account has an active `planning_reviewer` assignment.
- A maximum of two `DEVELOP` states is a conservative capacity control, not a universal law.
- Deficit receives four times each other benefit weight; unknown, low, moderate, and high
  confidence multipliers are `0`, `0.5`, `0.75`, and `1`. Cost penalty is `0.25`. These values must
  be evaluated with counterfactual tests and personal-response data.
- The evidence review uses abstract-level PubMed extraction. Full-text conflict and methods review
  is required before broader production use.

## Unresolved questions

- What structured age and population applicability rules should competency floors enforce?
- Which first chair-stand floor can be defended without treating a reference distribution as a
  health, safety, or universal athletic threshold?
- Should later multi-domain policies use different weights or development-capacity limits?
- When should organizational policy require separate policy authors and approvers?

## Consequences

- Engineering can prepare a policy and the owner can approve exact content without authoring JSON.
- Ratification is append-only, attributable, content-addressed, atomic, and idempotent.
- Approved policy state becomes available to initial-planning preparation without generating a
  plan prematurely.
- The next blocker remains a population-applicable competency-floor candidate, followed by a
  reviewed athlete-specific planning-context proposal.
