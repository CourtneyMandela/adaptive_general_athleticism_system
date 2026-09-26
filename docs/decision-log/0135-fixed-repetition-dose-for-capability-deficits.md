# 0135 — Fixed repetition dose for capability deficits

Status: accepted

Date: 2026-09-23

Decision version: `fixed-capability-repetition-dose@1.0.0`

## Decision

Add a separate immutable `FixedRepetitionDosePolicy` for ordinary capability-development work whose
assessment value is not dimensionally convertible into training repetitions. A derived fixed dose
requires the exact matching chain of:

```text
DEVELOP adaptation priority
→ below-floor capability need
→ current matching capability estimate
→ domain-matched adaptation
→ reviewed fixed-dose policy
→ separate progression authority
```

The estimate scope, estimate identity, capability-need identity, priority identity, source
observations, policy identity, numeric-value origin, and authority reference remain in the derived
output. The estimate's numeric value is never used in dose arithmetic. The policy supplies the
fixed sets and repetitions and enforces a maximum initial total.

Fixed-dose values must identify their origin as `engineering_judgment`, `professional_judgment`, or
`scientific_evidence`. A scientific numeric origin is invalid without an evidence claim. The policy
and ordered evidence links persist as immutable PostgreSQL/SQLAlchemy records. The existing
training-construction ratification and prepared-first-week paths accept exactly one of an
assessment-fraction repetition policy, fixed repetition policy, or introductory-exposure policy.

## Reason

The first owner-alpha training slice derives push-up repetitions as a bounded fraction of a maximum
repetition assessment. That transformation is dimensionally coherent for the same repeated task.
It is not coherent for countermovement-jump height: centimeters cannot determine a safe or useful
number of jump contacts. Reusing the existing policy would encode false precision and hide the
authority for the contact count.

The introductory-exposure policy also cannot be reused. It exists to satisfy a recent-exposure
prerequisite before assessment and explicitly does not establish a capability deficit or ordinary
training priority. The new policy preserves that separation while enabling a future governed
explosive-power training slice.

## Alternatives considered

- Multiply jump height by a fraction to obtain repetitions: rejected as dimensionally and
  scientifically invalid.
- Reuse the introductory jump-exposure dose: rejected because assessment preparation and
  capability development have different reasons, gates, and provenance.
- Put fixed repetitions directly into first-week construction: rejected because the numeric
  authority, uncertainty, evidence, and replacement history would be hidden.
- Require the estimate value to change the fixed starting dose: rejected until a reviewed rule can
  justify how the measurement should alter contacts.
- Create an operational jump-training candidate in the same change: deferred because the need or
  floor, exercise/resource authority, exact dose values, and scientific applicability still require
  separate preparation and owner review.

## Evidence and owner-review boundary

This decision creates an authority mechanism, not a training recommendation. The implementation
adds no operational sets, repetitions, effort, rest, jump threshold, scientific claim, or owner
approval. Tests use synthetic values explicitly labeled as software fixtures. Any owner-alpha
candidate must still present its evidence-supported uses, unsupported numeric choices, safety
constraints, exact digest, and planning-reviewer attestation.

## Assumptions and uncertainty

- Fixed repetition doses are appropriate only when a reviewed candidate can justify one bounded
  starting exposure and honestly label the numeric origin.
- The first version authorizes only below-floor `DEVELOP` lineage. `MAINTAIN` and `EXPOSE` fixed
  doses need separately specified policy semantics rather than silent reuse.
- The maximum applies to the initial derived dose. Subsequent progression remains governed by the
  separate progression policy and existing immutable prescription-revision path.
- A current estimate is still required even though its value is not transformed; it establishes
  the exact assessed construct, athlete state, staleness, and observation provenance.

## Consequences

- The next explosive-power slice can retain countermovement-jump height as centimeters while a
  separately reviewed policy governs contacts.
- Training-construction candidates can ratify and persist fixed-dose authority atomically with
  scheduling, progression, and safety authority.
- Prepared first-week construction can generate and persist the resulting prescription without a
  special workout generator or client-authored values.
- The next task is to prepare—not automatically ratify—the exact jump/power need, resource, evidence,
  and fixed-dose candidates needed for an owner-reviewable vertical slice.
