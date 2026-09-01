export type FirstSessionStepState = "complete" | "your_action" | "system_action" | "waiting";

export interface FirstSessionAssessmentState {
  status: string;
  can_start_run: boolean;
  approved_self_administered_protocol_count: number;
  eligibility: { outcome: string } | null;
  latest_run: {
    decisions: Array<{
      decision: string;
      result_status: string;
      result: {
        capability_estimate_status: string;
        capability_estimate: unknown | null;
      } | null;
    }>;
  } | null;
}

export interface FirstSessionPlanningState {
  status: string;
  current_capability_estimate_count: number;
  first_week_readiness: {
    first_week_plan: { scheduled_session_count: number } | null;
  } | null;
}

export interface FirstSessionStep {
  id: "profile" | "assessment" | "estimate" | "plan" | "session";
  title: string;
  state: FirstSessionStepState;
  detail: string;
}

export interface FirstSessionPath {
  heading: string;
  message: string;
  steps: FirstSessionStep[];
}

function assessmentNeedsAthleteAction(assessment: FirstSessionAssessmentState): boolean {
  return assessment.can_start_run
    || ["ready_to_start", "selection_deferred", "result_entry_ready", "reassessment_due"].includes(
      assessment.status,
    );
}

function assessmentHasCompletedResults(assessment: FirstSessionAssessmentState): boolean {
  return Boolean(
    assessment.latest_run?.decisions.some(
      (decision) => decision.decision === "selected" && decision.result_status === "completed",
    ),
  );
}

function estimateNeedsAthleteAction(assessment: FirstSessionAssessmentState): boolean {
  return Boolean(
    assessment.latest_run?.decisions.some(
      (decision) =>
        decision.result?.capability_estimate_status === "ready"
        && decision.result.capability_estimate === null,
    ),
  );
}

export function buildFirstSessionPath(
  assessment: FirstSessionAssessmentState,
  planning: FirstSessionPlanningState,
  hasScheduledWeek: boolean,
): FirstSessionPath {
  const assessmentContentReady = assessment.approved_self_administered_protocol_count > 0;
  const eligibilityReady = assessment.eligibility?.outcome === "selection_allowed";
  const hasEstimate = planning.current_capability_estimate_count > 0;
  const hasFirstPlan = planning.first_week_readiness?.first_week_plan !== null
    && planning.first_week_readiness?.first_week_plan !== undefined;

  let assessmentStep: FirstSessionStep;
  if (!assessmentContentReady) {
    assessmentStep = {
      id: "assessment",
      title: "Reviewed assessment",
      state: "system_action",
      detail:
        "AGAS still needs a scientifically reviewed self-administered assessment protocol. This is not another form you missed.",
    };
  } else if (!eligibilityReady) {
    assessmentStep = {
      id: "assessment",
      title: "Reviewed assessment",
      state: "system_action",
      detail:
        "An authorized eligibility review must open assessment selection. The athlete account cannot approve itself.",
    };
  } else if (assessmentNeedsAthleteAction(assessment)) {
    assessmentStep = {
      id: "assessment",
      title: "Reviewed assessment",
      state: "your_action",
      detail:
        assessment.status === "result_entry_ready"
          ? "Perform the selected assessment and record the requested result in the Assessment section below."
          : "Open the Assessment section below and select the governed assessment set.",
    };
  } else {
    assessmentStep = {
      id: "assessment",
      title: "Reviewed assessment",
      state: assessmentHasCompletedResults(assessment) || hasEstimate ? "complete" : "waiting",
      detail:
        assessmentHasCompletedResults(assessment) || hasEstimate
          ? "At least one selected assessment result has been recorded with its provenance."
          : "Waiting for the current governed assessment workflow to become actionable.",
    };
  }

  let estimateStep: FirstSessionStep;
  if (hasEstimate) {
    estimateStep = {
      id: "estimate",
      title: "Capability interpretation",
      state: "complete",
      detail: "A current derived estimate exists and remains linked to its source observation.",
    };
  } else if (estimateNeedsAthleteAction(assessment)) {
    estimateStep = {
      id: "estimate",
      title: "Capability interpretation",
      state: "your_action",
      detail: "Use Create reviewed estimate below after checking the recorded assessment result.",
    };
  } else {
    estimateStep = {
      id: "estimate",
      title: "Capability interpretation",
      state: "waiting",
      detail: "This follows a completed assessment; AGAS will not invent a fitness score from your profile.",
    };
  }

  const planStep: FirstSessionStep = hasFirstPlan
    ? {
        id: "plan",
        title: "Governed first plan",
        state: "complete",
        detail: "A reviewed first week has been persisted.",
      }
    : {
        id: "plan",
        title: "Governed first plan",
        state: hasEstimate ? "system_action" : "waiting",
        detail: hasEstimate
          ? "Planning authorities must turn the measured state into priorities, a block, and a feasible week."
          : "Planning starts only after a current capability estimate exists.",
      };

  const sessionStep: FirstSessionStep = hasScheduledWeek
    ? {
        id: "session",
        title: "First training session",
        state: "complete",
        detail: "A scheduled session is available in the current week.",
      }
    : {
        id: "session",
        title: "First training session",
        state: "waiting",
        detail: "This appears automatically after a reviewed, feasible week is created.",
      };

  const userAction = [assessmentStep, estimateStep].find((step) => step.state === "your_action");
  const heading = hasScheduledWeek
    ? "Your training week is ready."
    : userAction
      ? "You have one clear next step."
      : "Your profile is saved; AGAS still owes you the training path.";
  const message = hasScheduledWeek
    ? "Open the scheduled session below when you are ready to train."
    : userAction
      ? userAction.detail
      : "There is no additional onboarding form you need to find right now. Reviewed assessment, safety, and planning content must be completed before AGAS can responsibly prescribe your first session.";

  return {
    heading,
    message,
    steps: [
      {
        id: "profile",
        title: "Profile and environment",
        state: "complete",
        detail: "Your athlete profile and at least one training environment are saved.",
      },
      assessmentStep,
      estimateStep,
      planStep,
      sessionStep,
    ],
  };
}
