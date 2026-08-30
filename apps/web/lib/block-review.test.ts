import { describe, expect, it, vi } from "vitest";

import {
  BlockReviewError,
  fetchBlockPreparation,
  submitBlockPlan,
  validateBlockPlanRequest,
  type OperatorBlockPlanRequest,
} from "./block-review";

const strategyId = "11111111-1111-4111-8111-111111111111";
const demandId = "22222222-2222-4222-8222-222222222222";
const policyId = "33333333-3333-4333-8333-333333333333";

const request: OperatorBlockPlanRequest = {
  resource_demand_ids: [demandId],
  resource_allocation_policy_id: policyId,
  weekly_budget_minutes: 120,
  starts_on: "2026-08-31",
  duration_weeks: 4,
  constraints: ["Reviewed synthetic schedule constraint"],
  generated_at: "2026-08-29T12:00:00Z",
  applicability_rationale: "The exact reviewed demand history applies to this fixture.",
  uncertainty: "This fixture makes no scientific claim.",
};

describe("block reviewer client", () => {
  it("loads exact block-preparation inputs through reviewer authorization", async () => {
    const projection = { strategy: { id: strategyId }, priorities: [] };
    const fetcher = vi
      .fn<typeof fetch>()
      .mockResolvedValue(new Response(JSON.stringify(projection), { status: 200 }));

    await expect(
      fetchBlockPreparation("http://localhost:8000/", strategyId, fetcher),
    ).resolves.toEqual(projection);
    expect(fetcher).toHaveBeenCalledWith(
      `http://localhost:8000/v1/operator/strategies/${strategyId}/block-preparation`,
      {
        headers: {
          Accept: "application/json",
          Authorization: "Bearer dev.local-browser",
        },
      },
    );
  });

  it("submits exact context without client-authored reviewer identity", async () => {
    const result = { block_plan: { id: "block" }, decision_record: { id: "decision" } };
    const fetcher = vi
      .fn<typeof fetch>()
      .mockResolvedValue(new Response(JSON.stringify(result), { status: 201 }));

    await expect(
      submitBlockPlan("http://localhost:8000/", strategyId, request, fetcher),
    ).resolves.toEqual(result);
    const options = fetcher.mock.calls[0]?.[1];
    expect(fetcher.mock.calls[0]?.[0]).toBe(
      `http://localhost:8000/v1/operator/strategies/${strategyId}/blocks`,
    );
    expect(options).toMatchObject({
      method: "POST",
      headers: {
        Accept: "application/json",
        Authorization: "Bearer dev.local-browser",
        "Content-Type": "application/json",
      },
    });
    expect(JSON.parse(options?.body as string)).toEqual(request);
    expect(JSON.parse(options?.body as string)).not.toHaveProperty("reviewed_by");
    expect(JSON.parse(options?.body as string)).not.toHaveProperty(
      "review_authority_assignment_id",
    );
  });

  it("rejects identity spoofing, duplicate history, and invalid block context", () => {
    expect(() =>
      validateBlockPlanRequest({
        ...request,
        reviewed_by: "forged",
      } as unknown as OperatorBlockPlanRequest),
    ).toThrow("reviewed_by is server-owned");
    expect(() =>
      validateBlockPlanRequest({
        ...request,
        resource_demand_ids: [demandId, demandId],
      }),
    ).toThrow("must not contain duplicates");
    expect(() => validateBlockPlanRequest({ ...request, duration_weeks: 3 })).toThrow(
      "four to six weeks",
    );
    expect(() =>
      validateBlockPlanRequest({ ...request, starts_on: "2026-02-30" }),
    ).toThrow("real calendar date");
    expect(() =>
      validateBlockPlanRequest({
        ...request,
        constraints: ["same", "same"],
      }),
    ).toThrow("Constraints must not contain duplicates");
  });

  it("preserves server validation detail for reviewer correction", async () => {
    const fetcher = vi
      .fn<typeof fetch>()
      .mockResolvedValue(
        new Response(JSON.stringify({ detail: "one demand per priority required" }), {
          status: 422,
        }),
      );

    await expect(
      submitBlockPlan("http://localhost:8000", strategyId, request, fetcher),
    ).rejects.toEqual(new BlockReviewError("one demand per priority required", 422));
  });
});
