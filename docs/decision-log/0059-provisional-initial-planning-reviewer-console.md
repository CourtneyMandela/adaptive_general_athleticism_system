# 0059: Provisional initial-planning reviewer console

- Status: accepted
- Date: 2026-08-29
- Decision version: `initial-planning-reviewer-console@1.0.0`

## Decision

Add a separate `/review` PWA route for an authorized planning reviewer to parse, inspect, confirm,
and submit an externally prepared initial-planning document. Keep the athlete experience separate.

The console validates the transport shape, UUIDs, bounded component values, timestamps, duplicate
identifiers, and protected-field absence before presenting a structured preview. Submission sends
the exact previewed document to the authenticated endpoint from Decision 0058. It does not accept
or derive reviewer identity, choose policy or floor versions, infer component values, or create a
block or workout. Backend validation remains authoritative.

## Reason

The authenticated application boundary is operational but a reviewer otherwise needs raw HTTP
tooling. A small two-step console makes the boundary usable and inspectable without pretending the
system can author scientific-applicability judgments that have not yet been modeled.

## Major implementation choices

- Use a distinct reviewer route rather than adding controls to the athlete planning-status panel.
- Require externally prepared JSON because governed policy, floor, and candidate-context authoring
  workflows do not yet exist.
- Parse into a normalized typed request and preview exactly that object before submission.
- Reject `reviewed_by`, `review_authority_assignment_id`, and all other unsupported fields.
- Require an explicit confirmation after preview and invalidate the preview whenever source text or
  athlete identity changes.
- Display the immutable strategy and decision receipt, including priority states and evidence audit.

## Alternatives considered

- Add editable score sliders. Rejected because they make unsupported values easy to manufacture and
  obscure where the reviewed context originated.
- Submit raw JSON directly. Rejected because the reviewer should see the exact policy, review,
  provenance, uncertainty, and candidate values before the irreversible write.
- Place reviewer controls on the athlete page. Rejected because athlete ownership and reviewer
  authority are different security and product roles.
- Build policy, floor, evidence, and candidate authoring in the same milestone. Deferred because it
  would substantially broaden both scientific governance and UI scope.

## Evidence

This is an interface and application-security decision. It makes no training-science claim. The
reviewer role remains an application permission rather than proof of professional qualification.

## Assumptions

- The provisional development deployment can supply a reviewer bearer through
  `NEXT_PUBLIC_AGAS_REVIEWER_TOKEN`.
- Reviewed documents are prepared outside the PWA until governed authoring workflows exist.
- Client validation improves review usability but never replaces backend validation.
- Initial strategy creation remains intentionally irreversible except through later review-linked
  replanning.

## Unresolved questions

- What first-party workflow should author and approve candidate-context component values?
- Which evidence and competency-floor details should be retrievable inline during review?
- Should production deployments require separate author and approver accounts?
- How should incomplete review drafts be stored without weakening append-only accepted decisions?

## Consequences

The first-strategy boundary can now be exercised from the PWA with a visible, explicit review step
and an auditable receipt. It remains an internal provisional tool, not a complete scientific
governance workspace or an athlete self-service feature.
