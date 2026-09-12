# 0116 — Professional-judgment floor authority and proposal stage

Date: 2026-09-12

Status: accepted

Decision version: `competency-floor-authority@1.0.0`

## Decision

Add a distinct, append-only `CompetencyFloorAuthority` path for floor values whose operational
basis is professional judgment or personal calibration rather than a scientific claim. The
authority stores its exact statement, scope, intended population, rationale, applicability,
uncertainty, limitations, author and qualification context, optional supporting evidence, semantic
version, and canonical SHA-256 digest. A separate sequenced review stores the approval decision,
reviewer, timestamp, explicit attestation, uncertainty, and supersession lineage.

A `CompetencyFloor` and its review may cite reviewed evidence claims, approved judgment authorities,
or both. A floor with neither is invalid. A floor review that cites judgment cannot be approved
unless the current authority review was already approved. Every record and relationship is
append-only.

Also add a separate `proposal_only` competency-floor batch. The initial batch contains 15 researched
values across ten capability domains. Each item shows its exact source table and population where
available, proposed threshold, value origin, operational-authority origin, applicability to a
mid-thirties recreationally trained physical worker, evidence gap, and prerequisites. The batch and
each item are content-addressed. It is read-only and has no ratification endpoint, so reviewing it
cannot create planning authority.

The supplied ACSM and NSCA textbooks are permitted citable sources for the exact tables and
procedures they contain. Store the edition ISBN plus exact table/figure and PDF page locator.
Textbook inclusion does not convert a descriptive norm into an AGAS floor.

## Reason

The existing chair-stand slice proved the evidence, review, floor, strategy, and construction
machinery, but its 2.5th-percentile geriatric-screening lineage is a poor content choice for this
owner. More importantly, forcing an unsupported professional threshold through a general citation
would create false scientific provenance. The product needs to say plainly when a number is an
accountable judgment.

The proposal stage is necessary because several candidate values are sex-, apparatus-, protocol-,
or sport-specific, while AGAS currently stores age but not an athlete-reported sex classification.
Some tests also require maximal effort, impact, deceleration, specialized equipment, or supervised
administration. Making all 15 immediately ratifiable would let an attractive research table bypass
the assessment and applicability work that gives the number meaning.

## Alternatives considered

- **Continue requiring an `EvidenceClaim` for every floor.** Rejected because it launders
  professional judgment through citations that do not support the numeric threshold.
- **Put a free-text authority label directly on `CompetencyFloor`.** Rejected because it would not
  provide independent versioning, digest verification, review lineage, or reusable provenance.
- **Treat owner review of the 15-item batch as immediate ratification.** Rejected because many items
  still lack a governed matching assessment and demographic applicability rule.
- **Infer sex from the owner's name, appearance, or assumed identity.** Rejected. An applicability
  input must be explicitly reported and preserved as an observation before a sex-specific rule can
  be selected.
- **Use only sex-neutral values by choosing the lower sex-stratified threshold.** Rejected because
  that would repeat the chair-stand failure mode by hiding a deliberately weak comparison behind
  convenience.
- **Discard the chair-stand historical records.** Rejected because history is immutable. Its use as
  the owner-alpha path should be withdrawn through a later review/replacement after a better
  assessment chain exists, not erased.

## Evidence

- ACSM's *Guidelines for Exercise Testing and Prescription*, 12th edition,
  ISBN 9781975219246: Tables 3.8, 3.10, 3.11, and 3.12 and Figures 3.3 and 3.4.
- Haff and Triplett, *Essentials of Strength Training and Conditioning*, 5th edition,
  ISBN 9781718216273: Tables 14.14, 14.30, and 14.34.
- The master blueprint requires explicit provenance, preserved uncertainty, versioned material
  rules, competency floors distinct from ideals, and the observation-to-planning chain.

The sources support the quoted reference values and procedures only. Selection of a value as an
AGAS competency floor remains a separate operational decision.

## Assumptions and unresolved questions

- `professional_judgment` and `personal_calibration` are the only non-scientific authority kinds in
  version 1. Evidence-informed engineering proposals remain proposals until a named reviewer adopts
  them through one of those explicit paths.
- The application can record reviewer account provenance but cannot verify an ATC or other external
  professional credential. Qualification context is therefore attested metadata, not a credential
  claim made by AGAS.
- The batch intentionally includes paired male/female references where the source separates them.
  Which branch is applicable remains unresolved until the athlete reports the relevant
  classification and the product defines its narrow use.
- The 1.5× body-mass squat, 1.0× body-mass bench press, 0.5× body-mass carry for 100 m, and six
  movement families in 90 days are deliberately labeled unsupported engineering proposals. They
  must not be attributed to the contextual textbook figures.
- Several proposals may be rejected after review. A batch is a research throughput mechanism, not
  a requirement to keep every value.

## Consequences

- AGAS can preserve professional judgment honestly without fabricating scientific support.
- Approved judgment can later govern a floor with the same immutable review discipline as other
  planning authorities.
- The owner can inspect the requested 15-item batch in the planning-governance UI without risking
  accidental activation.
- A follow-up milestone must collect owner feedback, choose applicable demographic branches,
  research or govern matching assessments, and convert only accepted proposals into releases.
- The chair-stand floor and dose remain historical scaffolding for now; they are not endorsed as the
  desired first-session content for this owner.
