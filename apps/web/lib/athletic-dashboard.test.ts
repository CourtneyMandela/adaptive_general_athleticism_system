import { describe, expect, it, vi } from "vitest";

import {
  AthleticDashboardRequestError,
  capabilityDomainLabel,
  capabilityValueLabel,
  fetchAthleticDashboard,
  type AthleticDashboardProjection,
} from "./athletic-dashboard";

const athleteId = "00000000-0000-4000-8000-000000000001";

const projection: AthleticDashboardProjection = {
  athlete_id: athleteId,
  athlete_display_name: "Fixture athlete",
  as_of: "2026-08-28T16:00:00Z",
  estimated_domain_count: 1,
  unestimated_domain_count: 16,
  projection_version: "athletic-dashboard-projection@1.0.0",
  domains: [
    {
      domain: "maximum_strength",
      status: "current",
      historical_estimate_count: 2,
      latest_estimates: [
        {
          estimate_id: "00000000-0000-4000-8000-000000000002",
          kind: "derived",
          estimate_scope: "assessment_specific:trap_bar_3rm",
          estimate: 90,
          unit_or_scale: "kg",
          confidence: "moderate",
          status: "current",
          calculation_method: "fixture method",
          source_observation_ids: ["00000000-0000-4000-8000-000000000003"],
          estimated_at: "2026-08-27T16:00:00Z",
          valid_until: "2026-09-27T16:00:00Z",
          rule_version: "fixture@1.0.0",
          historical_estimate_count: 2,
        },
      ],
    },
  ],
};

describe("athletic dashboard client", () => {
  it("loads the owned provenance projection with development authorization", async () => {
    const fetcher = vi.fn(async () => new Response(JSON.stringify(projection), { status: 200 }));

    await expect(fetchAthleticDashboard("http://localhost:8000/", athleteId, fetcher)).resolves.toEqual(
      projection,
    );
    expect(fetcher).toHaveBeenCalledWith(
      `http://localhost:8000/v1/athletes/${athleteId}/dashboard`,
      {
        headers: {
          Accept: "application/json",
          Authorization: "Bearer dev.local-browser",
        },
      },
    );
  });

  it("preserves backend failure detail", async () => {
    const fetcher = vi.fn(
      async () => new Response(JSON.stringify({ detail: "athlete does not exist" }), { status: 404 }),
    );

    await expect(fetchAthleticDashboard("http://localhost:8000", athleteId, fetcher)).rejects.toEqual(
      new AthleticDashboardRequestError("athlete does not exist", 404),
    );
  });

  it("formats domain and heterogeneous values without inventing a normalized score", () => {
    expect(capabilityDomainLabel("repeated_effort_capacity")).toBe("Repeated Effort Capacity");
    expect(capabilityValueLabel(90, "kg")).toBe("90 kg");
    expect(capabilityValueLabel({ category: "stable" }, "ordinal")).toBe(
      '{"category":"stable"} ordinal',
    );
  });
});
