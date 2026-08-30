import { authorizedHeaders, reviewerDevelopmentAccessToken } from "./identity";
import type {
  ResourceDemandEvidenceClaim,
  ResourceDemandObservation,
} from "./resource-demand-review";

const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export type PriorityState = "develop" | "maintain" | "expose" | "defer";
export type PlanningStatus = "full" | "partial" | "infeasible";

export interface BlockDemandHistoryItem {
  resource_demand: {
    id: string;
    adaptation_priority_id: string;
    adaptation_id: string;
    priority_state: PriorityState;
    minimum_weekly_minutes: number;
    target_weekly_minutes: number;
    sessions_per_week: number;
    source_observation_ids: string[];
    evidence_claim_ids: string[];
    rationale: string;
    demand_version: string;
  };
  stimulus_requirement: { id: string; rationale: string } | null;
  exercise_resolution: {
    id: string;
    status: PlanningStatus;
    selected_exercise_id: string | null;
    unresolved_issues: Array<{ code: string; detail: string }>;
    rationale: string;
  } | null;
}

export interface BlockPreparationProjection {
  strategy: {
    id: string;
    athlete_id: string;
    block_hypothesis: string;
    generated_at: string;
    next_review_at: string;
    rule_version: string;
  };
  projected_at: string;
  priorities: Array<{
    priority: {
      id: string;
      adaptation_id: string;
      state: PriorityState;
      rank: number;
      score: number;
      development_allocation: number;
      rationale: string[];
    };
    adaptation: {
      id: string;
      name: string;
      domain: string;
    };
    demand_history: BlockDemandHistoryItem[];
  }>;
  resource_allocation_policies: Array<{
    id: string;
    develop_weight: number;
    maintain_weight: number;
    expose_weight: number;
    allow_partial_exercise_resolution: boolean;
    policy_version: string;
  }>;
  existing_blocks: Array<{
    id: string;
    status: PlanningStatus;
    starts_on: string;
    ends_on: string;
    duration_weeks: number;
    weekly_budget_minutes: number;
    constraints: string[];
    generated_at: string;
    rule_version: string;
  }>;
  source_observations: ResourceDemandObservation[];
  evidence_claims: ResourceDemandEvidenceClaim[];
  projection_version: string;
}

export interface OperatorBlockPlanRequest {
  resource_demand_ids: string[];
  resource_allocation_policy_id: string;
  weekly_budget_minutes: number;
  starts_on: string;
  duration_weeks: number;
  constraints: string[];
  generated_at: string;
  applicability_rationale: string;
  uncertainty: string;
}

export interface BlockPlanCreationResult {
  block_plan: {
    id: string;
    long_range_strategy_id: string;
    status: PlanningStatus;
    starts_on: string;
    ends_on: string;
    duration_weeks: number;
    weekly_budget_minutes: number;
    hypothesis: string;
    constraints: string[];
    rule_version: string;
    allocations: Array<{
      id: string;
      resource_demand_id: string;
      adaptation_priority_id: string;
      adaptation_id: string;
      priority_state: PriorityState;
      minimum_weekly_minutes: number;
      target_weekly_minutes: number;
      allocated_weekly_minutes: number;
      sessions_per_week: number;
      status: PlanningStatus;
      issues: Array<{ code: string; detail: string }>;
    }>;
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

export class BlockReviewError extends Error {
  constructor(
    message: string,
    readonly status?: number,
  ) {
    super(message);
    this.name = "BlockReviewError";
  }
}

function normalizedBaseUrl(apiBaseUrl: string): string {
  return apiBaseUrl.replace(/\/$/, "");
}

function assertUuid(value: string, label: string): void {
  if (!uuidPattern.test(value)) throw new BlockReviewError(`${label} must be a UUID.`);
}

function assertNonBlank(value: string, label: string): void {
  if (!value.trim()) throw new BlockReviewError(`${label} must not be blank.`);
}

async function responseError(response: Response): Promise<BlockReviewError> {
  let message = `Request failed with status ${response.status}.`;
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string" && body.detail.trim()) message = body.detail;
  } catch {
    // Preserve the status-based message for non-JSON failures.
  }
  return new BlockReviewError(message, response.status);
}

export function validateBlockPlanRequest(request: OperatorBlockPlanRequest): void {
  const unsafe = request as unknown as Record<string, unknown>;
  for (const field of ["reviewed_by", "review_authority_assignment_id"]) {
    if (field in unsafe) throw new BlockReviewError(`${field} is server-owned.`);
  }
  if (request.resource_demand_ids.length === 0) {
    throw new BlockReviewError("One demand per strategy priority is required.");
  }
  request.resource_demand_ids.forEach((id, index) =>
    assertUuid(id, `Resource demand ${index + 1}`),
  );
  if (new Set(request.resource_demand_ids).size !== request.resource_demand_ids.length) {
    throw new BlockReviewError("Resource-demand selections must not contain duplicates.");
  }
  assertUuid(request.resource_allocation_policy_id, "Resource-allocation policy");
  if (!Number.isInteger(request.weekly_budget_minutes) || request.weekly_budget_minutes <= 0) {
    throw new BlockReviewError("Weekly budget must be a positive integer.");
  }
  if (!Number.isInteger(request.duration_weeks) || request.duration_weeks < 4 || request.duration_weeks > 6) {
    throw new BlockReviewError("Block duration must be four to six weeks.");
  }
  if (!/^\d{4}-\d{2}-\d{2}$/.test(request.starts_on)) {
    throw new BlockReviewError("Block start date must use YYYY-MM-DD.");
  }
  const startDate = new Date(`${request.starts_on}T00:00:00Z`);
  if (Number.isNaN(startDate.valueOf()) || startDate.toISOString().slice(0, 10) !== request.starts_on) {
    throw new BlockReviewError("Block start date must be a real calendar date.");
  }
  if (!/(Z|[+-]\d{2}:\d{2})$/.test(request.generated_at)) {
    throw new BlockReviewError("generated_at must include a timezone.");
  }
  if (request.starts_on < request.generated_at.slice(0, 10)) {
    throw new BlockReviewError("Block cannot start before it is generated.");
  }
  const normalizedConstraints = request.constraints.map((item) => item.trim());
  if (normalizedConstraints.some((item) => !item)) {
    throw new BlockReviewError("Constraints must not contain blank values.");
  }
  if (new Set(normalizedConstraints).size !== normalizedConstraints.length) {
    throw new BlockReviewError("Constraints must not contain duplicates.");
  }
  assertNonBlank(request.applicability_rationale, "Applicability rationale");
  assertNonBlank(request.uncertainty, "Uncertainty");
}

export async function fetchBlockPreparation(
  apiBaseUrl: string,
  strategyId: string,
  fetcher: typeof fetch = fetch,
): Promise<BlockPreparationProjection> {
  assertUuid(strategyId, "Strategy ID");
  const response = await fetcher(
    `${normalizedBaseUrl(apiBaseUrl)}/v1/operator/strategies/${strategyId}/block-preparation`,
    {
      headers: authorizedHeaders(
        { Accept: "application/json" },
        reviewerDevelopmentAccessToken,
      ),
    },
  );
  if (!response.ok) throw await responseError(response);
  return (await response.json()) as BlockPreparationProjection;
}

export async function submitBlockPlan(
  apiBaseUrl: string,
  strategyId: string,
  request: OperatorBlockPlanRequest,
  fetcher: typeof fetch = fetch,
): Promise<BlockPlanCreationResult> {
  assertUuid(strategyId, "Strategy ID");
  validateBlockPlanRequest(request);
  const response = await fetcher(
    `${normalizedBaseUrl(apiBaseUrl)}/v1/operator/strategies/${strategyId}/blocks`,
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
  return (await response.json()) as BlockPlanCreationResult;
}
