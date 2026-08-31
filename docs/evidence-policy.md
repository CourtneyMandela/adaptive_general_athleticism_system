# Evidence Policy

## Principle

Pretrained model knowledge is not scientific provenance. Any material scientific claim used by AGAS must be traceable to a structured, reviewed, versioned evidence claim.

A versioned policy record is not approved merely because it exists. Where a governed policy-review
boundary exists, new decisions must retain the exact current approved review and its evidence links.
Withdrawal or supersession preserves historical decisions but cannot silently authorize new ones.

## Preferred sources

1. Systematic reviews, meta-analyses, rigorous position stands, and transparent consensus statements.
2. Randomized or controlled trials and strong longitudinal interventions.
3. Appropriate observational, validation, biomechanics, and mechanistic studies.
4. Clearly labeled expert interpretation only when stronger evidence is unavailable.

Consumer fitness media, social posts, influencers, and commercial content may not establish scientific training rules.

## Stored provenance

An `EvidenceClaim` records the claim, population, intervention, comparator, outcome, study design,
uncertainty, limitations, strength, applicability, source identifiers, extraction/reviewer label,
creation time, and version. Source identifiers may include PMID, DOI, or another stable scholarly
identifier. Claim storage alone is not scientific approval.

New governed claims must also link to the exact immutable `EvidenceSource` metadata snapshots that
were reviewed. A source snapshot stores publication metadata, all identifiers, retrieval provider,
URI/query/time, metadata version, and provenance notes. If provider metadata changes, append a new
sequenced snapshot; do not rewrite the older snapshot or silently redirect historical claims.
Identifiers on the claim must agree with its linked snapshots. Existing secondary-AI seed claims
predate this relational link and remain provisional until deliberately re-retrieved and reviewed.

Evidence strength and athlete applicability must be assessed separately. A strong result in a dissimilar population may have low applicability to the current athlete.

An approval decision belongs to a separate append-only `EvidenceClaimReview` chain for the exact
claim version. Every review retains source-verification, extraction, evidence-strength, and athlete-
applicability rationales plus uncertainty, conflict disclosure, reviewer label, review time, and
version. A claim is ready in the evidence-governance projection only when exact source snapshots are
available and the current review is approved. A reviewer label and application permission are
provenance, not proof of scientific qualification.

## Review and updates

- Do not fabricate citations, identifiers, study results, effect sizes, or populations.
- Store uncertainty and limitations explicitly.
- Do not silently edit a material scientific rule. Create a new version and preserve the prior record.
- Re-review claims when stronger evidence appears, existing evidence is contradicted, or athlete applicability changes.
- Seed claims require checked source metadata and interpretation. Secondary-AI verification must
  remain distinguishable from production approval in the catalog manifest and reviewer field.

The development-only evidence-governance bundle importer is a typed transport for externally
retrieved metadata, claims, and explicit external review records. Version 1 accepts source and
claim records; version 2 may also carry `EvidenceClaimReview` history. It requires exact source-
snapshot links and atomic, idempotent persistence. Structural import does not search databases,
verify that a provider response is authentic, judge evidence strength, establish reviewer
qualifications, or create a review decision. Those remain separate retrieval and scientific-review
responsibilities.

The read-only evidence-governance workbench may display review history to an account with the
scientific-governance inspection role. It contains no approval mutation. Existing planning
authorities are not retroactively treated as reviewed merely because the new projection exists;
universal operational enforcement requires deliberate replacement of provisional authorities.

The PubMed adapter is retrieval only. Search results are identifiers, and an EFetch result is an
unreviewed metadata snapshot—not evidence that a claim is true. Retrieval must include the NCBI
tool/contact parameters, remain within NCBI usage limits, and respect the provider's disclaimer and
copyright guidance, including the possibility that abstracts are protected. API keys must not be
stored in source provenance or surfaced in errors. A human review boundary must remain between
retrieved metadata and any operational `EvidenceClaim`.

## Planning thresholds

Competency floors and scientifically informed planning signals are material claims. An operational
floor must link to at least one reviewed `EvidenceClaim` and declare its population, applicability,
uncertainty, metric scope, unit, and version. Priority policies are versioned heuristics rather than
scientific facts. Tests may use clearly labeled software-only fixture claims, but those fixtures
must never be shipped as training evidence or seed data.

Initial planning must retain the selected floor evidence and every estimate's direct source
observations. General relevance, goal relevance, prerequisite value, expected trainability,
transfer value, and recovery-cost inputs are explicit governed context—not conclusions that may be
invented from an assessment result or an LLM. Only the local operator workflow accepts these
inputs. A floor or policy is not authorized merely because it exists: each has a linear,
append-only review history, and the exact current review must be approved, evidence-linked, and no
later than the strategy timestamp. Every floor review must include the claims cited by its floor.
The operator command pins those review IDs, requires reviewer, rationale, and uncertainty metadata,
and appends a decision audit in the strategy transaction; athlete-authenticated HTTP clients cannot
submit them. Review records preserve governance provenance but do not turn software-fixture claims
or heuristic policy weights into scientific evidence.

## Assessment protocols

An assessment definition is not operational merely because its constraints are representable in
code. Its current `AssessmentDefinitionReview` must be approved and must retain evidence-claim
links, exact administration and result-entry instructions, a reassessment interval, applicability,
uncertainty, reviewer identity, review time, and version. A new review is appended when approval
changes; prior decisions are not edited or deleted. A later rejection or needs-revision decision
removes the definition from the operational catalog.

Self-service selection also requires the current review to contain a machine-readable measurement
schema. Its label, type, allowed values, bounds, and step are protocol claims, not neutral UI
metadata. They require the same qualified evidence and applicability review as the instructions and
must receive a new schema/review version when changed. A schema-less approval remains readable but
cannot enter the self-service workflow.

`recommended_reassessment_days` is likewise a material protocol claim. Ordinary self-service
retesting must not invent a default interval. The schedule uses the exact historical review attached
to the latest performance, and a different interval requires a new review version. The software
fixture intervals in tests are not scientific recommendations.

The repository ships no fabricated assessment protocol or norm. Software tests may use explicitly
labeled non-scientific fixtures in isolated databases. Protocol evidence, population validity,
measurement reliability, result interpretation, and self-administration suitability require
qualified review before production use.

Athlete eligibility is a separate authority from protocol approval. A current, approved definition
does not establish that it should be selected for a particular athlete, while an eligibility review
does not validate a protocol's scientific basis. Eligibility decisions must retain their source
observations, process reference, reviewer, rationale, uncertainty, review time, validity window, and
rule version. They authorize selection only and must not be represented as diagnoses or medical
clearance. Persisted selection requires both exact authorities so later changes do not rewrite why
the historical decision was permitted.

Recording a selected assessment result preserves the reported measurement as a direct observation
and repeats the exact protocol and eligibility authorities in relational lineage. Unit agreement is
not scientific interpretation. The recording boundary does not apply population norms or create a
capability estimate. The reviewed measurement schema validates entry shape only; it does not
establish reliability or interpret meaning. Reliability judgments, estimation formulas, validity
windows, and norm interpretation require separate reviewed policies before they can become
operational.

An operational `CapabilityEstimationPolicy` must be linked to evidence and to the exact approved
protocol review it interprets. Its append-only history retains decision, reviewer, review time,
applicability, uncertainty, observation window, validity window, calculation method, and rule
version. Only the current approved policy can authorize a new estimate. Matching observation type
alone is insufficient: assessment-derived sources must be persisted performances of that exact
definition. The initial calculation preserves the latest protocol-specific measurement and grades
confidence conservatively; it is not a population norm or whole-domain athletic score.

No estimation policy is shipped as production evidence. Synthetic test policies prove software
lineage only. A real deployment must supply qualified policy review before the PWA will offer
capability interpretation.

The development-only assessment-governance bundle importer is a typed transport for externally
curated records, not an evidence-review engine. It requires all referenced `EvidenceClaim` records
to exist and preserves their exact identifiers, but it does not fetch sources, verify metadata,
qualify the named reviewer, or turn structural validity into scientific approval. Production
evidence ingestion and assessment approval remain separate governed workflows.

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
effectiveness, motivation, readiness, or an appropriate progression. A rule that converts
execution or adherence into progression must carry its own version, applicability, uncertainty,
and evidence provenance. The application service loads such persisted policy records; it does not
create thresholds or increments.

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

A follow-up capability estimate and a block review answer different questions. Replanning may use
a valid reviewed follow-up estimate as current-state evidence even when the block's causal outcome
is inconclusive or unsupported. The replacement strategy must retain review lineage and must not
present the observed change as caused by the intervention. Relevance, trainability, transfer, and
cost inputs require their own governed provenance; one personal response does not establish them.

The persisted review boundary will not review a caller-selected favorable subset. Every planned
week and session outcome must be present, every executed prescription must appear in exactly one
response, and all post-session safety decisions are loaded from persistence. Comparison direction
and meaningful-change thresholds remain explicit policy inputs; the service does not manufacture
them from an observed change.
