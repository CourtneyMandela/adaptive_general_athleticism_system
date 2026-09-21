import { type Confidence, type ProvenanceInput, isUuid } from "./current-week";
import { authorizedHeaders } from "./identity";

export type AssessmentWorkflowStatus =
  | "eligibility_required"
  | "eligibility_review_required"
  | "selection_blocked"
  | "eligibility_inactive"
  | "protocol_catalog_empty"
  | "environment_required"
  | "ready_to_start"
  | "selection_deferred"
  | "result_entry_ready"
  | "run_blocked"
  | "complete"
  | "reassessment_due"
  | "reassessment_not_due";

export type AssessmentResultStatus =
  | "completed"
  | "ready"
  | "not_selected"
  | "protocol_unavailable"
  | "eligibility_unavailable";

export type AssessmentCapabilityEstimateStatus =
  | "completed"
  | "ready"
  | "policy_unavailable"
  | "policy_superseded"
  | "stale";

export interface AssessmentDecisionProjection {
  selection_id: string;
  decision: "selected" | "deferred" | "excluded";
  reason_codes: string[];
  rationale: string[];
  assessment_definition_id: string;
  assessment_definition_review_id: string | null;
  name: string;
  domain: string;
  intensity: string;
  unit_or_scale: string;
  protocol_version: string;
  protocol_instructions: string[];
  result_entry_instructions: string;
  measurement_schema: AssessmentMeasurementSchema | null;
  applicability_notes: string;
  uncertainty: string;
  evidence_claim_ids: string[];
  review_version: string;
  result_status: AssessmentResultStatus;
  result: {
    performance_id: string;
    result_observation_id: string;
    performed_at: string;
    measurement: unknown;
    unit: string | null;
    reliability: Confidence;
    provenance: Record<string, unknown>;
    rule_version: string;
    next_reassessment_at: string;
    reassessment_interval_source_review_id: string;
    capability_estimate_status: AssessmentCapabilityEstimateStatus;
    capability_estimate: {
      estimate_id: string;
      estimate: unknown;
      unit_or_scale: string;
      estimate_scope: string;
      confidence: Confidence;
      calculation_method: string;
      source_observation_ids: string[];
      estimated_at: string;
      valid_until: string | null;
      rule_version: string;
      policy_id: string;
      policy_reviewed_at: string;
      policy_reviewed_by: string;
      applicability_notes: string;
      uncertainty: string;
      evidence_claim_ids: string[];
    } | null;
  } | null;
}

export interface AssessmentMeasurementSchema {
  measurement_type: "number" | "integer" | "category";
  label: string;
  minimum: number | null;
  maximum: number | null;
  step: number | null;
  allowed_values: string[];
  measurement_schema_version: string;
}

export interface AssessmentWorkflowProjection {
  athlete_id: string;
  athlete_display_name: string;
  as_of: string;
  status: AssessmentWorkflowStatus;
  message: string;
  can_start_run: boolean;
  can_record_results: boolean;
  approved_self_administered_protocol_count: number;
  due_protocol_count: number;
  next_reassessment_at: string | null;
  reassessment_rule_version: string;
  eligibility: {
    eligibility_review_id: string;
    outcome: "selection_allowed" | "selection_blocked" | "review_required";
    reviewed_at: string;
    valid_until: string;
    maximum_assessment_intensity: "low" | "moderate" | "high" | "maximal";
    rule_version: string;
  } | null;
  jump_exposure_need?: {
    exposure_need_id: string;
    exposure_type: "jumping";
    target_scope: string;
    status: "unknown" | "introductory_exposure_needed" | "recent_exposure_confirmed";
    lookback_days: number;
    minimum_exposure_days: number;
    source_observation_ids: string[];
    confidence: Confidence;
    rationale: string;
    uncertainty: string;
    authority_reference: string;
    identified_at: string;
    valid_until: string | null;
    active: boolean;
    rule_version: string;
  } | null;
  introductory_jump_dose?: {
    policy_id: string;
    exercise_id: string;
    exercise_name: string;
    sets: number;
    repetitions_per_set: number;
    total_contacts: number;
    rest_seconds: number;
    effort_rpe_minimum: number;
    effort_rpe_maximum: number;
    technique_constraints: string[];
    planned_duration_minutes: number;
    numeric_value_origin: "engineering_judgment" | "professional_judgment" | "scientific_evidence";
    authority_reference: string;
    uncertainty: string;
  } | null;
  introductory_jump_history?: {
    qualifying_days: number;
    required_days: number;
    last_execution_at: string | null;
    session_recorded_today: boolean;
  } | null;
  environments: Array<{ environment_id: string; name: string }>;
  latest_run: {
    run_id: string;
    environment_id: string;
    environment_name: string;
    evaluated_at: string;
    rule_version: string;
    decisions: AssessmentDecisionProjection[];
  } | null;
}

export type ReadinessAnswer = "no" | "yes" | "unsure";

export interface AssessmentReadinessInput {
  adultConfirmed: boolean;
  regularModerateActivityLastThreeMonths: ReadinessAnswer;
  knownCardiovascularMetabolicOrRenalDisease: ReadinessAnswer;
  concerningSignsOrSymptoms: ReadinessAnswer;
  clinicianExerciseRestriction: ReadinessAnswer;
  currentLowerBodyOrBalanceConcern: ReadinessAnswer;
  controlledChairStandWithoutArms: ReadinessAnswer;
  currentUpperBodyWristOrHandConcern: ReadinessAnswer;
  controlledStandardPushup: ReadinessAnswer;
  controlledTwoFootJumpAndLanding: ReadinessAnswer;
  recentTwoFootJumpAndLandingExposure28Days: ReadinessAnswer;
  answersConfirmed: boolean;
}

export interface AssessmentReadinessReportCommand {
  report_id: string;
  reported_at: string;
  adult_confirmed: boolean;
  regular_moderate_activity_last_three_months: ReadinessAnswer;
  known_cardiovascular_metabolic_or_renal_disease: ReadinessAnswer;
  concerning_signs_or_symptoms: ReadinessAnswer;
  clinician_exercise_restriction: ReadinessAnswer;
  current_lower_body_or_balance_concern: ReadinessAnswer;
  controlled_chair_stand_without_arms: ReadinessAnswer;
  current_upper_body_wrist_or_hand_concern: ReadinessAnswer;
  controlled_standard_pushup: ReadinessAnswer;
  controlled_two_foot_jump_and_landing: ReadinessAnswer;
  recent_two_foot_jump_and_landing_exposure_28_days: ReadinessAnswer;
  answers_confirmed: true;
}

export interface AssessmentReadinessReportResult {
  observation_id: string;
  eligibility_review_id: string;
  outcome: "selection_allowed" | "selection_blocked" | "review_required";
  maximum_assessment_intensity: "low" | "moderate" | "high" | "maximal";
  valid_until: string;
  next_action: string;
  jump_exposure_need_id: string;
  jump_exposure_status:
    | "unknown"
    | "introductory_exposure_needed"
    | "recent_exposure_confirmed";
  jump_exposure_next_action: string;
  created: boolean;
  rule_version: string;
}

export interface AssessmentRunInput {
  environmentId: string;
  bodyMassKg: number | null;
  trainingAgeMonthsByDomain: Record<string, number | null>;
  exerciseSkillTags: string[];
  recentExposureTags: string[];
  reliability: Confidence;
  evaluatedAt?: Date;
}

export interface AssessmentRunCommand {
  environment_id: string;
  body_mass_kg: number | null;
  training_age_months_by_domain: Record<string, number>;
  exercise_skill_tags: string[];
  recent_exposure_tags: string[];
  evaluated_at: string;
  reliability: Confidence;
  provenance: ProvenanceInput;
}

export interface AssessmentResultCommand {
  performed_at: string;
  measurement: number | string;
  unit: string;
  reliability: Confidence;
  provenance: ProvenanceInput;
}

export interface IntroductoryExposureExecutionInput {
  exposureNeedId: string;
  environmentId: string;
  startedAt: Date;
  endedAt: Date;
  actualSets: number;
  actualContacts: number;
  sessionRpe: number | null;
  preSessionReady: boolean;
  controlledLandings: boolean;
  stopConditionOccurred: boolean;
  answersConfirmed: boolean;
  reliability: Confidence;
}

export interface IntroductoryExposureExecutionCommand {
  execution_id: string;
  exposure_need_id: string;
  environment_id: string;
  started_at: string;
  ended_at: string;
  actual_sets: number;
  actual_contacts: number;
  session_rpe: number | null;
  pre_session_ready: boolean;
  controlled_landings: boolean;
  stop_condition_occurred: boolean;
  answers_confirmed: true;
  reliability: Confidence;
  provenance: ProvenanceInput;
}

export const assessmentProvenance: ProvenanceInput = {
  recorded_by: "unverified-athlete-user",
  source_system: "agas-web",
  ingestion_method: "assessment-context-form",
};

export const assessmentResultProvenance: ProvenanceInput = {
  recorded_by: "unverified-athlete-user",
  source_system: "agas-web",
  ingestion_method: "assessment-result-form",
};

export const introductoryExposureProvenance: ProvenanceInput = {
  recorded_by: "unverified-athlete-user",
  source_system: "agas-web",
  ingestion_method: "introductory-exposure-form",
};

export class AssessmentRequestError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "AssessmentRequestError";
  }
}

export function buildAssessmentReadinessReportCommand(
  input: AssessmentReadinessInput,
  reportedAt: Date = new Date(),
  reportId: string = crypto.randomUUID(),
): AssessmentReadinessReportCommand {
  if (!input.answersConfirmed) {
    throw new Error("Confirm that the readiness answers are current and accurate.");
  }
  if (!Number.isFinite(reportedAt.valueOf())) {
    throw new Error("The readiness report time is invalid.");
  }
  if (!isUuid(reportId)) {
    throw new Error("The readiness report identity is invalid.");
  }
  return {
    report_id: reportId,
    reported_at: reportedAt.toISOString(),
    adult_confirmed: input.adultConfirmed,
    regular_moderate_activity_last_three_months:
      input.regularModerateActivityLastThreeMonths,
    known_cardiovascular_metabolic_or_renal_disease:
      input.knownCardiovascularMetabolicOrRenalDisease,
    concerning_signs_or_symptoms: input.concerningSignsOrSymptoms,
    clinician_exercise_restriction: input.clinicianExerciseRestriction,
    current_lower_body_or_balance_concern: input.currentLowerBodyOrBalanceConcern,
    controlled_chair_stand_without_arms: input.controlledChairStandWithoutArms,
    current_upper_body_wrist_or_hand_concern: input.currentUpperBodyWristOrHandConcern,
    controlled_standard_pushup: input.controlledStandardPushup,
    controlled_two_foot_jump_and_landing: input.controlledTwoFootJumpAndLanding,
    recent_two_foot_jump_and_landing_exposure_28_days:
      input.recentTwoFootJumpAndLandingExposure28Days,
    answers_confirmed: true,
  };
}

function normalizedTags(values: string[], label: string): string[] {
  const normalized = values.map((value) => value.trim()).filter(Boolean);
  const keys = normalized.map((value) => value.toLocaleLowerCase());
  if (new Set(keys).size !== keys.length) {
    throw new Error(`${label} cannot contain duplicates.`);
  }
  return normalized;
}

export function buildAssessmentRunCommand(input: AssessmentRunInput): AssessmentRunCommand {
  if (!isUuid(input.environmentId)) {
    throw new Error("Choose a persisted assessment environment.");
  }
  if (input.bodyMassKg !== null && (!Number.isFinite(input.bodyMassKg) || input.bodyMassKg <= 0)) {
    throw new Error("Body mass must be greater than zero when reported.");
  }
  const trainingHistory = Object.fromEntries(
    Object.entries(input.trainingAgeMonthsByDomain)
      .filter((entry): entry is [string, number] => entry[1] !== null)
      .map(([domain, months]) => {
        if (!Number.isInteger(months) || months < 0) {
          throw new Error("Training history must use whole, non-negative months.");
        }
        return [domain, months];
      }),
  );
  const evaluatedAt = input.evaluatedAt ?? new Date();
  if (!Number.isFinite(evaluatedAt.valueOf())) {
    throw new Error("The assessment time is invalid.");
  }
  return {
    environment_id: input.environmentId,
    body_mass_kg: input.bodyMassKg,
    training_age_months_by_domain: trainingHistory,
    exercise_skill_tags: normalizedTags(input.exerciseSkillTags, "Skill tags"),
    recent_exposure_tags: normalizedTags(input.recentExposureTags, "Exposure tags"),
    evaluated_at: evaluatedAt.toISOString(),
    reliability: input.reliability,
    provenance: assessmentProvenance,
  };
}

export function buildAssessmentResultCommand(
  decision: AssessmentDecisionProjection,
  rawValue: string,
  reliability: Confidence,
  performedAt: Date = new Date(),
): AssessmentResultCommand {
  const schema = decision.measurement_schema;
  if (!schema) {
    throw new Error("This protocol has no reviewed measurement schema.");
  }
  if (!Number.isFinite(performedAt.valueOf())) {
    throw new Error("The performance time is invalid.");
  }
  let measurement: number | string;
  if (schema.measurement_type === "category") {
    if (!schema.allowed_values.includes(rawValue)) {
      throw new Error("Choose an allowed result.");
    }
    measurement = rawValue;
  } else {
    measurement = Number(rawValue);
    if (!rawValue.trim() || !Number.isFinite(measurement)) {
      throw new Error("Enter a numeric result.");
    }
    if (schema.measurement_type === "integer" && !Number.isInteger(measurement)) {
      throw new Error("Enter a whole-number result.");
    }
    if (schema.minimum !== null && measurement < schema.minimum) {
      throw new Error(`Result must be at least ${schema.minimum}.`);
    }
    if (schema.maximum !== null && measurement > schema.maximum) {
      throw new Error(`Result must be at most ${schema.maximum}.`);
    }
    if (schema.step !== null) {
      const steps = (measurement - (schema.minimum ?? 0)) / schema.step;
      if (Math.abs(steps - Math.round(steps)) > 1e-9) {
        throw new Error(`Result must use increments of ${schema.step}.`);
      }
    }
  }
  return {
    performed_at: performedAt.toISOString(),
    measurement,
    unit: decision.unit_or_scale,
    reliability,
    provenance: assessmentResultProvenance,
  };
}

export function buildIntroductoryExposureExecutionCommand(
  input: IntroductoryExposureExecutionInput,
  executionId: string = crypto.randomUUID(),
): IntroductoryExposureExecutionCommand {
  if (!isUuid(executionId) || !isUuid(input.exposureNeedId) || !isUuid(input.environmentId)) {
    throw new Error("The exposure record, need, or environment identity is invalid.");
  }
  if (!input.answersConfirmed) {
    throw new Error("Confirm that the exposure record is accurate.");
  }
  if (!Number.isFinite(input.startedAt.valueOf()) || !Number.isFinite(input.endedAt.valueOf())) {
    throw new Error("The exposure session time is invalid.");
  }
  if (input.endedAt < input.startedAt) {
    throw new Error("The exposure cannot end before it starts.");
  }
  if (!Number.isInteger(input.actualSets) || input.actualSets < 0) {
    throw new Error("Actual sets must be a whole, non-negative number.");
  }
  if (!Number.isInteger(input.actualContacts) || input.actualContacts < 0) {
    throw new Error("Actual contacts must be a whole, non-negative number.");
  }
  if (
    input.sessionRpe !== null &&
    (!Number.isFinite(input.sessionRpe) || input.sessionRpe < 0 || input.sessionRpe > 10)
  ) {
    throw new Error("Session RPE must be between 0 and 10.");
  }
  if (!input.controlledLandings && !input.stopConditionOccurred) {
    throw new Error("An uncontrolled landing must be recorded as a stop condition.");
  }
  return {
    execution_id: executionId,
    exposure_need_id: input.exposureNeedId,
    environment_id: input.environmentId,
    started_at: input.startedAt.toISOString(),
    ended_at: input.endedAt.toISOString(),
    actual_sets: input.actualSets,
    actual_contacts: input.actualContacts,
    session_rpe: input.sessionRpe,
    pre_session_ready: input.preSessionReady,
    controlled_landings: input.controlledLandings,
    stop_condition_occurred: input.stopConditionOccurred,
    answers_confirmed: true,
    reliability: input.reliability,
    provenance: introductoryExposureProvenance,
  };
}

async function responseDetail(response: Response, fallback: string): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    return typeof body.detail === "string" ? body.detail : fallback;
  } catch {
    return fallback;
  }
}

export async function submitAssessmentReadinessReport(
  apiBaseUrl: string,
  athleteId: string,
  command: AssessmentReadinessReportCommand,
  fetcher: typeof fetch = fetch,
): Promise<AssessmentReadinessReportResult> {
  const response = await fetcher(
    `${apiBaseUrl.replace(/\/$/, "")}/v1/athletes/${athleteId}/assessment-readiness-reports`,
    {
      method: "POST",
      headers: authorizedHeaders({
        Accept: "application/json",
        "Content-Type": "application/json",
      }),
      body: JSON.stringify(command),
    },
  );
  if (!response.ok) {
    throw new AssessmentRequestError(
      await responseDetail(response, "Unable to save the readiness report."),
      response.status,
    );
  }
  return response.json() as Promise<AssessmentReadinessReportResult>;
}

export async function fetchAssessmentWorkflow(
  apiBaseUrl: string,
  athleteId: string,
  fetcher: typeof fetch = fetch,
): Promise<AssessmentWorkflowProjection> {
  const response = await fetcher(
    `${apiBaseUrl.replace(/\/$/, "")}/v1/athletes/${athleteId}/assessment-workflow`,
    { headers: authorizedHeaders({ Accept: "application/json" }) },
  );
  if (!response.ok) {
    throw new AssessmentRequestError(
      await responseDetail(response, "Unable to load assessment status."),
      response.status,
    );
  }
  return (await response.json()) as AssessmentWorkflowProjection;
}

export async function submitAssessmentRun(
  apiBaseUrl: string,
  athleteId: string,
  command: AssessmentRunCommand,
  fetcher: typeof fetch = fetch,
): Promise<unknown> {
  const response = await fetcher(
    `${apiBaseUrl.replace(/\/$/, "")}/v1/athletes/${athleteId}/assessment-runs`,
    {
      method: "POST",
      headers: authorizedHeaders({
        Accept: "application/json",
        "Content-Type": "application/json",
      }),
      body: JSON.stringify(command),
    },
  );
  if (!response.ok) {
    throw new AssessmentRequestError(
      await responseDetail(response, "Unable to create assessment selection."),
      response.status,
    );
  }
  return response.json();
}

export async function submitIntroductoryExposureExecution(
  apiBaseUrl: string,
  athleteId: string,
  command: IntroductoryExposureExecutionCommand,
  fetcher: typeof fetch = fetch,
): Promise<unknown> {
  const response = await fetcher(
    `${apiBaseUrl.replace(/\/$/, "")}/v1/athletes/${athleteId}/introductory-exposure-executions`,
    {
      method: "POST",
      headers: authorizedHeaders({
        Accept: "application/json",
        "Content-Type": "application/json",
      }),
      body: JSON.stringify(command),
    },
  );
  if (!response.ok) {
    throw new AssessmentRequestError(
      await responseDetail(response, "Unable to record the introductory exposure."),
      response.status,
    );
  }
  return response.json();
}

export async function submitAssessmentResult(
  apiBaseUrl: string,
  athleteId: string,
  runId: string,
  selectionId: string,
  command: AssessmentResultCommand,
  fetcher: typeof fetch = fetch,
): Promise<unknown> {
  const response = await fetcher(
    `${apiBaseUrl.replace(/\/$/, "")}/v1/athletes/${athleteId}/assessment-runs/${runId}` +
      `/selections/${selectionId}/result`,
    {
      method: "POST",
      headers: authorizedHeaders({
        Accept: "application/json",
        "Content-Type": "application/json",
      }),
      body: JSON.stringify(command),
    },
  );
  if (!response.ok) {
    throw new AssessmentRequestError(
      await responseDetail(response, "Unable to record the assessment result."),
      response.status,
    );
  }
  return response.json();
}

export async function submitAssessmentCapabilityEstimate(
  apiBaseUrl: string,
  athleteId: string,
  performanceId: string,
  fetcher: typeof fetch = fetch,
): Promise<unknown> {
  const response = await fetcher(
    `${apiBaseUrl.replace(/\/$/, "")}/v1/athletes/${athleteId}` +
      `/assessment-performances/${performanceId}/capability-estimate`,
    {
      method: "POST",
      headers: authorizedHeaders({ Accept: "application/json" }),
    },
  );
  if (!response.ok) {
    throw new AssessmentRequestError(
      await responseDetail(response, "Unable to create the capability estimate."),
      response.status,
    );
  }
  return response.json();
}
