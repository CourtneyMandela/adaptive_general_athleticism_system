# 0093 — Age-applicable competency floors and append-only demographics

Date: 2026-09-09

Status: accepted

Decision version: `competency-floor-age-applicability@1.0.0`

## Decision

Add nullable structured minimum and maximum age fields to `CompetencyFloor`. A floor with either
bound is eligible for an athlete only when the athlete's age is known at the decision time and
falls inside the inclusive range. Unknown or out-of-range applicability fails closed in planning
status, reviewer preparation, and initial-strategy creation. Unbounded existing floors retain their
previous behavior.

Record date of birth through authenticated, append-only `Observation` records. The latest report
effective at the requested time supplies the current value; a correction appends a new observation
and does not mutate the athlete row or delete the earlier report. The PWA explains that age is an
applicability input, not a capability score.

## Reason

The first candidate physical assessment currently under review has a source population aged
19–35. Free-text population notes cannot safely prevent a numerically compatible floor from being
used outside that population. Age must therefore be machine-checkable before any such floor is
introduced. The athlete model already had a legacy date-of-birth field, but overwriting that field
would destroy correction history and weaken decision-time reproducibility.

## Evidence

Lein et al.'s 30-second chair-stand reference study reports healthy adults aged 19–35 (PMID
35949374; PMCID PMC9340829). Hall et al. report age- and sex-related differences across adult
chair-stand performance (PMID 27356977). These sources demonstrate that population age can affect
applicability. They do not establish an AGAS competency threshold, a safety cutoff, or a universal
age range. No numeric floor is added by this change.

## Alternatives considered

- **Keep age only in prose.** Rejected because deterministic planning cannot reliably enforce it.
- **Overwrite `Athlete.date_of_birth`.** Rejected because corrections would erase historical
  inputs used by earlier decisions.
- **Store only a current age.** Rejected because age becomes stale and cannot reproduce age at an
  earlier planning instant.
- **Use broad age bands instead of date of birth.** Deferred. Bands minimize data but introduce
  boundary ambiguity as time passes; exact date supports deterministic age-at-date calculation.
- **Treat missing age as compatible.** Rejected because this silently assumes population
  applicability.

## Assumptions and provisional choices

- Age is calculated in completed years on the projection or planning date.
- Bounds are inclusive and limited to 0–130 years as a data-quality constraint, not a medical
  judgment.
- An attested authenticated self-report has high reliability for demographic identity only. It is
  not evidence about physical capability.
- Existing unbounded floors remain usable so this migration does not reinterpret historical test
  fixtures or authorities.
- Exact date of birth is sensitive account data and belongs only behind athlete ownership checks.

## Uncertainty

- A future privacy review may prefer an encrypted demographic store or derived age-band credential.
- Age bounds alone do not prove full population applicability; sex, health status, protocol,
  training history, and other factors remain governed review inputs.
- The correct chair-stand competency threshold remains unresolved and requires a separate evidence
  decision.

## Consequences

- An otherwise matching age-bounded floor cannot masquerade as applicable when age is unknown.
- Reviewer and athlete projections expose the applicability gap explicitly.
- Initial-strategy creation rechecks applicability server-side and cannot bypass the projection.
- Corrections preserve prior reports and allow historical projections to reproduce the value known
  at that time.
- The next coherent milestone is a prepared, narrowly scoped competency-floor candidate with exact
  population, protocol, evidence, uncertainty, and owner ratification.
