"use client";

import { useEffect, useState } from "react";

import {
  fetchPlanningStatus,
  type PlanningStatus,
  type PlanningStatusProjection,
} from "@/lib/planning-status";

const statusLabels: Record<PlanningStatus, string> = {
  capability_estimate_required: "Estimate required",
  capability_estimate_stale: "Reassessment required",
  planning_authorities_required: "Authorities required",
  planning_context_review_required: "Context review required",
  resource_demand_preparation_required: "Resource demands required",
  resource_allocation_policy_required: "Allocation policy required",
  exercise_resolution_review_required: "Exercise review required",
  block_context_review_required: "Block context review required",
  block_infeasible: "Block infeasible",
  block_selection_review_required: "Block selection required",
  weekly_scheduling_policy_required: "Approved scheduling policy required",
  weekly_plan_context_review_required: "Week 1 context required",
  first_week_created: "Week 1 created",
  first_week_infeasible: "Week 1 infeasible",
  first_week_selection_review_required: "Week 1 selection required",
};

export function PlanningStatusPanel({
  apiBaseUrl,
  athleteId,
}: {
  apiBaseUrl: string;
  athleteId: string;
}) {
  const [projection, setProjection] = useState<PlanningStatusProjection | null>(null);
  const [message, setMessage] = useState("");

  useEffect(() => {
    let active = true;
    void fetchPlanningStatus(apiBaseUrl, athleteId)
      .then((result) => {
        if (active) {
          setProjection(result);
          setMessage("");
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setMessage(error instanceof Error ? error.message : "Unable to load planning status.");
        }
      });
    return () => {
      active = false;
    };
  }, [apiBaseUrl, athleteId]);

  return (
    <section className="assessment-panel" aria-labelledby="planning-status-title">
      <header className="assessment-panel__heading">
        <div>
          <p className="eyebrow">Planning handoff</p>
          <h2 id="planning-status-title">From measured state to a governed strategy.</h2>
        </div>
        {projection ? (
          <span className={`status-badge status-badge--${projection.status}`}>
            {statusLabels[projection.status]}
          </span>
        ) : null}
      </header>

      {!projection && !message ? <p className="form-help">Loading planning state…</p> : null}
      {message ? <p className="form-error" role="alert">{message}</p> : null}
      {projection ? (
        <>
          <p className="assessment-message">{projection.message}</p>
          <dl className="assessment-summary">
            <div>
              <dt>Current estimates</dt>
              <dd>{projection.current_capability_estimate_count}</dd>
            </div>
            <div>
              <dt>Stale estimates</dt>
              <dd>{projection.stale_capability_estimate_count}</dd>
            </div>
            <div>
              <dt>Approved floors</dt>
              <dd>{projection.approved_compatible_competency_floor_count}</dd>
            </div>
            <div>
              <dt>Approved policies</dt>
              <dd>{projection.approved_priority_policy_count}</dd>
            </div>
          </dl>
          {projection.first_block_readiness ? (
            <dl className="assessment-summary planning-block-summary">
              <div>
                <dt>Demand coverage</dt>
                <dd>
                  {projection.first_block_readiness.priorities_with_resource_demand_count}/
                  {projection.first_block_readiness.strategy_priority_count}
                </dd>
              </div>
              <div>
                <dt>Block eligible</dt>
                <dd>
                  {projection.first_block_readiness.block_eligible_priority_count}/
                  {projection.first_block_readiness.strategy_priority_count}
                </dd>
              </div>
              <div>
                <dt>Demand history</dt>
                <dd>{projection.first_block_readiness.historical_resource_demand_count}</dd>
              </div>
              <div>
                <dt>Blocks</dt>
                <dd>{projection.first_block_readiness.block_plan_count}</dd>
              </div>
            </dl>
          ) : null}
          {projection.first_week_readiness ? (
            <dl className="assessment-summary planning-week-summary">
              <div>
                <dt>Active allocations</dt>
                <dd>{projection.first_week_readiness.active_resource_allocation_count}</dd>
              </div>
              <div>
                <dt>Approved schedule policies</dt>
                <dd>{projection.first_week_readiness.weekly_scheduling_policy_count}</dd>
              </div>
              <div>
                <dt>Week 1 plans</dt>
                <dd>{projection.first_week_readiness.first_week_plan_count}</dd>
              </div>
              <div>
                <dt>Scheduled sessions</dt>
                <dd>
                  {projection.first_week_readiness.first_week_plan?.scheduled_session_count ?? 0}
                </dd>
              </div>
            </dl>
          ) : null}
          {projection.requirements.length > 0 ? (
            <ul className="planning-requirements" aria-label="Planning requirements">
              {projection.requirements.map((requirement) => (
                <li
                  className={requirement.satisfied ? "planning-requirement--ready" : undefined}
                  key={requirement.code}
                >
                  <span aria-hidden="true">{requirement.satisfied ? "✓" : "○"}</span>
                  <span>{requirement.label}</span>
                  <strong>{requirement.satisfied ? "Ready" : "Pending"}</strong>
                </li>
              ))}
            </ul>
          ) : null}
          {projection.initial_strategy ? (
            <div>
              {projection.first_week_readiness?.first_week_plan ? (
                <p className="form-help">
                  Week 1 {projection.first_week_readiness.first_week_plan.status} · {" "}
                  {projection.first_week_readiness.first_week_plan.scheduled_session_count} session(s) · {" "}
                  {projection.first_week_readiness.first_week_plan.scheduling_issue_count} issue(s) · {" "}
                  {new Date(
                    `${projection.first_week_readiness.first_week_plan.week_start}T00:00:00`,
                  ).toLocaleDateString()}
                  {" – "}
                  {new Date(
                    `${projection.first_week_readiness.first_week_plan.week_end}T00:00:00`,
                  ).toLocaleDateString()}
                </p>
              ) : null}
              {projection.first_block_readiness?.block_plan ? (
                <p className="form-help">
                  Block {projection.first_block_readiness.block_plan.status} · {" "}
                  {projection.first_block_readiness.block_plan.duration_weeks} weeks · {" "}
                  {projection.first_block_readiness.block_plan.weekly_budget_minutes} min/week · {" "}
                  starts {" "}
                  {new Date(
                    `${projection.first_block_readiness.block_plan.starts_on}T00:00:00`,
                  ).toLocaleDateString()}
                </p>
              ) : null}
              <p className="form-help">
                Strategy horizon {projection.initial_strategy.horizon_months} months · next review {" "}
                {new Date(projection.initial_strategy.next_review_at).toLocaleDateString()} · rule {" "}
                {projection.initial_strategy.rule_version}
              </p>
            </div>
          ) : (
            <p className="form-help">
              {projection.uncovered_current_capability_estimate_count > 0
                ? `${projection.uncovered_current_capability_estimate_count} current estimate(s) do not have a compatible approved floor. `
                : "All current estimates have compatible approved floor coverage. "}
              Scientific authorities and athlete-specific planning context are reviewed outside
              this athlete-facing screen.
            </p>
          )}
        </>
      ) : null}
    </section>
  );
}
