import { describe, expect, it, vi } from "vitest";

import {
  CompetencyFloorGovernanceError,
  fetchCompetencyFloorCandidates,
  ratifyCompetencyFloorCandidateBatch,
  ratifyCompetencyFloorCandidate,
  type CompetencyFloorCandidateBatch,
  type CompetencyFloorCandidate,
} from "./competency-floor-governance";

const candidate: CompetencyFloorCandidate = {
  candidate_version: "competency-floor-candidate@1.1.0",
  candidate_id: "98400000-0000-4000-8000-000000000002",
  slug: "chair_stand_age_30_39_lower_reference_floor",
  release_label: "Age 30-39 chair-stand lower-reference floor",
  prepared_at: "2026-09-09T00:10:00Z",
  content_digest: `sha256:${"a".repeat(64)}`,
  summary: "Provisional lower reference.",
  authority_basis: {
    numeric_value_origin: "direct_study_result",
    operational_use_origin: "evidence_informed_engineering_judgment",
    numeric_value_explanation: "The number is reported directly.",
    operational_use_explanation: "Its use as a floor is provisional engineering judgment.",
  },
  domain: "muscular_endurance",
  estimate_scope: "assessment_specific:thirty_second_chair_stand_repetitions",
  unit_or_scale: "repetitions",
  threshold: 11,
  comparison_direction: "higher_is_better",
  minimum_age_years: 30,
  maximum_age_years: 39,
  governs: ["A matching comparison."],
  does_not_establish: ["Medical clearance."],
  unresolved_limitations: ["Population transfer."],
  evidence: [{
    title: "Reference study",
    source_url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC13193711/",
    population: "Colombian adults aged 30-39.",
    finding: "p2.5 was 11.",
    limitations: ["Small subgroup."],
    conflict_disclosure: "Authors reported none.",
  }],
};

const batch: CompetencyFloorCandidateBatch = {
  batch_version: "competency-floor-candidate-batch@1.0.0",
  batch_id: "98400000-0000-4000-8000-000000000100",
  content_digest: `sha256:${"b".repeat(64)}`,
  candidates: [{
    candidate_id: candidate.candidate_id,
    candidate_version: candidate.candidate_version,
    content_digest: candidate.content_digest,
  }],
};

describe("competency-floor governance transport", () => {
  it("loads and validates prepared candidates", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(new Response(JSON.stringify({
      projected_at: "2026-09-10T15:00:00Z",
      items: [{ candidate, status: "available", ratified_at: null, issues: [] }],
      batch,
      projection_version: "competency-floor-candidates@1.1.0",
    }), { status: 200 }));

    const result = await fetchCompetencyFloorCandidates("http://localhost:8000/", fetcher);

    expect(result.items[0].candidate.threshold).toBe(11);
    expect(fetcher).toHaveBeenCalledWith(
      "http://localhost:8000/v1/operator/competency-floor-candidates",
      expect.any(Object),
    );
  });

  it("rejects malformed candidate responses", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(new Response(JSON.stringify({
      projected_at: "2026-09-10T15:00:00Z",
      items: [{ candidate: { ...candidate, threshold: "11" }, status: "available", issues: [] }],
      batch,
      projection_version: "competency-floor-candidates@1.1.0",
    }), { status: 200 }));

    await expect(
      fetchCompetencyFloorCandidates("http://localhost:8000", fetcher),
    ).rejects.toEqual(new CompetencyFloorGovernanceError(
      "Competency-floor candidate response is invalid.",
      200,
    ));
  });

  it("ratifies only the exact version and digest", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ release_id: candidate.candidate_id }), { status: 201 }),
    );

    await ratifyCompetencyFloorCandidate("http://localhost:8000", candidate, fetcher);

    const request = fetcher.mock.calls[0];
    expect(request[0]).toBe(
      `http://localhost:8000/v1/operator/competency-floor-candidates/${candidate.candidate_id}/ratifications`,
    );
    expect(JSON.parse((request[1] as RequestInit).body as string)).toEqual({
      candidate_version: candidate.candidate_version,
      content_digest: candidate.content_digest,
      approval_attestation: true,
    });
  });

  it("ratifies the exact content-addressed batch in one request", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify({ batch }), { status: 201 }),
    );

    await ratifyCompetencyFloorCandidateBatch("http://localhost:8000/", batch, fetcher);

    const request = fetcher.mock.calls[0];
    expect(request[0]).toBe(
      "http://localhost:8000/v1/operator/competency-floor-candidate-batches/ratifications",
    );
    expect(JSON.parse((request[1] as RequestInit).body as string)).toEqual({
      ...batch,
      approval_attestation: true,
    });
  });
});
