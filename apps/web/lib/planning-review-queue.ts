import { authorizedHeaders, reviewerDevelopmentAccessToken } from "./identity";

export type PlanningWorkflowStage =
  | "initial_planning"
  | "resource_demands"
  | "block_creation"
  | "first_week";

export interface PlanningReviewQueueItem {
  workflow_stage: PlanningWorkflowStage;
  status: string;
  readiness: "ready" | "blocked";
  athlete_id: string;
  athlete_display_name: string;
  strategy_id: string | null;
  block_id: string | null;
  message: string;
  issues: string[];
}

export interface PlanningReviewQueueProjection {
  projected_at: string;
  items: PlanningReviewQueueItem[];
  projection_version: string;
}

export class PlanningReviewQueueError extends Error {
  constructor(message: string, readonly status?: number) {
    super(message);
    this.name = "PlanningReviewQueueError";
  }
}

function normalizedBaseUrl(value: string): string {
  return value.replace(/\/$/, "");
}

async function responseError(response: Response): Promise<PlanningReviewQueueError> {
  let message = `Request failed with status ${response.status}.`;
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string" && body.detail.trim()) message = body.detail;
  } catch {
    // Preserve the status-based fallback for non-JSON responses.
  }
  return new PlanningReviewQueueError(message, response.status);
}

function isQueueItem(value: unknown): value is PlanningReviewQueueItem {
  if (!value || typeof value !== "object") return false;
  const item = value as Partial<PlanningReviewQueueItem>;
  const commonFieldsAreValid = (
    (["initial_planning", "resource_demands", "block_creation", "first_week"] as unknown[])
      .includes(item.workflow_stage)
    && (["ready", "blocked"] as unknown[]).includes(item.readiness)
    && typeof item.status === "string"
    && typeof item.athlete_id === "string"
    && typeof item.athlete_display_name === "string"
    && typeof item.message === "string"
    && Array.isArray(item.issues)
  );
  if (!commonFieldsAreValid) return false;
  if (
    item.workflow_stage === "resource_demands"
    || item.workflow_stage === "block_creation"
    || item.workflow_stage === "first_week"
  ) {
    if (typeof item.strategy_id !== "string") return false;
  }
  return item.workflow_stage !== "first_week" || typeof item.block_id === "string";
}

export function planningReviewHref(item: PlanningReviewQueueItem): string {
  if (item.workflow_stage === "initial_planning") {
    return `/review?athleteId=${encodeURIComponent(item.athlete_id)}`;
  }
  if (item.workflow_stage === "resource_demands") {
    if (!item.strategy_id) throw new PlanningReviewQueueError("Resource work lacks a strategy ID.");
    return `/review/resource-demands?strategyId=${encodeURIComponent(item.strategy_id)}`;
  }
  if (item.workflow_stage === "block_creation") {
    if (!item.strategy_id) throw new PlanningReviewQueueError("Block work lacks a strategy ID.");
    return `/review/blocks?strategyId=${encodeURIComponent(item.strategy_id)}`;
  }
  if (!item.block_id) throw new PlanningReviewQueueError("First-week work lacks a block ID.");
  return `/review/weeks?blockId=${encodeURIComponent(item.block_id)}`;
}

export async function fetchPlanningReviewQueue(
  apiBaseUrl: string,
  fetcher: typeof fetch = fetch,
): Promise<PlanningReviewQueueProjection> {
  const response = await fetcher(
    `${normalizedBaseUrl(apiBaseUrl)}/v1/operator/planning-review-queue`,
    { headers: authorizedHeaders({ Accept: "application/json" }, reviewerDevelopmentAccessToken) },
  );
  if (!response.ok) throw await responseError(response);
  const body = (await response.json()) as Partial<PlanningReviewQueueProjection>;
  if (
    !body
    || !Array.isArray(body.items)
    || !body.items.every(isQueueItem)
    || typeof body.projected_at !== "string"
    || typeof body.projection_version !== "string"
  ) {
    throw new PlanningReviewQueueError("Planning review queue response is invalid.", response.status);
  }
  return body as PlanningReviewQueueProjection;
}
