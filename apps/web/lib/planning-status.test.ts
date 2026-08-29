import { describe, expect, it, vi } from "vitest";

import { PlanningStatusRequestError, fetchPlanningStatus } from "./planning-status";

const athleteId = "00000000-0000-4000-8000-000000000001";

describe("planning status client", () => {
  it("loads the owned projection with the development identity", async () => {
    const projection = {
      athlete_id: athleteId,
      athlete_display_name: "Fixture athlete",
      as_of: "2026-08-27T12:00:00Z",
      status: "planning_context_review_required",
      message: "Reviewed athlete-specific planning context is required.",
      capability_estimate_count: 1,
      current_capability_estimate_count: 1,
      stale_capability_estimate_count: 0,
      approved_priority_policy_count: 1,
      approved_compatible_competency_floor_count: 1,
      covered_current_capability_estimate_count: 1,
      uncovered_current_capability_estimate_count: 0,
      requirements: [
        {
          code: "approved_priority_policy_required",
          label: "Current approved priority policy",
          satisfied: true,
          matching_record_count: 1,
        },
      ],
      initial_strategy: null,
      first_block_readiness: null,
      first_week_readiness: null,
      projection_version: "athlete-planning-status-projection@1.3.0",
    };
    const fetcher = vi
      .fn<typeof fetch>()
      .mockResolvedValue(new Response(JSON.stringify(projection), { status: 200 }));

    await expect(fetchPlanningStatus("http://localhost:8000/", athleteId, fetcher)).resolves.toEqual(
      projection,
    );
    expect(fetcher).toHaveBeenCalledWith(
      `http://localhost:8000/v1/athletes/${athleteId}/planning-status`,
      {
        headers: {
          Accept: "application/json",
          Authorization: "Bearer dev.local-browser",
        },
      },
    );
  });

  it("preserves API failure details", async () => {
    const fetcher = vi
      .fn<typeof fetch>()
      .mockResolvedValue(
        new Response(JSON.stringify({ detail: "athlete does not exist" }), { status: 404 }),
      );

    await expect(fetchPlanningStatus("http://localhost:8000", athleteId, fetcher)).rejects.toEqual(
      new PlanningStatusRequestError("athlete does not exist", 404),
    );
  });
});
