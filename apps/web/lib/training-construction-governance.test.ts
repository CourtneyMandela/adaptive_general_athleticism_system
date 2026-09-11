import { describe, expect, it, vi } from "vitest";

import {
  fetchTrainingConstructionCandidates,
  ratifyTrainingConstructionCandidate,
  type TrainingConstructionCandidate,
} from "./training-construction-governance";

const candidate: TrainingConstructionCandidate = {
  candidate_version: "training-construction-candidate@1.0.0",
  candidate_id: "98900000-0000-4000-8000-000000000001",
  slug: "owner_alpha_chair_stand_construction_authorities",
  release_label: "Owner-alpha chair-stand construction authorities",
  prepared_at: "2026-09-11T11:00:00Z",
  content_digest: `sha256:${"a".repeat(64)}`,
  summary: "One atomic construction batch.",
  authority_basis: {
    scientific_support: "Broad direction only.",
    engineering_prior: "Exact constants are engineering priors.",
  },
  exact_artifacts: ["Dose policy", "Progression policy"],
  governs: ["Bounded first-session construction."],
  does_not_establish: ["Medical clearance."],
  unresolved_limitations: ["Personal calibration remains future work."],
  evidence: [{
    claim_id: "91000000-0000-4000-8000-000000000005",
    title: "ACSM",
    source_url: "https://example.test/source",
    supported_use: "Resistance-training direction.",
    unsupported_specifics: "No exact dose values.",
  }],
};

describe("training construction governance client", () => {
  it("loads a validated batch projection", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(new Response(JSON.stringify({
      projected_at: "2026-09-11T12:00:00Z",
      items: [{ candidate, status: "available", ratified_at: null, issues: [] }],
      projection_version: "training-construction-candidates@1.0.0",
    }), { status: 200, headers: { "Content-Type": "application/json" } }));

    const result = await fetchTrainingConstructionCandidates("https://agas.test/", fetcher);

    expect(result.items[0].candidate.exact_artifacts).toHaveLength(2);
    expect(fetcher).toHaveBeenCalledWith(
      "https://agas.test/v1/operator/training-construction-candidates",
      expect.objectContaining({ headers: expect.any(Object) }),
    );
  });

  it("ratifies the whole exact batch with one attestation", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(new Response("{}", {
      status: 201,
      headers: { "Content-Type": "application/json" },
    }));

    await ratifyTrainingConstructionCandidate("https://agas.test", candidate, fetcher);

    const init = fetcher.mock.calls[0][1] as RequestInit;
    expect(JSON.parse(String(init.body))).toEqual({
      candidate_version: candidate.candidate_version,
      content_digest: candidate.content_digest,
      approval_attestation: true,
    });
  });
});
