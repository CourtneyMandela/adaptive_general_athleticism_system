import { describe, expect, it, vi } from "vitest";

import {
  fetchPreparedResourceDemands,
  ratifyPreparedResourceDemand,
  type PreparedResourceDemandCandidate,
} from "./prepared-resource-demand";

const candidate = {
  candidate_version: "prepared-resource-demand@1.0.0",
  candidate_id: "10000000-0000-4000-8000-000000000001",
  content_digest: `sha256:${"a".repeat(64)}`,
} as PreparedResourceDemandCandidate;

describe("prepared resource-demand client", () => {
  it("loads the exact strategy-specific candidates", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ status: "blocked", blockers: ["Report a chair."] }), {
        status: 200,
      }),
    );

    const result = await fetchPreparedResourceDemands(
      "http://localhost:8000/",
      "20000000-0000-4000-8000-000000000001",
      fetcher,
    );

    expect(result.status).toBe("blocked");
    expect(fetcher.mock.calls[0][0]).toContain("prepared-resource-demands");
  });

  it("ratifies only the content identity and attestation", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ created: true }), { status: 201 }),
    );

    await ratifyPreparedResourceDemand(
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
