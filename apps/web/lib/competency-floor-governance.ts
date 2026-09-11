import { authorizedHeaders, reviewerDevelopmentAccessToken } from "./identity";

const numericValueOrigins = new Set<string>([
  "direct_study_result",
  "derived_from_study",
  "professional_judgment",
  "personal_calibration",
]);
const operationalUseOrigins = new Set<string>([
  "evidence_validated",
  "evidence_informed_engineering_judgment",
  "professional_judgment",
  "personal_calibration",
]);

export interface CompetencyFloorEvidenceSummary {
  title: string;
  source_url: string;
  population: string;
  finding: string;
  limitations: string[];
  conflict_disclosure: string;
}

export interface CompetencyFloorCandidate {
  candidate_version: "competency-floor-candidate@1.1.0";
  candidate_id: string;
  slug: string;
  release_label: string;
  prepared_at: string;
  content_digest: string;
  summary: string;
  authority_basis: {
    numeric_value_origin:
      | "direct_study_result"
      | "derived_from_study"
      | "professional_judgment"
      | "personal_calibration";
    operational_use_origin:
      | "evidence_validated"
      | "evidence_informed_engineering_judgment"
      | "professional_judgment"
      | "personal_calibration";
    numeric_value_explanation: string;
    operational_use_explanation: string;
  };
  domain: string;
  estimate_scope: string;
  unit_or_scale: string;
  threshold: number;
  comparison_direction: "higher_is_better" | "lower_is_better";
  minimum_age_years: number;
  maximum_age_years: number;
  governs: string[];
  does_not_establish: string[];
  unresolved_limitations: string[];
  evidence: CompetencyFloorEvidenceSummary[];
}

export interface CompetencyFloorCandidateItem {
  candidate: CompetencyFloorCandidate;
  status: "available" | "ratified" | "conflict";
  ratified_at: string | null;
  issues: string[];
}

export interface CompetencyFloorCandidateProjection {
  projected_at: string;
  items: CompetencyFloorCandidateItem[];
  batch: CompetencyFloorCandidateBatch;
  projection_version: string;
}

export interface CompetencyFloorCandidateReference {
  candidate_id: string;
  candidate_version: "competency-floor-candidate@1.1.0";
  content_digest: string;
}

export interface CompetencyFloorCandidateBatch {
  batch_version: "competency-floor-candidate-batch@1.0.0";
  batch_id: string;
  content_digest: string;
  candidates: CompetencyFloorCandidateReference[];
}

export class CompetencyFloorGovernanceError extends Error {
  constructor(message: string, readonly status?: number) {
    super(message);
    this.name = "CompetencyFloorGovernanceError";
  }
}

function isCandidateItem(value: unknown): value is CompetencyFloorCandidateItem {
  if (!value || typeof value !== "object") return false;
  const item = value as Partial<CompetencyFloorCandidateItem>;
  const candidate = item.candidate as Partial<CompetencyFloorCandidate> | undefined;
  return Boolean(
    candidate
    && candidate.candidate_version === "competency-floor-candidate@1.1.0"
    && typeof candidate.candidate_id === "string"
    && typeof candidate.release_label === "string"
    && typeof candidate.content_digest === "string"
    && typeof candidate.summary === "string"
    && candidate.authority_basis
    && numericValueOrigins.has(candidate.authority_basis.numeric_value_origin)
    && operationalUseOrigins.has(candidate.authority_basis.operational_use_origin)
    && typeof candidate.authority_basis.numeric_value_explanation === "string"
    && typeof candidate.authority_basis.operational_use_explanation === "string"
    && typeof candidate.threshold === "number"
    && typeof candidate.minimum_age_years === "number"
    && typeof candidate.maximum_age_years === "number"
    && Array.isArray(candidate.governs)
    && Array.isArray(candidate.does_not_establish)
    && Array.isArray(candidate.unresolved_limitations)
    && Array.isArray(candidate.evidence)
    && ["available", "ratified", "conflict"].includes(item.status ?? "")
    && Array.isArray(item.issues)
  );
}

function isBatch(
  value: unknown,
  items: CompetencyFloorCandidateItem[],
): value is CompetencyFloorCandidateBatch {
  if (!value || typeof value !== "object") return false;
  const batch = value as Partial<CompetencyFloorCandidateBatch>;
  if (
    batch.batch_version !== "competency-floor-candidate-batch@1.0.0"
    || typeof batch.batch_id !== "string"
    || typeof batch.content_digest !== "string"
    || !batch.content_digest.startsWith("sha256:")
    || !Array.isArray(batch.candidates)
    || batch.candidates.length === 0
  ) return false;
  const candidates = new Map(items.map((item) => [item.candidate.candidate_id, item.candidate]));
  const ids = new Set<string>();
  return batch.candidates.every((reference) => {
    if (
      !reference
      || reference.candidate_version !== "competency-floor-candidate@1.1.0"
      || typeof reference.candidate_id !== "string"
      || typeof reference.content_digest !== "string"
      || ids.has(reference.candidate_id)
    ) return false;
    ids.add(reference.candidate_id);
    const candidate = candidates.get(reference.candidate_id);
    return candidate?.candidate_version === reference.candidate_version
      && candidate.content_digest === reference.content_digest;
  }) && ids.size === candidates.size;
}

async function responseError(response: Response): Promise<CompetencyFloorGovernanceError> {
  let message = `Request failed with status ${response.status}.`;
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string" && body.detail.trim()) message = body.detail;
  } catch {
    // Preserve the status fallback for non-JSON responses.
  }
  return new CompetencyFloorGovernanceError(message, response.status);
}

export async function fetchCompetencyFloorCandidates(
  apiBaseUrl: string,
  fetcher: typeof fetch = fetch,
): Promise<CompetencyFloorCandidateProjection> {
  const response = await fetcher(
    `${apiBaseUrl.replace(/\/$/, "")}/v1/operator/competency-floor-candidates`,
    {
      headers: authorizedHeaders(
        { Accept: "application/json" },
        reviewerDevelopmentAccessToken,
      ),
    },
  );
  if (!response.ok) throw await responseError(response);
  const body = (await response.json()) as Partial<CompetencyFloorCandidateProjection>;
  if (
    !body
    || !Array.isArray(body.items)
    || !body.items.every(isCandidateItem)
    || !isBatch(body.batch, body.items)
    || typeof body.projected_at !== "string"
    || typeof body.projection_version !== "string"
  ) {
    throw new CompetencyFloorGovernanceError(
      "Competency-floor candidate response is invalid.",
      response.status,
    );
  }
  return body as CompetencyFloorCandidateProjection;
}

export async function ratifyCompetencyFloorCandidate(
  apiBaseUrl: string,
  candidate: CompetencyFloorCandidate,
  fetcher: typeof fetch = fetch,
): Promise<unknown> {
  const response = await fetcher(
    `${apiBaseUrl.replace(/\/$/, "")}/v1/operator/competency-floor-candidates/`
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

export async function ratifyCompetencyFloorCandidateBatch(
  apiBaseUrl: string,
  batch: CompetencyFloorCandidateBatch,
  fetcher: typeof fetch = fetch,
): Promise<unknown> {
  const response = await fetcher(
    `${apiBaseUrl.replace(/\/$/, "")}/v1/operator/competency-floor-candidate-batches/ratifications`,
    {
      method: "POST",
      headers: authorizedHeaders(
        { Accept: "application/json", "Content-Type": "application/json" },
        reviewerDevelopmentAccessToken,
      ),
      body: JSON.stringify({ ...batch, approval_attestation: true }),
    },
  );
  if (!response.ok) throw await responseError(response);
  return response.json();
}
