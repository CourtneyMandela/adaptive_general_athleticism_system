# 0091 — Current assessment-readiness screen

Date: 2026-09-08

Status: accepted for the single-owner alpha

Rule version: `assessment-readiness-screen@1.0.0`

## Decision

Replace the unusable “operator eligibility required” dead end with an authenticated, factual,
current-state readiness report and a deterministic decision rule. The athlete supplies facts but
cannot choose an outcome, validity window, reviewer, rationale, or authorized intensity. The API
stores the report as an `Observation` and the derived `AssessmentEligibilityReview` in one
transaction.

The rule allows selection only when the athlete confirms adult status, reports no known relevant
diagnosis, listed concerning sign/symptom, clinician restriction, or current lower-body/balance
concern, and confirms one comfortable controlled chair stand without arm assistance. “Yes” or
“unsure” on a safety-relevant factor requires further qualified review. Non-adult status blocks
this owner-alpha path. Current exercise participation is retained as context and is not converted
to a risk or fitness score.

An allowed decision expires after 24 hours and authorizes only evidence-ready self-administered
assessments at low or moderate intensity. The maximum intensity is persisted on the eligibility
record and enforced again during workflow projection and selection; it is not inferred from the
current catalog.

## Scientific and operational basis

- Riebe et al. (2015), PMID 26473759, describes the evidence-informed ACSM preparticipation model
  using current physical activity, signs/symptoms or known cardiovascular, metabolic, or renal
  disease, and desired exercise intensity.
- Whitfield et al. (2017), PMID 28557860, reports that the revised algorithm reduced referrals
  relative to older questionnaires while explicitly noting that further validation is needed.
- AGAS intentionally uses a more conservative alpha simplification: any reported/uncertain known
  disease or listed symptom stops self-service instead of attempting the full ACSM branching logic.
- The chair-specific movement question is an operational prerequisite for the first prepared test,
  not a validated medical screen.

The PMIDs and exact rule version are stored with each observation. They are method provenance, not
a claim that the app performed a professional examination or faithfully reproduced the complete
ACSM algorithm. A later governed screening-policy release should promote these sources into the
full `EvidenceClaim` review chain before this mechanism expands beyond the owner alpha.

## Data minimization

The form asks grouped yes/no/unsure questions. It does not ask for diagnoses, medications,
treatment details, symptom narratives, or clinician names. The user is told before submission that
the grouped answers become private assessment history. The ordinary assessment-selection request
still cannot submit health or symptom fields.

## Alternatives considered

- **Keep the local operator CLI as the only path.** Rejected because it leaves the hosted phone app
  unusable and makes the owner manually author rationale and policy.
- **Let the athlete choose “I am cleared.”** Rejected because it collapses factual reporting and
  authorization into self-approval.
- **Implement the full ACSM algorithm.** Deferred because the app cannot evaluate disease stability,
  medical clearance, or clinical significance and should not imitate professional judgment.
- **Collect a detailed medical history.** Rejected for this milestone because it increases privacy
  and interpretation risk without providing clinical review.
- **Make eligibility unlimited or authorize maximal tests.** Rejected because current state changes
  and the first self-administered protocol is moderate.

## Assumptions and limitations

- The user is capable of answering factual questions and will choose “unsure” rather than guess.
- A 24-hour window is a conservative product boundary, not a scientifically validated duration.
- The screen does not detect undisclosed, unknown, silent, or misinterpreted conditions.
- The app cannot assess urgency. User-facing copy directs perceived emergencies to local emergency
  services and otherwise stops the assessment when a relevant concern is present or uncertain.
- This does not authorize workouts, diagnose health, constitute medical clearance, or remove the
  protocol/equipment gates.

## Consequences

- A hosted owner can move from protocol approval to a narrowly governed first assessment without a
  developer-authored database command.
- Every decision retains its source observation, algorithm version, literature identifiers,
  validity window, intensity ceiling, rationale, uncertainty, and predecessor.
- New reports append and supersede; replay is idempotent and cannot rewrite historical answers.
