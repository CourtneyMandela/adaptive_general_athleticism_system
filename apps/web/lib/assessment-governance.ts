import {
  assessmentReviewerDevelopmentAccessToken,
  authorizedHeaders,
} from "./identity";

export interface AssessmentMeasurementSchema {
  measurement_type: "number" | "integer" | "category";
  label: string;
  minimum: number | null;
  maximum: number | null;
  step: number | null;
  allowed_values: string[];
  measurement_schema_version: string;
}

export interface AssessmentReview {
  id: string;
  decision: "approved" | "needs_revision" | "rejected";
  sequence_number: number;
  measurement_schema: AssessmentMeasurementSchema | null;
  recommended_reassessment_days: number | null;
  self_administered: boolean;
  reviewed_at: string;
  reviewer: string;
  applicability_notes: string;
  uncertainty: string;
  review_version: string;
  evidence_claim_ids: string[];
}

export interface CapabilityEstimationPolicy {
  id: string;
  decision: "approved" | "needs_revision" | "rejected";
  sequence_number: number;
  assessment_definition_review_id: string;
  calculation_method: string;
  valid_for_days: number;
  multi_observation_window_days: number;
  reviewed_at: string;
  reviewed_by: string;
  applicability_notes: string;
  uncertainty: string;
  rule_version: string;
  evidence_claim_ids: string[];
}

export interface AssessmentEvidenceClaim {
  id: string;
  claim: string;
  population: string;
  intervention: string;
  comparator: string | null;
  outcome: string;
  study_design: string;
  uncertainty: string;
  evidence_strength: string;
  athlete_applicability: string;
  applicability_notes: string;
  source_identifiers: { scheme: string; value: string }[];
  reviewer: string;
  claim_version: string;
}

export interface AssessmentGovernanceItem {
  definition: {
    id: string;
    slug: string;
    name: string;
    domain: string;
    observation_type: string;
    intensity: string;
    unit_or_scale: string;
    protocol_version: string;
  };
  status: "unreviewed" | "approved" | "needs_revision" | "rejected";
  readiness: "ready" | "blocked";
  current_review: AssessmentReview | null;
  review_history: AssessmentReview[];
  current_estimation_policy: CapabilityEstimationPolicy | null;
  estimation_policy_history: CapabilityEstimationPolicy[];
  evidence_claims: AssessmentEvidenceClaim[];
  issues: string[];
}

export interface AssessmentGovernanceProjection {
  projected_at: string;
  items: AssessmentGovernanceItem[];
  projection_version: string;
}

export class AssessmentGovernanceError extends Error {
  constructor(message: string, readonly status?: number) {
    super(message);
    this.name = "AssessmentGovernanceError";
  }
}

function isItem(value: unknown): value is AssessmentGovernanceItem {
  if (!value || typeof value !== "object") return false;
  const item = value as Partial<AssessmentGovernanceItem>;
  const definition = item.definition as Partial<AssessmentGovernanceItem["definition"]> | undefined;
  return Boolean(
    definition
    && typeof definition.id === "string"
    && typeof definition.name === "string"
    && typeof definition.slug === "string"
    && ["unreviewed", "approved", "needs_revision", "rejected"].includes(item.status ?? "")
    && ["ready", "blocked"].includes(item.readiness ?? "")
    && Array.isArray(item.review_history)
    && Array.isArray(item.estimation_policy_history)
    && Array.isArray(item.evidence_claims)
    && Array.isArray(item.issues),
  );
}

async function responseError(response: Response): Promise<AssessmentGovernanceError> {
  let message = `Request failed with status ${response.status}.`;
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string" && body.detail.trim()) message = body.detail;
  } catch {
    // Preserve the status fallback for non-JSON responses.
  }
  return new AssessmentGovernanceError(message, response.status);
}

export async function fetchAssessmentGovernance(
  apiBaseUrl: string,
  fetcher: typeof fetch = fetch,
): Promise<AssessmentGovernanceProjection> {
  const response = await fetcher(
    `${apiBaseUrl.replace(/\/$/, "")}/v1/operator/assessment-governance`,
    {
      headers: authorizedHeaders(
        { Accept: "application/json" },
        assessmentReviewerDevelopmentAccessToken,
      ),
    },
  );
  if (!response.ok) throw await responseError(response);
  const body = (await response.json()) as Partial<AssessmentGovernanceProjection>;
  if (
    !body
    || !Array.isArray(body.items)
    || !body.items.every(isItem)
    || typeof body.projected_at !== "string"
    || typeof body.projection_version !== "string"
  ) {
    throw new AssessmentGovernanceError(
      "Assessment-governance response is invalid.",
      response.status,
    );
  }
  return body as AssessmentGovernanceProjection;
}
