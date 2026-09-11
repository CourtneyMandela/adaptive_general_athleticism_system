import { describe, expect, it, vi } from "vitest";

import {
  fetchPreparedFirstBlock,
  ratifyPreparedFirstBlock,
  type PreparedFirstBlockCandidate,
} from "./prepared-first-block";

const strategyId = "11111111-1111-4111-8111-111111111111";
const candidate: PreparedFirstBlockCandidate = {
  candidate_version: "prepared-first-block@1.0.0",
  candidate_id: "22222222-2222-4222-8222-222222222222",
  content_digest: `sha256:${"a".repeat(64)}`,
  prepared_at: "2026-09-11T12:00:00Z",
  status: "available",
  athlete_id: "33333333-3333-4333-8333-333333333333",
  strategy_id: strategyId,
  starts_on: "2026-09-14",
  ends_on: "2026-10-11",
  duration_weeks: 4,
  weekly_budget_minutes: 10,
  resource_demand_ids: ["44444444-4444-4444-8444-444444444444"],
  resource_allocation_policy_id: "55555555-5555-4555-8555-555555555555",
  expected_status: "full",
  expected_allocations: [{
    adaptation_id: "66666666-6666-4666-8666-666666666666",
    priority_state: "develop",
    allocated_weekly_minutes: 10,
    sessions_per_week: 2,
    status: "full",
  }],
  construction_basis: "Exact governed resource envelope.",
  applicability_rationale: "This athlete and strategy only.",
  uncertainty: "No session is created.",
  safety_boundary: "A safety gate remains required.",
  identities: {
    block_plan_id: "77777777-7777-4777-8777-777777777777",
    resource_allocation_ids: ["88888888-8888-4888-8888-888888888888"],
    decision_record_id: "99999999-9999-4999-8999-999999999999",
  },
  accepted_result: null,
};

describe("prepared first block transport", () => {
  it("loads the candidate for the explicit start date", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ status: "available", candidate }), { status: 200 }),
    );

    await fetchPreparedFirstBlock("https://api.example.test/", strategyId, candidate.starts_on, fetcher);

    expect(fetcher.mock.calls[0][0]).toContain("starts_on=2026-09-14");
    expect(fetcher.mock.calls[0][1]?.headers).toMatchObject({ Accept: "application/json" });
  });

  it("ratifies only the exact digest, version, date, and attestation", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ created: true, result: {} }), { status: 201 }),
    );

    await ratifyPreparedFirstBlock("https://api.example.test", strategyId, candidate, fetcher);

    expect(JSON.parse(String(fetcher.mock.calls[0][1]?.body))).toEqual({
      candidate_version: candidate.candidate_version,
      content_digest: candidate.content_digest,
      starts_on: candidate.starts_on,
      approval_attestation: true,
    });
  });
});
