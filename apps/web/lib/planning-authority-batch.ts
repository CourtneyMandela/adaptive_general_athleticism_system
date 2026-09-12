import {
  fetchCompetencyFloorCandidates,
  ratifyCompetencyFloorCandidateBatch,
  type CompetencyFloorCandidateBatch,
  type CompetencyFloorCandidateProjection,
} from "./competency-floor-governance";
import {
  fetchPlanningGovernanceCandidates,
  ratifyPlanningGovernanceCandidate,
  type PlanningGovernanceCandidate,
  type PlanningGovernanceCandidateProjection,
} from "./planning-governance";
import {
  fetchResourceGovernanceCandidates,
  ratifyResourceGovernanceCandidate,
  type ResourceGovernanceCandidate,
  type ResourceGovernanceCandidateProjection,
} from "./resource-governance";
import {
  fetchTrainingConstructionCandidates,
  ratifyTrainingConstructionCandidate,
  type TrainingConstructionCandidate,
  type TrainingConstructionCandidateProjection,
} from "./training-construction-governance";

export interface PlanningAuthorityBatchState {
  available_group_count: number;
  blocked_group_count: number;
  conflict_group_count: number;
  ratified_group_count: number;
}

export interface PlanningAuthorityBatchResult {
  approved_group_count: number;
  remaining: PlanningAuthorityBatchState;
}

export interface PlanningAuthorityBatchOperations {
  fetchPlanning(apiBaseUrl: string): Promise<PlanningGovernanceCandidateProjection>;
  ratifyPlanning(apiBaseUrl: string, candidate: PlanningGovernanceCandidate): Promise<unknown>;
  fetchFloors(apiBaseUrl: string): Promise<CompetencyFloorCandidateProjection>;
  ratifyFloorBatch(apiBaseUrl: string, batch: CompetencyFloorCandidateBatch): Promise<unknown>;
  fetchResources(apiBaseUrl: string): Promise<ResourceGovernanceCandidateProjection>;
  ratifyResource(apiBaseUrl: string, candidate: ResourceGovernanceCandidate): Promise<unknown>;
  fetchConstruction(apiBaseUrl: string): Promise<TrainingConstructionCandidateProjection>;
  ratifyConstruction(
    apiBaseUrl: string,
    candidate: TrainingConstructionCandidate,
  ): Promise<unknown>;
}

const defaultOperations: PlanningAuthorityBatchOperations = {
  fetchPlanning: fetchPlanningGovernanceCandidates,
  ratifyPlanning: ratifyPlanningGovernanceCandidate,
  fetchFloors: fetchCompetencyFloorCandidates,
  ratifyFloorBatch: ratifyCompetencyFloorCandidateBatch,
  fetchResources: fetchResourceGovernanceCandidates,
  ratifyResource: ratifyResourceGovernanceCandidate,
  fetchConstruction: fetchTrainingConstructionCandidates,
  ratifyConstruction: ratifyTrainingConstructionCandidate,
};

export class PlanningAuthorityBatchError extends Error {
  constructor(message: string, readonly approvedGroupCount = 0) {
    super(message);
    this.name = "PlanningAuthorityBatchError";
  }
}

function countStatus(
  projections: {
    planning: PlanningGovernanceCandidateProjection;
    floors: CompetencyFloorCandidateProjection;
    resources: ResourceGovernanceCandidateProjection;
    construction: TrainingConstructionCandidateProjection;
  },
): PlanningAuthorityBatchState {
  const ordinaryItems = [
    ...projections.planning.items,
    ...projections.resources.items,
    ...projections.construction.items,
  ];
  const floorStatuses = projections.floors.items.map((item) => item.status);
  return {
    available_group_count:
      ordinaryItems.filter((item) => item.status === "available").length
      + (floorStatuses.includes("available") ? 1 : 0),
    blocked_group_count: ordinaryItems.filter((item) => item.status === "blocked").length,
    conflict_group_count:
      ordinaryItems.filter((item) => item.status === "conflict").length
      + floorStatuses.filter((status) => status === "conflict").length,
    ratified_group_count:
      ordinaryItems.filter((item) => item.status === "ratified").length
      + (floorStatuses.length > 0 && floorStatuses.every((status) => status === "ratified") ? 1 : 0),
  };
}

async function fetchAll(
  apiBaseUrl: string,
  operations: PlanningAuthorityBatchOperations,
) {
  const [planning, floors, resources, construction] = await Promise.all([
    operations.fetchPlanning(apiBaseUrl),
    operations.fetchFloors(apiBaseUrl),
    operations.fetchResources(apiBaseUrl),
    operations.fetchConstruction(apiBaseUrl),
  ]);
  return { planning, floors, resources, construction };
}

export async function fetchPlanningAuthorityBatchState(
  apiBaseUrl: string,
  operations: PlanningAuthorityBatchOperations = defaultOperations,
): Promise<PlanningAuthorityBatchState> {
  return countStatus(await fetchAll(apiBaseUrl, operations));
}

function assertNoConflicts(state: PlanningAuthorityBatchState, approvedGroupCount: number) {
  if (state.conflict_group_count > 0) {
    throw new PlanningAuthorityBatchError(
      "Resolve the conflicting authority before using batch approval.",
      approvedGroupCount,
    );
  }
}

export async function ratifyAvailablePlanningAuthorityBatch(
  apiBaseUrl: string,
  operations: PlanningAuthorityBatchOperations = defaultOperations,
): Promise<PlanningAuthorityBatchResult> {
  let approvedGroupCount = 0;
  try {
    assertNoConflicts(await fetchPlanningAuthorityBatchState(apiBaseUrl, operations), 0);

    const planning = await operations.fetchPlanning(apiBaseUrl);
    if (planning.items.some((item) => item.status === "conflict")) {
      throw new PlanningAuthorityBatchError(
        "A planning-policy conflict appeared during batch approval.",
        approvedGroupCount,
      );
    }
    for (const item of planning.items.filter((entry) => entry.status === "available")) {
      await operations.ratifyPlanning(apiBaseUrl, item.candidate);
      approvedGroupCount += 1;
    }

    const floors = await operations.fetchFloors(apiBaseUrl);
    if (floors.items.some((item) => item.status === "conflict")) {
      throw new PlanningAuthorityBatchError(
        "A competency-floor conflict appeared during batch approval.",
        approvedGroupCount,
      );
    }
    if (floors.items.some((item) => item.status === "available")) {
      await operations.ratifyFloorBatch(apiBaseUrl, floors.batch);
      approvedGroupCount += 1;
    }

    const resources = await operations.fetchResources(apiBaseUrl);
    if (resources.items.some((item) => item.status === "conflict")) {
      throw new PlanningAuthorityBatchError(
        "A resource-authority conflict appeared during batch approval.",
        approvedGroupCount,
      );
    }
    for (const item of resources.items.filter((entry) => entry.status === "available")) {
      await operations.ratifyResource(apiBaseUrl, item.candidate);
      approvedGroupCount += 1;
    }

    // Construction can become available only after the resource bundle is ratified, so re-read it.
    const construction = await operations.fetchConstruction(apiBaseUrl);
    if (construction.items.some((item) => item.status === "conflict")) {
      throw new PlanningAuthorityBatchError(
        "A training-construction conflict appeared during batch approval.",
        approvedGroupCount,
      );
    }
    for (const item of construction.items.filter((entry) => entry.status === "available")) {
      await operations.ratifyConstruction(apiBaseUrl, item.candidate);
      approvedGroupCount += 1;
    }

    return {
      approved_group_count: approvedGroupCount,
      remaining: await fetchPlanningAuthorityBatchState(apiBaseUrl, operations),
    };
  } catch (error) {
    if (error instanceof PlanningAuthorityBatchError) throw error;
    throw new PlanningAuthorityBatchError(
      error instanceof Error ? error.message : "Planning-authority batch approval failed.",
      approvedGroupCount,
    );
  }
}
