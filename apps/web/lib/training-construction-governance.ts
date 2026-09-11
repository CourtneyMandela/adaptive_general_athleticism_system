import { authorizedHeaders, reviewerDevelopmentAccessToken } from "./identity";

export interface TrainingConstructionEvidenceSummary {
  claim_id: string;
  title: string;
  source_url: string;
  supported_use: string;
  unsupported_specifics: string;
}

export interface TrainingConstructionCandidate {
  candidate_version: "training-construction-candidate@1.0.0";
  candidate_id: string;
  slug: string;
  release_label: string;
  prepared_at: string;
  content_digest: string;
  summary: string;
  authority_basis: {
    scientific_support: string;
    engineering_prior: string;
  };
  exact_artifacts: string[];
  governs: string[];
  does_not_establish: string[];
  unresolved_limitations: string[];
  evidence: TrainingConstructionEvidenceSummary[];
}

export interface TrainingConstructionCandidateItem {
  candidate: TrainingConstructionCandidate;
  status: "available" | "blocked" | "ratified" | "conflict";
  ratified_at: string | null;
  issues: string[];
}

export interface TrainingConstructionCandidateProjection {
  projected_at: string;
  items: TrainingConstructionCandidateItem[];
  projection_version: string;
}

export class TrainingConstructionGovernanceError extends Error {
  constructor(message: string, readonly status?: number) {
    super(message);
    this.name = "TrainingConstructionGovernanceError";
  }
}

function isCandidateItem(value: unknown): value is TrainingConstructionCandidateItem {
  if (!value || typeof value !== "object") return false;
  const item = value as Partial<TrainingConstructionCandidateItem>;
  const candidate = item.candidate as Partial<TrainingConstructionCandidate> | undefined;
  return Boolean(
    candidate
    && candidate.candidate_version === "training-construction-candidate@1.0.0"
    && typeof candidate.candidate_id === "string"
    && typeof candidate.content_digest === "string"
    && typeof candidate.release_label === "string"
    && typeof candidate.authority_basis === "object"
    && Array.isArray(candidate.exact_artifacts)
    && Array.isArray(candidate.governs)
    && Array.isArray(candidate.does_not_establish)
    && Array.isArray(candidate.unresolved_limitations)
    && Array.isArray(candidate.evidence)
    && ["available", "blocked", "ratified", "conflict"].includes(item.status ?? "")
    && Array.isArray(item.issues)
  );
}

async function responseError(response: Response): Promise<TrainingConstructionGovernanceError> {
  let message = `Request failed with status ${response.status}.`;
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string" && body.detail.trim()) message = body.detail;
  } catch {
    // Preserve the status fallback for non-JSON responses.
  }
  return new TrainingConstructionGovernanceError(message, response.status);
}

export async function fetchTrainingConstructionCandidates(
  apiBaseUrl: string,
  fetcher: typeof fetch = fetch,
): Promise<TrainingConstructionCandidateProjection> {
  const response = await fetcher(
    `${apiBaseUrl.replace(/\/$/, "")}/v1/operator/training-construction-candidates`,
    {
      headers: authorizedHeaders(
        { Accept: "application/json" },
        reviewerDevelopmentAccessToken,
      ),
    },
  );
  if (!response.ok) throw await responseError(response);
  const body = (await response.json()) as Partial<TrainingConstructionCandidateProjection>;
  if (
    !Array.isArray(body.items)
    || !body.items.every(isCandidateItem)
    || typeof body.projected_at !== "string"
    || typeof body.projection_version !== "string"
  ) {
    throw new TrainingConstructionGovernanceError(
      "Training-construction candidate response is invalid.",
      response.status,
    );
  }
  return body as TrainingConstructionCandidateProjection;
}

export async function ratifyTrainingConstructionCandidate(
  apiBaseUrl: string,
  candidate: TrainingConstructionCandidate,
  fetcher: typeof fetch = fetch,
): Promise<unknown> {
  const response = await fetcher(
    `${apiBaseUrl.replace(/\/$/, "")}/v1/operator/training-construction-candidates/`
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
  return response.json();
}
