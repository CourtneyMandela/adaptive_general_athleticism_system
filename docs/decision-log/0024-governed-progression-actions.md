# Decision 0024: Governed progression actions

- Status: accepted
- Date: 2026-08-22
- Decision version: `governed-progression-actions@1.0.0`

## Decision

Treat a `SessionPrescription.progression_rule_reference` as the prescription-level assignment to
an exact versioned progression rule. The current-week projection may expose a progression action
only when exactly one persisted `ProgressionPolicy` has that reference and the existing
transactional progression service can evaluate it without requiring the browser to invent a
planning input.

Each prescription receives a typed progression-action state:

- `awaiting_execution` before performed work exists;
- `awaiting_post_session_safety` until the recovery/safety report closes the session;
- `ready` when one matching non-exposure policy uses an automatically supported load or repetition
  adjustment;
- `manual_configuration_required` when exposure validation, revised session duration, or a
  non-automated adjustment dimension is required;
- `policy_unavailable` when no policy or multiple policies match the exact reference;
- `completed` when an immutable progression decision already exists.

Only `ready` exposes a policy ID to the browser. The PWA can then request evaluation through the
existing progression endpoint. It supplies decision and revision timestamps, but all performance,
adherence, post-session safety history, policy thresholds, outcome, adjustment, and revised
prescription content remain backend-owned.

The workout logger also adds an explicit per-exercise technique-constraint report with
`met`/`not met`/`not reported` states. It is never prefilled. This lets a policy that requires a
technique constraint consume an actual report rather than forcing a favorable assumption.

## Reason

The persisted prescription already carries a rule reference selected during planning. Reusing that
exact reference preserves lineage and avoids introducing a second, conflicting assignment model.
Failing closed on missing or ambiguous persisted policies preserves version governance. Restricting
the first browser action to typed load and repetition revisions avoids asking an athlete to choose
exposure caps or revised session-duration budgets.

## Alternatives considered

- Add an athlete-wide current progression policy. Rejected because different prescriptions can
  legitimately use different rules and adjustment dimensions.
- Select the newest or first matching policy. Rejected because recency and database order are not
  approved supersession rules.
- Add a generic policy-list endpoint and let the user choose. Rejected because scientific and
  planning policies are not ordinary daily-user preferences.
- Automatically derive an exposure target from the previous dose. Rejected because the exposure
  ledger requires an explicit proposed target and reviewed cap; a universal increment would be an
  invented training rule.
- Guess revised session duration after set or duration progression. Rejected because that changes
  the resource budget and may affect scheduling.
- Assume technique constraints were met when the workout was marked complete. Rejected because
  completion and technique reporting are distinct observations.

## Evidence and uncertainty

This is an orchestration and provenance decision implementing blueprint sections 37–42, 57, and
73. It adds no training threshold, increment, exposure cap, symptom taxonomy, or scientific claim.
Every operational progression policy still requires its existing evidence links and version.

The meaning and lifecycle of a rule reference as a unique assignment key should eventually be
enforced during policy administration. V1 detects duplicates at read time rather than silently
choosing one. Exposure target proposal, duration-budget revision, unsupported typed dimensions,
policy supersession, and manual approval remain unresolved workflows.

## Consequences

- A normal non-exposure load or repetition rule can close the daily performance-to-progression loop
  without copying business logic into React.
- Missing and ambiguous policy state is visible instead of producing an arbitrary decision.
- Exposure-sensitive progressions remain blocked from one-click evaluation until their governed
  planning inputs exist.
- Existing progression endpoints and immutable decision history remain unchanged.
