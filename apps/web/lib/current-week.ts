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

export type Confidence = "unknown" | "low" | "moderate" | "high";

export interface ProvenanceInput {
  recorded_by: string;
  source_system: string;
  ingestion_method: string;
}

export interface SafetyCheckCommand {
  safety_policy_id: string;
  timing: "pre_session";
  readiness: "ready" | "limited" | "not_ready";
  unusual_soreness: boolean;
  major_sleep_disruption: boolean;
  major_schedule_limitation: boolean;
  signals: [];
  note: string | null;
  reported_at: string;
  decided_at: string;
  reliability: Confidence;
  provenance: ProvenanceInput;
}

export interface SetPerformanceInput {
  set_index: number;
  performed: boolean;
  target_completed: boolean;
  actual_repetitions?: number;
  actual_duration_seconds?: number;
  effort_rpe?: number;
}

export interface SessionExecutionCommand {
  pre_session_safety_decision_id: string;
  status: "completed" | "partial" | "not_started";
  started_at: string | null;
  ended_at: string | null;
  items: Array<{
    prescription_id: string;
    status: "completed" | "partial" | "not_started";
    performances: SetPerformanceInput[];
    item_rpe: number | null;
  }>;
  applied_modifications: string[];
  session_rpe: number | null;
  note: string | null;
  logged_at: string;
  adherence_calculated_at: string;
  reliability: Confidence;
  provenance: ProvenanceInput;
}

export interface PrescriptionLogDraft {
  prescriptionId: string;
  performedSets: number;
  actualDosePerSet: number;
  itemRpe: number | null;
}

export const pwaProvenance: ProvenanceInput = {
  recorded_by: "unverified-athlete-user",
  source_system: "agas-web",
  ingestion_method: "interactive-form",
};

export class CurrentWeekRequestError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "CurrentWeekRequestError";
  }
}

export class SessionWriteRequestError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "SessionWriteRequestError";
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

async function postSessionCommand<T>(
  url: string,
  command: SafetyCheckCommand | SessionExecutionCommand,
  fetcher: typeof fetch,
): Promise<T> {
  const response = await fetcher(url, {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(command),
  });
  if (!response.ok) {
    let message = `Session write failed (${response.status})`;
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === "string") message = body.detail;
    } catch {
      // Retain the status-based message when the server does not return JSON.
    }
    throw new SessionWriteRequestError(message, response.status);
  }
  return (await response.json()) as T;
}

export async function submitSafetyCheck(
  apiBaseUrl: string,
  weeklyPlanId: string,
  plannedSessionId: string,
  command: SafetyCheckCommand,
  fetcher: typeof fetch = fetch,
): Promise<{ decision: { decision_id?: string; id?: string; outcome: string } }> {
  const baseUrl = apiBaseUrl.replace(/\/$/, "");
  return postSessionCommand(
    `${baseUrl}/v1/weekly-plans/${encodeURIComponent(weeklyPlanId)}/sessions/${encodeURIComponent(plannedSessionId)}/safety-checks`,
    command,
    fetcher,
  );
}

export async function submitSessionExecution(
  apiBaseUrl: string,
  weeklyPlanId: string,
  plannedSessionId: string,
  command: SessionExecutionCommand,
  fetcher: typeof fetch = fetch,
): Promise<{ execution: { id: string; status: string } }> {
  const baseUrl = apiBaseUrl.replace(/\/$/, "");
  return postSessionCommand(
    `${baseUrl}/v1/weekly-plans/${encodeURIComponent(weeklyPlanId)}/sessions/${encodeURIComponent(plannedSessionId)}/executions`,
    command,
    fetcher,
  );
}

export function buildExecutionCommand({
  session,
  drafts,
  safetyDecisionId,
  requiredModifications,
  startedAt,
  endedAt,
  sessionRpe,
  note,
  reliability,
  recordedAt = new Date(),
}: {
  session: PlannedSessionProjection;
  drafts: PrescriptionLogDraft[];
  safetyDecisionId: string;
  requiredModifications: string[];
  startedAt: Date | null;
  endedAt: Date | null;
  sessionRpe: number | null;
  note: string | null;
  reliability: Confidence;
  recordedAt?: Date;
}): SessionExecutionCommand {
  const draftsById = new Map(drafts.map((draft) => [draft.prescriptionId, draft]));
  const items = session.prescriptions.map((prescription) => {
    const draft = draftsById.get(prescription.prescription_id);
    if (!draft) throw new Error(`Missing log entry for ${prescription.exercise_name}.`);
    if (!Number.isInteger(draft.performedSets) || draft.performedSets < 0 || draft.performedSets > prescription.sets) {
      throw new Error(`${prescription.exercise_name} performed sets must be between 0 and ${prescription.sets}.`);
    }
    if (!Number.isInteger(draft.actualDosePerSet) || draft.actualDosePerSet < 0) {
      throw new Error(`${prescription.exercise_name} actual dose must be a non-negative whole number.`);
    }

    const target = prescription.repetitions_per_set ?? prescription.duration_seconds;
    if (target === null) throw new Error(`${prescription.exercise_name} has no executable dose.`);
    const targetCompleted = draft.actualDosePerSet >= target;
    const performances: SetPerformanceInput[] = Array.from(
      { length: prescription.sets },
      (_, index) => {
        const performed = index < draft.performedSets;
        const result: SetPerformanceInput = {
          set_index: index + 1,
          performed,
          target_completed: performed && targetCompleted,
        };
        if (performed) {
          if (prescription.repetitions_per_set !== null) {
            result.actual_repetitions = draft.actualDosePerSet;
          } else {
            result.actual_duration_seconds = draft.actualDosePerSet;
          }
          if (draft.itemRpe !== null) result.effort_rpe = draft.itemRpe;
        }
        return result;
      },
    );
    const status =
      draft.performedSets === 0
        ? "not_started"
        : draft.performedSets === prescription.sets && targetCompleted
          ? "completed"
          : "partial";
    return {
      prescription_id: prescription.prescription_id,
      status,
      performances: status === "not_started" ? [] : performances,
      item_rpe: status === "not_started" ? null : draft.itemRpe,
    } as const;
  });

  const itemStatuses = new Set(items.map((item) => item.status));
  const status = itemStatuses.size === 1 && itemStatuses.has("completed")
    ? "completed"
    : itemStatuses.size === 1 && itemStatuses.has("not_started")
      ? "not_started"
      : "partial";
  if (status !== "not_started") {
    if (!startedAt || !endedAt) throw new Error("Started sessions require actual start and end times.");
    if (!Number.isFinite(startedAt.getTime()) || !Number.isFinite(endedAt.getTime())) {
      throw new Error("Workout start and end must be valid times.");
    }
    if (endedAt <= startedAt) throw new Error("Workout end must be later than workout start.");
  }
  const loggedAt = new Date(Math.max(recordedAt.getTime(), (endedAt?.getTime() ?? 0) + 1));
  const loggedIso = loggedAt.toISOString();
  return {
    pre_session_safety_decision_id: safetyDecisionId,
    status,
    started_at: status === "not_started" ? null : startedAt!.toISOString(),
    ended_at: status === "not_started" ? null : endedAt!.toISOString(),
    items,
    applied_modifications: [...requiredModifications],
    session_rpe: status === "not_started" ? null : sessionRpe,
    note: note?.trim() || null,
    logged_at: loggedIso,
    adherence_calculated_at: loggedIso,
    reliability,
    provenance: pwaProvenance,
  };
}
