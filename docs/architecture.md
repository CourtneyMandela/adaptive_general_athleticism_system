# Architecture

## Current scope

The current foundation adds controlled exercise/adaptation vocabulary and a deliberately small,
validated seed boundary. A tested full-gym/travel/return scenario re-resolves exercises against the
current environment without changing the athlete, strategy, block, adaptation, or stimulus.
Existing immutable session, execution, response, and block-review behavior remains in place;
reviewed capability estimates can now drive a lineage-linked replacement strategy. Automatic
interpretation of arbitrary raw results, candidate-context inference, workout generation, and
production training-rule inference remain deferred. Governed assessment performances can create a
bounded protocol-specific estimate only through a current reviewed estimation policy.

`tests/integration/test_required_vertical_slice.py` composes these boundaries as one blueprint
acceptance contract. It records direct intake and assessment observations, derives estimates and
needs, plans and executes all sixteen occurrences of a four-week block, preserves an explicit
hotel strength-fidelity limitation, applies deterministic safety and progression, reassesses,
reviews response, replans, and creates a successor block whose allocation states depend on the
follow-up estimates. Its thresholds, doses, and progression increment are synthetic test inputs,
not application defaults or evidence-backed production rules.

`python -m agas_api.demo bootstrap` provides a narrower development-only entry point. It persists
the repository-owned synthetic travel profile, its provenance-bearing environment report,
ownership, and separate reviewer authority with deterministic identifiers, then stops at the
derived `capability_estimate_required` boundary. It cannot run under production or external-auth
configuration and does not promote the vertical-slice test's synthetic thresholds, policies, or
doses into application behavior. The browser smoke suite verifies the resulting PWA deep-link and
reviewer-workbench navigation contracts; backend integration tests verify real persistence and
authorization separately.

## Shape

AGAS is a modular monorepo, not a distributed microservice system. Boundaries are explicit in source layout so they can evolve independently while sharing one deployable backend initially.

```text
apps/web
   |
services/api
   |
packages/domain ---- PostgreSQL
   |
   +-- packages/adaptation_models
   +-- packages/exercise_ontology
   +-- packages/safety

services/evidence retrieves and parses PubMed source metadata without extracting or approving
scientific claims. services/planner consumes domain contracts for deterministic assessment selection,
conservative capability estimation, competency-floor comparison, adaptation priority,
long-range strategy, environment snapshots, stimulus requirements, exercise resolution, block
allocation, and weekly scheduling.
It also records authorized execution, derives descriptive adherence and training response, and
reviews explicit block hypotheses. `packages/safety` owns the
deterministic safety-gate precedence and consumes only structured, preclassified input.
packages/evaluation tests behavior across synthetic athletes.
```

## Domain boundaries

### Observation

An observation is an append-only fact reported, measured, performed, or imported. It retains source, timestamp, value, context, reliability, provenance, and schema version. It is never a capability score.

### Capability estimate

A capability estimate is explicitly derived. Creation requires at least one existing observation owned by the same athlete, a method identifier, confidence, timestamp, and rule/model version. Source links are stored relationally. New estimates supersede by addition; they do not rewrite source observations or prior estimates.

Assessment-derived estimates also declare an `estimate_scope`. The first policy copies the latest
matching result inside a versioned time window, preserves all qualifying source observations in
chronological order, and caps confidence at moderate. It does not convert results into population
norms, athletic labels, or unsupported composite scores.

An operational `CapabilityEstimationPolicy` is an immutable governance record bound to one exact
assessment definition and approved definition review. Linear predecessor history preserves policy
withdrawal and replacement; evidence claims, reviewer, applicability, uncertainty, validity and
source windows, method, and rule version remain explicit. New assessment estimates cite both this
policy and the performance that triggered derivation. The repository restricts their sources to
governed performances of that exact definition review and enforces one interpretation per
performance-policy pair.

`AthleticDashboardProjection` is an owned, read-only view over this append-only history. At a
requested instant it selects the latest visible estimate independently for each exact
`(domain, estimate_scope, unit_or_scale)` series. It returns derived classification, value,
confidence, current/stale validity, method, rule version, timestamps, source-observation IDs, and
history counts. Future estimates are excluded and every capability domain remains present even
when no estimate exists. The projection and PWA do not collapse incompatible scopes, apply
population norms, or render a cross-domain percentage bar without a reviewed comparison policy.

### Adaptive assessment

Assessment definitions are versioned protocols with explicit domain, intensity, unit, body-mass
requirement, equipment, training-history, skill, recent-exposure, injury, symptom, and
health-screening constraints. Each definition has a separate append-only
`AssessmentDefinitionReview` history. Reviews retain an explicit decision, ordered protocol and
result-entry instructions, reassessment interval, self-administration status, evidence-claim
links, applicability, uncertainty, reviewer, time, version, and an optional machine-readable
measurement schema. The schema supports explicitly versioned number, integer, and categorical
entry contracts with reviewed labels, ranges, steps, or allowed values. Replacements form a linear
sequence; a later rejection or needs-revision decision withdraws a prior approval without erasing
it. Only definitions whose latest review is approved and whose cited claims were evidence-ready at
that review time appear in the read-only global assessment catalog. A schema-less or evidence-
unready approval remains inspectable in the governance workbench but is ineligible for self-service
selection, and persistence rejects athlete selections against it. No operational assessment
protocol is seeded by this boundary.

Athlete-level authority is separate. `AssessmentEligibilityReview` is an append-only, linear,
time-bounded operator decision that references the observations and screening process actually
reviewed. Its outcomes allow selection, block selection, or require further review; the record is
not a diagnosis or medical clearance. Athlete-facing services cannot create this authority.

The persisted assessment-run service loads the athlete's current allowed eligibility decision and
the catalog's current approved, evidence-ready, self-administered definitions. It derives equipment
categories from the effective-dated state of an owned environment, records the non-medical context
as a direct observation, and atomically appends decisions, selections, and an
`AssessmentSelectionRun`.
Athlete input cannot supply injury, symptom, health-classification, or equipment-category fields.

The selector uses exact tag matching and a versioned deterministic rule. Each selected, deferred, or excluded
decision records reason codes, human-readable rationale, and the immutable intake observations it
used. Persisted selections also name the exact approved review that authorized evaluation, so a
later withdrawal does not make historical authority ambiguous. Every new persisted selection also
names its exact athlete eligibility review. Legacy selections may have null authority references
after migration, but new repository writes fail closed without both current authorities.

Incomplete health screening excludes assessment. Health, injury, and symptom tags are constraints
supplied by intake/safety workflows; the selector does not diagnose or infer medical meaning. A
performed assessment becomes a direct `Observation`. Any
capability state created from it remains a separate derived `CapabilityEstimate`.
One selected decision can append an `AssessmentPerformance` linked to its result observation, run,
definition, exact protocol approval, and exact active eligibility review. The narrow result request
accepts no free-form medical context, verifies the definition unit and exact review's measurement
schema, and rolls back its observation if lineage persistence fails. Deferred and duplicate results
fail closed. Selection and performance runs do not create estimates, apply norms, or generate
workouts.

The separate assessment-capability-estimation service resolves the current approved policy on the
server, admits only exact-definition performance observations, and invokes the conservative
estimator. The request contains no scientific decision fields. Repeating it is idempotent; a future
policy may append a new interpretation without rewriting the older estimate. A withdrawn policy or
changed protocol review blocks new interpretation while preserving historical results and estimates.

An authenticated `AssessmentWorkflowProjection` derives the athlete-facing state from those
append-only records rather than persisting a mutable status flag. It exposes safe eligibility
timing, environment choices, reviewed protocol instructions and uncertainty, ordered deterministic
decisions, exact versions and evidence identifiers, and completed result observations. It omits
screening sources, operator identity, and screening-process details. The PWA can submit the narrow
selection context when the projection permits it. It renders number, integer, or categorical result
controls directly from the exact reviewed schema and performs convenience validation, while the
backend remains authoritative for the same contract and all lineage rules.

`AssessmentReassessmentScheduler` derives cadence from current operational definitions and the
latest immutable performance for each definition. An unmeasured protocol is due immediately. A
measured protocol uses the reassessment interval on the exact historical review that authorized its
latest result; replacement review data does not rewrite that date. The selection service evaluates
only due definitions, rejects premature requests and an unresolved selected run before any write,
and records reassessment enforcement as `assessment-selection-run@2.0.0`. Evidence-ready runtime
authority is recorded by `assessment-selection-run@3.0.0`.

The workflow projection exposes due count, earliest future time, schedule-rule version, and each
result's exact interval-source review. Due status remains derived rather than a mutable workflow
record. Eligibility, environment, current protocol approval, evidence readiness at the authority's
own review time, and measurement-schema requirements still fail closed independently. The same
temporal evidence check guards result recording and assessment-derived estimate creation, while
historical selections, performances, and estimates remain readable.

### Needs and long-range strategy

A `CompetencyFloor` is a versioned, metric-scoped comparison target with explicit population,
applicability, uncertainty, direction, unit, and evidence-claim links. No operational floors are
seeded yet. Comparing a compatible capability estimate creates an immutable `CapabilityNeed` and
preserves below-floor, meets-floor, above-floor, unknown, stale, and incomparable outcomes.

A versioned `PriorityPolicy` makes every scoring weight, confidence multiplier, threshold, cost
penalty, and development-slot limit explicit. `AdaptationPlanningCandidate` inputs keep user and
context signals distinct from the persisted result. The deterministic planner records component
scores, rank, rationale, DEVELOP/MAINTAIN/EXPOSE/DEFER state, relative development allocation,
sequencing hints, review triggers, and a block hypothesis in `LongRangeStrategy`.

`CompetencyFloorReview` and `PriorityPolicyReview` keep governance separate from those immutable
authorities. Each authority has one linear, append-only review history with decision, evidence,
reviewer, applicability rationale, uncertainty, timestamp, and review version. Sequence and
single-successor database constraints reject forks. Superseding an approval does not alter a prior
strategy, but only the exact current approved reviews may authorize a new initial strategy.

`PersistedInitialPlanningService` is the transactional boundary for the first strategy. The command
pins the exact current priority-policy review, and each explicit candidate context names one
persisted estimate, competency floor, floor review, and adaptation. The service verifies athlete
lineage, approval currency, review timing, and provenance, creates one need per unique
floor-estimate pair,
adds every estimate source observation and floor evidence claim to the candidate, and delegates
only deterministic scoring and state assignment to the planner. It appends all needs and one root
strategy together with a `DecisionRecord` carrying reviewer, rationale, uncertainty, and typed
input and review identifiers. A repository guard and partial unique database index allow only one strategy
whose `supersedes_strategy_id` is null per athlete; later changes must use review-linked replanning.
Review histories remain local administrative inputs. The service is available through both a local
operator CLI and a role-protected operator HTTP endpoint. The HTTP request cannot supply reviewer
identity: the server binds the authenticated account and exact current `planning_reviewer`
assignment, then the service validates and records that authority. Initial planning remains absent
from athlete-authenticated writes because athlete ownership does not authorize expert scoring or
scientific-applicability decisions.

The strategy is not a workout. It contains no exercise, dose, weekly schedule, or session. Safety
restriction, introductory exposure, missing prerequisites, unresolved information, competency
deficits, and athlete-valued comparative advantages remain distinguishable reasons.

`get_planning_status_projection` is the read-only athlete-facing handoff around this boundary. It
classifies persisted estimates as current or stale at an explicit instant and reports whether the
root strategy exists. Before strategy creation it exposes exact reviewed-authority and context
requirements. After strategy creation it derives demand coverage for every priority, whether each
priority has a resolution eligible under the available allocation policies, the remaining explicit
block-context review, and any persisted block status. A single infeasible block remains visible;
multiple blocks become an ambiguity state because the model has no current-block pointer. For one
feasible block, the same projection reports scheduling-policy availability and preserves the atomic
weekly-plan boundary: exact prescriptions, session composition, and observation-backed availability
remain pending together until a weekly plan exists. Only `block_week == 1` establishes first-week
readiness. A single feasible or infeasible result is summarized with exact policy, availability,
template, prescription, issue, and rule lineage; multiple first-week plans remain ambiguous rather
than being sorted into authority by generation time. Narrow strategy, block, and week summaries are
presentation state, not second planning records. Missing floors, evidence, adaptation context,
policy, demand, resolution, or operator choices remain visible governed dependencies; the
projection cannot create inputs, choose historical records, or infer a weekly budget, calendar,
dose, session grouping, or exercise substitution.

### Environment and equipment

An athlete may own multiple environments. Equipment is cataloged independently, while availability
is an append-only, effective-dated event with capabilities and limits. Environment changes
therefore constrain future exercise resolution without changing athlete identity or adaptation
intent. New governed events name the direct observation that reported them; pre-migration history
may retain a null source as explicit unknown provenance. Repository validation requires a linked
observation and environment to belong to the same athlete.

The `EnvironmentSnapshotBuilder` selects the latest active availability event for each equipment
item at a stated capture time. A temporary outage may expire and reveal an older still-effective
availability record. Snapshots retain the exact availability IDs used, merged equipment
capabilities, load limits, usable floor area, outdoor access, and the environment's maximum noise
level. They are derived resolver inputs, not a replacement for availability history.

`PersistedEquipmentStateService` accepts a partial set of explicit available/unavailable changes
for one owned environment. It appends the exact direct user report and its temporal events in one
transaction. Omitted catalog items retain their current or unknown state. The owned read projection
uses `EnvironmentSnapshotBuilder.current_availability` so PWA state and exercise resolution share
one latest-active-event rule. The projection exposes the controlling event and observation IDs and
never turns missing history into an unavailable report.

### Exercise and adaptation ontologies

Exercises and adaptations are separate versioned entities. Movement pattern, loading type,
velocity characteristic, joint region, laterality, preferred stimulus, training modality, and dose
dimension use controlled enums. Exercise records also retain loadability, skill, impact, stability,
fatigue, progression, regression, and exact equipment requirements. Adaptations can carry typed
relationships with confidence and evidence references; the seed contains no speculative
relationships.

Ontology identity links are relational: exercise adaptation roles, equipment requirements,
exercise progression/regression edges, adaptation evidence, and adaptation relationship evidence
all use foreign keys. Flexible descriptive metadata remains JSONB. `agas_seed_data` validates IDs,
relationships, scenario references, and evidence links atomically before persistence. The initial
catalog is 14 exercises, 8 adaptations, and 8 equipment types—not a complete production library.
`SeedCatalogImporter` stages those global records in a nested transaction and appends a
digest-backed `CatalogImport` receipt with ordered foreign-key links to every imported identity.
Exact reimports are idempotent; version/content collisions fail. Synthetic scenario athletes are
not imported into athlete state.

### Stimulus and exercise resolution

A `StimulusRequirement` is an immutable, versioned expression of what a non-deferred adaptation
priority needs. It retains its strategy, exact priority, adaptation, observations, evidence claims,
movement and loading requirements, minimum loadability, velocity characteristics, physical
constraints, rationale, generation time, and rule version. It deliberately contains no sets,
repetitions, duration, or schedule.

The deterministic resolver first applies hard feasibility constraints: exact equipment
availability, contraindication tags, skill, impact, stability, fatigue, soreness, outdoor access,
space, and noise. Remaining exercises receive a policy-versioned weighted score for adaptation
role, movement coverage, loading type, loadability, velocity coverage, and laterality. A result is `FULL` only
when every fidelity component is complete; `PARTIAL` results enumerate every unresolved mismatch;
and `INFEASIBLE` results select nothing and retain explicit reasons. The score ranks candidates—it
does not claim two exercises are scientifically equivalent.

Equipment identity matching is intentionally exact in this milestone. A weekly prescription may
use a newer resolution than its block allocation only for the same stimulus and adaptation. A
partial re-resolution must be enabled by the weekly policy, and its unresolved limitations remain
attached to the resolution; the planning-time allocation is not overwritten. Category- or
capability-based substitutions require a future reviewed compatibility policy rather than hidden
resolver inference. The repository includes no fabricated exercise catalog or scientific
equivalence claims.

### Blocks, resources, prescriptions, and weekly feasibility

An `AdaptationResourceDemand` binds one strategy priority to its stimulus and exercise resolution.
It states explicit minimum and target weekly minutes plus session frequency and preserves athlete
observations, evidence claims, rationale, and version. Deferred priorities request zero resources.
The system does not infer acquisition, maintenance, or exposure doses from a state label.

The deterministic `BlockPlanner` first verifies that every strategy priority is represented and
that every active demand has a compatible exercise resolution. If minimum demand exceeds the
weekly time budget—or the resolution is unacceptable under the configured policy—the resulting
four-to-six-week `BlockPlan` is explicitly infeasible. Otherwise, minimums are reserved and
remaining whole-session minutes are assigned toward targets using a versioned state-weight policy.
Target shortfalls and permitted partial exercise resolutions remain visible as partial block
issues. Long-range development allocation scales development weight but is never treated as a
literal dose.

A `SessionPrescription` stores one explicit exercise and adaptation with its reason, sets,
repetitions or duration, typed intensity targets, rest, progression-rule reference, substitution
class, planned duration, fatigue class, observations, evidence, and rule version. Supported target
types distinguish absolute load, relative load, bodyweight, effort RPE, repetitions-in-reserve,
heart-rate zone, pace, and technique constraints. Prescriptions remain independently versioned so
one item can progress without rewriting a completed session.

A versioned `SessionTemplate` is the workout container. It gives ordered prescription items a
section, owns an explicit weekly frequency, and declares duration and maximum item fatigue. V1
accepts templates as governed input and validates that their aggregate frequencies exactly match
block allocations; it does not invent grouping rules.

`WeeklyAvailability` contains dated, timezone-aware, non-overlapping windows associated with one
athlete environment. `WeeklyScheduler` repeats each session template and places the whole workout
in one matching-environment window with adequate time. Every item in a template must resolve to
that environment, and the template duration must equal the sum of its item durations.
It enforces configurable daily limits and recovery between high-fatigue sessions. A required
occurrence that cannot be placed makes the immutable `WeeklyPlan` infeasible and records why.

### Safety decisions, execution, and adherence

Every ordinary execution requires a versioned pre-session `SessionSafetyDecision` for the exact
athlete, weekly plan, and planned session. The deterministic gate applies escalation, hold,
modification, then proceed precedence to a structured user-report observation. It does not parse
free text or classify medical meaning. A modification decision lists explicit changes; the
execution must acknowledge exactly those changes, while hold and escalation outcomes cannot
authorize ordinary logging.

`SessionExecution` retains the immutable session-template identity, authorizing decision,
timestamps, status, applied modifications, and ordered item results. Each item retains its
prescription identity, completion status, effort, note, and set-level repetitions or duration,
load, effort, and technique report. The same input is preserved as a direct `WORKOUT_RESULT`
observation. `SessionAdherence` remains a separate prescription-item-scoped `derived` record with
bounded prescribed-versus-performed set and dose ratios, its source observation, calculation
method, timestamp, and rule version. Optional
post-session safety decisions reference the completed execution without rewriting it. None of
these records chooses a progression.

### Progression and exposure

`ProgressionPolicy` makes adherence, effort, technique, adjustment, exposure, evidence, and
version requirements explicit. Decisions can progress, repeat, hold, or require review and never
mutate completed prescriptions. Evidence-linked exposure definitions produce derived ledger
entries from actual execution; configured initial, relative, and absolute caps reject unearned
jumps without using general fitness as a proxy.

Approved progression decisions may create a new `SessionPrescription` linked through an immutable
revision record to both the superseded prescription and authorizing decision. The applicator has
typed support for repetitions, sets, duration, and compatible absolute or relative load targets,
but the athlete-facing automatic boundary is provisionally limited to non-exposure load and
repetition adjustments. Unsupported or unit-incompatible adjustments fail explicitly. Evidence,
observation, exposure-entry, and safety-decision provenance uses ordered foreign-key association
tables.

### Training response and block review

A `TrainingResponse` is immutable derived history for one block adaptation. It requires comparable
numeric baseline and follow-up `CapabilityEstimate` records for the same athlete, domain, metric
scope, and unit. It retains the exact prescriptions, executions, adherence records, source
observations, prescribed and delivered dose, completion, uncertainty, context, confidence,
calculation method, and rule version. The follow-up measurement remains an observation and the
response does not replace either capability estimate.

A `BlockReviewPolicy` makes minimum delivery, minimum confidence, evidence, rationale, and policy
version explicit. Each `ResponseEvaluationTarget` supplies a direction and metric-specific
meaningful-change threshold; no universal threshold is embedded in the engine. A `BlockReview`
compares those targets with the original block hypothesis, preserves post-session safety history,
and records `SUPPORTED`, `PARTIALLY_SUPPORTED`, `NOT_SUPPORTED`, or `INCONCLUSIVE`. Any response
below the delivery or confidence threshold makes the review inconclusive rather than treating an
untested or poorly measured intervention as ineffective. Review is descriptive: it changes no
historical estimate, prescription, or future plan.

### Closed-loop replanning

`ClosedLoopReplanner` is the explicit boundary from a completed block review to a replacement
`LongRangeStrategy`. It accepts capability estimates that already exist as derived state and
requires each actively trained adaptation to use the exact follow-up estimate named by its
reviewed `TrainingResponse`. Inactive adaptations may retain an estimate from the prior strategy.
Each `ReplanningCandidateContext` names its estimate and competency floor directly, so adaptations
that share a broad capability domain are not accidentally coupled by domain alone.

The replanner rebuilds immutable `CapabilityNeed` records through the same competency-floor
detector, delegates scoring to the versioned long-range planner, and records both
`supersedes_strategy_id` and `triggering_block_review_id`. Those lineage values are a required pair
in the domain, repository, and relational schema. A review can be causally inconclusive while a
separately derived follow-up estimate remains valid current-state evidence; using that estimate
does not assert that the completed block caused the change. Candidate relevance, trainability,
transfer, and cost values remain explicit governed inputs rather than being inferred from a single
response.

This is an operator-only application boundary. The command requires reviewer, applicability, and
uncertainty metadata because candidate relevance, trainability, transfer, costs, prerequisites,
safety state, and comparative-advantage flags are expert planning inputs. The capability needs,
successor strategy, and a `DecisionRecord` citing the exact review chain, contexts, observations,
evidence, policy, and result identities commit or roll back together.

### Persisted next-block creation

`PersistedBlockCreationService` is the application boundary from a stored strategy to an immutable
`BlockPlan`. The caller supplies identities for already-governed resource demands and an allocation
policy, plus dates, weekly time budget, and explicit constraints. The service reconstructs every
referenced exercise resolution and delegates allocation to `BlockPlanner` in one transaction. The
same transaction appends a `DecisionRecord` that pins reviewer, applicability rationale,
uncertainty, demands, allocation policy, resulting allocations, observations, evidence, and block
identity.

The planner requires one demand for every strategy priority and verifies exact
strategy–priority–adaptation–state lineage. Active demands must reference a matching persisted
stimulus and exercise resolution; deferred demands consume no resources. Consequently a revised
strategy cannot reuse a demand attached to its predecessor, and block two materially depends on
the replanning result rather than merely copying block one. This boundary stops at resource
allocation: it creates no prescriptions, sessions, exercise substitutions, or progression rules.
It is invoked through reviewed operator JSON and a local CLI, not an athlete-authenticated route.

### Governed resource-demand preparation

`PersistedResourcePreparationService` provides the upstream application boundary required by block
creation. For an active strategy priority, it loads the persisted adaptation, environment,
effective-dated equipment availability, equipment records, explicit exercise candidates, and
resolver policy. It binds the caller's explicit stimulus specification to the immutable priority,
derives one environment snapshot, resolves exercise fidelity, and appends the requirement,
resolution, resource demand, and reviewer-attributed `DecisionRecord` in one transaction.

The service does not derive scientific dose from `DEVELOP`, `MAINTAIN`, or `EXPOSE`; minimum and
target minutes plus frequency remain explicit versioned inputs. An `INFEASIBLE` resolution is
persisted and makes downstream block planning infeasible. A `DEFER` priority instead creates a
zero-resource demand with no stimulus or resolution. This makes absence of training intentional
and traceable rather than ambiguous. Active and deferred commands require reviewer, applicability,
uncertainty, and preparation-time metadata. The application boundary is available through the
local planning-authoring CLI and a role-protected operator HTTP endpoint. The HTTP request cannot
supply reviewer identity or authority; the server binds the authenticated account and exact current
`planning_reviewer` assignment, and the service validates and records that authority.

A companion role-protected preparation projection composes the exact persisted strategy,
priorities, adaptations, demand history, strategy-linked observations and evidence, current
environment snapshots, resolver policies, and structured exercise catalog. It is read-only and
does not select a stimulus, environment, candidate set, dose, or demand history. Catalog inclusion
is not represented as scientific approval or environmental feasibility.

### Authenticated block preparation

`BlockPreparationProjector` composes one strategy's priorities, complete immutable demand history,
allocation policies, existing blocks, and all observation/evidence records referenced by the
strategy and demands. It does not select a historical demand, mark one current, approve a policy,
calculate a budget, choose dates or duration, or author constraints.

The role-protected block POST binds the authenticated account and exact active
`planning_reviewer` assignment to an otherwise explicit block command. The application service
revalidates that assignment and atomically appends the deterministic full, partial, or infeasible
block with its decision audit. Exactly one demand per strategy priority remains mandatory. The
boundary creates no prescriptions, session containers, availability, weekly schedule, or workout.

### Authenticated first-week preparation

`FirstWeekPreparationProjector` composes one block's exact allocation-to-demand-to-stimulus-to-
resolution-to-exercise chains, athlete environments, scheduling policies with their current
reviews, existing first-week plans, and the cited observation/evidence records. It does not choose
an intensity, dose, progression reference, session grouping, availability window, or policy.

The role-protected first-week POST binds the authenticated account and current reviewer assignment
to a complete explicit command. `PersistedWeeklyPlanService` revalidates that authority, requires
the exact current approved scheduling-policy review, runs the deterministic scheduler, and appends
prescriptions, session templates, dated availability, the weekly plan, and decision audit in one
transaction. Local reviewed CLI commands remain supported without account-role lineage.

### Operator-reviewed exercise re-resolution

`PersistedExerciseReResolutionService` applies a new environment state to an existing immutable
`StimulusRequirement`. It loads an explicit reviewed exercise-candidate set and resolver policy,
derives effective equipment state at the requested instant, and delegates to the same deterministic
resolver used during resource-demand preparation. The new `ExerciseResolution` and its
reviewer-attributed `DecisionRecord` commit or roll back together.

The service appends history instead of replacing the planning-time resolution. It preserves the
requirement's athlete, strategy, priority, adaptation, observation, evidence, and stimulus
semantics, and records the controlling equipment-availability events. `FULL`, `PARTIAL`, and
`INFEASIBLE` remain distinct. A successful transaction is only a new planning input: it does not
revise a demand, block allocation, dose, prescription, template, or weekly plan. It is available
through reviewed operator JSON and the local planning-authoring CLI, not the athlete API.

### Reviewed environment prescription revisions

`PersistedEnvironmentPrescriptionRevisionService` is the governed bridge from an exercise
re-resolution to the dose-bearing prescription lineage consumed by weekly roll-forward. It accepts
one closed source weekly plan and a batch of explicit replacement prescriptions. The source plan's
backend-derived review must be `environment_revision_required`; its scheduling policy review must
still be the exact current approval. Each replacement resolution must preserve the block
allocation's stimulus and adaptation, predate the replacement, select an exercise, and be full or
a policy-permitted partial match. Replacement sets, repetitions or duration, intensity, rest,
fatigue, progression reference, rationale, and rule version remain reviewed inputs.

Prescription revision lineage now has two mutually exclusive authorizers: a performance-derived
`ProgressionDecision`, or an operator `DecisionRecord` for environment planning. A database check
constraint, the domain model, and repository validation enforce that XOR. Environment decisions
must cite the source plan, block, allocation, immediate predecessor, new resolution, new
prescription, policy, review, observations, evidence, and availability events. The service appends
to the latest progression descendant rather than branching it, and rolls the decision and all
replacement prescriptions back together on failure.

This boundary creates no template, availability record, or weekly plan. It consumes the athlete's
already-persisted next-week availability confirmation, and the existing roll-forward service later
follows the revision lineage and creates a successor template only when needed. All
items retained within one session template must resolve to one environment after the reviewed
batch, preventing a mixed-environment container from being presented as executable. The local
`weekly_revision_admin` CLI and the role-protected operator endpoint are provisional operator
transports; no athlete HTTP write accepts dose or substitution authority. The HTTP request cannot
name its reviewer. The server records `account:<account-id>` and cites the exact active
`AccountRoleAssignment` in the decision evidence, making the authorization state at the time of
the append reconstructable after later revocation.

### Transactional weekly-plan creation

`PersistedWeeklyPlanService` is the boundary from an immutable block to one dated week. Transport
drafts key prescriptions and session items by block allocation, allowing the service to derive
athlete, adaptation, resolution, and selected-exercise identities from persisted state. The caller
must still provide the actual dose, intensity targets, rest, progression reference, session
composition, frequency, fatigue classification, dated availability, provenance, and rule versions.

The service creates `SessionPrescription`, `SessionTemplate`, and `WeeklyAvailability` records,
then delegates placement and feasibility to `WeeklyScheduler`. Prescriptions must cover every
active allocation exactly, container frequencies must reproduce each allocation frequency, and
container duration and fatigue must equal their item composition. The result is persisted whether
feasible or infeasible so schedule limitations remain explicit. All records commit or roll back
together with a `DecisionRecord` citing the reviewer, rationale, uncertainty, exact policy,
upstream block lineage, observations, evidence claims, and newly created records.

This is an operator-only application boundary invoked through a reviewed JSON file and local CLI.
It is deliberately absent from athlete-authenticated HTTP writes: dose, intensity, progression,
session grouping, fatigue classification, and scheduling-policy selection are expert inputs, and
omitting their controls from the PWA would not authorize an athlete client to submit them. The CLI
is provisional development administration until verified administrative identities and roles
exist.

### Transactional safety and session recording

`PersistedSessionSafetyService` is the write boundary for pre- and post-session reports. The URL
identifies the immutable weekly plan and planned occurrence. The service derives the athlete and
resolves the current predecessor-linked `AthleteSafetyPolicyAssignment`; the request cannot select
a policy. It supplies only already classified signals, readiness context, timestamps, reliability,
and provenance. The deterministic safety gate produces a direct user-report `Observation` and a
`SessionSafetyDecision`; both append or roll back together.

`PersistedSessionExecutionService` loads the plan, planned occurrence, session container, ordered
prescriptions, and requested pre-session decision. The decision must be the latest pre-session
decision for that occurrence and must authorize execution. The client supplies actual set-level
performance but cannot replace athlete, plan, container, or prescription identity. The service
atomically appends the workout-result observation, execution, and one derived adherence record per
prescription. A database uniqueness constraint permits only one execution per planned occurrence;
future correction support must use explicit supersession rather than competing histories.

### Transactional post-session progression

`PersistedProgressionService` is the boundary from one execution/prescription pair to its immutable
progression result. It derives the adherence identity and loads every post-session safety decision,
so transport input cannot omit an escalation. At least one post-session check must close the
ordinary workflow before the decision is evaluated.

When the selected progression policy declares an exposure type, the request identifies reviewed
exposure-definition and exposure-policy records and supplies only the proposed dose and target
time. The service derives the actual exposure entry from performed sets, loads the athlete's prior
ledger, validates the proposal, and passes that decision into `ProgressionEngine`. The exposure
entry, exposure validation, progression decision, and any automatically supported typed
prescription revision commit or roll back together. Database constraints prevent duplicate
adherence, exposure, and progression facts for the same execution chain.

### Transactional weekly progression roll-forward

`PersistedWeeklyPlanRollForwardService` is the narrow bridge from an immutable weekly plan to the
immediately following week of the same block. Before roll-forward, the athlete-facing
`PersistedWeeklyAvailabilityConfirmationService` appends a direct-report observation and one
`WeeklyAvailability` linked to the exact source plan. That transaction creates no planning state.
The current-week read model compares the latest prescription-resolution environments with those
confirmed windows and exposes a governed-review requirement when they differ.

The final roll-forward request supplies only the persisted availability ID and preparation time.
Client-authored week identity, source IDs, reliability, provenance, windows, and rule versions are
forbidden at this boundary. The service retains the source plan's scheduling policy and exact immutable policy-review
identifier, verifies that the review remains the current non-future approval, and follows each
session-template item through normalized prescription-revision records, and selects the latest
revision that existed at preparation time. Before any write, the service also uses the same
`CurrentWeekProjector` as the athlete-facing read model to reconstruct the exact source plan's
closure state. Only `ready_to_finalize_next_week` is eligible; incomplete execution, post-session
safety, or progression history and all hold, review-required, infeasible, unsupported, and final
block-week states fail closed at the backend boundary. The browser never supplies readiness as
command authority.

`WeeklySchedulingPolicy` records are proposals until an immutable
`WeeklySchedulingPolicyReview` chain approves them. Each review retains ordered evidence claims,
decision, reviewer, time, applicability rationale, uncertainty, predecessor, and review version.
First-week authoring requires the exact current approved review; roll-forward derives it from the
source plan. Plans created before this boundary may retain a null review ID as explicit unknown
historical provenance, but governed creation paths cannot produce another such plan. Policy review
administration remains operator-only.

Unchanged prescriptions and templates are reused. If one or more items changed, the service creates
a new immutable template with `previous_template_id`, preserving item order, section, frequency,
and prescription ancestry while recomputing duration and fatigue from the carried items. The new
`WeeklyPlan` records `previous_weekly_plan_id` and advances exactly seven days and one block week.
Any successor template and the new plan commit or roll back together; the previously confirmed
availability remains immutable. Unique lineage constraints reject competing automatic successors.

The service adds no dose rule and accepts no client-authored prescription revision. Changed
environments block finalization until the persisted resolution lineage matches the confirmed
environment; they never trigger an alleged equivalent exercise substitution. Exercise
re-resolution, exposure proposals, block continuation, and next-block creation remain separate
governed workflows.

### Transactional completed-block review

`PersistedBlockReviewService` closes the descriptive block history before replanning. It requires
exactly one feasible `WeeklyPlan` for every dated block week and one persisted execution outcome for
every planned occurrence; a missed session must therefore be recorded explicitly rather than
disappearing from review. It derives every execution/adherence relationship and loads every
post-session safety decision, requiring at least one such decision per execution.

The request groups the exact set of executed prescription identities into non-overlapping response
drafts and supplies compatible estimate identities, uncertainty, context, comparison direction,
and a meaningful-change threshold. The service rejects omissions and double counting, derives all
`TrainingResponse` records, evaluates the original hypothesis under a persisted review policy, and
appends the response/review chain and a reviewer-attributed `DecisionRecord` in one transaction.
The audit pins all interpretations, delivered records, estimates, observations, evidence, policy,
and created identities. One block has at most one completed review in V1. The review remains
descriptive and the existing replanning boundary is the only component that may derive a successor
strategy.

`BlockReviewPreparationProjector` is the read boundary before that write. It returns the exact
completed block history, eligible baseline and follow-up estimates, available review policies, and
the cited observations/evidence, with explicit incomplete-history issues. It never assigns
prescriptions to responses or invents meaningful-change thresholds. The authenticated review POST
binds the current `planning_reviewer` account and append-only role assignment into the command and
decision evidence; reviewer identity is not accepted from the client.

`ReplanningPreparationProjector` composes the immutable review, responses, prior strategy,
adaptations, allowed estimates, and compatible floors. An actively trained adaptation can use only
the follow-up estimate named by its reviewed response. It exposes choices but does not author
relevance, trainability, transfer, or recovery-cost scores. The authenticated replanning POST uses
the same reviewer-identity boundary and appends, rather than replaces, the successor strategy.
The local post-block CLI remains an administrative fallback; neither write is athlete-accessible.

### Current-week read projection

`CurrentWeekProjector` is a read-only application boundary for daily PWA use. An athlete ID and
explicit date identify at most one persisted weekly plan. The projector joins immutable session
containers and prescriptions with exercise/adaptation labels, the latest pre-session safety
decision, any execution and adherence, all post-session safety outcomes, and any progression
decision. It returns a purpose-built transport model rather than exposing persistence records or
adding presentation fields to domain history.

No matching plan is a valid empty-week result. Multiple plans covering the date are a conflict in
V1 because plan supersession is not modeled; the query will not silently choose the newest record.
Display status is a deterministic rendering of persisted execution or safety outcomes and is not a
new training or safety decision.

### Evidence claims

Evidence claims are reviewed, versioned interpretations linked to source identifiers. Evidence
strength and athlete applicability are separate. Three broad claims have source-checked PMID and
DOI identifiers and an explicit `secondary_ai_verified` catalog status. They remain pending owner
or qualified-domain approval and do not authorize dose, progression, or equivalence rules.

`EvidenceSource` is the immutable publication-metadata layer beneath new claims. Each record keeps
title, authors, journal/date metadata, optional abstract, publication types, all stable identifiers,
the primary identity, provider, retrieval URI/query/time, provenance notes, and metadata version.
Metadata corrections append a linear source snapshot with the same primary identity; sequence and
single-successor constraints prevent forks or silent replacement. `EvidenceClaim.source_record_ids`
is an ordered relational link to the exact snapshots interpreted. The original identifier list is
retained for portable citation and must agree with the snapshots at the governed import boundary.

`EvidenceClaimReview` is a separate append-only authorization record for one exact claim. Its
linear chain preserves the explicit decision, reviewer label, source-verification and extraction
rationales, separate strength and applicability rationales, uncertainty, conflict disclosure,
time, and review version. Positive sequence, same-claim predecessor, exact increment,
nondecreasing time, and single-successor checks prevent silent replacement or forks.

The local-only evidence-governance bundle command imports self-contained exact source, claim, and
optional review records atomically and idempotently. Version 1 bundles remain source-and-claim only;
version 2 adds reviews. The read-only `/v1/operator/evidence-governance` projection and
`/review/evidence` workbench resolve point-in-time state and block claims without exact snapshots or
a current approved review. They do not retrieve publications, interpret findings, approve science,
or qualify the named reviewer. Legacy provisional seed claims have no fabricated snapshot links or
reviews; they can be migrated only after deliberate retrieval and qualified review.

`EvidenceAuthorityEvaluator` applies the same rules to an ordered set of exact claims at another
authority record's own timestamp. It returns typed per-claim sources, point-in-time review history,
readiness, and blockers. Unknown, future, source-less, unavailable-source, unreviewed, and currently
non-approved claims fail closed. A later claim approval does not alter an older authority's
evaluation.

`agas_evidence.pubmed` is the first provider adapter. It uses NCBI ESearch for bounded operator
queries and EFetch XML for one exact PMID, supplies the configured tool/contact parameters, and
maps the response to an unpersisted `EvidenceSource`. Parsing retains inline title text, ordered
authors, publication metadata and types, abstract sections, PMID/DOI identifiers, retrieval query,
time, and adapter version. It rejects malformed, ambiguous, or PMID-mismatched responses. The
adapter performs no claim extraction or review, and API failures do not echo an API key.

### Decision records

Material architecture and training-model choices exist as both human-readable records in `docs/decision-log` and a versionable domain type for future persistence.

## Persistence

SQLAlchemy 2 maps domain records to a PostgreSQL-oriented relational schema. JSON columns are used only for flexible context and ontology metadata; identity, ownership, temporal history, versioning, and provenance links remain explicit columns and relationships. SQLite is used only for fast isolated tests.

Provider-subject accounts and athlete ownerships are normalized immutable records. The account
identity is not embedded in `Athlete`; one account may own multiple athlete records, while the V1
database constraint permits exactly one permanent owner record per athlete. Transfer, revocation,
and delegated athlete access are not implied by this narrow schema. Administrative authority is a
separate append-only `AccountRoleAssignment` lineage. The initial vocabulary contains distinct
`planning_reviewer` and `assessment_reviewer` permissions; sequenced active and revoked assignments
preserve every authorization change.

Historical athlete evidence, planning history, stimulus requirements, resolver policies, matches,
resolutions, resource demands, blocks, prescriptions, availability windows, and weekly plans are
append-only at the repository boundary. ORM
event guards reject update or delete operations on observations, estimates, assessment records,
competency floors, needs, priority policies, strategies, source links, availability events,
evidence/decision records, and versioned ontology records. Ordered relational links connect each
strategy to its athlete observations, estimates, floors, evidence, adaptations, and needs so
provenance survives deterministic serialization round trips. Ordered links also preserve a
requirement's observation/evidence sources, a resolution's candidate ranking, match issues, and the
availability events used by its environment snapshot.
Block allocations retain their exact demand and policy; prescriptions retain ordered observation
and evidence sources; session templates retain ordered prescription items and provenance; and
planned sessions retain their template, environment, and availability-window identities.
Successor session templates and weekly plans additionally retain explicit predecessor IDs, and
repository checks require carried template items to be the same prescription or a true descendant
through immutable progression decisions.
Safety policies, safety decisions and their observation links, executions, item executions, set
performances, adherence, exposure entries and validations, progression decisions and revisions,
training responses, review policies, reviews, and all of their ordered provenance links are also
append-only. Repository checks duplicate the
domain authorization invariants before persistence so invalid cross-athlete, cross-plan, blocking,
or unsupported execution chains cannot be inserted through normal application code.
Strategy revision links are likewise append-only and must form the concrete chain prior strategy
to completed block to block review to replacement strategy.

## API

FastAPI owns transport concerns and database lifecycle. In addition to health/readiness, narrow
write endpoints expose profile/environment onboarding and daily execution feedback. Onboarding
accepts only non-sensitive direct reports and validates equipment identities
against the global catalog, and atomically appends the athlete, observation, environments, and
equipment-availability events. It creates no estimate, safety assignment, assessment, or plan.
An account and athlete ownership are appended in the same transaction. Initial planning is a
role-protected operator application boundary from reviewed estimates, floors, adaptations,
contexts, and policy to needs, the sole root strategy, and its decision audit. It binds the exact
current reviewer assignment server-side and rejects client-authored reviewer identity.
Completed-block review and review-linked replanning use role-protected preparation and write
endpoints with the same binding. They commit response/review history or successor needs/strategy
history with immutable decision audits; the post-block CLI is retained for local administration.
Strategy-priority resource-demand preparation and
strategy-level block creation are exposed through role-protected operator endpoints and the
planning-authoring CLI. Existing-stimulus exercise
re-resolution uses the same operator-only transport and appends a new resolution without mutating
earlier decisions. Each commits its domain result with an immutable review audit. First-week
prescription, session-container, availability,
and scheduling creation likewise remains an operator-only service and CLI rather than an athlete
route. Weekly-plan and planned-session IDs anchor safety evaluation and actual-performance recording
through immutable observations.
One weekly-plan ID can also anchor a single consecutive roll-forward that consumes existing
prescription-revision lineage rather than accepting new dose.
Weekly advancement first appends a direct availability-confirmation observation and a
`WeeklyAvailability` linked to its source plan without creating planning state. The derived review
state then either requests governed environment revision or permits a separate roll-forward that
consumes the persisted availability identifier. Finalization never accepts replacement windows or
observation provenance.
An execution/prescription pair anchors governed exposure and progression processing. Within the
operator workflow, a block ID anchors completed-history review while a block-review ID anchors
successor-strategy derivation.
Missing dependencies, invalid inputs, and relational conflicts remain distinct transport errors.
Raw domain CRUD is intentionally absent because it could bypass invariants.

The role-protected operator environment-review queue is a read-only projection. It derives pending
work from the same current-week readiness projection used by finalization, then exposes the exact
confirmed windows and unresolved prescription, resolution, stimulus, adaptation, exercise, and
environment identifiers. It creates no mutable task row. Separate role-protected commands append
an exercise re-resolution and a complete environment prescription revision through the existing
deterministic services; neither command performs candidate selection, substitution inference, or
dose generation. A third role-protected operator command creates the initial strategy from exact
reviewed authority versions and explicit candidate scores. A fourth role-protected projection and
command expose exact strategy-to-demand inputs and append one reviewed demand. Neither boundary
infers candidate scores, stimuli, candidate exercises, doses, blocks, or sessions.

Every athlete-scoped route depends on a replaceable authenticated-principal boundary. The
authorizer resolves strategy, block, review, weekly-plan, and execution identifiers back to their
persisted athlete before the use case runs. A different account receives the same not-found result
as an absent aggregate. The equipment catalog is public because it has no athlete state.

The local `dev.<subject>` verifier maps to the configured development issuer and remains prohibited
in production. External mode is a provider-neutral JWT resource-server boundary: it validates an
asymmetric signature from the configured JWKS endpoint plus exact issuer, audience, expiration,
issued-at time, and opaque subject. Algorithms are a server-side allow-list rather than a token-
header choice; bounded JWKS caching permits ordinary provider key rotation. Onboarding creates the
account and owner atomically, and a local operator CLI handles pre-existing fixtures and append-only
reviewer role grants/revocations. An authenticated account
must have a current active `planning_reviewer` assignment to create an initial strategy, prepare a
resource demand, or read and complete operator environment reviews; athlete ownership alone is
insufficient. Operator writes bind the authenticated account and exact role assignment server-side
and reject client-supplied reviewer identity. The role is an
application permission, not evidence of a scientific or professional credential. Production
configuration rejects the development verifier and incomplete or non-HTTPS external settings.
Provider selection, browser authorization-code/session handling, account recovery, and deployment
remain separate from resource-server verification.

Assessment protocol governance uses a distinct append-only `assessment_reviewer` assignment. The
role-protected `GET /v1/operator/assessment-governance` projection evaluates definitions at an
explicit instant and returns all protocol-review and capability-estimation-policy history visible
at that instant, current records, evidence claims, and blockers. It separately evaluates the exact
claims cited by the current protocol review and policy at each record's own review time. Its
governance chain is ready only when the current review is approved, includes a versioned
measurement schema, permits self-administration, has a current approved estimation policy bound to
that exact review, and both authorities' evidence was ready at their decision times. This does not
replace the separate athlete-specific eligibility gate. The role is an application permission, not
evidence of scientific qualification.

The provisional local curation boundary accepts a versioned `AssessmentGovernanceBundle` containing
one exact definition, optional review, and optional estimation policy. Stable caller-supplied record
IDs make retries idempotent; existing IDs must match the complete immutable model. The repository
validates evidence references and linear review/policy history. Before adding a new approved review
or policy, the importer also requires every cited claim to have exact available source snapshots and
a current approved claim review at that authority's timestamp. All new records commit together, and
the governance projector reports the resulting point-in-time blockers. Exact replays of historical
records remain idempotent. The command is disabled in production and external-authentication mode
and is not exposed over HTTP. It neither ingests evidence claims nor verifies source authenticity or
reviewer credentials. Athlete-facing catalog and selection enforcement remains a separate,
deliberate data-migration milestone rather than silently invalidating historical records.

## Web

The Next.js App Router PWA begins with a bounded profile/environment onboarding form. It submits
goals and preferences as a timestamped direct report, presents only controlled persisted equipment
choices, and supports multiple environments without coupling athlete identity to equipment. A
successful submission opens the authoritative current-week projection; the honest initial state is
normally an empty week. The form does not collect sensitive health or injury data, derive capability
estimates, assign safety policy, conduct assessment, or generate training.

A separate `/review` route is the authenticated initial-planning console. Its primary workflow
loads eligible persisted inputs, requires the reviewer to enter every candidate component value,
and saves an immutable `InitialPlanningContextDraft`. A distinct action records one approved,
needs-revision, or rejected `InitialPlanningContextReview`; any changed value requires a new draft.
Only the approving account with the exact still-active assignment can create the strategy from the
approved artifact. The resulting decision evidence names both artifact IDs. The route retains the
externally prepared JSON path as a transitional fallback and is not part of athlete self-service.

Before parsing a document, the console can call the role-protected initial-planning preparation
projection. This read model composes each current estimate with its actual source observations,
compatible exact-current approved floor reviews, and domain-compatible adaptations. It separately
returns exact-current approved priority-policy reviews and all evidence claims referenced by the
offered authorities and adaptations. Stale estimates are visible but ineligible; withdrawn or
future authorities fail closed; an existing root strategy blocks initial creation. The projection
does not emit any candidate scoring field and creates no durable review snapshot or planning state.
The strategy creation boundary independently rejects an estimate that is stale at the explicit
generation time, so bypassing or delaying the console cannot make stale derived state eligible.

Candidate-context tables normalize the eight bounded score/cost components, safety and sequencing
flags, exact authority IDs, and ordered observation/evidence/prerequisite links. Drafts and reviews
are append-only. Eligibility is checked at draft authoring, approved review, and final strategy
creation. Same-account authoring and approval is provisionally allowed, but actor and assignment
fields remain separate for future separation-of-duty policy.

The `/review/resource-demands` route continues one created strategy into an explicit
priority-by-priority demand workflow. It displays every persisted priority and its immutable demand
history, then requires the reviewer to select the environment snapshot, resolver authority,
stimulus constraints, exercise candidate set, observation and evidence lineage, and weekly resource
amounts. No scientific field or exercise is preselected. Ontology relationships are descriptive
context, not a recommendation. The receipt exposes full, partial, infeasible, or deferred resolution
and the exact decision audit; block, week, session, and workout creation remain separate downstream
boundaries.

The `/review/blocks` route continues complete demand history into explicit block-context review.
It requires one selected demand for every priority, one allocation policy, a weekly budget, start
date, four-to-six-week duration, constraints, applicability rationale, uncertainty, and confirmation.
Every material control begins blank. Selected minimums and targets are summarized descriptively,
not used to infer a budget. The resulting allocation receipt preserves shortfalls and infeasibility
and stops before Week 1 authoring.

The `/review/weeks` route loads the exact first-week preparation projection for a block. It shows
every active allocation, selected exercise, stimulus/resolution rationale, environment count, and
currently approved policy review without preselecting any of them. Its authoring workflow represents
the full current discriminated intensity model, dose shape, rest, progression and substitution
references, per-record provenance, arbitrary session composition and order, dated environment
windows, and exact policy review. All material controls begin blank; browser validation is advisory
and the authenticated backend remains authoritative.

The `/review/queue` workbench derives each athlete's next reviewer-owned pre-block boundary from the
current leaf of immutable strategy history. It exposes at most one initial-planning,
resource-demand, block-creation, or first-week item per athlete and keeps missing prerequisites
visible as blockers. Deep links only navigate; each destination reloads its own authoritative
preparation projection. The queue stores no mutable task state and performs no training inference.

The `/review/assessments` workbench is a separate read-only scientific-governance view. It exposes
unreviewed, needs-revision, rejected, schema-incomplete, non-self-administered, missing-policy, and
policy/review-mismatch states together with immutable histories and source identifiers. It cannot
write a review or policy, infer scientific applicability, or authorize an athlete assessment.

The `/review/post-block` route composes the two authenticated closed-loop boundaries. A completed
block is discovered through a role-protected, read-only queue derived from due block, review, and
successor-strategy history. The queue includes both ready and blocked work, transitions reviewed
blocks to the replanning stage, and omits a block only after a successor strategy exists. It stores
no mutable task state. Manual IDs remain available for deep links and recovery.

Opening a block loads immutable weekly/session history, execution, adherence, post-session safety,
eligible estimate, policy, observation, and evidence records. The form requires an exact
non-overlapping prescription partition and explicit response interpretation; it does not suggest
an adaptation grouping, comparison direction, or meaningful-change threshold. A successful receipt
shows the server-derived response arithmetic and block outcome before replanning can begin.

An existing or newly created block-review ID then loads prior priorities, reviewed responses,
eligible estimates, compatible competency floors, observations, and evidence. One blank candidate
editor is structurally created per prior adaptation, but no estimate, floor, score, safety flag,
prerequisite, provenance record, or review interval is selected. The server revalidates all values,
rebuilds capability needs, and appends a lineage-linked successor strategy. Future-dated estimates
are excluded from block review and future or stale estimates are excluded from replanning
preparation so a displayed option can pass the same temporal contract enforced by the write service.

The PWA also has a provenance-first athletic dashboard and a connected current-week screen for an
existing athlete. The dashboard shows the latest derived records per exact measurement series,
confidence and freshness, exposes method/version/source counts on demand, and lists domains that
have not been estimated. It avoids false-precision bars because current protocol-specific units are
not necessarily comparable. An environment panel shows effective equipment state and lets the
athlete append partial current, future, or temporary changes with reliability and provenance. It
states explicitly that reporting equipment does not rewrite existing sessions or establish
substitution equivalence. The current-week screen
renders dated session containers, prescription dose and intensity, a compact rationale disclosure,
environment, safety status, execution, and adherence. Setup, loading, empty, conflict/error, and
mobile layouts are explicit. It also submits structured pre-session self-reports and actual
set/dose/effort workout results through the existing transactional use-case endpoints, then reloads
the read projection. The frontend derives only descriptive execution status from the entered work;
the backend remains authoritative for safety, execution validation, and adherence.

The assessment panel uses the same pattern. It renders protocol instructions and uncertainty from
the workflow projection and creates result controls only when the exact approved review contains a
supported versioned measurement schema. Browser validation is usability support, not authority;
the API reloads the current review and validates type, range, step, category, unit, and lineage
before appending a performance and direct observation.

For a completed result, the panel separately reports capability interpretation as unavailable,
ready, completed, superseded, or stale. It may request interpretation when ready, but never chooses
the policy or calculation. Estimate method, confidence, validity, applicability, uncertainty, and
evidence provenance come back from the backend.

After an execution, the PWA appends a structured post-session safety report linked to that exact
execution and then presents persisted per-prescription progression outcomes. It does not select a
progression policy, exposure definition, exposure policy, or proposed exposure target. Those remain
governed planning inputs rather than daily-user choices.

Beside assessment, a planning-status panel shows whether interpretation is missing or stale,
whether current estimates lack approved planning authorities, whether authorities are present but
athlete-specific context review remains, and which governed boundary separates the root strategy
from a usable first week. Its backend-derived checklists report approved priority-policy and
structurally compatible floor coverage, priority demand coverage, allocation-policy availability,
policy-gated resolution eligibility, current approved scheduling-policy availability, and the
explicit dose,
session-composition, and dated-availability inputs still required. Persisted partial or infeasible
blocks, feasible or infeasible first weeks, and ambiguous block/week history remain explicit.
Compatibility does not establish athlete applicability. The panel exposes no planning-score, dose,
exercise-selection, session-generation, or plan-generation action.

The prescription's exact versioned `progression_rule_reference` is now the action-assignment key.
The current-week projection resolves it against persisted policies and exposes a policy identifier
only when one unique policy can produce an automatically typed load or repetition revision without
exposure inputs. Missing, duplicate, exposure-governed, set/duration, and unsupported-dimension
configurations fail closed with an explicit reason. The browser can request evaluation for a ready
action using only a timestamp; it never returns the projected policy identity as command authority.
The transactional backend resolves the policy again, then loads performance, adherence, and all
post-session safety history before creating the immutable decision and revision.

The projection also exposes the persisted week's availability and one backend-derived weekly-review
state. Closure is descriptive and fail-closed: every scheduled occurrence needs an execution,
recorded executions need post-session safety, and every prescription needs a resolved progression
state before normal roll-forward is offered. `HOLD`, `REVIEW_REQUIRED`, infeasible weeks, missing or
unsupported policies, and final block weeks route to explicit review states. The web client does
not reproduce that decision tree.

For an ordinary closed week, the PWA proposes the existing windows shifted by seven days, permits
owned-environment selection and time edits, and requires explicit confirmation. It sends the exact
environment IDs, instants, reliability, and unverified-user provenance to the availability
confirmation boundary. The saved confirmation is an observation, not an inference that future
availability matches the past. A matching environment enables a separate finalization action; a
changed environment pauses with a visible governed-review state and never invents a substitution.

Technique-constraint reporting remains separate from completion and is not prefilled. When the
assigned policy requires technique confirmation, an unreported or failed constraint produces the
deterministic non-progression outcome rather than a favorable inference.

The secondary local-development setup requires an owned athlete ID. A sequenced immutable
assignment selects the athlete's reviewed safety policy, and the current-week projection exposes
that assignment for inspection. Session safety commands resolve it server-side rather than
accepting a browser-selected policy UUID. Assignment remains outside onboarding because
applicability is governed rather than a user preference. The client uses
`unverified-athlete-user` provenance to avoid implying
real-world identity verification. It sends no classified safety signal because no governed browser
classifier exists; a concerning-symptom selection pauses the ordinary form locally. Verified
production authentication, consent, and account lifecycle controls are required before sensitive
intake or production use.

## Configuration

Configuration is environment-based and prefixed with `AGAS_`. PostgreSQL is the local/default
authoritative store. The PWA's `NEXT_PUBLIC_AGAS_DEVELOPMENT_TOKEN`, provisional
`NEXT_PUBLIC_AGAS_REVIEWER_TOKEN`, and `NEXT_PUBLIC_AGAS_ASSESSMENT_REVIEWER_TOKEN` are public local
identity selectors, not secrets. Production provider secrets and tokens must never use a
`NEXT_PUBLIC_` variable and are not committed.
