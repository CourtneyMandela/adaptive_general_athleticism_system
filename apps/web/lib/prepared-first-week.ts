import { authorizedHeaders, reviewerDevelopmentAccessToken } from "./identity";
import type { WeeklyPlanCreationResult } from "./first-week-review";

const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const digestPattern = /^sha256:[0-9a-f]{64}$/;

export interface PreparedAvailabilityWindow {
  environment_id: string;
  starts_at: string;
  ends_at: string;
}

export interface PreparedFirstWeekCandidate {
  candidate_version: "prepared-first-week@1.0.0";
  candidate_id: string;
  content_digest: string;
  prepared_at: string;
  status: "available" | "accepted";
  athlete_id: string;
  block_id: string;
  week_start: string;
  exercise_name: string;
  environment_name: string;
  sessions: Array<{ starts_at: string; ends_at: string }>;
  sets: number;
  repetitions_per_set: number;
  rest_seconds: number;
  effort_rpe_range: string;
  planned_duration_minutes: number;
  technique_constraints: string[];
  dose_calculation: string;
  provenance_summary: string;
  uncertainty: string;
  safety_boundary: string;
  accepted_result: WeeklyPlanCreationResult | null;
}

export interface PreparedFirstWeekProjection {
  block_id: string;
  athlete_id: string | null;
  projected_at: string;
  status: "available" | "blocked" | "accepted";
  message: string;
  candidate: PreparedFirstWeekCandidate | null;
  blockers: string[];
  projection_version: string;
}

export interface PreparedFirstWeekRatificationResult {
  candidate_id: string;
  candidate_content_digest: string;
  created: boolean;
  result: WeeklyPlanCreationResult;
}

export class PreparedFirstWeekError extends Error {
  constructor(message: string, readonly status?: number) {
    super(message);
    this.name = "PreparedFirstWeekError";
  }
}

function assertUuid(value: string, label: string): void {
  if (!uuidPattern.test(value)) throw new PreparedFirstWeekError(`${label} must be a UUID.`);
}

function validateWindows(windows: PreparedAvailabilityWindow[]): void {
  if (!windows.length) throw new PreparedFirstWeekError("Offer at least one training time.");
  windows.forEach((window, index) => {
    assertUuid(window.environment_id, `Training time ${index + 1} environment`);
    const start = Date.parse(window.starts_at);
    const end = Date.parse(window.ends_at);
    if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start) {
      throw new PreparedFirstWeekError(`Training time ${index + 1} must have a valid start and end.`);
    }
  });
}

async function responseError(response: Response): Promise<PreparedFirstWeekError> {
  let message = `Request failed with status ${response.status}.`;
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string" && body.detail.trim()) message = body.detail;
  } catch {
    // Preserve the status-based message for non-JSON failures.
  }
  return new PreparedFirstWeekError(message, response.status);
}

function baseUrl(value: string): string {
  return value.replace(/\/$/, "");
}

export async function prepareFirstWeek(
  apiBaseUrl: string,
  blockId: string,
  windows: PreparedAvailabilityWindow[],
  fetcher: typeof fetch = fetch,
): Promise<PreparedFirstWeekProjection> {
  assertUuid(blockId, "Block ID");
  validateWindows(windows);
  const response = await fetcher(
    `${baseUrl(apiBaseUrl)}/v1/operator/blocks/${encodeURIComponent(blockId)}/prepared-first-week`,
    {
      method: "POST",
      headers: authorizedHeaders(
        { Accept: "application/json", "Content-Type": "application/json" },
        reviewerDevelopmentAccessToken,
      ),
      body: JSON.stringify({ windows }),
    },
  );
  if (!response.ok) throw await responseError(response);
  return (await response.json()) as PreparedFirstWeekProjection;
}

export async function ratifyPreparedFirstWeek(
  apiBaseUrl: string,
  blockId: string,
  candidate: PreparedFirstWeekCandidate,
  windows: PreparedAvailabilityWindow[],
  fetcher: typeof fetch = fetch,
): Promise<PreparedFirstWeekRatificationResult> {
  assertUuid(blockId, "Block ID");
  assertUuid(candidate.candidate_id, "Candidate ID");
  validateWindows(windows);
  if (!digestPattern.test(candidate.content_digest)) {
    throw new PreparedFirstWeekError("Candidate digest is invalid.");
  }
  const response = await fetcher(
    `${baseUrl(apiBaseUrl)}/v1/operator/blocks/${encodeURIComponent(blockId)}`
      + `/prepared-first-weeks/${encodeURIComponent(candidate.candidate_id)}/ratifications`,
    {
      method: "POST",
      headers: authorizedHeaders(
        { Accept: "application/json", "Content-Type": "application/json" },
        reviewerDevelopmentAccessToken,
      ),
      body: JSON.stringify({
        candidate_version: candidate.candidate_version,
        content_digest: candidate.content_digest,
        prepared_at: candidate.prepared_at,
        windows,
        approval_attestation: true,
      }),
    },
  );
  if (!response.ok) throw await responseError(response);
  return (await response.json()) as PreparedFirstWeekRatificationResult;
}
