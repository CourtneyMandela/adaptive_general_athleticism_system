# 0094 - Prepared age-bounded competency-floor candidate

Date: 2026-09-10

Status: accepted

Decision version: `prepared-chair-stand-floor-candidate@1.0.0`

## Decision

Add a server-owned, content-addressed competency-floor candidate for the governed 30-second
chair-stand estimate. The candidate threshold is 11 completed repetitions, uses
`higher_is_better`, and is applicable only from age 30 through 39 inclusive. A planning reviewer
may inspect the exact population, source, threshold, interpretation, limitations, version, and
SHA-256 digest in the existing planning-authorities screen. Ratification submits only the immutable
identity, digest, and attestation.

The server atomically persists the PubMed/PMC source snapshot, one exact evidence claim, its
evidence review, the `CompetencyFloor`, its planning review, reviewer-assignment provenance, and a
decision record. Exact retries are idempotent. Changed content or occupied identities fail closed
without partial persistence.

## Evidence and interpretation

Rodriguez-Castro et al. report empirical sex- and age-stratified reference values from 393
community-dwelling Colombian adults. In the 30-to-39-year strata, the 2.5th percentile for the
30-second test was 11 repetitions for women (n=29) and 11 for men (n=31). The paper describes p2.5
as a lower limit of normality for its reference population (PMID 42183074; PMCID PMC13193711; DOI
10.25100/cm.v56i4.6874).

AGAS does not elevate that descriptive percentile into a universal scientific truth. The floor is
an explicit engineering interpretation: a deliberately low, replaceable owner-alpha screening
boundary that can identify a possible development need. It is not medical clearance, diagnosis,
injury-risk prediction, an ideal target, or evidence of a training dose.

Primary source: https://pmc.ncbi.nlm.nih.gov/articles/PMC13193711/

## Alternatives considered

- **Use the young-adult study mean as the floor.** Rejected because a mean is a reference center,
  not a defensible minimum.
- **Infer a lower bound from mean minus standard deviations.** Rejected because it would add an
  unreported distributional assumption and obscure the derived threshold.
- **Apply the Colombian table to every age.** Rejected because age-specific values differ and a
  broad range would weaken applicability controls.
- **Create sex-specific records.** Deferred because both 30-to-39 strata report the same p2.5
  value; sex-specific applicability would add sensitive data without changing this candidate.
- **Wait for a perfect universal threshold.** Rejected for the owner alpha because no universal
  threshold is likely to be honest. Narrow, versioned, disclosed uncertainty is more testable.
- **Automatically approve the prepared floor.** Rejected because preparation and authority remain
  separate governance events.

## Assumptions and provisional choices

- The matching AGAS estimate preserves the same unit and narrow assessment scope; it is not a
  general strength score.
- The source protocol and AGAS self-administered protocol are similar but not identical. That
  limitation is retained in both evidence and floor review records.
- Evidence strength is moderate for the exact descriptive cohort claim and athlete applicability
  is low because of geography, subgroup size, and administration differences.
- Age compatibility is necessary but insufficient for broader population applicability.
- Ratification is appropriate only for a single-owner alpha and should be superseded when more
  applicable evidence or longitudinal personal calibration becomes available.

## Consequences

- An age-compatible current chair-stand estimate can have a reviewed comparison input for initial
  planning after explicit ratification.
- Missing DOB, age outside 30-39, stale estimates, scope mismatch, unit mismatch, absent review, or
  changed evidence continues to block use.
- The owner is asked to evaluate a prepared decision, not author scientific JSON or choose a
  threshold from scratch.
- The next blocker is governed athlete-specific candidate context and the first reviewed strategy;
  this milestone itself creates no workout.
