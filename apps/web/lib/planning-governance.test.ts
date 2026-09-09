import { describe, expect, it, vi } from "vitest";

import {
  fetchPlanningGovernanceCandidates,
  PlanningGovernanceError,
  ratifyPlanningGovernanceCandidate,
  type PlanningGovernanceCandidate,
} from "./planning-governance";

const candidate: PlanningGovernanceCandidate = {
  candidate_version: "planning-governance-candidate@1.0.0",
  candidate_id: "98400000-0000-4000-8000-000000000001",
  slug: "owner_alpha_conservative_priority_policy",
  release_label: "Conservative owner-alpha priority policy",
  prepared_at: "2026-09-09T10:30:00Z",
  content_digest: `sha256:${"a".repeat(64)}`,
  summary: "Transparent policy.",
  governs: ["Ranking"],
  does_not_establish: ["Workout"],
  operational_choices: ["Two development targets"],
  unresolved_limitations: ["Heuristic values"],
  evidence: [{
    title: "Source",
    source_url: "https://pubmed.ncbi.nlm.nih.gov/41843416/",
    population: "Adults",
    finding: "Beneficial",
    limitations: ["Not a ranking study"],
    conflict_disclosure: "Pending full review",
  }],
};

describe("planning governance client", () => {
  it("loads a structurally valid prepared candidate", async () => {
    const fetcher = vi.fn(async () => new Response(JSON.stringify({
      projected_at: "2026-09-09T15:00:00Z",
      items: [{ candidate, status: "available", ratified_at: null, issues: [] }],
      projection_version: "planning-governance-candidates@1.0.0",
    }), { status: 200 }));

    const result = await fetchPlanningGovernanceCandidates(
      "http://localhost:8000/",
      fetcher as unknown as typeof fetch,
    );

    expect(result.items[0].candidate.candidate_id).toBe(candidate.candidate_id);
    expect(fetcher).toHaveBeenCalledWith(
      "http://localhost:8000/v1/operator/planning-governance/candidates",
      expect.any(Object),
    );
  });

  it("rejects a malformed response", async () => {
    const fetcher = vi.fn(async () => new Response(JSON.stringify({ items: [{}] }), {
      status: 200,
    }));

    await expect(
      fetchPlanningGovernanceCandidates(
        "http://localhost:8000",
        fetcher as unknown as typeof fetch,
      ),
    ).rejects.toEqual(new PlanningGovernanceError("Planning candidate response is invalid.", 200));
  });

  it("posts only the immutable identity, digest, and attestation", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), { status: 201 }),
    );

    await ratifyPlanningGovernanceCandidate(
      "http://localhost:8000",
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
