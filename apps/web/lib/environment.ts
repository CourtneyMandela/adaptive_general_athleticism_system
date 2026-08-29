import type { Confidence, ProvenanceInput } from "./current-week";
import { authorizedHeaders } from "./identity";

export type EquipmentState = "available" | "unavailable" | "unknown";

export interface EnvironmentEquipmentProjection {
  equipment_id: string;
  name: string;
  category: string;
  state: EquipmentState;
  availability_event_id: string | null;
  source_observation_id: string | null;
  effective_from: string | null;
  effective_until: string | null;
  capabilities: Record<string, unknown>;
  load_limits: Record<string, unknown>;
  reason: string | null;
}

export interface EnvironmentStateProjection {
  environment_id: string;
  name: string;
  floor_area_m2: number | null;
  noise_constraints: string | null;
  max_noise_level: "low" | "moderate" | "high";
  outdoor_access: boolean;
  equipment: EnvironmentEquipmentProjection[];
}

export interface AthleteEnvironmentProjection {
  athlete_id: string;
  as_of: string;
  environments: EnvironmentStateProjection[];
  projection_version: string;
}

export interface EquipmentStateChangeInput {
  equipmentId: string;
  isAvailable: boolean;
  effectiveFrom: Date;
  effectiveUntil: Date | null;
  reason: string | null;
}

export interface EquipmentStateReportCommand {
  changes: Array<{
    equipment_id: string;
    is_available: boolean;
    effective_from: string;
    effective_until: string | null;
    capabilities: Record<string, never>;
    load_limits: Record<string, never>;
    reason: string | null;
  }>;
  reported_at: string;
  reliability: Confidence;
  provenance: ProvenanceInput;
  report_reason: string;
}

export const equipmentReportProvenance: ProvenanceInput = {
  recorded_by: "unverified-athlete-user",
  source_system: "agas-web",
  ingestion_method: "equipment-state-form",
};

export class EnvironmentRequestError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "EnvironmentRequestError";
  }
}

function isUuid(value: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(
    value,
  );
}

async function responseDetail(response: Response, fallback: string): Promise<string> {
  const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
  return payload?.detail ?? fallback;
}

export async function fetchAthleteEnvironments(
  apiBaseUrl: string,
  athleteId: string,
  fetcher: typeof fetch = fetch,
): Promise<AthleteEnvironmentProjection> {
  const response = await fetcher(
    `${apiBaseUrl.replace(/\/$/, "")}/v1/athletes/${encodeURIComponent(athleteId)}/environments`,
    { headers: authorizedHeaders({ Accept: "application/json" }) },
  );
  if (!response.ok) {
    throw new EnvironmentRequestError(
      await responseDetail(response, `Environment request failed with ${response.status}.`),
      response.status,
    );
  }
  return (await response.json()) as AthleteEnvironmentProjection;
}

export function buildEquipmentStateReportCommand({
  changes,
  reliability,
  reportReason,
  reportedAt = new Date(),
}: {
  changes: EquipmentStateChangeInput[];
  reliability: Confidence;
  reportReason: string;
  reportedAt?: Date;
}): EquipmentStateReportCommand {
  if (changes.length === 0) throw new Error("Choose at least one equipment change.");
  if (!Number.isFinite(reportedAt.getTime())) throw new Error("Report time must be valid.");
  const normalizedReason = reportReason.trim();
  if (!normalizedReason) throw new Error("Explain why the equipment state is changing.");
  const equipmentIds = changes.map((change) => change.equipmentId);
  if (new Set(equipmentIds).size !== equipmentIds.length) {
    throw new Error("Equipment changes must not contain duplicates.");
  }
  return {
    changes: changes.map((change) => {
      if (!isUuid(change.equipmentId)) throw new Error("Equipment selection must be valid.");
      if (!Number.isFinite(change.effectiveFrom.getTime())) {
        throw new Error("Equipment change start must be valid.");
      }
      if (
        change.effectiveUntil !== null &&
        (!Number.isFinite(change.effectiveUntil.getTime()) ||
          change.effectiveUntil <= change.effectiveFrom)
      ) {
        throw new Error("Temporary equipment state must end after it starts.");
      }
      return {
        equipment_id: change.equipmentId,
        is_available: change.isAvailable,
        effective_from: change.effectiveFrom.toISOString(),
        effective_until: change.effectiveUntil?.toISOString() ?? null,
        capabilities: {},
        load_limits: {},
        reason: change.reason?.trim() || null,
      };
    }),
    reported_at: reportedAt.toISOString(),
    reliability,
    provenance: equipmentReportProvenance,
    report_reason: normalizedReason,
  };
}

export async function submitEquipmentStateReport(
  apiBaseUrl: string,
  athleteId: string,
  environmentId: string,
  command: EquipmentStateReportCommand,
  fetcher: typeof fetch = fetch,
): Promise<{ observation: { id: string }; availability_events: Array<{ id: string }> }> {
  const response = await fetcher(
    `${apiBaseUrl.replace(/\/$/, "")}/v1/athletes/${encodeURIComponent(athleteId)}` +
      `/environments/${encodeURIComponent(environmentId)}/equipment-reports`,
    {
      method: "POST",
      headers: authorizedHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(command),
    },
  );
  if (!response.ok) {
    throw new EnvironmentRequestError(
      await responseDetail(response, `Equipment report failed with ${response.status}.`),
      response.status,
    );
  }
  return (await response.json()) as {
    observation: { id: string };
    availability_events: Array<{ id: string }>;
  };
}
