# AGENTS.md

## Purpose

This repository builds an adaptive, evidence-grounded system for developing broad general athleticism in ordinary adults.

The product is **not** an LLM workout generator.

Its core purpose is to maintain a structured model of an athlete, identify meaningful physical-development priorities, plan adaptations across multiple timescales, translate those adaptations into feasible training given current equipment and constraints, observe the athlete's response, and update future decisions accordingly.

All coding agents working in this repository must preserve that architecture.

---

## Read This First

Before making substantial product, architecture, training-logic, evidence, or data-model changes:

1. Read `docs/MASTER_BLUEPRINT.md` in full.
2. Inspect existing decision records in `docs/decision-log/`.
3. Inspect relevant tests before changing behavior.
4. Preserve the distinction between:
   - observations,
   - derived estimates,
   - evidence claims,
   - planning decisions,
   - prescriptions,
   - user-facing explanations.

Do not fill an architectural gap by inventing a generic fitness feature.

If the blueprint leaves a question unresolved, implement the smallest replaceable assumption necessary, document it, and preserve uncertainty.

---

# Core Product Invariant

The system must preserve this chain:

```text
OBSERVATION
↓
ATHLETE STATE
↓
IDENTIFIED NEED
↓
ADAPTATION TARGET
↓
EVIDENCE-GROUNDED STRATEGY
↓
STIMULUS
↓
AVAILABLE EXERCISE
↓
DOSE
↓
PERFORMANCE
↓
NEW OBSERVATION
```

Do not collapse the system into:

```text
USER
↓
LLM
↓
WORKOUT
```

That shortcut is a product failure.

---

# Non-Negotiable Engineering Rules

## 1. The LLM is not the training engine

The LLM may:

- interpret natural-language input,
- summarize evidence,
- formulate searches,
- propose planning options,
- explain decisions,
- identify ambiguity,
- critique plans,
- translate structured outputs into user-friendly language.

The LLM must not be the sole authority for:

- safety,
- progression,
- capability scoring,
- training-load changes,
- evidence claims,
- long-term developmental logic,
- exercise substitution equivalence,
- diagnosis,
- genetic inference.

Prefer explicit, inspectable code for rules that can reasonably be deterministic.

---

## 2. Never invent scientific evidence

Do not present pretrained model knowledge as scientific provenance.

A meaningful scientific claim used by the system should be traceable to an `EvidenceClaim` or equivalent structured evidence record.

Do not fabricate:

- citations,
- PMIDs,
- DOIs,
- study results,
- effect sizes,
- populations,
- confidence ratings.

When evidence is unavailable or uncertain, represent the uncertainty.

Consumer fitness websites, Reddit, YouTube, influencer content, and general health-media articles are not acceptable primary scientific evidence for training rules.

---

## 3. Observations are not estimates

Never store a derived athletic capability as though it were directly measured.

Example of prohibited modeling:

```text
power = 74
```

without provenance.

A derived capability estimate must retain:

- source observations,
- method,
- timestamp,
- confidence,
- units or scale,
- model/rule version.

A user report, wearable measurement, field test, and calculated capability estimate are distinct concepts.

Keep them distinct in code and storage.

---

## 4. Preserve uncertainty

Do not create false precision.

The system should be able to represent:

- unknown,
- low-confidence,
- moderate-confidence,
- high-confidence,
- stale,
- contradictory,
- insufficient-data states.

Do not infer biological ceilings from limited training response.

Do not convert "has not improved much under this intervention" into "cannot improve."

---

## 5. Do not force every athlete toward the same profile

The product does not optimize all users toward one standardized stat distribution.

Planning should distinguish among:

- minimum useful competency floors,
- meaningful bottlenecks,
- prerequisites for later development,
- qualities worth maintaining,
- comparative advantages worth cultivating,
- user-valued capabilities.

A strong-but-slow athlete and a fast-but-weak athlete should not receive the same developmental allocation merely because both want "general athleticism."

---

## 6. Adaptation targets and exercises are separate abstractions

Never make a named exercise the fundamental training objective.

The planner should determine the needed adaptation/stimulus first.

Then the exercise resolver should identify a feasible movement given:

- equipment,
- space,
- skill,
- symptoms,
- fatigue,
- time,
- loadability,
- impact,
- progression needs.

Changing equipment should generally change the **means**, not arbitrarily change the **goal**.

---

## 7. Do not pretend substitutions are equivalent when they are not

If the current environment cannot reproduce an important stimulus, represent that limitation.

Bad behavior:

> No barbell is available, so bodyweight squats are an equivalent replacement for high-force strength work.

Preferred behavior:

> The current environment cannot reproduce the previous high-force stimulus. Use the best feasible maintenance or partial substitute and reallocate remaining training resources intelligently.

The software must be able to express infeasibility.

---

## 8. Training priority does not mean training exclusivity

Capabilities may be assigned states such as:

- `DEVELOP`
- `MAINTAIN`
- `EXPOSE`
- `DEFER`

A quality can remain exposed or maintained while another receives primary developmental emphasis.

Do not implement simplistic "train one quality, ignore everything else" block logic unless a specific plan and evidence justify it.

---

## 9. Long-range planning must exist above workout generation

The system must distinguish:

- long-horizon strategy,
- macro/phase strategy,
- block or mesocycle strategy,
- weekly scheduling,
- session prescription,
- exercise selection.

Do not allow a session generator to silently become the long-term planner.

The system should be able to reason about:

- prerequisites,
- potentiation,
- interference,
- maintenance,
- residual effects,
- future exposure needs,
- changing constraints.

---

## 10. Do not hard-code periodization dogma

Do not assume one named periodization system is universally optimal.

The planning system may use:

- concurrent development,
- block emphasis,
- maintenance phases,
- undulating loading,
- concentrated training,
- staged exposure,

when appropriate.

These are tools, not universal laws.

---

## 11. Scientific rules must be versioned

Training rules and evidence-informed heuristics may evolve.

Any material rule should be replaceable and versioned.

Do not silently change the meaning of an existing rule while retaining the same version identifier.

Where feasible, store:

- rule version,
- rationale,
- supporting evidence,
- known uncertainty,
- date introduced.

---

## 12. Major decisions require decision records

For material architectural or training-model decisions, create a file in:

`docs/decision-log/`

Use sequential naming, for example:

```text
0001-initial-architecture.md
0002-capability-confidence-model.md
0003-equipment-resolution-strategy.md
```

Each record should include:

```text
Decision
Reason
Alternatives considered
Evidence
Uncertainty
Consequences
Version/date
```

Do not create decision records for trivial implementation details.

---

# Safety Rules

## Medical boundaries

This product is not a diagnostic or rehabilitation system.

Do not implement behavior that:

- diagnoses a medical condition,
- claims to identify injuries from ordinary training data,
- replaces necessary medical evaluation,
- guarantees injury prevention,
- tells an athlete to ignore concerning symptoms.

Certain symptom classes must be able to interrupt normal programming and trigger escalation guidance.

The exact safety policy belongs in `docs/safety-policy.md` and the safety package.

---

## Exposure progression

Track relevant exposure separately from general fitness.

Examples include:

- running,
- high-speed running,
- jumping,
- landing,
- change of direction,
- high-impact plyometrics.

Do not assume cardiovascular readiness equals tissue readiness.

Large unearned jumps in novel loading or impact should fail validation.

---

## Re-entry

Illness, injury, prolonged interruption, or major detraining may require a re-entry state.

Do not automatically resume the previous plan at full dose after a significant interruption.

---

# Evidence Policy

Refer to `docs/evidence-policy.md`.

At minimum:

### Preferred evidence

- systematic reviews,
- meta-analyses,
- professional position stands,
- consensus statements with transparent methods,
- randomized controlled trials,
- controlled intervention studies,
- strong longitudinal research,
- appropriate mechanistic or validation studies where needed.

### Evidence strength and athlete applicability are separate

A strong study can have poor applicability to a particular athlete.

Represent both when relevant.

Example:

```text
evidence_strength = high
athlete_applicability = low
```

because the study population may differ substantially from the user.

---

# Data Modeling Principles

## Use explicit domain objects

Prefer domain models such as:

- `Athlete`
- `Observation`
- `CapabilityEstimate`
- `Environment`
- `Equipment`
- `Exercise`
- `Adaptation`
- `EvidenceClaim`
- `TrainingPlan`
- `BlockPlan`
- `Session`
- `Prescription`
- `TrainingResponse`
- `DecisionRecord`

over loosely structured blobs.

JSON metadata may be used where flexibility is useful, but important product semantics should remain explicit.

---

## Provenance first

Whenever possible, a derived value should answer:

> Where did this come from?

A planning decision should ultimately be traceable to some combination of:

- athlete observations,
- explicit user constraints,
- evidence claims,
- system policies,
- versioned planning rules.

---

## Time matters

Athlete data becomes stale.

Models should account for:

- timestamps,
- effective dates,
- validity windows,
- superseded estimates,
- historical records.

Do not overwrite meaningful history merely to keep one current value.

---

# Exercise Ontology Principles

Exercises should contain structured metadata sufficient for intelligent resolution and substitution.

Relevant properties may include:

- movement pattern,
- unilateral/bilateral nature,
- primary adaptation,
- secondary adaptation,
- joint demands,
- equipment requirements,
- loadability,
- impact,
- velocity characteristics,
- stability requirement,
- skill complexity,
- fatigue cost,
- soreness cost,
- progression options,
- regressions,
- contraindication/symptom tags.

Do not add hundreds of poorly annotated exercises merely to increase catalog size.

Metadata quality is more important than exercise count.

---

# Adaptation Ontology Principles

Training decisions should be organized around adaptations such as:

- maximal strength,
- hypertrophy,
- aerobic base,
- aerobic power,
- repeated-effort capacity,
- muscular endurance,
- explosive power,
- acceleration,
- high-speed running,
- jump ability,
- landing/deceleration capacity,
- change of direction,
- relevant mobility,
- movement control,
- loaded locomotion,
- tissue/exposure capacity.

Adaptations may have relationships such as:

- prerequisite,
- partial prerequisite,
- potentiating,
- interfering,
- complementary,
- competing for recovery,
- maintenance-compatible.

These relationships need confidence and provenance where they materially affect planning.

---

# Planning Rules

The planner should broadly follow this order:

```text
1. Read athlete state.
2. Read capability estimates and confidence.
3. Identify important uncertainty.
4. Check useful competency floors.
5. Identify bottlenecks.
6. Check prerequisites.
7. Identify valuable strengths.
8. Assign DEVELOP / MAINTAIN / EXPOSE / DEFER.
9. Allocate training resources.
10. Determine required stimuli.
11. Resolve stimuli against available environment.
12. Schedule across the week.
13. Check fatigue/interference.
14. Run safety validation.
15. Generate sessions.
16. Preserve rationale and provenance.
```

Do not shortcut directly from athlete input to exercises.

---

# Progression Principles

Prefer deterministic and testable progression rules where appropriate.

Progression may alter:

- load,
- repetitions,
- sets,
- duration,
- density,
- range of motion,
- speed,
- complexity,
- modality.

Do not assume "add weight" is the universal progression.

Do not hard-code folklore such as a universal weekly percentage increase unless the rule is explicitly justified, versioned, and scoped.

---

# Individual Response Modeling

Population evidence is the starting prior.

Repeated personal observations should gradually inform future prescriptions.

A response record should distinguish:

- intended target,
- intervention,
- dose,
- adherence,
- baseline,
- follow-up,
- observed change,
- measurement uncertainty,
- context,
- confidence.

Do not convert an observed personal response into a genetic claim.

Preferred interpretation:

> This athlete has repeatedly shown a strong response to this type and dose of intervention under similar conditions.

Not:

> This athlete is genetically built for this.

---

# Anti-Sludge Requirements

The system must be actively tested for generic-program convergence.

Maintain synthetic athletes with substantially different:

- strengths,
- weaknesses,
- histories,
- body sizes,
- equipment,
- schedules,
- exposure histories,
- preferences.

Use paired counterfactual tests where one important variable changes.

Examples:

```text
same athlete
except aerobic capacity = low vs high
```

Expected: aerobic allocation changes.

```text
same athlete
except Achilles symptoms = absent vs present
```

Expected: impact/sprint prescription changes.

```text
same athlete
except equipment = full gym vs hotel
```

Expected: exercise selection changes while adaptation targets remain appropriately stable.

```text
same athlete
except strength = poor vs excellent
```

Expected: strength development allocation changes materially.

If meaningfully different athletes repeatedly receive effectively the same adaptation distribution and session structure, treat this as a defect.

---

# Testing Expectations

Changes to important domain behavior require tests.

Prefer:

- unit tests for domain rules,
- integration tests for planning loops,
- counterfactual tests,
- regression tests for synthetic athletes,
- end-to-end tests for core user flows.

Critical behavior should not exist only inside prompts where it cannot be reliably tested.

When fixing a bug, add a regression test whenever practical.

---

# Required First Vertical Slice

Do not prioritize advanced features until this loop works:

```text
ONBOARD
↓
ASSESS
↓
CREATE ATHLETE STATE
↓
IDENTIFY CAPABILITY DEFICITS
↓
CREATE LONG-RANGE STRATEGY
↓
ASSIGN DEVELOP / MAINTAIN / EXPOSE / DEFER
↓
CREATE BLOCK
↓
GENERATE WEEK
↓
LOG TRAINING
↓
ADAPT TRAINING
↓
REASSESS
↓
COMPARE EXPECTED VS OBSERVED RESPONSE
↓
UPDATE ATHLETE MODEL
↓
CREATE NEXT BLOCK
```

The second block must depend meaningfully on what occurred during the first.

---

# Features Deferred Until the Core Loop Works

Do not spend significant effort on:

- social features,
- leaderboards,
- avatar coaches,
- AI-generated workout videos,
- nutrition coaching,
- supplement systems,
- advanced wearable integrations,
- smartwatch apps,
- camera biomechanics,
- injury prediction,
- genetic personalization,
- large opaque machine-learning models.

These are not substitutes for a correct planning architecture.

---

# User Experience Principle

The internal system may be complex.

The user's daily interaction should not be.

A normal user should usually see:

- today's session,
- essential instructions,
- easy completion/logging,
- substitutions if needed,
- a concise explanation of current focus.

Detailed scientific reasoning and provenance should be available on demand through a "Why?" interface, not forced into every workout screen.

---

# Code Quality Expectations

Prefer:

- simple,
- inspectable,
- strongly typed,
- testable,
- replaceable,
- documented implementations.

Avoid:

- premature abstraction,
- unnecessary microservices,
- speculative ML,
- giant untyped JSON structures,
- hidden business logic in prompts,
- unnecessary dependencies,
- complexity added only because it appears sophisticated.

Build the smallest architecture that preserves the product principles.

---

# Agent Workflow

For each bounded implementation task:

1. Read the relevant blueprint sections.
2. Inspect related code and tests.
3. State or write down the implementation decision if material.
4. Implement the smallest coherent slice.
5. Add/update tests.
6. Run relevant tests and static checks.
7. Fix failures.
8. Summarize:
   - what changed,
   - why,
   - assumptions,
   - tests and results,
   - remaining risks,
   - recommended next task.

Do not silently broaden task scope.

---

# When Requirements Conflict

Priority order:

1. Safety policy
2. Explicit product invariants in the master blueprint
3. Evidence/provenance integrity
4. Correct athlete-state modeling
5. User constraints
6. Versioned training/planning rules
7. UX convenience
8. Implementation convenience

If two blueprint requirements genuinely conflict, do not invent a silent resolution.

Document the conflict in a decision record and choose the most conservative replaceable implementation.

---

# Definition of Architectural Failure

Treat any of the following as defects:

- LLM directly generates a workout without structured planning.
- Capability scores appear without provenance.
- Scientific claims appear without evidence records where provenance is required.
- Equipment changes erase the underlying adaptation objective without reason.
- All users drift toward the same capability profile.
- Different athlete states repeatedly produce effectively identical plans.
- The system claims an athlete has reached a genetic ceiling.
- A substitution is presented as equivalent when it cannot produce the required stimulus.
- Safety logic exists only as natural-language prompting.
- A plan cannot explain why a major component exists.
- The app grows flashy features while the closed feedback loop remains incomplete.

---

# Product North Star

Every major technical decision should move the repository toward a system that can truthfully say:

> I know what this athlete can currently do and how certain that estimate is.
>
> I know what currently limits broad physical capability.
>
> I know which qualities should be developed now, which should be maintained, which should receive low-dose exposure, and which should wait.
>
> I know what future abilities current training is preparing for.
>
> I know what equipment and constraints actually exist today.
>
> I can show the scientific basis for important assumptions.
>
> I can observe how this athlete responds to training.
>
> I can revise future decisions when personal evidence contradicts my prediction.
>
> I can do this without forcing every athlete into the same generic fitness program.

If a proposed feature does not help build that system, it is probably not a priority.
