import { describe, expect, it, vi } from "vitest";

import type { CurrentWeekProjection } from "./current-week";
import {
  buildAuthorityGroupAudit,
  fetchOwnerAlphaReadinessAudit,
  type AuthorityProjectionSet,
  type OwnerAlphaReadinessLoaders,
} from "./owner-alpha-readiness";

const athleteId = "00000000-0000-4000-8000-000000000001";
const candidateId = "00000000-0000-4000-8000-000000000002";

function projection(
  projectionVersion: string,
  status: "available" | "blocked" | "ratified" | "conflict" = "ratified",
) {
  return {
    projected_at: "2026-09-25T12:00:00Z",
    projection_version: projectionVersion,
    items: [
      {
        candidate: {
          candidate_id: candidateId,
          release_label: `${projectionVersion} release`,
          content_digest: `sha256:${"a".repeat(64)}`,
        },
        status,
        ratified_at: status === "ratified" ? "2026-09-24T12:00:00Z" : null,
        issues: status === "blocked" ? ["A prerequisite is missing."] : [],
      },
    ],
  };
}

function projections(): AuthorityProjectionSet {
  return {
    assessment: projection("assessment-governance-candidates@1.0.0") as never,
    planning: projection("planning-governance-candidates@1.0.0") as never,
    floors: { ...projection("competency-floor-candidates@1.1.0"), batch: {} } as never,
    resources: projection("resource-governance-candidates@1.0.0", "blocked") as never,
    construction: projection("training-construction-candidates@1.0.0") as never,
  };
}

function currentWeek(): CurrentWeekProjection {
  return {
    athlete_id: athleteId,
    athlete_display_name: "Owner athlete",
    as_of: "2026-09-25",
    safety_policy_assignment: null,
    week: null,
  };
}

describe("owner-alpha readiness audit", () => {
  it("normalizes every authority family without turning candidate inventory into approval", () => {
    const groups = buildAuthorityGroupAudit(projections());

    expect(groups.map((group) => group.key)).toEqual([
      "assessment",
      "planning_policy",
      "competency_floor",
      "resource",
      "training_construction",
    ]);
    expect(groups[0].items[0]).toEqual({
      candidate_id: candidateId,
      release_label: "assessment-governance-candidates@1.0.0 release",
      content_digest: `sha256:${"a".repeat(64)}`,
      status: "ratified",
      ratified_at: "2026-09-24T12:00:00Z",
      issues: [],
    });
    expect(groups[3].items[0]).toMatchObject({
      status: "blocked",
      issues: ["A prerequisite is missing."],
    });
  });

  it("binds owned athletes to their exact current week and reviewer task", async () => {
    const authority = projections();
    const currentWeekLoader = vi.fn().mockResolvedValue(currentWeek());
    const loaders = {
      assessment: vi.fn().mockResolvedValue(authority.assessment),
      planning: vi.fn().mockResolvedValue(authority.planning),
      floors: vi.fn().mockResolvedValue(authority.floors),
      resources: vi.fn().mockResolvedValue(authority.resources),
      construction: vi.fn().mockResolvedValue(authority.construction),
      directory: vi.fn().mockResolvedValue({
        projection_version: "account-athlete-directory@1.0.0",
        athletes: [{ athlete_id: athleteId, display_name: "Owner athlete" }],
      }),
      queue: vi.fn().mockResolvedValue({
        projected_at: "2026-09-25T12:00:00Z",
        projection_version: "planning-review-queue@1.0.0",
        items: [{
          athlete_id: athleteId,
          athlete_display_name: "Owner athlete",
          workflow_stage: "first_week",
          status: "ready_for_explicit_first_week",
          readiness: "ready",
          strategy_id: candidateId,
          block_id: candidateId,
          message: "Review Week 1.",
          issues: [],
        }],
      }),
      currentWeek: currentWeekLoader,
    } as unknown as OwnerAlphaReadinessLoaders;

    const audit = await fetchOwnerAlphaReadinessAudit(
      "/api/agas/",
      "2026-09-25",
      loaders,
    );

    expect(currentWeekLoader).toHaveBeenCalledWith(
      "/api/agas/",
      athleteId,
      "2026-09-25",
    );
    expect(audit.athletes[0].current_week).toEqual(currentWeek());
    expect(audit.athletes[0].planning_task?.workflow_stage).toBe("first_week");
    expect(audit.authority_groups).toHaveLength(5);
  });

  it("surfaces a current-week failure without erasing the authority audit", async () => {
    const authority = projections();
    const loaders = {
      assessment: vi.fn().mockResolvedValue(authority.assessment),
      planning: vi.fn().mockResolvedValue(authority.planning),
      floors: vi.fn().mockResolvedValue(authority.floors),
      resources: vi.fn().mockResolvedValue(authority.resources),
      construction: vi.fn().mockResolvedValue(authority.construction),
      directory: vi.fn().mockResolvedValue({
        projection_version: "account-athlete-directory@1.0.0",
        athletes: [{ athlete_id: athleteId, display_name: "Owner athlete" }],
      }),
      queue: vi.fn().mockResolvedValue({
        projected_at: "2026-09-25T12:00:00Z",
        projection_version: "planning-review-queue@1.0.0",
        items: [],
      }),
      currentWeek: vi.fn().mockRejectedValue(new Error("Current week is unavailable.")),
    } as unknown as OwnerAlphaReadinessLoaders;

    const audit = await fetchOwnerAlphaReadinessAudit("/api/agas", "2026-09-25", loaders);

    expect(audit.authority_groups).toHaveLength(5);
    expect(audit.athletes[0]).toMatchObject({
      current_week: null,
      current_week_error: "Current week is unavailable.",
      planning_task: null,
    });
  });
});
