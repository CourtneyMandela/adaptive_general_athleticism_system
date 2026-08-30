import { describe, expect, it, vi } from "vitest";

import {
  ResourceDemandReviewError,
  fetchResourceDemandPreparation,
  submitResourceDemand,
  validateResourceDemandRequest,
  type OperatorActiveResourceDemandRequest,
  type OperatorDeferredResourceDemandRequest,
  type OperatorResourceDemandRequest,
} from "./resource-demand-review";

const strategyId = "11111111-1111-4111-8111-111111111111";
const priorityId = "22222222-2222-4222-8222-222222222222";
const environmentId = "33333333-3333-4333-8333-333333333333";
const resolverPolicyId = "44444444-4444-4444-8444-444444444444";
const exerciseId = "55555555-5555-4555-8555-555555555555";
const observationId = "66666666-6666-4666-8666-666666666666";
const evidenceId = "77777777-7777-4777-8777-777777777777";

const activeRequest: OperatorActiveResourceDemandRequest = {
  mode: "active",
  environment_id: environmentId,
  exercise_candidate_ids: [exerciseId],
  exercise_resolver_policy_id: resolverPolicyId,
  stimulus_specification: {
    movement_patterns: ["knee_dominant"],
    allowed_loading_types: ["external_load"],
    allowed_lateralities: ["bilateral"],
    minimum_loadability: "moderate",
    required_velocity_characteristics: ["controlled"],
    maximum_skill_complexity: "moderate",
    maximum_impact_level: "low",
    maximum_stability_demand: "moderate",
    maximum_fatigue_cost: "moderate",
    maximum_soreness_cost: "moderate",
    requires_outdoor_access: false,
    minimum_floor_area_m2: 4,
    contraindication_tags: ["reviewed_constraint"],
    source_observation_ids: [observationId],
    evidence_claim_ids: [evidenceId],
    rationale: "The reviewer explicitly selected this stimulus boundary.",
  },
  minimum_weekly_minutes: 60,
  target_weekly_minutes: 90,
  sessions_per_week: 3,
  prepared_at: "2026-08-29T12:00:00Z",
  applicability_rationale: "The reviewed inputs apply to this synthetic fixture.",
  uncertainty: "This fixture makes no scientific claim.",
  demand_rationale: "The resource amount is an explicit reviewed fixture value.",
  demand_version: "reviewed-demand@1.0.0",
};

const deferredRequest: OperatorDeferredResourceDemandRequest = {
  mode: "deferred",
  source_observation_ids: [observationId],
  evidence_claim_ids: [evidenceId],
  prepared_at: "2026-08-29T12:00:00+00:00",
  applicability_rationale: "The reviewed inputs apply to this synthetic fixture.",
  uncertainty: "This fixture makes no scientific claim.",
  demand_rationale: "The priority is intentionally assigned no current resource.",
  demand_version: "reviewed-defer@1.0.0",
};

describe("resource-demand reviewer client", () => {
  it("loads the exact preparation projection through reviewer authorization", async () => {
    const projection = { strategy: { id: strategyId }, priorities: [] };
    const fetcher = vi
      .fn<typeof fetch>()
      .mockResolvedValue(new Response(JSON.stringify(projection), { status: 200 }));

    await expect(
      fetchResourceDemandPreparation("http://localhost:8000/", strategyId, fetcher),
    ).resolves.toEqual(projection);
    expect(fetcher).toHaveBeenCalledWith(
      `http://localhost:8000/v1/operator/strategies/${strategyId}/resource-demand-preparation`,
      {
        headers: {
          Accept: "application/json",
          Authorization: "Bearer dev.local-browser",
        },
      },
    );
  });

  it("submits the exact explicit demand without client-authored reviewer identity", async () => {
    const result = {
      stimulus_requirement: { id: "stimulus" },
      exercise_resolution: { id: "resolution", status: "full" },
      resource_demand: { id: "demand" },
      decision_record: { id: "decision" },
    };
    const fetcher = vi
      .fn<typeof fetch>()
      .mockResolvedValue(new Response(JSON.stringify(result), { status: 201 }));

    await expect(
      submitResourceDemand(
        "http://localhost:8000/",
        strategyId,
        priorityId,
        activeRequest,
        fetcher,
      ),
    ).resolves.toEqual(result);
    const options = fetcher.mock.calls[0]?.[1];
    expect(fetcher.mock.calls[0]?.[0]).toBe(
      `http://localhost:8000/v1/operator/strategies/${strategyId}/priorities/${priorityId}/resource-demands`,
    );
    expect(options).toMatchObject({
      method: "POST",
      headers: {
        Accept: "application/json",
        Authorization: "Bearer dev.local-browser",
        "Content-Type": "application/json",
      },
    });
    expect(JSON.parse(options?.body as string)).toEqual(activeRequest);
    expect(JSON.parse(options?.body as string)).not.toHaveProperty("reviewed_by");
    expect(JSON.parse(options?.body as string)).not.toHaveProperty(
      "review_authority_assignment_id",
    );
  });

  it("accepts an explicit zero-resource deferred decision with provenance", () => {
    expect(() => validateResourceDemandRequest(deferredRequest)).not.toThrow();
  });

  it("rejects reviewer spoofing and incomplete or internally inconsistent active inputs", () => {
    expect(() =>
      validateResourceDemandRequest({
        ...activeRequest,
        reviewed_by: "forged reviewer",
      } as unknown as OperatorResourceDemandRequest),
    ).toThrow("reviewed_by is server-owned");
    expect(() =>
      validateResourceDemandRequest({
        ...activeRequest,
        exercise_candidate_ids: [],
      }),
    ).toThrow("Exercise candidates requires at least one selection");
    expect(() =>
      validateResourceDemandRequest({
        ...activeRequest,
        target_weekly_minutes: 91,
      }),
    ).toThrow("divide evenly");
    expect(() =>
      validateResourceDemandRequest({
        ...activeRequest,
        stimulus_specification: {
          ...activeRequest.stimulus_specification,
          rationale: " ",
        },
      }),
    ).toThrow("Stimulus rationale must not be blank");
  });

  it("rejects unsupported controlled values before making the request", () => {
    expect(() =>
      validateResourceDemandRequest({
        ...activeRequest,
        stimulus_specification: {
          ...activeRequest.stimulus_specification,
          maximum_fatigue_cost: "unsupported" as "moderate",
        },
      }),
    ).toThrow("Maximum fatigue cost must be a supported controlled value");
  });

  it("preserves server validation detail so the reviewer can correct the input", async () => {
    const fetcher = vi
      .fn<typeof fetch>()
      .mockResolvedValue(
        new Response(JSON.stringify({ detail: "exact current resolver policy required" }), {
          status: 422,
        }),
      );

    await expect(
      submitResourceDemand(
        "http://localhost:8000",
        strategyId,
        priorityId,
        activeRequest,
        fetcher,
      ),
    ).rejects.toEqual(
      new ResourceDemandReviewError("exact current resolver policy required", 422),
    );
  });
});
