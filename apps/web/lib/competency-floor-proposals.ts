import { authorizedHeaders, reviewerDevelopmentAccessToken } from "./identity";

export interface CompetencyFloorProposalSource {
  source_id: string;
  title: string;
  authors: string[];
  edition: string;
  publisher: string;
  publication_year: number;
  isbn13: string;
  table_locator: string;
  page_locator: string;
  source_population: string;
  reported_value: string;
  source_role: "direct_reference" | "derived_reference" | "context_only";
  limitations: string[];
}

export interface CompetencyFloorProposal {
  proposal_version: "competency-floor-proposal@1.0.0";
  proposal_id: string;
  slug: string;
  label: string;
  prepared_at: string;
  content_digest: string;
  stage: "proposal_only";
  domain: string;
  estimate_scope: string;
  measurement: string;
  unit_or_scale: string;
  threshold: number;
  comparison_direction: "higher_is_better" | "lower_is_better";
  minimum_age_years: number;
  maximum_age_years: number;
  sex_scope: "male_reference" | "female_reference" | "sex_neutral";
  numeric_value_origin:
    | "direct_textbook_reference"
    | "derived_from_textbook_reference"
    | "engineering_proposal_without_numeric_evidence";
  operational_use_origin:
    | "evidence_informed_engineering_proposal"
    | "professional_judgment_required";
  threshold_rationale: string;
  population_match: "high" | "moderate" | "low";
  population_match_notes: string;
  source_ids: string[];
  evidence_gap: string;
  prerequisites_before_release: string[];
  does_not_establish: string[];
  review_questions: string[];
}

export interface CompetencyFloorProposalBatch {
  batch_version: "competency-floor-proposal-batch@1.0.0";
  batch_id: string;
  label: string;
  prepared_at: string;
  content_digest: string;
  source_catalog: CompetencyFloorProposalSource[];
  proposals: CompetencyFloorProposal[];
  release_boundary: string;
}

export class CompetencyFloorProposalError extends Error {
  constructor(message: string, readonly status?: number) {
    super(message);
    this.name = "CompetencyFloorProposalError";
  }
}

function validSource(value: unknown): value is CompetencyFloorProposalSource {
  if (!value || typeof value !== "object") return false;
  const source = value as Partial<CompetencyFloorProposalSource>;
  return typeof source.source_id === "string"
    && typeof source.title === "string"
    && typeof source.isbn13 === "string"
    && /^\d{13}$/.test(source.isbn13)
    && typeof source.table_locator === "string"
    && typeof source.source_population === "string"
    && Array.isArray(source.limitations);
}

function validProposal(value: unknown, sourceIds: Set<string>): value is CompetencyFloorProposal {
  if (!value || typeof value !== "object") return false;
  const proposal = value as Partial<CompetencyFloorProposal>;
  return proposal.proposal_version === "competency-floor-proposal@1.0.0"
    && proposal.stage === "proposal_only"
    && typeof proposal.proposal_id === "string"
    && typeof proposal.label === "string"
    && typeof proposal.threshold === "number"
    && ["higher_is_better", "lower_is_better"].includes(proposal.comparison_direction ?? "")
    && ["high", "moderate", "low"].includes(proposal.population_match ?? "")
    && Array.isArray(proposal.source_ids)
    && proposal.source_ids.every((id) => sourceIds.has(id))
    && Array.isArray(proposal.prerequisites_before_release)
    && Array.isArray(proposal.does_not_establish)
    && Array.isArray(proposal.review_questions)
    && typeof proposal.content_digest === "string"
    && proposal.content_digest.startsWith("sha256:");
}

export async function fetchCompetencyFloorProposals(
  apiBaseUrl: string,
  fetcher: typeof fetch = fetch,
): Promise<CompetencyFloorProposalBatch> {
  const response = await fetcher(
    `${apiBaseUrl.replace(/\/$/, "")}/v1/operator/competency-floor-proposals`,
    {
      headers: authorizedHeaders(
        { Accept: "application/json" },
        reviewerDevelopmentAccessToken,
      ),
    },
  );
  if (!response.ok) {
    let message = `Request failed with status ${response.status}.`;
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === "string" && body.detail.trim()) message = body.detail;
    } catch {
      // Preserve the status fallback for non-JSON responses.
    }
    throw new CompetencyFloorProposalError(message, response.status);
  }
  const body = (await response.json()) as Partial<CompetencyFloorProposalBatch>;
  const sources = Array.isArray(body.source_catalog) ? body.source_catalog : [];
  const sourceIds = new Set(sources.filter(validSource).map((source) => source.source_id));
  if (
    body.batch_version !== "competency-floor-proposal-batch@1.0.0"
    || typeof body.batch_id !== "string"
    || typeof body.content_digest !== "string"
    || !body.content_digest.startsWith("sha256:")
    || sources.length === 0
    || sourceIds.size !== sources.length
    || !Array.isArray(body.proposals)
    || body.proposals.length === 0
    || !body.proposals.every((proposal) => validProposal(proposal, sourceIds))
    || typeof body.release_boundary !== "string"
  ) {
    throw new CompetencyFloorProposalError("Competency-floor proposal response is invalid.", response.status);
  }
  return body as CompetencyFloorProposalBatch;
}
