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
    expect(result.steps.find((step) => step.id === "session")?.state).toBe("complete");
  });
});
