"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { fetchAssessmentWorkflow } from "@/lib/assessment";
import { fetchAssessmentGovernanceCandidates } from "@/lib/assessment-governance";
import {
  buildFirstSessionPath,
  type FirstSessionPath as FirstSessionPathProjection,
  type FirstSessionStepState,
} from "@/lib/first-session-path";
import { fetchPlanningStatus } from "@/lib/planning-status";
import { fetchPlanningGovernanceCandidates } from "@/lib/planning-governance";
import { fetchCompetencyFloorCandidates } from "@/lib/competency-floor-governance";
import { fetchResourceGovernanceCandidates } from "@/lib/resource-governance";
import { fetchTrainingConstructionCandidates } from "@/lib/training-construction-governance";

const stateLabels: Record<FirstSessionStepState, string> = {
  complete: "Done",
  your_action: "Your next step",
  system_action: "AGAS work needed",
  waiting: "Waiting",
};

export function FirstSessionPath({
  apiBaseUrl,
  athleteId,
  hasScheduledWeek,
}: {
  apiBaseUrl: string;
  athleteId: string;
  hasScheduledWeek: boolean;
}) {
  const [projection, setProjection] = useState<FirstSessionPathProjection | null>(null);
  const [message, setMessage] = useState("");

  useEffect(() => {
    let active = true;
    async function loadPath() {
      const [assessment, planning] = await Promise.all([
        fetchAssessmentWorkflow(apiBaseUrl, athleteId),
        fetchPlanningStatus(apiBaseUrl, athleteId),
      ]);
      const assessmentCandidateResult = assessment.approved_self_administered_protocol_count === 0
        ? await Promise.allSettled([fetchAssessmentGovernanceCandidates(apiBaseUrl)])
        : [];
      const assessmentCandidates = assessmentCandidateResult[0];
      const assessmentReview = assessmentCandidates?.status === "fulfilled"
        ? {
            available_candidate_count: assessmentCandidates.value.items.filter(
              (item) => item.status === "available",
            ).length,
            conflict_candidate_count: assessmentCandidates.value.items.filter(
              (item) => item.status === "conflict",
            ).length,
          }
        : undefined;

      let planningReview;
      if (
        planning.current_capability_estimate_count > 0
        && planning.status === "planning_authorities_required"
      ) {
        const candidateResults = await Promise.allSettled([
          fetchPlanningGovernanceCandidates(apiBaseUrl),
          fetchCompetencyFloorCandidates(apiBaseUrl),
          fetchResourceGovernanceCandidates(apiBaseUrl),
          fetchTrainingConstructionCandidates(apiBaseUrl),
        ]);
        const statuses = candidateResults.flatMap((result) =>
          result.status === "fulfilled" ? result.value.items.map((item) => item.status) : []
        );
        planningReview = {
          available_candidate_count: statuses.filter((status) => status === "available").length,
          blocked_candidate_count: statuses.filter((status) => status === "blocked").length,
          conflict_candidate_count: statuses.filter((status) => status === "conflict").length,
        };
      }

      return buildFirstSessionPath(
        assessment,
        planning,
        hasScheduledWeek,
        athleteId,
        assessmentReview,
        planningReview,
      );
    }

    void loadPath()
      .then((result) => {
        if (active) {
          setProjection(result);
          setMessage("");
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setMessage(
            error instanceof Error
              ? error.message
              : "Unable to load the path to your first session.",
          );
        }
      });
    return () => {
      active = false;
    };
  }, [apiBaseUrl, athleteId, hasScheduledWeek]);

  return (
    <section className="first-session-path" aria-labelledby="first-session-path-title">
      <header>
        <div>
          <p className="eyebrow">Path to your first session</p>
          <h2 id="first-session-path-title">
            {projection?.heading ?? "Checking what comes next…"}
          </h2>
        </div>
      </header>

      {projection ? <p className="first-session-path__message">{projection.message}</p> : null}
      {!projection && !message ? <p className="form-help">Loading your onboarding progress…</p> : null}
      {message ? <p className="form-error" role="alert">{message}</p> : null}

      {projection?.next_action ? (
        <Link className="first-session-path__action" href={projection.next_action.href}>
          {projection.next_action.label} →
        </Link>
      ) : null}

      {projection ? (
        <ol className="first-session-steps">
          {projection.steps.map((step, index) => (
            <li className={`first-session-step first-session-step--${step.state}`} key={step.id}>
              <span className="first-session-step__marker" aria-hidden="true">
                {step.state === "complete" ? "✓" : index + 1}
              </span>
              <div>
                <strong>{step.title}</strong>
                <p>{step.detail}</p>
              </div>
              <span className="first-session-step__state">{stateLabels[step.state]}</span>
            </li>
          ))}
        </ol>
      ) : null}
    </section>
  );
}
