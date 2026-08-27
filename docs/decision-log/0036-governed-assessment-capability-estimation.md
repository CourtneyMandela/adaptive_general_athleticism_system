# Decision 0036: Governed assessment capability estimation

- Status: accepted provisionally
- Date: 2026-08-27
- Decision version: `governed-assessment-capability-estimation@1.0.0`

## Decision

Persist `CapabilityEstimationPolicy` as immutable, append-only governance history bound to an exact
`AssessmentDefinition` and the exact approved `AssessmentDefinitionReview` whose protocol it
interprets. Policy revisions form one linear predecessor chain per definition. A policy records its
decision, evidence claims, reviewer, review time, applicability, uncertainty, observation contract,
validity window, calculation method, and rule version. Only the current approved policy may create
new assessment-derived capability state.

Create an assessment capability estimate through a narrow authenticated application boundary. The
server resolves the current policy; the browser cannot submit a formula, confidence, source list, or
derived value. Candidate sources are restricted to persisted performances of the same athlete,
exact assessment definition, and exact protocol review, within the reviewed observation window.
The existing conservative estimator copies the latest protocol-specific measurement, caps
confidence, and does not introduce norms or population interpretation.

Every resulting `CapabilityEstimate` records both the policy and the performance that triggered the
derivation. The database permits one interpretation per `(triggering performance, policy)` pair, so
retries return the same immutable estimate while a future policy version may append a new historical
interpretation. Assessment-specific estimates require both lineage fields and all source observations
must be governed results from the policy's definition.

The assessment workflow projection exposes direct result and derived estimate separately, including
confidence, validity, calculation/rule version, and policy identity. It reports when interpretation is
unavailable because no approved policy exists rather than manufacturing a score.

## Reason

Recorded assessment results are observations, not athlete capability truth. The blueprint requires a
separate capability-estimation layer with source references, confidence, staleness, method, and rule
version. Before this decision the estimator existed only as domain code and its policy was neither
persisted nor evidence-governed, so no safe application boundary could use it.

Binding policy to an exact reviewed protocol prevents a later change in test instructions or units
from silently changing the meaning of historical measurements. Restricting sources through
`AssessmentPerformance` prevents an unrelated manual observation with the same type from entering a
governed estimate.

## Alternatives considered

- Create an estimate immediately when recording a result. Rejected because measurement recording
  must remain valid when interpretation policy is absent, withdrawn, or awaiting review.
- Let the client choose a policy or send a derived value. Rejected because it would move scientific
  authority into an untrusted presentation boundary.
- Treat the newest matching observation type as sufficient provenance. Rejected because imported or
  manual observations can share a type without sharing the governed assessment protocol.
- Overwrite the prior estimate when policy changes. Rejected because it destroys the history of what
  the system concluded under each rule version.
- Add population norms or competency thresholds now. Deferred; they require their own evidence and
  applicability review and are not necessary to preserve a protocol-specific estimate.

## Assumptions and provisional choices

- Policy governance reuses the assessment review decisions `approved`, `needs_revision`, and
  `rejected` because the policy is part of the assessment interpretation chain.
- The current conservative calculation is an identity interpretation of a protocol-specific metric,
  not a claim that the number generalizes to the whole capability domain.
- A single result produces low confidence; multiple compatible results can reach moderate confidence,
  but this software rule is provisional and must itself be supported by an operational policy.
- Policy creation remains an operator/data-governance operation in this milestone; no athlete-facing
  UI can author or approve scientific policies.

## Evidence and uncertainty

No production policy or scientific claim is seeded by this change. Tests use synthetic evidence and
protocol fixtures solely to verify software behavior. An installation without a reviewed policy will
retain the direct observation and explicitly report that capability interpretation is unavailable.

## Consequences

- The observation-to-estimate boundary is now persisted, evidence-linked, versioned, and auditable.
- Repeated API requests cannot create duplicate interpretations under the same policy.
- Withdrawn or superseded policies remain queryable but cannot authorize new estimates.
- Real protocol policies, qualified review workflows, invalidation/correction records, normative
  interpretation, and competency-floor application remain future work.
