import { describe, expect, it } from "vitest";

import type { CompetencyFloorCandidateProjection } from "./competency-floor-governance";
import {
  explosivePowerConstructionSlug,
  explosivePowerFloorSlug,
  explosivePowerResourceCandidateId,
  selectExplosivePowerAuthorityReview,
} from "./explosive-power-authority-review";
import type { ResourceGovernanceCandidateProjection } from "./resource-governance";
import type { TrainingConstructionCandidateProjection } from "./training-construction-governance";

const digest = `sha256:${"a".repeat(64)}`;

const floors: CompetencyFloorCandidateProjection = {
  projected_at: "2026-09-23T17:00:00Z",
  projection_version: "competency-floor-candidates@1.1.0",
  items: [{
    status: "available",
    ratified_at: null,
    issues: [],
    candidate: {
      candidate_version: "competency-floor-candidate@1.1.0",
      candidate_id: "98400000-0000-4000-8000-000000000004",
      slug: explosivePowerFloorSlug,
      release_label: "Owner-alpha provisional countermovement-jump floor",
      prepared_at: "2026-09-23T14:30:00Z",
      content_digest: digest,
      summary: "Provisional jump comparison.",
      authority_basis: {
        numeric_value_origin: "engineering_judgment",
        operational_use_origin: "engineering_judgment",
        numeric_value_explanation: "Twenty centimeters is an engineering prior.",
        operational_use_explanation: "Owner-only use.",
      },
      domain: "explosive_power",
      estimate_scope: "assessment_specific:countermovement_vertical_jump_height_cm",
      unit_or_scale: "centimeters",
      threshold: 20,
      comparison_direction: "higher_is_better",
      minimum_age_years: 30,
      maximum_age_years: 39,
      governs: ["One exact comparison."],
      does_not_establish: ["Safety clearance."],
      unresolved_limitations: ["Personal calibration is absent."],
      evidence: [],
    },
  }],
  batch: {
    batch_version: "competency-floor-candidate-batch@1.0.0",
    batch_id: "98400000-0000-4000-8000-000000000100",
    content_digest: digest,
    candidates: [{
      candidate_id: "98400000-0000-4000-8000-000000000004",
      candidate_version: "competency-floor-candidate@1.1.0",
      content_digest: digest,
    }],
  },
};

const resources: ResourceGovernanceCandidateProjection = {
  projected_at: "2026-09-23T17:00:00Z",
  projection_version: "resource-governance-candidates@1.0.0",
  items: [{
    status: "blocked",
    ratified_at: null,
    issues: ["Floor review required."],
    candidate: {
      candidate_version: "resource-governance-candidate@1.0.0",
      candidate_id: explosivePowerResourceCandidateId,
      content_digest: digest,
      prepared_at: "2026-09-23T16:00:00Z",
      release_label: "Owner-alpha explosive-power resource authorities",
      summary: "Evidence-linked jump resources.",
      exact_artifacts: ["Countermovement jump."],
      governs: ["Exact resource resolution."],
      does_not_establish: ["A workout."],
      operational_choices: ["No partial resolution."],
      unresolved_limitations: ["Readiness remains separate."],
      evidence: [],
    },
  }],
};

const construction: TrainingConstructionCandidateProjection = {
  projected_at: "2026-09-23T17:00:00Z",
  projection_version: "training-construction-candidates@1.0.0",
  items: [{
    status: "blocked",
    ratified_at: null,
    issues: ["Resource review required."],
    candidate: {
      candidate_version: "training-construction-candidate@1.0.0",
      candidate_id: "98900000-0000-4000-8000-000000000004",
      slug: explosivePowerConstructionSlug,
      release_label: "Owner-alpha explosive-power jump authorities",
      prepared_at: "2026-09-23T16:30:00Z",
      content_digest: digest,
      summary: "Fixed three-by-three starting dose.",
      authority_basis: {
        scientific_support: "Plyometric training can improve jump performance.",
        engineering_prior: "The exact values are engineering choices.",
      },
      exact_artifacts: ["Fixed dose."],
      governs: ["Nine initial contacts."],
      does_not_establish: ["Medical clearance."],
      unresolved_limitations: ["Personal calibration is absent."],
      evidence: [],
    },
  }],
};

describe("explosive-power authority review selection", () => {
  it("joins only the exact floor, resource, and construction candidates", () => {
    const result = selectExplosivePowerAuthorityReview(floors, resources, construction);

    expect(result?.floor.candidate.threshold).toBe(20);
    expect(result?.resource.status).toBe("blocked");
    expect(result?.construction.candidate.slug).toBe(explosivePowerConstructionSlug);
  });

  it("refuses a partial cross-candidate explanation", () => {
    const missingResource = { ...resources, items: [] };

    expect(selectExplosivePowerAuthorityReview(floors, missingResource, construction)).toBeNull();
  });
});
