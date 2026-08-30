import { authorizedHeaders, reviewerDevelopmentAccessToken } from "./identity";

const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export type CostLevel = "low" | "moderate" | "high";
export type SessionSection = "preparation" | "primary" | "accessory" | "conditioning" | "cooldown" | "other";
export type IntensityTarget =
  | { kind: "absolute_load"; value: number; unit: string }
  | { kind: "relative_load"; percentage: number; reference: string }
  | { kind: "bodyweight" }
  | { kind: "effort_rpe"; minimum: number; maximum: number }
  | { kind: "repetitions_in_reserve"; minimum: number; maximum: number }
  | { kind: "heart_rate_zone"; zone: number }
  | { kind: "pace"; value: number; unit: string }
  | { kind: "technique"; constraints: string[] };

export interface FirstWeekPreparationProjection {
  block: { id: string; status: "full" | "partial" | "infeasible"; starts_on: string; ends_on: string; duration_weeks: number; weekly_budget_minutes: number; hypothesis: string; constraints: string[]; generated_at: string; rule_version: string };
  projected_at: string;
  allocation_inputs: Array<{
    allocation: { id: string; priority_state: string; allocated_weekly_minutes: number; sessions_per_week: number; status: string; issues: Array<{ code: string; detail: string }> };
    resource_demand: { id: string; rationale: string; demand_version: string };
    adaptation: { id: string; name: string; domain: string };
    stimulus_requirement: { id: string; rationale: string; rule_version: string } | null;
    exercise_resolution: { id: string; environment_id: string; status: string; rationale: string; unresolved_issues: Array<{ code: string; detail: string }> } | null;
    selected_exercise: { id: string; name: string; fatigue_cost: string } | null;
  }>;
  environments: Array<{ id: string; name: string; outdoor_access: boolean; max_noise_level: string; space_constraints: Record<string, unknown> }>;
  scheduling_policy_options: Array<{
    policy: { id: string; policy_version: string; minimum_high_fatigue_recovery_hours: number; maximum_sessions_per_day: number; maximum_high_fatigue_sessions_per_day: number; allow_partial_exercise_resolution: boolean };
    current_review: null | { id: string; decision: string; reviewed_at: string; reviewed_by: string; applicability_rationale: string; uncertainty: string; review_version: string; evidence_claim_ids: string[] };
  }>;
  existing_first_week_plans: Array<{ id: string; status: string; week_start: string; sessions: unknown[]; issues: unknown[] }>;
  source_observations: Array<{ id: string; observation_type: string; measurement: unknown; unit: string | null; timestamp: string; reliability: string }>;
  evidence_claims: Array<{ id: string; claim: string; evidence_strength: string; athlete_applicability: string; claim_version: string }>;
  projection_version: string;
}

export interface SessionPrescriptionDraft {
  resource_allocation_id: string;
  reason_for_inclusion: string;
  sets: number;
  repetitions_per_set?: number;
  duration_seconds?: number;
  intensity_targets: IntensityTarget[];
  rest_seconds: number;
  progression_rule_reference: string;
  substitution_class: string;
  planned_duration_minutes: number;
  fatigue_cost: CostLevel;
  source_observation_ids: string[];
  evidence_claim_ids: string[];
  rule_version: string;
}

export interface SessionTemplateDraft {
  name: string;
  items: Array<{ resource_allocation_id: string; order_index: number; section: SessionSection }>;
  sessions_per_week: number;
  planned_duration_minutes: number;
  fatigue_cost: CostLevel;
  source_observation_ids: string[];
  evidence_claim_ids: string[];
  rule_version: string;
}

export interface OperatorWeeklyPlanRequest {
  prescriptions: SessionPrescriptionDraft[];
  session_templates: SessionTemplateDraft[];
  availability: {
    week_start: string;
    windows: Array<{ environment_id: string; starts_at: string; ends_at: string }>;
    source_observation_ids: string[];
    rule_version: string;
  };
  scheduling_policy_id: string;
  scheduling_policy_review_id: string;
  prepared_at: string;
  applicability_rationale: string;
  uncertainty: string;
}

export interface WeeklyPlanCreationResult {
  prescriptions: Array<{ id: string; exercise_id: string; adaptation_id: string }>;
  session_templates: Array<{ id: string; name: string }>;
  availability: { id: string; week_start: string };
  weekly_plan: { id: string; status: string; sessions: Array<{ id: string; starts_at: string; ends_at: string }>; issues: Array<{ code: string; detail: string }> };
  decision_record: { id: string; decision: string; evidence: string[] };
}

export class FirstWeekReviewError extends Error {
  constructor(message: string, readonly status?: number) {
    super(message);
    this.name = "FirstWeekReviewError";
  }
}

function normalizedBaseUrl(value: string): string { return value.replace(/\/$/, ""); }
function assertUuid(value: string, label: string): void {
  if (!uuidPattern.test(value)) throw new FirstWeekReviewError(`${label} must be a UUID.`);
}
function assertNonBlank(value: string, label: string): void {
  if (!value.trim()) throw new FirstWeekReviewError(`${label} must not be blank.`);
}
function assertPositiveInteger(value: number, label: string): void {
  if (!Number.isInteger(value) || value <= 0) throw new FirstWeekReviewError(`${label} must be a positive integer.`);
}
function assertIds(values: string[], label: string): void {
  if (!values.length) throw new FirstWeekReviewError(`${label} must not be empty.`);
  values.forEach((value, index) => assertUuid(value, `${label} ${index + 1}`));
  if (new Set(values).size !== values.length) throw new FirstWeekReviewError(`${label} must not contain duplicates.`);
}
function assertTimestamp(value: string, label: string): void {
  if (!/(Z|[+-]\d{2}:\d{2})$/.test(value) || Number.isNaN(Date.parse(value))) {
    throw new FirstWeekReviewError(`${label} must be a valid timestamp with a timezone.`);
  }
}
function validateIntensity(target: IntensityTarget, label: string): void {
  if (target.kind === "absolute_load" || target.kind === "pace") {
    if (!(target.value > 0)) throw new FirstWeekReviewError(`${label} value must be positive.`);
    assertNonBlank(target.unit, `${label} unit`);
  } else if (target.kind === "relative_load") {
    if (!(target.percentage > 0 && target.percentage <= 200)) throw new FirstWeekReviewError(`${label} percentage must be between 0 and 200.`);
    assertNonBlank(target.reference, `${label} reference`);
  } else if (target.kind === "effort_rpe" || target.kind === "repetitions_in_reserve") {
    if (!Number.isFinite(target.minimum) || !Number.isFinite(target.maximum) || target.minimum < 0 || target.maximum > 10 || target.maximum < target.minimum) throw new FirstWeekReviewError(`${label} range must be ordered between 0 and 10.`);
  } else if (target.kind === "heart_rate_zone") {
    if (!Number.isInteger(target.zone) || target.zone < 1 || target.zone > 5) throw new FirstWeekReviewError(`${label} zone must be an integer from 1 to 5.`);
  } else if (target.kind === "technique" && (!target.constraints.length || target.constraints.some((item) => !item.trim()))) {
    throw new FirstWeekReviewError(`${label} requires non-blank constraints.`);
  }
}

async function responseError(response: Response): Promise<FirstWeekReviewError> {
  let message = `Request failed with status ${response.status}.`;
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string" && body.detail.trim()) message = body.detail;
  } catch { /* Keep the status-based error for non-JSON failures. */ }
  return new FirstWeekReviewError(message, response.status);
}

export function validateWeeklyPlanRequest(request: OperatorWeeklyPlanRequest): void {
  const unsafe = request as unknown as Record<string, unknown>;
  for (const field of ["reviewed_by", "review_authority_assignment_id"]) {
    if (field in unsafe) throw new FirstWeekReviewError(`${field} is server-owned.`);
  }
  if (!request.prescriptions.length) throw new FirstWeekReviewError("Prescriptions are required.");
  const allocationIds = request.prescriptions.map((item) => item.resource_allocation_id);
  allocationIds.forEach((id, index) => assertUuid(id, `Prescription allocation ${index + 1}`));
  if (new Set(allocationIds).size !== allocationIds.length) throw new FirstWeekReviewError("Prescription allocations must not contain duplicates.");
  request.prescriptions.forEach((item, index) => {
    const label = `Prescription ${index + 1}`;
    assertNonBlank(item.reason_for_inclusion, `${label} reason`);
    assertPositiveInteger(item.sets, `${label} sets`);
    if ((item.repetitions_per_set === undefined) === (item.duration_seconds === undefined)) throw new FirstWeekReviewError(`${label} requires exactly one of repetitions or duration.`);
    if (item.repetitions_per_set !== undefined) assertPositiveInteger(item.repetitions_per_set, `${label} repetitions`);
    if (item.duration_seconds !== undefined) assertPositiveInteger(item.duration_seconds, `${label} duration`);
    if (!item.intensity_targets.length) throw new FirstWeekReviewError(`${label} requires at least one intensity target.`);
    const kinds = item.intensity_targets.map((target) => target.kind);
    if (new Set(kinds).size !== kinds.length) throw new FirstWeekReviewError(`${label} intensity kinds must not contain duplicates.`);
    if (["absolute_load", "relative_load", "bodyweight"].filter((kind) => kinds.includes(kind as IntensityTarget["kind"])).length > 1) throw new FirstWeekReviewError(`${label} may contain only one load target.`);
    item.intensity_targets.forEach((target, targetIndex) => validateIntensity(target, `${label} intensity ${targetIndex + 1}`));
    if (!Number.isInteger(item.rest_seconds) || item.rest_seconds < 0) throw new FirstWeekReviewError(`${label} rest must be a non-negative integer.`);
    assertNonBlank(item.progression_rule_reference, `${label} progression rule`);
    assertNonBlank(item.substitution_class, `${label} substitution class`);
    assertPositiveInteger(item.planned_duration_minutes, `${label} planned duration`);
    if (!["low", "moderate", "high"].includes(item.fatigue_cost)) throw new FirstWeekReviewError(`${label} fatigue cost is invalid.`);
    assertIds(item.source_observation_ids, `${label} observations`);
    assertIds(item.evidence_claim_ids, `${label} evidence claims`);
    assertNonBlank(item.rule_version, `${label} rule version`);
  });
  if (!request.session_templates.length) throw new FirstWeekReviewError("Session composition is required.");
  request.session_templates.forEach((template, index) => {
    const label = `Session template ${index + 1}`;
    assertNonBlank(template.name, `${label} name`);
    if (!template.items.length) throw new FirstWeekReviewError(`${label} requires items.`);
    const ids = template.items.map((item) => item.resource_allocation_id);
    if (new Set(ids).size !== ids.length) throw new FirstWeekReviewError(`${label} allocations must not contain duplicates.`);
    template.items.forEach((item, itemIndex) => {
      assertUuid(item.resource_allocation_id, `${label} allocation ${itemIndex + 1}`);
      if (item.order_index !== itemIndex + 1) throw new FirstWeekReviewError(`${label} item order must be contiguous from one.`);
      if (!["preparation", "primary", "accessory", "conditioning", "cooldown", "other"].includes(item.section)) throw new FirstWeekReviewError(`${label} item section is invalid.`);
    });
    assertPositiveInteger(template.sessions_per_week, `${label} frequency`);
    assertPositiveInteger(template.planned_duration_minutes, `${label} planned duration`);
    if (!["low", "moderate", "high"].includes(template.fatigue_cost)) throw new FirstWeekReviewError(`${label} fatigue cost is invalid.`);
    assertIds(template.source_observation_ids, `${label} observations`);
    assertIds(template.evidence_claim_ids, `${label} evidence claims`);
    assertNonBlank(template.rule_version, `${label} rule version`);
  });
  if (!/^\d{4}-\d{2}-\d{2}$/.test(request.availability.week_start)) throw new FirstWeekReviewError("Availability week start must use YYYY-MM-DD.");
  request.availability.windows.forEach((window, index) => {
    assertUuid(window.environment_id, `Availability window ${index + 1} environment`);
    assertTimestamp(window.starts_at, `Availability window ${index + 1} start`);
    assertTimestamp(window.ends_at, `Availability window ${index + 1} end`);
    if (Date.parse(window.ends_at) <= Date.parse(window.starts_at)) throw new FirstWeekReviewError(`Availability window ${index + 1} must have positive duration.`);
  });
  assertIds(request.availability.source_observation_ids, "Availability observations");
  assertNonBlank(request.availability.rule_version, "Availability rule version");
  assertUuid(request.scheduling_policy_id, "Scheduling policy");
  assertUuid(request.scheduling_policy_review_id, "Scheduling policy review");
  assertTimestamp(request.prepared_at, "prepared_at");
  assertNonBlank(request.applicability_rationale, "Applicability rationale");
  assertNonBlank(request.uncertainty, "Uncertainty");
}

export async function fetchFirstWeekPreparation(apiBaseUrl: string, blockId: string, fetcher: typeof fetch = fetch): Promise<FirstWeekPreparationProjection> {
  assertUuid(blockId, "Block ID");
  const response = await fetcher(`${normalizedBaseUrl(apiBaseUrl)}/v1/operator/blocks/${blockId}/first-week-preparation`, {
    headers: authorizedHeaders({ Accept: "application/json" }, reviewerDevelopmentAccessToken),
  });
  if (!response.ok) throw await responseError(response);
  return (await response.json()) as FirstWeekPreparationProjection;
}

export async function submitFirstWeekPlan(apiBaseUrl: string, blockId: string, request: OperatorWeeklyPlanRequest, fetcher: typeof fetch = fetch): Promise<WeeklyPlanCreationResult> {
  assertUuid(blockId, "Block ID");
  validateWeeklyPlanRequest(request);
  const response = await fetcher(`${normalizedBaseUrl(apiBaseUrl)}/v1/operator/blocks/${blockId}/first-week-plans`, {
    method: "POST",
    headers: authorizedHeaders({ Accept: "application/json", "Content-Type": "application/json" }, reviewerDevelopmentAccessToken),
    body: JSON.stringify(request),
  });
  if (!response.ok) throw await responseError(response);
  return (await response.json()) as WeeklyPlanCreationResult;
}
