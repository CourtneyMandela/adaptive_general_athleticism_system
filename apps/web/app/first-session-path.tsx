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
    void Promise.allSettled([
      fetchAssessmentWorkflow(apiBaseUrl, athleteId),
      fetchPlanningStatus(apiBaseUrl, athleteId),
      fetchAssessmentGovernanceCandidates(apiBaseUrl),
    ])
      .then(([assessmentResult, planningResult, candidateResult]) => {
        if (assessmentResult.status === "rejected") throw assessmentResult.reason;
        if (planningResult.status === "rejected") throw planningResult.reason;
        const assessmentReview = candidateResult.status === "fulfilled"
          ? {
              available_candidate_count: candidateResult.value.items.filter(
                (item) => item.status === "available",
              ).length,
              conflict_candidate_count: candidateResult.value.items.filter(
                (item) => item.status === "conflict",
              ).length,
            }
          : undefined;
        if (active) {
          setProjection(buildFirstSessionPath(
            assessmentResult.value,
            planningResult.value,
            hasScheduledWeek,
            athleteId,
            assessmentReview,
          ));
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
