# 0138 — Governed jump-response interpretation

Date: 2026-09-24

Status: accepted provisionally

Decision version: `owner-alpha-jump-response-interpretation@1.0.0`

## Decision

Extend the digest-locked owner-alpha explosive-power construction release with two post-block
authorities that are ratified in the same explicit planning-review transaction as the jump dose,
progression, exposure, scheduling, and safety rules:

- a `BlockReviewPolicy` requiring at least 80 percent aggregate adherence and at least low response
  confidence; and
- a response-evaluation authority for the exact
  `assessment_specific:countermovement_vertical_jump_height_cm` scope, centimeter unit,
  explosive-power adaptation, higher-is-better direction, and a provisional 2 centimeter minimum
  meaningful change.

Classify every numeric value as engineering judgment. The 2 centimeter threshold is four increments
of the governed 0.5 centimeter entry resolution; it is not represented as a published minimal
detectable change, a universal responder threshold, or evidence that training caused the change.

After the release is ratified, post-block preparation may construct an exact response
interpretation only when it finds one strategy baseline and one post-block reassessment with the
matching domain, scope, and unit. It groups only prescriptions for the matching adaptation and
exposes the authority identity, digest, rationale, uncertainty, policy, estimates, and threshold to
the reviewer. Missing or ambiguous matches produce a visible preparation issue instead of a guess.

The reviewer interface pre-populates the exact prepared interpretation but retains explicit
confirmation. The completed-block write accepts an optional response-authority identity and
revalidates the ratified digest, bundled policy, adaptation, estimate semantics, comparison
direction, and threshold on the server. A stale, absent, or altered authority fails closed. The
decision audit retains the authority, candidate, and content digest.

## Reason

The completed-block engine already reconstructs all delivery, adherence, and safety history and
derives observed change. Its production gap was authority: the reviewer still had to invent a
metric-specific threshold in the form. That contradicts the owner-alpha operating model and risks
turning a browser value into an unreviewed scientific claim.

Bundling the narrow response authority with the exact jump-training release keeps the initial
training hypothesis and its later evaluation rule inspectable together while preserving distinct
records for observations, estimates, delivered dose, response arithmetic, and review decisions.

## Alternatives considered

- Infer a generic percentage change from the baseline. Rejected because percentage precision does
  not supply a validated reliability or meaningful-change rule.
- Treat one 0.5 centimeter entry increment as meaningful. Rejected because that would equate input
  resolution with measurement reliability.
- Use the 20 centimeter competency floor as the response threshold. Rejected because a competency
  comparison point and within-person change threshold answer different questions.
- Continue asking the owner to type a threshold. Retained only as the existing expert/manual
  fallback; it is not the prepared owner-alpha path.
- Claim 2 centimeters as a source-derived minimal detectable change. Rejected because the reviewed
  sources do not establish that result for the self-administered wall-marking protocol.

## Evidence

The bundled Oxfeldt et al. evidence supports only the broad proposition that multiweek lower-body
plyometric training can improve jump performance in healthy adults. The exact adherence cutoff,
confidence requirement, and 2 centimeter threshold are accountable AGAS engineering priors. The
assessment protocol's reviewed 0.5 centimeter entry resolution supplies context, not validation of
the threshold.

## Uncertainty

Wall-marked jump height can vary with reach position, parallax, fingertip marking, wall setup,
footwear, warm-up, familiarization, and effort. The 2 centimeter rule may be too sensitive or too
conservative for this athlete. Repeated personal measurements or a validated device-specific
protocol may justify a superseding authority. One supported block still does not establish a stable
personal response profile or genetic explanation.

## Consequences

- Ratifying the explosive-power construction release now installs a reusable block-review policy
  and an exact, content-addressed response authority.
- A matching completed jump block can reach the review form without asking the owner to author the
  meaningful-change number.
- Block review remains explicit and reviewer-owned; no candidate is auto-ratified and no response is
  auto-approved.
- The next product task is to prepare and server-bind the successor replanning context from the
  previously approved planning context plus the reviewed follow-up estimate, then construct the next
  block from that immutable successor strategy.
