import { describe, expect, it, vi } from "vitest";

import {
  fetchFirstWeekPreparation,
  FirstWeekReviewError,
  submitFirstWeekPlan,
  validateWeeklyPlanRequest,
  type OperatorWeeklyPlanRequest,
} from "./first-week-review";

const id = "11111111-1111-4111-8111-111111111111";

function request(): OperatorWeeklyPlanRequest {
  return {
    prescriptions: [{
      resource_allocation_id: id,
      reason_for_inclusion: "Reviewed fixture dose.",
      sets: 3,
      repetitions_per_set: 5,
      intensity_targets: [{ kind: "effort_rpe", minimum: 6, maximum: 8 }],
      rest_seconds: 120,
      progression_rule_reference: "fixture-progression@1.0.0",
      substitution_class: "fixture-strength",
      planned_duration_minutes: 20,
      fatigue_cost: "moderate",
      source_observation_ids: [id],
      evidence_claim_ids: [id],
      rule_version: "fixture-prescription@1.0.0",
    }],
    session_templates: [{
      name: "Reviewed session",
      items: [{ resource_allocation_id: id, order_index: 1, section: "primary" }],
      sessions_per_week: 1,
      planned_duration_minutes: 20,
      fatigue_cost: "moderate",
      source_observation_ids: [id],
      evidence_claim_ids: [id],
      rule_version: "fixture-template@1.0.0",
    }],
    availability: {
      week_start: "2026-08-31",
      windows: [{
        environment_id: id,
        starts_at: "2026-08-31T12:00:00Z",
        ends_at: "2026-08-31T13:00:00Z",
      }],
      source_observation_ids: [id],
      rule_version: "fixture-availability@1.0.0",
    },
    scheduling_policy_id: id,
    scheduling_policy_review_id: "22222222-2222-4222-8222-222222222222",
    prepared_at: "2026-08-29T12:00:00Z",
    applicability_rationale: "Exact reviewed fixture inputs.",
    uncertainty: "Fixture only.",
  };
}

describe("first-week reviewer client", () => {
  it("rejects client-supplied reviewer authority", () => {
    expect(() => validateWeeklyPlanRequest({ ...request(), reviewed_by: "spoofed" } as never))
      .toThrow("reviewed_by is server-owned");
  });

  it("requires explicit prescriptions and composition", () => {
    expect(() => validateWeeklyPlanRequest({ ...request(), prescriptions: [] })).toThrow(
      "Prescriptions are required",
    );
    expect(() => validateWeeklyPlanRequest({ ...request(), session_templates: [] })).toThrow(
      "Session composition is required",
    );
  });

  it("validates dose shape, intensity, provenance, and session order", () => {
    const base = request();
    expect(() => validateWeeklyPlanRequest({
      ...base,
      prescriptions: [{
        ...base.prescriptions[0],
        duration_seconds: 30,
      }],
    })).toThrow("exactly one of repetitions or duration");
    expect(() => validateWeeklyPlanRequest({
      ...base,
      prescriptions: [{ ...base.prescriptions[0], intensity_targets: [] }],
    })).toThrow("at least one intensity target");
    expect(() => validateWeeklyPlanRequest({
      ...base,
      prescriptions: [{ ...base.prescriptions[0], source_observation_ids: [] }],
    })).toThrow("observations must not be empty");
    expect(() => validateWeeklyPlanRequest({
      ...base,
      session_templates: [{
        ...base.session_templates[0],
        items: [{ ...base.session_templates[0].items[0], order_index: 2 }],
      }],
    })).toThrow("item order must be contiguous");
  });

  it("loads the role-protected preparation projection", async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ block: { id } })));
    await fetchFirstWeekPreparation("http://localhost:8000/", id, fetcher);
    expect(fetcher).toHaveBeenCalledWith(
      `http://localhost:8000/v1/operator/blocks/${id}/first-week-preparation`,
      expect.objectContaining({ headers: expect.any(Object) }),
    );
  });

  it("posts only reviewed inputs to the authenticated boundary", async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ ok: true })));
    await submitFirstWeekPlan("http://localhost:8000", id, request(), fetcher);
    const init = fetcher.mock.calls[0][1] as RequestInit;
    expect(init.method).toBe("POST");
    expect(JSON.parse(String(init.body))).not.toHaveProperty("reviewed_by");
  });

  it("preserves server error detail", async () => {
    const fetcher = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "policy review was withdrawn" }), { status: 422 }),
    );
    await expect(fetchFirstWeekPreparation("http://localhost:8000", id, fetcher)).rejects.toEqual(
      new FirstWeekReviewError("policy review was withdrawn", 422),
    );
  });
});
