import { describe, expect, it } from "vitest";

import {
  buildFirstSessionPath,
  type FirstSessionAssessmentState,
  type FirstSessionPlanningState,
} from "./first-session-path";

function assessment(
  overrides: Partial<FirstSessionAssessmentState> = {},
): FirstSessionAssessmentState {
  return {
    status: "eligibility_required",
    can_start_run: false,
    approved_self_administered_protocol_count: 0,
    eligibility: null,
    latest_run: null,
    ...overrides,
  };
}

function planning(
  overrides: Partial<FirstSessionPlanningState> = {},
): FirstSessionPlanningState {
  return {
    status: "capability_estimate_required",
    current_capability_estimate_count: 0,
    first_week_readiness: null,
    ...overrides,
  };
}

describe("first-session path", () => {
  it("tells a newly onboarded athlete that missing governance is not another form", () => {
    const result = buildFirstSessionPath(assessment(), planning(), false);

    expect(result.heading).toBe("Your profile is saved; AGAS still owes you the training path.");
    expect(result.message).toContain("There is no additional onboarding form");
    expect(result.next_action).toEqual({
      href: "/review/assessments",
      label: "Inspect assessment governance",
    });
    expect(result.steps).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ id: "profile", state: "complete" }),
        expect.objectContaining({ id: "assessment", state: "system_action" }),
        expect.objectContaining({ id: "estimate", state: "waiting" }),
        expect.objectContaining({ id: "plan", state: "waiting" }),
        expect.objectContaining({ id: "session", state: "waiting" }),
      ]),
    );
  });

  it("makes a prepared assessment release the owner's explicit next action", () => {
    const athleteId = "0fe4fa6f-d3de-49f8-8d95-239854fb0ecb";
    const result = buildFirstSessionPath(
      assessment(),
      planning(),
      false,
      athleteId,
      { available_candidate_count: 1, conflict_candidate_count: 0 },
    );

    expect(result.heading).toBe("You have one clear next step.");
    expect(result.message).toContain("prepared a complete assessment release");
    expect(result.steps.find((step) => step.id === "assessment")).toMatchObject({
      state: "your_action",
    });
    expect(result.next_action).toEqual({
      href: `/review/assessments?athleteId=${athleteId}`,
      label: "Review the prepared assessment",
    });
  });

  it("does not present a conflicting prepared release as approvable", () => {
    const result = buildFirstSessionPath(
      assessment(),
      planning(),
      false,
      undefined,
      { available_candidate_count: 0, conflict_candidate_count: 1 },
    );

    expect(result.steps.find((step) => step.id === "assessment")).toMatchObject({
      state: "system_action",
    });
    expect(result.heading).toContain("AGAS still owes");
    expect(result.next_action?.label).toBe("Inspect the assessment conflict");
  });

  it("identifies starting a governed assessment as the athlete's next action", () => {
    const result = buildFirstSessionPath(
      assessment({
        status: "ready_to_start",
        can_start_run: true,
        approved_self_administered_protocol_count: 2,
        eligibility: { outcome: "selection_allowed" },
      }),
      planning(),
      false,
    );

    expect(result.heading).toBe("You have one clear next step.");
    expect(result.steps.find((step) => step.id === "assessment")?.state).toBe("your_action");
    expect(result.next_action?.href).toBe("#assessment-title");
  });

  it("makes current readiness the athlete action once a protocol exists", () => {
    const result = buildFirstSessionPath(
      assessment({ approved_self_administered_protocol_count: 1 }),
      planning(),
      false,
    );

    const step = result.steps.find((item) => item.id === "assessment");
    expect(step?.state).toBe("your_action");
    expect(step?.detail).toContain("current-readiness check");
  });

  it("identifies reviewed estimate creation after a result is recorded", () => {
    const result = buildFirstSessionPath(
      assessment({
        status: "reassessment_not_due",
        approved_self_administered_protocol_count: 1,
        eligibility: { outcome: "selection_allowed" },
        latest_run: {
          decisions: [
            {
              decision: "selected",
              result_status: "completed",
              result: {
                capability_estimate_status: "ready",
                capability_estimate: null,
              },
            },
          ],
        },
      }),
      planning(),
      false,
    );

    expect(result.steps.find((step) => step.id === "assessment")?.state).toBe("complete");
    expect(result.steps.find((step) => step.id === "estimate")?.state).toBe("your_action");
  });

  it("separates completed measurement from reviewer-owned first-plan work", () => {
    const result = buildFirstSessionPath(
      assessment({
        status: "reassessment_not_due",
        approved_self_administered_protocol_count: 1,
        eligibility: { outcome: "selection_allowed" },
      }),
      planning({ current_capability_estimate_count: 1 }),
      false,
    );

    expect(result.steps.find((step) => step.id === "estimate")?.state).toBe("complete");
    expect(result.steps.find((step) => step.id === "plan")?.state).toBe("system_action");
    expect(result.next_action?.href).toBe("/review/queue");
  });

  it("routes missing planning authority to the prepared authority review", () => {
    const result = buildFirstSessionPath(
      assessment({
        status: "reassessment_not_due",
        approved_self_administered_protocol_count: 1,
        eligibility: { outcome: "selection_allowed" },
      }),
      planning({
        status: "planning_authorities_required",
        current_capability_estimate_count: 1,
      }),
      false,
    );

    expect(result.next_action).toEqual({
      href: "/review/planning-authorities",
      label: "Review the prepared planning authorities",
    });
  });

  it("preserves athlete context through governed review handoffs", () => {
    const athleteId = "0fe4fa6f-d3de-49f8-8d95-239854fb0ecb";
    const assessmentReview = buildFirstSessionPath(assessment(), planning(), false, athleteId);
    expect(assessmentReview.next_action?.href).toBe(
      `/review/assessments?athleteId=${athleteId}`,
    );

    const planningReview = buildFirstSessionPath(
      assessment({
        status: "reassessment_not_due",
        approved_self_administered_protocol_count: 1,
        eligibility: { outcome: "selection_allowed" },
      }),
      planning({
        status: "planning_authorities_required",
        current_capability_estimate_count: 1,
      }),
      false,
      athleteId,
    );
    expect(planningReview.next_action?.href).toBe(
      `/review/planning-authorities?athleteId=${athleteId}`,
    );
  });

  it("reports a scheduled first week as ready to train", () => {
    const result = buildFirstSessionPath(
      assessment({
        status: "reassessment_not_due",
        approved_self_administered_protocol_count: 1,
        eligibility: { outcome: "selection_allowed" },
      }),
      planning({
        status: "first_week_created",
        current_capability_estimate_count: 1,
        first_week_readiness: { first_week_plan: { scheduled_session_count: 3 } },
      }),
      true,
    );

    expect(result.heading).toBe("Your training week is ready.");
    expect(result.steps.find((step) => step.id === "plan")?.state).toBe("complete");
    expect(result.steps.find((step) => step.id === "session")?.state).toBe("your_action");
    expect(result.next_action).toEqual({
      href: "#week-title",
      label: "Open your scheduled sessions",
    });
  });
});
