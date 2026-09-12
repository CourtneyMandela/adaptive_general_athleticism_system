import { authorizedHeaders } from "./identity";

export interface AthleteExportTable {
  table_name: string;
  primary_key_columns: string[];
  rows: Record<string, unknown>[];
}

export interface AthleteExportExternalReference {
  source_table: string;
  source_column: string;
  target_table: string;
  target_column: string;
  target_value: unknown;
}

export interface AthleteDataExport {
  export_version: string;
  generated_at: string;
  athlete_id: string;
  tables: AthleteExportTable[];
  external_references: AthleteExportExternalReference[];
  manifest: {
    record_count: number;
    table_counts: Record<string, number>;
    content_digest: string;
    scope: string;
    restore_status: string;
  };
}

export class AthleteDataExportRequestError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "AthleteDataExportRequestError";
  }
}

function isAthleteDataExport(value: unknown): value is AthleteDataExport {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<AthleteDataExport>;
  return (
    typeof candidate.export_version === "string" &&
    typeof candidate.generated_at === "string" &&
    typeof candidate.athlete_id === "string" &&
    Array.isArray(candidate.tables) &&
    Array.isArray(candidate.external_references) &&
    !!candidate.manifest &&
    typeof candidate.manifest.record_count === "number" &&
    /^sha256:[0-9a-f]{64}$/.test(candidate.manifest.content_digest)
  );
}

export async function fetchAthleteDataExport(
  apiBaseUrl: string,
  athleteId: string,
  fetcher: typeof fetch = fetch,
): Promise<AthleteDataExport> {
  const response = await fetcher(
    `${apiBaseUrl.replace(/\/$/, "")}/v1/athletes/${encodeURIComponent(athleteId)}/data-export`,
    { headers: authorizedHeaders({ Accept: "application/json" }) },
  );
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new AthleteDataExportRequestError(
      payload?.detail ?? `Data export request failed with ${response.status}.`,
      response.status,
    );
  }
  const payload: unknown = await response.json();
  if (!isAthleteDataExport(payload) || payload.athlete_id !== athleteId) {
    throw new AthleteDataExportRequestError("The server returned an invalid athlete export.", 502);
  }
  return payload;
}

export function athleteDataExportFilename(payload: AthleteDataExport): string {
  const date = payload.generated_at.slice(0, 10);
  const safeDate = /^\d{4}-\d{2}-\d{2}$/.test(date) ? date : "undated";
  return `agas-athlete-data-${safeDate}-${payload.athlete_id}.json`;
}
