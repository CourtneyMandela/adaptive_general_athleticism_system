import { describe, expect, it, vi } from "vitest";

import {
  fetchPreparedInitialPlanningContext,
  ratifyPreparedInitialPlanningContext,
  type PreparedInitialPlanningContextCandidate,
} from "./prepared-planning-context";

const candidate = {
  candidate_version: "prepared-initial-planning-context@1.0.0",
  candidate_id: "10000000-0000-4000-8000-000000000001",
  content_digest: `sha256:${"a".repeat(64)}`,
} as PreparedInitialPlanningContextCandidate;

describe("prepared initial-planning context client", () => {
  it("loads the athlete-specific prepared context", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({
        athlete_id: "20000000-0000-4000-8000-000000000001",
        projected_at: "2026-09-10T12:00:00Z",
        status: "blocked",
        message: "Approve the exact policy.",
        candidate: null,
        blockers: ["Policy required."],
        projection_version: "prepared-initial-planning-context-projection@1.0.0",
      }), { status: 200 }),
    );

    const result = await fetchPreparedInitialPlanningContext(
      "http://localhost:8000/",
      "20000000-0000-4000-8000-000000000001",
      fetcher,
    );

    expect(result.status).toBe("blocked");
    expect(fetcher.mock.calls[0][0]).toContain("prepared-initial-planning-context");
  });

  it("ratifies only the immutable candidate identity, digest, and attestation", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ created: true }), { status: 201 }),
    );

    await ratifyPreparedInitialPlanningContext(
      "http://localhost:8000",
      "20000000-0000-4000-8000-000000000001",
      candidate,
      fetcher,
    );

    const request = fetcher.mock.calls[0][1] as RequestInit;
    expect(JSON.parse(request.body as string)).toEqual({
      candidate_version: candidate.candidate_version,
      content_digest: candidate.content_digest,
      approval_attestation: true,
    });
  });
});
