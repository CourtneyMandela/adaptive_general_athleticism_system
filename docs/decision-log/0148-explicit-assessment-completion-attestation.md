# 0148 — Explicit assessment-completion attestation

## Decision

Require every completed assessment-performance command to attest that the athlete completed the
exact reviewed protocol and that no listed stop condition occurred. Enforce both facts at the API
boundary, retain them in the append-only result observation context, and expose the same boundary
in the athlete-facing result form.

When an athlete reports stopping early or encountering a stop condition, the current interface
must not submit a completed result. It must explain that the attempt is not a zero and that AGAS
does not yet persist incomplete assessment attempts. This slice does not infer a diagnosis, invent a
replacement score, or silently convert an incomplete protocol into capability evidence.

## Reason

The high-effort 12-minute walk/run path previously displayed its protocol and stop conditions but
accepted an ordinary numeric result without proving that the reviewed protocol was completed. A
zero or partial distance submitted through that path could therefore be mistaken for a valid direct
performance observation and flow into a capability estimate. The distinction between attempted,
stopped, and completed performance is material safety and provenance, not presentation detail.

## Alternatives considered

- Rely on instructional text alone. Rejected because the server would still accept an ambiguous
  result from an old, altered, or non-browser client.
- Treat a stopped attempt as zero. Rejected because zero would falsely represent completed
  performance and could create a spurious deficit estimate.
- Store a stopped attempt in the existing result observation with a flag. Rejected because result
  observations are eligible assessment evidence; overloading them would weaken the completed-result
  invariant.
- Add the full incomplete-attempt persistence model in the same change. Deferred so this safety
  boundary remains small and replaceable. The future model must be append-only and must not make an
  incomplete attempt eligible for capability estimation.

## Evidence

No new scientific claim is introduced. The change preserves the exact protocol and stop conditions
already bound to the reviewed assessment definition. Automated tests verify client-side command
construction, API rejection of incomplete and safety-stopped submissions, retention of both
attestations in observation context, and the phone interaction that prevents a stopped attempt from
being submitted as completed.

## Uncertainty

An athlete attestation is a factual report, not independent verification that the protocol was
performed correctly. The application does not yet retain why or when an incomplete attempt stopped,
and it cannot yet distinguish abandonment, equipment failure, route problems, symptoms, or another
context without a separate governed attempt model.

## Consequences

- A completed assessment result has an explicit, server-enforced protocol-completion contract.
- A safety-stopped attempt cannot become a zero score, direct performance result, or capability
  estimate through the completed-result endpoint.
- The result observation retains the attested completion and stop-condition facts for provenance.
- Existing API clients must send both required booleans when recording a completed result; the rule
  version advances to `assessment-performance-recording@1.1.0`.
- The next product task is an append-only incomplete/stopped assessment-attempt record that remains
  categorically separate from valid result observations and derived estimates.

## Version/date

- Decision version: `explicit-assessment-completion-attestation@1.0.0`
- Date: 2026-09-25
