# Decision 0030: Reviewed assessment-definition catalog

- Status: accepted provisionally
- Date: 2026-08-22
- Decision version: `reviewed-assessment-catalog@1.0.0`

## Decision

Keep immutable `AssessmentDefinition` protocols separate from their governance state. Add an
append-only `AssessmentDefinitionReview` history for each definition. Reviews form one linear,
positive sequence and every replacement names the current predecessor. Each review stores its
decision, ordered administration and result-entry instructions, reassessment interval,
self-administration status, evidence-claim identifiers, reviewer, review time, applicability,
uncertainty, and version.

Only a definition whose latest review is `APPROVED` may appear in the read-only global assessment
catalog or be referenced by a persisted athlete assessment selection. A later `REJECTED` or
`NEEDS_REVISION` review withdraws the definition without deleting the prior approval or protocol.
Every new persisted selection stores the exact approving review ID. The migration leaves this
reference nullable only for pre-existing selections, which remain readable as legacy history. The
API has no protocol-review write endpoint, and this milestone seeds no assessment protocols.

## Reason

The deterministic selector can evaluate protocol constraints, but existence in the database does
not establish scientific validity, safe self-administration, applicability, or complete operating
instructions. A separate review history makes that authority explicit and lets a later evidence or
safety concern withdraw an approval while preserving every historical selection and decision.

The review and definition are separate because a governance decision can change when evidence or
applicability changes even if the protocol text does not. Linear sequencing prevents competing
current approvals.

## Alternatives considered

- Put `approved = true` on `AssessmentDefinition`. Rejected because changing it would mutate an
  immutable protocol and erase approval history.
- Treat any persisted definition as approved. Rejected because database existence is not evidence
  review.
- Delete or edit a withdrawn definition. Rejected because prior selections and observations must
  keep their original meaning.
- Seed familiar field tests from model memory. Rejected because protocol details, applicability,
  reliability, and norms require checked scientific provenance.
- Build sensitive screening and guided assessment in the same milestone. Deferred until controlled
  intake taxonomies, health-data obligations, escalation ownership, and qualified review are
  resolved.

## Assumptions and provisional choices

- One review is current per immutable definition; replacement is append-only and chronological.
- Every review decision, including rejection or needs revision, requires at least one evidence
  claim so its basis is inspectable.
- Approved reviews require a positive reassessment interval. The value is reviewed protocol data,
  not a software default.
- The public catalog may expose reviewed protocol and provenance metadata because it contains no
  athlete state. Athlete assessment execution will remain authenticated and ownership-scoped.
- `reviewer` is currently an inspectable label, not a verified professional credential or account
  foreign key.

## Evidence and uncertainty

This is an evidence-authority and auditability decision; it does not approve any particular test
or make a scientific training claim. Operational protocols still require source verification and
qualified review under `docs/evidence-policy.md`.

Reviewer authorization, credential verification, protocol retirement across jurisdictions,
controlled health and symptom taxonomies, consent, retention, referral ownership, and production
assessment evidence remain unresolved.

## Consequences

- Unreviewed and withdrawn definitions fail closed at the persistence boundary.
- Historical approvals, withdrawals, selections, observations, and estimates remain intact; new
  selections name their authorizing review.
- The PWA can later consume exact reviewed instructions without inventing protocol steps.
- The catalog will correctly remain empty until real protocols are curated and approved.
- Adaptive intake and assessment execution remain the next milestone rather than being simulated.
