import { describe, expect, it, vi } from "vitest";

import {
  fetchPlanningAuthorityBatchState,
  PlanningAuthorityBatchError,
  ratifyAvailablePlanningAuthorityBatch,
  type PlanningAuthorityBatchOperations,
} from "./planning-authority-batch";

function item(status: string, id: string) {
  return { status, candidate: { candidate_id: id } };
}

function operations(): PlanningAuthorityBatchOperations {
  let planningRatified = false;
  let floorRatified = false;
  let resourceRatified = false;
  let constructionRatified = false;
  return {
    fetchPlanning: vi.fn(async () => ({
      items: [item(planningRatified ? "ratified" : "available", "planning")],
    })) as unknown as PlanningAuthorityBatchOperations["fetchPlanning"],
    ratifyPlanning: vi.fn(async () => {
      planningRatified = true;
    }),
    fetchFloors: vi.fn(async () => ({
      items: [item(floorRatified ? "ratified" : "available", "floor")],
      batch: { batch_id: "floors" },
    })) as unknown as PlanningAuthorityBatchOperations["fetchFloors"],
    ratifyFloorBatch: vi.fn(async () => {
      floorRatified = true;
    }),
    fetchResources: vi.fn(async () => ({
      items: [item(resourceRatified ? "ratified" : "available", "resource")],
    })) as unknown as PlanningAuthorityBatchOperations["fetchResources"],
    ratifyResource: vi.fn(async () => {
      resourceRatified = true;
    }),
    fetchConstruction: vi.fn(async () => ({
      items: [item(
        constructionRatified ? "ratified" : resourceRatified ? "available" : "blocked",
        "construction",
      )],
    })) as unknown as PlanningAuthorityBatchOperations["fetchConstruction"],
    ratifyConstruction: vi.fn(async () => {
      constructionRatified = true;
    }),
  };
}

describe("planning-authority batch", () => {
  it("reports exact available, blocked, and ratified groups", async () => {
    await expect(fetchPlanningAuthorityBatchState("http://api", operations())).resolves.toEqual({
      available_group_count: 3,
      blocked_group_count: 1,
      conflict_group_count: 0,
      ratified_group_count: 0,
    });
  });

  it("ratifies dependency-ordered groups and rechecks construction after resources", async () => {
    const api = operations();
    const result = await ratifyAvailablePlanningAuthorityBatch("http://api", api);

    expect(result.approved_group_count).toBe(4);
    expect(result.remaining).toEqual({
      available_group_count: 0,
      blocked_group_count: 0,
      conflict_group_count: 0,
      ratified_group_count: 4,
    });
    expect(api.ratifyPlanning).toHaveBeenCalledTimes(1);
    expect(api.ratifyFloorBatch).toHaveBeenCalledTimes(1);
    expect(api.ratifyResource).toHaveBeenCalledTimes(1);
    expect(api.ratifyConstruction).toHaveBeenCalledTimes(1);
    expect(vi.mocked(api.fetchConstruction).mock.invocationCallOrder.at(-2)).toBeLessThan(
      vi.mocked(api.ratifyConstruction).mock.invocationCallOrder[0],
    );
  });

  it("makes a conflict a no-write batch failure", async () => {
    const api = operations();
    vi.mocked(api.fetchPlanning).mockResolvedValue({
      items: [item("conflict", "planning")],
    } as never);

    await expect(ratifyAvailablePlanningAuthorityBatch("http://api", api)).rejects.toEqual(
      new PlanningAuthorityBatchError(
        "Resolve the conflicting authority before using batch approval.",
        0,
      ),
    );
    expect(api.ratifyPlanning).not.toHaveBeenCalled();
    expect(api.ratifyFloorBatch).not.toHaveBeenCalled();
    expect(api.ratifyResource).not.toHaveBeenCalled();
    expect(api.ratifyConstruction).not.toHaveBeenCalled();
  });

  it("reports already-completed groups when a later independent save fails", async () => {
    const api = operations();
    vi.mocked(api.ratifyResource).mockRejectedValue(new Error("resource save stopped"));

    await expect(ratifyAvailablePlanningAuthorityBatch("http://api", api)).rejects.toEqual(
      new PlanningAuthorityBatchError("resource save stopped", 2),
    );
    expect(api.ratifyPlanning).toHaveBeenCalledTimes(1);
    expect(api.ratifyFloorBatch).toHaveBeenCalledTimes(1);
    expect(api.ratifyConstruction).not.toHaveBeenCalled();
  });
});
