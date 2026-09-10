import { authorizedHeaders, reviewerDevelopmentAccessToken } from "./identity";

export interface ResourceGovernanceEvidenceSummary {
  title: string;
  source_url: string;
  population: string;
  finding: string;
  limitations: string[];
}

export interface ResourceGovernanceCandidate {
  candidate_version: "resource-governance-candidate@1.0.0";
  candidate_id: string;
  content_digest: string;
  prepared_at: string;
  release_label: string;
  summary: string;
  exact_artifacts: string[];
  governs: string[];
  does_not_establish: string[];
  operational_choices: string[];
  unresolved_limitations: string[];
  evidence: ResourceGovernanceEvidenceSummary[];
}

export interface ResourceGovernanceCandidateItem {
  candidate: ResourceGovernanceCandidate;
  status: "available" | "blocked" | "ratified" | "conflict";
  ratified_at: string | null;
  issues: string[];
}

export interface ResourceGovernanceCandidateProjection {
  projected_at: string;
  items: ResourceGovernanceCandidateItem[];
  projection_version: string;
}

export class ResourceGovernanceError extends Error {
  constructor(message: string, readonly status?: number) {
    super(message);
    this.name = "ResourceGovernanceError";
  }
}

function isCandidateItem(value: unknown): value is ResourceGovernanceCandidateItem {
  if (!value || typeof value !== "object") return false;
  const item = value as Partial<ResourceGovernanceCandidateItem>;
  const candidate = item.candidate as Partial<ResourceGovernanceCandidate> | undefined;
  return Boolean(
    candidate
    && candidate.candidate_version === "resource-governance-candidate@1.0.0"
    && typeof candidate.candidate_id === "string"
    && typeof candidate.content_digest === "string"
    && typeof candidate.release_label === "string"
    && Array.isArray(candidate.exact_artifacts)
    && Array.isArray(candidate.governs)
    && Array.isArray(candidate.does_not_establish)
    && Array.isArray(candidate.operational_choices)
    && Array.isArray(candidate.unresolved_limitations)
    && Array.isArray(candidate.evidence)
    && ["available", "blocked", "ratified", "conflict"].includes(item.status ?? "")
    && Array.isArray(item.issues)
  );
}

async function responseError(response: Response): Promise<ResourceGovernanceError> {
  let message = `Request failed with status ${response.status}.`;
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string" && body.detail.trim()) message = body.detail;
  } catch {
    // Preserve the status fallback for non-JSON responses.
  }
  return new ResourceGovernanceError(message, response.status);
}

export async function fetchResourceGovernanceCandidates(
  apiBaseUrl: string,
  fetcher: typeof fetch = fetch,
): Promise<ResourceGovernanceCandidateProjection> {
  const response = await fetcher(
    `${apiBaseUrl.replace(/\/$/, "")}/v1/operator/resource-governance/candidates`,
    {
      headers: authorizedHeaders(
        { Accept: "application/json" },
        reviewerDevelopmentAccessToken,
      ),
    },
  );
  if (!response.ok) throw await responseError(response);
  const body = (await response.json()) as Partial<ResourceGovernanceCandidateProjection>;
  if (
    !Array.isArray(body.items)
    || !body.items.every(isCandidateItem)
    || typeof body.projected_at !== "string"
    || typeof body.projection_version !== "string"
  ) {
    throw new ResourceGovernanceError("Resource candidate response is invalid.", response.status);
  }
  return body as ResourceGovernanceCandidateProjection;
}

export async function ratifyResourceGovernanceCandidate(
  apiBaseUrl: string,
  candidate: ResourceGovernanceCandidate,
  fetcher: typeof fetch = fetch,
): Promise<unknown> {
  const response = await fetcher(
    `${apiBaseUrl.replace(/\/$/, "")}/v1/operator/resource-governance/candidates/`
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
