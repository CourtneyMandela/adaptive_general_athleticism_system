import { authorizedHeaders, reviewerDevelopmentAccessToken } from "./identity";

export interface PlanningPolicyEvidenceSummary {
  title: string;
  source_url: string;
  population: string;
  finding: string;
  limitations: string[];
  conflict_disclosure: string;
}

export interface PlanningGovernanceCandidate {
  candidate_version: "planning-governance-candidate@1.0.0";
  candidate_id: string;
  slug: string;
  release_label: string;
  prepared_at: string;
  content_digest: string;
  summary: string;
  governs: string[];
  does_not_establish: string[];
  operational_choices: string[];
  unresolved_limitations: string[];
  evidence: PlanningPolicyEvidenceSummary[];
}

export interface PlanningGovernanceCandidateItem {
  candidate: PlanningGovernanceCandidate;
  status: "available" | "ratified" | "conflict";
  ratified_at: string | null;
  issues: string[];
}

export interface PlanningGovernanceCandidateProjection {
  projected_at: string;
  items: PlanningGovernanceCandidateItem[];
  projection_version: string;
}

export class PlanningGovernanceError extends Error {
  constructor(message: string, readonly status?: number) {
    super(message);
    this.name = "PlanningGovernanceError";
  }
}

function isCandidateItem(value: unknown): value is PlanningGovernanceCandidateItem {
  if (!value || typeof value !== "object") return false;
  const item = value as Partial<PlanningGovernanceCandidateItem>;
  const candidate = item.candidate as Partial<PlanningGovernanceCandidate> | undefined;
  return Boolean(
    candidate
    && candidate.candidate_version === "planning-governance-candidate@1.0.0"
    && typeof candidate.candidate_id === "string"
    && typeof candidate.release_label === "string"
    && typeof candidate.content_digest === "string"
    && typeof candidate.summary === "string"
    && Array.isArray(candidate.governs)
    && Array.isArray(candidate.does_not_establish)
    && Array.isArray(candidate.operational_choices)
    && Array.isArray(candidate.unresolved_limitations)
    && Array.isArray(candidate.evidence)
    && ["available", "ratified", "conflict"].includes(item.status ?? "")
    && Array.isArray(item.issues)
  );
}

async function responseError(response: Response): Promise<PlanningGovernanceError> {
  let message = `Request failed with status ${response.status}.`;
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string" && body.detail.trim()) message = body.detail;
  } catch {
    // Preserve the status fallback for non-JSON responses.
  }
  return new PlanningGovernanceError(message, response.status);
}

export async function fetchPlanningGovernanceCandidates(
  apiBaseUrl: string,
  fetcher: typeof fetch = fetch,
): Promise<PlanningGovernanceCandidateProjection> {
  const response = await fetcher(
    `${apiBaseUrl.replace(/\/$/, "")}/v1/operator/planning-governance/candidates`,
    {
      headers: authorizedHeaders(
        { Accept: "application/json" },
        reviewerDevelopmentAccessToken,
      ),
    },
  );
  if (!response.ok) throw await responseError(response);
  const body = (await response.json()) as Partial<PlanningGovernanceCandidateProjection>;
  if (
    !body
    || !Array.isArray(body.items)
    || !body.items.every(isCandidateItem)
    || typeof body.projected_at !== "string"
    || typeof body.projection_version !== "string"
  ) {
    throw new PlanningGovernanceError("Planning candidate response is invalid.", response.status);
  }
  return body as PlanningGovernanceCandidateProjection;
}

export async function ratifyPlanningGovernanceCandidate(
  apiBaseUrl: string,
  candidate: PlanningGovernanceCandidate,
  fetcher: typeof fetch = fetch,
): Promise<unknown> {
  const response = await fetcher(
    `${apiBaseUrl.replace(/\/$/, "")}/v1/operator/planning-governance/candidates/`
      + `${candidate.candidate_id}/ratifications`,
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
