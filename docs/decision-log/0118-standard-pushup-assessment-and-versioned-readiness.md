# 0118 - Standard push-up assessment and versioned readiness

Date: 2026-09-15

Status: accepted

Decision version: `standard-pushup-assessment@1.0.0`

## Decision

Prepare a second immutable assessment-governance candidate for maximum consecutive standard
push-ups. The candidate uses ACSM's *Guidelines for Exercise Testing and Prescription*, 12th
edition, ISBN 9781975219246, Chapter 3, Box 3.10 and Table 3.11 as a reviewed source snapshot. The
operational assessment records one whole-number count of valid consecutive standard repetitions
and derives only a low-confidence, 28-day, assessment-specific estimate using the existing
latest-matching-observation method.

The stored bibliographic metadata uses the National Library of Medicine catalog record for the
12th-edition EPUB. This corrects the fourth editor to Paul M. Gallo without rewriting the earlier
proposal-only batch whose exact digest and feedback history remain immutable.

Use the same standard toes-as-pivot movement for every athlete who selects this protocol. Do not
infer sex and do not activate the table's age/sex fitness categories. The table uses standard
push-ups for males and modified knee push-ups for females, so those rows are not comparable enough
to serve as a hidden sex-neutral scale. This release creates no competency floor, pass/fail result,
training priority, exercise selection, or dose.

Expand the current athlete readiness report with an upper-body/wrist/hand concern question and a
controlled standard-push-up pre-check. Bump the readiness rule to
`assessment-readiness-screen@1.1.0`. Assessment workflow and selection treat eligibility created by
an older owner-readiness-rule version as inactive rather than silently extending its meaning.
An athlete with a reported recent moderate-activity base and no global stop factor may be considered
for high-effort assessments; otherwise the ceiling remains moderate. Movement-specific answers
exclude only the affected assessment rather than blocking unrelated measurements.

## Reason

The chair stand proved the assessment-to-observation-to-estimate machinery but is a poor primary
measure for the owner-alpha athlete. A standard push-up is phone-friendly, needs no specialized
equipment, and yields a real repeatable upper-body endurance observation. It is safer and more
practical than beginning with maximal treadmill testing, 1-RM lifting, or impact testing.

The source also demonstrates why protocol evidence and operational interpretation must stay
separate. It supports the construct and procedure but does not validate a universal AGAS threshold.
Keeping the result narrow adds useful athlete data without laundering a sex-specific category into
a training rule.

## Alternatives considered

- **Activate the age-30-to-39 male threshold of 17 repetitions.** Rejected because athlete sex has
  not been explicitly reported and the descriptive category is not an AGAS competency floor.
- **Use the lower source threshold as a universal floor.** Rejected because it would compare
  different movement protocols while disguising the mismatch.
- **Implement a modified knee push-up automatically for some athletes.** Rejected because AGAS must
  not infer sex or choose a protocol from identity assumptions. A separate regression assessment
  can be governed later on its own merits.
- **Reuse the chair-stand-only readiness review.** Rejected because lower-body control does not
  establish readiness to load the shoulders, elbows, wrists, and hands.
- **Begin with maximal strength, aerobic, or jump testing.** Deferred because those paths require
  more equipment, supervision, familiarization, or impact readiness and do not shorten the safe path
  to a first usable measurement.

## Assumptions and unresolved questions

- The ACSM textbook source is authoritative for the exact protocol description it contains. The
  primary studies cited by the textbook have not yet been independently appraised for this release,
  so evidence strength remains low.
- A thin consistent chin target and the warm-up details are reproducibility-oriented AGAS operating
  choices, not verbatim ACSM instructions.
- Self-counting can miss invalid repetitions. Video-assisted or observer validation remains a later
  option and is not required for this low-confidence owner-alpha baseline.
- The 28-day interval is a conservative product choice. It is not claimed as a scientifically
  optimal reassessment frequency.
- A later governed floor or personal-calibration authority is still required before this estimate
  can affect training priorities or session construction.

## Consequences

- After assessment-reviewer ratification and a fresh readiness report, the athlete can select,
  perform, record, and derive a narrow standard-push-up estimate through the existing phone UI.
- Old owner-readiness records remain preserved but cannot authorize assessment selection under the
  expanded readiness meaning. Eligibility produced by a separate operator-reviewed process retains
  its own versioned authority.
- The repository gains practical measurement value without turning a descriptive norm into an
  exercise prescription.
- The next planning milestone can build an honest personal-calibration or professional-judgment
  bridge from this exact estimate to an owner-relevant competency decision.
