import { authorizedHeaders } from "./identity";

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

export interface ProgressionActionProjection {
  status:
    | "awaiting_execution"
    | "awaiting_post_session_safety"
    | "ready"
    | "manual_configuration_required"
    | "policy_unavailable"
    | "completed";
  rule_reference: string;
  progression_policy_id: string | null;
  adjustment_dimension: string | null;
  adjustment_description: string | null;
  reason: string;
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
  progression_action: ProgressionActionProjection;
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

export type WeeklyReviewStatus =
  | "awaiting_sessions"
  | "awaiting_post_session_safety"
  | "awaiting_progression"
  | "manual_configuration_required"
  | "ready_to_prepare_next_week"
  | "environment_revision_required"
  | "ready_to_finalize_next_week"
  | "next_week_already_prepared"
  | "block_complete";

export interface WeeklyAvailabilityWindowProjection {
  environment_id: string;
  environment_name: string;
  starts_at: string;
  ends_at: string;
}

export interface WeekProjection {
  weekly_plan_id: string;
  block_plan_id: string;
  week_start: string;
  week_end: string;
  block_week: number;
  status: string;
  availability: {
    source_observation_ids: string[];
    rule_version: string;
    windows: WeeklyAvailabilityWindowProjection[];
  };
  review: {
    status: WeeklyReviewStatus;
    reason: string;
    scheduled_sessions: number;
    recorded_sessions: number;
    completed_sessions: number;
    post_session_closed: number;
    progression_items: number;
    resolved_progression_items: number;
    progression_outcomes: {
      progress: number;
      repeat: number;
      hold: number;
      review_required: number;
    };
    next_week_start: string | null;
    confirmed_availability: {
      weekly_availability_id: string;
      week_start: string;
      recorded_at: string;
      source_observation_ids: string[];
      rule_version: string;
      windows: WeeklyAvailabilityWindowProjection[];
    } | null;
    unresolved_environment_prescriptions: number;
  };
  sessions: PlannedSessionProjection[];
}

export interface CurrentWeekProjection {
  athlete_id: string;
  athlete_display_name: string;
  as_of: string;
  safety_policy_assignment: {
    assignment_id: string;
    safety_policy_id: string;
    policy_version: string;
    sequence_number: number;
    assigned_at: string;
    assigned_by: string;
    applicability_rationale: string;
    rule_version: string;
  } | null;
  week: WeekProjection | null;
}

export type Confidence = "unknown" | "low" | "moderate" | "high";

export interface ProvenanceInput {
  recorded_by: string;
  source_system: string;
  ingestion_method: string;
}

interface SafetyCheckCommandBase {
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

export interface PreSessionSafetyCheckCommand extends SafetyCheckCommandBase {
  timing: "pre_session";
  related_session_execution_id?: null;
  readiness: "ready" | "limited" | "not_ready";
}

export interface PostSessionSafetyCheckCommand extends SafetyCheckCommandBase {
  timing: "post_session";
  related_session_execution_id: string;
  readiness: null;
}

export type SafetyCheckCommand = PreSessionSafetyCheckCommand | PostSessionSafetyCheckCommand;

export interface SetPerformanceInput {
  set_index: number;
  performed: boolean;
  target_completed: boolean;
  actual_repetitions?: number;
  actual_duration_seconds?: number;
  effort_rpe?: number;
  technique_constraint_met?: boolean;
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
  techniqueConstraintMet: boolean | null;
}

export interface ProgressionEvaluationCommand {
  decided_at: string;
}

export interface WeeklyAvailabilityConfirmationCommand {
  windows: Array<{
    environment_id: string;
    starts_at: string;
    ends_at: string;
  }>;
  confirmed_at: string;
  reliability: Confidence;
  provenance: ProvenanceInput;
}

export interface WeeklyRollForwardCommand {
  weekly_availability_id: string;
  prepared_at: string;
}

export interface WeeklyAvailabilityDraft {
  environmentId: string;
  startsAt: Date;
  endsAt: Date;
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

export function safetyOutcomeLabel(outcome: string): string {
  const labels: Record<string, string> = {
    proceed: "No configured concern",
    modify: "Recovery needs attention",
    hold: "Progression on hold",
    stop_and_escalate: "Further review required",
  };
  return labels[outcome] ?? "Safety result recorded";
}

export function progressionOutcomeLabel(outcome: string): string {
  const labels: Record<string, string> = {
    progress: "Progress",
    repeat: "Repeat current dose",
    hold: "Hold progression",
    review_required: "Review required",
  };
  return labels[outcome] ?? "Decision recorded";
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
    { headers: authorizedHeaders({ Accept: "application/json" }) },
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
  command:
    | SafetyCheckCommand
    | SessionExecutionCommand
    | ProgressionEvaluationCommand
    | WeeklyAvailabilityConfirmationCommand
    | WeeklyRollForwardCommand,
  fetcher: typeof fetch,
): Promise<T> {
  const response = await fetcher(url, {
    method: "POST",
    headers: authorizedHeaders({
      Accept: "application/json",
      "Content-Type": "application/json",
    }),
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

export function buildProgressionEvaluationCommand(
  decidedAt = new Date(),
): ProgressionEvaluationCommand {
  if (!Number.isFinite(decidedAt.getTime())) throw new Error("Progression time must be valid.");
  return {
    decided_at: decidedAt.toISOString(),
  };
}

export async function submitProgressionEvaluation(
  apiBaseUrl: string,
  sessionExecutionId: string,
  prescriptionId: string,
  command: ProgressionEvaluationCommand,
  fetcher: typeof fetch = fetch,
): Promise<{
  progression_decision: { id: string; outcome: string };
  revised_prescription: { id: string } | null;
}> {
  const baseUrl = apiBaseUrl.replace(/\/$/, "");
  return postSessionCommand(
    `${baseUrl}/v1/session-executions/${encodeURIComponent(sessionExecutionId)}/prescriptions/${encodeURIComponent(prescriptionId)}/progression`,
    command,
    fetcher,
  );
}

export function buildWeeklyAvailabilityConfirmationCommand({
  windows,
  reliability,
  confirmedAt = new Date(),
}: {
  windows: WeeklyAvailabilityDraft[];
  reliability: Confidence;
  confirmedAt?: Date;
}): WeeklyAvailabilityConfirmationCommand {
  if (windows.length === 0) throw new Error("Confirm at least one availability window.");
  if (!Number.isFinite(confirmedAt.getTime())) throw new Error("Confirmation time must be valid.");
  return {
    windows: windows.map((window) => {
      if (!isUuid(window.environmentId)) throw new Error("Availability environment must be valid.");
      if (!Number.isFinite(window.startsAt.getTime()) || !Number.isFinite(window.endsAt.getTime())) {
        throw new Error("Availability times must be valid.");
      }
      if (window.endsAt <= window.startsAt) {
        throw new Error("Availability must end after it starts.");
      }
      return {
        environment_id: window.environmentId,
        starts_at: window.startsAt.toISOString(),
        ends_at: window.endsAt.toISOString(),
      };
    }),
    confirmed_at: confirmedAt.toISOString(),
    reliability,
    provenance: pwaProvenance,
  };
}

export async function submitWeeklyAvailabilityConfirmation(
  apiBaseUrl: string,
  weeklyPlanId: string,
  command: WeeklyAvailabilityConfirmationCommand,
  fetcher: typeof fetch = fetch,
): Promise<{ availability: { id: string; week_start: string } }> {
  const baseUrl = apiBaseUrl.replace(/\/$/, "");
  return postSessionCommand(
    `${baseUrl}/v1/weekly-plans/${encodeURIComponent(weeklyPlanId)}/availability-confirmations`,
    command,
    fetcher,
  );
}

export function buildWeeklyRollForwardCommand({
  weeklyAvailabilityId,
  preparedAt = new Date(),
}: {
  weeklyAvailabilityId: string;
  preparedAt?: Date;
}): WeeklyRollForwardCommand {
  if (!isUuid(weeklyAvailabilityId)) {
    throw new Error("Confirmed weekly availability must be valid.");
  }
  if (!Number.isFinite(preparedAt.getTime())) throw new Error("Preparation time must be valid.");
  return {
    weekly_availability_id: weeklyAvailabilityId,
    prepared_at: preparedAt.toISOString(),
  };
}

export async function submitWeeklyRollForward(
  apiBaseUrl: string,
  weeklyPlanId: string,
  command: WeeklyRollForwardCommand,
  fetcher: typeof fetch = fetch,
): Promise<{ weekly_plan: { id: string; week_start: string; status: string } }> {
  const baseUrl = apiBaseUrl.replace(/\/$/, "");
  return postSessionCommand(
    `${baseUrl}/v1/weekly-plans/${encodeURIComponent(weeklyPlanId)}/roll-forward`,
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
          if (draft.techniqueConstraintMet !== null) {
            result.technique_constraint_met = draft.techniqueConstraintMet;
          }
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
