import { describe, expect, it, vi } from "vitest";

import {
  prepareFirstWeek,
  ratifyPreparedFirstWeek,
  type PreparedAvailabilityWindow,
  type PreparedFirstWeekCandidate,
} from "./prepared-first-week";

const blockId = "11111111-1111-4111-8111-111111111111";
const windows: PreparedAvailabilityWindow[] = [{
  environment_id: "22222222-2222-4222-8222-222222222222",
  starts_at: "2026-09-15T18:00:00.000Z",
  ends_at: "2026-09-15T18:30:00.000Z",
}];
const candidate = {
  candidate_version: "prepared-first-week@1.1.0",
  candidate_id: "33333333-3333-4333-8333-333333333333",
  content_digest: `sha256:${"a".repeat(64)}`,
  prepared_at: "2026-09-11T18:00:00Z",
  block_id: blockId,
} as PreparedFirstWeekCandidate;

describe("prepared first week transport", () => {
  it("submits only factual availability for preview", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ status: "blocked", blockers: [] }), { status: 200 }),
    );

    await prepareFirstWeek("https://api.example.test/", blockId, windows, fetcher);

    expect(JSON.parse(String(fetcher.mock.calls[0][1]?.body))).toEqual({ windows });
  });

  it("binds the exact preview time, digest, windows, and attestation", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ created: true, result: {} }), { status: 201 }),
    );

    await ratifyPreparedFirstWeek("https://api.example.test", blockId, candidate, windows, fetcher);

    expect(JSON.parse(String(fetcher.mock.calls[0][1]?.body))).toEqual({
      candidate_version: candidate.candidate_version,
      content_digest: candidate.content_digest,
      prepared_at: candidate.prepared_at,
      windows,
      approval_attestation: true,
    });
  });
});
