import { authorizedHeaders, reviewerDevelopmentAccessToken } from "./identity";

const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const timezonePattern = /(Z|[+-]\d{2}:\d{2})$/;

const topLevelFields = new Set([
  "priority_policy_id",
  "priority_policy_review_id",
  "candidate_contexts",
  "generated_at",
  "horizon_months",
  "review_after_days",
  "applicability_rationale",
  "uncertainty",
]);

const candidateFields = new Set([
  "adaptation_id",
  "competency_floor_id",
  "competency_floor_review_id",
  "capability_estimate_id",
  "general_relevance",
  "goal_relevance",
  "prerequisite_value",
  "expected_trainability",
  "transfer_value",
  "fatigue_cost",
  "time_cost",
  "interference_cost",
  "safe_to_train",
  "introductory_exposure_needed",
  "prerequisites_met",
  "prerequisite_adaptation_ids",
  "cultivate_comparative_advantage",
  "source_observation_ids",
  "evidence_claim_ids",
]);

export interface InitialPlanningCandidateContext {
  adaptation_id: string;
  competency_floor_id: string;
  competency_floor_review_id: string;
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

export interface OperatorInitialStrategyRequest {
  priority_policy_id: string;
  priority_policy_review_id: string;
  candidate_contexts: InitialPlanningCandidateContext[];
  generated_at: string;
  horizon_months: number;
  review_after_days: number;
  applicability_rationale: string;
  uncertainty: string;
}

export interface InitialPlanningContextDraftRequest {
  priority_policy_id: string;
  priority_policy_review_id: string;
  candidate_contexts: InitialPlanningCandidateContext[];
  horizon_months: number;
  review_after_days: number;
  authored_at: string;
  applicability_rationale: string;
  uncertainty: string;
}

export interface InitialPlanningContextDraft extends InitialPlanningContextDraftRequest {
  id: string;
  schema_version: string;
  created_at: string;
  athlete_id: string;
  authored_by_account_id: string;
  author_authority_assignment_id: string;
  draft_version: string;
}

export type InitialPlanningContextReviewDecision =
  | "approved"
  | "needs_revision"
  | "rejected";

export interface InitialPlanningContextReviewRequest {
  decision: InitialPlanningContextReviewDecision;
  reviewed_at: string;
  applicability_rationale: string;
  uncertainty: string;
}

export interface InitialPlanningContextReview extends InitialPlanningContextReviewRequest {
  id: string;
  schema_version: string;
  created_at: string;
  draft_id: string;
  reviewed_by_account_id: string;
  review_authority_assignment_id: string;
  review_version: string;
}

export interface InitialStrategyCreationResult {
  capability_needs: Array<{
    id: string;
    domain: string;
    status: string;
    confidence: string;
    rationale: string;
  }>;
  strategy: {
    id: string;
    generated_at: string;
    next_review_at: string;
    horizon_months: number;
    block_hypothesis: string;
    rule_version: string;
    priorities: Array<{
      id: string;
      adaptation_id: string;
      state: string;
      score: number;
      rank: number;
      development_allocation: number;
      rationale: string[];
    }>;
  };
  decision_record: {
    id: string;
    decision: string;
    reason: string;
    evidence: string[];
    uncertainty: string;
    decision_version: string;
    decided_on: string;
  };
}

export type InitialPlanningPreparationStatus =
  | "capability_estimate_required"
  | "capability_estimate_stale"
  | "planning_authorities_required"
  | "planning_context_review_required"
  | "initial_strategy_exists";

export interface InitialPlanningPreparationProjection {
  athlete_id: string;
  athlete_display_name: string;
  projected_at: string;
  status: InitialPlanningPreparationStatus;
  message: string;
  initial_strategy_id: string | null;
  estimate_options: Array<{
    estimate: {
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
    };
    source_observations: Array<{
      id: string;
      observed_at: string;
      observation_type: string;
      measurement: unknown;
      unit: string | null;
      source: string;
      reliability: string;
      provenance: {
        recorded_by: string;
        source_system: string;
        ingestion_method: string;
      };
    }>;
    floor_options: Array<{
      floor: {
        id: string;
        domain: string;
        estimate_scope: string;
        unit_or_scale: string;
        threshold: number;
        comparison_direction: string;
        population: string;
        applicability_notes: string;
        uncertainty: string;
        evidence_claim_ids: string[];
        floor_version: string;
      };
      review: {
        id: string;
        decision: string;
        reviewed_at: string;
        reviewed_by: string;
        applicability_rationale: string;
        uncertainty: string;
        review_version: string;
      };
    }>;
    adaptation_options: Array<{
      id: string;
      name: string;
      domain: string;
      preferred_stimuli: string[];
      valid_modalities: string[];
      evidence_claim_ids: string[];
    }>;
  }>;
  stale_estimates: Array<{
    id: string;
    domain: string;
    estimate: unknown;
    unit_or_scale: string;
    valid_until: string | null;
    rule_version: string;
  }>;
  priority_policy_options: Array<{
    policy: {
      id: string;
      deficit_weight: number;
      general_relevance_weight: number;
      goal_relevance_weight: number;
      prerequisite_value_weight: number;
      expected_trainability_weight: number;
      transfer_value_weight: number;
      fatigue_cost_weight: number;
      time_cost_weight: number;
      interference_cost_weight: number;
      cost_penalty: number;
      develop_score_threshold: number;
      comparative_advantage_threshold: number;
      severe_deficit_threshold: number;
      max_develop_adaptations: number;
      policy_version: string;
    };
    review: {
      id: string;
      decision: string;
      reviewed_at: string;
      reviewed_by: string;
      applicability_rationale: string;
      uncertainty: string;
      review_version: string;
    };
  }>;
  evidence_claims: Array<{
    id: string;
    claim: string;
    population: string;
    intervention: string;
    outcome: string;
    study_design: string;
    uncertainty: string;
    evidence_strength: string;
    athlete_applicability: string;
    applicability_notes: string;
    source_identifiers: Array<{ scheme: string; value: string }>;
    claim_version: string;
  }>;
  projection_version: string;
}

export class InitialPlanningReviewError extends Error {
  constructor(
    message: string,
    readonly status?: number,
  ) {
    super(message);
    this.name = "InitialPlanningReviewError";
  }
}

export function isUuid(value: string): boolean {
  return uuidPattern.test(value);
}

function objectValue(value: unknown, label: string): Record<string, unknown> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new InitialPlanningReviewError(`${label} must be a JSON object.`);
  }
  return value as Record<string, unknown>;
}

function rejectUnknownFields(
  value: Record<string, unknown>,
  allowed: Set<string>,
  label: string,
): void {
  const unknown = Object.keys(value).filter((key) => !allowed.has(key));
  if (unknown.length > 0) {
    throw new InitialPlanningReviewError(
      `${label} contains unsupported field(s): ${unknown.join(", ")}.`,
    );
  }
}

function uuidValue(value: unknown, label: string): string {
  if (typeof value !== "string" || !isUuid(value)) {
    throw new InitialPlanningReviewError(`${label} must be a UUID.`);
  }
  return value;
}

function unitInterval(value: unknown, label: string): number {
  if (typeof value !== "number" || !Number.isFinite(value) || value < 0 || value > 1) {
    throw new InitialPlanningReviewError(`${label} must be a number from 0 to 1.`);
  }
  return value;
}

function integerInRange(value: unknown, label: string, minimum: number, maximum?: number): number {
  if (
    typeof value !== "number" ||
    !Number.isInteger(value) ||
    value < minimum ||
    (maximum !== undefined && value > maximum)
  ) {
    const range = maximum === undefined ? `at least ${minimum}` : `from ${minimum} to ${maximum}`;
    throw new InitialPlanningReviewError(`${label} must be an integer ${range}.`);
  }
  return value;
}

function nonEmptyText(value: unknown, label: string): string {
  if (typeof value !== "string" || !value.trim()) {
    throw new InitialPlanningReviewError(`${label} must not be blank.`);
  }
  return value.trim();
}

function optionalBoolean(value: unknown, label: string, fallback: boolean): boolean {
  if (value === undefined) {
    return fallback;
  }
  if (typeof value !== "boolean") {
    throw new InitialPlanningReviewError(`${label} must be true or false.`);
  }
  return value;
}

function optionalUuidList(value: unknown, label: string): string[] {
  if (value === undefined) {
    return [];
  }
  if (!Array.isArray(value)) {
    throw new InitialPlanningReviewError(`${label} must be an array of UUIDs.`);
  }
  const values = value.map((item, index) => uuidValue(item, `${label}[${index}]`));
  if (new Set(values).size !== values.length) {
    throw new InitialPlanningReviewError(`${label} must not contain duplicates.`);
  }
  return values;
}

function candidateValue(value: unknown, index: number): InitialPlanningCandidateContext {
  const label = `candidate_contexts[${index}]`;
  const candidate = objectValue(value, label);
  rejectUnknownFields(candidate, candidateFields, label);
  const adaptationId = uuidValue(candidate.adaptation_id, `${label}.adaptation_id`);
  const prerequisites = optionalUuidList(
    candidate.prerequisite_adaptation_ids,
    `${label}.prerequisite_adaptation_ids`,
  );
  if (prerequisites.includes(adaptationId)) {
    throw new InitialPlanningReviewError(`${label} cannot name itself as a prerequisite.`);
  }
  return {
    adaptation_id: adaptationId,
    competency_floor_id: uuidValue(
      candidate.competency_floor_id,
      `${label}.competency_floor_id`,
    ),
    competency_floor_review_id: uuidValue(
      candidate.competency_floor_review_id,
      `${label}.competency_floor_review_id`,
    ),
    capability_estimate_id: uuidValue(
      candidate.capability_estimate_id,
      `${label}.capability_estimate_id`,
    ),
    general_relevance: unitInterval(candidate.general_relevance, `${label}.general_relevance`),
    goal_relevance: unitInterval(candidate.goal_relevance, `${label}.goal_relevance`),
    prerequisite_value: unitInterval(
      candidate.prerequisite_value,
      `${label}.prerequisite_value`,
    ),
    expected_trainability: unitInterval(
      candidate.expected_trainability,
      `${label}.expected_trainability`,
    ),
    transfer_value: unitInterval(candidate.transfer_value, `${label}.transfer_value`),
    fatigue_cost: unitInterval(candidate.fatigue_cost, `${label}.fatigue_cost`),
    time_cost: unitInterval(candidate.time_cost, `${label}.time_cost`),
    interference_cost: unitInterval(
      candidate.interference_cost,
      `${label}.interference_cost`,
    ),
    safe_to_train: optionalBoolean(candidate.safe_to_train, `${label}.safe_to_train`, true),
    introductory_exposure_needed: optionalBoolean(
      candidate.introductory_exposure_needed,
      `${label}.introductory_exposure_needed`,
      false,
    ),
    prerequisites_met: optionalBoolean(
      candidate.prerequisites_met,
      `${label}.prerequisites_met`,
      true,
    ),
    prerequisite_adaptation_ids: prerequisites,
    cultivate_comparative_advantage: optionalBoolean(
      candidate.cultivate_comparative_advantage,
      `${label}.cultivate_comparative_advantage`,
      false,
    ),
    source_observation_ids: optionalUuidList(
      candidate.source_observation_ids,
      `${label}.source_observation_ids`,
    ),
    evidence_claim_ids: optionalUuidList(
      candidate.evidence_claim_ids,
      `${label}.evidence_claim_ids`,
    ),
  };
}

export function parseInitialStrategyDraft(json: string): OperatorInitialStrategyRequest {
  let parsed: unknown;
  try {
    parsed = JSON.parse(json) as unknown;
  } catch {
    throw new InitialPlanningReviewError("Planning input must be valid JSON.");
  }
  const value = objectValue(parsed, "Planning input");
  rejectUnknownFields(value, topLevelFields, "Planning input");
  if (!Array.isArray(value.candidate_contexts) || value.candidate_contexts.length === 0) {
    throw new InitialPlanningReviewError("candidate_contexts must contain at least one item.");
  }
  const contexts = value.candidate_contexts.map(candidateValue);
  const adaptationIds = contexts.map((item) => item.adaptation_id);
  if (new Set(adaptationIds).size !== adaptationIds.length) {
    throw new InitialPlanningReviewError(
      "candidate_contexts must contain each adaptation exactly once.",
    );
  }
  const generatedAt = nonEmptyText(value.generated_at, "generated_at");
  if (!timezonePattern.test(generatedAt) || Number.isNaN(Date.parse(generatedAt))) {
    throw new InitialPlanningReviewError("generated_at must be a valid timestamp with a timezone.");
  }
  return {
    priority_policy_id: uuidValue(value.priority_policy_id, "priority_policy_id"),
    priority_policy_review_id: uuidValue(
      value.priority_policy_review_id,
      "priority_policy_review_id",
    ),
    candidate_contexts: contexts,
    generated_at: generatedAt,
    horizon_months: integerInRange(value.horizon_months, "horizon_months", 6, 24),
    review_after_days: integerInRange(value.review_after_days, "review_after_days", 1),
    applicability_rationale: nonEmptyText(
      value.applicability_rationale,
      "applicability_rationale",
    ),
    uncertainty: nonEmptyText(value.uncertainty, "uncertainty"),
  };
}

export async function submitInitialStrategy(
  apiBaseUrl: string,
  athleteId: string,
  request: OperatorInitialStrategyRequest,
  fetcher: typeof fetch = fetch,
): Promise<InitialStrategyCreationResult> {
  if (!isUuid(athleteId)) {
    throw new InitialPlanningReviewError("Athlete ID must be a UUID.");
  }
  const response = await fetcher(
    `${apiBaseUrl.replace(/\/$/, "")}/v1/operator/athletes/${encodeURIComponent(athleteId)}/initial-strategies`,
    {
      method: "POST",
      headers: authorizedHeaders(
        { Accept: "application/json", "Content-Type": "application/json" },
        reviewerDevelopmentAccessToken,
      ),
      body: JSON.stringify(request),
    },
  );
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new InitialPlanningReviewError(
      payload?.detail ?? `Initial strategy request failed with ${response.status}.`,
      response.status,
    );
  }
  return (await response.json()) as InitialStrategyCreationResult;
}

export async function fetchInitialPlanningPreparation(
  apiBaseUrl: string,
  athleteId: string,
  fetcher: typeof fetch = fetch,
): Promise<InitialPlanningPreparationProjection> {
  if (!isUuid(athleteId)) {
    throw new InitialPlanningReviewError("Athlete ID must be a UUID.");
  }
  const response = await fetcher(
    `${apiBaseUrl.replace(/\/$/, "")}/v1/operator/athletes/${encodeURIComponent(athleteId)}/initial-planning-preparation`,
    {
      headers: authorizedHeaders(
        { Accept: "application/json" },
        reviewerDevelopmentAccessToken,
      ),
    },
  );
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new InitialPlanningReviewError(
      payload?.detail ?? `Initial-planning preparation request failed with ${response.status}.`,
      response.status,
    );
  }
  return (await response.json()) as InitialPlanningPreparationProjection;
}

async function requireSuccessfulResponse<T>(
  response: Response,
  fallbackMessage: string,
): Promise<T> {
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new InitialPlanningReviewError(
      payload?.detail ?? `${fallbackMessage} (${response.status}).`,
      response.status,
    );
  }
  return (await response.json()) as T;
}

export async function createInitialPlanningContextDraft(
  apiBaseUrl: string,
  athleteId: string,
  request: InitialPlanningContextDraftRequest,
  fetcher: typeof fetch = fetch,
): Promise<InitialPlanningContextDraft> {
  if (!isUuid(athleteId)) {
    throw new InitialPlanningReviewError("Athlete ID must be a UUID.");
  }
  const response = await fetcher(
    `${apiBaseUrl.replace(/\/$/, "")}/v1/operator/athletes/${encodeURIComponent(athleteId)}/initial-planning-context-drafts`,
    {
      method: "POST",
      headers: authorizedHeaders(
        { Accept: "application/json", "Content-Type": "application/json" },
        reviewerDevelopmentAccessToken,
      ),
      body: JSON.stringify(request),
    },
  );
  return requireSuccessfulResponse<InitialPlanningContextDraft>(
    response,
    "Initial-planning context draft request failed",
  );
}

export async function reviewInitialPlanningContextDraft(
  apiBaseUrl: string,
  draftId: string,
  request: InitialPlanningContextReviewRequest,
  fetcher: typeof fetch = fetch,
): Promise<InitialPlanningContextReview> {
  if (!isUuid(draftId)) {
    throw new InitialPlanningReviewError("Draft ID must be a UUID.");
  }
  const response = await fetcher(
    `${apiBaseUrl.replace(/\/$/, "")}/v1/operator/initial-planning-context-drafts/${encodeURIComponent(draftId)}/reviews`,
    {
      method: "POST",
      headers: authorizedHeaders(
        { Accept: "application/json", "Content-Type": "application/json" },
        reviewerDevelopmentAccessToken,
      ),
      body: JSON.stringify(request),
    },
  );
  return requireSuccessfulResponse<InitialPlanningContextReview>(
    response,
    "Initial-planning context review request failed",
  );
}

export async function createInitialStrategyFromContextReview(
  apiBaseUrl: string,
  reviewId: string,
  generatedAt: string,
  fetcher: typeof fetch = fetch,
): Promise<InitialStrategyCreationResult> {
  if (!isUuid(reviewId)) {
    throw new InitialPlanningReviewError("Review ID must be a UUID.");
  }
  const response = await fetcher(
    `${apiBaseUrl.replace(/\/$/, "")}/v1/operator/initial-planning-context-reviews/${encodeURIComponent(reviewId)}/strategy`,
    {
      method: "POST",
      headers: authorizedHeaders(
        { Accept: "application/json", "Content-Type": "application/json" },
        reviewerDevelopmentAccessToken,
      ),
      body: JSON.stringify({ generated_at: generatedAt }),
    },
  );
  return requireSuccessfulResponse<InitialStrategyCreationResult>(
    response,
    "Initial strategy creation from context review failed",
  );
}
