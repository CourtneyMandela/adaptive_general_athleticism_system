# Adaptive General Athleticism System
## Master Build Blueprint v0.1

**Working name:** AGAS  
**Purpose of this document:** Give an autonomous or semi-autonomous AI software-development agent enough specification to build the first scientifically defensible working version of an adaptive AI system for developing broad, transferable athletic capability in ordinary adults.

---

# 1. Mission

Build a system whose purpose is to progressively transform a generally healthy, initially sedentary or recreationally active adult into a highly capable generalist athlete.

The target is not specialization in one sport.

The target is:

> A person with no major physical weak link, several genuinely strong physical qualities, broad exposure to different movement demands, and enough strength, endurance, power, speed, coordination, work capacity, and tissue tolerance to perform unexpectedly well when confronted with unfamiliar recreational physical challenges.

The system must optimize **general capability under physical novelty**, not merely gym performance.

Examples of target activities include:

- hiking
- recreational running
- climbing
- swimming
- paddling
- recreational field or court sports
- carrying awkward objects
- obstacle courses
- dancing
- jumping
- sprinting
- martial arts
- cycling
- physically demanding travel or outdoor activities

Success means that unfamiliar physical challenges are rarely limited by a glaring deficit in basic physical preparation.

---

# 2. Primary Product Principle

The system is **not an LLM workout generator**.

Architecture must separate:

1. scientific evidence
2. athlete state
3. adaptation models
4. training constraints
5. programming rules
6. optimization/planning
7. safety rules
8. LLM reasoning
9. user interaction

The LLM may reason, explain, query evidence, identify ambiguity, and propose options.

The LLM must **not** be allowed to invent the fundamental training logic on each request.

The core rule is:

> The LLM assists the training system. It is not itself the training system.

---

# 3. Non-goals

V1 is not intended to:

- diagnose medical conditions
- predict injuries with high confidence
- replace physicians, physical therapists, athletic trainers, or qualified coaches where professional evaluation is appropriate
- produce sport-specific elite athletes
- optimize bodybuilding
- optimize powerlifting totals
- optimize marathon performance
- prescribe drugs or supplements
- provide clinical rehabilitation
- infer genetic ceilings
- perform sophisticated camera-based biomechanics
- build a social fitness network
- gamify exercise primarily through points or streaks
- generate workouts by copying popular fitness templates

These can be considered separately later.

---

# 4. Definition of General Athletic Preparedness

Represent athleticism as a multidimensional state rather than a single score.

V1 should track the following capability domains.

## 4.1 Aerobic capacity

Ability to sustain prolonged work using predominantly oxidative metabolism.

Relevant measures may include:

- submaximal heart-rate response
- field endurance tests
- estimated VO2-related metrics
- sustainable pace
- recovery between efforts

---

## 4.2 High-intensity aerobic / repeated-effort capacity

Ability to repeatedly produce moderately high outputs and recover between bouts.

Do not collapse this into aerobic capacity.

---

## 4.3 Maximum strength

Ability to produce high force against external resistance.

Track upper and lower body separately where useful.

---

## 4.4 Relative strength

Force-producing capacity relative to body mass.

Important for:

- climbing
- jumping
- locomotion
- bodyweight tasks
- recreational sports

---

## 4.5 Muscular endurance

Ability to repeat submaximal muscular efforts.

---

## 4.6 Explosive power

Ability to express force rapidly.

Potential observable tasks:

- jumps
- medicine-ball throws
- fast concentric actions

---

## 4.7 Acceleration and speed

Represent at least:

- acceleration ability
- exposure to high-speed running
- maximal or near-maximal locomotor speed

Do not require maximal sprint testing in unprepared beginners.

---

## 4.8 Deceleration and change of direction

Ability to absorb force and redirect movement.

This should be distinct from straight-line speed.

---

## 4.9 Loaded locomotion / carrying capacity

Ability to move while carrying significant external load.

Examples:

- farmer carries
- suitcase carries
- rucking
- awkward-object carries

---

## 4.10 Mobility and movement control

Track task-relevant usable ranges of motion.

Do not optimize maximal flexibility for its own sake.

The question is:

> Does available motion permit desired physical tasks with adequate control?

---

## 4.11 Balance and coordination

Ability to control the body under changing movement demands.

---

## 4.12 Movement versatility

Breadth of physical movement exposure.

Examples:

- jumping
- throwing
- catching
- climbing
- crawling
- rotating
- lateral movement
- swimming
- uneven terrain
- racquet or ball sports

This is not simply a physiological quantity.

It represents the breadth of movement problems the athlete has encountered.

---

# 5. Meta-outcome: Transfer Under Novelty

General athleticism cannot be completely inferred from laboratory or gym metrics.

Create an additional longitudinal construct:

**Novelty Transfer Performance**

The athlete periodically attempts unfamiliar or infrequently practiced activities.

Examples:

- climbing gym
- pickup basketball
- kayaking
- long hike
- racquet sport
- obstacle course
- dance class
- swimming
- trail run
- recreational martial arts
- recreational tournament

Record:

- perceived difficulty
- primary physical limiter
- secondary limiter
- unexpected soreness
- task competence
- time required to become comfortable
- whether conditioning limited performance
- whether strength limited performance
- whether coordination limited performance
- whether mobility limited performance
- whether localized tissue tolerance limited performance

This information feeds back into the athlete model.

The system must periodically ask:

> Is the athlete becoming better only at tests, or is their physical competence actually generalizing?

---

# 6. Do Not Optimize Everyone Toward the Same Profile

The system must explicitly reject the assumption that every athlete should have identical capability scores.

Instead use a three-layer objective.

## Layer 1 — Competency floors

For each domain define a broad useful minimum range.

A severe deficit receives substantial priority.

Example:

An athlete with excellent strength but extremely poor aerobic capacity should receive significant aerobic development.

---

## Layer 2 — Bottleneck removal

Determine which capability deficits materially restrict:

- broad activity participation
- development of other qualities
- recovery capacity
- desired recreational challenges

Prioritize removal of those bottlenecks.

---

## Layer 3 — Comparative advantages

Once broad competency is achieved, allow natural or acquired strengths to continue developing.

A broadly athletic individual might ultimately resemble:

- strength/power dominant
- endurance dominant
- speed/power dominant
- highly versatile balanced generalist

All may represent successful outcomes.

The system should create **robust generalists with individual character**, not standardized bodies.

---

# 7. Never Infer Genetic Destiny From Early Performance

Athletes differ, but observed response includes:

- biological differences
- measurement error
- adherence
- sleep
- nutrition
- intervention dose
- intervention choice
- training history
- stress
- test reliability

Therefore maintain separate fields for:

- current performance
- observed response
- response confidence
- estimated trainability
- uncertainty

Do not include:

`genetic_ceiling = X`

V1 must never claim that an athlete has reached a genetic limit.

A better representation:

```text
Aerobic response to current intervention:
small

Confidence:
moderate

Observation count:
3 blocks

Alternative interventions tested:
1

Estimated long-term ceiling:
unknown
```

Require repeated measurements before concluding that a training response is unusually small or large.

---

# 8. Athlete State Model

The athlete must exist as persistent structured data.

Suggested high-level schema:

```text
Athlete
├── identity
├── demographics
├── anthropometrics
├── training history
├── current activity level
├── health constraints
├── injury history
├── symptom constraints
├── exercise competencies
├── preferences
├── goals
├── schedule
├── recovery context
├── equipment environments
├── capability estimates
├── observations
├── assessments
├── training history
├── exposure history
├── response history
├── novelty challenges
└── plan history
```

---

# 9. Capability Estimates Are Not Ground Truth

Never store:

```text
power = 74
```

without provenance.

Instead:

```text
CapabilityEstimate
{
    domain
    estimate
    unit_or_scale
    confidence
    calculation_method
    evidence_observation_ids[]
    created_at
    valid_until
    model_version
}
```

Every displayed capability estimate must be traceable back to actual observations.

Example:

```text
Power estimate

Sources:
standing broad jump
countermovement jump
loaded jump performance

Confidence:
moderate
```

If only one noisy measure exists:

```text
Confidence:
low
```

---

# 10. Observation Model

All athlete knowledge should ultimately derive from observations.

Examples:

```text
Observation
{
    id
    athlete_id
    timestamp
    type
    measurement
    unit
    source
    reliability
    context
}
```

Sources may include:

- user report
- workout result
- test result
- wearable
- manually entered result
- imported activity
- coach evaluation

User-reported information should remain distinguishable from measured information.

---

# 11. Equipment and Environment Model

Equipment must be modeled as a changing constraint.

Never make the program fundamentally dependent on named exercises.

Represent environments separately.

Example:

```text
Environment: Home

Available:
floor
jump rope
resistance bands
Peloton bike

Unavailable:
barbell
rack
heavy dumbbells
sled
rowing ergometer
```

Another environment:

```text
Environment: Full Gym

Available:
barbells
rack
plates
dumbbells
cables
machines
cardio machines
boxes
medicine balls
```

Users must be able to:

- create environments
- switch environments
- temporarily mark equipment unavailable
- add new equipment
- indicate load limits
- indicate space constraints
- indicate noise constraints
- indicate outdoor access

Changing environment should **not alter the developmental objective**.

It should cause the prescription engine to solve for another exercise capable of producing the desired stimulus.

---

# 12. Exercise Ontology

An exercise is not merely a string.

Each exercise needs structured properties.

Example:

```text
Exercise
{
    name
    movement_patterns[]
    primary_adaptations[]
    secondary_adaptations[]
    primary_muscles[]
    joint_demands[]
    loading_type
    stability_requirement
    skill_complexity
    impact_level
    velocity_characteristic
    fatigue_cost
    soreness_cost
    equipment_requirements[]
    equipment_alternatives[]
    loadability
    progression_options[]
    regression_options[]
    contraindication_tags[]
    measurement_methods[]
}
```

Example:

```text
Exercise:
Bulgarian split squat

Movement:
knee-dominant
unilateral

Primary:
lower-body strength
hypertrophy

Secondary:
balance
hip stability

Loadability:
high with equipment
moderate without equipment

Skill:
moderate

Impact:
low
```

---

# 13. Prescription Must Begin With a Stimulus, Not an Exercise

The planner should first produce:

```text
Target adaptation:
lower-body force production

Movement exposure:
knee dominant

Desired loading:
high

Repetition range:
moderate-low

Stability:
high

Fatigue budget:
moderate

Session time:
12 minutes
```

Only then should the exercise resolver select a movement.

Possible result:

Full gym:

> safety-bar squat

Hotel:

> heavy dumbbell Bulgarian split squat

Home:

> loaded split squat using available external load

If available equipment cannot adequately reproduce the desired stimulus, report that explicitly.

Example:

> Current environment cannot provide a strong maximal-strength stimulus. Use the best available maintenance stimulus and temporarily shift additional training resources toward capacities that can be trained well here.

Do not falsely claim every substitute is equivalent.

---

# 14. Adaptation Ontology

Create explicit objects for trainable adaptations.

Example:

```text
Adaptation
{
    name
    prerequisites[]
    preferred_stimuli[]
    valid_modalities[]
    dose_dimensions[]
    fatigue_characteristics
    typical_measurement_methods[]
    maintenance_requirements
    interference_relationships[]
    potentiation_relationships[]
    evidence_claim_ids[]
}
```

Initial adaptations should include:

- maximal strength
- hypertrophy
- explosive power
- aerobic base
- aerobic power
- repeated-effort capacity
- muscular endurance
- acceleration
- high-speed running
- jump ability
- landing/deceleration capacity
- change of direction
- basic movement control
- relevant mobility
- loaded locomotion
- tendon/tissue exposure

---

# 15. Adaptation Relationship Graph

Create a directed graph describing relationships between physical qualities.

Possible relationship types:

- prerequisite
- partial prerequisite
- potentiating
- interfering
- complementary
- maintenance-compatible
- competing-for-recovery
- skill-dependent

Each relationship requires:

```text
relationship
strength
confidence
population
evidence_ids[]
notes
```

Example:

```text
Maximum strength → power

Relationship:
potentiating

Strength:
moderate

Evidence confidence:
moderate

Interpretation:
greater force capacity can increase the substrate from which power is developed, but power-specific high-velocity exposure remains necessary.
```

Relationships must not be represented as universal biological laws unless evidence warrants that confidence.

---

# 16. Planning Hierarchy

Planning must occur at multiple timescales.

```text
Athlete state
      ↓
Long-horizon development strategy
      ↓
Macrocycle strategy
      ↓
Mesocycle/block strategy
      ↓
Microcycle
      ↓
Session
      ↓
Exercise prescription
      ↓
Execution
      ↓
Observation
      ↓
Updated athlete state
```

---

# 17. Long-Horizon Planner

Time horizon:

approximately 6–24 months.

Its purpose is not to produce precise workouts.

Its purpose is to answer:

- what qualities are currently limiting?
- what prerequisites are missing?
- what should be developed first?
- what can develop concurrently?
- what should remain on maintenance?
- what needs introductory exposure?
- what should deliberately wait?
- what current strengths deserve further development?
- what future activities is the athlete preparing to tolerate?

The long-range plan must be revisionable.

Never promise a rigid one-year sequence.

---

# 18. Four Training States for Every Capability

Every significant training quality should be assigned one current status:

## DEVELOP

Meaningful training resources are allocated to causing adaptation.

## MAINTAIN

Use approximately the minimum practical dose needed to retain current capability.

## EXPOSE

Use low doses to:

- develop familiarity
- preserve skill
- establish tissue tolerance
- prepare for future emphasis

## DEFER

Intentionally allocate little or no meaningful training resource yet.

Example:

```text
Strength        DEVELOP
Aerobic base    DEVELOP
Jumping         EXPOSE
Sprinting       EXPOSE
Agility         EXPOSE
Anaerobic work  DEFER
```

Later:

```text
Strength        MAINTAIN
Aerobic base    MAINTAIN
Power           DEVELOP
Sprinting       DEVELOP
Jumping         DEVELOP
Agility         DEVELOP
```

Priority must not be interpreted as exclusivity.

---

# 19. Multi-objective Optimization

The planner is solving a constrained optimization problem.

Conceptually:

```text
maximize:

broad physical capability
+ reduction of major deficits
+ useful exceptional strengths
+ expected transfer to target activities
+ adherence probability
+ expected future potentiation

while minimizing:

training time
fatigue
interference
unnecessary redundancy
risk exposure
equipment incompatibility
schedule conflict
```

This need not initially use an advanced mathematical optimizer.

V1 may use:

- explicit scoring
- ranked constraints
- rules
- heuristic search

Do not use opaque machine learning before the system can be inspected and debugged.

---

# 20. Priority Scoring

V1 priority score should consider:

```text
priority =
deficit severity
× relevance to overall athleticism
× relevance to user goals
× prerequisite value
× expected trainability
× general transfer

adjusted by:

fatigue cost
injury/exposure constraints
available equipment
time cost
interference
maintenance requirements
confidence in estimate
```

Avoid pretending the exact equation is scientific truth.

All weights must be versioned and configurable.

---

# 21. Diminishing Marginal Utility

The system must explicitly model that raising a severe weakness is often more valuable than maximizing an already excellent quality.

Example:

Improving endurance from very poor to adequate may have enormous general utility.

Improving endurance from excellent to elite may demand considerable additional training while adding relatively little generalist utility.

However, the system must still allow high-performing traits to continue improving when:

- the athlete enjoys them
- the athlete responds unusually well
- they complement desired activities
- development cost remains reasonable
- doing so does not create major deficits elsewhere

---

# 22. Evidence Engine

Scientific evidence must exist as a first-class subsystem.

The LLM's pretrained knowledge is not sufficient provenance.

Allowed scientific source classes:

### Tier A

- systematic reviews
- meta-analyses
- major professional position stands
- consensus statements with transparent evidence methods

### Tier B

- randomized controlled trials
- controlled trials
- strong longitudinal intervention studies

### Tier C

- observational studies
- validation studies
- biomechanics studies
- mechanistic studies

### Tier D

- expert interpretation used only when higher evidence is unavailable

Consumer fitness sources are **not allowed as scientific evidence**.

Do not use:

- Men's Health
- random fitness blogs
- Reddit
- YouTube creators
- commercial supplement websites
- influencer articles

to establish training claims.

Such sources may only be used for non-scientific contextual information when explicitly appropriate.

---

# 23. Initial Evidence Retrieval Infrastructure

V1 should support structured searches using:

- PubMed
- Crossref
- optionally OpenAlex
- DOI metadata

Store publication metadata locally.

Prefer source metadata that includes:

- authors
- title
- journal
- year
- PMID
- DOI
- abstract
- publication type

---

# 24. Evidence Claim Object

Do not merely save papers.

Extract claims.

```text
EvidenceClaim
{
    claim
    domain
    population
    intervention
    comparator
    outcome
    study_design
    sample_size
    duration
    effect_direction
    uncertainty
    limitations
    evidence_strength
    applicability_notes
    source_ids[]
    reviewer
    created_at
    version
}
```

Example:

```text
Claim:
Concurrent aerobic and resistance training generally permits improvement in both aerobic capacity and maximal strength, although explosive-strength adaptation may be more vulnerable to interference depending on training organization.

Population:
healthy adults

Evidence:
meta-analysis

Confidence:
moderate/high
```

---

# 25. Scientific Applicability

Whenever evidence informs a recommendation, assess:

- age similarity
- sex relevance
- training status
- baseline fitness
- population
- intervention similarity
- duration
- dose
- exercise modality
- measured outcome

A study of elite cyclists must not automatically receive high applicability to a sedentary beginner.

Store both:

```text
evidence_strength
```

and:

```text
athlete_applicability
```

These are different.

---

# 26. Do Not Hard-code Periodization Dogma

The system may use:

- block approaches
- concurrent development
- undulating loading
- accumulation/emphasis phases
- maintenance phases
- concentrated training

depending on the problem.

It must not assume that one named periodization theory is universally optimal.

Planning logic should instead ask:

> What sequence of adaptations is most defensible for this athlete given prerequisites, current state, available resources, interference, and evidence?

---

# 27. Initial Scientific Seed Library

Seed the evidence database with at least the following topics:

1. progressive resistance-training prescription
2. resistance-training dose-response
3. strength and power development
4. concurrent strength/endurance training
5. aerobic training dose-response
6. interval training
7. maintenance doses
8. detraining
9. periodization
10. sprint exposure
11. plyometric training
12. landing/deceleration training
13. resistance training and injury prevention
14. neuromuscular injury-prevention programs
15. exercise-response variability
16. measurement error in individual-response research
17. aerobic nonresponse and intervention dose
18. training-load monitoring
19. motor learning
20. physical-activity adherence

Each seed rule must link to evidence claims.

---

# 28. Assessment Engine

Assessment should be adaptive.

The system must not prescribe the same maximal testing battery to every athlete.

Assessment selection considers:

- training age
- body mass
- health screening
- injury history
- current symptoms
- equipment
- exercise skill
- recent activity

Use three layers.

---

# 29. Layer 1 — Intake

Collect:

- basic demographics
- height/weight if user wishes
- activity history
- prior sports
- resistance-training history
- endurance history
- injury history
- current symptoms
- available weekly training time
- schedule
- equipment
- preferred activities
- disliked activities
- recreational goals
- upcoming events

---

# 30. Layer 2 — Baseline Capability Testing

Select safe tests appropriate to the person.

Possible categories:

### Aerobic

- walk test
- submaximal step test
- cycling test
- run/walk test

### Strength

- submaximal load estimation
- standardized repetition task
- bodyweight movement

### Power

only when appropriately prepared:

- broad jump
- vertical jump

### Muscular endurance

- push-ups
- repeated squat variation
- appropriate trunk endurance measure

### Balance/control

- unilateral balance
- controlled movement tests

### Loaded locomotion

when equipment exists:

- standardized carry

### Mobility

task-specific range assessments

Do not require every test.

---

# 31. Layer 3 — Exposure Inventory

Ask whether the athlete has recent experience with:

- sprinting
- jumping
- landing
- throwing
- catching
- climbing
- swimming
- lateral sport movement
- loaded carries
- hiking
- uneven terrain

Lack of exposure matters independently from strength or cardiovascular fitness.

---

# 32. Reassessment

Each capability estimate must have a recommended reassessment interval.

Examples:

- strength-related indicators: several weeks
- aerobic indicators: several weeks
- movement exposure: continuously
- full athletic review: approximately quarterly

Avoid excessive testing.

Testing should inform decisions, not become training's primary purpose.

---

# 33. Programming Engine

Programming must follow this sequence:

```text
1. Read athlete state
2. Read current capability estimates
3. Identify uncertainty
4. Evaluate competency floors
5. Identify bottlenecks
6. Check prerequisite graph
7. Identify strengths worth cultivating
8. Determine DEVELOP / MAINTAIN / EXPOSE / DEFER
9. Allocate weekly training resources
10. Identify required stimuli
11. Resolve stimuli against equipment
12. Schedule stimuli across week
13. Run interference/fatigue checks
14. Run safety checks
15. Generate sessions
16. Generate rationale/provenance
```

The LLM must not skip directly from step 1 to step 15.

---

# 34. Block Planning

Initial V1 planning horizon:

**4–6 weeks**

Each block stores:

```text
BlockPlan
{
    hypothesis
    priority_domains[]
    maintenance_domains[]
    exposure_domains[]
    deferred_domains[]
    expected_adaptations[]
    assessment_targets[]
    weekly_dose_targets
    progression_rules[]
    constraints[]
    evidence_ids[]
}
```

Example hypothesis:

> Increasing basic lower-body strength while maintaining aerobic volume and gradually introducing landing exposure should improve force capacity without sacrificing current endurance and should prepare the athlete for higher-intensity power work.

---

# 35. Microcycle Planning

Default to approximately one-week microcycles but make length configurable.

The scheduler must account for:

- session duration
- user availability
- high-fatigue sessions
- high-impact exposure
- concurrent training interference
- recovery
- work schedule
- recreational activities

It should be able to move sessions when life changes.

---

# 36. Session Planning

Every prescribed exercise requires:

```text
exercise
adaptation_target
reason_for_inclusion
sets
reps_or_duration
intensity_target
rest
progression_rule
substitution_class
```

The UI does not need to show all of this by default.

But it must exist internally.

---

# 37. Progression Engine

Use deterministic rules where reasonable.

Example resistance rule:

```text
IF
all target repetitions completed
AND
reported effort within target
AND
technique constraint satisfied
AND
symptom threshold acceptable

THEN
progress according to exercise progression rule
```

Progression may involve:

- load
- repetitions
- sets
- range of motion
- exercise complexity
- speed
- density

Do not assume load increase is always appropriate.

---

# 38. Conditioning Progression

Track:

- duration
- intensity
- frequency
- modality
- recovery

Progression decisions should account for:

- recent exposure
- completion
- heart-rate response where available
- RPE
- symptom response
- concurrent workload

Do not encode a universal “10% rule” as fact.

Progression limits should be configurable and evidence-linked.

---

# 39. Impact and Speed Exposure Ledger

Create dedicated exposure tracking for:

- jumping
- landing
- running
- high-speed running
- change of direction
- high-impact plyometrics

This prevents a common failure where cardiovascular fitness improves faster than tissues have adapted to impact.

Store recent exposure separately from general fitness.

---

# 40. Fatigue Model

V1 does not need to pretend fatigue is precisely measurable.

Track several dimensions:

```text
systemic fatigue
lower-body muscular fatigue
upper-body muscular fatigue
impact exposure
high-speed exposure
cardiorespiratory load
subjective readiness
```

Inputs may include:

- recent training
- RPE
- soreness
- sleep
- work stress
- illness
- resting HR
- HRV if available

Wearable data is informative but not authoritative.

---

# 41. Daily Autoregulation

Before training, collect minimal information:

- readiness
- unusual soreness
- pain/symptoms
- major sleep disruption
- major schedule limitation

Potential adaptations:

- unchanged
- reduce volume
- reduce intensity
- substitute modality
- remove high-impact element
- change intervals to lower-intensity conditioning
- shorten session

The goal is to preserve the intended adaptation whenever possible.

Bad behavior:

> Athlete slept poorly → replace entire workout with stretching.

Preferred behavior:

> Preserve high-value low-risk work while reducing the portions most sensitive to current fatigue.

---

# 42. Safety Layer

Safety rules execute before LLM discretion.

Categories:

### Medical escalation

Certain reports terminate ordinary programming and advise appropriate medical evaluation.

### Symptom modification

New pain or unusual symptoms can restrict:

- impact
- speed
- loading
- movement range

### Exposure constraints

Unprepared athletes should not suddenly receive large doses of:

- maximal sprinting
- high-intensity plyometrics
- long running volumes
- high-load strength work

### Return after interruption

Training following illness, injury, or prolonged inactivity requires a re-entry state.

The LLM cannot override hard safety constraints.

---

# 43. Injury Resilience Philosophy

Do not promise injury prevention or injury-proofing.

Instead optimize:

- progressive tissue exposure
- strength
- movement competence
- appropriate workload progression
- neuromuscular exposure
- variety of physical demands
- adequate recovery

The system should describe this as **capacity and resilience development**, not guaranteed injury prevention.

---

# 44. Maintenance Engine

Capabilities that are sufficiently developed should not necessarily continue receiving development-level volume.

The system must estimate a maintenance dose.

Maintenance rules require evidence provenance.

V1 should support reducing volume while preserving sufficient intensity or specificity when evidence supports it.

This frees training resources for new priorities.

---

# 45. Individual Response Model

Every completed developmental block should generate a response record.

```text
TrainingResponse
{
    target_domain
    intervention_summary
    dose
    adherence
    baseline_measurement
    followup_measurement
    observed_change
    measurement_uncertainty
    contextual_factors
    confidence
}
```

Over time build:

```text
AthleteResponseProfile
```

Examples:

```text
Moderate-volume strength training:
consistently strong response

Running-based aerobic development:
moderate response
higher soreness cost

Cycling intervals:
strong aerobic response
low orthopedic cost
```

These are empirical observations, not genetic statements.

---

# 46. Updating Personalization

Initially:

```text
population evidence weight = high
personal evidence weight = low
```

As repeated observations accumulate:

```text
population evidence
        +
personal response history
        ↓
updated prescription
```

Personal evidence must never override basic safety merely because an athlete previously tolerated something.

---

# 47. Block Review

At the end of a block:

1. retrieve original hypothesis
2. measure adherence
3. retrieve relevant performance changes
4. account for measurement uncertainty
5. inspect fatigue/symptoms
6. compare expected and observed adaptation
7. determine whether intervention likely worked
8. update response model
9. update athlete capability estimates
10. reconsider long-horizon strategy
11. produce next block

Example:

```text
Hypothesis:
Aerobic emphasis will improve submaximal conditioning
while strength maintenance preserves current force capacity.

Observed:
Aerobic benchmark +8%
Strength benchmark unchanged
Adherence 91%
Fatigue acceptable

Conclusion:
Hypothesis supported.

Next:
Move aerobic capacity from DEVELOP to MAINTAIN.
Increase lower-body strength allocation.
```

---

# 48. Long-Range Plan Replanning

Every major reassessment should trigger the long-range planner.

It may revise:

- sequence
- timing
- priorities
- anticipated future blocks
- exposure schedule

Example:

Original:

```text
strength emphasis
→ power emphasis
→ speed emphasis
```

Observed:

Strength develops unusually quickly but lower-leg impact tolerance lags.

Revised:

```text
strength maintenance
+
tissue exposure development
→ running exposure
→ power/speed expansion
```

The roadmap must be adaptive.

---

# 49. Anti-Sludge Evaluation Harness

This is mandatory before V1 is considered successful.

Create a suite of synthetic athletes.

Examples:

### Athlete A

Very strong. Poor aerobic capacity. Little running exposure.

### Athlete B

Strong endurance runner. Weak upper body. Good locomotion.

### Athlete C

Former soccer athlete after 10 sedentary years.

### Athlete D

Complete sedentary beginner with obesity.

### Athlete E

Strong lifter with no jumping or lateral movement.

### Athlete F

Fast recreational athlete with poor maximal strength.

### Athlete G

Balanced athlete with limited mobility in one relevant task.

### Athlete H

Highly fit cyclist with low impact tolerance.

### Athlete I

Beginner with only home equipment.

### Athlete J

Same athlete as I after joining a full gym.

---

# 50. Counterfactual Testing

Create paired synthetic athletes differing in exactly one important variable.

Examples:

```text
same athlete
except:
Achilles symptoms = absent/present
```

Expected:

Impact/sprint prescription changes.

---

```text
same athlete
except:
aerobic capacity = low/high
```

Expected:

Aerobic priority changes.

---

```text
same athlete
except:
equipment = full gym/hotel room
```

Expected:

Adaptation targets remain similar where appropriate but exercises change.

---

```text
same athlete
except:
strength = poor/excellent
```

Expected:

Strength allocation changes substantially.

---

# 51. Generic-Program Detection

Measure similarity between programs.

Possible metrics:

- exercise Jaccard similarity
- weekly adaptation-allocation similarity
- session-structure similarity
- training-domain allocation
- exercise-category distribution

High exercise overlap is not automatically wrong.

But athletes with meaningfully different deficits should show meaningfully different **adaptation allocations and rationales**.

Flag suspicious convergence for review.

---

# 52. Evidence-Provenance Tests

Every major rule used to make a plan should be traceable to:

- explicit system policy
- evidence claim
- athlete observation
- user constraint

The plan should be able to answer:

> Why is this here?

Example:

```text
Exercise:
split squat

Why:
lower-body strength target

Why strength:
current capability below desired floor

Why unilateral:
movement versatility requirement

Why today:
fits fatigue and weekly schedule

Evidence:
linked claims
```

---

# 53. LLM Roles

Allow the LLM to:

- conduct onboarding
- interpret natural-language user reports
- formulate evidence searches
- summarize papers
- compare evidence applicability
- explain prescriptions
- propose substitutions to the deterministic engine
- identify ambiguous information
- generate block hypotheses
- critique plans
- produce user-friendly coaching

Do not allow the LLM alone to:

- diagnose
- create unbounded training progressions
- ignore safety constraints
- fabricate evidence
- assign capability scores without measurements
- infer genetics
- declare an athlete injury-proof
- silently modify the athletic objective

---

# 54. Planner / Critic Architecture

Use separate AI roles.

## Planner

Proposes:

- priorities
- sequencing
- block hypothesis
- stimulus allocation

## Critic

Reviews:

- generic-template convergence
- missing athletic domains
- unnecessary redundancy
- weak evidence
- mismatch between athlete state and prescription
- excessive fatigue
- premature specialization
- ignored comparative advantages
- ignored equipment constraints
- questionable sequencing

The deterministic engine makes final validation.

---

# 55. User Experience

The complexity should mostly remain invisible.

Main screen:

```text
TODAY
45 minutes

A. Trap-bar deadlift
3 × 5

B. DB bench
3 × 8

C. Split squat
2 × 8 / side

D. Row
3 × 10

E. Bike
18 minutes
```

Optional:

**Why this workout?**

> Lower-body strength is a current development priority. Aerobic capacity is being maintained. Jump volume is intentionally low while impact exposure develops.

---

# 56. Equipment Change UX

User selects:

> I'm traveling.

Then:

```text
Available:
hotel treadmill
light dumbbells
floor
```

System responds by recalculating exercises.

It should explain when something cannot be reproduced:

> Heavy strength stimulus is limited in this environment. We will use a maintenance-oriented alternative and emphasize aerobic work and unilateral training until heavy loading is available again.

---

# 57. Post-workout UX

Keep friction extremely low.

Collect:

- completed?
- actual reps/load/time
- approximate effort
- pain/unusual symptoms?
- optional note

Do not require a lengthy questionnaire after every session.

---

# 58. Weekly Review UX

Show:

```text
Sessions completed: 4/4

Strength progression:
on target

Aerobic volume:
on target

Impact exposure:
+12%

Readiness:
stable

Current focus:
basic strength + aerobic capacity
```

Then:

> No plan change required.

Or:

> Repeated lower-leg soreness suggests impact exposure should remain unchanged next week.

---

# 59. Athletic Dashboard

Display domains with confidence.

Example:

```text
Strength           ███████░░░  high confidence
Aerobic capacity   ██████░░░░  moderate confidence
Power              ████░░░░░░  low confidence
Speed              ███░░░░░░░  low confidence
Loaded movement    █████░░░░░  moderate confidence
```

Never imply false precision.

---

# 60. “Why?” Interface

Every block should provide:

### What are we developing?

### Why now?

### What are we maintaining?

### What are we deliberately not emphasizing?

### What would cause the plan to change?

### What evidence supports the strategy?

This is critical for trust and debugging.

---

# 61. Recommended Technical Stack

Favor maintainability over novelty.

## Frontend

- Next.js
- TypeScript
- responsive PWA

Reason:

A phone-accessible web application minimizes deployment friction.

---

## Backend

Python + FastAPI.

Reasons:

- strong scientific ecosystem
- simple modeling
- easy optimization work
- easy testing
- strong AI-tool integration

---

## Database

PostgreSQL.

Add:

- JSONB where flexible metadata is needed
- pgvector if evidence embeddings become useful

Do not use a vector database as the authoritative athlete record.

---

## Scientific computation

Python libraries as needed:

- NumPy
- pandas
- SciPy

Avoid unnecessary ML frameworks in V1.

---

## Testing

- pytest
- frontend unit tests
- Playwright for end-to-end tests

---

# 62. Repository Layout

```text
/
├── apps/
│   └── web/
│
├── services/
│   ├── api/
│   ├── planner/
│   └── evidence/
│
├── packages/
│   ├── domain/
│   ├── exercise_ontology/
│   ├── adaptation_models/
│   ├── safety/
│   └── evaluation/
│
├── data/
│   ├── exercises/
│   ├── adaptations/
│   ├── evidence_seed/
│   └── synthetic_athletes/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── counterfactual/
│   └── anti_sludge/
│
└── docs/
    ├── architecture.md
    ├── evidence-policy.md
    ├── safety-policy.md
    └── decision-log/
```

---

# 63. V0 — Architecture Prototype

Do not build a polished app first.

Goal:

Prove that the reasoning loop works.

Implement:

1. athlete schema
2. equipment/environment schema
3. capability estimates
4. exercise ontology
5. basic adaptation ontology
6. primitive assessment engine
7. priority engine
8. block planner
9. session generator
10. workout logger
11. progression engine
12. reassessment
13. block review

A command-line interface or minimal web UI is sufficient initially.

---

# 64. First Vertical Slice

The first genuinely usable system must demonstrate this exact loop:

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
SELECT CURRENT DEVELOP / MAINTAIN / EXPOSE / DEFER STATES
↓
CREATE 4-WEEK BLOCK
↓
GENERATE WEEK 1
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

Nothing else takes priority until this works.

---

# 65. Vertical Slice Demonstration Scenario

The demo athlete should:

- be previously sedentary
- have poor endurance
- have low baseline strength
- have limited jumping/running exposure
- have four training days available
- initially have full gym equipment

The system generates a block.

Halfway through:

> Athlete travels for one week with only hotel equipment.

Expected behavior:

- goals remain unchanged
- heavy-strength stimulus is downgraded appropriately
- substitute exercises are selected
- available aerobic work continues
- no claim is made that light dumbbells perfectly replace heavy strength work
- original plan resumes or is recalculated after return

This scenario must be an automated integration test.

---

# 66. V1 Exercise Seed Data

Seed approximately:

**75–125 exercises**

Enough to represent:

- squat patterns
- hinge patterns
- presses
- pulls
- carries
- unilateral lower-body movements
- basic trunk training
- jumps
- landing drills
- running
- cycling
- rowing
- loaded walking
- basic agility drills
- mobility/control work

Quality of metadata matters more than having thousands of exercises.

---

# 67. V1 Evidence Seed

Seed approximately:

**25–50 high-value evidence claims**

Do not attempt to ingest the entire scientific literature.

Focus on claims necessary to operate V1.

Every seeded claim requires manual or secondary-AI verification.

---

# 68. V1 Synthetic Athlete Library

Create at least:

**25 synthetic athlete profiles**

Represent meaningful variation in:

- fitness
- strengths
- weaknesses
- body size
- training history
- equipment
- available time
- movement exposure
- activity preferences

Use these continuously in regression testing.

---

# 69. Milestone 1 — Domain Foundation

Deliver:

- database schema
- athlete state
- observations
- capability estimates
- environments
- exercises
- adaptations
- evidence claims

Acceptance:

All objects version correctly and retain provenance.

---

# 70. Milestone 2 — Assessment

Deliver:

- intake
- adaptive test selection
- test result recording
- capability estimation
- confidence grading

Acceptance:

Two athletes with different histories should not automatically receive identical maximal tests.

---

# 71. Milestone 3 — Planning Engine

Deliver:

- competency-floor detection
- bottleneck ranking
- comparative-advantage handling
- DEVELOP/MAINTAIN/EXPOSE/DEFER assignment
- initial long-range roadmap
- block hypothesis generation

Acceptance:

Synthetic athletes with opposite profiles receive meaningfully different allocation strategies.

---

# 72. Milestone 4 — Exercise Resolver

Deliver:

- stimulus definition
- equipment matching
- substitution scoring
- infeasibility detection

Acceptance:

Equipment changes modify exercise selection without arbitrarily modifying the underlying training objective.

---

# 73. Milestone 5 — Session and Progression Engine

Deliver:

- weekly scheduling
- sessions
- prescriptions
- workout logging
- deterministic progression
- symptom modifications

Acceptance:

Completed sessions produce predictable progression according to explicit rules.

---

# 74. Milestone 6 — Closed Loop

Deliver:

- reassessment
- block review
- training-response records
- capability updates
- updated priorities
- next-block generation

Acceptance:

The second block depends on what actually happened during the first.

---

# 75. Milestone 7 — Evidence Retrieval

Deliver:

- PubMed search
- metadata retrieval
- evidence storage
- evidence claim extraction
- evidence applicability review
- plan citation

Acceptance:

A user can inspect why a major programming assumption exists and trace it to scientific literature.

---

# 76. Milestone 8 — Anti-Sludge Harness

Deliver:

- synthetic athlete tests
- paired counterfactual tests
- similarity analysis
- generic-program alerts
- planner critic

Acceptance:

Changing a meaningful athlete variable produces an appropriately meaningful program change.

---

# 77. Milestone 9 — Usable PWA

Deliver:

- onboarding
- dashboard
- Today screen
- exercise completion
- substitutions
- equipment editor
- weekly review
- reassessment
- Why? screen

Acceptance:

A normal user can operate the system daily without talking to an AI in free-form chat.

---

# 78. V1 Definition of Done

V1 is complete only if all of the following work:

- user can create athlete profile
- user can define equipment
- user can complete an adaptive assessment
- capability estimates have provenance/confidence
- system creates a long-range development hypothesis
- system assigns training-domain states
- system generates a block
- block has evidence provenance
- sessions are generated from adaptation needs
- changing equipment triggers intelligent substitution
- workout performance is logged
- progression occurs automatically
- symptoms can alter appropriate training
- block can be reassessed
- personal response record is generated
- subsequent block changes accordingly
- synthetic athlete tests demonstrate non-generic programming
- major decisions are inspectable

---

# 79. Features Explicitly Deferred

Do not build until V1 succeeds:

- camera form analysis
- automated rep counting
- sprint video analysis
- injury prediction
- advanced wearable integrations
- smartwatch application
- nutrition coaching
- social functionality
- leaderboards
- AI-generated exercise videos
- avatar coaches
- advanced genetic personalization
- large-scale machine learning
- automated medical interpretation

---

# 80. Future V2

Add:

- calendar integration
- wearable integration
- richer activity imports
- improved response modeling
- probabilistic capability estimates
- N-of-1 experiment design
- richer novelty challenge system
- more sophisticated long-horizon optimization

---

# 81. Future V3

Add computer vision cautiously:

- rep detection
- range-of-motion estimation
- basic velocity
- jump height
- sprint timing

Do not allow computer vision to claim diagnostic certainty.

---

# 82. Future V4

Potentially introduce individualized predictive modeling:

```text
Given:
athlete state
training dose
sleep/recovery
past response

Predict:
expected adaptation distribution
```

Only pursue this after sufficient high-quality longitudinal data exists.

---

# 83. Critical Agent Instructions

Any AI coding agent implementing this project must obey:

### Rule 1

Do not generate generic workout templates to fill architectural gaps.

### Rule 2

Do not invent scientific claims.

### Rule 3

Do not rely on LLM memory as evidence provenance.

### Rule 4

Store uncertainty.

### Rule 5

Store decision provenance.

### Rule 6

Separate adaptation targets from exercise selection.

### Rule 7

Separate athlete observations from derived estimates.

### Rule 8

Version all training rules.

### Rule 9

Do not infer genetic ceilings.

### Rule 10

Do not claim equipment substitutions are physiologically equivalent when they are not.

### Rule 11

Do not optimize every athlete toward the same capability profile.

### Rule 12

Do not optimize only the easiest variables to measure.

### Rule 13

Do not build flashy features before the closed-loop planner works.

### Rule 14

Every major plan decision must answer:

> Why?

### Rule 15

Every major scientific rule must answer:

> According to what evidence?

---

# 84. Decision Record Requirement

Any material architectural or training-model decision should create:

```text
DecisionRecord
{
    decision
    reason
    alternatives_considered
    evidence
    uncertainty
    version
    date
}
```

This allows future developers or AIs to distinguish:

- deliberate design
- evidence-based rule
- provisional assumption
- implementation convenience

---

# 85. Scientific Updating

The evidence engine should periodically support review of rules when:

- stronger evidence appears
- existing evidence is contradicted
- an assumption proves poorly predictive
- applicability changes

Never silently replace a training rule.

Create a new version.

---

# 86. Foundational Scientific Guardrails for V1

The implementation should begin from several broad conclusions, while retaining the ability to revise their exact application.

1. Progressive resistance training can improve strength, muscle size, power, muscular endurance, and physical performance in healthy adults.

2. Different resistance-training variables should be manipulated according to the desired adaptation rather than assuming a single universal protocol.

3. Strength and aerobic development can usually occur concurrently, although programming can matter when maximizing power or certain highly specific adaptations.

4. Maintenance commonly requires less training volume than acquisition, making it possible to shift resources between qualities.

5. Periodization is a planning tool rather than a universal sequence that should be imposed on every athlete.

6. Apparent individual training response must be interpreted cautiously because intervention dose and measurement variability can affect classification.

7. Progressive resistance and neuromuscular training can contribute to reducing injury risk in athletic populations, but the product must not promise injury prevention.

These should enter the system as evidence claims with citations and confidence levels rather than hidden assumptions.

---

# 87. Initial Research Anchors

Seed review should include at minimum:

**Currier et al., 2026**  
American College of Sports Medicine Position Stand: Resistance Training Prescription for Muscle Function, Hypertrophy, and Physical Performance in Healthy Adults.  
PMID: 41843416.

**Schumann et al., 2022**  
Compatibility of Concurrent Aerobic and Strength Training for Skeletal Muscle Size and Function.  
PMID: 34757594.

**Spiering et al., 2021**  
Maintaining Physical Performance: The Minimal Dose of Exercise Needed to Preserve Endurance and Strength Over Time.  
PMID: 33629972.

**Mølmen et al., 2019**  
Block Periodization of Endurance Training — A Systematic Review and Meta-analysis.  
PMID: 31802956.

**Moesgaard et al., 2022**  
Effects of Periodization on Strength and Muscle Hypertrophy in Volume-Equated Resistance Training Programs.  
PMID: 35044672.

**Montero & Lundby, 2017**  
Refuting the Myth of Non-response to Exercise Training.  
PMID: 28133739.

**Ross et al., 2015**  
Separate Effects of Intensity and Amount of Exercise on Interindividual Cardiorespiratory Fitness Response.  
PMID: 26455890.

**Lauersen et al., 2014**  
The Effectiveness of Exercise Interventions to Prevent Sports Injuries.  
PMID: 24100287.

These are starting anchors, not the complete evidence base.

---

# 88. The Core Invariant

At every level of the system, preserve this chain:

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

Never permit the system to collapse into:

```text
USER
↓
LLM
↓
WORKOUT
```

---

# 89. First Build Order for an Autonomous Coding Agent

Execute in this order:

1. Create repository and architecture documents.
2. Implement core domain models.
3. Implement observation and provenance system.
4. Implement athlete state.
5. Implement equipment environments.
6. Implement exercise ontology.
7. Implement adaptation ontology.
8. Seed initial exercise data.
9. Seed initial evidence claims.
10. Implement capability estimate framework.
11. Implement basic assessments.
12. Implement priority scoring.
13. Implement DEVELOP/MAINTAIN/EXPOSE/DEFER logic.
14. Implement long-range strategy object.
15. Implement block planner.
16. Implement stimulus-to-exercise resolver.
17. Implement weekly scheduler.
18. Implement session prescription.
19. Implement workout logging.
20. Implement deterministic progression.
21. Implement fatigue/exposure ledgers.
22. Implement safety validation.
23. Implement reassessment.
24. Implement response records.
25. Implement block review.
26. Implement next-block replanning.
27. Build synthetic athlete suite.
28. Build counterfactual tests.
29. Build anti-sludge analysis.
30. Build minimal mobile-friendly UI.
31. Run the complete vertical-slice demo.
32. Fix architectural failures before adding features.

---

# 90. Final Acceptance Question

Do not judge success by:

> Can the AI generate impressive-looking workouts?

Judge it by:

> Given two meaningfully different humans, does the system correctly understand that they require different developmental trajectories, choose defensible priorities and sequencing, translate those priorities into whatever equipment is actually available, measure what happens, learn from the result, and make the next decision better than the previous one?

If the answer is yes, the core product exists.

If the answer is no, additional features should not be built.

---

# 91. Product North Star

The long-term system should eventually be able to say:

> I know what you can currently do.  
> I know how certain that estimate is.  
> I know what currently limits your general physical capability.  
> I know which qualities should be developed now and which should wait.  
> I know what we are trying to prepare you to tolerate later.  
> I know what equipment you actually have today.  
> I know how you responded to previous training.  
> I can show the scientific basis for the important assumptions I'm using.  
> I can change course when the evidence from your own training contradicts my prediction.  
> And I can do all of that without forcing you into the same generic workout template as everyone else.

That is the system this repository should build.