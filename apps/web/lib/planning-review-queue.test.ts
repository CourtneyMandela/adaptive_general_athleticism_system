import { describe, expect, it, vi } from "vitest";

import {
  PlanningReviewQueueError,
  fetchPlanningReviewQueue,
  planningReviewHref,
  type PlanningReviewQueueItem,
} from "./planning-review-queue";

const athleteId = "11111111-1111-4111-8111-111111111111";
const strategyId = "22222222-2222-4222-8222-222222222222";
const blockId = "33333333-3333-4333-8333-333333333333";

function item(
  workflow_stage: PlanningReviewQueueItem["workflow_stage"],
): PlanningReviewQueueItem {
  return {
    workflow_stage,
    status: `ready_for_explicit_${workflow_stage}`,
    readiness: "ready",
    athlete_id: athleteId,
    athlete_display_name: "Fixture athlete",
    strategy_id: workflow_stage === "initial_planning" ? null : strategyId,
    block_id: workflow_stage === "first_week" ? blockId : null,
    message: "Inspect exact persisted inputs.",
    issues: [],
  };
}

describe("planning review queue client", () => {
  it("loads the queue through reviewer authorization", async () => {
    const projection = {
      projected_at: "2026-08-30T12:00:00Z",
      items: [item("initial_planning")],
      projection_version: "planning-review-queue@1.0.0",
    };
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify(projection), { status: 200 }),
    );

    await expect(fetchPlanningReviewQueue("http://localhost:8000/", fetcher)).resolves.toEqual(
      projection,
    );
    expect(fetcher).toHaveBeenCalledWith(
      "http://localhost:8000/v1/operator/planning-review-queue",
      { headers: { Accept: "application/json", Authorization: "Bearer dev.local-browser" } },
    );
  });

  it("creates deterministic deep links for every workflow stage", () => {
    expect(planningReviewHref(item("initial_planning"))).toBe(`/review?athleteId=${athleteId}`);
    expect(planningReviewHref(item("resource_demands"))).toBe(
      `/review/resource-demands?strategyId=${strategyId}`,
    );
    expect(planningReviewHref(item("block_creation"))).toBe(
      `/review/blocks?strategyId=${strategyId}`,
    );
    expect(planningReviewHref(item("first_week"))).toBe(`/review/weeks?blockId=${blockId}`);
  });

  it("rejects malformed contracts and missing stage lineage", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ items: [{ unexpected: true }] }), { status: 200 }),
    );
    await expect(fetchPlanningReviewQueue("http://localhost:8000", fetcher)).rejects.toEqual(
      new PlanningReviewQueueError("Planning review queue response is invalid.", 200),
    );
    expect(() => planningReviewHref({ ...item("first_week"), block_id: null })).toThrow(
      "First-week work lacks a block ID.",
    );
  });
});
