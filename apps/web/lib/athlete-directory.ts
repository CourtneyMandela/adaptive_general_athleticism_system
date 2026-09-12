import { isUuid } from "./current-week";
import { authorizedHeaders } from "./identity";

export interface OwnedEnvironmentSummary {
  environment_id: string;
  name: string;
}

export interface OwnedAthleteSummary {
  athlete_id: string;
  display_name: string;
  profile_created_at: string;
  goals: string[];
  environments: OwnedEnvironmentSummary[];
  ownership_granted_at: string;
  ownership_rule_version: string;
}

export interface OwnedAthleteDirectory {
  projection_version: string;
  athletes: OwnedAthleteSummary[];
}

export class AthleteDirectoryRequestError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "AthleteDirectoryRequestError";
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isEnvironment(value: unknown): value is OwnedEnvironmentSummary {
  return (
    isRecord(value) &&
    typeof value.environment_id === "string" &&
    isUuid(value.environment_id) &&
    typeof value.name === "string" &&
    value.name.length > 0
  );
}

function isAthlete(value: unknown): value is OwnedAthleteSummary {
  return (
    isRecord(value) &&
    typeof value.athlete_id === "string" &&
    isUuid(value.athlete_id) &&
    typeof value.display_name === "string" &&
    value.display_name.length > 0 &&
    typeof value.profile_created_at === "string" &&
    Number.isFinite(Date.parse(value.profile_created_at)) &&
    Array.isArray(value.goals) &&
    value.goals.every((item) => typeof item === "string" && item.length > 0) &&
    Array.isArray(value.environments) &&
    value.environments.every(isEnvironment) &&
    typeof value.ownership_granted_at === "string" &&
    Number.isFinite(Date.parse(value.ownership_granted_at)) &&
    typeof value.ownership_rule_version === "string" &&
    value.ownership_rule_version.length > 0
  );
}

function isDirectory(value: unknown): value is OwnedAthleteDirectory {
  return (
    isRecord(value) &&
    value.projection_version === "account-athlete-directory@1.0.0" &&
    Array.isArray(value.athletes) &&
    value.athletes.every(isAthlete)
  );
}

async function responseDetail(response: Response, fallback: string): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    return typeof body.detail === "string" ? body.detail : fallback;
  } catch {
    return fallback;
  }
}

export async function fetchOwnedAthleteDirectory(
  apiBaseUrl: string,
  fetcher: typeof fetch = fetch,
): Promise<OwnedAthleteDirectory> {
  const response = await fetcher(`${apiBaseUrl.replace(/\/$/, "")}/v1/athletes`, {
    headers: authorizedHeaders({ Accept: "application/json" }),
    cache: "no-store",
  });
  if (!response.ok) {
    throw new AthleteDirectoryRequestError(
      await responseDetail(response, "Unable to recover your athlete profiles."),
      response.status,
    );
  }
  const payload: unknown = await response.json();
  if (!isDirectory(payload)) {
    throw new AthleteDirectoryRequestError("The athlete profile directory is invalid.", 502);
  }
  return payload;
}
