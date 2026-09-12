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

Authoritative professional textbooks and standards manuals may be used as citable sources for the
normative tables, test procedures, and professional recommendations they actually contain. Store an
ISBN for the exact edition plus the table/figure and page locator. A textbook's inclusion of a
percentile or category does not prove that the value is a health threshold, safety threshold, or
AGAS competency floor, and a secondary table must retain any population, apparatus, and protocol
limits disclosed by the text.

## Stored provenance

An `EvidenceClaim` records the claim, population, intervention, comparator, outcome, study design,
uncertainty, limitations, strength, applicability, source identifiers, extraction/reviewer label,
creation time, and version. Source identifiers may include PMID, DOI, or another stable scholarly
identifier, including an ISBN for a specific book edition. Claim storage alone is not scientific
approval. For a book, the source snapshot must also identify the exact table or figure used; an ISBN
alone is not a sufficiently precise extraction locator.

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

When an assessment protocol review or capability-estimation policy cites a claim, readiness is
evaluated at that authority record's own review time. The claim, its exact source snapshots, and a
current approved `EvidenceClaimReview` must all have existed by that time. Later evidence approval
does not retroactively repair an older authority; the authority itself must receive a new review
version. This temporal rule preserves what was actually knowable at each decision rather than
rewriting provenance from current state.

The PubMed adapter is retrieval only. Search results are identifiers, and an EFetch result is an
unreviewed metadata snapshot—not evidence that a claim is true. Retrieval must include the NCBI
tool/contact parameters, remain within NCBI usage limits, and respect the provider's disclaimer and
copyright guidance, including the possibility that abstracts are protected. API keys must not be
stored in source provenance or surfaced in errors. A human review boundary must remain between
retrieved metadata and any operational `EvidenceClaim`.

## Planning thresholds

Competency floors and scientifically informed planning signals are material claims. An operational
floor must declare its population, applicability, uncertainty, metric scope, unit, version, and at
least one governing basis. That basis may be a reviewed `EvidenceClaim`, an approved
`CompetencyFloorAuthority`, or both. Priority policies are versioned heuristics rather than
scientific facts. Tests may use clearly labeled software-only fixture claims, but those fixtures
must never be shipped as training evidence or seed data.

A floor candidate must distinguish the origin of its numeric value from the authority for using
that value operationally. A paper can directly report a percentile without validating that
percentile as a competency, health, safety, or training threshold. In that case the number is
study-sourced while the floor interpretation is evidence-informed engineering judgment. A value
supplied solely by professional judgment must be labeled as such and may not be laundered through a
general citation. A `CompetencyFloorAuthority` is the distinct non-scientific path for that case. It
records the exact statement, scope, population, rationale, applicability, uncertainty, limitations,
named author and qualification context, optional supporting-but-nonauthorizing evidence, version,
and a canonical SHA-256 digest. A separate append-only authority review records the reviewer,
decision, time, explicit attestation, uncertainty, and replacement lineage. An approved floor review
must cite the current approved authority review. A role assignment is application permission, not
verification of a professional credential.

Research proposals remain outside both authority paths. The owner-alpha floor proposal batch may
show a textbook value, a derived reference, or an unsupported engineering number for criticism,
but its `proposal_only` state has no ratification endpoint and cannot satisfy a planning prerequisite.
After review, accepted content must be rebuilt as an exact governed release with a matching
assessment/estimate scope. This prevents a preliminary batch review from silently becoming a
training rule.

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

The repository ships no fabricated assessment norm. Software tests may use explicitly labeled
non-scientific fixtures in isolated databases. One real 30-second chair-stand candidate is now
prepared from exact PubMed source snapshots, but it remains non-authoritative until explicit
owner-alpha ratification. Its low-strength, low-applicability claims, self-report bias, population
mismatch, disclosed conflicts, protocol adaptation, and absence of independent domain-expert review
remain visible. It authorizes no normative conversion or universal score.

An `approved` protocol decision alone does not authorize the athlete runtime. The public catalog,
workflow and reassessment set, selection persistence, and result-recording boundary require every
cited claim to have been evidence-ready at the protocol review time. Capability interpretation
requires the same point-in-time readiness for both the exact protocol review and the current
estimation policy. Unsupported authority remains available to protected governance and historical
inspection; it is not deleted or silently rewritten.

Athlete eligibility is a separate authority from protocol approval. A current, approved definition
does not establish that it should be selected for a particular athlete, while an eligibility review
does not validate a protocol's scientific basis. Eligibility decisions must retain their source
observations, process reference, reviewer, rationale, uncertainty, review time, validity window, and
rule version. The owner-alpha current-state screen also records its ACSM-method PubMed identifiers
and persists a maximum authorized assessment intensity. Those identifiers provide traceable method
provenance but do not substitute for a governed `EvidenceClaim` review; expansion beyond the narrow
owner alpha requires a dedicated reviewed screening-policy release. Eligibility decisions authorize
selection only and must not be represented as diagnoses or medical clearance. Persisted selection
requires both exact authorities so later changes do not rewrite why the historical decision was
permitted.

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

The prepared chair-stand candidate includes a narrow estimation policy that preserves the direct
repetition count as assessment-specific state. It is not production authority until ratified, and
even after ratification it authorizes no normative, maximum-strength, sport-performance, or training
interpretation. Other synthetic test policies prove software lineage only.

The development-only assessment-governance bundle importer is a typed transport for externally
curated records, not an evidence-review engine. New approved records must cite claims whose exact
source snapshots and approved claim reviews were already available at the authority's review time.
The importer preserves exact identifiers, but it does not fetch sources, verify authenticity,
qualify the named reviewer, or turn structural validity into scientific truth.

The owner-only alpha also has one narrow production release boundary for a complete assessment
chain. A release packages exact source snapshots, claims, claim-review content, one
self-administered definition, its protocol review, and its estimation policy. The API rejects
caller-supplied approval identities and decisions, binds the authenticated account and exact
assessment-reviewer assignment, verifies point-in-time evidence readiness, stores a canonical
content digest and decision audit, and commits all records atomically. This is ratification of exact
content, not source retrieval, evidence extraction, credential verification, medical clearance, or
automatic scientific truth. The application role is not a professional credential, and every real
release must retain that limitation in its applicability and uncertainty language.

Prepared candidates are server-owned reviewed artifacts, not editable browser forms. The client
submits only the exact candidate version, SHA-256 digest, and explicit attestation. The server binds
the actual content and ratification time, and changed content requires a fresh review. A candidate
may include exact supporting equipment needed to make its environmental constraints enforceable;
that equipment is committed within the same decision transaction.

Competency-floor candidates are stored as typed reviewed data documents rather than executable
Python literals. The loader canonicalizes the complete structured presentation and release before
checking its digest and validates that user-facing values exactly match the persisted floor. A
batch manifest contains every current per-artifact version and digest. Batch ratification is one
review action and one transaction, but it does not replace individual evidence chains, floor
reviews, or decision records. One stale or conflicting artifact fails the entire batch.

The same distinction applies to planning-policy candidates. The first prepared priority policy
cites PMID 41843416 for the broad finding that resistance training improves multiple adult
physical-capacity outcomes. That evidence does not establish the candidate's numeric weights,
thresholds, or maximum simultaneous priorities. Those values are explicitly identified as a
versioned engineering prior and require counterfactual and personal-response evaluation. Evidence
provenance must never be presented as scientific validation of values the source did not study.
The second deficit-only policy narrows the operational use: only an exact normalized competency
deficit has nonzero weight, and confidence still discounts that signal. Contextual relevance and
stimulus-dependent cost fields receive zero weight because their magnitudes are unavailable, not
because evidence establishes zero relevance or cost. Its `0.01` threshold is an engineering guard
against zero and numerical noise rather than a scientific meaningful-change threshold. The
athlete-specific prepared context must expose that distinction for every field.

The first resource-authority bundle extracts the 2026 ACSM position stand's broad resistance-
training function findings and at-least-twice-weekly primary recommendation into a distinct claim
and review. That claim does not establish chair sit-to-stand as an optimal exercise, a weekly-minute
amount, sets, repetitions, effort target, rest interval, or the bundle's resolver/allocation
constants. The candidate presentation and decision history must preserve those exclusions.

The first prepared resource demand cites that reviewed claim only for the broad resistance-training
direction and twice-weekly frequency. Its ten-minute weekly value is labeled and audited as a
replaceable engineering scheduling envelope, not a physiological dose or minimum-effective-dose
claim. Exercise sets, repetitions, effort, tempo, rest, and progression require a later, separately
reviewed evidence-to-policy decision.

Competency-floor applicability must be enforceable where a source population has a meaningful age
boundary. `minimum_age_years` and `maximum_age_years` record inclusive reviewed bounds; missing
athlete age or an age outside those bounds makes the floor unavailable for new planning. Age
compatibility does not establish full applicability and does not turn a reference distribution
into a health, safety, or universal athletic threshold. The 19–35-year population in PMID 35949374
therefore cannot silently support an all-adult chair-stand floor.

The first prepared floor uses PMID 42183074 / PMCID PMC13193711. Its exact evidence claim is only
that the empirical p2.5 value was 11 repetitions in both reported 30-to-39-year sex strata. The
separate floor review—not the paper—is responsible for the provisional product interpretation of
that lower reference as a screening boundary. The record preserves the small subgroup sizes,
Colombian population, protocol differences, low athlete applicability, and the fact that the study
does not validate a minimum useful athletic competency. Approval must never be described as proof
of safety, health, ideal performance, or training effectiveness.

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

The first owner-alpha construction batch makes this distinction operational. Its reviewed ACSM
claim supports the broad resistance-training direction, functional outcomes, and at-least-twice-
weekly recommendation. The exact estimate fraction, set count, repetition bounds, effort range,
rest, duration, recovery interval, daily cap, readiness modifications, and progression increment
are explicitly labeled as engineering priors in the candidate. Ratification authorizes those
replaceable product rules provisionally; evidence provenance must never be displayed as if the
source tested those exact constants.

`RepetitionDosePolicy` keeps the estimate scope, unit, adaptation, calculation constants,
technique constraints, linked progression policy, evidence claim IDs, rationale, uncertainty, and
policy version together. The deterministic planner carries the exact source estimate and policy
identities into its output. A newer policy is appended as a new record; neither the source estimate
nor the earlier dose rule may be overwritten.

The prepared first block introduces no new scientific claim. Its four-week horizon and
target-minutes-equal-budget rule are disclosed engineering choices bound into the candidate digest.
The candidate requires the exact ratified resource and construction bundles and current governing
evidence, but that lineage must not be represented as proof that four weeks or the resulting time
budget is physiologically optimal.

Prepared Week 1 dose is derived only from the exact capability estimate referenced by the block's
strategy lineage and the exact ratified repetition-dose policy. The availability observation is
not evidence for the dose, and the broad resistance-training claim is not presented as validation
of the engineering constants. The resulting prescription retains observation, evidence, estimate,
dose-policy, progression-policy, exercise-resolution, and scheduling-policy lineage.

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
