import { expect, test, type APIResponse } from "@playwright/test";

import { mockAccessToken } from "./mock-services";
import { OIDC_TRANSACTION_COOKIE_NAME } from "../lib/oidc-login";
import { SESSION_COOKIE_NAME } from "../lib/server-session";

const athleteId = "d0000000-0000-4000-8000-000000000001";

test("reviewer workbench exposes the synthetic athlete's honest next boundary", async ({
  page,
}) => {
  await page.route("http://localhost:8000/v1/owner-alpha/operator-access**", (route) => {
    const active = route.request().method() === "POST";
    return route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(
        active
          ? {
              activated: true,
              access: {
                access_version: "owner-alpha-operator-access@1.0.0",
                status: "active",
                message: "Owner-alpha assessment and planning review access is active.",
                authenticated_issuer: "urn:agas:development",
                authenticated_subject: "local-browser",
                can_activate: false,
                roles: [
                  { role: "assessment_reviewer", status: "active", assignment_id: athleteId },
                  { role: "planning_reviewer", status: "active", assignment_id: athleteId },
                ],
              },
            }
          : {
              access_version: "owner-alpha-operator-access@1.0.0",
              status: "eligible",
              message: "This exact allowlisted owner account may activate reviewer access.",
              authenticated_issuer: "urn:agas:development",
              authenticated_subject: "local-browser",
              can_activate: true,
              roles: [
                { role: "assessment_reviewer", status: null, assignment_id: null },
                { role: "planning_reviewer", status: null, assignment_id: null },
              ],
            },
      ),
    });
  });
  await page.route("http://localhost:8000/v1/operator/planning-review-queue**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        projected_at: "2026-08-30T14:00:00Z",
        projection_version: "planning-review-queue@1.0.0",
        items: [
          {
            workflow_stage: "initial_planning",
            status: "capability_estimate_required",
            readiness: "blocked",
            athlete_id: athleteId,
            athlete_display_name: "Synthetic four-day traveler",
            strategy_id: null,
            block_id: null,
            message: "No current capability estimate is available for initial planning.",
            issues: ["No current capability estimate is available for initial planning."],
          },
        ],
      }),
    }),
  );

  await page.goto("/review/queue");

  await expect(page.getByRole("heading", { name: "Reviewer access is not active yet." }))
    .toBeVisible();
  await page.getByLabel(/I understand these are application permissions/).check();
  await page.getByRole("button", { name: "Activate owner review access" }).click();
  await expect(page.getByText("Owner-alpha review access active")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Reviewer workbench" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Synthetic four-day traveler" })).toBeVisible();
  await expect(page.getByText("capability estimate required")).toBeVisible();
  await expect(page.getByRole("link", { name: "Inspect blockers" })).toHaveAttribute(
    "href",
    `/review?athleteId=${athleteId}`,
  );
});

test("the bootstrap athlete deep link opens the PWA without UUID copy and paste", async ({
  page,
}) => {
  await page.route("http://localhost:8000/v1/**", (route) => {
    if (route.request().url().includes(`/athletes/${athleteId}/current-week`)) {
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          athlete_id: athleteId,
          athlete_display_name: "Synthetic four-day traveler",
          as_of: "2026-08-30",
          safety_policy_assignment: null,
          week: null,
        }),
      });
    }
    return route.fulfill({
      status: 404,
      contentType: "application/json",
      body: JSON.stringify({ detail: "not needed by this navigation smoke test" }),
    });
  });

  await page.goto(`/?athleteId=${athleteId}`);

  await expect(page.getByRole("heading", { name: "Synthetic four-day traveler" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Change athlete" })).toBeVisible();
  await expect(page.getByText("There is no persisted plan covering")).toBeVisible();
});

test("a phone user can safety-check and record an exact set-by-set session", async ({
  page,
}) => {
  const weeklyPlanId = "d1000000-0000-4000-8000-000000000001";
  const plannedSessionId = "d1000000-0000-4000-8000-000000000002";
  const prescriptionId = "d1000000-0000-4000-8000-000000000003";
  const safetyDecisionId = "d1000000-0000-4000-8000-000000000004";
  let safetyRecorded = false;
  let executionBody: Record<string, unknown> | null = null;

  await page.route("http://localhost:8000/v1/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (url.pathname === `/v1/athletes/${athleteId}/current-week`) {
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          athlete_id: athleteId,
          athlete_display_name: "Courtney fixture",
          as_of: "2026-09-17",
          safety_policy_assignment: {
            assignment_id: "d1000000-0000-4000-8000-000000000005",
            safety_policy_id: "d1000000-0000-4000-8000-000000000006",
            policy_version: "owner-alpha-session-safety@1.0.0",
            sequence_number: 1,
            assigned_at: "2026-09-17T12:00:00Z",
            assigned_by: "owner-alpha",
            applicability_rationale: "Owner-alpha fixture.",
            rule_version: "safety-policy-assignment@1.0.0",
          },
          week: {
            weekly_plan_id: weeklyPlanId,
            block_plan_id: "d1000000-0000-4000-8000-000000000007",
            week_start: "2026-09-14",
            week_end: "2026-09-20",
            block_week: 1,
            status: "feasible",
            availability: { source_observation_ids: [], rule_version: "fixture@1", windows: [] },
            review: {
              status: "awaiting_sessions",
              reason: "One scheduled session remains.",
              scheduled_sessions: 1,
              recorded_sessions: 0,
              completed_sessions: 0,
              post_session_closed: 0,
              progression_items: 1,
              resolved_progression_items: 0,
              progression_outcomes: { progress: 0, repeat: 0, hold: 0, review_required: 0 },
              next_week_start: null,
              confirmed_availability: null,
              unresolved_environment_prescriptions: 0,
            },
            sessions: [{
              planned_session_id: plannedSessionId,
              session_template_id: "d1000000-0000-4000-8000-000000000008",
              session_name: "Push-up foundation",
              starts_at: "2026-09-17T22:00:00Z",
              ends_at: "2026-09-17T22:06:00Z",
              planned_duration_minutes: 6,
              environment_id: "d1000000-0000-4000-8000-000000000009",
              environment_name: "Home",
              status: safetyRecorded ? "cleared" : "scheduled",
              pre_session_safety: safetyRecorded ? {
                decision_id: safetyDecisionId,
                outcome: "proceed",
                required_modifications: [],
                decided_at: "2026-09-17T21:55:00Z",
              } : null,
              execution: null,
              prescriptions: [{
                order_index: 1,
                section: "primary",
                prescription_id: prescriptionId,
                exercise_id: "d1000000-0000-4000-8000-000000000010",
                exercise_name: "Standard push-up",
                adaptation_id: "d1000000-0000-4000-8000-000000000011",
                adaptation_name: "Upper-body muscular endurance",
                reason_for_inclusion: "Scope-matched governed dose.",
                sets: 2,
                repetitions_per_set: 6,
                duration_seconds: null,
                intensity_targets: ["RPE 5-7"],
                rest_seconds: 120,
                adherence: null,
                progression: null,
                progression_action: {
                  status: "awaiting_execution",
                  rule_reference: "owner-alpha-pushup@1.0.0",
                  progression_policy_id: null,
                  adjustment_dimension: null,
                  adjustment_description: null,
                  reason: "A recorded execution is required.",
                },
              }],
            }],
          },
        }),
      });
    }
    if (
      url.pathname === `/v1/weekly-plans/${weeklyPlanId}/sessions/${plannedSessionId}/safety-checks`
      && request.method() === "POST"
    ) {
      safetyRecorded = true;
      return route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({ decision: { id: safetyDecisionId, outcome: "proceed" } }),
      });
    }
    if (
      url.pathname === `/v1/weekly-plans/${weeklyPlanId}/sessions/${plannedSessionId}/executions`
      && request.method() === "POST"
    ) {
      executionBody = request.postDataJSON() as Record<string, unknown>;
      return route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({ execution: { id: "d1000000-0000-4000-8000-000000000012", status: "partial" } }),
      });
    }
    return route.fulfill({
      status: 404,
      contentType: "application/json",
      body: JSON.stringify({ detail: "not needed by the live-workout browser test" }),
    });
  });

  await page.goto(`/?athleteId=${athleteId}&on=2026-09-17`);
  await expect(page.getByRole("heading", { name: "Push-up foundation" })).toBeVisible();
  await page.getByRole("button", { name: "Save and evaluate" }).click();
  await page.getByText("Train this session").click();
  await page.getByRole("button", { name: "Start workout" }).click();
  await page.getByLabel("Set 1 done").check();
  await page.reload();
  await page.getByText("Train this session").click();
  await page.getByRole("button", { name: "Resume saved workout" }).click();
  await expect(page.getByLabel("Set 1 done")).toBeChecked();
  await expect(page.getByLabel("Set 2 done")).not.toBeChecked();
  await page.getByLabel("Set 2 done").check();
  await page.getByLabel("Actual reps").nth(1).fill("5");
  await page.getByRole("button", { name: "Finish workout" }).click();
  await page.getByLabel("Session RPE").fill("6");
  await page.getByRole("button", { name: "Save final workout record" }).click();

  await expect.poll(() => executionBody).not.toBeNull();
  const items = executionBody!.items as Array<{
    status: string;
    performances: Array<{ actual_repetitions: number; target_completed: boolean }>;
  }>;
  expect(executionBody).toMatchObject({
    pre_session_safety_decision_id: safetyDecisionId,
    status: "partial",
    session_rpe: 6,
  });
  expect(items[0].status).toBe("partial");
  expect(items[0].performances).toMatchObject([
    { actual_repetitions: 6, target_completed: true },
    { actual_repetitions: 5, target_completed: false },
  ]);
});

test("in-week progression updates only the next unperformed session", async ({ page }) => {
  const weeklyPlanId = "d2000000-0000-4000-8000-000000000001";
  const completedSessionId = "d2000000-0000-4000-8000-000000000002";
  const nextSessionId = "d2000000-0000-4000-8000-000000000003";
  const originalPrescriptionId = "d2000000-0000-4000-8000-000000000004";
  const revisedPrescriptionId = "d2000000-0000-4000-8000-000000000005";
  const nextSafetyDecisionId = "d2000000-0000-4000-8000-000000000006";
  let executionBody: Record<string, unknown> | null = null;

  const prescription = (prescriptionId: string, repetitionsPerSet: number) => ({
    order_index: 1,
    section: "primary",
    prescription_id: prescriptionId,
    exercise_id: "d2000000-0000-4000-8000-000000000010",
    exercise_name: "Standard push-up",
    adaptation_id: "d2000000-0000-4000-8000-000000000011",
    adaptation_name: "Upper-body muscular endurance",
    reason_for_inclusion: "Scope-matched governed dose.",
    sets: 2,
    repetitions_per_set: repetitionsPerSet,
    duration_seconds: null,
    intensity_targets: ["RPE 5-7"],
    rest_seconds: 120,
    execution_guidance: null,
    adherence: null,
    progression: null,
    progression_action: {
      status: "awaiting_execution",
      rule_reference: "owner-alpha-pushup@1.0.0",
      progression_policy_id: null,
      adjustment_dimension: null,
      adjustment_description: null,
      reason: "A recorded execution is required.",
    },
  });

  await page.route("http://localhost:8000/v1/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (url.pathname === `/v1/athletes/${athleteId}/current-week`) {
      const original = prescription(originalPrescriptionId, 6);
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          athlete_id: athleteId,
          athlete_display_name: "Courtney fixture",
          as_of: "2026-09-17",
          safety_policy_assignment: {
            assignment_id: "d2000000-0000-4000-8000-000000000012",
            safety_policy_id: "d2000000-0000-4000-8000-000000000013",
            policy_version: "owner-alpha-session-safety@1.0.0",
            sequence_number: 1,
            assigned_at: "2026-09-14T12:00:00Z",
            assigned_by: "owner-alpha",
            applicability_rationale: "Owner-alpha fixture.",
            rule_version: "safety-policy-assignment@1.0.0",
          },
          week: {
            weekly_plan_id: weeklyPlanId,
            block_plan_id: "d2000000-0000-4000-8000-000000000014",
            week_start: "2026-09-14",
            week_end: "2026-09-20",
            block_week: 1,
            status: "feasible",
            availability: { source_observation_ids: [], rule_version: "fixture@1", windows: [] },
            review: {
              status: "awaiting_sessions",
              reason: "One scheduled session remains.",
              scheduled_sessions: 2,
              recorded_sessions: 1,
              completed_sessions: 1,
              post_session_closed: 1,
              progression_items: 2,
              resolved_progression_items: 1,
              progression_outcomes: { progress: 1, repeat: 0, hold: 0, review_required: 0 },
              next_week_start: null,
              confirmed_availability: null,
              unresolved_environment_prescriptions: 0,
            },
            sessions: [
              {
                planned_session_id: completedSessionId,
                session_template_id: "d2000000-0000-4000-8000-000000000015",
                session_name: "Push-up foundation — completed",
                starts_at: "2026-09-15T22:00:00Z",
                ends_at: "2026-09-15T22:06:00Z",
                planned_duration_minutes: 6,
                environment_id: "d2000000-0000-4000-8000-000000000016",
                environment_name: "Home",
                status: "completed",
                pre_session_safety: {
                  decision_id: "d2000000-0000-4000-8000-000000000017",
                  outcome: "proceed",
                  required_modifications: [],
                  decided_at: "2026-09-15T21:55:00Z",
                },
                execution: {
                  execution_id: "d2000000-0000-4000-8000-000000000018",
                  status: "completed",
                  session_rpe: 6,
                  logged_at: "2026-09-15T22:07:00Z",
                  post_session_safety_outcomes: ["proceed"],
                },
                prescriptions: [{
                  ...original,
                  adherence: {
                    adherence_id: "d2000000-0000-4000-8000-000000000019",
                    performed_sets: 2,
                    prescribed_sets: 2,
                    actual_dose_total: 12,
                    prescribed_dose_total: 12,
                    dose_unit: "repetitions",
                    set_completion_ratio: 1,
                    dose_completion_ratio: 1,
                  },
                  progression: {
                    decision_id: "d2000000-0000-4000-8000-000000000020",
                    outcome: "progress",
                    adjustment_description: "add one repetition per set",
                    decided_at: "2026-09-15T22:10:00Z",
                  },
                  progression_action: {
                    ...original.progression_action,
                    status: "completed",
                    reason: "An immutable progression decision already exists.",
                  },
                }],
              },
              {
                planned_session_id: nextSessionId,
                session_template_id: "d2000000-0000-4000-8000-000000000015",
                session_name: "Push-up foundation — next",
                starts_at: "2026-09-18T22:00:00Z",
                ends_at: "2026-09-18T22:06:00Z",
                planned_duration_minutes: 6,
                environment_id: "d2000000-0000-4000-8000-000000000016",
                environment_name: "Home",
                status: "cleared",
                pre_session_safety: {
                  decision_id: nextSafetyDecisionId,
                  outcome: "proceed",
                  required_modifications: [],
                  decided_at: "2026-09-18T21:55:00Z",
                },
                execution: null,
                prescriptions: [prescription(revisedPrescriptionId, 7)],
              },
            ],
          },
        }),
      });
    }
    if (
      url.pathname === `/v1/weekly-plans/${weeklyPlanId}/sessions/${nextSessionId}/executions`
      && request.method() === "POST"
    ) {
      executionBody = request.postDataJSON() as Record<string, unknown>;
      return route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({
          execution: {
            id: "d2000000-0000-4000-8000-000000000021",
            status: "completed",
          },
        }),
      });
    }
    return route.fulfill({
      status: 404,
      contentType: "application/json",
      body: JSON.stringify({ detail: "not needed by the in-week progression browser test" }),
    });
  });

  await page.goto(`/?athleteId=${athleteId}&on=2026-09-17`);
  const completedCard = page.locator("article.session-card").filter({
    has: page.getByRole("heading", { name: "Push-up foundation — completed" }),
  });
  const nextCard = page.locator("article.session-card").filter({
    has: page.getByRole("heading", { name: "Push-up foundation — next" }),
  });

  await expect(completedCard.getByText("2 × 6", { exact: true })).toBeVisible();
  await expect(completedCard.getByText("2/2 sets · 100% dose")).toBeVisible();
  await expect(nextCard.getByText("2 × 7", { exact: true })).toBeVisible();

  await nextCard.getByText("Train this session").click();
  await nextCard.getByRole("button", { name: "Start workout" }).click();
  await expect(nextCard.getByLabel("Actual reps").first()).toHaveValue("7");
  await nextCard.getByLabel("Set 1 done").check();
  await nextCard.getByLabel("Set 2 done").check();
  await nextCard.getByRole("button", { name: "Finish workout" }).click();
  await nextCard.getByRole("button", { name: "Save final workout record" }).click();

  await expect.poll(() => executionBody).not.toBeNull();
  const items = executionBody!.items as Array<{
    prescription_id: string;
    performances: Array<{ actual_repetitions: number }>;
  }>;
  expect(items).toHaveLength(1);
  expect(items[0].prescription_id).toBe(revisedPrescriptionId);
  expect(items[0].performances).toMatchObject([
    { actual_repetitions: 7 },
    { actual_repetitions: 7 },
  ]);
});

test("the first-session path surfaces a prepared assessment as the next owner action", async ({
  page,
}) => {
  await page.route("http://localhost:8000/v1/**", (route) => {
    const url = new URL(route.request().url());
    if (url.pathname === "/v1/operator/assessment-governance/candidates") {
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          projected_at: "2026-09-12T16:00:00Z",
          projection_version: "assessment-governance-candidates@1.0.0",
          items: [{
            status: "available",
            ratified_at: null,
            issues: [],
            candidate: {
              candidate_version: "assessment-governance-candidate@1.0.0",
              candidate_id: "94000000-0000-4000-8000-000000000001",
              slug: "thirty_second_chair_stand",
              release_label: "30-second chair stand owner-alpha release",
              prepared_at: "2026-09-08T10:45:00Z",
              content_digest: `sha256:${"a".repeat(64)}`,
              summary: "A narrow, repeatable first measurement.",
              measures: "Assessment-specific sit-to-stand performance.",
              does_not_measure: ["A universal athleticism score."],
              capability_domain: "muscular_endurance",
              estimate_scope: "assessment_specific:thirty_second_chair_stand_repetitions",
              setup_requirements: ["A stable armless chair."],
              protocol_steps: ["Complete controlled stands for 30 seconds."],
              stop_conditions: ["Stop for pain or dizziness."],
              operational_choices: ["A single result remains low confidence."],
              unresolved_limitations: ["Population transfer is uncertain."],
              evidence: [],
            },
          }],
        }),
      });
    }
    if (url.pathname === `/v1/athletes/${athleteId}/assessment-workflow`) {
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          athlete_id: athleteId,
          athlete_display_name: "Synthetic four-day traveler",
          as_of: "2026-09-12T16:00:00Z",
          status: "protocol_catalog_empty",
          message: "No approved protocol is available.",
          can_start_run: false,
          can_record_results: false,
          approved_self_administered_protocol_count: 0,
          due_protocol_count: 0,
          next_reassessment_at: null,
          reassessment_rule_version: "assessment-reassessment-schedule@1.0.0",
          eligibility: null,
          environments: [],
          latest_run: null,
        }),
      });
    }
    if (url.pathname === `/v1/athletes/${athleteId}/planning-status`) {
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          athlete_id: athleteId,
          athlete_display_name: "Synthetic four-day traveler",
          as_of: "2026-09-12T16:00:00Z",
          status: "capability_estimate_required",
          message: "A current capability estimate is required.",
          capability_estimate_count: 0,
          current_capability_estimate_count: 0,
          stale_capability_estimate_count: 0,
          athlete_age_years: null,
          age_limited_floor_issue_count: 0,
          approved_priority_policy_count: 0,
          approved_compatible_competency_floor_count: 0,
          covered_current_capability_estimate_count: 0,
          uncovered_current_capability_estimate_count: 0,
          requirements: [],
          initial_strategy: null,
          first_block_readiness: null,
          first_week_readiness: null,
          projection_version: "planning-status@1.0.0",
        }),
      });
    }
    if (url.pathname === `/v1/athletes/${athleteId}/current-week`) {
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          athlete_id: athleteId,
          athlete_display_name: "Synthetic four-day traveler",
          as_of: "2026-09-12",
          safety_policy_assignment: null,
          week: null,
        }),
      });
    }
    return route.fulfill({
      status: 404,
      contentType: "application/json",
      body: JSON.stringify({ detail: "not needed by prepared-assessment browser test" }),
    });
  });

  await page.goto(`/?athleteId=${athleteId}`);

  await expect(page.getByRole("heading", { name: "You have one clear next step." })).toBeVisible();
  await expect(page.getByText("AGAS has prepared a complete assessment release.").first())
    .toBeVisible();
  await expect(page.getByRole("link", { name: "Review the prepared assessment →" }))
    .toHaveAttribute("href", `/review/assessments?athleteId=${athleteId}`);
});

test("a phone user preserves a safety-stopped attempt without creating a result", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const runId = "91780000-0000-4000-8000-000000000001";
  const selectionId = "91790000-0000-4000-8000-000000000001";
  let submittedResult: Record<string, unknown> | null = null;
  let submittedAttempt: Record<string, unknown> | null = null;
  const recordedAttempts: Array<Record<string, unknown>> = [];

  await page.route("http://localhost:8000/v1/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (
      url.pathname === `/v1/athletes/${athleteId}/assessment-runs/${runId}`
        + `/selections/${selectionId}/attempts`
      && request.method() === "POST"
    ) {
      submittedAttempt = request.postDataJSON() as Record<string, unknown>;
      const attemptSequence = recordedAttempts.length + 1;
      recordedAttempts.unshift({
        attempt_id: `917c0000-0000-4000-8000-${attemptSequence.toString().padStart(12, "0")}`,
        attempt_observation_id: `917d0000-0000-4000-8000-${attemptSequence.toString().padStart(12, "0")}`,
        status: submittedAttempt.status,
        reason: submittedAttempt.reason,
        attempted_at: submittedAttempt.attempted_at,
        reliability: submittedAttempt.reliability,
        provenance: submittedAttempt.provenance,
        rule_version: "assessment-attempt-recording@1.1.0",
        eligible_for_capability_estimation: false,
      });
      return route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({
          attempt: { id: recordedAttempts[0]?.attempt_id },
          eligible_for_capability_estimation: false,
        }),
      });
    }
    if (
      url.pathname === `/v1/athletes/${athleteId}/assessment-runs/${runId}`
        + `/selections/${selectionId}/result`
      && request.method() === "POST"
    ) {
      submittedResult = request.postDataJSON() as Record<string, unknown>;
      return route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({ performance: { id: selectionId }, result_observation: { id: runId } }),
      });
    }
    if (url.pathname === `/v1/athletes/${athleteId}/assessment-workflow`) {
      const safetyStopped = recordedAttempts.some(
        (attempt) => attempt.status === "safety_stopped",
      );
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          athlete_id: athleteId,
          athlete_display_name: "Synthetic four-day traveler",
          as_of: "2026-09-25T17:00:00Z",
          status: safetyStopped ? "run_blocked" : "result_entry_ready",
          message: safetyStopped
            ? "The latest selected assessment requires a fresh readiness review."
            : "One selected assessment is ready to perform.",
          can_start_run: false,
          can_record_results: !safetyStopped,
          approved_self_administered_protocol_count: 1,
          due_protocol_count: 1,
          next_reassessment_at: null,
          reassessment_rule_version: "assessment-reassessment-schedule@1.0.0",
          eligibility: {
            eligibility_review_id: "917a0000-0000-4000-8000-000000000001",
            outcome: "selection_allowed",
            reviewed_at: "2026-09-25T16:55:00Z",
            valid_until: "2026-09-26T16:55:00Z",
            maximum_assessment_intensity: "high",
            rule_version: "assessment-readiness-screen@1.0.0",
          },
          environments: [{
            environment_id: "917b0000-0000-4000-8000-000000000001",
            name: "Measured treadmill route",
          }],
          latest_run: {
            run_id: runId,
            environment_id: "917b0000-0000-4000-8000-000000000001",
            environment_name: "Measured treadmill route",
            evaluated_at: "2026-09-25T17:00:00Z",
            rule_version: "assessment-selection-run@1.0.0",
            decisions: [{
              selection_id: selectionId,
              decision: "selected",
              reason_codes: ["eligible"],
              rationale: ["The current exact review, readiness, and environment permit selection."],
              assessment_definition_id: "91730000-0000-4000-8000-000000000001",
              assessment_definition_review_id: "91750000-0000-4000-8000-000000000001",
              name: "12-minute walk/run distance",
              domain: "aerobic_capacity",
              intensity: "high",
              unit_or_scale: "meters",
              protocol_version: "agas-twelve-minute-walk-run@1.0.0",
              protocol_instructions: [
                "Warm up with easy walking and only familiar comfortable jogging.",
                "Cover the greatest distance sustainable for 12 minutes; walking is always permitted.",
                "Stop for pain, chest discomfort, dizziness, instability, or unusual shortness of breath.",
              ],
              result_entry_instructions: "Enter direct measured meters only; do not enter a stopped attempt.",
              measurement_schema: {
                measurement_type: "number",
                label: "Distance covered in 12 minutes",
                minimum: 0,
                maximum: null,
                step: 1,
                allowed_values: [],
                measurement_schema_version: "twelve-minute-walk-run-distance-m@1.0.0",
              },
              applicability_notes: "Owner-alpha direct within-person tracking only.",
              uncertainty: "Pacing and conditions affect repeatability.",
              evidence_claim_ids: ["91710000-0000-4000-8000-000000000001"],
              review_version: "agas-twelve-minute-walk-run-review@1.0.0",
              result_status: safetyStopped ? "safety_review_required" : "ready",
              attempts: recordedAttempts,
              result: null,
            }],
          },
          history_projection_version: "assessment-history-projection@1.0.0",
          history_runs: [{
            run_id: runId,
            assessment_eligibility_review_id: "917a0000-0000-4000-8000-000000000001",
            environment_id: "917b0000-0000-4000-8000-000000000001",
            environment_name: "Measured treadmill route",
            context_observation_id: "917e0000-0000-4000-8000-000000000001",
            evaluated_at: "2026-09-25T17:00:00Z",
            rule_version: "assessment-selection-run@1.0.0",
            selections: [{
              selection_id: selectionId,
              decision: "selected",
              reason_codes: ["eligible"],
              rationale: ["The current exact review, readiness, and environment permit selection."],
              source_observation_ids: ["917e0000-0000-4000-8000-000000000001"],
              evaluated_at: "2026-09-25T17:00:00Z",
              rule_version: "assessment-selection@1.0.0",
              assessment_definition_id: "91730000-0000-4000-8000-000000000001",
              assessment_definition_review_id: "91750000-0000-4000-8000-000000000001",
              assessment_eligibility_review_id: "917a0000-0000-4000-8000-000000000001",
              name: "12-minute walk/run distance",
              domain: "aerobic_capacity",
              unit_or_scale: "meters",
              protocol_version: "agas-twelve-minute-walk-run@1.0.0",
              review_version: "agas-twelve-minute-walk-run-review@1.0.0",
              attempts: recordedAttempts,
              completed_result: null,
            }],
          }],
        }),
      });
    }
    if (url.pathname === `/v1/athletes/${athleteId}/current-week`) {
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          athlete_id: athleteId,
          athlete_display_name: "Synthetic four-day traveler",
          as_of: "2026-09-25",
          safety_policy_assignment: null,
          week: null,
        }),
      });
    }
    return route.fulfill({
      status: 404,
      contentType: "application/json",
      body: JSON.stringify({ detail: "not needed by assessment-completion browser test" }),
    });
  });

  await page.goto(`/?athleteId=${athleteId}`);

  const assessment = page.getByRole("article").filter({
    has: page.getByRole("heading", { name: "12-minute walk/run distance" }),
  });
  await expect(assessment).toBeVisible();
  await expect(assessment.getByText(/walking is always permitted/i).first()).toBeVisible();
  const genericRecordButton = assessment.getByRole("button", { name: "Record incomplete attempt" });
  await expect(assessment.getByRole("button")).toBeDisabled();

  await assessment.getByLabel(
    "I did not complete the protocol, but no listed stop condition occurred.",
  ).check();
  const incompleteReason = assessment.getByLabel("Why was the protocol incomplete?");
  await expect(incompleteReason).toBeVisible();
  await expect(genericRecordButton).toBeDisabled();
  await incompleteReason.selectOption("external_interruption");
  await expect(genericRecordButton).toBeEnabled();
  await genericRecordButton.click();
  await expect.poll(() => recordedAttempts.length).toBe(1);
  expect(submittedAttempt).toMatchObject({
    status: "incomplete",
    reason: "external_interruption",
    protocol_completed: false,
    stop_condition_occurred: false,
  });

  await assessment.getByLabel("I stopped because a listed stop condition occurred.").check();
  await expect(assessment.getByText("Do not record this as a completed assessment.")).toBeVisible();
  await expect(assessment.getByText("A stopped attempt is not a zero result.")).toBeVisible();
  await expect(assessment.getByLabel("Distance covered in 12 minutes")).toBeDisabled();
  await expect(genericRecordButton).toBeEnabled();
  await genericRecordButton.click();

  await expect.poll(() => submittedAttempt).not.toBeNull();
  expect(submittedAttempt).toMatchObject({
    status: "safety_stopped",
    reason: "listed_stop_condition",
    protocol_completed: false,
    stop_condition_occurred: true,
  });
  expect(submittedAttempt).not.toHaveProperty("measurement");
  expect(submittedResult).toBeNull();
  await expect(assessment.getByText("safety stopped")).toBeVisible();
  await expect(assessment.getByText("Not eligible for capability estimation").first()).toBeVisible();
  await expect(assessment.getByText("Fresh readiness review required.")).toBeVisible();
  await expect(assessment.getByRole("button", { name: /Record/ })).toHaveCount(0);
  await page.getByText("Assessment history across 1 selection run").click();
  const history = page.getByRole("group").filter({
    hasText: "Incomplete attempts, completed direct observations, and derived capability estimates",
  });
  await expect(history.getByText("safety stopped")).toBeVisible();
  await expect(history.getByText("Not eligible for capability estimation").first()).toBeVisible();
  expect(submittedResult).toBeNull();
});

test("the athlete home routes directly to the exact next planning boundary", async ({ page }) => {
  await page.route("http://localhost:8000/v1/**", (route) => {
    const url = new URL(route.request().url());
    if (url.pathname === `/v1/athletes/${athleteId}/current-week`) {
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          athlete_id: athleteId,
          athlete_display_name: "Synthetic four-day traveler",
          as_of: "2026-09-12",
          safety_policy_assignment: null,
          week: null,
        }),
      });
    }
    if (url.pathname === `/v1/athletes/${athleteId}/assessment-workflow`) {
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          athlete_id: athleteId,
          athlete_display_name: "Synthetic four-day traveler",
          as_of: "2026-09-12T16:00:00Z",
          status: "reassessment_not_due",
          message: "The current assessment remains usable.",
          can_start_run: false,
          can_record_results: false,
          approved_self_administered_protocol_count: 1,
          due_protocol_count: 0,
          next_reassessment_at: "2026-10-12T16:00:00Z",
          reassessment_rule_version: "assessment-reassessment-schedule@1.0.0",
          eligibility: {
            eligibility_review_id: "d1000000-0000-4000-8000-000000000002",
            outcome: "selection_allowed",
            reviewed_at: "2026-09-12T15:00:00Z",
            valid_until: "2026-09-19T15:00:00Z",
            maximum_assessment_intensity: "moderate",
            rule_version: "assessment-readiness-screen@1.0.0",
          },
          environments: [],
          latest_run: null,
        }),
      });
    }
    if (url.pathname === `/v1/athletes/${athleteId}/planning-status`) {
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          athlete_id: athleteId,
          athlete_display_name: "Synthetic four-day traveler",
          as_of: "2026-09-12T16:00:00Z",
          status: "planning_context_review_required",
          message: "A reviewed initial planning context is required.",
          capability_estimate_count: 1,
          current_capability_estimate_count: 1,
          stale_capability_estimate_count: 0,
          athlete_age_years: 35,
          age_limited_floor_issue_count: 0,
          approved_priority_policy_count: 1,
          approved_compatible_competency_floor_count: 1,
          covered_current_capability_estimate_count: 1,
          uncovered_current_capability_estimate_count: 0,
          requirements: [],
          initial_strategy: null,
          first_block_readiness: null,
          first_week_readiness: null,
          projection_version: "planning-status@1.0.0",
        }),
      });
    }
    if (url.pathname === "/v1/operator/planning-review-queue") {
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          projected_at: "2026-09-12T16:00:00Z",
          projection_version: "planning-review-queue@1.0.0",
          items: [{
            workflow_stage: "initial_planning",
            status: "ready_for_explicit_initial_planning",
            readiness: "ready",
            athlete_id: athleteId,
            athlete_display_name: "Synthetic four-day traveler",
            strategy_id: null,
            block_id: null,
            message: "The measured state is ready for an explicit initial strategy review.",
            issues: [],
          }],
        }),
      });
    }
    return route.fulfill({
      status: 404,
      contentType: "application/json",
      body: JSON.stringify({ detail: "not needed by planning handoff browser test" }),
    });
  });

  await page.goto(`/?athleteId=${athleteId}`);

  await expect(page.getByRole("heading", { name: "You have one clear next step." })).toBeVisible();
  await expect(page.getByText("The measured state is ready for an explicit initial strategy review.").first())
    .toBeVisible();
  await expect(page.getByRole("link", { name: "Review your initial strategy →" }))
    .toHaveAttribute("href", `/review?athleteId=${athleteId}`);
});

test("a signed-in account recovers one owned profile without device-local state", async ({
  page,
}) => {
  await page.route("http://localhost:8000/v1/**", (route) => {
    const url = new URL(route.request().url());
    if (url.pathname === "/v1/athletes") {
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          projection_version: "account-athlete-directory@1.0.0",
          athletes: [
            {
              athlete_id: athleteId,
              display_name: "Recovered athlete",
              profile_created_at: "2026-08-22T18:00:00Z",
              goals: ["Build broad athletic capacity"],
              environments: [
                {
                  environment_id: "d0000000-0000-4000-8000-000000000002",
                  name: "Home",
                },
              ],
              ownership_granted_at: "2026-08-22T18:00:00Z",
              ownership_rule_version: "profile-environment-onboarding@1.0.0",
            },
          ],
        }),
      });
    }
    if (url.pathname.includes(`/athletes/${athleteId}/current-week`)) {
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          athlete_id: athleteId,
          athlete_display_name: "Recovered athlete",
          as_of: "2026-08-30",
          safety_policy_assignment: null,
          week: null,
        }),
      });
    }
    return route.fulfill({
      status: 404,
      contentType: "application/json",
      body: JSON.stringify({ detail: "not needed by profile recovery smoke test" }),
    });
  });

  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Recovered athlete" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Change athlete" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Create profile" })).toHaveCount(0);
});

test("multiple owned profiles require an explicit non-destructive choice", async ({ page }) => {
  const newerId = "d0000000-0000-4000-8000-000000000003";
  await page.route("http://localhost:8000/v1/**", (route) => {
    const url = new URL(route.request().url());
    if (url.pathname === "/v1/athletes") {
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          projection_version: "account-athlete-directory@1.0.0",
          athletes: [
            {
              athlete_id: newerId,
              display_name: "Courtney Szabo",
              profile_created_at: "2026-09-12T10:00:00Z",
              goals: ["Train consistently"],
              environments: [],
              ownership_granted_at: "2026-09-12T10:00:00Z",
              ownership_rule_version: "profile-environment-onboarding@1.0.0",
            },
            {
              athlete_id: athleteId,
              display_name: "Courtney Szabo",
              profile_created_at: "2026-08-22T18:00:00Z",
              goals: ["Build broad athletic capacity"],
              environments: [
                {
                  environment_id: "d0000000-0000-4000-8000-000000000002",
                  name: "Home",
                },
              ],
              ownership_granted_at: "2026-08-22T18:00:00Z",
              ownership_rule_version: "profile-environment-onboarding@1.0.0",
            },
          ],
        }),
      });
    }
    if (url.pathname.includes(`/athletes/${newerId}/current-week`)) {
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          athlete_id: newerId,
          athlete_display_name: "Courtney Szabo",
          as_of: "2026-08-30",
          safety_policy_assignment: null,
          week: null,
        }),
      });
    }
    return route.fulfill({
      status: 404,
      contentType: "application/json",
      body: JSON.stringify({ detail: "not needed by profile choice smoke test" }),
    });
  });

  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Choose the profile to continue." }))
    .toBeVisible();
  await expect(page.getByText("Nothing has been merged or deleted")).toBeVisible();
  await expect(page.getByRole("button", { name: "Create profile" })).toHaveCount(0);
  await page.getByRole("button", { name: /Train consistently/ }).click();
  await expect(page.getByRole("heading", { name: "Courtney Szabo" })).toBeVisible();
});

test("the phone workflow turns a factual readiness report into a narrow decision", async ({
  page,
}) => {
  let readinessAllowed = false;
  let submittedBody: Record<string, unknown> | null = null;
  await page.route("http://localhost:8000/v1/**", async (route) => {
    const request = route.request();
    if (request.url().includes(`/athletes/${athleteId}/assessment-readiness-reports`)) {
      submittedBody = request.postDataJSON() as Record<string, unknown>;
      readinessAllowed = true;
      return route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({
          observation_id: "d1000000-0000-4000-8000-000000000001",
          eligibility_review_id: "d1000000-0000-4000-8000-000000000002",
          outcome: "selection_allowed",
          maximum_assessment_intensity: "moderate",
          valid_until: "2026-09-09T16:00:00Z",
          next_action: "Continue to governed low/moderate assessment selection.",
          jump_exposure_need_id: "d1000000-0000-4000-8000-000000000004",
          jump_exposure_status: "recent_exposure_confirmed",
          jump_exposure_next_action: "Recent jump exposure is confirmed for assessment selection.",
          created: true,
          rule_version: "assessment-readiness-screen@1.0.0",
        }),
      });
    }
    if (request.url().includes(`/athletes/${athleteId}/assessment-workflow`)) {
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          athlete_id: athleteId,
          athlete_display_name: "Synthetic four-day traveler",
          as_of: "2026-09-08T16:00:00Z",
          status: readinessAllowed ? "ready_to_start" : "eligibility_required",
          message: readinessAllowed
            ? "Governed assessment selection is ready to start."
            : "A current readiness decision is required before assessment selection.",
          can_start_run: false,
          can_record_results: false,
          approved_self_administered_protocol_count: 1,
          due_protocol_count: 1,
          next_reassessment_at: null,
          reassessment_rule_version: "assessment-reassessment-schedule@1.0.0",
          eligibility: readinessAllowed
            ? {
                eligibility_review_id: "d1000000-0000-4000-8000-000000000002",
                outcome: "selection_allowed",
                reviewed_at: "2026-09-08T16:00:00Z",
                valid_until: "2026-09-09T16:00:00Z",
                maximum_assessment_intensity: "moderate",
                rule_version: "assessment-readiness-screen@1.0.0",
              }
            : null,
          environments: readinessAllowed
            ? [{ environment_id: "d1000000-0000-4000-8000-000000000003", name: "Home" }]
            : [],
          latest_run: null,
        }),
      });
    }
    if (request.url().includes(`/athletes/${athleteId}/planning-status`)) {
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          athlete_id: athleteId,
          athlete_display_name: "Synthetic four-day traveler",
          as_of: "2026-09-08T16:00:00Z",
          status: "capability_estimate_required",
          message: "A current capability estimate is required.",
          capability_estimate_count: 0,
          current_capability_estimate_count: 0,
          stale_capability_estimate_count: 0,
          athlete_age_years: null,
          age_limited_floor_issue_count: 0,
          approved_priority_policy_count: 0,
          approved_compatible_competency_floor_count: 0,
          covered_current_capability_estimate_count: 0,
          uncovered_current_capability_estimate_count: 0,
          requirements: [],
          initial_strategy: null,
          first_block_readiness: null,
          first_week_readiness: null,
          projection_version: "planning-status@1.0.0",
        }),
      });
    }
    if (request.url().includes(`/athletes/${athleteId}/current-week`)) {
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          athlete_id: athleteId,
          athlete_display_name: "Synthetic four-day traveler",
          as_of: "2026-09-08",
          safety_policy_assignment: null,
          week: null,
        }),
      });
    }
    return route.fulfill({
      status: 404,
      contentType: "application/json",
      body: JSON.stringify({ detail: "not needed by readiness browser test" }),
    });
  });

  await page.goto(`/?athleteId=${athleteId}`);
  await expect(page.getByText("This is a stop/go screen, not medical clearance.")).toBeVisible();
  const submit = page.getByRole("button", { name: "Evaluate current readiness" });
  await expect(submit).toBeDisabled();
  await page.getByLabel("I confirm that I am an adult").check();
  await page.getByLabel("Has a healthcare professional told you that you have cardiovascular").selectOption("no");
  await page.getByLabel("Do you currently have any concerning signs or symptoms?").selectOption("no");
  await page.getByLabel("Has a healthcare professional told you to avoid or limit exercise").selectOption("no");
  await page.getByLabel("Do you currently have lower-body pain").selectOption("no");
  await page.getByLabel("Using the exact stable chair setup").selectOption("yes");
  await page.getByLabel("Do you currently have upper-body, wrist, or hand pain").selectOption("no");
  await page.getByLabel("On a clear nonslip surface").selectOption("yes");
  await page.getByLabel("During the last 28 days").selectOption("yes");
  await page
    .getByLabel("On a nonslip floor, can you comfortably complete one controlled standard push-up")
    .selectOption("yes");
  await page.getByLabel("These answers describe my current state").check();
  await submit.click();

  await expect(page.getByText("Continue to governed low/moderate assessment selection.")).toBeVisible();
  await expect(page.getByText("Recent jump exposure is confirmed for assessment selection.")).toBeVisible();
  await expect(page.getByText("Open the Assessment section below and select the governed assessment set.").first())
    .toBeVisible();
  expect(submittedBody).toMatchObject({
    adult_confirmed: true,
    concerning_signs_or_symptoms: "no",
    controlled_chair_stand_without_arms: "yes",
    current_upper_body_wrist_or_hand_concern: "no",
    controlled_standard_pushup: "yes",
    controlled_two_foot_jump_and_landing: "yes",
    recent_two_foot_jump_and_landing_exposure_28_days: "yes",
    answers_confirmed: true,
  });
  expect(submittedBody).not.toHaveProperty("outcome");
});

test("the phone workflow appends a date-of-birth report for age applicability", async ({
  page,
}) => {
  let submittedBody: Record<string, unknown> | null = null;
  await page.route("http://localhost:8000/v1/**", async (route) => {
    const request = route.request();
    if (request.url().includes(`/athletes/${athleteId}/date-of-birth-reports`)) {
      submittedBody = request.postDataJSON() as Record<string, unknown>;
      return route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({
          observation_id: "d2000000-0000-4000-8000-000000000001",
          demographics: {
            athlete_id: athleteId,
            as_of: "2026-09-09T12:00:00Z",
            date_of_birth: "1990-01-03",
            age_years: 36,
            source_observation_id: "d2000000-0000-4000-8000-000000000001",
            source_kind: "reported_observation",
            report_count: 1,
            message: "Earlier reports remain in history.",
            projection_version: "athlete-demographics-projection@1.0.0",
          },
          created: true,
          rule_version: "athlete-date-of-birth-report@1.0.0",
        }),
      });
    }
    if (request.url().includes(`/athletes/${athleteId}/demographics`)) {
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          athlete_id: athleteId,
          as_of: "2026-09-09T12:00:00Z",
          date_of_birth: null,
          age_years: null,
          source_observation_id: null,
          source_kind: "unknown",
          report_count: 0,
          message: "Date of birth has not been reported.",
          projection_version: "athlete-demographics-projection@1.0.0",
        }),
      });
    }
    if (request.url().includes(`/athletes/${athleteId}/current-week`)) {
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          athlete_id: athleteId,
          athlete_display_name: "Synthetic four-day traveler",
          as_of: "2026-09-09",
          safety_policy_assignment: null,
          week: null,
        }),
      });
    }
    return route.fulfill({
      status: 404,
      contentType: "application/json",
      body: JSON.stringify({ detail: "not needed by demographics browser test" }),
    });
  });

  await page.goto(`/?athleteId=${athleteId}`);
  await expect(page.getByText("Age needed")).toBeVisible();
  await expect(page.getByText("Loading age information…")).toBeHidden();
  await page.getByLabel("Date of birth").fill("1990-01-03");
  await page.getByLabel("I confirm this date is correct.").check();
  await page.getByRole("button", { name: "Save date of birth" }).click();

  await expect(page.getByText("Date of birth saved as a new historical report.")).toBeVisible();
  await expect(page.getByText("Age 36")).toBeVisible();
  expect(submittedBody).toMatchObject({
    date_of_birth: "1990-01-03",
    date_of_birth_confirmed: true,
  });
  expect(submittedBody).not.toHaveProperty("age_years");
});

test("assessment workbench makes missing scientific governance explicit", async ({ page }) => {
  await page.route("http://localhost:8000/v1/operator/assessment-governance**", (route) => {
    if (route.request().url().endsWith("/candidates")) {
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          projected_at: "2026-09-08T15:00:00Z",
          projection_version: "assessment-governance-candidates@1.0.0",
          items: [{
            status: "available",
            ratified_at: null,
            issues: [],
            candidate: {
              candidate_version: "assessment-governance-candidate@1.0.0",
              candidate_id: "94000000-0000-4000-8000-000000000001",
              slug: "thirty_second_chair_stand",
              release_label: "30-second chair stand owner-alpha release",
              prepared_at: "2026-09-08T10:45:00Z",
              content_digest: `sha256:${"a".repeat(64)}`,
              summary: "A narrow, repeatable first measurement.",
              measures: "Assessment-specific sit-to-stand performance.",
              does_not_measure: ["A universal athleticism score."],
              capability_domain: "muscular_endurance",
              estimate_scope: "assessment_specific:thirty_second_chair_stand_repetitions",
              setup_requirements: ["A stable armless chair."],
              protocol_steps: ["Complete controlled stands for 30 seconds."],
              stop_conditions: ["Stop for pain or dizziness."],
              operational_choices: ["A single result remains low confidence."],
              unresolved_limitations: ["Population transfer is uncertain."],
              evidence: [{
                title: "Primary validity study",
                source_url: "https://pubmed.ncbi.nlm.nih.gov/35949374/",
                population: "81 healthy adults aged 19-35.",
                finding: "Count correlated with comparator tests.",
                limitations: ["Single cross-sectional study."],
                conflict_disclosure: "No declared conflicts.",
              }],
            },
          }],
        }),
      });
    }
    return route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        projected_at: "2026-08-30T16:00:00Z",
        projection_version: "assessment-governance-workbench@1.1.0",
        items: [
          {
            definition: {
              id: "a0000000-0000-4000-8000-000000000001",
              slug: "fixture_cycle",
              name: "Fixture cycle",
              domain: "aerobic_capacity",
              observation_type: "fixture_cycle_result",
              intensity: "moderate",
              unit_or_scale: "w",
              protocol_version: "fixture-cycle@1.0.0",
            },
            status: "unreviewed",
            readiness: "blocked",
            current_review: null,
            review_history: [],
            current_estimation_policy: null,
            estimation_policy_history: [],
            evidence_claims: [],
            review_evidence_governance: null,
            estimation_policy_evidence_governance: null,
            issues: [
              "assessment definition has no protocol review history",
              "no capability-estimation policy exists for this definition",
            ],
          },
        ],
      }),
    });
  });

  await page.goto(`/review/assessments?athleteId=${athleteId}`);

  await expect(page.getByRole("heading", { name: "Assessment governance" })).toBeVisible();
  await expect(page.getByText("Access is not scientific qualification.")).toBeVisible();
  await expect(page.getByRole("heading", { name: "30-second chair stand owner-alpha release" })).toBeVisible();
  await expect(page.getByText("A universal athleticism score.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Approve exact release" })).toBeDisabled();
  await expect(page.getByRole("heading", { name: "Fixture cycle" })).toBeVisible();
  await expect(page.getByText("assessment definition has no protocol review history")).toBeVisible();
  await expect(page.getByText("No capability-estimation policy exists.")).toBeVisible();
  await expect(page.getByRole("link", { name: "Return to assessment" })).toHaveAttribute(
    "href",
    `/?athleteId=${athleteId}#assessment-title`,
  );
});

test("owner can ratify exact prepared authorities, including a floor batch", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  let ratified = false;
  let floorRatified = false;
  let resourceRatified = false;
  let submittedBody: Record<string, unknown> = {};
  let submittedFloorBatchBody: Record<string, unknown> = {};
  let submittedResourceBody: Record<string, unknown> = {};
  let submittedProposalReviewBody: Record<string, unknown> = {};
  const candidate = {
    candidate_version: "planning-governance-candidate@1.0.0",
    candidate_id: "98400000-0000-4000-8000-000000000001",
    slug: "owner_alpha_conservative_priority_policy",
    release_label: "Conservative owner-alpha priority policy",
    prepared_at: "2026-09-09T10:30:00Z",
    content_digest: `sha256:${"b".repeat(64)}`,
    summary: "A transparent first ranking policy.",
    governs: ["How reviewed inputs are combined."],
    does_not_establish: ["Which adaptation Courtney should develop."],
    operational_choices: ["At most two adaptations may receive DEVELOP status."],
    unresolved_limitations: ["The numerical policy is an engineering prior."],
    evidence: [{
      title: "ACSM resistance-training position stand (2026)",
      source_url: "https://pubmed.ncbi.nlm.nih.gov/41843416/",
      population: "Healthy adults.",
      finding: "Resistance training improved multiple outcomes.",
      limitations: ["The source does not validate ranking weights."],
      conflict_disclosure: "Full-text review remains pending.",
    }],
  };
  await page.route("http://localhost:8000/v1/operator/planning-governance/candidates**", async (route) => {
    if (route.request().method() === "POST") {
      submittedBody = route.request().postDataJSON() as Record<string, unknown>;
      ratified = true;
      return route.fulfill({ contentType: "application/json", body: JSON.stringify({ ok: true }) });
    }
    return route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        projected_at: "2026-09-09T15:00:00Z",
        projection_version: "planning-governance-candidates@1.0.0",
        items: [{
          candidate,
          status: ratified ? "ratified" : "available",
          ratified_at: ratified ? "2026-09-09T15:00:00Z" : null,
          issues: [],
        }],
      }),
    });
  });
  const floorCandidate = {
    candidate_version: "competency-floor-candidate@1.1.0",
    candidate_id: "98400000-0000-4000-8000-000000000002",
    slug: "chair_stand_age_30_39_lower_reference_floor",
    release_label: "Age 30-39 chair-stand lower-reference floor",
    prepared_at: "2026-09-09T00:10:00Z",
    content_digest: `sha256:${"c".repeat(64)}`,
    summary: "A deliberately low, provisional comparison point.",
    authority_basis: {
      numeric_value_origin: "direct_study_result",
      operational_use_origin: "evidence_informed_engineering_judgment",
      numeric_value_explanation: "The number is reported directly.",
      operational_use_explanation: "Its use as a floor is provisional engineering judgment.",
    },
    domain: "muscular_endurance",
    estimate_scope: "assessment_specific:thirty_second_chair_stand_repetitions",
    unit_or_scale: "repetitions",
    threshold: 11,
    comparison_direction: "higher_is_better",
    minimum_age_years: 30,
    maximum_age_years: 39,
    governs: ["Whether a matching estimate is below this provisional lower reference."],
    does_not_establish: ["Medical safety, diagnosis, or clearance to train."],
    unresolved_limitations: ["The source is Colombian and the subgroup is small."],
    evidence: [{
      title: "Colombian adult sit-to-stand reference values (2025)",
      source_url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC13193711/",
      population: "Colombian adults aged 30-39.",
      finding: "The p2.5 value was 11 repetitions in both sex strata.",
      limitations: ["A reference percentile is not a health or safety cutoff."],
      conflict_disclosure: "The authors reported no relevant financial involvement.",
    }],
  };
  const jumpFloorCandidate = {
    ...floorCandidate,
    candidate_id: "98400000-0000-4000-8000-000000000004",
    slug: "owner_alpha_countermovement_jump_provisional_floor",
    release_label: "Owner-alpha provisional countermovement-jump floor",
    content_digest: `sha256:${"1".repeat(64)}`,
    summary: "A deliberately low owner-only jump comparison.",
    authority_basis: {
      numeric_value_origin: "engineering_judgment",
      operational_use_origin: "engineering_judgment",
      numeric_value_explanation: "The 20 centimeter value is an AGAS engineering prior, not a scientific finding.",
      operational_use_explanation: "Use is limited to the owner alpha and exact governed estimate.",
    },
    domain: "explosive_power",
    estimate_scope: "assessment_specific:countermovement_vertical_jump_height_cm",
    unit_or_scale: "centimeters",
    threshold: 20,
    governs: ["One exact owner-alpha jump-height comparison."],
    does_not_establish: ["Safety clearance or a training dose."],
    unresolved_limitations: ["Personal calibration is not yet available."],
  };
  const aerobicFloorCandidate = {
    ...floorCandidate,
    candidate_id: "91800000-0000-4000-8000-000000000001",
    slug: "owner_alpha_twelve_minute_walk_run_provisional_floor",
    release_label: "Owner-alpha provisional 12-minute walk/run floor",
    content_digest: `sha256:${"4".repeat(64)}`,
    summary: "A deliberately low owner-only 12-minute walk/run comparison.",
    authority_basis: {
      numeric_value_origin: "engineering_judgment",
      operational_use_origin: "engineering_judgment",
      numeric_value_explanation: "The 1200 meter value is an AGAS engineering prior, not a scientific finding.",
      operational_use_explanation: "Use is limited to the owner alpha and exact governed distance estimate.",
    },
    domain: "aerobic_capacity",
    estimate_scope: "assessment_specific:twelve_minute_walk_run_distance_m",
    unit_or_scale: "meters",
    threshold: 1200,
    governs: ["One exact owner-alpha 12-minute distance comparison."],
    does_not_establish: ["Medical clearance, a VO2 estimate, or a training dose."],
    unresolved_limitations: ["No source validates 1200 meters as a competency floor."],
  };
  await page.route("http://localhost:8000/v1/operator/competency-floor-candidates**", async (route) => {
    return route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        projected_at: "2026-09-10T15:00:00Z",
        projection_version: "competency-floor-candidates@1.1.0",
        items: [{
          candidate: floorCandidate,
          status: floorRatified ? "ratified" : "available",
          ratified_at: floorRatified ? "2026-09-10T15:00:00Z" : null,
          issues: [],
        }, {
          candidate: jumpFloorCandidate,
          status: "ratified",
          ratified_at: "2026-09-23T17:00:00Z",
          issues: [],
        }, {
          candidate: aerobicFloorCandidate,
          status: "ratified",
          ratified_at: "2026-09-25T17:00:00Z",
          issues: [],
        }],
        batch: {
          batch_version: "competency-floor-candidate-batch@1.0.0",
          batch_id: "98400000-0000-4000-8000-000000000100",
          content_digest: `sha256:${"f".repeat(64)}`,
          candidates: [{
            candidate_id: floorCandidate.candidate_id,
            candidate_version: floorCandidate.candidate_version,
            content_digest: floorCandidate.content_digest,
          }, {
            candidate_id: jumpFloorCandidate.candidate_id,
            candidate_version: jumpFloorCandidate.candidate_version,
            content_digest: jumpFloorCandidate.content_digest,
          }, {
            candidate_id: aerobicFloorCandidate.candidate_id,
            candidate_version: aerobicFloorCandidate.candidate_version,
            content_digest: aerobicFloorCandidate.content_digest,
          }],
        },
      }),
    });
  });
  await page.route(
    "http://localhost:8000/v1/operator/competency-floor-candidate-batches/ratifications",
    async (route) => {
      submittedFloorBatchBody = route.request().postDataJSON() as Record<string, unknown>;
      floorRatified = true;
      return route.fulfill({ contentType: "application/json", body: JSON.stringify({ ok: true }) });
    },
  );
  const resourceCandidate = {
    candidate_version: "resource-governance-candidate@1.0.0",
    candidate_id: "98600000-0000-4000-8000-000000000001",
    content_digest: `sha256:${"e".repeat(64)}`,
    prepared_at: "2026-09-10T17:00:00Z",
    release_label: "First owner-alpha resource authorities",
    summary: "Exact first-block prerequisites.",
    exact_artifacts: ["Exercise: Chair sit-to-stand"],
    governs: ["Exact ontology and policy records."],
    does_not_establish: ["Sets, repetitions, effort target, rest, or a workout."],
    operational_choices: ["Partial exercise resolutions are not allocatable."],
    unresolved_limitations: ["Stable-chair availability must be reported separately."],
    evidence: [{
      title: "ACSM resistance-training position stand (2026)",
      source_url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC12965823/",
      population: "Healthy adults.",
      finding: "Resistance training improved function.",
      limitations: ["No exact dose."],
    }],
  };
  const jumpResourceCandidate = {
    ...resourceCandidate,
    candidate_id: "98600000-0000-4000-8000-000000000003",
    content_digest: `sha256:${"2".repeat(64)}`,
    release_label: "Owner-alpha explosive-power resource authorities",
    summary: "Evidence-linked countermovement-jump resources.",
    exact_artifacts: ["Exercise: Countermovement jump"],
    governs: [
      "A reviewed broad plyometric-training direction.",
      "The exact countermovement-jump exercise.",
      "Full resource resolution only.",
      "A 24-minute weekly envelope across two 12-minute sessions.",
    ],
    does_not_establish: ["Sets, contacts, rest, or a workout."],
    operational_choices: ["The weekly envelope is an engineering choice."],
    unresolved_limitations: ["Readiness and recent jumping exposure remain separate."],
    evidence: [{
      title: "Oxfeldt et al. (2019)",
      source_url: "https://pubmed.ncbi.nlm.nih.gov/31136014/",
      population: "Healthy active adults.",
      finding: "Plyometric training improved jump performance.",
      limitations: ["No exact starting dose."],
    }],
  };
  const aerobicResourceCandidate = {
    ...resourceCandidate,
    candidate_id: "91900000-0000-4000-8000-000000000001",
    content_digest: `sha256:${"5".repeat(64)}`,
    release_label: "Owner-alpha aerobic-base resource authorities",
    summary: "A narrow bundle linking an aerobic-capacity need to treadmill walk/run exercise.",
    exact_artifacts: ["Exercise: Treadmill walk/run"],
    governs: [
      "A reviewed broad aerobic-training direction.",
      "The exact treadmill walk/run exercise.",
      "Full resource resolution only.",
      "A downstream prepared-demand envelope of 24 weekly minutes across two 12-minute scheduling slots.",
    ],
    does_not_establish: ["A speed, grade, duration dose, or workout."],
    operational_choices: ["Partial exercise resolutions are not allocatable."],
    unresolved_limitations: ["Readiness, symptoms, and treadmill availability remain separate."],
    evidence: [{
      title: "ACSM position stand on exercise quantity and quality (2011)",
      source_url: "https://pubmed.ncbi.nlm.nih.gov/21694556/",
      population: "Apparently healthy adults.",
      finding: "Regular individualized aerobic exercise improves cardiorespiratory fitness.",
      limitations: ["No exact modality or dose."],
    }],
  };
  const aerobicAssessmentCandidate = {
    candidate_version: "assessment-governance-candidate@1.0.0",
    candidate_id: "91770000-0000-4000-8000-000000000001",
    slug: "twelve_minute_walk_run_distance",
    release_label: "12-minute walk/run owner-alpha release",
    prepared_at: "2026-09-25T14:30:00Z",
    content_digest: `sha256:${"6".repeat(64)}`,
    summary: "A measured field test that retains direct distance.",
    measures: "Assessment-specific distance covered in 12 minutes, in meters.",
    does_not_measure: ["Laboratory VO2, diagnosis, medical fitness, or injury risk."],
    capability_domain: "aerobic_capacity",
    estimate_scope: "assessment_specific:twelve_minute_walk_run_distance_m",
    setup_requirements: ["A measured level, unobstructed route."],
    protocol_steps: ["Cover the greatest sustainable distance for 12 minutes, walking whenever needed."],
    stop_conditions: ["Stop immediately for pain, chest discomfort, dizziness, or unusual shortness of breath."],
    operational_choices: ["The direct distance is retained without applying a VO2 prediction equation."],
    unresolved_limitations: ["Pacing, route accuracy, and conditions affect repeatability."],
    evidence: [{
      title: "Mayorga-Vega et al. (2016)",
      source_url: "https://pubmed.ncbi.nlm.nih.gov/26987118/",
      population: "Children, adolescents, and adults across 123 validity studies.",
      finding: "The 12-minute walk/run distance had a pooled validity correlation of 0.78 with criterion fitness measures.",
      limitations: ["Distance is not a direct laboratory VO2 measurement."],
      conflict_disclosure: "The authors declared no competing interests.",
    }],
  };
  await page.route(
    "http://localhost:8000/v1/operator/assessment-governance/candidates**",
    async (route) => route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        projected_at: "2026-09-25T17:00:00Z",
        projection_version: "assessment-governance-candidates@1.0.0",
        items: [{
          candidate: aerobicAssessmentCandidate,
          status: "ratified",
          ratified_at: "2026-09-25T17:00:00Z",
          issues: [],
        }],
      }),
    }),
  );
  const aerobicConstructionCandidate = {
    candidate_version: "training-construction-candidate@1.0.0",
    candidate_id: "98900000-0000-4000-8000-000000000006",
    slug: "owner_alpha_aerobic_base_duration_authorities",
    release_label: "Owner-alpha aerobic-base duration authorities",
    prepared_at: "2026-09-25T16:00:00Z",
    content_digest: `sha256:${"7".repeat(64)}`,
    summary: "A fixed 600-second starting duration with a hard 720-second progression ceiling.",
    authority_basis: {
      scientific_support: "The reviewed position stand supports regular individualized aerobic exercise, but not these exact constants.",
      engineering_prior: "The 600-second start, RPE 4-6, 60-second increment, and 720-second ceiling are conservative engineering priors.",
    },
    exact_artifacts: ["Fixed-duration dose", "Duration progression ceiling"],
    governs: [
      "Derivation of one 600-second continuous aerobic set without converting assessment meters into training seconds.",
      "A 12-minute scheduling envelope with target effort RPE 4-6 and walking always permitted.",
      "Later progression by 60 seconds only after compliant completion, with an absolute 720-second per-set ceiling.",
    ],
    does_not_establish: ["Medical clearance, diagnosis, running readiness, or permission to train."],
    unresolved_limitations: ["The exact constants are not personally calibrated."],
    evidence: [{
      claim_id: "91920000-0000-4000-8000-000000000001",
      title: "ACSM position stand on exercise quantity and quality (2011)",
      source_url: "https://pubmed.ncbi.nlm.nih.gov/21694556/",
      supported_use: "Broad individualized aerobic-training direction.",
      unsupported_specifics: "No exact duration, effort range, increment, ceiling, or response threshold.",
    }],
  };
  const jumpConstructionCandidate = {
    candidate_version: "training-construction-candidate@1.0.0",
    candidate_id: "98900000-0000-4000-8000-000000000004",
    slug: "owner_alpha_explosive_power_jump_authorities",
    release_label: "Owner-alpha explosive-power jump authorities",
    prepared_at: "2026-09-23T16:30:00Z",
    content_digest: `sha256:${"3".repeat(64)}`,
    summary: "A fixed 3 by 3 starting dose with nine initial jump contacts, 120 seconds rest, and RPE 5-7.",
    authority_basis: {
      scientific_support: "The review supports the broad direction that plyometric training can improve jump performance.",
      engineering_prior: "The exact contact count, RPE, rest, and progression caps are conservative engineering priors.",
    },
    exact_artifacts: ["Fixed dose", "Jump-contact exposure cap"],
    governs: [
      "Three sets of three without converting centimeters into contacts.",
      "Nine initial contacts, 120 seconds rest, and RPE 5-7.",
      "Exposure-validated progression only.",
    ],
    does_not_establish: ["Medical clearance or permission to train."],
    unresolved_limitations: ["The constants are not personally calibrated."],
    evidence: [{
      claim_id: "91410000-0000-4000-8000-000000000001",
      title: "Oxfeldt et al. (2019)",
      source_url: "https://pubmed.ncbi.nlm.nih.gov/31136014/",
      supported_use: "Broad plyometric-training direction.",
      unsupported_specifics: "No exact contact count, RPE, rest, or progression cap.",
    }],
  };
  await page.route("http://localhost:8000/v1/operator/resource-governance/candidates**", async (route) => {
    if (route.request().method() === "POST") {
      submittedResourceBody = route.request().postDataJSON() as Record<string, unknown>;
      resourceRatified = true;
      return route.fulfill({ contentType: "application/json", body: JSON.stringify({ ok: true }) });
    }
    return route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        projected_at: "2026-09-10T18:00:00Z",
        projection_version: "resource-governance-candidates@1.0.0",
        items: [{
          candidate: resourceCandidate,
          status: resourceRatified ? "ratified" : "available",
          ratified_at: resourceRatified ? "2026-09-10T18:00:00Z" : null,
          issues: [],
        }, {
          candidate: jumpResourceCandidate,
          status: "ratified",
          ratified_at: "2026-09-23T17:00:00Z",
          issues: [],
        }, {
          candidate: aerobicResourceCandidate,
          status: "ratified",
          ratified_at: "2026-09-25T17:00:00Z",
          issues: [],
        }],
      }),
    });
  });
  await page.route(
    "http://localhost:8000/v1/operator/training-construction-candidates**",
    async (route) => route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        projected_at: "2026-09-10T18:00:00Z",
        projection_version: "training-construction-candidates@1.0.0",
        items: [{
          candidate: jumpConstructionCandidate,
          status: "ratified",
          ratified_at: "2026-09-23T17:00:00Z",
          issues: [],
        }, {
          candidate: aerobicConstructionCandidate,
          status: "ratified",
          ratified_at: "2026-09-25T17:00:00Z",
          issues: [],
        }],
      }),
    }),
  );
  const proposalBatch = {
        batch_version: "competency-floor-proposal-batch@1.0.0",
        batch_id: "c3b1083d-5d15-520e-b449-4f3539434be5",
        label: "Owner-alpha adult competency-floor research batch 1",
        prepared_at: "2026-09-12T17:00:00Z",
        content_digest: `sha256:${"a".repeat(64)}`,
        source_catalog: [{
          source_id: "acsm-12-table-3-8",
          title: "ACSM's Guidelines for Exercise Testing and Prescription",
          authors: ["Cemal Ozemek"],
          edition: "12th edition",
          publisher: "Wolters Kluwer",
          publication_year: 2026,
          isbn13: "9781975219246",
          table_locator: "Table 3.8, Treadmill-Based Cardiorespiratory Fitness",
          page_locator: "PDF pages 226-228",
          source_population: "FRIEND Registry adults aged 30-39.",
          reported_value: "The 55th-percentile male value was 41.6 mL/kg/min.",
          source_role: "direct_reference",
          limitations: ["Requires directly measured maximal treadmill testing."],
        }],
        proposals: [{
          proposal_version: "competency-floor-proposal@1.0.0",
          proposal_id: "98800000-0000-4000-8000-000000000001",
          slug: "treadmill_vo2max_male_30_39_p55",
          label: "Treadmill VO2max · male reference · age 30-39",
          prepared_at: "2026-09-12T17:00:00Z",
          content_digest: `sha256:${"d".repeat(64)}`,
          stage: "proposal_only",
          domain: "aerobic_capacity",
          estimate_scope: "assessment_specific:direct_treadmill_vo2max",
          measurement: "Directly measured maximal treadmill VO2max",
          unit_or_scale: "mL/kg/min",
          threshold: 41.6,
          comparison_direction: "higher_is_better",
          minimum_age_years: 30,
          maximum_age_years: 39,
          sex_scope: "male_reference",
          numeric_value_origin: "direct_textbook_reference",
          operational_use_origin: "evidence_informed_engineering_proposal",
          threshold_rationale: "Uses the table's 55th percentile as a reviewable proposal.",
          population_match: "moderate",
          population_match_notes: "Age matches; occupation and training history do not.",
          source_ids: ["acsm-12-table-3-8"],
          evidence_gap: "The source does not validate an AGAS floor.",
          prerequisites_before_release: ["Govern the exact assessment."],
          does_not_establish: ["Medical safety."],
          review_questions: ["Is the 55th percentile the right boundary?"],
        }],
        release_boundary: "Proposal only; no active floor is created.",
  };
  await page.route(
    "http://localhost:8000/v1/operator/competency-floor-proposal-reviews",
    async (route) => route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        projected_at: "2026-09-13T01:00:00Z",
        projection_version: "competency-floor-proposal-review-projection@1.0.0",
        batch: proposalBatch,
        items: [{
          proposal: proposalBatch.proposals[0],
          status: submittedProposalReviewBody.decision ?? "unreviewed",
          current_review: submittedProposalReviewBody.decision ? {
            id: "98700000-0000-4000-8000-000000000010",
            schema_version: "1.0.0",
            created_at: "2026-09-13T01:00:00Z",
            proposal_id: proposalBatch.proposals[0].proposal_id,
            proposal_content_digest: proposalBatch.proposals[0].content_digest,
            batch_id: proposalBatch.batch_id,
            batch_content_digest: proposalBatch.content_digest,
            decision: submittedProposalReviewBody.decision,
            sequence_number: 1,
            supersedes_review_id: null,
            reviewed_at: "2026-09-13T01:00:00Z",
            reviewer_account_id: "98700000-0000-4000-8000-000000000011",
            reviewer_authority_assignment_id: "98700000-0000-4000-8000-000000000012",
            rationale: submittedProposalReviewBody.rationale,
            attestation: "Feedback only.",
            review_version: "competency-floor-proposal-review@1.0.0",
          } : null,
        }],
      }),
    }),
  );
  await page.route(
    "http://localhost:8000/v1/operator/competency-floor-proposals/*/reviews",
    async (route) => {
      submittedProposalReviewBody = route.request().postDataJSON() as Record<string, unknown>;
      return route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({
          created: true,
          training_authority_created: false,
          review: {
            id: "98700000-0000-4000-8000-000000000010",
            schema_version: "1.0.0",
            created_at: "2026-09-13T01:00:00Z",
            proposal_id: proposalBatch.proposals[0].proposal_id,
            proposal_content_digest: proposalBatch.proposals[0].content_digest,
            batch_id: proposalBatch.batch_id,
            batch_content_digest: proposalBatch.content_digest,
            decision: submittedProposalReviewBody.decision,
            sequence_number: 1,
            supersedes_review_id: null,
            reviewed_at: "2026-09-13T01:00:00Z",
            reviewer_account_id: "98700000-0000-4000-8000-000000000011",
            reviewer_authority_assignment_id: "98700000-0000-4000-8000-000000000012",
            rationale: submittedProposalReviewBody.rationale,
            attestation: "Feedback only.",
            review_version: "competency-floor-proposal-review@1.0.0",
          },
        }),
      });
    },
  );

  await page.goto(`/review/planning-authorities?athleteId=${athleteId}`);

  await expect(page.getByRole("heading", { name: "Prepared planning authorities" })).toBeVisible();
  const jumpReview = page.getByRole("region", { name: "Why AGAS may propose jump training" });
  await expect(jumpReview).toBeVisible();
  await expect(jumpReview.getByText("20 centimeters", { exact: true })).toBeVisible();
  await expect(jumpReview.getByText(/without converting centimeters into contacts/)).toBeVisible();
  await expect(jumpReview.getByText(/exact contact count, RPE, rest, and progression caps/))
    .toBeVisible();
  const aerobicReview = page.getByRole("region", { name: "Why AGAS may propose aerobic-base training" });
  await expect(aerobicReview).toBeVisible();
  await expect(aerobicReview.getByText("1200 meters", { exact: true })).toBeVisible();
  await expect(aerobicReview.getByText(/No laboratory VO2 conversion/)).toBeVisible();
  await expect(aerobicReview.getByText(/one 600-second continuous aerobic set/)).toBeVisible();
  await expect(aerobicReview.getByText(/absolute 720-second per-set ceiling/)).toBeVisible();
  await expect(aerobicReview.getByRole("link", { name: "Review exact assessment" })).toHaveAttribute(
    "href",
    `/review/assessments?athleteId=${athleteId}#candidate-${aerobicAssessmentCandidate.candidate_id}`,
  );
  await expect(page.getByRole("heading", { name: "Approve the prepared authority set once" }))
    .toBeVisible();
  await expect(page.getByRole("button", { name: "Approve prepared authority set" }))
    .toBeDisabled();
  await expect(page.getByText("Which adaptation Courtney should develop.")).toBeVisible();
  const approve = page.getByRole("button", { name: "Approve exact policy" });
  await expect(approve).toBeDisabled();
  await page.getByLabel(/I reviewed the policy scope/).check();
  await approve.click();
  await expect(page.getByText(/This policy can now appear in initial-planning preparation/)).toBeVisible();
  await expect(page.getByRole("link", { name: "Re-check this athlete’s setup" })).toHaveAttribute(
    "href",
    `/?athleteId=${athleteId}#first-session-path-title`,
  );
  expect(submittedBody).toEqual({
    candidate_version: candidate.candidate_version,
    content_digest: candidate.content_digest,
    approval_attestation: true,
  });
  expect(submittedBody).not.toHaveProperty("deficit_weight");

  await expect(page.getByRole("heading", { name: "Competency-floor candidates" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Adult competency-floor proposals" })).toBeVisible();
  await page.getByText("Source table and population", { exact: true }).click();
  await expect(page.getByText("Table 3.8, Treadmill-Based Cardiorespiratory Fitness")).toBeVisible();
  await expect(page.getByText("FRIEND Registry adults aged 30-39.")).toBeVisible();
  await expect(page.getByText("41.6 mL/kg/min", { exact: true })).toBeVisible();
  await expect(page.getByText("Medical safety, diagnosis, or clearance to train.")).toBeVisible();
  await expect(page.getByText("evidence informed engineering judgment")).toBeVisible();
  await page.getByRole("button", { name: "Advance to engineering" }).click();
  await expect(page.getByText(/was saved as feedback only/)).toBeVisible();
  expect(submittedProposalReviewBody).toEqual({
    proposal_content_digest: `sha256:${"d".repeat(64)}`,
    batch_id: proposalBatch.batch_id,
    batch_content_digest: proposalBatch.content_digest,
    decision: "advance",
    rationale: "Advance this exact proposal for engineering preparation of its assessment, applicability, and governed authority artifacts.",
    feedback_only_attestation: true,
  });
  expect(submittedProposalReviewBody).not.toHaveProperty("threshold");
  const approveFloorBatch = page.getByRole("button", { name: "Approve exact batch (1 new)" });
  await expect(approveFloorBatch).toBeDisabled();

  await expect(page.getByRole("heading", { name: "First-block authority candidates" })).toBeVisible();
  await expect(page.getByText("Exercise: Chair sit-to-stand")).toBeVisible();
  const approveResource = page.getByRole("button", { name: "Approve resource authorities" });
  await expect(approveResource).toBeDisabled();

  await page.getByLabel(/I reviewed all currently available exact authority cards below/).check();
  await page.getByRole("button", { name: "Approve prepared authority set" }).click();
  await expect(page.getByText(/Approved 2 exact authority group/)).toBeVisible();
  await expect(page.getByText(/The floor can now be applied only/).first()).toBeVisible();
  await expect(page.getByText(/support a prepared resource demand/).first()).toBeVisible();
  expect(submittedFloorBatchBody).toEqual({
    batch_version: "competency-floor-candidate-batch@1.0.0",
    batch_id: "98400000-0000-4000-8000-000000000100",
    content_digest: `sha256:${"f".repeat(64)}`,
    candidates: [{
      candidate_id: floorCandidate.candidate_id,
      candidate_version: floorCandidate.candidate_version,
      content_digest: floorCandidate.content_digest,
    }, {
      candidate_id: jumpFloorCandidate.candidate_id,
      candidate_version: jumpFloorCandidate.candidate_version,
      content_digest: jumpFloorCandidate.content_digest,
    }, {
      candidate_id: aerobicFloorCandidate.candidate_id,
      candidate_version: aerobicFloorCandidate.candidate_version,
      content_digest: aerobicFloorCandidate.content_digest,
    }],
    approval_attestation: true,
  });
  expect(submittedFloorBatchBody).not.toHaveProperty("threshold");
  expect(submittedResourceBody).toEqual({
    candidate_version: resourceCandidate.candidate_version,
    content_digest: resourceCandidate.content_digest,
    approval_attestation: true,
  });
  expect(submittedResourceBody).not.toHaveProperty("adaptation_role_weight");
});

test("owner can accept a system-prepared planning context without inventing scores", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const contextId = "98500000-0000-4000-8000-000000000001";
  const estimateId = "96000000-0000-4000-8000-000000000010";
  const floorId = "99000000-0000-4000-8000-000000000001";
  const floorReviewId = "99100000-0000-4000-8000-000000000001";
  const adaptationId = "a0000000-0000-4000-8000-000000000004";
  let submittedBody: Record<string, unknown> = {};
  const candidateContext = {
    adaptation_id: adaptationId,
    competency_floor_id: floorId,
    competency_floor_review_id: floorReviewId,
    capability_estimate_id: estimateId,
    general_relevance: 0,
    goal_relevance: 0,
    prerequisite_value: 0,
    expected_trainability: 0,
    transfer_value: 0,
    fatigue_cost: 0,
    time_cost: 0,
    interference_cost: 0,
    safe_to_train: true,
    introductory_exposure_needed: false,
    prerequisites_met: true,
    prerequisite_adaptation_ids: [],
    cultivate_comparative_advantage: false,
    source_observation_ids: ["93000000-0000-4000-8000-000000000010"],
    evidence_claim_ids: ["91000000-0000-4000-8000-000000000010"],
  };
  const draft = {
    id: contextId,
    schema_version: "1.0.0",
    created_at: "2026-09-10T16:00:00Z",
    athlete_id: athleteId,
    priority_policy_id: "98000000-0000-4000-8000-000000000002",
    priority_policy_review_id: "98300000-0000-4000-8000-000000000002",
    candidate_contexts: [candidateContext],
    horizon_months: 12,
    review_after_days: 28,
    authored_by_account_id: "10000000-0000-4000-8000-000000000001",
    author_authority_assignment_id: "20000000-0000-4000-8000-000000000001",
    authored_at: "2026-09-10T16:00:00Z",
    applicability_rationale: "System prepared exact context.",
    uncertainty: "No workout or medical clearance.",
    draft_version: "initial-planning-context-draft@1.0.0",
  };
  const candidate = {
    candidate_version: "prepared-initial-planning-context@1.0.0",
    candidate_id: contextId,
    content_digest: `sha256:${"d".repeat(64)}`,
    prepared_at: "2026-09-10T16:00:00Z",
    athlete_id: athleteId,
    athlete_display_name: "Courtney",
    status: "available",
    summary: "AGAS prepared the exact first planning context from governed state.",
    priority_policy_id: draft.priority_policy_id,
    priority_policy_review_id: draft.priority_policy_review_id,
    policy_version: "owner-alpha-deficit-only-priority@1.0.0",
    floor_version: "chair-stand-age-30-39-lower-reference-floor@1.0.0",
    estimate_scope: "assessment_specific:thirty_second_chair_stand_repetitions",
    candidate_context: candidateContext,
    horizon_months: 12,
    review_after_days: 28,
    applicability_rationale: "Zero means unused, not unimportant.",
    uncertainty: "The estimate is low confidence.",
    components: [{
      field: "general_relevance",
      value: 0,
      treatment: "unused",
      basis: "Explicit zero paired with zero policy weight.",
      limitation: "No governed magnitude exists.",
    }],
    expected_priority_state: "develop",
    expected_priority_score: 0.045,
    safety_boundary: "This is not medical clearance; each session needs its safety gate.",
    accepted_draft_id: null,
    accepted_draft: null,
    accepted_review: null,
  };
  await page.route(
    `http://localhost:8000/v1/operator/athletes/${athleteId}/initial-planning-preparation**`,
    (route) => route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        athlete_id: athleteId,
        athlete_display_name: "Courtney",
        projected_at: "2026-09-10T16:00:00Z",
        athlete_age_years: 35,
        status: "planning_context_review_required",
        message: "Ready for exact context review.",
        initial_strategy_id: null,
        estimate_options: [],
        stale_estimates: [],
        priority_policy_options: [],
        evidence_claims: [],
        floor_applicability_issues: [],
        projection_version: "initial-planning-preparation@1.1.0",
      }),
    }),
  );
  await page.route(
    `http://localhost:8000/v1/operator/athletes/${athleteId}/prepared-initial-planning-context**`,
    async (route) => {
      if (route.request().method() === "POST") {
        submittedBody = route.request().postDataJSON() as Record<string, unknown>;
        return route.fulfill({
          status: 201,
          contentType: "application/json",
          body: JSON.stringify({
            candidate_id: contextId,
            candidate_content_digest: candidate.content_digest,
            created: true,
            draft,
            ratification_version: "prepared-initial-planning-context-ratification@1.0.0",
          }),
        });
      }
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          athlete_id: athleteId,
          projected_at: "2026-09-10T16:00:00Z",
          status: "available",
          message: "One exact context is ready.",
          candidate,
          blockers: [],
          projection_version: "prepared-initial-planning-context-projection@1.0.0",
        }),
      });
    },
  );

  await page.goto(`/review?athleteId=${athleteId}`);
  await page.getByRole("button", { name: "Load eligible inputs" }).click();
  await expect(page.getByRole("heading", { name: "Review what AGAS prepared" })).toBeVisible();
  await expect(page.getByText("DEVELOP", { exact: true })).toBeVisible();
  await expect(page.getByText("This is not medical clearance", { exact: false })).toBeVisible();
  const accept = page.getByRole("button", { name: "Accept prepared context" });
  await expect(accept).toBeDisabled();
  await page.getByLabel(/I inspected the exact prepared context/).check();
  await accept.click();
  await expect(page.getByRole("heading", { name: "Review the exact stored draft" })).toBeVisible();
  expect(submittedBody).toEqual({
    candidate_version: candidate.candidate_version,
    content_digest: candidate.content_digest,
    approval_attestation: true,
  });
  expect(submittedBody).not.toHaveProperty("general_relevance");
});

test("owner can accept a prepared resource envelope without authoring a dose", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const strategyId = "97000000-0000-4000-8000-000000000001";
  const priorityId = "97100000-0000-4000-8000-000000000001";
  const candidateId = "97200000-0000-4000-8000-000000000001";
  const adaptationId = "a0000000-0000-4000-8000-000000000004";
  const environmentId = "97300000-0000-4000-8000-000000000001";
  const candidateDigest = `sha256:${"e".repeat(64)}`;
  let accepted = false;
  let submittedBody: Record<string, unknown> = {};
  const result = {
    stimulus_requirement: {
      id: "97400000-0000-4000-8000-000000000001",
      rationale: "Exact controlled chair stimulus.",
    },
    exercise_resolution: {
      id: "97500000-0000-4000-8000-000000000001",
      status: "full",
      selected_exercise_id: "b1000000-0000-4000-8000-000000000001",
      unresolved_issues: [],
    },
    resource_demand: {
      id: "97600000-0000-4000-8000-000000000001",
      minimum_weekly_minutes: 10,
      target_weekly_minutes: 10,
      sessions_per_week: 2,
      demand_version: "owner-alpha-chair-stand-resource-envelope@1.0.0",
    },
    decision_record: {
      id: "97700000-0000-4000-8000-000000000001",
      decision: "Prepare active resource demand.",
      reason: `Prepared candidate digest: ${candidateDigest}.`,
      evidence: [`long_range_strategy:${strategyId}`],
      uncertainty: "No workout dose or safety clearance.",
      decision_version: "resource-demand-operator-review@1.0.0",
    },
  };
  const candidate = {
    candidate_version: "prepared-resource-demand@1.0.0",
    candidate_id: candidateId,
    content_digest: candidateDigest,
    prepared_at: "2026-09-10T18:00:00Z",
    status: accepted ? "accepted" : "available",
    athlete_id: athleteId,
    strategy_id: strategyId,
    priority_id: priorityId,
    priority_state: "develop",
    previous_priority_state: null,
    adaptation_id: adaptationId,
    adaptation_name: "Muscular endurance",
    environment_id: environmentId,
    environment_name: "Home",
    environment_snapshot: {
      captured_at: "2026-09-10T18:00:00Z",
      available_equipment: [],
      source_availability_ids: [],
      floor_area_m2: 4,
      max_noise_level: "high",
      outdoor_access: false,
    },
    resource_authority_candidate_id: "98600000-0000-4000-8000-000000000001",
    resource_authority_content_digest: `sha256:${"f".repeat(64)}`,
    stimulus_specification: {},
    exercise_candidate_id: "b1000000-0000-4000-8000-000000000001",
    exercise_name: "Chair sit-to-stand",
    exercise_resolver_policy_id: "98700000-0000-4000-8000-000000000001",
    expected_resolution_status: "full",
    expected_selected_exercise_id: "b1000000-0000-4000-8000-000000000001",
    minimum_weekly_minutes: 10,
    target_weekly_minutes: 10,
    sessions_per_week: 2,
    per_session_scheduling_minutes: 5,
    scheduling_basis: "A small engineering scheduling envelope, not a dose.",
    applicability_rationale: "Uses the exact ratified authority and factual Home state.",
    uncertainty: "No repetitions, sets, effort, tempo, rest, or progression is established.",
    safety_boundary: "Every session still requires its safety gate.",
    dose_boundary: "Two slots are scheduling resources, not an exercise prescription.",
    strategy_cycle: {
      cycle: "initial",
      predecessor_strategy_id: null,
      triggering_block_review_id: null,
      predecessor_block_plan_id: null,
      predecessor_block_ends_on: null,
      prior_priorities: [],
    },
    identities: {
      stimulus_requirement_id: result.stimulus_requirement.id,
      exercise_resolution_id: result.exercise_resolution.id,
      resource_demand_id: result.resource_demand.id,
      decision_record_id: result.decision_record.id,
    },
    accepted_result: accepted ? result : null,
  };
  await page.route(
    `http://localhost:8000/v1/operator/strategies/${strategyId}/resource-demand-preparation**`,
    (route) => route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        strategy: {
          id: strategyId,
          athlete_id: athleteId,
          block_hypothesis: "Develop the measured muscular-endurance deficit.",
          generated_at: "2026-09-10T17:00:00Z",
          next_review_at: "2026-10-08T17:00:00Z",
          rule_version: "long-range-strategy@1.0.0",
        },
        projected_at: "2026-09-10T18:00:00Z",
        priorities: [{
          priority: {
            id: priorityId,
            adaptation_id: adaptationId,
            state: "develop",
            score: 0.1,
            rank: 1,
            development_allocation: 1,
            rationale: ["Measured deficit."],
          },
          adaptation: { id: adaptationId, name: "Muscular endurance", domain: "muscular_endurance" },
          demand_history: [],
        }],
        source_observations: [],
        evidence_claims: [],
        environments: [],
        exercise_resolver_policies: [],
        exercise_catalog: [],
        projection_version: "resource-demand-preparation@1.0.0",
      }),
    }),
  );
  await page.route(
    `http://localhost:8000/v1/operator/strategies/${strategyId}/prepared-resource-demands**`,
    async (route) => {
      if (route.request().method() === "POST") {
        submittedBody = route.request().postDataJSON() as Record<string, unknown>;
        accepted = true;
        return route.fulfill({
          status: 201,
          contentType: "application/json",
          body: JSON.stringify({
            candidate_id: candidateId,
            candidate_content_digest: candidateDigest,
            created: true,
            result,
            ratification_version: "prepared-resource-demand-ratification@1.0.0",
          }),
        });
      }
      return route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({
          strategy_id: strategyId,
          athlete_id: athleteId,
          projected_at: "2026-09-10T18:00:00Z",
          status: accepted ? "accepted" : "available",
          message: accepted ? "Already stored." : "One exact demand is ready.",
          candidates: [{ ...candidate, status: accepted ? "accepted" : "available", accepted_result: accepted ? result : null }],
          blockers: [],
          projection_version: "prepared-resource-demand-projection@1.0.0",
        }),
      });
    },
  );

  await page.goto(`/review/resource-demands?strategyId=${strategyId}`);
  await page.getByRole("button", { name: "Load strategy preparation" }).click();
  await expect(page.getByRole("heading", { name: "Reserve the first governed training resource." })).toBeVisible();
  await expect(page.getByText("This is not the workout dose.")).toBeVisible();
  const accept = page.getByRole("button", { name: "Accept prepared resource demand" });
  await expect(accept).toBeDisabled();
  await page.getByLabel(/I reviewed this exact environment/).check();
  await accept.click();
  await expect(page.getByRole("heading", { name: "full resolution recorded" })).toBeVisible();
  expect(submittedBody).toEqual({
    candidate_version: candidate.candidate_version,
    content_digest: candidate.content_digest,
    approval_attestation: true,
  });
  expect(submittedBody).not.toHaveProperty("minimum_weekly_minutes");
  expect(submittedBody).not.toHaveProperty("stimulus_specification");
});

test("the installable shell fails closed to an honest offline screen", async ({ context, page }) => {
  await page.goto("/");

  const manifestResponse = await page.request.get("/manifest.webmanifest");
  expect(manifestResponse.ok()).toBe(true);
  const manifest = (await manifestResponse.json()) as {
    display?: string;
    icons?: { purpose?: string; src?: string }[];
  };
  expect(manifest.display).toBe("standalone");
  expect(manifest.icons).toEqual(
    expect.arrayContaining([
      expect.objectContaining({ purpose: "any", src: "/icons/agas-icon.svg" }),
      expect.objectContaining({ purpose: "maskable", src: "/icons/agas-icon-maskable.svg" }),
    ]),
  );

  await page.evaluate(async () => {
    await navigator.serviceWorker.register("/sw.js", { scope: "/" });
    await navigator.serviceWorker.ready;
    if (navigator.serviceWorker.controller) return;
    await new Promise<void>((resolve) => {
      navigator.serviceWorker.addEventListener("controllerchange", () => resolve(), { once: true });
    });
  });

  await context.setOffline(true);
  try {
    await page.reload({ waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading", { name: "You’re offline" })).toBeVisible();
    await expect(page.getByText("No athlete data is shown, changed, or queued")).toBeVisible();
  } finally {
    await context.setOffline(false);
  }
});

test("the same-origin API gateway fails closed without a server session", async ({ request }) => {
  const response = await request.get("/api/agas/v1/athletes/athlete-1/current-week");

  expect(response.status()).toBe(401);
  expect(response.headers()["cache-control"]).toBe("no-store");
  expect(await response.json()).toEqual({ detail: "Authentication is required." });
});

function responseCookie(response: APIResponse, name: string): string {
  const header = response
    .headersArray()
    .find(({ name: headerName, value }) =>
      headerName.toLowerCase() === "set-cookie" && value.startsWith(`${name}=`),
    )?.value;
  const match = new RegExp(`^${name}=([^;,]+)`).exec(header ?? "");
  expect(match, `${name} must be set`).not.toBeNull();
  return `${name}=${match?.[1] ?? ""}`;
}

test("browser login establishes an encrypted session that reaches the private API", async ({
  request,
}) => {
  const login = await request.get("/auth/login?return_to=%2F", { maxRedirects: 0 });
  expect(login.status()).toBe(303);
  expect(login.headers()["cache-control"]).toBe("no-store");
  const transactionCookie = responseCookie(login, OIDC_TRANSACTION_COOKIE_NAME);
  const authorizationUrl = login.headers().location;
  expect(authorizationUrl).toContain("http://127.0.0.1:3998/authorize?");
  expect(authorizationUrl).toContain("code_challenge_method=S256");

  const authorization = await request.get(authorizationUrl, { maxRedirects: 0 });
  expect(authorization.status()).toBe(303);
  const callbackUrl = authorization.headers().location;
  expect(callbackUrl).toContain("http://127.0.0.1:3100/auth/callback?");

  const callback = await request.get(callbackUrl, {
    headers: { cookie: transactionCookie },
    maxRedirects: 0,
  });
  expect(callback.status()).toBe(303);
  expect(callback.headers().location).toBe("http://127.0.0.1:3100/");
  const sessionCookie = responseCookie(callback, SESSION_COOKIE_NAME);
  expect(sessionCookie).not.toContain(mockAccessToken);

  const privateResponse = await request.get("/api/agas/v1/conformance/session", {
    headers: { cookie: sessionCookie },
  });
  expect(privateResponse.status()).toBe(200);
  expect(privateResponse.headers()["cache-control"]).toBe("no-store");
  expect(await privateResponse.json()).toEqual({
    authorization_received: true,
    subject: "e2e-athlete-owner",
  });

  const replay = await request.get(callbackUrl, {
    headers: { cookie: transactionCookie },
    maxRedirects: 0,
  });
  expect(replay.status()).toBe(502);
  expect(await replay.json()).toEqual({
    detail: "Identity provider returned an invalid response.",
  });
});
