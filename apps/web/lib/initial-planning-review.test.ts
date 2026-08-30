import { describe, expect, it, vi } from "vitest";

import {
  InitialPlanningReviewError,
  createInitialPlanningContextDraft,
  createInitialStrategyFromContextReview,
  fetchInitialPlanningPreparation,
  parseInitialStrategyDraft,
  reviewInitialPlanningContextDraft,
  submitInitialStrategy,
  type InitialPlanningContextDraftRequest,
  type OperatorInitialStrategyRequest,
} from "./initial-planning-review";

const athleteId = "11111111-1111-4111-8111-111111111111";
const policyId = "22222222-2222-4222-8222-222222222222";
const policyReviewId = "33333333-3333-4333-8333-333333333333";
const adaptationId = "44444444-4444-4444-8444-444444444444";
const floorId = "55555555-5555-4555-8555-555555555555";
const floorReviewId = "66666666-6666-4666-8666-666666666666";
const estimateId = "77777777-7777-4777-8777-777777777777";
const observationId = "88888888-8888-4888-8888-888888888888";
const evidenceId = "99999999-9999-4999-8999-999999999999";

const request: OperatorInitialStrategyRequest = {
  priority_policy_id: policyId,
  priority_policy_review_id: policyReviewId,
  candidate_contexts: [
    {
      adaptation_id: adaptationId,
      competency_floor_id: floorId,
      competency_floor_review_id: floorReviewId,
      capability_estimate_id: estimateId,
      general_relevance: 0.8,
      goal_relevance: 0.7,
      prerequisite_value: 0.6,
      expected_trainability: 0.5,
      transfer_value: 0.8,
      fatigue_cost: 0.3,
      time_cost: 0.2,
      interference_cost: 0.1,
      safe_to_train: true,
      introductory_exposure_needed: false,
      prerequisites_met: true,
      prerequisite_adaptation_ids: [],
      cultivate_comparative_advantage: false,
      source_observation_ids: [observationId],
      evidence_claim_ids: [evidenceId],
    },
  ],
  generated_at: "2026-08-29T12:00:00Z",
  horizon_months: 12,
  review_after_days: 42,
  applicability_rationale: "The reviewed inputs apply to this synthetic fixture.",
  uncertainty: "This fixture makes no scientific claim.",
};

describe("initial planning reviewer client", () => {
  it("normalizes a complete explicit document without inventing authority", () => {
    const parsed = parseInitialStrategyDraft(JSON.stringify(request));

    expect(parsed).toEqual(request);
    expect(parsed).not.toHaveProperty("reviewed_by");
    expect(parsed).not.toHaveProperty("review_authority_assignment_id");
  });

  it("rejects reviewer spoofing, unsupported values, and duplicate adaptations", () => {
    expect(() =>
      parseInitialStrategyDraft(JSON.stringify({ ...request, reviewed_by: "forged" })),
    ).toThrow("unsupported field(s): reviewed_by");
    expect(() =>
      parseInitialStrategyDraft(
        JSON.stringify({
          ...request,
          candidate_contexts: [{ ...request.candidate_contexts[0], fatigue_cost: 1.2 }],
        }),
      ),
    ).toThrow("fatigue_cost must be a number from 0 to 1");
    expect(() =>
      parseInitialStrategyDraft(
        JSON.stringify({
          ...request,
          candidate_contexts: [request.candidate_contexts[0], request.candidate_contexts[0]],
        }),
      ),
    ).toThrow("each adaptation exactly once");
  });

  it("submits the exact request with the configured reviewer authorization", async () => {
    const response = {
      capability_needs: [],
      strategy: { id: "strategy" },
      decision_record: { id: "decision" },
    };
    const fetcher = vi
      .fn<typeof fetch>()
      .mockResolvedValue(new Response(JSON.stringify(response), { status: 201 }));

    await expect(
      submitInitialStrategy("http://localhost:8000/", athleteId, request, fetcher),
    ).resolves.toEqual(response);
    expect(fetcher).toHaveBeenCalledWith(
      `http://localhost:8000/v1/operator/athletes/${athleteId}/initial-strategies`,
      expect.objectContaining({ method: "POST" }),
    );
    const options = fetcher.mock.calls[0]?.[1];
    expect(options?.headers).toMatchObject({
      Authorization: "Bearer dev.local-browser",
      "Content-Type": "application/json",
    });
    expect(JSON.parse(options?.body as string)).toEqual(request);
  });

  it("preserves server validation failures for reviewer correction", async () => {
    const fetcher = vi
      .fn<typeof fetch>()
      .mockResolvedValue(
        new Response(JSON.stringify({ detail: "exact current review required" }), { status: 422 }),
      );

    await expect(
      submitInitialStrategy("http://localhost:8000", athleteId, request, fetcher),
    ).rejects.toEqual(
      new InitialPlanningReviewError("exact current review required", 422),
    );
  });

  it("loads preparation inputs through the reviewer authority boundary", async () => {
    const projection = {
      athlete_id: athleteId,
      status: "planning_context_review_required",
      estimate_options: [],
      stale_estimates: [],
      priority_policy_options: [],
      evidence_claims: [],
    };
    const fetcher = vi
      .fn<typeof fetch>()
      .mockResolvedValue(new Response(JSON.stringify(projection), { status: 200 }));

    await expect(
      fetchInitialPlanningPreparation("http://localhost:8000/", athleteId, fetcher),
    ).resolves.toEqual(projection);
    expect(fetcher).toHaveBeenCalledWith(
      `http://localhost:8000/v1/operator/athletes/${athleteId}/initial-planning-preparation`,
      {
        headers: {
          Accept: "application/json",
          Authorization: "Bearer dev.local-browser",
        },
      },
    );
  });

  it("uses separate authenticated boundaries for draft, review, and strategy creation", async () => {
    const { generated_at: generatedAt, ...draftFields } = request;
    const draftRequest: InitialPlanningContextDraftRequest = {
      ...draftFields,
      authored_at: generatedAt,
    };
    const draft = { ...draftRequest, id: floorId };
    const review = { id: policyReviewId, draft_id: floorId, decision: "approved" };
    const result = { strategy: { id: adaptationId } };
    const fetcher = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(new Response(JSON.stringify(draft), { status: 201 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(review), { status: 201 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(result), { status: 201 }));

    await expect(
      createInitialPlanningContextDraft(
        "http://localhost:8000/",
        athleteId,
        draftRequest,
        fetcher,
      ),
    ).resolves.toEqual(draft);
    await expect(
      reviewInitialPlanningContextDraft(
        "http://localhost:8000/",
        floorId,
        {
          decision: "approved",
          reviewed_at: "2026-08-29T12:01:00Z",
          applicability_rationale: "Exact draft approved.",
          uncertainty: "Fixture uncertainty.",
        },
        fetcher,
      ),
    ).resolves.toEqual(review);
    await expect(
      createInitialStrategyFromContextReview(
        "http://localhost:8000/",
        policyReviewId,
        "2026-08-29T12:02:00Z",
        fetcher,
      ),
    ).resolves.toEqual(result);

    expect(fetcher.mock.calls.map(([url]) => url)).toEqual([
      `http://localhost:8000/v1/operator/athletes/${athleteId}/initial-planning-context-drafts`,
      `http://localhost:8000/v1/operator/initial-planning-context-drafts/${floorId}/reviews`,
      `http://localhost:8000/v1/operator/initial-planning-context-reviews/${policyReviewId}/strategy`,
    ]);
    for (const [, options] of fetcher.mock.calls) {
      expect(options?.headers).toMatchObject({
        Authorization: "Bearer dev.local-browser",
        "Content-Type": "application/json",
      });
    }
  });
});
