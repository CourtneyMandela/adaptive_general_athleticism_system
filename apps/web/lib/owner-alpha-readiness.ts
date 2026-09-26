import {
  fetchAssessmentGovernanceCandidates,
  type AssessmentGovernanceCandidateProjection,
} from "./assessment-governance";
import {
  fetchCompetencyFloorCandidates,
  type CompetencyFloorCandidateProjection,
} from "./competency-floor-governance";
import {
  fetchCurrentWeek,
  type CurrentWeekProjection,
} from "./current-week";
import {
  fetchOwnedAthleteDirectory,
  type OwnedAthleteDirectory,
} from "./athlete-directory";
import {
  fetchPlanningGovernanceCandidates,
  type PlanningGovernanceCandidateProjection,
} from "./planning-governance";
import {
  fetchPlanningReviewQueue,
  type PlanningReviewQueueProjection,
} from "./planning-review-queue";
import {
  fetchResourceGovernanceCandidates,
  type ResourceGovernanceCandidateProjection,
} from "./resource-governance";
import {
  fetchTrainingConstructionCandidates,
  type TrainingConstructionCandidateProjection,
} from "./training-construction-governance";

export type AuthorityCandidateStatus =
  | "available"
  | "blocked"
  | "ratified"
  | "conflict";

export type AuthorityGroupKey =
  | "assessment"
  | "planning_policy"
  | "competency_floor"
  | "resource"
  | "training_construction";

export interface AuthorityCandidateAuditItem {
  candidate_id: string;
  release_label: string;
  content_digest: string;
  status: AuthorityCandidateStatus;
  ratified_at: string | null;
  issues: string[];
}

export interface AuthorityGroupAudit {
  key: AuthorityGroupKey;
  label: string;
  projection_version: string;
  projected_at: string;
  items: AuthorityCandidateAuditItem[];
}

export interface AthleteLiveAudit {
  athlete_id: string;
  athlete_display_name: string;
  current_week: CurrentWeekProjection | null;
  current_week_error: string | null;
  planning_task: PlanningReviewQueueProjection["items"][number] | null;
}

export interface OwnerAlphaReadinessAudit {
  audited_on: string;
  authority_groups: AuthorityGroupAudit[];
  athletes: AthleteLiveAudit[];
  directory_projection_version: string;
  queue_projection_version: string;
  queue_projected_at: string;
}

interface OwnerAlphaReadinessLoaders {
  assessment: typeof fetchAssessmentGovernanceCandidates;
  planning: typeof fetchPlanningGovernanceCandidates;
  floors: typeof fetchCompetencyFloorCandidates;
  resources: typeof fetchResourceGovernanceCandidates;
  construction: typeof fetchTrainingConstructionCandidates;
  directory: typeof fetchOwnedAthleteDirectory;
  queue: typeof fetchPlanningReviewQueue;
  currentWeek: typeof fetchCurrentWeek;
}

interface AuthorityProjectionSet {
  assessment: AssessmentGovernanceCandidateProjection;
  planning: PlanningGovernanceCandidateProjection;
  floors: CompetencyFloorCandidateProjection;
  resources: ResourceGovernanceCandidateProjection;
  construction: TrainingConstructionCandidateProjection;
}

const defaultLoaders: OwnerAlphaReadinessLoaders = {
  assessment: fetchAssessmentGovernanceCandidates,
  planning: fetchPlanningGovernanceCandidates,
  floors: fetchCompetencyFloorCandidates,
  resources: fetchResourceGovernanceCandidates,
  construction: fetchTrainingConstructionCandidates,
  directory: fetchOwnedAthleteDirectory,
  queue: fetchPlanningReviewQueue,
  currentWeek: fetchCurrentWeek,
};

function candidateItems(
  items: Array<{
    candidate: { candidate_id: string; release_label: string; content_digest: string };
    status: AuthorityCandidateStatus;
    ratified_at: string | null;
    issues: string[];
  }>,
): AuthorityCandidateAuditItem[] {
  return items.map((item) => ({
    candidate_id: item.candidate.candidate_id,
    release_label: item.candidate.release_label,
    content_digest: item.candidate.content_digest,
    status: item.status,
    ratified_at: item.ratified_at,
    issues: item.issues,
  }));
}

export function buildAuthorityGroupAudit(
  projections: AuthorityProjectionSet,
): AuthorityGroupAudit[] {
  return [
    {
      key: "assessment",
      label: "Assessment protocols",
      projection_version: projections.assessment.projection_version,
      projected_at: projections.assessment.projected_at,
      items: candidateItems(projections.assessment.items),
    },
    {
      key: "planning_policy",
      label: "Planning policies",
      projection_version: projections.planning.projection_version,
      projected_at: projections.planning.projected_at,
      items: candidateItems(projections.planning.items),
    },
    {
      key: "competency_floor",
      label: "Competency floors",
      projection_version: projections.floors.projection_version,
      projected_at: projections.floors.projected_at,
      items: candidateItems(projections.floors.items),
    },
    {
      key: "resource",
      label: "Resource authorities",
      projection_version: projections.resources.projection_version,
      projected_at: projections.resources.projected_at,
      items: candidateItems(projections.resources.items),
    },
    {
      key: "training_construction",
      label: "Training construction",
      projection_version: projections.construction.projection_version,
      projected_at: projections.construction.projected_at,
      items: candidateItems(projections.construction.items),
    },
  ];
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "The current-week projection was unavailable.";
}

export async function fetchOwnerAlphaReadinessAudit(
  apiBaseUrl: string,
  on: string,
  loaders: OwnerAlphaReadinessLoaders = defaultLoaders,
): Promise<OwnerAlphaReadinessAudit> {
  const [assessment, planning, floors, resources, construction, directory, queue] =
    await Promise.all([
      loaders.assessment(apiBaseUrl),
      loaders.planning(apiBaseUrl),
      loaders.floors(apiBaseUrl),
      loaders.resources(apiBaseUrl),
      loaders.construction(apiBaseUrl),
      loaders.directory(apiBaseUrl),
      loaders.queue(apiBaseUrl),
    ]);

  const weekResults = await Promise.allSettled(
    directory.athletes.map((athlete) => loaders.currentWeek(apiBaseUrl, athlete.athlete_id, on)),
  );
  const queueByAthlete = new Map(queue.items.map((item) => [item.athlete_id, item]));
  const athletes = directory.athletes.map((athlete, index): AthleteLiveAudit => {
    const result = weekResults[index];
    return {
      athlete_id: athlete.athlete_id,
      athlete_display_name: athlete.display_name,
      current_week: result.status === "fulfilled" ? result.value : null,
      current_week_error: result.status === "rejected" ? errorMessage(result.reason) : null,
      planning_task: queueByAthlete.get(athlete.athlete_id) ?? null,
    };
  });

  return {
    audited_on: on,
    authority_groups: buildAuthorityGroupAudit({
      assessment,
      planning,
      floors,
      resources,
      construction,
    }),
    athletes,
    directory_projection_version: directory.projection_version,
    queue_projection_version: queue.projection_version,
    queue_projected_at: queue.projected_at,
  };
}

export type { OwnerAlphaReadinessLoaders, AuthorityProjectionSet, OwnedAthleteDirectory };
