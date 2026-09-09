import { authorizedHeaders } from "./identity";

export interface AthleteDemographicsProjection {
  athlete_id: string;
  as_of: string;
  date_of_birth: string | null;
  age_years: number | null;
  source_observation_id: string | null;
  source_kind: "reported_observation" | "legacy_profile" | "unknown";
  report_count: number;
  message: string;
  projection_version: string;
}

export interface DateOfBirthReportResult {
  observation_id: string;
  demographics: AthleteDemographicsProjection;
  created: boolean;
  rule_version: string;
}

export class AthleteDemographicsRequestError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "AthleteDemographicsRequestError";
  }
}

async function requireResponse<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new AthleteDemographicsRequestError(
      payload?.detail ?? `${fallback} (${response.status}).`,
      response.status,
    );
  }
  return (await response.json()) as T;
}

export async function fetchAthleteDemographics(
  apiBaseUrl: string,
  athleteId: string,
  fetcher: typeof fetch = fetch,
): Promise<AthleteDemographicsProjection> {
  const response = await fetcher(
    `${apiBaseUrl.replace(/\/$/, "")}/v1/athletes/${encodeURIComponent(athleteId)}/demographics`,
    { headers: authorizedHeaders({ Accept: "application/json" }) },
  );
  return requireResponse(response, "Demographics request failed");
}

export async function submitDateOfBirthReport(
  apiBaseUrl: string,
  athleteId: string,
  dateOfBirth: string,
  fetcher: typeof fetch = fetch,
): Promise<DateOfBirthReportResult> {
  const response = await fetcher(
    `${apiBaseUrl.replace(/\/$/, "")}/v1/athletes/${encodeURIComponent(athleteId)}/date-of-birth-reports`,
    {
      method: "POST",
      headers: authorizedHeaders({
        Accept: "application/json",
        "Content-Type": "application/json",
      }),
      body: JSON.stringify({
        report_id: crypto.randomUUID(),
        date_of_birth: dateOfBirth,
        reported_at: new Date().toISOString(),
        date_of_birth_confirmed: true,
      }),
    },
  );
  return requireResponse(response, "Date-of-birth report failed");
}
