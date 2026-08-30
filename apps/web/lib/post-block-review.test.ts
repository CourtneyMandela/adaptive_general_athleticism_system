import { describe, expect, it, vi } from "vitest";

import {
  PostBlockReviewError,
  fetchBlockReviewPreparation,
  fetchPostBlockReviewQueue,
  fetchReplanningPreparation,
  submitBlockReview,
  submitReplanning,
  validateBlockReviewRequest,
  validateReplanningRequest,
  type OperatorBlockReviewRequest,
  type OperatorReplanningRequest,
} from "./post-block-review";

const blockId = "11111111-1111-4111-8111-111111111111";
const reviewId = "22222222-2222-4222-8222-222222222222";
const policyId = "33333333-3333-4333-8333-333333333333";
const adaptationId = "44444444-4444-4444-8444-444444444444";
const prescriptionId = "55555555-5555-4555-8555-555555555555";
const baselineId = "66666666-6666-4666-8666-666666666666";
const followupId = "77777777-7777-4777-8777-777777777777";
const floorId = "88888888-8888-4888-8888-888888888888";

const reviewRequest: OperatorBlockReviewRequest = {
  block_review_policy_id: policyId,
  response_drafts: [{
    adaptation_id: adaptationId,
    prescription_ids: [prescriptionId],
    baseline_capability_estimate_id: baselineId,
    followup_capability_estimate_id: followupId,
    intervention_summary: "Reviewed delivered strength intervention.",
    measurement_uncertainty: "Field-test uncertainty remains material.",
    contextual_factors: ["travel week"],
    comparison_direction: "higher_is_better",
    minimum_meaningful_change: 5,
  }],
  responses_calculated_at: "2026-08-30T12:00:00Z",
  reviewed_at: "2026-08-30T12:01:00Z",
  applicability_rationale: "Interpret the exact completed block history.",
  uncertainty: "Observed change does not establish causality.",
};

const replanningRequest: OperatorReplanningRequest = {
  candidate_contexts: [{
    adaptation_id: adaptationId,
    competency_floor_id: floorId,
    capability_estimate_id: followupId,
    general_relevance: 0.8,
    goal_relevance: 0.7,
    prerequisite_value: 0.6,
    expected_trainability: 0.5,
    transfer_value: 0.8,
    fatigue_cost: 0.3,
    time_cost: 0.4,
    interference_cost: 0.2,
    safe_to_train: true,
    introductory_exposure_needed: false,
    prerequisites_met: true,
    prerequisite_adaptation_ids: [],
    cultivate_comparative_advantage: false,
    source_observation_ids: [],
    evidence_claim_ids: [],
  }],
  generated_at: "2026-08-30T12:02:00Z",
  review_after_days: 42,
  applicability_rationale: "Revise priorities from the reviewed response.",
  uncertainty: "Future response remains uncertain.",
};

describe("post-block reviewer client", () => {
  it("loads both preparation projections through reviewer authorization", async () => {
    const fetcher = vi.fn<typeof fetch>()
      .mockResolvedValueOnce(new Response(JSON.stringify({
        projected_at: "2026-08-30T12:00:00Z",
        items: [],
        projection_version: "post-block-review-queue@1.0.0",
      }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ block: { id: blockId } }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ block_review: { id: reviewId } }), { status: 200 }));

    await fetchPostBlockReviewQueue("http://localhost:8000/", fetcher);
    await fetchBlockReviewPreparation("http://localhost:8000/", blockId, fetcher);
    await fetchReplanningPreparation("http://localhost:8000/", reviewId, fetcher);

    expect(fetcher.mock.calls.map(([url]) => url)).toEqual([
      "http://localhost:8000/v1/operator/post-block-review-queue",
      `http://localhost:8000/v1/operator/blocks/${blockId}/review-preparation`,
      `http://localhost:8000/v1/operator/block-reviews/${reviewId}/replanning-preparation`,
    ]);
    expect(fetcher.mock.calls[0]?.[1]).toEqual({
      headers: { Accept: "application/json", Authorization: "Bearer dev.local-browser" },
    });
  });

  it("submits both decisions without client-authored reviewer identity", async () => {
    const fetcher = vi.fn<typeof fetch>()
      .mockResolvedValueOnce(new Response(JSON.stringify({ block_review: { id: reviewId } }), { status: 201 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ strategy: { id: blockId } }), { status: 201 }));

    await submitBlockReview("http://localhost:8000", blockId, reviewRequest, fetcher);
    await submitReplanning("http://localhost:8000", reviewId, replanningRequest, fetcher);

    for (const [, options] of fetcher.mock.calls) {
      expect(options).toMatchObject({
        method: "POST",
        headers: {
          Accept: "application/json",
          Authorization: "Bearer dev.local-browser",
          "Content-Type": "application/json",
        },
      });
      const body = JSON.parse(options?.body as string);
      expect(body).not.toHaveProperty("reviewed_by");
      expect(body).not.toHaveProperty("review_authority_assignment_id");
    }
  });

  it("rejects spoofing, duplicate response assignments, and invalid timing", () => {
    expect(() => validateBlockReviewRequest({
      ...reviewRequest,
      reviewed_by: "forged",
    } as unknown as OperatorBlockReviewRequest)).toThrow("reviewed_by is server-owned");
    expect(() => validateBlockReviewRequest({
      ...reviewRequest,
      response_drafts: [reviewRequest.response_drafts[0], reviewRequest.response_drafts[0]],
    })).toThrow("Response adaptations must not contain duplicates");
    expect(() => validateBlockReviewRequest({
      ...reviewRequest,
      reviewed_at: "2026-08-30T11:59:00Z",
    })).toThrow("cannot predate");
  });

  it("rejects incomplete or invalid successor-strategy contexts", () => {
    expect(() => validateReplanningRequest({
      ...replanningRequest,
      candidate_contexts: [{ ...replanningRequest.candidate_contexts[0], transfer_value: 1.1 }],
    })).toThrow("between zero and one");
    expect(() => validateReplanningRequest({
      ...replanningRequest,
      candidate_contexts: [
        replanningRequest.candidate_contexts[0],
        replanningRequest.candidate_contexts[0],
      ],
    })).toThrow("Candidate adaptations must not contain duplicates");
    expect(() => validateReplanningRequest({
      ...replanningRequest,
      review_after_days: 0,
    })).toThrow("positive integer");
  });

  it("preserves backend validation detail", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ detail: "every block week requires an execution" }), {
        status: 422,
      }),
    );

    await expect(
      submitBlockReview("http://localhost:8000", blockId, reviewRequest, fetcher),
    ).rejects.toEqual(
      new PostBlockReviewError("every block week requires an execution", 422),
    );
  });

  it("rejects a stale or malformed queue contract without crashing the page", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ block: { id: blockId } }), { status: 200 }),
    );

    await expect(fetchPostBlockReviewQueue("http://localhost:8000", fetcher)).rejects.toEqual(
      new PostBlockReviewError("Post-block review queue response is invalid.", 200),
    );
  });
});
