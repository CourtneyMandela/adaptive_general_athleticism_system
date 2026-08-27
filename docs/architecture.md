# Architecture

## Current scope

The current foundation adds controlled exercise/adaptation vocabulary and a deliberately small,
validated seed boundary. A tested full-gym/travel/return scenario re-resolves exercises against the
current environment without changing the athlete, strategy, block, adaptation, or stimulus.
Existing immutable session, execution, response, and block-review behavior remains in place;
reviewed capability estimates can now drive a lineage-linked replacement strategy. Automatic
capability estimation from raw results, candidate-context inference, workout generation, and
next-block generation remain deferred.

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

services/planner consumes domain contracts for deterministic assessment selection,
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

### Adaptive assessment

Assessment definitions are versioned protocols with explicit domain, intensity, unit, body-mass
requirement, equipment, training-history, skill, recent-exposure, injury, symptom, and
health-screening constraints. Each definition has a separate append-only
`AssessmentDefinitionReview` history. Reviews retain an explicit decision, ordered protocol and
result-entry instructions, reassessment interval, self-administration status, evidence-claim
links, applicability, uncertainty, reviewer, time, and version. Replacements form a linear
sequence; a later rejection or needs-revision decision withdraws a prior approval without erasing
it. Only definitions whose latest review is approved appear in the read-only global assessment
catalog, and persistence rejects athlete selections against any other definition. No operational
assessment protocol is seeded by this boundary.

Athlete-level authority is separate. `AssessmentEligibilityReview` is an append-only, linear,
time-bounded operator decision that references the observations and screening process actually
reviewed. Its outcomes allow selection, block selection, or require further review; the record is
not a diagnosis or medical clearance. Athlete-facing services cannot create this authority.

The persisted assessment-run service loads the athlete's current allowed eligibility decision and
the catalog's current approved, self-administered definitions. It derives equipment categories from
the effective-dated state of an owned environment, records the non-medical context as a direct
observation, and atomically appends decisions, selections, and an `AssessmentSelectionRun`.
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
accepts no free-form medical context, verifies the definition unit, and rolls back its observation
if lineage persistence fails. Deferred and duplicate results fail closed. Selection and performance
runs do not create estimates, apply norms, or generate workouts.

An authenticated `AssessmentWorkflowProjection` derives the athlete-facing state from those
append-only records rather than persisting a mutable status flag. It exposes safe eligibility
timing, environment choices, reviewed protocol instructions and uncertainty, ordered deterministic
decisions, exact versions and evidence identifiers, and completed result observations. It omits
screening sources, operator identity, and screening-process details. The PWA can submit the narrow
selection context when the projection permits it, but does not duplicate authority rules or render
generic result controls without a reviewed measurement schema.

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

The strategy is not a workout. It contains no exercise, dose, weekly schedule, or session. Safety
restriction, introductory exposure, missing prerequisites, unresolved information, competency
deficits, and athlete-valued comparative advantages remain distinguishable reasons.

### Environment and equipment

An athlete may own multiple environments. Equipment is cataloged independently, while availability is an append-only, effective-dated event with capabilities and limits. Environment changes therefore constrain future exercise resolution without changing athlete identity or adaptation intent.

The `EnvironmentSnapshotBuilder` selects the latest active availability event for each equipment
item at a stated capture time. A temporary outage may expire and reveal an older still-effective
availability record. Snapshots retain the exact availability IDs used, merged equipment
capabilities, load limits, usable floor area, outdoor access, and the environment's maximum noise
level. They are derived resolver inputs, not a replacement for availability history.

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
revision record to both the superseded prescription and authorizing decision. Repetitions, sets,
duration, and compatible absolute or relative load targets are automatically applicable in V1;
unsupported or unit-incompatible adjustments fail explicitly. Evidence, observation,
exposure-entry, and safety-decision provenance uses ordered foreign-key association tables.

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

### Persisted next-block creation

`PersistedBlockCreationService` is the application boundary from a stored strategy to an immutable
`BlockPlan`. The caller supplies identities for already-governed resource demands and an allocation
policy, plus dates, weekly time budget, and explicit constraints. The service reconstructs every
referenced exercise resolution and delegates allocation to `BlockPlanner` in one transaction.

The planner requires one demand for every strategy priority and verifies exact
strategy–priority–adaptation–state lineage. Active demands must reference a matching persisted
stimulus and exercise resolution; deferred demands consume no resources. Consequently a revised
strategy cannot reuse a demand attached to its predecessor, and block two materially depends on
the replanning result rather than merely copying block one. This boundary stops at resource
allocation: it creates no prescriptions, sessions, exercise substitutions, or progression rules.

### Governed resource-demand preparation

`PersistedResourcePreparationService` provides the upstream application boundary required by block
creation. For an active strategy priority, it loads the persisted adaptation, environment,
effective-dated equipment availability, equipment records, explicit exercise candidates, and
resolver policy. It binds the caller's explicit stimulus specification to the immutable priority,
derives one environment snapshot, resolves exercise fidelity, and appends the requirement,
resolution, and resource demand in one transaction.

The service does not derive scientific dose from `DEVELOP`, `MAINTAIN`, or `EXPOSE`; minimum and
target minutes plus frequency remain explicit versioned inputs. An `INFEASIBLE` resolution is
persisted and makes downstream block planning infeasible. A `DEFER` priority instead creates a
zero-resource demand with no stimulus or resolution. This makes absence of training intentional
and traceable rather than ambiguous.

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
together.

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
immediately following week of the same block. The request supplies only new dated availability and
a preparation timestamp. The service retains the source plan's scheduling policy, follows each
session-template item through normalized prescription-revision records, and selects the latest
revision that existed at preparation time.

Unchanged prescriptions and templates are reused. If one or more items changed, the service creates
a new immutable template with `previous_template_id`, preserving item order, section, frequency,
and prescription ancestry while recomputing duration and fatigue from the carried items. The new
`WeeklyPlan` records `previous_weekly_plan_id` and advances exactly seven days and one block week.
The complete template, availability, and plan chain commits or rolls back together; unique lineage
constraints reject competing automatic successors.

The service adds no dose rule and accepts no client-authored prescription revision. Changed
environments may make scheduling infeasible, but they never trigger an alleged equivalent exercise
substitution. Exercise re-resolution, exposure proposals, block continuation, and next-block
creation remain separate governed workflows.

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
appends the response/review chain in one transaction. One block has at most one completed review in
V1. The review remains descriptive and the existing replanning boundary is the only component that
may derive a successor strategy.

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

### Decision records

Material architecture and training-model choices exist as both human-readable records in `docs/decision-log` and a versionable domain type for future persistence.

## Persistence

SQLAlchemy 2 maps domain records to a PostgreSQL-oriented relational schema. JSON columns are used only for flexible context and ontology metadata; identity, ownership, temporal history, versioning, and provenance links remain explicit columns and relationships. SQLite is used only for fast isolated tests.

Provider-subject accounts and athlete ownerships are normalized immutable records. The account
identity is not embedded in `Athlete`; one account may own multiple athlete records, while the V1
database constraint permits exactly one permanent owner record per athlete. Transfer, revocation,
and delegated roles are not implied by this narrow schema.

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
write endpoints expose profile/environment onboarding, post-block replanning, and persisted block
creation. Onboarding accepts only non-sensitive direct reports, validates equipment identities
against the global catalog, and atomically appends the athlete, observation, environments, and
equipment-availability events. It creates no estimate, safety assignment, assessment, or plan.
An account and athlete ownership are appended in the same transaction. A block-review ID anchors
the stored replanning lineage; the application service loads the governed inputs, invokes
the deterministic planner, and commits new capability needs plus exactly one successor strategy
atomically. A strategy-priority pair anchors resource-demand preparation; the service appends
either an active stimulus-resolution-demand chain or one deferred zero-resource demand. A strategy
ID anchors block creation; the service loads persisted demands, their resolutions, and the selected
allocation policy before atomically appending a block. A block ID anchors explicit prescription,
session-container, availability, and weekly scheduling creation. Weekly-plan and planned-session
IDs anchor safety evaluation and actual-performance recording through immutable observations.
One weekly-plan ID can also anchor a single consecutive roll-forward that consumes existing
prescription-revision lineage rather than accepting new dose.
Roll-forward appends a direct availability-confirmation observation before the next
`WeeklyAvailability`, template revisions, and weekly plan. Its transaction preserves both the
athlete report authorizing scheduling and the earlier observation references carried by the
submitted availability draft.
An execution/prescription pair anchors governed exposure and progression processing. A block ID
anchors completed-history review, while a block-review ID anchors successor-strategy derivation.
Missing dependencies, invalid inputs, and relational conflicts remain distinct transport errors.
Raw domain CRUD is intentionally absent because it could bypass invariants.

Every athlete-scoped route depends on a replaceable authenticated-principal boundary. The
authorizer resolves strategy, block, review, weekly-plan, and execution identifiers back to their
persisted athlete before the use case runs. A different account receives the same not-found result
as an absent aggregate. The equipment catalog is public because it has no athlete state.

Only a development bearer verifier exists today. `dev.<subject>` maps to the configured development
issuer, onboarding creates the account and owner atomically, and a local operator CLI handles
pre-existing fixtures. Production configuration rejects that verifier; external mode remains
unavailable until a cryptographically verifying provider adapter is implemented.

## Web

The Next.js App Router PWA begins with a bounded profile/environment onboarding form. It submits
goals and preferences as a timestamped direct report, presents only controlled persisted equipment
choices, and supports multiple environments without coupling athlete identity to equipment. A
successful submission opens the authoritative current-week projection; the honest initial state is
normally an empty week. The form does not collect sensitive health or injury data, derive capability
estimates, assign safety policy, conduct assessment, or generate training.

The PWA also has a connected current-week screen for an existing athlete. It
renders dated session containers, prescription dose and intensity, a compact rationale disclosure,
environment, safety status, execution, and adherence. Setup, loading, empty, conflict/error, and
mobile layouts are explicit. It also submits structured pre-session self-reports and actual
set/dose/effort workout results through the existing transactional use-case endpoints, then reloads
the read projection. The frontend derives only descriptive execution status from the entered work;
the backend remains authoritative for safety, execution validation, and adherence.

After an execution, the PWA appends a structured post-session safety report linked to that exact
execution and then presents persisted per-prescription progression outcomes. It does not select a
progression policy, exposure definition, exposure policy, or proposed exposure target. Those remain
governed planning inputs rather than daily-user choices.

The prescription's exact versioned `progression_rule_reference` is now the action-assignment key.
The current-week projection resolves it against persisted policies and exposes a policy identifier
only when one unique policy can produce an automatically typed load or repetition revision without
exposure inputs. Missing, duplicate, exposure-governed, set/duration, and unsupported-dimension
configurations fail closed with an explicit reason. The browser can request evaluation for a ready
action, but the transactional backend still loads performance, adherence, all post-session safety
history, and the evidence-linked policy before creating the immutable decision and revision.

The projection also exposes the persisted week's availability and one backend-derived weekly-review
state. Closure is descriptive and fail-closed: every scheduled occurrence needs an execution,
recorded executions need post-session safety, and every prescription needs a resolved progression
state before normal roll-forward is offered. `HOLD`, `REVIEW_REQUIRED`, infeasible weeks, missing or
unsupported policies, and final block weeks route to explicit review states. The web client does
not reproduce that decision tree.

For an ordinary closed week, the PWA proposes the existing windows shifted by seven days, permits
time edits, and requires explicit confirmation. It sends the exact environment IDs, instants,
source-observation IDs, reliability, and unverified-user provenance to the transactional
roll-forward boundary. The saved confirmation is an observation, not an inference that future
availability matches the past.

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
authoritative store. The PWA's `NEXT_PUBLIC_AGAS_DEVELOPMENT_TOKEN` is a public local identity
selector, not a secret. Production provider secrets and tokens must never use a `NEXT_PUBLIC_`
variable and are not committed.
