# Evidence Policy

## Principle

Pretrained model knowledge is not scientific provenance. Any material scientific claim used by AGAS must be traceable to a structured, reviewed, versioned evidence claim.

## Preferred sources

1. Systematic reviews, meta-analyses, rigorous position stands, and transparent consensus statements.
2. Randomized or controlled trials and strong longitudinal interventions.
3. Appropriate observational, validation, biomechanics, and mechanistic studies.
4. Clearly labeled expert interpretation only when stronger evidence is unavailable.

Consumer fitness media, social posts, influencers, and commercial content may not establish scientific training rules.

## Stored provenance

An `EvidenceClaim` records the claim, population, intervention, comparator, outcome, study design, uncertainty, limitations, strength, applicability, source identifiers, reviewer, creation time, and version. Source identifiers may include PMID, DOI, or another stable scholarly identifier.

Evidence strength and athlete applicability must be assessed separately. A strong result in a dissimilar population may have low applicability to the current athlete.

## Review and updates

- Do not fabricate citations, identifiers, study results, effect sizes, or populations.
- Store uncertainty and limitations explicitly.
- Do not silently edit a material scientific rule. Create a new version and preserve the prior record.
- Re-review claims when stronger evidence appears, existing evidence is contradicted, or athlete applicability changes.
- Seed claims require checked source metadata and interpretation. Secondary-AI verification must
  remain distinguishable from production approval in the catalog manifest and reviewer field.

## Planning thresholds

Competency floors and scientifically informed planning signals are material claims. An operational
floor must link to at least one reviewed `EvidenceClaim` and declare its population, applicability,
uncertainty, metric scope, unit, and version. Priority policies are versioned heuristics rather than
scientific facts. Tests may use clearly labeled software-only fixture claims, but those fixtures
must never be shipped as training evidence or seed data.

## Exercise resolution

Exercise ontology metadata and resolver scores are not evidence of exercise equivalence. A full
match means the configured structural requirements are satisfied; a partial match must preserve
its mismatches, and an infeasible result must remain infeasible. Claims about transfer,
interchangeability, dose equivalence, or adaptation magnitude require reviewed evidence and a
versioned applicability judgment before they can become operational rules. No scientific exercise
claims. The small exercise catalog is provisional ontology annotation, not a production-approved
equivalence or prescription library.

## Dose and scheduling

`AdaptationResourceDemand`, `SessionPrescription`, and scheduling-policy values are versioned
inputs, not scientific facts merely because the software can store or schedule them. Operational
minimum doses, target doses, intensity targets, rest intervals, recovery intervals, and
progression rules require reviewed evidence, scoped applicability, and explicit uncertainty. The
current allocator and scheduler preserve these values and test feasibility; they do not establish
that a fixture value is effective or optimal.

Typed intensity targets make units and target semantics inspectable; they do not make a prescribed
load, RPE range, heart-rate zone, pace, or technique constraint evidence-based. Session-template
composition and frequency are likewise governed inputs until a reviewed generation policy exists.

## Safety and execution

A `SessionSafetyPolicy` must link to reviewed evidence claims before it is persisted. The policy's
allowed modifications and its response to readiness, soreness, sleep, or schedule input are
versioned operational interpretations, not medical facts. Concrete signal taxonomies and
escalation language must be reviewed outside the deterministic gate; the gate may not invent them
from raw text or model memory.

Set completion and dose-completion ratios are transparent descriptive calculations from an
immutable prescription and direct performance observation. They are not evidence of training
effectiveness, motivation, readiness, or an appropriate progression. Any future rule that converts
execution or adherence into progression must carry its own version, applicability, uncertainty,
and evidence provenance.

Milestone 5C requires evidence-claim identifiers on progression policies, exposure definitions,
and exposure caps. Test fixtures are software-only, not production thresholds.

## Training response and block review

Observed change is not automatically evidence that an intervention caused the change. A training
response must retain its compatible baseline and follow-up estimates, delivered dose, adherence,
measurement uncertainty, context, source observations, confidence, method, and version. Personal
response history must not be presented as a genetic ceiling or diagnosis.

Meaningful-change thresholds, minimum delivery, and minimum confidence are versioned operational
interpretations and must link to reviewed evidence before production use. The repository seeds no
universal response threshold. If delivery or confidence is insufficient, the review is
`INCONCLUSIVE`; it may not convert missing evidence into a claim that the block failed.
