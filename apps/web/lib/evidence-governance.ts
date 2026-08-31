import {
  assessmentReviewerDevelopmentAccessToken,
  authorizedHeaders,
} from "./identity";

export interface EvidenceSourceSnapshot {
  id: string;
  title: string;
  authors: string[];
  journal: string | null;
  publication_year: number | null;
  primary_identifier: { scheme: string; value: string };
  metadata_provider: string;
  retrieval_uri: string;
  retrieved_at: string;
  metadata_version: string;
  sequence_number: number;
}

export interface EvidenceClaimReview {
  id: string;
  decision: "approved" | "needs_revision" | "rejected";
  sequence_number: number;
  reviewed_at: string;
  reviewer: string;
  source_verification_rationale: string;
  extraction_rationale: string;
  evidence_strength_rationale: string;
  applicability_rationale: string;
  uncertainty: string;
  conflict_disclosure: string;
  review_version: string;
}

export interface EvidenceGovernanceItem {
  claim: {
    id: string;
    claim: string;
    domain: string;
    population: string;
    intervention: string;
    comparator: string | null;
    outcome: string;
    study_design: string;
    uncertainty: string;
    limitations: string[];
    evidence_strength: string;
    athlete_applicability: string;
    applicability_notes: string;
    source_identifiers: { scheme: string; value: string }[];
    source_record_ids: string[];
    reviewer: string;
    claim_version: string;
  };
  status: "unreviewed" | "approved" | "needs_revision" | "rejected";
  readiness: "ready" | "blocked";
  sources: EvidenceSourceSnapshot[];
  current_review: EvidenceClaimReview | null;
  review_history: EvidenceClaimReview[];
  issues: string[];
}

export interface EvidenceAuthorityEvaluation {
  evaluated_at: string;
  readiness: "ready" | "blocked";
  claim_results: EvidenceGovernanceItem[];
  issues: string[];
  evaluation_version: string;
}

export interface EvidenceGovernanceProjection {
  projected_at: string;
  items: EvidenceGovernanceItem[];
  projection_version: string;
}

export class EvidenceGovernanceError extends Error {
  constructor(message: string, readonly status?: number) {
    super(message);
    this.name = "EvidenceGovernanceError";
  }
}

function isItem(value: unknown): value is EvidenceGovernanceItem {
  if (!value || typeof value !== "object") return false;
  const item = value as Partial<EvidenceGovernanceItem>;
  const claim = item.claim as Partial<EvidenceGovernanceItem["claim"]> | undefined;
  return Boolean(
    claim
    && typeof claim.id === "string"
    && typeof claim.claim === "string"
    && ["unreviewed", "approved", "needs_revision", "rejected"].includes(item.status ?? "")
    && ["ready", "blocked"].includes(item.readiness ?? "")
    && Array.isArray(item.sources)
    && Array.isArray(item.review_history)
    && Array.isArray(item.issues),
  );
}

async function responseError(response: Response): Promise<EvidenceGovernanceError> {
  let message = `Request failed with status ${response.status}.`;
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string" && body.detail.trim()) message = body.detail;
  } catch {
    // Preserve the status fallback for non-JSON responses.
  }
  return new EvidenceGovernanceError(message, response.status);
}

export async function fetchEvidenceGovernance(
  apiBaseUrl: string,
  fetcher: typeof fetch = fetch,
): Promise<EvidenceGovernanceProjection> {
  const response = await fetcher(
    `${apiBaseUrl.replace(/\/$/, "")}/v1/operator/evidence-governance`,
    {
      headers: authorizedHeaders(
        { Accept: "application/json" },
        assessmentReviewerDevelopmentAccessToken,
      ),
    },
  );
  if (!response.ok) throw await responseError(response);
  const body = (await response.json()) as Partial<EvidenceGovernanceProjection>;
  if (
    !body
    || !Array.isArray(body.items)
    || !body.items.every(isItem)
    || typeof body.projected_at !== "string"
    || typeof body.projection_version !== "string"
  ) {
    throw new EvidenceGovernanceError("Evidence-governance response is invalid.", response.status);
  }
  return body as EvidenceGovernanceProjection;
}
