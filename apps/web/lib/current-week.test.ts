import { describe, expect, it, vi } from "vitest";

import {
  buildProgressionEvaluationCommand,
  buildExecutionCommand,
  CurrentWeekRequestError,
  fetchCurrentWeek,
  formatDose,
  isUuid,
  progressionOutcomeLabel,
  safetyOutcomeLabel,
  sessionStatusLabel,
  shiftIsoDate,
  submitSafetyCheck,
  submitSessionExecution,
  submitProgressionEvaluation,
  type PrescriptionProjection,
} from "./current-week";

const prescription: PrescriptionProjection = {
  order_index: 1,
  section: "primary",
  prescription_id: "00000000-0000-4000-8000-000000000001",
  exercise_id: "00000000-0000-4000-8000-000000000002",
  exercise_name: "Fixture squat",
  adaptation_id: "00000000-0000-4000-8000-000000000003",
  adaptation_name: "Maximum strength",
  reason_for_inclusion: "Fixture reason",
  sets: 3,
  repetitions_per_set: 5,
  duration_seconds: null,
  intensity_targets: ["RPE 6-8"],
  rest_seconds: 120,
  adherence: null,
  progression: null,
  progression_action: {
    status: "awaiting_execution" as const,
    rule_reference: "fixture-progression@1.0.0",
    progression_policy_id: null,
    adjustment_dimension: null,
    adjustment_description: null,
    reason: "progression requires a recorded session execution",
  },
};

const session = {
  planned_session_id: "00000000-0000-4000-8000-000000000010",
  session_template_id: "00000000-0000-4000-8000-000000000011",
  session_name: "Fixture session",
  starts_at: "2026-08-24T14:00:00Z",
  ends_at: "2026-08-24T15:00:00Z",
  planned_duration_minutes: 60,
  environment_id: "00000000-0000-4000-8000-000000000012",
  environment_name: "Fixture gym",
  status: "modified" as const,
  pre_session_safety: {
    decision_id: "00000000-0000-4000-8000-000000000013",
    outcome: "modify",
    required_modifications: ["reduce_volume"],
    decided_at: "2026-08-24T13:55:00Z",
  },
  execution: null,
  prescriptions: [prescription],
};

describe("current-week presentation", () => {
  it("formats prescribed repetitions and duration without changing the dose", () => {
    expect(formatDose(prescription)).toBe("3 × 5");
    expect(
      formatDose({ ...prescription, sets: 1, repetitions_per_set: null, duration_seconds: 1080 }),
    ).toBe("1 × 18 min");
  });

  it("moves the requested date by a week and validates athlete identifiers", () => {
    expect(shiftIsoDate("2026-08-24", 7)).toBe("2026-08-31");
    expect(isUuid(prescription.prescription_id)).toBe(true);
    expect(isUuid("not-an-athlete-id")).toBe(false);
  });

  it("uses explicit, safety-aware status labels", () => {
    expect(sessionStatusLabel("cleared")).toBe("Safety cleared");
    expect(sessionStatusLabel("needs_attention")).toBe("Needs attention");
    expect(sessionStatusLabel("stopped_safety")).toBe("Stopped for safety");
    expect(safetyOutcomeLabel("modify")).toBe("Recovery needs attention");
    expect(progressionOutcomeLabel("repeat")).toBe("Repeat current dose");
    expect(progressionOutcomeLabel("unexpected-policy-output")).toBe("Decision recorded");
  });

  it("requests the dated projection and preserves API errors", async () => {
    const success = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(
        JSON.stringify({
          athlete_id: prescription.adaptation_id,
          athlete_display_name: "Fixture athlete",
          as_of: "2026-08-24",
          week: null,
        }),
        { status: 200 },
      ),
    );
    await expect(
      fetchCurrentWeek("http://localhost:8000/", prescription.adaptation_id, "2026-08-24", success),
    ).resolves.toMatchObject({ athlete_display_name: "Fixture athlete", week: null });
    expect(success).toHaveBeenCalledWith(
      `http://localhost:8000/v1/athletes/${prescription.adaptation_id}/current-week?on=2026-08-24`,
      { headers: { Accept: "application/json" } },
    );

    const failure = vi
      .fn<typeof fetch>()
      .mockResolvedValue(new Response(JSON.stringify({ detail: "athlete does not exist" }), { status: 404 }));
    await expect(
      fetchCurrentWeek("http://localhost:8000", prescription.adaptation_id, "2026-08-24", failure),
    ).rejects.toEqual(new CurrentWeekRequestError("athlete does not exist", 404));
  });

  it("builds an exact completed execution without changing prescribed identity or dose", () => {
    const command = buildExecutionCommand({
      session,
      drafts: [{
        prescriptionId: prescription.prescription_id,
        performedSets: 3,
        actualDosePerSet: 5,
        itemRpe: 7,
        techniqueConstraintMet: true,
      }],
      safetyDecisionId: session.pre_session_safety.decision_id,
      requiredModifications: session.pre_session_safety.required_modifications,
      startedAt: new Date("2026-08-24T14:00:00Z"),
      endedAt: new Date("2026-08-24T15:00:00Z"),
      sessionRpe: 7,
      note: " completed ",
      reliability: "high",
      recordedAt: new Date("2026-08-24T15:01:00Z"),
    });

    expect(command).toMatchObject({
      pre_session_safety_decision_id: session.pre_session_safety.decision_id,
      status: "completed",
      applied_modifications: ["reduce_volume"],
      session_rpe: 7,
      note: "completed",
      reliability: "high",
    });
    expect(command.items[0]).toMatchObject({
      prescription_id: prescription.prescription_id,
      status: "completed",
      item_rpe: 7,
    });
    expect(command.items[0].performances).toHaveLength(3);
    expect(command.items[0].performances[0]).toMatchObject({
      set_index: 1,
      performed: true,
      target_completed: true,
      actual_repetitions: 5,
      effort_rpe: 7,
      technique_constraint_met: true,
    });
  });

  it("represents partial and not-started work explicitly", () => {
    const partial = buildExecutionCommand({
      session,
      drafts: [{
        prescriptionId: prescription.prescription_id,
        performedSets: 2,
        actualDosePerSet: 4,
        itemRpe: null,
        techniqueConstraintMet: false,
      }],
      safetyDecisionId: session.pre_session_safety.decision_id,
      requiredModifications: [],
      startedAt: new Date("2026-08-24T14:00:00Z"),
      endedAt: new Date("2026-08-24T14:45:00Z"),
      sessionRpe: null,
      note: null,
      reliability: "moderate",
      recordedAt: new Date("2026-08-24T14:46:00Z"),
    });
    expect(partial.status).toBe("partial");
    expect(partial.items[0].performances[0]).toMatchObject({
      performed: true,
      technique_constraint_met: false,
    });
    expect(partial.items[0].performances.at(-1)).toEqual({
      set_index: 3,
      performed: false,
      target_completed: false,
    });

    const notStarted = buildExecutionCommand({
      session,
      drafts: [{
        prescriptionId: prescription.prescription_id,
        performedSets: 0,
        actualDosePerSet: 5,
        itemRpe: null,
        techniqueConstraintMet: null,
      }],
      safetyDecisionId: session.pre_session_safety.decision_id,
      requiredModifications: [],
      startedAt: null,
      endedAt: null,
      sessionRpe: 8,
      note: null,
      reliability: "moderate",
      recordedAt: new Date("2026-08-24T14:46:00Z"),
    });
    expect(notStarted).toMatchObject({
      status: "not_started",
      started_at: null,
      ended_at: null,
      session_rpe: null,
    });
    expect(notStarted.items[0]).toMatchObject({ status: "not_started", performances: [] });
  });

  it("posts safety and execution commands only to their governed use-case endpoints", async () => {
    const fetcher = vi.fn<typeof fetch>().mockImplementation(async () =>
      new Response(JSON.stringify({ decision: { id: "decision", outcome: "proceed" }, execution: { id: "execution", status: "completed" } }), { status: 201 }),
    );
    const safetyCommand = {
      safety_policy_id: "00000000-0000-4000-8000-000000000020",
      timing: "pre_session" as const,
      readiness: "ready" as const,
      unusual_soreness: false,
      major_sleep_disruption: false,
      major_schedule_limitation: false,
      signals: [] as [],
      note: null,
      reported_at: "2026-08-24T13:55:00Z",
      decided_at: "2026-08-24T13:55:00Z",
      reliability: "moderate" as const,
      provenance: {
        recorded_by: "unverified-athlete-user",
        source_system: "agas-web",
        ingestion_method: "interactive-form",
      },
    };
    await submitSafetyCheck("http://localhost:8000/", "plan", "session", safetyCommand, fetcher);
    expect(fetcher.mock.calls[0][0]).toBe("http://localhost:8000/v1/weekly-plans/plan/sessions/session/safety-checks");
    expect(fetcher.mock.calls[0][1]).toMatchObject({ method: "POST" });

    await submitSafetyCheck("http://localhost:8000", "plan", "session", {
      ...safetyCommand,
      timing: "post_session",
      related_session_execution_id: "00000000-0000-4000-8000-000000000021",
      readiness: null,
      reported_at: "2026-08-24T15:02:00Z",
      decided_at: "2026-08-24T15:02:00Z",
    }, fetcher);
    expect(fetcher.mock.calls[1][0]).toBe("http://localhost:8000/v1/weekly-plans/plan/sessions/session/safety-checks");
    expect(JSON.parse(fetcher.mock.calls[1][1]!.body as string)).toMatchObject({
      timing: "post_session",
      related_session_execution_id: "00000000-0000-4000-8000-000000000021",
      readiness: null,
      signals: [],
    });

    const execution = buildExecutionCommand({
      session,
      drafts: [{
        prescriptionId: prescription.prescription_id,
        performedSets: 0,
        actualDosePerSet: 5,
        itemRpe: null,
        techniqueConstraintMet: null,
      }],
      safetyDecisionId: session.pre_session_safety.decision_id,
      requiredModifications: [],
      startedAt: null,
      endedAt: null,
      sessionRpe: null,
      note: null,
      reliability: "moderate",
      recordedAt: new Date("2026-08-24T14:46:00Z"),
    });
    await submitSessionExecution("http://localhost:8000", "plan", "session", execution, fetcher);
    expect(fetcher.mock.calls[2][0]).toBe("http://localhost:8000/v1/weekly-plans/plan/sessions/session/executions");

    const progressionPolicyId = "00000000-0000-4000-8000-000000000022";
    expect(() => buildProgressionEvaluationCommand("not-a-policy-id")).toThrow(
      "A valid assigned progression policy is required.",
    );
    const progressionCommand = buildProgressionEvaluationCommand(
      progressionPolicyId,
      new Date("2026-08-24T15:03:00Z"),
    );
    expect(progressionCommand).toEqual({
      progression_policy_id: progressionPolicyId,
      exposure: null,
      decided_at: "2026-08-24T15:03:00.000Z",
      revision_prescribed_at: "2026-08-24T15:03:00.001Z",
      revised_planned_duration_minutes: null,
    });
    const executionId = "00000000-0000-4000-8000-000000000023";
    await submitProgressionEvaluation(
      "http://localhost:8000",
      executionId,
      prescription.prescription_id,
      progressionCommand,
      fetcher,
    );
    expect(fetcher.mock.calls[3][0]).toBe(
      `http://localhost:8000/v1/session-executions/${executionId}/prescriptions/${prescription.prescription_id}/progression`,
    );
  });
});
