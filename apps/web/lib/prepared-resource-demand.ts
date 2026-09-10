import { authorizedHeaders, reviewerDevelopmentAccessToken } from "./identity";
import type {
  ResourceDemandPreparationResult,
  StimulusSpecificationRequest,
} from "./resource-demand-review";

export interface PreparedResourceDemandCandidate {
  candidate_version: "prepared-resource-demand@1.0.0";
  candidate_id: string;
  content_digest: string;
  prepared_at: string;
  status: "available" | "accepted";
  athlete_id: string;
  strategy_id: string;
  priority_id: string;
  adaptation_id: string;
  adaptation_name: string;
  environment_id: string;
  environment_name: string;
  environment_snapshot: {
    captured_at: string;
    available_equipment: Array<{
      equipment_id: string;
      category: string;
      capabilities: Record<string, unknown>;
      load_limits: Record<string, unknown>;
    }>;
    source_availability_ids: string[];
    floor_area_m2: number | null;
    max_noise_level: string;
    outdoor_access: boolean;
  };
  resource_authority_candidate_id: string;
  resource_authority_content_digest: string;
  stimulus_specification: StimulusSpecificationRequest;
  exercise_candidate_id: string;
  exercise_name: string;
  exercise_resolver_policy_id: string;
  expected_resolution_status: "full" | "partial" | "infeasible";
  expected_selected_exercise_id: string;
  minimum_weekly_minutes: number;
  target_weekly_minutes: number;
  sessions_per_week: number;
  per_session_scheduling_minutes: number;
  scheduling_basis: string;
  applicability_rationale: string;
  uncertainty: string;
  safety_boundary: string;
  dose_boundary: string;
  identities: {
    stimulus_requirement_id: string;
    exercise_resolution_id: string;
    resource_demand_id: string;
    decision_record_id: string;
  };
  accepted_result: ResourceDemandPreparationResult | null;
}

export interface PreparedResourceDemandProjection {
  strategy_id: string;
  athlete_id: string | null;
  projected_at: string;
  status: "available" | "blocked" | "accepted";
  message: string;
  candidates: PreparedResourceDemandCandidate[];
  blockers: string[];
  projection_version: string;
}

export interface PreparedResourceDemandRatificationResult {
  candidate_id: string;
  candidate_content_digest: string;
  created: boolean;
  result: ResourceDemandPreparationResult;
  ratification_version: string;
}

export class PreparedResourceDemandError extends Error {
  constructor(message: string, readonly status?: number) {
    super(message);
    this.name = "PreparedResourceDemandError";
  }
}

async function responseError(response: Response): Promise<PreparedResourceDemandError> {
  let message = `Request failed with status ${response.status}.`;
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string" && body.detail.trim()) message = body.detail;
  } catch {
    // Preserve the status fallback for non-JSON responses.
  }
  return new PreparedResourceDemandError(message, response.status);
}

function base(apiBaseUrl: string): string {
  return apiBaseUrl.replace(/\/$/, "");
}

export async function fetchPreparedResourceDemands(
  apiBaseUrl: string,
  strategyId: string,
  fetcher: typeof fetch = fetch,
): Promise<PreparedResourceDemandProjection> {
  const response = await fetcher(
    `${base(apiBaseUrl)}/v1/operator/strategies/${encodeURIComponent(strategyId)}`
      + "/prepared-resource-demands",
    {
      headers: authorizedHeaders(
        { Accept: "application/json" },
        reviewerDevelopmentAccessToken,
      ),
    },
  );
  if (!response.ok) throw await responseError(response);
  return response.json() as Promise<PreparedResourceDemandProjection>;
}

export async function ratifyPreparedResourceDemand(
  apiBaseUrl: string,
  strategyId: string,
  candidate: PreparedResourceDemandCandidate,
  fetcher: typeof fetch = fetch,
): Promise<PreparedResourceDemandRatificationResult> {
  const response = await fetcher(
    `${base(apiBaseUrl)}/v1/operator/strategies/${encodeURIComponent(strategyId)}`
      + `/prepared-resource-demands/${encodeURIComponent(candidate.candidate_id)}/ratifications`,
    {
      method: "POST",
      headers: authorizedHeaders(
        { Accept: "application/json", "Content-Type": "application/json" },
        reviewerDevelopmentAccessToken,
      ),
      body: JSON.stringify({
        candidate_version: candidate.candidate_version,
        content_digest: candidate.content_digest,
        approval_attestation: true,
      }),
    },
  );
  if (!response.ok) throw await responseError(response);
  return response.json() as Promise<PreparedResourceDemandRatificationResult>;
}
