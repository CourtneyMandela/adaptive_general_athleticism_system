import { authorizedHeaders, reviewerDevelopmentAccessToken } from "./identity";
import type { BlockPlanCreationResult, PlanningStatus, PriorityState } from "./block-review";

const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const digestPattern = /^sha256:[0-9a-f]{64}$/;

export interface PreparedFirstBlockCandidate {
  candidate_version: "prepared-first-block@1.0.0";
  candidate_id: string;
  content_digest: string;
  prepared_at: string;
  status: "available" | "accepted";
  athlete_id: string;
  strategy_id: string;
  starts_on: string;
  ends_on: string;
  duration_weeks: number;
  weekly_budget_minutes: number;
  resource_demand_ids: string[];
  resource_allocation_policy_id: string;
  expected_status: PlanningStatus;
  expected_allocations: Array<{
    adaptation_id: string;
    priority_state: PriorityState;
    allocated_weekly_minutes: number;
    sessions_per_week: number;
    status: PlanningStatus;
  }>;
  construction_basis: string;
  applicability_rationale: string;
  uncertainty: string;
  safety_boundary: string;
  identities: {
    block_plan_id: string;
    resource_allocation_ids: string[];
    decision_record_id: string;
  };
  accepted_result: BlockPlanCreationResult | null;
}

export interface PreparedFirstBlockProjection {
  strategy_id: string;
  athlete_id: string | null;
  starts_on: string;
  projected_at: string;
  status: "available" | "blocked" | "accepted";
  message: string;
  candidate: PreparedFirstBlockCandidate | null;
  blockers: string[];
  projection_version: string;
}

export interface PreparedFirstBlockRatificationResult {
  candidate_id: string;
  candidate_content_digest: string;
  created: boolean;
  result: BlockPlanCreationResult;
  ratification_version: string;
}

export class PreparedFirstBlockError extends Error {
  constructor(message: string, readonly status?: number) {
    super(message);
    this.name = "PreparedFirstBlockError";
  }
}

function assertUuid(value: string, label: string): void {
  if (!uuidPattern.test(value)) throw new PreparedFirstBlockError(`${label} must be a UUID.`);
}

function assertDate(value: string): void {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    throw new PreparedFirstBlockError("Start date must use YYYY-MM-DD.");
  }
  const parsed = new Date(`${value}T00:00:00Z`);
  if (Number.isNaN(parsed.valueOf()) || parsed.toISOString().slice(0, 10) !== value) {
    throw new PreparedFirstBlockError("Start date must be a real calendar date.");
  }
}

async function responseError(response: Response): Promise<PreparedFirstBlockError> {
  let message = `Request failed with status ${response.status}.`;
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string" && body.detail.trim()) message = body.detail;
  } catch {
    // Preserve the status-based message for non-JSON failures.
  }
  return new PreparedFirstBlockError(message, response.status);
}

function baseUrl(value: string): string {
  return value.replace(/\/$/, "");
}

export async function fetchPreparedFirstBlock(
  apiBaseUrl: string,
  strategyId: string,
  startsOn: string,
  fetcher: typeof fetch = fetch,
): Promise<PreparedFirstBlockProjection> {
  assertUuid(strategyId, "Strategy ID");
  assertDate(startsOn);
  const query = new URLSearchParams({ starts_on: startsOn });
  const response = await fetcher(
    `${baseUrl(apiBaseUrl)}/v1/operator/strategies/${encodeURIComponent(strategyId)}`
      + `/prepared-first-block?${query.toString()}`,
    {
      headers: authorizedHeaders({ Accept: "application/json" }, reviewerDevelopmentAccessToken),
    },
  );
  if (!response.ok) throw await responseError(response);
  return (await response.json()) as PreparedFirstBlockProjection;
}

export async function ratifyPreparedFirstBlock(
  apiBaseUrl: string,
  strategyId: string,
  candidate: PreparedFirstBlockCandidate,
  fetcher: typeof fetch = fetch,
): Promise<PreparedFirstBlockRatificationResult> {
  assertUuid(strategyId, "Strategy ID");
  assertUuid(candidate.candidate_id, "Candidate ID");
  assertDate(candidate.starts_on);
  if (!digestPattern.test(candidate.content_digest)) {
    throw new PreparedFirstBlockError("Candidate digest is invalid.");
  }
  const response = await fetcher(
    `${baseUrl(apiBaseUrl)}/v1/operator/strategies/${encodeURIComponent(strategyId)}`
      + `/prepared-first-blocks/${encodeURIComponent(candidate.candidate_id)}/ratifications`,
    {
      method: "POST",
      headers: authorizedHeaders(
        { Accept: "application/json", "Content-Type": "application/json" },
        reviewerDevelopmentAccessToken,
      ),
      body: JSON.stringify({
        candidate_version: candidate.candidate_version,
        content_digest: candidate.content_digest,
        starts_on: candidate.starts_on,
        approval_attestation: true,
      }),
    },
  );
  if (!response.ok) throw await responseError(response);
  return (await response.json()) as PreparedFirstBlockRatificationResult;
}
