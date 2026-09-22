import { athleteReviewHref } from "./athlete-navigation";
import {
  planningReviewHref,
  type PlanningReviewQueueItem,
  type PlanningWorkflowStage,
} from "./planning-review-queue";

export type FirstSessionStepState = "complete" | "your_action" | "system_action" | "waiting";

export interface FirstSessionAssessmentState {
  status: string;
  can_start_run: boolean;
  approved_self_administered_protocol_count: number;
  eligibility: { outcome: string } | null;
  jump_exposure_need?: {
    status: "unknown" | "introductory_exposure_needed" | "recent_exposure_confirmed";
    active: boolean;
  } | null;
  introductory_jump_history?: {
    qualifying_days: number;
    required_days: number;
    session_recorded_today: boolean;
  } | null;
  introductory_jump_dose?: unknown | null;
  latest_run: {
    decisions: Array<{
      decision: string;
      reason_codes?: string[];
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

export interface FirstSessionAssessmentReviewState {
  available_candidate_count: number;
  conflict_candidate_count: number;
}

export interface FirstSessionPlanningReviewState {
  available_candidate_count: number;
  blocked_candidate_count: number;
  conflict_candidate_count: number;
}

export interface FirstSessionExposureReviewState {
  available_candidate_count: number;
  conflict_candidate_count: number;
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
  next_action: {
    href: string;
    label: string;
  } | null;
}

const planningStageActionLabels: Record<PlanningWorkflowStage, string> = {
  initial_planning: "Review your initial strategy",
  resource_demands: "Review your training dose",
  block_creation: "Review your first training block",
  first_week: "Schedule your first training week",
};

function planningQueueDetail(item: PlanningReviewQueueItem): string {
  if (item.readiness === "ready") return item.message;
  const firstIssue = item.issues[0];
  return firstIssue
    ? `${item.message} Current blocker: ${firstIssue}`
    : item.message;
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

function assessmentNeedsEnvironmentAction(assessment: FirstSessionAssessmentState): boolean {
  return assessment.status === "environment_required"
    || Boolean(
      assessment.latest_run?.decisions.some(
        (decision) => decision.reason_codes?.includes("missing_equipment"),
      ),
    );
}

export function buildFirstSessionPath(
  assessment: FirstSessionAssessmentState,
  planning: FirstSessionPlanningState,
  hasScheduledWeek: boolean,
  athleteId?: string,
  assessmentReview?: FirstSessionAssessmentReviewState,
  planningReview?: FirstSessionPlanningReviewState,
  planningQueueItem?: PlanningReviewQueueItem,
  exposureReview?: FirstSessionExposureReviewState,
): FirstSessionPath {
  const assessmentContentReady = assessment.approved_self_administered_protocol_count > 0;
  const preparedAssessmentAvailable = (assessmentReview?.available_candidate_count ?? 0) > 0;
  const preparedAssessmentConflict = (assessmentReview?.conflict_candidate_count ?? 0) > 0;
  const eligibilityReady = assessment.eligibility?.outcome === "selection_allowed";
  const needsEnvironmentAction = assessmentNeedsEnvironmentAction(assessment);
  const introductoryExposureNeeded = assessment.jump_exposure_need?.active === true
    && assessment.jump_exposure_need.status === "introductory_exposure_needed";
  const introductoryExposureRecordedToday = introductoryExposureNeeded
    && assessment.introductory_jump_history?.session_recorded_today === true;
  const introductoryExposureDoseReady = assessment.introductory_jump_dose != null;
  const preparedExposureAuthorityAvailable = (exposureReview?.available_candidate_count ?? 0) > 0;
  const preparedExposureAuthorityConflict = (exposureReview?.conflict_candidate_count ?? 0) > 0;
  const qualifyingExposureDays = assessment.introductory_jump_history?.qualifying_days ?? 0;
  const requiredExposureDays = assessment.introductory_jump_history?.required_days ?? 2;
  const hasEstimate = planning.current_capability_estimate_count > 0;
  const preparedPlanningAvailable = (planningReview?.available_candidate_count ?? 0) > 0;
  const preparedPlanningConflict = (planningReview?.conflict_candidate_count ?? 0) > 0;
  const hasFirstPlan = planning.first_week_readiness?.first_week_plan !== null
    && planning.first_week_readiness?.first_week_plan !== undefined;

  let assessmentStep: FirstSessionStep;
  if (!assessmentContentReady) {
    assessmentStep = {
      id: "assessment",
      title: "Reviewed assessment",
      state: preparedAssessmentAvailable ? "your_action" : "system_action",
      detail: preparedAssessmentAvailable
        ? "AGAS has prepared a complete assessment release. Review its exact scope, evidence, and limitations, then decide whether to approve it for the owner-only alpha."
        : preparedAssessmentConflict
          ? "A prepared assessment conflicts with existing immutable governance history. AGAS must resolve that conflict before asking you to assess."
          : "AGAS still needs a scientifically reviewed self-administered assessment protocol. This is not another form you missed.",
    };
  } else if (!eligibilityReady) {
    assessmentStep = {
      id: "assessment",
      title: "Reviewed assessment",
      state: "your_action",
      detail:
        "Complete the factual current-readiness check below. AGAS—not the form—derives the narrow, time-bounded decision.",
    };
  } else if (needsEnvironmentAction) {
    assessmentStep = {
      id: "assessment",
      title: "Reviewed assessment",
      state: "your_action",
      detail:
        assessment.status === "environment_required"
          ? "The assessment needs a persisted training environment. Complete the environment information below before selection."
          : "The selected assessment needs equipment that is not currently reported available. Update the environment below, then rerun selection.",
    };
  } else if (introductoryExposureNeeded && !introductoryExposureDoseReady) {
    assessmentStep = {
      id: "assessment",
      title: "Reviewed introductory exposure",
      state: preparedExposureAuthorityAvailable ? "your_action" : "system_action",
      detail: preparedExposureAuthorityAvailable
        ? "AGAS has prepared the exact low-intensity jump dose and safety limits. Review that authority bundle before it can become your training instruction."
        : preparedExposureAuthorityConflict
          ? "The prepared introductory-exposure authority conflicts with immutable governance history. AGAS must resolve that conflict before asking you to jump."
          : "A reviewed introductory-exposure dose and safety authority are required before AGAS can ask you to perform the jump exposure.",
    };
  } else if (introductoryExposureNeeded) {
    assessmentStep = {
      id: "assessment",
      title: "Introductory jump exposure",
      state: introductoryExposureRecordedToday ? "waiting" : "your_action",
      detail: introductoryExposureRecordedToday
        ? `Exposure day ${qualifyingExposureDays} of ${requiredExposureDays} is recorded. The next qualifying exposure must happen on a different calendar day; return tomorrow or later.`
        : `Complete the governed low-intensity jump exposure below. You have ${qualifyingExposureDays} of ${requiredExposureDays} qualifying exposure days.`,
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
    : planningQueueItem
      ? {
          id: "plan",
          title: "Governed first plan",
          state: planningQueueItem.readiness === "ready" ? "your_action" : "system_action",
          detail: planningQueueDetail(planningQueueItem),
        }
      : {
        id: "plan",
        title: "Governed first plan",
        state: hasEstimate && preparedPlanningAvailable ? "your_action" : hasEstimate
          ? "system_action"
          : "waiting",
        detail: hasEstimate
          ? preparedPlanningAvailable
            ? "AGAS has prepared one or more exact planning-authority groups. Review their scope and limitations before athlete-specific planning begins."
            : preparedPlanningConflict
              ? "Prepared planning authority conflicts must be resolved before athlete-specific planning can begin."
              : "Planning authorities must turn the measured state into priorities, a block, and a feasible week."
          : "Planning starts only after a current capability estimate exists.",
      };

  const sessionStep: FirstSessionStep = hasScheduledWeek
    ? {
        id: "session",
        title: "First training session",
        state: "your_action",
        detail:
          "A session is scheduled. When it is time to train, complete its pre-session safety check and record what you actually perform.",
      }
    : {
        id: "session",
        title: "First training session",
        state: "waiting",
        detail: "This appears automatically after a reviewed, feasible week is created.",
      };

  const userAction = [assessmentStep, estimateStep, planStep]
    .find((step) => step.state === "your_action");
  let nextAction: FirstSessionPath["next_action"] = null;
  if (hasScheduledWeek) {
    nextAction = {
      href: "#week-title",
      label: "Open your scheduled sessions",
    };
  } else {
    if (!assessmentContentReady) {
      nextAction = {
        href: athleteReviewHref("/review/assessments", athleteId),
        label: preparedAssessmentAvailable
          ? "Review the prepared assessment"
          : preparedAssessmentConflict
            ? "Inspect the assessment conflict"
            : "Inspect assessment governance",
      };
    } else if (introductoryExposureNeeded && !introductoryExposureDoseReady) {
      nextAction = {
        href: athleteReviewHref("/review/planning-authorities", athleteId),
        label: preparedExposureAuthorityAvailable
          ? "Review the introductory exposure"
          : preparedExposureAuthorityConflict
            ? "Inspect the exposure-authority conflict"
            : "Inspect exposure governance",
      };
    } else if (userAction?.id === "assessment" && needsEnvironmentAction) {
      nextAction = {
        href: "#environment-title",
        label: "Update the assessment environment",
      };
    } else if (userAction?.id === "assessment" || userAction?.id === "estimate") {
      nextAction = {
        href: "#assessment-title",
        label: introductoryExposureNeeded
          ? `Complete exposure day ${Math.min(qualifyingExposureDays + 1, requiredExposureDays)}`
          : "Continue the assessment step",
      };
    } else if (introductoryExposureRecordedToday) {
      nextAction = {
        href: "#assessment-title",
        label: "Review your exposure progress",
      };
    } else if (planStep.state === "your_action" || planStep.state === "system_action") {
      nextAction = planning.status === "planning_authorities_required"
        ? {
            href: athleteReviewHref("/review/planning-authorities", athleteId),
            label: preparedPlanningAvailable
              ? "Review the prepared planning authorities"
              : preparedPlanningConflict
                ? "Inspect the planning-authority conflict"
                : "Inspect planning governance",
          }
        : planningQueueItem
          ? {
              href: planningReviewHref(planningQueueItem),
              label: planningQueueItem.readiness === "ready"
                ? planningStageActionLabels[planningQueueItem.workflow_stage]
                : "Inspect the current planning blocker",
            }
          : {
              href: athleteReviewHref("/review/queue", athleteId),
              label: "Continue the governed planning review",
            };
    }
  }
  const heading = hasScheduledWeek
    ? "Your training week is ready."
    : introductoryExposureRecordedToday
      ? "Today’s exposure is recorded."
    : userAction
      ? "You have one clear next step."
      : "Your profile is saved; AGAS still owes you the training path.";
  const message = hasScheduledWeek
    ? "Open the scheduled session below when you are ready to train."
    : introductoryExposureNeeded && !introductoryExposureDoseReady
      ? assessmentStep.detail
    : introductoryExposureRecordedToday
      ? assessmentStep.detail
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
    next_action: nextAction,
  };
}
