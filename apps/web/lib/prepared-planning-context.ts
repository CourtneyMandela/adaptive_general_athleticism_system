import { authorizedHeaders, reviewerDevelopmentAccessToken } from "./identity";
import type {
  InitialPlanningCandidateContext,
  InitialPlanningContextDraft,
  InitialPlanningContextReview,
} from "./initial-planning-review";

export interface PreparedContextComponent {
  field: string;
  value: number | boolean;
  treatment: "used" | "unused" | "hard_gate";
  basis: string;
  limitation: string;
}

export interface PreparedInitialPlanningContextCandidate {
  candidate_version: "prepared-initial-planning-context@1.0.0";
  candidate_id: string;
  content_digest: string;
  prepared_at: string;
  athlete_id: string;
  athlete_display_name: string;
  status: "available" | "accepted";
  summary: string;
  priority_policy_id: string;
  priority_policy_review_id: string;
  policy_version: string;
  floor_version: string;
  estimate_scope: string;
  candidate_context: InitialPlanningCandidateContext;
  horizon_months: number;
  review_after_days: number;
  applicability_rationale: string;
  uncertainty: string;
  components: PreparedContextComponent[];
  expected_priority_state: string;
  expected_priority_score: number;
  safety_boundary: string;
  accepted_draft_id: string | null;
  accepted_draft: InitialPlanningContextDraft | null;
  accepted_review: InitialPlanningContextReview | null;
}

export interface PreparedInitialPlanningContextProjection {
  athlete_id: string;
  projected_at: string;
  status: "available" | "blocked" | "accepted";
  message: string;
  candidate: PreparedInitialPlanningContextCandidate | null;
  blockers: string[];
  projection_version: string;
}

export interface PreparedInitialPlanningContextRatificationResult {
  candidate_id: string;
  candidate_content_digest: string;
  created: boolean;
  draft: InitialPlanningContextDraft;
  ratification_version: string;
}

export class PreparedPlanningContextError extends Error {
  constructor(message: string, readonly status?: number) {
    super(message);
    this.name = "PreparedPlanningContextError";
  }
}

async function responseError(response: Response): Promise<PreparedPlanningContextError> {
  let message = `Request failed with status ${response.status}.`;
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string" && body.detail.trim()) message = body.detail;
  } catch {
    // Preserve the status fallback for non-JSON responses.
  }
  return new PreparedPlanningContextError(message, response.status);
}

export async function fetchPreparedInitialPlanningContext(
  apiBaseUrl: string,
  athleteId: string,
  fetcher: typeof fetch = fetch,
): Promise<PreparedInitialPlanningContextProjection> {
  const response = await fetcher(
    `${apiBaseUrl.replace(/\/$/, "")}/v1/operator/athletes/`
      + `${encodeURIComponent(athleteId)}/prepared-initial-planning-context`,
    {
      headers: authorizedHeaders(
        { Accept: "application/json" },
        reviewerDevelopmentAccessToken,
      ),
    },
  );
  if (!response.ok) throw await responseError(response);
  return response.json() as Promise<PreparedInitialPlanningContextProjection>;
}

export async function ratifyPreparedInitialPlanningContext(
  apiBaseUrl: string,
  athleteId: string,
  candidate: PreparedInitialPlanningContextCandidate,
  fetcher: typeof fetch = fetch,
): Promise<PreparedInitialPlanningContextRatificationResult> {
  const response = await fetcher(
    `${apiBaseUrl.replace(/\/$/, "")}/v1/operator/athletes/`
      + `${encodeURIComponent(athleteId)}/prepared-initial-planning-context/`
      + `${encodeURIComponent(candidate.candidate_id)}/ratifications`,
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
  return response.json() as Promise<PreparedInitialPlanningContextRatificationResult>;
}
