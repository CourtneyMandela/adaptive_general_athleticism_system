import { describe, expect, it, vi } from "vitest";

import {
  CompetencyFloorProposalError,
  fetchCompetencyFloorProposals,
  type CompetencyFloorProposalBatch,
} from "./competency-floor-proposals";

const batch: CompetencyFloorProposalBatch = {
  batch_version: "competency-floor-proposal-batch@1.0.0",
  batch_id: "c3b1083d-5d15-520e-b449-4f3539434be5",
  label: "Owner-alpha adult competency-floor research batch 1",
  prepared_at: "2026-09-12T17:00:00Z",
  content_digest: `sha256:${"a".repeat(64)}`,
  source_catalog: [{
    source_id: "acsm-12-table-3-8",
    title: "ACSM's Guidelines",
    authors: ["Author"],
    edition: "12th edition",
    publisher: "Wolters Kluwer",
    publication_year: 2026,
    isbn13: "9781975219246",
    table_locator: "Table 3.8",
    page_locator: "PDF pages 226-228",
    source_population: "Adults aged 30-39.",
    reported_value: "41.6 mL/kg/min.",
    source_role: "direct_reference",
    limitations: ["Maximal treadmill testing."],
  }],
  proposals: [{
    proposal_version: "competency-floor-proposal@1.0.0",
    proposal_id: "98800000-0000-4000-8000-000000000001",
    slug: "treadmill_vo2max_male_30_39_p55",
    label: "Treadmill VO2max",
    prepared_at: "2026-09-12T17:00:00Z",
    content_digest: `sha256:${"b".repeat(64)}`,
    stage: "proposal_only",
    domain: "aerobic_capacity",
    estimate_scope: "assessment_specific:direct_treadmill_vo2max",
    measurement: "Directly measured treadmill VO2max",
    unit_or_scale: "mL/kg/min",
    threshold: 41.6,
    comparison_direction: "higher_is_better",
    minimum_age_years: 30,
    maximum_age_years: 39,
    sex_scope: "male_reference",
    numeric_value_origin: "direct_textbook_reference",
    operational_use_origin: "evidence_informed_engineering_proposal",
    threshold_rationale: "Uses a reported percentile.",
    population_match: "moderate",
    population_match_notes: "Age matches; training history does not.",
    source_ids: ["acsm-12-table-3-8"],
    evidence_gap: "Not a validated floor.",
    prerequisites_before_release: ["Govern the assessment."],
    does_not_establish: ["Medical safety."],
    review_questions: ["Is this the right percentile?"],
  }],
  release_boundary: "Proposal only.",
};

describe("competency-floor proposal transport", () => {
  it("loads a validated, non-ratifiable proposal batch", async () => {
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify(batch), { status: 200 }),
    );

    const result = await fetchCompetencyFloorProposals("http://localhost:8000/", fetcher);

    expect(result.proposals[0].stage).toBe("proposal_only");
    expect(result.proposals[0].threshold).toBe(41.6);
    expect(fetcher).toHaveBeenCalledWith(
      "http://localhost:8000/v1/operator/competency-floor-proposals",
      expect.any(Object),
    );
  });

  it("rejects a proposal that cites an unknown source", async () => {
    const invalid = structuredClone(batch);
    invalid.proposals[0].source_ids = ["missing"];
    const fetcher = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(JSON.stringify(invalid), { status: 200 }),
    );

    await expect(fetchCompetencyFloorProposals("http://localhost:8000", fetcher)).rejects.toEqual(
      new CompetencyFloorProposalError("Competency-floor proposal response is invalid.", 200),
    );
  });
});
