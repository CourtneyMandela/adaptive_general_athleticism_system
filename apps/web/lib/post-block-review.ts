import { authorizedHeaders, reviewerDevelopmentAccessToken } from "./identity";

const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export type ComparisonDirection = "higher_is_better" | "lower_is_better";

export interface ReviewObservation {
  id: string;
  observation_type: string;
  measurement: unknown;
  unit: string | null;
  timestamp: string;
  reliability: string;
}

export interface ReviewEvidenceClaim {
  id: string;
  claim: string;
  population: string;
  study_design: string;
  evidence_strength: string;
  athlete_applicability: string;
  uncertainty: string;
  claim_version: string;
}

export interface ReviewEstimate {
  id: string;
  domain: string;
  estimate: unknown;
  unit_or_scale: string;
  estimate_scope: string;
  confidence: string;
  calculation_method: string;
  source_observation_ids: string[];
  estimated_at: string;
  valid_until: string | null;
  rule_version: string;
}

export interface ReviewPrescription {
  id: string;
  adaptation_id: string;
  exercise_id: string;
  reason_for_inclusion: string;
  sets: number;
  repetitions_per_set: number | null;
  duration_seconds: number | null;
  planned_duration_minutes: number;
  fatigue_cost: string;
  rule_version: string;
}

export interface BlockReviewPreparationProjection {
  block: {
    id: string;
    athlete_id: string;
    long_range_strategy_id: string;
    starts_on: string;
    ends_on: string;
    duration_weeks: number;
    hypothesis: string;
    status: string;
    rule_version: string;
  };
  strategy: { id: string; block_hypothesis: string; rule_version: string };
  projected_at: string;
  status: "incomplete_history" | "ready_for_explicit_review" | "already_reviewed";
  issues: string[];
  weekly_plans: Array<{ id: string; block_week: number; week_start: string; status: string }>;
  session_history: Array<{
    weekly_plan_id: string;
    planned_session: { id: string; starts_at: string; ends_at: string };
    session_template: { id: string; name: string };
    prescriptions: ReviewPrescription[];
    execution: { id: string; status: string } | null;
    adherences: Array<{ id: string; prescription_id: string; adherence_ratio: number }>;
    post_session_safety_decisions: Array<{ id: string; outcome: string }>;
  }>;
  prescriptions: ReviewPrescription[];
  baseline_estimates: ReviewEstimate[];
  followup_estimates: ReviewEstimate[];
  block_review_policies: Array<{
    id: string;
    minimum_adherence_ratio: number;
    minimum_response_confidence: string;
    evidence_claim_ids: string[];
    rationale: string;
    policy_version: string;
  }>;
  existing_review: BlockReviewRecord | null;
  source_observations: ReviewObservation[];
  evidence_claims: ReviewEvidenceClaim[];
  projection_version: string;
}

export interface TrainingResponseDraft {
  adaptation_id: string;
  prescription_ids: string[];
  baseline_capability_estimate_id: string;
  followup_capability_estimate_id: string;
  intervention_summary: string;
  measurement_uncertainty: string;
  contextual_factors: string[];
  comparison_direction: ComparisonDirection;
  minimum_meaningful_change: number;
}

export interface OperatorBlockReviewRequest {
  block_review_policy_id: string;
  response_drafts: TrainingResponseDraft[];
  responses_calculated_at: string;
  reviewed_at: string;
  applicability_rationale: string;
  uncertainty: string;
}

export interface TrainingResponseRecord {
  id: string;
  adaptation_id: string;
  prescription_ids: string[];
  prescribed_item_count: number;
  completed_item_count: number;
  prescribed_dose_total: number;
  actual_dose_total: number;
  dose_unit: string;
  adherence_ratio: number;
  baseline_capability_estimate_id: string;
  followup_capability_estimate_id: string;
  baseline_value: number;
  followup_value: number;
  observed_change: number;
  confidence: string;
  calculation_method: string;
  rule_version: string;
}

export interface BlockReviewRecord {
  id: string;
  block_plan_id: string;
  outcome: string;
  aggregate_adherence_ratio: number;
  prescribed_item_count: number;
  completed_item_count: number;
  response_evaluations: Array<{
    training_response_id: string;
    comparison_direction: ComparisonDirection;
    minimum_meaningful_change: number;
    threshold_met: boolean | null;
    rationale: string;
  }>;
  rationale: string[];
  reviewed_at: string;
  rule_version: string;
}

export interface BlockReviewCreationResult {
  training_responses: TrainingResponseRecord[];
  block_review: BlockReviewRecord;
  decision_record: {
    id: string;
    decision: string;
    reason: string;
    evidence: string[];
    uncertainty: string;
    decision_version: string;
  };
}

export interface PostBlockReviewQueueItem {
  workflow_stage: "block_review" | "replanning";
  status:
    | "incomplete_history"
    | "ready_for_explicit_review"
    | "blocked"
    | "ready_for_explicit_replanning";
  athlete_id: string;
  athlete_display_name: string;
  block_id: string;
  block_review_id: string | null;
  block_starts_on: string;
  block_ends_on: string;
  block_hypothesis: string;
  reviewed_at: string | null;
  review_outcome: string | null;
  issues: string[];
}

export interface PostBlockReviewQueueProjection {
  projected_at: string;
  items: PostBlockReviewQueueItem[];
  projection_version: string;
}

export interface ReplanningCandidateContext {
  adaptation_id: string;
  competency_floor_id: string;
  capability_estimate_id: string;
  general_relevance: number;
  goal_relevance: number;
  prerequisite_value: number;
  expected_trainability: number;
  transfer_value: number;
  fatigue_cost: number;
  time_cost: number;
  interference_cost: number;
  safe_to_train: boolean;
  introductory_exposure_needed: boolean;
  prerequisites_met: boolean;
  prerequisite_adaptation_ids: string[];
  cultivate_comparative_advantage: boolean;
  source_observation_ids: string[];
  evidence_claim_ids: string[];
}

export interface ReplanningPreparationProjection {
  block_review: BlockReviewRecord;
  completed_block: BlockReviewPreparationProjection["block"];
  previous_strategy: {
    id: string;
    horizon_months: number;
    priorities: Array<{
      id: string;
      adaptation_id: string;
      state: string;
      rank: number;
      score: number;
      development_allocation: number;
    }>;
    rule_version: string;
  };
  priority_policy: { id: string; policy_version: string };
  projected_at: string;
  status: "blocked" | "ready_for_explicit_replanning" | "already_replanned";
  issues: string[];
  training_responses: TrainingResponseRecord[];
  adaptation_options: Array<{
    previous_priority: ReplanningPreparationProjection["previous_strategy"]["priorities"][number];
    adaptation: { id: string; name: string; domain: string };
    training_response: TrainingResponseRecord | null;
    requires_reviewed_followup: boolean;
    estimate_options: ReviewEstimate[];
    compatible_competency_floors: Array<{
      id: string;
      domain: string;
      estimate_scope: string;
      unit_or_scale: string;
      threshold: number;
      comparison_direction: ComparisonDirection;
      population: string;
      applicability_notes: string;
      uncertainty: string;
      evidence_claim_ids: string[];
      floor_version: string;
    }>;
  }>;
  existing_successor_strategy: PostBlockReplanningResult["strategy"] | null;
  source_observations: ReviewObservation[];
  evidence_claims: ReviewEvidenceClaim[];
  projection_version: string;
}

export interface OperatorReplanningRequest {
  candidate_contexts: ReplanningCandidateContext[];
  generated_at: string;
  review_after_days: number;
  applicability_rationale: string;
  uncertainty: string;
}

export interface PostBlockReplanningResult {
  capability_needs: Array<{ id: string; adaptation_id?: string; status: string }>;
  strategy: {
    id: string;
    supersedes_strategy_id: string;
    triggering_block_review_id: string;
    next_review_at: string;
    priorities: Array<{
      id: string;
      adaptation_id: string;
      state: string;
      rank: number;
      score: number;
      development_allocation: number;
    }>;
    rule_version: string;
  };
  decision_record: {
    id: string;
    decision: string;
    reason: string;
    evidence: string[];
    uncertainty: string;
    decision_version: string;
  };
}

export class PostBlockReviewError extends Error {
  constructor(message: string, readonly status?: number) {
    super(message);
    this.name = "PostBlockReviewError";
  }
}

export function isUuid(value: string): boolean {
  return uuidPattern.test(value);
}

function assertUuid(value: string, label: string): void {
  if (!isUuid(value)) throw new PostBlockReviewError(`${label} must be a UUID.`);
}

function assertNonBlank(value: string, label: string): void {
  if (!value.trim()) throw new PostBlockReviewError(`${label} must not be blank.`);
}

function assertTimestamp(value: string, label: string): void {
  if (!/(Z|[+-]\d{2}:\d{2})$/.test(value) || Number.isNaN(Date.parse(value))) {
    throw new PostBlockReviewError(`${label} must be a valid timestamp with a timezone.`);
  }
}

function assertUniqueIds(values: string[], label: string, allowEmpty = false): void {
  if (!allowEmpty && !values.length) throw new PostBlockReviewError(`${label} must not be empty.`);
  values.forEach((value, index) => assertUuid(value, `${label} ${index + 1}`));
  if (new Set(values).size !== values.length) {
    throw new PostBlockReviewError(`${label} must not contain duplicates.`);
  }
}

function assertUnitInterval(value: number, label: string): void {
  if (!Number.isFinite(value) || value < 0 || value > 1) {
    throw new PostBlockReviewError(`${label} must be between zero and one.`);
  }
}

function rejectServerOwnedFields(request: object): void {
  const unsafe = request as Record<string, unknown>;
  for (const field of ["reviewed_by", "review_authority_assignment_id"]) {
    if (field in unsafe) throw new PostBlockReviewError(`${field} is server-owned.`);
  }
}

async function responseError(response: Response): Promise<PostBlockReviewError> {
  let message = `Request failed with status ${response.status}.`;
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string" && body.detail.trim()) message = body.detail;
  } catch {
    // Preserve the status-based message for non-JSON failures.
  }
  return new PostBlockReviewError(message, response.status);
}

function normalizedBaseUrl(value: string): string {
  return value.replace(/\/$/, "");
}

export function validateBlockReviewRequest(request: OperatorBlockReviewRequest): void {
  rejectServerOwnedFields(request);
  assertUuid(request.block_review_policy_id, "Block-review policy");
  if (!request.response_drafts.length) {
    throw new PostBlockReviewError("At least one response interpretation is required.");
  }
  const assignedPrescriptionIds: string[] = [];
  const adaptationIds: string[] = [];
  request.response_drafts.forEach((draft, index) => {
    const label = `Response ${index + 1}`;
    assertUuid(draft.adaptation_id, `${label} adaptation`);
    adaptationIds.push(draft.adaptation_id);
    assertUniqueIds(draft.prescription_ids, `${label} prescriptions`);
    assignedPrescriptionIds.push(...draft.prescription_ids);
    assertUuid(draft.baseline_capability_estimate_id, `${label} baseline estimate`);
    assertUuid(draft.followup_capability_estimate_id, `${label} follow-up estimate`);
    if (draft.baseline_capability_estimate_id === draft.followup_capability_estimate_id) {
      throw new PostBlockReviewError(`${label} baseline and follow-up must be different.`);
    }
    assertNonBlank(draft.intervention_summary, `${label} intervention summary`);
    assertNonBlank(draft.measurement_uncertainty, `${label} measurement uncertainty`);
    const factors = draft.contextual_factors.map((item) => item.trim());
    if (factors.some((item) => !item) || new Set(factors).size !== factors.length) {
      throw new PostBlockReviewError(`${label} contextual factors must be unique and non-blank.`);
    }
    if (!(["higher_is_better", "lower_is_better"] as string[]).includes(draft.comparison_direction)) {
      throw new PostBlockReviewError(`${label} comparison direction is invalid.`);
    }
    if (!Number.isFinite(draft.minimum_meaningful_change) || draft.minimum_meaningful_change < 0) {
      throw new PostBlockReviewError(`${label} meaningful change must be non-negative.`);
    }
  });
  if (new Set(adaptationIds).size !== adaptationIds.length) {
    throw new PostBlockReviewError("Response adaptations must not contain duplicates.");
  }
  if (new Set(assignedPrescriptionIds).size !== assignedPrescriptionIds.length) {
    throw new PostBlockReviewError("One prescription cannot be assigned to multiple responses.");
  }
  assertTimestamp(request.responses_calculated_at, "Response calculation time");
  assertTimestamp(request.reviewed_at, "Review time");
  if (Date.parse(request.reviewed_at) < Date.parse(request.responses_calculated_at)) {
    throw new PostBlockReviewError("Review cannot predate response calculation.");
  }
  assertNonBlank(request.applicability_rationale, "Applicability rationale");
  assertNonBlank(request.uncertainty, "Uncertainty");
}

export function validateReplanningRequest(request: OperatorReplanningRequest): void {
  rejectServerOwnedFields(request);
  if (!request.candidate_contexts.length) {
    throw new PostBlockReviewError("One candidate context per prior adaptation is required.");
  }
  const adaptationIds: string[] = [];
  request.candidate_contexts.forEach((context, index) => {
    const label = `Candidate ${index + 1}`;
    assertUuid(context.adaptation_id, `${label} adaptation`);
    adaptationIds.push(context.adaptation_id);
    assertUuid(context.competency_floor_id, `${label} competency floor`);
    assertUuid(context.capability_estimate_id, `${label} capability estimate`);
    for (const [field, value] of Object.entries({
      general_relevance: context.general_relevance,
      goal_relevance: context.goal_relevance,
      prerequisite_value: context.prerequisite_value,
      expected_trainability: context.expected_trainability,
      transfer_value: context.transfer_value,
      fatigue_cost: context.fatigue_cost,
      time_cost: context.time_cost,
      interference_cost: context.interference_cost,
    })) assertUnitInterval(value, `${label} ${field.replaceAll("_", " ")}`);
    assertUniqueIds(context.prerequisite_adaptation_ids, `${label} prerequisites`, true);
    if (context.prerequisite_adaptation_ids.includes(context.adaptation_id)) {
      throw new PostBlockReviewError(`${label} cannot be its own prerequisite.`);
    }
    assertUniqueIds(context.source_observation_ids, `${label} observations`, true);
    assertUniqueIds(context.evidence_claim_ids, `${label} evidence claims`, true);
  });
  if (new Set(adaptationIds).size !== adaptationIds.length) {
    throw new PostBlockReviewError("Candidate adaptations must not contain duplicates.");
  }
  assertTimestamp(request.generated_at, "Strategy generation time");
  if (!Number.isInteger(request.review_after_days) || request.review_after_days <= 0) {
    throw new PostBlockReviewError("Review interval must be a positive integer.");
  }
  assertNonBlank(request.applicability_rationale, "Applicability rationale");
  assertNonBlank(request.uncertainty, "Uncertainty");
}

export async function fetchBlockReviewPreparation(
  apiBaseUrl: string,
  blockId: string,
  fetcher: typeof fetch = fetch,
): Promise<BlockReviewPreparationProjection> {
  assertUuid(blockId, "Block ID");
  const response = await fetcher(
    `${normalizedBaseUrl(apiBaseUrl)}/v1/operator/blocks/${blockId}/review-preparation`,
    { headers: authorizedHeaders({ Accept: "application/json" }, reviewerDevelopmentAccessToken) },
  );
  if (!response.ok) throw await responseError(response);
  return (await response.json()) as BlockReviewPreparationProjection;
}

export async function fetchPostBlockReviewQueue(
  apiBaseUrl: string,
  fetcher: typeof fetch = fetch,
): Promise<PostBlockReviewQueueProjection> {
  const response = await fetcher(
    `${normalizedBaseUrl(apiBaseUrl)}/v1/operator/post-block-review-queue`,
    { headers: authorizedHeaders({ Accept: "application/json" }, reviewerDevelopmentAccessToken) },
  );
  if (!response.ok) throw await responseError(response);
  const body = (await response.json()) as Partial<PostBlockReviewQueueProjection>;
  if (
    !body
    || !Array.isArray(body.items)
    || typeof body.projected_at !== "string"
    || typeof body.projection_version !== "string"
  ) {
    throw new PostBlockReviewError("Post-block review queue response is invalid.", response.status);
  }
  return body as PostBlockReviewQueueProjection;
}

export async function submitBlockReview(
  apiBaseUrl: string,
  blockId: string,
  request: OperatorBlockReviewRequest,
  fetcher: typeof fetch = fetch,
): Promise<BlockReviewCreationResult> {
  assertUuid(blockId, "Block ID");
  validateBlockReviewRequest(request);
  const response = await fetcher(
    `${normalizedBaseUrl(apiBaseUrl)}/v1/operator/blocks/${blockId}/reviews`,
    {
      method: "POST",
      headers: authorizedHeaders(
        { Accept: "application/json", "Content-Type": "application/json" },
        reviewerDevelopmentAccessToken,
      ),
      body: JSON.stringify(request),
    },
  );
  if (!response.ok) throw await responseError(response);
  return (await response.json()) as BlockReviewCreationResult;
}

export async function fetchReplanningPreparation(
  apiBaseUrl: string,
  blockReviewId: string,
  fetcher: typeof fetch = fetch,
): Promise<ReplanningPreparationProjection> {
  assertUuid(blockReviewId, "Block-review ID");
  const response = await fetcher(
    `${normalizedBaseUrl(apiBaseUrl)}/v1/operator/block-reviews/${blockReviewId}/replanning-preparation`,
    { headers: authorizedHeaders({ Accept: "application/json" }, reviewerDevelopmentAccessToken) },
  );
  if (!response.ok) throw await responseError(response);
  return (await response.json()) as ReplanningPreparationProjection;
}

export async function submitReplanning(
  apiBaseUrl: string,
  blockReviewId: string,
  request: OperatorReplanningRequest,
  fetcher: typeof fetch = fetch,
): Promise<PostBlockReplanningResult> {
  assertUuid(blockReviewId, "Block-review ID");
  validateReplanningRequest(request);
  const response = await fetcher(
    `${normalizedBaseUrl(apiBaseUrl)}/v1/operator/block-reviews/${blockReviewId}/replanning`,
    {
      method: "POST",
      headers: authorizedHeaders(
        { Accept: "application/json", "Content-Type": "application/json" },
        reviewerDevelopmentAccessToken,
      ),
      body: JSON.stringify(request),
    },
  );
  if (!response.ok) throw await responseError(response);
  return (await response.json()) as PostBlockReplanningResult;
}
