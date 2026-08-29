import { authorizedHeaders } from "./identity";
import type { Confidence } from "./current-week";

export type CapabilitySeriesStatus = "current" | "stale";
export type CapabilityDomainStatus = "not_estimated" | "current" | "stale" | "mixed";

export interface CapabilitySeriesProjection {
  estimate_id: string;
  kind: "derived";
  estimate_scope: string;
  estimate: unknown;
  unit_or_scale: string;
  confidence: Confidence;
  status: CapabilitySeriesStatus;
  calculation_method: string;
  source_observation_ids: string[];
  estimated_at: string;
  valid_until: string | null;
  rule_version: string;
  historical_estimate_count: number;
}

export interface CapabilityDomainProjection {
  domain: string;
  status: CapabilityDomainStatus;
  latest_estimates: CapabilitySeriesProjection[];
  historical_estimate_count: number;
}

export interface AthleticDashboardProjection {
  athlete_id: string;
  athlete_display_name: string;
  as_of: string;
  domains: CapabilityDomainProjection[];
  estimated_domain_count: number;
  unestimated_domain_count: number;
  projection_version: string;
}

export class AthleticDashboardRequestError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "AthleticDashboardRequestError";
  }
}

export async function fetchAthleticDashboard(
  apiBaseUrl: string,
  athleteId: string,
  fetcher: typeof fetch = fetch,
): Promise<AthleticDashboardProjection> {
  const response = await fetcher(
    `${apiBaseUrl.replace(/\/$/, "")}/v1/athletes/${encodeURIComponent(athleteId)}/dashboard`,
    { headers: authorizedHeaders({ Accept: "application/json" }) },
  );
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new AthleticDashboardRequestError(
      payload?.detail ?? `Athletic dashboard request failed with ${response.status}.`,
      response.status,
    );
  }
  return (await response.json()) as AthleticDashboardProjection;
}

export function capabilityDomainLabel(domain: string): string {
  return domain
    .split("_")
    .map((part) => `${part.slice(0, 1).toUpperCase()}${part.slice(1)}`)
    .join(" ");
}

export function capabilityValueLabel(value: unknown, unitOrScale: string): string {
  const rendered =
    typeof value === "number" || typeof value === "string" ? String(value) : JSON.stringify(value);
  return `${rendered} ${unitOrScale}`.trim();
}
