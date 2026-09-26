import { describe, expect, it } from "vitest";

import type { AssessmentGovernanceCandidateProjection } from "./assessment-governance";
import {
  aerobicAssessmentSlug,
  aerobicConstructionSlug,
  aerobicFloorSlug,
  aerobicResourceCandidateId,
  selectAerobicAuthorityReview,
} from "./aerobic-authority-review";
import type { CompetencyFloorCandidateProjection } from "./competency-floor-governance";
import type { ResourceGovernanceCandidateProjection } from "./resource-governance";
import type { TrainingConstructionCandidateProjection } from "./training-construction-governance";

const digest = `sha256:${"a".repeat(64)}`;

const assessments: AssessmentGovernanceCandidateProjection = {
  projected_at: "2026-09-25T17:00:00Z",
  projection_version: "assessment-governance-candidates@1.0.0",
  items: [{
    status: "available",
    ratified_at: null,
    issues: [],
    candidate: {
      candidate_version: "assessment-governance-candidate@1.0.0",
      candidate_id: "91770000-0000-4000-8000-000000000001",
      slug: aerobicAssessmentSlug,
      release_label: "12-minute walk/run owner-alpha release",
      prepared_at: "2026-09-25T14:30:00Z",
      content_digest: digest,
      summary: "A direct distance field assessment.",
      measures: "Assessment-specific distance covered in 12 minutes, in meters.",
      does_not_measure: ["Laboratory VO2."],
      capability_domain: "aerobic_capacity",
      estimate_scope: "assessment_specific:twelve_minute_walk_run_distance_m",
      setup_requirements: ["A measured route."],
      protocol_steps: ["Walk or run for 12 minutes."],
      stop_conditions: ["Stop for concerning symptoms."],
      operational_choices: ["No VO2 conversion."],
      unresolved_limitations: ["Pacing affects performance."],
      evidence: [],
    },
  }],
};

const floors: CompetencyFloorCandidateProjection = {
  projected_at: "2026-09-25T17:00:00Z",
  projection_version: "competency-floor-candidates@1.1.0",
  items: [{
    status: "available",
    ratified_at: null,
    issues: [],
    candidate: {
      candidate_version: "competency-floor-candidate@1.1.0",
      candidate_id: "91800000-0000-4000-8000-000000000001",
      slug: aerobicFloorSlug,
      release_label: "Owner-alpha provisional 12-minute walk/run floor",
      prepared_at: "2026-09-25T15:00:00Z",
      content_digest: digest,
      summary: "A provisional owner-only comparison.",
      authority_basis: {
        numeric_value_origin: "engineering_judgment",
        operational_use_origin: "engineering_judgment",
        numeric_value_explanation: "The 1200 meter value is an engineering prior.",
        operational_use_explanation: "Owner-only use.",
      },
      domain: "aerobic_capacity",
      estimate_scope: "assessment_specific:twelve_minute_walk_run_distance_m",
      unit_or_scale: "meters",
      threshold: 1200,
      comparison_direction: "higher_is_better",
      minimum_age_years: 30,
      maximum_age_years: 39,
      governs: ["One exact comparison."],
      does_not_establish: ["Medical clearance."],
      unresolved_limitations: ["Personal calibration is absent."],
      evidence: [],
    },
  }],
  batch: {
    batch_version: "competency-floor-candidate-batch@1.0.0",
    batch_id: "98400000-0000-4000-8000-000000000100",
    content_digest: digest,
    candidates: [{
      candidate_id: "91800000-0000-4000-8000-000000000001",
      candidate_version: "competency-floor-candidate@1.1.0",
      content_digest: digest,
    }],
  },
};

const resources: ResourceGovernanceCandidateProjection = {
  projected_at: "2026-09-25T17:00:00Z",
  projection_version: "resource-governance-candidates@1.0.0",
  items: [{
    status: "blocked",
    ratified_at: null,
    issues: ["Floor review required."],
    candidate: {
      candidate_version: "resource-governance-candidate@1.0.0",
      candidate_id: aerobicResourceCandidateId,
      content_digest: digest,
      prepared_at: "2026-09-25T15:30:00Z",
      release_label: "Owner-alpha aerobic-base resource authorities",
      summary: "Evidence-linked treadmill walk/run resources.",
      exact_artifacts: ["Treadmill walk/run."],
      governs: ["Broad direction.", "Exact exercise.", "Full resolution.", "A 24-minute weekly envelope."],
      does_not_establish: ["A workout."],
      operational_choices: ["No partial resolution."],
      unresolved_limitations: ["Readiness remains separate."],
      evidence: [],
    },
  }],
};

const construction: TrainingConstructionCandidateProjection = {
  projected_at: "2026-09-25T17:00:00Z",
  projection_version: "training-construction-candidates@1.0.0",
  items: [{
    status: "blocked",
    ratified_at: null,
    issues: ["Resource review required."],
    candidate: {
      candidate_version: "training-construction-candidate@1.0.0",
      candidate_id: "98900000-0000-4000-8000-000000000006",
      slug: aerobicConstructionSlug,
      release_label: "Owner-alpha aerobic-base duration authorities",
      prepared_at: "2026-09-25T16:00:00Z",
      content_digest: digest,
      summary: "A 600-second start with a 720-second ceiling.",
      authority_basis: {
        scientific_support: "Regular individualized aerobic exercise is supported.",
        engineering_prior: "The exact duration and progression values are engineering priors.",
      },
      exact_artifacts: ["Fixed duration dose."],
      governs: ["A 600-second set.", "RPE 4-6.", "A 720-second ceiling."],
      does_not_establish: ["Medical clearance."],
      unresolved_limitations: ["Personal calibration is absent."],
      evidence: [],
    },
  }],
};

describe("aerobic authority review selection", () => {
  it("joins only the exact assessment, floor, resource, and construction candidates", () => {
    const result = selectAerobicAuthorityReview(
      assessments,
      floors,
      resources,
      construction,
    );

    expect(result?.assessment.candidate.slug).toBe(aerobicAssessmentSlug);
    expect(result?.floor.candidate.threshold).toBe(1200);
    expect(result?.resource.status).toBe("blocked");
    expect(result?.construction.candidate.slug).toBe(aerobicConstructionSlug);
  });

  it("refuses a partial cross-candidate explanation", () => {
    const missingAssessment = { ...assessments, items: [] };

    expect(selectAerobicAuthorityReview(
      missingAssessment,
      floors,
      resources,
      construction,
    )).toBeNull();
  });
});
