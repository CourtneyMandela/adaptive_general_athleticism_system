export type SessionDisplayStatus =
  | "scheduled"
  | "cleared"
  | "modified"
  | "held"
  | "needs_attention"
  | "completed"
  | "partial"
  | "not_started"
  | "stopped_safety";

export interface AdherenceProjection {
  adherence_id: string;
  performed_sets: number;
  prescribed_sets: number;
  actual_dose_total: number;
  prescribed_dose_total: number;
  dose_unit: string;
  set_completion_ratio: number;
  dose_completion_ratio: number;
}

export interface ProgressionProjection {
  decision_id: string;
  outcome: string;
  adjustment_description: string | null;
  decided_at: string;
}

export interface PrescriptionProjection {
  order_index: number;
  section: string;
  prescription_id: string;
  exercise_id: string;
  exercise_name: string;
  adaptation_id: string;
  adaptation_name: string;
  reason_for_inclusion: string;
  sets: number;
  repetitions_per_set: number | null;
  duration_seconds: number | null;
  intensity_targets: string[];
  rest_seconds: number;
  adherence: AdherenceProjection | null;
  progression: ProgressionProjection | null;
}

export interface PlannedSessionProjection {
  planned_session_id: string;
  session_template_id: string;
  session_name: string;
  starts_at: string;
  ends_at: string;
  planned_duration_minutes: number;
  environment_id: string;
  environment_name: string;
  status: SessionDisplayStatus;
  pre_session_safety: {
    decision_id: string;
    outcome: string;
    required_modifications: string[];
    decided_at: string;
  } | null;
  execution: {
    execution_id: string;
    status: string;
    session_rpe: number | null;
    logged_at: string;
    post_session_safety_outcomes: string[];
  } | null;
  prescriptions: PrescriptionProjection[];
}

export interface CurrentWeekProjection {
  athlete_id: string;
  athlete_display_name: string;
  as_of: string;
  week: {
    weekly_plan_id: string;
    block_plan_id: string;
    week_start: string;
    week_end: string;
    block_week: number;
    status: string;
    sessions: PlannedSessionProjection[];
  } | null;
}

export class CurrentWeekRequestError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "CurrentWeekRequestError";
  }
}

export function localIsoDate(value = new Date()): string {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function shiftIsoDate(value: string, days: number): string {
  const shifted = new Date(`${value}T12:00:00`);
  shifted.setDate(shifted.getDate() + days);
  return localIsoDate(shifted);
}

export function isUuid(value: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(
    value.trim(),
  );
}

export function formatDose(prescription: PrescriptionProjection): string {
  if (prescription.repetitions_per_set !== null) {
    return `${prescription.sets} × ${prescription.repetitions_per_set}`;
  }
  const seconds = prescription.duration_seconds ?? 0;
  if (seconds >= 60 && seconds % 60 === 0) {
    return `${prescription.sets} × ${seconds / 60} min`;
  }
  return `${prescription.sets} × ${seconds} sec`;
}

export function sessionStatusLabel(status: SessionDisplayStatus): string {
  const labels: Record<SessionDisplayStatus, string> = {
    scheduled: "Scheduled",
    cleared: "Safety cleared",
    modified: "Modified",
    held: "On hold",
    needs_attention: "Needs attention",
    completed: "Completed",
    partial: "Partially completed",
    not_started: "Not completed",
    stopped_safety: "Stopped for safety",
  };
  return labels[status];
}

export async function fetchCurrentWeek(
  apiBaseUrl: string,
  athleteId: string,
  on: string,
  fetcher: typeof fetch = fetch,
): Promise<CurrentWeekProjection> {
  const baseUrl = apiBaseUrl.replace(/\/$/, "");
  const response = await fetcher(
    `${baseUrl}/v1/athletes/${encodeURIComponent(athleteId)}/current-week?on=${encodeURIComponent(on)}`,
    { headers: { Accept: "application/json" } },
  );
  if (!response.ok) {
    let message = `Current week request failed (${response.status})`;
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === "string") message = body.detail;
    } catch {
      // Retain the status-based message when the server does not return JSON.
    }
    throw new CurrentWeekRequestError(message, response.status);
  }
  return (await response.json()) as CurrentWeekProjection;
}
