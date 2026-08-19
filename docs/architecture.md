# Architecture

## Current scope

The current foundation corrects the provisional exercise-as-session shape before extending the
closed loop. Explicit `SessionTemplate` containers are scheduled as real workouts, safety remains
session-scoped, and execution, adherence, and progression retain prescription-item identity. Typed
intensity targets replace free text. Existing immutable `TrainingResponse` and deterministic
`BlockReview` behavior remains in place; capability updates and next-block generation are deferred.

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
health-screening constraints. The selector
uses exact tag matching and a versioned deterministic rule. Each selected, deferred, or excluded
decision records reason codes, human-readable rationale, and the immutable intake observations it
used.

Incomplete health screening excludes assessment. Health, injury, and symptom tags are constraints
supplied by intake/safety workflows; the selector does not diagnose or infer medical meaning. A
performed assessment becomes a direct `Observation`. Any
capability state created from it remains a separate derived `CapabilityEstimate`.

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

Exercises and adaptations are separate versioned entities. Exercise records carry structured movement, loading, skill, impact, velocity, stability, fatigue, progression, regression, and equipment metadata. Adaptations can carry typed relationships with confidence and evidence references. This milestone defines the structures without inventing scientific relationships or bulk seed data.

Ontology identity links are relational: exercise adaptation roles, equipment requirements, exercise progression/regression edges, adaptation evidence, and adaptation relationship evidence all use foreign keys. Flexible descriptive metadata remains JSONB. The repository rejects dangling ontology references before persistence.

### Stimulus and exercise resolution

A `StimulusRequirement` is an immutable, versioned expression of what a non-deferred adaptation
priority needs. It retains its strategy, exact priority, adaptation, observations, evidence claims,
movement and loading requirements, minimum loadability, velocity characteristics, physical
constraints, rationale, generation time, and rule version. It deliberately contains no sets,
repetitions, duration, or schedule.

The deterministic resolver first applies hard feasibility constraints: exact equipment
availability, contraindication tags, skill, impact, stability, fatigue, soreness, outdoor access,
space, and noise. Remaining exercises receive a policy-versioned weighted score for adaptation
role, movement coverage, loading type, loadability, and velocity coverage. A result is `FULL` only
when every fidelity component is complete; `PARTIAL` results enumerate every unresolved mismatch;
and `INFEASIBLE` results select nothing and retain explicit reasons. The score ranks candidates—it
does not claim two exercises are scientifically equivalent.

Equipment identity matching is intentionally exact in this milestone. Category- or
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

### Evidence claims

Evidence claims are reviewed, versioned interpretations linked to source identifiers. Evidence strength and athlete applicability are separate. The repository contains no fabricated scientific seed claims.

### Decision records

Material architecture and training-model choices exist as both human-readable records in `docs/decision-log` and a versionable domain type for future persistence.

## Persistence

SQLAlchemy 2 maps domain records to a PostgreSQL-oriented relational schema. JSON columns are used only for flexible context and ontology metadata; identity, ownership, temporal history, versioning, and provenance links remain explicit columns and relationships. SQLite is used only for fast isolated tests.

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
Safety policies, safety decisions and their observation links, executions, item executions, and set performances,
adherence records and their source links, training responses, review policies, reviews, and all of
their ordered provenance links are also append-only. Repository checks duplicate the
domain authorization invariants before persistence so invalid cross-athlete, cross-plan, blocking,
or unsupported execution chains cannot be inserted through normal application code.

## API

FastAPI owns transport concerns and database lifecycle. The initial API intentionally exposes only service metadata and health/readiness endpoints. Domain write endpoints will arrive with coherent use cases rather than raw CRUD that could bypass invariants.

## Web

The Next.js App Router shell is responsive and installable through a web app manifest. It
communicates the session-container foundation honestly and does not present a workout generator,
automatic athlete-state update, or a polished training workflow.

## Configuration

Configuration is environment-based and prefixed with `AGAS_`. PostgreSQL is the local/default authoritative store. Secrets are not committed.
