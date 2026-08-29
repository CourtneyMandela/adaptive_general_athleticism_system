import { authorizedHeaders } from "./identity";

export type PlanningStatus =
  | "capability_estimate_required"
  | "capability_estimate_stale"
  | "planning_authorities_required"
  | "planning_context_review_required"
  | "resource_demand_preparation_required"
  | "resource_allocation_policy_required"
  | "exercise_resolution_review_required"
  | "block_context_review_required"
  | "block_infeasible"
  | "block_selection_review_required"
  | "weekly_scheduling_policy_required"
  | "weekly_plan_context_review_required"
  | "first_week_created"
  | "first_week_infeasible"
  | "first_week_selection_review_required";

export type PlanningRequirementCode =
  | "approved_priority_policy_required"
  | "approved_compatible_competency_floor_required"
  | "reviewed_candidate_context_required"
  | "resource_demand_coverage_required"
  | "block_eligible_resolution_required"
  | "resource_allocation_policy_required"
  | "reviewed_block_context_required"
  | "unambiguous_block_selection_required"
  | "weekly_scheduling_policy_required"
  | "explicit_prescription_context_required"
  | "explicit_session_composition_required"
  | "confirmed_weekly_availability_required"
  | "unambiguous_first_week_selection_required";

export interface PlanningStatusProjection {
  athlete_id: string;
  athlete_display_name: string;
  as_of: string;
  status: PlanningStatus;
  message: string;
  capability_estimate_count: number;
  current_capability_estimate_count: number;
  stale_capability_estimate_count: number;
  approved_priority_policy_count: number;
  approved_compatible_competency_floor_count: number;
  covered_current_capability_estimate_count: number;
  uncovered_current_capability_estimate_count: number;
  requirements: Array<{
    code: PlanningRequirementCode;
    label: string;
    satisfied: boolean;
    matching_record_count: number;
  }>;
  initial_strategy: {
    strategy_id: string;
    generated_at: string;
    next_review_at: string;
    horizon_months: number;
    rule_version: string;
    priority_count: number;
  } | null;
  first_block_readiness: {
    strategy_priority_count: number;
    priorities_with_resource_demand_count: number;
    block_eligible_priority_count: number;
    historical_resource_demand_count: number;
    full_resolution_count: number;
    partial_resolution_count: number;
    infeasible_resolution_count: number;
    resource_allocation_policy_count: number;
    block_plan_count: number;
    block_plan: {
      block_plan_id: string;
      starts_on: string;
      ends_on: string;
      duration_weeks: number;
      weekly_budget_minutes: number;
      status: "full" | "partial" | "infeasible";
      allocation_count: number;
      rule_version: string;
    } | null;
  } | null;
  first_week_readiness: {
    active_resource_allocation_count: number;
    weekly_scheduling_policy_count: number;
    first_week_plan_count: number;
    first_week_plan: {
      weekly_plan_id: string;
      week_start: string;
      week_end: string;
      status: "feasible" | "infeasible";
      prescription_count: number;
      session_template_count: number;
      availability_window_count: number;
      scheduled_session_count: number;
      scheduling_issue_count: number;
      scheduling_policy_id: string;
      scheduling_policy_review_id: string | null;
      rule_version: string;
    } | null;
  } | null;
  projection_version: string;
}

export class PlanningStatusRequestError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "PlanningStatusRequestError";
  }
}

export async function fetchPlanningStatus(
  apiBaseUrl: string,
  athleteId: string,
  fetcher: typeof fetch = fetch,
): Promise<PlanningStatusProjection> {
  const response = await fetcher(
    `${apiBaseUrl.replace(/\/$/, "")}/v1/athletes/${encodeURIComponent(athleteId)}/planning-status`,
    { headers: authorizedHeaders({ Accept: "application/json" }) },
  );
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new PlanningStatusRequestError(
      payload?.detail ?? `Planning status request failed with ${response.status}.`,
      response.status,
    );
  }
  return (await response.json()) as PlanningStatusProjection;
}
