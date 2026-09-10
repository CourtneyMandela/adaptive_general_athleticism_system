import { describe, expect, it, vi } from "vitest";

import {
  fetchResourceGovernanceCandidates,
  ratifyResourceGovernanceCandidate,
  type ResourceGovernanceCandidate,
} from "./resource-governance";

const candidate: ResourceGovernanceCandidate = {
  candidate_version: "resource-governance-candidate@1.0.0",
  candidate_id: "98600000-0000-4000-8000-000000000001",
  content_digest: `sha256:${"a".repeat(64)}`,
  prepared_at: "2026-09-10T17:00:00Z",
  release_label: "First owner-alpha resource authorities",
  summary: "Exact prepared resources.",
  exact_artifacts: ["Exercise: Chair sit-to-stand"],
  governs: ["Exact ontology and policy records."],
  does_not_establish: ["A workout."],
  operational_choices: ["Full matches only."],
  unresolved_limitations: ["Dose remains separate."],
  evidence: [{
    title: "ACSM",
    source_url: "https://example.test/source",
    population: "Healthy adults.",
    finding: "Resistance training improves function.",
    limitations: ["No exact dose."],
  }],
};

describe("resource governance client", () => {
  it("loads a validated candidate projection", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(new Response(JSON.stringify({
      projected_at: "2026-09-10T18:00:00Z",
      items: [{ candidate, status: "available", ratified_at: null, issues: [] }],
      projection_version: "resource-governance-candidates@1.0.0",
    }), { status: 200, headers: { "Content-Type": "application/json" } }));

    const result = await fetchResourceGovernanceCandidates("https://agas.test/", fetcher);

    expect(result.items[0].candidate.release_label).toContain("resource authorities");
    expect(fetcher).toHaveBeenCalledWith(
      "https://agas.test/v1/operator/resource-governance/candidates",
      expect.objectContaining({ headers: expect.any(Object) }),
    );
  });

  it("ratifies only the exact version, digest, and attestation", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(new Response("{}", {
      status: 201,
      headers: { "Content-Type": "application/json" },
    }));

    await ratifyResourceGovernanceCandidate("https://agas.test", candidate, fetcher);

    const init = fetcher.mock.calls[0][1] as RequestInit;
    expect(JSON.parse(String(init.body))).toEqual({
      candidate_version: candidate.candidate_version,
      content_digest: candidate.content_digest,
      approval_attestation: true,
    });
  });
});
