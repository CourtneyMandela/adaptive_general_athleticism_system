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

export const explosivePowerFloorSlug = "owner_alpha_countermovement_jump_provisional_floor";
export const explosivePowerResourceCandidateId = "98600000-0000-4000-8000-000000000003";
export const explosivePowerConstructionSlug = "owner_alpha_explosive_power_jump_authorities";

export interface ExplosivePowerAuthorityReview {
  floor: CompetencyFloorCandidateItem;
  resource: ResourceGovernanceCandidateItem;
  construction: TrainingConstructionCandidateItem;
}

export function selectExplosivePowerAuthorityReview(
  floors: CompetencyFloorCandidateProjection,
  resources: ResourceGovernanceCandidateProjection,
  construction: TrainingConstructionCandidateProjection,
): ExplosivePowerAuthorityReview | null {
  const floor = floors.items.find(
    (item) => item.candidate.slug === explosivePowerFloorSlug,
  );
  const resource = resources.items.find(
    (item) => item.candidate.candidate_id === explosivePowerResourceCandidateId,
  );
  const constructionCandidate = construction.items.find(
    (item) => item.candidate.slug === explosivePowerConstructionSlug,
  );

  if (!floor || !resource || !constructionCandidate) return null;
  return { floor, resource, construction: constructionCandidate };
}
