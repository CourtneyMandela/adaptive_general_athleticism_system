import type {
  AssessmentGovernanceCandidateItem,
  AssessmentGovernanceCandidateProjection,
} from "./assessment-governance";
import type {
  CompetencyFloorCandidateItem,
  CompetencyFloorCandidateProjection,
} from "./competency-floor-governance";
import type {
  ResourceGovernanceCandidateItem,
  ResourceGovernanceCandidateProjection,
} from "./resource-governance";
import type {
  TrainingConstructionCandidateItem,
  TrainingConstructionCandidateProjection,
} from "./training-construction-governance";

export const aerobicAssessmentSlug = "twelve_minute_walk_run_distance";
export const aerobicFloorSlug = "owner_alpha_twelve_minute_walk_run_provisional_floor";
export const aerobicResourceCandidateId = "91900000-0000-4000-8000-000000000001";
export const aerobicConstructionSlug = "owner_alpha_aerobic_base_duration_authorities";

export interface AerobicAuthorityReview {
  assessment: AssessmentGovernanceCandidateItem;
  floor: CompetencyFloorCandidateItem;
  resource: ResourceGovernanceCandidateItem;
  construction: TrainingConstructionCandidateItem;
}

export function selectAerobicAuthorityReview(
  assessments: AssessmentGovernanceCandidateProjection,
  floors: CompetencyFloorCandidateProjection,
  resources: ResourceGovernanceCandidateProjection,
  construction: TrainingConstructionCandidateProjection,
): AerobicAuthorityReview | null {
  const assessment = assessments.items.find(
    (item) => item.candidate.slug === aerobicAssessmentSlug,
  );
  const floor = floors.items.find(
    (item) => item.candidate.slug === aerobicFloorSlug,
  );
  const resource = resources.items.find(
    (item) => item.candidate.candidate_id === aerobicResourceCandidateId,
  );
  const constructionCandidate = construction.items.find(
    (item) => item.candidate.slug === aerobicConstructionSlug,
  );

  if (!assessment || !floor || !resource || !constructionCandidate) return null;
  return { assessment, floor, resource, construction: constructionCandidate };
}
